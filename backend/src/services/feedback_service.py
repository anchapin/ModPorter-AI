"""
Feedback service for managing user feedback entries and votes.
"""

import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.models import FeedbackEntry

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for managing user feedback."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_feedback_by_id(self, feedback_id: str) -> Optional[FeedbackEntry]:
        """Get feedback entry by ID."""
        result = await self.db.execute(
            select(FeedbackEntry).where(FeedbackEntry.id == feedback_id)
        )
        return result.scalar_one_or_none()

    async def get_user_feedback(
        self, user_id: str, limit: int = 50
    ) -> List[FeedbackEntry]:
        """Get feedback entries submitted by a user."""
        result = await self.db.execute(
            select(FeedbackEntry)
            .where(FeedbackEntry.user_id == user_id)
            .order_by(FeedbackEntry.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
