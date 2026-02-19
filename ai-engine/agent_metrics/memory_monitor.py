"""
Memory Monitor for tracking memory usage during operations
"""

import time
import threading
import tracemalloc
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
import os

# Try to import psutil for more detailed memory info
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class MemorySnapshot:
    """Snapshot of memory usage at a point in time"""
    timestamp: float
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory percentage
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryAlert:
    """Alert for memory threshold exceeded"""
    timestamp: float
    current_mb: float
    threshold_mb: float
    percent: float
    message: str


class MemoryMonitor:
    """
    Thread-safe memory monitor for tracking memory usage.
    
    Features:
    - Track memory usage over time
    - Memory snapshots with labels
    - Threshold alerts
    - Memory leak detection
    - Export for dashboards
    """
    
    def __init__(
        self,
        warning_threshold_mb: float = 500.0,
        critical_threshold_mb: float = 1000.0,
        snapshot_interval: float = 60.0
    ):
        """
        Initialize the memory monitor.
        
        Args:
            warning_threshold_mb: Warning threshold in MB
            critical_threshold_mb: Critical threshold in MB
            snapshot_interval: Interval for automatic snapshots in seconds
        """
        self._lock = threading.Lock()
        self._snapshots: List[MemorySnapshot] = []
        self._alerts: List[MemoryAlert] = []
        self._warning_threshold = warning_threshold_mb
        self._critical_threshold = critical_threshold_mb
        self._snapshot_interval = snapshot_interval
        self._alert_callbacks: List[Callable] = []
        self._max_snapshots = 1000
        self._max_alerts = 100
        self._process = None
        self._baseline: Optional[MemorySnapshot] = None
        
        # Initialize process handle if psutil is available
        if HAS_PSUTIL:
            try:
                self._process = psutil.Process(os.getpid())
            except Exception:
                pass
        
        # Start tracemalloc for detailed tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start()
    
    def take_snapshot(self, label: str = "", metadata: Dict[str, Any] = None) -> MemorySnapshot:
        """
        Take a memory usage snapshot.
        
        Args:
            label: Optional label for the snapshot
            metadata: Optional metadata
            
        Returns:
            MemorySnapshot with current memory usage
        """
        snapshot = self._get_memory_snapshot(label, metadata)
        
        with self._lock:
            # Set baseline if not set
            if self._baseline is None:
                self._baseline = snapshot
            
            self._snapshots.append(snapshot)
            
            # Trim old snapshots if needed
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots = self._snapshots[-self._max_snapshots:]
            
            # Check thresholds
            self._check_thresholds(snapshot)
        
        return snapshot
    
    def _get_memory_snapshot(self, label: str = "", metadata: Dict[str, Any] = None) -> MemorySnapshot:
        """Get current memory usage"""
        if HAS_PSUTIL and self._process:
            try:
                mem_info = self._process.memory_info()
                rss_mb = mem_info.rss / (1024 * 1024)
                vms_mb = mem_info.vms / (1024 * 1024)
                percent = self._process.memory_percent()
            except Exception:
                # Fallback to tracemalloc
                rss_mb, vms_mb, percent = self._get_tracemalloc_snapshot()
        else:
            rss_mb, vms_mb, percent = self._get_tracemalloc_snapshot()
        
        return MemorySnapshot(
            timestamp=time.time(),
            rss_mb=rss_mb,
            vms_mb=vms_mb,
            percent=percent,
            label=label,
            metadata=metadata or {}
        )
    
    def _get_tracemalloc_snapshot(self) -> tuple:
        """Get memory info from tracemalloc"""
        try:
            current, peak = tracemalloc.get_traced_memory()
            rss_mb = current / (1024 * 1024)
            vms_mb = peak / (1024 * 1024)
            percent = 0.0  # tracemalloc doesn't provide percentage
            return rss_mb, vms_mb, percent
        except Exception:
            return 0.0, 0.0, 0.0
    
    def _check_thresholds(self, snapshot: MemorySnapshot):
        """Check if memory thresholds are exceeded"""
        if snapshot.rss_mb >= self._critical_threshold:
            alert = MemoryAlert(
                timestamp=snapshot.timestamp,
                current_mb=snapshot.rss_mb,
                threshold_mb=self._critical_threshold,
                percent=snapshot.percent,
                message=f"Critical memory threshold exceeded: {snapshot.rss_mb:.1f}MB >= {self._critical_threshold}MB"
            )
            self._alerts.append(alert)
            self._trigger_alert('critical_memory', alert)
        
        elif snapshot.rss_mb >= self._warning_threshold:
            alert = MemoryAlert(
                timestamp=snapshot.timestamp,
                current_mb=snapshot.rss_mb,
                threshold_mb=self._warning_threshold,
                percent=snapshot.percent,
                message=f"Warning: Memory threshold exceeded: {snapshot.rss_mb:.1f}MB >= {self._warning_threshold}MB"
            )
            self._alerts.append(alert)
            self._trigger_alert('warning_memory', alert)
        
        # Trim old alerts
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]
    
    def get_current_usage(self) -> Dict:
        """Get current memory usage"""
        snapshot = self._get_memory_snapshot()
        return {
            'rss_mb': round(snapshot.rss_mb, 2),
            'vms_mb': round(snapshot.vms_mb, 2),
            'percent': round(snapshot.percent, 2),
            'timestamp': datetime.fromtimestamp(snapshot.timestamp).isoformat()
        }
    
    def get_memory_history(self, limit: int = 100) -> List[Dict]:
        """Get memory usage history"""
        with self._lock:
            snapshots = self._snapshots[-limit:]
            return [
                {
                    'timestamp': datetime.fromtimestamp(s.timestamp).isoformat(),
                    'rss_mb': round(s.rss_mb, 2),
                    'vms_mb': round(s.vms_mb, 2),
                    'percent': round(s.percent, 2),
                    'label': s.label,
                    'metadata': s.metadata
                }
                for s in snapshots
            ]
    
    def get_memory_growth(self) -> Dict:
        """Analyze memory growth since baseline"""
        with self._lock:
            if self._baseline is None or not self._snapshots:
                return {'growth_mb': 0, 'growth_percent': 0}
            
            current = self._snapshots[-1]
            growth_mb = current.rss_mb - self._baseline.rss_mb
            growth_percent = (growth_mb / self._baseline.rss_mb * 100) if self._baseline.rss_mb > 0 else 0
            
            return {
                'baseline_mb': round(self._baseline.rss_mb, 2),
                'current_mb': round(current.rss_mb, 2),
                'growth_mb': round(growth_mb, 2),
                'growth_percent': round(growth_percent, 2),
                'duration_seconds': round(current.timestamp - self._baseline.timestamp, 2)
            }
    
    def get_peak_usage(self) -> Dict:
        """Get peak memory usage"""
        with self._lock:
            if not self._snapshots:
                return {'peak_mb': 0, 'timestamp': None}
            
            peak = max(self._snapshots, key=lambda s: s.rss_mb)
            return {
                'peak_mb': round(peak.rss_mb, 2),
                'timestamp': datetime.fromtimestamp(peak.timestamp).isoformat(),
                'label': peak.label
            }
    
    def get_alerts(self, limit: int = 50) -> List[Dict]:
        """Get memory alerts"""
        with self._lock:
            alerts = self._alerts[-limit:]
            return [
                {
                    'timestamp': datetime.fromtimestamp(a.timestamp).isoformat(),
                    'current_mb': round(a.current_mb, 2),
                    'threshold_mb': round(a.threshold_mb, 2),
                    'percent': round(a.percent, 2),
                    'message': a.message
                }
                for a in alerts
            ]
    
    def get_top_memory_consumers(self, limit: int = 10) -> List[Dict]:
        """Get top memory consumers using tracemalloc"""
        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            
            consumers = []
            for stat in top_stats[:limit]:
                consumers.append({
                    'file': str(stat.traceback),
                    'size_mb': round(stat.size / (1024 * 1024), 2),
                    'count': stat.count
                })
            
            return consumers
        except Exception:
            return []
    
    def add_alert_callback(self, callback: Callable):
        """Add a callback for memory alerts"""
        self._alert_callbacks.append(callback)
    
    def reset_baseline(self):
        """Reset the baseline to current memory usage"""
        with self._lock:
            self._baseline = self._get_memory_snapshot("baseline_reset")
    
    def clear_history(self):
        """Clear memory history"""
        with self._lock:
            self._snapshots.clear()
            self._alerts.clear()
            self._baseline = None
    
    def _trigger_alert(self, alert_type: str, alert: MemoryAlert):
        """Trigger an alert to all callbacks"""
        for callback in self._alert_callbacks:
            try:
                callback(alert_type, {
                    'timestamp': alert.timestamp,
                    'current_mb': alert.current_mb,
                    'threshold_mb': alert.threshold_mb,
                    'percent': alert.percent,
                    'message': alert.message
                })
            except Exception:
                pass
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        current = self.get_current_usage()
        peak = self.get_peak_usage()
        growth = self.get_memory_growth()
        
        lines = [
            '# HELP memory_rss_mb Current RSS memory in MB',
            '# TYPE memory_rss_mb gauge',
            f'memory_rss_mb {current["rss_mb"]}',
            
            '# HELP memory_vms_mb Current VMS memory in MB',
            '# TYPE memory_vms_mb gauge',
            f'memory_vms_mb {current["vms_mb"]}',
            
            '# HELP memory_percent Memory usage percentage',
            '# TYPE memory_percent gauge',
            f'memory_percent {current["percent"]}',
            
            '# HELP memory_peak_mb Peak memory usage in MB',
            '# TYPE memory_peak_mb gauge',
            f'memory_peak_mb {peak["peak_mb"]}',
            
            '# HELP memory_growth_mb Memory growth since baseline in MB',
            '# TYPE memory_growth_mb gauge',
            f'memory_growth_mb {growth["growth_mb"]}'
        ]
        
        return '\n'.join(lines)


# Global instance
memory_monitor = MemoryMonitor()


def track_memory_usage(label: str = "", metadata: Dict[str, Any] = None) -> MemorySnapshot:
    """
    Take a memory snapshot using the global monitor.
    
    Usage:
        snapshot = track_memory_usage("after_conversion", {"file": "mod.jar"})
    """
    return memory_monitor.take_snapshot(label, metadata)


def get_memory_report() -> Dict:
    """Get a comprehensive memory report"""
    return {
        'current_usage': memory_monitor.get_current_usage(),
        'peak_usage': memory_monitor.get_peak_usage(),
        'memory_growth': memory_monitor.get_memory_growth(),
        'memory_history': memory_monitor.get_memory_history(limit=50),
        'alerts': memory_monitor.get_alerts(limit=20),
        'top_consumers': memory_monitor.get_top_memory_consumers()
    }


class MemoryTracker:
    """Context manager for tracking memory usage of a code block"""
    
    def __init__(self, label: str = "", metadata: Dict[str, Any] = None):
        self.label = label
        self.metadata = metadata or {}
        self.start_snapshot = None
        self.end_snapshot = None
    
    def __enter__(self):
        self.start_snapshot = memory_monitor.take_snapshot(
            f"{self.label}_start",
            self.metadata
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_snapshot = memory_monitor.take_snapshot(
            f"{self.label}_end",
            self.metadata
        )
        return False
    
    @property
    def memory_delta(self) -> float:
        """Get memory change in MB"""
        if self.start_snapshot and self.end_snapshot:
            return self.end_snapshot.rss_mb - self.start_snapshot.rss_mb
        return 0.0