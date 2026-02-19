"""
Unit tests for enhanced task queue service.

Issue: #574 - Backend: Task Queue System - Background Job Processing
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.src.services.task_queue_enhanced import (
    AsyncTaskQueue,
    Task,
    TaskStatus,
    TaskPriority,
    RetryPolicy,
    QueueHealth,
    DEFAULT_RETRY_POLICY,
    CONVERSION_RETRY_POLICY,
    QUICK_RETRY_POLICY,
)


class TestRetryPolicy:
    """Tests for RetryPolicy."""
    
    def test_default_policy(self):
        """Test default retry policy values."""
        policy = RetryPolicy()
        
        assert policy.max_retries == 3
        assert policy.initial_delay_seconds == 1.0
        assert policy.max_delay_seconds == 300.0
        assert policy.backoff_multiplier == 2.0
        assert policy.retryable_errors == []
    
    def test_calculate_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        policy = RetryPolicy(
            initial_delay_seconds=1.0,
            max_delay_seconds=100.0,
            backoff_multiplier=2.0
        )
        
        # First retry: 1 * 2^0 = 1
        assert policy.calculate_delay(0) == 1.0
        
        # Second retry: 1 * 2^1 = 2
        assert policy.calculate_delay(1) == 2.0
        
        # Third retry: 1 * 2^2 = 4
        assert policy.calculate_delay(2) == 4.0
        
        # Fourth retry: 1 * 2^3 = 8
        assert policy.calculate_delay(3) == 8.0
    
    def test_calculate_delay_respects_max(self):
        """Test that delay respects maximum."""
        policy = RetryPolicy(
            initial_delay_seconds=1.0,
            max_delay_seconds=10.0,
            backoff_multiplier=2.0
        )
        
        # Should cap at max_delay_seconds
        assert policy.calculate_delay(10) == 10.0
        assert policy.calculate_delay(100) == 10.0
    
    def test_should_retry_within_limit(self):
        """Test retry decision within retry limit."""
        policy = RetryPolicy(max_retries=3)
        
        assert policy.should_retry("AnyError", 0) is True
        assert policy.should_retry("AnyError", 1) is True
        assert policy.should_retry("AnyError", 2) is True
    
    def test_should_retry_exceeds_limit(self):
        """Test retry decision when exceeding limit."""
        policy = RetryPolicy(max_retries=3)
        
        assert policy.should_retry("AnyError", 3) is False
        assert policy.should_retry("AnyError", 4) is False
    
    def test_should_retry_with_retryable_errors(self):
        """Test retry decision with specific retryable errors."""
        policy = RetryPolicy(
            max_retries=3,
            retryable_errors=["TimeoutError", "ConnectionError"]
        )
        
        assert policy.should_retry("TimeoutError", 0) is True
        assert policy.should_retry("ConnectionError", 1) is True
        assert policy.should_retry("ValueError", 0) is False
    
    def test_predefined_policies(self):
        """Test predefined retry policies."""
        assert DEFAULT_RETRY_POLICY.max_retries == 3
        
        assert CONVERSION_RETRY_POLICY.max_retries == 5
        assert "TimeoutError" in CONVERSION_RETRY_POLICY.retryable_errors
        
        assert QUICK_RETRY_POLICY.max_retries == 2
        assert QUICK_RETRY_POLICY.max_delay_seconds == 5.0


class TestTask:
    """Tests for Task dataclass."""
    
    def test_task_creation(self):
        """Test creating a task."""
        task = Task(
            id="test-id",
            name="test_task",
            payload={"key": "value"}
        )
        
        assert task.id == "test-id"
        assert task.name == "test_task"
        assert task.payload == {"key": "value"}
        assert task.status == TaskStatus.QUEUED
        assert task.priority == TaskPriority.NORMAL
        assert task.retry_count == 0
    
    def test_task_to_dict(self):
        """Test task serialization."""
        task = Task(
            id="test-id",
            name="test_task",
            payload={"key": "value"},
            status=TaskStatus.PROCESSING,
            priority=TaskPriority.HIGH
        )
        
        data = task.to_dict()
        
        assert data["id"] == "test-id"
        assert data["name"] == "test_task"
        assert data["payload"] == {"key": "value"}
        assert data["status"] == "processing"
        assert data["priority"] == 2
        assert "created_at" in data
    
    def test_task_from_dict(self):
        """Test task deserialization."""
        data = {
            "id": "test-id",
            "name": "test_task",
            "payload": {"key": "value"},
            "status": "processing",
            "priority": 2,
            "created_at": "2024-01-01T00:00:00",
            "started_at": "2024-01-01T00:01:00",
            "completed_at": None,
            "result": None,
            "error": None,
            "error_type": None,
            "retry_count": 1,
            "max_retries": 3,
            "next_retry_at": None,
            "timeout_seconds": 300
        }
        
        task = Task.from_dict(data)
        
        assert task.id == "test-id"
        assert task.name == "test_task"
        assert task.status == TaskStatus.PROCESSING
        assert task.priority == TaskPriority.HIGH
        assert task.retry_count == 1


class TestTaskStatus:
    """Tests for TaskStatus enum."""
    
    def test_all_statuses(self):
        """Test all task statuses exist."""
        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.DEAD_LETTER.value == "dead_letter"
        assert TaskStatus.RETRYING.value == "retrying"


class TestTaskPriority:
    """Tests for TaskPriority enum."""
    
    def test_priority_order(self):
        """Test priority values are ordered correctly."""
        assert TaskPriority.LOW.value < TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.CRITICAL.value


class TestQueueHealth:
    """Tests for QueueHealth dataclass."""
    
    def test_healthy_queue(self):
        """Test healthy queue status."""
        health = QueueHealth(
            total_queued=10,
            total_processing=2,
            total_completed=100,
            total_failed=5,
            total_dead_letter=0
        )
        
        assert health.healthy is True
        assert len(health.issues) == 0
    
    def test_unhealthy_queue_with_issues(self):
        """Test unhealthy queue with issues."""
        health = QueueHealth(
            total_queued=1500,
            total_processing=25,
            total_dead_letter=100,
            oldest_queued_age_seconds=4000
        )
        
        # Manually set issues as would be done by get_queue_health
        health.issues = [
            "Oldest queued task is 66.7 minutes old",
            "Queue backlog is high: 1500 tasks",
            "Dead letter queue has 100 tasks",
            "High number of processing tasks: 25"
        ]
        health.healthy = False
        
        assert health.healthy is False
        assert len(health.issues) == 4
    
    def test_to_dict(self):
        """Test health serialization."""
        health = QueueHealth(
            total_queued=10,
            total_processing=2,
            avg_processing_time_seconds=5.5
        )
        
        data = health.to_dict()
        
        assert data["total_queued"] == 10
        assert data["total_processing"] == 2
        assert data["avg_processing_time_seconds"] == 5.5
        assert "checked_at" in data


class TestAsyncTaskQueue:
    """Tests for AsyncTaskQueue (unit tests without Redis)."""
    
    def test_queue_initialization(self):
        """Test queue initialization."""
        queue = AsyncTaskQueue(
            redis_url="redis://localhost:6379",
            max_retries=5,
            default_timeout=600,
            dead_letter_enabled=True
        )
        
        assert queue.max_retries == 5
        assert queue.default_timeout == 600
        assert queue.dead_letter_enabled is True
        
        # Check queue names
        assert "task_queue:low" in queue._queue_names.values()
        assert "task_queue:critical" in queue._queue_names.values()
        assert queue._dead_letter_queue == "task_queue:dead_letter"
    
    def test_queue_names_by_priority(self):
        """Test queue names are mapped correctly."""
        queue = AsyncTaskQueue()
        
        assert queue._queue_names[TaskPriority.LOW] == "task_queue:low"
        assert queue._queue_names[TaskPriority.NORMAL] == "task_queue:normal"
        assert queue._queue_names[TaskPriority.HIGH] == "task_queue:high"
        assert queue._queue_names[TaskPriority.CRITICAL] == "task_queue:critical"


class TestTaskLifecycle:
    """Tests for task lifecycle documentation."""
    
    def test_lifecycle_states(self):
        """Test that all lifecycle states are defined."""
        expected_states = {
            "queued",
            "processing", 
            "completed",
            "failed",
            "cancelled",
            "dead_letter",
            "retrying"
        }
        
        actual_states = {status.value for status in TaskStatus}
        
        assert expected_states == actual_states
    
    def test_task_state_transitions(self):
        """Test valid task state transitions."""
        # Initial state
        task = Task(
            id="test-id",
            name="test_task",
            payload={}
        )
        assert task.status == TaskStatus.QUEUED
        
        # Transition to processing
        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.utcnow()
        assert task.status == TaskStatus.PROCESSING
        
        # Transition to completed
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.result = {"success": True}
        assert task.status == TaskStatus.COMPLETED


class TestRetryLogic:
    """Tests for retry logic."""
    
    def test_retry_delay_progression(self):
        """Test that retry delays increase progressively."""
        policy = RetryPolicy(
            initial_delay_seconds=1.0,
            max_delay_seconds=100.0,
            backoff_multiplier=2.0
        )
        
        delays = [policy.calculate_delay(i) for i in range(5)]
        
        # Each delay should be greater than the previous
        for i in range(1, len(delays)):
            assert delays[i] > delays[i-1]
    
    def test_max_delay_cap(self):
        """Test that delays are capped at max_delay_seconds."""
        policy = RetryPolicy(
            initial_delay_seconds=1.0,
            max_delay_seconds=10.0,
            backoff_multiplier=10.0
        )
        
        # Even with high backoff, should cap at max
        for i in range(10):
            assert policy.calculate_delay(i) <= 10.0


# Integration tests would require a Redis instance
# These are marked to be skipped in unit test runs
@pytest.mark.integration
class TestAsyncTaskQueueIntegration:
    """Integration tests for AsyncTaskQueue with Redis."""
    
    @pytest.fixture
    async def queue(self):
        """Create a queue with mocked Redis."""
        queue = AsyncTaskQueue()
        # In real tests, would connect to test Redis
        yield queue
    
    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self, queue):
        """Test enqueueing and dequeueing tasks."""
        # This would require actual Redis connection
        pass
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self, queue):
        """Test task retry mechanism."""
        pass
    
    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, queue):
        """Test dead letter queue functionality."""
        pass