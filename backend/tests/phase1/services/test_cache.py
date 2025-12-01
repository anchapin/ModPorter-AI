"""
Comprehensive tests for CacheService.

This module tests the core functionality of the CacheService,
including caching operations, invalidation, statistics, and Redis interactions.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import json
import os

from src.services.cache import CacheService


class TestCacheService:
    """Test cases for CacheService class."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client for testing."""
        redis = AsyncMock()
        redis.get = AsyncMock()
        redis.set = AsyncMock()
        redis.delete = AsyncMock()
        redis.exists = AsyncMock()
        redis.expire = AsyncMock()
        redis.keys = AsyncMock(return_value=[])
        redis.sadd = AsyncMock()
        redis.srem = AsyncMock()
        redis.smembers = AsyncMock(return_value=set())
        redis.incr = AsyncMock(return_value=1)
        redis.incrby = AsyncMock(return_value=1)
        return redis

    @pytest.fixture
    def service(self, mock_redis_client):
        """Create a CacheService instance with mocked Redis for testing."""
        with patch(
            "src.services.cache.aioredis.from_url", return_value=mock_redis_client
        ):
            service = CacheService()
            service._client = mock_redis_client
            service._redis_available = True
            return service

    @pytest.fixture
    def service_no_redis(self):
        """Create a CacheService instance with Redis disabled for testing."""
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
            "estimated_completion": datetime.utcnow() + timedelta(minutes=30),
            "created_at": datetime.utcnow() - timedelta(minutes=15),
            "started_at": datetime.utcnow() - timedelta(minutes=10),
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
            "analysis_time": datetime.utcnow() - timedelta(minutes=5),
        }

    @pytest.fixture
    def sample_conversion_result(self):
        """Sample conversion result for testing."""
        return {
            "success": True,
            "bedrock_files": [
                "blocks/blocks.json",
                "items/items.json",
                "entities/entities.json",
            ],
            "conversion_time": 120,
            "issues": [],
            "generated_at": datetime.utcnow() - timedelta(minutes=2),
        }

    def test_init(self):
        """Test CacheService initialization."""
        # Test with Redis enabled
        with patch("src.services.cache.aioredis.from_url") as mock_redis:
            mock_redis.return_value = AsyncMock()
            with patch.dict(os.environ, {"DISABLE_REDIS": "false"}):
                service = CacheService()
                assert service._redis_disabled is False
                assert service._cache_hits == 0
                assert service._cache_misses == 0

        # Test with Redis disabled
        with patch.dict(os.environ, {"DISABLE_REDIS": "true"}):
            service = CacheService()
            assert service._redis_disabled is True
            assert service._redis_available is False
            assert service._client is None

    def test_make_json_serializable(self):
        """Test JSON serialization for cache values."""
        service = CacheService()

        # Test with basic types
        basic_obj = {"string": "test", "number": 42, "boolean": True, "none": None}
        serialized = service._make_json_serializable(basic_obj)
        assert serialized == basic_obj

        # Test with datetime
        datetime_obj = datetime(2023, 1, 1, 12, 0, 0)
        obj_with_datetime = {
            "datetime_field": datetime_obj,
            "nested": {"another_datetime": datetime_obj},
        }
        serialized = service._make_json_serializable(obj_with_datetime)
        assert serialized["datetime_field"] == datetime_obj.isoformat()
        assert serialized["nested"]["another_datetime"] == datetime_obj.isoformat()

        # Test with list
        list_obj = ["string", 42, datetime_obj, {"nested_datetime": datetime_obj}]
        serialized = service._make_json_serializable(list_obj)
        assert serialized[2] == datetime_obj.isoformat()
        assert serialized[3]["nested_datetime"] == datetime_obj.isoformat()

    @pytest.mark.asyncio
    async def test_set_job_status(self, service, mock_redis_client, sample_job_status):
        """Test setting job status in cache."""
        job_id = "job_123"

        # Call the method
        await service.set_job_status(job_id, sample_job_status)

        # Verify Redis was called with correct parameters
        mock_redis_client.set.assert_called_once()
        args, kwargs = mock_redis_client.set.call_args

        # Check the key
        assert args[0] == f"conversion_jobs:{job_id}:status"

        # Check the value is a JSON string
        status_json = json.loads(args[1])
        assert status_json["job_id"] == job_id
        assert status_json["status"] == "processing"

    @pytest.mark.asyncio
    async def test_get_job_status(self, service, mock_redis_client, sample_job_status):
        """Test getting job status from cache."""
        job_id = "job_123"

        # Mock Redis to return JSON string of status
        mock_redis_client.get.return_value = json.dumps(
            service._make_json_serializable(sample_job_status)
        )

        # Call the method
        result = await service.get_job_status(job_id)

        # Verify Redis was called with correct key
        mock_redis_client.get.assert_called_once_with(
            f"conversion_jobs:{job_id}:status"
        )

        # Verify the result
        assert result is not None
        assert result["job_id"] == job_id
        assert result["status"] == "processing"
        assert result["progress"] == 45

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, service, mock_redis_client):
        """Test getting job status when not in cache."""
        job_id = "non_existent_job"

        # Mock Redis to return None
        mock_redis_client.get.return_value = None

        # Call the method
        result = await service.get_job_status(job_id)

        # Verify the result is None
        assert result is None

    @pytest.mark.asyncio
    async def test_set_progress(self, service, mock_redis_client):
        """Test setting job progress in cache."""
        job_id = "job_123"
        progress = 75

        # Call the method
        await service.set_progress(job_id, progress)

        # Verify Redis was called twice: once for progress, once for active set
        assert mock_redis_client.set.call_count == 2

        # Check progress was set
        mock_redis_client.set.assert_any_call(
            f"conversion_jobs:{job_id}:progress", progress
        )

        # Check job was added to active set
        mock_redis_client.sadd.assert_called_once_with("conversion_jobs:active", job_id)

    @pytest.mark.asyncio
    async def test_track_progress(self, service, mock_redis_client):
        """Test tracking job progress in cache."""
        job_id = "job_123"
        progress = 75

        # Call the method
        await service.track_progress(job_id, progress)

        # Verify Redis was called with correct parameters
        mock_redis_client.set.assert_called_once_with(
            f"conversion_jobs:{job_id}:progress", progress
        )

    @pytest.mark.asyncio
    async def test_cache_mod_analysis(
        self, service, mock_redis_client, sample_mod_analysis
    ):
        """Test caching mod analysis."""
        mod_hash = "mod_hash_123"
        ttl_seconds = 7200  # 2 hours

        # Call the method
        await service.cache_mod_analysis(mod_hash, sample_mod_analysis, ttl_seconds)

        # Verify Redis was called with correct parameters
        mock_redis_client.set.assert_called_once()
        args, kwargs = mock_redis_client.set.call_args

        # Check the key
        assert args[0] == f"{service.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"

        # Check TTL
        assert kwargs.get("ex") == ttl_seconds

        # Check the value is a JSON string
        analysis_json = json.loads(args[1])
        assert analysis_json["mod_name"] == "ExampleMod"
        assert analysis_json["features"] == [
            "custom_blocks",
            "custom_items",
            "custom_entities",
        ]

    @pytest.mark.asyncio
    async def test_get_cached_mod_analysis(
        self, service, mock_redis_client, sample_mod_analysis
    ):
        """Test getting cached mod analysis."""
        mod_hash = "mod_hash_123"

        # Mock Redis to return JSON string of analysis
        mock_redis_client.get.return_value = json.dumps(
            service._make_json_serializable(sample_mod_analysis)
        )

        # Call the method
        result = await service.get_cached_mod_analysis(mod_hash)

        # Verify Redis was called with correct key
        mock_redis_client.get.assert_called_once_with(
            f"{service.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"
        )

        # Verify the result
        assert result is not None
        assert result["mod_name"] == "ExampleMod"
        assert result["minecraft_version"] == "1.18.2"
        assert "custom_blocks" in result["features"]

    @pytest.mark.asyncio
    async def test_cache_conversion_result(
        self, service, mock_redis_client, sample_conversion_result
    ):
        """Test caching conversion result."""
        mod_hash = "mod_hash_456"
        ttl_seconds = 3600  # 1 hour

        # Call the method
        await service.cache_conversion_result(
            mod_hash, sample_conversion_result, ttl_seconds
        )

        # Verify Redis was called with correct parameters
        mock_redis_client.set.assert_called_once()
        args, kwargs = mock_redis_client.set.call_args

        # Check the key
        assert args[0] == f"{service.CACHE_CONVERSION_RESULT_PREFIX}{mod_hash}"

        # Check TTL
        assert kwargs.get("ex") == ttl_seconds

        # Check the value is a JSON string
        result_json = json.loads(args[1])
        assert result_json["success"] is True
        assert len(result_json["bedrock_files"]) == 3

    @pytest.mark.asyncio
    async def test_get_cached_conversion_result(
        self, service, mock_redis_client, sample_conversion_result
    ):
        """Test getting cached conversion result."""
        mod_hash = "mod_hash_456"

        # Mock Redis to return JSON string of result
        mock_redis_client.get.return_value = json.dumps(
            service._make_json_serializable(sample_conversion_result)
        )

        # Call the method
        result = await service.get_cached_conversion_result(mod_hash)

        # Verify Redis was called with correct key
        mock_redis_client.get.assert_called_once_with(
            f"{service.CACHE_CONVERSION_RESULT_PREFIX}{mod_hash}"
        )

        # Verify the result
        assert result is not None
        assert result["success"] is True
        assert result["conversion_time"] == 120

    @pytest.mark.asyncio
    async def test_cache_asset_conversion(self, service, mock_redis_client):
        """Test caching asset conversion."""
        asset_hash = "asset_hash_789"
        conversion_data = {
            "asset_path": "assets/textures/block/custom_block.png",
            "converted_path": "assets/textures/blocks/custom_block.png",
            "conversion_time": 5,
            "success": True,
        }
        ttl_seconds = 86400  # 24 hours

        # Call the method
        await service.cache_asset_conversion(asset_hash, conversion_data, ttl_seconds)

        # Verify Redis was called with correct parameters
        mock_redis_client.set.assert_called_once()
        args, kwargs = mock_redis_client.set.call_args

        # Check the key
        assert args[0] == f"{service.CACHE_ASSET_CONVERSION_PREFIX}{asset_hash}"

        # Check TTL
        assert kwargs.get("ex") == ttl_seconds

        # Check the value is a JSON string
        conversion_json = json.loads(args[1])
        assert conversion_json["asset_path"] == "assets/textures/block/custom_block.png"
        assert conversion_json["success"] is True

    @pytest.mark.asyncio
    async def test_get_cached_asset_conversion(self, service, mock_redis_client):
        """Test getting cached asset conversion."""
        asset_hash = "asset_hash_789"
        conversion_data = {
            "asset_path": "assets/textures/block/custom_block.png",
            "converted_path": "assets/textures/blocks/custom_block.png",
            "conversion_time": 5,
            "success": True,
        }

        # Mock Redis to return JSON string of conversion
        mock_redis_client.get.return_value = json.dumps(
            service._make_json_serializable(conversion_data)
        )

        # Call the method
        result = await service.get_cached_asset_conversion(asset_hash)

        # Verify Redis was called with correct key
        mock_redis_client.get.assert_called_once_with(
            f"{service.CACHE_ASSET_CONVERSION_PREFIX}{asset_hash}"
        )

        # Verify the result
        assert result is not None
        assert result["asset_path"] == "assets/textures/block/custom_block.png"
        assert result["conversion_time"] == 5

    @pytest.mark.asyncio
    async def test_invalidate_mod_cache(self, service, mock_redis_client):
        """Test invalidating mod cache."""
        mod_hash = "mod_hash_123"

        # Call the method
        await service.invalidate_mod_cache(mod_hash)

        # Verify Redis was called twice: once for analysis, once for result
        assert mock_redis_client.delete.call_count == 2

        # Check the keys
        mock_redis_client.delete.assert_any_call(
            f"{service.CACHE_MOD_ANALYSIS_PREFIX}{mod_hash}"
        )
        mock_redis_client.delete.assert_any_call(
            f"{service.CACHE_CONVERSION_RESULT_PREFIX}{mod_hash}"
        )

    @pytest.mark.asyncio
    async def test_invalidate_asset_cache(self, service, mock_redis_client):
        """Test invalidating asset cache."""
        asset_hash = "asset_hash_789"

        # Call the method
        await service.invalidate_asset_cache(asset_hash)

        # Verify Redis was called with correct key
        mock_redis_client.delete.assert_called_once_with(
            f"{service.CACHE_ASSET_CONVERSION_PREFIX}{asset_hash}"
        )

    @pytest.mark.asyncio
    async def test_get_active_jobs(self, service, mock_redis_client):
        """Test getting active jobs from cache."""
        job_ids = {"job_123", "job_456", "job_789"}

        # Mock Redis to return set of job IDs
        mock_redis_client.smembers.return_value = job_ids

        # Call the method
        result = await service.get_active_jobs()

        # Verify Redis was called with correct key
        mock_redis_client.smembers.assert_called_once_with("conversion_jobs:active")

        # Verify the result
        assert result == job_ids

    @pytest.mark.asyncio
    async def test_remove_from_active_jobs(self, service, mock_redis_client):
        """Test removing job from active jobs."""
        job_id = "job_123"

        # Call the method
        await service.remove_from_active_jobs(job_id)

        # Verify Redis was called with correct parameters
        mock_redis_client.srem.assert_called_once_with("conversion_jobs:active", job_id)

    @pytest.mark.asyncio
    async def test_increment_cache_hits(self, service, mock_redis_client):
        """Test incrementing cache hits counter."""
        # Call the method
        await service.increment_cache_hits()

        # Verify internal counter was updated
        assert service._cache_hits == 1

        # Verify Redis was called with correct key
        mock_redis_client.incr.assert_called_once_with("stats:cache_hits")

    @pytest.mark.asyncio
    async def test_increment_cache_misses(self, service, mock_redis_client):
        """Test incrementing cache misses counter."""
        # Call the method
        await service.increment_cache_misses()

        # Verify internal counter was updated
        assert service._cache_misses == 1

        # Verify Redis was called with correct key
        mock_redis_client.incr.assert_called_once_with("stats:cache_misses")

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, service, mock_redis_client):
        """Test getting cache statistics."""
        # Set internal counters
        service._cache_hits = 150
        service._cache_misses = 50

        # Mock Redis to return statistics
        mock_redis_client.get.side_effect = [
            "1000",  # total cache hits from Redis
            "500",  # total cache misses from Redis
        ]

        # Call the method
        result = await service.get_cache_stats()

        # Verify the result
        assert result is not None
        assert result["session_hits"] == 150
        assert result["session_misses"] == 50
        assert result["total_hits"] == 1000
        assert result["total_misses"] == 500
        assert result["session_hit_rate"] == 0.75  # 150 / (150 + 50)
        assert result["total_hit_rate"] == 0.67  # 1000 / (1000 + 500)

    @pytest.mark.asyncio
    async def test_reset_cache_stats(self, service, mock_redis_client):
        """Test resetting cache statistics."""
        # Set internal counters
        service._cache_hits = 100
        service._cache_misses = 25

        # Call the method
        await service.reset_cache_stats()

        # Verify internal counters were reset
        assert service._cache_hits == 0
        assert service._cache_misses == 0

        # Verify Redis was called with correct keys
        mock_redis_client.delete.assert_any_call("stats:cache_hits")
        mock_redis_client.delete.assert_any_call("stats:cache_misses")

    @pytest.mark.asyncio
    async def test_clear_cache_by_pattern(self, service, mock_redis_client):
        """Test clearing cache by pattern."""
        pattern = "cache:mod_analysis:*"

        # Mock Redis to return keys matching pattern
        matching_keys = [
            "cache:mod_analysis:hash1",
            "cache:mod_analysis:hash2",
            "cache:mod_analysis:hash3",
        ]
        mock_redis_client.keys.return_value = matching_keys

        # Call the method
        result = await service.clear_cache_by_pattern(pattern)

        # Verify Redis was called correctly
        mock_redis_client.keys.assert_called_once_with(pattern)

        # Verify all keys were deleted
        assert mock_redis_client.delete.call_count == 3
        for key in matching_keys:
            mock_redis_client.delete.assert_any_call(key)

        # Verify the result
        assert result["deleted_count"] == 3
        assert result["pattern"] == pattern

    @pytest.mark.asyncio
    async def test_redis_unavailable_handling(self, service_no_redis):
        """Test handling when Redis is unavailable."""
        # All operations should gracefully handle Redis unavailability
        await service_no_redis.set_job_status("job_123", {"status": "processing"})
        result = await service_no_redis.get_job_status("job_123")
        assert result is None

        await service_no_redis.set_progress("job_123", 50)
        await service_no_redis.cache_mod_analysis("hash", {"data": "value"})
        result = await service_no_redis.get_cached_mod_analysis("hash")
        assert result is None

        result = await service_no_redis.get_cache_stats()
        assert result["session_hits"] == 0
        assert result["session_misses"] == 0

    @pytest.mark.asyncio
    async def test_redis_exception_handling(self, service, mock_redis_client):
        """Test handling Redis exceptions."""
        # Mock Redis to raise an exception
        mock_redis_client.get.side_effect = Exception("Redis connection error")

        # Verify service handles exceptions gracefully
        result = await service.get_job_status("job_123")
        assert result is None

        # Verify Redis is marked as unavailable
        assert service._redis_available is False

    @pytest.mark.asyncio
    async def test_get_cache_size(self, service, mock_redis_client):
        """Test getting cache size."""
        # Mock Redis to return key counts for different patterns
        mock_redis_client.keys.side_effect = [
            [
                "cache:mod_analysis:hash1",
                "cache:mod_analysis:hash2",
            ],  # 2 mod analysis keys
            ["cache:conversion_result:hash3"],  # 1 conversion result key
            [
                "cache:asset_conversion:hash4",
                "cache:asset_conversion:hash5",
                "cache:asset_conversion:hash6",
            ],  # 3 asset conversion keys
        ]

        # Call the method
        result = await service.get_cache_size()

        # Verify the result
        assert result is not None
        assert result["mod_analysis_count"] == 2
        assert result["conversion_result_count"] == 1
        assert result["asset_conversion_count"] == 3
        assert result["total_count"] == 6

    @pytest.mark.asyncio
    async def test_purge_expired_entries(self, service, mock_redis_client):
        """Test purging expired cache entries."""
        # This test is more conceptual since Redis handles TTL automatically
        # In a real implementation, this might scan for entries with custom expiration logic

        # Mock Redis to return keys
        mock_redis_client.keys.return_value = [
            "cache:mod_analysis:hash1",
            "cache:conversion_result:hash2",
        ]

        # Mock Redis TTL checks
        mock_redis_client.ttl.side_effect = [
            -1,
            60,
        ]  # -1 means no expiry, 60 means 60 seconds left

        # Call the method
        result = await service.purge_expired_entries()

        # Verify the result
        assert result is not None
        assert "checked_count" in result
        assert "expired_count" in result
        assert result["checked_count"] == 2
        assert result["expired_count"] == 0  # None expired in this mock
