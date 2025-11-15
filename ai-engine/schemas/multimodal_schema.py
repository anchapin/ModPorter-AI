"""
Unified data schema for multi-modal RAG system.

This module defines the database schema and data models for storing
multi-modal embeddings and metadata in the advanced RAG system.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
import datetime as dt
from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Content types supported by the multi-modal RAG system."""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    MULTIMODAL = "multimodal"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"


class EmbeddingModel(str, Enum):
    """Embedding models used in the system."""
    OPENCLIP = "openclip/ViT-B-32"
    CODEBERT = "microsoft/codebert-base"
    SENTENCE_TRANSFORMER = "sentence-transformers/all-MiniLM-L6-v2"
    OPENAI_ADA = "openai/text-embedding-ada-002"
    FUSED = "fused/multimodal"


class ProcessingStatus(str, Enum):
    """Processing status for content items."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REPROCESSING = "reprocessing"


class MultiModalDocument(BaseModel):
    """
    Core document model for multi-modal content storage.

    This model represents a single document that may contain multiple
    types of content (text, code, images) with their respective embeddings.
    """

    # Core identifiers
    id: str = Field(..., description="Unique document identifier")
    content_hash: str = Field(..., description="MD5 hash of the original content")
    source_path: str = Field(..., description="Original file path or URL")

    # Content information
    content_type: ContentType = Field(..., description="Primary content type")
    content_text: Optional[str] = Field(None, description="Text content if applicable")
    content_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional content metadata")

    # Processing information
    chunk_index: Optional[int] = Field(None, description="Chunk index if document was split")
    total_chunks: Optional[int] = Field(None, description="Total number of chunks")
    processing_status: ProcessingStatus = Field(ProcessingStatus.PENDING)

    # Timestamps
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    indexed_at: Optional[dt.datetime] = Field(None)

    # Context information
    project_context: Optional[str] = Field(None, description="Project or context identifier")
    tags: List[str] = Field(default_factory=list, description="Content tags for filtering")

    class Config:
        json_encoders = {dt.datetime: lambda v: v.isoformat()}


class EmbeddingVector(BaseModel):
    """
    Embedding vector storage with metadata.

    Stores the actual vector embeddings along with information about
    how they were generated and their dimensions.
    """

    # Core identifiers
    document_id: str = Field(..., description="Reference to MultiModalDocument")
    embedding_id: str = Field(..., description="Unique embedding identifier")

    # Embedding information
    model_name: EmbeddingModel = Field(..., description="Model used to generate embedding")
    embedding_vector: List[float] = Field(..., description="The actual embedding vector")
    embedding_dimension: int = Field(..., description="Dimension of the embedding")

    # Quality metrics
    confidence_score: Optional[float] = Field(None, description="Model confidence in embedding quality")
    similarity_threshold: Optional[float] = Field(None, description="Minimum similarity for matches")

    # Processing metadata
    model_version: Optional[str] = Field(None, description="Version of the embedding model")
    preprocessing_steps: List[str] = Field(default_factory=list, description="Applied preprocessing steps")

    # Performance metrics
    generation_time_ms: Optional[float] = Field(None, description="Time to generate embedding")
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))

    class Config:
        json_encoders = {dt.datetime: lambda v: v.isoformat()}


class ImageMetadata(BaseModel):
    """
    Metadata specific to image content.

    Stores image-specific information for better context understanding
    and processing optimization.
    """

    document_id: str = Field(..., description="Reference to MultiModalDocument")

    # Image properties
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    channels: int = Field(..., description="Number of color channels")
    format: str = Field(..., description="Image format (PNG, JPG, etc.)")
    file_size_bytes: int = Field(..., description="File size in bytes")

    # Minecraft-specific metadata
    minecraft_asset_type: Optional[str] = Field(None, description="Type of Minecraft asset (block, item, entity)")
    texture_category: Optional[str] = Field(None, description="Texture category (blocks, items, entities)")
    animation_frames: Optional[int] = Field(None, description="Number of animation frames if animated")

    # Processing information
    preprocessing_applied: List[str] = Field(default_factory=list, description="Applied image preprocessing")
    color_palette: Optional[List[str]] = Field(None, description="Dominant colors in hex format")

    # Visual features
    has_transparency: bool = Field(False, description="Whether image has transparency")
    is_tileable: Optional[bool] = Field(None, description="Whether texture is tileable")
    complexity_score: Optional[float] = Field(None, description="Visual complexity score (0-1)")


class CodeMetadata(BaseModel):
    """
    Metadata specific to code content.

    Stores code-specific information for better semantic understanding
    and conversion accuracy.
    """

    document_id: str = Field(..., description="Reference to MultiModalDocument")

    # Code properties
    language: str = Field(..., description="Programming language")
    file_extension: str = Field(..., description="File extension")
    lines_of_code: int = Field(..., description="Number of lines of code")

    # Java/Minecraft specific
    package_name: Optional[str] = Field(None, description="Java package name")
    class_names: List[str] = Field(default_factory=list, description="Class names in the file")
    method_names: List[str] = Field(default_factory=list, description="Method names in the file")
    minecraft_version: Optional[str] = Field(None, description="Target Minecraft version")
    mod_loader: Optional[str] = Field(None, description="Mod loader (Forge, Fabric, etc.)")

    # Code analysis
    complexity_score: Optional[float] = Field(None, description="Code complexity score")
    dependencies: List[str] = Field(default_factory=list, description="External dependencies")
    ast_features: Optional[Dict[str, Any]] = Field(None, description="AST-based features")

    # Conversion metadata
    conversion_confidence: Optional[float] = Field(None, description="Confidence in conversion accuracy")
    conversion_notes: List[str] = Field(default_factory=list, description="Notes about conversion process")


class SearchQuery(BaseModel):
    """
    Search query model for the advanced RAG system.

    Represents a search query with context and filtering options
    for multi-modal retrieval.
    """

    # Query content
    query_text: str = Field(..., description="The search query text")
    query_context: Optional[str] = Field(None, description="Additional context for the query")

    # Search parameters
    top_k: int = Field(10, description="Number of results to return")
    similarity_threshold: float = Field(0.7, description="Minimum similarity score")

    # Filtering options
    content_types: Optional[List[ContentType]] = Field(None, description="Filter by content types")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    project_context: Optional[str] = Field(None, description="Filter by project context")
    date_range: Optional[tuple] = Field(None, description="Filter by date range")

    # Search strategy
    use_hybrid_search: bool = Field(True, description="Use hybrid search (vector + keyword)")
    enable_reranking: bool = Field(True, description="Enable result re-ranking")
    expand_query: bool = Field(True, description="Enable query expansion")

    # Model preferences
    preferred_models: Optional[List[EmbeddingModel]] = Field(None, description="Preferred embedding models")

    class Config:
        json_encoders = {dt.datetime: lambda v: v.isoformat()}


class SearchResult(BaseModel):
    """
    Search result model containing matched document and relevance information.
    """

    # Document information
    document: MultiModalDocument = Field(..., description="The matched document")

    # Relevance scores
    similarity_score: float = Field(..., description="Vector similarity score")
    keyword_score: Optional[float] = Field(None, description="Keyword matching score")
    final_score: float = Field(..., description="Final combined relevance score")

    # Ranking information
    rank: int = Field(..., description="Result rank in the search results")
    embedding_model_used: EmbeddingModel = Field(..., description="Model used for similarity calculation")

    # Context information
    matched_content: Optional[str] = Field(None, description="Specific content that matched")
    match_explanation: Optional[str] = Field(None, description="Explanation of why this result matched")

    # Metadata
    retrieved_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))

    class Config:
        json_encoders = {dt.datetime: lambda v: v.isoformat()}


class HybridSearchConfig(BaseModel):
    """
    Configuration for hybrid search combining vector and keyword search.
    """

    # Weight distribution
    vector_weight: float = Field(0.7, description="Weight for vector similarity")
    keyword_weight: float = Field(0.3, description="Weight for keyword matching")

    # Keyword search settings
    enable_fuzzy_matching: bool = Field(True, description="Enable fuzzy keyword matching")
    min_keyword_length: int = Field(3, description="Minimum keyword length")
    stemming_enabled: bool = Field(True, description="Enable keyword stemming")

    # Vector search settings
    vector_similarity_metric: str = Field("cosine", description="Similarity metric for vectors")
    normalize_vectors: bool = Field(True, description="Normalize vectors before comparison")

    # Re-ranking settings
    rerank_top_k: int = Field(50, description="Number of candidates for re-ranking")
    rerank_model: Optional[str] = Field(None, description="Model for re-ranking")


# Database schema creation utilities
def get_database_schema() -> Dict[str, Any]:
    """
    Get the database schema definition for multi-modal RAG system.

    Returns:
        Dictionary containing table definitions and indexes.
    """
    return {
        "tables": {
            "multimodal_documents": {
                "columns": [
                    {"name": "id", "type": "VARCHAR(255)", "primary_key": True},
                    {"name": "content_hash", "type": "VARCHAR(32)", "index": True},
                    {"name": "source_path", "type": "TEXT"},
                    {"name": "content_type", "type": "VARCHAR(50)", "index": True},
                    {"name": "content_text", "type": "TEXT"},
                    {"name": "content_metadata", "type": "JSONB"},
                    {"name": "chunk_index", "type": "INTEGER"},
                    {"name": "total_chunks", "type": "INTEGER"},
                    {"name": "processing_status", "type": "VARCHAR(50)", "index": True},
                    {"name": "created_at", "type": "TIMESTAMP", "default": "NOW()"},
                    {"name": "updated_at", "type": "TIMESTAMP", "default": "NOW()"},
                    {"name": "indexed_at", "type": "TIMESTAMP"},
                    {"name": "project_context", "type": "VARCHAR(255)", "index": True},
                    {"name": "tags", "type": "TEXT[]", "index": True}
                ],
                "indexes": [
                    {"name": "idx_content_type_status", "columns": ["content_type", "processing_status"]},
                    {"name": "idx_project_tags", "columns": ["project_context", "tags"]},
                    {"name": "idx_created_at", "columns": ["created_at"]}
                ]
            },
            "embedding_vectors": {
                "columns": [
                    {"name": "document_id", "type": "VARCHAR(255)", "foreign_key": "multimodal_documents.id"},
                    {"name": "embedding_id", "type": "VARCHAR(255)", "primary_key": True},
                    {"name": "model_name", "type": "VARCHAR(100)", "index": True},
                    {"name": "embedding_vector", "type": "VECTOR", "dimension": "variable"},
                    {"name": "embedding_dimension", "type": "INTEGER"},
                    {"name": "confidence_score", "type": "FLOAT"},
                    {"name": "similarity_threshold", "type": "FLOAT"},
                    {"name": "model_version", "type": "VARCHAR(50)"},
                    {"name": "preprocessing_steps", "type": "TEXT[]"},
                    {"name": "generation_time_ms", "type": "FLOAT"},
                    {"name": "created_at", "type": "TIMESTAMP", "default": "NOW()"}
                ],
                "indexes": [
                    {"name": "idx_model_dimension", "columns": ["model_name", "embedding_dimension"]},
                    {"name": "idx_vector_similarity", "type": "HNSW", "columns": ["embedding_vector"]},
                    {"name": "idx_document_model", "columns": ["document_id", "model_name"]}
                ]
            },
            "image_metadata": {
                "columns": [
                    {"name": "document_id", "type": "VARCHAR(255)", "foreign_key": "multimodal_documents.id"},
                    {"name": "width", "type": "INTEGER"},
                    {"name": "height", "type": "INTEGER"},
                    {"name": "channels", "type": "INTEGER"},
                    {"name": "format", "type": "VARCHAR(10)"},
                    {"name": "file_size_bytes", "type": "BIGINT"},
                    {"name": "minecraft_asset_type", "type": "VARCHAR(50)"},
                    {"name": "texture_category", "type": "VARCHAR(50)"},
                    {"name": "animation_frames", "type": "INTEGER"},
                    {"name": "preprocessing_applied", "type": "TEXT[]"},
                    {"name": "color_palette", "type": "TEXT[]"},
                    {"name": "has_transparency", "type": "BOOLEAN"},
                    {"name": "is_tileable", "type": "BOOLEAN"},
                    {"name": "complexity_score", "type": "FLOAT"}
                ],
                "indexes": [
                    {"name": "idx_asset_type", "columns": ["minecraft_asset_type"]},
                    {"name": "idx_texture_category", "columns": ["texture_category"]},
                    {"name": "idx_dimensions", "columns": ["width", "height"]}
                ]
            },
            "code_metadata": {
                "columns": [
                    {"name": "document_id", "type": "VARCHAR(255)", "foreign_key": "multimodal_documents.id"},
                    {"name": "language", "type": "VARCHAR(50)", "index": True},
                    {"name": "file_extension", "type": "VARCHAR(10)"},
                    {"name": "lines_of_code", "type": "INTEGER"},
                    {"name": "package_name", "type": "VARCHAR(255)"},
                    {"name": "class_names", "type": "TEXT[]"},
                    {"name": "method_names", "type": "TEXT[]"},
                    {"name": "minecraft_version", "type": "VARCHAR(20)"},
                    {"name": "mod_loader", "type": "VARCHAR(50)"},
                    {"name": "complexity_score", "type": "FLOAT"},
                    {"name": "dependencies", "type": "TEXT[]"},
                    {"name": "ast_features", "type": "JSONB"},
                    {"name": "conversion_confidence", "type": "FLOAT"},
                    {"name": "conversion_notes", "type": "TEXT[]"}
                ],
                "indexes": [
                    {"name": "idx_language_version", "columns": ["language", "minecraft_version"]},
                    {"name": "idx_package_class", "columns": ["package_name", "class_names"]},
                    {"name": "idx_complexity", "columns": ["complexity_score"]}
                ]
            }
        },
        "extensions": [
            "vector",  # For vector similarity search
            "pg_trgm"  # For fuzzy text matching
        ]
    }
