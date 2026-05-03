"""
Conversion Job Queue Service

Redis-based job queue for managing AI conversion requests.
"""

import logging
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ConversionJobQueue:
    """Redis-based job queue for conversions."""

    # Queue keys
    QUEUE_KEY = "conversion:queue"
    JOBS_KEY = "conversion:jobs"
    PROGRESS_KEY = "conversion:progress"
    RESULTS_KEY = "conversion:results"

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def enqueue_job(
        self,
        user_id: str,
        java_code: str,
        mod_info: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        priority: int = 0,
    ) -> str:
        """
        Add a conversion job to the queue.

        Args:
            user_id: User ID
            java_code: Java source code
            mod_info: Mod metadata
            options: Conversion options
            priority: Job priority (higher = more urgent)

        Returns:
            Job ID
        """
        r = await self._get_redis()
        job_id = str(uuid.uuid4())

        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "java_code": java_code,
            "mod_info": json.dumps(mod_info),
            "options": json.dumps(options or {}),
            "priority": priority,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store job data
        await r.hset(f"{self.JOBS_KEY}:{job_id}", mapping=job_data)

        # Add to priority queue (sorted set with priority as score)
        await r.zadd(self.QUEUE_KEY, {job_id: priority})

        logger.info(f"Job {job_id} queued for user {user_id}")
        return job_id

    async def dequeue_job(self) -> Optional[Dict[str, Any]]:
        """
        Get the next job from the queue (highest priority).

        Returns:
            Job data or None if queue is empty
        """
        r = await self._get_redis()

        # Get highest priority job
        result = await r.zpopmax(self.QUEUE_KEY, count=1)
        if not result:
            return None

        job_id = result[0][0]
        job_data = await r.hgetall(f"{self.JOBS_KEY}:{job_id}")

        if job_data:
            # Update status
            await r.hset(
                f"{self.JOBS_KEY}:{job_id}",
                mapping={
                    "status": "processing",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            # Parse JSON fields
            job_data["mod_info"] = json.loads(job_data.get("mod_info", "{}"))
            job_data["options"] = json.loads(job_data.get("options", "{}"))

        return job_data

    async def update_progress(
        self,
        job_id: str,
        progress: int,
        current_stage: str,
        message: Optional[str] = None,
    ):
        """
        Update job progress.

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            current_stage: Current processing stage
            message: Optional status message
        """
        r = await self._get_redis()

        progress_data = {
            "job_id": job_id,
            "progress": progress,
            "current_stage": current_stage,
            "message": message or "",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        await r.hset(f"{self.PROGRESS_KEY}:{job_id}", mapping=progress_data)

        # Also update job status
        await r.hset(
            f"{self.JOBS_KEY}:{job_id}",
            mapping={
                "status": "processing",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.debug(f"Job {job_id} progress: {progress}% - {current_stage}")

    async def complete_job(
        self,
        job_id: str,
        result: Dict[str, Any],
        bedrock_code: str,
    ):
        """
        Mark job as completed with result.

        Args:
            job_id: Job ID
            result: Conversion result metadata
            bedrock_code: Generated Bedrock code
        """
        r = await self._get_redis()

        # Store result
        result_data = {
            "job_id": job_id,
            "result": json.dumps(result),
            "bedrock_code": bedrock_code,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        await r.hset(f"{self.RESULTS_KEY}:{job_id}", mapping=result_data)

        # Update job status
        await r.hset(
            f"{self.JOBS_KEY}:{job_id}",
            mapping={
                "status": "completed",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"Job {job_id} completed")

    async def fail_job(
        self,
        job_id: str,
        error_message: str,
    ):
        """
        Mark job as failed.

        Args:
            job_id: Job ID
            error_message: Error description
        """
        r = await self._get_redis()

        # Update job status
        await r.hset(
            f"{self.JOBS_KEY}:{job_id}",
            mapping={
                "status": "failed",
                "error_message": error_message,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.error(f"Job {job_id} failed: {error_message}")

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current job status.

        Args:
            job_id: Job ID

        Returns:
            Job status data or None
        """
        r = await self._get_redis()

        job_data = await r.hgetall(f"{self.JOBS_KEY}:{job_id}")
        if not job_data:
            return None

        # Get progress if available
        progress_data = await r.hgetall(f"{self.PROGRESS_KEY}:{job_id}")

        return {
            "job_id": job_id,
            "status": job_data.get("status"),
            "progress": int(progress_data.get("progress", 0)),
            "current_stage": progress_data.get("current_stage", ""),
            "message": progress_data.get("message", ""),
            "created_at": job_data.get("created_at"),
            "updated_at": job_data.get("updated_at"),
        }

    async def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job result if completed.

        Args:
            job_id: Job ID

        Returns:
            Result data or None
        """
        r = await self._get_redis()

        result_data = await r.hgetall(f"{self.RESULTS_KEY}:{job_id}")
        if not result_data:
            return None

        return {
            "job_id": job_id,
            "result": json.loads(result_data.get("result", "{}")),
            "bedrock_code": result_data.get("bedrock_code", ""),
            "completed_at": result_data.get("completed_at"),
        }

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        r = await self._get_redis()

        queue_size = await r.zcard(self.QUEUE_KEY)

        return {
            "queue_size": queue_size,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# Singleton instance
_job_queue = None


def get_conversion_job_queue() -> ConversionJobQueue:
    """Get or create job queue singleton."""
    global _job_queue
    if _job_queue is None:
        _job_queue = ConversionJobQueue()
    return _job_queue
