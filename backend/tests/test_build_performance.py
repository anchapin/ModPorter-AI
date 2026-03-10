"""
Tests for Build Performance Tracking (Issue #691)

Tests the build performance tracking service, API endpoints, and metrics integration.
"""

import pytest
import time
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from models.build_performance_models import (
    BuildPerformanceMetrics,
    BuildStageTiming,
    BuildResourceUsage,
    BuildPerformanceStartRequest,
    BuildPerformanceEndRequest,
)
from services.build_performance_service import (
    BuildPerformanceService,
    BuildStages,
    start_build_performance_tracking,
    update_build_stage,
    end_build_performance_tracking,
    get_build_performance,
)


class TestBuildPerformanceModels:
    """Tests for build performance data models."""

    def test_build_stage_timing_creation(self):
        """Test creating a build stage timing."""
        stage = BuildStageTiming(
            stage_name=BuildStages.JAVA_ANALYSIS,
            start_time=datetime.now(timezone.utc),
            status="running",
        )

        assert stage.stage_name == "java_analysis"
        assert stage.status == "running"
        assert stage.start_time is not None
        assert stage.end_time is None
        assert stage.duration_ms is None

    def test_build_stage_complete(self):
        """Test completing a build stage."""
        stage = BuildStageTiming(
            stage_name=BuildStages.JAVA_ANALYSIS,
            start_time=datetime.now(timezone.utc),
            status="running",
        )

        # Complete the stage
        stage.complete(status="completed")

        assert stage.status == "completed"
        assert stage.end_time is not None
        assert stage.duration_ms is not None
        assert stage.duration_ms > 0

    def test_build_performance_metrics_creation(self):
        """Test creating a build performance metrics object."""
        metrics = BuildPerformanceMetrics(
            conversion_id="test-conversion-123",
            build_type="conversion",
            target_version="1.20.0",
            mod_size_bytes=1024000,
            status="running",
        )

        assert metrics.conversion_id == "test-conversion-123"
        assert metrics.build_type == "conversion"
        assert metrics.target_version == "1.20.0"
        assert metrics.mod_size_bytes == 1024000
        assert metrics.status == "running"
        assert metrics.build_id is not None  # Auto-generated UUID

    def test_build_start_request(self):
        """Test creating a build start request."""
        request = BuildPerformanceStartRequest(
            conversion_id="test-conversion-456",
            build_type="conversion",
            target_version="1.20.0",
            mod_size_bytes=2048000,
        )

        assert request.conversion_id == "test-conversion-456"
        assert request.build_type == "conversion"
        assert request.target_version == "1.20.0"
        assert request.mod_size_bytes == 2048000

    def test_build_end_request(self):
        """Test creating a build end request."""
        request = BuildPerformanceEndRequest(
            status="completed",
            performance_score=95.5,
        )

        assert request.status == "completed"
        assert request.performance_score == 95.5


class TestBuildPerformanceService:
    """Tests for the build performance service."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance for each test."""
        return BuildPerformanceService()

    def test_start_tracking(self, service):
        """Test starting a new build tracking."""
        request = BuildPerformanceStartRequest(
            conversion_id="test-123",
            build_type="conversion",
            target_version="1.20.0",
            mod_size_bytes=1024000,
        )

        build = service.start_tracking(request)

        assert build is not None
        assert build.conversion_id == "test-123"
        assert build.status == "running"
        assert len(build.stages) > 0
        assert build.stages[0].stage_name == BuildStages.INITIALIZATION

    def test_update_stage(self, service):
        """Test updating a build stage."""
        # Start tracking
        request = BuildPerformanceStartRequest(
            conversion_id="test-456",
            build_type="conversion",
        )
        build = service.start_tracking(request)

        # Update to file transfer stage
        updated = service.update_stage(
            build.build_id,
            BuildStages.FILE_TRANSFER,
            status="completed",
        )

        assert updated is not None
        stage_names = [s.stage_name for s in updated.stages]
        assert BuildStages.FILE_TRANSFER in stage_names

    def test_end_tracking_completed(self, service):
        """Test ending tracking with completed status."""
        # Start tracking
        request = BuildPerformanceStartRequest(
            conversion_id="test-789",
            build_type="conversion",
        )
        build = service.start_tracking(request)

        # Update stage
        service.update_stage(build.build_id, BuildStages.FILE_TRANSFER, status="completed")

        # End tracking
        end_request = BuildPerformanceEndRequest(
            status="completed",
            performance_score=90.0,
        )
        final_build = service.end_tracking(build.build_id, end_request)

        assert final_build is not None
        assert final_build.status == "completed"
        assert final_build.performance_score == 90.0
        assert final_build.completed_at is not None

    def test_end_tracking_failed(self, service):
        """Test ending tracking with failed status."""
        # Start tracking
        request = BuildPerformanceStartRequest(
            conversion_id="test-fail",
            build_type="conversion",
        )
        build = service.start_tracking(request)

        # End with failure
        end_request = BuildPerformanceEndRequest(
            status="failed",
            error_message="Build failed",
        )
        final_build = service.end_tracking(build.build_id, end_request)

        assert final_build is not None
        assert final_build.status == "failed"
        assert final_build.error_message == "Build failed"

    def test_get_nonexistent_build(self, service):
        """Test getting a build that doesn't exist."""
        result = service.get_build("nonexistent-id")
        assert result is None

    def test_track_stage_context_manager(self, service):
        """Test using track_stage as context manager."""
        # Start tracking
        request = BuildPerformanceStartRequest(
            conversion_id="test-context",
            build_type="conversion",
        )
        build = service.start_tracking(request)

        # Use context manager
        with service.track_stage(build.build_id, BuildStages.JAVA_ANALYSIS):
            # Simulate some work
            time.sleep(0.01)

        # Verify stage was completed
        updated = service.get_build(build.build_id)
        assert updated is not None
        stage = next((s for s in updated.stages if s.stage_name == BuildStages.JAVA_ANALYSIS), None)
        assert stage is not None
        assert stage.status == "completed"
        assert stage.duration_ms is not None


class TestBuildPerformanceConvenienceFunctions:
    """Tests for convenience functions."""

    @patch("services.build_performance_service._build_performance_service", None)
    def test_start_build_performance_tracking(self):
        """Test convenience function for starting tracking."""
        build = start_build_performance_tracking(
            conversion_id="convenience-test",
            build_type="conversion",
            target_version="1.20.0",
            mod_size_bytes=500000,
        )

        assert build is not None
        assert build.conversion_id == "convenience-test"
        assert build.build_type == "conversion"

    @patch("services.build_performance_service._build_performance_service", None)
    def test_update_and_end_build(self):
        """Test convenience functions for updating and ending."""
        # Start
        build = start_build_performance_tracking(
            conversion_id="update-test",
            build_type="conversion",
        )

        # Update
        updated = update_build_stage(
            build.build_id,
            BuildStages.FILE_TRANSFER,
            status="completed",
        )
        assert updated is not None

        # End
        ended = end_build_performance_tracking(
            build.build_id,
            status="completed",
            performance_score=85.0,
        )
        assert ended is not None
        assert ended.status == "completed"
        assert ended.performance_score == 85.0

    @patch("services.build_performance_service._build_performance_service", None)
    def test_get_build_performance(self):
        """Test getting build performance via convenience function."""
        # Start a build
        build = start_build_performance_tracking(
            conversion_id="get-test",
            build_type="conversion",
        )

        # Get while still active
        result = get_build_performance(build.build_id)

        assert result is not None
        assert result.build_id == build.build_id
        assert result.conversion_id == "get-test"

        # Now end it
        end_build_performance_tracking(
            build.build_id,
            status="completed",
        )


class TestBuildStages:
    """Tests for build stage constants."""

    def test_all_stages_defined(self):
        """Test that all expected stages are defined."""
        assert BuildStages.INITIALIZATION == "initialization"
        assert BuildStages.FILE_TRANSFER == "file_transfer"
        assert BuildStages.JAVA_ANALYSIS == "java_analysis"
        assert BuildStages.BEDROCK_ARCHITECT == "bedrock_architect"
        assert BuildStages.LOGIC_TRANSLATION == "logic_translation"
        assert BuildStages.ASSET_CONVERSION == "asset_conversion"
        assert BuildStages.PACKAGING == "packaging"
        assert BuildStages.QA_VALIDATION == "qa_validation"
        assert BuildStages.FINALIZATION == "finalization"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
