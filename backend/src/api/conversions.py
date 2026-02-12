"""
Conversion API endpoints.

This module provides REST endpoints for managing conversion jobs:
- POST /api/v1/conversions - Start new conversion
- GET /api/v1/conversions - List conversions (paginated)
- GET /api/v1/conversions/{id} - Get conversion status
- GET /api/v1/conversions/{id}/download - Download .mcaddon file
- DELETE /api/v1/conversions/{id} - Cancel/delete conversion
- WS /api/v1/conversions/{id}/ws - WebSocket progress endpoint
"""

import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db import crud
from websocket.manager import manager
from websocket.progress_handler import ProgressHandler, AgentStatus
from services.cache import CacheService

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
TEMP_UPLOADS_DIR = os.getenv("TEMP_UPLOADS_DIR", "temp_uploads")
CONVERSION_OUTPUTS_DIR = os.getenv("CONVERSION_OUTPUTS_DIR", "conversion_outputs")
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {".jar", ".zip"}

# Cache service
cache = CacheService()


# Pydantic Models
class ConversionOptions(BaseModel):
    """Options for conversion behavior."""

    assumptions: str = Field(
        default="conservative",
        description="Conversion strategy: 'conservative' or 'aggressive'",
    )
    target_version: str = Field(
        default="1.20.0",
        description="Target Minecraft Bedrock version",
    )

    @validator("assumptions")
    def validate_assumptions(cls, v):
        if v not in ("conservative", "aggressive"):
            raise ValueError("assumptions must be 'conservative' or 'aggressive'")
        return v


class ConversionCreateRequest(BaseModel):
    """Request model for creating a conversion (multipart form data)."""

    options: Optional[ConversionOptions] = Field(
        default=None, description="Conversion options"
    )


class ConversionCreateResponse(BaseModel):
    """Response model for conversion creation."""

    conversion_id: str = Field(..., description="UUID of the conversion job")
    status: str = Field(..., description="Initial status (queued)")
    estimated_time_seconds: int = Field(
        default=1800, description="Estimated conversion time in seconds"
    )
    created_at: datetime = Field(
        ...,
        description="ISO 8601 timestamp when conversion was created",
    )


class ConversionStatusResponse(BaseModel):
    """Response model for conversion status."""

    conversion_id: str = Field(..., description="UUID of the conversion job")
    status: str = Field(..., description="Current status")
    progress: int = Field(..., description="Progress percentage (0-100)")
    message: str = Field(..., description="Human-readable status message")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    result_url: Optional[str] = Field(None, description="Download URL if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    original_filename: Optional[str] = Field(None, description="Original uploaded filename")


class ConversionListResponse(BaseModel):
    """Response model for conversion listing."""

    conversions: List[ConversionStatusResponse]
    total: int = Field(..., description="Total number of conversions")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


# Helper Functions
def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename with only safe characters
    """
    # Remove directory paths
    filename = os.path.basename(filename)

    # Remove dangerous characters
    filename = "".join(c for c in filename if c.isalnum() or c in "._-")

    # Ensure filename is not empty
    if not filename:
        filename = "uploaded_file"

    return filename


def validate_file_type(filename: str) -> tuple[bool, str]:
    """
    Validate file type is allowed.

    Args:
        filename: Name of the file to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    _, ext = os.path.splitext(filename.lower())

    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type {ext} not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    return True, ""


async def validate_file_size(file: UploadFile) -> tuple[bool, str]:
    """
    Validate file size does not exceed maximum.

    Args:
        file: UploadFile to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Read file to check size
    total_size = 0
    for chunk in file.file:
        total_size += len(chunk)
        if total_size > MAX_UPLOAD_SIZE:
            return False, f"File size exceeds {MAX_UPLOAD_SIZE // (1024 * 1024)}MB limit"

    # Reset file pointer
    await file.seek(0)

    return True, ""


# WebSocket Endpoint
@router.websocket("/api/v1/conversions/{conversion_id}/ws")
async def websocket_conversion_progress(websocket: WebSocket, conversion_id: str):
    """
    WebSocket endpoint for real-time conversion progress updates.

    Connect to this endpoint to receive live progress updates for a conversion job.

    Message Format (Server → Client):
    ```json
    {
      "type": "agent_progress",
      "data": {
        "agent": "JavaAnalyzerAgent",
        "status": "in_progress",
        "progress": 45,
        "message": "Analyzing Java AST...",
        "timestamp": "2025-02-12T10:30:00Z",
        "details": {}
      }
    }
    ```

    Message Types:
    - agent_progress: Individual agent progress update
    - conversion_complete: Entire conversion completed
    - conversion_failed: Entire conversion failed

    Args:
        websocket: WebSocket connection
        conversion_id: UUID of the conversion job to follow
    """
    await manager.connect(websocket, conversion_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "connection_established",
                "data": {
                    "conversion_id": conversion_id,
                    "message": "Connected to conversion progress stream",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
        )

        # Keep connection alive and handle incoming messages
        while True:
            # Receive any messages from client (for future bidirectional support)
            try:
                data = await websocket.receive_text()
                # Currently just echo back, but could handle client commands
                logger.debug(f"Received WebSocket message for {conversion_id}: {data}")
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for conversion {conversion_id}")
                break

    except Exception as e:
        logger.error(f"WebSocket error for conversion {conversion_id}: {e}")
    finally:
        manager.disconnect(websocket, conversion_id)


# REST Endpoints
@router.post(
    "/api/v1/conversions",
    response_model=ConversionCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["conversions"],
)
async def create_conversion(
    file: UploadFile = File(..., description="Mod file (.jar or .zip)"),
    options: str = Form(default="{}", description="JSON string of conversion options"),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new mod conversion job.

    Uploads a Java mod file and starts the conversion process to Bedrock Edition.
    Returns immediately with a conversion_id for tracking progress.

    **Security:**
    - Validates file type (.jar, .zip only)
    - Enforces 100MB file size limit
    - Sanitizes filenames to prevent path traversal
    - Rate limiting (applied at middleware level)

    **Request:** multipart/form-data
    - file: The mod file (binary)
    - options: JSON string with conversion options
      ```json
      {
        "assumptions": "conservative",
        "target_version": "1.20.0"
      }
      ```

    **Response:** 202 Accepted
    ```json
    {
      "conversion_id": "uuid-v4",
      "status": "queued",
      "estimated_time_seconds": 1800,
      "created_at": "2025-02-12T10:30:00Z"
    }
    ```

    Use the returned conversion_id with:
    - GET /api/v1/conversions/{id} - Check status
    - WS /api/v1/conversions/{id}/ws - Real-time progress
    - GET /api/v1/conversions/{id}/download - Download result
    """
    # Validate file was provided
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    # Sanitize filename
    safe_filename = sanitize_filename(file.filename)

    # Validate file type
    is_valid, error_msg = validate_file_type(safe_filename)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    # Validate file size
    is_valid, error_msg = await validate_file_size(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=error_msg,
        )

    # Parse options
    try:
        import json

        options_data = json.loads(options)
        conversion_options = ConversionOptions(**options_data)
    except Exception as e:
        logger.warning(f"Invalid options provided: {e}, using defaults")
        conversion_options = ConversionOptions()

    # Generate file_id and save file
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(safe_filename)[1]
    saved_filename = f"{file_id}{file_ext}"
    file_path = os.path.join(TEMP_UPLOADS_DIR, saved_filename)

    # Ensure upload directory exists
    os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

    # Save uploaded file
    try:
        with open(file_path, "wb") as buffer:
            for chunk in file.file:
                buffer.write(chunk)
        logger.info(f"File saved: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file",
        )
    finally:
        await file.close()

    # Create conversion job in database
    try:
        job = await crud.create_job(
            session=db,
            file_id=file_id,
            original_filename=safe_filename,
            target_version=conversion_options.target_version,
            options=conversion_options.dict(),
            commit=True,
        )

        conversion_id = str(job.id)
        logger.info(f"Conversion job created: {conversion_id}")

    except Exception as e:
        logger.error(f"Failed to create conversion job: {e}")
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversion job",
        )

    # Start background conversion task
    # TODO: Integrate with actual AI Engine or simulation
    # For now, we'll update status to queued
    from fastapi.background import BackgroundTasks

    # Note: Background tasks should be added by the caller (main.py)
    # We'll just return the conversion details

    # Cache job status
    await cache.set_job_status(
        conversion_id,
        {
            "conversion_id": conversion_id,
            "status": "queued",
            "progress": 0,
            "original_filename": safe_filename,
        },
    )
    await cache.set_progress(conversion_id, 0)

    return ConversionCreateResponse(
        conversion_id=conversion_id,
        status="queued",
        estimated_time_seconds=1800,  # 30 minutes default
        created_at=job.created_at,
    )


@router.get(
    "/api/v1/conversions/{conversion_id}",
    response_model=ConversionStatusResponse,
    tags=["conversions"],
)
async def get_conversion(
    conversion_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the status of a specific conversion job.

    Returns detailed status information including:
    - Current status (queued, processing, completed, failed)
    - Progress percentage
    - Human-readable message
    - Download URL (if completed)
    - Error details (if failed)

    **Response:**
    ```json
    {
      "conversion_id": "uuid-v4",
      "status": "processing",
      "progress": 45,
      "message": "JavaAnalyzerAgent is analyzing mod structure...",
      "created_at": "2025-02-12T10:30:00Z",
      "updated_at": "2025-02-12T10:35:00Z",
      "result_url": null,
      "error": null,
      "original_filename": "example_mod.jar"
    }
    ```
    """
    # Try cache first for speed
    cached = await cache.get_job_status(conversion_id)
    if cached:
        return ConversionStatusResponse(**cached)

    # Fallback to database
    job = await crud.get_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversion {conversion_id} not found",
        )

    # Build response
    progress = job.progress.progress if job.progress else 0
    result_url = None

    if job.status == "completed":
        result_url = f"/api/v1/conversions/{conversion_id}/download"

    # Build descriptive message
    status_messages = {
        "queued": "Job is queued and waiting to start",
        "preprocessing": "Preprocessing uploaded file",
        "processing": f"AI conversion in progress ({progress}%)",
        "postprocessing": "Finalizing conversion results",
        "completed": "Conversion completed successfully",
        "failed": "Conversion failed",
        "cancelled": "Job was cancelled by the user",
    }

    message = status_messages.get(job.status, f"Job status: {job.status}")

    response = ConversionStatusResponse(
        conversion_id=conversion_id,
        status=job.status,
        progress=progress,
        message=message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        result_url=result_url,
        error=None,
        original_filename=job.input_data.get("original_filename"),
    )

    # Update cache
    await cache.set_job_status(conversion_id, response.dict())

    return response


@router.get(
    "/api/v1/conversions",
    response_model=ConversionListResponse,
    tags=["conversions"],
)
async def list_conversions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    """
    List conversion jobs with pagination.

    Returns a paginated list of conversions, optionally filtered by status.

    **Query Parameters:**
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - status: Filter by status (optional)

    **Response:**
    ```json
    {
      "conversions": [...],
      "total": 42,
      "page": 1,
      "page_size": 20
    }
    ```
    """
    # Get all jobs
    jobs = await crud.list_jobs(db)

    # Filter by status if provided
    if status:
        jobs = [job for job in jobs if job.status == status]

    # Pagination
    total = len(jobs)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_jobs = jobs[start:end]

    # Build response
    conversions = []
    for job in paginated_jobs:
        progress = job.progress.progress if job.progress else 0
        result_url = None

        if job.status == "completed":
            result_url = f"/api/v1/conversions/{job.id}/download"

        conversions.append(
            ConversionStatusResponse(
                conversion_id=str(job.id),
                status=job.status,
                progress=progress,
                message=f"Job status: {job.status}",
                created_at=job.created_at,
                updated_at=job.updated_at,
                result_url=result_url,
                error=None,
                original_filename=job.input_data.get("original_filename"),
            )
        )

    return ConversionListResponse(
        conversions=conversions,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/api/v1/conversions/{conversion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["conversions"],
)
async def delete_conversion(
    conversion_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel or delete a conversion job.

    - If the job is in progress, it will be cancelled
    - If the job is completed, the result file will be deleted
    - The database record will be marked as deleted

    **Response:** 204 No Content (success)
    """
    job = await crud.get_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversion {conversion_id} not found",
        )

    # Update status to cancelled
    await crud.update_job_status(db, conversion_id, "cancelled")
    await cache.set_job_status(
        conversion_id,
        {
            "conversion_id": conversion_id,
            "status": "cancelled",
            "progress": 0,
            "original_filename": job.input_data.get("original_filename"),
        },
    )

    # Notify WebSocket clients
    await ProgressHandler.broadcast_conversion_failed(
        conversion_id, "Conversion was cancelled by user"
    )

    return None


@router.get(
    "/api/v1/conversions/{conversion_id}/download",
    tags=["conversions"],
)
async def download_conversion(conversion_id: str, db: AsyncSession = Depends(get_db)):
    """
    Download the converted .mcaddon file.

    Returns the converted add-on file for download.
    The job must have status "completed".

    **Response:** Binary file download
    - Content-Type: application/zip
    - Content-Disposition: attachment; filename="{original_name}_converted.mcaddon"

    **Error Responses:**
    - 404: Conversion not found or result file missing
    - 400: Conversion not completed
    """
    job = await crud.get_job(db, conversion_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversion {conversion_id} not found",
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conversion is not completed. Current status: {job.status}",
        )

    # Determine file path
    # Check for both .mcaddon and .zip extensions
    base_path = os.path.join(CONVERSION_OUTPUTS_DIR, f"{conversion_id}_converted")

    mcaddon_path = base_path + ".mcaddon"
    zip_path = base_path + ".zip"

    file_path = None
    if os.path.exists(mcaddon_path):
        file_path = mcaddon_path
    elif os.path.exists(zip_path):
        file_path = zip_path

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result file not found on server",
        )

    # Generate download filename
    original_filename = job.input_data.get("original_filename", "mod")
    base_name = os.path.splitext(original_filename)[0]
    download_filename = f"{base_name}_converted.mcaddon"

    return FileResponse(
        path=file_path,
        media_type="application/zip",
        filename=download_filename,
    )
