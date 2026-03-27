"""
Knowledge base API endpoints.

Provides endpoints for pattern submission, review, voting, and library access.
"""

import logging
import sys
import os
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db import crud
from db.models import PatternSubmission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])


# ============================================================================
# Pydantic Models
# ============================================================================


class PatternSubmitRequest(BaseModel):
    """Request model for pattern submission."""

    java_pattern: str = Field(..., description="Java code example")
    bedrock_pattern: str = Field(..., description="Bedrock code example (JSON or JavaScript)")
    description: str = Field(..., description="Pattern description (min 20 characters)", min_length=20)
    contributor_id: str = Field(..., description="User submitting the pattern")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    category: str = Field(..., description="Pattern category (item, block, entity, etc.)")


class PatternSubmissionResponse(BaseModel):
    """Response model for pattern submission."""

    id: str
    java_pattern: str
    bedrock_pattern: str
    description: str
    contributor_id: str
    status: str
    created_at: str
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[str] = None
    upvotes: int
    downvotes: int
    tags: List[str]
    category: str

    @classmethod
    def from_orm(cls, submission: PatternSubmission) -> "PatternSubmissionResponse":
        """Convert ORM model to Pydantic model."""
        return cls(
            id=str(submission.id),
            java_pattern=submission.java_pattern,
            bedrock_pattern=submission.bedrock_pattern,
            description=submission.description,
            contributor_id=submission.contributor_id,
            status=submission.status,
            created_at=submission.created_at.isoformat(),
            reviewed_by=submission.reviewed_by,
            review_notes=submission.review_notes,
            reviewed_at=submission.reviewed_at.isoformat() if submission.reviewed_at else None,
            upvotes=submission.upvotes,
            downvotes=submission.downvotes,
            tags=submission.tags or [],
            category=submission.category,
        )


class PatternReviewRequest(BaseModel):
    """Request model for pattern review."""

    approved: bool = Field(..., description="Whether to approve the pattern")
    notes: Optional[str] = Field(None, description="Optional review notes")


class PatternVoteRequest(BaseModel):
    """Request model for pattern voting."""

    upvote: bool = Field(..., description="True for upvote, False for downvote")


class ConversionPatternResponse(BaseModel):
    """Response model for conversion pattern."""

    id: str
    name: str
    description: str
    java_example: str
    bedrock_example: str
    category: str
    tags: List[str]
    complexity: str
    success_rate: float


# ============================================================================
# AI Engine Integration
# ============================================================================


def _get_community_manager():
    """Get CommunityPatternManager from AI engine."""
    ai_engine_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "ai-engine",
    )
    if ai_engine_path not in sys.path:
        sys.path.insert(0, ai_engine_path)

    from knowledge.community import CommunityPatternManager
    return CommunityPatternManager()


def _get_pattern_library():
    """Get PatternLibrary from AI engine."""
    ai_engine_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "ai-engine",
    )
    if ai_engine_path not in sys.path:
        sys.path.insert(0, ai_engine_path)

    from knowledge.patterns import PatternLibrary
    return PatternLibrary()


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/patterns/submit",
    response_model=PatternSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_pattern(
    request: PatternSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a new pattern for review.

    Validates the pattern and creates a pending submission.
    """
    try:
        # Get community manager
        manager = _get_community_manager()

        # Validate and create submission
        submission = await manager.submit_pattern(
            java_pattern=request.java_pattern,
            bedrock_pattern=request.bedrock_pattern,
            description=request.description,
            contributor_id=request.contributor_id,
            tags=request.tags,
            category=request.category,
        )

        # Also store in database
        db_submission = await crud.create_pattern_submission(
            db=db,
            java_pattern=request.java_pattern,
            bedrock_pattern=request.bedrock_pattern,
            description=request.description,
            contributor_id=request.contributor_id,
            tags=request.tags,
            category=request.category,
        )

        logger.info(
            f"Pattern submitted by {request.contributor_id}: "
            f"category={request.category}, id={db_submission.id}"
        )

        return PatternSubmissionResponse.from_orm(db_submission)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error submitting pattern: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit pattern: {str(e)}",
        )


@router.get(
    "/patterns/pending",
    response_model=List[PatternSubmissionResponse],
)
async def get_pending_submissions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Get pending pattern submissions for review.

    Returns submissions ordered by created_at DESC.
    """
    try:
        submissions = await crud.get_pending_submissions(db, limit=limit)
        return [
            PatternSubmissionResponse.from_orm(submission)
            for submission in submissions
        ]
    except Exception as e:
        logger.error(f"Error getting pending submissions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending submissions: {str(e)}",
        )


@router.post(
    "/patterns/{submission_id}/review",
    response_model=PatternSubmissionResponse,
)
async def review_pattern(
    submission_id: str,
    request: PatternReviewRequest,
    reviewer_id: str = Field(..., description="Reviewer user ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Review a pattern submission.

    Approves or rejects the pattern and updates the library if approved.
    """
    try:
        # Get community manager
        manager = _get_community_manager()

        # Update in manager (adds to library if approved)
        await manager.review_pattern(
            submission_id=submission_id,
            reviewer_id=reviewer_id,
            approved=request.approved,
            notes=request.notes,
        )

        # Update in database
        status = "approved" if request.approved else "rejected"
        db_submission = await crud.update_pattern_submission_status(
            db=db,
            submission_id=submission_id,
            status=status,
            reviewed_by=reviewer_id,
            notes=request.notes,
        )

        logger.info(
            f"Pattern {submission_id} {status} by {reviewer_id}"
        )

        return PatternSubmissionResponse.from_orm(db_submission)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error reviewing pattern: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review pattern: {str(e)}",
        )


@router.post(
    "/patterns/{submission_id}/vote",
    response_model=PatternSubmissionResponse,
)
async def vote_on_pattern(
    submission_id: str,
    request: PatternVoteRequest,
    user_id: str = Field(..., description="User voting on the pattern"),
    db: AsyncSession = Depends(get_db),
):
    """
    Vote on a pattern submission.

    Records an upvote or downvote.
    """
    try:
        # Get community manager
        manager = _get_community_manager()

        # Update in manager
        await manager.vote_on_pattern(
            submission_id=submission_id,
            user_id=user_id,
            upvote=request.upvote,
        )

        # Update in database
        db_submission = await crud.vote_on_pattern(
            db=db,
            submission_id=submission_id,
            upvote=request.upvote,
        )

        logger.info(
            f"User {user_id} {'upvoted' if request.upvote else 'downvoted'} "
            f"pattern {submission_id}"
        )

        return PatternSubmissionResponse.from_orm(db_submission)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error voting on pattern: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to vote on pattern: {str(e)}",
        )


@router.get(
    "/patterns/library",
    response_model=List[ConversionPatternResponse],
)
async def get_pattern_library(
    category: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    Get approved patterns from the library.

    Supports filtering by category and tags.
    """
    try:
        # Get pattern library
        library = _get_pattern_library()

        # Parse tags if provided
        tag_list = tags.split(",") if tags else None

        # Search library
        patterns = library.search(
            query="",  # Empty query returns all
            category=category,
            tags=tag_list,
            limit=limit,
        )

        # Convert to response format
        return [
            ConversionPatternResponse(
                id=pattern.id,
                name=pattern.name,
                description=pattern.description,
                java_example=pattern.java_example,
                bedrock_example=pattern.bedrock_example,
                category=pattern.category,
                tags=pattern.tags,
                complexity=pattern.complexity,
                success_rate=pattern.success_rate,
            )
            for pattern in patterns
        ]

    except Exception as e:
        logger.error(f"Error getting pattern library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pattern library: {str(e)}",
        )
