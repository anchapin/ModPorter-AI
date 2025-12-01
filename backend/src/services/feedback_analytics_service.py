"""
Comprehensive feedback analytics and reporting service.

This module handles:
- Feedback metrics and KPIs
- Trend analysis and insights
- User engagement analytics
- Quality metrics reporting
- Community health indicators
- Automated report generation
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc


class AnalyticsTimeRange(Enum):
    """Predefined time ranges for analytics."""

    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_QUARTER = "this_quarter"
    LAST_QUARTER = "last_quarter"
    THIS_YEAR = "this_year"


class ReportType(Enum):
    """Types of reports that can be generated."""

    COMMUNITY_HEALTH = "community_health"
    FEEDBACK_ANALYSIS = "feedback_analysis"
    USER_ENGAGEMENT = "user_engagement"
    QUALITY_METRICS = "quality_metrics"
    REPUTATION_ANALYSIS = "reputation_analysis"
    TREND_ANALYSIS = "trend_analysis"
    PERFORMANCE_SUMMARY = "performance_summary"


@dataclass
class AnalyticsQuery:
    """Analytics query configuration."""

    metric: str
    time_range: AnalyticsTimeRange
    filters: Optional[Dict[str, Any]] = None
    group_by: Optional[str] = None
    order_by: Optional[str] = None
    limit: Optional[int] = None


class FeedbackAnalyticsService:
    """Service for comprehensive feedback analytics and reporting."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_feedback_overview(
        self, time_range: AnalyticsTimeRange = AnalyticsTimeRange.LAST_7_DAYS
    ) -> Dict[str, Any]:
        """Get high-level feedback overview metrics."""
        try:
            start_date, end_date = self._get_time_range_dates(time_range)

            # Base feedback query
            select(FeedbackEntry).where(
                FeedbackEntry.created_at.between(start_date, end_date)
            )

            # Total feedback count
            result = await self.db.execute(
                select(func.count(FeedbackEntry.id)).where(
                    FeedbackEntry.created_at.between(start_date, end_date)
                )
            )
            total_feedback = result.scalar()

            # Feedback by type
            result = await self.db.execute(
                select(
                    FeedbackEntry.feedback_type,
                    func.count(FeedbackEntry.id).label("count"),
                )
                .where(FeedbackEntry.created_at.between(start_date, end_date))
                .group_by(FeedbackEntry.feedback_type)
            )
            feedback_by_type = {row.feedback_type: row.count for row in result.all()}

            # Feedback by status
            result = await self.db.execute(
                select(
                    FeedbackEntry.status, func.count(FeedbackEntry.id).label("count")
                )
                .where(FeedbackEntry.created_at.between(start_date, end_date))
                .group_by(FeedbackEntry.status)
            )
            feedback_by_status = {row.status: row.count for row in result.all()}

            # Engagement metrics
            result = await self.db.execute(
                select(
                    func.count(FeedbackVote.id).label("total_votes"),
                    func.count(func.distinct(FeedbackVote.user_id)).label(
                        "unique_voters"
                    ),
                )
                .join(FeedbackEntry, FeedbackVote.feedback_id == FeedbackEntry.id)
                .where(FeedbackEntry.created_at.between(start_date, end_date))
            )
            vote_stats = result.first()

            # Average response time (time to first vote)
            result = await self.db.execute(
                select(
                    func.avg(
                        func.extract(
                            "epoch", FeedbackVote.created_at - FeedbackEntry.created_at
                        )
                    ).label("avg_response_seconds")
                )
                .join(FeedbackVote, FeedbackEntry.id == FeedbackVote.feedback_id)
                .where(FeedbackEntry.created_at.between(start_date, end_date))
                .group_by(FeedbackEntry.id)
            )
            avg_response_data = result.all()
            avg_response_hours = (
                sum(row.avg_response_seconds or 0 for row in avg_response_data)
                / len(avg_response_data)
                / 3600
                if avg_response_data
                else 0
            )

            return {
                "time_range": time_range.value,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "summary": {
                    "total_feedback": total_feedback,
                    "total_votes": vote_stats.total_votes if vote_stats else 0,
                    "unique_voters": vote_stats.unique_voters if vote_stats else 0,
                    "average_response_hours": round(avg_response_hours, 2),
                },
                "feedback_by_type": feedback_by_type,
                "feedback_by_status": feedback_by_status,
                "engagement_rate": (
                    (vote_stats.total_votes / total_feedback * 100)
                    if total_feedback > 0
                    else 0
                ),
            }

        except Exception as e:
            logger.error(f"Error getting feedback overview: {str(e)}")
            raise

    async def get_user_engagement_metrics(
        self, time_range: AnalyticsTimeRange = AnalyticsTimeRange.LAST_30_DAYS
    ) -> Dict[str, Any]:
        """Get detailed user engagement metrics."""
        try:
            start_date, end_date = self._get_time_range_dates(time_range)

            metrics = {
                "time_range": time_range.value,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "submission_metrics": {},
                "voting_metrics": {},
                "user_activity": {},
                "retention_metrics": {},
            }

            # Submission metrics
            result = await self.db.execute(
                select(
                    func.count(func.distinct(FeedbackEntry.user_id)).label(
                        "unique_submitters"
                    ),
                    func.count(FeedbackEntry.id).label("total_submissions"),
                    func.avg(
                        func.count(FeedbackEntry.id).over(
                            partition_by=FeedbackEntry.user_id
                        )
                    ).label("avg_submissions_per_user"),
                ).where(FeedbackEntry.created_at.between(start_date, end_date))
            )
            submission_stats = result.first()
            metrics["submission_metrics"] = {
                "unique_submitters": submission_stats.unique_submitters,
                "total_submissions": submission_stats.total_submissions,
                "avg_submissions_per_user": round(
                    submission_stats.avg_submissions_per_user or 0, 2
                ),
            }

            # Voting metrics
            result = await self.db.execute(
                select(
                    func.count(func.distinct(FeedbackVote.user_id)).label(
                        "unique_voters"
                    ),
                    func.count(FeedbackVote.id).label("total_votes"),
                    func.avg(
                        func.count(FeedbackVote.id).over(
                            partition_by=FeedbackVote.user_id
                        )
                    ).label("avg_votes_per_user"),
                )
                .join(FeedbackEntry, FeedbackVote.feedback_id == FeedbackEntry.id)
                .where(FeedbackEntry.created_at.between(start_date, end_date))
            )
            voting_stats = result.first()
            metrics["voting_metrics"] = {
                "unique_voters": voting_stats.unique_voters,
                "total_votes": voting_stats.total_votes,
                "avg_votes_per_user": round(voting_stats.avg_votes_per_user or 0, 2),
            }

            # User activity patterns (daily breakdown)
            result = await self.db.execute(
                select(
                    func.date(FeedbackEntry.created_at).label("date"),
                    func.count(FeedbackEntry.id).label("submissions"),
                    func.count(func.distinct(FeedbackEntry.user_id)).label(
                        "active_users"
                    ),
                )
                .where(FeedbackEntry.created_at.between(start_date, end_date))
                .group_by(func.date(FeedbackEntry.created_at))
                .order_by(func.date(FeedbackEntry.created_at))
            )
            daily_activity = [
                {
                    "date": row.date.isoformat(),
                    "submissions": row.submissions,
                    "active_users": row.active_users,
                }
                for row in result.all()
            ]
            metrics["user_activity"]["daily_patterns"] = daily_activity

            # User retention (users who returned after first submission)
            result = await self.db.execute(
                select(
                    func.count(func.distinct(FeedbackEntry.user_id)).label(
                        "total_users"
                    ),
                    func.count(
                        func.distinct(
                            func.case(
                                (
                                    func.count(FeedbackEntry.id) > 1,
                                    FeedbackEntry.user_id,
                                )
                            )
                        )
                    ).label("returning_users"),
                )
                .where(FeedbackEntry.created_at.between(start_date, end_date))
                .group_by(FeedbackEntry.user_id)
            )
            retention_data = result.all()
            total_users = len(retention_data)
            returning_users = len(
                [row for row in retention_data if row.total_users > 1]
            )

            metrics["retention_metrics"] = {
                "total_users": total_users,
                "returning_users": returning_users,
                "retention_rate": round((returning_users / total_users * 100), 2)
                if total_users > 0
                else 0,
            }

            return metrics

        except Exception as e:
            logger.error(f"Error getting user engagement metrics: {str(e)}")
            raise

    async def get_quality_analysis(
        self, time_range: AnalyticsTimeRange = AnalyticsTimeRange.LAST_30_DAYS
    ) -> Dict[str, Any]:
        """Get comprehensive quality analysis metrics."""
        try:
            start_date, end_date = self._get_time_range_dates(time_range)

            # Quality assessment metrics
            result = await self.db.execute(
                select(
                    func.count(QualityAssessment.id).label("total_assessments"),
                    func.avg(QualityAssessment.quality_score).label(
                        "avg_quality_score"
                    ),
                    func.count(func.distinct(QualityAssessment.assessor_type)).label(
                        "assessor_types"
                    ),
                ).where(QualityAssessment.created_at.between(start_date, end_date))
            )
            quality_stats = result.first()

            # Quality grade distribution
            result = await self.db.execute(
                select(
                    QualityAssessment.quality_grade,
                    func.count(QualityAssessment.id).label("count"),
                )
                .where(QualityAssessment.created_at.between(start_date, end_date))
                .group_by(QualityAssessment.quality_grade)
            )
            grade_distribution = {row.quality_grade: row.count for row in result.all()}

            # Most common quality issues
            result = await self.db.execute(
                select(QualityAssessment.issues_detected)
                .where(QualityAssessment.created_at.between(start_date, end_date))
                .where(QualityAssessment.issues_detected.isnot(None))
                .where(func.array_length(QualityAssessment.issues_detected, 1) > 0)
            )
            all_issues = []
            for row in result.all():
                issues = row.issues_detected or []
                all_issues.extend([issue.get("type", "unknown") for issue in issues])

            # Count issue types
            from collections import Counter

            issue_counts = Counter(all_issues)
            common_issues = dict(issue_counts.most_common(10))

            # Auto-action effectiveness
            result = await self.db.execute(
                select(
                    QualityAssessment.auto_actions,
                    QualityAssessment.reviewed_by_human,
                    QualityAssessment.human_override_score.isnot(None).label(
                        "human_overridden"
                    ),
                ).where(QualityAssessment.created_at.between(start_date, end_date))
            )
            auto_action_data = result.all()

            auto_actions_taken = 0
            human_reviews_required = 0
            human_overrides = 0

            for row in auto_action_data:
                if row.auto_actions:
                    auto_actions_taken += len(row.auto_actions)
                if row.reviewed_by_human:
                    human_reviews_required += 1
                if row.human_overridden:
                    human_overrides += 1

            total_assessments = quality_stats.total_assessments or 0

            return {
                "time_range": time_range.value,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "summary": {
                    "total_assessments": total_assessments,
                    "average_quality_score": round(
                        float(quality_stats.avg_quality_score or 0), 2
                    ),
                    "assessor_types": quality_stats.assessor_types or 0,
                },
                "grade_distribution": grade_distribution,
                "common_issues": common_issues,
                "automation_metrics": {
                    "auto_actions_taken": auto_actions_taken,
                    "human_reviews_required": human_reviews_required,
                    "human_overrides": human_overrides,
                    "automation_effectiveness": round(
                        (
                            (total_assessments - human_reviews_required)
                            / total_assessments
                            * 100
                        ),
                        2,
                    )
                    if total_assessments > 0
                    else 0,
                    "override_rate": round(
                        (human_overrides / human_reviews_required * 100), 2
                    )
                    if human_reviews_required > 0
                    else 0,
                },
            }

        except Exception as e:
            logger.error(f"Error getting quality analysis: {str(e)}")
            raise

    async def get_trend_analysis(
        self,
        metric: str = "feedback_volume",
        time_range: AnalyticsTimeRange = AnalyticsTimeRange.LAST_90_DAYS,
    ) -> Dict[str, Any]:
        """Get trend analysis for specific metrics."""
        try:
            start_date, end_date = self._get_time_range_dates(time_range)

            trend_data = {
                "metric": metric,
                "time_range": time_range.value,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "daily_data": [],
                "trend_analysis": {},
                "insights": [],
            }

            if metric == "feedback_volume":
                # Daily feedback submission trends
                result = await self.db.execute(
                    select(
                        func.date(FeedbackEntry.created_at).label("date"),
                        func.count(FeedbackEntry.id).label("count"),
                        func.count(func.distinct(FeedbackEntry.user_id)).label(
                            "unique_users"
                        ),
                    )
                    .where(FeedbackEntry.created_at.between(start_date, end_date))
                    .group_by(func.date(FeedbackEntry.created_at))
                    .order_by(func.date(FeedbackEntry.created_at))
                )

                for row in result.all():
                    trend_data["daily_data"].append(
                        {
                            "date": row.date.isoformat(),
                            "value": row.count,
                            "unique_users": row.unique_users,
                        }
                    )

            elif metric == "quality_score":
                # Daily quality score trends
                result = await self.db.execute(
                    select(
                        func.date(QualityAssessment.created_at).label("date"),
                        func.avg(QualityAssessment.quality_score).label("avg_score"),
                        func.count(QualityAssessment.id).label("count"),
                    )
                    .where(QualityAssessment.created_at.between(start_date, end_date))
                    .group_by(func.date(QualityAssessment.created_at))
                    .order_by(func.date(QualityAssessment.created_at))
                )

                for row in result.all():
                    trend_data["daily_data"].append(
                        {
                            "date": row.date.isoformat(),
                            "value": round(float(row.avg_score), 2),
                            "count": row.count,
                        }
                    )

            elif metric == "user_engagement":
                # Daily user engagement trends (votes per user)
                result = await self.db.execute(
                    select(
                        func.date(FeedbackVote.created_at).label("date"),
                        func.count(FeedbackVote.id).label("total_votes"),
                        func.count(func.distinct(FeedbackVote.user_id)).label(
                            "unique_voters"
                        ),
                    )
                    .where(FeedbackVote.created_at.between(start_date, end_date))
                    .group_by(func.date(FeedbackVote.created_at))
                    .order_by(func.date(FeedbackVote.created_at))
                )

                for row in result.all():
                    votes_per_user = (
                        row.total_votes / row.unique_voters
                        if row.unique_voters > 0
                        else 0
                    )
                    trend_data["daily_data"].append(
                        {
                            "date": row.date.isoformat(),
                            "value": round(votes_per_user, 2),
                            "total_votes": row.total_votes,
                            "unique_voters": row.unique_voters,
                        }
                    )

            # Calculate trend analysis
            if len(trend_data["daily_data"]) >= 2:
                values = [day["value"] for day in trend_data["daily_data"]]
                trend_data["trend_analysis"] = self._calculate_trend_metrics(values)

            # Generate insights
            trend_data["insights"] = self._generate_trend_insights(trend_data)

            return trend_data

        except Exception as e:
            logger.error(f"Error getting trend analysis: {str(e)}")
            raise

    async def get_top_contributors(
        self,
        time_range: AnalyticsTimeRange = AnalyticsTimeRange.LAST_30_DAYS,
        limit: int = 20,
        metric: str = "reputation",
    ) -> List[Dict[str, Any]]:
        """Get top contributors based on various metrics."""
        try:
            start_date, end_date = self._get_time_range_dates(time_range)

            contributors = []

            if metric == "reputation":
                # Top by reputation score
                result = await self.db.execute(
                    select(
                        UserReputation.user_id,
                        User.username,
                        UserReputation.reputation_score,
                        UserReputation.level,
                        func.count(FeedbackEntry.id).label("feedback_count"),
                    )
                    .join(User, UserReputation.user_id == User.id)
                    .join(
                        FeedbackEntry, UserReputation.user_id == FeedbackEntry.user_id
                    )
                    .where(FeedbackEntry.created_at.between(start_date, end_date))
                    .group_by(
                        UserReputation.user_id,
                        User.username,
                        UserReputation.reputation_score,
                        UserReputation.level,
                    )
                    .order_by(desc(UserReputation.reputation_score))
                    .limit(limit)
                )

                for row in result.all():
                    contributors.append(
                        {
                            "user_id": row.user_id,
                            "username": row.username,
                            "score": float(row.reputation_score),
                            "level": row.level,
                            "feedback_count": row.feedback_count,
                            "metric_type": "reputation",
                        }
                    )

            elif metric == "feedback_volume":
                # Top by feedback submission count
                result = await self.db.execute(
                    select(
                        FeedbackEntry.user_id,
                        User.username,
                        func.count(FeedbackEntry.id).label("feedback_count"),
                        func.avg(FeedbackEntry.quality_score).label("avg_quality"),
                        func.sum(FeedbackEntry.helpful_count).label("total_helpful"),
                    )
                    .join(User, FeedbackEntry.user_id == User.id)
                    .where(FeedbackEntry.created_at.between(start_date, end_date))
                    .group_by(FeedbackEntry.user_id, User.username)
                    .order_by(desc(func.count(FeedbackEntry.id)))
                    .limit(limit)
                )

                for row in result.all():
                    contributors.append(
                        {
                            "user_id": row.user_id,
                            "username": row.username,
                            "feedback_count": row.feedback_count,
                            "average_quality": round(float(row.avg_quality), 2)
                            if row.avg_quality
                            else 0,
                            "total_helpful": row.total_helpful or 0,
                            "metric_type": "feedback_volume",
                        }
                    )

            elif metric == "helpfulness":
                # Top by helpful votes received
                result = await self.db.execute(
                    select(
                        FeedbackEntry.user_id,
                        User.username,
                        func.sum(FeedbackEntry.helpful_count).label("total_helpful"),
                        func.count(FeedbackEntry.id).label("feedback_count"),
                        func.avg(FeedbackEntry.quality_score).label("avg_quality"),
                    )
                    .join(User, FeedbackEntry.user_id == User.id)
                    .where(FeedbackEntry.created_at.between(start_date, end_date))
                    .group_by(FeedbackEntry.user_id, User.username)
                    .order_by(desc(func.sum(FeedbackEntry.helpful_count)))
                    .limit(limit)
                )

                for row in result.all():
                    contributors.append(
                        {
                            "user_id": row.user_id,
                            "username": row.username,
                            "total_helpful": row.total_helpful or 0,
                            "feedback_count": row.feedback_count,
                            "average_quality": round(float(row.avg_quality), 2)
                            if row.avg_quality
                            else 0,
                            "helpfulness_ratio": round(
                                (row.total_helpful or 0) / row.feedback_count, 2
                            )
                            if row.feedback_count > 0
                            else 0,
                            "metric_type": "helpfulness",
                        }
                    )

            return contributors

        except Exception as e:
            logger.error(f"Error getting top contributors: {str(e)}")
            raise

    async def generate_report(
        self,
        report_type: ReportType,
        time_range: AnalyticsTimeRange = AnalyticsTimeRange.LAST_30_DAYS,
        format_type: str = "json",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive reports."""
        try:
            report_data = {
                "report_type": report_type.value,
                "time_range": time_range.value,
                "generated_at": datetime.utcnow().isoformat(),
                "filters": filters or {},
            }

            if report_type == ReportType.COMMUNITY_HEALTH:
                report_data.update(
                    await self._generate_community_health_report(time_range)
                )

            elif report_type == ReportType.FEEDBACK_ANALYSIS:
                report_data.update(
                    await self._generate_feedback_analysis_report(time_range)
                )

            elif report_type == ReportType.USER_ENGAGEMENT:
                report_data.update(
                    await self._generate_user_engagement_report(time_range)
                )

            elif report_type == ReportType.QUALITY_METRICS:
                report_data.update(
                    await self._generate_quality_metrics_report(time_range)
                )

            elif report_type == ReportType.REPUTATION_ANALYSIS:
                report_data.update(
                    await self._generate_reputation_analysis_report(time_range)
                )

            elif report_type == ReportType.TREND_ANALYSIS:
                report_data.update(
                    await self._generate_trend_analysis_report(time_range)
                )

            elif report_type == ReportType.PERFORMANCE_SUMMARY:
                report_data.update(
                    await self._generate_performance_summary_report(time_range)
                )

            return report_data

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise

    def _get_time_range_dates(
        self, time_range: AnalyticsTimeRange
    ) -> Tuple[datetime, datetime]:
        """Calculate start and end dates for time range."""
        end_date = datetime.utcnow()

        if time_range == AnalyticsTimeRange.TODAY:
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == AnalyticsTimeRange.YESTERDAY:
            yesterday = end_date - timedelta(days=1)
            start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = yesterday.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
        elif time_range == AnalyticsTimeRange.LAST_7_DAYS:
            start_date = end_date - timedelta(days=7)
        elif time_range == AnalyticsTimeRange.LAST_30_DAYS:
            start_date = end_date - timedelta(days=30)
        elif time_range == AnalyticsTimeRange.LAST_90_DAYS:
            start_date = end_date - timedelta(days=90)
        elif time_range == AnalyticsTimeRange.THIS_MONTH:
            start_date = end_date.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
        elif time_range == AnalyticsTimeRange.LAST_MONTH:
            last_month = end_date.replace(day=1) - timedelta(days=1)
            start_date = last_month.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            end_date = last_month.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
        elif time_range == AnalyticsTimeRange.THIS_QUARTER:
            quarter = (end_date.month - 1) // 3 + 1
            start_date = end_date.replace(
                month=(quarter - 1) * 3 + 1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        elif time_range == AnalyticsTimeRange.THIS_YEAR:
            start_date = end_date.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        else:
            start_date = end_date - timedelta(days=30)  # Default to 30 days

        return start_date, end_date

    def _calculate_trend_metrics(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend metrics from time series data."""
        if len(values) < 2:
            return {}

        # Simple linear regression to find trend
        n = len(values)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)

        # Calculate percentage change
        if values[0] != 0:
            percentage_change = ((values[-1] - values[0]) / abs(values[0])) * 100
        else:
            percentage_change = 0

        # Determine trend direction
        if slope > 0.1:
            trend_direction = "increasing"
        elif slope < -0.1:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"

        return {
            "slope": round(slope, 4),
            "percentage_change": round(percentage_change, 2),
            "trend_direction": trend_direction,
            "volatility": round(
                (max(values) - min(values)) / (sum(values) / n) * 100, 2
            )
            if values
            else 0,
        }

    def _generate_trend_insights(self, trend_data: Dict[str, Any]) -> List[str]:
        """Generate insights from trend data."""
        insights = []

        if not trend_data.get("trend_analysis"):
            return insights

        analysis = trend_data["trend_analysis"]
        metric = trend_data["metric"]

        if analysis.get("trend_direction") == "increasing":
            if metric == "feedback_volume":
                insights.append(
                    "Feedback submission rate is increasing, showing growing community engagement."
                )
            elif metric == "quality_score":
                insights.append("Average feedback quality is improving over time.")
            elif metric == "user_engagement":
                insights.append("User engagement is trending upward.")
        elif analysis.get("trend_direction") == "decreasing":
            if metric == "feedback_volume":
                insights.append(
                    "Feedback submissions are declining - consider engagement strategies."
                )
            elif metric == "quality_score":
                insights.append(
                    "Feedback quality is declining - review quality control measures."
                )
            elif metric == "user_engagement":
                insights.append(
                    "User engagement is decreasing - investigate potential issues."
                )

        if analysis.get("volatility", 0) > 50:
            insights.append(
                f"High volatility detected in {metric} - inconsistent patterns."
            )

        return insights

    async def _generate_community_health_report(
        self, time_range: AnalyticsTimeRange
    ) -> Dict[str, Any]:
        """Generate community health report."""
        overview = await self.get_feedback_overview(time_range)
        engagement = await self.get_user_engagement_metrics(time_range)

        return {
            "overview": overview,
            "engagement": engagement,
            "health_score": self._calculate_health_score(overview, engagement),
        }

    async def _generate_feedback_analysis_report(
        self, time_range: AnalyticsTimeRange
    ) -> Dict[str, Any]:
        """Generate feedback analysis report."""
        overview = await self.get_feedback_overview(time_range)
        quality = await self.get_quality_analysis(time_range)
        top_contributors = await self.get_top_contributors(
            time_range, metric="feedback_volume"
        )

        return {
            "overview": overview,
            "quality_analysis": quality,
            "top_contributors": top_contributors[:10],
        }

    async def _generate_user_engagement_report(
        self, time_range: AnalyticsTimeRange
    ) -> Dict[str, Any]:
        """Generate user engagement report."""
        engagement = await self.get_user_engagement_metrics(time_range)
        voting_trends = await self.get_trend_analysis("user_engagement", time_range)

        return {"engagement_metrics": engagement, "voting_trends": voting_trends}

    async def _generate_quality_metrics_report(
        self, time_range: AnalyticsTimeRange
    ) -> Dict[str, Any]:
        """Generate quality metrics report."""
        quality = await self.get_quality_analysis(time_range)
        quality_trends = await self.get_trend_analysis("quality_score", time_range)

        return {"quality_analysis": quality, "quality_trends": quality_trends}

    async def _generate_reputation_analysis_report(
        self, time_range: AnalyticsTimeRange
    ) -> Dict[str, Any]:
        """Generate reputation analysis report."""
        start_date, end_date = self._get_time_range_dates(time_range)

        # Reputation distribution
        result = await self.db.execute(
            select(
                UserReputation.level,
                func.count(UserReputation.id).label("count"),
                func.avg(UserReputation.reputation_score).label("avg_score"),
            )
            .group_by(UserReputation.level)
            .order_by(desc(func.avg(UserReputation.reputation_score)))
        )
        reputation_distribution = [
            {
                "level": row.level,
                "user_count": row.count,
                "average_score": float(row.avg_score),
            }
            for row in result.all()
        ]

        # Reputation events in time range
        result = await self.db.execute(
            select(
                ReputationEvent.event_type,
                func.count(ReputationEvent.id).label("count"),
                func.avg(ReputationEvent.score_change).label("avg_change"),
            )
            .where(ReputationEvent.event_date >= start_date.date())
            .group_by(ReputationEvent.event_type)
        )
        events_summary = [
            {
                "event_type": row.event_type,
                "count": row.count,
                "average_change": float(row.avg_change) if row.avg_change else 0,
            }
            for row in result.all()
        ]

        return {
            "reputation_distribution": reputation_distribution,
            "events_summary": events_summary,
            "top_contributors": await self.get_top_contributors(
                time_range, metric="reputation"
            ),
        }

    async def _generate_trend_analysis_report(
        self, time_range: AnalyticsTimeRange
    ) -> Dict[str, Any]:
        """Generate comprehensive trend analysis report."""
        feedback_trends = await self.get_trend_analysis("feedback_volume", time_range)
        quality_trends = await self.get_trend_analysis("quality_score", time_range)
        engagement_trends = await self.get_trend_analysis("user_engagement", time_range)

        return {
            "feedback_trends": feedback_trends,
            "quality_trends": quality_trends,
            "engagement_trends": engagement_trends,
        }

    async def _generate_performance_summary_report(
        self, time_range: AnalyticsTimeRange
    ) -> Dict[str, Any]:
        """Generate performance summary report."""
        overview = await self.get_feedback_overview(time_range)
        engagement = await self.get_user_engagement_metrics(time_range)
        quality = await self.get_quality_analysis(time_range)

        return {
            "executive_summary": {
                "total_feedback": overview["summary"]["total_feedback"],
                "engagement_rate": overview["engagement_rate"],
                "average_quality": quality["summary"]["average_quality_score"],
                "active_users": engagement["submission_metrics"]["unique_submitters"],
            },
            "key_metrics": {
                "feedback_overview": overview,
                "engagement_metrics": engagement,
                "quality_metrics": quality,
            },
        }

    def _calculate_health_score(self, overview: Dict, engagement: Dict) -> float:
        """Calculate overall community health score."""
        try:
            score = 0.0

            # Volume component (30%)
            volume_score = min(overview["summary"]["total_feedback"] / 100, 1.0) * 30
            score += volume_score

            # Engagement component (35%)
            engagement_score = min(overview["engagement_rate"] / 20, 1.0) * 35
            score += engagement_score

            # Retention component (35%)
            retention_score = (
                min(engagement["retention_metrics"]["retention_rate"] / 50, 1.0) * 35
            )
            score += retention_score

            return round(score, 2)

        except Exception:
            return 0.0
