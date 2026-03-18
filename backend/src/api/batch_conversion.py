"""
Batch Conversion API

Convert multiple mods simultaneously.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from db.base import get_db
from db.models import User, ConversionJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch", tags=["Batch Conversion"])


class BatchConversionRequest(BaseModel):
    """Batch conversion request."""

    files: List[Dict[str, Any]] = Field(..., min_items=2, max_items=20)
    options: Optional[Dict[str, Any]] = None
    priority: str = Field(default="normal", description="low, normal, high")


class BatchConversionResponse(BaseModel):
    """Batch conversion response."""

    batch_id: str
    total_files: int
    estimated_time_minutes: int
    status: str
    message: str


class BatchStatusResponse(BaseModel):
    """Batch status response."""

    batch_id: str
    total: int
    completed: int
    failed: int
    pending: int
    progress_percent: float
    conversions: List[dict]


class BatchResultResponse(BaseModel):
    """Batch result response."""

    batch_id: str
    results: List[dict]
    download_all_url: Optional[str]
    summary: dict


@router.post("/convert", response_model=BatchConversionResponse)
async def start_batch_conversion(
    request: BatchConversionRequest,
    user_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start batch conversion of multiple mods.

    - Upload 2-20 mod files
    - Convert simultaneously
    - Track progress centrally
    - Download all results as ZIP
    """
    # Check user quota
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if user has batch conversion access (Pro feature)
    # For beta, allow all users
    if len(request.files) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 files per batch",
        )

    # Create batch record
    batch_id = f"batch_{datetime.utcnow().timestamp()}"

    # Create individual conversion jobs
    conversion_ids = []
    for file_data in request.files:
        conversion = ConversionJob(
            user_id=user_id,
            status="queued",
            input_data=file_data,
            batch_id=batch_id,
        )
        db.add(conversion)
        conversion_ids.append(str(conversion.id))

    await db.commit()

    # Start background processing
    background_tasks.add_task(
        process_batch_conversion,
        batch_id,
        conversion_ids,
        request.options,
    )

    # Estimate time (2 minutes per file average)
    estimated_time = len(request.files) * 2

    return BatchConversionResponse(
        batch_id=batch_id,
        total_files=len(request.files),
        estimated_time_minutes=estimated_time,
        status="queued",
        message=f"Batch conversion started with {len(request.files)} files",
    )


async def process_batch_conversion(
    batch_id: str,
    conversion_ids: List[str],
    options: Optional[Dict[str, Any]],
):
    """
    Process batch conversion in background.

    Would process conversions with rate limiting.
    """
    logger.info(f"Processing batch {batch_id} with {len(conversion_ids)} conversions")

    # Process each conversion
    # Would have proper error handling and progress tracking
    for conversion_id in conversion_ids:
        # Process conversion
        # Update status
        pass

    logger.info(f"Batch {batch_id} completed")


@router.get("/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get batch conversion status.

    Shows progress for all conversions in batch.
    """
    # Get all conversions in batch
    result = await db.execute(
        select(ConversionJob).where(
            ConversionJob.batch_id == batch_id,
            ConversionJob.user_id == user_id,
        )
    )
    conversions = result.scalars().all()

    if not conversions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )

    # Calculate status
    completed = sum(1 for c in conversions if c.status == "completed")
    failed = sum(1 for c in conversions if c.status == "failed")
    pending = sum(1 for c in conversions if c.status in ["queued", "processing"])

    total = len(conversions)
    progress = (completed / total * 100) if total > 0 else 0

    return BatchStatusResponse(
        batch_id=batch_id,
        total=total,
        completed=completed,
        failed=failed,
        pending=pending,
        progress_percent=progress,
        conversions=[
            {
                "conversion_id": str(c.id),
                "filename": c.input_data.get("filename", "unknown"),
                "status": c.status,
                "progress": c.progress.progress if c.progress else 0,
            }
            for c in conversions
        ],
    )


@router.get("/{batch_id}/results", response_model=BatchResultResponse)
async def get_batch_results(
    batch_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get batch conversion results.

    Download individual results or all as ZIP.
    """
    # Get all conversions in batch
    result = await db.execute(
        select(ConversionJob).where(
            ConversionJob.batch_id == batch_id,
            ConversionJob.user_id == user_id,
        )
    )
    conversions = result.scalars().all()

    if not conversions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )

    # Build results
    results = []
    successful = 0
    failed = 0

    for conversion in conversions:
        if conversion.status == "completed":
            successful += 1
            results.append(
                {
                    "conversion_id": str(conversion.id),
                    "filename": conversion.input_data.get("filename", "unknown"),
                    "status": "completed",
                    "download_url": f"/api/v1/conversions/{conversion.id}/download",
                }
            )
        else:
            failed += 1
            results.append(
                {
                    "conversion_id": str(conversion.id),
                    "filename": conversion.input_data.get("filename", "unknown"),
                    "status": conversion.status,
                    "error": conversion.error_message
                    if hasattr(conversion, "error_message")
                    else None,
                }
            )

    # Generate ZIP download URL if there are successful conversions
    download_all_url = None
    if successful > 0:
        download_all_url = f"/api/v1/batch/{batch_id}/download-all"

    return BatchResultResponse(
        batch_id=batch_id,
        results=results,
        download_all_url=download_all_url,
        summary={
            "total": len(conversions),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(conversions) * 100) if conversions else 0,
        },
    )


@router.get("/{batch_id}/download-all")
async def download_all_batch(
    batch_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Download all successful conversions as ZIP.

    Creates ZIP archive of all .mcaddon files.
    """
    # Would generate ZIP file with all conversions
    # For now, return placeholder

    return {
        "batch_id": batch_id,
        "message": "ZIP download would start here",
        "filename": f"modporter_batch_{batch_id}.zip",
    }


@router.delete("/{batch_id}")
async def cancel_batch(
    batch_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel batch conversion.

    Stops pending conversions, keeps completed ones.
    """
    # Get all conversions in batch
    result = await db.execute(
        select(ConversionJob).where(
            ConversionJob.batch_id == batch_id,
            ConversionJob.user_id == user_id,
        )
    )
    conversions = result.scalars().all()

    if not conversions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )

    # Cancel pending conversions
    cancelled = 0
    for conversion in conversions:
        if conversion.status in ["queued", "processing"]:
            conversion.status = "cancelled"
            cancelled += 1

    await db.commit()

    return {
        "message": f"Batch cancelled. {cancelled} conversions stopped.",
        "cancelled_count": cancelled,
    }
