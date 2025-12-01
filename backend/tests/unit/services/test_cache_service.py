"""
Unit tests for the CacheService class.

This test module provides comprehensive coverage of the CacheService functionality,
including error handling, edge cases, and performance considerations.
"""

import pytest
import json
import base64
from datetime import datetime
from unittest.mock import patch, AsyncMock

# Import the service and mocks
from src.services.cache import CacheService
from src.models.cache_models import CacheStats
import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
)
from tests.mocks.redis_mock import create_mock_redis_client


class TestCacheService:
    """Test cases for CacheService class."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client for testing."""
        return create_mock_redis_client()

    @pytest.fixture
    def cache_service(self, mock_redis_client):
        """Create a CacheService instance with a mock Redis client."""
        with patch("services.cache.aioredis.from_url", return_value=mock_redis_client):
            service = CacheService()
            service._client = mock_redis_client
            service._redis_available = True
            service._redis_disabled = False
            return service

    @pytest.fixture
    def disabled_cache_service(self):
        """Create a CacheService instance with Redis disabled."""
        with patch.dict(os.environ, {"DISABLE_REDIS": "true"}):
            service = CacheService()
            service._redis_available = False
            service._redis_disabled = True
            service._client = None
            return service

    @pytest.fixture
    def cache_service_with_unavailable_redis(self):
        """Create a CacheService instance with Redis unavailable."""
        service = CacheService()
        service._client = None
        service._redis_available = False
        service._redis_disabled = False
        return service

    class TestInitialization:
        """Test cases for CacheService initialization."""

        def test_init_with_redis_enabled(self):
            """Test initialization with Redis enabled."""
            mock_client = create_mock_redis_client()
            with patch("services.cache.aioredis.from_url", return_value=mock_client):
                service = CacheService()
                assert service._redis_disabled is False
                assert service._client is mock_client
                assert service._redis_available is True

        def test_init_with_redis_disabled(self):
            """Test initialization with Redis disabled."""
            with patch.dict(os.environ, {"DISABLE_REDIS": "true"}):
                service = CacheService()
                assert service._redis_disabled is True
                assert service._client is None
                assert service._redis_available is False

        def test_init_with_redis_connection_error(self):
            """Test initialization when Redis connection fails."""
            with patch(
                "services.cache.aioredis.from_url",
                side_effect=Exception("Connection error"),
            ):
                service = CacheService()
                assert service._redis_available is False
                assert service._client is None

    class TestJobStatusMethods:
        """Test cases for job status caching methods."""

        @pytest.mark.asyncio
        async def test_set_job_status(self, cache_service):
            """Test setting job status."""
            job_id = "test-job-123"
            status = {"progress": 50, "status": "processing"}

            await cache_service.set_job_status(job_id, status)

            # Verify the key was set in Redis
            expected_key = f"conversion_jobs:{job_id}:status"
            cached_data = await cache_service._client.get(expected_key)
            assert json.loads(cached_data) == status

        @pytest.mark.asyncio
        async def test_set_job_status_with_datetime(self, cache_service):
            """Test setting job status with datetime objects."""
            job_id = "test-job-123"
            status = {
                "progress": 50,
                "status": "processing",
                "updated_at": datetime(2023, 1, 1, 12, 0, 0),
            }

            await cache_service.set_job_status(job_id, status)

            # Verify the key was set in Redis with datetime converted to ISO string
            expected_key = f"conversion_jobs:{job_id}:status"
            cached_data = await cache_service._client.get(expected_key)
            parsed_data = json.loads(cached_data)

            assert parsed_data["progress"] == 50
            assert parsed_data["status"] == "processing"
            assert parsed_data["updated_at"] == "2023-01-01T12:00:00"

        @pytest.mark.asyncio
        async def test_set_job_status_disabled(self, disabled_cache_service):
            """Test setting job status when Redis is disabled."""
            job_id = "test-job-123"
            status = {"progress": 50, "status": "processing"}

            # Should not raise an error, just return early
            await disabled_cache_service.set_job_status(job_id, status)

        @pytest.mark.asyncio
        async def test_get_job_status(self, cache_service):
            """Test getting job status."""
            job_id = "test-job-123"
            status = {"progress": 75, "status": "completed"}

            # First set the status
            await cache_service.set_job_status(job_id, status)

            # Then retrieve it
            result = await cache_service.get_job_status(job_id)
            assert result == status

        @pytest.mark.asyncio
        async def test_get_job_status_not_found(self, cache_service):
            """Test getting job status when job doesn't exist."""
            job_id = "nonexistent-job"

            result = await cache_service.get_job_status(job_id)
            assert result is None

        @pytest.mark.asyncio
        async def test_get_job_status_disabled(self, disabled_cache_service):
            """Test getting job status when Redis is disabled."""
            job_id = "test-job-123"

            result = await disabled_cache_service.get_job_status(job_id)
            assert result is None

        @pytest.mark.asyncio
        async def test_set_job_status_with_unavailable_redis(
            self, cache_service_with_unavailable_redis
        ):
            """Test setting job status when Redis becomes unavailable."""
            job_id = "test-job-123"
            status = {"progress": 50, "status": "processing"}

            # Should not raise an error, just log a warning
            await cache_service_with_unavailable_redis.set_job_status(job_id, status)

    class TestProgressMethods:
        """Test cases for progress tracking methods."""

        @pytest.mark.asyncio
        async def test_track_progress(self, cache_service):
            """Test tracking job progress."""
            job_id = "test-job-123"
            progress = 50

            await cache_service.track_progress(job_id, progress)

            # Verify the progress was set
            expected_key = f"conversion_jobs:{job_id}:progress"
            cached_progress = await cache_service._client.get(expected_key)
            assert int(cached_progress) == progress

        @pytest.mark.asyncio
        async def test_set_progress_with_active_set(self, cache_service):
            """Test setting progress and adding job to active set."""
            job_id = "test-job-123"
            progress = 50

            await cache_service.set_progress(job_id, progress)

            # Verify the progress was set
            expected_key = f"conversion_jobs:{job_id}:progress"
            cached_progress = await cache_service._client.get(expected_key)
            assert int(cached_progress) == progress

            # Verify job was added to active set
            active_jobs = await cache_service._client.sadd(
                "conversion_jobs:active", job_id
            )
            assert active_jobs > 0  # At least one job should be in the set

        @pytest.mark.asyncio
        async def test_track_progress_disabled(self, disabled_cache_service):
            """Test tracking progress when Redis is disabled."""
            job_id = "test-job-123"
            progress = 50

            # Should not raise an error, just log a warning
            await disabled_cache_service.track_progress(job_id, progress)

    class TestModAnalysisMethods:
        """Test cases for mod analysis caching methods."""

        @pytest.mark.asyncio
        async def test_cache_mod_analysis(self, cache_service):
            """Test caching mod analysis."""
            mod_hash = "abc123"
            analysis = {"classes": 10, "methods": 50, "features": ["blocks", "items"]}
            ttl = 3600

            await cache_service.cache_mod_analysis(mod_hash, analysis, ttl)

            # Verify the analysis was cached
            expected_key = f"{CacheService.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"
            cached_data = await cache_service._client.get(expected_key)
            assert json.loads(cached_data) == analysis

        @pytest.mark.asyncio
        async def test_cache_mod_analysis_default_ttl(self, cache_service):
            """Test caching mod analysis with default TTL."""
            mod_hash = "abc123"
            analysis = {"classes": 10, "methods": 50, "features": ["blocks", "items"]}

            await cache_service.cache_mod_analysis(mod_hash, analysis)

            # Verify the analysis was cached
            expected_key = f"{CacheService.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"
            cached_data = await cache_service._client.get(expected_key)
            assert json.loads(cached_data) == analysis

        @pytest.mark.asyncio
        async def test_get_mod_analysis_hit(self, cache_service):
            """Test getting mod analysis with cache hit."""
            mod_hash = "abc123"
            analysis = {"classes": 10, "methods": 50, "features": ["blocks", "items"]}

            # First cache the analysis
            await cache_service.cache_mod_analysis(mod_hash, analysis)

            # Reset hit/miss counters
            cache_service._cache_hits = 0
            cache_service._cache_misses = 0

            # Then retrieve it
            result = await cache_service.get_mod_analysis(mod_hash)
            assert result == analysis
            assert cache_service._cache_hits == 1
            assert cache_service._cache_misses == 0

        @pytest.mark.asyncio
        async def test_get_mod_analysis_miss(self, cache_service):
            """Test getting mod analysis with cache miss."""
            mod_hash = "nonexistent"

            # Reset hit/miss counters
            cache_service._cache_hits = 0
            cache_service._cache_misses = 0

            # Try to retrieve it
            result = await cache_service.get_mod_analysis(mod_hash)
            assert result is None
            assert cache_service._cache_hits == 0
            assert cache_service._cache_misses == 1

        @pytest.mark.asyncio
        async def test_get_mod_analysis_with_exception(self, cache_service):
            """Test getting mod analysis when Redis throws an exception."""
            mod_hash = "abc123"

            # Make Redis client throw an exception
            cache_service._client.get = AsyncMock(side_effect=Exception("Redis error"))

            # Reset hit/miss counters
            cache_service._cache_hits = 0
            cache_service._cache_misses = 0

            # Try to retrieve it
            result = await cache_service.get_mod_analysis(mod_hash)
            assert result is None
            assert cache_service._cache_hits == 0
            assert cache_service._cache_misses == 1

    class TestConversionResultMethods:
        """Test cases for conversion result caching methods."""

        @pytest.mark.asyncio
        async def test_cache_conversion_result(self, cache_service):
            """Test caching conversion result."""
            mod_hash = "def456"
            result = {
                "success": True,
                "download_url": "http://example.com/addon.mcaddon",
            }
            ttl = 3600

            await cache_service.cache_conversion_result(mod_hash, result, ttl)

            # Verify the result was cached
            expected_key = f"{CacheService.CACHE_CONVERSION_RESULT_PREFIX}{mod_hash}"
            cached_data = await cache_service._client.get(expected_key)
            assert json.loads(cached_data) == result

        @pytest.mark.asyncio
        async def test_get_conversion_result(self, cache_service):
            """Test getting conversion result."""
            mod_hash = "def456"
            result = {
                "success": True,
                "download_url": "http://example.com/addon.mcaddon",
            }

            # First cache the result
            await cache_service.cache_conversion_result(mod_hash, result)

            # Then retrieve it
            retrieved = await cache_service.get_conversion_result(mod_hash)
            assert retrieved == result

    class TestAssetConversionMethods:
        """Test cases for asset conversion caching methods."""

        @pytest.mark.asyncio
        async def test_cache_asset_conversion(self, cache_service):
            """Test caching asset conversion."""
            asset_hash = "ghi789"
            converted_asset = b"binary_data_here"
            ttl = 3600

            await cache_service.cache_asset_conversion(asset_hash, converted_asset, ttl)

            # Verify the asset was cached
            expected_key = f"{CacheService.CACHE_ASSET_CONVERSION_PREFIX}{asset_hash}"
            cached_asset = await cache_service._client.get(expected_key)
            # Should be base64 encoded in Redis
            decoded_asset = base64.b64decode(cached_asset.encode("utf-8"))
            assert decoded_asset == converted_asset

        @pytest.mark.asyncio
        async def test_get_asset_conversion(self, cache_service):
            """Test getting asset conversion."""
            asset_hash = "ghi789"
            converted_asset = b"binary_data_here"

            # First cache the asset
            await cache_service.cache_asset_conversion(asset_hash, converted_asset)

            # Then retrieve it
            retrieved = await cache_service.get_asset_conversion(asset_hash)
            assert retrieved == converted_asset

        @pytest.mark.asyncio
        async def test_get_asset_conversion_not_found(self, cache_service):
            """Test getting asset conversion when not found."""
            asset_hash = "nonexistent"

            retrieved = await cache_service.get_asset_conversion(asset_hash)
            assert retrieved is None

    class TestExportDataMethods:
        """Test cases for export data caching methods."""

        @pytest.mark.asyncio
        async def test_set_export_data(self, cache_service):
            """Test setting export data."""
            conversion_id = "conv-123"
            export_data = b"mcaddon_data_here"
            ttl = 3600

            await cache_service.set_export_data(conversion_id, export_data, ttl)

            # Verify the data was cached
            expected_key = f"export:{conversion_id}:data"
            cached_data = await cache_service._client.get(expected_key)
            # Should be base64 encoded in Redis
            decoded_data = base64.b64decode(cached_data.encode("utf-8"))
            assert decoded_data == export_data

        @pytest.mark.asyncio
        async def test_get_export_data(self, cache_service):
            """Test getting export data."""
            conversion_id = "conv-123"
            export_data = b"mcaddon_data_here"

            # First set the data
            await cache_service.set_export_data(conversion_id, export_data)

            # Then retrieve it
            retrieved = await cache_service.get_export_data(conversion_id)
            assert retrieved == export_data

        @pytest.mark.asyncio
        async def test_delete_export_data(self, cache_service):
            """Test deleting export data."""
            conversion_id = "conv-123"
            export_data = b"mcaddon_data_here"

            # First set the data
            await cache_service.set_export_data(conversion_id, export_data)

            # Then delete it
            await cache_service.delete_export_data(conversion_id)

            # Verify it's gone
            retrieved = await cache_service.get_export_data(conversion_id)
            assert retrieved is None

        @pytest.mark.asyncio
        async def test_export_data_disabled(self, disabled_cache_service):
            """Test export data operations when Redis is disabled."""
            conversion_id = "conv-123"
            export_data = b"mcaddon_data_here"

            # These should not raise errors, just return early
            await disabled_cache_service.set_export_data(conversion_id, export_data)
            result = await disabled_cache_service.get_export_data(conversion_id)
            assert result is None
            await disabled_cache_service.delete_export_data(conversion_id)

    class TestUtilityMethods:
        """Test cases for utility methods."""

        @pytest.mark.asyncio
        async def test_get_cache_stats(self, cache_service):
            """Test getting cache statistics."""
            # Set up some test data
            cache_service._cache_hits = 10
            cache_service._cache_misses = 5

            stats = await cache_service.get_cache_stats()

            assert isinstance(stats, CacheStats)
            assert stats.hits == 10
            assert stats.misses == 5

        @pytest.mark.asyncio
        async def test_get_cache_stats_with_exception(self, cache_service):
            """Test getting cache statistics when Redis throws an exception."""
            # Make Redis client throw an exception
            cache_service._client.keys = AsyncMock(side_effect=Exception("Redis error"))

            # Reset hit/miss counters
            cache_service._cache_hits = 10
            cache_service._cache_misses = 5

            stats = await cache_service.get_cache_stats()

            assert isinstance(stats, CacheStats)
            assert stats.hits == 10
            assert stats.misses == 5
            assert stats.current_items == 0
            assert stats.total_size_bytes == 0

        @pytest.mark.asyncio
        async def test_invalidate_cache(self, cache_service):
            """Test invalidating cache."""
            cache_key = "test:key"

            # First set a value
            await cache_service._client.set(cache_key, "test_value")

            # Verify it exists
            value = await cache_service._client.get(cache_key)
            assert value == "test_value"

            # Invalidate it
            await cache_service.invalidate_cache(cache_key)

            # Verify it's gone
            value = await cache_service._client.get(cache_key)
            assert value is None

    class TestJsonSerialization:
        """Test cases for JSON serialization utilities."""

        def test_make_json_serializable_with_datetime(self, cache_service):
            """Test JSON serialization with datetime objects."""
            obj = {
                "string": "test",
                "number": 42,
                "datetime": datetime(2023, 1, 1, 12, 0, 0),
                "nested": {"datetime": datetime(2023, 6, 15, 8, 30, 0)},
                "list": [datetime(2023, 12, 25, 0, 0, 0), "string"],
            }

            result = cache_service._make_json_serializable(obj)

            assert result["string"] == "test"
            assert result["number"] == 42
            assert result["datetime"] == "2023-01-01T12:00:00"
            assert result["nested"]["datetime"] == "2023-06-15T08:30:00"
            assert result["list"][0] == "2023-12-25T00:00:00"
            assert result["list"][1] == "string"

        def test_make_json_serializable_with_none(self, cache_service):
            """Test JSON serialization with None values."""
            obj = {"none_value": None, "nested": {"none_value": None}}

            result = cache_service._make_json_serializable(obj)

            assert result["none_value"] is None
            assert result["nested"]["none_value"] is None

        def test_make_json_serializable_with_list(self, cache_service):
            """Test JSON serialization with lists."""
            obj = {
                "simple_list": [1, 2, 3],
                "complex_list": [
                    {"key": "value"},
                    datetime(2023, 1, 1, 12, 0, 0),
                    None,
                ],
            }

            result = cache_service._make_json_serializable(obj)

            assert result["simple_list"] == [1, 2, 3]
            assert result["complex_list"][0] == {"key": "value"}
            assert result["complex_list"][1] == "2023-01-01T12:00:00"
            assert result["complex_list"][2] is None
