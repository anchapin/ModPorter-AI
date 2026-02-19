"""
Alert Manager for performance and usage alerts
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents an alert"""
    alert_type: str
    severity: AlertSeverity
    message: str
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'alert_type': self.alert_type,
            'severity': self.severity.value,
            'message': self.message,
            'timestamp': datetime.fromtimestamp(self.timestamp).isoformat(),
            'data': self.data,
            'acknowledged': self.acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': datetime.fromtimestamp(self.acknowledged_at).isoformat() if self.acknowledged_at else None
        }


class AlertManager:
    """
    Thread-safe alert manager for performance and usage alerts.
    
    Features:
    - Multiple alert types (slow operations, memory, cost, errors)
    - Severity levels
    - Alert callbacks for notifications
    - Alert acknowledgment
    - Alert history
    """
    
    def __init__(
        self,
        max_alerts: int = 1000,
        slow_operation_threshold: float = 5.0,
        memory_warning_threshold: float = 500.0,
        memory_critical_threshold: float = 1000.0,
        cost_warning_threshold: float = 10.0,
        error_rate_threshold: float = 0.1
    ):
        """
        Initialize the alert manager.
        
        Args:
            max_alerts: Maximum number of alerts to keep in history
            slow_operation_threshold: Threshold in seconds for slow operation alerts
            memory_warning_threshold: Memory warning threshold in MB
            memory_critical_threshold: Memory critical threshold in MB
            cost_warning_threshold: Cost warning threshold in USD
            error_rate_threshold: Error rate threshold (0.0 to 1.0)
        """
        self._lock = threading.Lock()
        self._alerts: List[Alert] = []
        self._max_alerts = max_alerts
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Thresholds
        self._thresholds = {
            'slow_operation': slow_operation_threshold,
            'memory_warning': memory_warning_threshold,
            'memory_critical': memory_critical_threshold,
            'cost_warning': cost_warning_threshold,
            'error_rate': error_rate_threshold
        }
        
        # Alert counters for rate limiting
        self._alert_counts: Dict[str, List[float]] = defaultdict(list)
        self._rate_limit_window = 60.0  # 1 minute window
        self._rate_limit_max = 10  # Max alerts per type per window
    
    def create_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        data: Dict[str, Any] = None
    ) -> Optional[Alert]:
        """
        Create a new alert.
        
        Args:
            alert_type: Type of alert (e.g., 'slow_operation', 'memory', 'cost')
            severity: Alert severity level
            message: Alert message
            data: Additional data
            
        Returns:
            The created Alert or None if rate limited
        """
        # Rate limiting
        if not self._check_rate_limit(alert_type):
            logger.debug(f"Alert rate limited: {alert_type}")
            return None
        
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=time.time(),
            data=data or {}
        )
        
        with self._lock:
            self._alerts.append(alert)
            
            # Trim old alerts if needed
            if len(self._alerts) > self._max_alerts:
                self._alerts = self._alerts[-self._max_alerts:]
        
        # Log the alert
        log_msg = f"[{severity.value.upper()}] {alert_type}: {message}"
        if severity == AlertSeverity.CRITICAL:
            logger.critical(log_msg)
        elif severity == AlertSeverity.ERROR:
            logger.error(log_msg)
        elif severity == AlertSeverity.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        # Trigger callbacks
        self._trigger_callbacks(alert)
        
        return alert
    
    def alert_slow_operation(self, operation: str, duration: float, metadata: Dict = None):
        """Create a slow operation alert"""
        threshold = self._thresholds['slow_operation']
        severity = AlertSeverity.WARNING if duration < threshold * 2 else AlertSeverity.ERROR
        
        return self.create_alert(
            alert_type='slow_operation',
            severity=severity,
            message=f"Slow operation detected: {operation} took {duration:.2f}s (threshold: {threshold}s)",
            data={
                'operation': operation,
                'duration': duration,
                'threshold': threshold,
                **(metadata or {})
            }
        )
    
    def alert_memory_usage(self, current_mb: float, threshold_type: str = 'warning'):
        """Create a memory usage alert"""
        threshold_key = f'memory_{threshold_type}'
        threshold = self._thresholds[threshold_key]
        severity = AlertSeverity.WARNING if threshold_type == 'warning' else AlertSeverity.CRITICAL
        
        return self.create_alert(
            alert_type='memory_usage',
            severity=severity,
            message=f"Memory usage {threshold_type}: {current_mb:.1f}MB (threshold: {threshold}MB)",
            data={
                'current_mb': current_mb,
                'threshold_type': threshold_type,
                'threshold': threshold
            }
        )
    
    def alert_cost_threshold(self, total_cost: float, threshold: float = None):
        """Create a cost threshold alert"""
        threshold = threshold or self._thresholds['cost_warning']
        
        return self.create_alert(
            alert_type='cost_threshold',
            severity=AlertSeverity.WARNING,
            message=f"Cost threshold exceeded: ${total_cost:.2f} (threshold: ${threshold:.2f})",
            data={
                'total_cost': total_cost,
                'threshold': threshold
            }
        )
    
    def alert_error_rate(self, error_rate: float, operation: str = None):
        """Create an error rate alert"""
        threshold = self._thresholds['error_rate']
        
        return self.create_alert(
            alert_type='error_rate',
            severity=AlertSeverity.ERROR,
            message=f"High error rate detected: {error_rate*100:.1f}% (threshold: {threshold*100:.1f}%)",
            data={
                'error_rate': error_rate,
                'threshold': threshold,
                'operation': operation
            }
        )
    
    def alert_llm_failure(self, model: str, error: str, provider: str = None):
        """Create an LLM failure alert"""
        return self.create_alert(
            alert_type='llm_failure',
            severity=AlertSeverity.ERROR,
            message=f"LLM API failure: {model} - {error}",
            data={
                'model': model,
                'provider': provider,
                'error': error
            }
        )
    
    def alert_custom(self, alert_type: str, severity: AlertSeverity, message: str, data: Dict = None):
        """Create a custom alert"""
        return self.create_alert(alert_type, severity, message, data)
    
    def acknowledge_alert(self, alert_index: int, acknowledged_by: str = None) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_index: Index of the alert in the history
            acknowledged_by: Who acknowledged the alert
            
        Returns:
            True if successful, False if alert not found
        """
        with self._lock:
            if 0 <= alert_index < len(self._alerts):
                alert = self._alerts[alert_index]
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = time.time()
                return True
            return False
    
    def get_alerts(
        self,
        severity: AlertSeverity = None,
        alert_type: str = None,
        unacknowledged_only: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get alerts with optional filtering.
        
        Args:
            severity: Filter by severity
            alert_type: Filter by alert type
            unacknowledged_only: Only return unacknowledged alerts
            limit: Maximum number of alerts to return
            
        Returns:
            List of alert dictionaries
        """
        with self._lock:
            alerts = self._alerts.copy()
        
        # Apply filters
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        
        # Sort by timestamp (newest first) and limit
        alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
        
        return [a.to_dict() for a in alerts]
    
    def get_alert_summary(self) -> Dict:
        """Get a summary of alerts"""
        with self._lock:
            alerts = self._alerts.copy()
        
        total = len(alerts)
        if total == 0:
            return {
                'total_alerts': 0,
                'by_severity': {},
                'by_type': {},
                'unacknowledged': 0
            }
        
        by_severity = defaultdict(int)
        by_type = defaultdict(int)
        unacknowledged = 0
        
        for alert in alerts:
            by_severity[alert.severity.value] += 1
            by_type[alert.alert_type] += 1
            if not alert.acknowledged:
                unacknowledged += 1
        
        return {
            'total_alerts': total,
            'by_severity': dict(by_severity),
            'by_type': dict(by_type),
            'unacknowledged': unacknowledged
        }
    
    def add_callback(self, alert_type: str, callback: Callable):
        """
        Add a callback for a specific alert type.
        
        Args:
            alert_type: Alert type to listen for (or '*' for all)
            callback: Function to call with (alert: Alert) argument
        """
        self._callbacks[alert_type].append(callback)
    
    def remove_callback(self, alert_type: str, callback: Callable):
        """Remove a callback"""
        if callback in self._callbacks[alert_type]:
            self._callbacks[alert_type].remove(callback)
    
    def set_threshold(self, threshold_name: str, value: float):
        """Set a threshold value"""
        if threshold_name in self._thresholds:
            self._thresholds[threshold_name] = value
    
    def get_thresholds(self) -> Dict[str, float]:
        """Get all threshold values"""
        return self._thresholds.copy()
    
    def clear_alerts(self):
        """Clear all alerts"""
        with self._lock:
            self._alerts.clear()
            self._alert_counts.clear()
    
    def _check_rate_limit(self, alert_type: str) -> bool:
        """Check if an alert type is rate limited"""
        current_time = time.time()
        
        # Clean old entries
        self._alert_counts[alert_type] = [
            t for t in self._alert_counts[alert_type]
            if current_time - t < self._rate_limit_window
        ]
        
        # Check limit
        if len(self._alert_counts[alert_type]) >= self._rate_limit_max:
            return False
        
        # Add current time
        self._alert_counts[alert_type].append(current_time)
        return True
    
    def _trigger_callbacks(self, alert: Alert):
        """Trigger callbacks for an alert"""
        # Call type-specific callbacks
        for callback in self._callbacks.get(alert.alert_type, []):
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        # Call wildcard callbacks
        for callback in self._callbacks.get('*', []):
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")


# Global instance
alert_manager = AlertManager()


def configure_alerts(
    slow_operation_threshold: float = None,
    memory_warning_threshold: float = None,
    memory_critical_threshold: float = None,
    cost_warning_threshold: float = None,
    error_rate_threshold: float = None
):
    """
    Configure alert thresholds.
    
    Args:
        slow_operation_threshold: Threshold in seconds for slow operation alerts
        memory_warning_threshold: Memory warning threshold in MB
        memory_critical_threshold: Memory critical threshold in MB
        cost_warning_threshold: Cost warning threshold in USD
        error_rate_threshold: Error rate threshold (0.0 to 1.0)
    """
    if slow_operation_threshold is not None:
        alert_manager.set_threshold('slow_operation', slow_operation_threshold)
    if memory_warning_threshold is not None:
        alert_manager.set_threshold('memory_warning', memory_warning_threshold)
    if memory_critical_threshold is not None:
        alert_manager.set_threshold('memory_critical', memory_critical_threshold)
    if cost_warning_threshold is not None:
        alert_manager.set_threshold('cost_warning', cost_warning_threshold)
    if error_rate_threshold is not None:
        alert_manager.set_threshold('error_rate', error_rate_threshold)