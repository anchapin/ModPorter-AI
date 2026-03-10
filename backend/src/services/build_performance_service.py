"""
Build Performance Service

Service for tracking and collecting build performance metrics during mod conversion.
Provides detailed timing information for various build stages, resource usage tracking,
and performance analysis.

Issue: #691 - Build performance tracking
"""

import logging
import time
import psutil
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from contextlib import contextmanager
from collections import defaultdict

from models import (
    BuildStageTiming,
    BuildResourceUsage,
    BuildPerformanceMetrics,
    BuildPerformanceSnapshot,
    BuildPerformanceStartRequest,
    BuildPerformanceEndRequest,
    BuildPerformanceResponse,
    BuildPerformanceSummary,
    BuildPerformanceStats,
)
from services.cache import CacheService

# Import metrics for recording
try:
    from services import metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Cache keys
BUILD_PERFORMANCE_KEY_PREFIX = "build_performance:"
BUILD_PERFORMANCE_LIST_KEY = "build_performance:list"

# Build stage names (standardized)
class BuildStages:
    """Standard build stage names."""
    INITIALIZATION = "initialization"
    FILE_TRANSFER = "file_transfer"
    JAVA_ANALYSIS = "java_analysis"
    BEDROCK_ARCHITECT = "bedrock_architect"
    LOGIC_TRANSLATION = "logic_translation"
    ASSET_CONVERSION = "asset_conversion"
    PACKAGING = "packaging"
    QA_VALIDATION = "qa_validation"
    FINALIZATION = "finalization"


class BuildPerformanceService:
    """
    Service for tracking build performance metrics.
    
    This service provides:
    - Stage-by-stage timing tracking
    - Resource usage monitoring
    - Performance snapshots
    - Aggregate statistics
    """
    
    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache = cache_service or CacheService()
        self._active_builds: Dict[str, BuildPerformanceMetrics] = {}
        self._lock = threading.Lock()
    
    def start_tracking(self, request: BuildPerformanceStartRequest) -> BuildPerformanceMetrics:
        """
        Start tracking performance for a new build.
        
        Args:
            request: Build performance start request
            
        Returns:
            BuildPerformanceMetrics object
        """
        build = BuildPerformanceMetrics(
            conversion_id=request.conversion_id,
            build_type=request.build_type,
            target_version=request.target_version,
            mod_size_bytes=request.mod_size_bytes,
            status="running",
        )
        
        # Store in active builds
        with self._lock:
            self._active_builds[build.build_id] = build
        
        # Initialize with first stage
        stage = BuildStageTiming(
            stage_name=BuildStages.INITIALIZATION,
            start_time=datetime.now(timezone.utc),
            status="running",
        )
        build.stages.append(stage)
        
        # Record metrics
        if METRICS_AVAILABLE:
            try:
                metrics.update_active_builds(len(self._active_builds))
            except Exception as e:
                logger.warning(f"Failed to update metrics: {e}")
        
        logger.info(f"Started performance tracking for build {build.build_id}, conversion {request.conversion_id}")
        
        return build
    
    def update_stage(
        self,
        build_id: str,
        stage_name: str,
        status: str = "running",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[BuildPerformanceMetrics]:
        """
        Update the status of a build stage.
        
        Args:
            build_id: The build ID
            stage_name: Name of the stage
            status: New status (running, completed, failed)
            error_message: Error message if failed
            metadata: Additional metadata
            
        Returns:
            Updated BuildPerformanceMetrics or None if not found
        """
        with self._lock:
            build = self._active_builds.get(build_id)
            if not build:
                return None
            
            # Find existing stage or create new one
            stage = None
            for s in build.stages:
                if s.stage_name == stage_name:
                    stage = s
                    break
            
            if stage:
                # Update existing stage
                stage.status = status
                stage.error_message = error_message
                if metadata:
                    stage.metadata.update(metadata)
                
                if status in ("completed", "failed"):
                    stage.complete(status=status, error_message=error_message)
            else:
                # Create new stage
                stage = BuildStageTiming(
                    stage_name=stage_name,
                    start_time=datetime.now(timezone.utc),
                    status=status,
                    error_message=error_message,
                    metadata=metadata or {},
                )
                
                if status in ("completed", "failed"):
                    stage.complete(status=status, error_message=error_message)
                
                build.stages.append(stage)
            
            return build
    
    def start_stage(self, build_id: str, stage_name: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[BuildPerformanceMetrics]:
        """
        Start a new build stage.
        
        Args:
            build_id: The build ID
            stage_name: Name of the stage to start
            metadata: Optional metadata
            
        Returns:
            Updated BuildPerformanceMetrics or None
        """
        return self.update_stage(build_id, stage_name, status="running", metadata=metadata)
    
    def complete_stage(
        self,
        build_id: str,
        stage_name: str,
        status: str = "completed",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[BuildPerformanceMetrics]:
        """
        Mark a build stage as complete.
        
        Args:
            build_id: The build ID
            stage_name: Name of the stage to complete
            status: Completion status (completed, failed)
            error_message: Error message if failed
            metadata: Optional metadata
            
        Returns:
            Updated BuildPerformanceMetrics or None
        """
        return self.update_stage(build_id, stage_name, status=status, error_message=error_message, metadata=metadata)
    
    def end_tracking(
        self,
        build_id: str,
        request: BuildPerformanceEndRequest,
    ) -> Optional[BuildPerformanceMetrics]:
        """
        End tracking for a build.
        
        Args:
            build_id: The build ID
            request: End tracking request with final status
            
        Returns:
            Final BuildPerformanceMetrics or None
        """
        with self._lock:
            build = self._active_builds.get(build_id)
            if not build:
                return None
            
            # Complete the last running stage if any
            for stage in build.stages:
                if stage.status == "running":
                    stage.complete(status=request.status)
            
            # Set final status
            build.status = request.status
            build.error_message = request.error_message
            build.completed_at = datetime.now(timezone.utc)
            
            # Calculate total duration
            if build.stages:
                first_stage = build.stages[0]
                last_stage = build.stages[-1]
                if first_stage.start_time and last_stage.end_time:
                    build.total_duration_ms = (last_stage.end_time - first_stage.start_time).total_seconds() * 1000
            
            # Set performance score
            if request.performance_score is not None:
                build.performance_score = request.performance_score
            else:
                # Calculate default performance score based on duration
                build.performance_score = self._calculate_performance_score(build)
            
            # Calculate build efficiency
            build.build_efficiency = self._calculate_build_efficiency(build)
            
            # Final resource snapshot
            try:
                build.resource_usage = self._capture_resource_usage()
            except Exception as e:
                logger.warning(f"Failed to capture resource usage: {e}")
            
            # Remove from active builds
            del self._active_builds[build_id]
            
            # Record metrics
            if METRICS_AVAILABLE:
                try:
                    duration_seconds = build.total_duration_ms / 1000 if build.total_duration_ms else None
                    metrics.record_build_performance(
                        status=request.status,
                        build_type=build.build_type,
                        duration=duration_seconds,
                        target_version=build.target_version,
                        performance_score=build.performance_score,
                    )
                    metrics.update_active_builds(len(self._active_builds))
                except Exception as e:
                    logger.warning(f"Failed to record metrics: {e}")
            
            logger.info(f"Ended performance tracking for build {build_id}, status: {request.status}, duration: {build.total_duration_ms}ms")
            
            return build
    
    def get_build(self, build_id: str) -> Optional[BuildPerformanceMetrics]:
        """
        Get a build by ID.
        
        Args:
            build_id: The build ID
            
        Returns:
            BuildPerformanceMetrics or None
        """
        with self._lock:
            return self._active_builds.get(build_id)
    
    def get_snapshot(self, build_id: str) -> Optional[BuildPerformanceSnapshot]:
        """
        Get a snapshot of current build performance.
        
        Args:
            build_id: The build ID
            
        Returns:
            BuildPerformanceSnapshot or None
        """
        build = self.get_build(build_id)
        if not build:
            return None
        
        # Find current stage
        current_stage = None
        for stage in build.stages:
            if stage.status == "running":
                current_stage = stage
                break
        
        # Calculate elapsed time
        elapsed_ms = 0.0
        if build.stages and build.stages[0].start_time:
            elapsed_ms = (datetime.now(timezone.utc) - build.stages[0].start_time).total_seconds() * 1000
        
        # Calculate progress
        progress_percent = self._calculate_progress(build)
        
        # Estimate remaining time
        estimated_remaining = None
        if progress_percent > 0:
            estimated_remaining = (elapsed_ms / progress_percent * 100) - elapsed_ms
        
        # Capture resource usage
        resource_usage = None
        try:
            resource_usage = self._capture_resource_usage()
        except Exception:
            pass
        
        return BuildPerformanceSnapshot(
            build_id=build_id,
            conversion_id=build.conversion_id,
            current_stage=current_stage.stage_name if current_stage else None,
            progress_percent=progress_percent,
            elapsed_ms=elapsed_ms,
            estimated_remaining_ms=estimated_remaining,
            resource_usage=resource_usage,
        )
    
    def get_response(self, build_id: str) -> Optional[BuildPerformanceResponse]:
        """
        Get build performance as API response.
        
        Args:
            build_id: The build ID
            
        Returns:
            BuildPerformanceResponse or None
        """
        build = self.get_build(build_id)
        if not build:
            # Try to get from cache (for completed builds)
            cached = self._get_from_cache(build_id)
            if cached:
                return self._to_response(cached)
            return None
        
        return self._to_response(build)
    
    def get_summary(self, build_id: str) -> Optional[BuildPerformanceSummary]:
        """
        Get build performance summary.
        
        Args:
            build_id: The build ID
            
        Returns:
            BuildPerformanceSummary or None
        """
        build = self.get_build(build_id)
        if not build:
            cached = self._get_from_cache(build_id)
            if cached:
                build = cached
            else:
                return None
        
        failed_stages = sum(1 for s in build.stages if s.status == "failed")
        
        return BuildPerformanceSummary(
            conversion_id=build.conversion_id,
            build_id=build.build_id,
            total_duration_ms=build.total_duration_ms or 0.0,
            stage_count=len(build.stages),
            failed_stages=failed_stages,
            performance_score=build.performance_score,
            status=build.status,
        )
    
    def get_stats(
        self,
        conversion_id: Optional[str] = None,
        limit: int = 100,
    ) -> BuildPerformanceStats:
        """
        Get aggregate performance statistics.
        
        Args:
            conversion_id: Optional filter by conversion ID
            limit: Maximum number of builds to consider
            
        Returns:
            BuildPerformanceStats
        """
        builds = self._get_all_builds(limit=limit)
        
        if conversion_id:
            builds = [b for b in builds if b.conversion_id == conversion_id]
        
        if not builds:
            return BuildPerformanceStats()
        
        completed_builds = [b for b in builds if b.status == "completed"]
        failed_builds = [b for b in builds if b.status == "failed"]
        
        # Calculate duration stats
        durations = [b.total_duration_ms for b in builds if b.total_duration_ms is not None]
        
        stats = BuildPerformanceStats(
            total_builds=len(builds),
            completed_builds=len(completed_builds),
            failed_builds=len(failed_builds),
            period_start=min(b.created_at for b in builds) if builds else None,
            period_end=max(b.completed_at for b in builds if b.completed_at) if builds else None,
        )
        
        if durations:
            durations_sorted = sorted(durations)
            stats.average_duration_ms = sum(durations) / len(durations)
            stats.median_duration_ms = durations_sorted[len(durations_sorted) // 2]
            stats.p95_duration_ms = durations_sorted[int(len(durations_sorted) * 0.95)]
            stats.p99_duration_ms = durations_sorted[int(len(durations_sorted) * 0.99)]
        
        # Calculate average performance score
        scores = [b.performance_score for b in completed_builds if b.performance_score is not None]
        if scores:
            stats.average_performance_score = sum(scores) / len(scores)
        
        # Calculate stage-specific stats
        stage_durations: Dict[str, List[float]] = defaultdict(list)
        for build in builds:
            for stage in build.stages:
                if stage.duration_ms is not None:
                    stage_durations[stage.stage_name].append(stage.duration_ms)
        
        for stage_name, durations in stage_durations.items():
            if durations:
                stats.stage_stats[stage_name] = {
                    "average_ms": sum(durations) / len(durations),
                    "min_ms": min(durations),
                    "max_ms": max(durations),
                    "count": len(durations),
                }
        
        return stats
    
    def _calculate_performance_score(self, build: BuildPerformanceMetrics) -> float:
        """
        Calculate performance score based on build metrics.
        
        Args:
            build: The build metrics
            
        Returns:
            Performance score 0-100
        """
        if not build.stages:
            return 50.0
        
        # Factor 1: Stage success rate (40%)
        successful_stages = sum(1 for s in build.stages if s.status == "completed")
        total_stages = len(build.stages)
        success_rate = successful_stages / total_stages if total_stages > 0 else 0
        
        # Factor 2: Duration efficiency (30%) - based on expected max duration
        max_expected_duration_ms = 600000  # 10 minutes
        if build.total_duration_ms and build.total_duration_ms < max_expected_duration_ms:
            duration_score = 1 - (build.total_duration_ms / max_expected_duration_ms)
        else:
            duration_score = 0
        
        # Factor 3: Stage completion (30%)
        # More stages = more complete processing
        stage_completion = min(total_stages / 8, 1.0)  # Assume 8 stages is full
        
        score = (success_rate * 40) + (duration_score * 30) + (stage_completion * 30)
        return max(0, min(100, score))
    
    def _calculate_build_efficiency(self, build: BuildPerformanceMetrics) -> float:
        """
        Calculate build efficiency as percentage of time actually spent vs total elapsed.
        
        Args:
            build: The build metrics
            
        Returns:
            Efficiency percentage
        """
        if not build.stages or not build.total_duration_ms:
            return 0.0
        
        # Sum of actual stage durations vs total elapsed
        actual_time = sum(s.duration_ms for s in build.stages if s.duration_ms)
        
        if build.total_duration_ms > 0:
            return (actual_time / build.total_duration_ms) * 100
        return 0.0
    
    def _calculate_progress(self, build: BuildPerformanceMetrics) -> float:
        """Calculate overall build progress percentage."""
        if not build.stages:
            return 0.0
        
        completed = sum(1 for s in build.stages if s.status in ("completed", "failed"))
        total = len(build.stages)
        
        if total == 0:
            return 0.0
        
        # Weight running stage by estimated progress
        progress = (completed / total) * 100
        
        # Check if there's a running stage
        for stage in build.stages:
            if stage.status == "running":
                # Estimate 50% complete for running stage
                progress += 50 / total
                break
        
        return min(100, progress)
    
    def _capture_resource_usage(self) -> BuildResourceUsage:
        """Capture current resource usage."""
        process = psutil.Process()
        
        try:
            cpu_percent = process.cpu_percent(interval=0.1)
        except Exception:
            cpu_percent = None
        
        try:
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            peak_memory_mb = memory_info.rss / (1024 * 1024)  # RSS is current
        except Exception:
            memory_mb = None
            peak_memory_mb = None
        
        return BuildResourceUsage(
            cpu_usage_percent=cpu_percent,
            memory_usage_mb=memory_mb,
            peak_memory_mb=peak_memory_mb,
        )
    
    def _to_response(self, build: BuildPerformanceMetrics) -> BuildPerformanceResponse:
        """Convert BuildPerformanceMetrics to API response."""
        return BuildPerformanceResponse(
            build_id=build.build_id,
            conversion_id=build.conversion_id,
            status=build.status,
            total_duration_ms=build.total_duration_ms,
            performance_score=build.performance_score,
            stages=[
                {
                    "stage_name": s.stage_name,
                    "status": s.status,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "duration_ms": s.duration_ms,
                    "error_message": s.error_message,
                    "metadata": s.metadata,
                }
                for s in build.stages
            ],
            resource_usage=build.resource_usage.model_dump() if build.resource_usage else None,
            metadata=build.metadata,
            created_at=build.created_at,
            completed_at=build.completed_at,
        )
    
    def _get_from_cache(self, build_id: str) -> Optional[BuildPerformanceMetrics]:
        """Get completed build from cache."""
        try:
            import json
            data = self.cache.get(f"{BUILD_PERFORMANCE_KEY_PREFIX}{build_id}")
            if data:
                if isinstance(data, str):
                    data = json.loads(data)
                return BuildPerformanceMetrics(**data)
        except Exception as e:
            logger.warning(f"Failed to get build from cache: {e}")
        return None
    
    def _get_all_builds(self, limit: int = 100) -> List[BuildPerformanceMetrics]:
        """Get all builds (from active and cache)."""
        builds = []
        
        # Get from active builds
        with self._lock:
            builds.extend(list(self._active_builds.values()))
        
        # This would need Redis/memcached for full implementation
        # For now, return active builds
        
        return builds[:limit]
    
    @contextmanager
    def track_stage(self, build_id: str, stage_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for tracking a build stage.
        
        Usage:
            with service.track_stage(build_id, "java_analysis"):
                # do work
                pass
        
        Args:
            build_id: The build ID
            stage_name: Name of the stage
            metadata: Optional metadata
        """
        self.start_stage(build_id, stage_name, metadata)
        try:
            yield
            self.complete_stage(build_id, stage_name, status="completed")
        except Exception as e:
            self.complete_stage(build_id, stage_name, status="failed", error_message=str(e))
            raise


# Global service instance
_build_performance_service: Optional[BuildPerformanceService] = None


def get_build_performance_service() -> BuildPerformanceService:
    """Get or create the global build performance service instance."""
    global _build_performance_service
    if _build_performance_service is None:
        _build_performance_service = BuildPerformanceService()
    return _build_performance_service


# Convenience functions for tracking

def start_build_performance_tracking(
    conversion_id: str,
    build_type: str = "conversion",
    target_version: str = "1.20.0",
    mod_size_bytes: Optional[int] = None,
) -> BuildPerformanceMetrics:
    """Start tracking build performance."""
    service = get_build_performance_service()
    request = BuildPerformanceStartRequest(
        conversion_id=conversion_id,
        build_type=build_type,
        target_version=target_version,
        mod_size_bytes=mod_size_bytes,
    )
    return service.start_tracking(request)


def update_build_stage(
    build_id: str,
    stage_name: str,
    status: str = "running",
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[BuildPerformanceMetrics]:
    """Update a build stage."""
    service = get_build_performance_service()
    return service.update_stage(build_id, stage_name, status, error_message, metadata)


def end_build_performance_tracking(
    build_id: str,
    status: str = "completed",
    error_message: Optional[str] = None,
    performance_score: Optional[float] = None,
) -> Optional[BuildPerformanceMetrics]:
    """End tracking build performance."""
    service = get_build_performance_service()
    request = BuildPerformanceEndRequest(
        status=status,
        error_message=error_message,
        performance_score=performance_score,
    )
    return service.end_tracking(build_id, request)


def get_build_performance(build_id: str) -> Optional[BuildPerformanceResponse]:
    """Get build performance data."""
    service = get_build_performance_service()
    return service.get_response(build_id)


def get_build_performance_snapshot(build_id: str) -> Optional[BuildPerformanceSnapshot]:
    """Get build performance snapshot."""
    service = get_build_performance_service()
    return service.get_snapshot(build_id)


def get_build_performance_stats(
    conversion_id: Optional[str] = None,
    limit: int = 100,
) -> BuildPerformanceStats:
    """Get aggregate performance statistics."""
    service = get_build_performance_service()
    return service.get_stats(conversion_id, limit)
