"""
Automation Analytics System

Provides comprehensive analytics for the conversion automation system:
- Automation metrics dashboard
- Success rate tracking
- Mode distribution analysis
- Continuous improvement recommendations
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class ConversionMetric:
    """Single conversion metric record."""

    conversion_id: str
    timestamp: datetime
    mod_path: str
    mode: str
    success: bool
    duration_seconds: float
    automation_level: float  # 0.0 to 1.0 (1.0 = fully automated)
    manual_interventions: int = 0
    errors: List[str] = field(default_factory=list)
    user_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversion_id": self.conversion_id,
            "timestamp": self.timestamp.isoformat(),
            "mod_path": self.mod_path,
            "mode": self.mode,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "automation_level": self.automation_level,
            "manual_interventions": self.manual_interventions,
        }


@dataclass
class AutomationDashboard:
    """Dashboard data for automation metrics."""

    # Overall metrics
    total_conversions: int = 0
    successful_conversions: int = 0
    failed_conversions: int = 0
    automation_rate: float = 0.0  # 0.0 to 1.0

    # Time metrics
    avg_conversion_time: float = 0.0  # seconds
    total_time_saved: float = 0.0  # seconds

    # Mode distribution
    mode_distribution: Dict[str, int] = field(default_factory=dict)

    # Error metrics
    error_rate: float = 0.0
    top_errors: List[Dict[str, Any]] = field(default_factory=list)

    # Trends
    automation_trend: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_conversions": self.total_conversions,
            "successful_conversions": self.successful_conversions,
            "failed_conversions": self.failed_conversions,
            "success_rate": (
                self.successful_conversions / self.total_conversions
                if self.total_conversions > 0
                else 0
            ),
            "automation_rate": self.automation_rate,
            "avg_conversion_time_sec": self.avg_conversion_time,
            "total_time_saved_hours": self.total_time_saved / 3600,
            "mode_distribution": self.mode_distribution,
            "error_rate": self.error_rate,
        }


class AutomationMetricsCollector:
    """
    Collects and stores automation metrics.

    Features:
    - Real-time metric collection
    - Time-series storage
    - Aggregation functions
    """

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.metrics: List[ConversionMetric] = []
        self._lock = None  # Would use threading.Lock in production
        logger.info(f"AutomationMetricsCollector initialized (max_history={max_history})")

    def record_conversion(self, metric: ConversionMetric):
        """Record a conversion metric."""
        self.metrics.append(metric)

        # Trim history if needed
        if len(self.metrics) > self.max_history:
            self.metrics = self.metrics[-self.max_history :]

        logger.debug(f"Recorded conversion: {metric.conversion_id} (success={metric.success})")

    def get_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> List[ConversionMetric]:
        """Get metrics with optional filtering."""
        filtered = self.metrics

        if start_time:
            filtered = [m for m in filtered if m.timestamp >= start_time]
        if end_time:
            filtered = [m for m in filtered if m.timestamp <= end_time]
        if user_id:
            filtered = [m for m in filtered if m.user_id == user_id]
        if mode:
            filtered = [m for m in filtered if m.mode == mode]

        return filtered

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self.metrics:
            return {"total": 0}

        total = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.success)
        avg_duration = sum(m.duration_seconds for m in self.metrics) / total
        avg_automation = sum(m.automation_level for m in self.metrics) / total

        return {
            "total": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total,
            "avg_duration_sec": avg_duration,
            "avg_automation_level": avg_automation,
        }


class SuccessRateTracker:
    """
    Tracks success rates by various dimensions.

    Features:
    - Success rate by mode
    - Success rate by time period
    - Success rate by user
    - Trend analysis
    """

    def __init__(self):
        self.success_by_mode: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"success": 0, "total": 0}
        )
        self.success_by_day: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"success": 0, "total": 0}
        )
        self.success_by_user: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"success": 0, "total": 0}
        )
        logger.info("SuccessRateTracker initialized")

    def record_outcome(self, mode: str, success: bool, user_id: Optional[str] = None):
        """Record a conversion outcome."""
        # By mode
        self.success_by_mode[mode]["total"] += 1
        if success:
            self.success_by_mode[mode]["success"] += 1

        # By day
        day_key = datetime.now().strftime("%Y-%m-%d")
        self.success_by_day[day_key]["total"] += 1
        if success:
            self.success_by_day[day_key]["success"] += 1

        # By user
        if user_id:
            self.success_by_user[user_id]["total"] += 1
            if success:
                self.success_by_user[user_id]["success"] += 1

    def get_success_rate_by_mode(self) -> Dict[str, float]:
        """Get success rate by mode."""
        rates = {}
        for mode, counts in self.success_by_mode.items():
            if counts["total"] > 0:
                rates[mode] = counts["success"] / counts["total"]
        return rates

    def get_success_rate_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get success rate trend over recent days."""
        trend = []

        for i in range(days - 1, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            counts = self.success_by_day.get(date, {"success": 0, "total": 0})

            if counts["total"] > 0:
                trend.append(
                    {
                        "date": date,
                        "success_rate": counts["success"] / counts["total"],
                        "total": counts["total"],
                    }
                )

        return trend

    def get_overall_success_rate(self) -> float:
        """Get overall success rate."""
        total_success = sum(c["success"] for c in self.success_by_mode.values())
        total = sum(c["total"] for c in self.success_by_mode.values())
        return total_success / total if total > 0 else 0


class ModeDistributionAnalyzer:
    """
    Analyzes mode distribution and patterns.

    Features:
    - Mode distribution tracking
    - Mode performance comparison
    - Automation level by mode
    """

    def __init__(self):
        self.mode_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_duration": 0,
                "total_automation": 0,
                "success": 0,
            }
        )
        logger.info("ModeDistributionAnalyzer initialized")

    def record_conversion(self, mode: str, duration: float, automation_level: float, success: bool):
        """Record a conversion for mode analysis."""
        stats = self.mode_stats[mode]
        stats["count"] += 1
        stats["total_duration"] += duration
        stats["total_automation"] += automation_level
        if success:
            stats["success"] += 1

    def get_mode_distribution(self) -> Dict[str, int]:
        """Get distribution of conversions by mode."""
        return {mode: stats["count"] for mode, stats in self.mode_stats.items()}

    def get_mode_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics by mode."""
        performance = {}

        for mode, stats in self.mode_stats.items():
            count = stats["count"]
            if count > 0:
                performance[mode] = {
                    "count": count,
                    "avg_duration_sec": stats["total_duration"] / count,
                    "avg_automation_level": stats["total_automation"] / count,
                    "success_rate": stats["success"] / count,
                }

        return performance


class ImprovementRecommendationEngine:
    """
    Generates recommendations for continuous improvement.

    Features:
    - Bottleneck identification
    - Optimization suggestions
    - Trend-based recommendations
    """

    def __init__(self):
        self.recommendations: List[Dict[str, Any]] = []
        logger.info("ImprovementRecommendationEngine initialized")

    def analyze_and_recommend(
        self,
        dashboard: AutomationDashboard,
        mode_performance: Dict[str, Dict[str, Any]],
        success_trend: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate improvement recommendations."""
        recommendations = []

        # Check automation rate
        if dashboard.automation_rate < 0.95:
            recommendations.append(
                {
                    "category": "automation",
                    "priority": "high",
                    "issue": f"Automation rate is {dashboard.automation_rate:.0%} (target: 95%)",
                    "recommendation": "Review manual intervention patterns and create automation rules",
                    "impact": "Could save significant manual effort",
                }
            )

        # Check conversion time
        if dashboard.avg_conversion_time > 180:  # 3 minutes
            recommendations.append(
                {
                    "category": "performance",
                    "priority": "medium",
                    "issue": f"Average conversion time is {dashboard.avg_conversion_time:.0f}s",
                    "recommendation": "Optimize slow conversion steps or enable parallel processing",
                    "impact": "Faster conversions, higher throughput",
                }
            )

        # Check error rate
        if dashboard.error_rate > 0.10:  # 10%
            recommendations.append(
                {
                    "category": "reliability",
                    "priority": "high",
                    "issue": f"Error rate is {dashboard.error_rate:.0%}",
                    "recommendation": "Review top errors and implement error recovery",
                    "impact": "Fewer failed conversions",
                }
            )

        # Check mode-specific issues
        for mode, perf in mode_performance.items():
            if perf.get("success_rate", 1.0) < 0.80:
                recommendations.append(
                    {
                        "category": "mode_quality",
                        "priority": "medium",
                        "issue": f"{mode} mode has {perf['success_rate']:.0%} success rate",
                        "recommendation": f"Review {mode} mode conversion patterns and rules",
                        "impact": "Improved success rate for {mode} conversions",
                    }
                )

        # Check trend
        if len(success_trend) >= 7:
            recent_avg = sum(t["success_rate"] for t in success_trend[-3:]) / 3
            older_avg = sum(t["success_rate"] for t in success_trend[:3]) / 3

            if recent_avg < older_avg - 0.05:
                recommendations.append(
                    {
                        "category": "trend",
                        "priority": "high",
                        "issue": "Success rate declining over past week",
                        "recommendation": "Investigate recent changes that may have affected quality",
                        "impact": "Prevent further quality degradation",
                    }
                )

        self.recommendations = recommendations
        return recommendations

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get current recommendations."""
        return self.recommendations


class AutomationAnalyticsDashboard:
    """
    Main dashboard for automation analytics.

    Combines all analytics components:
    - Metrics collection
    - Success rate tracking
    - Mode analysis
    - Recommendations
    """

    def __init__(self):
        self.metrics_collector = AutomationMetricsCollector()
        self.success_tracker = SuccessRateTracker()
        self.mode_analyzer = ModeDistributionAnalyzer()
        self.recommendation_engine = ImprovementRecommendationEngine()
        logger.info("AutomationAnalyticsDashboard initialized")

    def record_conversion(
        self,
        conversion_id: str,
        mod_path: str,
        mode: str,
        success: bool,
        duration_seconds: float,
        automation_level: float,
        manual_interventions: int = 0,
        errors: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ):
        """Record a conversion for analytics."""
        metric = ConversionMetric(
            conversion_id=conversion_id,
            timestamp=datetime.now(),
            mod_path=mod_path,
            mode=mode,
            success=success,
            duration_seconds=duration_seconds,
            automation_level=automation_level,
            manual_interventions=manual_interventions,
            errors=errors or [],
            user_id=user_id,
        )

        # Record in all trackers
        self.metrics_collector.record_conversion(metric)
        self.success_tracker.record_outcome(mode, success, user_id)
        self.mode_analyzer.record_conversion(mode, duration_seconds, automation_level, success)

    def get_dashboard(self) -> AutomationDashboard:
        """Get current dashboard data."""
        dashboard = AutomationDashboard()

        # Get summary stats
        stats = self.metrics_collector.get_summary_stats()
        dashboard.total_conversions = stats.get("total", 0)
        dashboard.successful_conversions = stats.get("successful", 0)
        dashboard.failed_conversions = stats.get("failed", 0)
        dashboard.automation_rate = stats.get("avg_automation_level", 0)
        dashboard.avg_conversion_time = stats.get("avg_duration_sec", 0)

        # Mode distribution
        dashboard.mode_distribution = self.mode_analyzer.get_mode_distribution()

        # Error rate
        if dashboard.total_conversions > 0:
            dashboard.error_rate = dashboard.failed_conversions / dashboard.total_conversions

        # Success trend
        dashboard.automation_trend = self.success_tracker.get_success_rate_trend()

        return dashboard

    def get_full_analytics(self) -> Dict[str, Any]:
        """Get complete analytics data."""
        dashboard = self.get_dashboard()
        mode_performance = self.mode_analyzer.get_mode_performance()
        success_trend = self.success_tracker.get_success_rate_trend()
        recommendations = self.recommendation_engine.analyze_and_recommend(
            dashboard, mode_performance, success_trend
        )

        return {
            "dashboard": dashboard.to_dict(),
            "mode_performance": mode_performance,
            "success_trend": success_trend,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat(),
        }

    def export_report(self, format: str = "json") -> str:
        """Export analytics report."""
        analytics = self.get_full_analytics()

        if format == "json":
            return json.dumps(analytics, indent=2)
        else:
            # Simple text format
            lines = [
                "=" * 60,
                "AUTOMATION ANALYTICS REPORT",
                "=" * 60,
                f"Generated: {analytics['generated_at']}",
                "",
                "DASHBOARD",
                "-" * 40,
            ]

            for key, value in analytics["dashboard"].items():
                lines.append(f"  {key}: {value}")

            lines.extend(["", "RECOMMENDATIONS", "-" * 40])
            for rec in analytics["recommendations"]:
                lines.append(f"  [{rec['priority'].upper()}] {rec['issue']}")
                lines.append(f"    → {rec['recommendation']}")

            return "\n".join(lines)


# Convenience functions
_dashboard_instance: Optional[AutomationAnalyticsDashboard] = None


def get_analytics_dashboard() -> AutomationAnalyticsDashboard:
    """Get or create analytics dashboard instance."""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = AutomationAnalyticsDashboard()
    return _dashboard_instance


def record_conversion(
    conversion_id: str,
    mode: str,
    success: bool,
    duration_seconds: float,
    automation_level: float = 1.0,
) -> None:
    """Convenience function to record a conversion."""
    dashboard = get_analytics_dashboard()
    dashboard.record_conversion(
        conversion_id=conversion_id,
        mod_path=f"mod_{conversion_id}.jar",
        mode=mode,
        success=success,
        duration_seconds=duration_seconds,
        automation_level=automation_level,
    )


def get_automation_report() -> Dict[str, Any]:
    """Get current automation analytics report."""
    dashboard = get_analytics_dashboard()
    return dashboard.get_full_analytics()
