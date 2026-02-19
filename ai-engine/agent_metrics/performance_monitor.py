"""
Performance Monitor for tracking operation timing and performance metrics
"""

import time
import functools
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
import json
import os


@dataclass
class OperationMetric:
    """Metric for a single operation"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self, success: bool = True, error: str = None):
        """Mark the operation as complete"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error = error


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for an operation type"""
    operation_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    avg_duration: float = 0.0
    last_called: Optional[float] = None
    
    def add_metric(self, metric: OperationMetric):
        """Add a metric to the aggregation"""
        self.total_calls += 1
        if metric.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        
        if metric.duration is not None:
            self.total_duration += metric.duration
            self.min_duration = min(self.min_duration, metric.duration)
            self.max_duration = max(self.max_duration, metric.duration)
            self.avg_duration = self.total_duration / self.total_calls
        
        self.last_called = metric.end_time or metric.start_time
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'operation_name': self.operation_name,
            'total_calls': self.total_calls,
            'successful_calls': self.successful_calls,
            'failed_calls': self.failed_calls,
            'total_duration': round(self.total_duration, 4),
            'min_duration': round(self.min_duration, 4) if self.min_duration != float('inf') else 0,
            'max_duration': round(self.max_duration, 4),
            'avg_duration': round(self.avg_duration, 4),
            'last_called': datetime.fromtimestamp(self.last_called).isoformat() if self.last_called else None
        }


class PerformanceMonitor:
    """
    Thread-safe performance monitor for tracking operation metrics.
    
    Features:
    - Track operation timing with start/complete pattern
    - Decorator for automatic timing of functions
    - Aggregated metrics per operation type
    - Performance thresholds and alerts
    - Export metrics for dashboards
    """
    
    def __init__(self, slow_operation_threshold: float = 5.0):
        """
        Initialize the performance monitor.
        
        Args:
            slow_operation_threshold: Threshold in seconds for slow operation alerts
        """
        self._lock = threading.Lock()
        self._active_operations: Dict[str, OperationMetric] = {}
        self._completed_operations: List[OperationMetric] = []
        self._aggregated_metrics: Dict[str, AggregatedMetrics] = defaultdict(
            lambda: AggregatedMetrics(operation_name="")
        )
        self._slow_operation_threshold = slow_operation_threshold
        self._alert_callbacks: List[Callable] = []
        self._max_completed_operations = 1000  # Limit memory usage
    
    def start_operation(self, name: str, metadata: Dict[str, Any] = None) -> str:
        """
        Start tracking an operation.
        
        Args:
            name: Name of the operation
            metadata: Optional metadata for the operation
            
        Returns:
            Operation ID for tracking
        """
        op_id = f"{name}_{threading.current_thread().ident}_{time.time()}"
        metric = OperationMetric(
            name=name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        
        with self._lock:
            self._active_operations[op_id] = metric
        
        return op_id
    
    def complete_operation(self, op_id: str, success: bool = True, 
                          error: str = None, metadata: Dict[str, Any] = None) -> Optional[OperationMetric]:
        """
        Complete a tracked operation.
        
        Args:
            op_id: Operation ID returned from start_operation
            success: Whether the operation succeeded
            error: Error message if failed
            metadata: Additional metadata to merge
            
        Returns:
            The completed metric or None if not found
        """
        with self._lock:
            metric = self._active_operations.pop(op_id, None)
            
            if metric is None:
                return None
            
            if metadata:
                metric.metadata.update(metadata)
            
            metric.complete(success=success, error=error)
            
            # Add to completed operations
            self._completed_operations.append(metric)
            
            # Trim old operations if needed
            if len(self._completed_operations) > self._max_completed_operations:
                self._completed_operations = self._completed_operations[-self._max_completed_operations:]
            
            # Update aggregated metrics
            agg_key = metric.name
            self._aggregated_metrics[agg_key].operation_name = metric.name
            self._aggregated_metrics[agg_key].add_metric(metric)
            
            # Check for slow operation
            if metric.duration and metric.duration > self._slow_operation_threshold:
                self._trigger_alert('slow_operation', {
                    'operation': metric.name,
                    'duration': metric.duration,
                    'threshold': self._slow_operation_threshold,
                    'metadata': metric.metadata
                })
        
        return metric
    
    def track_operation(self, name: str, metadata: Dict[str, Any] = None):
        """
        Context manager for tracking an operation.
        
        Usage:
            with monitor.track_operation("analyze_jar", {"file": "mod.jar"}):
                # ... operation code ...
        """
        return _OperationContext(self, name, metadata)
    
    def timed(self, name: str = None, metadata: Dict[str, Any] = None):
        """
        Decorator for timing a function.
        
        Usage:
            @monitor.timed("analyze_mod")
            def analyze_mod(path):
                # ... function code ...
        """
        def decorator(func):
            op_name = name or func.__name__
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                op_id = self.start_operation(op_name, metadata)
                try:
                    result = func(*args, **kwargs)
                    self.complete_operation(op_id, success=True)
                    return result
                except Exception as e:
                    self.complete_operation(op_id, success=False, error=str(e))
                    raise
            
            return wrapper
        return decorator
    
    def add_alert_callback(self, callback: Callable):
        """Add a callback for performance alerts"""
        self._alert_callbacks.append(callback)
    
    def get_metrics(self, operation_name: str = None) -> Dict:
        """
        Get metrics for operations.
        
        Args:
            operation_name: Optional specific operation to get metrics for
            
        Returns:
            Dictionary of metrics
        """
        with self._lock:
            if operation_name:
                if operation_name in self._aggregated_metrics:
                    return self._aggregated_metrics[operation_name].to_dict()
                return {}
            
            return {
                name: agg.to_dict() 
                for name, agg in self._aggregated_metrics.items()
            }
    
    def get_recent_operations(self, limit: int = 100) -> List[Dict]:
        """Get recent completed operations"""
        with self._lock:
            recent = self._completed_operations[-limit:]
            return [
                {
                    'name': op.name,
                    'duration': op.duration,
                    'success': op.success,
                    'error': op.error,
                    'timestamp': datetime.fromtimestamp(op.start_time).isoformat(),
                    'metadata': op.metadata
                }
                for op in recent
            ]
    
    def get_summary(self) -> Dict:
        """Get a summary of all metrics"""
        with self._lock:
            total_operations = sum(agg.total_calls for agg in self._aggregated_metrics.values())
            total_successful = sum(agg.successful_calls for agg in self._aggregated_metrics.values())
            total_failed = sum(agg.failed_calls for agg in self._aggregated_metrics.values())
            
            # Find slowest operations
            slowest = sorted(
                [(name, agg.avg_duration) for name, agg in self._aggregated_metrics.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Find most called operations
            most_called = sorted(
                [(name, agg.total_calls) for name, agg in self._aggregated_metrics.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return {
                'total_operations': total_operations,
                'successful_operations': total_successful,
                'failed_operations': total_failed,
                'success_rate': round(total_successful / total_operations * 100, 2) if total_operations > 0 else 0,
                'active_operations': len(self._active_operations),
                'operation_types': len(self._aggregated_metrics),
                'slowest_operations': [{'name': name, 'avg_duration': duration} for name, duration in slowest],
                'most_called_operations': [{'name': name, 'calls': calls} for name, calls in most_called]
            }
    
    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self._active_operations.clear()
            self._completed_operations.clear()
            self._aggregated_metrics.clear()
    
    def _trigger_alert(self, alert_type: str, data: Dict):
        """Trigger an alert to all callbacks"""
        for callback in self._alert_callbacks:
            try:
                callback(alert_type, data)
            except Exception as e:
                # Don't let alert callback errors affect operation
                pass
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        with self._lock:
            for name, agg in self._aggregated_metrics.items():
                safe_name = name.replace('-', '_').replace(' ', '_')
                lines.append(f'# HELP {safe_name}_total Total calls')
                lines.append(f'# TYPE {safe_name}_total counter')
                lines.append(f'{safe_name}_total {agg.total_calls}')
                
                lines.append(f'# HELP {safe_name}_duration_seconds Average duration')
                lines.append(f'# TYPE {safe_name}_duration_seconds gauge')
                lines.append(f'{safe_name}_duration_seconds {agg.avg_duration}')
                
                lines.append(f'# HELP {safe_name}_errors_total Total errors')
                lines.append(f'# TYPE {safe_name}_errors_total counter')
                lines.append(f'{safe_name}_errors_total {agg.failed_calls}')
        
        return '\n'.join(lines)


class _OperationContext:
    """Context manager for tracking operations"""
    
    def __init__(self, monitor: PerformanceMonitor, name: str, metadata: Dict[str, Any] = None):
        self.monitor = monitor
        self.name = name
        self.metadata = metadata
        self.op_id = None
    
    def __enter__(self):
        self.op_id = self.monitor.start_operation(self.name, self.metadata)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.monitor.complete_operation(
                self.op_id, 
                success=False, 
                error=str(exc_val)
            )
        else:
            self.monitor.complete_operation(self.op_id, success=True)
        return False


# Global instance
performance_tracker = PerformanceMonitor()


def timed_operation(name: str = None, metadata: Dict[str, Any] = None):
    """
    Decorator for timing operations using the global performance tracker.
    
    Usage:
        @timed_operation("analyze_jar")
        def analyze_jar(path):
            # ... code ...
    """
    return performance_tracker.timed(name, metadata)


def get_performance_report() -> Dict:
    """Get a comprehensive performance report"""
    return {
        'summary': performance_tracker.get_summary(),
        'metrics': performance_tracker.get_metrics(),
        'recent_operations': performance_tracker.get_recent_operations(limit=50)
    }


def reset_metrics():
    """Reset all performance metrics"""
    performance_tracker.reset()