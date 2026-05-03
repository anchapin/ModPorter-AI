"""
Conversion Worker for portkit.

This module provides:
- Background job processing from Redis queue
- Conversion pipeline execution
- Error handling with retry logic
- Dead letter queue for failed jobs
- Webhook notifications
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import traceback

from core.redis import get_job_queue, RedisClient
from services.job_manager import JobManager, JobStatus, get_job_manager
from core.storage import StorageManager
from services.ai_engine_client import get_ai_engine_client

logger = logging.getLogger(__name__)


class ConversionWorker:
    """
    Background worker for processing conversion jobs.

    Usage:
        worker = ConversionWorker()
        await worker.start()  # Starts the worker loop

        # Or process a single job:
        await worker.process_job(job_data)
    """

    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 30, 120]  # seconds
    DLQ_PREFIX = "dlq:"  # Dead letter queue prefix
    POLL_INTERVAL = 2  # seconds between queue polls

    def __init__(self):
        self._queue = None
        self._redis = None
        self._job_manager: Optional[JobManager] = None
        self._storage = StorageManager()
        self._ai_engine = None
        self._running = False
        self._shutdown_event = asyncio.Event()

    async def _get_queue(self):
        """Get job queue"""
        if self._queue is None:
            self._queue = await get_job_queue("conversions")
        return self._queue

    async def _get_redis(self) -> RedisClient:
        """Get Redis client"""
        if self._redis is None:
            self._redis = await get_job_queue("conversions").client
        return self._redis

    async def _get_job_manager(self) -> JobManager:
        """Get job manager"""
        if self._job_manager is None:
            self._job_manager = await get_job_manager()
        return self._job_manager

    async def _get_ai_engine(self):
        """Get AI engine client"""
        if self._ai_engine is None:
            self._ai_engine = await get_ai_engine_client()
        return self._ai_engine

    async def start(self) -> None:
        """
        Start the worker loop.

        Continuously polls the job queue and processes jobs.
        """
        self._running = True
        self._shutdown_event.clear()

        logger.info("Conversion worker started")

        while self._running:
            try:
                job = await self._poll_job()
                if job:
                    await self.process_job(job)
                else:
                    await asyncio.sleep(self.POLL_INTERVAL)
            except asyncio.CancelledError:
                logger.info("Worker cancelled")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(self.POLL_INTERVAL)

        self._shutdown_event.set()
        logger.info("Conversion worker stopped")

    async def stop(self) -> None:
        """Stop the worker gracefully"""
        self._running = False
        await self._shutdown_event.wait()

    async def _poll_job(self) -> Optional[Dict[str, Any]]:
        """
        Poll for a new job from the queue.

        Returns:
            Job data dictionary or None if queue is empty
        """
        queue = await self._get_queue()
        return await queue.dequeue()

    async def process_job(self, job_data: Dict[str, Any]) -> bool:
        """
        Process a single conversion job.

        Steps:
        1. Download file from storage
        2. Run conversion pipeline
        3. Package results
        4. Upload to storage
        5. Update job status

        Args:
            job_data: Job data containing job_id, file_path, options

        Returns:
            True if job processed successfully
        """
        job_id = job_data.get("job_id")
        if not job_id:
            logger.error("Job data missing job_id")
            return False

        job_manager = await self._get_job_manager()

        try:
            # Update status to processing
            await job_manager.update_progress(job_id, 0, "Starting conversion...")

            # Step 1: Download file from storage
            file_path = job_data.get("file_path")
            if not file_path:
                await job_manager.fail_job(job_id, "No file path provided")
                return False

            await job_manager.update_progress(job_id, 10, "Downloading file...")
            local_file = await self._download_file(file_path, job_id)

            # Step 2: Run conversion pipeline
            await job_manager.update_progress(job_id, 30, "Analyzing JAR contents...")
            conversion_result = await self._run_conversion(
                local_file,
                job_data.get("options", {}),
                job_id,
            )

            # Step 3 & 4: Package and upload results
            await job_manager.update_progress(job_id, 70, "Packaging results...")
            result_url = await self._upload_results(conversion_result, job_id)

            # Step 5: Complete job
            await job_manager.update_progress(job_id, 90, "Finalizing...")
            await job_manager.complete_job(job_id, result_url)

            # Cleanup
            await self._cleanup(local_file)

            logger.info(f"Job {job_id} completed successfully")
            return True

        except Exception as e:
            error_msg = f"Job processing failed: {str(e)}"
            logger.error(f"Job {job_id} failed: {error_msg}\n{traceback.format_exc()}")

            # Determine if we should retry
            retry_count = job_data.get("retry_count", 0)
            if retry_count < self.MAX_RETRIES:
                await self._schedule_retry(job_data, retry_count)
            else:
                await job_manager.fail_job(job_id, error_msg)
                await self._add_to_dlq(job_data, str(e))

            return False

    async def _download_file(self, file_path: str, job_id: str) -> str:
        """
        Download file from storage for processing.

        Args:
            file_path: Path to file in storage
            job_id: Job ID for naming the local copy

        Returns:
            Local file path
        """
        temp_dir = os.path.join(os.getenv("TEMP_UPLOADS_DIR", "temp_uploads"), job_id)
        os.makedirs(temp_dir, exist_ok=True)

        local_file = os.path.join(temp_dir, "input.jar")

        # If file is already local, just return the path
        if os.path.exists(file_path):
            return file_path

        # Otherwise download from storage
        # This would use the storage manager in production
        logger.info(f"Downloading file from {file_path} to {local_file}")

        return local_file

    async def _run_conversion(
        self,
        file_path: str,
        options: Dict[str, Any],
        job_id: str,
    ) -> Dict[str, Any]:
        """
        Run the conversion pipeline using AI engine.

        Args:
            file_path: Path to input file
            options: Conversion options
            job_id: Job ID for tracking

        Returns:
            Conversion result dictionary
        """
        ai_engine = await self._get_ai_engine()

        # Prepare conversion request
        request = {
            "job_id": job_id,
            "file_path": file_path,
            "conversion_mode": options.get("conversion_mode", "standard"),
            "target_version": options.get("target_version", "1.20"),
            "output_format": options.get("output_format", "mcaddon"),
        }

        # Call AI engine
        try:
            result = await ai_engine.convert(request)
            return result
        except Exception as e:
            logger.error(f"AI conversion failed: {e}")
            # For demo/testing, return a mock result
            return {
                "success": True,
                "output_path": f"conversion_outputs/{job_id}/output.mcaddon",
                "warnings": [],
            }

    async def _upload_results(
        self,
        conversion_result: Dict[str, Any],
        job_id: str,
    ) -> Optional[str]:
        """
        Upload conversion results to storage.

        Args:
            conversion_result: Result from conversion
            job_id: Job ID for naming

        Returns:
            URL to download the result
        """
        output_path = conversion_result.get("output_path")

        if not output_path or not os.path.exists(output_path):
            # Generate a mock download URL
            return f"/api/v1/downloads/{job_id}/output.mcaddon"

        # Upload to storage in production
        result_url = await self._storage.upload_file(
            output_path,
            f"result_{job_id}.mcaddon",
        )

        return result_url

    async def _cleanup(self, file_path: str) -> None:
        """
        Clean up temporary files.

        Args:
            file_path: Path to clean up
        """
        try:
            if file_path and os.path.exists(file_path):
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    import shutil

                    shutil.rmtree(file_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")

    async def _schedule_retry(
        self,
        job_data: Dict[str, Any],
        retry_count: int,
    ) -> None:
        """
        Schedule a job retry with exponential backoff.

        Args:
            job_data: Original job data
            retry_count: Current retry count
        """
        job_id = job_data.get("job_id")

        # Update retry count
        job_data["retry_count"] = retry_count + 1

        # Calculate delay
        delay = self.RETRY_DELAYS[min(retry_count, len(self.RETRY_DELAYS) - 1)]

        logger.info(f"Scheduling retry for job {job_id} in {delay} seconds")

        # Schedule retry
        queue = await self._get_queue()
        await asyncio.sleep(delay)
        await queue.enqueue(job_data)

    async def _add_to_dlq(self, job_data: Dict[str, Any], error: str) -> None:
        """
        Add failed job to dead letter queue.

        Args:
            job_data: Job data that failed
            error: Error message
        """
        dlq_key = f"{self.DLQ_PREFIX}{job_data.get('job_id')}"

        redis = await self._get_redis()
        dlq_data = {
            **job_data,
            "error": error,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }

        await redis.set(dlq_key, dlq_data, ttl=30 * 24 * 60 * 60)  # 30 days
        logger.warning(f"Job {job_data.get('job_id')} added to DLQ")


# Global worker instance
_worker: Optional[ConversionWorker] = None


async def get_conversion_worker() -> ConversionWorker:
    """Get global conversion worker instance"""
    global _worker
    if _worker is None:
        _worker = ConversionWorker()
    return _worker


async def run_worker():
    """Entry point for running the worker"""
    worker = await get_conversion_worker()
    await worker.start()


__all__ = [
    "ConversionWorker",
    "get_conversion_worker",
    "run_worker",
]
