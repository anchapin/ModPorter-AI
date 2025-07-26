"""
Feedback API endpoints for conversion job feedback and AI training data.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.base import get_db
from db import crud

router = APIRouter()


class FeedbackRequest(BaseModel):
    job_id: str
    feedback_type: str
    user_id: Optional[str] = None
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    job_id: str
    feedback_type: str
    user_id: Optional[str] = None
    comment: Optional[str] = None
    created_at: str


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Submit feedback for a conversion job."""
    try:
        job_uuid = uuid.UUID(feedback.job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    # Check if job exists
    job = await crud.get_job(db, feedback.job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Conversion job with ID '{feedback.job_id}' not found"
        )
    
    # Create feedback
    db_feedback = await crud.create_feedback(
        db,
        job_id=job_uuid,
        feedback_type=feedback.feedback_type,
        user_id=feedback.user_id,
        comment=feedback.comment
    )
    
    return FeedbackResponse(
        id=str(db_feedback.id),
        job_id=str(db_feedback.job_id),
        feedback_type=db_feedback.feedback_type,
        user_id=db_feedback.user_id,
        comment=db_feedback.comment,
        created_at=db_feedback.created_at.isoformat()
    )


@router.get("/ai/training_data")
async def get_training_data(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get feedback data for AI training."""
    feedback_list = await crud.list_all_feedback(db, skip=skip, limit=limit)
    
    training_data = []
    for feedback in feedback_list:
        training_data.append({
            "id": str(feedback.id),
            "job_id": str(feedback.job_id),
            "feedback_type": feedback.feedback_type,
            "user_id": feedback.user_id,
            "comment": feedback.comment,
            "created_at": feedback.created_at.isoformat()
        })
    
    return training_data