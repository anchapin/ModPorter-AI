"""
Backward compatibility shim for services.task_queue.

This module re-exports symbols from celery_tasks to maintain compatibility
with code that imports from services.task_queue.

Issue: #1098 - Consolidate task queues to Celery
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional

import redis.asyncio as aioredis

from services.celery_config import celery_app, REDIS_URL

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enum with lifecycle states."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"
    RETRYING = "retrying"


class TaskPriority(Enum):
    """Task priority enum."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class Task:
    """Task class for backward compatibility."""

    def __init__(
        self,
        id: str = None,
        name: str = "",
        payload: Dict[str, Any] = None,
        status: TaskStatus = None,
        priority: TaskPriority = None,
        created_at: datetime = None,
        **kwargs,
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.payload = payload or {}
        self.status = status or TaskStatus.QUEUED
        self.priority = priority or TaskPriority.NORMAL
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "payload": self.payload,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TaskData:
    """Task data structure stored in Redis."""

    id: str
    name: str
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.QUEUED
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None
    timeout_seconds: int = 300

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "payload": self.payload,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskData":
        """Reconstruct TaskData from dictionary (e.g., from Redis JSON)."""
        status = data.get("status", "queued")
        if isinstance(status, str):
            status = TaskStatus(status)
        priority = data.get("priority", 1)
        if isinstance(priority, int):
            priority = TaskPriority(priority)
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        started_at = data.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)
        next_retry_at = data.get("next_retry_at")
        if isinstance(next_retry_at, str):
            next_retry_at = datetime.fromisoformat(next_retry_at)
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            payload=data.get("payload", {}),
            status=status,
            priority=priority,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            result=data.get("result"),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            next_retry_at=next_retry_at,
            timeout_seconds=data.get("timeout_seconds", 300),
        )


_task_queue: Optional["AsyncTaskQueue"] = None


class AsyncTaskQueue:
    """AsyncTaskQueue class for backward compatibility."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or REDIS_URL
        self._redis: Optional[redis.Redis] = None
        self._queue_names = {
            TaskPriority.LOW: "celery:low",
            TaskPriority.NORMAL: "celery:normal",
            TaskPriority.HIGH: "celery:high",
            TaskPriority.CRITICAL: "celery:critical",
        }
        self._dead_letter_queue = "celery:dead_letter"

    async def connect(self):
        """Connect to Redis."""
        self._redis = redis.from_url(self.redis_url, decode_responses=True)

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            self._redis.close()
            self._redis = None

    def _get_redis(self) -> redis.Redis:
        """Get Redis client."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def enqueue(
        self,
        name: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
    ) -> Task:
        """Enqueue a task."""
        return await enqueue_task(
            name=name, payload=payload, priority=priority, max_retries=max_retries
        )

    async def get_status(self, task_id: str) -> Optional[TaskData]:
        """Get task status."""
        return await get_task_status(task_id)

    async def cancel(self, task_id: str) -> bool:
        """Cancel a task."""
        return await cancel_task(task_id)

    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return await get_queue_stats()


async def get_task_queue() -> AsyncTaskQueue:
    """Get task queue singleton."""
    global _task_queue
    if _task_queue is None:
        _task_queue = AsyncTaskQueue()
        await _task_queue.connect()
    return _task_queue


async def celery_enqueue(
    name: str,
    payload: Dict[str, Any],
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = 3,
    timeout_seconds: int = 300,
) -> TaskData:
    """Async wrapper for enqueueing tasks - maintains compatibility with old code."""
    task = TaskData(
        id=str(uuid.uuid4()),
        name=name,
        payload=payload,
        priority=priority,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )

    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.set(f"task:{task.id}", json.dumps(task.to_dict()), ex=86400)

    queue_name = {
        TaskPriority.LOW: "celery:low",
        TaskPriority.NORMAL: "celery:normal",
        TaskPriority.HIGH: "celery:high",
        TaskPriority.CRITICAL: "celery:critical",
    }[priority]
    r.zadd(queue_name, {task.id: time.time()})
    r.hincrby("celery:metrics", "tasks_enqueued", 1)

    celery_app.send_task(
        "services.celery_tasks.process_task",
        args=[task.id],
        queue=queue_name,
        timeout=timeout_seconds,
    )

    return task


async def enqueue_task(
    name: str,
    payload: dict,
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = 3,
    timeout_seconds: int = 300,
):
    """Enqueue a task - delegates to Celery async wrapper."""
    return await celery_enqueue(
        name=name,
        payload=payload,
        priority=priority,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )


async def get_task_status(task_id: str) -> Optional[TaskData]:
    """Get task status from Redis."""
    r = redis.from_url(REDIS_URL, decode_responses=True)
    task_data = r.get(f"task:{task_id}")
    if task_data:
        return TaskData.from_dict(json.loads(task_data))
    return None


async def cancel_task(task_id: str) -> bool:
    """Cancel a queued task."""
    r = redis.from_url(REDIS_URL, decode_responses=True)
    task_data = r.get(f"task:{task_id}")
    if task_data:
        task_dict = json.loads(task_data)
        if task_dict["status"] == TaskStatus.QUEUED.value:
            task_dict["status"] = TaskStatus.CANCELLED.value
            task_dict["completed_at"] = datetime.now(timezone.utc).isoformat()
            r.set(f"task:{task_id}", json.dumps(task_dict), ex=86400)

            for queue_name in ["celery:low", "celery:normal", "celery:high", "celery:critical"]:
                r.zrem(queue_name, task_id)
            r.zrem("celery:retry", task_id)

            r.hincrby("celery:metrics", "tasks_cancelled", 1)
            return True
    return False


async def get_queue_stats() -> Dict[str, Any]:
    """Get queue statistics."""
    r = redis.from_url(REDIS_URL, decode_responses=True)

    stats = {
        "queues": {},
        "total_queued": 0,
        "total_processing": r.scard("celery:processing"),
        "total_dead_letter": r.zcard("celery:dead_letter"),
    }

    for priority, queue_name in {
        TaskPriority.LOW: "celery:low",
        TaskPriority.NORMAL: "celery:normal",
        TaskPriority.HIGH: "celery:high",
        TaskPriority.CRITICAL: "celery:critical",
    }.items():
        count = r.zcard(queue_name)
        stats["queues"][priority.name.lower()] = count
        stats["total_queued"] += count

    return stats


import redis


# For compatibility with code that expects TaskQueue class
class TaskQueue:
    """TaskQueue class for backward compatibility - delegates to Celery."""

    def __init__(self, *args, **kwargs):
        pass

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def enqueue(
        self,
        name: str,
        payload: dict,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
    ):
        return await enqueue_task(
            name=name, payload=payload, priority=priority, max_retries=max_retries
        )

    async def get_status(self, task_id: str):
        return await get_task_status(task_id)

    async def cancel(self, task_id: str):
        return await cancel_task(task_id)

    async def get_stats(self):
        return await get_queue_stats()


__all__ = [
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskData",
    "AsyncTaskQueue",
    "TaskQueue",
    "enqueue_task",
    "get_task_status",
    "cancel_task",
    "get_queue_stats",
    "get_task_queue",
    "_task_queue",
]
