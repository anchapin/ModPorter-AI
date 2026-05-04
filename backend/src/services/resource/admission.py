"""
Admission control and overflow queuing.

Handles admission control decisions (reject jobs when at capacity)
and manages the overflow waiting queue for pending jobs.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from models.conversion_mode import ConversionMode

logger = logging.getLogger(__name__)


@dataclass
class AdmissionRequest:
    """A request for admission evaluation."""

    job_id: str
    mode: Optional[ConversionMode] = None
    priority: int = 0
    gpu_memory_required_gb: float = 0.0
    memory_required_gb: float = 0.0
    cpu_cores_required: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AdmissionDecision:
    """Result of an admission control decision."""

    admitted: bool
    job_id: str
    reason: Optional[str] = None
    queue_position: Optional[int] = None
    estimated_wait_seconds: Optional[int] = None


@dataclass
class OverflowJob:
    """A job in the overflow waiting queue."""

    request: AdmissionRequest
    queue_position: int
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attempts: int = 0


class AdmissionController:
    """
    Admission control with overflow queuing.

    Decides whether to admit jobs based on current capacity
    and manages the overflow queue when resources are constrained.
    """

    def __init__(
        self,
        max_concurrent_jobs: int = 10,
        max_gpu_memory_gb: float = 32.0,
        max_memory_gb: float = 64.0,
    ):
        """
        Initialize admission controller.

        Args:
            max_concurrent_jobs: Maximum concurrent jobs allowed
            max_gpu_memory_gb: Maximum GPU memory in GB
            max_memory_gb: Maximum system memory in GB
        """
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_gpu_memory_gb = max_gpu_memory_gb
        self.max_memory_gb = max_memory_gb

        self._active_job_count: int = 0
        self._active_gpu_memory_gb: float = 0.0
        self._active_memory_gb: float = 0.0
        self._overflow_queue: List[OverflowJob] = []

    def evaluate_admission(self, request: AdmissionRequest) -> AdmissionDecision:
        """
        Evaluate whether a job should be admitted.

        Args:
            request: The admission request

        Returns:
            AdmissionDecision with admit/reject decision
        """
        if self._active_job_count >= self.max_concurrent_jobs:
            position = self._add_to_overflow(request)
            logger.info(f"Job {request.job_id} queued at position {position}: at capacity")
            return AdmissionDecision(
                admitted=False,
                job_id=request.job_id,
                reason="At maximum capacity",
                queue_position=position,
            )

        gpu_needed = request.gpu_memory_required_gb
        if self._active_gpu_memory_gb + gpu_needed > self.max_gpu_memory_gb:
            position = self._add_to_overflow(request)
            logger.info(f"Job {request.job_id} queued at position {position}: GPU memory")
            return AdmissionDecision(
                admitted=False,
                job_id=request.job_id,
                reason="GPU memory capacity exceeded",
                queue_position=position,
            )

        mem_needed = request.memory_required_gb
        if self._active_memory_gb + mem_needed > self.max_memory_gb:
            position = self._add_to_overflow(request)
            logger.info(f"Job {request.job_id} queued at position {position}: system memory")
            return AdmissionDecision(
                admitted=False,
                job_id=request.job_id,
                reason="System memory capacity exceeded",
                queue_position=position,
            )

        logger.info(f"Job {request.job_id} admitted")
        return AdmissionDecision(admitted=True, job_id=request.job_id)

    def admit_job(self, request: AdmissionRequest) -> bool:
        """
        Record that a job has been admitted.

        Args:
            request: The admission request

        Returns:
            True if admitted, False if capacity would be exceeded
        """
        if self._active_job_count >= self.max_concurrent_jobs:
            return False
        if self._active_gpu_memory_gb + request.gpu_memory_required_gb > self.max_gpu_memory_gb:
            return False
        if self._active_memory_gb + request.memory_required_gb > self.max_memory_gb:
            return False

        self._active_job_count += 1
        self._active_gpu_memory_gb += request.gpu_memory_required_gb
        self._active_memory_gb += request.memory_required_gb
        return True

    def release_job(self, request: AdmissionRequest) -> int:
        """
        Release resources from a completed job.

        Args:
            request: The original admission request

        Returns:
            Number of jobs that could be dequeued from overflow
        """
        self._active_job_count = max(0, self._active_job_count - 1)
        self._active_gpu_memory_gb = max(0, self._active_gpu_memory_gb - request.gpu_memory_required_gb)
        self._active_memory_gb = max(0, self._active_memory_gb - request.memory_required_gb)

        dequeued = 0
        while self._overflow_queue:
            next_job = self._overflow_queue[0]
            decision = self._can_admit(next_job.request)
            if decision.admitted:
                self._overflow_queue.pop(0)
                self._requeue_admitted(next_job.request)
                dequeued += 1
            else:
                break

        return dequeued

    def _add_to_overflow(self, request: AdmissionRequest) -> int:
        """Add a request to the overflow queue."""
        position = len(self._overflow_queue) + 1
        overflow_job = OverflowJob(request=request, queue_position=position)
        self._overflow_queue.append(overflow_job)
        return position

    def _can_admit(self, request: AdmissionRequest) -> AdmissionDecision:
        """Check if a request can be admitted given current load."""
        if self._active_job_count >= self.max_concurrent_jobs:
            return AdmissionDecision(
                admitted=False,
                job_id=request.job_id,
                reason="At maximum capacity",
            )
        if self._active_gpu_memory_gb + request.gpu_memory_required_gb > self.max_gpu_memory_gb:
            return AdmissionDecision(
                admitted=False,
                job_id=request.job_id,
                reason="GPU memory capacity exceeded",
            )
        if self._active_memory_gb + request.memory_required_gb > self.max_memory_gb:
            return AdmissionDecision(
                admitted=False,
                job_id=request.job_id,
                reason="System memory capacity exceeded",
            )
        return AdmissionDecision(admitted=True, job_id=request.job_id)

    def _requeue_admitted(self, request: AdmissionRequest):
        """Re-queue an admitted overflow job by updating internal state."""
        self._active_job_count += 1
        self._active_gpu_memory_gb += request.gpu_memory_required_gb
        self._active_memory_gb += request.memory_required_gb

    def get_overflow_queue_depth(self) -> int:
        """Get the current overflow queue depth."""
        return len(self._overflow_queue)

    def get_pending_requests(self) -> List[AdmissionRequest]:
        """Get all pending requests in overflow queue."""
        return [job.request for job in self._overflow_queue]

    def get_capacity_status(self) -> Dict[str, Any]:
        """Get current capacity status."""
        return {
            "active_jobs": self._active_job_count,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "active_gpu_memory_gb": self._active_gpu_memory_gb,
            "max_gpu_memory_gb": self.max_gpu_memory_gb,
            "active_memory_gb": self._active_memory_gb,
            "max_memory_gb": self.max_memory_gb,
            "overflow_queue_depth": len(self._overflow_queue),
        }