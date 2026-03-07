"""
Logging Middleware for ModPorter AI Backend
Provides request/response logging with structured logging.

Issue: #695 - Add structured logging
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from services.structured_logging import set_correlation_id, clear_correlation_id, get_correlation_id

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses with correlation IDs.
    
    Features:
    - Automatic correlation ID generation for each request
    - Request/response timing
    - Structured logging of HTTP method, path, status code
    - Request/response body size logging
    """
    
    def __init__(self, app: ASGIApp, exclude_paths: list = None):
        """
        Initialize the logging middleware.
        
        Args:
            app: The ASGI application
            exclude_paths: List of paths to exclude from logging (e.g., health checks)
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/api/v1/metrics",
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log details."""
        
        # Check if path should be excluded
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        # Generate correlation ID for this request
        correlation_id = set_correlation_id()
        
        # Start timer
        start_time = time.time()
        
        # Build initial log data
        request_id = str(uuid.uuid4())
        
        # Log request
        log = logger.bind(
            correlation_id=correlation_id,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
            client_host=request.client.host if request.client else None,
        )
        
        log.info(
            "request_started",
            event="request",
            path=request.url.path,
            method=request.method,
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Add response details to log
            log.bind(
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            ).info(
                "request_completed",
                event="request",
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log exception
            duration_ms = (time.time() - start_time) * 1000
            
            log.error(
                "request_failed",
                event="request",
                path=request.url.path,
                method=request.method,
                error=str(e),
                duration_ms=round(duration_ms, 2),
                exc_info=e,
            )
            raise
            
        finally:
            # Clear correlation ID
            clear_correlation_id()
    
    def _should_exclude(self, path: str) -> bool:
        """Check if the path should be excluded from logging."""
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware for setting up request context variables.
    
    This middleware ensures that correlation IDs and other context
    are properly set up for each request.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Set up request context and process the request."""
        
        # Get correlation ID from header if present
        correlation_id = request.headers.get("X-Correlation-ID")
        if correlation_id:
            set_correlation_id(correlation_id)
        
        # Add request metadata
        from services.structured_logging import set_request_metadata
        set_request_metadata({
            "method": request.method,
            "path": request.url.path,
            "client_host": request.client.host if request.client else None,
        })
        
        try:
            response = await call_next(request)
            return response
        finally:
            from services.structured_logging import clear_request_metadata
            clear_request_metadata()
