"""
Automation Metrics Service

Service for tracking and calculating automation-related metrics during mod conversions.
Provides detailed metrics on automation rate, one-click conversions, auto-recovery success,
conversion time, mode classification accuracy, and user satisfaction.

Issue: GAP-2.5-06 - Automation Metrics Dashboard
"""

import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import time

logger = logging.getLogger(__name__)


# Target thresholds for automation metrics
TARGET_AUTOMATION_RATE = 95.0  # 95% of conversions without human intervention
TARGET_ONE_CLICK_RATE = 80.0  # 80% of conversions started with one click
TARGET_AUTO_RECOVERY_RATE = 80.0  # 80% of errors recovered automatically


@dataclass
class ConversionEvent:
    """Record of a single conversion event for metrics tracking."""
    
    conversion_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Automation metrics
    was_automated: bool = False  # True if no human intervention required
    was_one_click: bool = False  # True if started with single click
    # Time metrics
    upload_time: Optional[datetime] = None
    download_time: Optional[datetime] = None
    conversion_time_seconds: Optional[float] = None
    # Mode classification
    mode_classification_correct: Optional[bool] = None  # True if auto-classified mode matched user choice
    # Error recovery
    had_error: bool = False
    auto_recovered: bool = False  # True if error was recovered automatically
    # User satisfaction
    user_satisfaction_score: Optional[float] = None  # 1-5 scale
    
    @property
    def conversion_duration_seconds(self) -> Optional[float]:
        """Calculate conversion duration if both times are available."""
        if self.upload_time and self.download_time:
            return (self.download_time - self.upload_time).total_seconds()
        return self.conversion_time_seconds


@dataclass
class AutomationMetricsSnapshot:
    """Current snapshot of automation metrics."""
    
    # Calculated rates (percentages)
    automation_rate: float = 0.0
    one_click_rate: float = 0.0
    auto_recovery_rate: float = 0.0
    mode_classification_accuracy: float = 0.0
    
    # Averages
    avg_conversion_time_seconds: float = 0.0
    avg_user_satisfaction: float = 0.0
    
    # Counts
    total_conversions: int = 0
    automated_conversions: int = 0
    one_click_conversions: int = 0
    errors_total: int = 0
    auto_recovered_count: int = 0
    mode_classifications_total: int = 0
    mode_classifications_correct: int = 0
    satisfaction_scores_total: int = 0
    
    # Targets
    target_automation_rate: float = TARGET_AUTOMATION_RATE
    target_one_click_rate: float = TARGET_ONE_CLICK_RATE
    target_auto_recovery_rate: float = TARGET_AUTO_RECOVERY_RATE
    
    # Status indicators (True if target met)
    automation_target_met: bool = False
    one_click_target_met: bool = False
    auto_recovery_target_met: bool = False
    
    # Timestamp
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Time range
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


@dataclass
class AutomationMetricsHistoryPoint:
    """Single point in the metrics history."""
    
    timestamp: datetime
    automation_rate: float
    one_click_rate: float
    auto_recovery_rate: float
    avg_conversion_time_seconds: float
    mode_classification_accuracy: float
    avg_user_satisfaction: float
    total_conversions: int


class AutomationMetricsService:
    """
    Service for tracking and calculating automation metrics.
    
    This service provides:
    - Recording of conversion events with automation metadata
    - Calculation of current automation metrics
    - Historical tracking of metrics over time
    - Target comparison for goal tracking
    
    Thread-safe implementation using locks for concurrent access.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure single instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the metrics service."""
        if self._initialized:
            return
        
        self._events: List[ConversionEvent] = []
        self._history: List[AutomationMetricsHistoryPoint] = []
        self._lock = threading.Lock()
        
        # Configuration
        self._max_stored_events = 10000
        self._history_retention_days = 30
        
        # Calculate initial metrics
        self._initialized = True
        logger.info("AutomationMetricsService initialized")
    
    def record_conversion_event(
        self,
        conversion_id: str,
        was_automated: bool = False,
        was_one_click: bool = False,
        upload_time: Optional[datetime] = None,
        download_time: Optional[datetime] = None,
        conversion_time_seconds: Optional[float] = None,
        mode_classification_correct: Optional[bool] = None,
        had_error: bool = False,
        auto_recovered: bool = False,
        user_satisfaction_score: Optional[float] = None,
    ) -> ConversionEvent:
        """
        Record a conversion event with automation metrics.
        
        Args:
            conversion_id: Unique identifier for the conversion
            was_automated: Whether conversion completed without human intervention
            was_one_click: Whether conversion was started with single click
            upload_time: When the file was uploaded
            download_time: When the converted file was downloaded
            conversion_time_seconds: Manual override for conversion time
            mode_classification_correct: Whether auto mode classification was correct
            had_error: Whether an error occurred during conversion
            auto_recovered: Whether any error was recovered automatically
            user_satisfaction_score: User satisfaction score (1-5)
            
        Returns:
            The created ConversionEvent
        """
        event = ConversionEvent(
            conversion_id=conversion_id,
            was_automated=was_automated,
            was_one_click=was_one_click,
            upload_time=upload_time,
            download_time=download_time,
            conversion_time_seconds=conversion_time_seconds,
            mode_classification_correct=mode_classification_correct,
            had_error=had_error,
            auto_recovered=auto_recovered,
            user_satisfaction_score=user_satisfaction_score,
        )
        
        with self._lock:
            self._events.append(event)
            
            # Trim old events if over limit
            if len(self._events) > self._max_stored_events:
                self._events = self._events[-self._max_stored_events:]
        
        logger.debug(f"Recorded conversion event: {conversion_id}, automated={was_automated}")
        return event
    
    def get_current_metrics(
        self,
        period_hours: int = 24,
    ) -> AutomationMetricsSnapshot:
        """
        Get current automation metrics snapshot.
        
        Args:
            period_hours: Time period to calculate metrics for (default 24 hours)
            
        Returns:
            AutomationMetricsSnapshot with current metrics
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=period_hours)
        
        with self._lock:
            # Filter events within period
            recent_events = [e for e in self._events if e.timestamp >= cutoff]
            
            if not recent_events:
                return AutomationMetricsSnapshot(
                    period_start=cutoff,
                    period_end=datetime.now(timezone.utc),
                )
            
            # Calculate metrics
            total = len(recent_events)
            
            # Automation rate
            automated = sum(1 for e in recent_events if e.was_automated)
            automation_rate = (automated / total * 100) if total > 0 else 0.0
            
            # One-click rate
            one_click = sum(1 for e in recent_events if e.was_one_click)
            one_click_rate = (one_click / total * 100) if total > 0 else 0.0
            
            # Auto-recovery rate
            errors = [e for e in recent_events if e.had_error]
            auto_recovered = sum(1 for e in errors if e.auto_recovered)
            auto_recovery_rate = (auto_recovered / len(errors) * 100) if errors else 0.0
            
            # Mode classification accuracy
            classified = [e for e in recent_events if e.mode_classification_correct is not None]
            correct = sum(1 for e in classified if e.mode_classification_correct)
            mode_accuracy = (correct / len(classified) * 100) if classified else 0.0
            
            # Average conversion time
            times = [
                (e.download_time - e.upload_time).total_seconds()
                for e in recent_events
                if e.upload_time and e.download_time
            ]
            if times:
                times.extend([
                    e.conversion_time_seconds
                    for e in recent_events
                    if e.conversion_time_seconds is not None and not (e.upload_time and e.download_time)
                ])
            avg_conversion_time = (sum(times) / len(times)) if times else 0.0
            
            # Average user satisfaction
            scores = [e.user_satisfaction_score for e in recent_events if e.user_satisfaction_score is not None]
            avg_satisfaction = (sum(scores) / len(scores)) if scores else 0.0
            
            # Build snapshot
            snapshot = AutomationMetricsSnapshot(
                automation_rate=round(automation_rate, 2),
                one_click_rate=round(one_click_rate, 2),
                auto_recovery_rate=round(auto_recovery_rate, 2),
                mode_classification_accuracy=round(mode_accuracy, 2),
                avg_conversion_time_seconds=round(avg_conversion_time, 2),
                avg_user_satisfaction=round(avg_satisfaction, 2),
                total_conversions=total,
                automated_conversions=automated,
                one_click_conversions=one_click,
                errors_total=len(errors),
                auto_recovered_count=auto_recovered,
                mode_classifications_total=len(classified),
                mode_classifications_correct=correct,
                satisfaction_scores_total=len(scores),
                target_automation_rate=TARGET_AUTOMATION_RATE,
                target_one_click_rate=TARGET_ONE_CLICK_RATE,
                target_auto_recovery_rate=TARGET_AUTO_RECOVERY_RATE,
                automation_target_met=automation_rate >= TARGET_AUTOMATION_RATE,
                one_click_target_met=one_click_rate >= TARGET_ONE_CLICK_RATE,
                auto_recovery_target_met=auto_recovery_rate >= TARGET_AUTO_RECOVERY_RATE,
                calculated_at=datetime.now(timezone.utc),
                period_start=cutoff,
                period_end=datetime.now(timezone.utc),
            )
            
            return snapshot
    
    def get_dashboard_data(
        self,
        period_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get dashboard-ready data with metrics and status.
        
        Args:
            period_hours: Time period to calculate metrics for
            
        Returns:
            Dictionary with dashboard-ready metrics data
        """
        snapshot = self.get_current_metrics(period_hours=period_hours)
        
        # Determine overall status
        targets_met = sum([
            snapshot.automation_target_met,
            snapshot.one_click_target_met,
            snapshot.auto_recovery_target_met,
        ])
        
        if targets_met == 3:
            overall_status = "excellent"
        elif targets_met == 2:
            overall_status = "good"
        elif targets_met == 1:
            overall_status = "needs_improvement"
        else:
            overall_status = "critical"
        
        return {
            "metrics": {
                "automation_rate": {
                    "value": snapshot.automation_rate,
                    "target": snapshot.target_automation_rate,
                    "met": snapshot.automation_target_met,
                    "unit": "percent",
                },
                "one_click_rate": {
                    "value": snapshot.one_click_rate,
                    "target": snapshot.target_one_click_rate,
                    "met": snapshot.one_click_target_met,
                    "unit": "percent",
                },
                "auto_recovery_rate": {
                    "value": snapshot.auto_recovery_rate,
                    "target": snapshot.target_auto_recovery_rate,
                    "met": snapshot.auto_recovery_target_met,
                    "unit": "percent",
                },
                "avg_conversion_time_seconds": {
                    "value": snapshot.avg_conversion_time_seconds,
                    "unit": "seconds",
                },
                "mode_classification_accuracy": {
                    "value": snapshot.mode_classification_accuracy,
                    "unit": "percent",
                },
                "user_satisfaction": {
                    "value": snapshot.avg_user_satisfaction,
                    "unit": "score",
                    "max_score": 5.0,
                },
            },
            "summary": {
                "total_conversions": snapshot.total_conversions,
                "automated_conversions": snapshot.automated_conversions,
                "one_click_conversions": snapshot.one_click_conversions,
                "total_errors": snapshot.errors_total,
                "auto_recovered": snapshot.auto_recovered_count,
            },
            "status": {
                "overall": overall_status,
                "targets_met": targets_met,
                "total_targets": 3,
            },
            "period": {
                "start": snapshot.period_start.isoformat() if snapshot.period_start else None,
                "end": snapshot.period_end.isoformat() if snapshot.period_end else None,
                "hours": period_hours,
            },
            "calculated_at": snapshot.calculated_at.isoformat(),
        }
    
    def get_historical_data(
        self,
        days: int = 7,
        interval_hours: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get historical metrics data.
        
        Args:
            days: Number of days of history to retrieve
            interval_hours: Interval between data points in hours
            
        Returns:
            List of historical data points
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        with self._lock:
            # Filter historical points within range
            historical = [
                h for h in self._history
                if h.timestamp >= cutoff
            ]
        
        return [
            {
                "timestamp": h.timestamp.isoformat(),
                "automation_rate": h.automation_rate,
                "one_click_rate": h.one_click_rate,
                "auto_recovery_rate": h.auto_recovery_rate,
                "avg_conversion_time_seconds": h.avg_conversion_time_seconds,
                "mode_classification_accuracy": h.mode_classification_accuracy,
                "avg_user_satisfaction": h.avg_user_satisfaction,
                "total_conversions": h.total_conversions,
            }
            for h in historical
        ]
    
    def record_historical_snapshot(self) -> None:
        """
        Record current metrics to historical data.
        Should be called periodically (e.g., hourly) to build history.
        """
        snapshot = self.get_current_metrics(period_hours=1)
        
        point = AutomationMetricsHistoryPoint(
            timestamp=datetime.now(timezone.utc),
            automation_rate=snapshot.automation_rate,
            one_click_rate=snapshot.one_click_rate,
            auto_recovery_rate=snapshot.auto_recovery_rate,
            avg_conversion_time_seconds=snapshot.avg_conversion_time_seconds,
            mode_classification_accuracy=snapshot.mode_classification_accuracy,
            avg_user_satisfaction=snapshot.avg_user_satisfaction,
            total_conversions=snapshot.total_conversions,
        )
        
        with self._lock:
            self._history.append(point)
            
            # Clean old history
            cutoff = datetime.now(timezone.utc) - timedelta(days=self._history_retention_days)
            self._history = [h for h in self._history if h.timestamp >= cutoff]
        
        logger.debug(f"Recorded historical snapshot: {snapshot.total_conversions} conversions")
    
    def get_all_events(
        self,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all recorded conversion events.
        
        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip
            start_date: Filter events after this date
            end_date: Filter events before this date
            
        Returns:
            List of event dictionaries
        """
        with self._lock:
            events = self._events
            
            if start_date:
                events = [e for e in events if e.timestamp >= start_date]
            if end_date:
                events = [e for e in events if e.timestamp <= end_date]
            
            # Sort by timestamp descending
            events = sorted(events, key=lambda e: e.timestamp, reverse=True)
            
            # Apply pagination
            total = len(events)
            events = events[offset:offset + limit]
        
        return [
            {
                "conversion_id": e.conversion_id,
                "timestamp": e.timestamp.isoformat(),
                "was_automated": e.was_automated,
                "was_one_click": e.was_one_click,
                "conversion_time_seconds": e.conversion_duration_seconds,
                "mode_classification_correct": e.mode_classification_correct,
                "had_error": e.had_error,
                "auto_recovered": e.auto_recovered,
                "user_satisfaction_score": e.user_satisfaction_score,
            }
            for e in events
        ], total
    
    def reset_metrics(self) -> None:
        """
        Reset all stored metrics and history.
        Use with caution - typically only for testing.
        """
        with self._lock:
            self._events.clear()
            self._history.clear()
        logger.info("Automation metrics reset")


# Module-level convenience functions
_service: Optional[AutomationMetricsService] = None


def get_automation_metrics_service() -> AutomationMetricsService:
    """Get the singleton AutomationMetricsService instance."""
    global _service
    if _service is None:
        _service = AutomationMetricsService()
    return _service


def record_conversion_event(**kwargs) -> ConversionEvent:
    """Convenience function to record a conversion event."""
    return get_automation_metrics_service().record_conversion_event(**kwargs)


def get_current_metrics(period_hours: int = 24) -> AutomationMetricsSnapshot:
    """Convenience function to get current metrics."""
    return get_automation_metrics_service().get_current_metrics(period_hours=period_hours)


def get_dashboard_data(period_hours: int = 24) -> Dict[str, Any]:
    """Convenience function to get dashboard data."""
    return get_automation_metrics_service().get_dashboard_data(period_hours=period_hours)


def get_historical_data(days: int = 7, interval_hours: int = 1) -> List[Dict[str, Any]]:
    """Convenience function to get historical data."""
    return get_automation_metrics_service().get_historical_data(days=days, interval_hours=interval_hours)
