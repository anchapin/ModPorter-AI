"""
Celery configuration for distributed task processing.

Issue: #1098 - Consolidate task queues: remove task_queue.py duplicate, migrate to Celery
Issue: #1151 - Pre-beta: Conversion job timeout handling and per-user rate limiting
"""

import os
from celery import Celery
from typing import Dict

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "portkit",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "services.celery_tasks",
    ],
)


# Conversion job timeout limits per subscription tier (Issue #1151)
# Creator: 5 minutes, Studio: 15 minutes, Enterprise: 30 minutes
CONVERSION_TIMEOUT_SECONDS: Dict[str, int] = {
    "free": 180,       # 3 minutes for free tier
    "payg": 300,       # 5 minutes for payg
    "creator": 300,    # 5 minutes for creator
    "creator_byok": 300,
    "pro": 600,        # 10 minutes for pro
    "studio": 900,     # 15 minutes for studio
    "studio_byok": 900,
    "enterprise": 1800,  # 30 minutes for enterprise
}


def get_conversion_timeout(tier: str) -> int:
    """Get conversion timeout in seconds for a subscription tier."""
    return CONVERSION_TIMEOUT_SECONDS.get(tier, CONVERSION_TIMEOUT_SECONDS["free"])


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    result_expires=86400,
    task_routes={
        "services.celery_tasks.conversion_task": {"queue": "high"},
        "services.celery_tasks.asset_conversion_task": {"queue": "high"},
        "services.celery_tasks.java_analysis_task": {"queue": "normal"},
        "services.celery_tasks.texture_extraction_task": {"queue": "normal"},
        "services.celery_tasks.model_conversion_task": {"queue": "normal"},
        "services.celery_tasks.heavy_task": {"queue": "low"},
    },
    task_annotations={
        "services.celery_tasks.conversion_task": {
            "rate_limit": "10/m",
        },
        "services.celery_tasks.asset_conversion_task": {
            "rate_limit": "50/m",
        },
    },
    beat_schedule={
        "cleanup-old-tasks": {
            "task": "services.celery_tasks.cleanup_old_tasks",
            "schedule": 3600.0,
        },
        "process-retry-queue": {
            "task": "services.celery_tasks.process_retry_queue",
            "schedule": 60.0,
        },
        "purge-orphaned-files": {
            "task": "services.celery_tasks.purge_orphaned_files",
            "schedule": 3600.0,
        },
    },
)
