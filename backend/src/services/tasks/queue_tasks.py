"""
Queue management Celery tasks.

Includes:
- Task status queries
- Queue statistics
- Dead letter queue management
- Health checks
- Retry queue processing

Issue: #1098 - Consolidate task queues
"""

from typing import Dict, Any, Optional, List
from celery import Celery
import logging
import json
import time

from tasks.base import (
    TaskStatus,
    TaskPriority,
    TaskData,
    QUEUE_NAMES,
    DEAD_LETTER_QUEUE,
    PROCESSING_SET,
    METRICS_KEY,
    RETRY_QUEUE,
)
from services.celery_config import celery_app, REDIS_URL
import redis

logger = logging.getLogger(__name__)


def _get_redis_sync():
    """Get synchronous Redis client for Celery tasks."""
    return redis.from_url(REDIS_URL, decode_responses=True)


@celery_app.task(name="services.tasks.queue_tasks.get_task_status")
def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status by ID."""
    r = _get_redis_sync()
    task_data = r.get(f"portkit:task:{task_id}")
    if task_data:
        return json.loads(task_data)
    return None


@celery_app.task(name="services.tasks.queue_tasks.cancel_task")
def cancel_task(task_id: str) -> bool:
    """Cancel a queued task."""
    r = _get_redis_sync()
    task_data = r.get(f"portkit:task:{task_id}")
    if task_data:
        task_dict = json.loads(task_data)
        if task_dict["status"] == TaskStatus.QUEUED.value:
            task_dict["status"] = TaskStatus.CANCELLED.value
            task_dict["completed_at"] = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat()
            r.set(f"portkit:task:{task_id}", json.dumps(task_dict), ex=86400)

            for queue_name in QUEUE_NAMES.values():
                r.zrem(queue_name, task_id)
            r.zrem(RETRY_QUEUE, task_id)

            r.hincrby(METRICS_KEY, "tasks_cancelled", 1)
            logger.info(f"Task {task_id} cancelled")
            return True
    return False


@celery_app.task(name="services.tasks.queue_tasks.get_queue_stats")
def get_queue_stats() -> Dict[str, Any]:
    """Get queue statistics."""
    r = _get_redis_sync()

    stats = {
        "queues": {},
        "total_queued": 0,
        "total_processing": r.scard(PROCESSING_SET),
        "total_dead_letter": r.zcard(DEAD_LETTER_QUEUE),
    }

    for priority, queue_name in QUEUE_NAMES.items():
        count = r.zcard(queue_name)
        stats["queues"][priority.name.lower()] = count
        stats["total_queued"] += count

    return stats


@celery_app.task(name="services.tasks.queue_tasks.get_dead_letter_tasks")
def get_dead_letter_tasks(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get tasks from the dead letter queue."""
    r = _get_redis_sync()
    task_ids = r.zrange(DEAD_LETTER_QUEUE, start=offset, end=offset + limit - 1)

    tasks = []
    for task_id in task_ids:
        task_data = r.get(f"portkit:task:{task_id}")
        if task_data:
            tasks.append(json.loads(task_data))

    return tasks


@celery_app.task(name="services.tasks.queue_tasks.reprocess_dead_letter_task")
def reprocess_dead_letter_task(task_id: str) -> bool:
    """Move a task from dead letter queue back to main queue."""
    r = _get_redis_sync()
    task_data = r.get(f"portkit:task:{task_id}")
    if not task_data:
        return False

    task = TaskData.from_dict(json.loads(task_data))

    r.zrem(DEAD_LETTER_QUEUE, task_id)

    task.status = TaskStatus.QUEUED
    task.retry_count = 0
    task.error = None
    task.started_at = None
    task.completed_at = None

    queue_name = QUEUE_NAMES[task.priority]
    r.zadd(queue_name, {task_id: time.time()})
    r.set(f"portkit:task:{task_id}", json.dumps(task.to_dict()), ex=86400)

    r.hincrby(METRICS_KEY, "tasks_reprocessed", 1)
    logger.info(f"Task {task_id} reprocessed from dead letter queue")

    return True


@celery_app.task(name="services.tasks.queue_tasks.health_check")
def health_check() -> Dict[str, Any]:
    """Check queue health."""
    stats = get_queue_stats()
    issues = []

    if stats["total_queued"] > 1000:
        issues.append(f"Queue backlog is high: {stats['total_queued']} tasks")

    if stats["total_dead_letter"] > 50:
        issues.append(f"Dead letter queue has {stats['total_dead_letter']} tasks")

    return {
        "healthy": len(issues) == 0,
        "issues": issues,
        "stats": stats,
        "checked_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }


@celery_app.task(name="services.tasks.queue_tasks.process_retry_queue")
def process_retry_queue() -> Dict[str, Any]:
    """Process tasks in the retry queue that are ready."""
    r = _get_redis_sync()
    now = time.time()
    task_ids = r.zrangebyscore(RETRY_QUEUE, min=0, max=now)
    requeued = 0

    for task_id in task_ids:
        r.zrem(RETRY_QUEUE, task_id)
        task_data = r.get(f"portkit:task:{task_id}")
        if task_data:
            task = TaskData.from_dict(json.loads(task_data))
            task.status = TaskStatus.QUEUED
            task.next_retry_at = None

            queue_name = QUEUE_NAMES[task.priority]
            r.zadd(queue_name, {task_id: time.time()})
            r.set(f"portkit:task:{task_id}", json.dumps(task.to_dict()), ex=86400)
            requeued += 1

    if requeued > 0:
        logger.info(f"Re-queued {requeued} tasks from retry queue")

    return {"requeued": requeued}