from typing import List, Optional
from uuid import UUID as PyUUID # Renamed to avoid conflict with pydantic's UUID if any confusion

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.db import crud
from src.db.models import DocumentEmbedding as DBDocumentEmbedding # SQLAlchemy model
from src.models.embedding_models import (
    DocumentEmbeddingCreate,
    DocumentEmbeddingResponse,
    EmbeddingSearchQuery,
)

router = APIRouter()

@router.post(
    "/embeddings/",
    response_model=DocumentEmbeddingResponse,
    status_code=status.HTTP_201_CREATED, # Default to 201, will change to 200 if existing
)
async def create_or_get_embedding(
    embedding_data: DocumentEmbeddingCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new document embedding or retrieve an existing one if the content hash matches.
    - If an embedding with the same `content_hash` exists, it's returned (HTTP 200).
    - Otherwise, a new embedding record is created and returned (HTTP 201).
    """
    existing_embedding = await crud.get_document_embedding_by_hash(
        db, content_hash=embedding_data.content_hash
    )
    if existing_embedding:
        # FastAPI will automatically override the default 201 status code with 200 here
        # if we just return. For clarity, one could use Response(status_code=200)
        # but Pydantic model conversion works best by returning the ORM object directly.
        # Forcing status code change needs a Response object or changing status_code in decorator dynamically.
        # Simplest is to document that 200 is returned for existing.
        # To explicitly set status code with response_model, you'd do:
        # return JSONResponse(content=jsonable_encoder(existing_embedding), status_code=status.HTTP_200_OK)
        # However, FastAPI handles ORM model to Pydantic conversion well.
        # Let's rely on FastAPI's default behavior of ORM to Pydantic conversion which implies status 200 OK for a normal return.
        # The status_code in the decorator is for the "success" case, which is typically creation for POST.
        # To handle this cleanly, we might need to adjust how status code is set or just accept that
        # FastAPI's automatic 200 on return is standard for "found existing".
        # For now, let's assume the client is okay with a 201 even if it's pre-existing,
        # or handle it client-side by checking the payload.
        # A more RESTful way for "get or create" is PUT, or a specific "get-or-create" endpoint.
        # Given the client expects 201 or 200, let's try to manage it.
        # The simplest is to let it return 201 and the client can check hash if it needs to know.
        # Or, if we MUST return 200 for existing:
        # raise HTTPException(status_code=status.HTTP_200_OK, detail=existing_embedding)
        # This isn't ideal as HTTPException is for errors.
        # The problem is `response_model` and `status_code` are fixed in the decorator.
        # Let's re-evaluate: if found, just return it. The client will get a 200 OK by default if no specific status_code is raised.
        # The `status_code=status.HTTP_201_CREATED` in decorator is for when a new resource IS created.
        # If we just `return existing_embedding`, FastAPI should serialize it and send a 200 OK.
        # This means the decorator status_code is the "creation" path.

        # Correction: If using response_model, FastAPI usually returns 200 OK by default for POST if not specified.
        # If status_code is set in decorator, it will use that.
        # The problem is returning *different* success codes (200 vs 201) with response_model.
        # The common pattern is POST for create (201), GET for retrieve (200).
        # To adhere to the "return existing with 200"
        # We can check if it exists, and if so, return it. FastAPI will use 200.
        # If it doesn't exist, create it, and it will use the decorator's 201.
        # This seems to be how FastAPI behaves: status_code in decorator is for successful creation.
        # If the function returns without raising an exception before the point of "creation",
        # it might use 200. Let's test this assumption.
        # For this implementation, if it exists, we will return it. FastAPI should use 200.
        # If it does not exist, we create it, and FastAPI will use the decorator's 201.

        # Re-checking FastAPI docs: status_code in decorator is the default for successful responses.
        # To return a different code for existing, we need to return a Response object.
        from fastapi.responses import JSONResponse
        # We need to manually convert Pydantic model for JSONResponse
        # existing_response = DocumentEmbeddingResponse.from_orm(existing_embedding) # pydantic v1
        existing_response = DocumentEmbeddingResponse.model_validate(existing_embedding) # pydantic v2
        return JSONResponse(content=existing_response.model_dump(), status_code=status.HTTP_200_OK)

    db_embedding = await crud.create_document_embedding(
        db=db,
        embedding=embedding_data.embedding,
        document_source=embedding_data.document_source,
        content_hash=embedding_data.content_hash,
    )
    return db_embedding # Will be automatically converted to DocumentEmbeddingResponse with 201 status


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
        return [] # Return empty list, which is a valid response (200 OK)

    # ORM objects will be automatically converted to DocumentEmbeddingResponse
    return similar_embeddings

# Placeholder for future GET by ID, DELETE, etc.
# @router.get("/embeddings/{embedding_id}", response_model=DocumentEmbeddingResponse)
# async def get_embedding_by_id_route(embedding_id: PyUUID, db: AsyncSession = Depends(get_db)):
#     db_embedding = await crud.get_document_embedding_by_id(db, embedding_id=embedding_id)
#     if db_embedding is None:
#         raise HTTPException(status_code=404, detail="Embedding not found")
#     return db_embedding
