# Fix for Issue #1536: security(backend): add rate limiting to webhook management endpoints

## Status: COMPLETED

## Current Status of Rate Limiting on Webhook Endpoints

**Before this fix:**
- The webhook management endpoints (`/webhooks/config`, `/webhooks/test`, `/webhooks/deliveries`) had NO rate limiting
- The rest of the API used existing rate limiting infrastructure in `services/rate_limiter.py`

**Existing rate limiting patterns in codebase:**
- `RateLimiter` class with token bucket algorithm supporting both in-memory and Redis-based storage
- Tier-based scaling (free, creator, pro, studio, enterprise, etc.)
- Endpoint-specific rate limiters: `conversion_rate_limiter`, `upload_rate_limiter`
- Pattern used in conversions.py: creates a MockRequest object to pass user context for rate limiting

## Code Changes

### 1. `backend/src/services/rate_limiter.py` (lines 537-539)
Added new endpoint-specific rate limiter for webhooks:
```python
webhook_rate_limiter = RateLimiter(
    config=RateLimitConfig(requests_per_minute=20, requests_per_hour=100, burst_size=5)
)
```

### 2. `backend/src/api/webhooks.py`
Added rate limiting to all 5 webhook endpoints:

**Added imports and helper function (lines 21-68):**
```python
from services.rate_limiter import (
    RateLimitConfig,
    webhook_rate_limiter,
)

async def _check_webhook_rate_limit(request: Request, user_id: str, user_tier: str) -> None:
    """
    Check rate limit for webhook endpoints.
    Raises HTTPException 429 if rate limit exceeded.
    """
    # ... MockRequest class and rate limit check ...
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={...},
        )
```

**Applied to endpoints:**
- `GET /webhooks/config` - line 131
- `POST /webhooks/config` - line 160
- `DELETE /webhooks/config` - line 201
- `POST /webhooks/test` - line 235
- `GET /webhooks/deliveries` - line 306

## Rate Limit Configuration

- **20 requests per minute** (base, scales with tier multiplier)
- **100 requests per hour**
- **burst_size: 5**

Enterprise tier users get scaled limits (300/min base × tier ratio). The lower limit compared to conversions (30/min) reflects that webhook management is a less frequent operation.

## Consistency with Codebase

- Uses same `RateLimiter` class and `RateLimitConfig` as other endpoints
- Uses same MockRequest pattern found in `conversions.py`
- Returns same error response structure with rate limit metadata
- Tier-based scaling follows existing patterns in the codebase
- Supports Redis-based distributed rate limiting (inherits from RateLimiter class)
- Passes ruff linting with no issues
- All 3105 unit tests pass

## Files Changed
1. `backend/src/services/rate_limiter.py` - added `webhook_rate_limiter` instance
2. `backend/src/api/webhooks.py` - added rate limiting to all webhook endpoints

## Acceptance Criteria Checklist
- [x] Rate limiting added to GET /webhooks/config
- [x] Rate limiting added to POST /webhooks/config
- [x] Rate limiting added to DELETE /webhooks/config
- [x] Rate limiting added to POST /webhooks/test
- [x] Rate limiting added to GET /webhooks/deliveries
- [x] Uses Redis-based rate limiting for distributed systems
- [x] Consistent with existing rate limiting patterns in codebase
- [x] All tests pass (3105 passed)
- [x] No linting errors