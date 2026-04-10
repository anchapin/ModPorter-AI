"""
Unit tests for FeedbackAnalyticsService.
"""

import pytest
from datetime import datetime, timedelta, timezone
from services.feedback_analytics import (
    FeedbackAnalyticsService,
    get_feedback_analytics,
    FeedbackMetrics,
)


class TestFeedbackAnalyticsService:
    """Test cases for FeedbackAnalyticsService."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        return FeedbackAnalyticsService()

    @pytest.fixture
    def sample_feedback(self):
        """Sample feedback data."""
        now = datetime.now(timezone.utc)
        return [
            {
                "conversion_id": "conv-1",
                "rating": 5,
                "timestamp": now - timedelta(days=1),
                "feedback_type": "positive",
                "properties": {"model_used": "gpt-4", "duration_seconds": 120},
            },
            {
                "conversion_id": "conv-2",
                "rating": 4,
                "timestamp": now - timedelta(days=2),
                "feedback_type": "positive",
                "properties": {"model_used": "gpt-4", "duration_seconds": 45},
            },
            {
                "conversion_id": "conv-3",
                "rating": 2,
                "timestamp": now - timedelta(days=3),
                "feedback_type": "negative",
                "properties": {"model_used": "claude-3", "duration_seconds": 600},
            },
            {
                "conversion_id": "conv-4",
                "rating": 1,
                "timestamp": now - timedelta(days=4),
                "feedback_type": "negative",
                "properties": {"model_used": "claude-3", "duration_seconds": 400},
            },
        ]

    def test_add_feedback(self, service):
        """Test adding feedback."""
        feedback = {"conversion_id": "test-1", "rating": 5}
        service.add_feedback(feedback)
        assert len(service._feedback_data) == 1
        assert service._feedback_data[0]["conversion_id"] == "test-1"

    def test_add_bug_report(self, service):
        """Test adding bug report."""
        bug = {"title": "Test bug", "severity": "high", "status": "new"}
        service.add_bug_report(bug)
        assert len(service._bug_reports) == 1
        assert service._bug_reports[0]["title"] == "Test bug"

    def test_add_feature_request(self, service):
        """Test adding feature request."""
        feature = {"title": "New feature", "category": "ui", "votes": 10}
        service.add_feature_request(feature)
        assert len(service._feature_requests) == 1
        assert service._feature_requests[0]["title"] == "New feature"

    def test_get_satisfaction_score_empty(self, service):
        """Test satisfaction score with no data."""
        now = datetime.now(timezone.utc)
        result = service.get_satisfaction_score(now - timedelta(days=7), now)
        assert result["average"] == 0.0
        assert result["count"] == 0

    def test_get_satisfaction_score_with_data(self, service, sample_feedback):
        """Test satisfaction score calculation."""
        for fb in sample_feedback:
            service.add_feedback(fb)

        now = datetime.now(timezone.utc)
        result = service.get_satisfaction_score(now - timedelta(days=7), now)

        assert result["count"] == 4
        assert result["average"] == pytest.approx(3.0)
        assert "promoters" in result
        assert "detractors" in result
        assert "nps" in result

    def test_get_feedback_by_type(self, service, sample_feedback):
        """Test feedback count by type."""
        for fb in sample_feedback:
            service.add_feedback(fb)

        now = datetime.now(timezone.utc)
        result = service.get_feedback_by_type(now - timedelta(days=7), now)

        assert result["positive"] == 2
        assert result["negative"] == 2

    def test_get_bug_summary(self, service):
        """Test bug summary."""
        now = datetime.now(timezone.utc)
        service.add_bug_report(
            {
                "title": "Bug 1",
                "severity": "critical",
                "status": "open",
                "timestamp": now - timedelta(days=1),
            }
        )
        service.add_bug_report(
            {
                "title": "Bug 2",
                "severity": "high",
                "status": "resolved",
                "timestamp": now - timedelta(days=2),
            }
        )

        result = service.get_bug_summary(now - timedelta(days=7), now)

        assert result["total"] == 2
        assert result["critical_count"] == 1
        assert result["high_count"] == 1

    def test_get_feature_request_summary(self, service):
        """Test feature request summary."""
        now = datetime.now(timezone.utc)
        service.add_feature_request(
            {
                "title": "Feature 1",
                "category": "conversion",
                "status": "planned",
                "votes": 50,
                "timestamp": now - timedelta(days=1),
            }
        )
        service.add_feature_request(
            {
                "title": "Feature 2",
                "category": "ui",
                "status": "submitted",
                "votes": 30,
                "timestamp": now - timedelta(days=2),
            }
        )

        result = service.get_feature_request_summary(now - timedelta(days=7), now)

        assert result["total"] == 2
        assert len(result["top_features"]) == 2

    def test_conversion_feedback_correlation(self, service, sample_feedback):
        """Test conversion feedback correlation."""
        for fb in sample_feedback:
            service.add_feedback(fb)

        now = datetime.now(timezone.utc)
        result = service.get_conversion_feedback_correlation(now - timedelta(days=7), now)

        assert "by_model" in result
        assert "by_duration" in result
        assert "insights" in result

    def test_get_weekly_report(self, service, sample_feedback):
        """Test weekly report generation."""
        for fb in sample_feedback:
            service.add_feedback(fb)

        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=now.weekday())
        result = service.get_weekly_report(week_start)

        assert "period" in result
        assert "satisfaction" in result
        assert "bugs" in result
        assert "feature_requests" in result
        assert "generated_at" in result

    def test_singleton_pattern(self):
        """Test singleton pattern for get_feedback_analytics."""
        instance1 = get_feedback_analytics()
        instance2 = get_feedback_analytics()
        assert instance1 is instance2


class TestFeedbackMetrics:
    """Test cases for FeedbackMetrics dataclass."""

    def test_feedback_metrics_creation(self):
        """Test creating FeedbackMetrics instance."""
        metrics = FeedbackMetrics(
            total_feedback=100,
            average_rating=4.5,
            rating_distribution={1: 5, 2: 10, 3: 15, 4: 30, 5: 40},
            feedback_by_type={"positive": 60, "negative": 40},
            response_rate=0.75,
            satisfaction_trend="improving",
        )

        assert metrics.total_feedback == 100
        assert metrics.average_rating == 4.5
        assert metrics.satisfaction_trend == "improving"
