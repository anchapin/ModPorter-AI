"""
Resource Allocator - Backwards Compatibility Module

This module provides backwards compatibility for imports from services.resource_allocator.
The actual implementation has been split into the resource/ subpackage.

Legacy import path: from services.resource_allocator import ...
New import path: from services.resource import ...

See: docs/GAP-ANALYSIS-v2.5.md (GAP-2.5-05)
"""

from services.resource import (
    ResourceType,
    AllocationStrategy,
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