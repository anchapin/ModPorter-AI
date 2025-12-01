"""
Simple tests for CacheService that work with existing Redis mocking
This file provides basic cache service tests without complex mocking
"""

import pytest
from unittest.mock import patch
from datetime import datetime
import os
import sys
import asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))


class TestCacheServiceSimple:
    """Simple test cases for CacheService using existing mocking"""

    @pytest.mark.asyncio
    async def test_cache_service_import(self):
        """Test that CacheService can be imported with existing mocks."""
        # This test ensures the mocking infrastructure in conftest.py works
        from src.services.cache import CacheService

        # Should be able to create an instance without errors
        service = CacheService()
        assert service is not None

    @pytest.mark.asyncio
    async def test_cache_service_without_redis(self):
        """Test CacheService behavior when Redis is disabled."""
        from src.services.cache import CacheService

        # Create service with Redis disabled
        service = CacheService()
        service._redis_available = False
        service._redis_disabled = True
        service._client = None

        # Test various operations - they should not raise exceptions
        await service.set_job_status("test_job", {"status": "processing"})
        await service.set_progress("test_job", 50)
        await service.track_progress("test_job", 60)

        result = await service.get_job_status("test_job")
        assert result is None  # Should return None when Redis is disabled

        # Cache operations should not raise exceptions
        await service.cache_mod_analysis("hash123", {"test": "data"})
        await service.cache_conversion_result("conv123", {"result": "success"})
        await service.cache_asset_conversion("asset123", b"converted_data")

        # Should not raise exceptions
        result = await service.get_mod_analysis("hash123")
        result = await service.get_conversion_result("conv123")
        result = await service.get_asset_conversion("asset123")

    def test_make_json_serializable(self):
        """Test JSON serialization of datetime objects."""
        from src.services.cache import CacheService

        service = CacheService()
        service._redis_available = False
        service._redis_disabled = True

        # Test with datetime
        test_datetime = datetime(2023, 1, 1, 12, 0, 0)
        result = service._make_json_serializable(test_datetime)
        assert result == "2023-01-01T12:00:00"

        # Test with nested dict containing datetime
        test_dict = {
            "name": "test",
            "created_at": test_datetime,
            "nested": {"updated_at": test_datetime, "simple": "value"},
            "list": [test_datetime, "simple_value"],
        }
        result = service._make_json_serializable(test_dict)
        assert result["created_at"] == "2023-01-01T12:00:00"
        assert result["nested"]["updated_at"] == "2023-01-01T12:00:00"
        assert result["nested"]["simple"] == "value"
        assert result["list"][0] == "2023-01-01T12:00:00"
        assert result["list"][1] == "simple_value"

    @pytest.mark.asyncio
    async def test_cache_statistics_operations(self):
        """Test cache statistics operations without Redis."""
        from src.services.cache import CacheService

        service = CacheService()
        service._redis_available = False
        service._redis_disabled = True
        service._client = None

        # Test the actual methods that exist
        stats = await service.get_cache_stats()
        assert stats is not None  # Should return a CacheStats object

    @pytest.mark.asyncio
    async def test_cache_invalidation_operations(self):
        """Test cache invalidation operations without Redis."""
        from src.services.cache import CacheService

        service = CacheService()
        service._redis_available = False
        service._redis_disabled = True
        service._client = None

        # Test the actual methods that exist
        await service.invalidate_cache("test_key")
        await service.invalidate_cache("mod_analysis:hash123")
        await service.invalidate_cache("conversion_result:conv123")

    @pytest.mark.asyncio
    async def test_export_data_operations(self):
        """Test export data operations without Redis."""
        from src.services.cache import CacheService

        service = CacheService()
        service._redis_available = False
        service._redis_disabled = True
        service._client = None

        # Test export data operations
        test_data = b"test export data"
        await service.set_export_data("conv_123", test_data)

        result = await service.get_export_data("conv_123")
        assert result is None  # Should return None when Redis is disabled

        await service.delete_export_data("conv_123")

    @pytest.mark.asyncio
    async def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling."""
        from src.services.cache import CacheService

        service = CacheService()
        service._redis_available = False
        service._redis_disabled = True
        service._client = None

        # Test with None and empty values
        await service.set_job_status(None, {})
        await service.set_job_status("", {})
        await service.set_job_status("valid_job", None)

        result = await service.get_job_status(None)
        assert result is None

        result = await service.get_job_status("")
        assert result is None

        # Test with very long strings
        long_job_id = "x" * 1000
        large_status = {"data": "y" * 10000}

        await service.set_job_status(long_job_id, large_status)
        result = await service.get_job_status(long_job_id)

        # Should not raise exceptions
        True  # If we get here, no exceptions were raised

    @pytest.mark.asyncio
    async def test_cache_service_initialization_scenarios(self):
        """Test different CacheService initialization scenarios."""
        from src.services.cache import CacheService

        # Test with Redis disabled via environment
        with patch.dict(os.environ, {"DISABLE_REDIS": "true"}):
            service = CacheService()
            assert service._redis_disabled is True
            assert service._redis_available is False
            assert service._client is None

        # Test with Redis enabled but connection fails (simulate by mocking aioredis)
        with patch.dict(os.environ, {"DISABLE_REDIS": "false"}):
            with patch(
                "src.services.cache.aioredis.from_url",
                side_effect=Exception("Connection failed"),
            ):
                service = CacheService()
                assert service._redis_available is False
                assert service._client is None

    def test_cache_constants(self):
        """Test that cache constants are properly defined."""
        from src.services.cache import CacheService

        service = CacheService()
        service._redis_available = False
        service._redis_disabled = True

        # Check that constants are defined
        assert hasattr(CacheService, "CACHE_MOD_ANALYSIS_PREFIX")
        assert hasattr(CacheService, "CACHE_CONVERSION_RESULT_PREFIX")
        assert hasattr(CacheService, "CACHE_ASSET_CONVERSION_PREFIX")

        # Check that they're strings
        assert isinstance(CacheService.CACHE_MOD_ANALYSIS_PREFIX, str)
        assert isinstance(CacheService.CACHE_CONVERSION_RESULT_PREFIX, str)
        assert isinstance(CacheService.CACHE_ASSET_CONVERSION_PREFIX, str)

    @pytest.mark.asyncio
    async def test_cache_ttl_operations(self):
        """Test cache operations with different TTL values."""
        from src.services.cache import CacheService

        service = CacheService()
        service._redis_available = False
        service._redis_disabled = True
        service._client = None

        # Test with custom TTL values
        await service.cache_mod_analysis("hash123", {"data": "test"}, ttl_seconds=7200)
        await service.cache_conversion_result(
            "conv123", {"result": "success"}, ttl_seconds=3600
        )
        await service.cache_asset_conversion(
            "asset123", {"asset": "data"}, ttl_seconds=1800
        )

        # Should not raise exceptions
        True  # If we get here, no exceptions were raised

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent cache operations."""
        from src.services.cache import CacheService

        service = CacheService()
        service._redis_available = False
        service._redis_disabled = True
        service._client = None

        # Create multiple concurrent operations
        async def set_status(job_id: str, status: dict):
            await service.set_job_status(job_id, status)

        async def get_status(job_id: str):
            return await service.get_job_status(job_id)

        # Run multiple operations concurrently
        tasks = []
        for i in range(10):
            tasks.append(set_status(f"job_{i}", {"status": f"processing_{i}"}))
            tasks.append(get_status(f"job_{i}"))

        # Should not raise exceptions
        await asyncio.gather(*tasks, return_exceptions=True)

    def test_service_attributes(self):
        """Test CacheService attributes and methods."""
        from src.services.cache import CacheService

        service = CacheService()
        service._redis_available = False
        service._redis_disabled = True
        service._client = None

        # Test that all expected methods exist
        expected_methods = [
            "set_job_status",
            "get_job_status",
            "set_progress",
            "track_progress",
            "cache_mod_analysis",
            "get_mod_analysis",
            "cache_conversion_result",
            "get_conversion_result",
            "cache_asset_conversion",
            "get_asset_conversion",
            "get_cache_stats",
            "invalidate_cache",
            "set_export_data",
            "get_export_data",
            "delete_export_data",
        ]

        for method_name in expected_methods:
            assert hasattr(service, method_name), f"Method {method_name} not found"
            assert callable(getattr(service, method_name)), (
                f"Method {method_name} is not callable"
            )
