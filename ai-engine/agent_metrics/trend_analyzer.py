"""
Trend Analysis for automation metrics
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    Analyze trends in automation metrics over time.
    
    Features:
    - Track metrics over time (hourly/daily/weekly)
    - Identify improving/degrading trends
    - Detect anomalies using standard deviation
    - Generate automated reports
    - Provide actionable insights
    """
    
    def __init__(self, retention_days: int = 30):
        """
        Initialize the trend analyzer.
        
        Args:
            retention_days: Number of days to retain historical data
        """
        self._historical_data: List[Dict[str, Any]] = []
        self._retention_days = retention_days
        self._lock = asyncio.Lock()
    
    async def record_snapshot(
        self,
        metrics: Dict[str, Any],
    ) -> None:
        """
        Record a metrics snapshot with timestamp.
        
        Args:
            metrics: Dictionary of metric values
        """
        async with self._lock:
            self._historical_data.append({
                "timestamp": datetime.now(),
                "metrics": metrics.copy(),
            })
            self._cleanup_old_data()
    
    async def record_metric(
        self,
        metric_name: str,
        value: float,
    ) -> None:
        """
        Record a single metric value.
        
        Args:
            metric_name: Name of the metric
            value: Value of the metric
        """
        async with self._lock:
            self._historical_data.append({
                "timestamp": datetime.now(),
                "metrics": {metric_name: value},
            })
            self._cleanup_old_data()
    
    def _cleanup_old_data(self) -> None:
        """Remove data older than retention period."""
        cutoff = datetime.now() - timedelta(days=self._retention_days)
        self._historical_data = [
            s for s in self._historical_data
            if s["timestamp"] >= cutoff
        ]
    
    def _get_cutoff(self, period: str) -> datetime:
        """Get cutoff datetime for a period."""
        now = datetime.now()
        if period == "1h":
            return now - timedelta(hours=1)
        elif period == "24h":
            return now - timedelta(hours=24)
        elif period == "7d":
            return now - timedelta(days=7)
        elif period == "30d":
            return now - timedelta(days=30)
        return now - timedelta(hours=24)
    
    def get_metric_trend(
        self,
        metric_name: str,
        period: str = "24h",
    ) -> List[Dict[str, Any]]:
        """
        Get trend for a specific metric over period.
        
        Args:
            metric_name: Name of the metric
            period: Time period (1h, 24h, 7d, 30d)
            
        Returns:
            List of metric values over time
        """
        cutoff = self._get_cutoff(period)
        snapshots = [
            s for s in self._historical_data
            if s["timestamp"] >= cutoff and metric_name in s["metrics"]
        ]
        return [
            {
                "timestamp": s["timestamp"].isoformat(),
                "value": s["metrics"][metric_name],
            }
            for s in snapshots
        ]
    
    def get_success_rate_trend(
        self,
        period: str = "24h",
    ) -> List[Dict[str, Any]]:
        """
        Get success rate trend over period.
        
        Args:
            period: Time period
            
        Returns:
            List of success rate values over time
        """
        return self.get_metric_trend("success_rate", period)
    
    def get_processing_time_trend(
        self,
        period: str = "24h",
    ) -> List[Dict[str, Any]]:
        """
        Get processing time trend over period.
        
        Args:
            period: Time period
            
        Returns:
            List of processing time values over time
        """
        return self.get_metric_trend("avg_processing_time", period)
    
    def detect_anomalies(
        self,
        metric: str,
        threshold: float = 2.0,
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies using z-score method.
        
        Args:
            metric: Metric name to check
            threshold: Z-score threshold for anomaly detection
            
        Returns:
            List of detected anomalies
        """
        values = [s["metrics"].get(metric, 0) for s in self._historical_data if metric in s["metrics"]]
        if len(values) < 10:
            return []
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5
        
        if std == 0:
            return []
        
        anomalies = []
        for s in self._historical_data:
            if metric not in s["metrics"]:
                continue
            value = s["metrics"][metric]
            z_score = abs((value - mean) / std)
            if z_score > threshold:
                anomalies.append({
                    "timestamp": s["timestamp"].isoformat(),
                    "value": value,
                    "mean": mean,
                    "std": std,
                    "z_score": round(z_score, 2),
                    "deviation": round(value - mean, 3),
                    "direction": "above" if value > mean else "below",
                })
        
        return sorted(anomalies, key=lambda x: x["z_score"], reverse=True)
    
    def calculate_trend(
        self,
        metric: str,
        period: str = "24h",
    ) -> float:
        """
        Calculate trend direction (-1 to 1) for a metric.
        
        Args:
            metric: Metric name
            period: Time period
            
        Returns:
            Trend value (-1 = declining, 0 = stable, 1 = improving)
        """
        cutoff = self._get_cutoff(period)
        snapshots = [
            s for s in self._historical_data
            if s["timestamp"] >= cutoff and metric in s["metrics"]
        ]
        
        if len(snapshots) < 2:
            return 0.0
        
        # Split into first half and second half
        mid = len(snapshots) // 2
        first_half = [s["metrics"][metric] for s in snapshots[:mid]]
        second_half = [s["metrics"][metric] for s in snapshots[mid:]]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        # Avoid division by zero
        if first_avg == 0:
            return 0.0
        
        # Calculate percentage change
        change = (second_avg - first_avg) / first_avg
        
        # Clamp to -1 to 1
        return max(-1.0, min(1.0, change))
    
    def get_trend_summary(self, period: str = "24h") -> Dict[str, Any]:
        """
        Get trend summary for key metrics.
        
        Args:
            period: Time period
            
        Returns:
            Dictionary with trend information for all key metrics
        """
        metrics = ["success_rate", "avg_processing_time", "auto_recovery_rate"]
        trends = {}
        
        for metric in metrics:
            trend = self.calculate_trend(metric, period)
            trends[metric] = {
                "trend": round(trend, 3),
                "direction": "improving" if trend > 0.05 else "declining" if trend < -0.05 else "stable",
            }
        
        return trends
    
    def get_improvement_recommendations(self) -> List[str]:
        """
        Generate improvement recommendations based on trends.
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Check success rate trend
        success_trend = self.calculate_trend("success_rate", "7d")
        if success_trend < -0.05:
            recommendations.append(
                "⚠️ Success rate declining over the past week. "
                "Review recent failure patterns and error types."
            )
        
        # Check processing time trend
        time_trend = self.calculate_trend("avg_processing_time", "7d")
        if time_trend > 0.2:
            recommendations.append(
                "⚠️ Processing time increasing significantly. "
                "Consider scaling resources or optimizing the pipeline."
            )
        
        # Check auto-recovery rate
        recovery_trend = self.calculate_trend("auto_recovery_rate", "7d")
        if recovery_trend < -0.1:
            recommendations.append(
                "⚠️ Auto-recovery rate declining. "
                "Review error patterns and update recovery strategies."
            )
        
        # Check for anomalies
        success_anomalies = self.detect_anomalies("success_rate")
        if len(success_anomalies) > 5:
            recommendations.append(
                f"⚠️ Found {len(success_anomalies)} anomalies in success rate. "
                "Investigate outliers for root causes."
            )
        
        if not recommendations:
            recommendations.append(
                "✅ All metrics trending positively. Continue monitoring."
            )
        
        return recommendations
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive analytics report.
        
        Returns:
            Dictionary with report data
        """
        return {
            "generated_at": datetime.now().isoformat(),
            "period": "7d",
            "trends": self.get_trend_summary("7d"),
            "recommendations": self.get_improvement_recommendations(),
            "recent_anomalies": {
                "success_rate": self.detect_anomalies("success_rate")[:3],
                "processing_time": self.detect_anomalies("avg_processing_time")[:3],
            },
            "data_points": len(self._historical_data),
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a complete summary of the trend analyzer.
        
        Returns:
            Dictionary with summary data
        """
        return {
            "data_points": len(self._historical_data),
            "retention_days": self._retention_days,
            "metrics_tracked": list(set(
                metric
                for snapshot in self._historical_data
                for metric in snapshot["metrics"].keys()
            )),
            "oldest_data": (
                self._historical_data[0]["timestamp"].isoformat()
                if self._historical_data else None
            ),
            "newest_data": (
                self._historical_data[-1]["timestamp"].isoformat()
                if self._historical_data else None
            ),
        }
    
    def reset(self) -> None:
        """Reset all historical data."""
        self._historical_data.clear()


# Singleton instance for global access
trend_analyzer = TrendAnalyzer()
