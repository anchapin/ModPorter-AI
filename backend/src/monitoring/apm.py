"""
Production Application Performance Monitoring (APM)
Comprehensive monitoring for application performance and business metrics
"""

import asyncio
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from functools import wraps
import uuid
import json
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class Span:
    """APM span for tracing operations"""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    status: str  # ok, error, timeout
    error_message: Optional[str]
    tags: Dict[str, Any]
    metrics: Dict[str, float]


class APMManager:
    """Application Performance Monitoring Manager"""

    def __init__(self, service_name: str, redis_client: redis.Redis = None):
        self.service_name = service_name
        self.redis = redis_client
        self.active_spans: Dict[str, Span] = {}
        self.completed_spans: List[Span] = []
        self.max_completed_spans = 10000

        # Prometheus metrics
        self.request_count = Counter(
            f"{service_name}_requests_total",
            "Total requests",
            ["method", "endpoint", "status"],
        )

        self.request_duration = Histogram(
            f"{service_name}_request_duration_seconds",
            "Request duration",
            ["method", "endpoint"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0],
        )

        self.active_connections = Gauge(
            f"{service_name}_active_connections", "Active connections"
        )

        self.error_count = Counter(
            f"{service_name}_errors_total", "Total errors", ["error_type", "endpoint"]
        )

        self.business_metrics = Counter(
            f"{service_name}_business_metrics_total",
            "Business metrics",
            ["metric_name", "metric_type"],
        )

        self.system_metrics = {
            "cpu_usage": Gauge(
                f"{service_name}_cpu_usage_percent", "CPU usage percentage"
            ),
            "memory_usage": Gauge(
                f"{service_name}_memory_usage_bytes", "Memory usage in bytes"
            ),
            "disk_usage": Gauge(
                f"{service_name}_disk_usage_percent", "Disk usage percentage"
            ),
            "gc_collection": Counter(
                f"{service_name}_gc_collections_total", "GC collections", ["generation"]
            ),
        }

        # Custom metrics registry
        self.custom_metrics: Dict[str, Any] = {}

    def create_span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        tags: Dict[str, Any] = None,
    ) -> Span:
        """Create a new APM span"""
        trace_id = getattr(self, "_current_trace_id", str(uuid.uuid4()))
        span_id = str(uuid.uuid4())

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=datetime.utcnow(),
            end_time=None,
            duration_ms=None,
            status="ok",
            error_message=None,
            tags=tags or {},
            metrics={},
        )

        self.active_spans[span_id] = span
        self._current_trace_id = trace_id

        return span

    def finish_span(
        self,
        span_id: str,
        status: str = "ok",
        error_message: Optional[str] = None,
        metrics: Dict[str, float] = None,
    ):
        """Finish an APM span"""
        if span_id not in self.active_spans:
            return

        span = self.active_spans.pop(span_id)
        span.end_time = datetime.utcnow()
        span.status = status
        span.error_message = error_message
        span.metrics.update(metrics or {})

        if span.end_time and span.start_time:
            span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000

        # Add to completed spans
        self.completed_spans.append(span)

        # Limit completed spans to prevent memory issues
        if len(self.completed_spans) > self.max_completed_spans:
            self.completed_spans = self.completed_spans[-self.max_completed_spans :]

        # Store in Redis if available
        if self.redis:
            asyncio.create_task(self._store_span_in_redis(span))

        # Update Prometheus metrics
        self._update_prometheus_metrics(span)

    async def _store_span_in_redis(self, span: Span):
        """Store span in Redis for distributed tracing"""
        try:
            span_data = asdict(span)
            span_data["start_time"] = span.start_time.isoformat()
            if span.end_time:
                span_data["end_time"] = span.end_time.isoformat()

            await self.redis.setex(
                f"apm:span:{span.span_id}",
                3600,  # 1 hour TTL
                json.dumps(span_data, default=str),
            )

            # Add to trace index
            await self.redis.sadd(f"apm:trace:{span.trace_id}", span.span_id)
            await self.redis.expire(f"apm:trace:{span.trace_id}", 3600)

        except Exception as e:
            logger.error(f"Failed to store span in Redis: {e}")

    def _update_prometheus_metrics(self, span: Span):
        """Update Prometheus metrics based on span"""
        try:
            # Update request duration
            if span.duration_ms:
                self.request_duration.observe(
                    span.duration_ms / 1000.0,
                    labels={
                        "method": span.tags.get("method", "UNKNOWN"),
                        "endpoint": span.operation_name,
                    },
                )

            # Update error count
            if span.status == "error":
                self.error_count.inc(
                    labels={
                        "error_type": span.error_message or "UNKNOWN",
                        "endpoint": span.operation_name,
                    }
                )

            # Update business metrics
            for metric_name, value in span.metrics.items():
                self.business_metrics.inc(
                    labels={"metric_name": metric_name, "metric_type": "counter"}
                )

        except Exception as e:
            logger.error(f"Failed to update Prometheus metrics: {e}")

    def trace_function(self, operation_name: str = None, tags: Dict[str, Any] = None):
        """Decorator to trace function calls"""

        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                func_name = operation_name or f"{func.__module__}.{func.__name__}"
                span = self.create_span(func_name, tags=tags)

                try:
                    result = await func(*args, **kwargs)
                    self.finish_span(span.span_id, status="ok")
                    return result
                except Exception as e:
                    error_message = str(e)
                    self.finish_span(
                        span.span_id, status="error", error_message=error_message
                    )
                    raise

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                func_name = operation_name or f"{func.__module__}.{func.__name__}"
                span = self.create_span(func_name, tags=tags)

                try:
                    result = func(*args, **kwargs)
                    self.finish_span(span.span_id, status="ok")
                    return result
                except Exception as e:
                    error_message = str(e)
                    self.finish_span(
                        span.span_id, status="error", error_message=error_message
                    )
                    raise

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    @asynccontextmanager
    async def trace_context(self, operation_name: str, tags: Dict[str, Any] = None):
        """Context manager for tracing operations"""
        span = self.create_span(operation_name, tags=tags)

        try:
            yield span
            self.finish_span(span.span_id, status="ok")
        except Exception as e:
            error_message = str(e)
            self.finish_span(span.span_id, status="error", error_message=error_message)
            raise

    def record_business_metric(
        self, metric_name: str, value: float, tags: Dict[str, Any] = None
    ):
        """Record business metric"""
        self.business_metrics.inc(
            labels={"metric_name": metric_name, "metric_type": "counter"}
        )

        if self.redis:
            asyncio.create_task(self._store_business_metric(metric_name, value, tags))

    async def _store_business_metric(
        self, metric_name: str, value: float, tags: Dict[str, Any]
    ):
        """Store business metric in Redis"""
        try:
            metric_data = {
                "name": metric_name,
                "value": value,
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name,
                "tags": tags or {},
            }

            await self.redis.lpush(
                f"apm:business_metrics:{metric_name}", json.dumps(metric_data)
            )
            await self.redis.ltrim(
                f"apm:business_metrics:{metric_name}", 0, 9999
            )  # Keep last 10k
            await self.redis.expire(
                f"apm:business_metrics:{metric_name}", 86400
            )  # 24 hours

        except Exception as e:
            logger.error(f"Failed to store business metric: {e}")

    def get_span_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get summary of spans in the last N minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_spans = [s for s in self.completed_spans if s.start_time > cutoff_time]

        if not recent_spans:
            return {
                "total_spans": 0,
                "successful_spans": 0,
                "failed_spans": 0,
                "avg_duration_ms": 0,
                "operations": {},
            }

        successful_spans = [s for s in recent_spans if s.status == "ok"]
        failed_spans = [s for s in recent_spans if s.status == "error"]

        # Calculate average duration
        durations = [s.duration_ms for s in recent_spans if s.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Group by operation
        operations = {}
        for span in recent_spans:
            op_name = span.operation_name
            if op_name not in operations:
                operations[op_name] = {"count": 0, "errors": 0, "avg_duration_ms": 0}

            operations[op_name]["count"] += 1
            if span.status == "error":
                operations[op_name]["errors"] += 1

            if span.duration_ms:
                operations[op_name]["avg_duration_ms"] += span.duration_ms

        # Calculate averages per operation
        for op_data in operations.values():
            if op_data["count"] > 0:
                op_data["avg_duration_ms"] /= op_data["count"]
                op_data["error_rate"] = op_data["errors"] / op_data["count"] * 100
            else:
                op_data["error_rate"] = 0

        return {
            "total_spans": len(recent_spans),
            "successful_spans": len(successful_spans),
            "failed_spans": len(failed_spans),
            "avg_duration_ms": avg_duration,
            "operations": operations,
        }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk metrics
            disk = psutil.disk_usage("/")

            # Network metrics
            network = psutil.net_io_counters()

            # Process metrics
            process = psutil.Process()

            # Update Prometheus metrics
            self.system_metrics["cpu_usage"].set(cpu_percent)
            self.system_metrics["memory_usage"].set(memory.used)
            self.system_metrics["disk_usage"].set((disk.used / disk.total) * 100)

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {"percent": cpu_percent, "count": cpu_count},
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent,
                    "swap": {
                        "total": swap.total,
                        "used": swap.used,
                        "percent": swap.percent,
                    },
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100,
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                },
                "process": {
                    "pid": process.pid,
                    "memory_info": process.memory_info()._asdict(),
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads(),
                    "create_time": process.create_time(),
                },
            }

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}

    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        return generate_latest()

    async def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get all spans for a trace"""
        if not self.redis:
            return []

        try:
            span_ids = await self.redis.smembers(f"apm:trace:{trace_id}")
            spans = []

            for span_id in span_ids:
                span_data = await self.redis.get(f"apm:span:{span_id}")
                if span_data:
                    spans.append(json.loads(span_data))

            return spans

        except Exception as e:
            logger.error(f"Failed to get trace: {e}")
            return []

    async def get_business_metrics(
        self, metric_name: str, minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """Get business metrics for a specific metric"""
        if not self.redis:
            return []

        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            metric_data = await self.redis.lrange(
                f"apm:business_metrics:{metric_name}", 0, 1000
            )

            metrics = []
            for data in metric_data:
                metric = json.loads(data)
                metric_time = datetime.fromisoformat(metric["timestamp"])
                if metric_time > cutoff_time:
                    metrics.append(metric)

            return metrics

        except Exception as e:
            logger.error(f"Failed to get business metrics: {e}")
            return []


# Decorator for automatic function tracing
def trace(operation_name: str = None, tags: Dict[str, Any] = None):
    """Decorator to automatically trace function calls"""

    def decorator(func):
        # Get APM manager from current context or create default
        apm_manager = getattr(trace, "_apm_manager", None)
        if apm_manager is None:
            apm_manager = APMManager("default")
            trace._apm_manager = apm_manager

        return apm_manager.trace_function(operation_name, tags)(func)

    return decorator


# Custom metrics class
class CustomMetric:
    """Custom metric for application-specific monitoring"""

    def __init__(
        self, name: str, metric_type: str, description: str, labels: List[str] = None
    ):
        self.name = name
        self.metric_type = metric_type
        self.description = description
        self.labels = labels or []

        if metric_type == "counter":
            self.metric = Counter(name, description, self.labels)
        elif metric_type == "histogram":
            self.metric = Histogram(name, description, self.labels)
        elif metric_type == "gauge":
            self.metric = Gauge(name, description, self.labels)
        else:
            raise ValueError(f"Unsupported metric type: {metric_type}")

    def inc(self, value: float = 1, labels: Dict[str, str] = None):
        """Increment counter metric"""
        if self.metric_type == "counter":
            self.metric.labels(**labels or {}).inc(value)

    def observe(self, value: float, labels: Dict[str, str] = None):
        """Observe histogram metric"""
        if self.metric_type == "histogram":
            self.metric.labels(**labels or {}).observe(value)

    def set(self, value: float, labels: Dict[str, str] = None):
        """Set gauge metric"""
        if self.metric_type == "gauge":
            self.metric.labels(**labels or {}).set(value)
