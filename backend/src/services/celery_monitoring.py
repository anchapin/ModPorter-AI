"""
Celery queue monitoring service for Portkit.

Provides metrics collection for Celery task monitoring via celery-exporter
and Prometheus integration for queue depth, task metrics, and worker health.

Issue: #1212 - Pre-beta: Full observability stack
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


class QueuePriority(Enum):
    """Queue priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QueueMetrics:
    """Metrics for a single queue."""

    name: str
    depth: int = 0
    messages_enqueued: int = 0
    messages_dequeued: int = 0
    messages_failed: int = 0
    avg_processing_time: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkerMetrics:
    """Metrics for Celery workers."""

    name: str
    online: bool = False
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_load: float = 0.0
    last_heartbeat: Optional[datetime] = None


@dataclass
class CeleryClusterMetrics:
    """Aggregated metrics for the Celery cluster."""

    total_queues: int = 0
    total_queue_depth: int = 0
    total_workers: int = 0
    online_workers: int = 0
    total_tasks_enqueued: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    total_tasks_retrying: int = 0
    tasks_by_queue: Dict[str, int] = field(default_factory=dict)
    queue_metrics: Dict[str, QueueMetrics] = field(default_factory=dict)
    worker_metrics: Dict[str, WorkerMetrics] = field(default_factory=dict)
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CeleryQueueMonitor:
    """Monitor Celery queue health and metrics."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        namespace: str = "portkit",
    ):
        """
        Initialize Celery queue monitor.

        Args:
            redis_url: Redis connection URL
            namespace: Key namespace prefix
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.namespace = namespace
        self._redis_client = None
        self._metrics_key = f"{namespace}:metrics"

    def _get_redis(self):
        """Get Redis client."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis_client

    def get_queue_depth(self, queue_name: str) -> int:
        """Get the current depth of a queue."""
        r = self._get_redis()
        key = f"{self.namespace}:queue:{queue_name}"
        return r.zcard(key)

    def get_all_queue_depths(self) -> Dict[str, int]:
        """Get depths for all priority queues."""
        depths = {}
        for priority in QueuePriority:
            queue_key = f"{self.namespace}:queue:{priority.value}"
            r = self._get_redis()
            depth = r.zcard(queue_key)
            depths[priority.value] = depth
        return depths

    def get_dead_letter_queue_depth(self) -> int:
        """Get the dead letter queue depth."""
        r = self._get_redis()
        key = f"{self.namespace}:dead_letter"
        return r.zcard(key)

    def get_processing_set_size(self) -> int:
        """Get number of tasks currently being processed."""
        r = self._get_redis()
        key = f"{self.namespace}:processing"
        return r.scard(key)

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        r = self._get_redis()

        stats = {
            "queues": {},
            "total_queued": 0,
            "total_processing": r.scard(f"{self.namespace}:processing"),
            "total_dead_letter": r.zcard(f"{self.namespace}:dead_letter"),
            "retry_queue_size": r.zcard(f"{self.namespace}:retry"),
            "metrics": {},
        }

        for priority in QueuePriority:
            queue_key = f"{self.namespace}:queue:{priority.value}"
            count = r.zcard(queue_key)
            stats["queues"][priority.value] = count
            stats["total_queued"] += count

        metrics_raw = r.hgetall(self._metrics_key)
        if metrics_raw:
            stats["metrics"] = {k: int(v) for k, v in metrics_raw.items()}

        return stats

    def collect_cluster_metrics(self) -> CeleryClusterMetrics:
        """Collect comprehensive cluster metrics."""
        stats = self.get_queue_stats()

        metrics = CeleryClusterMetrics(
            total_queues=len(QueuePriority),
            total_queue_depth=stats["total_queued"],
            total_workers=0,
            online_workers=0,
            total_tasks_enqueued=stats["metrics"].get("tasks_enqueued", 0),
            total_tasks_completed=stats["metrics"].get("tasks_completed", 0),
            total_tasks_failed=stats["metrics"].get("tasks_failed", 0),
            total_tasks_retrying=stats["retry_queue_size"],
            tasks_by_queue=stats["queues"],
        )

        for queue_name, depth in stats["queues"].items():
            metrics.queue_metrics[queue_name] = QueueMetrics(
                name=queue_name,
                depth=depth,
            )

        return metrics

    def check_queue_health(self) -> Dict[str, Any]:
        """
        Check queue health and return status.

        Returns dict with:
        - healthy: bool
        - issues: list of issue descriptions
        - alerts: list of triggered alert conditions
        """
        issues = []
        alerts = []

        stats = self.get_queue_stats()

        if stats["total_queued"] > 1000:
            issues.append(f"Queue backlog is critically high: {stats['total_queued']} tasks")
            alerts.append(
                {
                    "type": "queue_backlog_critical",
                    "severity": "P1",
                    "value": stats["total_queued"],
                    "threshold": 1000,
                }
            )

        if stats["total_queued"] > 100:
            issues.append(f"Queue backlog is elevated: {stats['total_queued']} tasks")
            alerts.append(
                {
                    "type": "queue_backlog_warning",
                    "severity": "P2",
                    "value": stats["total_queued"],
                    "threshold": 100,
                }
            )

        if stats["total_dead_letter"] > 50:
            issues.append(f"Dead letter queue has {stats['total_dead_letter']} tasks")
            alerts.append(
                {
                    "type": "dead_letter_queue_high",
                    "severity": "P2",
                    "value": stats["total_dead_letter"],
                    "threshold": 50,
                }
            )

        if stats["total_processing"] == 0 and stats["total_queued"] > 0:
            issues.append("No workers processing but tasks are queued")
            alerts.append(
                {
                    "type": "workers_idle",
                    "severity": "P1",
                    "value": 0,
                    "threshold": 1,
                }
            )

        if stats["retry_queue_size"] > 100:
            issues.append(f"Retry queue is building: {stats['retry_queue_size']} tasks")
            alerts.append(
                {
                    "type": "retry_queue_building",
                    "severity": "P2",
                    "value": stats["retry_queue_size"],
                    "threshold": 100,
                }
            )

        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "alerts": alerts,
            "stats": stats,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_task_failure_rate(self, window_minutes: int = 5) -> float:
        """
        Calculate task failure rate over a time window.

        Args:
            window_minutes: Time window in minutes

        Returns:
            Failure rate as a percentage (0-100)
        """
        metrics = self._get_redis().hgetall(self._metrics_key)
        if not metrics:
            return 0.0

        completed = int(metrics.get("tasks_completed", 0))
        failed = int(metrics.get("tasks_failed", 0))

        total = completed + failed
        if total == 0:
            return 0.0

        return (failed / total) * 100

    def is_worker_available(self) -> bool:
        """Check if any workers are available to process tasks."""
        return self.get_processing_set_size() >= 0

    def get_queue_depth_prometheus(self) -> List[Dict[str, Any]]:
        """
        Get queue metrics in Prometheus exposition format.

        Returns list of metrics suitable for Prometheus /metrics endpoint.
        """
        stats = self.get_queue_stats()

        metrics = [
            {
                "name": "celery_queue_depth",
                "type": "gauge",
                "labels": {},
                "value": stats["total_queued"],
                "help": "Total number of tasks in all queues",
            },
            {
                "name": "celery_queue_processing",
                "type": "gauge",
                "labels": {},
                "value": stats["total_processing"],
                "help": "Number of tasks currently being processed",
            },
            {
                "name": "celery_dead_letter_queue_size",
                "type": "gauge",
                "labels": {},
                "value": stats["total_dead_letter"],
                "help": "Number of tasks in dead letter queue",
            },
            {
                "name": "celery_retry_queue_size",
                "type": "gauge",
                "labels": {},
                "value": stats["retry_queue_size"],
                "help": "Number of tasks in retry queue",
            },
        ]

        for queue_name, count in stats["queues"].items():
            metrics.append(
                {
                    "name": "celery_queue_size",
                    "type": "gauge",
                    "labels": {"queue": queue_name},
                    "value": count,
                    "help": f"Number of tasks in {queue_name} queue",
                }
            )

        return metrics


class CeleryAlertRules:
    """Alert rules for Celery queue monitoring."""

    ALERT_RULES = [
        {
            "name": "CeleryQueueDepthHigh",
            "expr": "celery_queue_depth > 100",
            "for": "5m",
            "severity": "P1",
            "summary": "Queue depth exceeds threshold for 5 minutes",
            "description": "Queue depth is {value}, threshold is 100",
        },
        {
            "name": "CeleryTaskFailureRateHigh",
            "expr": "rate(celery_tasks_total{state='failure'}[5m]) / rate(celery_tasks_total[5m]) > 0.1",
            "for": "5m",
            "severity": "P1",
            "summary": "Task failure rate exceeds 10%",
            "description": "Failure rate is {value}",
        },
        {
            "name": "CeleryWorkersOffline",
            "expr": "celery_workers_online == 0",
            "for": "1m",
            "severity": "P0",
            "summary": "All Celery workers are offline",
            "description": "No workers available to process tasks",
        },
        {
            "name": "CeleryTaskDurationP95High",
            "expr": "histogram_quantile(0.95, rate(celery_task_runtime_seconds_bucket[5m])) > 120",
            "for": "5m",
            "severity": "P2",
            "summary": "P95 task duration exceeds 120 seconds",
            "description": "P95 duration is {value}s",
        },
        {
            "name": "CeleryDeadLetterQueueHigh",
            "expr": "celery_dead_letter_queue_size > 50",
            "for": "5m",
            "severity": "P2",
            "summary": "Dead letter queue has too many failed tasks",
            "description": "Dead letter queue size is {value}",
        },
        {
            "name": "CeleryQueueBuilding",
            "expr": "increase(celery_tasks_total{state='enqueued'}[5m]) > 100",
            "for": "5m",
            "severity": "P2",
            "summary": "Queue is rapidly building up",
            "description": "Enqueue rate is {value}/5m",
        },
    ]

    @classmethod
    def get_alert_rules_prometheus(cls) -> str:
        """Get alert rules in Prometheus format."""
        rules = []
        for rule in cls.ALERT_RULES:
            rules.append(f"  - alert: {rule['name']}")
            rules.append(f"    expr: {rule['expr']}")
            rules.append(f"    for: {rule['for']}")
            rules.append(f"    labels:")
            rules.append(f"      severity: {rule['severity']}")
            rules.append(f"      team: infrastructure")
            rules.append(f"    annotations:")
            rules.append(f'      summary: "{rule["summary"]}"')
            rules.append(f'      description: "{rule["description"]}"')
            rules.append("")

        return "\n".join(rules)


def get_celery_monitor() -> CeleryQueueMonitor:
    """Get a Celery queue monitor instance."""
    return CeleryQueueMonitor(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        namespace=os.getenv("CELERY_NAMESPACE", "portkit"),
    )
