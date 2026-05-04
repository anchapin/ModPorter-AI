"""
Resource allocation subpackage.

Provides intelligent resource management for GPU/memory tracking,
resource capacity, and allocation strategies for batch processing.

Modules:
- types: ResourceType and AllocationStrategy enums
- quota: Per-job CPU/memory quota tracking
- gpu_pool: GPU reservation and inference slot management
- admission: Admission control and overflow queuing
- metrics: Resource utilization metrics collection

Original monolithic file: services/resource_allocator.py (33K)
"""

from .types import ResourceType, AllocationStrategy
from .quota import JobQuota, QuotaAllocation, QuotaTracker
from .gpu_pool import GPUPool, InferenceSlot, GPUAllocation, GPUPoolManager
from .admission import AdmissionRequest, AdmissionDecision, OverflowJob, AdmissionController
from .metrics import UtilizationSnapshot, ResourceMetricsCollector

from .allocator import (
    ResourcePool,
    ResourceAllocation,
    WorkerNode,
    ResourceAllocationRequest,
    ResourceAllocationResult,
    ResourceAllocatorStats,
    ResourceAllocator,
    get_resource_allocator,
    reset_resource_allocator,
)

__all__ = [
    "ResourceType",
    "AllocationStrategy",
    "JobQuota",
    "QuotaAllocation",
    "QuotaTracker",
    "GPUPool",
    "InferenceSlot",
    "GPUAllocation",
    "GPUPoolManager",
    "AdmissionRequest",
    "AdmissionDecision",
    "OverflowJob",
    "AdmissionController",
    "UtilizationSnapshot",
    "ResourceMetricsCollector",
    "ResourcePool",
    "ResourceAllocation",
    "WorkerNode",
    "ResourceAllocationRequest",
    "ResourceAllocationResult",
    "ResourceAllocatorStats",
    "ResourceAllocator",
    "get_resource_allocator",
    "reset_resource_allocator",
]