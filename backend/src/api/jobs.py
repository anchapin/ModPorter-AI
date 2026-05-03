"""
Jobs API for portkit.

This module provides REST endpoints for job management:
- GET /api/v1/jobs - List jobs for current user
- GET /api/v1/jobs/{job_id} - Get job status
- DELETE /api/v1/jobs/{job_id} - Cancel a job
- POST /api/v1/jobs - Create a new job
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
    Path,
    status,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from services.job_manager import (
    JobManager,
    JobStatus,
    JobOptions,
    ConversionMode,
    TargetVersion,
    OutputFormat,
    get_job_manager,
)

logger = logging.getLogger(__name__)

# Security scheme for auth dependency
security = HTTPBearer()

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


# Pydantic Models


class JobOptionsRequest(BaseModel):
    """Request model for job options"""

    conversion_mode: Optional[ConversionMode] = Field(
        default=ConversionMode.STANDARD, description="Conversion mode: simple, standard, or complex"
    )
    target_version: Optional[TargetVersion] = Field(
        default=TargetVersion.V1_20, description="Target Minecraft version: 1.19, 1.20, or 1.21"
    )
    output_format: Optional[OutputFormat] = Field(
        default=OutputFormat.MCADDON, description="Output format: mcaddon or zip"
    )
    webhook_url: Optional[str] = Field(
        default=None, description="URL to receive webhook on completion"
    )


class JobCreateRequest(BaseModel):
    """Request model for creating a job"""

    file_path: str = Field(..., description="Path to the uploaded file")
    original_filename: str = Field(..., description="Original filename")
    options: Optional[JobOptionsRequest] = Field(default=None, description="Job conversion options")


class JobResponse(BaseModel):
    """Response model for job details"""

    job_id: str = Field(..., description="Unique job identifier")
    user_id: str = Field(..., description="User who owns this job")
    original_filename: str = Field(..., description="Original filename")
    status: str = Field(..., description="Job status")
    progress: int = Field(..., description="Progress percentage (0-100)")
    current_step: str = Field(..., description="Current processing step")
    result_url: Optional[str] = Field(None, description="Download URL when complete")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: str = Field(..., description="Job creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")


class JobListResponse(BaseModel):
    """Response model for listing jobs"""

    jobs: List[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class JobCreateResponse(BaseModel):
    """Response model for job creation"""

    job_id: str = Field(..., description="Created job ID")
    message: str = Field(..., description="Status message")


class JobDeleteResponse(BaseModel):
    """Response model for job cancellation"""

    job_id: str = Field(..., description="Job ID")
    message: str = Field(..., description="Status message")


# Dependency


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> str:
    """
    Get current user ID from the authenticated request context.

    Uses the JWT Bearer token from the Authorization header.
    Raises HTTPException 401 if the token is invalid or user not found.
    """
    from security.auth import verify_token
    from db.models import User
    from sqlalchemy import select

    token = credentials.credentials
    user_id = verify_token(token, "access")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return str(user.id)


async def get_job_manager_dep() -> JobManager:
    """Dependency for getting job manager"""
    return await get_job_manager()


# Endpoints


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: JobCreateRequest,
    job_manager: JobManager = Depends(get_job_manager_dep),
    user_id: str = Depends(get_current_user_id),
) -> JobCreateResponse:
    """
    Create a new conversion job.

    - **file_path**: Path to the uploaded file in storage
    - **original_filename**: Original filename for reference
    - **options**: Optional conversion options (mode, version, format, webhook)

    Returns the job ID for tracking progress.
    """
    options = None
    if request.options:
        options = JobOptions(
            conversion_mode=request.options.conversion_mode,
            target_version=request.options.target_version,
            output_format=request.options.output_format,
            webhook_url=request.options.webhook_url,
        )

    job_id = await job_manager.create_job(
        user_id=user_id,
        file_path=request.file_path,
        original_filename=request.original_filename,
        options=options,
    )

    logger.info(f"Created job {job_id} for user {user_id}")

    return JobCreateResponse(
        job_id=job_id,
        message=f"Job created successfully. Use GET /api/v1/jobs/{job_id} to track progress.",
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(50, ge=1, le=100, description="Maximum jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
    job_manager: JobManager = Depends(get_job_manager_dep),
    user_id: str = Depends(get_current_user_id),
) -> JobListResponse:
    """
    List jobs for the current user.

    - **limit**: Maximum number of jobs to return (1-100)
    - **offset**: Number of jobs to skip for pagination

    Returns a paginated list of jobs.
    """
    jobs = await job_manager.list_jobs(user_id, limit=limit, offset=offset)

    # Convert to response format
    job_responses = [
        JobResponse(
            job_id=job.job_id,
            user_id=job.user_id,
            original_filename=job.original_filename,
            status=job.status.value,
            progress=job.progress,
            current_step=job.current_step,
            result_url=job.result_url,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
        )
        for job in jobs
    ]

    return JobListResponse(
        jobs=job_responses,
        total=len(job_responses),
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str = Path(
        ...,
        pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="Job ID to retrieve",
    ),
    job_manager: JobManager = Depends(get_job_manager_dep),
    user_id: str = Depends(get_current_user_id),
) -> JobResponse:
    """
    Get job status and details.

    - **job_id**: The job identifier

    Returns job status, progress, and result URL when complete.
    """
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found"
        )

    # Check ownership
    if job.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this job"
        )

    return JobResponse(
        job_id=job.job_id,
        user_id=job.user_id,
        original_filename=job.original_filename,
        status=job.status.value,
        progress=job.progress,
        current_step=job.current_step,
        result_url=job.result_url,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


@router.delete("/{job_id}", response_model=JobDeleteResponse)
async def cancel_job(
    job_id: str = Path(
        ...,
        pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="Job ID to cancel",
    ),
    job_manager: JobManager = Depends(get_job_manager_dep),
    user_id: str = Depends(get_current_user_id),
) -> JobDeleteResponse:
    """
    Cancel a pending or processing job.

    - **job_id**: The job identifier

    Cancels a job that is still pending or processing.
    Cannot cancel completed or failed jobs.
    """
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found"
        )

    # Check ownership
    if job.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel this job"
        )

    # Check if job can be cancelled
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status '{job.status.value}'",
        )

    success = await job_manager.cancel_job(job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to cancel job"
        )

    return JobDeleteResponse(job_id=job_id, message=f"Job '{job_id}' cancelled successfully")


# Export router
__all__ = ["router"]
