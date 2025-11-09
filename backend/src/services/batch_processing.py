"""
Batch Processing Service for Large Graph Operations

This service provides efficient batch processing capabilities for knowledge graph
operations, including chunking, parallel processing, and progress tracking.
"""

import logging
import json
import asyncio
import uuid
import time
import threading
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func

from ..db.crud import get_async_session
from ..db.knowledge_graph_crud import (
    KnowledgeNodeCRUD, KnowledgeRelationshipCRUD, ConversionPatternCRUD
)
from ..models import (
    KnowledgeNode, KnowledgeRelationship, ConversionPattern
)

logger = logging.getLogger(__name__)


class BatchOperationType(Enum):
    """Types of batch operations."""
    IMPORT_NODES = "import_nodes"
    IMPORT_RELATIONSHIPS = "import_relationships"
    IMPORT_PATTERNS = "import_patterns"
    EXPORT_GRAPH = "export_graph"
    DELETE_NODES = "delete_nodes"
    DELETE_RELATIONSHIPS = "delete_relationships"
    UPDATE_NODES = "update_nodes"
    UPDATE_RELATIONSHIPS = "update_relationships"
    VALIDATE_GRAPH = "validate_graph"
    CALCULATE_METRICS = "calculate_metrics"
    APPLY_CONVERSIONS = "apply_conversions"


class BatchStatus(Enum):
    """Status of batch operations."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ProcessingMode(Enum):
    """Processing modes for batch operations."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CHUNKED = "chunked"
    STREAMING = "streaming"


@dataclass
class BatchJob:
    """Batch job definition."""
    job_id: str
    operation_type: BatchOperationType
    status: BatchStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    chunk_size: int = 100
    processing_mode: ProcessingMode = ProcessingMode.SEQUENTIAL
    parallel_workers: int = 4
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchProgress:
    """Progress tracking for batch operations."""
    job_id: str
    total_items: int
    processed_items: int
    failed_items: int
    current_chunk: int
    total_chunks: int
    progress_percentage: float
    estimated_remaining_seconds: float
    processing_rate_items_per_second: float
    last_update: datetime


@dataclass
class BatchResult:
    """Result of batch operation."""
    success: bool
    job_id: str
    operation_type: BatchOperationType
    total_processed: int = 0
    total_failed: int = 0
    execution_time_seconds: float = 0.0
    result_data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)


class BatchProcessingService:
    """Batch processing service for large graph operations."""
    
    def __init__(self):
        self.active_jobs: Dict[str, BatchJob] = {}
        self.job_history: List[BatchJob] = []
        self.progress_tracking: Dict[str, BatchProgress] = {}
        self.job_queue: List[str] = []
        
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.lock = threading.RLock()
        
        # Processing limits
        self.max_concurrent_jobs = 5
        self.max_chunk_size = 1000
        self.max_queue_size = 100
        
        # Statistics
        self.total_jobs_processed = 0
        self.total_items_processed = 0
        self.total_processing_time = 0.0
        
        # Start processing thread
        self.processing_thread: Optional[threading.Thread] = None
        self.stop_processing = False
        self._start_processing_thread()
    
    async def submit_batch_job(
        self,
        operation_type: BatchOperationType,
        parameters: Dict[str, Any],
        processing_mode: ProcessingMode = ProcessingMode.SEQUENTIAL,
        chunk_size: int = 100,
        parallel_workers: int = 4,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Submit a batch job for processing.
        
        Args:
            operation_type: Type of batch operation
            parameters: Parameters for the operation
            processing_mode: How to process the batch
            chunk_size: Size of chunks for chunked processing
            parallel_workers: Number of parallel workers
            db: Database session
        
        Returns:
            Job submission result
        """
        try:
            job_id = str(uuid.uuid4())
            
            # Estimate total items
            total_items = await self._estimate_total_items(operation_type, parameters, db)
            
            # Create batch job
            job = BatchJob(
                job_id=job_id,
                operation_type=operation_type,
                status=BatchStatus.PENDING,
                created_at=datetime.utcnow(),
                total_items=total_items,
                chunk_size=min(chunk_size, self.max_chunk_size),
                processing_mode=processing_mode,
                parallel_workers=parallel_workers,
                parameters=parameters,
                metadata={
                    "queued_at": datetime.utcnow().isoformat(),
                    "estimated_duration": await self._estimate_duration(operation_type, total_items)
                }
            )
            
            with self.lock:
                # Check queue size
                if len(self.job_queue) >= self.max_queue_size:
                    return {
                        "success": False,
                        "error": "Job queue is full. Please try again later."
                    }
                
                # Check concurrent jobs
                running_jobs = sum(
                    1 for j in self.active_jobs.values()
                    if j.status in [BatchStatus.RUNNING, BatchStatus.PENDING]
                )
                
                if running_jobs >= self.max_concurrent_jobs:
                    self.job_queue.append(job_id)
                else:
                    # Start immediately
                    job.status = BatchStatus.RUNNING
                    job.started_at = datetime.utcnow()
                
                self.active_jobs[job_id] = job
                
                # Initialize progress tracking
                self.progress_tracking[job_id] = BatchProgress(
                    job_id=job_id,
                    total_items=total_items,
                    processed_items=0,
                    failed_items=0,
                    current_chunk=0,
                    total_chunks=max(1, total_items // job.chunk_size),
                    progress_percentage=0.0,
                    estimated_remaining_seconds=0.0,
                    processing_rate_items_per_second=0.0,
                    last_update=datetime.utcnow()
                )
            
            return {
                "success": True,
                "job_id": job_id,
                "operation_type": operation_type.value,
                "estimated_total_items": total_items,
                "processing_mode": processing_mode.value,
                "chunk_size": job.chunk_size,
                "parallel_workers": parallel_workers,
                "status": job.status.value,
                "queue_position": len(self.job_queue) if job.status == BatchStatus.PENDING else 0,
                "message": "Batch job submitted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error submitting batch job: {e}")
            return {
                "success": False,
                "error": f"Job submission failed: {str(e)}"
            }
    
    async def get_job_status(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Get status and progress of a batch job.
        
        Args:
            job_id: ID of the job
        
        Returns:
            Job status and progress information
        """
        try:
            with self.lock:
                if job_id not in self.active_jobs and job_id not in [j.job_id for j in self.job_history]:
                    return {
                        "success": False,
                        "error": "Job not found"
                    }
                
                # Get job (check active first, then history)
                job = self.active_jobs.get(job_id)
                if not job:
                    for historical_job in self.job_history:
                        if historical_job.job_id == job_id:
                            job = historical_job
                            break
                
                if not job:
                    return {
                        "success": False,
                        "error": "Job not found"
                    }
                
                # Get progress
                progress = self.progress_tracking.get(job_id)
                
                # Calculate progress percentage
                progress_percentage = 0.0
                if job.total_items > 0:
                    progress_percentage = (job.processed_items / job.total_items) * 100
                
                # Calculate processing rate and estimated remaining
                processing_rate = 0.0
                estimated_remaining = 0.0
                
                if progress and job.started_at:
                    elapsed_time = (datetime.utcnow() - job.started_at).total_seconds()
                    if elapsed_time > 0:
                        processing_rate = job.processed_items / elapsed_time
                        remaining_items = job.total_items - job.processed_items
                        estimated_remaining = remaining_items / processing_rate if processing_rate > 0 else 0
                
                return {
                    "success": True,
                    "job_id": job_id,
                    "operation_type": job.operation_type.value,
                    "status": job.status.value,
                    "progress": {
                        "total_items": job.total_items,
                        "processed_items": job.processed_items,
                        "failed_items": job.failed_items,
                        "progress_percentage": progress_percentage,
                        "processing_rate_items_per_second": processing_rate,
                        "estimated_remaining_seconds": estimated_remaining,
                        "current_chunk": progress.current_chunk if progress else 0,
                        "total_chunks": progress.total_chunks if progress else 0
                    },
                    "timing": {
                        "created_at": job.created_at.isoformat(),
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                        "elapsed_seconds": (
                            (datetime.utcnow() - job.started_at).total_seconds()
                            if job.started_at else 0
                        )
                    },
                    "parameters": job.parameters,
                    "result": job.result if job.status == BatchStatus.COMPLETED else None,
                    "error_message": job.error_message,
                    "metadata": job.metadata
                }
                
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {
                "success": False,
                "error": f"Failed to get job status: {str(e)}"
            }
    
    async def cancel_job(
        self,
        job_id: str,
        reason: str = "User requested cancellation"
    ) -> Dict[str, Any]:
        """
        Cancel a running batch job.
        
        Args:
            job_id: ID of the job to cancel
            reason: Reason for cancellation
        
        Returns:
            Cancellation result
        """
        try:
            with self.lock:
                if job_id not in self.active_jobs:
                    return {
                        "success": False,
                        "error": "Job not found or already completed"
                    }
                
                job = self.active_jobs[job_id]
                
                if job.status not in [BatchStatus.PENDING, BatchStatus.RUNNING]:
                    return {
                        "success": False,
                        "error": f"Cannot cancel job in status: {job.status.value}"
                    }
                
                # Update job status
                job.status = BatchStatus.CANCELLED
                job.completed_at = datetime.utcnow()
                job.error_message = f"Cancelled: {reason}"
                
                # Remove from active jobs
                del self.active_jobs[job_id]
                
                # Add to history
                self.job_history.append(job)
                
                # Remove progress tracking
                if job_id in self.progress_tracking:
                    del self.progress_tracking[job_id]
                
                return {
                    "success": True,
                    "job_id": job_id,
                    "cancelled_at": job.completed_at.isoformat(),
                    "reason": reason,
                    "processed_items": job.processed_items,
                    "message": "Job cancelled successfully"
                }
                
        except Exception as e:
            logger.error(f"Error cancelling job: {e}")
            return {
                "success": False,
                "error": f"Job cancellation failed: {str(e)}"
            }
    
    async def pause_job(
        self,
        job_id: str,
        reason: str = "User requested pause"
    ) -> Dict[str, Any]:
        """
        Pause a running batch job.
        
        Args:
            job_id: ID of the job to pause
            reason: Reason for pause
        
        Returns:
            Pause result
        """
        try:
            with self.lock:
                if job_id not in self.active_jobs:
                    return {
                        "success": False,
                        "error": "Job not found or already completed"
                    }
                
                job = self.active_jobs[job_id]
                
                if job.status != BatchStatus.RUNNING:
                    return {
                        "success": False,
                        "error": f"Cannot pause job in status: {job.status.value}"
                    }
                
                # Update job status
                job.status = BatchStatus.PAUSED
                job.metadata["paused_at"] = datetime.utcnow().isoformat()
                job.metadata["pause_reason"] = reason
                
                return {
                    "success": True,
                    "job_id": job_id,
                    "paused_at": job.metadata["paused_at"],
                    "reason": reason,
                    "processed_items": job.processed_items,
                    "message": "Job paused successfully"
                }
                
        except Exception as e:
            logger.error(f"Error pausing job: {e}")
            return {
                "success": False,
                "error": f"Job pause failed: {str(e)}"
            }
    
    async def resume_job(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Resume a paused batch job.
        
        Args:
            job_id: ID of the job to resume
        
        Returns:
            Resume result
        """
        try:
            with self.lock:
                if job_id not in self.active_jobs:
                    return {
                        "success": False,
                        "error": "Job not found or already completed"
                    }
                
                job = self.active_jobs[job_id]
                
                if job.status != BatchStatus.PAUSED:
                    return {
                        "success": False,
                        "error": f"Cannot resume job in status: {job.status.value}"
                    }
                
                # Update job status
                job.status = BatchStatus.RUNNING
                
                # Adjust timing
                if "paused_at" in job.metadata:
                    paused_at = datetime.fromisoformat(job.metadata["paused_at"])
                    pause_duration = datetime.utcnow() - paused_at
                    if job.started_at:
                        job.started_at += pause_duration
                
                return {
                    "success": True,
                    "job_id": job_id,
                    "resumed_at": datetime.utcnow().isoformat(),
                    "processed_items": job.processed_items,
                    "message": "Job resumed successfully"
                }
                
        except Exception as e:
            logger.error(f"Error resuming job: {e}")
            return {
                "success": False,
                "error": f"Job resume failed: {str(e)}"
            }
    
    async def get_active_jobs(self) -> Dict[str, Any]:
        """Get list of all active jobs."""
        try:
            with self.lock:
                active_jobs = []
                
                for job_id, job in self.active_jobs.items():
                    progress = self.progress_tracking.get(job_id)
                    
                    # Calculate progress percentage
                    progress_percentage = 0.0
                    if job.total_items > 0:
                        progress_percentage = (job.processed_items / job.total_items) * 100
                    
                    active_jobs.append({
                        "job_id": job_id,
                        "operation_type": job.operation_type.value,
                        "status": job.status.value,
                        "total_items": job.total_items,
                        "processed_items": job.processed_items,
                        "failed_items": job.failed_items,
                        "progress_percentage": progress_percentage,
                        "processing_mode": job.processing_mode.value,
                        "parallel_workers": job.parallel_workers,
                        "created_at": job.created_at.isoformat(),
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "current_chunk": progress.current_chunk if progress else 0,
                        "total_chunks": progress.total_chunks if progress else 0
                    })
                
                # Sort by creation time (newest first)
                active_jobs.sort(key=lambda x: x["created_at"], reverse=True)
                
                return {
                    "success": True,
                    "active_jobs": active_jobs,
                    "total_active": len(active_jobs),
                    "queue_size": len(self.job_queue),
                    "max_concurrent_jobs": self.max_concurrent_jobs,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting active jobs: {e}")
            return {
                "success": False,
                "error": f"Failed to get active jobs: {str(e)}"
            }
    
    async def get_job_history(
        self,
        limit: int = 50,
        operation_type: Optional[BatchOperationType] = None
    ) -> Dict[str, Any]:
        """Get history of completed jobs."""
        try:
            with self.lock:
                history = self.job_history.copy()
                
                # Filter by operation type if specified
                if operation_type:
                    history = [
                        job for job in history
                        if job.operation_type == operation_type
                    ]
                
                # Sort by completion time (newest first)
                history.sort(key=lambda x: x.completed_at or x.created_at, reverse=True)
                
                # Apply limit
                history = history[:limit]
                
                # Format for response
                formatted_history = []
                for job in history:
                    execution_time = 0.0
                    if job.started_at and job.completed_at:
                        execution_time = (job.completed_at - job.started_at).total_seconds()
                    
                    formatted_history.append({
                        "job_id": job.job_id,
                        "operation_type": job.operation_type.value,
                        "status": job.status.value,
                        "total_items": job.total_items,
                        "processed_items": job.processed_items,
                        "failed_items": job.failed_items,
                        "success_rate": (
                            (job.processed_items / job.total_items) * 100
                            if job.total_items > 0 else 0
                        ),
                        "execution_time_seconds": execution_time,
                        "processing_mode": job.processing_mode.value,
                        "created_at": job.created_at.isoformat(),
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                        "error_message": job.error_message,
                        "has_result": bool(job.result)
                    })
                
                return {
                    "success": True,
                    "job_history": formatted_history,
                    "total_history": len(formatted_history),
                    "filter_operation_type": operation_type.value if operation_type else None,
                    "limit_applied": limit,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting job history: {e}")
            return {
                "success": False,
                "error": f"Failed to get job history: {str(e)}"
            }
    
    # Private Helper Methods
    
    def _start_processing_thread(self):
        """Start the background processing thread."""
        try:
            def process_queue():
                while not self.stop_processing:
                    try:
                        with self.lock:
                            # Check for queued jobs
                            if self.job_queue and len(self.active_jobs) < self.max_concurrent_jobs:
                                job_id = self.job_queue.pop(0)
                                
                                if job_id in self.active_jobs:
                                    job = self.active_jobs[job_id]
                                    job.status = BatchStatus.RUNNING
                                    job.started_at = datetime.utcnow()
                                    
                                    # Start job processing
                                    asyncio.create_task(self._process_job(job_id))
                        
                        # Sleep before next check
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error in processing thread: {e}")
                        time.sleep(1)
            
            self.processing_thread = threading.Thread(target=process_queue, daemon=True)
            self.processing_thread.start()
            
        except Exception as e:
            logger.error(f"Error starting processing thread: {e}")
    
    async def _process_job(self, job_id: str):
        """Process a single batch job."""
        try:
            job = self.active_jobs.get(job_id)
            if not job:
                return
            
            start_time = time.time()
            
            # Process based on operation type
            if job.operation_type == BatchOperationType.IMPORT_NODES:
                result = await self._process_import_nodes(job)
            elif job.operation_type == BatchOperationType.IMPORT_RELATIONSHIPS:
                result = await self._process_import_relationships(job)
            elif job.operation_type == BatchOperationType.IMPORT_PATTERNS:
                result = await self._process_import_patterns(job)
            elif job.operation_type == BatchOperationType.EXPORT_GRAPH:
                result = await self._process_export_graph(job)
            elif job.operation_type == BatchOperationType.DELETE_NODES:
                result = await self._process_delete_nodes(job)
            elif job.operation_type == BatchOperationType.DELETE_RELATIONSHIPS:
                result = await self._process_delete_relationships(job)
            elif job.operation_type == BatchOperationType.UPDATE_NODES:
                result = await self._process_update_nodes(job)
            elif job.operation_type == BatchOperationType.VALIDATE_GRAPH:
                result = await self._process_validate_graph(job)
            else:
                result = BatchResult(
                    success=False,
                    job_id=job_id,
                    operation_type=job.operation_type,
                    error_message=f"Unsupported operation type: {job.operation_type.value}"
                )
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Update job with result
            with self.lock:
                if job_id in self.active_jobs:
                    job = self.active_jobs[job_id]
                    job.status = BatchStatus.COMPLETED if result.success else BatchStatus.FAILED
                    job.completed_at = datetime.utcnow()
                    job.processed_items = result.total_processed
                    job.failed_items = result.total_failed
                    job.result = result.result_data
                    job.error_message = result.error_message if not result.success else None
                    job.metadata["execution_time_seconds"] = execution_time
                    
                    # Move to history
                    self.job_history.append(job)
                    del self.active_jobs[job_id]
                    
                    # Update statistics
                    self.total_jobs_processed += 1
                    self.total_items_processed += result.total_processed
                    self.total_processing_time += execution_time
                    
                    # Remove progress tracking
                    if job_id in self.progress_tracking:
                        del self.progress_tracking[job_id]
                    
                    # Process next job in queue
                    if self.job_queue and len(self.active_jobs) < self.max_concurrent_jobs:
                        next_job_id = self.job_queue.pop(0)
                        if next_job_id in self.active_jobs:
                            next_job = self.active_jobs[next_job_id]
                            next_job.status = BatchStatus.RUNNING
                            next_job.started_at = datetime.utcnow()
                            asyncio.create_task(self._process_job(next_job_id))
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            
            # Update job as failed
            with self.lock:
                if job_id in self.active_jobs:
                    job = self.active_jobs[job_id]
                    job.status = BatchStatus.FAILED
                    job.completed_at = datetime.utcnow()
                    job.error_message = str(e)
                    
                    # Move to history
                    self.job_history.append(job)
                    del self.active_jobs[job_id]
                    
                    # Remove progress tracking
                    if job_id in self.progress_tracking:
                        del self.progress_tracking[job_id]
    
    async def _process_import_nodes(self, job: BatchJob) -> BatchResult:
        """Process import nodes batch job."""
        try:
            async with get_async_session() as db:
                nodes_data = job.parameters.get("nodes", [])
                if not nodes_data:
                    return BatchResult(
                        success=False,
                        job_id=job.job_id,
                        operation_type=job.operation_type,
                        error_message="No nodes data provided"
                    )
                
                total_nodes = len(nodes_data)
                processed_nodes = 0
                failed_nodes = 0
                errors = []
                
                # Process in chunks based on mode
                if job.processing_mode == ProcessingMode.CHUNKED:
                    chunks = [
                        nodes_data[i:i + job.chunk_size]
                        for i in range(0, len(nodes_data), job.chunk_size)
                    ]
                else:
                    chunks = [nodes_data]
                
                for chunk_idx, chunk in enumerate(chunks):
                    if job.status == BatchStatus.CANCELLED:
                        break
                    
                    # Process chunk
                    chunk_result = await self._process_nodes_chunk(chunk, db)
                    
                    processed_nodes += chunk_result["processed"]
                    failed_nodes += chunk_result["failed"]
                    errors.extend(chunk_result["errors"])
                    
                    # Update progress
                    with self.lock:
                        if job.job_id in self.progress_tracking:
                            progress = self.progress_tracking[job.job_id]
                            progress.processed_items = processed_nodes
                            progress.failed_items = failed_nodes
                            progress.current_chunk = chunk_idx + 1
                            progress.progress_percentage = (processed_nodes / total_nodes) * 100
                            progress.last_update = datetime.utcnow()
                        
                        if job.job_id in self.active_jobs:
                            job.processed_items = processed_nodes
                            job.failed_items = failed_nodes
                
                return BatchResult(
                    success=failed_nodes == 0,
                    job_id=job.job_id,
                    operation_type=job.operation_type,
                    total_processed=processed_nodes,
                    total_failed=failed_nodes,
                    errors=errors,
                    result_data={
                        "imported_nodes": processed_nodes,
                        "failed_nodes": failed_nodes,
                        "total_nodes": total_nodes
                    },
                    statistics={
                        "processing_mode": job.processing_mode.value,
                        "chunk_size": job.chunk_size,
                        "chunks_processed": len(chunks)
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in import nodes: {e}")
            return BatchResult(
                success=False,
                job_id=job.job_id,
                operation_type=job.operation_type,
                error_message=str(e)
            )
    
    async def _process_nodes_chunk(self, nodes_chunk: List[Dict[str, Any]], db: AsyncSession) -> Dict[str, Any]:
        """Process a chunk of nodes."""
        try:
            processed = 0
            failed = 0
            errors = []
            
            for node_data in nodes_chunk:
                try:
                    # Create node
                    await KnowledgeNodeCRUD.create(db, node_data)
                    processed += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"Failed to create node {node_data.get('id', 'unknown')}: {str(e)}")
            
            await db.commit()
            
            return {
                "processed": processed,
                "failed": failed,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error processing nodes chunk: {e}")
            return {
                "processed": 0,
                "failed": len(nodes_chunk),
                "errors": [f"Chunk processing failed: {str(e)}"]
            }
    
    async def _estimate_total_items(
        self,
        operation_type: BatchOperationType,
        parameters: Dict[str, Any],
        db: AsyncSession = None
    ) -> int:
        """Estimate total items for a batch operation."""
        try:
            if operation_type in [BatchOperationType.IMPORT_NODES, BatchOperationType.IMPORT_RELATIONSHIPS, BatchOperationType.IMPORT_PATTERNS]:
                # For imports, count the provided data
                if operation_type == BatchOperationType.IMPORT_NODES:
                    return len(parameters.get("nodes", []))
                elif operation_type == BatchOperationType.IMPORT_RELATIONSHIPS:
                    return len(parameters.get("relationships", []))
                elif operation_type == BatchOperationType.IMPORT_PATTERNS:
                    return len(parameters.get("patterns", []))
            
            elif operation_type in [BatchOperationType.DELETE_NODES, BatchOperationType.DELETE_RELATIONSHIPS]:
                # For deletes, count matching items
                if db:
                    if operation_type == BatchOperationType.DELETE_NODES:
                        filters = parameters.get("filters", {})
                        nodes = await KnowledgeNodeCRUD.search(db, "", limit=1, **filters)
                        # This would need proper count implementation
                        return 1000  # Placeholder
                    elif operation_type == BatchOperationType.DELETE_RELATIONSHIPS:
                        filters = parameters.get("filters", {})
                        # Count relationships
                        return 500  # Placeholder
            
            return 100  # Default estimation
            
        except Exception as e:
            logger.error(f"Error estimating total items: {e}")
            return 100
    
    async def _estimate_duration(
        self,
        operation_type: BatchOperationType,
        total_items: int
    ) -> float:
        """Estimate execution duration in seconds."""
        try:
            # Base rates (items per second) - these would be calibrated from historical data
            rates = {
                BatchOperationType.IMPORT_NODES: 50.0,
                BatchOperationType.IMPORT_RELATIONSHIPS: 100.0,
                BatchOperationType.IMPORT_PATTERNS: 25.0,
                BatchOperationType.DELETE_NODES: 200.0,
                BatchOperationType.DELETE_RELATIONSHIPS: 300.0,
                BatchOperationType.UPDATE_NODES: 30.0,
                BatchOperationType.VALIDATE_GRAPH: 75.0,
                BatchOperationType.EXPORT_GRAPH: 150.0
            }
            
            rate = rates.get(operation_type, 50.0)
            return total_items / rate if rate > 0 else 60.0
            
        except Exception:
            return 60.0  # Default 1 minute


# Singleton instance
batch_processing_service = BatchProcessingService()
