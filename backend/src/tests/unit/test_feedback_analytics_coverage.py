"""
Tests for feedback_analytics.py to boost coverage.

Covers:
- FeedbackAnalyticsService class
- Feedback, bug report, feature request management
- Satisfaction score calculation
- Feedback aggregation methods
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from unittest import mock

try:
    from datetime import timezone
except ImportError:
    timezone = None

from services.feedback_analytics import (
    FeedbackAnalyticsService,
    FeedbackMetrics,
)


class TestFeedbackAnalyticsService:
    """Test FeedbackAnalyticsService class."""

    @pytest.fixture
    def service(self):
        """Create feedback analytics service."""
        return FeedbackAnalyticsService()

    def test_service_initialization(self):
        """Test service initializes with empty data."""
        service = FeedbackAnalyticsService()
        assert service._feedback_data == []
        assert service._bug_reports == []
        assert service._feature_requests == []


class TestAddFeedback:
    """Test adding feedback data."""

    @pytest.fixture
    def service(self):
        return FeedbackAnalyticsService()

    def test_add_feedback_basic(self, service):
        """Test adding basic feedback."""
        feedback = {
            "conversion_id": "conv-123",
            "rating": 5,
            "timestamp": datetime.now(),
            "comment": "Great conversion!",
        }

        service.add_feedback(feedback)

        assert len(service._feedback_data) == 1
        assert service._feedback_data[0]["conversion_id"] == "conv-123"

    def test_add_multiple_feedback(self, service):
        """Test adding multiple feedback entries."""
        for i in range(5):
            feedback = {
                "conversion_id": f"conv-{i}",
                "rating": i + 1,
                "timestamp": datetime.now() if timezone is None else datetime.now(timezone.utc),
            }
            service.add_feedback(feedback)

        assert len(service._feedback_data) == 5

    def test_add_feedback_no_timestamp(self, service):
        """Test adding feedback without timestamp."""
        feedback = {"conversion_id": "conv-no-ts", "rating": 4}

        service.add_feedback(feedback)

        assert len(service._feedback_data) == 1


class TestAddBugReports:
    """Test adding bug reports."""

    @pytest.fixture
    def service(self):
        return FeedbackAnalyticsService()

    def test_add_bug_report_basic(self, service):
        """Test adding basic bug report."""
        bug = {
            "title": "Crash on startup",
            "conversion_id": "conv-123",
            "severity": "high",
            "timestamp": datetime.now(),
        }

        service.add_bug_report(bug)

        assert len(service._bug_reports) == 1
        assert service._bug_reports[0]["title"] == "Crash on startup"

    def test_add_multiple_bug_reports(self, service):
        """Test adding multiple bug reports."""
        for i in range(3):
            bug = {
                "title": f"Bug {i}",
                "conversion_id": f"conv-{i}",
                "severity": "medium",
                "timestamp": datetime.now() if timezone is None else datetime.now(timezone.utc),
            }
            service.add_bug_report(bug)

        assert len(service._bug_reports) == 3


class TestAddFeatureRequests:
    """Test adding feature requests."""

    @pytest.fixture
    def service(self):
        return FeedbackAnalyticsService()

    def test_add_feature_request_basic(self, service):
        """Test adding basic feature request."""
        feature = {
            "title": "Add support for custom entities",
            "conversion_id": "conv-123",
            "priority": "high",
            "timestamp": datetime.now(),
        }

        service.add_feature_request(feature)

        assert len(service._feature_requests) == 1
        assert service._feature_requests[0]["title"] == "Add support for custom entities"

    def test_add_multiple_feature_requests(self, service):
        """Test adding multiple feature requests."""
        for i in range(4):
            feature = {
                "title": f"Feature {i}",
                "conversion_id": f"conv-{i}",
                "priority": "low",
                "timestamp": datetime.now() if timezone is None else datetime.now(timezone.utc),
            }
            service.add_feature_request(feature)

        assert len(service._feature_requests) == 4


class TestSatisfactionScore:
    """Test satisfaction score calculation."""

    @pytest.fixture
    def service(self):
        return FeedbackAnalyticsService()

    def test_get_satisfaction_score_empty(self, service):
        """Test satisfaction score with no feedback."""
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()

        with patch("services.feedback_analytics.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.now()
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = service.get_satisfaction_score(start, end)

        assert result["average"] == 0.0
        assert result["count"] == 0
        assert result["distribution"] == {}


class TestFeedbackByType:
    """Test feedback categorization by type."""

    @pytest.fixture
    def service(self):
        return FeedbackAnalyticsService()

    def test_get_feedback_by_type_empty(self, service):
        """Test get_feedback_by_type with no data."""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)

        result = service.get_feedback_by_type(start, end)

        assert result == {}


class TestFeedbackMetrics:
    """Test FeedbackMetrics dataclass."""

    def test_feedback_metrics_creation(self):
        """Test FeedbackMetrics creation."""
        metrics = FeedbackMetrics(
            total_feedback=100,
            average_rating=4.5,
            rating_distribution={1: 5, 2: 10, 3: 20, 4: 35, 5: 30},
            feedback_by_type={"bug_report": 30, "general": 70},
            response_rate=0.85,
            satisfaction_trend="improving",
        )

        assert metrics.total_feedback == 100
        assert metrics.average_rating == 4.5
        assert metrics.satisfaction_trend == "improving"

    def test_feedback_metrics_defaults(self):
        """Test FeedbackMetrics with default values."""
        metrics = FeedbackMetrics(
            total_feedback=0,
            average_rating=0.0,
            rating_distribution={},
            feedback_by_type={},
            response_rate=0.0,
            satisfaction_trend="stable",
        )

        assert metrics.total_feedback == 0
        assert metrics.satisfaction_trend == "stable"
