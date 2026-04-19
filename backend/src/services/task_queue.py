"""
Backward compatibility shim for services.task_queue.

This module re-exports symbols from celery_tasks to maintain compatibility
with code that imports from services.task_queue.

Issue: #1098 - Consolidate task queues to Celery
"""

from services.celery_tasks import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskData,
    RetryPolicy,
    DEFAULT_RETRY_POLICY,
    CONVERSION_RETRY_POLICY,
    celery_enqueue,
    get_task_status,
    cancel_task,
    get_queue_stats,
)


# Alias the async wrapper for backward compatibility
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
    "RetryPolicy",
    "DEFAULT_RETRY_POLICY",
    "CONVERSION_RETRY_POLICY",
    "enqueue_task",
    "get_task_status",
    "cancel_task",
    "get_queue_stats",
    "TaskQueue",
]
