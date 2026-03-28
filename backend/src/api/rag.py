"""
RAG Search API - Advanced RAG pipeline endpoint.

This module provides the REST API endpoint for the advanced RAG pipeline
with multi-stage reranking, query rewriting, and adaptive fusion.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class RAGSearchRequest(BaseModel):
    """Request model for RAG search."""

    query: str = Field(..., description="Search query")
    top_k: int = Field(20, description="Number of results to return")
    enable_rewrite: bool = Field(True, description="Enable query rewriting")
    enable_rerank: bool = Field(True, description="Enable reranking")
    rerank_stages: List[str] = Field(
        ["feature", "cross_encoder"], description="Reranking stages to apply"
    )
    fusion_strategy: str = Field("adaptive", description="Fusion strategy")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional filters")


class SearchResultItem(BaseModel):
    """Single search result item."""

    document_id: str
    source_path: str
    content_type: str
    score: float
    rank: int
    matched_content: Optional[str] = None


class QueryAnalysisResponse(BaseModel):
    """Query analysis response."""

    original_query: str
    rewritten_query: Optional[str] = None
    query_type: str
    complexity: str
    confidence: float


class RAGSearchResponse(BaseModel):
    """Response model for RAG search."""

    results: List[SearchResultItem]
    query_analysis: QueryAnalysisResponse
    rewritten_query: Optional[str] = None
    timing: Dict[str, float]
    stages_applied: List[str]


@router.post("/rag", response_model=RAGSearchResponse)
async def rag_search(request: RAGSearchRequest):
    """
    Execute advanced RAG pipeline search.

    This endpoint combines:
    - Query rewriting for clarification
    - Query expansion with related terms
    - Hybrid search (vector + keyword)
    - Multi-stage reranking
    - Adaptive fusion based on query type
    """
    try:
        import sys
        from pathlib import Path

        ai_engine_path = str(Path(__file__).parent.parent.parent.parent / "ai-engine")
        if ai_engine_path not in sys.path:
            sys.path.insert(0, ai_engine_path)

        from search.rag_pipeline import RAGPipeline, PipelineConfig

        config = PipelineConfig(
            enable_query_expansion=request.enable_rewrite,
            enable_reranking=request.enable_rerank,
            reranking_stages=request.rerank_stages,
            fusion_strategy=request.fusion_strategy
            if request.fusion_strategy != "adaptive"
            else "reciprocal_rank",
            max_results=request.top_k,
            cache_enabled=False,
        )

        pipeline = RAGPipeline(config)

        result = pipeline.search(request.query, top_k=request.top_k)

        results_items = []
        for r in result.results:
            results_items.append(
                SearchResultItem(
                    document_id=r.document.id,
                    source_path=r.document.source_path or "",
                    content_type=r.document.content_type or "unknown",
                    score=r.final_score,
                    rank=r.rank,
                    matched_content=r.matched_content,
                )
            )

        return RAGSearchResponse(
            results=results_items,
            query_analysis=QueryAnalysisResponse(
                original_query=result.query_analysis.original_query,
                rewritten_query=result.query_analysis.rewritten_query,
                query_type=result.query_analysis.query_type.value
                if hasattr(result.query_analysis.query_type, "value")
                else str(result.query_analysis.query_type),
                complexity=result.query_analysis.complexity.value
                if hasattr(result.query_analysis.complexity, "value")
                else str(result.query_analysis.complexity),
                confidence=result.query_analysis.confidence,
            ),
            rewritten_query=result.query_analysis.rewritten_query,
            timing=result.timing,
            stages_applied=result.reranking_stages_applied,
        )

    except ImportError as e:
        logger.error(f"Failed to import RAG pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RAG pipeline not available"
        )
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Search failed: {str(e)}"
        )


@router.get("/rag/health")
async def rag_health():
    """Health check for RAG pipeline."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
