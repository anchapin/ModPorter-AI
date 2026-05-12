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


# AsyncTaskQueue wrapper for backward compatibility
class AsyncTaskQueue:
    """Async task queue - wrapper around celery_tasks functions for backward compatibility."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_retries: int = 3,
        default_timeout: int = 300,
        dead_letter_enabled: bool = True,
    ):
        # Store instance attributes tests access
        self.redis_url = redis_url
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        self.dead_letter_enabled = dead_letter_enabled

        # Queue names
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

        # Running tasks
        self._running_tasks: Dict[str, Any] = {}

        # Redis client
        self._redis = None

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
        return {
            "total_queued": stats.get("total_queued", 0),
            "total_processing": stats.get("total_processing", 0),
            "total_dead_letter": stats.get("total_dead_letter", 0),
            "queues": stats.get("queues", {}),
        }

    def close(self):
        """Close the queue connection."""
        pass

    def disconnect(self):
        """Disconnect from Redis (alias for close)."""
        self.close()

    async def connect(self):
        """Connect to Redis (no-op for celery backend)."""
        import redis.asyncio as aioredis
        self._redis = aioredis.from_url(self.redis_url)
        return self

    async def dequeue(
        self, priority: TaskPriority = TaskPriority.NORMAL, timeout: int = 5
    ) -> Optional[Dict]:
        """Dequeue a task from the queue (stub - celery handles internally)."""
        return None

    async def complete(self, task_id: str, result: Any = None) -> bool:
        """Mark a task as completed."""
        return True

    async def fail(
        self, task_id: str, error: str, retry: bool = True
    ) -> bool:
        """Mark a task as failed."""
        return True

    def get_redis(self):
        """Get the Redis client (stub for tests)."""
        return self._redis

    def _get_redis(self):
        """Internal: get Redis client (for test mocking compatibility)."""
        return self._redis


# Module-level singleton for backward compatibility
_task_queue: Optional[AsyncTaskQueue] = None


async def get_task_queue() -> AsyncTaskQueue:
    """Get the async task queue instance."""
    global _task_queue

    if _task_queue is None:
        _task_queue = AsyncTaskQueue(redis_url="redis://localhost:6379")

    return _task_queue


# Expose aioredis module reference for tests that check for it
# (actual Redis operations are handled by celery_tasks)
import redis.asyncio as aioredis

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
    "aioredis",
]