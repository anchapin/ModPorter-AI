"""
Fixed tests for CacheService with proper Redis mocking
This file addresses the Redis dependency issues with comprehensive mocking
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import json
import os
import sys

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from src.services.cache import CacheService


class TestCacheServiceFixed:
    """Test cases for CacheService with proper Redis mocking"""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a comprehensive mock Redis client."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.set = AsyncMock(return_value=True)
        redis.delete = AsyncMock(return_value=1)
        redis.exists = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=True)
        redis.keys = AsyncMock(return_value=[])
        redis.sadd = AsyncMock(return_value=1)
        redis.srem = AsyncMock(return_value=1)
        redis.smembers = AsyncMock(return_value=set())
        redis.incr = AsyncMock(return_value=1)
        redis.incrby = AsyncMock(return_value=1)
        redis.flushdb = AsyncMock(return_value=True)
        redis.ping = AsyncMock(return_value=True)
        return redis

    @pytest.fixture
    def service_with_redis(self, mock_redis_client):
        """Create a CacheService instance with fully mocked Redis."""
        # Mock the environment and Redis connection
        with patch.dict(os.environ, {"DISABLE_REDIS": "false"}):
            with patch(
                "src.services.cache.aioredis.from_url", return_value=mock_redis_client
            ):
                with patch("src.services.cache.settings") as mock_settings:
                    mock_settings.redis_url = "redis://localhost:6379"
                    service = CacheService()
                    # Force Redis to be available
                    service._client = mock_redis_client
                    service._redis_available = True
                    service._redis_disabled = False
                    return service

    @pytest.fixture
    def service_without_redis(self):
        """Create a CacheService instance with Redis disabled."""
        with patch.dict(os.environ, {"DISABLE_REDIS": "true"}):
            service = CacheService()
            service._redis_available = False
            service._redis_disabled = True
            return service

    @pytest.fixture
    def sample_job_status(self):
        """Sample job status for testing."""
        return {
            "job_id": "job_123",
            "status": "processing",
            "progress": 45,
            "current_step": "converting_entities",
            "estimated_completion": (
                datetime.utcnow() + timedelta(minutes=30)
            ).isoformat(),
            "created_at": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
            "started_at": (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
        }

    @pytest.fixture
    def sample_mod_analysis(self):
        """Sample mod analysis for testing."""
        return {
            "mod_name": "ExampleMod",
            "mod_version": "1.0.0",
            "minecraft_version": "1.18.2",
            "features": ["custom_blocks", "custom_items", "custom_entities"],
            "estimated_complexity": "medium",
            "analysis_time": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
        }

    def test_cache_service_init_with_redis(self):
        """Test CacheService initialization with Redis available."""
        mock_redis = AsyncMock()
        with patch("src.services.cache.aioredis.from_url", return_value=mock_redis):
            with patch.dict(os.environ, {}, clear=True):
                service = CacheService()
                assert not service._redis_disabled
                service._client = mock_redis
                service._redis_available = True

    def test_cache_service_init_without_redis(self):
        """Test CacheService initialization with Redis disabled."""
        with patch.dict(os.environ, {"DISABLE_REDIS": "true"}):
            service = CacheService()
            assert service._redis_disabled
            assert service._redis_available is False
            assert service._client is None

    def test_make_json_serializable(self):
        """Test JSON serialization of datetime objects."""
        service = CacheService()

        # Test with datetime
        test_datetime = datetime(2023, 1, 1, 12, 0, 0)
        result = service._make_json_serializable(test_datetime)
        assert result == "2023-01-01T12:00:00"

        # Test with nested dict containing datetime
        test_dict = {
            "name": "test",
            "created_at": test_datetime,
            "nested": {"updated_at": test_datetime, "simple": "value"},
        }
        result = service._make_json_serializable(test_dict)
        assert result["created_at"] == "2023-01-01T12:00:00"
        assert result["nested"]["updated_at"] == "2023-01-01T12:00:00"
        assert result["nested"]["simple"] == "value"

    @pytest.mark.asyncio
    async def test_set_job_status_with_redis(
        self, service_with_redis, mock_redis_client, sample_job_status
    ):
        """Test setting job status with Redis available."""
        job_id = "job_123"

        await service_with_redis.set_job_status(job_id, sample_job_status)

        # Verify Redis was called
        mock_redis_client.set.assert_called_once_with(
            f"conversion_jobs:{job_id}:status", json.dumps(sample_job_status)
        )

    @pytest.mark.asyncio
    async def test_set_job_status_without_redis(
        self, service_without_redis, sample_job_status
    ):
        """Test setting job status with Redis disabled."""
        job_id = "job_123"

        # Should not raise any exceptions
        await service_without_redis.set_job_status(job_id, sample_job_status)

    @pytest.mark.asyncio
    async def test_get_job_status_with_redis(
        self, service_with_redis, mock_redis_client, sample_job_status
    ):
        """Test getting job status with Redis available."""
        job_id = "job_123"
        mock_redis_client.get.return_value = json.dumps(sample_job_status)

        result = await service_with_redis.get_job_status(job_id)

        assert result == sample_job_status
        mock_redis_client.get.assert_called_once_with(
            f"conversion_jobs:{job_id}:status"
        )

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(
        self, service_with_redis, mock_redis_client
    ):
        """Test getting non-existent job status."""
        job_id = "nonexistent_job"
        mock_redis_client.get.return_value = None

        result = await service_with_redis.get_job_status(job_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_set_progress_with_redis(self, service_with_redis, mock_redis_client):
        """Test setting progress with Redis available."""
        job_id = "job_123"
        progress = 75

        await service_with_redis.set_progress(job_id, progress)

        # Should call both set and sadd
        mock_redis_client.set.assert_called_once_with(
            f"conversion_jobs:{job_id}:progress", progress
        )
        mock_redis_client.sadd.assert_called_once_with("conversion_jobs:active", job_id)

    @pytest.mark.asyncio
    async def test_track_progress_with_redis(
        self, service_with_redis, mock_redis_client
    ):
        """Test tracking progress with Redis available."""
        job_id = "job_123"
        progress = 50

        await service_with_redis.track_progress(job_id, progress)

        # Should only call set (not sadd like set_progress)
        mock_redis_client.set.assert_called_once_with(
            f"conversion_jobs:{job_id}:progress", progress
        )
        mock_redis_client.sadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_mod_analysis_with_redis(
        self, service_with_redis, mock_redis_client, sample_mod_analysis
    ):
        """Test caching mod analysis with Redis available."""
        mod_hash = "hash123"

        await service_with_redis.cache_mod_analysis(mod_hash, sample_mod_analysis)

        expected_key = f"{service_with_redis.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"
        mock_redis_client.set.assert_called_once_with(
            expected_key, json.dumps(sample_mod_analysis), ex=3600
        )

    @pytest.mark.asyncio
    async def test_get_cached_mod_analysis_with_redis(
        self, service_with_redis, mock_redis_client, sample_mod_analysis
    ):
        """Test getting cached mod analysis with Redis available."""
        mod_hash = "hash123"
        mock_redis_client.get.return_value = json.dumps(sample_mod_analysis)

        result = await service_with_redis.get_cached_mod_analysis(mod_hash)

        assert result == sample_mod_analysis
        expected_key = f"{service_with_redis.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"
        mock_redis_client.get.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_cache_conversion_result_with_redis(
        self, service_with_redis, mock_redis_client
    ):
        """Test caching conversion result with Redis available."""
        conversion_hash = "conv123"
        result_data = {"success": True, "files": ["file1.json"]}

        await service_with_redis.cache_conversion_result(conversion_hash, result_data)

        expected_key = (
            f"{service_with_redis.CACHE_CONVERSION_RESULT_PREFIX}{conversion_hash}"
        )
        mock_redis_client.set.assert_called_once_with(
            expected_key, json.dumps(result_data), ex=7200
        )

    @pytest.mark.asyncio
    async def test_get_cached_conversion_result_with_redis(
        self, service_with_redis, mock_redis_client
    ):
        """Test getting cached conversion result with Redis available."""
        conversion_hash = "conv123"
        result_data = {"success": True, "files": ["file1.json"]}
        mock_redis_client.get.return_value = json.dumps(result_data)

        result = await service_with_redis.get_cached_conversion_result(conversion_hash)

        assert result == result_data
        expected_key = (
            f"{service_with_redis.CACHE_CONVERSION_RESULT_PREFIX}{conversion_hash}"
        )
        mock_redis_client.get.assert_called_once_with(expected_key)

    @pytest.mark.asyncio
    async def test_get_active_jobs_with_redis(
        self, service_with_redis, mock_redis_client
    ):
        """Test getting active jobs with Redis available."""
        active_jobs = ["job1", "job2", "job3"]
        mock_redis_client.smembers.return_value = active_jobs

        result = await service_with_redis.get_active_jobs()

        assert result == active_jobs
        mock_redis_client.smembers.assert_called_once_with("conversion_jobs:active")

    @pytest.mark.asyncio
    async def test_remove_from_active_jobs_with_redis(
        self, service_with_redis, mock_redis_client
    ):
        """Test removing job from active jobs with Redis available."""
        job_id = "job123"

        await service_with_redis.remove_from_active_jobs(job_id)

        mock_redis_client.srem.assert_called_once_with("conversion_jobs:active", job_id)

    @pytest.mark.asyncio
    async def test_cache_statistics_with_redis(
        self, service_with_redis, mock_redis_client
    ):
        """Test cache statistics operations with Redis available."""
        # Test increment hits
        await service_with_redis.increment_cache_hits()
        mock_redis_client.incr.assert_called_with("cache:stats:hits")

        # Test increment misses
        await service_with_redis.increment_cache_misses()
        mock_redis_client.incr.assert_called_with("cache:stats:misses")

    @pytest.mark.asyncio
    async def test_get_cache_stats_with_redis(
        self, service_with_redis, mock_redis_client
    ):
        """Test getting cache statistics with Redis available."""
        mock_redis_client.incr.return_value = 1
        mock_redis_client.get.return_value = "5"

        # Set some initial values
        await service_with_redis.increment_cache_hits()
        await service_with_redis.increment_cache_hits()
        await service_with_redis.increment_cache_misses()

        # Reset mock to test the get_cache_stats method
        mock_redis_client.reset_mock()
        mock_redis_client.get.side_effect = lambda key: {
            "cache:stats:hits": "2",
            "cache:stats:misses": "1",
        }.get(key, "0")

        stats = await service_with_redis.get_cache_stats()

        assert "hits" in stats
        assert "misses" in stats

    @pytest.mark.asyncio
    async def test_clear_cache_by_pattern_with_redis(
        self, service_with_redis, mock_redis_client
    ):
        """Test clearing cache by pattern with Redis available."""
        pattern = "cache:mod_analysis:*"
        matching_keys = ["cache:mod_analysis:key1", "cache:mod_analysis:key2"]
        mock_redis_client.keys.return_value = matching_keys

        result = await service_with_redis.clear_cache_by_pattern(pattern)

        assert result == len(matching_keys)
        mock_redis_client.keys.assert_called_once_with(pattern)
        mock_redis_client.delete.assert_called_once_with(*matching_keys)

    @pytest.mark.asyncio
    async def test_redis_exception_handling(
        self, service_with_redis, mock_redis_client
    ):
        """Test that Redis exceptions are handled gracefully."""
        # Make Redis operations fail
        mock_redis_client.set.side_effect = Exception("Redis connection failed")

        # Should not raise exception
        await service_with_redis.set_job_status("job123", {"status": "test"})

        # Redis should be marked as unavailable
        assert service_with_redis._redis_available is False

    @pytest.mark.asyncio
    async def test_edge_cases_and_boundary_conditions(
        self, service_with_redis, mock_redis_client
    ):
        """Test edge cases and boundary conditions."""
        # Test with None values
        await service_with_redis.set_job_status(None, {})
        await service_with_redis.get_job_status(None)

        # Test with empty strings
        await service_with_redis.set_job_status("", {})
        await service_with_redis.get_job_status("")

        # Test with very long strings
        long_job_id = "x" * 1000
        await service_with_redis.set_job_status(long_job_id, {"status": "test"})

        # Verify no exceptions were raised
        True  # If we get here, no exceptions were raised
