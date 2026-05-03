"""
Unit tests for cache service.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import os

# Set DISABLE_REDIS to avoid actual Redis connection
os.environ["DISABLE_REDIS"] = "true"

from services.cache import CacheService


class TestCacheServiceInit:
    def test_cache_service_init(self):
        """Test CacheService can be initialized."""
        service = CacheService()
        assert service is not None


class TestCacheServiceMethods:
    def test_service_has_required_methods(self):
        """Test CacheService has all required methods."""
        service = CacheService()
        methods = [
            "set_job_status",
            "get_job_status",
            "cache_mod_analysis",
            "get_mod_analysis",
            "cache_conversion_result",
            "get_conversion_result",
            "invalidate_cache",
            "get_cache_stats",
            "clear_all_caches",
            "get_cache_hit_rate",
        ]
        for method in methods:
            assert hasattr(service, method), f"Missing method: {method}"


class TestCacheServiceConstants:
    def test_cache_prefixes_defined(self):
        """Test cache prefixes are defined."""
        assert hasattr(CacheService, "CACHE_MOD_ANALYSIS_PREFIX")
        assert hasattr(CacheService, "CACHE_CONVERSION_RESULT_PREFIX")
        assert hasattr(CacheService, "CACHE_ASSET_CONVERSION_PREFIX")

    def test_ttl_defaults_defined(self):
        """Test TTL defaults are defined."""
        assert hasattr(CacheService, "DEFAULT_TTL_MOD_ANALYSIS")
        assert hasattr(CacheService, "DEFAULT_TTL_CONVERSION_RESULT")
        assert hasattr(CacheService, "DEFAULT_TTL_JOB_STATUS")
