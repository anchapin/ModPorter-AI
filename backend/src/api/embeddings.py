import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

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

        # We need to manually convert Pydantic model for JSONResponse
        # existing_response = DocumentEmbeddingResponse.from_orm(existing_embedding) # pydantic v1
        existing_response = DocumentEmbeddingResponse.model_validate(
            existing_embedding
        )  # pydantic v2
        return JSONResponse(content=existing_response.model_dump(), status_code=status.HTTP_200_OK)

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
    response_model=List[float],
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
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "ai-engine"
    )
    if ai_engine_path not in sys.path:
        sys.path.insert(0, ai_engine_path)

    try:
        from utils.embedding_generator import LocalEmbeddingGenerator, OpenAIEmbeddingGenerator

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

    except ImportError as e:
        logger.error("Embedding generator not available", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Embedding generator not available",
        )
    except Exception as e:
        logger.error("Error generating embeddings", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating embeddings",
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
        ChunkingStrategyFactory, DocumentMetadataExtractor = _get_ai_engine_indexing()

        # Create chunking strategy
        strategy = ChunkingStrategyFactory.create(
            request.chunking_strategy,
            chunk_size=request.chunk_size,
            overlap=request.overlap,
        )

        # Extract document metadata
        extractor = DocumentMetadataExtractor()
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
