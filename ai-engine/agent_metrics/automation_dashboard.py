"""
Automation Dashboard for real-time analytics
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from .automation_metrics import automation_metrics, AutomationMetrics
from .bottleneck_detector import bottleneck_detector, BottleneckDetector
from .trend_analyzer import trend_analyzer, TrendAnalyzer

logger = logging.getLogger(__name__)


class AutomationDashboard:
    """
    Real-time automation analytics dashboard.
    
    Features:
    - Unified view of all automation metrics
    - Real-time updates via get_realtime_update()
    - Integration with existing metrics system
    - Alert generation based on thresholds
    - Export functionality (JSON, CSV)
    """
    
    # Alert thresholds
    SUCCESS_RATE_WARNING = 0.80
    SUCCESS_RATE_CRITICAL = 0.60
    PROCESSING_TIME_WARNING = 60.0  # seconds
    PROCESSING_TIME_CRITICAL = 120.0
    AUTO_RECOVERY_WARNING = 0.70
    AUTO_RECOVERY_CRITICAL = 0.50
    
    def __init__(
        self,
        metrics: Optional[AutomationMetrics] = None,
        bottleneck_detector: Optional[BottleneckDetector] = None,
        trend_analyzer: Optional[TrendAnalyzer] = None,
    ):
        """
        Initialize the automation dashboard.
        
        Args:
            metrics: Automation metrics instance (uses singleton if not provided)
            bottleneck_detector: Bottleneck detector instance
            trend_analyzer: Trend analyzer instance
        """
        # Use provided instances or fall back to singletons
        self._metrics = metrics
        self._bottleneck_detector = bottleneck_detector
        self._trend_analyzer = trend_analyzer
        self._active_conversions = 0
        self._lock = asyncio.Lock()
        
        # Lazy initialization of singletons on first access
        self._metrics_initialized = metrics is not None
        self._bottleneck_initialized = bottleneck_detector is not None
        self._trend_initialized = trend_analyzer is not None
    
    @property
    def _metrics_instance(self) -> AutomationMetrics:
        """Get metrics instance with lazy initialization."""
        if self._metrics is None:
            from .automation_metrics import automation_metrics
            self._metrics = automation_metrics
        return self._metrics
    
    @property
    def _bottleneck_instance(self) -> BottleneckDetector:
        """Get bottleneck detector instance with lazy initialization."""
        if self._bottleneck_detector is None:
            from .bottleneck_detector import bottleneck_detector
            self._bottleneck_detector = bottleneck_detector
        return self._bottleneck_detector
    
    @property
    def _trend_instance(self) -> TrendAnalyzer:
        """Get trend analyzer instance with lazy initialization."""
        if self._trend_analyzer is None:
            from .trend_analyzer import trend_analyzer
            self._trend_analyzer = trend_analyzer
        return self._trend_analyzer
    
    async def start_conversion(self, conversion_id: str) -> None:
        """
        Mark start of a conversion.
        
        Args:
            conversion_id: Unique conversion identifier
        """
        async with self._lock:
            self._active_conversions += 1
        await self._bottleneck_instance.start_conversion(conversion_id)
    
    async def end_conversion(
        self,
        conversion_id: str,
        success: bool,
        mode: str,
        processing_time: float,
        error_type: Optional[str] = None,
        auto_recovered: bool = False,
    ) -> None:
        """
        Mark end of a conversion and record metrics.
        
        Args:
            conversion_id: Unique conversion identifier
            success: Whether the conversion succeeded
            mode: Conversion mode
            processing_time: Time taken in seconds
            error_type: Error type if failed
            auto_recovered: Whether error was auto-recovered
        """
        async with self._lock:
            self._active_conversions = max(0, self._active_conversions - 1)
        
        # Record metrics
        await self._metrics_instance.record_conversion(
            success=success,
            mode=mode,
            processing_time=processing_time,
            error_type=error_type,
            auto_recovered=auto_recovered,
        )
        
        # Get stage times and record bottleneck data
        stages = await self._bottleneck_instance.end_conversion(conversion_id)
        if stages:
            for stage, duration in stages.items():
                await self._bottleneck_instance.record_stage_time(
                    conversion_id=conversion_id,
                    stage=stage,
                    duration=duration,
                )
        
        # Record trend snapshot
        await self._trend_instance.record_snapshot({
            "success_rate": self._metrics_instance.get_success_rate(),
            "avg_processing_time": self._metrics_instance.get_avg_processing_time(),
            "auto_recovery_rate": self._metrics_instance.get_auto_recovery_rate(),
        })
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get all dashboard data in a single query.
        
        Returns:
            Complete dashboard data
        """
        return {
            "overview": {
                "total_conversions": self._metrics_instance._metrics["total_conversions"],
                "successful_conversions": self._metrics_instance._metrics["successful_conversions"],
                "failed_conversions": self._metrics_instance._metrics["failed_conversions"],
                "success_rate": self._metrics_instance.get_success_rate(),
                "auto_recovery_rate": self._metrics_instance.get_auto_recovery_rate(),
                "manual_intervention_rate": self._metrics_instance.get_manual_intervention_rate(),
                "avg_processing_time": self._metrics_instance.get_avg_processing_time(),
                "active_conversions": self._active_conversions,
            },
            "by_mode": self._metrics_instance.get_mode_success_rates(),
            "error_types": self._metrics_instance.get_top_error_types(10),
            "bottlenecks": self._bottleneck_instance.get_bottlenecks(),
            "stage_statistics": self._bottleneck_instance.get_stage_statistics(),
            "pipeline_time": self._bottleneck_instance.get_total_pipeline_time(),
            "alerts": self._get_active_alerts(),
            "trends": self._trend_instance.get_trend_summary("24h"),
            "timestamp": datetime.now().isoformat(),
        }
    
    def get_realtime_update(self) -> Dict[str, Any]:
        """
        Get lightweight update for WebSocket/polling.
        
        Returns:
            Lightweight metrics update
        """
        return {
            "success_rate": round(self._metrics_instance.get_success_rate(), 3),
            "active_conversions": self._active_conversions,
            "recent_bottlenecks": self._bottleneck_instance.get_bottlenecks()[:3],
            "alerts": self._get_active_alerts(),
            "timestamp": datetime.now().isoformat(),
        }
    
    def _get_active_alerts(self) -> list:
        """
        Get currently active alerts based on thresholds.
        
        Returns:
            List of active alerts
        """
        alerts = []
        
        success_rate = self._metrics_instance.get_success_rate()
        if success_rate < self.SUCCESS_RATE_CRITICAL:
            alerts.append({
                "level": "critical",
                "message": f"Success rate critically low: {success_rate:.1%}",
                "metric": "success_rate",
                "value": success_rate,
            })
        elif success_rate < self.SUCCESS_RATE_WARNING:
            alerts.append({
                "level": "warning",
                "message": f"Success rate below target: {success_rate:.1%}",
                "metric": "success_rate",
                "value": success_rate,
            })
        
        avg_time = self._metrics_instance.get_avg_processing_time()
        if avg_time > self.PROCESSING_TIME_CRITICAL:
            alerts.append({
                "level": "critical",
                "message": f"Processing time critically high: {avg_time:.1f}s",
                "metric": "avg_processing_time",
                "value": avg_time,
            })
        elif avg_time > self.PROCESSING_TIME_WARNING:
            alerts.append({
                "level": "warning",
                "message": f"Processing time above target: {avg_time:.1f}s",
                "metric": "avg_processing_time",
                "value": avg_time,
            })
        
        auto_recovery = self._metrics_instance.get_auto_recovery_rate()
        if auto_recovery < self.AUTO_RECOVERY_CRITICAL:
            alerts.append({
                "level": "critical",
                "message": f"Auto-recovery rate critically low: {auto_recovery:.1%}",
                "metric": "auto_recovery_rate",
                "value": auto_recovery,
            })
        elif auto_recovery < self.AUTO_RECOVERY_WARNING:
            alerts.append({
                "level": "warning",
                "message": f"Auto-recovery rate below target: {auto_recovery:.1%}",
                "metric": "auto_recovery_rate",
                "value": auto_recovery,
            })
        
        # Add bottleneck alerts
        bottlenecks = self._bottleneck_instance.get_bottlenecks()
        for bottleneck in bottlenecks[:3]:
            if bottleneck["severity"] == "high":
                alerts.append({
                    "level": "warning",
                    "message": f"High latency in {bottleneck['stage']}: {bottleneck['avg_time']:.1f}s",
                    "metric": f"stage_{bottleneck['stage']}",
                    "value": bottleneck["avg_time"],
                })
        
        return alerts
    
    def export_json(self) -> str:
        """
        Export dashboard data as JSON string.
        
        Returns:
            JSON string of dashboard data
        """
        import json
        return json.dumps(self.get_dashboard_data(), indent=2)
    
    def export_csv(self) -> str:
        """
        Export metrics as CSV string.
        
        Returns:
            CSV string of metrics
        """
        data = self.get_dashboard_data()
        
        lines = ["metric,value"]
        
        # Overview metrics
        for key, value in data["overview"].items():
            lines.append(f"{key},{value}")
        
        # Mode success rates
        for mode, rate in data["by_mode"].items():
            lines.append(f"mode_{mode}_success_rate,{rate}")
        
        return "\n".join(lines)
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status.
        
        Returns:
            Health status dictionary
        """
        alerts = self._get_active_alerts()
        
        if any(a["level"] == "critical" for a in alerts):
            status = "critical"
        elif any(a["level"] == "warning" for a in alerts):
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "alerts": alerts,
            "success_rate": self._metrics_instance.get_success_rate(),
            "active_conversions": self._active_conversions,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def record_retry(self, success: bool) -> None:
        """
        Record a retry attempt.
        
        Args:
            success: Whether the retry succeeded
        """
        await self._metrics_instance.record_retry(success)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the dashboard.
        
        Returns:
            Summary dictionary
        """
        return {
            "metrics": self._metrics_instance.get_summary(),
            "bottlenecks": self._bottleneck_instance.get_summary(),
            "trends": self._trend_instance.get_summary(),
            "health": self.get_health_status(),
        }


# Singleton instance for global access
automation_dashboard = AutomationDashboard()
