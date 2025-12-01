"""
Reputation service for community feedback quality controls.

This module handles:
- User reputation calculation and tracking
- Quality score assessment for feedback
- Reputation-based permissions and features
- Anti-manipulation controls
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_

from db.models import User, FeedbackEntry, FeedbackVote, KnowledgeNodeVersion
from db.reputation_models import UserReputation
from .feedback_service import FeedbackService

logger = logging.getLogger(__name__)


class ReputationLevel(Enum):
    """Reputation levels with associated privileges."""

    NEWCOMER = (
        0,
        "Newcomer",
        {"daily_votes": 5, "can_moderate": False, "bonus_weight": 1.0},
    )
    CONTRIBUTOR = (
        10,
        "Contributor",
        {"daily_votes": 10, "can_moderate": False, "bonus_weight": 1.1},
    )
    TRUSTED = (
        50,
        "Trusted Contributor",
        {"daily_votes": 20, "can_moderate": False, "bonus_weight": 1.25},
    )
    EXPERT = (
        150,
        "Expert",
        {"daily_votes": 50, "can_moderate": False, "bonus_weight": 1.5},
    )
    MODERATOR = (
        500,
        "Moderator",
        {"daily_votes": 100, "can_moderate": True, "bonus_weight": 2.0},
    )

    def __init__(self, min_score: int, display_name: str, privileges: Dict[str, Any]):
        self.min_score = min_score
        self.display_name = display_name
        self.privileges = privileges

    @classmethod
    def get_level(cls, reputation_score: int) -> "ReputationLevel":
        """Get reputation level for a given score."""
        for level in sorted(cls, key=lambda x: x.min_score, reverse=True):
            if reputation_score >= level.min_score:
                return level
        return cls.NEWCOMER


class ReputationService:
    """Service for managing user reputation and quality controls."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.feedback_service = FeedbackService(db)

    async def calculate_user_reputation(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate comprehensive reputation score for a user.

        Reputation factors:
        - Feedback quality scores (40%)
        - Community engagement (25%)
        - Expertise contributions (20%)
        - Account age and consistency (15%)
        """
        try:
            # Get user's feedback and calculate quality score
            feedback_quality = await self._calculate_feedback_quality_score(user_id)

            # Calculate community engagement score
            engagement_score = await self._calculate_engagement_score(user_id)

            # Calculate expertise contribution score
            expertise_score = await self._calculate_expertise_score(user_id)

            # Calculate account consistency score
            consistency_score = await self._calculate_consistency_score(user_id)

            # Weighted combination
            total_score = (
                feedback_quality * 0.4
                + engagement_score * 0.25
                + expertise_score * 0.2
                + consistency_score * 0.15
            )

            # Get level and privileges
            level = ReputationLevel.get_level(int(total_score))

            # Update or create reputation record
            await self._update_reputation_record(user_id, total_score, level)

            return {
                "user_id": user_id,
                "reputation_score": round(total_score, 2),
                "level": level.name,
                "level_display": level.display_name,
                "privileges": level.privileges,
                "breakdown": {
                    "feedback_quality": round(feedback_quality, 2),
                    "engagement": round(engagement_score, 2),
                    "expertise": round(expertise_score, 2),
                    "consistency": round(consistency_score, 2),
                },
                "updated_at": datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"Error calculating reputation for user {user_id}: {str(e)}")
            raise

    async def _calculate_feedback_quality_score(self, user_id: str) -> float:
        """Calculate quality score based on user's feedback submissions."""
        try:
            # Get user's feedback with quality metrics
            result = await self.db.execute(
                select(
                    func.count(FeedbackEntry.id).label("total_feedback"),
                    func.avg(FeedbackEntry.quality_score).label("avg_quality"),
                    func.avg(FeedbackEntry.helpful_count).label("avg_helpful"),
                    func.count(
                        func.filter(FeedbackEntry.ai_tags.contains(["enhanced"]))
                    ).label("enhanced_count"),
                ).where(
                    FeedbackEntry.user_id == user_id, FeedbackEntry.status == "approved"
                )
            )
            stats = result.first()

            if not stats or stats.total_feedback == 0:
                return 0.0

            # Base score from average quality rating
            base_score = (stats.avg_quality or 0) * 20  # 0-20 points

            # Bonus for helpful votes
            helpful_bonus = min((stats.avg_helpful or 0) * 2, 15)  # 0-15 points

            # Bonus for AI-enhanced contributions
            enhanced_ratio = stats.enhanced_count / stats.total_feedback
            enhanced_bonus = enhanced_ratio * 10  # 0-10 points

            # Volume bonus (diminishing returns)
            volume_bonus = min(math.log(stats.total_feedback + 1) * 2, 5)  # 0-5 points

            return base_score + helpful_bonus + enhanced_bonus + volume_bonus

        except Exception as e:
            logger.error(f"Error calculating feedback quality score: {str(e)}")
            return 0.0

    async def _calculate_engagement_score(self, user_id: str) -> float:
        """Calculate community engagement score."""
        try:
            # Get recent activity (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            # Feedback activity
            result = await self.db.execute(
                select(
                    func.count(FeedbackEntry.id).label("feedback_count"),
                    func.count(FeedbackVote.id).label("vote_count"),
                ).where(
                    and_(
                        FeedbackEntry.user_id == user_id,
                        FeedbackEntry.created_at >= thirty_days_ago,
                    )
                )
            )
            activity_stats = result.first() or (0, 0)

            # Voting activity
            result = await self.db.execute(
                select(func.count(FeedbackVote.id)).where(
                    and_(
                        FeedbackVote.user_id == user_id,
                        FeedbackVote.created_at >= thirty_days_ago,
                    )
                )
            )
            vote_stats = result.first()

            # Calculate engagement score
            feedback_score = min(activity_stats.feedback_count * 2, 25)  # 0-25 points
            voting_score = min((vote_stats[0] or 0) * 0.5, 15)  # 0-15 points

            return feedback_score + voting_score

        except Exception as e:
            logger.error(f"Error calculating engagement score: {str(e)}")
            return 0.0

    async def _calculate_expertise_score(self, user_id: str) -> float:
        """Calculate expertise contribution score."""
        try:
            # Check for knowledge graph contributions
            result = await self.db.execute(
                select(
                    func.count(KnowledgeNodeVersion.id).label("node_versions"),
                    func.count(
                        func.filter(
                            KnowledgeNodeVersion.change_type.in_(
                                ["create", "major_improvement"]
                            )
                        )
                    ).label("major_contributions"),
                ).where(KnowledgeNodeVersion.author_id == user_id)
            )
            expertise_stats = result.first()

            if not expertise_stats:
                return 0.0

            # Score for knowledge contributions
            version_score = min(expertise_stats.node_versions * 3, 30)  # 0-30 points
            major_bonus = expertise_stats.major_contributions * 5  # 0-20 points

            return version_score + major_bonus

        except Exception as e:
            logger.error(f"Error calculating expertise score: {str(e)}")
            return 0.0

    async def _calculate_consistency_score(self, user_id: str) -> float:
        """Calculate consistency and trustworthiness score."""
        try:
            # Get user information
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                return 0.0

            # Account age score
            account_age = datetime.utcnow() - user.created_at
            age_days = account_age.days
            age_score = min(age_days / 30, 20)  # 0-20 points

            # Consistency bonus based on regular activity
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            result = await self.db.execute(
                select(
                    func.count(
                        func.distinct(func.date(FeedbackEntry.created_at))
                    ).label("active_days")
                ).where(
                    and_(
                        FeedbackEntry.user_id == user_id,
                        FeedbackEntry.created_at >= thirty_days_ago,
                    )
                )
            )
            consistency_stats = result.first()

            active_days = consistency_stats.active_days or 0
            consistency_score = min(active_days * 0.5, 10)  # 0-10 points

            return age_score + consistency_score

        except Exception as e:
            logger.error(f"Error calculating consistency score: {str(e)}")
            return 0.0

    async def _update_reputation_record(
        self, user_id: str, score: float, level: ReputationLevel
    ) -> None:
        """Update or create user reputation record."""
        try:
            # Check if record exists
            result = await self.db.execute(
                select(UserReputation).where(UserReputation.user_id == user_id)
            )
            reputation_record = result.scalar_one_or_none()

            if reputation_record:
                # Update existing record
                reputation_record.reputation_score = score
                reputation_record.level = level.name
                reputation_record.updated_at = datetime.utcnow()
            else:
                # Create new record
                reputation_record = UserReputation(
                    user_id=user_id,
                    reputation_score=score,
                    level=level.name,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self.db.add(reputation_record)

            await self.db.commit()

        except Exception as e:
            logger.error(f"Error updating reputation record: {str(e)}")
            await self.db.rollback()
            raise

    async def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """Get user's current permissions based on reputation level."""
        try:
            result = await self.db.execute(
                select(UserReputation).where(UserReputation.user_id == user_id)
            )
            reputation_record = result.scalar_one_or_none()

            if not reputation_record:
                level = ReputationLevel.NEWCOMER
            else:
                level = ReputationLevel[reputation_record.level]

            return {
                "level": level.name,
                "level_display": level.display_name,
                "permissions": level.privileges,
                "can_vote": True,
                "daily_votes_remaining": await self._get_daily_votes_remaining(user_id),
                "can_moderate": level.privileges.get("can_moderate", False),
                "vote_weight": level.privileges.get("bonus_weight", 1.0),
            }

        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return ReputationLevel.NEWCOMER.privileges

    async def _get_daily_votes_remaining(self, user_id: str) -> int:
        """Calculate remaining daily votes for user."""
        try:
            # Get user's daily vote limit
            permissions = await self.get_user_permissions(user_id)
            daily_limit = permissions["permissions"]["daily_votes"]

            # Count votes today
            today = datetime.utcnow().date()
            result = await self.db.execute(
                select(func.count(FeedbackVote.id)).where(
                    and_(
                        FeedbackVote.user_id == user_id,
                        func.date(FeedbackVote.created_at) == today,
                    )
                )
            )
            votes_today = result.scalar()

            return max(0, daily_limit - votes_today)

        except Exception as e:
            logger.error(f"Error calculating daily votes remaining: {str(e)}")
            return 5  # Default minimum

    async def check_vote_eligibility(self, user_id: str) -> Tuple[bool, str]:
        """Check if user is eligible to vote on feedback."""
        try:
            permissions = await self.get_user_permissions(user_id)
            daily_remaining = permissions["daily_votes_remaining"]

            if daily_remaining <= 0:
                return False, "Daily vote limit reached"

            return True, "Eligible to vote"

        except Exception as e:
            logger.error(f"Error checking vote eligibility: {str(e)}")
            return False, "Error checking eligibility"

    async def calculate_vote_weight(self, user_id: str) -> float:
        """Calculate the weight of a user's vote based on reputation."""
        try:
            permissions = await self.get_user_permissions(user_id)
            return permissions["vote_weight"]

        except Exception as e:
            logger.error(f"Error calculating vote weight: {str(e)}")
            return 1.0

    async def detect_manipulation_patterns(self, user_id: str) -> List[str]:
        """Detect potential reputation manipulation patterns."""
        try:
            warnings = []

            # Check for rapid voting patterns
            recent_votes = await self._check_rapid_voting(user_id)
            if recent_votes:
                warnings.append(
                    f"Rapid voting pattern detected: {recent_votes} votes in 10 minutes"
                )

            # Check for biased voting (always voting same direction)
            voting_bias = await self._check_voting_bias(user_id)
            if voting_bias > 0.9:
                warnings.append(
                    f"High voting bias detected: {voting_bias:.1%} same-direction votes"
                )

            # Check for reciprocal voting patterns
            reciprocal = await self._check_reciprocal_voting(user_id)
            if reciprocal:
                warnings.append(
                    f"Reciprocal voting patterns detected with {len(reciprocal)} users"
                )

            return warnings

        except Exception as e:
            logger.error(f"Error detecting manipulation patterns: {str(e)}")
            return ["Error analyzing voting patterns"]

    async def _check_rapid_voting(self, user_id: str) -> int:
        """Check for unusually rapid voting."""
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)

        result = await self.db.execute(
            select(func.count(FeedbackVote.id)).where(
                and_(
                    FeedbackVote.user_id == user_id,
                    FeedbackVote.created_at >= ten_minutes_ago,
                )
            )
        )
        return result.scalar()

    async def _check_voting_bias(self, user_id: str) -> float:
        """Check if user has strong voting bias."""
        # Get last 50 votes
        result = await self.db.execute(
            select(FeedbackVote.vote_type)
            .where(FeedbackVote.user_id == user_id)
            .order_by(FeedbackVote.created_at.desc())
            .limit(50)
        )
        votes = [row[0] for row in result.all()]

        if not votes or len(votes) < 10:
            return 0.0

        # Calculate bias towards most common vote type
        vote_counts = {"helpful": 0, "not_helpful": 0}
        for vote in votes:
            vote_counts[vote] += 1

        most_common = max(vote_counts.values())
        return most_common / len(votes)

    async def _check_reciprocal_voting(self, user_id: str) -> List[str]:
        """Check for reciprocal voting patterns."""
        # Users this person has voted for
        result = await self.db.execute(
            select(FeedbackEntry.user_id)
            .join(FeedbackVote, FeedbackEntry.id == FeedbackVote.feedback_id)
            .where(FeedbackVote.user_id == user_id)
            .distinct()
        )
        voted_users = [row[0] for row in result.all()]

        reciprocal_users = []

        for voted_user in voted_users:
            # Check if voted_user has voted back
            result = await self.db.execute(
                select(func.count(FeedbackVote.id))
                .join(FeedbackEntry, FeedbackVote.feedback_id == FeedbackEntry.id)
                .where(
                    and_(
                        FeedbackVote.user_id == voted_user,
                        FeedbackEntry.user_id == user_id,
                    )
                )
            )
            back_votes = result.scalar()

            if back_votes >= 3:  # Threshold for reciprocal pattern
                reciprocal_users.append(voted_user)

        return reciprocal_users

    async def get_reputation_leaderboard(
        self, limit: int = 50, timeframe: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get reputation leaderboard."""
        try:
            query = (
                select(
                    UserReputation.user_id,
                    UserReputation.reputation_score,
                    UserReputation.level,
                    User.username,
                )
                .join(User, UserReputation.user_id == User.id)
                .order_by(UserReputation.reputation_score.desc())
                .limit(limit)
            )

            result = await self.db.execute(query)
            leaderboard = []

            for rank, (user_id, score, level, username) in enumerate(result.all(), 1):
                level_info = ReputationLevel[level]
                leaderboard.append(
                    {
                        "rank": rank,
                        "user_id": user_id,
                        "username": username,
                        "reputation_score": score,
                        "level": level,
                        "level_display": level_info.display_name,
                        "privileges": level_info.privileges,
                    }
                )

            return leaderboard

        except Exception as e:
            logger.error(f"Error getting reputation leaderboard: {str(e)}")
            return []

    async def award_reputation_bonus(
        self, user_id: str, bonus_type: str, amount: float, reason: str
    ) -> bool:
        """Award reputation bonus for exceptional contributions."""
        try:
            # Create reputation bonus record
            {
                "user_id": user_id,
                "bonus_type": bonus_type,
                "amount": amount,
                "reason": reason,
                "awarded_at": datetime.utcnow(),
            }

            # Update user's reputation
            current_reputation = await self.calculate_user_reputation(user_id)
            new_score = current_reputation["reputation_score"] + amount
            new_level = ReputationLevel.get_level(int(new_score))

            await self._update_reputation_record(user_id, new_score, new_level)

            logger.info(
                f"Awarded {amount} reputation bonus to user {user_id} "
                f"for {bonus_type}: {reason}"
            )

            return True

        except Exception as e:
            logger.error(f"Error awarding reputation bonus: {str(e)}")
            return False
