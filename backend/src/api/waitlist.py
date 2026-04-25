"""Waitlist API endpoint for pre-launch signups"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import WaitlistEntry

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_waitlist_stats(db: AsyncSession) -> dict:
    """Compute waitlist statistics shared by multiple endpoints."""
    # Total count
    total_result = await db.execute(select(func.count(WaitlistEntry.id)))
    total_count = total_result.scalar() or 0

    # Calculate today (midnight UTC) and week start
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # New today
    today_result = await db.execute(
        select(func.count(WaitlistEntry.id)).where(WaitlistEntry.created_at >= today_start)
    )
    new_today = today_result.scalar() or 0

    # New this week
    week_result = await db.execute(
        select(func.count(WaitlistEntry.id)).where(WaitlistEntry.created_at >= week_start)
    )
    new_this_week = week_result.scalar() or 0

    return {
        "total_count": total_count,
        "new_today": new_today,
        "new_this_week": new_this_week,
    }


class WaitlistSignupRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    source: Optional[str] = None


class WaitlistSignupResponse(BaseModel):
    success: bool
    message: str


class WaitlistEntryResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    source: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class WaitlistStatsResponse(BaseModel):
    total_count: int
    entries: list[WaitlistEntryResponse]
    new_today: int
    new_this_week: int


@router.post(
    "/waitlist",
    response_model=WaitlistSignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join the waitlist",
    description="Add an email to the Portkit waitlist. Returns success even if already registered.",
)
async def join_waitlist(
    request: WaitlistSignupRequest,
    db: AsyncSession = Depends(get_db),
) -> WaitlistSignupResponse:
    existing = await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == request.email))
    if existing.scalar_one_or_none() is not None:
        return WaitlistSignupResponse(
            success=True,
            message="You're already on the waitlist! We'll be in touch soon.",
        )

    entry = WaitlistEntry(
        email=request.email,
        name=request.name,
        source=request.source,
    )
    db.add(entry)
    await db.commit()

    logger.info("New waitlist signup: %s", request.email)
    return WaitlistSignupResponse(
        success=True,
        message="You're on the list! We'll notify you when Portkit is ready.",
    )


@router.get(
    "/waitlist",
    response_model=WaitlistStatsResponse,
    summary="Get waitlist entries",
    description="Get all waitlist entries with optional filtering. Requires admin API key in the X-Admin-Api-Key header.",
)
async def get_waitlist(
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    x_admin_api_key: str = Header(
        ..., alias="X-Admin-Api-Key", description="Admin API key for authentication"
    ),
    db: AsyncSession = Depends(get_db),
) -> WaitlistStatsResponse:
    """Get waitlist entries with statistics."""
    from config import settings

    # Validate API key
    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # Get entries with pagination
    result = await db.execute(
        select(WaitlistEntry).order_by(WaitlistEntry.created_at.desc()).offset(offset).limit(limit)
    )
    entries = result.scalars().all()

    # Get waitlist stats
    stats = await get_waitlist_stats(db)

    return WaitlistStatsResponse(
        total_count=stats["total_count"],
        entries=[WaitlistEntryResponse.model_validate(e) for e in entries],
        new_today=stats["new_today"],
        new_this_week=stats["new_this_week"],
    )


@router.get(
    "/waitlist/stats",
    response_model=dict,
    summary="Get waitlist statistics only",
    description="Get waitlist statistics without full entries. Requires admin API key in the X-Admin-Api-Key header.",
)
async def get_waitlist_stats_only(
    x_admin_api_key: str = Header(
        ..., alias="X-Admin-Api-Key", description="Admin API key for authentication"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get waitlist statistics only."""
    from config import settings

    # Validate API key
    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # Get waitlist stats using shared helper
    stats = await get_waitlist_stats(db)

    # Get source breakdown
    source_result = await db.execute(
        select(WaitlistEntry.source, func.count(WaitlistEntry.id)).group_by(WaitlistEntry.source)
    )
    source_breakdown = {row[0] or "unknown": row[1] for row in source_result.all()}

    return {
        "total_count": stats["total_count"],
        "new_today": stats["new_today"],
        "new_this_week": stats["new_this_week"],
        "source_breakdown": source_breakdown,
    }
