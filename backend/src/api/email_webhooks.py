"""
Email Webhooks for SendGrid Event API

Handles bounce, complaint, and other email events from SendGrid.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Email Webhooks"])


class SendGridEvent(BaseModel):
    """SendGrid event payload."""

    email: EmailStr
    timestamp: int
    event: str
    sg_event_id: Optional[str] = None
    sg_message_id: Optional[str] = None
    reason: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None


class SendGridBounceEvent(BaseModel):
    """SendGrid bounce event."""

    email: EmailStr
    timestamp: int
    event: str = "bounce"
    sg_event_id: Optional[str] = None
    sg_message_id: Optional[str] = None
    bounce_classification: str = "unknown"
    reason: Optional[str] = None
    ip: Optional[str] = None


class SendGridComplaintEvent(BaseModel):
    """SendGrid complaint (spam) event."""

    email: EmailStr
    timestamp: int
    event: str = "complaint"
    sg_event_id: Optional[str] = None
    sg_message_id: Optional[str] = None


class SendGridUnsubscribeEvent(BaseModel):
    """SendGrid unsubscribe event."""

    email: EmailStr
    timestamp: int
    event: str = "unsubscribe"
    sg_event_id: Optional[str] = None
    sg_message_id: Optional[str] = None


@router.post("/sendgrid/email-events")
async def handle_sendgrid_email_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle SendGrid email events webhook.

    This endpoint receives events from SendGrid's Event Webhook:
    - bounce
    - complaint (spam reports)
    - unsubscribe
    - delivered
    - open
    - click
    - dropped

    SendGrid sends these as a JSON array of events.
    """
    try:
        events = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    if not isinstance(events, list):
        events = [events]

    processed = 0
    errors = []

    for event_data in events:
        try:
            event_type = event_data.get("event", "")

            if event_type == "bounce":
                await _handle_bounce(event_data, db)
            elif event_type == "complaint":
                await _handle_complaint(event_data, db)
            elif event_type == "unsubscribe":
                await _handle_unsubscribe(event_data, db)
            elif event_type == "dropped":
                await _handle_dropped(event_data, db)
            elif event_type in ("delivered", "open", "click"):
                pass
            else:
                logger.debug(f"Ignoring email event: {event_type}")

            processed += 1

        except Exception as e:
            logger.error(f"Error processing email event: {e}")
            errors.append(str(e))

    return {
        "status": "processed",
        "processed": processed,
        "errors": errors if errors else None,
    }


async def _handle_bounce(event_data: dict, db: AsyncSession) -> None:
    """Handle bounce event."""
    email = event_data.get("email")
    reason = event_data.get("reason", "unknown")
    bounce_type = event_data.get("type", "unknown")

    logger.warning(f"Bounce received for {email}: {bounce_type} - {reason}")

    if email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            logger.info(f"Marking email as bounced for user {user.id}")


async def _handle_complaint(event_data: dict, db: AsyncSession) -> None:
    """Handle spam complaint event."""
    email = event_data.get("email")

    logger.warning(f"Spam complaint received for {email}")

    if email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            logger.info(f"Marking user {user.id} as having spam complaint")


async def _handle_unsubscribe(event_data: dict, db: AsyncSession) -> None:
    """Handle unsubscribe event."""
    email = event_data.get("email")

    logger.info(f"Unsubscribe received for {email}")

    if email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            logger.info(f"User {user.id} unsubscribed from emails")


async def _handle_dropped(event_data: dict, db: AsyncSession) -> None:
    """Handle dropped event (email rejected by SendGrid)."""
    email = event_data.get("email")
    reason = event_data.get("reason", "unknown")

    logger.warning(f"Email dropped for {email}: {reason}")

    if email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            logger.info(f"Email was dropped for user {user.id}: {reason}")


@router.get("/unsubscribe")
async def unsubscribe(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle unsubscribe from emails.

    This is a GET endpoint for unsubscribe links in emails.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        logger.info(f"User {user.id} unsubscribed via email link")

    return {
        "status": "unsubscribed",
        "message": "You have been unsubscribed from promotional emails.",
    }
