from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi import Request
from starlette.responses import RedirectResponse
import os


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce HTTPS for production traffic.

    Redirects HTTP requests to HTTPS when:
    - ENVIRONMENT is set to "production"
    - Or FORCE_HTTPS is set to "true"

    Excludes:
    - Health check endpoints
    - Documentation endpoints
    - Metrics endpoints
    - Localhost/127.0.0.1 requests (for development)

    Issue: #1535 - security(backend): force HTTPS in production by default
    """

    # Paths to exclude from HTTPS redirect
    EXCLUDED_PATHS = {
        "/api/v1/health",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
        "/api/v1/metrics",
        "/metrics",
    }

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    def _is_production(self) -> bool:
        """Check if running in production mode."""
        environment = os.getenv("ENVIRONMENT", "").lower()
        force_https = os.getenv("FORCE_HTTPS", "").lower()

        # Production if ENVIRONMENT is set to production, or FORCE_HTTPS is explicitly true
        return environment == "production" or force_https == "true"

    def _should_redirect(self, request: Request) -> bool:
        """Check if the request should be redirected to HTTPS."""
        # Only redirect if on HTTP (not already HTTPS)
        if request.url.scheme == "https":
            return False

        # Don't redirect if not production and FORCE_HTTPS not set
        if not self._is_production():
            return False

        # Don't redirect excluded paths (health checks, docs, etc.)
        if request.url.path in self.EXCLUDED_PATHS:
            return False

        # Don't redirect localhost/127.0.0.1 requests (development)
        host = request.headers.get("host", "")
        if host in ("localhost", "127.0.0.1", "[::1]"):
            return False

        return True

    async def dispatch(self, request: Request, call_next):
        if self._should_redirect(request):
            # Build HTTPS URL
            https_url = request.url.replace(scheme="https")

            # Preserve port if non-standard (80 for HTTP)
            # If host has a port, keep it - the redirect will work properly
            return RedirectResponse(
                url=str(https_url),
                status_code=307,  # Temporary redirect to preserve request method
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Adds:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - Referrer-Policy
    - Permissions-Policy
    - Content-Security-Policy (for download endpoints)

    Note: The legacy X-XSS-Protection header was intentionally removed (PR #1421 /
    issue #1419) because it is deprecated and can introduce XSS vulnerabilities in
    older browsers. Modern browsers ignore it; CSP is used instead.

    Issue: #973 - File upload security: sandboxing, validation, and virus scanning
    """

    # Download endpoints that need restrictive CSP
    DOWNLOAD_ENDPOINTS = (
        "/api/v1/download",
        "/api/v1/conversions/",
        "/api/v1/addon/",
        "/results/",
    )

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    def _is_download_endpoint(self, path: str) -> bool:
        """Check if the request path is a download endpoint."""
        return any(path.startswith(endpoint) for endpoint in self.DOWNLOAD_ENDPOINTS)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path

        # Add standard security headers
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), accelerometer=(), gyroscope=()"
        )

        # Add Content-Security-Policy for download endpoints
        # This prevents XSS attacks when serving user-uploaded content
        if self._is_download_endpoint(path):
            # Restrictive CSP for download endpoints - only allow same-origin
            csp = (
                "default-src 'none'; "
                "script-src 'none'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'none'; "
                "frame-src 'none'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'none'; "
                "plugin-types 'none'"
            )
            response.headers["Content-Security-Policy"] = csp

            # Additional headers for download security
            response.headers["X-Download-Options"] = "noopen"
            response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

            # Prevent caching of downloaded files (security)
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response
