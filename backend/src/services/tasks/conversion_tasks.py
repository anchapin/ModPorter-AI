"""
Conversion-related Celery tasks.

Issue: #1098 - Consolidate task queues
"""

from typing import Dict, Any, Optional, List
from celery import shared_task
import logging

from tasks.base import (
    TaskData,
    TaskPriority,
    QUEUE_NAMES,
    METRICS_KEY,
    DEAD_LETTER_QUEUE,
    PROCESSING_SET,
    RETRY_QUEUE,
    DEFAULT_RETRY_POLICY,
)
from services.celery_config import celery_app, REDIS_URL
import redis
import time
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _get_redis_sync():
    """Get synchronous Redis client for Celery tasks."""
    return redis.from_url(REDIS_URL, decode_responses=True)


def _run_async(coro):
    """Run an async coroutine from synchronous context."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result(timeout=300)


def handle_conversion_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle conversion task - runs in worker process."""
    from services.conversion_service import process_conversion_task as _process

    job_id = payload.get("job_id")
    file_id = payload.get("file_id")
    logger.info(f"Processing conversion job: {job_id}")
    try:
        return _run_async(_process(payload))
    except Exception as e:
        logger.error(f"Conversion job {job_id} failed: {e}")
        raise


def handle_asset_conversion_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle asset conversion task."""
    from services.asset_conversion_service import asset_conversion_service as _svc

    asset_id = payload.get("asset_id")
    logger.info(f"Processing asset conversion: {asset_id}")
    try:
        return _run_async(_svc.convert_asset(asset_id))
    except Exception as e:
        logger.error(f"Asset conversion {asset_id} failed: {e}")
        raise


def handle_model_conversion_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle model conversion task."""
    from services.asset_conversion_service import asset_conversion_service as _svc

    model_id = payload.get("model_id")
    logger.info(f"Processing model conversion: {model_id}")
    try:
        return _run_async(_svc.convert_asset(model_id))
    except Exception as e:
        logger.error(f"Model conversion {model_id} failed: {e}")
        raise


@shared_task(name="services.tasks.conversion_tasks.conversion_task")
def conversion_task(job_id: str, file_id: str) -> Dict[str, Any]:
    """Convenience task for conversion jobs."""
    return handle_conversion_task({"job_id": job_id, "file_id": file_id})


@shared_task(name="services.tasks.conversion_tasks.asset_conversion_task")
def asset_conversion_task(asset_id: str) -> Dict[str, Any]:
    """Convenience task for asset conversion."""
    return handle_asset_conversion_task({"asset_id": asset_id})


@shared_task(name="services.tasks.conversion_tasks.model_conversion_task")
def model_conversion_task(model_id: str) -> Dict[str, Any]:
    """Convenience task for model conversion."""
    return handle_model_conversion_task({"model_id": model_id})


async def enqueue_conversion_task(
    job_id: str,
    file_id: str,
    priority: TaskPriority = TaskPriority.NORMAL,
    subscription_tier: str = "free",
    timeout_seconds: int = 300,
) -> TaskData:
    """Enqueue a conversion task with proper timeout handling."""
    from services.celery_config import get_conversion_timeout

    if timeout_seconds == 300:
        timeout_seconds = get_conversion_timeout(subscription_tier)

    payload = {
        "job_id": job_id,
        "file_id": file_id,
        "subscription_tier": subscription_tier,
    }

    task = TaskData(
        id=str(uuid.uuid4()),
        name="conversion",
        payload=payload,
        priority=priority,
        max_retries=3,
        timeout_seconds=timeout_seconds,
    )

    r = _get_redis_sync()
    r.set(f"portkit:task:{task.id}", __import__("json").dumps(task.to_dict()), ex=86400)

    queue_name = QUEUE_NAMES[priority]
    r.zadd(queue_name, {task.id: time.time()})
    r.hincrby(METRICS_KEY, "tasks_enqueued", 1)

    celery_app.send_task(
        "services.tasks.process_task",
        args=[task.id],
        queue=queue_name,
        timeout=timeout_seconds,
        soft_timeout=timeout_seconds - 30,
    )

    return task


# Legacy compatibility alias
enqueue_task = enqueue_conversion_task
