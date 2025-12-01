"""
Comprehensive Performance Monitoring and Adaptive Optimization System

This module provides real-time performance monitoring, bottleneck detection,
and adaptive optimization for the ModPorter conversion pipeline.
"""

import asyncio
import time
import psutil
import threading
from typing import Dict, List, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging
from contextlib import asynccontextmanager
from functools import wraps
import numpy as np
from sklearn.preprocessing import StandardScaler
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import statistics

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric data point"""

    timestamp: datetime
    operation_type: str
    operation_id: str
    duration_ms: float
    cpu_percent: float
    memory_mb: float
    db_connections: int
    cache_hit_rate: float
    queue_length: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration"""

    metric_name: str
    warning_threshold: float
    critical_threshold: float
    window_minutes: int = 5
    consecutive_violations: int = 3


@dataclass
class OptimizationAction:
    """Optimization action definition"""

    action_type: str
    description: str
    priority: int
    condition: str
    action_func: Callable
    cooldown_minutes: int = 10


class MetricsCollector:
    """High-performance metrics collection system"""

    def __init__(self, max_samples: int = 10000):
        self.metrics: deque[PerformanceMetric] = deque(maxlen=max_samples)
        self.operation_metrics: Dict[str, List[float]] = defaultdict(list)
        self.system_metrics = deque(maxlen=1000)
        self.lock = threading.RLock()
        self.last_collection = time.time()

    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric"""
        with self.lock:
            self.metrics.append(metric)
            self.operation_metrics[metric.operation_type].append(metric.duration_ms)

            # Keep only recent metrics for each operation type
            if len(self.operation_metrics[metric.operation_type]) > 1000:
                self.operation_metrics[metric.operation_type] = self.operation_metrics[
                    metric.operation_type
                ][-500:]

    def collect_system_metrics(self) -> Dict[str, float]:
        """Collect current system performance metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_mb": psutil.virtual_memory().used / 1024 / 1024,
            "disk_usage": psutil.disk_usage("/").percent
            if hasattr(psutil, "disk_usage")
            else 0,
            "network_io": sum(
                psutil.net_io_counters().bytes_sent, psutil.net_io_counters().bytes_recv
            ),
            "process_count": len(psutil.pids()),
            "timestamp": time.time(),
        }

    def get_operation_stats(
        self, operation_type: str, window_minutes: int = 5
    ) -> Dict[str, float]:
        """Get statistics for a specific operation type"""
        with self.lock:
            metrics = [
                m.duration_ms
                for m in self.metrics
                if m.operation_type == operation_type
                and m.timestamp > datetime.now() - timedelta(minutes=window_minutes)
            ]

            if not metrics:
                return {}

            return {
                "count": len(metrics),
                "avg_ms": statistics.mean(metrics),
                "median_ms": statistics.median(metrics),
                "p95_ms": np.percentile(metrics, 95),
                "p99_ms": np.percentile(metrics, 99),
                "min_ms": min(metrics),
                "max_ms": max(metrics),
                "std_dev": statistics.stdev(metrics) if len(metrics) > 1 else 0,
            }

    def get_trend_analysis(
        self, operation_type: str, window_minutes: int = 60
    ) -> Dict[str, float]:
        """Analyze performance trends over time"""
        with self.lock:
            metrics = sorted(
                [
                    (m.timestamp, m.duration_ms)
                    for m in self.metrics
                    if m.operation_type == operation_type
                    and m.timestamp > datetime.now() - timedelta(minutes=window_minutes)
                ]
            )

            if len(metrics) < 10:
                return {"trend": 0.0, "confidence": 0.0}

            times = np.array([(t - metrics[0][0]).total_seconds() for t, _ in metrics])
            durations = np.array([d for _, d in metrics])

            # Linear regression for trend
            coeffs = np.polyfit(times, durations, 1)
            trend_slope = coeffs[0]

            # Calculate R-squared for confidence
            y_pred = np.polyval(coeffs, times)
            ss_res = np.sum((durations - y_pred) ** 2)
            ss_tot = np.sum((durations - np.mean(durations)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            return {
                "trend": trend_slope,
                "confidence": r_squared,
                "samples": len(metrics),
            }


class AdaptiveOptimizer:
    """Adaptive optimization engine"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.optimization_actions: List[OptimizationAction] = []
        self.action_history: deque = deque(maxlen=1000)
        self.learning_rates: Dict[str, float] = defaultdict(lambda: 0.01)
        self.performance_baseline: Dict[str, float] = {}
        self.scaler = StandardScaler()

    def register_optimization_action(self, action: OptimizationAction) -> None:
        """Register an optimization action"""
        self.optimization_actions.append(action)
        logger.info(f"Registered optimization action: {action.description}")

    def evaluate_optimization_opportunities(self) -> List[OptimizationAction]:
        """Identify optimization opportunities"""
        opportunities = []
        current_time = datetime.now()

        for action in self.optimization_actions:
            # Check cooldown period
            recent_actions = [
                a
                for a in self.action_history
                if a["action_type"] == action.action_type
                and current_time - a["timestamp"]
                < timedelta(minutes=action.cooldown_minutes)
            ]

            if recent_actions:
                continue

            # Evaluate if action should be triggered
            if self._should_trigger_action(action):
                opportunities.append(action)

        # Sort by priority
        return sorted(opportunities, key=lambda x: x.priority, reverse=True)

    def _should_trigger_action(self, action: OptimizationAction) -> bool:
        """Evaluate if an optimization action should be triggered"""
        try:
            # Parse condition and evaluate
            return eval(
                action.condition, {"__builtins__": {}}, self._get_condition_context()
            )
        except Exception as e:
            logger.error(f"Error evaluating optimization condition: {e}")
            return False

    def _get_condition_context(self) -> Dict[str, Any]:
        """Get context for evaluating optimization conditions"""
        context = {}

        # Add operation statistics
        for op_type in [
            "conversion",
            "mod_analysis",
            "batch_processing",
            "cache_access",
        ]:
            stats = self.metrics.get_operation_stats(op_type)
            if stats:
                context.update(
                    {
                        f"{op_type}_avg_ms": stats["avg_ms"],
                        f"{op_type}_p95_ms": stats["p95_ms"],
                        f"{op_type}_count": stats["count"],
                    }
                )

        # Add system metrics
        system = self.metrics.collect_system_metrics()
        context.update(
            {
                "cpu_percent": system["cpu_percent"],
                "memory_percent": system["memory_percent"],
                "process_count": system["process_count"],
            }
        )

        # Add trend analysis
        for op_type in ["conversion", "mod_analysis"]:
            trend = self.metrics.get_trend_analysis(op_type)
            if trend:
                context[f"{op_type}_trend"] = trend["trend"]
                context[f"{op_type}_trend_confidence"] = trend["confidence"]

        return context

    async def execute_optimization(self, action: OptimizationAction) -> Dict[str, Any]:
        """Execute an optimization action"""
        logger.info(f"Executing optimization: {action.description}")

        start_time = time.time()
        result = {
            "action_type": action.action_type,
            "start_time": datetime.now(),
            "success": False,
            "result": None,
            "error": None,
        }

        try:
            optimization_result = await action.action_func()
            result["success"] = True
            result["result"] = optimization_result

            # Update learning based on results
            self._update_learning(action.action_type, True, optimization_result)

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Optimization failed: {e}")

            # Update learning based on failure
            self._update_learning(action.action_type, False, None)

        result["duration_ms"] = (time.time() - start_time) * 1000

        # Record in history
        self.action_history.append(result)

        return result

    def _update_learning(self, action_type: str, success: bool, result: Any) -> None:
        """Update learning rates based on optimization results"""
        if success:
            # Increase confidence in successful actions
            self.learning_rates[action_type] *= 1.1
        else:
            # Decrease confidence in failed actions
            self.learning_rates[action_type] *= 0.9

        # Keep learning rates bounded
        self.learning_rates[action_type] = max(
            0.001, min(0.1, self.learning_rates[action_type])
        )


class PerformanceMonitor:
    """Main performance monitoring and adaptive optimization system"""

    def __init__(self, enable_prometheus: bool = True, prometheus_port: int = 8000):
        self.metrics_collector = MetricsCollector()
        self.optimizer = AdaptiveOptimizer(self.metrics_collector)
        self.thresholds: List[PerformanceThreshold] = []
        self.monitoring_active = False
        self.optimization_interval = 30  # seconds
        self.alert_callbacks: List[Callable] = []

        # Prometheus metrics
        self.enable_prometheus = enable_prometheus
        if enable_prometheus:
            self._setup_prometheus_metrics()
            try:
                start_http_server(prometheus_port)
                logger.info(
                    f"Prometheus metrics server started on port {prometheus_port}"
                )
            except Exception as e:
                logger.warning(f"Failed to start Prometheus server: {e}")
                self.enable_prometheus = False

        # Background monitoring task
        self._monitoring_task = None
        self._system_metrics_task = None

    def _setup_prometheus_metrics(self) -> None:
        """Setup Prometheus metrics"""
        self.prometheus_counters = {
            "operations_total": Counter(
                "modporter_operations_total",
                "Total operations",
                ["operation_type", "status"],
            ),
            "optimizations_total": Counter(
                "modporter_optimizations_total",
                "Total optimizations",
                ["action_type", "success"],
            ),
            "alerts_total": Counter(
                "modporter_alerts_total", "Total alerts", ["severity"]
            ),
        }

        self.prometheus_histograms = {
            "operation_duration_ms": Histogram(
                "modporter_operation_duration_ms",
                "Operation duration in ms",
                ["operation_type"],
            ),
            "queue_length": Histogram(
                "modporter_queue_length", "Queue length", ["queue_type"]
            ),
        }

        self.prometheus_gauges = {
            "active_operations": Gauge(
                "modporter_active_operations", "Number of active operations"
            ),
            "cache_hit_rate": Gauge("modporter_cache_hit_rate", "Cache hit rate"),
            "cpu_percent": Gauge("modporter_cpu_percent", "CPU usage percentage"),
            "memory_percent": Gauge(
                "modporter_memory_percent", "Memory usage percentage"
            ),
            "db_connections": Gauge("modporter_db_connections", "Database connections"),
        }

    def start_monitoring(self) -> None:
        """Start performance monitoring"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._system_metrics_task = asyncio.create_task(self._system_metrics_loop())

        logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        self.monitoring_active = False

        if self._monitoring_task:
            self._monitoring_task.cancel()

        if self._system_metrics_task:
            self._system_metrics_task.cancel()

        logger.info("Performance monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Check for optimization opportunities
                opportunities = self.optimizer.evaluate_optimization_opportunities()

                for opportunity in opportunities[:3]:  # Limit concurrent optimizations
                    await self.optimizer.execute_optimization(opportunity)

                # Check thresholds and send alerts
                await self._check_thresholds()

                # Update Prometheus gauges
                if self.enable_prometheus:
                    await self._update_prometheus_metrics()

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            await asyncio.sleep(self.optimization_interval)

    async def _system_metrics_loop(self) -> None:
        """Collect system metrics"""
        while self.monitoring_active:
            try:
                system_metrics = self.metrics_collector.collect_system_metrics()
                self.metrics_collector.system_metrics.append(system_metrics)

                # Update system Prometheus metrics
                if self.enable_prometheus:
                    self.prometheus_gauges["cpu_percent"].set(
                        system_metrics["cpu_percent"]
                    )
                    self.prometheus_gauges["memory_percent"].set(
                        system_metrics["memory_percent"]
                    )

            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")

            await asyncio.sleep(5)  # Collect system metrics every 5 seconds

    async def _check_thresholds(self) -> None:
        """Check performance thresholds and send alerts"""
        for threshold in self.thresholds:
            if await self._evaluate_threshold(threshold):
                await self._send_alert(
                    threshold,
                    "critical" if self._is_critical_violation(threshold) else "warning",
                )

    async def _evaluate_threshold(self, threshold: PerformanceThreshold) -> bool:
        """Evaluate if a threshold is violated"""
        # Implementation would depend on the specific metric type
        # This is a placeholder for threshold evaluation logic
        return False

    def _is_critical_violation(self, threshold: PerformanceThreshold) -> bool:
        """Check if threshold violation is critical"""
        # Implementation for checking criticality
        return False

    async def _send_alert(self, threshold: PerformanceThreshold, severity: str) -> None:
        """Send performance alert"""
        alert_data = {
            "threshold": threshold.metric_name,
            "severity": severity,
            "timestamp": datetime.now(),
            "message": f"Performance threshold violation: {threshold.metric_name}",
        }

        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

        # Update Prometheus counter
        if self.enable_prometheus:
            self.prometheus_counters["alerts_total"].labels(severity=severity).inc()

        logger.warning(f"Performance alert: {alert_data}")

    async def _update_prometheus_metrics(self) -> None:
        """Update Prometheus metrics"""
        try:
            # Update cache hit rate
            recent_metrics = [
                m
                for m in self.metrics_collector.metrics
                if m.timestamp > datetime.now() - timedelta(minutes=5)
            ]

            if recent_metrics:
                avg_cache_hit_rate = statistics.mean(
                    [m.cache_hit_rate for m in recent_metrics]
                )
                self.prometheus_gauges["cache_hit_rate"].set(avg_cache_hit_rate)

                # Update active operations
                active_count = len(
                    [
                        m
                        for m in recent_metrics
                        if m.timestamp > datetime.now() - timedelta(seconds=30)
                    ]
                )
                self.prometheus_gauges["active_operations"].set(active_count)

        except Exception as e:
            logger.error(f"Error updating Prometheus metrics: {e}")

    def register_threshold(self, threshold: PerformanceThreshold) -> None:
        """Register a performance threshold"""
        self.thresholds.append(threshold)

    def register_alert_callback(self, callback: Callable) -> None:
        """Register an alert callback function"""
        self.alert_callbacks.append(callback)

    @asynccontextmanager
    async def monitor_operation(self, operation_type: str, operation_id: str = None):
        """Context manager for monitoring operations"""
        start_time = time.time()
        system_before = self.metrics_collector.collect_system_metrics()

        if operation_id is None:
            operation_id = f"{operation_type}_{int(start_time * 1000)}"

        try:
            yield operation_id

            # Record successful operation
            duration = (time.time() - start_time) * 1000
            system_after = self.metrics_collector.collect_system_metrics()

            metric = PerformanceMetric(
                timestamp=datetime.now(),
                operation_type=operation_type,
                operation_id=operation_id,
                duration_ms=duration,
                cpu_percent=(system_before["cpu_percent"] + system_after["cpu_percent"])
                / 2,
                memory_mb=system_after["memory_mb"],
                db_connections=0,  # Would be populated from actual DB connection pool
                cache_hit_rate=0.0,  # Would be populated from actual cache stats
                error_count=0,
            )

            self.metrics_collector.record_metric(metric)

            # Update Prometheus metrics
            if self.enable_prometheus:
                self.prometheus_histograms["operation_duration_ms"].labels(
                    operation_type=operation_type
                ).observe(duration)
                self.prometheus_counters["operations_total"].labels(
                    operation_type=operation_type, status="success"
                ).inc()

        except Exception as e:
            # Record failed operation
            duration = (time.time() - start_time) * 1000
            system_after = self.metrics_collector.collect_system_metrics()

            metric = PerformanceMetric(
                timestamp=datetime.now(),
                operation_type=operation_type,
                operation_id=operation_id,
                duration_ms=duration,
                cpu_percent=(system_before["cpu_percent"] + system_after["cpu_percent"])
                / 2,
                memory_mb=system_after["memory_mb"],
                db_connections=0,
                cache_hit_rate=0.0,
                error_count=1,
                metadata={"error": str(e)},
            )

            self.metrics_collector.record_metric(metric)

            # Update Prometheus metrics
            if self.enable_prometheus:
                self.prometheus_histograms["operation_duration_ms"].labels(
                    operation_type=operation_type
                ).observe(duration)
                self.prometheus_counters["operations_total"].labels(
                    operation_type=operation_type, status="error"
                ).inc()

            raise

    def get_performance_report(
        self, operation_type: str = None, window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "generated_at": datetime.now(),
            "window_minutes": window_minutes,
            "total_operations": len(self.metrics_collector.metrics),
            "operation_stats": {},
            "system_metrics": {},
            "optimization_history": list(self.optimizer.action_history)[-10:],
            "trend_analysis": {},
        }

        if operation_type:
            report["operation_stats"][operation_type] = (
                self.metrics_collector.get_operation_stats(
                    operation_type, window_minutes
                )
            )
            report["trend_analysis"][operation_type] = (
                self.metrics_collector.get_trend_analysis(
                    operation_type, window_minutes
                )
            )
        else:
            # Get stats for all operation types
            op_types = set(m.operation_type for m in self.metrics_collector.metrics)
            for op_type in op_types:
                report["operation_stats"][op_type] = (
                    self.metrics_collector.get_operation_stats(op_type, window_minutes)
                )
                report["trend_analysis"][op_type] = (
                    self.metrics_collector.get_trend_analysis(op_type, window_minutes)
                )

        # Add system metrics summary
        if self.metrics_collector.system_metrics:
            recent_system = list(self.metrics_collector.system_metrics)[
                -60:
            ]  # Last 60 samples (5 minutes)
            report["system_metrics"] = {
                "avg_cpu_percent": statistics.mean(
                    [s["cpu_percent"] for s in recent_system]
                ),
                "avg_memory_percent": statistics.mean(
                    [s["memory_percent"] for s in recent_system]
                ),
                "max_memory_mb": max([s["memory_mb"] for s in recent_system]),
                "avg_process_count": statistics.mean(
                    [s["process_count"] for s in recent_system]
                ),
            }

        return report


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Decorator for easy operation monitoring
def monitor_performance(operation_type: str):
    """Decorator for monitoring function performance"""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with performance_monitor.monitor_operation(operation_type):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, we need to run them in an async context
            async def run_async():
                async with performance_monitor.monitor_operation(operation_type):
                    return func(*args, **kwargs)

            return asyncio.run(run_async())

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
