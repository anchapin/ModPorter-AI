"""
Backward compatibility shim for services.task_queue.

Re-exports symbols from celery_tasks to maintain compatibility
with code that imports from services.task_queue.

Issue: #1098 - Consolidate task queues to Celery
"""

from typing import Dict, Any, Optional, List

# Re-export from celery_tasks for backward compatibility
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
    enqueue_task,
    conversion_task,
    asset_conversion_task,
    cleanup_old_tasks,
    process_retry_queue,
)

# Re-export Task class for backward compatibility
from services.celery_tasks import TaskData as Task


# Full AsyncTaskQueue for backward compatibility with full attribute support
class AsyncTaskQueue:
    """Async task queue with Redis backend - wrapper around celery_tasks functions for backward compatibility."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_retries: int = 3,
        default_timeout: int = 300,
        dead_letter_enabled: bool = True,
        # Additional params accepted for backward compatibility
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

    def close(self):
        pass


# Module-level singleton for backward compatibility
_task_queue = AsyncTaskQueue()


async def get_task_queue() -> AsyncTaskQueue:
    """Get the async task queue instance."""
    return _task_queue


__all__ = [
    "TaskStatus",
    "TaskPriority",
    "Task",
    "RetryPolicy",
    "AsyncTaskQueue",
    "DEFAULT_RETRY_POLICY",
    "CONVERSION_RETRY_POLICY",
    "enqueue_task",
    "get_task_status",
    "cancel_task",
    "get_queue_stats",
    "get_task_queue",
    "conversion_task",
    "asset_conversion_task",
    "cleanup_old_tasks",
    "process_retry_queue",
    "TimeoutResult",
    "_task_queue",
]