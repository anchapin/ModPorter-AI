"""
Unit tests for webhook notification service.

Issue #1501 - Enterprise Phase 1: Webhook Notifications for Batch Completion
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from services.webhook_service import (
    WebhookService,
    WebhookPayload,
    WebhookDelivery,
    WebhookDeliveryStatus,
    send_batch_completion_webhook,
    EnterpriseWebhookManager,
)
from services.retry import RetryConfig


class TestWebhookPayload:
    """Tests for WebhookPayload model."""

    def test_webhook_payload_creation(self):
        """Test creating a webhook payload."""
        payload = WebhookPayload(
            batch_id="batch_123",
            user_id="user_456",
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_files=10,
            completed_files=8,
            failed_files=2,
            success_rate=80.0,
            results=[],
        )

        assert payload.event == "batch.completed"
        assert payload.batch_id == "batch_123"
        assert payload.user_id == "user_456"
        assert payload.total_files == 10
        assert payload.completed_files == 8
        assert payload.failed_files == 2
        assert payload.success_rate == 80.0

    def test_webhook_payload_to_dict(self):
        """Test converting payload to dictionary."""
        payload = WebhookPayload(
            batch_id="batch_123",
            user_id="user_456",
            timestamp="2024-01-01T00:00:00Z",
            total_files=5,
            completed_files=5,
            failed_files=0,
            success_rate=100.0,
            results=[{"id": "1", "status": "completed"}],
        )

        data = payload.model_dump()
        assert isinstance(data, dict)
        assert data["batch_id"] == "batch_123"
        assert data["event"] == "batch.completed"
        assert len(data["results"]) == 1


class TestWebhookService:
    """Tests for WebhookService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def webhook_service(self, mock_db):
        """Create a WebhookService instance."""
        return WebhookService(mock_db)

    def test_generate_signature(self, webhook_service):
        """Test HMAC signature generation."""
        payload = '{"test": "data"}'
        secret = "my_secret_key"

        signature = webhook_service._generate_signature(payload, secret)

        assert signature is not None
        assert len(signature) == 64  # SHA256 hex digest
        assert isinstance(signature, str)

    def test_generate_signature_deterministic(self, webhook_service):
        """Test that signature generation is deterministic."""
        payload = '{"test": "data"}'
        secret = "my_secret_key"

        sig1 = webhook_service._generate_signature(payload, secret)
        sig2 = webhook_service._generate_signature(payload, secret)

        assert sig1 == sig2

    def test_generate_signature_different_for_different_payloads(self, webhook_service):
        """Test that different payloads produce different signatures."""
        secret = "my_secret_key"

        sig1 = webhook_service._generate_signature('{"a": 1}', secret)
        sig2 = webhook_service._generate_signature('{"a": 2}', secret)

        assert sig1 != sig2

    def test_generate_signature_different_for_different_secrets(self, webhook_service):
        """Test that different secrets produce different signatures."""
        payload = '{"test": "data"}'

        sig1 = webhook_service._generate_signature(payload, "secret1")
        sig2 = webhook_service._generate_signature(payload, "secret2")

        assert sig1 != sig2

    @pytest.mark.asyncio
    async def test_send_webhook_success(self, webhook_service, mock_db):
        """Test successful webhook delivery."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        webhook_service._client = mock_client

        with patch.object(webhook_service, '_get_client', return_value=mock_client):
            delivery = await webhook_service.send_webhook(
                webhook_url="https://example.com/webhook",
                payload={"event": "test"},
                event_type="test.event",
                user_id="user_123",
            )

        assert delivery is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_send_webhook_failure_with_retry(self, webhook_service, mock_db):
        """Test webhook delivery failure and retry."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        webhook_service._client = mock_client

        with patch.object(webhook_service, '_get_client', return_value=mock_client):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                delivery = await webhook_service.send_webhook(
                    webhook_url="https://example.com/webhook",
                    payload={"event": "test"},
                    event_type="test.event",
                    user_id="user_123",
                    max_retries=3,
                )

        assert delivery is not None
        assert delivery.status == WebhookDeliveryStatus.FAILED
        assert delivery.attempts == 3

    @pytest.mark.asyncio
    async def test_send_webhook_timeout(self, webhook_service, mock_db):
        """Test webhook delivery timeout."""
        import httpx

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.is_closed = False

        webhook_service._client = mock_client

        with patch.object(webhook_service, '_get_client', return_value=mock_client):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                delivery = await webhook_service.send_webhook(
                    webhook_url="https://example.com/webhook",
                    payload={"event": "test"},
                    event_type="test.event",
                    user_id="user_123",
                    max_retries=2,
                )

        assert delivery is not None
        assert delivery.status == WebhookDeliveryStatus.FAILED
        assert "Timeout" in delivery.error_message

    @pytest.mark.asyncio
    async def test_close_client(self, webhook_service):
        """Test closing the HTTP client."""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        webhook_service._client = mock_client

        await webhook_service.close()

        mock_client.aclose.assert_called_once()


class TestSendBatchCompletionWebhook:
    """Tests for send_batch_completion_webhook function."""

    @pytest.mark.asyncio
    async def test_send_batch_completion_webhook_success(self):
        """Test sending batch completion webhook."""
        mock_db = AsyncMock()
        mock_service = AsyncMock()
        mock_delivery = MagicMock()
        mock_service.send_webhook = AsyncMock(return_value=mock_delivery)

        with patch('services.webhook_service.WebhookService', return_value=mock_service):
            result = await send_batch_completion_webhook(
                db=mock_db,
                batch_id="batch_123",
                user_id="user_456",
                webhook_url="https://example.com/webhook",
                total_files=10,
                completed_files=8,
                failed_files=2,
                results=[{"id": "1", "status": "completed"}],
            )

        assert result == mock_delivery
        mock_service.send_webhook.assert_called_once()
        mock_service.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_batch_completion_webhook_with_secret(self):
        """Test sending batch completion webhook with secret."""
        mock_db = AsyncMock()
        mock_service = AsyncMock()
        mock_delivery = MagicMock()
        mock_service.send_webhook = AsyncMock(return_value=mock_delivery)

        with patch('services.webhook_service.WebhookService', return_value=mock_service):
            result = await send_batch_completion_webhook(
                db=mock_db,
                batch_id="batch_123",
                user_id="user_456",
                webhook_url="https://example.com/webhook",
                total_files=10,
                completed_files=10,
                failed_files=0,
                results=[],
                secret="my_secret",
            )

        call_kwargs = mock_service.send_webhook.call_args.kwargs
        assert call_kwargs["secret"] == "my_secret"


class TestRetryConfig:
    """Tests for RetryConfig used by webhook service."""

    def test_retry_config_defaults(self):
        """Test default retry configuration."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_retry_config_custom(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_calculate_delay(self):
        """Test delay calculation with exponential backoff."""
        from services.retry import calculate_delay

        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=60.0, jitter=False)

        # First attempt: 1.0 * 2^0 = 1.0
        assert calculate_delay(1, config) == 1.0

        # Second attempt: 1.0 * 2^1 = 2.0
        assert calculate_delay(2, config) == 2.0

        # Third attempt: 1.0 * 2^2 = 4.0
        assert calculate_delay(3, config) == 4.0

    def test_calculate_delay_respects_max(self):
        """Test delay calculation respects max_delay."""
        from services.retry import calculate_delay

        config = RetryConfig(base_delay=10.0, exponential_base=2.0, max_delay=30.0, jitter=False)

        # Fifth attempt: 10.0 * 2^4 = 160, but max is 30
        assert calculate_delay(5, config) == 30.0


class TestWebhookDeliveryModel:
    """Tests for WebhookDelivery model."""

    def test_webhook_delivery_status_constants(self):
        """Test webhook delivery status constants."""
        assert WebhookDeliveryStatus.PENDING == "pending"
        assert WebhookDeliveryStatus.SUCCESS == "success"
        assert WebhookDeliveryStatus.FAILED == "failed"
        assert WebhookDeliveryStatus.RETRYING == "retrying"