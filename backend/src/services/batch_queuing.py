"""
Intelligent Batch Queuing System for v2.5 Milestone

Implements smart queue management with mode-based grouping, priority scheduling,
parallel processing support, and batch job grouping by similar characteristics.

Pipeline Flow:
1. Jobs enter queue
2. Classifier groups by mode (Simple together, Expert together)
3. Priority sorter arranges within groups
4. Resource allocator assigns resources
5. Parallel processor executes

See: docs/GAP-ANALYSIS-v2.5.md (GAP-2.5-05)
"""

import logging
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import heapq

from models.conversion_mode import ConversionMode, ModeClassificationResult
from services.error_handler import ConversionError, categorize_error, get_error_handler

logger = logging.getLogger(__name__)


class QueuePriority(str, Enum):
    """Queue priority levels for job scheduling."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    def to_score(self) -> int:
        """Convert priority to numeric score for sorting."""
        scores = {
            QueuePriority.LOW: 0,
            QueuePriority.NORMAL: 1,
            QueuePriority.HIGH: 2,
            QueuePriority.CRITICAL: 3,
        }
        return scores[self]


class BatchJobStatus(str, Enum):
    """Status of a batch job."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """Represents a single job in the batch queue."""

    job_id: str
    user_id: str
    mod_data: Dict[str, Any]
    mode: Optional[ConversionMode] = None
    mode_classification: Optional[ModeClassificationResult] = None
    priority: QueuePriority = QueuePriority.NORMAL
    priority_score: int = 1  # Computed priority including complexity
    status: BatchJobStatus = BatchJobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    estimated_complexity: int = 0  # Computed complexity score
    resource_requirements: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "BatchJob") -> bool:
        """Enable priority queue sorting."""
        return self.priority_score < other.priority_score


@dataclass
class BatchGroup:
    """A group of similar jobs batched together."""

    group_id: str
    mode: ConversionMode
    jobs: List[BatchJob] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: BatchJobStatus = BatchJobStatus.PENDING
    completed_count: int = 0
    failed_count: int = 0

    @property
    def total_jobs(self) -> int:
        return len(self.jobs)

    @property
    def progress(self) -> float:
        if not self.jobs:
            return 0.0
        return (self.completed_count / len(self.jobs)) * 100


class BatchQueueStats:
    """Statistics for batch queue monitoring."""

    def __init__(self):
        self.total_jobs_enqueued = 0
        self.total_jobs_processed = 0
        self.total_jobs_failed = 0
        self.total_batches_created = 0
        self.mode_distribution: Dict[ConversionMode, int] = defaultdict(int)
        self.average_wait_time_seconds = 0.0
        self.average_processing_time_seconds = 0.0
        self.queue_depth_by_mode: Dict[ConversionMode, int] = defaultdict(int)
        self.last_updated: datetime = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_jobs_enqueued": self.total_jobs_enqueued,
            "total_jobs_processed": self.total_jobs_processed,
            "total_jobs_failed": self.total_jobs_failed,
            "total_batches_created": self.total_batches_created,
            "mode_distribution": {k.value: v for k, v in self.mode_distribution.items()},
            "average_wait_time_seconds": self.average_wait_time_seconds,
            "average_processing_time_seconds": self.average_processing_time_seconds,
            "queue_depth_by_mode": {k.value: v for k, v in self.queue_depth_by_mode.items()},
            "last_updated": self.last_updated.isoformat(),
        }


class IntelligentBatchQueue:
    """
    Intelligent batch queue with mode-based grouping and priority scheduling.

    Implements the batch processing pipeline:
    1. Jobs enter queue
    2. Classifier groups by mode (Simple together, Expert together)
    3. Priority sorter arranges within groups
    4. Resource allocator assigns resources
    5. Parallel processor executes
    """

    def __init__(
        self,
        max_parallel_jobs: int = 4,
        max_group_size: int = 10,
        enable_mode_grouping: bool = True,
        enable_priority_scheduling: bool = True,
    ):
        """
        Initialize the intelligent batch queue.

        Args:
            max_parallel_jobs: Maximum jobs to process in parallel
            max_group_size: Maximum jobs per batch group
            enable_mode_grouping: Whether to group jobs by conversion mode
            enable_priority_scheduling: Whether to enable priority-based scheduling
        """
        self.max_parallel_jobs = max_parallel_jobs
        self.max_group_size = max_group_size
        self.enable_mode_grouping = enable_mode_grouping
        self.enable_priority_scheduling = enable_priority_scheduling

        # Mode-based queues (jobs grouped by conversion mode)
        self._mode_queues: Dict[ConversionMode, List[BatchJob]] = defaultdict(list)

        # Global priority queue for mixed-mode processing
        self._priority_queue: List[BatchJob] = []

        # Batch groups awaiting processing
        self._batch_groups: Dict[str, BatchGroup] = {}

        # Jobs currently being processed
        self._processing_jobs: Dict[str, BatchJob] = {}

        # Job lookup
        self._jobs: Dict[str, BatchJob] = {}

        # Statistics
        self._stats = BatchQueueStats()

        # Executor for parallel processing
        self._executor = ThreadPoolExecutor(max_workers=max_parallel_jobs)

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"IntelligentBatchQueue initialized: "
            f"max_parallel={max_parallel_jobs}, max_group_size={max_group_size}, "
            f"mode_grouping={enable_mode_grouping}, priority_scheduling={enable_priority_scheduling}"
        )

    def _compute_job_priority_score(self, job: BatchJob) -> int:
        """
        Compute the priority score for a job based on multiple factors.

        Score composition:
        - Base priority (user-specified)
        - Complexity factor (higher complexity = adjusted priority)
        - Wait time factor (longer waiting jobs get boost)
        """
        base_score = job.priority.to_score()

        # Complexity factor: expert jobs might need more resources but get handled
        # in their own queue, so we give them a slight boost for fairness
        complexity_factor = 0
        if job.mode:
            complexity_factor = {
                ConversionMode.SIMPLE: 0,
                ConversionMode.STANDARD: 1,
                ConversionMode.COMPLEX: 2,
                ConversionMode.EXPERT: 3,
            }.get(job.mode, 0)

        # Combine scores (priority is most important, then complexity)
        # Higher score = higher priority
        total_score = (base_score * 10) + complexity_factor

        return total_score

    def _compute_job_complexity(self, job: BatchJob) -> int:
        """
        Compute complexity score for a job based on its characteristics.

        Used for resource allocation and group sorting.
        """
        if job.mode_classification:
            features = job.mode_classification.features
            score = 0

            # Class count contribution
            score += min(features.total_classes, 100) // 10

            # Dependency contribution
            score += min(features.total_dependencies, 20)

            # Complex features
            if features.has_dimensions or features.has_worldgen:
                score += 20
            if features.has_multiblock or features.has_custom_AI:
                score += 15
            if features.has_entities:
                score += 5
            if features.has_biomes:
                score += 10

            return score

        # Fallback based on mod_data size
        return len(str(job.mod_data)) // 1000

    async def enqueue_job(
        self,
        user_id: str,
        mod_data: Dict[str, Any],
        mode: Optional[ConversionMode] = None,
        mode_classification: Optional[ModeClassificationResult] = None,
        priority: QueuePriority = QueuePriority.NORMAL,
        job_id: Optional[str] = None,
    ) -> str:
        """
        Add a job to the queue.

        Args:
            user_id: User ID
            mod_data: Mod data to convert
            mode: Conversion mode (if pre-classified)
            mode_classification: Full classification result
            priority: Job priority
            job_id: Optional job ID (generated if not provided)

        Returns:
            Job ID
        """
        async with self._lock:
            job_id = job_id or str(uuid.uuid4())

            # Extract mode from mode_classification if not provided
            if mode is None and mode_classification is not None:
                mode = mode_classification.mode

            job = BatchJob(
                job_id=job_id,
                user_id=user_id,
                mod_data=mod_data,
                mode=mode,
                mode_classification=mode_classification,
                priority=priority,
                status=BatchJobStatus.QUEUED,
            )

            # Compute complexity and priority score
            job.estimated_complexity = self._compute_job_complexity(job)
            job.priority_score = self._compute_job_priority_score(job)

            # Store job
            self._jobs[job_id] = job
            self._stats.total_jobs_enqueued += 1
            self._stats.last_updated = datetime.now(timezone.utc)

            # Add to mode-specific queue if enabled
            if self.enable_mode_grouping and mode:
                heapq.heappush(self._mode_queues[mode], job)
                self._stats.queue_depth_by_mode[mode] += 1
                logger.debug(f"Job {job_id} added to mode queue: {mode.value}")
            else:
                # Add to global priority queue
                heapq.heappush(self._priority_queue, job)

            logger.info(f"Job {job_id} enqueued with priority {priority.value}, mode={mode}")

            return job_id

    async def enqueue_batch(
        self,
        user_id: str,
        jobs_data: List[Dict[str, Any]],
        default_priority: QueuePriority = QueuePriority.NORMAL,
    ) -> List[str]:
        """
        Enqueue multiple jobs as a batch.

        Args:
            user_id: User ID
            jobs_data: List of mod data dicts
            default_priority: Default priority for jobs

        Returns:
            List of job IDs
        """
        job_ids = []
        for mod_data in jobs_data:
            job_id = await self.enqueue_job(
                user_id=user_id,
                mod_data=mod_data,
                priority=default_priority,
            )
            job_ids.append(job_id)
        return job_ids

    async def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    async def get_next_job(self, mode: Optional[ConversionMode] = None) -> Optional[BatchJob]:
        """
        Get the next job from the queue.

        Args:
            mode: If specified, get from specific mode queue

        Returns:
            Next job to process, or None if queue is empty
        """
        async with self._lock:
            if mode and mode in self._mode_queues:
                if self._mode_queues[mode]:
                    job = heapq.heappop(self._mode_queues[mode])
                    self._stats.queue_depth_by_mode[mode] = max(
                        0, self._stats.queue_depth_by_mode[mode] - 1
                    )
                    return job

            # Fallback to global priority queue
            if self._priority_queue:
                return heapq.heappop(self._priority_queue)

            return None

    async def get_batch_group(
        self,
        mode: ConversionMode,
        max_size: Optional[int] = None,
    ) -> Optional[BatchGroup]:
        """
        Get a batch group of similar jobs for parallel processing.

        Args:
            mode: Conversion mode to group
            max_size: Maximum group size (default: self.max_group_size)

        Returns:
            BatchGroup with jobs ready for processing
        """
        async with self._lock:
            max_size = max_size or self.max_group_size

            if mode not in self._mode_queues or not self._mode_queues[mode]:
                return None

            # Pop jobs for this group
            jobs = []
            while len(jobs) < max_size and self._mode_queues[mode]:
                job = heapq.heappop(self._mode_queues[mode])
                job.status = BatchJobStatus.PENDING
                jobs.append(job)

            if not jobs:
                return None

            group_id = str(uuid.uuid4())
            group = BatchGroup(
                group_id=group_id,
                mode=mode,
                jobs=jobs,
            )

            self._batch_groups[group_id] = group
            self._stats.total_batches_created += 1
            self._stats.queue_depth_by_mode[mode] = max(
                0, self._stats.queue_depth_by_mode[mode] - len(jobs)
            )

            logger.info(f"Created batch group {group_id} with {len(jobs)} {mode.value} jobs")

            return group

    async def create_mixed_batch(self, max_size: Optional[int] = None) -> Optional[BatchGroup]:
        """
        Create a mixed batch from global priority queue.

        Takes highest priority jobs regardless of mode.
        Useful when mode grouping is disabled or queues are unbalanced.

        Args:
            max_size: Maximum group size

        Returns:
            BatchGroup with mixed jobs
        """
        async with self._lock:
            max_size = max_size or self.max_group_size

            if not self._priority_queue:
                return None

            # Get highest priority jobs
            jobs = []
            temp_queue = []

            while len(jobs) < max_size and self._priority_queue:
                job = heapq.heappop(self._priority_queue)
                job.status = BatchJobStatus.PENDING
                jobs.append(job)

            # Re-queue remaining jobs
            for job in self._priority_queue:
                heapq.heappush(temp_queue, job)
            self._priority_queue = temp_queue

            if not jobs:
                return None

            # Determine dominant mode (for logging/tracking)
            mode_counts = defaultdict(int)
            for job in jobs:
                if job.mode:
                    mode_counts[job.mode] += 1

            dominant_mode = (
                max(mode_counts.keys(), key=lambda m: mode_counts[m])
                if mode_counts
                else ConversionMode.STANDARD
            )

            group_id = str(uuid.uuid4())
            group = BatchGroup(
                group_id=group_id,
                mode=dominant_mode,
                jobs=jobs,
            )

            self._batch_groups[group_id] = group
            self._stats.total_batches_created += 1

            logger.info(f"Created mixed batch group {group_id} with {len(jobs)} jobs")

            return group

    async def update_job_status(
        self,
        job_id: str,
        status: BatchJobStatus,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update job status.

        Args:
            job_id: Job ID
            status: New status
            error_message: Error message if failed

        Returns:
            True if updated, False if job not found
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            job.status = status
            job.error_message = error_message

            if status == BatchJobStatus.PROCESSING:
                job.started_at = datetime.now(timezone.utc)
                self._processing_jobs[job_id] = job
            elif status == BatchJobStatus.COMPLETED:
                job.completed_at = datetime.now(timezone.utc)
                self._stats.total_jobs_processed += 1
                if job_id in self._processing_jobs:
                    del self._processing_jobs[job_id]
            elif status == BatchJobStatus.FAILED:
                job.completed_at = datetime.now(timezone.utc)
                self._stats.total_jobs_failed += 1
                if job_id in self._processing_jobs:
                    del self._processing_jobs[job_id]

            # Update group status if job is part of a group
            for group in self._batch_groups.values():
                for i, gjob in enumerate(group.jobs):
                    if gjob.job_id == job_id:
                        if status == BatchJobStatus.COMPLETED:
                            group.completed_count += 1
                        elif status == BatchJobStatus.FAILED:
                            group.failed_count += 1
                        break

            self._stats.last_updated = datetime.now(timezone.utc)
            return True

    async def retry_job(self, job_id: str) -> bool:
        """
        Retry a failed job.

        Args:
            job_id: Job ID

        Returns:
            True if re-queued, False if max retries exceeded or job not found
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.retry_count >= job.max_retries:
                logger.warning(f"Job {job_id} max retries exceeded")
                return False

            job.retry_count += 1
            job.status = BatchJobStatus.QUEUED
            job.error_message = None
            job.completed_at = None

            # Re-add to queue
            if self.enable_mode_grouping and job.mode:
                heapq.heappush(self._mode_queues[job.mode], job)
                self._stats.queue_depth_by_mode[job.mode] += 1
            else:
                heapq.heappush(self._priority_queue, job)

            logger.info(f"Job {job_id} re-queued for retry (attempt {job.retry_count})")
            return True

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a queued job.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled, False if not found or already processing
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.status == BatchJobStatus.PROCESSING:
                return False

            job.status = BatchJobStatus.CANCELLED
            self._stats.last_updated = datetime.now(timezone.utc)

            logger.info(f"Job {job_id} cancelled")
            return True

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics."""
        async with self._lock:
            stats = self._stats.to_dict()

            # Add real-time queue depths
            stats["mode_queues"] = {
                mode.value: len(queue) for mode, queue in self._mode_queues.items()
            }
            stats["global_queue_depth"] = len(self._priority_queue)
            stats["jobs_in_processing"] = len(self._processing_jobs)
            stats["active_batch_groups"] = len(self._batch_groups)

            # Calculate total queued
            total_queued = sum(len(q) for q in self._mode_queues.values()) + len(
                self._priority_queue
            )
            stats["total_queued"] = total_queued

            return stats

    async def process_batch_parallel(
        self,
        processor_func: Callable[[BatchJob], Awaitable[Dict[str, Any]]],
        mode: Optional[ConversionMode] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process available jobs in parallel.

        Args:
            processor_func: Async function to process each job
            mode: Process from specific mode queue, or None for global

        Returns:
            Dict with 'completed' and 'failed' job results
        """
        results = {"completed": [], "failed": []}

        # Get batch to process
        if self.enable_mode_grouping and mode:
            batch = await self.get_batch_group(mode)
        elif mode:
            batch = await self.get_batch_group(mode)
        else:
            # Create mixed batch from highest priority jobs
            batch = await self.create_mixed_batch()

        if not batch:
            logger.debug("No batch available for processing")
            return results

        # Process jobs in parallel
        tasks = []
        for job in batch.jobs:
            await self.update_job_status(job.job_id, BatchJobStatus.PROCESSING)
            task = asyncio.create_task(self._process_single_job(job, processor_func))
            tasks.append(task)

        # Wait for all to complete
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for job, result in zip(batch.jobs, task_results):
            if isinstance(result, Exception):
                results["failed"].append(
                    {
                        "job_id": job.job_id,
                        "error": str(result),
                    }
                )
                await self.update_job_status(job.job_id, BatchJobStatus.FAILED, str(result))
            elif result.get("success"):
                results["completed"].append(
                    {
                        "job_id": job.job_id,
                        "result": result,
                    }
                )
                await self.update_job_status(job.job_id, BatchJobStatus.COMPLETED)
            else:
                error = result.get("error", "Unknown error")
                results["failed"].append(
                    {
                        "job_id": job.job_id,
                        "error": error,
                    }
                )
                await self.update_job_status(job.job_id, BatchJobStatus.FAILED, error)

        # Mark batch as completed
        batch.status = BatchJobStatus.COMPLETED

        logger.info(
            f"Batch {batch.group_id} processed: "
            f"{len(results['completed'])} completed, {len(results['failed'])} failed"
        )

        return results

    async def _process_single_job(
        self,
        job: BatchJob,
        processor_func: Callable[[BatchJob], Awaitable[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Process a single job with the given processor function."""
        try:
            result = await processor_func(job)
            return result
        except ConversionError as e:
            # Record via error handler framework
            error_handler = get_error_handler()
            error_handler.record_error(e, job_id=job.job_id)
            categorized = categorize_error(e)
            logger.error(f"Conversion error processing job {job.job_id}: {e}")
            return {"success": False, "error": categorized["user_message"]}
        except Exception as e:
            # Unexpected error - record via error handler framework
            error_handler = get_error_handler()
            error_handler.record_error(e, job_id=job.job_id)
            categorized = categorize_error(e)
            logger.error(f"Error processing job {job.job_id}: {e}")
            return {"success": False, "error": categorized["user_message"]}

    async def close(self):
        """Clean up resources."""
        self._executor.shutdown(wait=True)
        logger.info("IntelligentBatchQueue closed")


# Global queue instance
_batch_queue: Optional[IntelligentBatchQueue] = None


def get_batch_queue() -> IntelligentBatchQueue:
    """Get or create the global batch queue instance."""
    global _batch_queue
    if _batch_queue is None:
        _batch_queue = IntelligentBatchQueue()
    return _batch_queue


def reset_batch_queue():
    """Reset the global batch queue (for testing)."""
    global _batch_queue
    if _batch_queue:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — safe to use asyncio.run()
            asyncio.run(_batch_queue.close())
        else:
            # Already in async context — schedule close without blocking
            loop.create_task(_batch_queue.close())
    _batch_queue = None
