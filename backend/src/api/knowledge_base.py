"""
Knowledge base API endpoints.

Provides endpoints for pattern submission, review, voting, and library access.
"""

import logging
import sys
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db import crud
from db.models import PatternSubmission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])


# ============================================================================
# Pydantic Models
# ============================================================================


class PatternSubmitRequest(BaseModel):
    """Request model for pattern submission."""

    java_pattern: str = Field(..., description="Java code example")
    bedrock_pattern: str = Field(..., description="Bedrock code example (JSON or JavaScript)")
    description: str = Field(
        ..., description="Pattern description (min 20 characters)", min_length=20
    )
    contributor_id: str = Field(..., description="User submitting the pattern")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    category: str = Field(..., description="Pattern category (item, block, entity, etc.)")


class PatternSubmissionResponse(BaseModel):
    """Response model for pattern submission."""

    id: str
    java_pattern: str
    bedrock_pattern: str
    description: str
    contributor_id: str
    status: str
    created_at: str
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[str] = None
    upvotes: int
    downvotes: int
    tags: List[str]
    category: str

    @classmethod
    def from_orm(cls, submission: PatternSubmission) -> "PatternSubmissionResponse":
        """Convert ORM model to Pydantic model."""
        return cls(
            id=str(submission.id),
            java_pattern=submission.java_pattern,
            bedrock_pattern=submission.bedrock_pattern,
            description=submission.description,
            contributor_id=submission.contributor_id,
            status=submission.status,
            created_at=submission.created_at.isoformat(),
            reviewed_by=submission.reviewed_by,
            review_notes=submission.review_notes,
            reviewed_at=submission.reviewed_at.isoformat() if submission.reviewed_at else None,
            upvotes=submission.upvotes,
            downvotes=submission.downvotes,
            tags=submission.tags or [],
            category=submission.category,
        )


class PatternReviewRequest(BaseModel):
    """Request model for pattern review."""

    approved: bool = Field(..., description="Whether to approve the pattern")
    notes: Optional[str] = Field(None, description="Optional review notes")


class PatternVoteRequest(BaseModel):
    """Request model for pattern voting."""

    upvote: bool = Field(..., description="True for upvote, False for downvote")


class ConversionPatternResponse(BaseModel):
    """Response model for conversion pattern."""

    id: str
    name: str
    description: str
    java_example: str
    bedrock_example: str
    category: str
    tags: List[str]
    complexity: str
    success_rate: float


# ============================================================================
# AI Engine Integration
# ============================================================================


def _get_community_manager():
    """Get CommunityPatternManager from AI engine."""
    ai_engine_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "ai-engine",
    )
    if ai_engine_path not in sys.path:
        sys.path.insert(0, ai_engine_path)

    from knowledge.community import CommunityPatternManager

    return CommunityPatternManager()


def _get_pattern_library():
    """Get PatternLibrary from AI engine."""
    ai_engine_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "ai-engine",
    )
    if ai_engine_path not in sys.path:
        sys.path.insert(0, ai_engine_path)

    from knowledge.patterns import PatternLibrary

    return PatternLibrary()


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/patterns/submit",
    response_model=PatternSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_pattern(
    request: PatternSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a new pattern for review.

    Validates the pattern and creates a pending submission.
    """
    try:
        # Get community manager
        manager = _get_community_manager()

        # Validate and create submission
        submission = await manager.submit_pattern(
            java_pattern=request.java_pattern,
            bedrock_pattern=request.bedrock_pattern,
            description=request.description,
            contributor_id=request.contributor_id,
            tags=request.tags,
            category=request.category,
        )

        # Also store in database
        db_submission = await crud.create_pattern_submission(
            db=db,
            java_pattern=request.java_pattern,
            bedrock_pattern=request.bedrock_pattern,
            description=request.description,
            contributor_id=request.contributor_id,
            tags=request.tags,
            category=request.category,
        )

        logger.info(
            f"Pattern submitted by {request.contributor_id}: "
            f"category={request.category}, id={db_submission.id}"
        )

        return PatternSubmissionResponse.from_orm(db_submission)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An unexpected error occurred.",
        )
    except Exception as e:
        logger.error(f"Error submitting pattern: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit pattern.",
        )


@router.get(
    "/patterns/pending",
    response_model=List[PatternSubmissionResponse],
)
async def get_pending_submissions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Get pending pattern submissions for review.

    Returns submissions ordered by created_at DESC.
    """
    try:
        submissions = await crud.get_pending_submissions(db, limit=limit)
        return [PatternSubmissionResponse.from_orm(submission) for submission in submissions]
    except Exception as e:
        logger.error(f"Error getting pending submissions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pending submissions.",
        )


@router.post(
    "/patterns/{submission_id}/review",
    response_model=PatternSubmissionResponse,
)
async def review_pattern(
    submission_id: str,
    request: PatternReviewRequest,
    reviewer_id: str = Query(..., description="Reviewer user ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Review a pattern submission.

    Approves or rejects the pattern and updates the library if approved.
    """
    try:
        # Get community manager
        manager = _get_community_manager()

        # Update in manager (adds to library if approved)
        await manager.review_pattern(
            submission_id=submission_id,
            reviewer_id=reviewer_id,
            approved=request.approved,
            notes=request.notes,
        )

        # Update in database
        status = "approved" if request.approved else "rejected"
        db_submission = await crud.update_pattern_submission_status(
            db=db,
            submission_id=submission_id,
            status=status,
            reviewed_by=reviewer_id,
            notes=request.notes,
        )

        logger.info(f"Pattern {submission_id} {status} by {reviewer_id}")

        return PatternSubmissionResponse.from_orm(db_submission)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="An unexpected error occurred.",
        )
    except Exception as e:
        logger.error(f"Error reviewing pattern: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to review pattern.",
        )


@router.post(
    "/patterns/{submission_id}/vote",
    response_model=PatternSubmissionResponse,
)
async def vote_on_pattern(
    submission_id: str,
    request: PatternVoteRequest,
    user_id: str = Query(..., description="User voting on the pattern"),
    db: AsyncSession = Depends(get_db),
):
    """
    Vote on a pattern submission.

    Records an upvote or downvote.
    """
    try:
        # Get community manager
        manager = _get_community_manager()

        # Update in manager
        await manager.vote_on_pattern(
            submission_id=submission_id,
            user_id=user_id,
            upvote=request.upvote,
        )

        # Update in database
        db_submission = await crud.vote_on_pattern(
            db=db,
            submission_id=submission_id,
            upvote=request.upvote,
        )

        logger.info(
            f"User {user_id} {'upvoted' if request.upvote else 'downvoted'} pattern {submission_id}"
        )

        return PatternSubmissionResponse.from_orm(db_submission)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="An unexpected error occurred.",
        )
    except Exception as e:
        logger.error(f"Error voting on pattern: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to vote on pattern.",
        )


@router.get(
    "/patterns/library",
    response_model=List[ConversionPatternResponse],
)
async def get_pattern_library(
    category: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    Get approved patterns from the library.

    Supports filtering by category and tags.
    """
    try:
        # Get pattern library
        library = _get_pattern_library()

        # Parse tags if provided
        tag_list = tags.split(",") if tags else None

        # Search library
        patterns = library.search(
            query="",  # Empty query returns all
            category=category,
            tags=tag_list,
            limit=limit,
        )

        # Convert to response format
        return [
            ConversionPatternResponse(
                id=pattern.id,
                name=pattern.name,
                description=pattern.description,
                java_example=pattern.java_example,
                bedrock_example=pattern.bedrock_example,
                category=pattern.category,
                tags=pattern.tags,
                complexity=pattern.complexity,
                success_rate=pattern.success_rate,
            )
            for pattern in patterns
        ]

    except Exception as e:
        logger.error(f"Error getting pattern library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pattern library.",
        )


class RelatedChunkResponse(BaseModel):
    """Response model for related chunk."""

    chunk_id: str
    title: str
    relationship_type: str
    confidence: float


class RelatedChunksResponse(BaseModel):
    """Response model for related chunks endpoint."""

    chunk_id: str
    related: List[RelatedChunkResponse]


def _get_cross_reference_detector():
    """Get CrossReferenceDetector from AI engine."""
    ai_engine_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "ai-engine",
    )
    if ai_engine_path not in sys.path:
        sys.path.insert(0, ai_engine_path)

    from knowledge.cross_reference import CrossReferenceDetector

    return CrossReferenceDetector()


@router.get(
    "/chunks/{chunk_id}/related",
    response_model=RelatedChunksResponse,
)
async def get_related_chunks(
    chunk_id: str,
    limit: int = 5,
    relationship_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get chunks related to a given chunk.

    Returns chunks that are semantically related based on concept relationships
    stored in the knowledge graph.

    Args:
        chunk_id: The ID of the chunk to find related chunks for
        limit: Maximum number of related chunks to return (default: 5)
        relationship_type: Optional filter for relationship type
                          (extends, implements, calls, uses, related_to)
        db: Database session
    """
    try:
        detector = _get_cross_reference_detector()

        related_chunks = await detector.find_related_chunks(
            chunk_id=chunk_id,
            limit=limit,
            relationship_type=relationship_type,
        )

        return RelatedChunksResponse(
            chunk_id=chunk_id,
            related=[
                RelatedChunkResponse(
                    chunk_id=chunk["chunk_id"],
                    title=chunk["title"],
                    relationship_type=chunk["relationship_type"],
                    confidence=chunk["confidence"],
                )
                for chunk in related_chunks
            ],
        )

    except Exception as e:
        logger.error(f"Error getting related chunks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get related chunks.",
        )


@router.post(
    "/chunks/{chunk_id}/analyze",
    status_code=status.HTTP_201_CREATED,
)
async def analyze_chunk_relationships(
    chunk_id: str,
    chunk_content: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze a chunk and store its concepts and relationships.

    This endpoint extracts concepts from the chunk content and stores
    them in the knowledge graph for future cross-reference lookups.

    Args:
        chunk_id: The ID of the chunk
        chunk_content: The text content of the chunk to analyze
        db: Database session
    """
    try:
        detector = _get_cross_reference_detector()
        await detector.initialize(db)

        result = await detector.store_concepts_and_relationships(
            chunk_id=chunk_id,
            chunk_content=chunk_content,
        )

        return {
            "chunk_id": chunk_id,
            "analyzed": result.get("stored", False),
            "concepts_count": result.get("concepts_count", 0),
            "relationships_count": result.get("relationships_count", 0),
        }

    except Exception as e:
        logger.error(f"Error analyzing chunk relationships: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze chunk.",
        )


@router.post(
    "/graph/build",
    status_code=status.HTTP_201_CREATED,
)
async def build_concept_graph(
    chunks: List[Dict[str, str]],
    db: AsyncSession = Depends(get_db),
):
    """
    Build the concept graph by processing multiple chunks.

    Takes a list of chunks and processes them to extract and store
    concepts and relationships in the knowledge graph.

    Args:
        chunks: List of chunks with 'id' and 'content' keys
        db: Database session
    """
    try:
        detector = _get_cross_reference_detector()
        await detector.initialize(db)

        result = await detector.build_concept_graph(chunks=chunks)

        return result

    except Exception as e:
        logger.error(f"Error building concept graph: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build concept graph.",
        )


# ============================================================================
# Multi-Modal Asset Endpoints (Task 5)
# ============================================================================


class TextureUploadRequest(BaseModel):
    """Request model for texture file upload."""

    file_name: str = Field(..., description="Texture file name")
    category: Optional[str] = Field(
        None, description="Texture category (blocks, items, entities, gui, environment)"
    )
    project_context: Optional[str] = Field(None, description="Project or context identifier")


class TextureMetadataResponse(BaseModel):
    """Response model for texture metadata."""

    document_id: str
    file_name: str
    width: int
    height: int
    format: str
    has_transparency: bool
    color_palette: List[str]
    texture_category: Optional[str]
    is_tileable: Optional[bool]
    animation_frames: Optional[int]
    complexity_score: Optional[float]


class ModelUploadRequest(BaseModel):
    """Request model for 3D model file upload."""

    file_name: str = Field(..., description="Model file name")
    model_type: Optional[str] = Field(
        None, description="Model type (entity, block, item, animated)"
    )
    project_context: Optional[str] = Field(None, description="Project or context identifier")


class ModelMetadataResponse(BaseModel):
    """Response model for 3D model metadata."""

    document_id: str
    file_name: str
    geometry_count: int
    cube_count: int
    bone_count: int
    texture_width: int
    texture_height: int
    animations: List[Dict[str, Any]]
    material_references: List[str]
    parent_references: List[str]
    model_type: str


class MultimodalSearchRequest(BaseModel):
    """Request model for multi-modal search."""

    query_text: str = Field(..., description="Search query text")
    content_types: Optional[List[str]] = Field(None, description="Filter by content types")
    modalities: Optional[List[str]] = Field(None, description="Filter by modalities")
    top_k: int = Field(10, description="Number of results to return")


class MultimodalSearchResponse(BaseModel):
    """Response model for multi-modal search results."""

    results: List[Dict[str, Any]]
    query: str
    total_results: int


class RelatedModalResponse(BaseModel):
    """Response model for related content across modalities."""

    document_id: str
    related_items: List[Dict[str, Any]]


@router.post(
    "/assets/texture",
    status_code=status.HTTP_201_CREATED,
    response_model=TextureMetadataResponse,
)
async def upload_texture_asset(
    file_data: str = Body(..., description="Base64 encoded texture file"),
    request: TextureUploadRequest = Depends(
        lambda: TextureUploadRequest(
            file_name="texture.png",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and index a texture file.

    Extracts metadata from PNG/JPG texture files including:
    - Dimensions, format, transparency detection
    - Dominant color palette
    - Category classification
    - Tileability detection
    - Animation frames (for animated images)
    - Visual complexity score
    """
    import base64
    import tempfile

    try:
        # Decode the file data
        file_bytes = base64.b64decode(file_data)

        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=request.file_name, delete=False) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name

        # Extract texture metadata
        try:
            from ai_engine.utils.texture_metadata_extractor import TextureMetadataExtractor

            extractor = TextureMetadataExtractor()
            metadata = extractor.extract(tmp_path)

            if metadata is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to extract texture metadata",
                )
        finally:
            # Clean up temp file
            import os

            os.unlink(tmp_path)

        # Generate document ID
        document_id = f"texture_{request.file_name}_{datetime.now(timezone.utc).timestamp()}"

        return TextureMetadataResponse(
            document_id=document_id,
            file_name=request.file_name,
            width=metadata.get("width", 0),
            height=metadata.get("height", 0),
            format=metadata.get("format", "unknown"),
            has_transparency=metadata.get("has_transparency", False),
            color_palette=metadata.get("color_palette", []),
            texture_category=metadata.get("texture_category"),
            is_tileable=metadata.get("is_tileable"),
            animation_frames=metadata.get("animation_frames"),
            complexity_score=metadata.get("complexity_score"),
        )

    except Exception as e:
        logger.error(f"Error uploading texture asset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload texture.",
        )


@router.post(
    "/assets/model",
    status_code=status.HTTP_201_CREATED,
    response_model=ModelMetadataResponse,
)
async def upload_model_asset(
    file_data: str = Body(..., description="Base64 encoded model JSON file"),
    request: ModelUploadRequest = Depends(
        lambda: ModelUploadRequest(
            file_name="model.json",
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and index a 3D model file.

    Extracts metadata from Bedrock .json model files including:
    - Geometry definition (cube count, bone count)
    - Animation data (animation names, length, loops)
    - Material references
    - Parent model references
    - Model type classification
    """
    import base64
    import tempfile
    import json

    try:
        # Decode the file data
        file_bytes = base64.b64decode(file_data)

        # Parse JSON
        model_data = json.loads(file_bytes)

        # Create temporary file for extractor
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
            json.dump(model_data, tmp_file)
            tmp_path = tmp_file.name

        # Extract model metadata
        try:
            from ai_engine.utils.model_metadata_extractor import ModelMetadataExtractor

            extractor = ModelMetadataExtractor()
            metadata = extractor.extract(tmp_path)

            if metadata is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to extract model metadata",
                )
        finally:
            # Clean up temp file
            import os

            os.unlink(tmp_path)

        # Generate document ID
        document_id = f"model_{request.file_name}_{datetime.now(timezone.utc).timestamp()}"

        return ModelMetadataResponse(
            document_id=document_id,
            file_name=request.file_name,
            geometry_count=metadata.get("geometry_count", 0),
            cube_count=metadata.get("cube_count", 0),
            bone_count=metadata.get("bone_count", 0),
            texture_width=metadata.get("texture_width", 64),
            texture_height=metadata.get("texture_height", 64),
            animations=metadata.get("animations", []),
            material_references=metadata.get("material_references", []),
            parent_references=metadata.get("parent_references", []),
            model_type=metadata.get("model_type", "entity"),
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON model file",
        )
    except Exception as e:
        logger.error(f"Error uploading model asset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload model.",
        )


@router.post(
    "/search/multimodal",
    response_model=MultimodalSearchResponse,
)
async def search_multimodal(
    request: MultimodalSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Search with content type filtering and modality-aware scoring.

    Supports filtering by:
    - Content types (texture, model, code, text, documentation)
    - Modalities (visual, textual, code)

    Applies modality-aware scoring to weight results appropriately.
    """
    try:
        from ai_engine.search.multimodal_search_engine import MultiModalSearchEngine
        from schemas.multimodal_schema import SearchQuery, ContentType

        # Convert content type strings to enums
        content_types = None
        if request.content_types:
            content_types = []
            for ct in request.content_types:
                try:
                    content_types.append(ContentType(ct))
                except ValueError:
                    pass  # Skip invalid content types

        # Create search query
        query = SearchQuery(
            query_text=request.query_text,
            content_types=content_types,
            top_k=request.top_k,
        )

        # Initialize search engine
        engine = MultiModalSearchEngine(db_session=db)

        # Perform search (empty documents would be populated from DB)
        results = await engine.search(query, {})

        return MultimodalSearchResponse(
            results=[
                {
                    "document_id": r.document.id,
                    "content_type": r.document.content_type.value,
                    "score": r.final_score,
                    "rank": r.rank,
                }
                for r in results
            ],
            query=request.query_text,
            total_results=len(results),
        )

    except Exception as e:
        logger.error(f"Error in multi-modal search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed.",
        )


@router.get(
    "/documents/{doc_id}/related-modal",
    response_model=RelatedModalResponse,
)
async def get_related_across_modalities(
    doc_id: str,
    target_modalities: Optional[str] = None,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """
    Get related content across modalities for a document.

    Given a document ID, finds related content across different modalities:
    - Code → Related textures
    - Texture → Related code
    - Text → Related documentation

    Args:
        doc_id: Document ID to find related content for
        target_modalities: Comma-separated list of target modalities (optional)
        limit: Maximum number of related items to return
    """
    try:
        from ai_engine.search.cross_modal_retriever import CrossModalRetriever

        # Parse target modalities
        modalities = None
        if target_modalities:
            modalities = [m.strip() for m in target_modalities.split(",")]

        # Initialize retriever
        retriever = CrossModalRetriever(db_session=db)

        # Find related content
        related = retriever.find_related_across_modalities(
            document_id=doc_id,
            target_modalities=modalities,
            limit=limit,
        )

        return RelatedModalResponse(
            document_id=doc_id,
            related_items=related,
        )

    except Exception as e:
        logger.error(f"Error finding related modalities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find related content.",
        )
