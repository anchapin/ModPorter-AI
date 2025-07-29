import uuid
from datetime import datetime
from typing import Optional
import os
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
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.types import TypeDecorator
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db.declarative_base import Base

# Custom type that automatically chooses the right JSON type based on the database
class JSONType(TypeDecorator):
    impl = JSONB  # Default to JSONB for PostgreSQL
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(SQLiteJSON)
        else:
            return dialect.type_descriptor(JSONB)


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'queued'"),
    )
    input_data: Mapped[dict] = mapped_column(JSONType, nullable=False)
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
    # Relationship to feedback
    feedback = relationship(
        "ConversionFeedback", back_populates="job", cascade="all, delete-orphan"
    )


class ConversionResult(Base):
    __tablename__ = "conversion_results"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversion_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    output_data: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job = relationship("ConversionJob", back_populates="results")


class JobProgress(Base):
    __tablename__ = "job_progress"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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
    last_update: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    job = relationship("ConversionJob", back_populates="progress")


# Addon Management Models

class Addon(Base):
    __tablename__ = "addons"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False) # Assuming user_id is a string for now
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
    blocks = relationship("AddonBlock", back_populates="addon", cascade="all, delete-orphan")
    assets = relationship("AddonAsset", back_populates="addon", cascade="all, delete-orphan")
    recipes = relationship("AddonRecipe", back_populates="addon", cascade="all, delete-orphan")


class AddonBlock(Base):
    __tablename__ = "addon_blocks"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    addon_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="CASCADE"), nullable=False
    )
    identifier: Mapped[str] = mapped_column(String, nullable=False)
    properties: Mapped[dict] = mapped_column(JSONType, nullable=True, default={})
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
    addon = relationship("Addon", back_populates="blocks")
    behavior = relationship("AddonBehavior", back_populates="block", uselist=False, cascade="all, delete-orphan")


class AddonAsset(Base):
    __tablename__ = "addon_assets"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    addon_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False)  # E.g., "texture", "sound", "script"
    path: Mapped[str] = mapped_column(String, nullable=False) # Relative path within the addon structure
    original_filename: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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

    # Relationship
    addon = relationship("Addon", back_populates="assets")


class AddonBehavior(Base):
    __tablename__ = "addon_behaviors"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    block_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addon_blocks.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    data: Mapped[dict] = mapped_column(JSONType, nullable=False, default={}) # Behavior components, events, etc.
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

    # Relationship
    block = relationship("AddonBlock", back_populates="behavior")


class AddonRecipe(Base):
    __tablename__ = "addon_recipes"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    addon_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="CASCADE"), nullable=False
    )
    data: Mapped[dict] = mapped_column(JSONType, nullable=False, default={}) # Crafting recipe definition
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

    # Relationship
    addon = relationship("Addon", back_populates="recipes")


# Feedback Models

class ConversionFeedback(Base):
    __tablename__ = "conversion_feedback"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversion_jobs.id"), nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    job = relationship("ConversionJob", back_populates="feedback")


# Comparison Models

class ComparisonResultDb(Base):
    __tablename__ = "comparison_results"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversion_id = Column(
        UUID(as_uuid=True), ForeignKey("conversion_jobs.id"), nullable=False
    )
    structural_diff = Column(JSONType)
    code_diff = Column(JSONType)
    asset_diff = Column(JSONType)
    assumptions_applied = Column(JSONType)
    confidence_scores = Column(JSONType)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    feature_mappings = relationship(
        "FeatureMappingDb",
        back_populates="comparison_result",
        cascade="all, delete-orphan",
    )
    conversion_job = relationship("ConversionJob", back_populates="comparison_results")


class FeatureMappingDb(Base):
    __tablename__ = "feature_mappings"
    __table_args__ = {'extend_existing': True}

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


# Document Embedding Models

class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    embedding = Column(VECTOR(1536), nullable=False) # Assuming nullable=False for embedding
    document_source = Column(String, nullable=False, index=True)
    content_hash = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# A/B Testing Models

class Experiment(Base):
    __tablename__ = "experiments"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft, active, paused, completed
    traffic_allocation: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100
    )  # Percentage (0-100)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    variants = relationship(
        "ExperimentVariant", back_populates="experiment", cascade="all, delete-orphan"
    )
    # Note: Access to results can be achieved via experiment.variants
    # then iterating through variant.results for each variant


class ExperimentVariant(Base):
    __tablename__ = "experiment_variants"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_control: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    strategy_config: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    experiment = relationship("Experiment", back_populates="variants")
    results = relationship(
        "ExperimentResult", back_populates="variant", cascade="all, delete-orphan"
    )


class ExperimentResult(Base):
    __tablename__ = "experiment_results"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiment_variants.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    kpi_quality: Mapped[Optional[float]] = mapped_column(
        DECIMAL(5, 2), nullable=True
    )  # Quality score (0.00 to 100.00)
    kpi_speed: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Execution time in milliseconds
    kpi_cost: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 2), nullable=True
    )  # Computational cost
    user_feedback_score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2), nullable=True
    )  # User feedback score (1.0 to 5.0)
    user_feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_metadata: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True, name="metadata")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    variant = relationship("ExperimentVariant", back_populates="results")
    # Note: Access to experiment can be achieved via result.variant.experiment
