"""
Celery tasks for distributed task processing.

Replaces the custom AsyncTaskQueue implementation from task_queue_enhanced.py
with Celery-backed workers for retry logic, dead-letter queues, and monitoring.

Issue: #1098 - Consolidate task queues: remove task_queue.py duplicate, migrate to Celery
"""

import json
import asyncio
import uuid
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

from celery import Celery, Task, shared_task
from celery.exceptions import SoftTimeLimitExceeded

import redis.asyncio as aioredis

from services.celery_config import celery_app, REDIS_URL

import logging

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


@dataclass
class RetryPolicy:
    """Configurable retry policy for tasks."""

    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 300.0
    backoff_multiplier: float = 2.0

    def calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for exponential backoff."""
        delay = self.initial_delay_seconds * (self.backoff_multiplier**retry_count)
        return min(delay, self.max_delay_seconds)


DEFAULT_RETRY_POLICY = RetryPolicy()
CONVERSION_RETRY_POLICY = RetryPolicy(
    max_retries=5,
    initial_delay_seconds=2.0,
    max_delay_seconds=600.0,
)


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
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "next_retry_at": (self.next_retry_at.isoformat() if self.next_retry_at else None),
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskData":
        return cls(
            id=data["id"],
            name=data["name"],
            payload=data["payload"],
            status=TaskStatus(data["status"]),
            priority=TaskPriority(data["priority"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=(
                datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
            ),
            result=data.get("result"),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            next_retry_at=(
                datetime.fromisoformat(data["next_retry_at"]) if data.get("next_retry_at") else None
            ),
            timeout_seconds=data.get("timeout_seconds", 300),
        )


QUEUE_NAMES = {
    TaskPriority.LOW: "celery:low",
    TaskPriority.NORMAL: "celery:normal",
    TaskPriority.HIGH: "celery:high",
    TaskPriority.CRITICAL: "celery:critical",
}
DEAD_LETTER_QUEUE = "celery:dead_letter"
PROCESSING_SET = "celery:processing"
METRICS_KEY = "celery:metrics"
RETRY_QUEUE = "celery:retry"


def _get_redis_sync():
    """Get synchronous Redis client for Celery tasks."""
    return redis.from_url(REDIS_URL, decode_responses=True)


import redis


class CeleryTaskBase(Task):
    """Base class for Celery tasks with retry logic."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        logger.info(f"Task {task_id} retrying: {exc}")


@celery_app.task(bind=True, base=CeleryTaskBase, name="services.celery_tasks.process_task")
def process_task(self, task_id: str) -> Dict[str, Any]:
    """
    Process a task by ID - called by Celery workers.

    This is the main entry point for all task processing.
    """
    r = _get_redis_sync()

    try:
        task_data = r.get(f"task:{task_id}")
        if not task_data:
            logger.error(f"Task {task_id} not found in Redis")
            return {"status": "error", "message": "Task not found"}

        task = TaskData.from_dict(json.loads(task_data))

        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now(timezone.utc)
        r.set(f"task:{task_id}", json.dumps(task.to_dict()), ex=86400)
        r.sadd(PROCESSING_SET, task_id)
        r.hincrby(METRICS_KEY, "tasks_dequeued", 1)

        logger.info(f"Processing task {task_id} ({task.name})")

        handler = _get_task_handler(task.name)
        if handler is None:
            raise ValueError(f"No handler for task type: {task.name}")

        result = handler(task.payload)

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        task.result = result
        r.set(f"task:{task_id}", json.dumps(task.to_dict()), ex=86400)
        r.srem(PROCESSING_SET, task_id)
        r.hincrby(METRICS_KEY, "tasks_completed", 1)

        logger.info(f"Task {task_id} completed")
        return {"status": "success", "result": result}

    except SoftTimeLimitExceeded:
        logger.error(f"Task {task_id} soft time limit exceeded")
        _fail_task(r, task_id, "Soft time limit exceeded", retry=False)
        return {"status": "error", "message": "Soft time limit exceeded"}
    except Exception as exc:
        logger.error(f"Task {task_id} failed: {exc}")
        retry = _fail_task(r, task_id, str(exc), retry=True)
        if retry:
            raise self.retry(exc=exc, countdown=5)
        return {"status": "error", "message": str(exc)}


def _get_task_handler(task_name: str):
    """Get the handler function for a task name."""
    handlers = {
        "conversion": handle_conversion_task,
        "asset_conversion": handle_asset_conversion_task,
        "java_analysis": handle_java_analysis_task,
        "texture_extraction": handle_texture_extraction_task,
        "model_conversion": handle_model_conversion_task,
    }
    return handlers.get(task_name)


def _fail_task(r, task_id: str, error: str, retry: bool = True) -> bool:
    """Mark task as failed and potentially schedule retry."""
    task_data = r.get(f"task:{task_id}")
    if not task_data:
        return False

    task = TaskData.from_dict(json.loads(task_data))
    task.error = error

    retry_count = task.retry_count
    max_retries = task.max_retries

    if retry and retry_count < max_retries:
        delay = DEFAULT_RETRY_POLICY.calculate_delay(retry_count)
        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay)

        task.retry_count = retry_count + 1
        task.status = TaskStatus.RETRYING
        task.started_at = None
        task.next_retry_at = next_retry

        r.zadd(RETRY_QUEUE, {task_id: next_retry.timestamp()})
        r.set(f"task:{task_id}", json.dumps(task.to_dict()), ex=86400)
        r.srem(PROCESSING_SET, task_id)
        r.hincrby(METRICS_KEY, "tasks_retried", 1)

        logger.info(f"Task {task_id} scheduled for retry ({retry_count + 1}/{max_retries})")
        return True
    else:
        if True:
            task.status = TaskStatus.DEAD_LETTER
            task.completed_at = datetime.now(timezone.utc)
            r.zadd(DEAD_LETTER_QUEUE, {task_id: time.time()})
            r.hincrby(METRICS_KEY, "tasks_dead_lettered", 1)
            logger.warning(f"Task {task_id} moved to dead letter queue: {error}")
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now(timezone.utc)
            r.hincrby(METRICS_KEY, "tasks_failed", 1)
            logger.error(f"Task {task_id} failed: {error}")

        r.set(f"task:{task_id}", json.dumps(task.to_dict()), ex=86400)
        r.srem(PROCESSING_SET, task_id)
        return False


@celery_app.task(name="services.celery_tasks.cleanup_old_tasks")
def cleanup_old_tasks(max_age_hours: int = 24) -> Dict[str, Any]:
    """Clean up old completed/failed tasks."""
    r = _get_redis_sync()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    cleaned = 0

    for key in r.scan_iter("task:*"):
        if key == METRICS_KEY:
            continue
        task_data = r.get(key)
        if task_data:
            task_dict = json.loads(task_data)
            status = task_dict.get("status")
            if status in ("completed", "failed", "cancelled", "dead_letter"):
                completed_at = task_dict.get("completed_at")
                if completed_at:
                    completed_time = datetime.fromisoformat(completed_at)
                    if completed_time < cutoff:
                        r.delete(key)
                        cleaned += 1

    logger.info(f"Cleaned up {cleaned} old tasks")
    return {"cleaned": cleaned}


@celery_app.task(name="services.celery_tasks.process_retry_queue")
def process_retry_queue() -> Dict[str, Any]:
    """Process tasks in the retry queue that are ready."""
    r = _get_redis_sync()
    now = time.time()
    task_ids = r.zrangebyscore(RETRY_QUEUE, min=0, max=now)
    requeued = 0

    for task_id in task_ids:
        r.zrem(RETRY_QUEUE, task_id)
        task_data = r.get(f"task:{task_id}")
        if task_data:
            task = TaskData.from_dict(json.loads(task_data))
            task.status = TaskStatus.QUEUED
            task.next_retry_at = None

            queue_name = QUEUE_NAMES[task.priority]
            r.zadd(queue_name, {task_id: time.time()})
            r.set(f"task:{task_id}", json.dumps(task.to_dict()), ex=86400)
            requeued += 1

    if requeued > 0:
        logger.info(f"Re-queued {requeued} tasks from retry queue")

    return {"requeued": requeued}


@celery_app.task(name="services.celery_tasks.enqueue_task")
def enqueue_task(
    name: str,
    payload: Dict[str, Any],
    priority: int = 1,
    max_retries: int = 3,
    timeout_seconds: int = 300,
) -> Dict[str, Any]:
    """Enqueue a new task via Celery."""
    r = _get_redis_sync()

    task = TaskData(
        id=str(uuid.uuid4()),
        name=name,
        payload=payload,
        priority=TaskPriority(priority),
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )

    r.set(f"task:{task.id}", json.dumps(task.to_dict()), ex=86400)

    queue_name = QUEUE_NAMES[task.priority]
    r.zadd(queue_name, {task.id: time.time()})
    r.hincrby(METRICS_KEY, "tasks_enqueued", 1)

    celery_app.send_task(
        "services.celery_tasks.process_task",
        args=[task.id],
        queue=queue_name,
        timeout=timeout_seconds,
    )

    logger.info(f"Task {task.id} ({name}) enqueued with priority {task.priority.name}")
    return {"task_id": task.id, "status": "queued"}


@celery_app.task(name="services.celery_tasks.get_task_status")
def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status by ID."""
    r = _get_redis_sync()
    task_data = r.get(f"task:{task_id}")
    if task_data:
        return json.loads(task_data)
    return None


@celery_app.task(name="services.celery_tasks.cancel_task")
def cancel_task(task_id: str) -> bool:
    """Cancel a queued task."""
    r = _get_redis_sync()
    task_data = r.get(f"task:{task_id}")
    if task_data:
        task_dict = json.loads(task_data)
        if task_dict["status"] == TaskStatus.QUEUED.value:
            task_dict["status"] = TaskStatus.CANCELLED.value
            task_dict["completed_at"] = datetime.now(timezone.utc).isoformat()
            r.set(f"task:{task_id}", json.dumps(task_dict), ex=86400)

            for queue_name in QUEUE_NAMES.values():
                r.zrem(queue_name, task_id)
            r.zrem(RETRY_QUEUE, task_id)

            r.hincrby(METRICS_KEY, "tasks_cancelled", 1)
            logger.info(f"Task {task_id} cancelled")
            return True
    return False


@celery_app.task(name="services.celery_tasks.get_queue_stats")
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


@celery_app.task(name="services.celery_tasks.get_dead_letter_tasks")
def get_dead_letter_tasks(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get tasks from the dead letter queue."""
    r = _get_redis_sync()
    task_ids = r.zrange(DEAD_LETTER_QUEUE, start=offset, end=offset + limit - 1)

    tasks = []
    for task_id in task_ids:
        task_data = r.get(f"task:{task_id}")
        if task_data:
            tasks.append(json.loads(task_data))

    return tasks


@celery_app.task(name="services.celery_tasks.reprocess_dead_letter_task")
def reprocess_dead_letter_task(task_id: str) -> bool:
    """Move a task from dead letter queue back to main queue."""
    r = _get_redis_sync()
    task_data = r.get(f"task:{task_id}")
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
    r.set(f"task:{task_id}", json.dumps(task.to_dict()), ex=86400)

    r.hincrby(METRICS_KEY, "tasks_reprocessed", 1)
    logger.info(f"Task {task_id} reprocessed from dead letter queue")

    return True


@celery_app.task(name="services.celery_tasks.health_check")
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
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def handle_conversion_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle conversion task - runs in worker process."""
    job_id = payload.get("job_id")
    file_id = payload.get("file_id")
    logger.info(f"Processing conversion job: {job_id}")
    return {
        "job_id": job_id,
        "status": "completed",
        "result_url": f"/api/v1/conversions/{job_id}/download",
    }


def handle_asset_conversion_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle asset conversion task."""
    asset_id = payload.get("asset_id")
    logger.info(f"Processing asset conversion: {asset_id}")
    return {"asset_id": asset_id, "status": "converted"}


def handle_java_analysis_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Java analysis task."""
    mod_id = payload.get("mod_id")
    logger.info(f"Processing Java analysis: {mod_id}")
    return {"mod_id": mod_id, "status": "analyzed"}


def handle_texture_extraction_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle texture extraction task."""
    jar_path = payload.get("jar_path")
    logger.info(f"Processing texture extraction: {jar_path}")
    return {"jar_path": jar_path, "status": "extracted"}


def handle_model_conversion_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle model conversion task."""
    model_id = payload.get("model_id")
    logger.info(f"Processing model conversion: {model_id}")
    return {"model_id": model_id, "status": "converted"}


# Legacy compatibility - expose same interface as old task_queue_enhanced
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

    queue_name = QUEUE_NAMES[priority]
    r.zadd(queue_name, {task.id: time.time()})
    r.hincrby(METRICS_KEY, "tasks_enqueued", 1)

    celery_app.send_task(
        "services.celery_tasks.process_task",
        args=[task.id],
        queue=queue_name,
        timeout=timeout_seconds,
    )

    return task


# Conversion task shortcuts
@shared_task(name="services.celery_tasks.conversion_task")
def conversion_task(job_id: str, file_id: str) -> Dict[str, Any]:
    """Convenience task for conversion jobs."""
    return handle_conversion_task({"job_id": job_id, "file_id": file_id})


@shared_task(name="services.celery_tasks.asset_conversion_task")
def asset_conversion_task(asset_id: str) -> Dict[str, Any]:
    """Convenience task for asset conversion."""
    return handle_asset_conversion_task({"asset_id": asset_id})


@shared_task(name="services.celery_tasks.java_analysis_task")
def java_analysis_task(mod_id: str) -> Dict[str, Any]:
    """Convenience task for Java analysis."""
    return handle_java_analysis_task({"mod_id": mod_id})


@shared_task(name="services.celery_tasks.texture_extraction_task")
def texture_extraction_task(jar_path: str) -> Dict[str, Any]:
    """Convenience task for texture extraction."""
    return handle_texture_extraction_task({"jar_path": jar_path})


@shared_task(name="services.celery_tasks.model_conversion_task")
def model_conversion_task(model_id: str) -> Dict[str, Any]:
    """Convenience task for model conversion."""
    return handle_model_conversion_task({"model_id": model_id})


@shared_task(name="services.celery_tasks.heavy_task")
def heavy_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Heavy processing task for batch operations."""
    logger.info(f"Processing heavy task")
    return {"status": "completed"}
