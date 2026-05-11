"""
Celery tasks subpackage.

Organized into logical modules:
- base: TaskStatus, TaskPriority, TaskData, retry policies, queue constants
- conversion_tasks: Handlers and tasks for conversion jobs
- cleanup_tasks: File cleanup and orphaned file purge tasks
- notification_tasks: Email and notification tasks
- queue_tasks: Queue management tasks (status, stats, dead letter)
- inference_tasks: LLM inference tasks

Issue: #1098 - Consolidate task queues
"""

from tasks.base import (
    TaskStatus,
    TaskPriority,
    TaskData,
    TimeoutResult,
    RetryPolicy,
    DEFAULT_RETRY_POLICY,
    CONVERSION_RETRY_POLICY,
    QUEUE_NAMES,
    DEAD_LETTER_QUEUE,
    PROCESSING_SET,
    METRICS_KEY,
    RETRY_QUEUE,
    TASK_KEY_PREFIX,
)

# Import handlers for task routing
from tasks.conversion_tasks import (
    handle_conversion_task,
    handle_asset_conversion_task,
    handle_model_conversion_task,
    handle_java_analysis_task,
    handle_texture_extraction_task,
)

# Import tasks for Celery worker
from tasks.conversion_tasks import (
    conversion_task,
    asset_conversion_task,
    model_conversion_task,
)

from tasks.cleanup_tasks import (
    cleanup_old_tasks,
    purge_orphaned_files,
    delete_input_file,
)

from tasks.queue_tasks import (
    get_task_status,
    cancel_task,
    get_queue_stats,
    get_dead_letter_tasks,
    reprocess_dead_letter_task,
    health_check,
    process_retry_queue,
)

from tasks.notification_tasks import (
    send_conversion_complete_email,
    send_conversion_failed_email,
    send_rate_limit_warning,
)

# Re-export Celery app for convenience
from services.celery_config import celery_app

__all__ = [
    # Base types
    "TaskStatus",
    "TaskPriority", 
    "TaskData",
    "TimeoutResult",
    "RetryPolicy",
    "DEFAULT_RETRY_POLICY",
    "CONVERSION_RETRY_POLICY",
    # Queue constants
    "QUEUE_NAMES",
    "DEAD_LETTER_QUEUE",
    "PROCESSING_SET",
    "METRICS_KEY",
    "RETRY_QUEUE",
    "TASK_KEY_PREFIX",
    # Handlers
    "handle_conversion_task",
    "handle_asset_conversion_task",
    "handle_model_conversion_task",
    "handle_java_analysis_task",
    "handle_texture_extraction_task",
    # Tasks
    "conversion_task",
    "asset_conversion_task",
    "model_conversion_task",
    "cleanup_old_tasks",
    "purge_orphaned_files",
    "delete_input_file",
    "get_task_status",
    "cancel_task",
    "get_queue_stats",
    "get_dead_letter_tasks",
    "reprocess_dead_letter_task",
    "health_check",
    "process_retry_queue",
    "send_conversion_complete_email",
    "send_conversion_failed_email",
    "send_rate_limit_warning",
    # Celery app
    "celery_app",
]