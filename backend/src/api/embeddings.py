from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db import crud

# DocumentEmbedding import removed as it's unused
from models.embedding_models import (
    DocumentEmbeddingCreate,
    DocumentEmbeddingResponse,
    EmbeddingSearchQuery,
)

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
        return JSONResponse(
            content=existing_response.model_dump(), status_code=status.HTTP_200_OK
        )

    db_embedding = await crud.create_document_embedding(
        db=db,
        embedding=embedding_data.embedding,
        document_source=embedding_data.document_source,
        content_hash=embedding_data.content_hash,
    )
    return db_embedding  # Will be automatically converted to DocumentEmbeddingResponse with 201 status


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


# Placeholder for future GET by ID, DELETE, etc.
# @router.get("/embeddings/{embedding_id}", response_model=DocumentEmbeddingResponse)
# async def get_embedding_by_id_route(embedding_id: PyUUID, db: AsyncSession = Depends(get_db)):
#     db_embedding = await crud.get_document_embedding_by_id(db, embedding_id=embedding_id)
#     if db_embedding is None:
#         raise HTTPException(status_code=404, detail="Embedding not found")
#     return db_embedding
