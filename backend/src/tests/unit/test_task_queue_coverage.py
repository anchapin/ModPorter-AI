"""
Tests for task_queue service.

This module provides test coverage for the async task queue:
- TaskStatus enum
- TaskPriority enum  
- Task dataclass
- AsyncTaskQueue class
"""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone

from services.task_queue import (
    TaskStatus,
    TaskPriority,
    Task,
    AsyncTaskQueue,
)


class TestTaskStatus:
    """Test cases for TaskStatus enum."""

    def test_task_status_values(self):
        """Test TaskStatus enum has correct values."""
        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_from_value(self):
        """Test creating TaskStatus from string value."""
        status = TaskStatus("queued")
        assert status == TaskStatus.QUEUED


class TestTaskPriority:
    """Test cases for TaskPriority enum."""

    def test_task_priority_values(self):
        """Test TaskPriority enum has correct values."""
        assert TaskPriority.LOW.value == 0
        assert TaskPriority.NORMAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.CRITICAL.value == 3

    def test_task_priority_members(self):
        """Test TaskPriority enum members exist."""
        priorities = list(TaskPriority)
        assert len(priorities) == 4
        assert TaskPriority.LOW in priorities
        assert TaskPriority.NORMAL in priorities
        assert TaskPriority.HIGH in priorities
        assert TaskPriority.CRITICAL in priorities


class TestTask:
    """Test cases for Task dataclass."""

    def test_task_creation(self):
        """Test creating a Task with required fields."""
        task = Task(
            id="task-123",
            name="test_task",
            payload={"key": "value"}
        )
        
        assert task.id == "task-123"
        assert task.name == "test_task"
        assert task.payload == {"key": "value"}
        assert task.status == TaskStatus.QUEUED
        assert task.priority == TaskPriority.NORMAL

    def test_task_with_all_fields(self):
        """Test creating a Task with all fields."""
        created = datetime.now(timezone.utc)
        started = datetime.now(timezone.utc)
        completed = datetime.now(timezone.utc)
        
        task = Task(
            id="task-456",
            name="full_task",
            payload={"data": "test"},
            status=TaskStatus.PROCESSING,
            priority=TaskPriority.HIGH,
            created_at=created,
            started_at=started,
            completed_at=completed,
            result={"output": "result"},
            error=None,
            retry_count=1,
            max_retries=3
        )
        
        assert task.status == TaskStatus.PROCESSING
        assert task.priority == TaskPriority.HIGH
        assert task.retry_count == 1

    def test_task_to_dict(self):
        """Test Task.to_dict() method."""
        task = Task(
            id="task-789",
            name="dict_task",
            payload={"test": "data"}
        )
        
        task_dict = task.to_dict()
        
        assert task_dict["id"] == "task-789"
        assert task_dict["name"] == "dict_task"
        assert task_dict["payload"] == {"test": "data"}
        assert task_dict["status"] == "queued"
        assert task_dict["priority"] == 1

    def test_task_default_values(self):
        """Test Task has correct default values."""
        task = Task(id="test", name="test", payload={})
        
        assert task.status == TaskStatus.QUEUED
        assert task.priority == TaskPriority.NORMAL
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.result is None
        assert task.error is None


class TestAsyncTaskQueue:
    """Test cases for AsyncTaskQueue class."""

    def test_queue_names(self):
        """Test queue names for different priorities."""
        queue = AsyncTaskQueue()
        
        assert queue._queue_names[TaskPriority.LOW] == "task_queue:low"
        assert queue._queue_names[TaskPriority.NORMAL] == "task_queue:normal"
        assert queue._queue_names[TaskPriority.HIGH] == "task_queue:high"
        assert queue._queue_names[TaskPriority.CRITICAL] == "task_queue:critical"

    def test_default_values(self):
        """Test AsyncTaskQueue default values."""
        queue = AsyncTaskQueue()
        
        assert queue.redis_url == "redis://localhost:6379"
        assert queue.max_retries == 3
        assert queue.default_timeout == 300

    def test_custom_values(self):
        """Test AsyncTaskQueue with custom values."""
        queue = AsyncTaskQueue(
            redis_url="redis://custom:6379",
            max_retries=5,
            default_timeout=600
        )
        
        assert queue.redis_url == "redis://custom:6379"
        assert queue.max_retries == 5
        assert queue.default_timeout == 600

    def test_running_tasks_initialized(self):
        """Test AsyncTaskQueue initializes running tasks dict."""
        queue = AsyncTaskQueue()
        assert queue._running_tasks == {}
        assert isinstance(queue._running_tasks, dict)

    def test_queue_priority_count(self):
        """Test queue has all priority levels."""
        queue = AsyncTaskQueue()
        assert len(queue._queue_names) == 4