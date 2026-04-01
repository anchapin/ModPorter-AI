"""
File Upload API for ModPorter-AI.

Provides endpoints for:
- JAR file upload with validation
- Chunked upload support for large files
- Upload status tracking
"""

import os
import uuid
import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    BackgroundTasks,
    Path,
    Query,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.storage import StorageManager
from services.file_handler import FileHandler
from api.jobs import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])

# Storage and file handler instances
storage = StorageManager()
file_handler = FileHandler()


# Pydantic models for request/response
class UploadInitResponse(BaseModel):
    """Response for initiating a chunked upload"""

    upload_id: str = Field(..., description="Unique identifier for the upload session")
    chunk_size: int = Field(..., description="Expected chunk size in bytes")
    total_size: Optional[int] = Field(None, description="Total file size if known")
    message: str = Field(..., description="Status message")


class ChunkUploadResponse(BaseModel):
    """Response for uploading a chunk"""

    upload_id: str = Field(..., description="Upload session ID")
    chunk_index: int = Field(..., description="Index of the uploaded chunk")
    chunks_received: int = Field(..., description="Total chunks received so far")
    message: str = Field(..., description="Status message")


class UploadCompleteResponse(BaseModel):
    """Response for completing an upload"""

    job_id: str = Field(..., description="Unique job ID for the uploaded file")
    original_filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="Size of the uploaded file in bytes")
    content_type: str = Field(..., description="Content type of the file")
    message: str = Field(..., description="Status message")


class UploadStatusResponse(BaseModel):
    """Response for upload status check"""

    job_id: str = Field(..., description="Job ID")
    status: str = Field(..., description="Upload status: pending, uploading, completed, failed")
    progress: int = Field(..., description="Upload progress percentage")
    message: str = Field(..., description="Status message")


class UploadErrorResponse(BaseModel):
    """Error response model"""

    detail: str = Field(..., description="Error message")


# In-memory storage for upload sessions (would be Redis in production)
upload_sessions: dict = {}


def validate_file_type(filename: str, content_type: str) -> bool:
    """Validate file type is acceptable JAR/ZIP"""
    allowed_extensions = [".jar", ".zip", ".mcaddon"]
    allowed_content_types = [
        "application/java-archive",
        "application/zip",
        "application/x-java-archive",
    ]

    ext = os.path.splitext(filename)[1].lower()

    # Check extension
    if ext not in allowed_extensions:
        return False

    # Check content type (if provided)
    if content_type and content_type not in allowed_content_types:
        # Some clients send application/octet-stream for JARs
        if content_type != "application/octet-stream":
            return False

    return True


@router.post("", response_model=UploadCompleteResponse, status_code=201)
async def upload_jar_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    user_id: str = Depends(get_current_user_id),
) -> UploadCompleteResponse:
    """
    Upload a JAR file for processing.

    - Accepts multipart/form-data with a JAR/ZIP file
    - Validates file type (application/java-archive, application/zip)
    - Stores file and returns job_id for tracking

    Maximum file size: 100MB
    """
    # Validate file type
    if not validate_file_type(file.filename, file.content_type):
        raise HTTPException(
            status_code=400, detail=f"Invalid file type. Allowed: .jar, .zip, .mcaddon"
        )

    # Generate job ID
    job_id = str(uuid.uuid4())
    original_filename = file.filename

    # Determine save path
    file_ext = os.path.splitext(original_filename)[1].lower()
    saved_filename = f"{job_id}{file_ext}"

    try:
        # Read file content
        content = await file.read()
        file_size = len(content)

        # Validate file size (max 100MB)
        MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
        if file_size > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds the limit of {MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
            )

        # Save file using storage manager
        file_path = await storage.save_file(
            content=content,
            job_id=job_id,
            filename=saved_filename,
            user_id=user_id,
        )

        # Process file in background (validation, metadata extraction)
        if background_tasks:
            background_tasks.add_task(file_handler.process_file, job_id=job_id, file_path=file_path)

        logger.info(f"File uploaded successfully: {original_filename} -> {job_id}")

        return UploadCompleteResponse(
            job_id=job_id,
            original_filename=original_filename,
            file_size=file_size,
            content_type=file.content_type or "application/java-archive",
            message=f"File '{original_filename}' uploaded successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.post("/chunked/init", response_model=UploadInitResponse)
async def init_chunked_upload(
    filename: str = Query(..., description="Original filename"),
    total_size: Optional[int] = Query(None, description="Total file size in bytes"),
    content_type: Optional[str] = Query(None, description="Content type"),
):
    """
    Initialize a chunked upload session.

    Returns an upload_id to be used for subsequent chunk uploads.
    """
    # Validate file type
    if not validate_file_type(filename, content_type or ""):
        raise HTTPException(
            status_code=400, detail=f"Invalid file type. Allowed: .jar, .zip, .mcaddon"
        )

    # Generate upload session ID
    upload_id = str(uuid.uuid4())
    chunk_size = 5 * 1024 * 1024  # 5MB chunks

    # Store upload session
    upload_sessions[upload_id] = {
        "filename": filename,
        "total_size": total_size,
        "content_type": content_type,
        "chunks": [],
        "status": "uploading",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return UploadInitResponse(
        upload_id=upload_id,
        chunk_size=chunk_size,
        total_size=total_size,
        message="Chunked upload initialized. Upload chunks using /chunked/{upload_id}",
    )


@router.post("/chunked/{upload_id}", response_model=ChunkUploadResponse)
async def upload_chunk(
    upload_id: str = Path(..., description="Upload session ID"),
    chunk: UploadFile = File(..., description="File chunk"),
    chunk_index: int = Query(..., description="Index of the chunk"),
):
    """
    Upload a chunk of a large file.

    - upload_id: Session ID from init endpoint
    - chunk: Binary chunk data
    - chunk_index: Zero-based index of the chunk
    """
    # Verify upload session exists
    if upload_id not in upload_sessions:
        raise HTTPException(
            status_code=404, detail="Upload session not found. Initialize with /chunked/init first"
        )

    session = upload_sessions[upload_id]

    # Read chunk content
    content = await chunk.read()

    # Store chunk
    session["chunks"].append({"index": chunk_index, "content": content, "size": len(content)})

    # Sort chunks by index
    session["chunks"].sort(key=lambda x: x["index"])

    return ChunkUploadResponse(
        upload_id=upload_id,
        chunk_index=chunk_index,
        chunks_received=len(session["chunks"]),
        message=f"Chunk {chunk_index} received",
    )


@router.post("/chunked/{upload_id}/complete", response_model=UploadCompleteResponse)
async def complete_chunked_upload(
    upload_id: str = Path(..., description="Upload session ID"),
):
    """
    Complete a chunked upload and reassemble the file.
    """
    if upload_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="Upload session not found")

    session = upload_sessions[upload_id]

    # Reassemble chunks
    try:
        content = b"".join(chunk["content"] for chunk in session["chunks"])
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing chunk: {e}")

    # Generate job ID
    job_id = str(uuid.uuid4())
    original_filename = session["filename"]
    file_ext = os.path.splitext(original_filename)[1].lower()
    saved_filename = f"{job_id}{file_ext}"

    # Save file
    file_path = await storage.save_file(
        content=content, job_id=job_id, filename=saved_filename, user_id="default"
    )

    # Clean up session
    del upload_sessions[upload_id]

    # Process file
    await file_handler.process_file(job_id=job_id, file_path=file_path)

    return UploadCompleteResponse(
        job_id=job_id,
        original_filename=original_filename,
        file_size=len(content),
        content_type=session["content_type"] or "application/java-archive",
        message=f"File '{original_filename}' uploaded and assembled successfully",
    )


@router.get("/{job_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    job_id: str = Path(
        ...,
        pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="Job ID to check status for",
    ),
):
    """
    Get the status of an uploaded file.

    Returns current processing status and progress.
    """
    # Get status from storage manager
    status = await storage.get_upload_status(job_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Upload job '{job_id}' not found")

    return UploadStatusResponse(
        job_id=job_id,
        status=status.get("status", "unknown"),
        progress=status.get("progress", 0),
        message=status.get("message", "Status unknown"),
    )


@router.delete("/{job_id}")
async def cancel_upload(
    job_id: str = Path(
        ...,
        pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="Job ID to cancel",
    ),
):
    """
    Cancel an in-progress upload and clean up files.
    """
    # Delete files associated with job
    await storage.delete_job_files(job_id)

    return {"message": f"Upload job '{job_id}' cancelled and files cleaned up"}


# Export router for inclusion in main.py
__all__ = ["router"]
