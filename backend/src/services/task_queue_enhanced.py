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
    RetryPolicy as BaseRetryPolicy,
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
)

# Re-export Task class for backward compatibility
from services.celery_tasks import TaskData as Task


# Extended RetryPolicy with retryable_errors and should_retry for backward compatibility
@dataclass
class RetryPolicy(BaseRetryPolicy):
    """Configurable retry policy for tasks - extended with retryable_errors and should_retry."""

    retryable_errors: List[str] = field(default_factory=list)

    def should_retry(self, error_type: str, retry_count: int) -> bool:
        """Determine if an error should be retried."""
        if retry_count >= self.max_retries:
            return False
        if self.retryable_errors and error_type not in self.retryable_errors:
            return False
        return True


# Re-create DEFAULT_RETRY_POLICY with new class (base values are same)
DEFAULT_RETRY_POLICY = RetryPolicy()

# CONVERSION_RETRY_POLICY needs retryable_errors
CONVERSION_RETRY_POLICY = RetryPolicy(
    max_retries=5,
    initial_delay_seconds=2.0,
    max_delay_seconds=600.0,
    retryable_errors=["TimeoutError", "ConnectionError", "RedisError"],
)


# QueueHealth for enhanced queue monitoring
@dataclass
class QueueHealth:
    """Health metrics for queue monitoring."""

    # Support both old field names (total_queued, total_processing, etc.)
    # and new field names (queue_size, processing_count, etc.)
    total_queued: int = 0
    total_processing: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_dead_letter: int = 0
    oldest_queued_age_seconds: int = 0
    avg_processing_time_seconds: float = 0.0

    # New field names (for compatibility with updated code)
    is_healthy: bool = True
    queue_size: int = 0
    processing_count: int = 0
    dead_letter_count: int = 0
    average_wait_time_ms: float = 0.0
    last_health_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    issues: List[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        """Property for backward compatibility."""
        return self.is_healthy

    @healthy.setter
    def healthy(self, value: bool):
        """Property setter for backward compatibility."""
        self.is_healthy = value

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict with all fields."""
        return {
            "total_queued": self.total_queued or self.queue_size,
            "total_processing": self.total_processing or self.processing_count,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "total_dead_letter": self.total_dead_letter or self.dead_letter_count,
            "oldest_queued_age_seconds": self.oldest_queued_age_seconds,
            "avg_processing_time_seconds": self.avg_processing_time_seconds or self.average_wait_time_ms / 1000.0,
            "is_healthy": self.is_healthy,
            "queue_size": self.queue_size or self.total_queued,
            "processing_count": self.processing_count or self.total_processing,
            "dead_letter_count": self.dead_letter_count or self.total_dead_letter,
            "average_wait_time_ms": self.average_wait_time_ms,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "issues": self.issues,
        }

    @classmethod
    def from_stats(cls, stats: Dict) -> "QueueHealth":
        """Create QueueHealth from queue stats."""
        issues = []
        queue_size = stats.get("queue_size", stats.get("total_queued", 0))
        dead_letter_count = stats.get("dead_letter_count", stats.get("total_dead_letter", 0))

        if queue_size > 1000:
            issues.append(f"Queue backlog is high: {queue_size} tasks")
        if dead_letter_count > 100:
            issues.append(f"Dead letter queue backlog detected: {dead_letter_count} tasks")
        if stats.get("oldest_queued_age_seconds", 0) > 3600:
            issues.append(f"Oldest queued task is {stats.get('oldest_queued_age_seconds', 0) / 60:.1f} minutes old")

        return cls(
            total_queued=queue_size,
            total_processing=stats.get("processing_count", stats.get("total_processing", 0)),
            total_completed=stats.get("total_completed", 0),
            total_failed=stats.get("total_failed", 0),
            total_dead_letter=dead_letter_count,
            oldest_queued_age_seconds=stats.get("oldest_queued_age_seconds", 0),
            avg_processing_time_seconds=stats.get("avg_processing_time_seconds", stats.get("average_wait_time_ms", 0) / 1000.0),
            is_healthy=len(issues) == 0,
            queue_size=queue_size,
            processing_count=stats.get("processing_count", stats.get("total_processing", 0)),
            dead_letter_count=dead_letter_count,
            average_wait_time_ms=stats.get("average_wait_time_ms", 0),
            last_health_check=datetime.now(timezone.utc),
            issues=issues,
        )


# Retry policy presets from enhanced queue
QUICK_RETRY_POLICY = RetryPolicy(
    max_retries=2,
    initial_delay_seconds=0.5,
    max_delay_seconds=5.0,
)


# AsyncTaskQueue for backward compatibility
class AsyncTaskQueue:
    """Async task queue with Redis backend - thin wrapper around celery_tasks functions."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_retries: int = 3,
        default_timeout: int = 300,
        dead_letter_enabled: bool = True,
        # Additional params for backward compatibility
        name: str = None,
        payload: Dict = None,
        priority: "TaskPriority" = None,
    ):
        # Store instance attributes for backward compatibility
        self.redis_url = redis_url
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        self.dead_letter_enabled = dead_letter_enabled

        # Queue names for each priority level
        self._queue_names = {
            TaskPriority.LOW: "task_queue:low",
            TaskPriority.NORMAL: "task_queue:normal",
            TaskPriority.HIGH: "task_queue:high",
            TaskPriority.CRITICAL: "task_queue:critical",
        }

        # Dead letter queue name (for backward compatibility)
        self._dead_letter_queue = "task_queue:dead_letter"

        # Track running tasks
        self._running_tasks = {}

    async def enqueue(
        self, name: str, payload: Dict, priority: TaskPriority = TaskPriority.NORMAL
    ) -> TaskData:
        return await enqueue_task(name, payload, priority)

    async def get_status(self, task_id: str) -> Optional[Dict]:
        return get_task_status(task_id)

    async def cancel(self, task_id: str) -> bool:
        return cancel_task(task_id)

    async def get_stats(self) -> Dict:
        return get_queue_stats()

    async def health(self) -> QueueHealth:
        stats = await self.get_stats()
        return QueueHealth.from_stats(stats)

    # Backward-compatibility methods (delegated to health())
    async def get_queue_health(self) -> QueueHealth:
        return await self.health()


async def get_queue_health() -> QueueHealth:
    """Get queue health - backward-compatibility shim."""
    stats = get_queue_stats()
    return QueueHealth.from_stats(stats)


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
    # Queue class
    "AsyncTaskQueue",
    # Task data
    "TaskData",
]