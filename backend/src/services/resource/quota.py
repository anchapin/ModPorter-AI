"""
Per-job CPU/memory quota tracking.

Tracks resource quotas per conversion job including GPU memory,
RAM, and CPU core allocation limits.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from models.conversion_mode import ConversionMode


@dataclass
class JobQuota:
    """Resource quota for a single job."""

    job_id: str
    gpu_memory_quota_gb: float = 0.0
    memory_quota_gb: float = 0.0
    cpu_cores_quota: int = 1
    estimated_duration_seconds: int = 300
    mode: Optional[ConversionMode] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class QuotaAllocation:
    """Result of allocating a quota to a job."""

    allocation_id: str
    job_id: str
    gpu_memory_allocated_gb: float
    memory_allocated_gb: float
    cpu_cores_allocated: int
    allocated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    released_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.released_at is None


class QuotaTracker:
    """
    Tracks per-job resource quotas.

    Manages the allocation and release of quotas for individual jobs,
    supporting both GPU-heavy and CPU-only workloads.
    """

    def __init__(self):
        self._quotas: Dict[str, JobQuota] = {}
        self._allocations: Dict[str, QuotaAllocation] = {}

    def register_quota(self, quota: JobQuota) -> str:
        """Register a quota for a job."""
        self._quotas[quota.job_id] = quota
        return quota.job_id

    def allocate_quota(self, job_id: str) -> Optional[QuotaAllocation]:
        """Allocate resources for a job based on its quota."""
        quota = self._quotas.get(job_id)
        if not quota:
            return None

        allocation_id = str(uuid.uuid4())
        allocation = QuotaAllocation(
            allocation_id=allocation_id,
            job_id=job_id,
            gpu_memory_allocated_gb=quota.gpu_memory_quota_gb,
            memory_allocated_gb=quota.memory_quota_gb,
            cpu_cores_allocated=quota.cpu_cores_quota,
        )
        self._allocations[allocation_id] = allocation
        return allocation

    def release_quota(self, job_id: str) -> int:
        """Release all quotas for a job. Returns number released."""
        released = 0
        for alloc in self._allocations.values():
            if alloc.job_id == job_id and alloc.is_active:
                alloc.released_at = datetime.now(timezone.utc)
                released += 1
        return released

    def get_quota(self, job_id: str) -> Optional[JobQuota]:
        """Get quota for a job."""
        return self._quotas.get(job_id)

    def get_allocation(self, allocation_id: str) -> Optional[QuotaAllocation]:
        """Get allocation by ID."""
        return self._allocations.get(allocation_id)

    def get_job_allocations(self, job_id: str) -> list:
        """Get all allocations for a job."""
        return [
            a for a in self._allocations.values() if a.job_id == job_id
        ]