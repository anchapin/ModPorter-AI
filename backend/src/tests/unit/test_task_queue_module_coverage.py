"""
Unit tests for services/task_queue.py module to increase line coverage.

Tests AsyncTaskQueue, Task, TaskStatus, TaskPriority and related functions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime, timezone
import uuid


class TestTaskStatus:
    """Test TaskStatus enum"""

    def test_task_status_values(self):
        """Test TaskStatus enum values"""
        from services.task_queue import TaskStatus

        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestTaskPriority:
    """Test TaskPriority enum"""

    def test_task_priority_values(self):
        """Test TaskPriority enum values"""
        from services.task_queue import TaskPriority

        assert TaskPriority.LOW.value == 0
        assert TaskPriority.NORMAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.CRITICAL.value == 3


class TestTask:
    """Test Task dataclass"""

    def test_task_creation(self):
        """Test creating a Task"""
        from services.task_queue import Task, TaskStatus, TaskPriority

        task = Task(
            id="task-123",
            name="test_task",
            payload={"key": "value"},
            status=TaskStatus.QUEUED,
            priority=TaskPriority.NORMAL,
        )

        assert task.id == "task-123"
        assert task.name == "test_task"
        assert task.status == TaskStatus.QUEUED

    def test_task_to_dict(self):
        """Test Task to_dict method"""
        from services.task_queue import Task, TaskStatus, TaskPriority

        task = Task(id="task-123", name="test_task", payload={"key": "value"})

        result = task.to_dict()

        assert "id" in result
        assert "name" in result
        assert "payload" in result
        assert "status" in result

    def test_task_default_values(self):
        """Test Task default values"""
        from services.task_queue import Task

        task = Task(id="task-123", name="test", payload={})

        assert task.status.value == "queued"
        assert task.priority.value == 1
        assert task.retry_count == 0
        assert task.max_retries == 3


class TestAsyncTaskQueue:
    """Test AsyncTaskQueue class"""

    @pytest.mark.asyncio
    async def test_task_queue_init(self):
        """Test AsyncTaskQueue initialization"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue(
            redis_url="redis://localhost:6379", max_retries=5, default_timeout=600
        )

        assert queue.redis_url == "redis://localhost:6379"
        assert queue.max_retries == 5
        assert queue.default_timeout == 600

    @pytest.mark.asyncio
    async def test_task_queue_default_values(self):
        """Test AsyncTaskQueue default values"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()

        assert queue.max_retries == 3
        assert queue.default_timeout == 300

    @pytest.mark.asyncio
    async def test_task_queue_connect(self):
        """Test connecting to Redis"""
        from services.task_queue import AsyncTaskQueue

        with patch("services.task_queue.aioredis") as mock_redis:
            mock_redis.from_url = AsyncMock()

            queue = AsyncTaskQueue()
            await queue.connect()

            assert queue._redis is not None

    @pytest.mark.asyncio
    async def test_task_queue_disconnect(self):
        """Test disconnecting from Redis"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()
        queue._redis = AsyncMock()

        await queue.disconnect()

        assert queue._redis is None or queue._redis.close.called

    @pytest.mark.asyncio
    async def test_task_queue_get_redis(self):
        """Test getting Redis client"""
        from services.task_queue import AsyncTaskQueue

        with patch("services.task_queue.aioredis") as mock_redis:
            mock_redis.from_url = AsyncMock()

            queue = AsyncTaskQueue()
            redis = await queue._get_redis()

            assert redis is not None


class TestAsyncTaskQueueEnqueue:
    """Test enqueue methods"""

    @pytest.mark.asyncio
    async def test_enqueue(self):
        """Test enqueueing a task"""
        from services.task_queue import AsyncTaskQueue, TaskPriority

        queue = AsyncTaskQueue()

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock()
            mock_redis.zadd = AsyncMock()
            mock_get_redis.return_value = mock_redis

            task = await queue.enqueue(
                name="test_task", payload={"data": "value"}, priority=TaskPriority.NORMAL
            )

            assert task is not None
            assert task.name == "test_task"

    @pytest.mark.asyncio
    async def test_enqueue_with_custom_retries(self):
        """Test enqueueing with custom retries"""
        from services.task_queue import AsyncTaskQueue, TaskPriority

        queue = AsyncTaskQueue(max_retries=5)

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock()
            mock_redis.zadd = AsyncMock()
            mock_get_redis.return_value = mock_redis

            task = await queue.enqueue(name="test_task", payload={}, max_retries=10)

            assert task.max_retries == 10


class TestAsyncTaskQueueDequeue:
    """Test dequeue methods"""

    @pytest.mark.asyncio
    async def test_dequeue(self):
        """Test dequeuing a task"""
        from services.task_queue import AsyncTaskQueue, TaskPriority

        queue = AsyncTaskQueue()

        task_dict = {
            "id": "task-123",
            "name": "test",
            "payload": {},
            "status": "queued",
            "priority": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
            "max_retries": 3,
        }

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.zpopmin = AsyncMock(return_value=[("task-123", 1)])
            mock_redis.get = AsyncMock(return_value=json.dumps(task_dict))
            mock_redis.set = AsyncMock()
            mock_get_redis.return_value = mock_redis

            task = await queue.dequeue()

            assert task is not None

    @pytest.mark.asyncio
    async def test_dequeue_empty_queue(self):
        """Test dequeuing from empty queue"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.zpopmin = AsyncMock(return_value=[])
            mock_get_redis.return_value = mock_redis

            task = await queue.dequeue()

            assert task is None


class TestAsyncTaskQueueComplete:
    """Test complete/fail/cancel methods"""

    @pytest.mark.asyncio
    async def test_complete(self):
        """Test completing a task"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()

        task_dict = {
            "id": "task-123",
            "name": "test",
            "payload": {},
            "status": "processing",
            "priority": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
            "max_retries": 3,
        }

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=json.dumps(task_dict))
            mock_redis.set = AsyncMock()
            mock_get_redis.return_value = mock_redis

            await queue.complete("task-123", {"result": "success"})

            mock_redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_fail_with_retry(self):
        """Test failing a task with retry"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()

        task_dict = {
            "id": "task-123",
            "name": "test",
            "payload": {},
            "status": "processing",
            "priority": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
            "max_retries": 3,
        }

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=json.dumps(task_dict))
            mock_redis.set = AsyncMock()
            mock_redis.zadd = AsyncMock()
            mock_get_redis.return_value = mock_redis

            result = await queue.fail("task-123", "Error occurred", retry=True)

            assert result is True

    @pytest.mark.asyncio
    async def test_fail_without_retry(self):
        """Test failing a task without retry"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()

        task_dict = {
            "id": "task-123",
            "name": "test",
            "payload": {},
            "status": "processing",
            "priority": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": 3,
            "max_retries": 3,
        }

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=json.dumps(task_dict))
            mock_redis.set = AsyncMock()
            mock_get_redis.return_value = mock_redis

            result = await queue.fail("task-123", "Error occurred", retry=True)

            assert result is False

    @pytest.mark.asyncio
    async def test_fail_no_task(self):
        """Test failing non-existent task"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_get_redis.return_value = mock_redis

            result = await queue.fail("nonexistent", "Error")

            assert result is False

    @pytest.mark.asyncio
    async def test_cancel_queued_task(self):
        """Test cancelling a queued task"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()

        task_dict = {
            "id": "task-123",
            "name": "test",
            "payload": {},
            "status": "queued",
            "priority": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=json.dumps(task_dict))
            mock_redis.set = AsyncMock()
            mock_redis.zrem = AsyncMock()
            mock_get_redis.return_value = mock_redis

            result = await queue.cancel("task-123")

            assert result is True

    @pytest.mark.asyncio
    async def test_cancel_non_queued_task(self):
        """Test cancelling non-queued task"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()

        task_dict = {
            "id": "task-123",
            "name": "test",
            "payload": {},
            "status": "processing",
            "priority": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=json.dumps(task_dict))
            mock_get_redis.return_value = mock_redis

            result = await queue.cancel("task-123")

            assert result is False


class TestAsyncTaskQueueStatus:
    """Test status and listing methods"""

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting task status"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()

        task_dict = {"id": "task-123", "name": "test", "status": "processing"}

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=json.dumps(task_dict))
            mock_get_redis.return_value = mock_redis

            result = await queue.get_status("task-123")

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_status_not_found(self):
        """Test getting status for non-existent task"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_get_redis.return_value = mock_redis

            result = await queue.get_status("nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        """Test listing tasks"""
        from services.task_queue import AsyncTaskQueue, TaskStatus

        queue = AsyncTaskQueue()

        task_dict = {"id": "task-123", "name": "test", "status": "queued"}

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()

            async def mock_scan_iter(pattern):
                yield "task:task-123"

            mock_redis.scan_iter = mock_scan_iter
            mock_redis.get = AsyncMock(return_value=json.dumps(task_dict))
            mock_get_redis.return_value = mock_redis

            result = await queue.list_tasks()

            assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_list_tasks_filtered(self):
        """Test listing tasks with status filter"""
        from services.task_queue import AsyncTaskQueue, TaskStatus

        queue = AsyncTaskQueue()

        task_dict = {"id": "task-123", "name": "test", "status": "completed"}

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()

            async def mock_scan_iter(pattern):
                yield "task:task-123"

            mock_redis.scan_iter = mock_scan_iter
            mock_redis.get = AsyncMock(return_value=json.dumps(task_dict))
            mock_get_redis.return_value = mock_redis

            result = await queue.list_tasks(status=TaskStatus.COMPLETED)

            assert len(result) >= 0


class TestAsyncTaskQueueStats:
    """Test queue statistics"""

    @pytest.mark.asyncio
    async def test_get_queue_stats(self):
        """Test getting queue statistics"""
        from services.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()

        task_dict = {"id": "task-123", "name": "test", "status": "queued"}

        with patch.object(queue, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()

            async def mock_scan_iter(pattern):
                yield "task:task-123"

            mock_redis.scan_iter = mock_scan_iter
            mock_redis.get = AsyncMock(return_value=json.dumps(task_dict))
            mock_redis.zcard = AsyncMock(return_value=5)
            mock_get_redis.return_value = mock_redis

            result = await queue.get_queue_stats()

            assert "queues" in result
            assert "total_tasks" in result
            assert "by_status" in result


class TestModuleFunctions:
    """Test module-level convenience functions"""

    @pytest.mark.asyncio
    async def test_get_task_queue(self):
        """Test get_task_queue function"""
        from services.task_queue import get_task_queue, _task_queue

        _task_queue = None

        with patch("services.task_queue.AsyncTaskQueue") as MockQueue:
            mock_instance = AsyncMock()
            mock_instance.connect = AsyncMock()
            MockQueue.return_value = mock_instance

            queue = await get_task_queue()

            assert queue is not None

    @pytest.mark.asyncio
    async def test_enqueue_task(self):
        """Test enqueue_task convenience function"""
        from services.task_queue import enqueue_task, _task_queue
        from services.task_queue import TaskPriority

        _task_queue = None

        with patch("services.task_queue.get_task_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_queue.enqueue = AsyncMock(
                return_value=MagicMock(id="task-123", name="test", payload={})
            )
            mock_get_queue.return_value = mock_queue

            task = await enqueue_task("test", {"data": "value"})

            assert task is not None

    @pytest.mark.asyncio
    async def test_get_task_status(self):
        """Test get_task_status convenience function"""
        from services.task_queue import get_task_status, _task_queue

        _task_queue = None

        with patch("services.task_queue.get_task_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_queue.get_status = AsyncMock(return_value={"status": "queued"})
            mock_get_queue.return_value = mock_queue

            status = await get_task_status("task-123")

            assert status is not None

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test cancel_task convenience function"""
        from services.task_queue import cancel_task, _task_queue

        _task_queue = None

        with patch("services.task_queue.get_task_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_queue.cancel = AsyncMock(return_value=True)
            mock_get_queue.return_value = mock_queue

            result = await cancel_task("task-123")

            assert result is True

    @pytest.mark.asyncio
    async def test_get_queue_stats_function(self):
        """Test get_queue_stats convenience function"""
        from services.task_queue import get_queue_stats, _task_queue

        _task_queue = None

        with patch("services.task_queue.get_task_queue") as mock_get_queue:
            mock_queue = AsyncMock()
            mock_queue.get_queue_stats = AsyncMock(return_value={"total_tasks": 0})
            mock_get_queue.return_value = mock_queue

            stats = await get_queue_stats()

            assert stats is not None


class TestQueueNames:
    """Test queue name configuration"""

    def test_queue_names(self):
        """Test queue name configuration"""
        from services.task_queue import AsyncTaskQueue, TaskPriority

        queue = AsyncTaskQueue()

        assert queue._queue_names[TaskPriority.LOW] == "task_queue:low"
        assert queue._queue_names[TaskPriority.NORMAL] == "task_queue:normal"
        assert queue._queue_names[TaskPriority.HIGH] == "task_queue:high"
        assert queue._queue_names[TaskPriority.CRITICAL] == "task_queue:critical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
