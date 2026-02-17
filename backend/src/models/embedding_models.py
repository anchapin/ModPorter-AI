from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List

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

    model_config = {
        "from_attributes": True  # For Pydantic V2, replaces orm_mode
    }

class EmbeddingSearchQuery(BaseModel):
    query_embedding: List[float]
    limit: int = 5

class EmbeddingSearchResult(BaseModel): # For consistent response structure if needed, though list of DocumentEmbeddingResponse is also fine
    results: List[DocumentEmbeddingResponse]

class EmbeddingGenerateRequest(BaseModel):
    """Request model for generating embeddings."""
    texts: List[str]
    provider: str = "auto"  # "openai", "local", or "auto"
