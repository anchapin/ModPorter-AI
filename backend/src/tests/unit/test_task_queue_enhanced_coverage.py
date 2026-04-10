"""
Comprehensive unit tests for task_queue_enhanced.py using mocked Redis.
Boosts coverage for AsyncTaskQueue async methods.
"""

import pytest
import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from services.task_queue_enhanced import (
    AsyncTaskQueue,
    Task,
    TaskStatus,
    TaskPriority,
    RetryPolicy,
    QueueHealth,
    enqueue_task,
    get_task_status,
    cancel_task,
    get_queue_stats,
    get_queue_health,
    get_task_queue,
)


class AsyncIter:
    """Helper to mock async iterators."""

    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)


class TestAsyncTaskQueueCoverage:
    """Tests for AsyncTaskQueue with mocked Redis."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = AsyncMock()
        # Use MagicMock for scan_iter so it returns the AsyncIter directly instead of a coroutine
        redis.scan_iter = MagicMock(side_effect=lambda match=None: AsyncIter(["task:1", "task:2"]))
        return redis

    @pytest.fixture
    async def queue(self, mock_redis):
        """Create a queue with mocked Redis."""
        queue = AsyncTaskQueue(redis_url="redis://fake")
        queue._redis = mock_redis
        return queue

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connect and disconnect methods."""
        queue = AsyncTaskQueue()
        # mock_from_url must be an AsyncMock to be awaitable
        with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_from_url:
            mock_redis_inst = AsyncMock()
            mock_from_url.return_value = mock_redis_inst

            await queue.connect()
            assert queue._redis == mock_redis_inst
            mock_from_url.assert_called_once()

            await queue.disconnect()
            mock_redis_inst.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue(self, queue, mock_redis):
        """Test enqueueing a task."""
        payload = {"data": "test"}
        task = await queue.enqueue("test_task", payload, priority=TaskPriority.HIGH)

        assert task.name == "test_task"
        assert task.priority == TaskPriority.HIGH
        assert task.payload == payload

        # Verify Redis calls
        mock_redis.set.assert_called_once()
        mock_redis.zadd.assert_called_once()
        mock_redis.hincrby.assert_called_once_with(queue._metrics_key, "tasks_enqueued", 1)

    @pytest.mark.asyncio
    async def test_dequeue_success(self, queue, mock_redis):
        """Test successfully dequeueing a task."""
        task_id = "task-123"
        task_data = Task(id=task_id, name="t1", payload={}).to_dict()

        # Setup mocks for finding a task in CRITICAL queue
        mock_redis.zrangebyscore.side_effect = [
            [task_id],  # CRITICAL
            [],
            [],
            [],  # Others
        ]
        mock_redis.zrem.return_value = 1
        mock_redis.get.return_value = json.dumps(task_data)

        task = await queue.dequeue()

        assert task is not None
        assert task.id == task_id
        assert task.status == TaskStatus.PROCESSING
        mock_redis.sadd.assert_called_once_with(queue._processing_set, task_id)
        mock_redis.hincrby.assert_called_once_with(queue._metrics_key, "tasks_dequeued", 1)

    @pytest.mark.asyncio
    async def test_dequeue_empty(self, queue, mock_redis):
        """Test dequeue when all queues are empty."""
        mock_redis.zrangebyscore.return_value = []

        task = await queue.dequeue()
        assert task is None

    @pytest.mark.asyncio
    async def test_complete(self, queue, mock_redis):
        """Test marking a task as completed."""
        task_id = "t1"
        started_at = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        task_data = {"id": task_id, "status": "processing", "started_at": started_at}
        mock_redis.get.return_value = json.dumps(task_data)

        await queue.complete(task_id, result={"ok": True})

        # Verify Redis updates
        args, kwargs = mock_redis.set.call_args
        updated_task = json.loads(args[1])
        assert updated_task["status"] == "completed"
        assert updated_task["result"] == {"ok": True}
        mock_redis.srem.assert_called_once_with(queue._processing_set, task_id)
        mock_redis.hincrby.assert_called_with(queue._metrics_key, "tasks_completed", 1)
        mock_redis.hincrbyfloat.assert_called_once()  # For processing time

    @pytest.mark.asyncio
    async def test_fail_retry(self, queue, mock_redis):
        """Test failing a task with retry."""
        task_id = "t1"
        task_data = {"id": task_id, "status": "processing", "retry_count": 0, "max_retries": 3}
        mock_redis.get.return_value = json.dumps(task_data)

        retried = await queue.fail(task_id, "Connection timeout", error_type="ConnectionError")

        assert retried is True
        mock_redis.zadd.assert_called_once()  # Added to retry queue
        mock_redis.hincrby.assert_called_with(queue._metrics_key, "tasks_retried", 1)

    @pytest.mark.asyncio
    async def test_fail_dead_letter(self, queue, mock_redis):
        """Test failing a task and moving to dead letter queue."""
        task_id = "t1"
        # Max retries reached
        task_data = {"id": task_id, "status": "processing", "retry_count": 3, "max_retries": 3}
        mock_redis.get.return_value = json.dumps(task_data)

        retried = await queue.fail(task_id, "Fatal error")

        assert retried is False
        # Check moved to dead letter
        mock_redis.zadd.assert_called_once_with(
            queue._dead_letter_queue, {task_id: pytest.approx(time.time(), abs=1)}
        )
        mock_redis.hincrby.assert_called_with(queue._metrics_key, "tasks_dead_lettered", 1)

    @pytest.mark.asyncio
    async def test_fail_no_dead_letter(self, queue, mock_redis):
        """Test failing a task when dead letter is disabled."""
        queue.dead_letter_enabled = False
        task_id = "t1"
        task_data = {"id": task_id, "status": "processing", "retry_count": 3, "max_retries": 3}
        mock_redis.get.return_value = json.dumps(task_data)

        retried = await queue.fail(task_id, "Fatal error")

        assert retried is False
        mock_redis.hincrby.assert_called_with(queue._metrics_key, "tasks_failed", 1)

    @pytest.mark.asyncio
    async def test_process_retry_queue(self, queue, mock_redis):
        """Test processing the retry queue."""
        task_ids = ["t1", "t2"]
        mock_redis.zrangebyscore.return_value = task_ids

        t1_data = Task(id="t1", name="n1", payload={}, priority=TaskPriority.HIGH).to_dict()
        t2_data = Task(id="t2", name="n2", payload={}, priority=TaskPriority.NORMAL).to_dict()
        mock_redis.get.side_effect = [json.dumps(t1_data), json.dumps(t2_data)]

        requeued = await queue.process_retry_queue()

        assert requeued == 2
        assert mock_redis.zrem.call_count == 2
        assert mock_redis.zadd.call_count == 2
        # Verify added back to priority queues
        mock_redis.zadd.assert_any_call(
            "task_queue:high", {"t1": pytest.approx(time.time(), abs=1)}
        )
        mock_redis.zadd.assert_any_call(
            "task_queue:normal", {"t2": pytest.approx(time.time(), abs=1)}
        )

    @pytest.mark.asyncio
    async def test_get_dead_letter_tasks(self, queue, mock_redis):
        """Test listing dead letter tasks."""
        mock_redis.zrange.return_value = ["t1"]
        mock_redis.get.return_value = json.dumps({"id": "t1", "status": "dead_letter"})

        tasks = await queue.get_dead_letter_tasks()
        assert len(tasks) == 1
        assert tasks[0]["id"] == "t1"

    @pytest.mark.asyncio
    async def test_reprocess_dead_letter_task(self, queue, mock_redis):
        """Test reprocessing a dead letter task."""
        task_id = "t1"
        task_data = Task(id=task_id, name="n1", payload={}, priority=TaskPriority.LOW).to_dict()
        mock_redis.get.return_value = json.dumps(task_data)

        success = await queue.reprocess_dead_letter_task(task_id)

        assert success is True
        mock_redis.zrem.assert_called_once_with(queue._dead_letter_queue, task_id)
        mock_redis.zadd.assert_called_once()  # Re-added to queue
        mock_redis.hincrby.assert_called_with(queue._metrics_key, "tasks_reprocessed", 1)

    @pytest.mark.asyncio
    async def test_cancel_success(self, queue, mock_redis):
        """Test successfully cancelling a queued task."""
        task_id = "t1"
        task_data = {"id": task_id, "status": "queued"}
        mock_redis.get.return_value = json.dumps(task_data)

        success = await queue.cancel(task_id)

        assert success is True
        mock_redis.zrem.assert_called()  # Removed from queues
        mock_redis.hincrby.assert_called_with(queue._metrics_key, "tasks_cancelled", 1)

    @pytest.mark.asyncio
    async def test_cancel_already_processing(self, queue, mock_redis):
        """Test cancelling a task that is already processing (should fail)."""
        task_id = "t1"
        task_data = {"id": task_id, "status": "processing"}
        mock_redis.get.return_value = json.dumps(task_data)

        success = await queue.cancel(task_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_list_tasks(self, queue, mock_redis):
        """Test listing tasks with filtering."""
        # mock_scan_iter returns AsyncIter(["task:1", "task:2"])
        mock_redis.get.side_effect = [
            json.dumps({"id": "1", "status": "completed"}),
            json.dumps({"id": "2", "status": "queued"}),
        ]

        # List all
        tasks = await queue.list_tasks()
        assert len(tasks) == 2

        # Filter by status
        # Reset side effect
        mock_redis.scan_iter.side_effect = lambda match=None: AsyncIter(["task:1", "task:2"])
        mock_redis.get.side_effect = [
            json.dumps({"id": "1", "status": "completed"}),
            json.dumps({"id": "2", "status": "queued"}),
        ]
        tasks_queued = await queue.list_tasks(status=TaskStatus.QUEUED)
        assert len(tasks_queued) == 1
        assert tasks_queued[0]["id"] == "2"

    @pytest.mark.asyncio
    async def test_get_queue_health_comprehensive(self, queue, mock_redis):
        """Test comprehensive queue health report."""
        # Mock counts for each priority queue
        mock_redis.zcard.side_effect = [
            10,  # LOW
            20,  # NORMAL
            5,  # HIGH
            2,  # CRITICAL
            1,  # DEAD LETTER
        ]
        # Mock oldest task age
        mock_redis.zrange.return_value = [("t1", time.time() - 5000)]  # 5000s old

        # Mock processing set count
        mock_redis.scard.return_value = 25

        # Mock other metrics
        mock_redis.hgetall.return_value = {
            "tasks_completed": "100",
            "tasks_failed": "5",
            "total_processing_time": "500.0",
        }

        health = await queue.get_queue_health()

        assert health.total_queued == 37  # 10+20+5+2
        assert health.total_processing == 25
        assert health.total_dead_letter == 1
        assert health.total_completed == 100
        assert health.avg_processing_time_seconds == 5.0
        assert health.healthy is False  # Because oldest > 3600 and processing > 20
        assert len(health.issues) == 2

    @pytest.mark.asyncio
    async def test_cleanup_old_tasks(self, queue, mock_redis):
        """Test cleaning up old tasks."""
        # mock_scan_iter returns AsyncIter(["task:1", "task:2"])
        old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        new_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        mock_redis.get.side_effect = [
            json.dumps({"id": "1", "status": "completed", "completed_at": old_time}),
            json.dumps({"id": "2", "status": "completed", "completed_at": new_time}),
        ]

        cleaned = await queue.cleanup_old_tasks(max_age_hours=24)
        assert cleaned == 1
        mock_redis.delete.assert_called_once_with("task:1")


class TestGlobalTaskQueueFunctions:
    """Test global convenience functions for task queue."""

    @pytest.mark.asyncio
    @patch("services.task_queue_enhanced.get_task_queue")
    async def test_enqueue_task(self, mock_get_queue):
        mock_q = AsyncMock()
        mock_get_queue.return_value = mock_q
        await enqueue_task("name", {})
        mock_q.enqueue.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.task_queue_enhanced.get_task_queue")
    async def test_get_task_status(self, mock_get_queue):
        mock_q = AsyncMock()
        mock_get_queue.return_value = mock_q
        await get_task_status("id")
        mock_q.get_status.assert_called_once_with("id")

    @pytest.mark.asyncio
    @patch("services.task_queue_enhanced.get_task_queue")
    async def test_cancel_task(self, mock_get_queue):
        mock_q = AsyncMock()
        mock_get_queue.return_value = mock_q
        await cancel_task("id")
        mock_q.cancel.assert_called_once_with("id")

    @pytest.mark.asyncio
    @patch("services.task_queue_enhanced.get_task_queue")
    async def test_get_queue_stats(self, mock_get_queue):
        mock_q = AsyncMock()
        mock_get_queue.return_value = mock_q
        await get_queue_stats()
        mock_q.get_queue_stats.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.task_queue_enhanced.get_task_queue")
    async def test_get_queue_health(self, mock_get_queue):
        mock_q = AsyncMock()
        mock_get_queue.return_value = mock_q
        await get_queue_health()
        mock_q.get_queue_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_queue_singleton(self):
        """Test get_task_queue returns singleton and connects."""
        with patch("services.task_queue_enhanced.AsyncTaskQueue") as mock_queue_cls:
            mock_inst = AsyncMock()
            mock_queue_cls.return_value = mock_inst

            # Reset global
            import services.task_queue_enhanced

            services.task_queue_enhanced._task_queue = None

            q1 = await get_task_queue()
            q2 = await get_task_queue()

            assert q1 is q2
            mock_inst.connect.assert_called_once()
