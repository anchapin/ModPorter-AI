"""
Task Queue API Endpoints
REST API for managing background tasks.

Issue: #379 - Implement async task queue (Phase 3)
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from services.task_queue import (
    AsyncTaskQueue,
    TaskStatus,
    TaskPriority,
    get_task_queue,
    enqueue_task,
    get_task_status,
    cancel_task,
    get_queue_stats
)

router = APIRouter(prefix="/api/v1/tasks", tags=["task-queue"])


# Request/Response Models
class TaskEnqueueRequest(BaseModel):
    """Request model for enqueuing a task"""
    name: str = Field(..., description="Task name/identifier")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task payload data")
    priority: str = Field(default="normal", description="Task priority: low, normal, high, critical")
    max_retries: Optional[int] = Field(default=None, description="Maximum retry attempts")


class TaskResponse(BaseModel):
    """Response model for task information"""
    id: str
    name: str
    status: str
    priority: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int
    max_retries: int


class QueueStatsResponse(BaseModel):
    """Response model for queue statistics"""
    queues: Dict[str, int]
    total_tasks: int
    by_status: Dict[str, int]


def priority_string_to_enum(priority: str) -> TaskPriority:
    """Convert priority string to TaskPriority enum"""
    priority_map = {
        "low": TaskPriority.LOW,
        "normal": TaskPriority.NORMAL,
        "high": TaskPriority.HIGH,
        "critical": TaskPriority.CRITICAL
    }
    return priority_map.get(priority.lower(), TaskPriority.NORMAL)


# Endpoints
@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(request: TaskEnqueueRequest):
    """
    Enqueue a new task for background processing.
    
    Args:
        request: Task details including name, payload, priority
        
    Returns:
        Created task information
    """
    try:
        priority = priority_string_to_enum(request.priority)
        
        task = await enqueue_task(
            name=request.name,
            payload=request.payload,
            priority=priority
        )
        
        return TaskResponse(
            id=task.id,
            name=task.name,
            status=task.status.value,
            priority=task.priority.value,
            created_at=task.created_at.isoformat(),
            retry_count=task.retry_count,
            max_retries=task.max_retries
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue task: {str(e)}")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """
    Get task status and information.
    
    Args:
        task_id: Task ID
        
    Returns:
        Task information
    """
    task_data = await get_task_status(task_id)
    
    if task_data is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return TaskResponse(
        id=task_data["id"],
        name=task_data["name"],
        status=task_data["status"],
        priority=task_data["priority"],
        created_at=task_data["created_at"],
        started_at=task_data.get("started_at"),
        completed_at=task_data.get("completed_at"),
        result=task_data.get("result"),
        error=task_data.get("error"),
        retry_count=task_data.get("retry_count", 0),
        max_retries=task_data.get("max_retries", 3)
    )


@router.delete("/{task_id}")
async def cancel_task_endpoint(task_id: str):
    """
    Cancel a queued task.
    
    Args:
        task_id: Task ID
        
    Returns:
        Success message
    """
    success = await cancel_task(task_id)
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail=f"Task {task_id} cannot be cancelled (may not exist or already started)"
        )
    
    return {"message": f"Task {task_id} cancelled successfully"}


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks to return")
):
    """
    List tasks, optionally filtered by status.
    
    Args:
        status: Optional status filter
        limit: Maximum number of tasks to return
        
    Returns:
        List of tasks
    """
    try:
        task_status = TaskStatus(status) if status else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    queue = await get_task_queue()
    tasks = await queue.list_tasks(status=task_status, limit=limit)
    
    return [
        TaskResponse(
            id=task["id"],
            name=task["name"],
            status=task["status"],
            priority=task["priority"],
            created_at=task["created_at"],
            started_at=task.get("started_at"),
            completed_at=task.get("completed_at"),
            result=task.get("result"),
            error=task.get("error"),
            retry_count=task.get("retry_count", 0),
            max_retries=task.get("max_retries", 3)
        )
        for task in tasks
    ]


@router.get("/stats/queue", response_model=QueueStatsResponse)
async def get_queue_statistics():
    """
    Get queue statistics including task counts by status and priority.
    
    Returns:
        Queue statistics
    """
    stats = await get_queue_stats()
    
    return QueueStatsResponse(
        queues=stats["queues"],
        total_tasks=stats["total_tasks"],
        by_status=stats["by_status"]
    )
