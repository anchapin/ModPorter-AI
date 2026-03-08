"""
Structured Logging Service for ModPorter AI
Provides structured JSON logs using structlog with correlation IDs and log aggregation support.

Issue: #695 - Add structured logging
"""

import logging
import structlog
import uuid
import sys
import os
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler
from structlog.processors import JSONRenderer, TimeStamper, add_log_level
from structlog.stdlib import LoggerFactory
from structlog.stdlib import ProcessorFormatter

# Context variable to store correlation ID across async operations
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Context variable to store request metadata
request_metadata_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "request_metadata", default=None
)


def configure_structlog(
    log_level: str = None,
    log_file: Optional[str] = None,
    json_format: bool = None,
    debug_mode: bool = False,
):
    """
    Configure structlog for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (optional)
        json_format: Use JSON format (auto-detected from environment if None)
        debug_mode: Enable debug mode for verbose output
    """
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Auto-detect JSON format in production
    if json_format is None:
        json_format = os.getenv("LOG_JSON_FORMAT", "false").lower() == "true"
        # Also enable JSON if running in production environment
        if os.getenv("ENVIRONMENT", "development") == "production":
            json_format = True

    # Get log directory
    log_dir = os.getenv("LOG_DIR", "/var/log/modporter")

    # Configure processors based on format
    # Order matters: context merging -> logger info -> level -> timestamper -> renderer -> exception handling
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if debug_mode:
        processors.append(structlog.dev.ConsoleRenderer())
    elif json_format:
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=False))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_format:
        # Use structlog for JSON output
        console_handler.setFormatter(LoggingFormatter(debug_mode=debug_mode))
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root_logger.addHandler(console_handler)

    # File handler for production
    if log_file is None:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "modporter.log")

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(LoggingFormatter(json_format=True))
    root_logger.addHandler(file_handler)

    return structlog.get_logger()


class LoggingFormatter(logging.Formatter):
    """Formatter that integrates structlog with standard logging"""

    def __init__(self, json_format: bool = False, debug_mode: bool = False):
        super().__init__()
        self.json_format = json_format
        self.debug_mode = debug_mode

    def format(self, record: logging.LogRecord) -> str:
        # Build structured log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add request metadata if available
        metadata = request_metadata_var.get()
        if metadata:
            log_data["request"] = metadata

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Add performance metrics if available
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        if self.json_format:
            import json

            return json.dumps(log_data)
        else:
            # Plain text format
            corr_str = f"[{correlation_id[:8]}...] " if correlation_id else ""
            return f"{log_data['timestamp']} {record.levelname} {corr_str}{record.getMessage()}"


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a configured structlog logger instance.

    Args:
        name: The name for the logger (typically __name__)

    Returns:
        Configured structlog logger instance
    """
    return structlog.get_logger(name)


def get_standard_logger(name: str) -> logging.Logger:
    """
    Get a standard library logger configured to work with structlog.

    Args:
        name: The name for the logger (typically __name__)

    Returns:
        Configured standard logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler for production
        log_dir = os.getenv("LOG_DIR", "/var/log/modporter")
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "modporter.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(LoggingFormatter(json_format=True))
        logger.addHandler(file_handler)

    return logger


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set the correlation ID for the current context.
    If no ID is provided, a new UUID will be generated.

    Args:
        correlation_id: Optional correlation ID to use

    Returns:
        The correlation ID (either provided or generated)
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    correlation_id_var.set(correlation_id)
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID from the context.

    Returns:
        Current correlation ID or None
    """
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """
    Clear the correlation ID from the current context.
    """
    correlation_id_var.set(None)


def set_request_metadata(metadata: Dict[str, Any]) -> None:
    """
    Set request metadata for the current context.

    Args:
        metadata: Dictionary of metadata to store
    """
    request_metadata_var.set(metadata)
    structlog.contextvars.bind_contextvars(**metadata)


def clear_request_metadata() -> None:
    """
    Clear request metadata from the current context.
    """
    request_metadata_var.set(None)


class LogContext:
    """
    Context manager for setting correlation ID and metadata.

    Usage:
        with LogContext(correlation_id="req-123", user_id="user-456"):
            logger.info("Processing request")
    """

    def __init__(self, correlation_id: Optional[str] = None, **metadata):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.metadata = metadata
        self.old_correlation_id = None
        self.old_metadata = None

    def __enter__(self):
        self.old_correlation_id = correlation_id_var.get()
        self.old_metadata = request_metadata_var.get()

        correlation_id_var.set(self.correlation_id)
        request_metadata_var.set(self.metadata)

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=self.correlation_id, **self.metadata)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        correlation_id_var.set(self.old_correlation_id)
        request_metadata_var.set(self.old_metadata)


def log_api_request(
    logger: structlog.BoundLogger,
    method: str,
    path: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    **extra_fields,
) -> None:
    """
    Log an API request with structured data.

    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **extra_fields: Additional fields to log
    """
    log_data = {
        "event": "api_request",
        "method": method,
        "path": path,
    }

    if status_code is not None:
        log_data["status_code"] = status_code

    if duration_ms is not None:
        log_data["duration_ms"] = round(duration_ms, 2)

    log_data.update(extra_fields)

    logger.info(f"{method} {path}", **log_data)


def log_conversion_event(
    logger: structlog.BoundLogger,
    job_id: str,
    event: str,
    progress: Optional[int] = None,
    **extra_fields,
) -> None:
    """
    Log a conversion event with structured data.

    Args:
        logger: Logger instance
        job_id: Conversion job ID
        event: Event name (started, progress, completed, failed)
        progress: Progress percentage (0-100)
        **extra_fields: Additional fields to log
    """
    log_data = {
        "event": "conversion",
        "job_id": job_id,
        "conversion_event": event,
    }

    if progress is not None:
        log_data["progress"] = progress

    log_data.update(extra_fields)

    logger.info(f"Conversion {job_id}: {event}", **log_data)


def log_error_with_context(
    logger: structlog.BoundLogger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    **extra_fields,
) -> None:
    """
    Log an error with additional context.

    Args:
        logger: Logger instance
        error: The exception that occurred
        context: Additional context about the error
        **extra_fields: Additional fields to log
    """
    log_data = {
        "event": "error",
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    if context:
        log_data["context"] = context

    log_data.update(extra_fields)

    logger.error(str(error), exc_info=error, **log_data)


# Module-level logger with lazy initialization
def _get_module_logger() -> structlog.BoundLogger:
    """Get the module-level structlog logger."""
    return structlog.get_logger(__name__)


# Lazy logger proxy
class _LazyStructlogLogger:
    """Lazy proxy for the default logger that defers initialization until first access."""

    _instance = None

    def __getattr__(self, name):
        if self._instance is None:
            self._instance = _get_module_logger()
        return getattr(self._instance, name)

    def __call__(self, *args, **kwargs):
        if self._instance is None:
            self._instance = _get_module_logger()
        return self._instance(*args, **kwargs)

    def __repr__(self):
        if self._instance is None:
            return f"<{self.__class__.__name__}: not initialized>"
        return repr(self._instance)

    def __str__(self):
        if self._instance is None:
            return f"<{self.__class__.__name__}: not initialized>"
        return str(self._instance)


logger = _LazyStructlogLogger()
