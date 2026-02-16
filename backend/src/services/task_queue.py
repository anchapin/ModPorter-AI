"""
Async Task Queue Service
Provides background task processing with Redis-based queue implementation.

Issue: #379 - Implement async task queue (Phase 3)
"""

import json
import asyncio
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enum"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority enum"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    """Task data structure"""
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
    retry_count: int = 0
    max_retries: int = 3

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
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }


class AsyncTaskQueue:
    """
    Async task queue using Redis for background job processing.
    Supports priorities, retries, and status tracking.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_retries: int = 3,
        default_timeout: int = 300
    ):
        self.redis_url = redis_url
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        self._redis: Optional[aioredis.Redis] = None
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
        # Queue names for different priorities
        self._queue_names = {
            TaskPriority.LOW: "task_queue:low",
            TaskPriority.NORMAL: "task_queue:normal",
            TaskPriority.HIGH: "task_queue:high",
            TaskPriority.CRITICAL: "task_queue:critical"
        }
        
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
        max_retries: Optional[int] = None
    ) -> Task:
        """
        Add a task to the queue.
        
        Args:
            name: Task name/identifier
            payload: Task data
            priority: Task priority
            max_retries: Maximum retry attempts
            
        Returns:
            Created Task
        """
        redis = await self._get_redis()
        
        task = Task(
            id=str(uuid.uuid4()),
            name=name,
            payload=payload,
            priority=priority,
            max_retries=max_retries if max_retries is not None else self.max_retries
        )
        
        # Store task data
        await redis.set(
            f"task:{task.id}",
            json.dumps(task.to_dict()),
            ex=86400  # 24 hour expiry
        )
        
        # Add to priority queue
        queue_name = self._queue_names[priority]
        await redis.zadd(queue_name, {task.id: priority.value})
        
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
            
            # Get highest priority task
            task_ids = await redis.zpopmin(queue_name, count=1)
            
            if task_ids:
                task_id = task_ids[0][0].decode() if isinstance(task_ids[0][0], bytes) else task_ids[0][0]
                
                # Get task data
                task_data = await redis.get(f"task:{task_id}")
                
                if task_data:
                    task_dict = json.loads(task_data)
                    task = Task(
                        id=task_dict["id"],
                        name=task_dict["name"],
                        payload=task_dict["payload"],
                        status=TaskStatus(task_dict["status"]),
                        priority=TaskPriority(task_dict["priority"]),
                        created_at=datetime.fromisoformat(task_dict["created_at"]),
                        retry_count=task_dict.get("retry_count", 0),
                        max_retries=task_dict.get("max_retries", self.max_retries)
                    )
                    
                    # Update status to processing
                    task.status = TaskStatus.PROCESSING
                    task.started_at = datetime.utcnow()
                    
                    await redis.set(
                        f"task:{task.id}",
                        json.dumps(task.to_dict()),
                        ex=86400
                    )
                    
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
            
            await redis.set(
                f"task:{task_id}",
                json.dumps(task_dict),
                ex=86400
            )
            
            logger.info(f"Task {task_id} completed")

    async def fail(
        self, 
        task_id: str, 
        error: str,
        retry: bool = True
    ) -> bool:
        """
        Mark a task as failed.
        
        Args:
            task_id: Task ID
            error: Error message
            retry: Whether to retry the task
            
        Returns:
            True if task was retried, False otherwise
        """
        redis = await self._get_redis()
        
        task_data = await redis.get(f"task:{task_id}")
        if not task_data:
            return False
            
        task_dict = json.loads(task_data)
        task_dict["error"] = error
        
        retry_count = task_dict.get("retry_count", 0)
        max_retries = task_dict.get("max_retries", self.max_retries)
        
        if retry and retry_count < max_retries:
            # Re-queue for retry
            task_dict["retry_count"] = retry_count + 1
            task_dict["status"] = TaskStatus.QUEUED.value
            task_dict["started_at"] = None
            
            # Re-add to queue with normal priority
            queue_name = self._queue_names[TaskPriority.NORMAL]
            await redis.zadd(queue_name, {task_id: TaskPriority.NORMAL.value})
            
            await redis.set(
                f"task:{task_id}",
                json.dumps(task_dict),
                ex=86400
            )
            
            logger.info(f"Task {task_id} re-queued for retry ({retry_count + 1}/{max_retries})")
            return True
        else:
            # Mark as failed
            task_dict["status"] = TaskStatus.FAILED.value
            task_dict["completed_at"] = datetime.utcnow().isoformat()
            
            await redis.set(
                f"task:{task_id}",
                json.dumps(task_dict),
                ex=86400
            )
            
            logger.error(f"Task {task_id} failed: {error}")
            return False

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
                
                # Remove from queue
                for queue_name in self._queue_names.values():
                    await redis.zrem(queue_name, task_id)
                
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
        for key in keys[:limit]:
            task_data = await redis.get(key)
            if task_data:
                task_dict = json.loads(task_data)
                if status is None or task_dict["status"] == status.value:
                    tasks.append(task_dict)
        
        return tasks

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        redis = await self._get_redis()
        
        stats = {
            "queues": {},
            "total_tasks": 0,
            "by_status": {
                "queued": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
        }
        
        # Count tasks in each queue
        for priority, queue_name in self._queue_names.items():
            count = await redis.zcard(queue_name)
            stats["queues"][priority.name.lower()] = count
            stats["total_tasks"] += count
        
        # Count by status
        keys = []
        async for key in redis.scan_iter("task:*"):
            keys.append(key)
        
        for key in keys:
            task_data = await redis.get(key)
            if task_data:
                task_dict = json.loads(task_data)
                status = task_dict.get("status", "queued")
                if status in stats["by_status"]:
                    stats["by_status"][status] += 1
        
        return stats


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
    priority: TaskPriority = TaskPriority.NORMAL
) -> Task:
    """Enqueue a task"""
    queue = await get_task_queue()
    return await queue.enqueue(name, payload, priority)


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
