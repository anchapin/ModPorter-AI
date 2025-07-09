from typing import Optional
from sqlalchemy import (
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
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from src.db.declarative_base import Base
import uuid  # For default factories in new models


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'queued'"),
    )
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship: one job -> many results and progress
    results = relationship(
        "ConversionResult", back_populates="job", cascade="all, delete-orphan"
    )
    progress = relationship(
        "JobProgress", back_populates="job", cascade="all, delete-orphan", uselist=False
    )
    # Relationship to comparison_results
    comparison_results = relationship(
        "ComparisonResultDb", back_populates="conversion_job"
    )


class ConversionResult(Base):
    __tablename__ = "conversion_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversion_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    output_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job = relationship("ConversionJob", back_populates="results")


class JobProgress(Base):
    __tablename__ = "job_progress"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversion_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    progress: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    last_update: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    job = relationship("ConversionJob", back_populates="progress")


class ConversionFeedback(Base):
    __tablename__ = "conversion_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversion_jobs.id"), nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    job = relationship("ConversionJob", back_populates="feedback")


class ComparisonResultDb(Base):
    __tablename__ = "comparison_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversion_id = Column(
        UUID(as_uuid=True), ForeignKey("conversion_jobs.id"), nullable=False
    )
    structural_diff = Column(JSONB)
    code_diff = Column(JSONB)
    asset_diff = Column(JSONB)
    assumptions_applied = Column(JSONB)
    confidence_scores = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    feature_mappings = relationship(
        "FeatureMappingDb",
        back_populates="comparison_result",
        cascade="all, delete-orphan",
    )
    conversion_job = relationship("ConversionJob", back_populates="comparison_results")


class FeatureMappingDb(Base):
    __tablename__ = "feature_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comparison_id = Column(
        UUID(as_uuid=True), ForeignKey("comparison_results.id"), nullable=False
    )
    java_feature = Column(Text)
    bedrock_equivalent = Column(Text)
    mapping_type = Column(VARCHAR(50))
    confidence_score = Column(DECIMAL(3, 2))

    comparison_result = relationship(
        "ComparisonResultDb", back_populates="feature_mappings"
    )
