"""
Resource Allocator for v2.5 Milestone

Manages GPU/memory tracking, resource capacity, and allocation strategies
(round-robin, capacity-based, mode-based) for intelligent batch processing.

See: docs/GAP-ANALYSIS-v2.5.md (GAP-2.5-05)
"""

import logging
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import copy

from models.conversion_mode import ConversionMode

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Types of resources that can be allocated."""
    GPU = "gpu"
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"


class AllocationStrategy(str, Enum):
    """
    Resource allocation strategies.
    
    - ROUND_ROBIN: Distribute evenly across workers
    - CAPACITY_BASED: Allocate based on job requirements vs available capacity
    - MODE_BASED: Allocate dedicated resources per conversion mode
    - PRIORITY_BASED: Higher priority jobs get more resources
    """
    ROUND_ROBIN = "round_robin"
    CAPACITY_BASED = "capacity_based"
    MODE_BASED = "mode_based"
    PRIORITY_BASED = "priority_based"


@dataclass
class ResourcePool:
    """A pool of homogeneous resources (e.g., all GPUs of a specific type)."""
    pool_id: str
    resource_type: ResourceType
    total_capacity: float
    available_capacity: float
    allocated_amount: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def utilization(self) -> float:
        """Current utilization percentage (0-100)."""
        if self.total_capacity == 0:
            return 100.0
        return (self.allocated_amount / self.total_capacity) * 100

    @property
    def is_available(self) -> bool:
        """Check if pool has capacity available."""
        return self.available_capacity > 0


@dataclass
class ResourceAllocation:
    """Represents a resource allocation for a job or batch."""
    allocation_id: str
    job_id: str
    resource_type: ResourceType
    pool_id: str
    allocated_amount: float
    allocated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    released_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        """Check if allocation is still active."""
        return self.released_at is None


@dataclass
class WorkerNode:
    """Represents a worker node with its resources."""
    node_id: str
    hostname: str
    gpu_count: int = 0
    gpu_memory_total: float = 0.0  # GB
    gpu_memory_available: float = 0.0
    cpu_cores: int = 0
    memory_total: float = 0.0  # GB
    memory_available: float = 0.0
    disk_total: float = 0.0  # GB
    disk_available: float = 0.0
    is_healthy: bool = True
    current_load: float = 0.0  # 0-100%
    active_allocations: List[str] = field(default_factory=list)  # allocation_ids
    mode_affinity: Optional[ConversionMode] = None  # Preferred mode for this node

    @property
    def can_accept_work(self) -> bool:
        """Check if node can accept more work."""
        return self.is_healthy and self.current_load < 90.0

    @property
    def effective_gpu_memory(self) -> float:
        """Effective GPU memory considering current load."""
        return self.gpu_memory_available * (1 - (self.current_load / 100))

    def allocate_resources(
        self,
        gpu_required: float,
        memory_required: float,
        cpu_required: int = 1,
    ) -> bool:
        """
        Attempt to allocate resources on this node.

        Args:
            gpu_required: GPU memory required in GB
            memory_required: RAM required in GB
            cpu_required: CPU cores required

        Returns:
            True if allocation successful, False otherwise
        """
        if not self.can_accept_work:
            return False

        # Check GPU
        if gpu_required > 0 and gpu_required > self.gpu_memory_available:
            return False

        # Check RAM
        if memory_required > self.memory_available:
            return False

        # Check CPU (simplified - just check cores)
        if cpu_required > self.cpu_cores:
            return False

        # Perform allocation
        self.gpu_memory_available -= gpu_required
        self.memory_available -= memory_required
        self.current_load = min(100, self.current_load + 10)

        return True

    def release_resources(
        self,
        gpu_amount: float,
        memory_amount: float,
        cpu_amount: int = 1,
    ):
        """Release resources back to this node."""
        self.gpu_memory_available = min(
            self.gpu_memory_total,
            self.gpu_memory_available + gpu_amount
        )
        self.memory_available = min(
            self.memory_total,
            self.memory_available + memory_amount
        )
        self.current_load = max(0, self.current_load - 10)


@dataclass
class ResourceAllocationRequest:
    """Request for resource allocation."""
    job_id: str
    mode: Optional[ConversionMode] = None
    priority: int = 0
    gpu_memory_required: float = 0.0  # GB
    memory_required: float = 0.0  # GB
    cpu_cores_required: int = 1
    estimated_duration_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ResourceAllocationResult:
    """Result of a resource allocation request."""
    allocation_id: str
    success: bool
    job_id: str
    node_id: Optional[str] = None
    allocated_gpu_memory: float = 0.0
    allocated_memory: float = 0.0
    allocated_cpu_cores: int = 0
    strategy_used: AllocationStrategy = AllocationStrategy.ROUND_ROBIN
    reason: Optional[str] = None
    queue_position: Optional[int] = None


class ResourceAllocatorStats:
    """Statistics for resource allocation monitoring."""

    def __init__(self):
        self.total_allocations = 0
        self.successful_allocations = 0
        self.failed_allocations = 0
        self.total_releases = 0
        self.current_active_allocations = 0
        self.peak_allocations = 0
        self.allocation_by_strategy: Dict[AllocationStrategy, int] = defaultdict(int)
        self.allocation_by_mode: Dict[ConversionMode, int] = defaultdict(int)
        self.node_utilization: Dict[str, float] = {}
        self.wait_queue_depth = 0
        self.last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_allocations": self.total_allocations,
            "successful_allocations": self.successful_allocations,
            "failed_allocations": self.failed_allocations,
            "total_releases": self.total_releases,
            "current_active_allocations": self.current_active_allocations,
            "peak_allocations": self.peak_allocations,
            "allocation_by_strategy": {k.value: v for k, v in self.allocation_by_strategy.items()},
            "allocation_by_mode": {k.value: v for k, v in self.allocation_by_mode.items()},
            "node_utilization": self.node_utilization,
            "wait_queue_depth": self.wait_queue_depth,
            "last_updated": self.last_updated.isoformat(),
        }


class ResourceAllocator:
    """
    Intelligent resource allocator with multiple allocation strategies.

    Supports:
    - GPU/memory tracking across worker nodes
    - Resource capacity management
    - Allocation strategies: round-robin, capacity-based, mode-based, priority-based
    - Resource monitoring and reporting
    """

    def __init__(
        self,
        default_strategy: AllocationStrategy = AllocationStrategy.CAPACITY_BASED,
        enable_mode_affinity: bool = True,
    ):
        """
        Initialize the resource allocator.

        Args:
            default_strategy: Default allocation strategy
            enable_mode_affinity: Whether to enable mode-based resource affinity
        """
        self.default_strategy = default_strategy
        self.enable_mode_affinity = enable_mode_affinity

        # Worker nodes
        self._nodes: Dict[str, WorkerNode] = {}

        # Resource pools
        self._pools: Dict[ResourceType, Dict[str, ResourcePool]] = defaultdict(dict)

        # Active allocations
        self._allocations: Dict[str, ResourceAllocation] = {}

        # Allocation tracking by job
        self._job_allocations: Dict[str, List[str]] = defaultdict(list)

        # Round-robin state
        self._round_robin_index: Dict[str, int] = {}  # Per pool/node type

        # Wait queue for when resources are not available
        self._wait_queue: List[ResourceAllocationRequest] = []

        # Statistics
        self._stats = ResourceAllocatorStats()

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"ResourceAllocator initialized with strategy={default_strategy.value}, "
            f"mode_affinity={enable_mode_affinity}"
        )

    # === Node Management ===

    async def register_node(
        self,
        hostname: str,
        gpu_count: int = 0,
        gpu_memory: float = 0.0,
        cpu_cores: int = 4,
        memory: float = 16.0,
        disk: float = 100.0,
        mode_affinity: Optional[ConversionMode] = None,
    ) -> str:
        """
        Register a worker node with the allocator.

        Args:
            hostname: Node hostname
            gpu_count: Number of GPUs
            gpu_memory: GPU memory per GPU in GB
            cpu_cores: Number of CPU cores
            memory: Total RAM in GB
            disk: Total disk space in GB
            mode_affinity: Preferred conversion mode for this node

        Returns:
            Node ID
        """
        async with self._lock:
            node_id = str(uuid.uuid4())

            node = WorkerNode(
                node_id=node_id,
                hostname=hostname,
                gpu_count=gpu_count,
                gpu_memory_total=gpu_memory * gpu_count,
                gpu_memory_available=gpu_memory * gpu_count,
                cpu_cores=cpu_cores,
                memory_total=memory,
                memory_available=memory,
                disk_total=disk,
                disk_available=disk,
                mode_affinity=mode_affinity,
            )

            self._nodes[node_id] = node

            # Initialize round-robin index
            self._round_robin_index[node_id] = 0

            logger.info(
                f"Registered node {node_id} ({hostname}): "
                f"GPUs={gpu_count}x{gpu_memory}GB, CPU={cpu_cores} cores, RAM={memory}GB"
            )

            return node_id

    async def unregister_node(self, node_id: str) -> bool:
        """
        Unregister a worker node.

        Args:
            node_id: Node ID

        Returns:
            True if unregistered, False if not found
        """
        async with self._lock:
            if node_id not in self._nodes:
                return False

            node = self._nodes[node_id]

            # Release all allocations on this node
            for alloc_id in node.active_allocations[:]:
                await self.release_allocation(alloc_id)

            del self._nodes[node_id]
            logger.info(f"Unregistered node {node_id}")
            return True

    async def update_node_status(
        self,
        node_id: str,
        is_healthy: Optional[bool] = None,
        current_load: Optional[float] = None,
    ) -> bool:
        """Update node health or load status."""
        async with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return False

            if is_healthy is not None:
                node.is_healthy = is_healthy
            if current_load is not None:
                node.current_load = current_load

            return True

    # === Resource Pools ===

    async def create_resource_pool(
        self,
        pool_id: str,
        resource_type: ResourceType,
        total_capacity: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Create a resource pool.

        Args:
            pool_id: Unique pool ID
            resource_type: Type of resource
            total_capacity: Total capacity
            metadata: Optional metadata

        Returns:
            True if created
        """
        async with self._lock:
            pool = ResourcePool(
                pool_id=pool_id,
                resource_type=resource_type,
                total_capacity=total_capacity,
                available_capacity=total_capacity,
                metadata=metadata or {},
            )
            self._pools[resource_type][pool_id] = pool
            self._round_robin_index[f"pool_{pool_id}"] = 0
            return True

    async def get_pool_stats(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """Get stats for a resource pool."""
        async with self._lock:
            for pools in self._pools.values():
                if pool_id in pools:
                    pool = pools[pool_id]
                    return {
                        "pool_id": pool.pool_id,
                        "resource_type": pool.resource_type.value,
                        "total_capacity": pool.total_capacity,
                        "available_capacity": pool.available_capacity,
                        "allocated_amount": pool.allocated_amount,
                        "utilization": pool.utilization,
                        "metadata": pool.metadata,
                    }
            return None

    # === Allocation ===

    async def allocate(
        self,
        request: ResourceAllocationRequest,
        strategy: Optional[AllocationStrategy] = None,
    ) -> ResourceAllocationResult:
        """
        Allocate resources for a job.

        Args:
            request: Resource allocation request
            strategy: Allocation strategy to use (default: self.default_strategy)

        Returns:
            ResourceAllocationResult
        """
        strategy = strategy or self.default_strategy

        async with self._lock:
            self._stats.total_allocations += 1

            # Try allocation based on strategy
            if strategy == AllocationStrategy.ROUND_ROBIN:
                result = await self._allocate_round_robin(request)
            elif strategy == AllocationStrategy.CAPACITY_BASED:
                result = await self._allocate_capacity_based(request)
            elif strategy == AllocationStrategy.MODE_BASED:
                result = await self._allocate_mode_based(request)
            elif strategy == AllocationStrategy.PRIORITY_BASED:
                result = await self._allocate_priority_based(request)
            else:
                result = await self._allocate_capacity_based(request)

            self._stats.allocation_by_strategy[strategy] += 1

            if result.success:
                self._stats.successful_allocations += 1
                self._stats.current_active_allocations = len(self._allocations)
                self._stats.peak_allocations = max(
                    self._stats.peak_allocations,
                    self._stats.current_active_allocations
                )
                if request.mode:
                    self._stats.allocation_by_mode[request.mode] += 1
            else:
                self._stats.failed_allocations += 1
                # Add to wait queue
                self._wait_queue.append(request)
                self._stats.wait_queue_depth = len(self._wait_queue)
                result.queue_position = len(self._wait_queue)

            self._stats.last_updated = datetime.now(timezone.utc)
            return result

    async def _allocate_round_robin(
        self,
        request: ResourceAllocationRequest,
    ) -> ResourceAllocationResult:
        """Allocate using round-robin strategy across healthy nodes."""
        allocation_id = str(uuid.uuid4())

        # Get healthy nodes
        healthy_nodes = [n for n in self._nodes.values() if n.can_accept_work]
        if not healthy_nodes:
            return ResourceAllocationResult(
                allocation_id=allocation_id,
                success=False,
                job_id=request.job_id,
                strategy_used=AllocationStrategy.ROUND_ROBIN,
                reason="No healthy nodes available",
            )

        # Round-robin selection
        node_id = list(healthy_nodes.keys())[self._round_robin_index.get("global", 0) % len(healthy_nodes)]
        self._round_robin_index["global"] = (self._round_robin_index.get("global", 0) + 1) % len(healthy_nodes)

        node = self._nodes[node_id]

        # Try allocation
        if node.allocate_resources(
            gpu_required=request.gpu_memory_required,
            memory_required=request.memory_required,
            cpu_required=request.cpu_cores_required,
        ):
            # Create allocation record
            allocation = ResourceAllocation(
                allocation_id=allocation_id,
                job_id=request.job_id,
                resource_type=ResourceType.GPU if request.gpu_memory_required > 0 else ResourceType.MEMORY,
                pool_id=node_id,
                allocated_amount=request.gpu_memory_required or request.memory_required,
            )
            self._allocations[allocation_id] = allocation
            node.active_allocations.append(allocation_id)
            self._job_allocations[request.job_id].append(allocation_id)

            return ResourceAllocationResult(
                allocation_id=allocation_id,
                success=True,
                job_id=request.job_id,
                node_id=node_id,
                allocated_gpu_memory=request.gpu_memory_required,
                allocated_memory=request.memory_required,
                allocated_cpu_cores=request.cpu_cores_required,
                strategy_used=AllocationStrategy.ROUND_ROBIN,
            )
        else:
            return ResourceAllocationResult(
                allocation_id=allocation_id,
                success=False,
                job_id=request.job_id,
                strategy_used=AllocationStrategy.ROUND_ROBIN,
                reason="Node resources exhausted",
            )

    async def _allocate_capacity_based(
        self,
        request: ResourceAllocationRequest,
    ) -> ResourceAllocationResult:
        """Allocate based on available capacity (best fit)."""
        allocation_id = str(uuid.uuid4())

        # Find node with best fit
        best_node = None
        best_utilization = float('inf')

        for node in self._nodes.values():
            if not node.can_accept_work:
                continue

            # Check if node can satisfy requirements
            if (request.gpu_memory_required > 0 and request.gpu_memory_required > node.gpu_memory_available):
                continue
            if request.memory_required > node.memory_available:
                continue
            if request.cpu_cores_required > node.cpu_cores:
                continue

            # Select node with lowest utilization that can handle the job
            if node.current_load < best_utilization:
                best_utilization = node.current_load
                best_node = node

        if not best_node:
            return ResourceAllocationResult(
                allocation_id=allocation_id,
                success=False,
                job_id=request.job_id,
                strategy_used=AllocationStrategy.CAPACITY_BASED,
                reason="No node with sufficient capacity",
            )

        # Perform allocation
        best_node.allocate_resources(
            gpu_required=request.gpu_memory_required,
            memory_required=request.memory_required,
            cpu_required=request.cpu_cores_required,
        )

        allocation = ResourceAllocation(
            allocation_id=allocation_id,
            job_id=request.job_id,
            resource_type=ResourceType.GPU if request.gpu_memory_required > 0 else ResourceType.MEMORY,
            pool_id=best_node.node_id,
            allocated_amount=request.gpu_memory_required or request.memory_required,
        )
        self._allocations[allocation_id] = allocation
        best_node.active_allocations.append(allocation_id)
        self._job_allocations[request.job_id].append(allocation_id)

        return ResourceAllocationResult(
            allocation_id=allocation_id,
            success=True,
            job_id=request.job_id,
            node_id=best_node.node_id,
            allocated_gpu_memory=request.gpu_memory_required,
            allocated_memory=request.memory_required,
            allocated_cpu_cores=request.cpu_cores_required,
            strategy_used=AllocationStrategy.CAPACITY_BASED,
        )

    async def _allocate_mode_based(
        self,
        request: ResourceAllocationRequest,
    ) -> ResourceAllocationResult:
        """Allocate resources based on conversion mode affinity."""
        allocation_id = str(uuid.uuid4())

        # First, try to find a node with matching mode affinity
        if request.mode and self.enable_mode_affinity:
            affinity_nodes = [
                n for n in self._nodes.values()
                if n.can_accept_work and n.mode_affinity == request.mode
            ]

            if affinity_nodes:
                # Use capacity-based allocation among affinity nodes
                for node in affinity_nodes:
                    if (request.gpu_memory_required <= node.gpu_memory_available and
                        request.memory_required <= node.memory_available and
                        request.cpu_cores_required <= node.cpu_cores):

                        node.allocate_resources(
                            gpu_required=request.gpu_memory_required,
                            memory_required=request.memory_required,
                            cpu_required=request.cpu_cores_required,
                        )

                        allocation = ResourceAllocation(
                            allocation_id=allocation_id,
                            job_id=request.job_id,
                            resource_type=ResourceType.GPU if request.gpu_memory_required > 0 else ResourceType.MEMORY,
                            pool_id=node.node_id,
                            allocated_amount=request.gpu_memory_required or request.memory_required,
                        )
                        self._allocations[allocation_id] = allocation
                        node.active_allocations.append(allocation_id)
                        self._job_allocations[request.job_id].append(allocation_id)

                        return ResourceAllocationResult(
                            allocation_id=allocation_id,
                            success=True,
                            job_id=request.job_id,
                            node_id=node.node_id,
                            allocated_gpu_memory=request.gpu_memory_required,
                            allocated_memory=request.memory_required,
                            allocated_cpu_cores=request.cpu_cores_required,
                            strategy_used=AllocationStrategy.MODE_BASED,
                        )

        # Fallback to capacity-based allocation
        return await self._allocate_capacity_based(request)

    async def _allocate_priority_based(
        self,
        request: ResourceAllocationRequest,
    ) -> ResourceAllocationResult:
        """Allocate giving priority to higher-priority jobs."""
        allocation_id = str(uuid.uuid4())

        # Sort nodes by availability (most available first)
        sorted_nodes = sorted(
            [n for n in self._nodes.values() if n.can_accept_work],
            key=lambda n: n.current_load
        )

        for node in sorted_nodes:
            if (request.gpu_memory_required <= node.gpu_memory_available and
                request.memory_required <= node.memory_available and
                request.cpu_cores_required <= node.cpu_cores):

                node.allocate_resources(
                    gpu_required=request.gpu_memory_required,
                    memory_required=request.memory_required,
                    cpu_required=request.cpu_cores_required,
                )

                allocation = ResourceAllocation(
                    allocation_id=allocation_id,
                    job_id=request.job_id,
                    resource_type=ResourceType.GPU if request.gpu_memory_required > 0 else ResourceType.MEMORY,
                    pool_id=node.node_id,
                    allocated_amount=request.gpu_memory_required or request.memory_required,
                )
                self._allocations[allocation_id] = allocation
                node.active_allocations.append(allocation_id)
                self._job_allocations[request.job_id].append(allocation_id)

                return ResourceAllocationResult(
                    allocation_id=allocation_id,
                    success=True,
                    job_id=request.job_id,
                    node_id=node.node_id,
                    allocated_gpu_memory=request.gpu_memory_required,
                    allocated_memory=request.memory_required,
                    allocated_cpu_cores=request.cpu_cores_required,
                    strategy_used=AllocationStrategy.PRIORITY_BASED,
                )

        return ResourceAllocationResult(
            allocation_id=allocation_id,
            success=False,
            job_id=request.job_id,
            strategy_used=AllocationStrategy.PRIORITY_BASED,
            reason="No node with sufficient capacity",
        )

    async def release_allocation(self, allocation_id: str) -> bool:
        """
        Release a resource allocation.

        Args:
            allocation_id: Allocation ID to release

        Returns:
            True if released, False if not found
        """
        async with self._lock:
            allocation = self._allocations.get(allocation_id)
            if not allocation:
                return False

            if allocation.is_active:
                allocation.released_at = datetime.now(timezone.utc)

            # Find and update the node
            node = self._nodes.get(allocation.pool_id)
            if node and allocation_id in node.active_allocations:
                node.active_allocations.remove(allocation_id)
                node.release_resources(
                    gpu_amount=allocation.allocated_amount,
                    memory_amount=0,  # Memory tracked separately
                )

            self._stats.total_releases += 1
            self._stats.current_active_allocations = max(
                0, self._stats.current_active_allocations - 1
            )
            self._stats.last_updated = datetime.now(timezone.utc)

            logger.debug(f"Released allocation {allocation_id}")
            return True

    async def release_job_allocations(self, job_id: str) -> int:
        """
        Release all allocations for a job.

        Args:
            job_id: Job ID

        Returns:
            Number of allocations released
        """
        allocation_ids = self._job_allocations.get(job_id, [])
        released = 0

        for alloc_id in allocation_ids:
            if await self.release_allocation(alloc_id):
                released += 1

        if allocation_ids:
            del self._job_allocations[job_id]

        return released

    # === Utility Methods ===

    async def get_allocation(self, allocation_id: str) -> Optional[ResourceAllocation]:
        """Get an allocation by ID."""
        return self._allocations.get(allocation_id)

    async def get_node_allocations(self, node_id: str) -> List[ResourceAllocation]:
        """Get all allocations for a node."""
        node = self._nodes.get(node_id)
        if not node:
            return []

        return [
            self._allocations[aid]
            for aid in node.active_allocations
            if aid in self._allocations
        ]

    async def get_job_allocations(self, job_id: str) -> List[ResourceAllocation]:
        """Get all allocations for a job."""
        allocation_ids = self._job_allocations.get(job_id, [])
        return [
            self._allocations[aid]
            for aid in allocation_ids
            if aid in self._allocations
        ]

    async def process_wait_queue(self) -> int:
        """
        Process jobs in the wait queue.

        Returns:
            Number of jobs successfully allocated from queue
        """
        processed = 0
        still_waiting = []

        # Sort by priority (higher first)
        self._wait_queue.sort(key=lambda r: r.priority, reverse=True)

        for request in self._wait_queue:
            result = await self.allocate(request)
            if result.success:
                processed += 1
            else:
                still_waiting.append(request)

        self._wait_queue = still_waiting
        self._stats.wait_queue_depth = len(self._wait_queue)

        return processed

    async def get_stats(self) -> Dict[str, Any]:
        """Get resource allocator statistics."""
        async with self._lock:
            stats = self._stats.to_dict()

            # Add node details
            stats["nodes"] = {}
            for node_id, node in self._nodes.items():
                stats["nodes"][node_id] = {
                    "node_id": node.node_id,
                    "hostname": node.hostname,
                    "gpu_memory_available_gb": node.gpu_memory_available,
                    "gpu_memory_total_gb": node.gpu_memory_total,
                    "memory_available_gb": node.memory_available,
                    "memory_total_gb": node.memory_total,
                    "cpu_cores": node.cpu_cores,
                    "current_load_percent": node.current_load,
                    "is_healthy": node.is_healthy,
                    "can_accept_work": node.can_accept_work,
                    "active_allocation_count": len(node.active_allocations),
                    "mode_affinity": node.mode_affinity.value if node.mode_affinity else None,
                }

            # Add pool details
            stats["pools"] = {}
            for res_type, pools in self._pools.items():
                stats["pools"][res_type.value] = {
                    pool_id: {
                        "total_capacity": p.total_capacity,
                        "available_capacity": p.available_capacity,
                        "utilization": p.utilization,
                    }
                    for pool_id, p in pools.items()
                }

            stats["active_allocations_count"] = len(self._allocations)
            stats["wait_queue_depth"] = len(self._wait_queue)

            return stats

    async def get_available_resources(self) -> Dict[str, Any]:
        """Get summary of available resources across all nodes."""
        total_gpu_memory = sum(n.gpu_memory_available for n in self._nodes.values())
        total_memory = sum(n.memory_available for n in self._nodes.values())
        total_cpu_cores = sum(n.cpu_cores for n in self._nodes.values() if n.is_healthy)

        healthy_nodes = sum(1 for n in self._nodes.values() if n.is_healthy)

        return {
            "total_nodes": len(self._nodes),
            "healthy_nodes": healthy_nodes,
            "total_gpu_memory_available_gb": total_gpu_memory,
            "total_memory_available_gb": total_memory,
            "total_cpu_cores_available": total_cpu_cores,
        }

    async def close(self):
        """Clean up resources."""
        # Release all allocations
        for allocation_id in list(self._allocations.keys()):
            await self.release_allocation(allocation_id)

        logger.info("ResourceAllocator closed")


# Global allocator instance
_resource_allocator: Optional[ResourceAllocator] = None


def get_resource_allocator() -> ResourceAllocator:
    """Get or create the global resource allocator instance."""
    global _resource_allocator
    if _resource_allocator is None:
        _resource_allocator = ResourceAllocator()
    return _resource_allocator


def reset_resource_allocator():
    """Reset the global resource allocator (for testing)."""
    global _resource_allocator
    if _resource_allocator:
        asyncio.run(_resource_allocator.close())
    _resource_allocator = None
