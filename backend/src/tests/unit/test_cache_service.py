import json
import pytest
import base64
from unittest.mock import AsyncMock, patch

# Absolute import for src.services.cache
from src.services.cache import CacheService

# Absolute import for src.models.cache_models
from models.cache_models import CacheStats

# Need to import datetime here for the global test data
from datetime import datetime


# Fixture for CacheService instance
@pytest.fixture
def cache_service():
    service = CacheService()
    # Replace the actual client with a mock for all tests in this file
    service._client = AsyncMock()
    return service


# Test data
MOD_HASH = "test_mod_hash"
ANALYSIS_DATA = {
    "some_key": "some_value",
    "nested": {"num": 1},
    "date_obj": datetime.now(),
}  # Added datetime to test serialization
CONVERSION_RESULT = {
    "success": True,
    "output_path": "/path/to/output",
    "timestamp": datetime.now(),
}  # Added datetime
ASSET_HASH = "test_asset_hash"
ASSET_DATA = b"binary_asset_data_example"
DEFAULT_TTL = 3600


# Tests for mod_analysis
@pytest.mark.asyncio
async def test_cache_mod_analysis_success(cache_service: CacheService):
    # Ensure datetime is imported for test data if redefined locally
    from datetime import datetime

    global ANALYSIS_DATA
    ANALYSIS_DATA = {
        "some_key": "some_value",
        "nested": {"num": 1},
        "date_obj": datetime.now(),
    }

    await cache_service.cache_mod_analysis(
        MOD_HASH, ANALYSIS_DATA, ttl_seconds=DEFAULT_TTL
    )
    expected_key = f"{cache_service.CACHE_MOD_ANALYSIS_PREFIX}{MOD_HASH}"
    # Use the service's own serializer method for expected value
    expected_value = json.dumps(cache_service._make_json_serializable(ANALYSIS_DATA))
    cache_service._client.set.assert_called_once_with(
        expected_key, expected_value, ex=DEFAULT_TTL
    )


@pytest.mark.asyncio
async def test_get_mod_analysis_hit(cache_service: CacheService):
    # Ensure datetime is imported for test data if redefined locally
    from datetime import datetime

    global ANALYSIS_DATA
    ANALYSIS_DATA = {
        "some_key": "some_value",
        "nested": {"num": 1},
        "date_obj": datetime.now(),
    }

    expected_key = f"{cache_service.CACHE_MOD_ANALYSIS_PREFIX}{MOD_HASH}"
    # Use the service's own serializer method for stored value consistency
    stored_value = json.dumps(cache_service._make_json_serializable(ANALYSIS_DATA))
    cache_service._client.get.return_value = stored_value

    result = await cache_service.get_mod_analysis(MOD_HASH)

    cache_service._client.get.assert_called_once_with(expected_key)
    # Compare after serializing expected if it contains datetime or other special types
    assert result == cache_service._make_json_serializable(ANALYSIS_DATA)
    # Verify cache hit counter is incremented
    assert cache_service._cache_hits == 1
    assert cache_service._cache_misses == 0


@pytest.mark.asyncio
async def test_get_mod_analysis_miss(cache_service: CacheService):
    expected_key = f"{cache_service.CACHE_MOD_ANALYSIS_PREFIX}{MOD_HASH}"
    cache_service._client.get.return_value = None

    result = await cache_service.get_mod_analysis(MOD_HASH)

    cache_service._client.get.assert_called_once_with(expected_key)
    assert result is None
    # Verify cache miss counter is incremented
    assert cache_service._cache_hits == 0
    assert cache_service._cache_misses == 1


# Tests for conversion_result
@pytest.mark.asyncio
async def test_cache_conversion_result_success(cache_service: CacheService):
    # Ensure datetime is imported for test data if redefined locally
    from datetime import datetime

    global CONVERSION_RESULT
    CONVERSION_RESULT = {
        "success": True,
        "output_path": "/path/to/output",
        "timestamp": datetime.now(),
    }

    await cache_service.cache_conversion_result(
        MOD_HASH, CONVERSION_RESULT, ttl_seconds=DEFAULT_TTL
    )
    expected_key = f"{cache_service.CACHE_CONVERSION_RESULT_PREFIX}{MOD_HASH}"
    expected_value = json.dumps(
        cache_service._make_json_serializable(CONVERSION_RESULT)
    )
    cache_service._client.set.assert_called_once_with(
        expected_key, expected_value, ex=DEFAULT_TTL
    )


@pytest.mark.asyncio
async def test_get_conversion_result_hit(cache_service: CacheService):
    # Ensure datetime is imported for test data if redefined locally
    from datetime import datetime

    global CONVERSION_RESULT
    CONVERSION_RESULT = {
        "success": True,
        "output_path": "/path/to/output",
        "timestamp": datetime.now(),
    }

    expected_key = f"{cache_service.CACHE_CONVERSION_RESULT_PREFIX}{MOD_HASH}"
    stored_value = json.dumps(cache_service._make_json_serializable(CONVERSION_RESULT))
    cache_service._client.get.return_value = stored_value

    result = await cache_service.get_conversion_result(MOD_HASH)

    cache_service._client.get.assert_called_once_with(expected_key)
    assert result == cache_service._make_json_serializable(CONVERSION_RESULT)


@pytest.mark.asyncio
async def test_get_conversion_result_miss(cache_service: CacheService):
    expected_key = f"{cache_service.CACHE_CONVERSION_RESULT_PREFIX}{MOD_HASH}"
    cache_service._client.get.return_value = None

    result = await cache_service.get_conversion_result(MOD_HASH)

    cache_service._client.get.assert_called_once_with(expected_key)
    assert result is None


# Tests for asset_conversion
@pytest.mark.asyncio
async def test_cache_asset_conversion_success(cache_service: CacheService):
    await cache_service.cache_asset_conversion(
        ASSET_HASH, ASSET_DATA, ttl_seconds=DEFAULT_TTL
    )
    expected_key = f"{cache_service.CACHE_ASSET_CONVERSION_PREFIX}{ASSET_HASH}"
    encoded_asset = base64.b64encode(ASSET_DATA).decode("utf-8")
    cache_service._client.set.assert_called_once_with(
        expected_key, encoded_asset, ex=DEFAULT_TTL
    )


@pytest.mark.asyncio
async def test_get_asset_conversion_hit(cache_service: CacheService):
    expected_key = f"{cache_service.CACHE_ASSET_CONVERSION_PREFIX}{ASSET_HASH}"
    encoded_asset = base64.b64encode(ASSET_DATA).decode("utf-8")
    cache_service._client.get.return_value = encoded_asset

    result = await cache_service.get_asset_conversion(ASSET_HASH)

    cache_service._client.get.assert_called_once_with(expected_key)
    assert result == ASSET_DATA


@pytest.mark.asyncio
async def test_get_asset_conversion_miss(cache_service: CacheService):
    expected_key = f"{cache_service.CACHE_ASSET_CONVERSION_PREFIX}{ASSET_HASH}"
    cache_service._client.get.return_value = None

    result = await cache_service.get_asset_conversion(ASSET_HASH)

    cache_service._client.get.assert_called_once_with(expected_key)
    assert result is None


# Test for invalidate_cache
@pytest.mark.asyncio
async def test_invalidate_cache_success(cache_service: CacheService):
    cache_key_to_invalidate = (
        f"{cache_service.CACHE_MOD_ANALYSIS_PREFIX}some_specific_hash"
    )
    await cache_service.invalidate_cache(cache_key_to_invalidate)
    cache_service._client.delete.assert_called_once_with(cache_key_to_invalidate)


# Test for get_cache_stats
@pytest.mark.asyncio
async def test_get_cache_stats_basic(cache_service: CacheService):
    cache_service._client.keys.side_effect = [
        [b"cache:mod_analysis:1", b"cache:mod_analysis:2"],
        [b"cache:conversion_result:3"],
        [],
    ]
    cache_service._client.info.return_value = {"used_memory": 1024000}

    # Set some cache hit/miss counters
    cache_service._cache_hits = 15
    cache_service._cache_misses = 5

    stats = await cache_service.get_cache_stats()

    assert isinstance(stats, CacheStats)
    assert stats.current_items == 3
    assert stats.total_size_bytes == 1024000
    assert stats.hits == 15
    assert stats.misses == 5

    assert cache_service._client.keys.call_count == 3
    cache_service._client.keys.assert_any_call(
        f"{cache_service.CACHE_MOD_ANALYSIS_PREFIX}*"
    )
    cache_service._client.keys.assert_any_call(
        f"{cache_service.CACHE_CONVERSION_RESULT_PREFIX}*"
    )
    cache_service._client.keys.assert_any_call(
        f"{cache_service.CACHE_ASSET_CONVERSION_PREFIX}*"
    )

    cache_service._client.info.assert_called_once_with("memory")


@pytest.mark.asyncio
async def test_get_cache_stats_redis_error(cache_service: CacheService):
    cache_service._client.keys.side_effect = Exception("Redis down")

    # Use absolute path for logger patch
    with patch("src.services.cache.logger") as mock_logger:
        stats = await cache_service.get_cache_stats()

        assert isinstance(stats, CacheStats)
        assert stats.current_items == 0
        assert stats.total_size_bytes == 0
        mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_cache_mod_analysis_redis_error(cache_service: CacheService):
    # Ensure datetime is imported for test data if redefined locally
    from datetime import datetime

    global ANALYSIS_DATA
    ANALYSIS_DATA = {
        "some_key": "some_value",
        "nested": {"num": 1},
        "date_obj": datetime.now(),
    }

    # Skip test if Redis is disabled for tests
    if cache_service._redis_disabled:
        pytest.skip("Redis is disabled for tests")

    cache_service._client.set.side_effect = Exception("Redis down")
    # Use absolute path for logger patch
    with patch("src.services.cache.logger") as mock_logger:
        await cache_service.cache_mod_analysis(MOD_HASH, ANALYSIS_DATA)
        mock_logger.warning.assert_called_once()
        assert cache_service._redis_available is False  # Should be False after error


@pytest.mark.asyncio
async def test_get_mod_analysis_redis_error(cache_service: CacheService):
    # Skip test if Redis is disabled for tests
    if cache_service._redis_disabled:
        pytest.skip("Redis is disabled for tests")

    cache_service._client.get.side_effect = Exception("Redis down")
    # Use absolute path for logger patch
    with patch("src.services.cache.logger") as mock_logger:
        result = await cache_service.get_mod_analysis(MOD_HASH)
        assert result is None
        mock_logger.warning.assert_called_once()
        assert cache_service._redis_available is False  # Should be False after error


# Tests for set_progress method
@pytest.mark.asyncio
async def test_set_progress_success(cache_service: CacheService):
    # Skip test if Redis is disabled for tests
    if cache_service._redis_disabled:
        pytest.skip("Redis is disabled for tests")

    job_id = "test_job_123"
    progress = 75

    await cache_service.set_progress(job_id, progress)

    expected_key = f"conversion_jobs:{job_id}:progress"
    cache_service._client.set.assert_called_once_with(expected_key, progress)
    cache_service._client.sadd.assert_called_once_with("conversion_jobs:active", job_id)


@pytest.mark.asyncio
async def test_set_progress_redis_error(cache_service: CacheService):
    # Skip test if Redis is disabled for tests
    if cache_service._redis_disabled:
        pytest.skip("Redis is disabled for tests")

    job_id = "test_job_123"
    progress = 75

    cache_service._client.set.side_effect = Exception("Redis connection failed")

    with patch("src.services.cache.logger") as mock_logger:
        await cache_service.set_progress(job_id, progress)

        mock_logger.warning.assert_called_once()
        assert cache_service._redis_available is False


# Redundant import of datetime at the end is removed as it's already at the top.
# from datetime import datetime
