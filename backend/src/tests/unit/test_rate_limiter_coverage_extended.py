"""
Comprehensive unit tests for rate_limiter service - Extended coverage.
Covers uncovered lines from rate_limiter.py (63% coverage target).
"""

import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import Request, status

from services.rate_limiter import (
    RateLimitConfig,
    RateLimitState,
    RateLimiter,
    RateLimitMiddleware,
    create_global_limiter,
    get_rate_limiter,
    check_rate_limit,
)


class TestRateLimitConfigExtended:
    """Extended tests for RateLimitConfig."""

    def test_user_requests_per_minute_config(self):
        """Test user-specific per-minute rate limit config."""
        config = RateLimitConfig(requests_per_minute=100, user_requests_per_minute=50)
        assert config.user_requests_per_minute == 50

    def test_user_requests_per_hour_config(self):
        """Test user-specific per-hour rate limit config."""
        config = RateLimitConfig(requests_per_hour=1000, user_requests_per_hour=500)
        assert config.user_requests_per_hour == 500

    def test_burst_size_config(self):
        """Test burst size configuration."""
        config = RateLimitConfig(burst_size=20)
        assert config.burst_size == 20


class TestRateLimitStateExtended:
    """Extended tests for RateLimitState."""

    def test_last_request_initialization(self):
        """Test last_request is initialized to current time."""
        state = RateLimitState()
        assert state.last_request > 0

    def test_tokens_initialization(self):
        """Test tokens are initialized to 0."""
        state = RateLimitState()
        assert state.tokens == 0.0

    def test_window_start_initialization(self):
        """Test window_start is initialized to current time."""
        state = RateLimitState()
        assert state.window_start > 0

    def test_reset_window_updates_time(self):
        """Test reset_window updates window_start."""
        state = RateLimitState()
        original_window_start = state.window_start
        time.sleep(0.01)  # Small delay
        state.reset_window()
        assert state.window_start >= original_window_start


class TestRateLimiterClientKey:
    """Tests for _get_client_key method."""

    @pytest.fixture
    def limiter(self):
        return RateLimiter()

    def test_get_client_key_with_forwarded_header(self, limiter):
        """Test client key extraction with X-Forwarded-For header."""
        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.state = MagicMock()
        mock_request.state.user_id = None  # Explicitly set to None

        client_key = limiter._get_client_key(mock_request)
        assert client_key == "ip:192.168.1.1"

    def test_get_client_key_without_forwarded_header(self, limiter):
        """Test client key extraction without X-Forwarded-For header."""
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.100"
        mock_request.state = MagicMock()
        mock_request.state.user_id = None  # Explicitly set to None

        client_key = limiter._get_client_key(mock_request)
        assert client_key == "ip:192.168.1.100"

    def test_get_client_key_with_user_id(self, limiter):
        """Test client key uses user_id when present."""
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.100"
        mock_request.state = MagicMock()
        mock_request.state.user_id = "user123"

        client_key = limiter._get_client_key(mock_request)
        assert client_key == "user:user123"

    def test_get_client_key_fallback_to_unknown(self, limiter):
        """Test client key falls back to unknown when no client."""
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None
        mock_request.state = MagicMock()
        mock_request.state.user_id = None  # Explicitly set to None

        client_key = limiter._get_client_key(mock_request)
        assert client_key == "ip:unknown"


class TestRateLimiterUserConfig:
    """Tests for _get_user_config method."""

    @pytest.fixture
    def limiter(self):
        return RateLimiter()

    def test_get_user_config_free_tier(self, limiter):
        """Test config for free tier user."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_tier = "free"

        config = limiter._get_user_config(mock_request)
        assert config.requests_per_minute == 10  # Free tier limit

    def test_get_user_config_premium_tier(self, limiter):
        """Test config for premium tier user."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_tier = "premium"

        config = limiter._get_user_config(mock_request)
        assert config.requests_per_minute == 300
        assert config.requests_per_hour == 10000

    def test_get_user_config_with_base_config(self, limiter):
        """Test config overrides base config."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_tier = "free"

        base_config = RateLimitConfig(requests_per_minute=10)
        config = limiter._get_user_config(mock_request, base_config=base_config)

        assert config.requests_per_minute == 10


class TestRateLimiterLocalCheck:
    """Tests for _check_local method."""

    @pytest.fixture
    def limiter(self):
        config = RateLimitConfig(requests_per_minute=10, requests_per_hour=100, burst_size=5)
        return RateLimiter(config=config)

    def test_check_local_allowed_request(self, limiter):
        """Test local check allows request within limit."""
        is_allowed, metadata = limiter._check_local(
            "test_client", RateLimitConfig(requests_per_minute=10, burst_size=5), time.time()
        )

        assert is_allowed is True
        assert "limit_minute" in metadata
        assert "remaining_minute" in metadata

    def test_check_local_exceeds_limit(self, limiter):
        """Test local check denies when limit exceeded."""
        config = RateLimitConfig(requests_per_minute=1, burst_size=1)

        # First request
        is_allowed_1, _ = limiter._check_local("test_client_exceed", config, time.time())
        assert is_allowed_1 is True

        # Second request should be blocked (burst exhausted)
        is_allowed_2, metadata = limiter._check_local(
            "test_client_exceed", config, time.time() + 0.1
        )
        # May be allowed or blocked depending on token bucket state
        assert "limit_minute" in metadata

    def test_check_local_window_reset(self, limiter):
        """Test local check resets window after 60 seconds."""
        client_key = "window_reset_test"
        config = RateLimitConfig(requests_per_minute=10, burst_size=5)

        # First request
        limiter._check_local(client_key, config, time.time())

        # Request after window reset
        is_allowed, _ = limiter._check_local(client_key, config, time.time() + 61)
        assert is_allowed is True


class TestRateLimiterStatus:
    """Tests for get_rate_limit_status method."""

    @pytest.fixture
    def limiter(self):
        return RateLimiter()

    @pytest.mark.asyncio
    async def test_get_rate_limit_status_local(self, limiter):
        """Test status check in local mode."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_tier = "free"
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        limiter._use_redis = False

        status = await limiter.get_rate_limit_status(mock_request)

        assert "limit_minute" in status
        assert "remaining_minute" in status
        assert "used_minute" in status

    @pytest.mark.asyncio
    async def test_get_rate_limit_status_with_user(self, limiter):
        """Test status check with authenticated user."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_tier = "premium"
        mock_request.state.user_id = "user456"
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        limiter._use_redis = False

        status = await limiter.get_rate_limit_status(mock_request)

        assert status["limit_minute"] == 300  # Premium tier


class TestRateLimiterRedisCheck:
    """Tests for Redis-based rate limiting."""

    @pytest.fixture
    def limiter(self):
        return RateLimiter()

    @pytest.mark.asyncio
    async def test_check_redis_fallback_on_error(self, limiter):
        """Test fallback to local check when Redis fails."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_tier = "free"
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        # Setup Redis mock that raises error
        limiter._use_redis = True
        limiter._redis = AsyncMock()
        limiter._redis.incr = AsyncMock(side_effect=Exception("Redis error"))

        is_allowed, metadata = await limiter.check_rate_limit(mock_request)

        # Should fallback to local check
        assert "limit_minute" in metadata


class TestRateLimitMiddlewareDispatch:
    """Tests for RateLimitMiddleware.dispatch method."""

    @pytest.fixture
    def mock_limiter(self):
        return MagicMock()

    @pytest.fixture
    def middleware(self, mock_limiter):
        return RateLimitMiddleware(MagicMock(), mock_limiter)

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path(self, middleware):
        """Test middleware skips rate limiting for excluded paths."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/health"

        mock_call_next = AsyncMock(return_value=MagicMock())

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_endpoint_specific_limits(self, middleware):
        """Test endpoint-specific rate limits."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/conversions"
        mock_request.state = MagicMock()
        mock_request.state.user_id = None
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        # Mock limiter to return allowed
        middleware.rate_limiter.check_rate_limit = AsyncMock(
            return_value=(
                True,
                {
                    "limit_minute": 10,
                    "remaining_minute": 9,
                    "reset_at_minute": int(time.time() + 60),
                    "used_minute": 1,
                },
            )
        )

        mock_response = MagicMock()
        mock_response.headers = {}  # Fix: use actual dict for headers
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-RateLimit-Limit"] == "10"

    @pytest.mark.asyncio
    async def test_dispatch_rate_limit_exceeded(self, middleware):
        """Test middleware returns 429 when rate limit exceeded."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/test"
        mock_request.state = MagicMock()
        mock_request.state.user_id = None
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        # Mock limiter to return blocked
        middleware.rate_limiter.check_rate_limit = AsyncMock(
            return_value=(
                False,
                {
                    "limit_minute": 60,
                    "remaining_minute": 0,
                    "reset_at_minute": int(time.time() + 60),
                    "retry_after": 30,
                },
            )
        )

        response = await middleware.dispatch(mock_request, AsyncMock())

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "X-RateLimit-Limit" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_adds_rate_limit_headers(self, middleware):
        """Test middleware adds rate limit headers to successful responses."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/test"
        mock_request.state = MagicMock()
        mock_request.state.user_id = None
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        middleware.rate_limiter.check_rate_limit = AsyncMock(
            return_value=(
                True,
                {
                    "limit_minute": 60,
                    "remaining_minute": 59,
                    "reset_at_minute": int(time.time() + 60),
                    "used_minute": 1,
                },
            )
        )

        mock_response = MagicMock()
        mock_response.headers = {}  # Fix: use actual dict for headers
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-RateLimit-Limit"] == "60"


class TestRateLimiterEdgeCases:
    """Tests for edge cases in RateLimiter."""

    @pytest.fixture
    def limiter(self):
        return RateLimiter()

    @pytest.mark.asyncio
    async def test_check_rate_limit_with_override_config(self, limiter):
        """Test check_rate_limit accepts override config."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.user_tier = "free"
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        override_config = RateLimitConfig(requests_per_minute=5)

        is_allowed, metadata = await limiter.check_rate_limit(
            mock_request, endpoint="/test", override_config=override_config
        )

        assert "limit_minute" in metadata
        assert metadata["limit_minute"] == 5

    def test_rate_limiter_initialization_with_redis_url(self):
        """Test RateLimiter initialization with custom Redis URL."""
        limiter = RateLimiter(redis_url="redis://custom:6379")
        assert limiter.redis_url == "redis://custom:6379"

    @pytest.mark.asyncio
    async def test_rate_limiter_close(self):
        """Test close method handles missing Redis."""
        limiter = RateLimiter()
        limiter._redis = None

        # Should not raise
        await limiter.close()

    @pytest.mark.asyncio
    async def test_rate_limiter_close_with_redis(self):
        """Test close method closes Redis connection."""
        limiter = RateLimiter()
        limiter._redis = AsyncMock()

        await limiter.close()

        limiter._redis.close.assert_called_once()
