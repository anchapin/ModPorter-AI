"""
Build Performance API Router

API endpoints for build performance tracking.
Provides endpoints for starting, updating, and retrieving build performance metrics.

Issue: #691 - Build performance tracking
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

from models import (
    BuildPerformanceStartRequest,
    BuildPerformanceStartResponse,
    BuildStageUpdateRequest,
    BuildPerformanceEndRequest,
    BuildPerformanceResponse,
    BuildPerformanceSummary,
    BuildPerformanceStats,
    BuildPerformanceSnapshot,
)
from services.build_performance_service import (
    get_build_performance_service,
    BuildStages,
    start_build_performance_tracking,
    end_build_performance_tracking,
    get_build_performance,
    get_build_performance_snapshot,
    get_build_performance_stats,
)

router = APIRouter()


@router.post("/start", response_model=BuildPerformanceStartResponse, status_code=201)
async def start_performance_tracking(request: BuildPerformanceStartRequest):
    """
    Start tracking performance for a new build.

    This endpoint initializes performance tracking for a conversion build.
    Returns a build_id that should be used for subsequent API calls.
    """
    try:
        build = start_build_performance_tracking(
            conversion_id=request.conversion_id,
            build_type=request.build_type,
            target_version=request.target_version,
            mod_size_bytes=request.mod_size_bytes,
        )

        return BuildPerformanceStartResponse(
            build_id=build.build_id,
            conversion_id=build.conversion_id,
            message=f"Performance tracking started for build {build.build_id}",
            started_at=build.created_at,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to start tracking")


@router.post("/{build_id}/stage", response_model=BuildPerformanceResponse)
async def update_stage(build_id: str, request: BuildStageUpdateRequest):
    """
    Update a build stage status.

    Use this to mark a stage as running, completed, or failed.
    """
    service = get_build_performance_service()
    build = service.update_stage(
        build_id=build_id,
        stage_name=request.stage_name,
        status=request.status,
        error_message=request.error_message,
        metadata=request.metadata,
    )

    if not build:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    response = service.get_response(build_id)
    return response


@router.post("/{build_id}/stage/{stage_name}/start", response_model=BuildPerformanceResponse)
async def start_stage(build_id: str, stage_name: str):
    """
    Mark a build stage as started.
    """
    service = get_build_performance_service()
    build = service.start_stage(build_id=build_id, stage_name=stage_name)

    if not build:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    response = service.get_response(build_id)
    return response


@router.post("/{build_id}/stage/{stage_name}/complete", response_model=BuildPerformanceResponse)
async def complete_stage(
    build_id: str,
    stage_name: str,
    status: str = "completed",
    error_message: Optional[str] = None,
):
    """
    Mark a build stage as completed (or failed).
    """
    service = get_build_performance_service()
    build = service.complete_stage(
        build_id=build_id,
        stage_name=stage_name,
        status=status,
        error_message=error_message,
    )

    if not build:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    response = service.get_response(build_id)
    return response


@router.post("/{build_id}/end", response_model=BuildPerformanceResponse)
async def end_performance_tracking(build_id: str, request: BuildPerformanceEndRequest):
    """
    End tracking for a build.

    This should be called when the build completes (success or failure).
    """
    service = get_build_performance_service()
    build = end_build_performance_tracking(
        build_id=build_id,
        status=request.status,
        error_message=request.error_message,
        performance_score=request.performance_score,
    )

    if not build:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    response = service.get_response(build_id)
    return response


@router.get("/{build_id}", response_model=BuildPerformanceResponse)
async def get_build_performance_endpoint(build_id: str):
    """
    Get complete performance data for a build.
    """
    response = get_build_performance(build_id)

    if not response:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    return response


@router.get("/{build_id}/snapshot", response_model=BuildPerformanceSnapshot)
async def get_build_snapshot(build_id: str):
    """
    Get a snapshot of current build performance.

    This provides real-time performance data including:
    - Current stage
    - Progress percentage
    - Elapsed time
    - Estimated remaining time
    - Current resource usage
    """
    snapshot = get_build_performance_snapshot(build_id)

    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found or completed")

    return snapshot


@router.get("/{build_id}/summary", response_model=BuildPerformanceSummary)
async def get_build_summary(build_id: str):
    """
    Get a summary of build performance.

    This provides a quick overview including:
    - Total duration
    - Stage count
    - Failed stages
    - Performance score
    """
    service = get_build_performance_service()
    summary = service.get_summary(build_id)

    if not summary:
        raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

    return summary


@router.get("/stats", response_model=BuildPerformanceStats)
async def get_performance_stats(
    conversion_id: Optional[str] = None,
    limit: int = 100,
):
    """
    Get aggregate performance statistics.

    Provides overall performance metrics including:
    - Total/completed/failed build counts
    - Average, median, P95, P99 duration
    - Average performance score
    - Stage-specific statistics
    """
    return get_build_performance_stats(conversion_id=conversion_id, limit=limit)


@router.get("/stages", response_model=List[str])
async def get_available_stages():
    """
    Get list of available build stage names.

    These are the standardized stage names that can be used when tracking builds.
    """
    return [
        BuildStages.INITIALIZATION,
        BuildStages.FILE_TRANSFER,
        BuildStages.JAVA_ANALYSIS,
        BuildStages.BEDROCK_ARCHITECT,
        BuildStages.LOGIC_TRANSLATION,
        BuildStages.ASSET_CONVERSION,
        BuildStages.PACKAGING,
        BuildStages.QA_VALIDATION,
        BuildStages.FINALIZATION,
    ]


@router.get("/", response_model=List[BuildPerformanceSummary])
async def list_builds(
    conversion_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """
    List all builds with optional filtering.
    """
    service = get_build_performance_service()
    service.get_stats(conversion_id=conversion_id, limit=limit)

    # Note: This is a simplified implementation
    # Full implementation would need persistent storage
    return []
