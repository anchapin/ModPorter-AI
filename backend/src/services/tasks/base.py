"""
Base types and constants for Celery tasks.

Issue: #1098 - Consolidate task queues
"""

from datetime import datetime, timedelta, timezone
from enum import Enum, IntEnum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


class TaskStatus(Enum):
    """Task status enum with lifecycle states."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"
    RETRYING = "retrying"
    TIMEOUT = "timeout"  # Issue #1151: Timeout status for clean timeout response


@dataclass
class TimeoutResult:
    """Structured timeout response (not a 500) - Issue #1151"""

    status: str = "timeout"
    message: str = ""
    timeout_seconds: int = 0
    tier: str = "free"
    can_retry: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": "timeout",
            "error_code": "CONVERSION_TIMEOUT",
            "message": self.message,
            "timeout_seconds": self.timeout_seconds,
            "tier": self.tier,
            "can_retry": self.can_retry,
            "retry_after_seconds": min(self.timeout_seconds * 2, 3600),
        }


class TaskPriority(IntEnum):
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


# Queue constants
QUEUE_NAMES = {
    TaskPriority.LOW: "portkit:queue:low",
    TaskPriority.NORMAL: "portkit:queue:normal",
    TaskPriority.HIGH: "portkit:queue:high",
    TaskPriority.CRITICAL: "portkit:queue:critical",
}
DEAD_LETTER_QUEUE = "portkit:dead_letter"
PROCESSING_SET = "portkit:processing"
METRICS_KEY = "portkit:metrics"
RETRY_QUEUE = "portkit:retry"
TASK_KEY_PREFIX = "portkit:task:"