"""
Test for cache service with proper imports and actual testing.
This test verifies that the cache service can be imported and basic functionality works.
"""

import pytest
from unittest.mock import AsyncMock, patch
import sys
import os

# Ensure we can import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from services.cache import CacheService


class TestCacheServiceIntegration:
    """Integration tests for CacheService with proper imports"""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.keys.return_value = []
        mock_redis.ping.return_value = True
        return mock_redis

    @pytest.fixture
    async def cache_service(self, mock_redis):
        """Create a CacheService instance with mocked Redis"""
        with patch("services.cache.aioredis", mock_redis):
            service = CacheService()
            yield service

    @pytest.mark.asyncio
    async def test_cache_service_import(self):
        """Test that CacheService can be imported successfully"""
        # This test verifies that the import works without errors
        assert CacheService is not None
        assert callable(CacheService)

    @pytest.mark.asyncio
    async def test_cache_service_initialization(self, mock_redis):
        """Test that CacheService can be initialized with mocked Redis"""
        with patch("services.cache.aioredis", mock_redis):
            service = CacheService()
            assert service is not None
            assert hasattr(service, "_client")

    @pytest.mark.asyncio
    async def test_set_job_status_basic(self, cache_service, mock_redis):
        """Test basic job status setting"""
        job_id = "test_job_123"
        status = "processing"

        result = await cache_service.set_job_status(job_id, status)

        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_status_basic(self, cache_service, mock_redis):
        """Test basic job status retrieval"""
        job_id = "test_job_123"
        expected_status = "processing"

        # Mock Redis to return a status
        mock_redis.get.return_value = f'"{expected_status}"'  # JSON string

        result = await cache_service.get_job_status(job_id)

        assert result == expected_status
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, cache_service, mock_redis):
        """Test that cache miss returns None"""
        job_id = "nonexistent_job"

        # Mock Redis to return None (cache miss)
        mock_redis.get.return_value = None

        result = await cache_service.get_job_status(job_id)

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_cache_functionality(self, cache_service, mock_redis):
        """Test cache invalidation"""
        pattern = "job:test_job_*"

        # Mock Redis to return some keys
        mock_redis.keys.return_value = [b"job:test_job_123", b"job:test_job_456"]

        result = await cache_service.invalidate_cache(pattern)

        assert result is True
        mock_redis.keys.assert_called_once_with(pattern)
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_set_operation(self, cache_service, mock_redis):
        """Test error handling when Redis fails during set"""
        job_id = "test_job_123"
        status = "processing"

        # Mock Redis to raise an exception
        mock_redis.setex.side_effect = Exception("Redis connection failed")

        result = await cache_service.set_job_status(job_id, status)

        assert result is False

    @pytest.mark.asyncio
    async def test_error_handling_in_get_operation(self, cache_service, mock_redis):
        """Test error handling when Redis fails during get"""
        job_id = "test_job_123"

        # Mock Redis to raise an exception
        mock_redis.get.side_effect = Exception("Redis connection failed")

        result = await cache_service.get_job_status(job_id)

        assert result is None
