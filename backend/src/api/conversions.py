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
from services.task_queue import enqueue_task, TaskPriority

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
TEMP_UPLOADS_DIR = os.getenv("TEMP_UPLOADS_DIR", "temp_uploads")
CONVERSION_OUTPUTS_DIR = os.getenv("CONVERSION_OUTPUTS_DIR", "conversion_outputs")
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB chunks for chunked uploads
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


# Resumable Upload Models
class ChunkUploadInitResponse(BaseModel):
    """Response for initializing a chunked upload."""
    upload_id: str = Field(..., description="Unique identifier for this upload session")
    chunk_size: int = Field(..., description="Size of each chunk in bytes")
    total_size: int = Field(..., description="Total file size in bytes")
    filename: str = Field(..., description="Original filename")
    message: str = Field(..., description="Status message")


class ChunkUploadResponse(BaseModel):
    """Response for chunk upload."""
    upload_id: str = Field(..., description="Upload session ID")
    chunk_number: int = Field(..., description="Current chunk number (1-indexed)")
    chunks_received: int = Field(..., description="Total chunks received")
    total_chunks: int = Field(..., description="Total expected chunks")
    progress: float = Field(..., description="Upload progress (0-100)")


class UploadProgressResponse(BaseModel):
    """Response for upload progress check."""
    upload_id: str
    received_bytes: int
    total_bytes: int
    progress: float
    status: str


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

    # Enqueue conversion task to async task queue for background processing
    # This enables concurrent conversions and better resource management
    try:
        await enqueue_task(
            name="conversion",
            payload={
                "conversion_id": conversion_id,
                "file_id": file_id,
                "file_path": file_path,
                "original_filename": safe_filename,
                "target_version": conversion_options.target_version,
                "options": conversion_options.dict(),
            },
            priority=TaskPriority.NORMAL
        )
        logger.info(f"Conversion task enqueued for job: {conversion_id}")
    except Exception as e:
        # Log but don't fail - conversion is still created, can be picked up by worker
        logger.warning(f"Failed to enqueue conversion task: {e}")

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


# Chunked/Resumable Upload Endpoints
@router.post(
    "/api/v1/uploads/init",
    response_model=ChunkUploadInitResponse,
    tags=["uploads"],
)
async def init_chunked_upload(
    filename: str = Form(..., description="Original filename"),
    total_size: int = Form(..., description="Total file size in bytes"),
):
    """
    Initialize a resumable/chunked upload session.
    
    For large files, use this endpoint to start a chunked upload session.
    Returns an upload_id to be used in subsequent chunk upload requests.
    
    **Benefits:**
    - Supports resumable uploads (resume from where left off)
    - Better for large files (100MB+)
    - Progress tracking per chunk
    
    **Request:** multipart/form-data
    - filename: Original filename
    - total_size: Total file size in bytes
    
    **Response:**
    ```json
    {
      "upload_id": "uuid-v4",
      "chunk_size": 5242880,
      "total_size": 104857600,
      "filename": "large_mod.jar",
      "message": "Upload session initialized"
    }
    ```
    """
    # Validate file size
    if total_size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_UPLOAD_SIZE // (1024 * 1024)}MB limit"
        )
    
    # Validate file type
    safe_filename = sanitize_filename(filename)
    is_valid, error_msg = validate_file_type(safe_filename)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    
    # Generate upload ID
    upload_id = str(uuid.uuid4())
    
    # Store upload metadata in cache
    upload_metadata = {
        "upload_id": upload_id,
        "filename": safe_filename,
        "total_size": total_size,
        "chunk_size": CHUNK_SIZE,
        "chunks_received": 0,
        "status": "in_progress",
    }
    
    await cache.set_job_status(f"upload:{upload_id}", upload_metadata)
    
    # Create temporary directory for chunks
    chunks_dir = os.path.join(TEMP_UPLOADS_DIR, "chunks", upload_id)
    os.makedirs(chunks_dir, exist_ok=True)
    
    return ChunkUploadInitResponse(
        upload_id=upload_id,
        chunk_size=CHUNK_SIZE,
        total_size=total_size,
        filename=safe_filename,
        message="Upload session initialized. Use upload_id in subsequent chunk requests."
    )


@router.post(
    "/api/v1/uploads/{upload_id}/chunk",
    response_model=ChunkUploadResponse,
    tags=["uploads"],
)
async def upload_chunk(
    upload_id: UUID,
    chunk_number: int = Form(..., description="Chunk number (1-indexed)"),
    total_chunks: int = Form(..., description="Total number of chunks"),
    chunk: UploadFile = File(..., description="Chunk data"),
):
    """
    Upload a single chunk of a resumable upload.
    
    **Request:** multipart/form-data
    - chunk_number: Current chunk number (1-indexed)
    - total_chunks: Total number of chunks expected
    - chunk: Binary chunk data
    
    **Response:**
    ```json
    {
      "upload_id": "uuid-v4",
      "chunk_number": 1,
      "chunks_received": 1,
      "total_chunks": 20,
      "progress": 5.0
    }
    ```
    """
    upload_id_str = str(upload_id)
    # Get upload metadata
    upload_metadata = await cache.get_job_status(f"upload:{upload_id_str}")
    
    if not upload_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found. Initialize with /api/v1/uploads/init first."
        )
    
    if upload_metadata.get("status") != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload session is {upload_metadata.get('status')}"
        )
    
    # Validate chunk size
    chunk_data = await chunk.read()
    if len(chunk_data) > CHUNK_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chunk size exceeds maximum of {CHUNK_SIZE} bytes"
        )
    
    # Save chunk to disk
    chunks_dir = os.path.join(TEMP_UPLOADS_DIR, "chunks", upload_id_str)
    chunk_path = os.path.join(chunks_dir, f"chunk_{chunk_number:04d}")
    
    with open(chunk_path, "wb") as f:
        f.write(chunk_data)
    
    # Update chunks received count
    chunks_received = upload_metadata.get("chunks_received", 0) + 1
    upload_metadata["chunks_received"] = chunks_received
    await cache.set_job_status(f"upload:{upload_id_str}", upload_metadata)
    
    # Calculate progress
    progress = (chunks_received / total_chunks) * 100
    
    return ChunkUploadResponse(
        upload_id=upload_id_str,
        chunk_number=chunk_number,
        chunks_received=chunks_received,
        total_chunks=total_chunks,
        progress=round(progress, 2)
    )


@router.get(
    "/api/v1/uploads/{upload_id}/progress",
    response_model=UploadProgressResponse,
    tags=["uploads"],
)
async def get_upload_progress(upload_id: UUID):
    """
    Get the progress of a resumable upload.
    
    **Response:**
    ```json
    {
      "upload_id": "uuid-v4",
      "received_bytes": 5242880,
      "total_bytes": 104857600,
      "progress": 5.0,
      "status": "in_progress"
    }
    ```
    """
    upload_id_str = str(upload_id)
    upload_metadata = await cache.get_job_status(f"upload:{upload_id_str}")
    
    if not upload_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )
    
    chunks_dir = os.path.join(TEMP_UPLOADS_DIR, "chunks", upload_id_str)
    received_bytes = 0
    
    if os.path.exists(chunks_dir):
        for chunk_file in os.listdir(chunks_dir):
            chunk_path = os.path.join(chunks_dir, chunk_file)
            if os.path.isfile(chunk_path):
                received_bytes += os.path.getsize(chunk_path)
    
    total_bytes = upload_metadata.get("total_size", 0)
    progress = (received_bytes / total_bytes * 100) if total_bytes > 0 else 0
    
    return UploadProgressResponse(
        upload_id=upload_id_str,
        received_bytes=received_bytes,
        total_bytes=total_bytes,
        progress=round(progress, 2),
        status=upload_metadata.get("status", "unknown")
    )


@router.post(
    "/api/v1/uploads/{upload_id}/complete",
    response_model=ConversionCreateResponse,
    tags=["uploads"],
)
async def complete_chunked_upload(
    upload_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Complete a resumable upload by combining all chunks.
    
    This endpoint combines all uploaded chunks into the final file
    and creates a conversion job.
    """
    upload_id_str = str(upload_id)
    # Get upload metadata
    upload_metadata = await cache.get_job_status(f"upload:{upload_id_str}")
    
    if not upload_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )
    
    if upload_metadata.get("status") != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload session is {upload_metadata.get('status')}"
        )
    
    chunks_dir = os.path.join(TEMP_UPLOADS_DIR, "chunks", upload_id_str)
    safe_filename = upload_metadata["filename"]
    total_size = upload_metadata["total_size"]
    
    # Combine chunks
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(safe_filename)[1]
    saved_filename = f"{file_id}{file_ext}"
    file_path = os.path.join(TEMP_UPLOADS_DIR, saved_filename)
    
    try:
        with open(file_path, "wb") as outfile:
            # Read chunks in order
            chunk_number = 1
            while True:
                chunk_path = os.path.join(chunks_dir, f"chunk_{chunk_number:04d}")
                if not os.path.exists(chunk_path):
                    break
                with open(chunk_path, "rb") as infile:
                    outfile.write(infile.read())
                chunk_number += 1
        
        # Verify file size
        actual_size = os.path.getsize(file_path)
        if actual_size != total_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size mismatch. Expected {total_size}, got {actual_size}"
            )
        
        # Update upload status
        upload_metadata["status"] = "completed"
        await cache.set_job_status(f"upload:{upload_id_str}", upload_metadata)
        
        # Create conversion job
        job = await crud.create_job(
            session=db,
            file_id=file_id,
            original_filename=safe_filename,
            target_version="1.20.0",
            options={},
            commit=True,
        )
        
        conversion_id = str(job.id)
        
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
        
        # Clean up chunks
        shutil.rmtree(chunks_dir, ignore_errors=True)
        
        return ConversionCreateResponse(
            conversion_id=conversion_id,
            status="queued",
            estimated_time_seconds=1800,
            created_at=job.created_at,
        )
        
    except Exception as e:
        logger.error(f"Failed to complete chunked upload: {e}")
        # Clean up on failure
        if os.path.exists(file_path):
            os.remove(file_path)
        shutil.rmtree(chunks_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete upload: {str(e)}"
        )


@router.delete(
    "/api/v1/uploads/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["uploads"],
)
async def cancel_upload(upload_id: UUID):
    """
    Cancel a resumable upload session.
    
    Deletes all uploaded chunks and cleans up the upload session.
    """
    upload_id_str = str(upload_id)
    upload_metadata = await cache.get_job_status(f"upload:{upload_id_str}")
    
    if not upload_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )
    
    # Update status to cancelled
    upload_metadata["status"] = "cancelled"
    await cache.set_job_status(f"upload:{upload_id_str}", upload_metadata)
    
    # Clean up chunks
    chunks_dir = os.path.join(TEMP_UPLOADS_DIR, "chunks", upload_id_str)
    shutil.rmtree(chunks_dir, ignore_errors=True)
    
    return None
