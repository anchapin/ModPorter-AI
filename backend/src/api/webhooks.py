"""
Webhook Management API

Provides endpoints for enterprise customers to configure webhook notifications
for batch conversion completion events.

Issue #1501 - Enterprise Phase 1: Webhook Notifications for Batch Completion
Issue #1536 - Security: Rate limiting for webhook management endpoints
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.base import get_db
from db.models import User
from api._authz import get_current_user
from services.rate_limiter import (
    RateLimitConfig,
    webhook_rate_limiter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhook Management"])


async def _check_webhook_rate_limit(request: Request, user_id: str, user_tier: str) -> None:
    """
    Check rate limit for webhook endpoints.
    Raises HTTPException 429 if rate limit exceeded.
    """
    from starlette.datastructures import Headers

    class MockRequest:
        def __init__(self, uid: str, tier: str, client_host: str = "127.0.0.1"):
            self.state = type("State", (), {"user_id": uid, "user_tier": tier})()
            self.client = type("Client", (), {"host": client_host})()
            self.headers = Headers()

    base_config = RateLimitConfig(
        requests_per_minute=20,
        requests_per_hour=100,
        burst_size=5,
    )

    mock_request = MockRequest(user_id, user_tier)
    is_allowed, metadata = await webhook_rate_limiter.check_rate_limit(
        mock_request, override_config=base_config
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Webhook rate limit exceeded for {user_tier} tier. Maximum {metadata['limit_minute']} requests per minute.",
                "retry_after": metadata.get("retry_after", 60),
                "rate_limit": {
                    "limit": metadata["limit_minute"],
                    "remaining": metadata["remaining_minute"],
                    "reset_at": metadata["reset_at_minute"],
                },
            },
        )


class WebhookConfigRequest(BaseModel):
    """Request to configure webhook URL."""

    webhook_url: str = Field(..., description="Webhook endpoint URL")
    webhook_secret: Optional[str] = Field(
        None, description="Optional secret for HMAC signature verification"
    )


class WebhookConfigResponse(BaseModel):
    """Webhook configuration response."""

    webhook_url: Optional[str] = None
    webhook_secret_set: bool = False
    message: str


class WebhookTestRequest(BaseModel):
    """Request to test webhook configuration."""

    webhook_url: str = Field(..., description="Webhook endpoint URL to test")


class WebhookTestResponse(BaseModel):
    """Webhook test response."""

    success: bool
    status_code: Optional[int] = None
    message: str


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery record response."""

    id: str
    webhook_url: str
    event_type: str
    status: str
    attempts: int
    response_status: Optional[int] = None
    error_message: Optional[str] = None
    created_at: str
    last_attempt_at: Optional[str] = None


@router.get("/config", response_model=WebhookConfigResponse)
async def get_webhook_config(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current webhook configuration for the authenticated user.

    Returns the configured webhook URL and whether a secret is set.
    """
    user_id = str(current_user.id)

    if current_user.subscription_tier != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook configuration is only available for enterprise customers",
        )

    await _check_webhook_rate_limit(request, user_id, current_user.subscription_tier)

    return WebhookConfigResponse(
        webhook_url=current_user.webhook_url,
        webhook_secret_set=current_user.webhook_secret is not None,
        message="Webhook configuration retrieved"
        if current_user.webhook_url
        else "No webhook configured",
    )


@router.post("/config", response_model=WebhookConfigResponse)
async def set_webhook_config(
    request: Request,
    request_body: WebhookConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Configure webhook URL for the authenticated enterprise user.

    The webhook will receive POST requests when batch conversions complete.
    """
    user_id = str(current_user.id)

    if current_user.subscription_tier != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook configuration is only available for enterprise customers",
        )

    await _check_webhook_rate_limit(request, user_id, current_user.subscription_tier)

    # Validate URL format
    if not request_body.webhook_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook URL must start with http:// or https://",
        )

    current_user.webhook_url = request_body.webhook_url
    if request_body.webhook_secret:
        current_user.webhook_secret = request_body.webhook_secret

    await db.commit()

    logger.info(f"Webhook configured for user {user_id}: {request_body.webhook_url}")

    return WebhookConfigResponse(
        webhook_url=request_body.webhook_url,
        webhook_secret_set=request_body.webhook_secret is not None,
        message="Webhook configuration updated successfully",
    )


@router.delete("/config", response_model=WebhookConfigResponse)
async def delete_webhook_config(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove webhook configuration for the authenticated user.
    """
    user_id = str(current_user.id)

    if current_user.subscription_tier != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook configuration is only available for enterprise customers",
        )

    await _check_webhook_rate_limit(request, user_id, current_user.subscription_tier)

    current_user.webhook_url = None
    current_user.webhook_secret = None

    await db.commit()

    logger.info(f"Webhook removed for user {user_id}")

    return WebhookConfigResponse(
        webhook_url=None,
        webhook_secret_set=False,
        message="Webhook configuration removed",
    )


@router.post("/test", response_model=WebhookTestResponse)
async def test_webhook(
    request: Request,
    request_body: WebhookTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a test webhook to verify the endpoint is reachable.

    Returns the HTTP status code from the webhook endpoint.
    """
    if current_user.subscription_tier != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook testing is only available for enterprise customers",
        )

    await _check_webhook_rate_limit(request, str(current_user.id), current_user.subscription_tier)

    import httpx
    from datetime import datetime, timezone

    test_payload = {
        "event": "webhook.test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "This is a test webhook from Portkit",
        "user_id": str(current_user.id),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                request_body.webhook_url,
                json=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Portkit-Webhook/1.0",
                    "X-Webhook-Event": "webhook.test",
                },
            )

        success = 200 <= response.status_code < 300

        return WebhookTestResponse(
            success=success,
            status_code=response.status_code,
            message="Webhook endpoint responded successfully"
            if success
            else f"Webhook returned status {response.status_code}",
        )

    except httpx.TimeoutException:
        return WebhookTestResponse(
            success=False,
            status_code=None,
            message="Webhook endpoint timed out",
        )
    except httpx.ConnectError:
        return WebhookTestResponse(
            success=False,
            status_code=None,
            message="Could not connect to webhook endpoint",
        )
    except Exception as e:
        return WebhookTestResponse(
            success=False,
            status_code=None,
            message=f"Error: {str(e)}",
        )


@router.get("/deliveries", response_model=list[WebhookDeliveryResponse])
async def get_webhook_deliveries(
    request: Request,
    limit: int = Query(default=50, le=100),
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get recent webhook delivery attempts for the authenticated user.

    Shows delivery history for auditing and debugging.
    """
    if current_user.subscription_tier != "enterprise":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook delivery history is only available for enterprise customers",
        )

    await _check_webhook_rate_limit(request, str(current_user.id), current_user.subscription_tier)

    from services.webhook_service import WebhookDelivery, WebhookDeliveryStatus
    from sqlalchemy import desc

    query = select(WebhookDelivery).where(WebhookDelivery.user_id == str(current_user.id))

    if status_filter:
        query = query.where(WebhookDelivery.status == status_filter)

    query = query.order_by(desc(WebhookDelivery.created_at)).limit(limit)

    result = await db.execute(query)
    deliveries = result.scalars().all()

    return [
        WebhookDeliveryResponse(
            id=str(d.id),
            webhook_url=d.webhook_url,
            event_type=d.event_type,
            status=d.status,
            attempts=d.attempts,
            response_status=d.response_status,
            error_message=d.error_message,
            created_at=d.created_at.isoformat() if d.created_at else None,
            last_attempt_at=d.last_attempt_at.isoformat() if d.last_attempt_at else None,
        )
        for d in deliveries
    ]
