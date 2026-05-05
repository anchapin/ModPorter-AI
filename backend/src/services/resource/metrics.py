"""
Resource utilization metrics collection.

Collects and reports resource utilization metrics that feed
into automation_metrics.py for monitoring and alerting.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List
from collections import defaultdict


@dataclass
class UtilizationSnapshot:
    """A snapshot of resource utilization at a point in time."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_nodes: int = 0
    healthy_nodes: int = 0
    total_gpu_memory_gb: float = 0.0
    available_gpu_memory_gb: float = 0.0
    total_memory_gb: float = 0.0
    available_memory_gb: float = 0.0
    total_cpu_cores: int = 0
    available_cpu_cores: int = 0
    active_allocations: int = 0
    pending_jobs: int = 0

    @property
    def gpu_utilization_percent(self) -> float:
        if self.total_gpu_memory_gb == 0:
            return 0.0
        used = self.total_gpu_memory_gb - self.available_gpu_memory_gb
        return (used / self.total_gpu_memory_gb) * 100

    @property
    def memory_utilization_percent(self) -> float:
        if self.total_memory_gb == 0:
            return 0.0
        used = self.total_memory_gb - self.available_memory_gb
        return (used / self.total_memory_gb) * 100


class ResourceMetricsCollector:
    """
    Collects resource utilization metrics.

    Provides metrics collection for monitoring resource usage
    patterns and feeding data into automation_metrics.py.
    """

    def __init__(self):
        self._snapshots: List[UtilizationSnapshot] = []
        self._peak_allocations: int = 0
        self._total_allocations: int = 0
        self._failed_allocations: int = 0
        self._by_strategy: Dict[str, int] = defaultdict(int)
        self._by_mode: Dict[str, int] = defaultdict(int)

    def record_allocation(
        self,
        gpu_memory_gb: float,
        memory_gb: float,
        strategy: str,
        mode: str,
    ):
        """Record a successful allocation."""
        self._total_allocations += 1

    def record_failed_allocation(self):
        """Record a failed allocation."""
        self._failed_allocations += 1

    def record_strategy_used(self, strategy: str):
        """Record which allocation strategy was used."""
        self._by_strategy[strategy] += 1

    def record_mode_used(self, mode: str):
        """Record which conversion mode was used."""
        self._by_mode[mode] += 1

    def update_peak(self, current_allocations: int):
        """Update peak allocation count."""
        self._peak_allocations = max(self._peak_allocations, current_allocations)

    def add_snapshot(self, snapshot: UtilizationSnapshot):
        """Add a utilization snapshot."""
        self._snapshots.append(snapshot)
        if len(self._snapshots) > 1000:
            self._snapshots = self._snapshots[-1000:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        latest = self._snapshots[-1] if self._snapshots else None

        return {
            "total_allocations": self._total_allocations,
            "failed_allocations": self._failed_allocations,
            "peak_allocations": self._peak_allocations,
            "allocation_by_strategy": dict(self._by_strategy),
            "allocation_by_mode": dict(self._by_mode),
            "latest_snapshot": {
                "timestamp": latest.timestamp.isoformat() if latest else None,
                "gpu_utilization_percent": latest.gpu_utilization_percent if latest else 0.0,
                "memory_utilization_percent": latest.memory_utilization_percent if latest else 0.0,
                "active_allocations": latest.active_allocations if latest else 0,
                "pending_jobs": latest.pending_jobs if latest else 0,
            }
            if latest
            else None,
        }
