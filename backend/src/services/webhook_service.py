"""
Webhook Notification Service

Provides webhook notification delivery with retry logic for batch conversion completion.
Supports configurable webhook URLs per enterprise customer.

Issue #1501 - Enterprise Phase 1: Webhook Notifications for Batch Completion
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import httpx
from sqlalchemy import select, String, Text, Integer, DateTime, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl

from db.declarative_base import Base
from db.models import JSONType
from services.retry import RetryConfig, retry_async

logger = logging.getLogger(__name__)


class WebhookDeliveryStatus(str):
    """Webhook delivery status"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookPayload(BaseModel):
    """Webhook payload for batch completion"""
    event: str = "batch.completed"
    batch_id: str
    user_id: str
    timestamp: str
    total_files: int
    completed_files: int
    failed_files: int
    success_rate: float
    results: List[Dict[str, Any]]


class WebhookConfig(BaseModel):
    """Webhook configuration"""
    url: HttpUrl
    secret: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3


class WebhookDelivery(Base):
    """
    Tracks webhook delivery attempts for audit trail.

    Stores delivery status, attempts, and response data for debugging.
    """
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    webhook_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="'pending'",
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("'0'"),
    )
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    response_status: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    response_body: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_webhook_deliveries_user_event", "user_id", "event_type"),
        Index("ix_webhook_deliveries_status", "status"),
    )


class WebhookService:
    """
    Service for sending webhook notifications with retry logic.

    Features:
    - Async HTTP delivery with configurable timeouts
    - Exponential backoff retry for failed deliveries
    - Delivery tracking in database for audit
    - HMAC signature support for payload verification
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for payload verification"""
        import hmac
        import hashlib
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    async def send_webhook(
        self,
        webhook_url: str,
        payload: Dict[str, Any],
        event_type: str = "batch.completed",
        user_id: Optional[str] = None,
        secret: Optional[str] = None,
        max_retries: int = 3,
    ) -> WebhookDelivery:
        """
        Send webhook notification with retry logic.

        Args:
            webhook_url: The URL to send the webhook to
            payload: The payload data
            event_type: Type of event (e.g., "batch.completed")
            user_id: User ID for tracking
            secret: Optional secret for HMAC signature
            max_retries: Maximum number of retry attempts

        Returns:
            WebhookDelivery record with delivery status
        """
        delivery = WebhookDelivery(
            user_id=user_id or "system",
            webhook_url=webhook_url,
            event_type=event_type,
            payload=payload,
            status=WebhookDeliveryStatus.PENDING,
        )
        self.db.add(delivery)
        await self.db.commit()
        await self.db.refresh(delivery)

        retry_config = RetryConfig(
            max_attempts=max_retries,
            base_delay=2.0,
            max_delay=60.0,
            exponential_base=2.0,
        )

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                client = await self._get_client()

                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Portkit-Webhook/1.0",
                    "X-Webhook-Event": event_type,
                    "X-Webhook-Delivery-ID": str(delivery.id),
                }

                if secret:
                    import json
                    payload_str = json.dumps(payload, sort_keys=True)
                    headers["X-Webhook-Signature"] = self._generate_signature(payload_str, secret)

                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                )

                delivery.attempts = attempt
                delivery.last_attempt_at = datetime.now(timezone.utc)
                delivery.response_status = response.status_code

                if response.status_code >= 200 and response.status_code < 300:
                    delivery.status = WebhookDeliveryStatus.SUCCESS
                    delivery.response_body = response.text[:1000] if response.text else None
                    await self.db.commit()
                    logger.info(
                        f"Webhook delivered successfully: {delivery.id} "
                        f"(attempt {attempt}, status {response.status_code})"
                    )
                    return delivery
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:500]}"
                    delivery.error_message = last_error
                    delivery.response_body = response.text[:1000] if response.text else None
                    logger.warning(
                        f"Webhook delivery failed: {delivery.id} "
                        f"(attempt {attempt}, status {response.status_code})"
                    )

            except httpx.TimeoutException as e:
                last_error = f"Timeout: {str(e)}"
                delivery.error_message = last_error
                logger.warning(
                    f"Webhook timeout: {delivery.id} (attempt {attempt})"
                )
            except httpx.ConnectError as e:
                last_error = f"Connection error: {str(e)}"
                delivery.error_message = last_error
                logger.warning(
                    f"Webhook connection error: {delivery.id} (attempt {attempt})"
                )
            except Exception as e:
                last_error = f"Unexpected error: {type(e).__name__}: {str(e)}"
                delivery.error_message = last_error
                logger.error(
                    f"Webhook unexpected error: {delivery.id} (attempt {attempt}): {e}"
                )

            delivery.attempts = attempt
            delivery.last_attempt_at = datetime.now(timezone.utc)

            if attempt < max_retries:
                delivery.status = WebhookDeliveryStatus.RETRYING
                await self.db.commit()
                delay = retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1))
                await asyncio.sleep(delay)

        delivery.status = WebhookDeliveryStatus.FAILED
        delivery.error_message = last_error
        await self.db.commit()

        logger.error(
            f"Webhook delivery exhausted all retries: {delivery.id}, "
            f"final_error: {last_error}"
        )
        return delivery


async def send_batch_completion_webhook(
    db: AsyncSession,
    batch_id: str,
    user_id: str,
    webhook_url: str,
    total_files: int,
    completed_files: int,
    failed_files: int,
    results: List[Dict[str, Any]],
    secret: Optional[str] = None,
) -> WebhookDelivery:
    """
    Convenience function to send batch completion webhook.

    Args:
        db: Database session
        batch_id: Batch identifier
        user_id: User identifier
        webhook_url: Webhook endpoint URL
        total_files: Total number of files in batch
        completed_files: Number of successfully converted files
        failed_files: Number of failed conversions
        results: List of conversion results
        secret: Optional HMAC secret for signature

    Returns:
        WebhookDelivery record
    """
    payload = WebhookPayload(
        batch_id=batch_id,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_files=total_files,
        completed_files=completed_files,
        failed_files=failed_files,
        success_rate=(completed_files / total_files * 100) if total_files > 0 else 0,
        results=results,
    )

    service = WebhookService(db)
    try:
        return await service.send_webhook(
            webhook_url=webhook_url,
            payload=payload.model_dump(),
            event_type="batch.completed",
            user_id=user_id,
            secret=secret,
        )
    finally:
        await service.close()


class EnterpriseWebhookManager:
    """
    Manages enterprise customer webhook configurations.

    Provides CRUD operations for webhook URLs per enterprise customer.
    """

    @staticmethod
    async def get_user_webhook_url(db: AsyncSession, user_id: str) -> Optional[str]:
        """
        Get configured webhook URL for a user.

        Returns the user's configured webhook URL if they are an enterprise customer.
        """
        from db.models import User

        result = await db.execute(
            select(User.webhook_url).where(
                User.id == uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            )
        )
        row = result.scalar_one_or_none()
        return row

    @staticmethod
    async def set_user_webhook_url(
        db: AsyncSession,
        user_id: str,
        webhook_url: str,
    ) -> None:
        """Set webhook URL for a user."""
        from db.models import User

        result = await db.execute(
            select(User).where(
                User.id == uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            )
        )
        user = result.scalar_one_or_none()

        if user:
            user.webhook_url = webhook_url
            await db.commit()

    @staticmethod
    async def delete_user_webhook_url(db: AsyncSession, user_id: str) -> None:
        """Remove webhook URL for a user."""
        from db.models import User

        result = await db.execute(
            select(User).where(
                User.id == uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            )
        )
        user = result.scalar_one_or_none()

        if user:
            user.webhook_url = None
            await db.commit()


async def get_failed_webhook_deliveries(
    db: AsyncSession,
    limit: int = 100,
) -> List[WebhookDelivery]:
    """Get recent failed webhook deliveries for monitoring/alerting."""
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.status == WebhookDeliveryStatus.FAILED)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def retry_failed_webhook(
    db: AsyncSession,
    delivery_id: str,
) -> WebhookDelivery:
    """
    Retry a failed webhook delivery.

    Resets the delivery status and re-sends the webhook.
    """
    result = await db.execute(
        select(WebhookDelivery).where(WebhookDelivery.id == uuid.UUID(delivery_id))
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise ValueError(f"Webhook delivery not found: {delivery_id}")

    delivery.status = WebhookDeliveryStatus.PENDING
    delivery.attempts = 0
    delivery.error_message = None
    await db.commit()

    service = WebhookService(db)
    try:
        return await service.send_webhook(
            webhook_url=delivery.webhook_url,
            payload=delivery.payload,
            event_type=delivery.event_type,
            user_id=delivery.user_id,
        )
    finally:
        await service.close()