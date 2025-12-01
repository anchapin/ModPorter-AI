"""
Reputation system database models for community feedback quality controls.
"""

import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Boolean,
    String,
    Integer,
    DateTime,
    Date,
    func,
    Text,
    DECIMAL,
    TypeDecorator,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from .declarative_base import Base


# Custom type that automatically chooses the right JSON type based on the database
class JSONType(TypeDecorator):
    impl = JSONB  # Default to JSONB for PostgreSQL
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(SQLiteJSON)
        else:
            return dialect.type_descriptor(JSONB)


class UserReputation(Base):
    """User reputation tracking for community feedback system."""

    __tablename__ = "user_reputations"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )
    reputation_score: Mapped[float] = mapped_column(
        DECIMAL(8, 2), nullable=False, default=0.0
    )
    level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="NEWCOMER"
    )  # NEWCOMER, CONTRIBUTOR, TRUSTED, EXPERT, MODERATOR
    feedback_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Total feedback submitted
    approved_feedback: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Approved feedback count
    helpful_votes_received: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Helpful votes on user's feedback
    total_votes_cast: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Votes user has cast
    moderation_actions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Moderation actions taken
    quality_bonus_total: Mapped[float] = mapped_column(
        DECIMAL(6, 2), nullable=False, default=0.0
    )  # Total quality bonuses
    penalties_total: Mapped[float] = mapped_column(
        DECIMAL(6, 2), nullable=False, default=0.0
    )  # Total penalties
    last_activity_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consecutive_days_active: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Streak tracker
    badges_earned: Mapped[List[str]] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Achievement badges
    privileges: Mapped[Dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Current privileges
    restrictions: Mapped[List[str]] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Active restrictions
    reputation_history: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Score change history
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ReputationBonus(Base):
    """Reputation bonus awards for exceptional contributions."""

    __tablename__ = "reputation_bonuses"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    bonus_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # helpful_vote, expert_feedback, bug_discovery, etc.
    amount: Mapped[float] = mapped_column(DECIMAL(6, 2), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Detailed reason for the bonus
    related_entity_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Related feedback/job/etc.
    awarded_by: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Who awarded the bonus (auto or user)
    is_manual: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Manual or automatic award
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Temporary bonuses
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    meta_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Additional context
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class QualityAssessment(Base):
    """Automated quality assessment results for feedback."""

    __tablename__ = "quality_assessments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    feedback_id: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )
    quality_score: Mapped[float] = mapped_column(DECIMAL(5, 2), nullable=False)  # 0-100
    quality_grade: Mapped[str] = mapped_column(
        String(15), nullable=False
    )  # excellent, good, acceptable, poor, unacceptable
    issues_detected: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Quality issues found
    warnings: Mapped[List[str]] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Non-critical warnings
    auto_actions: Mapped[List[str]] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Automatic actions taken
    assessor_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="automated"
    )  # automated, human
    assessor_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # ID of assessor if human
    confidence_score: Mapped[float] = mapped_column(
        DECIMAL(3, 2), nullable=False, default=0.0
    )  # Assessment confidence
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    reviewed_by_human: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    human_reviewer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    human_override_score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(5, 2), nullable=True
    )
    human_override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assessment_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Full assessment details
    assessment_version: Mapped[str] = mapped_column(
        String(10), nullable=False, default="1.0"
    )  # Assessment algorithm version
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ReputationEvent(Base):
    """Historical tracking of reputation score changes."""

    __tablename__ = "reputation_events"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # feedback_approved, vote_cast, bonus_awarded, penalty_applied
    score_change: Mapped[float] = mapped_column(
        DECIMAL(6, 2), nullable=False
    )  # Can be positive or negative
    previous_score: Mapped[float] = mapped_column(DECIMAL(8, 2), nullable=False)
    new_score: Mapped[float] = mapped_column(DECIMAL(8, 2), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Human-readable reason
    related_entity_type: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # feedback, vote, bonus, penalty
    related_entity_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # ID of related entity
    triggered_by: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # What triggered this event
    context_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Additional context
    is_reversible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )  # Can this event be reversed?
    reversed_by: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # ID of reversal event
    event_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True
    )  # For daily/weekly aggregation
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class QualityMetric(Base):
    """Aggregated quality metrics for analytics and reporting."""

    __tablename__ = "quality_metrics"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    metric_date: Mapped[date] = mapped_column(
        Date, nullable=False, unique=True, index=True
    )  # Daily aggregation
    total_feedback_assessed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    average_quality_score: Mapped[float] = mapped_column(
        DECIMAL(5, 2), nullable=False, default=0.0
    )
    quality_distribution: Mapped[Dict[str, int]] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Score ranges and counts
    issue_type_counts: Mapped[Dict[str, int]] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Types of issues found
    auto_action_counts: Mapped[Dict[str, int]] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Actions taken automatically
    human_review_rate: Mapped[float] = mapped_column(
        DECIMAL(3, 2), nullable=False, default=0.0
    )  # Percentage requiring human review
    false_positive_rate: Mapped[float] = mapped_column(
        DECIMAL(3, 2), nullable=False, default=0.0
    )  # Incorrect auto-actions
    processing_time_avg: Mapped[float] = mapped_column(
        DECIMAL(8, 3), nullable=False, default=0.0
    )  # Average assessment time in seconds
    assessment_count_by_user_level: Mapped[Dict[str, int]] = mapped_column(
        JSONType, nullable=False, default={}
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
