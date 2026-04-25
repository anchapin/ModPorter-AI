"""Waitlist API endpoint for pre-launch signups"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import WaitlistEntry

logger = logging.getLogger(__name__)

router = APIRouter()


class WaitlistSignupRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    source: Optional[str] = None


class WaitlistSignupResponse(BaseModel):
    success: bool
    message: str


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
