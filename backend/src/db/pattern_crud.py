"""
Async CRUD operations for Community Pattern Library

Handles:
- Pattern CRUD operations
- Category and tag management
- Rating and review operations
- Search and filtering
"""
import re
import math
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, and_, or_, desc, asc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from db.models import User
from db.pattern_models import (
    Pattern, PatternCategory, PatternTag, PatternRating,
    PatternReview, PatternReviewComment, PatternReviewVote,
    pattern_tags
)


async def generate_slug(name: str, db: AsyncSession) -> str:
    """Generate a URL-safe slug from pattern name"""
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^a-z0-9\s-]', '', name.lower())
    slug = re.sub(r'[\s-]+', '-', slug)
    slug = slug.strip('-')
    
    # Check for existing slugs and append number if needed
    result = await db.execute(
        select(Pattern).filter(Pattern.slug.startswith(slug))
    )
    existing = result.scalars().all()
    if existing:
        suffix = 1
        while f"{slug}-{suffix}" in [p.slug for p in existing]:
            suffix += 1
        slug = f"{slug}-{suffix}"
    
    return slug


async def get_or_create_tags(tag_names: List[str], db: AsyncSession) -> List[PatternTag]:
    """Get or create tags by name"""
    tags = []
    for name in tag_names:
        name = name.strip().lower()
        if not name:
            continue
        
        result = await db.execute(
            select(PatternTag).filter(PatternTag.name == name)
        )
        tag = result.scalar_one_or_none()
        if not tag:
            tag = PatternTag(name=name)
            db.add(tag)
            await db.flush()
        
        tag.usage_count += 1
        tags.append(tag)
    
    return tags


# === Category CRUD ===

async def create_category(data, db: AsyncSession) -> PatternCategory:
    """Create a new category"""
    category = PatternCategory(**data.model_dump())
    db.add(category)
    await db.flush()
    return category


async def get_category(category_id: str, db: AsyncSession) -> Optional[PatternCategory]:
    """Get category by ID"""
    result = await db.execute(
        select(PatternCategory).filter(PatternCategory.id == category_id)
    )
    return result.scalar_one_or_none()


async def get_category_by_name(name: str, db: AsyncSession) -> Optional[PatternCategory]:
    """Get category by name"""
    result = await db.execute(
        select(PatternCategory).filter(PatternCategory.name == name)
    )
    return result.scalar_one_or_none()


async def get_categories(db: AsyncSession, active_only: bool = True) -> List[PatternCategory]:
    """Get all categories"""
    query = select(PatternCategory)
    if active_only:
        query = query.filter(PatternCategory.is_active == True)
    query = query.order_by(PatternCategory.sort_order, PatternCategory.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_category(category_id: str, data, db: AsyncSession) -> Optional[PatternCategory]:
    """Update a category"""
    category = await get_category(category_id, db)
    if not category:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    await db.flush()
    return category


async def delete_category(category_id: str, db: AsyncSession) -> bool:
    """Delete a category (soft delete by setting inactive)"""
    category = await get_category(category_id, db)
    if not category:
        return False
    
    category.is_active = False
    await db.flush()
    return True


# === Tag CRUD ===

async def create_tag(data, db: AsyncSession) -> PatternTag:
    """Create a new tag"""
    tag = PatternTag(**data.model_dump())
    db.add(tag)
    await db.flush()
    return tag


async def get_tag(tag_id: str, db: AsyncSession) -> Optional[PatternTag]:
    """Get tag by ID"""
    result = await db.execute(
        select(PatternTag).filter(PatternTag.id == tag_id)
    )
    return result.scalar_one_or_none()


async def get_tag_by_name(name: str, db: AsyncSession) -> Optional[PatternTag]:
    """Get tag by name"""
    result = await db.execute(
        select(PatternTag).filter(PatternTag.name == name.lower())
    )
    return result.scalar_one_or_none()


async def get_tags(db: AsyncSession, limit: int = 50, sort_by_usage: bool = True) -> List[PatternTag]:
    """Get tags, optionally sorted by usage count"""
    query = select(PatternTag)
    if sort_by_usage:
        query = query.order_by(desc(PatternTag.usage_count), PatternTag.name)
    else:
        query = query.order_by(PatternTag.name)
    query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


# === Pattern CRUD ===

async def create_pattern(data, db: AsyncSession, user_id: Optional[str] = None) -> Pattern:
    """Create a new pattern"""
    # Generate slug
    slug = await generate_slug(data.name, db)
    
    # Get or create tags
    tags = await get_or_create_tags(data.tag_names, db)
    
    # Create pattern
    pattern = Pattern(
        name=data.name,
        slug=slug,
        description=data.description,
        code=data.code,
        code_language=data.code_language,
        category_id=data.category_id,
        author_id=user_id,
        author_name=data.author_name,
        status="pending",
    )
    
    pattern.tags = tags
    db.add(pattern)
    await db.flush()
    
    return pattern


async def get_pattern(pattern_id: str, db: AsyncSession) -> Optional[Pattern]:
    """Get pattern by ID"""
    result = await db.execute(
        select(Pattern).options(
            joinedload(Pattern.category),
            joinedload(Pattern.tags)
        ).filter(Pattern.id == pattern_id)
    )
    return result.unique().scalar_one_or_none()


async def get_pattern_by_slug(slug: str, db: AsyncSession) -> Optional[Pattern]:
    """Get pattern by slug"""
    result = await db.execute(
        select(Pattern).options(
            joinedload(Pattern.category),
            joinedload(Pattern.tags)
        ).filter(Pattern.slug == slug)
    )
    return result.unique().scalar_one_or_none()


async def update_pattern(pattern_id: str, data, db: AsyncSession) -> Optional[Pattern]:
    """Update a pattern"""
    pattern = await get_pattern(pattern_id, db)
    if not pattern:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    
    # Handle tag updates
    if "tag_names" in update_data:
        tags = await get_or_create_tags(update_data.pop("tag_names"), db)
        pattern.tags = tags
    
    # Update other fields
    for field, value in update_data.items():
        if value is not None:
            setattr(pattern, field, value)
    
    # If code/name changed, increment version and set to pending
    if "code" in update_data or "name" in update_data:
        pattern.version += 1
        pattern.status = "pending"
    
    await db.flush()
    return pattern


async def delete_pattern(pattern_id: str, db: AsyncSession) -> bool:
    """Delete a pattern"""
    pattern = await get_pattern(pattern_id, db)
    if not pattern:
        return False
    
    await db.delete(pattern)
    await db.flush()
    return True


# === Pattern Search ===

async def search_patterns(params, db: AsyncSession) -> Tuple[List[Pattern], int]:
    """Search and filter patterns"""
    query = select(Pattern).options(
        joinedload(Pattern.category),
        joinedload(Pattern.tags)
    )
    
    # Only show approved patterns for public search
    query = query.filter(Pattern.status == "approved")
    
    # Apply filters
    if params.query:
        search_term = f"%{params.query}%"
        query = query.filter(
            or_(
                Pattern.name.ilike(search_term),
                Pattern.description.ilike(search_term),
                Pattern.author_name.ilike(search_term)
            )
        )
    
    if params.category_id:
        query = query.filter(Pattern.category_id == params.category_id)
    
    if params.min_rating:
        query = query.filter(Pattern.avg_rating >= params.min_rating)
    
    if params.is_featured is not None:
        query = query.filter(Pattern.is_featured == params.is_featured)
    
    if params.tag_ids:
        query = query.filter(Pattern.tags.any(PatternTag.id.in_(params.tag_ids)))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_column = {
        "created_at": Pattern.created_at,
        "avg_rating": Pattern.avg_rating,
        "download_count": Pattern.download_count,
        "view_count": Pattern.view_count,
        "name": Pattern.name,
    }.get(params.sort_by, Pattern.created_at)
    
    if params.sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Apply pagination
    offset = (params.page - 1) * params.page_size
    query = query.offset(offset).limit(params.page_size)
    
    result = await db.execute(query)
    patterns = result.unique().scalars().all()
    
    return list(patterns), total


async def get_pending_patterns(db: AsyncSession, page: int = 1, page_size: int = 20) -> Tuple[List[Pattern], int]:
    """Get patterns pending review"""
    query = select(Pattern).options(
        joinedload(Pattern.category),
        joinedload(Pattern.tags)
    ).filter(Pattern.status == "pending")
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    offset = (page - 1) * page_size
    query = query.order_by(desc(Pattern.created_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    patterns = result.unique().scalars().all()
    
    return list(patterns), total


async def get_all_patterns(db: AsyncSession, status: Optional[str] = None, page: int = 1, page_size: int = 20) -> Tuple[List[Pattern], int]:
    """Get all patterns (admin)"""
    query = select(Pattern).options(
        joinedload(Pattern.category),
        joinedload(Pattern.tags)
    )
    
    if status:
        query = query.filter(Pattern.status == status)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    offset = (page - 1) * page_size
    query = query.order_by(desc(Pattern.created_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    patterns = result.unique().scalars().all()
    
    return list(patterns), total


# === View/Download Count ===

async def increment_view_count(pattern_id: str, db: AsyncSession) -> None:
    """Increment view count"""
    result = await db.execute(
        select(Pattern).filter(Pattern.id == pattern_id)
    )
    pattern = result.scalar_one_or_none()
    if pattern:
        pattern.view_count += 1
        await db.flush()


async def increment_download_count(pattern_id: str, db: AsyncSession) -> None:
    """Increment download count"""
    result = await db.execute(
        select(Pattern).filter(Pattern.id == pattern_id)
    )
    pattern = result.scalar_one_or_none()
    if pattern:
        pattern.download_count += 1
        await db.flush()


async def increment_use_count(pattern_id: str, db: AsyncSession) -> None:
    """Increment use count"""
    result = await db.execute(
        select(Pattern).filter(Pattern.id == pattern_id)
    )
    pattern = result.scalar_one_or_none()
    if pattern:
        pattern.use_count += 1
        await db.flush()


# === Rating Functions ===

async def rate_pattern(pattern_id: str, data, db: AsyncSession, user_id: Optional[str] = None, user_name: str = "Anonymous") -> Optional[PatternRating]:
    """Rate a pattern (1-5 stars)"""
    pattern = await get_pattern(pattern_id, db)
    if not pattern or pattern.status != "approved":
        return None
    
    # Check for existing rating
    query = select(PatternRating).filter(PatternRating.pattern_id == pattern_id)
    if user_id:
        query = query.filter(PatternRating.user_id == user_id)
    else:
        query = query.filter(PatternRating.user_id.is_(None))
    
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update existing rating
        existing.rating = data.rating
        rating = existing
    else:
        # Create new rating
        rating = PatternRating(
            pattern_id=pattern_id,
            user_id=user_id,
            user_name=user_name,
            rating=data.rating
        )
        db.add(rating)
    
    await db.flush()
    
    # Update pattern's cached rating
    await update_pattern_rating_cache(pattern_id, db)
    
    return rating


async def get_pattern_rating(pattern_id: str, user_id: Optional[str], db: AsyncSession) -> Optional[PatternRating]:
    """Get user's rating for a pattern"""
    query = select(PatternRating).filter(PatternRating.pattern_id == pattern_id)
    if user_id:
        query = query.filter(PatternRating.user_id == user_id)
    else:
        query = query.filter(PatternRating.user_id.is_(None))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_rating_summary(pattern_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Get rating summary for a pattern"""
    pattern = await get_pattern(pattern_id, db)
    if not pattern:
        return {"avg_rating": 0.0, "rating_count": 0, "rating_distribution": {}}
    
    # Get all ratings
    result = await db.execute(
        select(PatternRating).filter(PatternRating.pattern_id == pattern_id)
    )
    ratings = list(result.scalars().all())
    
    if not ratings:
        return {"avg_rating": 0.0, "rating_count": 0, "rating_distribution": {}}
    
    # Calculate distribution
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total = 0
    for r in ratings:
        distribution[r.rating] = distribution.get(r.rating, 0) + 1
        total += r.rating
    
    avg = total / len(ratings)
    
    return {
        "avg_rating": round(avg, 2),
        "rating_count": len(ratings),
        "rating_distribution": distribution
    }


async def update_pattern_rating_cache(pattern_id: str, db: AsyncSession) -> None:
    """Update cached rating on pattern"""
    summary = await get_rating_summary(pattern_id, db)
    pattern = await get_pattern(pattern_id, db)
    if pattern:
        pattern.avg_rating = summary["avg_rating"]
        pattern.rating_count = summary["rating_count"]
        await db.flush()


# === Review Functions ===

async def create_review(pattern_id: str, data, db: AsyncSession, user_id: Optional[str] = None, user_name: str = "Anonymous") -> Optional[PatternReview]:
    """Create a review for a pattern"""
    pattern = await get_pattern(pattern_id, db)
    if not pattern or pattern.status != "approved":
        return None
    
    # Check for existing review from this user
    query = select(PatternReview).filter(PatternReview.pattern_id == pattern_id)
    if user_id:
        query = query.filter(PatternReview.user_id == user_id)
    
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        return None  # One review per user
    
    review = PatternReview(
        pattern_id=pattern_id,
        user_id=user_id,
        user_name=user_name,
        title=data.title,
        content=data.content
    )
    db.add(review)
    await db.flush()
    
    return review


async def get_review(review_id: str, db: AsyncSession) -> Optional[PatternReview]:
    """Get review by ID"""
    result = await db.execute(
        select(PatternReview).filter(PatternReview.id == review_id)
    )
    return result.scalar_one_or_none()


async def update_review(review_id: str, data, db: AsyncSession) -> Optional[PatternReview]:
    """Update a review"""
    review = await get_review(review_id, db)
    if not review:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)
    
    await db.flush()
    return review


async def delete_review(review_id: str, db: AsyncSession) -> bool:
    """Delete a review"""
    review = await get_review(review_id, db)
    if not review:
        return False
    
    await db.delete(review)
    await db.flush()
    return True


async def get_pattern_reviews(pattern_id: str, db: AsyncSession, page: int = 1, page_size: int = 10) -> Tuple[List[PatternReview], int]:
    """Get reviews for a pattern"""
    query = select(PatternReview).filter(PatternReview.pattern_id == pattern_id)
    
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    offset = (page - 1) * page_size
    query = query.order_by(desc(PatternReview.helpful_count), PatternReview.created_at).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    reviews = list(result.scalars().all())
    
    return reviews, total


# === Review Comment Functions ===

async def add_review_comment(review_id: str, content: str, db: AsyncSession, user_id: Optional[str] = None, user_name: str = "Anonymous") -> Optional[PatternReviewComment]:
    """Add a comment to a review"""
    review = await get_review(review_id, db)
    if not review:
        return None
    
    comment = PatternReviewComment(
        review_id=review_id,
        user_id=user_id,
        user_name=user_name,
        content=content
    )
    db.add(comment)
    await db.flush()
    
    return comment


async def get_review_comments(review_id: str, db: AsyncSession) -> List[PatternReviewComment]:
    """Get comments for a review"""
    result = await db.execute(
        select(PatternReviewComment).filter(
            PatternReviewComment.review_id == review_id
        ).order_by(PatternReviewComment.created_at)
    )
    return list(result.scalars().all())


# === Review Vote Functions ===

async def vote_review(review_id: str, data, db: AsyncSession, user_id: Optional[str] = None) -> Optional[PatternReviewVote]:
    """Vote on a review (helpful/not helpful)"""
    review = await get_review(review_id, db)
    if not review:
        return None
    
    # Check for existing vote
    query = select(PatternReviewVote).filter(PatternReviewVote.review_id == review_id)
    if user_id:
        query = query.filter(PatternReviewVote.user_id == user_id)
    
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update existing vote
        if existing.is_helpful != data.is_helpful:
            existing.is_helpful = data.is_helpful
            if data.is_helpful:
                review.helpful_count += 1
                review.not_helpful_count -= 1
            else:
                review.helpful_count -= 1
                review.not_helpful_count += 1
        vote = existing
    else:
        # Create new vote
        vote = PatternReviewVote(
            review_id=review_id,
            user_id=user_id,
            is_helpful=data.is_helpful
        )
        db.add(vote)
        
        if data.is_helpful:
            review.helpful_count += 1
        else:
            review.not_helpful_count += 1
    
    await db.flush()
    return vote


# === Admin Review Functions ===

async def approve_pattern(pattern_id: str, reviewer_id: Optional[str], comment: Optional[str], db: AsyncSession) -> Optional[Pattern]:
    """Approve a pattern"""
    result = await db.execute(
        select(Pattern).filter(Pattern.id == pattern_id)
    )
    pattern = result.scalar_one_or_none()
    if not pattern:
        return None
    
    pattern.status = "approved"
    pattern.review_comment = comment
    pattern.reviewed_by = reviewer_id
    pattern.reviewed_at = datetime.utcnow()
    pattern.published_at = datetime.utcnow()
    
    await db.flush()
    return pattern


async def reject_pattern(pattern_id: str, reviewer_id: Optional[str], comment: str, db: AsyncSession) -> Optional[Pattern]:
    """Reject a pattern"""
    result = await db.execute(
        select(Pattern).filter(Pattern.id == pattern_id)
    )
    pattern = result.scalar_one_or_none()
    if not pattern:
        return None
    
    pattern.status = "rejected"
    pattern.review_comment = comment
    pattern.reviewed_by = reviewer_id
    pattern.reviewed_at = datetime.utcnow()
    
    await db.flush()
    return pattern


async def feature_pattern(pattern_id: str, featured: bool, db: AsyncSession) -> Optional[Pattern]:
    """Toggle featured status"""
    result = await db.execute(
        select(Pattern).filter(Pattern.id == pattern_id)
    )
    pattern = result.scalar_one_or_none()
    if not pattern:
        return None
    
    pattern.is_featured = featured
    await db.flush()
    return pattern


# === Stats Functions ===

async def get_pattern_stats(db: AsyncSession) -> Dict[str, Any]:
    """Get overall pattern library stats"""
    total_result = await db.execute(select(func.count(Pattern.id)))
    total = total_result.scalar() or 0
    
    approved_result = await db.execute(
        select(func.count(Pattern.id)).filter(Pattern.status == "approved")
    )
    approved = approved_result.scalar() or 0
    
    pending_result = await db.execute(
        select(func.count(Pattern.id)).filter(Pattern.status == "pending")
    )
    pending = pending_result.scalar() or 0
    
    rejected_result = await db.execute(
        select(func.count(Pattern.id)).filter(Pattern.status == "rejected")
    )
    rejected = rejected_result.scalar() or 0
    
    ratings_result = await db.execute(select(func.count(PatternRating.id)))
    total_ratings = ratings_result.scalar() or 0
    
    if total_ratings > 0:
        avg_result = await db.execute(select(func.avg(PatternRating.rating)))
        avg_rating = avg_result.scalar() or 0
    else:
        avg_rating = 0
    
    reviews_result = await db.execute(select(func.count(PatternReview.id)))
    total_reviews = reviews_result.scalar() or 0
    
    return {
        "total_patterns": total,
        "approved_patterns": approved,
        "pending_patterns": pending,
        "rejected_patterns": rejected,
        "total_ratings": total_ratings,
        "avg_rating": round(float(avg_rating), 2),
        "total_reviews": total_reviews
    }
