from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Any, Optional


class DocumentEmbeddingCreate(BaseModel):
    embedding: List[float]
    document_source: str
    content_hash: str


class DocumentEmbeddingResponse(BaseModel):
    id: UUID
    embedding: List[float]
    document_source: str
    content_hash: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}  # For Pydantic V2, replaces orm_mode


class EmbeddingSearchQuery(BaseModel):
    query_embedding: List[float]
    limit: int = 5


class EmbeddingSearchResult(
    BaseModel
):  # For consistent response structure if needed, though list of DocumentEmbeddingResponse is also fine
    results: List[DocumentEmbeddingResponse]


class EmbeddingGenerateRequest(BaseModel):
    """Request model for generating embeddings."""

    texts: List[str]
    provider: str = "auto"  # "openai", "local", or "auto"


# New models for document indexing


class IndexDocumentRequest(BaseModel):
    """Request model for indexing a document with smart chunking."""

    content: str
    source: str
    metadata: dict = {}  # Optional user-provided metadata
    chunking_strategy: str = "semantic"  # "fixed", "semantic", "recursive"
    chunk_size: int = 512
    overlap: int = 50


class IndexDocumentResponse(BaseModel):
    """Response model for document indexing."""

    document_id: str
    chunks_created: int
    metadata: dict


class ChunkResponse(BaseModel):
    """Response model for a single chunk."""

    id: str
    content: str  # Note: embedding is excluded from response
    chunk_index: int
    heading_context: list[str] = []
    original_heading: str = None
    char_start: int
    char_end: int
    metadata: dict = {}

    model_config = {"from_attributes": True}


class DocumentWithChunksResponse(BaseModel):
    """Response model for document with all chunks."""

    id: str
    title: str = None
    document_source: str
    metadata: dict = {}
    chunks: List[ChunkResponse]


# New models for enhanced search


class EnhancedSearchQuery(BaseModel):
    """Enhanced search query with hybrid search, re-ranking, and query expansion options."""

    query_text: str = Field(..., min_length=1, description="Search query text")
    query_embedding: Optional[List[float]] = Field(None, description="Optional query embedding (will generate if not provided)")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    use_hybrid: bool = Field(default=True, description="Combine vector + keyword search")
    use_reranker: bool = Field(default=True, description="Apply cross-encoder re-ranking")
    expand_query: bool = Field(default=True, description="Expand query with synonyms and domain terms")
    search_mode: str = Field(default="hybrid", pattern="^(vector|keyword|hybrid)$")
    ranking_strategy: str = Field(default="weighted_sum", pattern="^(weighted_sum|rrf|ensemble)$")


class EnhancedSearchResult(BaseModel):
    """Enhanced search result with detailed scoring and metadata."""

    document_id: str
    content: str
    metadata: Dict[str, Any]
    similarity_score: float = Field(ge=0.0, le=1.0, description="Vector similarity score")
    keyword_score: float = Field(ge=0.0, description="BM25 keyword score")
    final_score: float = Field(description="Final combined/reranked score")
    rank: int = Field(ge=1, description="Result rank")
    match_explanation: str = Field(description="Human-readable explanation of match")
    reranked: bool = Field(description="Whether cross-encoder re-ranking was applied")
    expanded_query: Optional[str] = Field(None, description="Expanded query if expansion enabled")


class EnhancedSearchResponse(BaseModel):
    """Response wrapper for enhanced search results."""

    results: List[EnhancedSearchResult]
    total_results: int
    query: str
    expanded_query: Optional[str]
    search_mode: str
    ranking_strategy: str
    latency_ms: float
    hybrid_used: bool
    reranker_used: bool
    expansion_used: bool
