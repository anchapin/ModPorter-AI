"""
Structured Logging Configuration for ModPorter AI

Uses structlog for structured JSON logging with:
- Correlation IDs for request tracing
- Timestamp in ISO format
- Log levels
- Source location (file, line, function)
"""

import logging
import sys

import structlog


def setup_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to output logs as JSON (True) or human-readable (False)
    """
    # Common processors for all log formats
    common_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Add format-specific processors
    if json_format:
        # JSON output for production/Docker
        processors = common_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console output for development
        processors = common_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(message)s") if json_format else None
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class StructlogMiddleware:
    """
    ASGI middleware for structured HTTP request logging.

    Logs:
    - Request method and path
    - Response status code
    - Request duration
    - Client IP
    """

    def __init__(self, app, log_level: str = "INFO"):
        self.app = app
        self.log_level = log_level
        self.logger = get_logger(__name__)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        import time
        from uuid import uuid4

        # Generate correlation ID
        correlation_id = str(uuid4())

        # Store in scope for access in handlers
        scope["correlation_id"] = correlation_id

        # Extract request info
        method = scope["method"]
        path = scope["path"]
        client = scope.get("client", ("unknown", 0))
        client_ip = client[0] if client else "unknown"

        # Log request start
        self.logger.info(
            "request_started",
            method=method,
            path=path,
            client_ip=client_ip,
            correlation_id=correlation_id,
        )

        # Track timing
        start_time = time.time()

        # Wrap send to capture status code
        status_code = None

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            # Process request
            await self.app(scope, receive, send_wrapper)
        finally:
            # Log request complete
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "request_completed",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
                client_ip=client_ip,
                correlation_id=correlation_id,
            )
