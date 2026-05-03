"""
Full coverage tests for rate_limiter.py targeting uncovered lines:
- RateLimiter.initialize() (75-83) — Redis init with success/failure
- _check_redis() (151-170) — Redis happy path
- get_rate_limit_status() Redis path (232-248)
- extract_user_from_token() (274-293)
- UserContextMiddleware.dispatch() (306-317)
- get_rate_limiter() (445-450)
- init_rate_limiter() (456-460)
- close_rate_limiter() (467-468)
- check_rate_limit() convenience (474-475)
"""

import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock, PropertyMock

from services.rate_limiter import (
    RateLimitConfig,
    RateLimitState,
    RateLimiter,
    RateLimitMiddleware,
    UserContextMiddleware,
    extract_user_from_token,
    create_global_limiter,
    get_rate_limiter,
    init_rate_limiter,
    close_rate_limiter,
    check_rate_limit,
    _rate_limiter,
)


class TestRateLimiterInitialize:
    """Lines 73-83: RateLimiter.initialize()"""

    @pytest.mark.asyncio
    async def test_initialize_redis_success(self):
        limiter = RateLimiter()
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        with patch("services.rate_limiter.aioredis") as mock_aioredis:
            mock_aioredis.from_url = AsyncMock(return_value=mock_redis)
            await limiter.initialize()
        assert limiter._use_redis is True

    @pytest.mark.asyncio
    async def test_initialize_redis_failure_fallback(self):
        limiter = RateLimiter()
        with patch("services.rate_limiter.aioredis") as mock_aioredis:
            mock_aioredis.from_url = AsyncMock(side_effect=Exception("no redis"))
            await limiter.initialize()
        assert limiter._use_redis is False


class TestCheckRedisHappyPath:
    """Lines 140-178: _check_redis() main path"""

    @pytest.mark.asyncio
    async def test_check_redis_allows_under_limit(self):
        limiter = RateLimiter()
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=[1, 1])
        mock_redis.expire = AsyncMock(return_value=True)
        limiter._redis = mock_redis
        limiter._use_redis = True

        config = RateLimitConfig(requests_per_minute=60, requests_per_hour=1000)
        is_allowed, meta = await limiter._check_redis("client1", config, time.time())
        assert is_allowed is True
        assert meta["limit_minute"] == 60
        assert meta["limit_hour"] == 1000
        assert meta["remaining_minute"] == 59
        assert meta["remaining_hour"] == 999

    @pytest.mark.asyncio
    async def test_check_redis_blocks_over_limit(self):
        limiter = RateLimiter()
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=[61, 500])
        limiter._redis = mock_redis
        limiter._use_redis = True

        config = RateLimitConfig(requests_per_minute=60, requests_per_hour=1000)
        is_allowed, meta = await limiter._check_redis("client2", config, time.time())
        assert is_allowed is False
        assert meta["retry_after"] is not None

    @pytest.mark.asyncio
    async def test_check_redis_hour_limit_blocks(self):
        limiter = RateLimiter()
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=[10, 1001])
        limiter._redis = mock_redis
        limiter._use_redis = True

        config = RateLimitConfig(requests_per_minute=60, requests_per_hour=1000)
        is_allowed, meta = await limiter._check_redis("client3", config, time.time())
        assert is_allowed is False

    @pytest.mark.asyncio
    async def test_check_redis_sets_expiry_on_first_request(self):
        limiter = RateLimiter()
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=[1, 1])
        mock_redis.expire = AsyncMock(return_value=True)
        limiter._redis = mock_redis
        limiter._use_redis = True

        config = RateLimitConfig()
        await limiter._check_redis("new_client", config, time.time())
        assert mock_redis.expire.call_count == 2

    @pytest.mark.asyncio
    async def test_check_redis_no_expiry_on_subsequent(self):
        limiter = RateLimiter()
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=[5, 10])
        mock_redis.expire = AsyncMock(return_value=True)
        limiter._redis = mock_redis
        limiter._use_redis = True

        config = RateLimitConfig()
        await limiter._check_redis("existing_client", config, time.time())
        mock_redis.expire.assert_not_called()


class TestGetRateLimitStatusRedis:
    """Lines 225-259: get_rate_limit_status() Redis path"""

    @pytest.mark.asyncio
    async def test_status_redis_happy_path(self):
        limiter = RateLimiter()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=["5", "100"])
        limiter._redis = mock_redis
        limiter._use_redis = True

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.state = MagicMock()
        mock_request.state.user_id = None
        mock_request.state.user_tier = "free"

        result = await limiter.get_rate_limit_status(mock_request)
        assert result["limit_minute"] == 60
        assert result["used_minute"] == 5
        assert result["used_hour"] == 100

    @pytest.mark.asyncio
    async def test_status_redis_null_counts(self):
        limiter = RateLimiter()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=[None, None])
        limiter._redis = mock_redis
        limiter._use_redis = True

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.state = MagicMock()
        mock_request.state.user_id = None
        mock_request.state.user_tier = "free"

        result = await limiter.get_rate_limit_status(mock_request)
        assert result["used_minute"] == 0
        assert result["used_hour"] == 0

    @pytest.mark.asyncio
    async def test_status_redis_error_falls_back(self):
        limiter = RateLimiter()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("redis down"))
        limiter._redis = mock_redis
        limiter._use_redis = True

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "1.2.3.4"
        mock_request.state = MagicMock()
        mock_request.state.user_id = None
        mock_request.state.user_tier = "free"

        result = await limiter.get_rate_limit_status(mock_request)
        assert "limit_minute" in result


class TestExtractUserFromToken:
    """Lines 266-293: extract_user_from_token()"""

    @pytest.mark.asyncio
    async def test_bearer_token_valid(self):
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer valid_token_123"}
        with patch("services.rate_limiter.verify_token", return_value="user42"):
            uid, tier = await extract_user_from_token(mock_request)
        assert uid == "user42"
        assert tier == "free"

    @pytest.mark.asyncio
    async def test_bearer_token_invalid(self):
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer bad_token"}
        with patch("services.rate_limiter.verify_token", return_value=None):
            uid, tier = await extract_user_from_token(mock_request)
        assert uid is None
        assert tier is None

    @pytest.mark.asyncio
    async def test_no_auth_header(self):
        mock_request = MagicMock()
        mock_request.headers = {}
        uid, tier = await extract_user_from_token(mock_request)
        assert uid is None
        assert tier is None

    @pytest.mark.asyncio
    async def test_api_key_valid(self):
        mock_request = MagicMock()
        mock_request.headers = {"X-API-Key": "ak_1234567890abcdef"}
        uid, tier = await extract_user_from_token(mock_request)
        assert uid is not None
        assert uid.startswith("apikey:")
        assert tier == "free"

    @pytest.mark.asyncio
    async def test_api_key_too_short(self):
        mock_request = MagicMock()
        mock_request.headers = {"X-API-Key": "short"}
        uid, tier = await extract_user_from_token(mock_request)
        assert uid is None

    @pytest.mark.asyncio
    async def test_bearer_prefix_missing(self):
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Basic abc123"}
        uid, tier = await extract_user_from_token(mock_request)
        assert uid is None


class TestUserContextMiddleware:
    """Lines 296-317: UserContextMiddleware.dispatch()"""

    @pytest.mark.asyncio
    async def test_health_path_skipped(self):
        app = MagicMock()
        mw = UserContextMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/health"
        call_next = AsyncMock(return_value=MagicMock())
        await mw.dispatch(mock_request, call_next)
        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_docs_path_skipped(self):
        app = MagicMock()
        mw = UserContextMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/docs"
        call_next = AsyncMock(return_value=MagicMock())
        await mw.dispatch(mock_request, call_next)
        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_sets_user_context(self):
        app = MagicMock()
        mw = UserContextMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/conversions"
        call_next = AsyncMock(return_value=MagicMock())
        with patch(
            "services.rate_limiter.extract_user_from_token",
            return_value=("user1", "premium"),
        ):
            resp = await mw.dispatch(mock_request, call_next)
        assert mock_request.state.user_id == "user1"
        assert mock_request.state.user_tier == "premium"

    @pytest.mark.asyncio
    async def test_no_token_continues(self):
        app = MagicMock()
        mw = UserContextMiddleware(app)
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/conversions"
        call_next = AsyncMock(return_value=MagicMock())
        with patch(
            "services.rate_limiter.extract_user_from_token",
            return_value=(None, None),
        ):
            resp = await mw.dispatch(mock_request, call_next)
        call_next.assert_called_once()


class TestModuleFunctions:
    """Lines 430-475: module-level functions"""

    @pytest.mark.asyncio
    async def test_init_rate_limiter(self):
        import services.rate_limiter as mod

        original = mod._rate_limiter
        mod._rate_limiter = None
        try:
            await init_rate_limiter()
            assert mod._rate_limiter is not None
        finally:
            mod._rate_limiter = original

    @pytest.mark.asyncio
    async def test_get_rate_limiter_returns_existing(self):
        import services.rate_limiter as mod

        existing = MagicMock()
        original = mod._rate_limiter
        mod._rate_limiter = existing
        try:
            result = await get_rate_limiter()
            assert result is existing
        finally:
            mod._rate_limiter = original

    @pytest.mark.asyncio
    async def test_get_rate_limiter_creates_and_inits(self):
        import services.rate_limiter as mod

        original = mod._rate_limiter
        mod._rate_limiter = None
        try:
            mock_limiter = MagicMock()
            mock_limiter.initialize = AsyncMock()
            with patch("services.rate_limiter.RateLimiter", return_value=mock_limiter):
                with patch("services.rate_limiter.create_global_limiter") as mock_create:
                    mock_create.return_value = mock_limiter
                    result = await get_rate_limiter()
            assert result is mock_limiter
            mock_limiter.initialize.assert_called_once()
        finally:
            mod._rate_limiter = original

    @pytest.mark.asyncio
    async def test_get_rate_limiter_creates_and_inits(self):
        import services.rate_limiter as mod

        original = mod._rate_limiter
        mod._rate_limiter = None
        try:
            result = await get_rate_limiter()
            assert result is not None
            assert mod._rate_limiter is not None
        finally:
            mod._rate_limiter = original

    @pytest.mark.asyncio
    async def test_close_rate_limiter(self):
        import services.rate_limiter as mod

        original = mod._rate_limiter
        mock_limiter = MagicMock()
        mock_limiter.close = AsyncMock()
        mod._rate_limiter = mock_limiter
        try:
            await close_rate_limiter()
            mock_limiter.close.assert_called_once()
            assert mod._rate_limiter is None
        finally:
            mod._rate_limiter = original

    @pytest.mark.asyncio
    async def test_close_rate_limiter_none(self):
        import services.rate_limiter as mod

        original = mod._rate_limiter
        mod._rate_limiter = None
        try:
            await close_rate_limiter()
        finally:
            mod._rate_limiter = original

    @pytest.mark.asyncio
    async def test_check_rate_limit_convenience(self):
        mock_limiter = MagicMock()
        mock_limiter.check_rate_limit = AsyncMock(
            return_value={"limit_minute": 60, "remaining_minute": 59}
        )
        with patch("services.rate_limiter.get_rate_limiter", return_value=mock_limiter):
            result = await check_rate_limit(MagicMock())
        assert result["limit_minute"] == 60

    def test_create_global_limiter_idempotent(self):
        import services.rate_limiter as mod

        original = mod._rate_limiter
        mod._rate_limiter = None
        try:
            limiter1 = create_global_limiter()
            limiter2 = create_global_limiter()
            assert limiter1 is limiter2
        finally:
            mod._rate_limiter = original


class TestMiddlewareDispatchAuthenticated:
    """Middleware dispatch with authenticated user (line 364-365)"""

    @pytest.mark.asyncio
    async def test_dispatch_authenticated_user_type(self):
        mock_limiter = MagicMock()
        mock_limiter.check_rate_limit = AsyncMock(
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
        mock_limiter._get_client_key = MagicMock(return_value="user:abc")
        mock_limiter._local_state = {"user:abc": MagicMock()}
        mw = RateLimitMiddleware(MagicMock(), mock_limiter)

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/test"
        mock_request.state = MagicMock()
        mock_request.state.user_id = "abc"
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "1.2.3.4"

        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        resp = await mw.dispatch(mock_request, call_next)
        assert resp.headers["X-RateLimit-Limit"] == "60"

    @pytest.mark.asyncio
    async def test_dispatch_upload_endpoint_limits(self):
        mock_limiter = MagicMock()
        mock_limiter.check_rate_limit = AsyncMock(
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
        mock_limiter._get_client_key = MagicMock(return_value="ip:1.2.3.4")
        mock_limiter._local_state = {}
        mw = RateLimitMiddleware(MagicMock(), mock_limiter)

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/upload/file.jar"
        mock_request.state = MagicMock()
        mock_request.state.user_id = None
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "1.2.3.4"

        mock_response = MagicMock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        resp = await mw.dispatch(mock_request, call_next)
        assert resp.headers["X-RateLimit-Limit"] == "60"
