"""
Feedback Analytics Dashboard

Analyze feedback data and generate insights.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FeedbackMetrics:
    """Feedback metrics snapshot."""

    total_feedback: int
    average_rating: float
    rating_distribution: Dict[int, int]
    feedback_by_type: Dict[str, int]
    response_rate: float
    satisfaction_trend: str  # "improving", "stable", "declining"


class FeedbackAnalyticsService:
    """Analytics service for feedback data."""

    def __init__(self):
        self._feedback_data = []
        self._bug_reports = []
        self._feature_requests = []

    def add_feedback(self, feedback: Dict[str, Any]):
        """Add feedback data point."""
        self._feedback_data.append(feedback)
        logger.debug(f"Added feedback: {feedback.get('conversion_id')}")

    def add_bug_report(self, bug: Dict[str, Any]):
        """Add bug report."""
        self._bug_reports.append(bug)
        logger.info(f"Bug report added: {bug.get('title')}")

    def add_feature_request(self, feature: Dict[str, Any]):
        """Add feature request."""
        self._feature_requests.append(feature)
        logger.info(f"Feature request added: {feature.get('title')}")

    def get_satisfaction_score(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Get satisfaction score for date range.

        Returns:
            Dict with average rating, count, and distribution
        """
        ratings = []
        for feedback in self._feedback_data:
            timestamp = feedback.get("timestamp", datetime.now(timezone.utc))
            if start_date <= timestamp <= end_date:
                rating = feedback.get("rating", 0)
                if rating > 0:
                    ratings.append(rating)

        if not ratings:
            return {
                "average": 0.0,
                "count": 0,
                "distribution": {},
            }

        # Calculate distribution
        distribution = {i: 0 for i in range(1, 6)}
        for rating in ratings:
            distribution[rating] += 1

        return {
            "average": sum(ratings) / len(ratings),
            "count": len(ratings),
            "distribution": distribution,
            "promoters": sum(1 for r in ratings if r >= 4),
            "detractors": sum(1 for r in ratings if r <= 2),
            "nps": (
                (sum(1 for r in ratings if r >= 4) - sum(1 for r in ratings if r <= 2))
                / len(ratings)
            )
            * 100,
        }

    def get_feedback_by_type(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, int]:
        """Get feedback count by type."""
        by_type = {}

        for feedback in self._feedback_data:
            timestamp = feedback.get("timestamp", datetime.now(timezone.utc))
            if start_date <= timestamp <= end_date:
                feedback_type = feedback.get("feedback_type", "other")
                by_type[feedback_type] = by_type.get(feedback_type, 0) + 1

        return by_type

    def get_bug_summary(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get bug report summary."""
        bugs = []
        for bug in self._bug_reports:
            timestamp = bug.get("timestamp", datetime.now(timezone.utc))
            if start_date <= timestamp <= end_date:
                bugs.append(bug)

        by_severity = {}
        by_status = {}

        for bug in bugs:
            severity = bug.get("severity", "unknown")
            status = bug.get("status", "new")
            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total": len(bugs),
            "by_severity": by_severity,
            "by_status": by_status,
            "critical_count": by_severity.get("critical", 0),
            "high_count": by_severity.get("high", 0),
        }

    def get_feature_request_summary(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get feature request summary."""
        features = []
        for feature in self._feature_requests:
            timestamp = feature.get("timestamp", datetime.now(timezone.utc))
            if start_date <= timestamp <= end_date:
                features.append(feature)

        by_category = {}
        by_status = {}

        for feature in features:
            category = feature.get("category", "other")
            status = feature.get("status", "submitted")
            by_category[category] = by_category.get(category, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1

        # Top requested features (by votes if available)
        top_features = sorted(
            features,
            key=lambda x: x.get("votes", 0),
            reverse=True,
        )[:10]

        return {
            "total": len(features),
            "by_category": by_category,
            "by_status": by_status,
            "top_features": [
                {
                    "title": f.get("title"),
                    "votes": f.get("votes", 0),
                    "category": f.get("category"),
                }
                for f in top_features
            ],
        }

    def get_conversion_feedback_correlation(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Analyze correlation between conversion metrics and feedback.

        Returns:
            Dict with insights about conversion quality and feedback
        """
        # Group feedback by conversion characteristics
        feedback_by_model = {}
        feedback_by_duration = {"fast": [], "medium": [], "slow": []}

        for feedback in self._feedback_data:
            timestamp = feedback.get("timestamp", datetime.now(timezone.utc))
            if not (start_date <= timestamp <= end_date):
                continue

            rating = feedback.get("rating", 0)
            properties = feedback.get("properties", {})

            # By model used
            model = properties.get("model_used", "unknown")
            if model not in feedback_by_model:
                feedback_by_model[model] = []
            feedback_by_model[model].append(rating)

            # By duration
            duration = properties.get("duration_seconds", 0)
            if duration < 60:
                feedback_by_duration["fast"].append(rating)
            elif duration < 300:
                feedback_by_duration["medium"].append(rating)
            else:
                feedback_by_duration["slow"].append(rating)

        # Calculate averages
        model_averages = {
            model: sum(ratings) / len(ratings) if ratings else 0
            for model, ratings in feedback_by_model.items()
        }

        duration_averages = {
            category: sum(ratings) / len(ratings) if ratings else 0
            for category, ratings in feedback_by_duration.items()
        }

        return {
            "by_model": model_averages,
            "by_duration": duration_averages,
            "insights": self._generate_insights(model_averages, duration_averages),
        }

    def _generate_insights(
        self,
        model_averages: Dict[str, float],
        duration_averages: Dict[str, float],
    ) -> List[str]:
        """Generate insights from data."""
        insights = []

        # Model insights
        if model_averages:
            best_model = max(model_averages, key=model_averages.get)
            worst_model = min(model_averages, key=model_averages.get)
            insights.append(
                f"Best performing model: {best_model} ({model_averages[best_model]:.1f}/5)"
            )
            if model_averages[best_model] - model_averages[worst_model] > 0.5:
                insights.append(f"Consider reducing use of {worst_model}")

        # Duration insights
        if duration_averages["fast"] > duration_averages["slow"]:
            insights.append("Faster conversions have higher satisfaction")

        return insights

    def get_weekly_report(self, week_start: datetime) -> Dict[str, Any]:
        """
        Generate weekly feedback report.

        Args:
            week_start: Start of the week (Monday)

        Returns:
            Weekly report dict
        """
        week_end = week_start + timedelta(days=7)

        satisfaction = self.get_satisfaction_score(week_start, week_end)
        bugs = self.get_bug_summary(week_start, week_end)
        features = self.get_feature_request_summary(week_start, week_end)
        feedback_by_type = self.get_feedback_by_type(week_start, week_end)

        return {
            "period": {
                "start": week_start.isoformat(),
                "end": week_end.isoformat(),
            },
            "satisfaction": satisfaction,
            "bugs": bugs,
            "feature_requests": features,
            "feedback_by_type": feedback_by_type,
            "total_feedback": sum(feedback_by_type.values()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# Singleton instance
_feedback_analytics = None


def get_feedback_analytics() -> FeedbackAnalyticsService:
    """Get or create feedback analytics singleton."""
    global _feedback_analytics
    if _feedback_analytics is None:
        _feedback_analytics = FeedbackAnalyticsService()
    return _feedback_analytics
