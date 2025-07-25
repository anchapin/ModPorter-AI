import uuid
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
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.orm import relationship, Mapped, mapped_column
from db.declarative_base import Base


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"
    __table_args__ = {'extend_existing': True}

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
    __table_args__ = {'extend_existing': True}

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


# Addon Management Models

class Addon(Base):
    __tablename__ = "addons"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False) # Assuming user_id is a string for now
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
        server_default=text("gen_random_uuid()"),
    )
    addon_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="CASCADE"), nullable=False
    )
    identifier: Mapped[str] = mapped_column(String, nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
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

    # Relationships
    addon = relationship("Addon", back_populates="blocks")
    behavior = relationship("AddonBehavior", back_populates="block", uselist=False, cascade="all, delete-orphan")


class AddonAsset(Base):
    __tablename__ = "addon_assets"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    addon_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False)  # E.g., "texture", "sound", "script"
    path: Mapped[str] = mapped_column(String, nullable=False) # Relative path within the addon structure
    original_filename: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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

    # Relationship
    addon = relationship("Addon", back_populates="assets")


class AddonBehavior(Base):
    __tablename__ = "addon_behaviors"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    block_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addon_blocks.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb")) # Behavior components, events, etc.
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

    # Relationship
    block = relationship("AddonBlock", back_populates="behavior")


class AddonRecipe(Base):
    __tablename__ = "addon_recipes"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    addon_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="CASCADE"), nullable=False
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb")) # Crafting recipe definition
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
    created_at: Mapped[DateTime] = mapped_column(
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
