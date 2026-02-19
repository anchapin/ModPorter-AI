"""
Resource limiting for file processing operations.

This module provides resource management and limiting capabilities
to prevent resource exhaustion attacks.

Issue: #576 - Backend: File Processing Security
"""

import asyncio
import logging
import os
import resource
import shutil
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Generator

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Configuration for resource limits."""
    # Memory limits (in MB)
    max_memory_mb: int = 512
    
    # Disk limits (in MB)
    max_disk_usage_mb: int = 1024  # 1GB max disk usage per job
    
    # Processing time limits (in seconds)
    max_processing_time_seconds: int = 300  # 5 minutes
    
    # Concurrent operation limits
    max_concurrent_uploads: int = 10
    max_concurrent_extractions: int = 5
    
    # File handle limits
    max_open_files: int = 100
    
    # CPU time limits (in seconds)
    max_cpu_time_seconds: int = 60


@dataclass
class ResourceUsage:
    """Current resource usage metrics."""
    memory_mb: float = 0.0
    disk_mb: float = 0.0
    open_files: int = 0
    cpu_time_seconds: float = 0.0
    processing_time_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "memory_mb": self.memory_mb,
            "disk_mb": self.disk_mb,
            "open_files": self.open_files,
            "cpu_time_seconds": self.cpu_time_seconds,
            "processing_time_seconds": self.processing_time_seconds,
            "timestamp": self.timestamp.isoformat()
        }


class ResourceLimitExceeded(Exception):
    """Raised when a resource limit is exceeded."""
    def __init__(self, resource_type: str, current: float, limit: float):
        self.resource_type = resource_type
        self.current = current
        self.limit = limit
        super().__init__(
            f"Resource limit exceeded for {resource_type}: "
            f"{current:.2f} > {limit:.2f}"
        )


class ResourceLimiter:
    """
    Resource limiter for managing and enforcing resource constraints.
    
    This class provides:
    - Memory usage tracking and limiting
    - Disk usage monitoring
    - Processing time limits
    - Concurrent operation management
    """
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        """Initialize with optional custom limits."""
        self.limits = limits or ResourceLimits()
        self._start_time: Optional[datetime] = None
        self._disk_usage_path: Optional[Path] = None
        self._lock = threading.Lock()
        self._active_operations: Dict[str, int] = {
            "uploads": 0,
            "extractions": 0,
        }
    
    def start_tracking(self, disk_path: Optional[Path] = None) -> None:
        """
        Start resource tracking for an operation.
        
        Args:
            disk_path: Path to track disk usage for
        """
        self._start_time = datetime.utcnow()
        self._disk_usage_path = disk_path
        logger.debug(f"Started resource tracking at {self._start_time}")
    
    def stop_tracking(self) -> ResourceUsage:
        """
        Stop tracking and return final resource usage.
        
        Returns:
            Final ResourceUsage metrics
        """
        usage = self.get_current_usage()
        self._start_time = None
        self._disk_usage_path = None
        logger.debug(f"Stopped resource tracking: {usage}")
        return usage
    
    def get_current_usage(self) -> ResourceUsage:
        """
        Get current resource usage metrics.
        
        Returns:
            Current ResourceUsage metrics
        """
        usage = ResourceUsage()
        
        # Memory usage
        try:
            usage.memory_mb = self._get_memory_usage_mb()
        except Exception as e:
            logger.debug(f"Could not get memory usage: {e}")
        
        # Disk usage
        if self._disk_usage_path:
            try:
                usage.disk_mb = self._get_directory_size_mb(self._disk_usage_path)
            except Exception as e:
                logger.debug(f"Could not get disk usage: {e}")
        
        # Open files
        try:
            usage.open_files = self._get_open_file_count()
        except Exception as e:
            logger.debug(f"Could not get open file count: {e}")
        
        # Processing time
        if self._start_time:
            elapsed = (datetime.utcnow() - self._start_time).total_seconds()
            usage.processing_time_seconds = elapsed
        
        # CPU time
        try:
            usage.cpu_time_seconds = self._get_cpu_time()
        except Exception as e:
            logger.debug(f"Could not get CPU time: {e}")
        
        return usage
    
    def check_limits(self) -> None:
        """
        Check if any resource limits are exceeded.
        
        Raises:
            ResourceLimitExceeded: If any limit is exceeded
        """
        usage = self.get_current_usage()
        
        # Check memory limit
        if usage.memory_mb > self.limits.max_memory_mb:
            raise ResourceLimitExceeded(
                "memory", usage.memory_mb, self.limits.max_memory_mb
            )
        
        # Check disk limit
        if usage.disk_mb > self.limits.max_disk_usage_mb:
            raise ResourceLimitExceeded(
                "disk", usage.disk_mb, self.limits.max_disk_usage_mb
            )
        
        # Check processing time limit
        if usage.processing_time_seconds > self.limits.max_processing_time_seconds:
            raise ResourceLimitExceeded(
                "processing_time",
                usage.processing_time_seconds,
                self.limits.max_processing_time_seconds
            )
        
        # Check open files limit
        if usage.open_files > self.limits.max_open_files:
            raise ResourceLimitExceeded(
                "open_files", usage.open_files, self.limits.max_open_files
            )
    
    def check_available_disk_space(self, path: Path, required_mb: int) -> bool:
        """
        Check if there's enough disk space available.
        
        Args:
            path: Path to check
            required_mb: Required space in MB
            
        Returns:
            True if enough space is available
        """
        try:
            stat = shutil.disk_usage(path)
            available_mb = stat.free / (1024 * 1024)
            return available_mb >= required_mb
        except Exception as e:
            logger.error(f"Error checking disk space: {e}")
            return False
    
    @contextmanager
    def track_operation(self, operation_type: str) -> Generator[None, None, None]:
        """
        Context manager to track an operation with resource limits.
        
        Args:
            operation_type: Type of operation (e.g., 'upload', 'extraction')
            
        Yields:
            None
            
        Raises:
            ResourceLimitExceeded: If limits are exceeded
        """
        with self._lock:
            # Check concurrent operation limits
            if operation_type == "upload":
                if self._active_operations["uploads"] >= self.limits.max_concurrent_uploads:
                    raise ResourceLimitExceeded(
                        "concurrent_uploads",
                        self._active_operations["uploads"],
                        self.limits.max_concurrent_uploads
                    )
                self._active_operations["uploads"] += 1
            elif operation_type == "extraction":
                if self._active_operations["extractions"] >= self.limits.max_concurrent_extractions:
                    raise ResourceLimitExceeded(
                        "concurrent_extractions",
                        self._active_operations["extractions"],
                        self.limits.max_concurrent_extractions
                    )
                self._active_operations["extractions"] += 1
        
        try:
            self.start_tracking()
            yield
            self.check_limits()
        finally:
            self.stop_tracking()
            with self._lock:
                if operation_type == "upload":
                    self._active_operations["uploads"] -= 1
                elif operation_type == "extraction":
                    self._active_operations["extractions"] -= 1
    
    @contextmanager
    def time_limit(self, seconds: Optional[int] = None) -> Generator[None, None, None]:
        """
        Context manager with a time limit.
        
        Args:
            seconds: Time limit in seconds (uses config if not specified)
            
        Yields:
            None
            
        Raises:
            ResourceLimitExceeded: If time limit is exceeded
        """
        limit = seconds or self.limits.max_processing_time_seconds
        
        def timeout_handler(signum, frame):
            raise ResourceLimitExceeded("time", limit, limit)
        
        # Set up signal-based timeout (Unix only)
        try:
            import signal
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(limit)
            try:
                yield
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        except (ImportError, ValueError):
            # Fallback for Windows or threads
            start_time = datetime.utcnow()
            yield
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > limit:
                raise ResourceLimitExceeded("time", elapsed, limit)
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            # Fallback using resource module (Unix only)
            try:
                usage = resource.getrusage(resource.RUSAGE_SELF)
                return usage.ru_maxrss / 1024  # Convert KB to MB
            except (AttributeError, OSError):
                return 0.0
    
    def _get_directory_size_mb(self, path: Path) -> float:
        """Get total size of a directory in MB."""
        if not path.exists():
            return 0.0
        
        total_size = 0
        try:
            for entry in path.rglob('*'):
                if entry.is_file():
                    total_size += entry.stat().st_size
        except Exception as e:
            logger.debug(f"Error calculating directory size: {e}")
        
        return total_size / (1024 * 1024)
    
    def _get_open_file_count(self) -> int:
        """Get count of open file descriptors."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return len(process.open_files())
        except ImportError:
            # Fallback using /proc (Linux only)
            try:
                return len(os.listdir(f'/proc/self/fd'))
            except (FileNotFoundError, PermissionError):
                return 0
    
    def _get_cpu_time(self) -> float:
        """Get CPU time used by the process."""
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return usage.ru_utime + usage.ru_stime
        except (AttributeError, OSError):
            return 0.0


class DiskSpaceMonitor:
    """
    Monitor for disk space usage with alerts.
    """
    
    def __init__(
        self,
        warning_threshold_mb: int = 500,
        critical_threshold_mb: int = 100
    ):
        """Initialize with thresholds."""
        self.warning_threshold_mb = warning_threshold_mb
        self.critical_threshold_mb = critical_threshold_mb
    
    def check_disk_space(self, path: Path) -> Dict[str, Any]:
        """
        Check disk space and return status.
        
        Args:
            path: Path to check
            
        Returns:
            Dictionary with disk space status
        """
        try:
            stat = shutil.disk_usage(path)
            total_mb = stat.total / (1024 * 1024)
            used_mb = stat.used / (1024 * 1024)
            free_mb = stat.free / (1024 * 1024)
            percent_used = (stat.used / stat.total) * 100
            
            status = "ok"
            if free_mb < self.critical_threshold_mb:
                status = "critical"
            elif free_mb < self.warning_threshold_mb:
                status = "warning"
            
            return {
                "status": status,
                "total_mb": total_mb,
                "used_mb": used_mb,
                "free_mb": free_mb,
                "percent_used": percent_used,
                "warning_threshold_mb": self.warning_threshold_mb,
                "critical_threshold_mb": self.critical_threshold_mb
            }
        except Exception as e:
            logger.error(f"Error checking disk space: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Global resource limiter instance
_resource_limiter: Optional[ResourceLimiter] = None


def get_resource_limiter() -> ResourceLimiter:
    """Get or create the global resource limiter instance."""
    global _resource_limiter
    if _resource_limiter is None:
        _resource_limiter = ResourceLimiter()
    return _resource_limiter