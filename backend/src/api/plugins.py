"""
Plugin Ecosystem API endpoints.

This module provides REST endpoints for IDE plugin integrations:
- POST /api/v1/plugins/convert - Start conversion from IDE plugin
- GET /api/v1/plugins/convert/{job_id}/status - Get conversion status
- GET /api/v1/plugins/convert/{job_id}/download - Download converted addon

Supported plugins:
- bridge. (most-used Bedrock add-on IDE)
- VS Code Extension
- Blockbench Plugin
"""

import base64
import logging
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db import crud
from db.models import User
from api._authz import get_current_user  # issue #1417
from services.cache import CacheService

logger = logging.getLogger(__name__)

router = APIRouter()

cache = CacheService()


async def _ensure_owned_job(db, job_id: str, current_user: User):
    """Issue #1417: 404 unless ``job_id`` exists AND is owned by ``current_user``."""
    job = await crud.get_job(db, job_id)
    if job is None or str(getattr(job, "user_id", "") or "") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversion job '{job_id}' not found",
        )
    return job


TEMP_UPLOADS_DIR = os.getenv("TEMP_UPLOADS_DIR", "temp_uploads")
CONVERSION_OUTPUTS_DIR = os.getenv("CONVERSION_OUTPUTS_DIR", "conversion_outputs")


class PluginType(str, Enum):
    BRIDGE = "bridge"
    VSCODE = "vscode"
    BLOCKBENCH = "blockbench"


class PluginConversionRequest(BaseModel):
    plugin_type: PluginType = Field(
        ...,
        description="The IDE plugin initiating the conversion (bridge, vscode, or blockbench)",
    )
    file_data: str = Field(
        ...,
        description="Base64-encoded Java mod file (.jar or .zip)",
    )
    file_name: str = Field(
        ...,
        description="Original filename of the mod",
    )
    target_version: str = Field(
        default="1.20.0",
        description="Target Minecraft Bedrock version",
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional conversion settings",
    )

    @field_validator("file_data")
    @classmethod
    def validate_base64(cls, v: str) -> str:
        try:
            base64.b64decode(v, validate=True)
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {e}")
        return v


class PluginConversionResponse(BaseModel):
    job_id: str = Field(..., description="Unique conversion job ID")
    status: str = Field(..., description="Initial job status")
    message: str = Field(..., description="Status message")
    estimated_time: Optional[int] = Field(
        default=35,
        description="Estimated conversion time in seconds",
    )


class PluginConversionStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    result_url: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime


async def save_plugin_file(
    file_data: str,
    file_id: str,
    original_filename: str,
) -> tuple[str, int]:
    file_ext = os.path.splitext(original_filename)[1].lower()
    if file_ext not in [".jar", ".zip"]:
        file_ext = ".jar"

    saved_filename = f"{file_id}{file_ext}"
    file_path = os.path.join(TEMP_UPLOADS_DIR, saved_filename)

    os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

    try:
        decoded_data = base64.b64decode(file_data)
        real_file_size = len(decoded_data)

        with open(file_path, "wb") as f:
            f.write(decoded_data)

        return saved_filename, real_file_size
    except Exception as e:
        logger.error(f"Failed to save plugin file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process uploaded file: {e}",
        )


async def trigger_conversion(job_id: str) -> None:
    """Trigger the conversion pipeline for a job."""
    try:
        from main import simulate_ai_conversion, try_ai_engine_or_fallback

        await try_ai_engine_or_fallback(job_id)
    except Exception as e:
        logger.error(f"Failed to trigger conversion for job {job_id}: {e}")


@router.post(
    "/convert",
    response_model=PluginConversionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["plugins"],
)
async def start_plugin_conversion(
    request: PluginConversionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start a new conversion job from an IDE plugin.

    This endpoint accepts base64-encoded mod files from IDE plugins
    (bridge., VS Code, Blockbench) and initiates the conversion pipeline.
    """
    file_id = str(uuid.uuid4())
    original_filename = request.file_name

    saved_filename, file_size = await save_plugin_file(
        file_data=request.file_data,
        file_id=file_id,
        original_filename=original_filename,
    )

    logger.info(
        f"Plugin conversion started: plugin={request.plugin_type}, "
        f"file={original_filename}, file_id={file_id}, size={file_size}"
    )

    job = await crud.create_job(
        db,
        file_id=file_id,
        original_filename=original_filename,
        target_version=request.target_version,
        options=request.options or {},
        user_id=str(current_user.id),  # issue #1417: record owner for later checks
        commit=False,
    )
    job = await crud.update_job_status(db, str(job.id), "queued", commit=False)
    await db.commit()
    await db.refresh(job)

    mirror_data = {
        "job_id": str(job.id),
        "file_id": file_id,
        "original_filename": original_filename,
        "status": "preprocessing",
        "progress": 0,
        "target_version": request.target_version,
        "options": request.options,
        "result_url": None,
        "error_message": None,
        "created_at": job.created_at.isoformat()
        if job.created_at
        else datetime.now(timezone.utc).isoformat(),
        "updated_at": job.updated_at.isoformat()
        if job.updated_at
        else datetime.now(timezone.utc).isoformat(),
    }

    await cache.set_job_status(str(job.id), mirror_data)
    await cache.set_progress(str(job.id), 0)

    background_tasks.add_task(trigger_conversion, str(job.id))

    return PluginConversionResponse(
        job_id=str(job.id),
        status="preprocessing",
        message=f"Conversion started from {request.plugin_type} plugin",
        estimated_time=35,
    )


@router.get(
    "/convert/{job_id}/status",
    response_model=PluginConversionStatus,
    tags=["plugins"],
)
async def get_plugin_conversion_status(
    job_id: str = Path(
        ...,
        pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="Unique conversion job ID",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the status of a conversion job started from an IDE plugin.
    """
    # Issue #1417: ownership check via DB even when serving from cache
    await _ensure_owned_job(db, job_id, current_user)

    cached = await cache.get_job_status(job_id)
    if cached:
        status_val = cached.get("status", "unknown")
        progress = cached.get("progress", 0)
        error_message = cached.get("error_message")
        result_url = cached.get("result_url")

        if status_val == "completed":
            result_url = f"/api/v1/plugins/convert/{job_id}/download"

        descriptive_message = _build_status_message(status_val, progress, error_message)

        created_at_str = cached.get("created_at")
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = datetime.now(timezone.utc)
        else:
            created_at = datetime.now(timezone.utc)

        return PluginConversionStatus(
            job_id=job_id,
            status=status_val,
            progress=progress,
            message=descriptive_message,
            result_url=result_url,
            error=error_message,
            created_at=created_at,
        )

    job = await crud.get_job(db, job_id)
    if not job:
        # Should be unreachable: _ensure_owned_job above already verified existence.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversion job '{job_id}' not found",
        )

    progress = job.progress.progress if job.progress else 0
    error_message = None
    result_url = None
    job_status = job.status

    if job_status == "completed":
        result_url = f"/api/v1/plugins/convert/{job_id}/download"
    elif job_status == "failed":
        error_message = "Conversion failed"

    descriptive_message = _build_status_message(job_status, progress, error_message)

    return PluginConversionStatus(
        job_id=job_id,
        status=job_status,
        progress=progress,
        message=descriptive_message,
        result_url=result_url,
        error=error_message,
        created_at=job.created_at,
    )


@router.get(
    "/convert/{job_id}/download",
    tags=["plugins"],
)
async def download_plugin_conversion(
    job_id: str = Path(
        ...,
        pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        description="Unique conversion job ID",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download the converted addon from a plugin-initiated conversion.
    """
    # Issue #1417: enforce ownership before serving any cached/db data
    await _ensure_owned_job(db, job_id, current_user)

    cached = await cache.get_job_status(job_id)
    if not cached:
        job = await crud.get_job(db, job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversion job '{job_id}' not found",
            )
        job_status = job.status
        original_filename = job.input_data.get("original_filename", "converted")
    else:
        job_status = cached.get("status")
        original_filename = cached.get("original_filename", "converted")

    if job_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' is not completed. Current status: {job_status}",
        )

    internal_filename = f"{job_id}_converted.mcaddon"
    file_path = os.path.join(CONVERSION_OUTPUTS_DIR, internal_filename)

    if not os.path.exists(file_path):
        internal_filename_zip = f"{job_id}_converted.zip"
        zip_path = os.path.join(CONVERSION_OUTPUTS_DIR, internal_filename_zip)
        if os.path.exists(zip_path):
            file_path = zip_path
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Converted file not found",
            )

    base_name = original_filename.rsplit(".", 1)[0] if original_filename else "converted"
    return FileResponse(
        path=file_path,
        filename=f"{base_name}_converted.mcaddon",
        media_type="application/octet-stream",
    )


def _build_status_message(status: str, progress: int, error: Optional[str] = None) -> str:
    """Build a human-readable status message."""
    status_messages = {
        "queued": "Job is queued and waiting to start.",
        "preprocessing": "Preprocessing uploaded file.",
        "processing": f"AI conversion in progress ({progress}%).",
        "postprocessing": "Finalizing conversion results.",
        "completed": "Conversion completed successfully.",
        "failed": f"Conversion failed: {error}" if error else "Conversion failed.",
        "cancelled": "Job was cancelled by the user.",
    }
    return status_messages.get(status, f"Job status: {status}.")
