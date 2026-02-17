"""
Structured Logging Service for ModPorter AI
Provides correlation IDs, structured JSON logs, and log aggregation support.

Issue: #383 - Structured logging (Phase 3)
"""

import logging
import json
import uuid
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler
import os

# Context variable to store correlation ID across async operations
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

# Context variable to store request metadata
request_metadata_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar('request_metadata', default=None)


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging with correlation IDs.
    """
    
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
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # Add performance metrics if available
        if hasattr(record, 'duration_ms'):
            log_data["duration_ms"] = record.duration_ms
        
        return json.dumps(log_data)


class PlainFormatter(logging.Formatter):
    """
    Human-readable formatter for development.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        correlation_id = correlation_id_var.get()
        corr_str = f"[{correlation_id[:8]}...] " if correlation_id else ""
        return f"{self.formatTime(record)} {record.levelname} {corr_str}{record.getMessage()}"


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: The name for the logger (typically __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Use plain formatter for console in development
        console_formatter = PlainFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler for production
        log_dir = os.getenv("LOG_DIR", "/var/log/modporter")
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "modporter.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(StructuredFormatter())
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
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        correlation_id_var.set(self.old_correlation_id)
        request_metadata_var.set(self.old_metadata)


def log_api_request(logger: logging.Logger, method: str, path: str, 
                    status_code: Optional[int] = None, duration_ms: Optional[float] = None,
                    **extra_fields) -> None:
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
    
    # Create a custom log record with extra data
    extra = {"extra_data": log_data}
    logger.info(f"{method} {path}", extra=extra)


def log_conversion_event(logger: logging.Logger, job_id: str, event: str,
                         progress: Optional[int] = None, **extra_fields) -> None:
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
    
    extra = {"extra_data": log_data}
    logger.info(f"Conversion {job_id}: {event}", extra=extra)


def log_error_with_context(logger: logging.Logger, error: Exception, 
                            context: Optional[Dict[str, Any]] = None,
                            **extra_fields) -> None:
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
    
    extra = {"extra_data": log_data}
    logger.error(str(error), exc_info=True, extra=extra)


# Module-level logger with lazy initialization to avoid import errors in test environments
class _LazyLogger:
    """Lazy proxy for the default logger that defers initialization until first access."""
    _instance = None
    
    def __getattr__(self, name):
        if self._instance is None:
            self._instance = get_logger(__name__)
        return getattr(self._instance, name)
    
    def __call__(self, *args, **kwargs):
        if self._instance is None:
            self._instance = get_logger(__name__)
        return self._instance(*args, **kwargs)
    
    def __repr__(self):
        if self._instance is None:
            return f"<{self.__class__.__name__}: not initialized>"
        return repr(self._instance)
    
    def __str__(self):
        if self._instance is None:
            return f"<{self.__class__.__name__}: not initialized>"
        return str(self._instance)

logger = _LazyLogger()
