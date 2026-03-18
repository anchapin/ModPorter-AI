"""
Pydantic schemas for Community Pattern Library API

These schemas define the request/response models for:
- Pattern submission
- Pattern browsing/search
- Ratings and reviews
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# === Category Schemas ===

class PatternCategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: int = 0


class PatternCategoryCreate(PatternCategoryBase):
    pass


class PatternCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class PatternCategory(PatternCategoryBase):
    id: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === Tag Schemas ===

class PatternTagBase(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = None


class PatternTagCreate(PatternTagBase):
    pass


class PatternTag(PatternTagBase):
    id: str
    usage_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === Pattern Schemas ===

class PatternTagResponse(BaseModel):
    """Tag info for pattern responses"""
    id: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class PatternCategoryResponse(BaseModel):
    """Category info for pattern responses"""
    id: str
    name: str
    icon: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PatternBase(BaseModel):
    name: str = Field(..., max_length=200)
    description: str
    code: str
    code_language: str = "javascript"
    category_id: str
    tag_names: List[str] = Field(default_factory=list)


class PatternCreate(PatternBase):
    author_name: str = Field(..., max_length=100)


class PatternUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    code: Optional[str] = None
    code_language: Optional[str] = None
    category_id: Optional[str] = None
    tag_names: Optional[List[str]] = None


class PatternSubmitResponse(BaseModel):
    """Response after pattern submission"""
    id: str
    name: str
    status: str
    message: str


class PatternListItem(BaseModel):
    """Pattern summary for list views"""
    id: str
    name: str
    slug: str
    description: str
    code_language: str
    category: PatternCategoryResponse
    tags: List[PatternTagResponse] = []
    author_name: str
    status: str
    version: int
    avg_rating: float
    rating_count: int
    download_count: int
    view_count: int
    is_featured: bool
    created_at: datetime
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PatternDetail(PatternListItem):
    """Full pattern details"""
    code: str
    review_comment: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    updated_at: datetime
    use_count: int

    model_config = ConfigDict(from_attributes=True)


# === Review Workflow Schemas ===

class PatternReviewAction(BaseModel):
    """Action to approve/reject a pattern"""
    action: str = Field(..., pattern="^(approve|reject)$")
    comment: Optional[str] = None


class PatternStatusResponse(BaseModel):
    """Response after review action"""
    id: str
    status: str
    review_comment: Optional[str] = None
    reviewed_at: datetime


# === Rating Schemas ===

class RatingCreate(BaseModel):
    """Submit a rating"""
    rating: int = Field(..., ge=1, le=5)


class RatingResponse(BaseModel):
    """Rating response"""
    id: str
    pattern_id: str
    user_name: str
    rating: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RatingSummary(BaseModel):
    """Summary of ratings for a pattern"""
    avg_rating: float
    rating_count: int
    rating_distribution: dict = {}  # {1: count, 2: count, ...}

    model_config = ConfigDict(from_attributes=True)


# === Review Schemas ===

class ReviewCreate(BaseModel):
    """Create a review"""
    title: str = Field(..., max_length=200)
    content: str


class ReviewUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None


class ReviewResponse(BaseModel):
    """Review response"""
    id: str
    pattern_id: str
    user_name: str
    title: str
    content: str
    helpful_count: int
    not_helpful_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    """Paginated review list"""
    reviews: List[ReviewResponse]
    total: int
    page: int
    page_size: int


# === Review Comment Schemas ===

class ReviewCommentCreate(BaseModel):
    """Add a comment to a review"""
    content: str


class ReviewCommentResponse(BaseModel):
    """Comment response"""
    id: str
    review_id: str
    user_name: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# === Review Vote Schemas ===

class ReviewVoteCreate(BaseModel):
    """Vote on a review"""
    is_helpful: bool


# === Search/Filter Schemas ===

class PatternSearchParams(BaseModel):
    """Search and filter parameters"""
    query: Optional[str] = None
    category_id: Optional[str] = None
    tag_ids: Optional[List[str]] = None
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    is_featured: Optional[bool] = None
    sort_by: str = Field("created_at", pattern="^(created_at|avg_rating|download_count|view_count|name)$")
    sort_order: str = Field("desc", pattern="^(asc|desc)$")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PatternSearchResponse(BaseModel):
    """Paginated pattern search results"""
    patterns: List[PatternListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# === Stats Schemas ===

class PatternStats(BaseModel):
    """Pattern statistics"""
    total_patterns: int
    approved_patterns: int
    pending_patterns: int
    rejected_patterns: int
    total_ratings: int
    avg_rating: float
    total_reviews: int
