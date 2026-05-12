"""
Backward compatibility shim for services.task_queue.

Re-exports symbols from celery_tasks to maintain compatibility
with code that imports from services.task_queue.

Issue: #1098 - Consolidate task queues to Celery
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import redis.asyncio as aioredis

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

logger = logging.getLogger(__name__)


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

    async def connect(self) -> None:
        """Connect to Redis"""
        self._redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        logger.info("Connected to Redis for task queue")

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis")

    async def _get_redis(self) -> aioredis.Redis:
        """Get Redis client, connecting if needed"""
        if self._redis is None:
            await self.connect()
        return self._redis

    async def enqueue(
        self,
        name: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: Optional[int] = None,
    ):
        """Add a task to the queue."""
        redis = await self._get_redis()

        task = Task(
            id=str(uuid.uuid4()),
            name=name,
            payload=payload,
            priority=priority,
            max_retries=max_retries if max_retries is not None else self.max_retries,
        )

        # Store task data
        await redis.set(
            f"task:{task.id}",
            json.dumps(task.to_dict()),
            ex=86400,
        )

        # Add to priority queue
        queue_name = self._queue_names[priority]
        await redis.zadd(queue_name, {task.id: priority.value})

        logger.info(f"Task {task.id} ({name}) enqueued with priority {priority.name}")

        return task

    async def dequeue(self, priority: TaskPriority = None, timeout: int = 5) -> Optional[Task]:
        """Get the next task from the queue. Checks queues in priority order."""
        redis = await self._get_redis()

        # Check queues in priority order if no specific priority given
        priorities = (
            [priority]
            if priority
            else [
                TaskPriority.CRITICAL,
                TaskPriority.HIGH,
                TaskPriority.NORMAL,
                TaskPriority.LOW,
            ]
        )

        for p in priorities:
            queue_name = self._queue_names[p]
            task_ids = await redis.zpopmin(queue_name, count=1)

            if task_ids:
                task_id = (
                    task_ids[0][0].decode()
                    if isinstance(task_ids[0][0], bytes)
                    else task_ids[0][0]
                )

                task_data = await redis.get(f"task:{task_id}")

                if task_data:
                    task_dict = json.loads(task_data)
                    task = Task(
                        id=task_dict["id"],
                        name=task_dict["name"],
                        payload=task_dict["payload"],
                        status=TaskStatus(task_dict["status"]),
                        priority=TaskPriority(task_dict["priority"]),
                        created_at=datetime.fromisoformat(task_dict["created_at"]),
                        retry_count=task_dict.get("retry_count", 0),
                        max_retries=task_dict.get("max_retries", self.max_retries),
                    )

                    task.status = TaskStatus.PROCESSING
                    task.started_at = datetime.now(timezone.utc)

                    await redis.set(f"task:{task.id}", json.dumps(task.to_dict()), ex=86400)

                    logger.info(f"Task {task.id} ({task.name}) dequeued")
                    return task

        return None

    async def complete(self, task_id: str, result: Any = None) -> None:
        """Mark a task as completed"""
        redis = await self._get_redis()

        task_data = await redis.get(f"task:{task_id}")
        if task_data:
            task_dict = json.loads(task_data)
            task_dict["status"] = TaskStatus.COMPLETED.value
            task_dict["completed_at"] = datetime.now(timezone.utc).isoformat()
            task_dict["result"] = result

            await redis.set(f"task:{task_id}", json.dumps(task_dict), ex=86400)
            logger.info(f"Task {task_id} completed")

    async def fail(self, task_id: str, error: str, retry: bool = True) -> bool:
        """Mark a task as failed"""
        redis = await self._get_redis()

        task_data = await redis.get(f"task:{task_id}")
        if not task_data:
            return False

        task_dict = json.loads(task_data)
        task_dict["error"] = error

        retry_count = task_dict.get("retry_count", 0)
        max_retries = task_dict.get("max_retries", self.max_retries)

        if retry and retry_count < max_retries:
            # Retry: increment count and re-queue
            task_dict["retry_count"] = retry_count + 1
            task_dict["status"] = TaskStatus.PENDING.value
            priority = TaskPriority(task_dict["priority"])
            queue_name = self._queue_names[priority]
            await redis.zadd(queue_name, {task_id: priority.value})
            await redis.set(f"task:{task_id}", json.dumps(task_dict), ex=86400)
            logger.info(f"Task {task_id} failed, retry {retry_count + 1}/{max_retries}")
            return True
        else:
            # Move to dead letter
            task_dict["status"] = TaskStatus.FAILED.value
            await redis.set(f"task:{task_id}", json.dumps(task_dict), ex=86400)
            if self.dead_letter_enabled:
                await redis.zadd(self._dead_letter_queue, {task_id: 1})
            logger.info(f"Task {task_id} failed permanently, moved to dead letter")
            return False

    async def get_status(self, task_id: str) -> Optional[Dict]:
        """Get task status"""
        redis = await self._get_redis()
        task_data = await redis.get(f"task:{task_id}")
        if task_data:
            return json.loads(task_data)
        return None

    async def cancel(self, task_id: str) -> bool:
        """Cancel a task"""
        redis = await self._get_redis()
        task_data = await redis.get(f"task:{task_id}")
        if task_data:
            task_dict = json.loads(task_data)
            task_dict["status"] = TaskStatus.CANCELLED.value
            task_dict["cancelled_at"] = datetime.now(timezone.utc).isoformat()
            await redis.set(f"task:{task_id}", json.dumps(task_dict), ex=86400)
            # Remove from queue
            for q in self._queue_names.values():
                await redis.zrem(q, task_id)
            logger.info(f"Task {task_id} cancelled")
            return True
        return False

    async def get_stats(self) -> Dict:
        """Get queue statistics"""
        redis = await self._get_redis()
        stats = {"total_queued": 0, "total_processing": 0, "total_dead_letter": 0, "queues": {}}

        for name, queue_name in self._queue_names.items():
            count = await redis.zcard(queue_name)
            stats["queues"][name.value] = count
            stats["total_queued"] += count

        stats["total_dead_letter"] = await redis.zcard(self._dead_letter_queue)

        processing_keys = []
        async for key in redis.scan_iter(match="task_queue:processing:*"):
            processing_keys.append(key)
        stats["total_processing"] = len(processing_keys)

        return stats

    def close(self):
        """Close the queue connection."""
        self._redis = None

    def get_redis(self):
        """Get the Redis client (sync stub for tests)."""
        return self._redis


# Module-level singleton for backward compatibility
_task_queue: Optional[AsyncTaskQueue] = None


async def get_task_queue() -> AsyncTaskQueue:
    """Get the async task queue instance."""
    global _task_queue

    if _task_queue is None:
        _task_queue = AsyncTaskQueue(redis_url="redis://localhost:6379")

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
    "aioredis",
]
