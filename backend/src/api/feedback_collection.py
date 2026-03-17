"""
Feedback API Endpoints for ModPorter AI

Collect and manage user feedback on conversions.
"""

import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from db.base import get_db
from db.models import ConversionJob
from services.analytics_service import get_analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


class FeedbackSubmitRequest(BaseModel):
    """Feedback submission request."""

    conversion_id: str
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    feedback_type: str = Field(
        ..., description="Type: conversion_quality, bug_report, feature_request"
    )
    comment: Optional[str] = Field(None, max_length=2000)
    specific_issues: Optional[List[str]] = None
    would_recommend: Optional[bool] = None


class FeedbackSubmitResponse(BaseModel):
    """Feedback submission response."""

    message: str
    feedback_id: str
    thank_you: bool


class ConversionRatingRequest(BaseModel):
    """Quick conversion rating."""

    conversion_id: str
    rating: int = Field(..., ge=1, le=5)
    would_use_again: bool = True


class BugReportRequest(BaseModel):
    """Bug report submission."""

    conversion_id: Optional[str] = None
    title: str
    description: str
    severity: str = Field(..., description="low, medium, high, critical")
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    attachments: Optional[List[str]] = None


class FeatureRequestRequest(BaseModel):
    """Feature request submission."""

    title: str
    description: str
    use_case: str
    priority: str = Field(default="medium", description="low, medium, high")
    similar_tools: Optional[str] = None


@router.post("/submit", response_model=FeedbackSubmitResponse)
async def submit_feedback(
    request: FeedbackSubmitRequest,
    user_id: str,  # From authentication
    db: AsyncSession = Depends(get_db),
):
    """
    Submit feedback for a conversion.

    - Rating (1-5 stars)
    - Feedback type
    - Optional comment
    - Specific issues list
    """
    # Verify conversion exists and belongs to user
    result = await db.execute(
        select(ConversionJob).where(
            ConversionJob.id == request.conversion_id,
            ConversionJob.user_id == user_id,
        )
    )
    conversion = result.scalar_one_or_none()

    if not conversion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversion not found",
        )

    # Create feedback record (would be stored in database)
    feedback_id = f"feedback_{request.conversion_id}_{datetime.utcnow().timestamp()}"

    # Track analytics
    analytics = get_analytics_service()
    analytics.track_feedback_submitted(
        user_id=user_id,
        conversion_id=request.conversion_id,
        rating=request.rating,
        feedback_type=request.feedback_type,
    )

    logger.info(
        f"Feedback received from user {user_id}: {request.rating}/5 for {request.conversion_id}"
    )

    return FeedbackSubmitResponse(
        message="Thank you for your feedback!",
        feedback_id=feedback_id,
        thank_you=True,
    )


@router.post("/rate-conversion", response_model=dict)
async def rate_conversion(
    request: ConversionRatingRequest,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Quick conversion rating (1-5 stars).

    Simple one-click rating after conversion.
    """
    # Verify conversion
    result = await db.execute(
        select(ConversionJob).where(
            ConversionJob.id == request.conversion_id,
            ConversionJob.user_id == user_id,
        )
    )
    conversion = result.scalar_one_or_none()

    if not conversion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversion not found",
        )

    # Track analytics
    analytics = get_analytics_service()
    analytics.track_feedback_submitted(
        user_id=user_id,
        conversion_id=request.conversion_id,
        rating=request.rating,
        feedback_type="conversion_rating",
    )

    return {
        "message": "Thanks for rating!",
        "rating": request.rating,
        "would_use_again": request.would_use_again,
    }


@router.post("/bug-report", response_model=dict)
async def submit_bug_report(
    request: BugReportRequest,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a bug report.

    - Title and description
    - Severity level
    - Steps to reproduce
    - Expected vs actual behavior
    """
    # Create bug report (would be stored in database)
    bug_id = f"bug_{datetime.utcnow().timestamp()}"

    logger.warning(f"Bug report from user {user_id}: {request.title} ({request.severity})")

    # For critical bugs, notify team immediately
    if request.severity == "critical":
        # Would send Slack/email notification to dev team
        logger.critical(f"CRITICAL BUG: {request.title} - {request.description}")

    return {
        "message": "Bug report submitted. Thank you!",
        "bug_id": bug_id,
        "severity": request.severity,
        "expected_response_time": (
            "24-48 hours" if request.severity in ["high", "critical"] else "3-5 days"
        ),
    }


@router.post("/feature-request", response_model=dict)
async def submit_feature_request(
    request: FeatureRequestRequest,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a feature request.

    - Title and description
    - Use case
    - Priority suggestion
    - Similar tools (if any)
    """
    # Create feature request (would be stored in database)
    feature_id = f"feature_{datetime.utcnow().timestamp()}"

    logger.info(f"Feature request from user {user_id}: {request.title}")

    return {
        "message": "Feature request submitted. Thanks for the suggestion!",
        "feature_id": feature_id,
        "title": request.title,
        "next_steps": "Our team will review your request. You'll be notified if we implement it.",
    }


@router.get("/my-feedback", response_model=list)
async def get_my_feedback(
    user_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's feedback history.

    Returns list of feedback submissions with status.
    """
    # Would query database for user's feedback
    # For now, return empty list
    return []


@router.get("/conversion/{conversion_id}/feedback", response_model=dict)
async def get_conversion_feedback(
    conversion_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get feedback status for a specific conversion.

    Returns feedback if submitted, or indicates no feedback yet.
    """
    # Verify conversion belongs to user
    result = await db.execute(
        select(ConversionJob).where(
            ConversionJob.id == conversion_id,
            ConversionJob.user_id == user_id,
        )
    )
    conversion = result.scalar_one_or_none()

    if not conversion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversion not found",
        )

    # Would query for feedback on this conversion
    return {
        "conversion_id": conversion_id,
        "has_feedback": False,  # Would be actual status
        "can_submit": True,
    }
