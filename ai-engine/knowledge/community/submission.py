"""
Community pattern submission handler.

Manages user-submitted patterns, review workflow, and voting.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SubmissionStatus(Enum):
    """Pattern submission status."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class PatternSubmission:
    """
    Represents a user-submitted pattern.

    Contains Java and Bedrock code examples, description, and metadata.
    """
    id: str
    java_pattern: str
    bedrock_pattern: str
    description: str
    contributor_id: str
    status: SubmissionStatus
    created_at: datetime
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    upvotes: int = 0
    downvotes: int = 0
    tags: List[str] = field(default_factory=list)
    category: str = "unknown"

    def __post_init__(self):
        """Validate submission data."""
        if not self.java_pattern:
            raise ValueError("Java pattern cannot be empty")
        if not self.bedrock_pattern:
            raise ValueError("Bedrock pattern cannot be empty")
        if len(self.description) < 20:
            raise ValueError("Description must be at least 20 characters")
        if not self.contributor_id:
            raise ValueError("Contributor ID cannot be empty")
        if self.upvotes < 0:
            raise ValueError("Upvotes cannot be negative")
        if self.downvotes < 0:
            raise ValueError("Downvotes cannot be negative")

    def to_dict(self) -> dict:
        """Convert submission to dictionary."""
        return {
            "id": str(self.id),
            "java_pattern": self.java_pattern,
            "bedrock_pattern": self.bedrock_pattern,
            "description": self.description,
            "contributor_id": self.contributor_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "reviewed_by": self.reviewed_by,
            "review_notes": self.review_notes,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "upvotes": self.upvotes,
            "downvotes": self.downvotes,
            "tags": self.tags,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PatternSubmission":
        """Create submission from dictionary."""
        return cls(
            id=data["id"],
            java_pattern=data["java_pattern"],
            bedrock_pattern=data["bedrock_pattern"],
            description=data["description"],
            contributor_id=data["contributor_id"],
            status=SubmissionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            reviewed_by=data.get("reviewed_by"),
            review_notes=data.get("review_notes"),
            reviewed_at=datetime.fromisoformat(data["reviewed_at"]) if data.get("reviewed_at") else None,
            upvotes=data.get("upvotes", 0),
            downvotes=data.get("downvotes", 0),
            tags=data.get("tags", []),
            category=data.get("category", "unknown"),
        )

    @property
    def score(self) -> int:
        """Calculate net score (upvotes - downvotes)."""
        return self.upvotes - self.downvotes


class CommunityPatternManager:
    """
    Manages community-submitted patterns.

    Handles submission, validation, review, and voting workflows.
    """

    def __init__(self):
        """Initialize manager."""
        from .validation import PatternValidator
        self.validator = PatternValidator()
        self.submissions: dict = {}  # In-memory storage (would use database in production)

    async def submit_pattern(
        self,
        java_pattern: str,
        bedrock_pattern: str,
        description: str,
        contributor_id: str,
        tags: List[str],
        category: str,
    ) -> PatternSubmission:
        """
        Submit a new pattern for review.

        Args:
            java_pattern: Java code example
            bedrock_pattern: Bedrock code example
            description: Pattern description
            contributor_id: User submitting the pattern
            tags: List of tags for categorization
            category: Pattern category (item, block, entity, etc.)

        Returns:
            Created PatternSubmission

        Raises:
            ValueError: If validation fails
        """
        # Validate pattern
        result = await self.validator.validate_pattern(java_pattern, bedrock_pattern, description)
        if not result.is_valid:
            error_msg = "Pattern validation failed: " + "; ".join(result.errors)
            logger.warning(f"Pattern submission rejected: {error_msg}")
            raise ValueError(error_msg)

        # Create submission
        import uuid
        submission = PatternSubmission(
            id=str(uuid.uuid4()),
            java_pattern=java_pattern,
            bedrock_pattern=bedrock_pattern,
            description=description,
            contributor_id=contributor_id,
            status=SubmissionStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            tags=tags,
            category=category,
        )

        # Store submission (in-memory for now)
        self.submissions[submission.id] = submission

        # Notify reviewers (log for now)
        logger.info(
            f"New pattern submission from {contributor_id}: {submission.id}. "
            f"Category: {category}, Tags: {tags}"
        )

        return submission

    async def review_pattern(
        self,
        submission_id: str,
        reviewer_id: str,
        approved: bool,
        notes: Optional[str] = None,
    ) -> None:
        """
        Review a pattern submission.

        Args:
            submission_id: Submission to review
            reviewer_id: User reviewing the pattern
            approved: Whether to approve the pattern
            notes: Optional review notes

        Raises:
            ValueError: If submission not found
        """
        submission = self.submissions.get(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")

        # Update submission status
        submission.status = SubmissionStatus.APPROVED if approved else SubmissionStatus.REJECTED
        submission.reviewed_by = reviewer_id
        submission.review_notes = notes
        submission.reviewed_at = datetime.now(timezone.utc)

        # If approved, add to pattern library
        if approved:
            from ..patterns.base import ConversionPattern, PatternLibrary
            from ..patterns.mappings import PatternMapping, PatternMappingRegistry

            # Create pattern from submission
            pattern = ConversionPattern(
                id=f"community_{submission.id[:8]}",
                name=f"Community: {submission.category} pattern",
                description=submission.description,
                java_example=submission.java_pattern,
                bedrock_example=submission.bedrock_pattern,
                category=submission.category,
                tags=submission.tags,
                complexity="simple",  # Default to simple, could be determined by analyzer
                success_rate=0.0,  # Will be updated based on conversions
            )

            # Add to pattern library
            library = PatternLibrary()
            library.add_pattern(pattern)

            logger.info(f"Approved pattern {submission.id} added to library")

        # Notify contributor (log for now)
        action = "approved" if approved else "rejected"
        logger.info(
            f"Pattern {submission_id} {action} by {reviewer_id}. "
            f"Contributor: {submission.contributor_id}"
        )

    async def vote_on_pattern(self, submission_id: str, user_id: str, upvote: bool) -> None:
        """
        Vote on a pattern submission.

        Args:
            submission_id: Submission to vote on
            user_id: User voting (for tracking, could prevent double-voting)
            upvote: True for upvote, False for downvote

        Raises:
            ValueError: If submission not found
        """
        submission = self.submissions.get(submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")

        # Update vote counts
        if upvote:
            submission.upvotes += 1
        else:
            submission.downvotes += 1

        logger.info(
            f"User {user_id} {'upvoted' if upvote else 'downvoted'} "
            f"pattern {submission_id}. Score: {submission.score}"
        )

    async def get_pending_submissions(self, limit: int = 50) -> List[PatternSubmission]:
        """
        Get pending submissions for review.

        Args:
            limit: Maximum number of submissions to return

        Returns:
            List of pending submissions, sorted by created_at DESC
        """
        pending = [
            s for s in self.submissions.values()
            if s.status == SubmissionStatus.PENDING
        ]

        # Sort by created_at descending
        pending.sort(key=lambda x: x.created_at, reverse=True)

        return pending[:limit]

    async def get_submission(self, submission_id: str) -> Optional[PatternSubmission]:
        """
        Get a submission by ID.

        Args:
            submission_id: Submission identifier

        Returns:
            PatternSubmission if found, None otherwise
        """
        return self.submissions.get(submission_id)
