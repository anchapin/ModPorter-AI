# Fix for Issue #1535: security(backend): force HTTPS in production by default

## Status: COMPLETED

## Summary

Implemented HTTPS enforcement for production traffic by adding an HTTPS redirect middleware and verifying HSTS headers are properly configured.

## Current HTTPS Configuration Status

| Component | Status | Details |
|-----------|--------|---------|
| HTTPS Redirect | ✅ IMPLEMENTED | New `HTTPSRedirectMiddleware` added |
| HSTS Header | ✅ CONFIGURED | Already present in `SecurityHeadersMiddleware` |
| HSTS Value | ✅ SECURE | `max-age=63072000; includeSubDomains; preload` (2 years) |

## Files Changed

### 1. `backend/src/services/security_headers.py`
- Added `HTTPSRedirectMiddleware` class that:
  - Redirects HTTP → HTTPS in production (ENVIRONMENT=production or FORCE_HTTPS=true)
  - Uses 307 temporary redirect to preserve HTTP method (safe for POST/PUT)
  - Excludes health checks, docs, and metrics endpoints
  - Excludes localhost/127.0.0.1 for local development

### 2. `backend/src/main.py`
- Imported `HTTPSRedirectMiddleware` alongside `SecurityHeadersMiddleware`
- Added middleware to app pipeline when not in TESTING mode
- Positioned as outermost middleware to catch HTTP requests first

### 3. `backend/src/tests/unit/test_https_redirect.py` (NEW)
- Comprehensive unit tests for `HTTPSRedirectMiddleware`
- Tests for production detection, redirect logic, excluded paths, and dispatch behavior

## Configuration

To enable HTTPS enforcement in production, set either:
```bash
ENVIRONMENT=production
# OR
FORCE_HTTPS=true
```

## How It Works

1. **Detection**: Middleware checks `ENVIRONMENT` or `FORCE_HTTPS` env vars
2. **Exclusion**: Health checks, docs, metrics, and localhost bypass redirect
3. **Redirect**: HTTP requests get 307 redirect to HTTPS equivalent
4. **HSTS**: Once on HTTPS, `Strict-Transport-Security` header ensures future requests skip HTTP entirely

## HSTS Configuration (Existing)

The `SecurityHeadersMiddleware` already sets a strong HSTS header:
```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

This tells browsers to:
- Only connect via HTTPS for the next 2 years (63072000 seconds)
- Apply to all subdomains
- Include in HSTS preload lists (Chromium, Firefox, etc.)

## Verification

All manual verification tests pass:
- ✅ ENVIRONMENT=production triggers redirect
- ✅ FORCE_HTTPS=true triggers redirect
- ✅ development environment does NOT trigger redirect
- ✅ All excluded paths properly bypass redirect
- ✅ Localhost requests bypass redirect