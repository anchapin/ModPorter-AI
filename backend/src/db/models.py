import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    Boolean,
    String,
    Integer,
    ForeignKey,
    DateTime,
    Date,
    func,
    text,
    Column,
    Text,
    VARCHAR,
    DECIMAL,
    TIMESTAMP,
    TypeDecorator,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.orm import relationship, Mapped, mapped_column
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


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"
    __table_args__ = {"extend_existing": True}

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
    # Relationship to assets
    assets = relationship(
        "Asset", back_populates="conversion", cascade="all, delete-orphan"
    )


class ConversionResult(Base):
    __tablename__ = "conversion_results"
    __table_args__ = {"extend_existing": True}

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
    __table_args__ = {"extend_existing": True}

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
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[str] = mapped_column(
        String, nullable=False
    )  # Assuming user_id is a string for now
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
    blocks = relationship(
        "AddonBlock", back_populates="addon", cascade="all, delete-orphan"
    )
    assets = relationship(
        "AddonAsset", back_populates="addon", cascade="all, delete-orphan"
    )
    recipes = relationship(
        "AddonRecipe", back_populates="addon", cascade="all, delete-orphan"
    )


class AddonBlock(Base):
    __tablename__ = "addon_blocks"
    __table_args__ = {"extend_existing": True}

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
    behavior = relationship(
        "AddonBehavior",
        back_populates="block",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AddonAsset(Base):
    __tablename__ = "addon_assets"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    addon_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # E.g., "texture", "sound", "script"
    path: Mapped[str] = mapped_column(
        String, nullable=False
    )  # Relative path within the addon structure
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
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    block_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("addon_blocks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    data: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Behavior components, events, etc.
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
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    addon_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="CASCADE"), nullable=False
    )
    data: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Crafting recipe definition
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


# Behavior File Model for Post-Conversion Editor


class BehaviorFile(Base):
    __tablename__ = "behavior_files"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversion_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'entity_behavior', 'block_behavior', 'script', 'recipe', etc.
    content: Mapped[str] = mapped_column(Text, nullable=False)
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
    conversion = relationship("ConversionJob", backref="behavior_files")


# Feedback Models


class ConversionFeedback(Base):
    __tablename__ = "conversion_feedback"
    __table_args__ = {"extend_existing": True}

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
    vote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    helpful_count: Mapped[float] = mapped_column(
        DECIMAL(10, 2), nullable=False, default=0.0
    )
    not_helpful_count: Mapped[float] = mapped_column(
        DECIMAL(10, 2), nullable=False, default=0.0
    )

    job = relationship("ConversionJob", back_populates="feedback")


# Asset Management Models


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversion_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversion_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'texture', 'model', 'sound', 'script', etc.
    original_path: Mapped[str] = mapped_column(String, nullable=False)
    converted_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pending'"),
    )  # 'pending', 'processing', 'converted', 'failed'
    asset_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONType, nullable=True, default={}
    )
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    conversion = relationship("ConversionJob", back_populates="assets")


# Comparison Models


class ComparisonResultDb(Base):
    __tablename__ = "comparison_results"
    __table_args__ = {"extend_existing": True}

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
    __table_args__ = {"extend_existing": True}

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
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    embedding = Column(
        VECTOR(1536), nullable=False
    )  # Assuming nullable=False for embedding
    document_source = Column(String, nullable=False, index=True)
    content_hash = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# A/B Testing Models


class Experiment(Base):
    __tablename__ = "experiments"
    __table_args__ = {"extend_existing": True}

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
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
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
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiment_variants.id", ondelete="CASCADE"),
        nullable=False,
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
    result_asset_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONType, nullable=True, name="result_metadata_json"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    variant = relationship("ExperimentVariant", back_populates="results")
    # Note: Access to experiment can be achieved via result.variant.experiment


class BehaviorTemplate(Base):
    __tablename__ = "behavior_templates"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    template_type: Mapped[str] = mapped_column(String(100), nullable=False)
    template_data: Mapped[dict] = mapped_column(JSONType, nullable=False)
    tags: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    created_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
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


# Knowledge Graph Models


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    neo4j_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Neo4j element ID
    node_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'java_concept', 'bedrock_concept', 'conversion_pattern', etc.
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    properties: Mapped[dict] = mapped_column(JSONType, nullable=False, default={})
    minecraft_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="latest"
    )
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'java', 'bedrock', 'both'
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    expert_validated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    community_rating: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2), nullable=True
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

    versions = relationship(
        "KnowledgeNodeVersion", back_populates="node", cascade="all, delete-orphan"
    )


class KnowledgeNodeVersion(Base):
    __tablename__ = "knowledge_node_versions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    node_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    change_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'create', 'update', 'major_improvement'
    changes: Mapped[dict] = mapped_column(JSONType, nullable=False, default={})
    author_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship
    node = relationship("KnowledgeNode", back_populates="versions")


class KnowledgeRelationship(Base):
    __tablename__ = "knowledge_relationships"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    neo4j_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Neo4j element ID
    source_node_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_node_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # 'converts_to', 'similar_to', 'requires', etc.
    confidence_score: Mapped[float] = mapped_column(
        DECIMAL(3, 2), nullable=False, default=0.5
    )
    properties: Mapped[dict] = mapped_column(JSONType, nullable=False, default={})
    minecraft_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="latest"
    )
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    expert_validated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    community_votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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


class ConversionPattern(Base):
    __tablename__ = "conversion_patterns"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    java_pattern: Mapped[dict] = mapped_column(JSONType, nullable=False)
    bedrock_pattern: Mapped[dict] = mapped_column(JSONType, nullable=False)
    graph_representation: Mapped[dict] = mapped_column(
        JSONType, nullable=False
    )  # Cypher query pattern
    validation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # 'pending', 'validated', 'deprecated'
    community_rating: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2), nullable=True
    )
    expert_reviewed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    success_rate: Mapped[float] = mapped_column(
        DECIMAL(5, 2), nullable=False, default=0.0
    )
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minecraft_versions: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )
    tags: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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


class CommunityContribution(Base):
    __tablename__ = "community_contributions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    contributor_id: Mapped[str] = mapped_column(String, nullable=False)
    contribution_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'pattern', 'node', 'relationship', 'correction'
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    contribution_data: Mapped[dict] = mapped_column(JSONType, nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # 'pending', 'approved', 'rejected', 'needs_revision'
    votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    validation_results: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default={}
    )
    minecraft_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="latest"
    )
    tags: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
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

    # Relationships for peer review system
    reviews = relationship(
        "PeerReview", back_populates="contribution", cascade="all, delete-orphan"
    )
    workflow = relationship(
        "ReviewWorkflow",
        back_populates="contribution",
        uselist=False,
        cascade="all, delete-orphan",
    )


class VersionCompatibility(Base):
    __tablename__ = "version_compatibility"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    java_version: Mapped[str] = mapped_column(String(20), nullable=False)
    bedrock_version: Mapped[str] = mapped_column(String(20), nullable=False)
    compatibility_score: Mapped[float] = mapped_column(
        DECIMAL(3, 2), nullable=False, default=0.0
    )
    features_supported: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )
    deprecated_patterns: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )
    migration_guides: Mapped[dict] = mapped_column(JSONType, nullable=False, default={})
    auto_update_rules: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default={}
    )
    known_issues: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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


# Peer Review System Models


class PeerReview(Base):
    __tablename__ = "peer_reviews"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    contribution_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_contributions.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[str] = mapped_column(String, nullable=False)  # Reviewer user ID
    review_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="community"
    )  # 'community', 'expert', 'automated'
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # 'pending', 'approved', 'rejected', 'needs_revision'
    overall_score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2), nullable=True
    )  # 0.0-10.0 score
    technical_accuracy: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1-5 rating
    documentation_quality: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1-5 rating
    minecraft_compatibility: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1-5 rating
    innovation_value: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1-5 rating
    review_comments: Mapped[str] = mapped_column(Text, nullable=False, default="")
    suggestions: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # List of improvement suggestions
    approval_conditions: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Conditions for approval
    automated_checks: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Results of automated validation
    reviewer_confidence: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2), nullable=True
    )  # 0.0-1.0 confidence level
    review_time_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Time spent reviewing
    review_round: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # Review iteration number
    is_final_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Whether this is the final review
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
    contribution = relationship("CommunityContribution", back_populates="reviews")


class ReviewWorkflow(Base):
    __tablename__ = "review_workflows"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    contribution_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_contributions.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="standard"
    )  # 'standard', 'fast_track', 'expert', 'automated'
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # 'active', 'completed', 'suspended', 'rejected'
    current_stage: Mapped[str] = mapped_column(
        String(30), nullable=False, default="initial_review"
    )  # Workflow stage
    required_reviews: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2
    )  # Number of reviews needed
    completed_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approval_threshold: Mapped[float] = mapped_column(
        DECIMAL(3, 2), nullable=False, default=7.0
    )  # Average score needed
    auto_approve_score: Mapped[float] = mapped_column(
        DECIMAL(3, 2), nullable=False, default=8.5
    )  # Auto-approval threshold
    reject_threshold: Mapped[float] = mapped_column(
        DECIMAL(3, 2), nullable=False, default=3.0
    )  # Auto-rejection threshold
    assigned_reviewers: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # List of reviewer IDs
    reviewer_pool: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Available reviewers
    escalation_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Escalation attempts made
    deadline_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Review deadline in minutes
    automation_rules: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Automated review rules
    stage_history: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Workflow stage transitions
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
    contribution = relationship("CommunityContribution", back_populates="workflow")


class ReviewerExpertise(Base):
    __tablename__ = "reviewer_expertise"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    reviewer_id: Mapped[str] = mapped_column(String, nullable=False)  # User ID
    expertise_areas: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Areas of expertise
    minecraft_versions: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Version expertise
    java_experience_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # 1-5 scale
    bedrock_experience_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # 1-5 scale
    review_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Total reviews completed
    average_review_score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2), nullable=True
    )  # Average quality score of reviews
    approval_rate: Mapped[Optional[float]] = mapped_column(
        DECIMAL(5, 2), nullable=True
    )  # Percentage of contributions approved
    response_time_avg: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Average response time in hours
    expertise_score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2), nullable=True
    )  # Calculated expertise score
    is_active_reviewer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    max_concurrent_reviews: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3
    )  # Maximum simultaneous reviews
    current_reviews: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Currently assigned reviews
    special_permissions: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Special review permissions
    reputation_score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2), nullable=True
    )  # Community reputation
    last_active_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
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


class ReviewTemplate(Base):
    __tablename__ = "review_templates"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    template_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # 'pattern', 'node', 'relationship', 'correction'
    contribution_types: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Applicable contribution types
    review_criteria: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Review criteria list
    scoring_weights: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Weight for each criterion
    required_checks: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Mandatory checks
    automated_tests: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Automated test requirements
    approval_conditions: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Default approval conditions
    reviewer_qualifications: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Required reviewer qualifications
    default_workflow: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Default workflow configuration
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    usage_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # Times template has been used
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


class ReviewAnalytics(Base):
    __tablename__ = "review_analytics"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)  # Daily aggregation
    contributions_submitted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    contributions_approved: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    contributions_rejected: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    contributions_needing_revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    avg_review_time_hours: Mapped[Optional[float]] = mapped_column(
        DECIMAL(5, 2), nullable=True
    )
    avg_review_score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2), nullable=True
    )
    active_reviewers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reviewer_utilization: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2), nullable=True
    )  # Percentage of capacity used
    auto_approvals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    auto_rejections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manual_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    escalation_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_score_distribution: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Score ranges and counts
    reviewer_performance: Mapped[dict] = mapped_column(
        JSONType, nullable=False, default={}
    )  # Reviewer metrics
    bottlenecks: Mapped[list] = mapped_column(
        JSONType, nullable=False, default=list
    )  # Identified bottlenecks
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


# User Model (matching auth.py schema)
class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


# Feedback Vote Model
class FeedbackVote(Base):
    __tablename__ = "feedback_votes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    feedback_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversion_feedback.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String, nullable=False
    )  # Keeping as string to match other user_id usages
    vote_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'helpful', 'not_helpful'
    vote_weight: Mapped[float] = mapped_column(
        DECIMAL(3, 2), nullable=False, default=1.0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# Alias for compatibility
FeedbackEntry = ConversionFeedback
