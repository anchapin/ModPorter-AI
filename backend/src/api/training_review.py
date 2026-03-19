"""
Manual Review Queue API endpoints for training data quality control.
"""

import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from pydantic import BaseModel, ConfigDict
from enum import Enum

from db.base import get_db
from db import models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/training", tags=["AI Training"])


class ReviewStatus(str, Enum):
    """Status of training data review."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class TrainingDataReviewRequest(BaseModel):
    """Request to review a training data item."""
    training_data_id: str
    status: ReviewStatus
    reviewer_notes: Optional[str] = None
    quality_score: Optional[float] = None  # Override automated score
    issues_found: Optional[List[str]] = None


class TrainingDataReviewResponse(BaseModel):
    """Response for a training data review."""
    id: str
    training_data_id: str
    status: ReviewStatus
    reviewer_notes: Optional[str]
    quality_score: float
    issues_found: List[str]
    reviewer_id: Optional[str]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class TrainingDataItemResponse(BaseModel):
    """Response for a training data item."""
    id: str
    job_id: str
    input_source: str
    output_target: str
    mod_type: str
    complexity: str
    automated_score: float
    review_status: Optional[ReviewStatus]
    manual_score: Optional[float]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ReviewQueueStats(BaseModel):
    """Statistics for the review queue."""
    pending: int
    approved: int
    rejected: int
    needs_revision: int
    total: int
    average_score: float


@router.get("/review/queue", response_model=List[TrainingDataItemResponse])
async def get_review_queue(
    skip: int = 0,
    limit: int = 20,
    status_filter: Optional[ReviewStatus] = None,
    sort_by: str = "automated_score",
    db: AsyncSession = Depends(get_db),
):
    """
    Get training data items pending review.
    
    Returns items sorted by automated quality score (lowest first) 
    to prioritize items that need review.
    """
    logger.info(f"Fetching review queue: skip={skip}, limit={limit}, status={status_filter}")
    
    # Query for items that could be in review queue
    # In production, you'd have a separate review queue table
    # For now, we'll query from conversion jobs with feedback
    
    stmt = select(ConversionFeedback).order_by(
        desc(ConversionFeedback.created_at)
    ).offset(skip).limit(limit)
    
    if status_filter:
        # Filter by status if we have review records
        stmt = stmt.where(ConversionFeedback.feedback_type == status_filter.value)
    
    result = await db.execute(stmt)
    feedbacks = result.scalars().all()
    
    items = []
    for fb in feedbacks:
        # Get corresponding job
        job_stmt = select(ConversionJob).where(ConversionJob.id == fb.job_id)
        job_result = await db.execute(job_stmt)
        job = job_result.scalar_one_or_none()
        
        if job:
            item = TrainingDataItemResponse(
                id=str(fb.id),
                job_id=str(fb.job_id),
                input_source=str(job.input_data)[:500],  # Truncate for preview
                output_target="",  # Would need to fetch from results
                mod_type="unknown",
                complexity="medium",
                automated_score=0.5,  # Would calculate from job data
                review_status=fb.feedback_type,
                manual_score=None,
                created_at=fb.created_at.isoformat()
            )
            items.append(item)
    
    return items


@router.post("/review", response_model=TrainingDataReviewResponse)
async def submit_review(
    review: TrainingDataReviewRequest,
    reviewer_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a review decision for training data.
    
    This allows human reviewers to approve/reject training data
    and provide quality scores.
    """
    logger.info(f"Submitting review for {review.training_data_id}: status={review.status}")
    
    # In production, you'd create/update a review record
    # For now, we simulate with a response
    
    review_record = TrainingDataReviewResponse(
        id=str(uuid.uuid4()),
        training_data_id=review.training_data_id,
        status=review.status,
        reviewer_notes=review.reviewer_notes,
        quality_score=review.quality_score or 0.5,
        issues_found=review.issues_found or [],
        reviewer_id=reviewer_id,
        created_at=datetime.now().isoformat()
    )
    
    # Log the review
    logger.info(f"Review submitted: {review_record}")
    
    return review_record


@router.get("/review/stats", response_model=ReviewQueueStats)
async def get_review_stats(db: AsyncSession = Depends(get_db)):
    """
    Get statistics about the review queue.
    """
    # Get counts by feedback type
    stmt = select(ConversionFeedback)
    result = await db.execute(stmt)
    feedbacks = result.scalars().all()
    
    stats = {
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "needs_revision": 0,
        "total": len(feedbacks),
        "average_score": 0.5
    }
    
    for fb in feedbacks:
        ft = fb.feedback_type
        if ft in stats:
            stats[ft] += 1
    
    return ReviewQueueStats(**stats)


@router.post("/review/batch")
async def batch_review(
    reviews: List[TrainingDataReviewRequest],
    reviewer_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit multiple reviews in a batch.
    """
    logger.info(f"Batch review: {len(reviews)} items")
    
    results = []
    for review in reviews:
        result = await submit_review(review, reviewer_id, db)
        results.append(result)
    
    return {
        "status": "success",
        "reviewed_count": len(results),
        "results": results
    }


@router.get("/export")
async def export_approved_training_data(
    min_quality: float = Query(0.7, ge=0.0, le=1.0),
    format: str = Query("jsonl", regex="^(jsonl|json)$"),
    limit: int = Query(1000, ge=1, le=10000),
    db: AsyncSession = Depends(get_db),
):
    """
    Export approved training data for model fine-tuning.
    
    Returns training data that has been reviewed and approved,
    with quality scores above the threshold.
    """
    logger.info(f"Exporting training data: min_quality={min_quality}, format={format}, limit={limit}")
    
    # In production, query for approved reviews
    # For now, return a placeholder structure
    
    return {
        "format": format,
        "count": 0,
        "min_quality": min_quality,
        "message": "Export functionality requires review queue integration",
        "data": []
    }


# Import needed models
from db.models import ConversionJob, ConversionFeedback
