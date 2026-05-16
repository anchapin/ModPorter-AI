"""
Unit tests for conversion quality metrics service and API.

Issue: #1547 - DX: Publish conversion quality metrics and accuracy data
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone

from services.conversion_quality_metrics import (
    ConversionQualityMetricsService,
    ConversionQualityMetrics,
    ConversionAccuracyMetrics,
    ConversionStage,
)


class TestConversionQualityMetricsService:
    """Tests for ConversionQualityMetricsService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mock db."""
        return ConversionQualityMetricsService(mock_db)

    def test_service_init(self, service, mock_db):
        """Test service initializes with db session."""
        assert service.db is mock_db

    def test_conversion_quality_metrics_dataclass(self):
        """Test ConversionQualityMetrics dataclass."""
        metrics = ConversionQualityMetrics(
            total_conversions=100,
            successful_conversions=80,
            failed_conversions=15,
            cancelled_conversions=5,
            success_rate=80.0,
            failure_rate=15.0,
            average_processing_time_seconds=45.5,
            conversions_by_target_version={"1.20.0": 100},
            conversions_by_status={"completed": 80, "failed": 15, "cancelled": 5},
            feedback_score=4.2,
            total_feedback_count=50,
            period_days=30,
        )
        assert metrics.total_conversions == 100
        assert metrics.successful_conversions == 80
        assert metrics.success_rate == 80.0

    def test_conversion_accuracy_metrics_dataclass(self):
        """Test ConversionAccuracyMetrics dataclass."""
        accuracy = ConversionAccuracyMetrics(
            total_features_attempted=200,
            features_converted_successfully=180,
            accuracy_percentage=90.0,
            by_feature_category={"blocks": {"attempted": 100, "success": 90}},
        )
        assert accuracy.total_features_attempted == 200
        assert accuracy.accuracy_percentage == 90.0

    def test_conversion_stage_enum(self):
        """Test ConversionStage enum values."""
        assert ConversionStage.QUEUED.value == "queued"
        assert ConversionStage.PROCESSING.value == "processing"
        assert ConversionStage.COMPLETED.value == "completed"
        assert ConversionStage.FAILED.value == "failed"


class TestConversionQualityMetricsApi:
    """Tests for conversion quality metrics API endpoints."""

    def test_quality_response_model(self):
        """Test ConversionQualityResponse model can be instantiated."""
        from api.conversion_quality_metrics import ConversionQualityResponse

        response = ConversionQualityResponse(
            total_conversions=100,
            successful_conversions=80,
            failed_conversions=15,
            cancelled_conversions=5,
            success_rate=80.0,
            failure_rate=15.0,
            average_processing_time_seconds=None,
            conversions_by_target_version={"1.20.0": 100},
            conversions_by_status={"completed": 80, "failed": 15},
            feedback_score=4.2,
            total_feedback_count=50,
            period_days=30,
        )
        assert response.total_conversions == 100
        assert response.success_rate == 80.0

    def test_metrics_summary_response_model(self):
        """Test ConversionMetricsSummaryResponse model can be instantiated."""
        from api.conversion_quality_metrics import ConversionMetricsSummaryResponse

        response = ConversionMetricsSummaryResponse(
            generated_at=datetime.now(timezone.utc).isoformat(),
            period_days=30,
            summary={
                "total_conversions": 100,
                "successful": 80,
                "failed": 15,
                "cancelled": 5,
                "success_rate_percent": 80.0,
                "failure_rate_percent": 15.0,
            },
            conversions_by_status={"completed": 80, "failed": 15},
            conversions_by_target_version={"1.20.0": 100},
            user_feedback={"total_submissions": 50, "average_score": 4.2},
            metadata={"description": "Test metrics", "version": "1.0.0"},
        )
        assert response.period_days == 30
        assert response.summary["total_conversions"] == 100

    def test_accuracy_response_model(self):
        """Test AccuracyMetricsResponse model can be instantiated."""
        from api.conversion_quality_metrics import AccuracyMetricsResponse

        response = AccuracyMetricsResponse(
            total_features_attempted=200,
            features_converted_successfully=180,
            accuracy_percentage=90.0,
            by_feature_category={},
        )
        assert response.total_features_attempted == 200
        assert response.accuracy_percentage == 90.0


class TestConversionQualityMetricsServiceAsync:
    """Async tests for ConversionQualityMetricsService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock async database session."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        return mock_session

    @pytest.mark.asyncio
    async def test_get_quality_metrics_with_no_jobs(self, mock_db_session):
        """Test quality metrics returns zeros when no jobs exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_feedback_count = MagicMock()
        mock_feedback_count.scalar.return_value = 0

        mock_db_session.execute = AsyncMock(
            side_effect=[mock_result, mock_feedback_count, mock_feedback_count]
        )

        service = ConversionQualityMetricsService(mock_db_session)
        metrics = await service.get_quality_metrics(days=30)

        assert metrics.total_conversions == 0
        assert metrics.success_rate == 0.0
        assert metrics.failure_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_metrics_summary(self, mock_db_session):
        """Test metrics summary returns expected structure."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_feedback_count = MagicMock()
        mock_feedback_count.scalar.return_value = 0

        mock_db_session.execute = AsyncMock(
            side_effect=[mock_result, mock_feedback_count, mock_feedback_count]
        )

        service = ConversionQualityMetricsService(mock_db_session)
        summary = await service.get_metrics_summary(days=30)

        assert "generated_at" in summary
        assert "period_days" in summary
        assert "summary" in summary
        assert "metadata" in summary
        assert summary["metadata"]["issue"] == "#1547"

    def test_get_accuracy_metrics(self, mock_db_session):
        """Test accuracy metrics returns placeholder data."""
        service = ConversionQualityMetricsService(mock_db_session)
        accuracy = service.get_accuracy_metrics(days=30)

        assert accuracy.total_features_attempted == 0
        assert accuracy.accuracy_percentage == 0.0
        assert accuracy.by_feature_category == {}