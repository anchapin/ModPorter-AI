"""
Pattern Library Models for Community Pattern Sharing

These models support:
- Pattern submission with categories and tags
- Review workflow (pending, approved, rejected)
- Rating and review system
- Pattern versioning
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Boolean,
    String,
    Integer,
    ForeignKey,
    DateTime,
    func,
    text,
    Column,
    Text,
    VARCHAR,
    DECIMAL,
    TIMESTAMP,
    Table,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db.declarative_base import Base


class User(Base):
    """User model for pattern authors and reviewers"""
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PatternCategory(Base):
    """Categories for organizing patterns"""
    __tablename__ = "pattern_categories"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship to patterns
    patterns = relationship("Pattern", back_populates="category")


class PatternTag(Base):
    """Tags for pattern discovery"""
    __tablename__ = "pattern_tags"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


# Association table for pattern-tag many-to-many relationship
pattern_tags = Table(
    "pattern_tags_association",
    Base.metadata,
    Column("pattern_id", UUID(as_uuid=True), ForeignKey("patterns.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("pattern_tags.id", ondelete="CASCADE"), primary_key=True),
)


class Pattern(Base):
    """
    Main pattern model for community pattern sharing.
    Supports versioning, review workflow, and publication states.
    """
    __tablename__ = "patterns"
    __table_args__ = (
        Index("idx_patterns_status", "status"),
        Index("idx_patterns_category", "category_id"),
        Index("idx_patterns_author", "author_id"),
        Index("idx_patterns_created", "created_at"),
        {"extend_existing": True}
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # Pattern identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Pattern content (code/expression)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    code_language: Mapped[str] = mapped_column(String(50), default="javascript")
    
    # Metadata
    category_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pattern_categories.id"),
        nullable=False,
    )
    
    # Author info
    author_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,  # Nullable for anon patterns
    )
    author_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Review workflow
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pending'"),
    )  # pending, approved, rejected, archived
    version: Mapped[int] = mapped_column(Integer, default=1)
    previous_version_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patterns.id"),
        nullable=True,
    )
    
    # Review info
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Stats
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Rating (cached average)
    avg_rating: Mapped[float] = mapped_column(DECIMAL(3, 2), default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Featured flag
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
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
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    category = relationship("PatternCategory", back_populates="patterns")
    tags = relationship("PatternTag", secondary=pattern_tags, back_populates="patterns")
    ratings = relationship("PatternRating", back_populates="pattern", cascade="all, delete-orphan")
    reviews = relationship("PatternReview", back_populates="pattern", cascade="all, delete-orphan")
    versions = relationship("Pattern", backref="previous_version", remote_side=[id])


class PatternRating(Base):
    """5-star ratings for patterns"""
    __tablename__ = "pattern_ratings"
    __table_args__ = (
        Index("idx_rating_pattern_user", "pattern_id", "user_id", unique=True),
        {"extend_existing": True}
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    pattern_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patterns.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,  # Nullable for anon ratings
    )
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    # Relationships
    pattern = relationship("Pattern", back_populates="ratings")


class PatternReview(Base):
    """Written reviews for patterns"""
    __tablename__ = "pattern_reviews"
    __table_args__ = (
        Index("idx_review_pattern", "pattern_id"),
        {"extend_existing": True}
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    pattern_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patterns.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Review stats
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    not_helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
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
    
    # Relationships
    pattern = relationship("Pattern", back_populates="reviews")
    comments = relationship("PatternReviewComment", back_populates="review", cascade="all, delete-orphan")
    votes = relationship("PatternReviewVote", back_populates="review", cascade="all, delete-orphan")


class PatternReviewComment(Base):
    """Comments on pattern reviews"""
    __tablename__ = "pattern_review_comments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    review_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pattern_reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    # Relationships
    review = relationship("PatternReview", back_populates="comments")


class PatternReviewVote(Base):
    """Helpful/not helpful votes on reviews"""
    __tablename__ = "pattern_review_votes"
    __table_args__ = (
        Index("idx_vote_review_user", "review_id", "user_id", unique=True),
        {"extend_existing": True}
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    review_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pattern_reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    is_helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    # Relationships
    review = relationship("PatternReview", back_populates="votes")


# Add back reference to PatternTag
PatternTag.patterns = relationship("Pattern", secondary=pattern_tags, back_populates="tags")
