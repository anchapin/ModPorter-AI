"""
Backward compatibility shim for task_queue_enhanced.

Re-exports symbols from celery_tasks and tasks/ subpackage.
This shim exists to maintain backward compatibility during migration.

Issue: #1098 - Consolidate task queues
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

# Re-export everything from celery_tasks for backward compatibility
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
    get_dead_letter_tasks,
    reprocess_dead_letter_task,
    health_check,
    process_retry_queue,
    enqueue_task,
    conversion_task,
    asset_conversion_task,
    java_analysis_task,
    texture_extraction_task,
    model_conversion_task,
    cleanup_old_tasks,
    purge_orphaned_files,
    delete_input_file,
)

# Re-export Task class for backward compatibility
from services.celery_tasks import TaskData as Task

# QueueHealth for enhanced queue monitoring
@dataclass
class QueueHealth:
    """Health metrics for queue monitoring."""
    
    is_healthy: bool
    queue_size: int
    processing_count: int
    dead_letter_count: int
    average_wait_time_ms: float
    last_health_check: datetime
    issues: List[str] = field(default_factory=list)
    
    @classmethod
    def from_stats(cls, stats: Dict) -> "QueueHealth":
        """Create QueueHealth from queue stats."""
        issues = []
        if stats.get("queue_size", 0) > 1000:
            issues.append("Queue size exceeds 1000")
        if stats.get("dead_letter_count", 0) > 100:
            issues.append("Dead letter queue backlog detected")
        return cls(
            is_healthy=len(issues) == 0,
            queue_size=stats.get("queue_size", 0),
            processing_count=stats.get("processing_count", 0),
            dead_letter_count=stats.get("dead_letter_count", 0),
            average_wait_time_ms=stats.get("avg_wait_time_ms", 0),
            last_health_check=datetime.now(timezone.utc),
            issues=issues,
        )


# Retry policy presets from enhanced queue
QUICK_RETRY_POLICY = RetryPolicy(
    max_retries=1,
    initial_delay_seconds=0.5,
    max_delay_seconds=10.0,
)


# AsyncTaskQueue for backward compatibility
class AsyncTaskQueue:
    """Async task queue with Redis backend - thin wrapper around celery_tasks functions."""
    
    def __init__(self):
        pass
    
    async def enqueue(self, task_name: str, payload: Dict, priority: TaskPriority = TaskPriority.NORMAL) -> TaskData:
        return await enqueue_task(task_name, payload, priority)
    
    async def get_status(self, task_id: str) -> Optional[Dict]:
        return get_task_status(task_id)
    
    async def cancel(self, task_id: str) -> bool:
        return cancel_task(task_id)
    
    async def get_stats(self) -> Dict:
        return get_queue_stats()
    
    async def health(self) -> QueueHealth:
        stats = await self.get_stats()
        return QueueHealth.from_stats(stats)


__all__ = [
    # Base types
    "TaskStatus",
    "TaskPriority", 
    "Task",
    "RetryPolicy",
    "QueueHealth",
    "TimeoutResult",
    # Policy presets
    "DEFAULT_RETRY_POLICY",
    "CONVERSION_RETRY_POLICY",
    "QUICK_RETRY_POLICY",
    # Functions
    "enqueue_task",
    "get_task_status",
    "cancel_task",
    "get_queue_stats",
    "get_dead_letter_tasks",
    "reprocess_dead_letter_task",
    "health_check",
    "process_retry_queue",
    # Queue class
    "AsyncTaskQueue",
    # Task data
    "TaskData",
]
