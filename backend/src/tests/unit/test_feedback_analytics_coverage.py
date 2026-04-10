"""
Comprehensive unit tests for services/feedback_analytics.py to improve coverage.
"""

import pytest
from datetime import datetime, timedelta, timezone
from services.feedback_analytics import (
    FeedbackAnalyticsService,
    get_feedback_analytics,
    FeedbackMetrics,
)


class TestFeedbackAnalyticsServiceCoverage:
    """Tests for FeedbackAnalyticsService."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        return FeedbackAnalyticsService()

    def test_add_methods(self, service):
        """Test adding different types of feedback."""
        service.add_feedback({"conversion_id": "c1", "rating": 5})
        assert len(service._feedback_data) == 1

        service.add_bug_report({"title": "Bug 1", "severity": "high"})
        assert len(service._bug_reports) == 1

        service.add_feature_request({"title": "Feature 1"})
        assert len(service._feature_requests) == 1

    def test_get_satisfaction_score_empty(self, service):
        """Test score calculation with no data."""
        score = service.get_satisfaction_score(datetime.now(), datetime.now())
        assert score["average"] == 0.0
        assert score["count"] == 0

    def test_get_satisfaction_score_calculation(self, service):
        """Test average and NPS calculation."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=1)
        end = now + timedelta(days=1)

        # 2 promoters (5, 4), 1 neutral (3), 1 detractor (1)
        service.add_feedback({"rating": 5, "timestamp": now})
        service.add_feedback({"rating": 4, "timestamp": now})
        service.add_feedback({"rating": 3, "timestamp": now})
        service.add_feedback({"rating": 1, "timestamp": now})
        # Outside range
        service.add_feedback({"rating": 5, "timestamp": now - timedelta(days=2)})

        score = service.get_satisfaction_score(start, end)

        assert score["count"] == 4
        assert score["average"] == (5 + 4 + 3 + 1) / 4
        assert score["distribution"][5] == 1
        assert score["promoters"] == 2
        assert score["detractors"] == 1
        # NPS = (2/4 - 1/4) * 100 = 25
        assert score["nps"] == 25.0

    def test_get_feedback_by_type(self, service):
        """Test grouping feedback by type."""
        now = datetime.now(timezone.utc)
        service.add_feedback({"feedback_type": "ui", "timestamp": now})
        service.add_feedback({"feedback_type": "ui", "timestamp": now})
        service.add_feedback({"feedback_type": "api", "timestamp": now})

        by_type = service.get_feedback_by_type(
            now - timedelta(minutes=1), now + timedelta(minutes=1)
        )
        assert by_type["ui"] == 2
        assert by_type["api"] == 1

    def test_get_bug_summary(self, service):
        """Test bug summary aggregation."""
        now = datetime.now(timezone.utc)
        service.add_bug_report({"severity": "critical", "status": "fixed", "timestamp": now})
        service.add_bug_report({"severity": "high", "status": "new", "timestamp": now})

        summary = service.get_bug_summary(now - timedelta(minutes=1), now + timedelta(minutes=1))
        assert summary["total"] == 2
        assert summary["critical_count"] == 1
        assert summary["by_status"]["fixed"] == 1

    def test_get_feature_request_summary(self, service):
        """Test feature request summary and sorting."""
        now = datetime.now(timezone.utc)
        service.add_feature_request(
            {"title": "F1", "votes": 10, "category": "core", "timestamp": now}
        )
        service.add_feature_request(
            {"title": "F2", "votes": 50, "category": "ui", "timestamp": now}
        )

        summary = service.get_feature_request_summary(
            now - timedelta(minutes=1), now + timedelta(minutes=1)
        )
        assert summary["total"] == 2
        assert summary["top_features"][0]["title"] == "F2"  # Most votes first
        assert summary["by_category"]["core"] == 1

    def test_get_conversion_feedback_correlation(self, service):
        """Test correlation analysis and insights."""
        now = datetime.now(timezone.utc)
        # Fast conversion, high rating
        service.add_feedback(
            {
                "rating": 5,
                "timestamp": now,
                "properties": {"model_used": "gpt-4", "duration_seconds": 30},
            }
        )
        # Slow conversion, low rating
        service.add_feedback(
            {
                "rating": 2,
                "timestamp": now,
                "properties": {"model_used": "gpt-3.5", "duration_seconds": 400},
            }
        )

        corr = service.get_conversion_feedback_correlation(
            now - timedelta(minutes=1), now + timedelta(minutes=1)
        )

        assert corr["by_model"]["gpt-4"] == 5.0
        assert corr["by_model"]["gpt-3.5"] == 2.0
        assert corr["by_duration"]["fast"] == 5.0
        assert corr["by_duration"]["slow"] == 2.0

        assert len(corr["insights"]) >= 2
        assert any("gpt-4" in i for i in corr["insights"])
        assert any("Faster conversions" in i for i in corr["insights"])

    def test_get_weekly_report(self, service):
        """Test generation of comprehensive weekly report."""
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=now.weekday())  # Monday

        service.add_feedback({"rating": 5, "timestamp": now, "feedback_type": "general"})

        report = service.get_weekly_report(week_start)

        assert "satisfaction" in report
        assert "period" in report
        assert report["total_feedback"] == 1
        assert "generated_at" in report

    def test_get_feedback_analytics_singleton(self):
        """Test singleton accessor."""
        s1 = get_feedback_analytics()
        s2 = get_feedback_analytics()
        assert s1 is s2
        assert isinstance(s1, FeedbackAnalyticsService)
