"""
Graph Database Performance Monitor

This module provides real-time monitoring and alerting for graph database
operations to ensure they don't impact overall application performance.
"""

import time
import psutil
import threading
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from collections import defaultdict, deque
from dataclasses import dataclass, field
import json
from pathlib import Path
import os

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance measurement."""

    operation: str
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    memory_delta: float
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation": self.operation,
            "duration": self.duration,
            "memory_delta": self.memory_delta,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class OperationThresholds:
    """Performance thresholds for different operations."""

    max_duration: float
    max_memory_delta: float
    min_success_rate: float = 0.95
    alert_after_failures: int = 3


class GraphPerformanceMonitor:
    """Monitor and track graph database performance."""

    # Default thresholds for different operations
    DEFAULT_THRESHOLDS = {
        "node_creation": OperationThresholds(0.1, 10.0),  # 100ms, 10MB
        "batch_node_creation": OperationThresholds(2.0, 100.0),  # 2s, 100MB
        "relationship_creation": OperationThresholds(0.15, 5.0),  # 150ms, 5MB
        "batch_relationship_creation": OperationThresholds(3.0, 50.0),  # 3s, 50MB
        "search": OperationThresholds(0.5, 20.0),  # 500ms, 20MB
        "neighbors": OperationThresholds(1.0, 50.0),  # 1s, 50MB
        "traversal": OperationThresholds(2.0, 100.0),  # 2s, 100MB
        "validation_update": OperationThresholds(0.2, 5.0),  # 200ms, 5MB
        "delete": OperationThresholds(0.5, 20.0),  # 500ms, 20MB
    }

    def __init__(
        self,
        max_history: int = 10000,
        window_size: int = 100,
        alert_callback: Optional[Callable] = None,
        log_file: Optional[str] = None,
    ):
        """
        Initialize performance monitor.

        Args:
            max_history: Maximum number of metrics to keep in memory
            window_size: Size of rolling window for statistics
            alert_callback: Callback function for performance alerts
            log_file: Optional file to log metrics
        """
        self.metrics: List[PerformanceMetric] = []
        self.max_history = max_history
        self.window_size = window_size
        self.alert_callback = alert_callback
        self.log_file = log_file

        # Operation-specific data
        self.operation_metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()

        # Threading lock for thread safety
        self.lock = threading.Lock()

        # Statistics cache
        self._stats_cache: Dict[str, Any] = {}
        self._stats_cache_time = 0
        self._stats_cache_ttl = 5  # 5 seconds

        # Ensure log directory exists
        if self.log_file:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Graph performance monitor initialized")

    def start_operation(self, operation: str) -> Dict[str, Any]:
        """
        Start monitoring a new operation.

        Args:
            operation: Name of the operation being monitored

        Returns:
            Dict[str, Any]: Context data for end_operation
        """
        try:
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB

            return {
                "operation": operation,
                "start_time": time.time(),
                "memory_before": memory_before,
            }
        except Exception as e:
            logger.error(f"Error starting operation monitoring: {e}")
            return {
                "operation": operation,
                "start_time": time.time(),
                "memory_before": 0,
            }

    def end_operation(
        self,
        context: Dict[str, Any],
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> PerformanceMetric:
        """
        End monitoring an operation and record metrics.

        Args:
            context: Context from start_operation
            success: Whether the operation succeeded
            error_message: Error message if operation failed

        Returns:
            PerformanceMetric: The recorded metric
        """
        try:
            end_time = time.time()
            process = psutil.Process()
            memory_after = process.memory_info().rss / 1024 / 1024  # MB

            metric = PerformanceMetric(
                operation=context["operation"],
                start_time=context["start_time"],
                end_time=end_time,
                duration=end_time - context["start_time"],
                memory_before=context["memory_before"],
                memory_after=memory_after,
                memory_delta=memory_after - context["memory_before"],
                success=success,
                error_message=error_message,
            )

            # Record the metric
            with self.lock:
                self.metrics.append(metric)
                self.operation_metrics[metric.operation].append(metric)

                # Limit history size
                if len(self.metrics) > self.max_history:
                    self.metrics = self.metrics[-self.max_history :]

                # Update failure count
                if not success:
                    self.failure_counts[metric.operation] += 1
                else:
                    # Reset failure count on success
                    self.failure_counts[metric.operation] = 0

                # Invalidate stats cache
                self._stats_cache_time = 0

            # Check for performance issues
            self._check_thresholds(metric)

            # Log to file if configured
            if self.log_file:
                self._log_to_file(metric)

            return metric

        except Exception as e:
            logger.error(f"Error ending operation monitoring: {e}")
            # Return a minimal metric
            return PerformanceMetric(
                operation=context.get("operation", "unknown"),
                start_time=context.get("start_time", time.time()),
                end_time=time.time(),
                duration=0,
                memory_before=0,
                memory_after=0,
                memory_delta=0,
                success=success,
                error_message=error_message,
            )

    def _check_thresholds(self, metric: PerformanceMetric):
        """Check if metric exceeds performance thresholds."""
        thresholds = self.thresholds.get(metric.operation)
        if not thresholds:
            return

        alerts = []

        # Check duration
        if metric.duration > thresholds.max_duration:
            alerts.append(
                f"Duration {metric.duration:.3f}s exceeds threshold {thresholds.max_duration:.3f}s"
            )

        # Check memory delta
        if metric.memory_delta > thresholds.max_memory_delta:
            alerts.append(
                f"Memory delta {metric.memory_delta:.1f}MB exceeds threshold {thresholds.max_memory_delta:.1f}MB"
            )

        # Check success rate
        if self.failure_counts[metric.operation] >= thresholds.alert_after_failures:
            alerts.append(
                f"Operation failed {self.failure_counts[metric.operation]} times consecutively"
            )

        # Send alerts if any
        if alerts:
            alert_msg = f"Performance alert for {metric.operation}: " + "; ".join(
                alerts
            )
            self._send_alert(alert_msg, metric)

    def _send_alert(self, message: str, metric: PerformanceMetric):
        """Send performance alert."""
        logger.warning(message)

        if self.alert_callback:
            try:
                self.alert_callback(message, metric)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def _log_to_file(self, metric: PerformanceMetric):
        """Log metric to file."""
        try:
            with open(self.log_file, "a") as f:
                json.dump(metric.to_dict(), f)
                f.write("\n")
        except Exception as e:
            logger.error(f"Error writing to log file: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics for all operations."""
        current_time = time.time()

        # Return cached stats if still valid
        if (
            current_time - self._stats_cache_time < self._stats_cache_ttl
            and self._stats_cache
        ):
            return self._stats_cache

        with self.lock:
            stats = {
                "total_operations": len(self.metrics),
                "operations": {},
                "summary": {},
                "alerts": {},
            }

            # Calculate statistics for each operation
            for operation, metrics_deque in self.operation_metrics.items():
                if not metrics_deque:
                    continue

                durations = [m.duration for m in metrics_deque]
                memory_deltas = [m.memory_delta for m in metrics_deque]
                successes = [m for m in metrics_deque if m.success]

                stats["operations"][operation] = {
                    "count": len(metrics_deque),
                    "success_count": len(successes),
                    "success_rate": len(successes) / len(metrics_deque),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "avg_memory_delta": sum(memory_deltas) / len(memory_deltas),
                    "min_memory_delta": min(memory_deltas),
                    "max_memory_delta": max(memory_deltas),
                    "recent_failures": self.failure_counts[operation],
                }

                # Check if operation is currently problematic
                threshold = self.thresholds.get(operation)
                if threshold:
                    avg_duration = stats["operations"][operation]["avg_duration"]
                    avg_memory = stats["operations"][operation]["avg_memory_delta"]
                    success_rate = stats["operations"][operation]["success_rate"]

                    issues = []
                    if avg_duration > threshold.max_duration:
                        issues.append("slow_duration")
                    if avg_memory > threshold.max_memory_delta:
                        issues.append("high_memory")
                    if success_rate < threshold.min_success_rate:
                        issues.append("low_success_rate")
                    if self.failure_counts[operation] >= threshold.alert_after_failures:
                        issues.append("consecutive_failures")

                    if issues:
                        stats["alerts"][operation] = issues

            # Calculate summary statistics
            if self.metrics:
                all_durations = [m.duration for m in self.metrics]
                all_memory = [m.memory_delta for m in self.metrics]
                all_successes = [m for m in self.metrics if m.success]

                stats["summary"] = {
                    "total_duration": sum(all_durations),
                    "avg_duration": sum(all_durations) / len(all_durations),
                    "max_duration": max(all_durations),
                    "total_memory_delta": sum(all_memory),
                    "avg_memory_delta": sum(all_memory) / len(all_memory),
                    "max_memory_delta": max(all_memory),
                    "overall_success_rate": len(all_successes) / len(self.metrics),
                }

            # Cache the results
            self._stats_cache = stats
            self._stats_cache_time = current_time

            return stats

    def get_recent_metrics(
        self, operation: Optional[str] = None, count: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent performance metrics."""
        with self.lock:
            metrics = self.metrics[-count:]

            if operation:
                metrics = [m for m in metrics if m.operation == operation]

            return [m.to_dict() for m in metrics]

    def set_thresholds(self, operation: str, thresholds: OperationThresholds):
        """Set custom thresholds for an operation."""
        self.thresholds[operation] = thresholds
        logger.info(f"Updated thresholds for {operation}")

    def reset_failure_counts(self):
        """Reset failure counters for all operations."""
        with self.lock:
            self.failure_counts.clear()
        logger.info("Reset failure counts")

    def clear_history(self):
        """Clear all performance history."""
        with self.lock:
            self.metrics.clear()
            self.operation_metrics.clear()
            self.failure_counts.clear()
            self._stats_cache = {}
            self._stats_cache_time = 0
        logger.info("Cleared performance history")


# Global performance monitor instance
performance_monitor = GraphPerformanceMonitor(
    max_history=10000,
    window_size=100,
    log_file=os.getenv("GRAPH_PERFORMANCE_LOG", "logs/graph_performance.jsonl"),
)


def monitor_graph_operation(operation_name: str):
    """
    Decorator to automatically monitor graph database operations.

    Args:
        operation_name: Name of the operation being monitored

    Usage:
        @monitor_graph_operation("node_creation")
        def create_node(...):
            ...
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            context = performance_monitor.start_operation(operation_name)
            try:
                result = func(*args, **kwargs)
                performance_monitor.end_operation(context, success=True)
                return result
            except Exception as e:
                performance_monitor.end_operation(
                    context, success=False, error_message=str(e)
                )
                raise

        return wrapper

    return decorator


class GraphPerformanceMiddleware:
    """FastAPI middleware to monitor graph operations."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Only monitor API requests related to graph operations
        if scope["type"] == "http" and "/api/knowledge-graph" in scope["path"]:
            path_parts = scope["path"].split("/")

            # Determine operation type from path
            if "nodes" in path_parts:
                operation = (
                    "node_creation" if scope["method"] == "POST" else "node_query"
                )
            elif "relationships" in path_parts:
                operation = (
                    "relationship_creation"
                    if scope["method"] == "POST"
                    else "relationship_query"
                )
            elif "search" in path_parts:
                operation = "search"
            elif "visualization" in path_parts:
                operation = "visualization"
            else:
                operation = "other_graph"

            context = performance_monitor.start_operation(operation)

            try:
                await self.app(scope, receive, send)
                performance_monitor.end_operation(context, success=True)
            except Exception as e:
                performance_monitor.end_operation(
                    context, success=False, error_message=str(e)
                )
                raise
        else:
            await self.app(scope, receive, send)


# Example alert callback
def email_alert_callback(message: str, metric: PerformanceMetric):
    """Example callback for sending email alerts."""
    # Implementation would send email/SMS/etc.
    logger.critical(f"ALERT: {message}")

    # Here you could integrate with:
    # - Email services (SendGrid, AWS SES)
    # - Slack/webhook notifications
    # - PagerDuty alerts
    # - Custom monitoring systems
