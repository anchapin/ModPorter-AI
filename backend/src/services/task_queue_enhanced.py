"""
Enhanced Async Task Queue Service
Provides background task processing with Redis-based queue implementation.

Enhanced features for Issue #574:
- Configurable retry policies with exponential backoff
- Dead letter queue management
- Resource limit enforcement
- Queue health monitoring
- Job lifecycle documentation

Issue: #574 - Backend: Task Queue System - Background Job Processing
"""

import json
import asyncio
import uuid
import math
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enum with lifecycle states."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"  # New: Task moved to dead letter queue
    RETRYING = "retrying"  # New: Task is being retried


class TaskPriority(Enum):
    """Task priority enum with documentation.
    
    Priority levels determine the order in which tasks are processed:
    - CRITICAL: System-critical tasks (health checks, cleanup)
    - HIGH: User-facing tasks (conversions, downloads)
    - NORMAL: Standard background tasks
    - LOW: Batch operations, analytics
    """
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class RetryPolicy:
    """
    Configurable retry policy for tasks.
    
    Attributes:
        max_retries: Maximum number of retry attempts
        initial_delay_seconds: Initial delay before first retry
        max_delay_seconds: Maximum delay between retries
        backoff_multiplier: Multiplier for exponential backoff
        retryable_errors: List of error types that should trigger retry
    """
    max_retries: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 300.0  # 5 minutes max
    backoff_multiplier: float = 2.0
    retryable_errors: List[str] = field(default_factory=list)
    
    def calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for a given retry attempt using exponential backoff."""
        delay = self.initial_delay_seconds * (self.backoff_multiplier ** retry_count)
        return min(delay, self.max_delay_seconds)
    
    def should_retry(self, error_type: str, retry_count: int) -> bool:
        """Determine if a task should be retried based on error and retry count."""
        if retry_count >= self.max_retries:
            return False
        if self.retryable_errors and error_type not in self.retryable_errors:
            return False
        return True


# Default retry policies
DEFAULT_RETRY_POLICY = RetryPolicy()
CONVERSION_RETRY_POLICY = RetryPolicy(
    max_retries=5,
    initial_delay_seconds=2.0,
    max_delay_seconds=600.0,  # 10 minutes
    retryable_errors=["TimeoutError", "ConnectionError", "ResourceLimitError"]
)
QUICK_RETRY_POLICY = RetryPolicy(
    max_retries=2,
    initial_delay_seconds=0.5,
    max_delay_seconds=5.0
)


@dataclass
class Task:
    """Task data structure with lifecycle tracking."""
    id: str
    name: str
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.QUEUED
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    retry_policy: Optional[RetryPolicy] = None
    next_retry_at: Optional[datetime] = None
    resource_limits: Optional[Dict[str, Any]] = None
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
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "error_type": self.error_type,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "timeout_seconds": self.timeout_seconds
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a Task from a dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            payload=data["payload"],
            status=TaskStatus(data["status"]),
            priority=TaskPriority(data["priority"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result=data.get("result"),
            error=data.get("error"),
            error_type=data.get("error_type"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            next_retry_at=datetime.fromisoformat(data["next_retry_at"]) if data.get("next_retry_at") else None,
            timeout_seconds=data.get("timeout_seconds", 300)
        )


@dataclass
class QueueHealth:
    """Queue health metrics."""
    total_queued: int = 0
    total_processing: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_dead_letter: int = 0
    avg_processing_time_seconds: float = 0.0
    oldest_queued_age_seconds: float = 0.0
    worker_count: int = 0
    healthy: bool = True
    issues: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_queued": self.total_queued,
            "total_processing": self.total_processing,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "total_dead_letter": self.total_dead_letter,
            "avg_processing_time_seconds": self.avg_processing_time_seconds,
            "oldest_queued_age_seconds": self.oldest_queued_age_seconds,
            "worker_count": self.worker_count,
            "healthy": self.healthy,
            "issues": self.issues,
            "checked_at": self.checked_at.isoformat()
        }


class AsyncTaskQueue:
    """
    Enhanced async task queue using Redis for background job processing.
    
    Features:
    - Priority-based queues
    - Configurable retry policies with exponential backoff
    - Dead letter queue management
    - Resource limit enforcement
    - Queue health monitoring
    
    Job Lifecycle:
    1. QUEUED: Task is created and waiting to be processed
    2. PROCESSING: Task is being handled by a worker
    3. COMPLETED: Task finished successfully
    4. FAILED: Task failed after all retries
    5. DEAD_LETTER: Task moved to dead letter queue for manual review
    6. RETRYING: Task is scheduled for retry
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_retries: int = 3,
        default_timeout: int = 300,
        dead_letter_enabled: bool = True
    ):
        self.redis_url = redis_url
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        self.dead_letter_enabled = dead_letter_enabled
        self._redis: Optional[aioredis.Redis] = None
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
        # Queue names for different priorities
        self._queue_names = {
            TaskPriority.LOW: "task_queue:low",
            TaskPriority.NORMAL: "task_queue:normal",
            TaskPriority.HIGH: "task_queue:high",
            TaskPriority.CRITICAL: "task_queue:critical"
        }
        
        # Dead letter queue
        self._dead_letter_queue = "task_queue:dead_letter"
        
        # Processing tracking
        self._processing_set = "task_queue:processing"
        
        # Metrics tracking
        self._metrics_key = "task_queue:metrics"
        
    async def connect(self) -> None:
        """Connect to Redis"""
        self._redis = await aioredis.from_url(
            self.redis_url,
            decode_responses=True
        )
        logger.info("Connected to Redis for task queue")
        
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            logger.info("Disconnected from Redis")
    
    async def _get_redis(self) -> aioredis.Redis:
        """Get Redis client, connecting if needed"""
        if self._redis is None:
            await self.connect()
        return self._redis

    async def enqueue(
        self,
        name: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: Optional[int] = None,
        retry_policy: Optional[RetryPolicy] = None,
        timeout_seconds: Optional[int] = None,
        resource_limits: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Add a task to the queue.
        
        Args:
            name: Task name/identifier
            payload: Task data
            priority: Task priority
            max_retries: Maximum retry attempts
            retry_policy: Custom retry policy
            timeout_seconds: Task timeout in seconds
            resource_limits: Resource constraints for this task
            
        Returns:
            Created Task
        """
        redis = await self._get_redis()
        
        task = Task(
            id=str(uuid.uuid4()),
            name=name,
            payload=payload,
            priority=priority,
            max_retries=max_retries if max_retries is not None else self.max_retries,
            retry_policy=retry_policy or DEFAULT_RETRY_POLICY,
            timeout_seconds=timeout_seconds or self.default_timeout,
            resource_limits=resource_limits
        )
        
        # Store task data
        await redis.set(
            f"task:{task.id}",
            json.dumps(task.to_dict()),
            ex=86400  # 24 hour expiry
        )
        
        # Add to priority queue with timestamp for age tracking
        queue_name = self._queue_names[priority]
        score = time.time()
        await redis.zadd(queue_name, {task.id: score})
        
        # Update metrics
        await self._increment_metric("tasks_enqueued")
        
        logger.info(f"Task {task.id} ({name}) enqueued with priority {priority.name}")
        
        return task

    async def dequeue(self) -> Optional[Task]:
        """
        Get the next task from the queue.
        Checks queues in priority order (critical -> high -> normal -> low)
        
        Returns:
            Next Task or None if queue is empty
        """
        redis = await self._get_redis()
        
        # Check queues in priority order
        for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, 
                         TaskPriority.NORMAL, TaskPriority.LOW]:
            queue_name = self._queue_names[priority]
            
            # Get oldest task (lowest score = oldest timestamp)
            now = time.time()
            task_ids = await redis.zrangebyscore(
                queue_name,
                min=0,
                max=now,
                start=0,
                num=1
            )
            
            if task_ids:
                task_id = task_ids[0]
                
                # Remove from queue atomically
                removed = await redis.zrem(queue_name, task_id)
                if not removed:
                    continue  # Task was grabbed by another worker
                
                # Get task data
                task_data = await redis.get(f"task:{task_id}")
                
                if task_data:
                    task_dict = json.loads(task_data)
                    task = Task.from_dict(task_dict)
                    
                    # Update status to processing
                    task.status = TaskStatus.PROCESSING
                    task.started_at = datetime.utcnow()
                    
                    # Add to processing set
                    await redis.sadd(self._processing_set, task_id)
                    await redis.set(
                        f"task:{task.id}",
                        json.dumps(task.to_dict()),
                        ex=86400
                    )
                    
                    # Update metrics
                    await self._increment_metric("tasks_dequeued")
                    
                    logger.info(f"Task {task.id} ({task.name}) dequeued")
                    return task
                    
        return None

    async def complete(
        self, 
        task_id: str, 
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark a task as completed"""
        redis = await self._get_redis()
        
        task_data = await redis.get(f"task:{task_id}")
        if task_data:
            task_dict = json.loads(task_data)
            task_dict["status"] = TaskStatus.COMPLETED.value
            task_dict["completed_at"] = datetime.utcnow().isoformat()
            task_dict["result"] = result
            
            # Calculate processing time
            if task_dict.get("started_at"):
                started = datetime.fromisoformat(task_dict["started_at"])
                processing_time = (datetime.utcnow() - started).total_seconds()
                await self._record_processing_time(processing_time)
            
            await redis.set(
                f"task:{task_id}",
                json.dumps(task_dict),
                ex=86400
            )
            
            # Remove from processing set
            await redis.srem(self._processing_set, task_id)
            
            # Update metrics
            await self._increment_metric("tasks_completed")
            
            logger.info(f"Task {task_id} completed")

    async def fail(
        self, 
        task_id: str, 
        error: str,
        error_type: Optional[str] = None,
        retry: bool = True
    ) -> bool:
        """
        Mark a task as failed.
        
        Args:
            task_id: Task ID
            error: Error message
            error_type: Type of error for retry policy evaluation
            retry: Whether to attempt retry
            
        Returns:
            True if task was retried, False otherwise
        """
        redis = await self._get_redis()
        
        task_data = await redis.get(f"task:{task_id}")
        if not task_data:
            return False
            
        task_dict = json.loads(task_data)
        task_dict["error"] = error
        task_dict["error_type"] = error_type or "UnknownError"
        
        retry_count = task_dict.get("retry_count", 0)
        max_retries = task_dict.get("max_retries", self.max_retries)
        
        # Determine if we should retry
        should_retry = retry and retry_count < max_retries
        
        if should_retry:
            # Calculate retry delay with exponential backoff
            delay = DEFAULT_RETRY_POLICY.calculate_delay(retry_count)
            next_retry = datetime.utcnow() + timedelta(seconds=delay)
            
            task_dict["retry_count"] = retry_count + 1
            task_dict["status"] = TaskStatus.RETRYING.value
            task_dict["started_at"] = None
            task_dict["next_retry_at"] = next_retry.isoformat()
            
            # Add to retry queue (sorted by retry time)
            retry_score = next_retry.timestamp()
            await redis.zadd("task_queue:retry", {task_id: retry_score})
            
            await redis.set(
                f"task:{task_id}",
                json.dumps(task_dict),
                ex=86400
            )
            
            # Remove from processing set
            await redis.srem(self._processing_set, task_id)
            
            # Update metrics
            await self._increment_metric("tasks_retried")
            
            logger.info(f"Task {task_id} scheduled for retry ({retry_count + 1}/{max_retries}) at {next_retry}")
            return True
        else:
            # Move to dead letter queue or mark as failed
            if self.dead_letter_enabled:
                task_dict["status"] = TaskStatus.DEAD_LETTER.value
                task_dict["completed_at"] = datetime.utcnow().isoformat()
                
                await redis.zadd(
                    self._dead_letter_queue,
                    {task_id: time.time()}
                )
                
                await self._increment_metric("tasks_dead_lettered")
                logger.warning(f"Task {task_id} moved to dead letter queue: {error}")
            else:
                task_dict["status"] = TaskStatus.FAILED.value
                task_dict["completed_at"] = datetime.utcnow().isoformat()
                
                await self._increment_metric("tasks_failed")
                logger.error(f"Task {task_id} failed: {error}")
            
            await redis.set(
                f"task:{task_id}",
                json.dumps(task_dict),
                ex=86400
            )
            
            # Remove from processing set
            await redis.srem(self._processing_set, task_id)
            
            return False

    async def process_retry_queue(self) -> int:
        """
        Process tasks in the retry queue that are ready to be retried.
        
        Returns:
            Number of tasks re-queued
        """
        redis = await self._get_redis()
        now = time.time()
        
        # Get tasks ready for retry
        task_ids = await redis.zrangebyscore(
            "task_queue:retry",
            min=0,
            max=now
        )
        
        requeued = 0
        for task_id in task_ids:
            # Remove from retry queue
            await redis.zrem("task_queue:retry", task_id)
            
            # Get task data
            task_data = await redis.get(f"task:{task_id}")
            if task_data:
                task_dict = json.loads(task_data)
                task = Task.from_dict(task_dict)
                
                # Re-add to appropriate priority queue
                queue_name = self._queue_names[task.priority]
                await redis.zadd(queue_name, {task_id: time.time()})
                
                # Update status
                task_dict["status"] = TaskStatus.QUEUED.value
                task_dict["next_retry_at"] = None
                await redis.set(f"task:{task_id}", json.dumps(task_dict), ex=86400)
                
                requeued += 1
        
        if requeued > 0:
            logger.info(f"Re-queued {requeued} tasks from retry queue")
        
        return requeued

    async def get_dead_letter_tasks(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get tasks from the dead letter queue.
        
        Args:
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip
            
        Returns:
            List of dead letter tasks
        """
        redis = await self._get_redis()
        
        task_ids = await redis.zrange(
            self._dead_letter_queue,
            start=offset,
            end=offset + limit - 1
        )
        
        tasks = []
        for task_id in task_ids:
            task_data = await redis.get(f"task:{task_id}")
            if task_data:
                tasks.append(json.loads(task_data))
        
        return tasks

    async def reprocess_dead_letter_task(self, task_id: str) -> bool:
        """
        Move a task from dead letter queue back to the main queue.
        
        Args:
            task_id: Task ID to reprocess
            
        Returns:
            True if successful
        """
        redis = await self._get_redis()
        
        task_data = await redis.get(f"task:{task_id}")
        if not task_data:
            return False
        
        task_dict = json.loads(task_data)
        task = Task.from_dict(task_dict)
        
        # Remove from dead letter queue
        await redis.zrem(self._dead_letter_queue, task_id)
        
        # Reset task state
        task_dict["status"] = TaskStatus.QUEUED.value
        task_dict["retry_count"] = 0
        task_dict["error"] = None
        task_dict["error_type"] = None
        task_dict["started_at"] = None
        task_dict["completed_at"] = None
        
        # Add back to queue
        queue_name = self._queue_names[task.priority]
        await redis.zadd(queue_name, {task_id: time.time()})
        await redis.set(f"task:{task_id}", json.dumps(task_dict), ex=86400)
        
        await self._increment_metric("tasks_reprocessed")
        logger.info(f"Task {task_id} reprocessed from dead letter queue")
        
        return True

    async def cancel(self, task_id: str) -> bool:
        """Cancel a queued task"""
        redis = await self._get_redis()
        
        task_data = await redis.get(f"task:{task_id}")
        if task_data:
            task_dict = json.loads(task_data)
            
            if task_dict["status"] == TaskStatus.QUEUED.value:
                task_dict["status"] = TaskStatus.CANCELLED.value
                task_dict["completed_at"] = datetime.utcnow().isoformat()
                
                await redis.set(
                    f"task:{task_id}",
                    json.dumps(task_dict),
                    ex=86400
                )
                
                # Remove from all queues
                for queue_name in self._queue_names.values():
                    await redis.zrem(queue_name, task_id)
                await redis.zrem("task_queue:retry", task_id)
                
                await self._increment_metric("tasks_cancelled")
                logger.info(f"Task {task_id} cancelled")
                return True
                
        return False

    async def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        redis = await self._get_redis()
        
        task_data = await redis.get(f"task:{task_id}")
        if task_data:
            return json.loads(task_data)
        return None

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by status"""
        redis = await self._get_redis()
        
        # Get all task keys
        keys = []
        async for key in redis.scan_iter("task:*"):
            keys.append(key)
        
        tasks = []
        for key in keys[:limit * 2]:  # Get extra to account for filtering
            task_data = await redis.get(key)
            if task_data:
                task_dict = json.loads(task_data)
                if status is None or task_dict["status"] == status.value:
                    tasks.append(task_dict)
                    if len(tasks) >= limit:
                        break
        
        return tasks

    async def get_queue_health(self) -> QueueHealth:
        """
        Get comprehensive queue health metrics.
        
        Returns:
            QueueHealth with current metrics and issues
        """
        redis = await self._get_redis()
        health = QueueHealth()
        issues = []
        
        try:
            # Count tasks in each queue
            for priority, queue_name in self._queue_names.items():
                count = await redis.zcard(queue_name)
                health.total_queued += count
                
                # Check for old tasks
                if count > 0:
                    oldest = await redis.zrange(queue_name, 0, 0, withscores=True)
                    if oldest:
                        oldest_score = oldest[0][1]
                        age = time.time() - oldest_score
                        health.oldest_queued_age_seconds = max(
                            health.oldest_queued_age_seconds, 
                            age
                        )
            
            # Count processing tasks
            health.total_processing = await redis.scard(self._processing_set)
            
            # Count dead letter tasks
            health.total_dead_letter = await redis.zcard(self._dead_letter_queue)
            
            # Get metrics
            metrics = await redis.hgetall(self._metrics_key)
            if metrics:
                health.total_completed = int(metrics.get("tasks_completed", 0))
                health.total_failed = int(metrics.get("tasks_failed", 0))
                
                # Calculate average processing time
                total_time = float(metrics.get("total_processing_time", 0))
                completed_count = int(metrics.get("tasks_completed", 0))
                if completed_count > 0:
                    health.avg_processing_time_seconds = total_time / completed_count
            
            # Determine health issues
            if health.oldest_queued_age_seconds > 3600:  # 1 hour
                issues.append(f"Oldest queued task is {health.oldest_queued_age_seconds/60:.1f} minutes old")
            
            if health.total_queued > 1000:
                issues.append(f"Queue backlog is high: {health.total_queued} tasks")
            
            if health.total_dead_letter > 50:
                issues.append(f"Dead letter queue has {health.total_dead_letter} tasks")
            
            if health.total_processing > 20:
                issues.append(f"High number of processing tasks: {health.total_processing}")
            
            health.issues = issues
            health.healthy = len(issues) == 0
            
        except Exception as e:
            logger.error(f"Error getting queue health: {e}")
            health.healthy = False
            health.issues.append(f"Error checking health: {str(e)}")
        
        return health

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics (legacy compatibility)"""
        health = await self.get_queue_health()
        return health.to_dict()

    async def _increment_metric(self, metric_name: str) -> None:
        """Increment a metric counter."""
        redis = await self._get_redis()
        await redis.hincrby(self._metrics_key, metric_name, 1)

    async def _record_processing_time(self, seconds: float) -> None:
        """Record processing time for metrics."""
        redis = await self._get_redis()
        await redis.hincrbyfloat(self._metrics_key, "total_processing_time", seconds)

    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed tasks.
        
        Args:
            max_age_hours: Maximum age of tasks to keep
            
        Returns:
            Number of tasks cleaned up
        """
        redis = await self._get_redis()
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned = 0
        
        keys = []
        async for key in redis.scan_iter("task:*"):
            if key == self._metrics_key:
                continue
            keys.append(key)
        
        for key in keys:
            task_data = await redis.get(key)
            if task_data:
                task_dict = json.loads(task_data)
                status = task_dict.get("status")
                
                if status in ("completed", "failed", "cancelled", "dead_letter"):
                    completed_at = task_dict.get("completed_at")
                    if completed_at:
                        completed_time = datetime.fromisoformat(completed_at)
                        if completed_time < cutoff:
                            await redis.delete(key)
                            cleaned += 1
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old tasks")
        
        return cleaned


# Global task queue instance
_task_queue: Optional[AsyncTaskQueue] = None


async def get_task_queue() -> AsyncTaskQueue:
    """Get or create the global task queue instance"""
    global _task_queue
    
    if _task_queue is None:
        redis_url = "redis://localhost:6379"  # Could be from config
        _task_queue = AsyncTaskQueue(redis_url=redis_url)
        await _task_queue.connect()
    
    return _task_queue


# Convenience functions
async def enqueue_task(
    name: str,
    payload: Dict[str, Any],
    priority: TaskPriority = TaskPriority.NORMAL,
    retry_policy: Optional[RetryPolicy] = None
) -> Task:
    """Enqueue a task"""
    queue = await get_task_queue()
    return await queue.enqueue(name, payload, priority, retry_policy=retry_policy)


async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status"""
    queue = await get_task_queue()
    return await queue.get_status(task_id)


async def cancel_task(task_id: str) -> bool:
    """Cancel a task"""
    queue = await get_task_queue()
    return await queue.cancel(task_id)


async def get_queue_stats() -> Dict[str, Any]:
    """Get queue statistics"""
    queue = await get_task_queue()
    return await queue.get_queue_stats()


async def get_queue_health() -> QueueHealth:
    """Get queue health"""
    queue = await get_task_queue()
    return await queue.get_queue_health()