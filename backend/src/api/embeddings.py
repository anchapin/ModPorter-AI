import logging
from typing import List, Optional
import uuid

import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.base import get_db
from db import crud
from db.models import DocumentEmbedding

# DocumentEmbedding import removed as it's unused
from models.embedding_models import (
    DocumentEmbeddingCreate,
    DocumentEmbeddingResponse,
    EmbeddingSearchQuery,
    EmbeddingGenerateRequest,
    IndexDocumentRequest,
    IndexDocumentResponse,
    DocumentWithChunksResponse,
    ChunkResponse,
    EnhancedSearchQuery,
    EnhancedSearchResult,
    EnhancedSearchResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/embeddings/",
    response_model=DocumentEmbeddingResponse,
    status_code=status.HTTP_201_CREATED,  # Default to 201, will change to 200 if existing
)
async def create_or_get_embedding(
    embedding_data: DocumentEmbeddingCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new document embedding or retrieve an existing one if the content hash matches.
    - If an embedding with the same `content_hash` exists, it's returned (HTTP 200).
    - Otherwise, a new embedding record is created and returned (HTTP 201).

    Status Code Handling:
    - FastAPI automatically overrides the default 201 status code with 200 for existing records.
    - For clarity, one could use `Response(status_code=200)` explicitly, but Pydantic model conversion works best
      by returning the ORM object directly.
    - To explicitly set the status code with the response model, use:
      `return JSONResponse(content=jsonable_encoder(existing_embedding), status_code=status.HTTP_200_OK)`.
    - FastAPI's default behavior of ORM to Pydantic conversion implies status 200 OK for a normal return.
    - The status_code in the decorator is for the "success" case, which is typically creation for POST.
    - A more RESTful approach for "get or create" might involve using PUT or a specific "get-or-create" endpoint.
    """
    existing_embedding = await crud.get_document_embedding_by_hash(
        db, content_hash=embedding_data.content_hash
    )
    if existing_embedding:
        from fastapi.responses import JSONResponse
        from fastapi.encoders import jsonable_encoder

        # We need to manually convert Pydantic model for JSONResponse
        # existing_response = DocumentEmbeddingResponse.from_orm(existing_embedding) # pydantic v1
        existing_response = DocumentEmbeddingResponse.model_validate(
            existing_embedding
        )  # pydantic v2
        return JSONResponse(
            content=jsonable_encoder(existing_response.model_dump()),
            status_code=status.HTTP_200_OK,
        )

    db_embedding = await crud.create_document_embedding(
        db=db,
        embedding=embedding_data.embedding,
        document_source=embedding_data.document_source,
        content_hash=embedding_data.content_hash,
    )
    return (
        db_embedding  # Will be automatically converted to DocumentEmbeddingResponse with 201 status
    )


@router.post("/embeddings/search/", response_model=List[DocumentEmbeddingResponse])
async def search_similar_embeddings(
    search_query: EmbeddingSearchQuery, db: AsyncSession = Depends(get_db)
):
    """
    Find document embeddings similar to the query_embedding.
    """
    if not search_query.query_embedding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="query_embedding must not be empty.",
        )

    similar_embeddings = await crud.find_similar_embeddings(
        db=db,
        query_embedding=search_query.query_embedding,
        limit=search_query.limit,
    )
    if not similar_embeddings:
        return []  # Return empty list, which is a valid response (200 OK)

    # ORM objects will be automatically converted to DocumentEmbeddingResponse
    return similar_embeddings


# Generate embeddings endpoint
@router.post(
    "/embeddings/generate",
    response_model=List[List[float]],
    status_code=status.HTTP_200_OK,
)
async def generate_embeddings(
    request: EmbeddingGenerateRequest,
):
    """
    Generate embeddings for text using configured embedding provider.

    This endpoint allows clients to generate embeddings without providing pre-computed vectors.
    Supports both OpenAI and local sentence-transformers models.

    Request body:
    ```json
    {
        "texts": ["text to embed", "another text"],
        "provider": "openai" | "local" | "auto"  (optional, default: "auto")
    }
    ```

    Returns:
    ```json
    [
        [0.1, 0.2, ...],  // embedding vector 1
        [0.3, 0.4, ...]   // embedding vector 2
    ]
    ```
    """
    # Import embedding generator
    import sys
    import os

    # Add ai-engine to path for embedding generator
    ai_engine_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "ai-engine",
    )
    if ai_engine_path not in sys.path:
        sys.path.insert(0, ai_engine_path)

    try:
        from utils.embedding_generator import (
            LocalEmbeddingGenerator,
            OpenAIEmbeddingGenerator,
        )

        # Determine provider
        provider = request.provider or "auto"

        # Create generator based on provider
        if provider == "openai":
            generator = OpenAIEmbeddingGenerator()
        elif provider == "local":
            generator = LocalEmbeddingGenerator()
        else:  # auto
            # Try OpenAI first, fallback to local
            generator = OpenAIEmbeddingGenerator()
            if generator._client is None:
                generator = LocalEmbeddingGenerator()

        # Generate embeddings
        results = generator.generate_embeddings(request.texts)

        # Convert to list format
        embeddings = []
        for result in results:
            if result is not None:
                embeddings.append(result.embedding.tolist())
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate embeddings",
                )

        return embeddings

    except ImportError:
        logger.error("Embedding generator not available", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        )
    except Exception:
        logger.error("Error generating embeddings", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        )


# Placeholder for future GET by ID, DELETE, etc.
# @router.get("/embeddings/{embedding_id}", response_model=DocumentEmbeddingResponse)
# async def get_embedding_by_id_route(embedding_id: PyUUID, db: AsyncSession = Depends(get_db)):
#     db_embedding = await crud.get_document_embedding_by_id(db, embedding_id=embedding_id)
#     if db_embedding is None:
#         raise HTTPException(status_code=404, detail="Embedding not found")
#     return db_embedding


# New endpoints for improved document indexing


def _get_ai_engine_indexing():
    """Get AI engine indexing module."""
    import sys
    import os

    ai_engine_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "ai-engine"
    )
    if ai_engine_path not in sys.path:
        sys.path.insert(0, ai_engine_path)

    from indexing.chunking_strategies import ChunkingStrategyFactory
    from indexing.metadata_extractor import DocumentMetadataExtractor

    return ChunkingStrategyFactory, DocumentMetadataExtractor


@router.post(
    "/embeddings/index-document",
    response_model=IndexDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def index_document(
    request: IndexDocumentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Index a document with smart chunking.

    This endpoint:
    1. Chunks the document using the specified strategy
    2. Extracts metadata from the document
    3. Generates embeddings for each chunk
    4. Stores the document hierarchy in the database

    Request body:
    ```json
    {
        "content": "Document text...",
        "source": "source-identifier",
        "metadata": {},  // optional
        "chunking_strategy": "semantic",  // "fixed", "semantic", "recursive"
        "chunk_size": 512,
        "overlap": 50
    }
    ```
    """
    try:
        # Import chunking and metadata modules
        chunking_strategy_factory, document_metadata_extractor = _get_ai_engine_indexing()

        # Create chunking strategy
        strategy = chunking_strategy_factory.create(
            request.chunking_strategy,
            chunk_size=request.chunk_size,
            overlap=request.overlap,
        )

        # Extract document metadata
        extractor = document_metadata_extractor()
        doc_metadata = extractor.extract(request.content, source=request.source)

        # Chunk the document
        chunks = strategy.chunk(
            request.content,
            chunk_size=request.chunk_size,
            overlap=request.overlap,
        )

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No content to index",
            )

        # Generate embeddings for each chunk
        chunk_texts = [chunk.content for chunk in chunks]

        # Get embedding generator
        from utils.embedding_generator import LocalEmbeddingGenerator

        embedding_gen = LocalEmbeddingGenerator()
        embeddings = embedding_gen.generate_embeddings(chunk_texts)

        # Prepare chunk data for database
        chunk_data_list = []
        for i, chunk in enumerate(chunks):
            chunk_meta = extractor.create_chunk_metadata(
                document_id="",  # Will be set when creating document
                chunk_index=i,
                total_chunks=len(chunks),
                heading_context=chunk.heading_context,
                content=chunk.content,
                doc_type=doc_metadata.document_type,
                tags=doc_metadata.tags,
                original_heading=chunk.original_heading,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
            )

            embedding = embeddings[i].embedding.tolist() if embeddings[i] else None
            if embedding is None:
                continue

            chunk_data_list.append(
                {
                    "content": chunk.content,
                    "embedding": embedding,
                    "content_hash": chunk.content_hash,
                    "metadata": chunk_meta.to_dict(),
                }
            )

        # Create document with chunks in database
        parent_doc, db_chunks = await crud.create_document_with_chunks(
            db=db,
            chunks=chunk_data_list,
            document_source=request.source,
            title=doc_metadata.title,
        )

        # Combine metadata
        combined_metadata = {
            **doc_metadata.to_dict(),
            **request.metadata,
            "chunking_strategy": request.chunking_strategy,
        }

        return IndexDocumentResponse(
            document_id=str(parent_doc.id),
            chunks_created=len(db_chunks),
            metadata=combined_metadata,
        )

    except ValueError as e:
        logger.error(f"Invalid chunking strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid chunking strategy: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error indexing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error indexing document: {str(e)}",
        )


@router.get(
    "/embeddings/documents/{document_id}",
    response_model=DocumentWithChunksResponse,
)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a document with all its chunks.

    Returns the parent document and all its child chunks.
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )

    parent_doc, chunks = await crud.get_document_with_chunks(db, doc_uuid)

    if parent_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Build chunk responses
    chunk_responses = []
    for chunk in chunks:
        chunk_meta = chunk.metadata_json or {}
        chunk_responses.append(
            ChunkResponse(
                id=str(chunk.id),
                content=chunk.content_hash,  # Return hash, not full content for security
                chunk_index=chunk.chunk_index or 0,
                heading_context=chunk_meta.get("heading_context", []),
                original_heading=chunk_meta.get("original_heading"),
                char_start=chunk_meta.get("char_start", 0),
                char_end=chunk_meta.get("char_end", 0),
                metadata=chunk_meta,
            )
        )

    return DocumentWithChunksResponse(
        id=str(parent_doc.id),
        title=parent_doc.title or "",
        document_source=parent_doc.document_source,
        metadata=parent_doc.metadata_json or {},
        chunks=chunk_responses,
    )


@router.get(
    "/embeddings/documents/{document_id}/chunks",
    response_model=List[ChunkResponse],
)
async def get_document_chunks(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all chunks for a specific document.
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )

    chunks = await crud.get_chunks_by_parent(db, doc_uuid)

    # Build chunk responses
    chunk_responses = []
    for chunk in chunks:
        chunk_meta = chunk.metadata_json or {}
        chunk_responses.append(
            ChunkResponse(
                id=str(chunk.id),
                content=chunk_meta.get("content", ""),  # Return content if available
                chunk_index=chunk.chunk_index or 0,
                heading_context=chunk_meta.get("heading_context", []),
                original_heading=chunk_meta.get("original_heading"),
                char_start=chunk_meta.get("char_start", 0),
                char_end=chunk_meta.get("char_end", 0),
                metadata=chunk_meta,
            )
        )

    return chunk_responses


# ============================================================================
# Hybrid Search API - Phase 15-02: Semantic Search Enhancement
# ============================================================================


class HybridSearchRequest(BaseModel):
    """Request model for hybrid search."""

    query: str = Field(..., description="Search query text")
    limit: int = Field(default=10, description="Maximum number of results")
    search_mode: str = Field(
        default="hybrid", description="Search mode: vector_only, keyword_only, hybrid, adaptive"
    )
    include_metadata: bool = Field(
        default=True, description="Include document metadata in response"
    )
    # Phase 15-02: New parameters for semantic search enhancement
    use_reranker: bool = Field(
        default=True, description="Enable cross-encoder re-ranking for improved results"
    )
    use_hybrid: bool = Field(
        default=True, description="Use hybrid search (vector + keyword) vs vector-only"
    )
    expand_query: bool = Field(
        default=True, description="Enable query expansion with synonyms and related terms"
    )
    diversity: float = Field(
        default=0.3, description="Diversity parameter for MMR re-ranking (0.0-1.0)"
    )
    rerank_top_k: int = Field(default=50, description="Number of top results to re-rank")


class HybridSearchResult(BaseModel):
    """Single search result with scores."""

    document_id: str
    document_source: str
    title: Optional[str] = None
    chunk_index: Optional[int] = None
    score: float
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None
    metadata: dict = {}


class HybridSearchResponse(BaseModel):
    """Response model for hybrid search."""

    results: List[HybridSearchResult]
    query: str
    total: int
    search_mode: str
    execution_time_ms: float


@router.post("/embeddings/hybrid-search", response_model=HybridSearchResponse)
async def hybrid_search(  # noqa: C901
    request: HybridSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Perform hybrid search combining vector and keyword search.

    This endpoint provides enhanced search capabilities (Phase 15-02):
    - Vector-based semantic similarity search
    - Keyword-based search (BM25 when available)
    - Query expansion with synonyms and related terms
    - Cross-encoder re-ranking for improved precision
    - Adaptive combination of both methods

    Request body:
    ```json
    {
        "query": "search query text",
        "limit": 10,
        "search_mode": "hybrid",  // vector_only, keyword_only, hybrid, adaptive
        "include_metadata": true,
        "use_reranker": true,      // Enable cross-encoder re-ranking
        "use_hybrid": true,        // Use hybrid (vector + keyword) vs vector-only
        "expand_query": true,      // Enable query expansion
        "diversity": 0.3,          // Diversity for MMR re-ranking
        "rerank_top_k": 50         // Number of results to re-rank
    }
    ```

    Returns ranked search results with scores.
    """
    import time
    import sys
    import os

    start_time = time.time()

    # Validate search mode
    valid_modes = ["vector_only", "keyword_only", "hybrid", "adaptive"]
    if request.search_mode not in valid_modes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search_mode. Must be one of: {valid_modes}",
        )

    try:
        # Setup ai-engine path
        ai_engine_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "ai-engine",
        )
        if ai_engine_path not in sys.path:
            sys.path.insert(0, ai_engine_path)

        # Phase 15-02: Import AI engine components
        from utils.embedding_generator import LocalEmbeddingGenerator, OpenAIEmbeddingGenerator

        # Import query expansion if enabled
        original_query = request.query
        expanded_query = request.query

        if request.expand_query:
            try:
                from search.query_expansion import QueryExpansionEngine

                query_expander = QueryExpansionEngine()
                # Expand the query for better recall
                expanded_result = query_expander.expand(request.query)
                if expanded_result and expanded_result.expanded_query:
                    expanded_query = expanded_result.expanded_query
                    logger.info(f"Query expanded: '{original_query}' -> '{expanded_query}'")
            except Exception as e:
                logger.warning(f"Query expansion failed: {e}, using original query")

        # Generate embedding for query (use expanded query if expansion enabled)
        generator = OpenAIEmbeddingGenerator()
        if generator._client is None:
            generator = LocalEmbeddingGenerator()

        query_to_embed = expanded_query if request.expand_query else original_query
        query_embeddings = generator.generate_embeddings([query_to_embed])
        if not query_embeddings or query_embeddings[0] is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate query embedding",
            )

        query_embedding = query_embeddings[0].embedding.tolist()

        # Get more results than needed to allow for re-ranking
        fetch_limit = (
            max(request.limit, request.rerank_top_k) if request.use_reranker else request.limit
        )

        # Perform vector search
        similar_embeddings = await crud.find_similar_embeddings(
            db=db,
            query_embedding=query_embedding,
            limit=fetch_limit,
        )

        # Build results with vector scores
        results = []
        for doc in similar_embeddings:
            doc_meta = doc.metadata_json or {}
            # Calculate actual similarity score from distance
            vector_score = 1.0 / (1.0 + (doc.distance or 0.0))

            # For hybrid mode, we would need text content for keyword scoring
            # For now, use vector score as primary
            keyword_score = None

            # Combine scores based on search mode
            if request.search_mode == "vector_only":
                final_score = vector_score
            elif request.search_mode == "keyword_only":
                final_score = keyword_score if keyword_score else 0.0
            else:  # hybrid or adaptive
                # Weighted combination: 70% vector, 30% keyword (when available)
                if keyword_score:
                    final_score = 0.7 * vector_score + 0.3 * keyword_score
                else:
                    final_score = vector_score

            result = HybridSearchResult(
                document_id=str(doc.id),
                document_source=doc.document_source,
                title=doc.title,
                chunk_index=doc.chunk_index,
                score=final_score,
                vector_score=vector_score,
                keyword_score=keyword_score,
                metadata=doc_meta if request.include_metadata else {},
            )
            results.append(result)

        # Phase 15-02: Apply re-ranking if enabled
        reranking_metadata = {}
        if request.use_reranker and len(results) > 1:
            try:
                from search.reranking_engine import CrossEncoderReRanker, EnsembleReRanker

                # Use ensemble reranker for best results
                reranker = EnsembleReRanker()

                # Convert to format expected by reranker
                from schemas.multimodal_schema import SearchResult as AISearchResult

                search_results = [
                    AISearchResult(
                        id=str(r.document_id),
                        content=r.metadata.get("content", ""),
                        source=r.document_source,
                        score=r.score,
                        metadata=r.metadata,
                    )
                    for r in results
                ]

                # Perform re-ranking
                reranked_results = reranker.rerank(query_to_embed, search_results)

                # Update results with reranked scores
                if reranked_results:
                    for i, reranked in enumerate(reranked_results):
                        if i < len(results):
                            results[i].score = reranked.score
                            reranking_metadata[f"rank_{i + 1}"] = reranked.id

                    # Re-sort by reranked scores
                    results = sorted(results, key=lambda x: x.score, reverse=True)

                    logger.info(f"Re-ranking applied to {len(results)} results")

            except Exception as e:
                logger.warning(f"Re-ranking failed: {e}, using original rankings")

        # Apply diversity if specified (MMR-like approach)
        if request.diversity > 0 and len(results) > 1:
            # Simple diversity: boost results from different sources
            seen_sources = set()
            final_results = []
            for r in results:
                if r.document_source not in seen_sources or len(final_results) >= request.limit:
                    final_results.append(r)
                    seen_sources.add(r.document_source)
                    if len(final_results) >= request.limit:
                        break
            results = final_results

        # Trim to requested limit
        results = results[: request.limit]

        execution_time = (time.time() - start_time) * 1000

        logger.info(
            f"Hybrid search completed: query='{original_query}', "
            f"expanded='{expanded_query}', results={len(results)}, "
            f"reranker={request.use_reranker}, expand={request.expand_query}, "
            f"time={execution_time:.1f}ms"
        )

        return HybridSearchResponse(
            results=results,
            query=original_query,
            total=len(results),
            search_mode=request.search_mode,
            execution_time_ms=execution_time,
        )

    except ImportError as e:
        logger.error("Required module not available", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Required module not available: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Search failed: {str(e)}"
        )


# Legacy alias for backward compatibility
@router.post("/embeddings/search/hybrid", response_model=HybridSearchResponse)
async def hybrid_search_legacy(
    request: HybridSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Legacy endpoint - redirects to /embeddings/hybrid-search"""
    return await hybrid_search(request, db)


# ============================================================================
# Enhanced Search API - Phase 15-02: Direct Search Engine Integration
# ============================================================================

# Singleton instances for search engines (lazy initialization)
_hybrid_engine = None
_reranker = None
_query_expander = None


def get_hybrid_engine():
    """Get or create singleton HybridSearchEngine instance."""
    global _hybrid_engine
    if _hybrid_engine is None:
        import sys
        import os

        ai_engine_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "ai-engine"
        )
        if ai_engine_path not in sys.path:
            sys.path.insert(0, ai_engine_path)

        from search.hybrid_search_engine import HybridSearchEngine

        _hybrid_engine = HybridSearchEngine()
        logger.info("HybridSearchEngine initialized")
    return _hybrid_engine


def get_reranker():
    """Get or create singleton CrossEncoderReRanker instance."""
    global _reranker
    if _reranker is None:
        import sys
        import os

        ai_engine_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "ai-engine"
        )
        if ai_engine_path not in sys.path:
            sys.path.insert(0, ai_engine_path)

        from search.reranking_engine import CrossEncoderReRanker

        _reranker = CrossEncoderReRanker(model_name="msmarco")
        logger.info("CrossEncoderReRanker initialized with ms-marco model")
    return _reranker


def get_query_expander():
    """Get or create singleton QueryExpansionEngine instance."""
    global _query_expander
    if _query_expander is None:
        import sys
        import os

        ai_engine_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "ai-engine"
        )
        if ai_engine_path not in sys.path:
            sys.path.insert(0, ai_engine_path)

        from search.query_expansion import QueryExpansionEngine

        _query_expander = QueryExpansionEngine()
        logger.info("QueryExpansionEngine initialized")
    return _query_expander


@router.post("/embeddings/search-enhanced/", response_model=EnhancedSearchResponse)
async def search_similar_embeddings_enhanced(
    search_query: EnhancedSearchQuery,
    db: AsyncSession = Depends(get_db),
):
    """
    Enhanced semantic search with hybrid ranking, re-ranking, and query expansion.

    Features:
    - Hybrid search: Combines vector similarity (semantic) with BM25 keyword matching
    - Cross-encoder re-ranking: Improves result quality using neural re-ranking
    - Query expansion: Expands queries with domain-specific terms and synonyms
    - Performance: Target latency < 500ms

    Parameters:
    ----------
    - use_hybrid: If True (default), combine vector + keyword search. If False, vector-only.
    - use_reranker: If True (default), apply cross-encoder re-ranking to top results.
    - expand_query: If True (default), expand query with synonyms and domain terms.
    - top_k: Number of results to return (1-100, default 10).
    - search_mode: Force specific search mode ("vector", "keyword", or "hybrid").
    - ranking_strategy: How to combine scores ("weighted_sum", "rrf", or "ensemble").

    Returns:
    -------
    - EnhancedSearchResponse with results, metadata, and performance metrics
    """
    import time

    start_time = time.time()
    original_query = search_query.query_text
    expanded_query = None
    reranked = False

    try:
        # Step 1: Query expansion (if enabled)
        if search_query.expand_query:
            expander = get_query_expander()
            expansion_result = expander.expand_query(
                original_query, strategies=["domain_expansion", "synonym_expansion"], max_expansion_terms=10
            )
            expanded_query = expansion_result.expanded_query
            logger.info(f"Query expanded: '{original_query}' -> '{expanded_query}'")
        else:
            expanded_query = original_query

        # Step 2: Generate query embedding if not provided
        query_embedding = search_query.query_embedding
        if query_embedding is None:
            # Use local embedding generation
            import sys
            import os

            ai_engine_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "ai-engine"
            )
            if ai_engine_path not in sys.path:
                sys.path.insert(0, ai_engine_path)

            from utils.embedding_generator import LocalEmbeddingGenerator

            embedding_gen = LocalEmbeddingGenerator()
            query_embeddings = embedding_gen.generate_embeddings([expanded_query])
            if not query_embeddings or query_embeddings[0] is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate query embedding"
                )
            query_embedding = query_embeddings[0].embedding.tolist()
            logger.debug(f"Generated query embedding (dim: {len(query_embedding)})")

        # Step 3: Fetch all documents from database
        # NOTE: Caching layer for documents not yet implemented.
        # For now, fetch from database (should be fast with indexed queries)
        from sqlalchemy import select

        result = await db.execute(select(DocumentEmbedding).where(DocumentEmbedding.embedding.isnot(None)).limit(1000))
        documents_db = result.scalars().all()

        if not documents_db:
            logger.warning("No documents found in database")
            return EnhancedSearchResponse(
                results=[],
                total_results=0,
                query=original_query,
                expanded_query=expanded_query,
                search_mode=search_query.search_mode,
                ranking_strategy=search_query.ranking_strategy,
                latency_ms=(time.time() - start_time) * 1000,
                hybrid_used=search_query.use_hybrid,
                reranker_used=False,
                expansion_used=search_query.expand_query,
            )

        # Convert database documents to MultiModalDocument format
        import sys
        import os

        ai_engine_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "ai-engine"
        )
        if ai_engine_path not in sys.path:
            sys.path.insert(0, ai_engine_path)

        from schemas.multimodal_schema import MultiModalDocument, ContentType

        documents = {}
        embeddings_dict = {}

        for doc_db in documents_db:
            # Create MultiModalDocument from database record
            doc = MultiModalDocument(
                id=str(doc_db.id), content=doc_db.document_source or "", content_type=ContentType.TEXT, metadata=doc_db.metadata_json or {}
            )
            documents[doc.id] = doc
            embeddings_dict[doc.id] = doc_db.embedding

        logger.info(f"Loaded {len(documents)} documents for search")

        # Step 4: Perform hybrid search
        engine = get_hybrid_engine()

        # Map search mode string to enum
        from search.hybrid_search_engine import SearchMode

        mode_map = {"vector": SearchMode.VECTOR_ONLY, "keyword": SearchMode.KEYWORD_ONLY, "hybrid": SearchMode.HYBRID}
        search_mode = mode_map.get(search_query.search_mode, SearchMode.HYBRID)

        # Determine top_k for retrieval (get more for re-ranking)
        retrieval_k = search_query.top_k * 5 if search_query.use_reranker else search_query.top_k

        from schemas.multimodal_schema import SearchQuery

        search_results = await engine.search(
            query=SearchQuery(query_text=expanded_query, top_k=retrieval_k),
            documents=documents,
            embeddings=embeddings_dict,
            query_embedding=query_embedding,
            search_mode=search_mode if search_query.use_hybrid else SearchMode.VECTOR_ONLY,
        )

        logger.info(f"Hybrid search returned {len(search_results)} candidates")

        # Step 5: Cross-encoder re-ranking (if enabled)
        final_results = search_results

        if search_query.use_reranker and search_results:
            reranker = get_reranker()

            # Re-rank top candidates (limit to 50 for performance)
            rerank_candidates = search_results[:50] if len(search_results) > 50 else search_results

            reranked_results = reranker.rerank(query=expanded_query, results=rerank_candidates, top_k=search_query.top_k)

            # Convert ReRankingResult back to EnhancedSearchResult format
            reranked = True
            final_results = []
            for rerank_result in reranked_results:
                original_result = rerank_candidates[rerank_result.original_rank - 1]
                final_results.append(
                    EnhancedSearchResult(
                        document_id=original_result.document.id,
                        content=original_result.matched_content or original_result.document.content,
                        metadata=original_result.document.metadata or {},
                        similarity_score=original_result.similarity_score,
                        keyword_score=original_result.keyword_score,
                        final_score=rerank_result.final_score,
                        rank=rerank_result.new_rank,
                        match_explanation=rerank_result.explanation,
                        reranked=True,
                        expanded_query=expanded_query if expanded_query != original_query else None,
                    )
                )

            logger.info(f"Re-ranking applied, returned {len(final_results)} results")
        else:
            # Convert search results to EnhancedSearchResult format (no re-ranking)
            final_results = [
                EnhancedSearchResult(
                    document_id=result.document.id,
                    content=result.matched_content or result.document.content,
                    metadata=result.document.metadata or {},
                    similarity_score=result.similarity_score,
                    keyword_score=result.keyword_score,
                    final_score=result.final_score,
                    rank=result.rank,
                    match_explanation=result.match_explanation,
                    reranked=False,
                    expanded_query=expanded_query if expanded_query != original_query else None,
                )
                for result in search_results[:search_query.top_k]
            ]

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Log performance
        logger.info(
            f"Enhanced search completed: {len(final_results)} results, "
            f"{latency_ms:.2f}ms, hybrid={search_query.use_hybrid}, "
            f"reranked={reranked}, expanded={search_query.expand_query}"
        )

        # Warn if latency exceeds target
        if latency_ms > 500:
            logger.warning(f"Search latency {latency_ms:.2f}ms exceeds 500ms target")

        return EnhancedSearchResponse(
            results=final_results,
            total_results=len(final_results),
            query=original_query,
            expanded_query=expanded_query if expanded_query != original_query else None,
            search_mode=search_query.search_mode,
            ranking_strategy=search_query.ranking_strategy,
            latency_ms=latency_ms,
            hybrid_used=search_query.use_hybrid,
            reranker_used=reranked,
            expansion_used=search_query.expand_query,
        )

    except Exception as e:
        logger.error(f"Error in enhanced search: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Search failed: {str(e)}")
