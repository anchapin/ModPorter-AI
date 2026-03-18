"""
Pattern Library API for Community Pattern Sharing

Endpoints:
- Pattern submission and management
- Category and tag management
- Pattern search and browsing
- Rating and review system
- Admin review workflow
"""
import math
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.base import get_db
from db.models import User
from db import pattern_crud as crud
from schemas.pattern_schemas import (
    PatternCreate, PatternUpdate, PatternSubmitResponse,
    PatternListItem, PatternDetail,
    PatternCategoryCreate, PatternCategoryUpdate, PatternCategory,
    PatternTagCreate, PatternTag,
    PatternSearchParams, PatternSearchResponse,
    PatternReviewAction, PatternStatusResponse,
    RatingCreate, RatingResponse, RatingSummary,
    ReviewCreate, ReviewUpdate, ReviewResponse, ReviewListResponse,
    ReviewCommentCreate, ReviewCommentResponse,
    ReviewVoteCreate,
    PatternStats,
)

router = APIRouter(prefix="/patterns", tags=["Pattern Library"])


# === Dependency: Get current user (simplified for now) ===
async def get_current_user(
    credentials: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Simplified dependency to get current user.
    In production, this would verify JWT tokens.
    """
    # For now, return None (anonymous user)
    # This can be extended with proper auth
    return None


# === Category Endpoints ===

@router.get("/categories", response_model=List[PatternCategory])
async def get_categories(
    db: AsyncSession = Depends(get_db),
    active_only: bool = True
):
    """Get all pattern categories"""
    return await crud.get_categories(db, active_only)


@router.post("/categories", response_model=PatternCategory, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: PatternCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create a new category (admin only in production)"""
    # Check if category exists
    existing = await crud.get_category_by_name(data.name, db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category already exists"
        )
    
    return await crud.create_category(data, db)


@router.get("/categories/{category_id}", response_model=PatternCategory)
async def get_category(
    category_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific category"""
    category = await crud.get_category(category_id, db)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.patch("/categories/{category_id}", response_model=PatternCategory)
async def update_category(
    category_id: str,
    data: PatternCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Update a category (admin only)"""
    category = await crud.update_category(category_id, data, db)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Delete a category (admin only - soft delete)"""
    success = await crud.delete_category(category_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )


# === Tag Endpoints ===

@router.get("/tags", response_model=List[PatternTag])
async def get_tags(
    limit: int = Query(50, ge=1, le=200),
    sort_by_usage: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get all tags, optionally sorted by usage count"""
    return await crud.get_tags(db, limit, sort_by_usage)


@router.post("/tags", response_model=PatternTag, status_code=status.HTTP_201_CREATED)
async def create_tag(
    data: PatternTagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create a new tag"""
    existing = await crud.get_tag_by_name(data.name, db)
    if existing:
        return existing
    
    return await crud.create_tag(data, db)


# === Pattern Endpoints ===

@router.post("/submit", response_model=PatternSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_pattern(
    data: PatternCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Submit a new pattern for review.
    
    The pattern will be set to 'pending' status and require admin approval.
    """
    # Verify category exists
    category = await crud.get_category(data.category_id, db)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category ID"
        )
    
    # Get user info
    user_id = current_user.id if current_user else None
    author_name = current_user.name if current_user else data.author_name
    
    # Create pattern
    pattern = await crud.create_pattern(data, db, user_id)
    
    return PatternSubmitResponse(
        id=pattern.id,
        name=pattern.name,
        status=pattern.status,
        message="Pattern submitted successfully and is pending review"
    )


@router.get("/search", response_model=PatternSearchResponse)
async def search_patterns(
    query: Optional[str] = None,
    category_id: Optional[str] = None,
    tag_ids: Optional[str] = Query(None, description="Comma-separated tag IDs"),
    min_rating: Optional[float] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Search and filter patterns"""
    # Parse tag_ids
    tag_id_list = None
    if tag_ids:
        tag_id_list = [t.strip() for t in tag_ids.split(",") if t.strip()]
    
    params = PatternSearchParams(
        query=query,
        category_id=category_id,
        tag_ids=tag_id_list,
        min_rating=min_rating,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    
    patterns, total = await crud.search_patterns(params, db)
    
    return PatternSearchResponse(
        patterns=patterns,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size)
    )


@router.get("/featured", response_model=List[PatternListItem])
async def get_featured_patterns(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get featured patterns"""
    # Get patterns where is_featured is True
    params = PatternSearchParams(
        is_featured=True,
        sort_by="download_count",
        sort_order="desc",
        page=1,
        page_size=limit
    )
    patterns, _ = await crud.search_patterns(params, db)
    return patterns


@router.get("/", response_model=List[PatternListItem])
async def list_patterns(
    category_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List approved patterns"""
    params = PatternSearchParams(
        category_id=category_id,
        page=page,
        page_size=page_size
    )
    
    patterns, _ = await crud.search_patterns(params, db)
    return patterns


@router.get("/{pattern_id}", response_model=PatternDetail)
async def get_pattern(
    pattern_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get pattern details"""
    pattern = await crud.get_pattern(pattern_id, db)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    # Increment view count
    await crud.increment_view_count(pattern_id, db)
    
    return pattern


@router.get("/slug/{slug}", response_model=PatternDetail)
async def get_pattern_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get pattern by slug"""
    pattern = await crud.get_pattern_by_slug(slug, db)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    # Only approved patterns can be viewed by slug
    if pattern.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    # Increment view count
    await crud.increment_view_count(pattern.id, db)
    
    return pattern


@router.patch("/{pattern_id}", response_model=PatternDetail)
async def update_pattern(
    pattern_id: str,
    data: PatternUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Update a pattern (author or admin only)"""
    pattern = await crud.get_pattern(pattern_id, db)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    # In production, check ownership
    # if pattern.author_id != current_user.id and not current_user.is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    updated = await crud.update_pattern(pattern_id, data, db)
    return updated


@router.post("/{pattern_id}/download")
async def download_pattern(
    pattern_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Record a pattern download and return the code"""
    pattern = await crud.get_pattern(pattern_id, db)
    if not pattern or pattern.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    # Increment download count
    await crud.increment_download_count(pattern_id, db)
    
    return {"code": pattern.code}


# === Rating Endpoints ===

@router.post("/{pattern_id}/ratings", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def rate_pattern(
    pattern_id: str,
    data: RatingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Rate a pattern (1-5 stars)"""
    pattern = await crud.get_pattern(pattern_id, db)
    if not pattern or pattern.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    user_id = current_user.id if current_user else None
    user_name = current_user.name if current_user else "Anonymous"
    
    rating = await crud.rate_pattern(pattern_id, data, db, user_id, user_name)
    if not rating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not rate pattern"
        )
    
    return rating


@router.get("/{pattern_id}/ratings/summary", response_model=RatingSummary)
async def get_rating_summary(
    pattern_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get rating summary for a pattern"""
    pattern = await crud.get_pattern(pattern_id, db)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    return await crud.get_rating_summary(pattern_id, db)


# === Review Endpoints ===

@router.post("/{pattern_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    pattern_id: str,
    data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create a review for a pattern"""
    pattern = await crud.get_pattern(pattern_id, db)
    if not pattern or pattern.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    user_id = current_user.id if current_user else None
    user_name = current_user.name if current_user else "Anonymous"
    
    review = await crud.create_review(pattern_id, data, db, user_id, user_name)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this pattern"
        )
    
    return review


@router.get("/{pattern_id}/reviews", response_model=ReviewListResponse)
async def get_pattern_reviews(
    pattern_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get reviews for a pattern"""
    reviews, total = await crud.get_pattern_reviews(pattern_id, db, page, page_size)
    
    return ReviewListResponse(
        reviews=reviews,
        total=total,
        page=page,
        page_size=page_size
    )


@router.patch("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    data: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Update a review"""
    review = await crud.update_review(review_id, data, db)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    return review


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Delete a review"""
    success = await crud.delete_review(review_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )


# === Review Comment Endpoints ===

@router.post("/reviews/{review_id}/comments", response_model=ReviewCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_review_comment(
    review_id: str,
    data: ReviewCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Add a comment to a review"""
    user_id = current_user.id if current_user else None
    user_name = current_user.name if current_user else "Anonymous"
    
    comment = await crud.add_review_comment(review_id, data.content, db, user_id, user_name)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    return comment


@router.get("/reviews/{review_id}/comments", response_model=List[ReviewCommentResponse])
async def get_review_comments(
    review_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get comments for a review"""
    return await crud.get_review_comments(review_id, db)


# === Review Vote Endpoints ===

@router.post("/reviews/{review_id}/vote", response_model=BaseModel)
async def vote_review(
    review_id: str,
    data: ReviewVoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Vote on a review (helpful/not helpful)"""
    user_id = current_user.id if current_user else None
    
    vote = await crud.vote_review(review_id, data, db, user_id)
    if not vote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    return {"message": "Vote recorded"}


# === Admin Endpoints ===

@router.get("/admin/pending", response_model=List[PatternListItem])
async def get_pending_patterns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get patterns pending review (admin only)"""
    # In production, check admin role
    patterns, _ = await crud.get_pending_patterns(db, page, page_size)
    return patterns


@router.get("/admin/all", response_model=List[PatternListItem])
async def get_all_patterns(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get all patterns (admin only)"""
    # In production, check admin role
    patterns, _ = await crud.get_all_patterns(db, status, page, page_size)
    return patterns


@router.post("/admin/{pattern_id}/approve", response_model=PatternStatusResponse)
async def approve_pattern(
    pattern_id: str,
    data: PatternReviewAction,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Approve a pattern (admin only)"""
    # In production, check admin role
    user_id = current_user.id if current_user else None
    
    pattern = await crud.approve_pattern(pattern_id, user_id, data.comment, db)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    return PatternStatusResponse(
        id=pattern.id,
        status=pattern.status,
        review_comment=pattern.review_comment,
        reviewed_at=pattern.reviewed_at
    )


@router.post("/admin/{pattern_id}/reject", response_model=PatternStatusResponse)
async def reject_pattern(
    pattern_id: str,
    data: PatternReviewAction,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Reject a pattern (admin only)"""
    # In production, check admin role
    user_id = current_user.id if current_user else None
    
    if not data.comment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejection comment is required"
        )
    
    pattern = await crud.reject_pattern(pattern_id, user_id, data.comment, db)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    return PatternStatusResponse(
        id=pattern.id,
        status=pattern.status,
        review_comment=pattern.review_comment,
        reviewed_at=pattern.reviewed_at
    )


@router.post("/admin/{pattern_id}/feature", response_model=PatternDetail)
async def feature_pattern(
    pattern_id: str,
    featured: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Toggle featured status (admin only)"""
    # In production, check admin role
    pattern = await crud.feature_pattern(pattern_id, featured, db)
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pattern not found"
        )
    
    return pattern


# === Stats Endpoint ===

@router.get("/stats", response_model=PatternStats)
async def get_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get pattern library statistics"""
    return await crud.get_pattern_stats(db)
