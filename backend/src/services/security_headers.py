from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Adds:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Content-Security-Policy (for download endpoints)

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
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

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
