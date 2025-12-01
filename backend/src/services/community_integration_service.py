"""
Integration service for community feedback with reputation and quality systems.

This module handles:
- Automatic reputation updates when feedback is processed
- Quality assessment triggers
- Community-driven feedback enhancement
- Reputation-based feature gating
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update

from ..db.models import FeedbackEntry, FeedbackVote
from ..db.reputation_models import UserReputation, QualityAssessment, ReputationEvent
from ..services.reputation_service import ReputationService, ReputationLevel
from ..services.quality_control_service import QualityService
from ..services.feedback_service import FeedbackService
from ..core.logging import get_logger

logger = get_logger(__name__)


class CommunityEvent(Enum):
    """Community events that trigger reputation updates."""

    FEEDBACK_SUBMITTED = "feedback_submitted"
    FEEDBACK_APPROVED = "feedback_approved"
    FEEDBACK_REJECTED = "feedback_rejected"
    FEEDBACK_ENHANCED = "feedback_enhanced"
    HELPFUL_VOTE_RECEIVED = "helpful_vote_received"
    VOTE_CAST = "vote_cast"
    MODERATION_ACTION = "moderation_action"
    QUALITY_BONUS = "quality_bonus"
    EXPERT_CONTRIBUTION = "expert_contribution"


class CommunityIntegrationService:
    """Service for integrating community features with the main system."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.reputation_service = ReputationService(db)
        self.quality_service = QualityService(db)
        self.feedback_service = FeedbackService(db)

    async def process_feedback_submission(
        self, feedback_id: str, user_id: str, auto_assess_quality: bool = True
    ) -> Dict[str, Any]:
        """Process new feedback submission with reputation and quality integration."""
        try:
            logger.info(
                f"Processing feedback submission: {feedback_id} from user: {user_id}"
            )

            results = {
                "feedback_id": feedback_id,
                "user_id": user_id,
                "quality_assessment": None,
                "reputation_update": None,
                "auto_actions": [],
                "enhancement_suggestions": [],
            }

            # Run quality assessment
            if auto_assess_quality:
                quality_assessment = await self.quality_service.assess_feedback_quality(
                    feedback_id, user_id
                )
                results["quality_assessment"] = quality_assessment
                results["auto_actions"] = quality_assessment.get("auto_actions", [])

            # Update user reputation
            reputation_update = await self.reputation_service.calculate_user_reputation(
                user_id
            )
            results["reputation_update"] = reputation_update

            # Create reputation event
            await self._create_reputation_event(
                user_id=user_id,
                event_type=CommunityEvent.FEEDBACK_SUBMITTED.value,
                score_change=0.5,  # Small bonus for participation
                reason="Feedback submitted",
                related_entity_type="feedback",
                related_entity_id=feedback_id,
            )

            # Generate enhancement suggestions if user has sufficient reputation
            user_permissions = await self.reputation_service.get_user_permissions(
                user_id
            )
            if user_permissions["vote_weight"] > 1.0:  # Enhanced users
                suggestions = await self._generate_enhancement_suggestions(feedback_id)
                results["enhancement_suggestions"] = suggestions

            return results

        except Exception as e:
            logger.error(f"Error processing feedback submission: {str(e)}")
            raise

    async def process_feedback_approval(
        self, feedback_id: str, user_id: str, approved_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process feedback approval with reputation rewards."""
        try:
            logger.info(f"Processing feedback approval: {feedback_id}")

            # Get feedback details
            result = await self.db.execute(
                select(FeedbackEntry).where(FeedbackEntry.id == feedback_id)
            )
            feedback = result.scalar_one_or_none()

            if not feedback:
                raise ValueError(f"Feedback {feedback_id} not found")

            # Award reputation bonus for approval
            bonus_amount = self._calculate_approval_bonus(feedback)
            if bonus_amount > 0:
                success = await self.reputation_service.award_reputation_bonus(
                    user_id=user_id,
                    bonus_type="feedback_approved",
                    amount=bonus_amount,
                    reason=f"Feedback approved: {feedback.title or 'Untitled'}",
                )

                if success:
                    await self._create_reputation_event(
                        user_id=user_id,
                        event_type=CommunityEvent.FEEDBACK_APPROVED.value,
                        score_change=bonus_amount,
                        reason="Feedback approved",
                        related_entity_type="feedback",
                        related_entity_id=feedback_id,
                    )

            # Update feedback status
            await self.db.execute(
                update(FeedbackEntry)
                .where(FeedbackEntry.id == feedback_id)
                .values(status="approved", updated_at=datetime.utcnow())
            )

            await self.db.commit()

            return {
                "feedback_id": feedback_id,
                "user_id": user_id,
                "bonus_awarded": bonus_amount,
                "approved_by": approved_by,
                "new_reputation": await self.reputation_service.calculate_user_reputation(
                    user_id
                ),
            }

        except Exception as e:
            logger.error(f"Error processing feedback approval: {str(e)}")
            await self.db.rollback()
            raise

    async def process_feedback_vote(
        self, feedback_id: str, voter_id: str, vote_type: str, vote_weight: float
    ) -> Dict[str, Any]:
        """Process feedback vote with reputation integration."""
        try:
            # Get feedback to find the original author
            result = await self.db.execute(
                select(FeedbackEntry).where(FeedbackEntry.id == feedback_id)
            )
            feedback = result.scalar_one_or_none()

            if not feedback:
                raise ValueError(f"Feedback {feedback_id} not found")

            results = {
                "feedback_id": feedback_id,
                "voter_id": voter_id,
                "feedback_author_id": feedback.user_id,
                "vote_type": vote_type,
                "vote_weight": vote_weight,
                "reputation_changes": {},
            }

            # Award reputation to feedback author for helpful votes
            if vote_type == "helpful" and feedback.user_id != voter_id:
                bonus_amount = vote_weight * 2.0  # Scale bonus by vote weight

                # Check for vote manipulation before awarding
                manipulation_warnings = (
                    await self.reputation_service.detect_manipulation_patterns(voter_id)
                )
                if not manipulation_warnings:
                    success = await self.reputation_service.award_reputation_bonus(
                        user_id=feedback.user_id,
                        bonus_type="helpful_vote_received",
                        amount=bonus_amount,
                        reason=f"Received helpful vote on feedback: {feedback.title or 'Untitled'}",
                        related_entity_id=feedback_id,
                    )

                    if success:
                        await self._create_reputation_event(
                            user_id=feedback.user_id,
                            event_type=CommunityEvent.HELPFUL_VOTE_RECEIVED.value,
                            score_change=bonus_amount,
                            reason=f"Helpful vote received from {voter_id}",
                            related_entity_type="vote",
                            related_entity_id=f"{feedback_id}:{voter_id}",
                        )

                        results["reputation_changes"][feedback.user_id] = bonus_amount

            # Small reputation change for casting vote (encourages engagement)
            vote_bonus = 0.1 * vote_weight
            await self._create_reputation_event(
                user_id=voter_id,
                event_type=CommunityEvent.VOTE_CAST.value,
                score_change=vote_bonus,
                reason=f"Cast {vote_type} vote",
                related_entity_type="vote",
                related_entity_id=f"{feedback_id}:{voter_id}",
            )

            results["reputation_changes"][voter_id] = vote_bonus

            return results

        except Exception as e:
            logger.error(f"Error processing feedback vote: {str(e)}")
            raise

    async def enhance_feedback_with_ai(
        self, feedback_id: str, enhancement_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Enhance feedback using AI based on community reputation."""
        try:
            # Get feedback and user reputation
            result = await self.db.execute(
                select(FeedbackEntry, UserReputation)
                .join(UserReputation, FeedbackEntry.user_id == UserReputation.user_id)
                .where(FeedbackEntry.id == feedback_id)
            )
            row = result.first()

            if not row:
                raise ValueError(f"Feedback {feedback_id} not found")

            feedback, reputation = row

            # Check if user has sufficient reputation for enhancement
            user_level = ReputationLevel[reputation.level]
            if user_level.min_score < 50:  # Need at least Trusted level
                return {
                    "feedback_id": feedback_id,
                    "error": "Insufficient reputation for AI enhancement",
                    "required_level": "Trusted (50+ reputation)",
                }

            # Enhance feedback using existing feedback service
            enhancement_result = await self.feedback_service.enhance_feedback_with_ai(
                feedback_id, enhancement_type
            )

            # Award reputation bonus for AI enhancement
            enhancement_bonus = 5.0 * (
                1 + user_level.privileges.get("bonus_weight", 1.0)
            )
            await self.reputation_service.award_reputation_bonus(
                user_id=feedback.user_id,
                bonus_type="feedback_enhanced",
                amount=enhancement_bonus,
                reason=f"AI-enhanced feedback: {feedback.title or 'Untitled'}",
                related_entity_id=feedback_id,
            )

            await self._create_reputation_event(
                user_id=feedback.user_id,
                event_type=CommunityEvent.FEEDBACK_ENHANCED.value,
                score_change=enhancement_bonus,
                reason="Feedback AI-enhanced",
                related_entity_type="feedback",
                related_entity_id=feedback_id,
            )

            return {
                "feedback_id": feedback_id,
                "enhancement_result": enhancement_result,
                "bonus_awarded": enhancement_bonus,
                "new_reputation": await self.reputation_service.calculate_user_reputation(
                    feedback.user_id
                ),
            }

        except Exception as e:
            logger.error(f"Error enhancing feedback with AI: {str(e)}")
            raise

    async def get_community_insights(self, time_range: str = "7d") -> Dict[str, Any]:
        """Get comprehensive community insights and analytics."""
        try:
            # Calculate time window
            days = int(time_range.replace("d", ""))
            start_date = datetime.utcnow() - timedelta(days=days)

            insights = {
                "time_range": time_range,
                "period_start": start_date,
                "period_end": datetime.utcnow(),
                "activity_metrics": {},
                "quality_metrics": {},
                "reputation_metrics": {},
                "engagement_metrics": {},
                "top_contributors": [],
                "trending_topics": [],
            }

            # Activity metrics
            result = await self.db.execute(
                select(func.count(FeedbackEntry.id)).where(
                    FeedbackEntry.created_at >= start_date
                )
            )
            insights["activity_metrics"]["feedback_submitted"] = result.scalar()

            # Quality metrics
            result = await self.db.execute(
                select(
                    func.count(QualityAssessment.id).label("total_assessments"),
                    func.avg(QualityAssessment.quality_score).label("avg_quality"),
                ).where(QualityAssessment.created_at >= start_date)
            )
            quality_stats = result.first()
            insights["quality_metrics"] = {
                "assessments_performed": quality_stats.total_assessments,
                "average_quality_score": float(quality_stats.avg_quality)
                if quality_stats.avg_quality
                else 0,
            }

            # Reputation metrics
            result = await self.db.execute(
                select(
                    func.count(UserReputation.id).label("active_users"),
                    func.avg(UserReputation.reputation_score).label("avg_reputation"),
                ).where(UserReputation.last_activity_date >= start_date)
            )
            reputation_stats = result.first()
            insights["reputation_metrics"] = {
                "active_users": reputation_stats.active_users,
                "average_reputation": float(reputation_stats.avg_reputation)
                if reputation_stats.avg_reputation
                else 0,
            }

            # Engagement metrics
            result = await self.db.execute(
                select(func.count(FeedbackVote.id)).where(
                    FeedbackVote.created_at >= start_date
                )
            )
            insights["engagement_metrics"]["votes_cast"] = result.scalar()

            # Top contributors
            result = await self.db.execute(
                select(
                    UserReputation.user_id,
                    UserReputation.reputation_score,
                    func.count(FeedbackEntry.id).label("feedback_count"),
                )
                .join(FeedbackEntry, UserReputation.user_id == FeedbackEntry.user_id)
                .where(FeedbackEntry.created_at >= start_date)
                .group_by(UserReputation.user_id, UserReputation.reputation_score)
                .order_by(desc(UserReputation.reputation_score))
                .limit(10)
            )

            insights["top_contributors"] = [
                {
                    "user_id": row.user_id,
                    "reputation_score": float(row.reputation_score),
                    "feedback_count": row.feedback_count,
                }
                for row in result.all()
            ]

            return insights

        except Exception as e:
            logger.error(f"Error getting community insights: {str(e)}")
            raise

    def _calculate_approval_bonus(self, feedback: FeedbackEntry) -> float:
        """Calculate reputation bonus for approved feedback."""
        base_bonus = 2.0

        # Bonus for detailed feedback
        content_length = len(feedback.content or "")
        if content_length > 500:
            base_bonus += 1.0
        elif content_length > 200:
            base_bonus += 0.5

        # Bonus for technical feedback
        if feedback.feedback_type in ["bug_report", "technical_issue"]:
            base_bonus += 1.5

        # Bonus for including additional context
        if feedback.additional_context:
            base_bonus += 0.5

        return base_bonus

    async def _create_reputation_event(
        self,
        user_id: str,
        event_type: str,
        score_change: float,
        reason: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a reputation event record."""
        try:
            # Get current user reputation
            result = await self.db.execute(
                select(UserReputation).where(UserReputation.user_id == user_id)
            )
            reputation_record = result.scalar_one_or_none()

            previous_score = (
                reputation_record.reputation_score if reputation_record else 0.0
            )
            new_score = previous_score + score_change

            # Create reputation event
            event = ReputationEvent(
                user_id=user_id,
                event_type=event_type,
                score_change=score_change,
                previous_score=previous_score,
                new_score=new_score,
                reason=reason,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                context_data=context_data or {},
                event_date=datetime.utcnow().date(),
            )
            self.db.add(event)

            # Update reputation record if it exists
            if reputation_record:
                reputation_record.reputation_score = new_score
                reputation_record.updated_at = datetime.utcnow()

            await self.db.commit()

        except Exception as e:
            logger.error(f"Error creating reputation event: {str(e)}")
            await self.db.rollback()

    async def _generate_enhancement_suggestions(self, feedback_id: str) -> List[str]:
        """Generate AI-powered enhancement suggestions for feedback."""
        try:
            # This would integrate with the AI enhancement system
            # For now, return placeholder suggestions
            suggestions = [
                "Add more specific technical details",
                "Include steps to reproduce the issue",
                "Add expected vs actual behavior",
                "Consider providing code examples",
                "Include Minecraft version information",
            ]

            return suggestions[:3]  # Return top 3 suggestions

        except Exception as e:
            logger.error(f"Error generating enhancement suggestions: {str(e)}")
            return []
