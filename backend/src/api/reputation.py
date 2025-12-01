"""
Reputation system API endpoints.

This module provides endpoints for:
- User reputation management
- Quality assessment
- Reputation leaderboard
- Moderation tools
- Quality metrics
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from db import get_async_session
from db.models import User, FeedbackEntry, FeedbackVote
from db.reputation_models import UserReputation, QualityAssessment, ReputationEvent
from sqlalchemy.future import select
from sqlalchemy import and_
from services.reputation_service import ReputationService, ReputationLevel
from services.quality_control_service import QualityService
from security.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for request/response
class ReputationResponse(BaseModel):
    user_id: str
    reputation_score: float
    level: str
    level_display: str
    privileges: Dict[str, Any]
    breakdown: Dict[str, float]
    updated_at: datetime


class UserPermissionsResponse(BaseModel):
    level: str
    level_display: str
    permissions: Dict[str, Any]
    can_vote: bool
    daily_votes_remaining: int
    can_moderate: bool
    vote_weight: float


class QualityAssessmentResponse(BaseModel):
    feedback_id: str
    quality_score: float
    quality_grade: str
    issues: List[Dict[str, Any]]
    warnings: List[str]
    auto_actions: List[str]
    assessment_time: datetime
    assessor: str


class ReputationLeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    reputation_score: float
    level: str
    level_display: str
    privileges: Dict[str, Any]


class VoteRequest(BaseModel):
    feedback_id: str
    vote_type: str = Field(..., description="Vote type: 'helpful' or 'not_helpful'")


class ReputationBonusRequest(BaseModel):
    user_id: str
    bonus_type: str
    amount: float = Field(..., gt=0, description="Bonus amount must be positive")
    reason: str
    related_entity_id: Optional[str] = None


class QualityMetricsResponse(BaseModel):
    time_range: str
    total_feedback: int
    quality_distribution: Dict[str, float]
    common_issues: Dict[str, float]
    auto_actions: Dict[str, float]
    average_quality_score: float


@router.get("/reputation/me", response_model=ReputationResponse)
async def get_my_reputation(
    current_user: User = Depends(get_current_user), db=Depends(get_async_session)
):
    """Get current user's reputation information."""
    try:
        reputation_service = ReputationService(db)
        reputation_data = await reputation_service.calculate_user_reputation(
            current_user.id
        )

        return ReputationResponse(**reputation_data)

    except Exception as e:
        logger.error(f"Error getting user reputation: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve reputation information"
        )


@router.get("/reputation/{user_id}", response_model=ReputationResponse)
async def get_user_reputation(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get reputation information for a specific user."""
    try:
        reputation_service = ReputationService(db)
        reputation_data = await reputation_service.calculate_user_reputation(user_id)

        return ReputationResponse(**reputation_data)

    except Exception as e:
        logger.error(f"Error getting user {user_id} reputation: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve reputation information"
        )


@router.get("/reputation/{user_id}/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get user's current permissions based on reputation level."""
    try:
        reputation_service = ReputationService(db)
        permissions = await reputation_service.get_user_permissions(user_id)

        return UserPermissionsResponse(**permissions)

    except Exception as e:
        logger.error(f"Error getting user permissions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve permissions")


@router.get("/reputation/leaderboard", response_model=List[ReputationLeaderboardEntry])
async def get_reputation_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    timeframe: Optional[str] = Query(None, description="Timeframe: '7d', '30d', '90d'"),
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get reputation leaderboard."""
    try:
        reputation_service = ReputationService(db)
        leaderboard = await reputation_service.get_reputation_leaderboard(
            limit, timeframe
        )

        return [ReputationLeaderboardEntry(**entry) for entry in leaderboard]

    except Exception as e:
        logger.error(f"Error getting reputation leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve leaderboard")


@router.get("/quality/assess/{feedback_id}", response_model=QualityAssessmentResponse)
async def get_quality_assessment(
    feedback_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get quality assessment for a specific feedback."""
    try:
        quality_service = QualityService(db)
        assessment = await quality_service.assess_feedback_quality(feedback_id)

        return QualityAssessmentResponse(**assessment)

    except Exception as e:
        logger.error(f"Error getting quality assessment: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve quality assessment"
        )


@router.post("/quality/assess-batch", response_model=List[QualityAssessmentResponse])
async def batch_quality_assessment(
    feedback_ids: List[str],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Run quality assessment on multiple feedback items."""
    try:
        if len(feedback_ids) > 100:
            raise HTTPException(
                status_code=400, detail="Maximum 100 feedback IDs per batch"
            )

        quality_service = QualityService(db)
        assessments = await quality_service.batch_quality_assessment(feedback_ids)

        return [QualityAssessmentResponse(**assessment) for assessment in assessments]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch quality assessment: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to run batch quality assessment"
        )


@router.get("/quality/metrics", response_model=QualityMetricsResponse)
async def get_quality_metrics(
    time_range: str = Query("7d", description="Time range: '7d', '30d', '90d'"),
    user_id: Optional[str] = Query(None, description="Filter by specific user"),
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get quality metrics and statistics."""
    try:
        quality_service = QualityService(db)
        metrics = await quality_service.get_quality_metrics(time_range, user_id)

        if "error" in metrics:
            raise HTTPException(status_code=400, detail=metrics["error"])

        return QualityMetricsResponse(**metrics)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quality metrics: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve quality metrics"
        )


@router.post("/feedback/vote")
async def vote_on_feedback(
    vote_request: VoteRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Cast a vote on feedback (with reputation-based restrictions)."""
    try:
        # Validate vote type
        if vote_request.vote_type not in ["helpful", "not_helpful"]:
            raise HTTPException(status_code=400, detail="Invalid vote type")

        reputation_service = ReputationService(db)

        # Check eligibility
        eligible, reason = await reputation_service.check_vote_eligibility(
            current_user.id
        )
        if not eligible:
            raise HTTPException(status_code=429, detail=reason)

        # Check if user already voted
        existing_vote = await db.execute(
            select(FeedbackVote).where(
                and_(
                    FeedbackVote.feedback_id == vote_request.feedback_id,
                    FeedbackVote.user_id == current_user.id,
                )
            )
        )
        if existing_vote.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="User has already voted on this feedback"
            )

        # Verify feedback exists
        feedback = await db.execute(
            select(FeedbackEntry).where(FeedbackEntry.id == vote_request.feedback_id)
        )
        if not feedback.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Feedback not found")

        # Get vote weight
        vote_weight = await reputation_service.calculate_vote_weight(current_user.id)

        # Create vote
        new_vote = FeedbackVote(
            feedback_id=vote_request.feedback_id,
            user_id=current_user.id,
            vote_type=vote_request.vote_type,
            vote_weight=vote_weight,
        )
        db.add(new_vote)

        # Update feedback vote counts
        if vote_request.vote_type == "helpful":
            await db.execute(
                FeedbackEntry.__table__.update()
                .where(FeedbackEntry.id == vote_request.feedback_id)
                .values(
                    vote_count=FeedbackEntry.vote_count + 1,
                    helpful_count=FeedbackEntry.helpful_count + vote_weight,
                )
            )
        else:
            await db.execute(
                FeedbackEntry.__table__.update()
                .where(FeedbackEntry.id == vote_request.feedback_id)
                .values(
                    vote_count=FeedbackEntry.vote_count + 1,
                    not_helpful_count=FeedbackEntry.not_helpful_count + vote_weight,
                )
            )

        await db.commit()

        # Trigger reputation update in background
        background_tasks.add_task(
            reputation_service.calculate_user_reputation, current_user.id
        )

        return {"message": "Vote recorded successfully", "vote_weight": vote_weight}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording vote: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to record vote")


@router.post("/reputation/bonus")
async def award_reputation_bonus(
    bonus_request: ReputationBonusRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Award reputation bonus (requires moderator privileges)."""
    try:
        # Check moderator permissions
        reputation_service = ReputationService(db)
        permissions = await reputation_service.get_user_permissions(current_user.id)

        if not permissions.get("can_moderate", False):
            raise HTTPException(
                status_code=403, detail="Insufficient privileges to award bonuses"
            )

        # Award bonus
        success = await reputation_service.award_reputation_bonus(
            user_id=bonus_request.user_id,
            bonus_type=bonus_request.bonus_type,
            amount=bonus_request.amount,
            reason=bonus_request.reason,
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to award reputation bonus"
            )

        return {"message": "Reputation bonus awarded successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error awarding reputation bonus: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to award reputation bonus")


@router.get("/moderation/manipulation-check/{user_id}")
async def check_manipulation_patterns(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Check user for manipulation patterns (moderator only)."""
    try:
        # Check moderator permissions
        reputation_service = ReputationService(db)
        permissions = await reputation_service.get_user_permissions(current_user.id)

        if not permissions.get("can_moderate", False):
            raise HTTPException(status_code=403, detail="Insufficient privileges")

        # Check for manipulation patterns
        warnings = await reputation_service.detect_manipulation_patterns(user_id)

        return {
            "user_id": user_id,
            "manipulation_warnings": warnings,
            "checked_at": datetime.utcnow(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking manipulation patterns: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to check manipulation patterns"
        )


@router.post("/moderation/override-quality")
async def override_quality_assessment(
    feedback_id: str,
    override_score: float = Query(..., ge=0, le=100),
    override_reason: str = Query(...),
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Override automated quality assessment (moderator only)."""
    try:
        # Check moderator permissions
        reputation_service = ReputationService(db)
        permissions = await reputation_service.get_user_permissions(current_user.id)

        if not permissions.get("can_moderate", False):
            raise HTTPException(status_code=403, detail="Insufficient privileges")

        # Get existing assessment
        result = await db.execute(
            select(QualityAssessment).where(
                QualityAssessment.feedback_id == feedback_id
            )
        )
        assessment = result.scalar_one_or_none()

        if not assessment:
            # Create new assessment if none exists
            quality_service = QualityService(db)
            assessment_data = await quality_service.assess_feedback_quality(feedback_id)

            assessment = QualityAssessment(
                feedback_id=feedback_id,
                quality_score=assessment_data["quality_score"],
                quality_grade=assessment_data["quality_grade"],
                issues_detected=assessment_data["issues"],
                assessment_data=assessment_data,
            )
            db.add(assessment)
            await db.flush()

        # Update with human override
        assessment.human_override_score = override_score
        assessment.human_override_reason = override_reason
        assessment.reviewed_by_human = True
        assessment.human_reviewer_id = current_user.id
        assessment.quality_score = override_score
        assessment.quality_grade = quality_service._get_quality_grade(override_score)

        await db.commit()

        return {"message": "Quality assessment overridden successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error overriding quality assessment: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500, detail="Failed to override quality assessment"
        )


@router.get("/analytics/reputation-trends")
async def get_reputation_trends(
    time_range: str = Query("30d", description="Time range: '7d', '30d', '90d'"),
    current_user: User = Depends(get_current_user),
    db=Depends(get_async_session),
):
    """Get reputation trends and analytics."""
    try:
        # Calculate time window
        days = int(time_range.replace("d", ""))
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get reputation events in time range
        result = await db.execute(
            select(
                ReputationEvent.event_type,
                func.count(ReputationEvent.id).label("count"),
                func.avg(ReputationEvent.score_change).label("avg_change"),
            )
            .where(ReputationEvent.event_date >= start_date.date())
            .group_by(ReputationEvent.event_type)
        )

        events_data = result.all()

        # Get reputation level distribution
        result = await db.execute(
            select(
                UserReputation.level,
                func.count(UserReputation.id).label("count"),
                func.avg(UserReputation.reputation_score).label("avg_score"),
            ).group_by(UserReputation.level)
        )

        level_data = result.all()

        return {
            "time_range": time_range,
            "events_summary": [
                {
                    "event_type": row.event_type,
                    "count": row.count,
                    "average_change": float(row.avg_change) if row.avg_change else 0,
                }
                for row in events_data
            ],
            "level_distribution": [
                {
                    "level": row.level,
                    "user_count": row.count,
                    "average_score": float(row.avg_score) if row.avg_score else 0,
                    "display_name": ReputationLevel[row.level].display_name,
                }
                for row in level_data
            ],
        }

    except Exception as e:
        logger.error(f"Error getting reputation trends: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve reputation trends"
        )
