"""
GPU resource pool and inference slot management.

Manages GPU reservation, inference slot allocation, and the
GPU pool abstraction for AI inference workloads.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from collections import defaultdict

from .types import ResourceType


@dataclass
class GPUPool:
    """A pool of homogeneous GPU resources."""

    pool_id: str
    total_capacity_gb: float
    available_capacity_gb: float = 0.0
    allocated_amount_gb: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.available_capacity_gb == 0.0:
            self.available_capacity_gb = self.total_capacity_gb

    @property
    def utilization(self) -> float:
        if self.total_capacity_gb == 0:
            return 100.0
        return (self.allocated_amount_gb / self.total_capacity_gb) * 100

    @property
    def is_available(self) -> bool:
        return self.available_capacity_gb > 0


@dataclass
class InferenceSlot:
    """An inference slot on a GPU for running AI models."""

    slot_id: str
    pool_id: str
    gpu_index: int
    memory_limit_gb: float
    memory_used_gb: float = 0.0
    job_id: Optional[str] = None
    allocated_at: Optional[datetime] = None
    released_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.job_id is not None and self.released_at is None

    @property
    def is_free(self) -> bool:
        return self.job_id is None


@dataclass
class GPUAllocation:
    """GPU resource allocation for a job."""

    allocation_id: str
    job_id: str
    pool_id: str
    allocated_gb: float
    slot_id: Optional[str] = None
    allocated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    released_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.released_at is None


class GPUPoolManager:
    """
    Manages GPU pools and inference slot allocation.

    Handles GPU reservation for AI inference workloads with
    support for multiple GPU types and inference slots.
    """

    def __init__(self):
        self._pools: Dict[str, GPUPool] = {}
        self._slots: Dict[str, InferenceSlot] = {}
        self._allocations: Dict[str, GPUAllocation] = {}
        self._round_robin_index: Dict[str, int] = defaultdict(int)

    def create_pool(
        self,
        pool_id: str,
        total_capacity_gb: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a GPU pool."""
        pool = GPUPool(
            pool_id=pool_id,
            total_capacity_gb=total_capacity_gb,
            metadata=metadata or {},
        )
        self._pools[pool_id] = pool
        return True

    def create_inference_slot(
        self,
        pool_id: str,
        gpu_index: int,
        memory_limit_gb: float,
    ) -> Optional[str]:
        """Create an inference slot within a pool."""
        if pool_id not in self._pools:
            return None

        slot_id = str(uuid.uuid4())
        slot = InferenceSlot(
            slot_id=slot_id,
            pool_id=pool_id,
            gpu_index=gpu_index,
            memory_limit_gb=memory_limit_gb,
        )
        self._slots[slot_id] = slot
        return slot_id

    def allocate_gpu(
        self,
        job_id: str,
        memory_required_gb: float,
        pool_id: Optional[str] = None,
    ) -> Optional[GPUAllocation]:
        """Allocate GPU memory for a job."""
        allocation_id = str(uuid.uuid4())

        if pool_id and pool_id in self._pools:
            pool = self._pools[pool_id]
            if pool.available_capacity_gb < memory_required_gb:
                return None

            pool.available_capacity_gb -= memory_required_gb
            pool.allocated_amount_gb += memory_required_gb

            allocation = GPUAllocation(
                allocation_id=allocation_id,
                job_id=job_id,
                pool_id=pool_id,
                allocated_gb=memory_required_gb,
            )
            self._allocations[allocation_id] = allocation
            return allocation

        for pid, pool in self._pools.items():
            if pool.available_capacity_gb >= memory_required_gb:
                pool.available_capacity_gb -= memory_required_gb
                pool.allocated_amount_gb += memory_required_gb

                allocation = GPUAllocation(
                    allocation_id=allocation_id,
                    job_id=job_id,
                    pool_id=pid,
                    allocated_gb=memory_required_gb,
                )
                self._allocations[allocation_id] = allocation
                return allocation

        return None

    def release_gpu(self, allocation_id: str) -> bool:
        """Release a GPU allocation."""
        allocation = self._allocations.get(allocation_id)
        if not allocation or not allocation.is_active:
            return False

        pool = self._pools.get(allocation.pool_id)
        if pool:
            pool.available_capacity_gb = min(
                pool.total_capacity_gb,
                pool.available_capacity_gb + allocation.allocated_gb,
            )
            pool.allocated_amount_gb = max(0, pool.allocated_amount_gb - allocation.allocated_gb)

        allocation.released_at = datetime.now(timezone.utc)
        return True

    def release_job_gpus(self, job_id: str) -> int:
        """Release all GPU allocations for a job."""
        released = 0
        for alloc in self._allocations.values():
            if alloc.job_id == job_id and alloc.is_active:
                if self.release_gpu(alloc.allocation_id):
                    released += 1
        return released

    def get_pool_stats(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """Get stats for a GPU pool."""
        pool = self._pools.get(pool_id)
        if not pool:
            return None
        return {
            "pool_id": pool.pool_id,
            "total_capacity_gb": pool.total_capacity_gb,
            "available_capacity_gb": pool.available_capacity_gb,
            "allocated_amount_gb": pool.allocated_amount_gb,
            "utilization": pool.utilization,
            "metadata": pool.metadata,
        }

    def get_available_gpu_memory(self) -> float:
        """Get total available GPU memory across all pools."""
        return sum(p.available_capacity_gb for p in self._pools.values())
