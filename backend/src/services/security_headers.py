from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Optionally add CSP (Content Security Policy)
        # For an API, this might be restrictive, but 'default-src 'self'' is a good baseline.
        # However, to be safe and avoid breaking changes in this small task,
        # I'll stick to the standard headers above which are low risk.
        # response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response
