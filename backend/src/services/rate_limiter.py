"""
Rate Limiting Middleware for Portkit Backend

Provides per-user and global rate limiting for API endpoints.
Implements token bucket algorithm for smooth rate limiting.

Issue: #456 - Performance Optimization - Rate limiting for API endpoints
"""

import time
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import logging

import redis.asyncio as aioredis
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from config import settings
from services.metrics import (
    record_rate_limit_hit,
    record_rate_limit_request,
    update_rate_limit_usage,
    update_active_rate_limit_clients,
)
from security.auth import verify_token

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    # Per-user limits (overrides global if set)
    user_requests_per_minute: Optional[int] = None
    user_requests_per_hour: Optional[int] = None


@dataclass
class RateLimitState:
    """Current state of rate limiting for a client"""

    request_count: int = 0
    window_start: float = field(default_factory=time.time)
    tokens: float = 0.0
    last_request: float = field(default_factory=time.time)

    def reset_window(self):
        """Reset the sliding window"""
        self.request_count = 0
        self.window_start = time.time()


class RateLimiter:
    """
    Token bucket rate limiter with sliding window algorithm.
    Supports both in-memory and Redis-based storage.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None, redis_url: Optional[str] = None):
        self.config = config or RateLimitConfig()
        self.redis_url = redis_url or getattr(settings, "redis_url", "redis://localhost:6379")
        self._redis: Optional[aioredis.Redis] = None
        self._local_state: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._use_redis = False

    async def initialize(self):
        """Initialize Redis connection if available"""
        try:
            self._redis = await aioredis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            await self._redis.ping()
            self._use_redis = True
            logger.info("Rate limiter using Redis backend")
        except Exception as e:
            logger.warning(f"Redis not available for rate limiter: {e}. Using in-memory storage.")
            self._use_redis = False

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()

    def _get_client_key(self, request: Request) -> str:
        """Get unique key for client (IP + optional user ID)"""
        # Get IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        # Check for authenticated user
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        return f"ip:{ip}"

    def _get_user_config(
        self, request: Request, base_config: Optional[RateLimitConfig] = None
    ) -> RateLimitConfig:
        """Get rate limit config for specific user (can be overridden per user/tier)"""
        user_tier = getattr(request.state, "user_tier", "free")

        if base_config is not None:
            return base_config

        tier_limits = {
            "free": RateLimitConfig(requests_per_minute=10, requests_per_hour=50, burst_size=3),
            "creator": RateLimitConfig(requests_per_minute=30, requests_per_hour=200, burst_size=5),
            "creator_byok": RateLimitConfig(requests_per_minute=30, requests_per_hour=200, burst_size=5),
            "pro": RateLimitConfig(requests_per_minute=60, requests_per_hour=500, burst_size=10),
            "studio": RateLimitConfig(requests_per_minute=120, requests_per_hour=1000, burst_size=20),
            "studio_byok": RateLimitConfig(requests_per_minute=120, requests_per_hour=1000, burst_size=20),
            "enterprise": RateLimitConfig(requests_per_minute=300, requests_per_hour=5000, burst_size=50),
            "payg": RateLimitConfig(requests_per_minute=30, requests_per_hour=200, burst_size=5),
        }

        if user_tier in tier_limits:
            return tier_limits[user_tier]

        if user_tier == "premium":
            return RateLimitConfig(requests_per_minute=300, requests_per_hour=10000, burst_size=50)

        return self.config

    async def check_rate_limit(
        self,
        request: Request,
        endpoint: Optional[str] = None,
        override_config: Optional[RateLimitConfig] = None,
    ) -> tuple[bool, Dict[str, any]]:
        """
        Check if request is within rate limits.

        Returns:
            Tuple of (is_allowed, metadata_dict)
        """
        client_key = self._get_client_key(request)
        config = self._get_user_config(request, base_config=override_config)

        current_time = time.time()

        if self._use_redis and self._redis:
            return await self._check_redis(client_key, config, current_time)
        else:
            return self._check_local(client_key, config, current_time)

    async def _check_redis(
        self, client_key: str, config: RateLimitConfig, current_time: float
    ) -> tuple[bool, Dict[str, any]]:
        """Check rate limit using Redis"""
        try:
            # Get current count for this minute
            minute_key = f"ratelimit:{client_key}:minute"
            hour_key = f"ratelimit:{client_key}:hour"

            # Atomic increment with expiry
            minute_count = await self._redis.incr(minute_key)
            if minute_count == 1:
                await self._redis.expire(minute_key, 60)

            hour_count = await self._redis.incr(hour_key)
            if hour_count == 1:
                await self._redis.expire(hour_key, 3600)

            # Check limits
            remaining_minute = config.requests_per_minute - minute_count
            remaining_hour = config.requests_per_hour - hour_count

            is_allowed = (
                minute_count <= config.requests_per_minute
                and hour_count <= config.requests_per_hour
            )

            reset_at_minute = int(current_time + 60)
            reset_at_hour = int(current_time + 3600)

            return is_allowed, {
                "limit_minute": config.requests_per_minute,
                "limit_hour": config.requests_per_hour,
                "remaining_minute": max(0, remaining_minute),
                "remaining_hour": max(0, remaining_hour),
                "reset_at_minute": reset_at_minute,
                "reset_at_hour": reset_at_hour,
                "retry_after": (max(0, 60 - (current_time % 60)) if not is_allowed else None),
            }

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fallback to local check on error
            return self._check_local(client_key, config, current_time)

    def _check_local(
        self, client_key: str, config: RateLimitConfig, current_time: float
    ) -> tuple[bool, Dict[str, any]]:
        """Check rate limit using in-memory state"""
        state = self._local_state[client_key]

        # Check if window needs reset (every minute)
        if current_time - state.window_start >= 60:
            state.reset_window()

        # Token bucket algorithm for burst handling
        # Refill tokens based on time elapsed
        time_passed = current_time - state.last_request
        tokens_to_add = (current_time - time_passed) * (config.requests_per_minute / 60.0)
        state.tokens = min(config.burst_size, state.tokens + tokens_to_add)
        state.last_request = current_time

        # Check limits
        can_proceed = state.request_count < config.requests_per_minute and state.tokens >= 1

        if can_proceed:
            state.request_count += 1
            state.tokens -= 1

        remaining_minute = config.requests_per_minute - state.request_count
        remaining_hour = min(
            remaining_minute,
            config.requests_per_hour - state.request_count,  # Simplified
        )

        return can_proceed, {
            "limit_minute": config.requests_per_minute,
            "limit_hour": config.requests_per_hour,
            "remaining_minute": max(0, remaining_minute),
            "remaining_hour": max(0, remaining_hour),
            "reset_at_minute": int(current_time + 60),
            "reset_at_hour": int(current_time + 3600),
            "retry_after": (max(0, 60 - (current_time % 60)) if not can_proceed else None),
        }

    async def get_rate_limit_status(self, request: Request) -> Dict[str, any]:
        """Get current rate limit status without consuming a token"""
        client_key = self._get_client_key(request)
        config = self._get_user_config(request)
        current_time = time.time()

        if self._use_redis and self._redis:
            try:
                minute_key = f"ratelimit:{client_key}:minute"
                hour_key = f"ratelimit:{client_key}:hour"

                minute_count = int(await self._redis.get(minute_key) or 0)
                hour_count = int(await self._redis.get(hour_key) or 0)

                return {
                    "limit_minute": config.requests_per_minute,
                    "limit_hour": config.requests_per_hour,
                    "remaining_minute": max(0, config.requests_per_minute - minute_count),
                    "remaining_hour": max(0, config.requests_per_hour - hour_count),
                    "used_minute": minute_count,
                    "used_hour": hour_count,
                }
            except Exception as e:
                logger.error(f"Redis status check failed: {e}")

        # Fallback to local
        state = self._local_state[client_key]
        return {
            "limit_minute": config.requests_per_minute,
            "limit_hour": config.requests_per_hour,
            "remaining_minute": max(0, config.requests_per_minute - state.request_count),
            "remaining_hour": max(0, config.requests_per_hour - state.request_count),
            "used_minute": state.request_count,
            "used_hour": state.request_count,
        }


# Paths that don't need authentication
AUTH_OPTIONAL_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register"}


async def extract_user_from_token(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Extract user_id and tier from JWT token in request.

    Returns:
        Tuple of (user_id, tier) or (None, None) if not authenticated
    """
    # Check Authorization header for Bearer token
    auth_header = request.headers.get("Authorization", "")

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Strip "Bearer " prefix
        user_id = verify_token(token, "access")
        if user_id:
            # For now, default to "free" tier - tier lookup requires DB call
            # which we avoid in middleware for performance
            return user_id, "free"

    # Check X-API-Key header (for API key authentication)
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        # Note: API key validation requires DB lookup
        # For now, treat valid-looking keys as authenticated
        # Full implementation would look up API key in DB
        if api_key and len(api_key) > 10:
            return f"apikey:{api_key[:8]}", "free"

    return None, None


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts user context from JWT token BEFORE other middleware.

    This runs BEFORE RateLimitMiddleware to populate request.state with user info,
    enabling per-user rate limiting instead of per-IP.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip for health checks and docs
        if request.url.path in {"/api/v1/health", "/docs", "/redoc", "/openapi.json"}:
            return await call_next(request)

        # Try to extract user info from token
        user_id, tier = await extract_user_from_token(request)

        if user_id:
            request.state.user_id = user_id
            request.state.user_tier = tier
            logger.debug("User context set for request")

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    """

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

        # Endpoints to exclude from rate limiting
        self.exclude_paths = {
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/metrics",
            "/api/v1/rate-limit/dashboard",
            "/api/v1/rate-limit/summary",
            "/api/v1/rate-limit/endpoints",
            "/api/v1/rate-limit/clients",
            "/api/v1/rate-limit/config",
            "/api/v1/rate-limit/metrics/prometheus",
        }

        # Endpoints with different limits
        self.endpoint_limits = {
            "/api/v1/conversions": RateLimitConfig(requests_per_minute=30, requests_per_hour=300),
            "/api/v1/upload": RateLimitConfig(requests_per_minute=60, requests_per_hour=600),
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Check if endpoint has specific limits
        limiter_config = None
        for path, config in self.endpoint_limits.items():
            if request.url.path.startswith(path):
                limiter_config = config
                break

        # Determine client type for metrics
        client_type = (
            "user" if hasattr(request.state, "user_id") and request.state.user_id else "ip"
        )

        # Apply custom config if set (passed as override_config)

        is_allowed, metadata = await self.rate_limiter.check_rate_limit(
            request, override_config=limiter_config
        )

        if not is_allowed:
            # Record rate limit hit for metrics
            endpoint = request.url.path
            record_rate_limit_hit(endpoint, client_type)
            record_rate_limit_request(endpoint, client_type, False)

            logger.warning(
                f"Rate limit exceeded for {self.rate_limiter._get_client_key(request)} "
                f"on {request.url.path}"
            )

            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": metadata.get("retry_after", 60),
                    "rate_limit": {
                        "limit": metadata["limit_minute"],
                        "remaining": metadata["remaining_minute"],
                        "reset_at": metadata["reset_at_minute"],
                    },
                },
                headers={
                    "X-RateLimit-Limit": str(metadata["limit_minute"]),
                    "X-RateLimit-Remaining": str(metadata["remaining_minute"]),
                    "X-RateLimit-Reset": str(metadata["reset_at_minute"]),
                    "Retry-After": str(metadata.get("retry_after", 60)),
                },
            )
            return response

        # Record allowed request
        record_rate_limit_request(request.url.path, client_type, True)

        # Update usage metrics
        client_key = self.rate_limiter._get_client_key(request)
        update_rate_limit_usage(client_key, "minute", metadata.get("used_minute", 0))

        # Update active clients count
        active_count = len(self.rate_limiter._local_state)
        update_active_rate_limit_clients(active_count)

        # Add rate limit headers to successful responses
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(metadata["limit_minute"])
        response.headers["X-RateLimit-Remaining"] = str(metadata["remaining_minute"])
        response.headers["X-RateLimit-Reset"] = str(metadata["reset_at_minute"])

        return response


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def create_global_limiter() -> RateLimiter:
    """Create the global rate limiter instance synchronously"""
    global _rate_limiter

    if _rate_limiter is None:
        config = RateLimitConfig(requests_per_minute=60, requests_per_hour=1000, burst_size=10)
        _rate_limiter = RateLimiter(config=config)

    return _rate_limiter


async def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance"""
    global _rate_limiter

    if _rate_limiter is None:
        create_global_limiter()
        if _rate_limiter:
            await _rate_limiter.initialize()

    return _rate_limiter  # type: ignore


async def init_rate_limiter():
    """Initialize the rate limiter on app startup"""
    global _rate_limiter
    if _rate_limiter is None:
        create_global_limiter()

    if _rate_limiter:
        await _rate_limiter.initialize()


async def close_rate_limiter():
    """Close rate limiter on app shutdown"""
    global _rate_limiter
    if _rate_limiter:
        await _rate_limiter.close()
        _rate_limiter = None


# Convenience function for checking rate limits
async def check_rate_limit(request: Request) -> Dict[str, any]:
    """Check rate limit for a request"""
    limiter = await get_rate_limiter()
    return await limiter.check_rate_limit(request)


# Endpoint-specific rate limiters
conversion_rate_limiter = RateLimiter(
    config=RateLimitConfig(requests_per_minute=30, requests_per_hour=300, burst_size=5)
)

upload_rate_limiter = RateLimiter(
    config=RateLimitConfig(requests_per_minute=60, requests_per_hour=600, burst_size=10)
)
