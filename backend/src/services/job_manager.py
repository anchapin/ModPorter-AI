"""
Job Manager Service for ModPorter-AI.

This module provides:
- Job creation and tracking
- Job status management (pending, processing, completed, failed)
- Job queue integration with Redis
- Progress updates and webhooks
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field, asdict

from core.redis import get_redis_client, JobQueue
from core.storage import StorageManager

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status states"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConversionMode(str, Enum):
    """Conversion mode options"""

    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"


class TargetVersion(str, Enum):
    """Target Minecraft versions"""

    V1_19 = "1.19"
    V1_20 = "1.20"
    V1_21 = "1.21"


class OutputFormat(str, Enum):
    """Output format options"""

    MCADDON = "mcaddon"
    ZIP = "zip"


@dataclass
class JobOptions:
    """Job conversion options"""

    conversion_mode: ConversionMode = ConversionMode.STANDARD
    target_version: TargetVersion = TargetVersion.V1_20
    output_format: OutputFormat = OutputFormat.MCADDON
    webhook_url: Optional[str] = None
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversion_mode": self.conversion_mode.value,
            "target_version": self.target_version.value,
            "output_format": self.output_format.value,
            "webhook_url": self.webhook_url,
            "priority": self.priority,
        }


@dataclass
class Job:
    """Job data model"""

    job_id: str
    user_id: str
    file_path: str
    original_filename: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    current_step: str = "pending"
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        return cls(**data)


class JobManager:
    """
    Job management service for handling conversion jobs.

    Usage:
        manager = JobManager()

        # Create job
        job_id = await manager.create_job(
            user_id="user123",
            file_path="/path/to/file.jar",
            options=JobOptions()
        )

        # Get job status
        job = await manager.get_job(job_id)

        # Update progress
        await manager.update_progress(job_id, 50, "Analyzing JAR contents...")
    """

    JOB_TTL = 7 * 24 * 60 * 60  # 7 days in seconds
    JOB_PREFIX = "job:"
    USER_JOBS_PREFIX = "user_jobs:"

    def __init__(self):
        self._redis = None
        self._queue: Optional[JobQueue] = None
        self._storage = StorageManager()

    async def _get_redis(self):
        """Get Redis client"""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis

    async def _get_queue(self) -> JobQueue:
        """Get job queue"""
        if self._queue is None:
            self._queue = await get_job_queue("conversions")
        return self._queue

    async def create_job(
        self,
        user_id: str,
        file_path: str,
        original_filename: str,
        options: Optional[JobOptions] = None,
    ) -> str:
        """
        Create a new job and add it to the queue.

        Args:
            user_id: The user who owns this job
            file_path: Path to the uploaded file
            original_filename: Original filename for reference
            options: Conversion options

        Returns:
            job_id: Unique identifier for the job
        """
        job_id = str(uuid.uuid4())
        options = options or JobOptions()

        job = Job(
            job_id=job_id,
            user_id=user_id,
            file_path=file_path,
            original_filename=original_filename,
            options=options.to_dict(),
        )

        # Save job to Redis
        redis = await self._get_redis()
        job_key = f"{self.JOB_PREFIX}{job_id}"

        await redis.set(
            job_key,
            job.to_dict(),
            ttl=self.JOB_TTL,
            json_encode=True,
        )

        # Add to user's job list
        user_jobs_key = f"{self.USER_JOBS_PREFIX}{user_id}"
        await redis._client.zadd(
            user_jobs_key,
            {job_id: datetime.now(timezone.utc).timestamp()},
        )
        await redis.expire(user_jobs_key, self.JOB_TTL)

        # Add to processing queue
        queue = await self._get_queue()
        job_payload = {
            "job_id": job_id,
            "user_id": user_id,
            "file_path": file_path,
            "original_filename": original_filename,
            "options": options.to_dict(),
        }

        await queue.enqueue(job_payload, priority=options.priority)

        logger.info(f"Created job {job_id} for user {user_id}")
        return job_id

    async def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job details by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job object if found, None otherwise
        """
        redis = await self._get_redis()
        job_key = f"{self.JOB_PREFIX}{job_id}"

        job_data = await redis.get(job_key)
        if not job_data:
            return None

        if isinstance(job_data, str):
            job_data = json.loads(job_data)

        return Job.from_dict(job_data)

    async def list_jobs(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Job]:
        """
        List jobs for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip

        Returns:
            List of Job objects
        """
        redis = await self._get_redis()
        user_jobs_key = f"{self.USER_JOBS_PREFIX}{user_id}"

        # Get job IDs sorted by time (newest first)
        job_ids = await redis._client.zrevrange(
            user_jobs_key,
            offset,
            offset + limit - 1,
        )

        jobs = []
        for job_id in job_ids:
            job = await self.get_job(job_id)
            if job:
                jobs.append(job)

        return jobs

    async def update_progress(
        self,
        job_id: str,
        progress: int,
        current_step: str,
    ) -> bool:
        """
        Update job progress.

        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
            current_step: Description of current processing step

        Returns:
            True if updated successfully
        """
        job = await self.get_job(job_id)
        if not job:
            return False

        job.progress = min(100, max(0, progress))
        job.current_step = current_step
        job.status = JobStatus.PROCESSING
        job.updated_at = datetime.now(timezone.utc).isoformat()

        redis = await self._get_redis()
        job_key = f"{self.JOB_PREFIX}{job_id}"

        return await redis.set(
            job_key,
            job.to_dict(),
            ttl=self.JOB_TTL,
            json_encode=True,
        )

    async def complete_job(
        self,
        job_id: str,
        result_url: Optional[str] = None,
    ) -> bool:
        """
        Mark job as completed.

        Args:
            job_id: Job identifier
            result_url: URL to download the converted file

        Returns:
            True if completed successfully
        """
        job = await self.get_job(job_id)
        if not job:
            return False

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.current_step = "completed"
        job.result_url = result_url
        job.updated_at = datetime.now(timezone.utc).isoformat()
        job.completed_at = datetime.now(timezone.utc).isoformat()

        redis = await self._get_redis()
        job_key = f"{self.JOB_PREFIX}{job_id}"

        success = await redis.set(
            job_key,
            job.to_dict(),
            ttl=self.JOB_TTL,
            json_encode=True,
        )

        # Trigger webhook if configured
        if job.options.get("webhook_url"):
            await self._send_webhook(job)

        return success

    async def fail_job(
        self,
        job_id: str,
        error_message: str,
    ) -> bool:
        """
        Mark job as failed.

        Args:
            job_id: Job identifier
            error_message: Error description

        Returns:
            True if marked as failed
        """
        job = await self.get_job(job_id)
        if not job:
            return False

        job.status = JobStatus.FAILED
        job.error_message = error_message
        job.current_step = "failed"
        job.updated_at = datetime.now(timezone.utc).isoformat()
        job.completed_at = datetime.now(timezone.utc).isoformat()

        redis = await self._get_redis()
        job_key = f"{self.JOB_PREFIX}{job_id}"

        success = await redis.set(
            job_key,
            job.to_dict(),
            ttl=self.JOB_TTL,
            json_encode=True,
        )

        # Trigger webhook if configured
        if job.options.get("webhook_url"):
            await self._send_webhook(job)

        return success

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or processing job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled successfully
        """
        job = await self.get_job(job_id)
        if not job:
            return False

        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            return False

        job.status = JobStatus.CANCELLED
        job.current_step = "cancelled"
        job.updated_at = datetime.now(timezone.utc).isoformat()
        job.completed_at = datetime.now(timezone.utc).isoformat()

        redis = await self._get_redis()
        job_key = f"{self.JOB_PREFIX}{job_id}"

        return await redis.set(
            job_key,
            job.to_dict(),
            ttl=self.JOB_TTL,
            json_encode=True,
        )

    async def _send_webhook(self, job: Job) -> None:
        """
        Send webhook notification for job completion/failure.

        Args:
            job: The completed/failed job
        """
        import httpx

        webhook_url = job.options.get("webhook_url")
        if not webhook_url:
            return

        payload = {
            "job_id": job.job_id,
            "status": job.status.value,
            "result_url": job.result_url,
            "error_message": job.error_message,
            "original_filename": job.original_filename,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(webhook_url, json=payload)
                logger.info(f"Webhook sent for job {job.job_id}")
        except Exception as e:
            logger.error(f"Failed to send webhook for job {job.job_id}: {e}")


# Global instance
_job_manager: Optional[JobManager] = None


async def get_job_manager() -> JobManager:
    """Get global job manager instance"""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager


__all__ = [
    "JobManager",
    "JobStatus",
    "ConversionMode",
    "TargetVersion",
    "OutputFormat",
    "JobOptions",
    "Job",
    "get_job_manager",
]
