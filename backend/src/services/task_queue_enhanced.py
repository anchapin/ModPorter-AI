"""
Backward compatibility shim for task_queue_enhanced.

Re-exports symbols from celery_tasks and tasks/ subpackage.
This shim exists to maintain backward compatibility during migration.

Issue: #1098 - Consolidate task queues
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

# Re-export everything from celery_tasks for backward compatibility
from services.celery_tasks import (
    TaskStatus,
    TaskPriority,
    RetryPolicy,
    TaskData,
    TimeoutResult,
    DEFAULT_RETRY_POLICY,
    CONVERSION_RETRY_POLICY,
    get_task_status,
    cancel_task,
    get_queue_stats,
    get_dead_letter_tasks,
    reprocess_dead_letter_task,
    health_check,
    process_retry_queue,
    enqueue_task,
    conversion_task,
    asset_conversion_task,
    java_analysis_task,
    texture_extraction_task,
    model_conversion_task,
    cleanup_old_tasks,
    purge_orphaned_files,
    delete_input_file,
    QUEUE_NAMES,
    DEAD_LETTER_QUEUE,
)

# Re-export Task class for backward compatibility
from services.celery_tasks import TaskData as Task


# QueueHealth for enhanced queue monitoring — BACKWARD COMPAT with OLD field names
@dataclass
class QueueHealth:
    """Health metrics for queue monitoring — matches old field names for backward compat."""

    # Old field names (what tests expect)
    total_queued: int = 0
    total_processing: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_dead_letter: int = 0
    avg_processing_time_seconds: float = 0.0
    oldest_queued_age_seconds: float = 0.0
    worker_count: int = 0
    healthy: bool = True
    issues: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # New-style field aliases (also accepted for forward compat)
    is_healthy: Optional[bool] = None
    queue_size: Optional[int] = None
    processing_count: Optional[int] = None
    dead_letter_count: Optional[int] = None
    average_wait_time_ms: Optional[float] = None
    last_health_check: Optional[datetime] = None

    def __post_init__(self):
        # Map new-style fields to old-style if old-style not provided
        if self.queue_size is not None and self.total_queued == 0:
            self.total_queued = self.queue_size
        if self.processing_count is not None and self.total_processing == 0:
            self.total_processing = self.processing_count
        if self.dead_letter_count is not None and self.total_dead_letter == 0:
            self.total_dead_letter = self.dead_letter_count
        if self.average_wait_time_ms is not None and self.avg_processing_time_seconds == 0.0:
            self.avg_processing_time_seconds = self.average_wait_time_ms / 1000.0
        if self.is_healthy is not None:
            self.healthy = self.is_healthy
        if self.last_health_check is not None:
            self.checked_at = self.last_health_check

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_queued": self.total_queued,
            "total_processing": self.total_processing,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "total_dead_letter": self.total_dead_letter,
            "avg_processing_time_seconds": self.avg_processing_time_seconds,
            "oldest_queued_age_seconds": self.oldest_queued_age_seconds,
            "worker_count": self.worker_count,
            "healthy": self.healthy,
            "issues": self.issues,
            "checked_at": self.checked_at.isoformat(),
        }


# Retry policy presets from enhanced queue
QUICK_RETRY_POLICY = RetryPolicy(
    max_retries=1,
    initial_delay_seconds=0.5,
    max_delay_seconds=10.0,
)


# AsyncTaskQueue for backward compatibility — stores ALL instance attributes tests access
class AsyncTaskQueue:
    """Async task queue with Redis backend - thin wrapper around celery_tasks functions."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_retries: int = 3,
        default_timeout: int = 300,
        dead_letter_enabled: bool = True,
        # Deprecated/unused params accepted for backward compatibility
        name: str = None,
        payload: Dict = None,
        priority: "TaskPriority" = None,
    ):
        # Store all instance attributes tests directly access
        self.redis_url = redis_url
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        self.dead_letter_enabled = dead_letter_enabled

        # Queue names for different priorities (mimic old Redis-based queue naming)
        self._queue_names = {
            TaskPriority.LOW: "task_queue:low",
            TaskPriority.NORMAL: "task_queue:normal",
            TaskPriority.HIGH: "task_queue:high",
            TaskPriority.CRITICAL: "task_queue:critical",
        }

        # Dead letter queue
        self._dead_letter_queue = "task_queue:dead_letter"

        # Processing tracking
        self._processing_set = "task_queue:processing"

        # Metrics tracking
        self._metrics_key = "task_queue:metrics"

        # Running tasks dict (for async task tracking)
        self._running_tasks: Dict[str, Any] = {}

        # Redis client (not actually used in shim, but tests access it)
        self._redis = None

    async def connect(self) -> None:
        """Connect to Redis — no-op shim."""
        pass

    async def disconnect(self) -> None:
        """Disconnect from Redis — no-op shim."""
        pass

    async def _get_redis(self) -> Any:
        """Get Redis client — returns None (shim)."""
        return None

    async def enqueue(
        self, name: str, payload: Dict, priority: TaskPriority = TaskPriority.NORMAL
    ) -> TaskData:
        return await enqueue_task(name, payload, priority)

    async def get_status(self, task_id: str) -> Optional[Dict]:
        return get_task_status(task_id)

    async def cancel(self, task_id: str) -> bool:
        return cancel_task(task_id)

    async def get_stats(self) -> Dict:
        stats = get_queue_stats()
        # Map to old-style keys for backward compat
        return {
            "total_queued": stats.get("total_queued", 0),
            "total_processing": stats.get("total_processing", 0),
            "total_dead_letter": stats.get("total_dead_letter", 0),
            "queues": stats.get("queues", {}),
        }

    async def health(self) -> QueueHealth:
        stats = await self.get_stats()
        issues = []
        if stats.get("total_queued", 0) > 1000:
            issues.append(f"Queue backlog is high: {stats['total_queued']} tasks")
        if stats.get("total_dead_letter", 0) > 50:
            issues.append(f"Dead letter queue has {stats['total_dead_letter']} tasks")
        return QueueHealth(
            total_queued=stats.get("total_queued", 0),
            total_processing=stats.get("total_processing", 0),
            total_dead_letter=stats.get("total_dead_letter", 0),
            healthy=len(issues) == 0,
            issues=issues,
        )

    async def get_queue_health(self) -> QueueHealth:
        return await self.health()


async def get_queue_health() -> QueueHealth:
    """Get queue health - backward-compatibility shim."""
    stats = get_queue_stats()
    issues = []
    if stats.get("total_queued", 0) > 1000:
        issues.append(f"Queue backlog is high: {stats['total_queued']} tasks")
    if stats.get("total_dead_letter", 0) > 50:
        issues.append(f"Dead letter queue has {stats['total_dead_letter']} tasks")
    return QueueHealth(
        total_queued=stats.get("total_queued", 0),
        total_processing=stats.get("total_processing", 0),
        total_dead_letter=stats.get("total_dead_letter", 0),
        healthy=len(issues) == 0,
        issues=issues,
    )


# Module-level singleton for backward compatibility
_task_queue: Optional[AsyncTaskQueue] = None


async def get_task_queue() -> AsyncTaskQueue:
    """Get or create the global task queue instance."""
    global _task_queue

    if _task_queue is None:
        redis_url = "redis://localhost:6379"
        _task_queue = AsyncTaskQueue(redis_url=redis_url)

    return _task_queue


__all__ = [
    # Base types
    "TaskStatus",
    "TaskPriority",
    "Task",
    "RetryPolicy",
    "QueueHealth",
    "TimeoutResult",
    # Policy presets
    "DEFAULT_RETRY_POLICY",
    "CONVERSION_RETRY_POLICY",
    "QUICK_RETRY_POLICY",
    # Functions
    "enqueue_task",
    "get_task_status",
    "cancel_task",
    "get_queue_stats",
    "get_dead_letter_tasks",
    "reprocess_dead_letter_task",
    "health_check",
    "process_retry_queue",
    "get_queue_health",
    "get_task_queue",
    # Queue class
    "AsyncTaskQueue",
    # Task data
    "TaskData",
    # Module singleton
    "_task_queue",
]