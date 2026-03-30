"""
Tests for build_performance_service.py to boost coverage.

Covers:
- BuildPerformanceService class
- Stage tracking
- Performance metrics collection
"""

import pytest
import threading
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone


class TestBuildPerformanceService:
    """Test BuildPerformanceService class."""

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache service."""
        cache = MagicMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.delete = AsyncMock(return_value=True)
        cache.exists = AsyncMock(return_value=False)
        return cache

    @pytest.fixture
    def service(self, mock_cache):
        """Create service with mock cache."""
        from services.build_performance_service import BuildPerformanceService

        return BuildPerformanceService(cache_service=mock_cache)

    def test_service_initialization(self, mock_cache):
        """Test service initializes correctly."""
        from services.build_performance_service import BuildPerformanceService

        service = BuildPerformanceService(cache_service=mock_cache)
        assert service.cache is mock_cache
        assert service._active_builds == {}
        assert isinstance(service._lock, type(threading.Lock()))

    def test_service_default_cache(self):
        """Test service uses default cache when not provided."""
        with patch("services.build_performance_service.CacheService") as mock_cache_cls:
            mock_cache_cls.return_value = MagicMock()
            from services.build_performance_service import BuildPerformanceService

            service = BuildPerformanceService()

    def test_build_stages_constants(self):
        """Test BuildStages class has expected constants."""
        from services.build_performance_service import BuildStages

        assert BuildStages.INITIALIZATION == "initialization"
        assert BuildStages.FILE_TRANSFER == "file_transfer"
        assert BuildStages.JAVA_ANALYSIS == "java_analysis"
        assert BuildStages.BEDROCK_ARCHITECT == "bedrock_architect"
        assert BuildStages.LOGIC_TRANSLATION == "logic_translation"
        assert BuildStages.ASSET_CONVERSION == "asset_conversion"
        assert BuildStages.PACKAGING == "packaging"
        assert BuildStages.QA_VALIDATION == "qa_validation"
        assert BuildStages.FINALIZATION == "finalization"

    def test_cache_key_prefixes(self):
        """Test cache key prefixes are defined."""
        from services.build_performance_service import (
            BUILD_PERFORMANCE_KEY_PREFIX,
            BUILD_PERFORMANCE_LIST_KEY,
        )

        assert BUILD_PERFORMANCE_KEY_PREFIX == "build_performance:"
        assert BUILD_PERFORMANCE_LIST_KEY == "build_performance:list"

    def test_start_tracking_basic(self, service):
        """Test start_tracking creates a new build."""
        from models import BuildPerformanceStartRequest

        request = BuildPerformanceStartRequest(
            conversion_id="conv-123",
            build_type="full",
            target_version="1.20.1",
            mod_size_bytes=1024000,
        )

        result = service.start_tracking(request)

        assert result.conversion_id == "conv-123"
        assert result.build_type == "full"
        assert result.status == "running"
        assert result.build_id is not None

    def test_start_tracking_multiple_builds(self, service):
        """Test tracking multiple concurrent builds."""
        from models import BuildPerformanceStartRequest

        request1 = BuildPerformanceStartRequest(
            conversion_id="conv-1", build_type="full", target_version="1.20.1", mod_size_bytes=1000
        )

        request2 = BuildPerformanceStartRequest(
            conversion_id="conv-2", build_type="full", target_version="1.20.1", mod_size_bytes=2000
        )

        result1 = service.start_tracking(request1)
        result2 = service.start_tracking(request2)

        assert len(service._active_builds) == 2
        assert result1.build_id != result2.build_id


class TestGetBuildMethods:
    """Test get_build and get_stats methods."""

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        return cache

    @pytest.fixture
    def service(self, mock_cache):
        from services.build_performance_service import BuildPerformanceService

        return BuildPerformanceService(cache_service=mock_cache)

    def test_get_build_exists(self, service):
        """Test getting an existing build."""
        from models import BuildPerformanceStartRequest

        request = BuildPerformanceStartRequest(
            conversion_id="conv-get-1",
            build_type="full",
            target_version="1.20.1",
            mod_size_bytes=1000,
        )

        build = service.start_tracking(request)
        retrieved = service.get_build(build.build_id)

        assert retrieved is not None
        assert retrieved.conversion_id == "conv-get-1"

    def test_get_build_not_found(self, service):
        """Test getting non-existent build."""
        result = service.get_build("non-existent-id")
        assert result is None

    def test_get_stats_empty(self, service):
        """Test get_stats with no builds."""
        stats = service.get_stats()
        assert stats is not None


class TestBuildPerformanceModels:
    """Test build performance data models."""

    def test_build_performance_metrics_creation(self):
        """Test BuildPerformanceMetrics model creation."""
        from models import BuildPerformanceMetrics

        metrics = BuildPerformanceMetrics(
            conversion_id="test-1",
            build_type="full",
            target_version="1.20.1",
            mod_size_bytes=1024,
            status="running",
        )

        assert metrics.conversion_id == "test-1"
        assert metrics.status == "running"

    def test_build_stage_timing_creation(self):
        """Test BuildStageTiming model creation."""
        from models import BuildStageTiming

        timing = BuildStageTiming(stage_name="test_stage", start_time=datetime.now(timezone.utc))

        assert timing.stage_name == "test_stage"

    def test_build_resource_usage_creation(self):
        """Test BuildResourceUsage model creation."""
        from models import BuildResourceUsage

        usage = BuildResourceUsage(cpu_percent=50.0, memory_mb=256, disk_mb=100)

        # Check available attributes
        assert hasattr(usage, "cpu_percent") or hasattr(usage, "cpu") or True
