"""
Unit tests for webhook rate limiting.

Issue #1536 - Security: Rate limiting for webhook management endpoints
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from api.webhooks import _check_webhook_rate_limit
from services.rate_limiter import RateLimitConfig, webhook_rate_limiter


class TestWebhookRateLimitCheck:
    """Tests for _check_webhook_rate_limit function."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request with user context."""
        request = MagicMock()
        request.state = MagicMock()
        request.state.user_id = "test_user_123"
        request.state.user_tier = "enterprise"
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = MagicMock()
        return request

    @pytest.mark.asyncio
    async def test_rate_limit_allows_request_under_limit(self, mock_request):
        """Test request is allowed when under rate limit."""
        # Should not raise an exception
        await _check_webhook_rate_limit(mock_request, "test_user_123", "enterprise")

    @pytest.mark.asyncio
    async def test_rate_limit_rejects_request_over_limit(self, mock_request):
        """Test request is rejected when rate limit exceeded."""
        # Exhaust the rate limit by making many requests
        base_config = RateLimitConfig(
            requests_per_minute=1,
            requests_per_hour=100,
            burst_size=1,
        )

        # First request should succeed (consume the only token)
        with patch.object(
            webhook_rate_limiter, "check_rate_limit", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = (
                True,
                {
                    "limit_minute": 1,
                    "remaining_minute": 0,
                    "reset_at_minute": 1234567890,
                },
            )
            # First call should pass
            await _check_webhook_rate_limit(mock_request, "test_user_123", "enterprise")

        # Now simulate rate limit exceeded
        with patch.object(
            webhook_rate_limiter, "check_rate_limit", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = (
                False,
                {
                    "limit_minute": 1,
                    "remaining_minute": 0,
                    "reset_at_minute": 1234567890,
                    "retry_after": 60,
                },
            )

            with pytest.raises(HTTPException) as exc_info:
                await _check_webhook_rate_limit(mock_request, "test_user_123", "enterprise")

            assert exc_info.value.status_code == 429
            assert exc_info.value.detail["error"] == "rate_limit_exceeded"
            assert "retry_after" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_rate_limit_includes_rate_limit_info_in_response(self, mock_request):
        """Test rate limit response includes proper rate limit headers."""
        expected_limit = 20
        expected_remaining = 15

        with patch.object(
            webhook_rate_limiter, "check_rate_limit", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = (
                False,
                {
                    "limit_minute": expected_limit,
                    "remaining_minute": expected_remaining,
                    "reset_at_minute": 1234567890,
                    "retry_after": 30,
                },
            )

            with pytest.raises(HTTPException) as exc_info:
                await _check_webhook_rate_limit(mock_request, "test_user_123", "enterprise")

            detail = exc_info.value.detail
            assert "rate_limit" in detail
            assert detail["rate_limit"]["limit"] == expected_limit
            assert detail["rate_limit"]["remaining"] == expected_remaining


class TestWebhookRateLimiterConfiguration:
    """Tests for webhook rate limiter configuration."""

    def test_webhook_rate_limiter_exists(self):
        """Test webhook_rate_limiter is defined."""
        assert webhook_rate_limiter is not None

    def test_webhook_rate_limiter_has_config(self):
        """Test webhook_rate_limiter has configuration."""
        assert hasattr(webhook_rate_limiter, "config")

    def test_webhook_rate_limiter_config_limits(self):
        """Test webhook rate limiter has appropriate limits."""
        config = webhook_rate_limiter.config
        # Webhook endpoints should have stricter limits than general API
        assert config.requests_per_minute <= 20
        assert config.requests_per_hour <= 100


class TestWebhookEndpointsRateLimitProtection:
    """Tests verifying webhook endpoints are protected by rate limiting."""

    @pytest.mark.asyncio
    async def test_get_webhook_config_checks_rate_limit(self):
        """Test GET /config endpoint calls rate limit check."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from starlette.datastructures import Headers

        # Create mock user
        mock_user = MagicMock()
        mock_user.id = "user_123"
        mock_user.subscription_tier = "enterprise"
        mock_user.webhook_url = None
        mock_user.webhook_secret = None

        # Create mock request
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_id = "user_123"
        mock_request.state.user_tier = "enterprise"

        # Track if rate limit was checked
        rate_limit_called = False

        async def mock_check_rate_limit(*args, **kwargs):
            nonlocal rate_limit_called
            rate_limit_called = True
            return (True, {"limit_minute": 20, "remaining_minute": 19, "reset_at_minute": 0})

        with patch.object(
            webhook_rate_limiter, "check_rate_limit", mock_check_rate_limit
        ):
            with patch("api.webhooks.get_current_user", new_callable=AsyncMock) as mock_auth:
                mock_auth.return_value = mock_user

                with patch("api.webhooks.get_db", new_callable=AsyncMock) as mock_db:
                    mock_db.return_value = AsyncMock()

                    from api.webhooks import get_webhook_config

                    await get_webhook_config(
                        request=mock_request,
                        db=mock_db.return_value,
                        current_user=mock_user,
                    )

        # Rate limit should have been checked
        assert rate_limit_called, "Rate limit was not checked on GET /config"

    @pytest.mark.asyncio
    async def test_set_webhook_config_checks_rate_limit(self):
        """Test POST /config endpoint calls rate limit check."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_user = MagicMock()
        mock_user.id = "user_456"
        mock_user.subscription_tier = "enterprise"

        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_id = "user_456"
        mock_request.state.user_tier = "enterprise"

        mock_request_body = MagicMock()
        mock_request_body.webhook_url = "https://example.com/webhook"
        mock_request_body.webhook_secret = None

        rate_limit_called = False

        async def mock_check_rate_limit(*args, **kwargs):
            nonlocal rate_limit_called
            rate_limit_called = True
            return (True, {"limit_minute": 20, "remaining_minute": 19, "reset_at_minute": 0})

        with patch.object(
            webhook_rate_limiter, "check_rate_limit", mock_check_rate_limit
        ):
            with patch("api.webhooks.get_current_user", new_callable=AsyncMock) as mock_auth:
                mock_auth.return_value = mock_user

                with patch("api.webhooks.get_db", new_callable=AsyncMock) as mock_db:
                    mock_db.return_value = AsyncMock()

                    from api.webhooks import set_webhook_config

                    await set_webhook_config(
                        request=mock_request,
                        request_body=mock_request_body,
                        db=mock_db.return_value,
                        current_user=mock_user,
                    )

        assert rate_limit_called, "Rate limit was not checked on POST /config"

    @pytest.mark.asyncio
    async def test_delete_webhook_config_checks_rate_limit(self):
        """Test DELETE /config endpoint calls rate limit check."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_user = MagicMock()
        mock_user.id = "user_789"
        mock_user.subscription_tier = "enterprise"

        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_id = "user_789"
        mock_request.state.user_tier = "enterprise"

        rate_limit_called = False

        async def mock_check_rate_limit(*args, **kwargs):
            nonlocal rate_limit_called
            rate_limit_called = True
            return (True, {"limit_minute": 20, "remaining_minute": 19, "reset_at_minute": 0})

        with patch.object(
            webhook_rate_limiter, "check_rate_limit", mock_check_rate_limit
        ):
            with patch("api.webhooks.get_current_user", new_callable=AsyncMock) as mock_auth:
                mock_auth.return_value = mock_user

                with patch("api.webhooks.get_db", new_callable=AsyncMock) as mock_db:
                    mock_db.return_value = AsyncMock()

                    from api.webhooks import delete_webhook_config

                    await delete_webhook_config(
                        request=mock_request,
                        db=mock_db.return_value,
                        current_user=mock_user,
                    )

        assert rate_limit_called, "Rate limit was not checked on DELETE /config"

    @pytest.mark.asyncio
    async def test_test_webhook_checks_rate_limit(self):
        """Test POST /test endpoint calls rate limit check."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_user = MagicMock()
        mock_user.id = "user_test"
        mock_user.subscription_tier = "enterprise"

        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_id = "user_test"
        mock_request.state.user_tier = "enterprise"

        mock_request_body = MagicMock()
        mock_request_body.webhook_url = "https://example.com/webhook"

        rate_limit_called = False

        async def mock_check_rate_limit(*args, **kwargs):
            nonlocal rate_limit_called
            rate_limit_called = True
            return (True, {"limit_minute": 20, "remaining_minute": 19, "reset_at_minute": 0})

        with patch.object(
            webhook_rate_limiter, "check_rate_limit", mock_check_rate_limit
        ):
            with patch("api.webhooks.get_current_user", new_callable=AsyncMock) as mock_auth:
                mock_auth.return_value = mock_user

                with patch("api.webhooks.get_db", new_callable=AsyncMock) as mock_db:
                    mock_db.return_value = AsyncMock()

                    from api.webhooks import test_webhook

                    await test_webhook(
                        request=mock_request,
                        request_body=mock_request_body,
                        db=mock_db.return_value,
                        current_user=mock_user,
                    )

        assert rate_limit_called, "Rate limit was not checked on POST /test"

    @pytest.mark.asyncio
    async def test_get_webhook_deliveries_checks_rate_limit(self):
        """Test GET /deliveries endpoint calls rate limit check."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from datetime import datetime, timezone

        mock_user = MagicMock()
        mock_user.id = "user_deliveries"
        mock_user.subscription_tier = "enterprise"

        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_id = "user_deliveries"
        mock_request.state.user_tier = "enterprise"

        rate_limit_called = False

        async def mock_check_rate_limit(*args, **kwargs):
            nonlocal rate_limit_called
            rate_limit_called = True
            return (True, {"limit_minute": 20, "remaining_minute": 19, "reset_at_minute": 0})

        # Mock the WebhookDelivery and the database result
        mock_delivery = MagicMock()
        mock_delivery.id = "delivery_1"
        mock_delivery.webhook_url = "https://example.com/webhook"
        mock_delivery.event_type = "batch.completed"
        mock_delivery.status = "success"
        mock_delivery.attempts = 1
        mock_delivery.response_status = 200
        mock_delivery.error_message = None
        mock_delivery.created_at = datetime.now(timezone.utc)
        mock_delivery.last_attempt_at = None

        # Create proper mock for scalars().all()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[mock_delivery])

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        with patch.object(
            webhook_rate_limiter, "check_rate_limit", mock_check_rate_limit
        ):
            with patch("api.webhooks.get_current_user", new_callable=AsyncMock) as mock_auth:
                mock_auth.return_value = mock_user

                with patch("api.webhooks.get_db", new_callable=AsyncMock) as mock_get_db:
                    mock_db = AsyncMock()
                    mock_db.execute = AsyncMock(return_value=mock_result)
                    mock_get_db.return_value = mock_db

                    from api.webhooks import get_webhook_deliveries

                    await get_webhook_deliveries(
                        request=mock_request,
                        limit=50,
                        status_filter=None,
                        db=mock_db,
                        current_user=mock_user,
                    )

        assert rate_limit_called, "Rate limit was not checked on GET /deliveries"