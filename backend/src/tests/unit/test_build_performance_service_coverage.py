"""
Comprehensive unit tests for build_performance_service.py to boost coverage to ~100%.

Covers:
- BuildPerformanceService class
- Stage tracking and lifecycle
- Snapshotting and progress estimation
- Resource usage monitoring
- Aggregate statistics calculation
- Convenience functions and context manager
"""

import pytest
import threading
import psutil
import json
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone, timedelta
from services.build_performance_service import (
    BuildPerformanceService,
    BuildStages,
    get_build_performance_service,
    start_build_performance_tracking,
    update_build_stage,
    end_build_performance_tracking,
    get_build_performance,
    get_build_performance_snapshot,
    get_build_performance_stats,
)
from models.build_performance_models import (
    BuildPerformanceStartRequest,
    BuildPerformanceEndRequest,
    BuildStageTiming,
    BuildResourceUsage,
    BuildPerformanceMetrics,
)


class TestBuildPerformanceServiceComprehensive:
    """Comprehensive tests for BuildPerformanceService."""

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache service."""
        cache = MagicMock()
        cache.get.return_value = None
        return cache

    @pytest.fixture
    def service(self, mock_cache):
        """Create service with mock cache."""
        return BuildPerformanceService(cache_service=mock_cache)

    def test_initialization(self, mock_cache):
        """Test service initialization."""
        service = BuildPerformanceService(cache_service=mock_cache)
        assert service.cache is mock_cache
        assert service._active_builds == {}
        assert isinstance(service._lock, type(threading.Lock()))

    def test_default_initialization(self):
        """Test initialization with default cache service."""
        with patch("services.build_performance_service.CacheService") as mock_cache_cls:
            service = BuildPerformanceService()
            mock_cache_cls.assert_called_once()
            assert service.cache is not None

    def test_start_tracking(self, service):
        """Test starting tracking for a build."""
        request = BuildPerformanceStartRequest(
            conversion_id="conv-1", build_type="test", target_version="1.20.1", mod_size_bytes=1000
        )

        # metrics functions might not exist in the module, use create=True
        with patch("services.metrics.update_active_builds", create=True) as mock_metrics:
            metrics = service.start_tracking(request)

            assert metrics.conversion_id == "conv-1"
            assert metrics.build_type == "test"
            assert metrics.status == "running"
            assert len(metrics.stages) == 1
            assert metrics.stages[0].stage_name == BuildStages.INITIALIZATION
            assert metrics.build_id in service._active_builds
            mock_metrics.assert_called_once_with(1)

    def test_update_stage_new_and_existing(self, service):
        """Test updating existing stage and creating new one."""
        request = BuildPerformanceStartRequest(conversion_id="c1")
        build = service.start_tracking(request)
        build_id = build.build_id

        # Update existing INITIALIZATION stage
        service.update_stage(
            build_id, BuildStages.INITIALIZATION, status="completed", metadata={"foo": "bar"}
        )
        assert build.stages[0].status == "completed"
        assert build.stages[0].metadata == {"foo": "bar"}
        assert build.stages[0].end_time is not None

        # Create new stage
        service.update_stage(build_id, BuildStages.FILE_TRANSFER, status="running")
        assert len(build.stages) == 2
        assert build.stages[1].stage_name == BuildStages.FILE_TRANSFER
        assert build.stages[1].status == "running"

        # Update new stage to failed
        service.update_stage(
            build_id, BuildStages.FILE_TRANSFER, status="failed", error_message="Disk full"
        )
        assert build.stages[1].status == "failed"
        assert build.stages[1].error_message == "Disk full"

    def test_start_and_complete_stage_shortcuts(self, service):
        """Test start_stage and complete_stage shortcut methods."""
        request = BuildPerformanceStartRequest(conversion_id="c1")
        build = service.start_tracking(request)
        build_id = build.build_id

        service.start_stage(build_id, BuildStages.JAVA_ANALYSIS, metadata={"files": 10})
        assert build.stages[1].stage_name == BuildStages.JAVA_ANALYSIS
        assert build.stages[1].status == "running"
        assert build.stages[1].metadata == {"files": 10}

        service.complete_stage(build_id, BuildStages.JAVA_ANALYSIS, metadata={"results": "done"})
        assert build.stages[1].status == "completed"
        assert build.stages[1].metadata == {"files": 10, "results": "done"}

    def test_update_stage_non_existent_build(self, service):
        """Test update_stage returns None for non-existent build."""
        result = service.update_stage("invalid_id", "some_stage")
        assert result is None

    def test_end_tracking_success(self, service):
        """Test ending tracking for a build."""
        request = BuildPerformanceStartRequest(conversion_id="c1")
        build = service.start_tracking(request)
        build_id = build.build_id

        # Add some stages with duration
        now = datetime.now(timezone.utc)
        build.stages[0].start_time = now - timedelta(seconds=10)
        service.complete_stage(build_id, BuildStages.INITIALIZATION)
        build.stages[0].end_time = now - timedelta(seconds=5)
        build.stages[0].duration_ms = 5000.0

        end_request = BuildPerformanceEndRequest(status="completed", performance_score=95.0)

        with (
            patch("services.metrics.record_build_performance", create=True) as mock_metrics,
            patch("services.metrics.update_active_builds", create=True),
            patch("services.build_performance_service.psutil.Process") as mock_process,
        ):
            # Setup mock process for resource usage
            mock_proc_instance = mock_process.return_value
            mock_proc_instance.cpu_percent.return_value = 10.0
            mock_mem = MagicMock()
            mock_mem.rss = 100 * 1024 * 1024  # 100MB
            mock_proc_instance.memory_info.return_value = mock_mem

            final_metrics = service.end_tracking(build_id, end_request)

            assert final_metrics.status == "completed"
            assert final_metrics.performance_score == 95.0
            assert final_metrics.build_id not in service._active_builds
            assert final_metrics.resource_usage.memory_usage_mb == 100.0
            mock_metrics.assert_called_once()

    def test_end_tracking_calculates_default_score(self, service):
        """Test end_tracking calculates a default score if none provided."""
        request = BuildPerformanceStartRequest(conversion_id="c1")
        build = service.start_tracking(request)

        # Add a few successful stages
        for stage in [BuildStages.FILE_TRANSFER, BuildStages.JAVA_ANALYSIS]:
            service.start_stage(build.build_id, stage)
            service.complete_stage(build.build_id, stage)

        end_request = BuildPerformanceEndRequest(status="completed")
        final_metrics = service.end_tracking(build.build_id, end_request)

        assert final_metrics.performance_score is not None
        assert 0 <= final_metrics.performance_score <= 100

    def test_get_snapshot(self, service):
        """Test getting a performance snapshot."""
        request = BuildPerformanceStartRequest(conversion_id="c-snap")
        build = service.start_tracking(request)

        # Start next stage
        service.start_stage(build.build_id, BuildStages.FILE_TRANSFER)

        with patch("services.build_performance_service.psutil.Process") as mock_process:
            snapshot = service.get_snapshot(build.build_id)

            assert snapshot.build_id == build.build_id
            assert snapshot.current_stage == BuildStages.INITIALIZATION
            assert snapshot.progress_percent > 0

    def test_get_snapshot_non_existent(self, service):
        """Test get_snapshot returns None for invalid ID."""
        assert service.get_snapshot("invalid") is None

    def test_get_response_from_active_and_cache(self, service, mock_cache):
        """Test get_response reponses from memory or cache."""
        request = BuildPerformanceStartRequest(conversion_id="c1")
        build = service.start_tracking(request)

        # From active
        resp = service.get_response(build.build_id)
        assert resp.build_id == build.build_id

        # From cache (simulated)
        mock_cache.get.return_value = json.dumps(build.model_dump(mode="json"))
        resp_cached = service.get_response("cached_id")
        assert resp_cached is not None
        assert resp_cached.conversion_id == "c1"

    def test_get_summary(self, service):
        """Test get_summary."""
        request = BuildPerformanceStartRequest(conversion_id="c1")
        build = service.start_tracking(request)
        service.complete_stage(build.build_id, BuildStages.INITIALIZATION)
        service.start_stage(build.build_id, BuildStages.FILE_TRANSFER)
        service.update_stage(build.build_id, BuildStages.FILE_TRANSFER, status="failed")

        summary = service.get_summary(build.build_id)
        assert summary.conversion_id == "c1"
        assert summary.failed_stages == 1
        assert summary.stage_count == 2

    def test_get_stats_comprehensive(self, service):
        """Test aggregate statistics calculation."""
        now = datetime.now(timezone.utc)

        # Create a few finished builds
        build1 = BuildPerformanceMetrics(
            conversion_id="c1",
            status="completed",
            total_duration_ms=1000.0,
            performance_score=90.0,
            created_at=now - timedelta(minutes=10),
            completed_at=now - timedelta(minutes=9),
        )
        build1.stages.append(
            BuildStageTiming(
                stage_name="s1",
                start_time=now,
                end_time=now + timedelta(seconds=1),
                duration_ms=1000.0,
                status="completed",
            )
        )

        build2 = BuildPerformanceMetrics(
            conversion_id="c1",
            status="failed",
            total_duration_ms=2000.0,
            performance_score=40.0,
            created_at=now - timedelta(minutes=5),
            completed_at=now - timedelta(minutes=4),
        )
        build2.stages.append(
            BuildStageTiming(
                stage_name="s1",
                start_time=now,
                end_time=now + timedelta(seconds=2),
                duration_ms=2000.0,
                status="failed",
            )
        )

        service._active_builds = {build1.build_id: build1, build2.build_id: build2}

        stats = service.get_stats(conversion_id="c1")

        assert stats.total_builds == 2
        assert stats.completed_builds == 1
        assert stats.failed_builds == 1
        assert stats.average_duration_ms == 1500.0
        assert "s1" in stats.stage_stats
        assert stats.stage_stats["s1"]["average_ms"] == 1500.0

    def test_calculate_performance_score_edge_cases(self, service):
        """Test performance score calculation with no stages."""
        build = BuildPerformanceMetrics(conversion_id="c1")
        score = service._calculate_performance_score(build)
        assert score == 50.0  # Default for no stages

    def test_calculate_build_efficiency_edge_cases(self, service):
        """Test efficiency calculation with edge cases."""
        build = BuildPerformanceMetrics(conversion_id="c1")
        assert service._calculate_build_efficiency(build) == 0.0

        build.total_duration_ms = 1000.0
        build.stages.append(
            BuildStageTiming(
                stage_name="s1", start_time=datetime.now(timezone.utc), duration_ms=500.0
            )
        )
        assert service._calculate_build_efficiency(build) == 50.0

    def test_capture_resource_usage_exception(self, service):
        """Test resource usage capture handles psutil exceptions gracefully."""
        with patch("services.build_performance_service.psutil.Process") as mock_process:
            mock_proc_instance = mock_process.return_value
            mock_proc_instance.cpu_percent.side_effect = Exception("psutil error")
            mock_proc_instance.memory_info.side_effect = Exception("psutil error")

            usage = service._capture_resource_usage()
            assert usage.cpu_usage_percent is None
            assert usage.memory_usage_mb is None

    def test_track_stage_context_manager(self, service):
        """Test track_stage context manager."""
        request = BuildPerformanceStartRequest(conversion_id="c1")
        build = service.start_tracking(request)

        with service.track_stage(build.build_id, "context_stage"):
            assert build.stages[1].stage_name == "context_stage"
            assert build.stages[1].status == "running"

        assert build.stages[1].status == "completed"

        # Test exception in context manager
        try:
            with service.track_stage(build.build_id, "error_stage"):
                raise ValueError("Oops")
        except ValueError:
            pass

        assert build.stages[2].stage_name == "error_stage"
        assert build.stages[2].status == "failed"
        assert build.stages[2].error_message == "Oops"


class TestConvenienceFunctions:
    """Test global convenience functions."""

    @patch("services.build_performance_service.get_build_performance_service")
    def test_start_build_performance_tracking(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        start_build_performance_tracking("conv-123")
        mock_service.start_tracking.assert_called_once()

    @patch("services.build_performance_service.get_build_performance_service")
    def test_update_build_stage(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        update_build_stage("b1", "s1", status="completed")
        mock_service.update_stage.assert_called_once()
        # Verify first two args, rest can be positional or keyword
        args, kwargs = mock_service.update_stage.call_args
        assert args[0] == "b1"
        assert args[1] == "s1"

    @patch("services.build_performance_service.get_build_performance_service")
    def test_end_build_performance_tracking(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        end_build_performance_tracking("b1", status="completed")
        mock_service.end_tracking.assert_called_once()

    @patch("services.build_performance_service.get_build_performance_service")
    def test_get_build_performance(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        get_build_performance("b1")
        mock_service.get_response.assert_called_once_with("b1")

    @patch("services.build_performance_service.get_build_performance_service")
    def test_get_build_performance_snapshot(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        get_build_performance_snapshot("b1")
        mock_service.get_snapshot.assert_called_once_with("b1")

    @patch("services.build_performance_service.get_build_performance_service")
    def test_get_build_performance_stats(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        get_build_performance_stats(conversion_id="c1")
        mock_service.get_stats.assert_called_once_with("c1", 100)

    def test_get_build_performance_service_singleton(self):
        """Test get_build_performance_service returns a singleton."""
        s1 = get_build_performance_service()
        s2 = get_build_performance_service()
        assert s1 is s2
        assert isinstance(s1, BuildPerformanceService)
