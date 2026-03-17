"""
Build Performance Models

Data models for tracking build performance metrics during mod conversion.
These models capture detailed timing information for various build stages,
resource usage, and performance bottlenecks.

Issue: #691 - Build performance tracking
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid


class BuildStageTiming(BaseModel):
    """Timing information for a single build stage."""

    stage_name: str = Field(..., description="Name of the build stage")
    start_time: datetime = Field(..., description="When the stage started")
    end_time: Optional[datetime] = Field(None, description="When the stage ended")
    duration_ms: Optional[float] = Field(None, description="Duration in milliseconds")
    status: str = Field(
        default="pending",
        description="Stage status: pending, running, completed, failed",
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional stage metadata"
    )

    def complete(self, status: str = "completed", error_message: Optional[str] = None):
        """Mark the stage as complete."""
        self.end_time = datetime.now(timezone.utc)
        self.status = status
        self.error_message = error_message
        if self.end_time and self.start_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000


class BuildResourceUsage(BaseModel):
    """Resource usage metrics during a build."""

    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    peak_memory_mb: Optional[float] = Field(None, description="Peak memory usage in MB")
    disk_io_read_mb: Optional[float] = Field(None, description="Disk read in MB")
    disk_io_write_mb: Optional[float] = Field(None, description="Disk write in MB")
    network_io_mb: Optional[float] = Field(None, description="Network I/O in MB")


class BuildPerformanceMetrics(BaseModel):
    """Complete performance metrics for a build."""

    build_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique build identifier"
    )
    conversion_id: str = Field(..., description="Associated conversion ID")

    # Timing
    stages: List[BuildStageTiming] = Field(
        default_factory=list, description="Build stage timings"
    )
    total_duration_ms: Optional[float] = Field(
        None, description="Total build duration in milliseconds"
    )

    # Resource usage
    resource_usage: Optional[BuildResourceUsage] = Field(
        None, description="Resource usage metrics"
    )

    # Build details
    build_type: str = Field(
        default="conversion", description="Type of build: conversion, benchmark, test"
    )
    target_version: str = Field(
        default="1.20.0", description="Target Minecraft version"
    )
    mod_size_bytes: Optional[int] = Field(
        None, description="Size of the mod file in bytes"
    )

    # Status
    status: str = Field(
        default="pending",
        description="Build status: pending, running, completed, failed",
    )
    error_message: Optional[str] = Field(
        None, description="Error message if build failed"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(None)

    # Performance scores
    performance_score: Optional[float] = Field(
        None, description="Overall performance score 0-100"
    )
    build_efficiency: Optional[float] = Field(
        None, description="Build efficiency percentage"
    )

    # Additional data
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class BuildPerformanceSnapshot(BaseModel):
    """Snapshot of build performance at a point in time."""

    build_id: str
    conversion_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_stage: Optional[str] = None
    progress_percent: float = 0.0
    elapsed_ms: float = 0.0
    estimated_remaining_ms: Optional[float] = None
    resource_usage: Optional[BuildResourceUsage] = None


# API Request/Response Models


class BuildPerformanceStartRequest(BaseModel):
    """Request to start tracking build performance."""

    conversion_id: str = Field(..., description="Associated conversion ID")
    build_type: str = Field(default="conversion", description="Type of build")
    target_version: str = Field(default="1.20.0")
    mod_size_bytes: Optional[int] = Field(None)


class BuildPerformanceStartResponse(BaseModel):
    """Response when starting performance tracking."""

    build_id: str
    conversion_id: str
    message: str
    started_at: datetime


class BuildStageUpdateRequest(BaseModel):
    """Request to update a build stage."""

    stage_name: str
    status: str = "running"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BuildPerformanceEndRequest(BaseModel):
    """Request to end build performance tracking."""

    status: str = Field(
        default="completed", description="Final status: completed, failed"
    )
    error_message: Optional[str] = None
    performance_score: Optional[float] = None


class BuildPerformanceResponse(BaseModel):
    """Response with build performance data."""

    build_id: str
    conversion_id: str
    status: str
    total_duration_ms: Optional[float]
    performance_score: Optional[float]
    stages: List[Dict[str, Any]]
    resource_usage: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime]


class BuildPerformanceSummary(BaseModel):
    """Summary of build performance for a conversion."""

    conversion_id: str
    build_id: str
    total_duration_ms: float
    stage_count: int
    failed_stages: int
    performance_score: Optional[float]
    status: str


class BuildPerformanceStats(BaseModel):
    """Aggregate performance statistics."""

    total_builds: int = 0
    completed_builds: int = 0
    failed_builds: int = 0
    average_duration_ms: Optional[float] = None
    median_duration_ms: Optional[float] = None
    p95_duration_ms: Optional[float] = None
    p99_duration_ms: Optional[float] = None
    average_performance_score: Optional[float] = None

    # Stage-specific stats
    stage_stats: Dict[str, Dict[str, float]] = Field(default_factory=dict)

    # Time period
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
