"""
Enhanced Batch Conversion API v2

Implements Phase 2.5.4: Batch Conversion Automation
- Batch upload interface with validation
- Intelligent queue management
- Priority-based processing
- Batch progress tracking
- Per-item error handling

Success Criteria:
- 100 mods in <1 hour
- Queue efficiency >90%
- Per-mod tracking accuracy 100%

Issue: REQ-2.13 - Batch Automation
"""

import asyncio
import hashlib
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import redis.asyncio as aioredis

from services.batch_processor import (
    BatchUploadHandler,
    BatchProgressTracker,
    BatchErrorHandler,
    IntelligentQueueManager,
    BatchStatus,
    ItemStatus,
    Priority,
    Batch,
    BatchItem,
    BatchUploadResult,
    ErrorType,
    get_batch_upload_handler,
    get_queue_manager,
    get_progress_tracker,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch/v2", tags=["Batch Conversion v2"])


# ============================================================================
# Request/Response Models
# ============================================================================

class BatchUploadRequest(BaseModel):
    """Request for batch upload."""
    priority: str = Field(default="normal", description="vip, high, normal, low")
    

class BatchUploadResponse(BaseModel):
    """Response for batch upload."""
    batch_id: str
    total_items: int
    valid_items: int
    invalid_items: int
    status: str
    message: str


class BatchItemStatus(BaseModel):
    """Status of individual batch item."""
    item_id: str
    filename: str
    status: str
    progress: float
    priority: int
    error: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class BatchStatusResponseV2(BaseModel):
    """Batch status response v2."""
    batch_id: str
    status: str
    total_items: int
    completed_items: int
    failed_items: int
    queued_items: int
    processing_items: int
    progress: float
    efficiency: Optional[float] = None
    items: List[BatchItemStatus]


class BatchProgressUpdate(BaseModel):
    """WebSocket progress update."""
    batch_id: str
    item_id: str
    progress: float
    status: str
    message: str = ""


class QueueStatsResponse(BaseModel):
    """Queue statistics response."""
    queue_size: int
    cpu_in_use: float
    memory_in_use_mb: int
    concurrent_jobs: int
    max_cpu_slots: int
    max_memory_gb: int
    max_concurrent: int
    efficiency: float


class BatchErrorSummary(BaseModel):
    """Summary of batch errors."""
    batch_id: str
    total_errors: int
    errors_by_type: Dict[str, int]
    failed_items: List[str]
    recovery_rate: float


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/upload", response_model=BatchUploadResponse)
async def upload_batch(
    files: List[UploadFile] = File(...),
    user_id: str = "default_user",
    priority: str = "normal",
):
    """
    Upload batch of mod files for conversion.
    
    - Supports drag-and-drop and multiple file selection
    - Validates file size (max 500MB), type (.jar, .zip, .tar.gz)
    - Detects duplicates by checksum
    - Max batch size: 100 mods
    """
    handler = get_batch_upload_handler()
    
    # Convert UploadFile to dict format
    file_list = []
    for file in files:
        content = await file.read()
        checksum = hashlib.md5(content).hexdigest()
        
        # Save to temp storage
        temp_path = f"/tmp/w-gsd-ex/backend/temp_uploads/{file.filename}"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(content)
        
        file_list.append({
            "filename": file.filename,
            "size": len(content),
            "path": temp_path,
            "checksum": checksum,
        })
    
    # Process batch upload
    try:
        result = await handler.upload_batch(
            files=file_list,
            user_id=user_id,
        )
        
        return BatchUploadResponse(
            batch_id=result.batch_id,
            total_items=result.total_items,
            valid_items=result.valid_items,
            invalid_items=len(result.errors),
            status="pending",
            message=f"Batch uploaded: {result.valid_items} valid, {len(result.errors)} invalid",
        )
    except Exception as e:
        logger.error(f"Batch upload failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{batch_id}/process")
async def process_batch(
    batch_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Start processing a batch.
    
    - Enqueues all items to intelligent queue
    - Applies priority-based scheduling
    - Starts progress tracking
    """
    handler = get_batch_upload_handler()
    queue_manager = get_queue_manager()
    
    # Get batch
    batch = await handler.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Update batch status
    batch.status = BatchStatus.QUEUED
    await handler.update_batch(batch)
    
    # Enqueue all items
    for item in batch.items:
        priority = Priority.NORMAL
        if item.priority >= 100:
            priority = Priority.VIP
        elif item.priority >= 75:
            priority = Priority.HIGH
        elif item.priority >= 25:
            priority = Priority.LOW
        
        await queue_manager.enqueue(item, priority)
    
    # Start queue processing in background
    async def process_item(item: BatchItem) -> Dict[str, Any]:
        # This would call the actual conversion service
        # Simulated for now
        await asyncio.sleep(0.1)  # Simulate processing time
        return {"path": f"/outputs/{item.item_id}.mcaddon"}
    
    background_tasks.add_task(queue_manager.process_queue, process_item)
    
    # Update batch to processing
    batch.status = BatchStatus.PROCESSING
    batch.started_at = datetime.utcnow()
    await handler.update_batch(batch)
    
    return {
        "batch_id": batch_id,
        "status": "processing",
        "message": f"Processing {len(batch.items)} items",
    }


@router.get("/{batch_id}/status", response_model=BatchStatusResponseV2)
async def get_batch_status(batch_id: str):
    """
    Get detailed batch status with per-item tracking.
    
    - Real-time progress for each item
    - Error details per item
    - Queue efficiency metrics
    """
    handler = get_batch_upload_handler()
    tracker = get_progress_tracker()
    queue_manager = get_queue_manager()
    
    # Get batch
    batch = await handler.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Get progress from tracker
    progress = await tracker.get_batch_progress(batch_id)
    
    # Calculate stats
    completed = sum(1 for item in batch.items if item.status == ItemStatus.COMPLETED)
    failed = sum(1 for item in batch.items if item.status == ItemStatus.FAILED)
    queued = sum(1 for item in batch.items if item.status == ItemStatus.QUEUED)
    processing = sum(1 for item in batch.items if item.status == ItemStatus.PROCESSING)
    
    # Calculate efficiency (processing time / total time)
    efficiency = None
    if batch.started_at and completed > 0:
        total_time = (datetime.utcnow() - batch.started_at).total_seconds()
        processing_time = sum(
            (item.completed_at - item.started_at).total_seconds()
            for item in batch.items
            if item.started_at and item.completed_at
        )
        if total_time > 0:
            efficiency = (processing_time / total_time) * 100
    
    return BatchStatusResponseV2(
        batch_id=batch_id,
        status=batch.status.value,
        total_items=len(batch.items),
        completed_items=completed,
        failed_items=failed,
        queued_items=queued,
        processing_items=processing,
        progress=batch.progress,
        efficiency=efficiency,
        items=[
            BatchItemStatus(
                item_id=item.item_id,
                filename=item.filename,
                status=item.status.value,
                progress=item.progress,
                priority=item.priority,
                error={
                    "type": item.error.error_type.value if item.error else None,
                    "message": item.error.message if item.error else None,
                    "recoverable": item.error.recoverable if item.error else None,
                } if item.error else None,
                started_at=item.started_at.isoformat() if item.started_at else None,
                completed_at=item.completed_at.isoformat() if item.completed_at else None,
            )
            for item in batch.items
        ],
    )


@router.get("/{batch_id}/item/{item_id}")
async def get_item_status(batch_id: str, item_id: str):
    """Get status of specific item in batch."""
    handler = get_batch_upload_handler()
    
    batch = await handler.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    item = next((i for i in batch.items if i.item_id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {
        "item_id": item.item_id,
        "filename": item.filename,
        "status": item.status.value,
        "progress": item.progress,
        "priority": item.priority,
        "error": {
            "type": item.error.error_type.value if item.error else None,
            "message": item.error.message if item.error else None,
        } if item.error else None,
        "started_at": item.started_at.isoformat() if item.started_at else None,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        "result_path": item.result_path,
    }


@router.post("/{batch_id}/item/{item_id}/retry")
async def retry_item(batch_id: str, item_id: str):
    """Retry a failed item."""
    handler = get_batch_upload_handler()
    queue_manager = get_queue_manager()
    
    batch = await handler.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    item = next((i for i in batch.items if i.item_id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.status != ItemStatus.FAILED:
        raise HTTPException(status_code=400, detail="Item is not failed")
    
    # Reset and requeue
    item.status = ItemStatus.PENDING
    item.retry_count = 0
    item.error = None
    
    await handler.update_batch(batch)
    await queue_manager.enqueue(item, Priority(item.priority))
    
    return {
        "message": f"Item {item_id} requeued for retry",
        "status": "queued",
    }


@router.delete("/{batch_id}/item/{item_id}")
async def cancel_item(batch_id: str, item_id: str):
    """Cancel a specific item in batch."""
    handler = get_batch_upload_handler()
    
    batch = await handler.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    item = next((i for i in batch.items if i.item_id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.status in [ItemStatus.COMPLETED, ItemStatus.FAILED]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed/failed item")
    
    item.status = ItemStatus.FAILED
    await handler.update_batch(batch)
    
    return {"message": f"Item {item_id} cancelled"}


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_stats():
    """Get queue statistics for monitoring."""
    queue_manager = get_queue_manager()
    stats = queue_manager.get_stats()
    
    # Calculate efficiency
    if stats["concurrent_jobs"] > 0 and stats["queue_size"] > 0:
        efficiency = (stats["concurrent_jobs"] / (stats["concurrent_jobs"] + stats["queue_size"])) * 100
    else:
        efficiency = 100.0
    
    return QueueStatsResponse(
        queue_size=stats["queue_size"],
        cpu_in_use=stats["cpu_in_use"],
        memory_in_use_mb=stats["memory_in_use"],
        concurrent_jobs=stats["concurrent_jobs"],
        max_cpu_slots=stats["max_cpu_slots"],
        max_memory_gb=stats["max_memory_gb"],
        max_concurrent=stats["max_concurrent"],
        efficiency=efficiency,
    )


@router.get("/{batch_id}/errors", response_model=BatchErrorSummary)
async def get_batch_errors(batch_id: str):
    """Get error summary for batch."""
    handler = get_batch_upload_handler()
    
    batch = await handler.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Collect errors
    errors_by_type = {}
    failed_items = []
    recovered = 0
    
    for item in batch.items:
        if item.error:
            failed_items.append(item.item_id)
            error_type = item.error.error_type.value
            errors_by_type[error_type] = errors_by_type.get(error_type, 0) + 1
            
            if not item.error.recoverable:
                recovered += 1
    
    total_errors = len(failed_items)
    recovery_rate = ((total_errors - recovered) / total_errors * 100) if total_errors > 0 else 100.0
    
    return BatchErrorSummary(
        batch_id=batch_id,
        total_errors=total_errors,
        errors_by_type=errors_by_type,
        failed_items=failed_items,
        recovery_rate=recovery_rate,
    )


# ============================================================================
# WebSocket for Real-time Progress
# ============================================================================

@router.websocket("/ws/{batch_id}")
async def websocket_progress(websocket: WebSocket, batch_id: str):
    """
    WebSocket endpoint for real-time batch progress updates.
    
    Streams progress for each item in the batch.
    """
    await websocket.accept()
    
    tracker = get_progress_tracker()
    
    try:
        # Send initial state
        initial_progress = await tracker.get_batch_progress(batch_id)
        await websocket.send_json({
            "type": "initial",
            "data": initial_progress,
        })
        
        # Stream updates
        async for update in tracker.watch_batch(batch_id):
            await websocket.send_json({
                "type": "update",
                "data": update,
            })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for batch {batch_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011)


# ============================================================================
# Batch Processing Simulation (for testing)
# ============================================================================

async def simulate_batch_processing(batch_id: str):
    """
    Simulate batch processing for testing.
    
    This would be replaced by actual conversion service calls.
    """
    handler = get_batch_upload_handler()
    tracker = get_progress_tracker()
    
    batch = await handler.get_batch(batch_id)
    if not batch:
        return
    
    for item in batch.items:
        # Simulate processing
        for progress in range(0, 101, 10):
            item.progress = progress / 100.0
            item.status = ItemStatus.PROCESSING
            
            await tracker.update_progress(
                batch_id=batch_id,
                item_id=item.item_id,
                progress=item.progress,
                status=item.status,
                message=f"Processing {item.filename}...",
            )
            
            await asyncio.sleep(0.1)
        
        # Complete
        item.status = ItemStatus.COMPLETED
        item.progress = 1.0
        item.completed_at = datetime.utcnow()
        
        await tracker.update_progress(
            batch_id=batch_id,
            item_id=item.item_id,
            progress=1.0,
            status=ItemStatus.COMPLETED,
            message="Completed",
        )
    
    # Update batch status
    batch.status = BatchStatus.COMPLETED
    batch.completed_at = datetime.utcnow()
    batch.completed_items = len(batch.items)
    await handler.update_batch(batch)
