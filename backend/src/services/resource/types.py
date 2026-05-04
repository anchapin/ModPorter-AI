"""
Shared types for resource management.
"""

from enum import Enum


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