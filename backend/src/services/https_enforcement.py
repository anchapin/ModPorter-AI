"""
HTTPS and HSTS Enforcement Middleware for ModPorter AI

Provides:
- HTTPS redirect for production environments
- Strict HSTS header enforcement
- Secure cookie settings
"""

import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS in production.

    Only redirects when:
    - ENVIRONMENT is set to 'production' or 'staging'
    - The request is over HTTP (not HTTPS)
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.redirect_enabled = self.environment in ("production", "staging")

    async def dispatch(self, request: Request, call_next):
        if not self.redirect_enabled:
            return await call_next(request)

        # Check if already HTTPS
        if request.headers.get("X-Forwarded-Proto") == "https":
            return await call_next(request)

        if request.headers.get("X-Forwarded-Proto") == "http":
            # Redirect to HTTPS
            url = f"https://{request.headers.get('Host', '')}{request.url.path}"
            if request.url.query:
                url += f"?{request.url.query}"
            return RedirectResponse(url, status_code=301)

        return await call_next(request)


class HSTSStrictMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce strict HSTS policy.

    Applies HSTS header with:
    - max-age=63072000 (2 years)
    - includeSubDomains
    - preload flag for major browser preload lists

    Only applied in production when FORCE_HSTS=true or ENVIRONMENT=production.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.force_hsts = os.getenv("FORCE_HSTS", "").lower() == "true"
        self.hsts_enabled = self.environment == "production" or self.force_hsts

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if self.hsts_enabled:
            # Check if already set by SecurityHeadersMiddleware
            if "Strict-Transport-Security" not in response.headers:
                response.headers["Strict-Transport-Security"] = (
                    "max-age=63072000; includeSubDomains; preload"
                )

        return response
