"""
Better Stack log aggregation service for Portkit.

Provides structured logging with Better Stack (Logtail) integration
for searchable, persistent log storage with 30-day retention.

Issue: #1212 - Pre-beta: Full observability stack
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from contextvars import ContextVar
from functools import wraps
import threading

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

TRACE_ID_CTX: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
SPAN_ID_CTX: ContextVar[Optional[str]] = ContextVar("span_id", default=None)


class BetterStackHandler(logging.Handler):
    """Custom logging handler that ships logs to Better Stack."""

    def __init__(self, api_token: str, source_token: str, host: str = "in.logs.betterstack.com"):
        super().__init__()
        self.api_token = api_token
        self.source_token = source_token
        self.host = host
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100
        self._flush_interval = 5.0
        self._last_flush = datetime.now(timezone.utc)
        self._lock = threading.Lock()
        self._client = None

    def _get_client(self):
        if httpx is None:
            return None
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to Better Stack."""
        try:
            log_entry = self._format_log_entry(record)
            with self._lock:
                self._buffer.append(log_entry)
                if len(self._buffer) >= self._buffer_size or self._should_flush():
                    self._flush()

        except Exception as e:
            self.handleError(record)

    def _should_flush(self) -> bool:
        """Check if buffer should be flushed based on time."""
        now = datetime.now(timezone.utc)
        elapsed = (now - self._last_flush).total_seconds()
        return elapsed >= self._flush_interval

    def _format_log_entry(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Format a log record as a structured log entry."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "service": "portkit-backend",
        }

        if hasattr(record, "trace_id") and record.trace_id:
            log_entry["trace_id"] = record.trace_id

        if hasattr(record, "span_id") and record.span_id:
            log_entry["span_id"] = record.span_id

        if record.exc_info:
            log_entry["exception"] = self.formatter.formatException(record.exc_info)

        if record.name:
            log_entry["logger"] = record.name

        if record.funcName:
            log_entry["function"] = record.funcName

        if record.lineno:
            log_entry["line"] = record.lineno

        return log_entry

    def _flush(self) -> None:
        """Flush buffered logs to Better Stack."""
        if not self._buffer:
            return

        logs_to_send = self._buffer[:]
        self._buffer = []
        self._last_flush = datetime.now(timezone.utc)

        try:
            import asyncio
            asyncio.create_task(self._send_logs_async(logs_to_send))
        except RuntimeError:
            self._send_logs_sync(logs_to_send)

    async def _send_logs_async(self, logs: List[Dict[str, Any]]) -> None:
        """Send logs asynchronously to Better Stack."""
        client = self._get_client()
        if client is None:
            return

        try:
            url = f"https://{self.host}/api/v1/bulk"
            headers = {
                "Authorization": f"Bearer {self.source_token}",
                "Content-Type": "application/json",
            }
            payload = {"logs": logs}
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code not in (200, 201, 202, 204):
                logger.warning(f"Failed to send logs to Better Stack: {response.status_code}")
        except Exception as e:
            logger.warning(f"Error sending logs to Better Stack: {e}")

    def _send_logs_sync(self, logs: List[Dict[str, Any]]) -> None:
        """Send logs synchronously to Better Stack (fallback)."""
        try:
            import urllib.request
            import urllib.error

            url = f"https://{self.host}/api/v1/bulk"
            headers = {
                "Authorization": f"Bearer {self.source_token}",
                "Content-Type": "application/json",
            }
            payload = json.dumps({"logs": logs}).encode("utf-8")
            request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status not in (200, 201, 202, 204):
                    logger.warning(f"Failed to send logs to Better Stack: {response.status}")
        except Exception as e:
            logger.warning(f"Error sending logs to Better Stack: {e}")


class StructuredLogger:
    """Structured logger with context propagation for Better Stack."""

    def __init__(self, name: str = "portkit"):
        self.logger = logging.getLogger(name)
        self._trace_id: Optional[str] = None
        self._span_id: Optional[str] = None
        self._context: Dict[str, Any] = {}

    def set_trace_context(self, trace_id: Optional[str], span_id: Optional[str] = None) -> None:
        """Set trace context for log correlation."""
        self._trace_id = trace_id
        self._span_id = span_id
        TRACE_ID_CTX.set(trace_id)
        SPAN_ID_CTX.set(span_id)

    def set_context(self, **kwargs) -> None:
        """Set additional context for all subsequent logs."""
        self._context.update(kwargs)

    def clear_context(self) -> None:
        """Clear the log context."""
        self._context = {}

    def _build_log_entry(self, level: str, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build a structured log entry."""
        trace_id = self._trace_id or TRACE_ID_CTX.get()
        span_id = self._span_id or SPAN_ID_CTX.get()

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "service": "portkit-backend",
        }

        if trace_id:
            entry["trace_id"] = trace_id
        if span_id:
            entry["span_id"] = span_id

        if context:
            entry["context"] = {**self._context, **context}
        elif self._context:
            entry["context"] = self._context.copy()

        return entry

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log debug message."""
        entry = self._build_log_entry("DEBUG", message, context)
        entry.update(kwargs)
        self.logger.debug(json.dumps(entry))

    def info(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log info message."""
        entry = self._build_log_entry("INFO", message, context)
        entry.update(kwargs)
        self.logger.info(json.dumps(entry))

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log warning message."""
        entry = self._build_log_entry("WARNING", message, context)
        entry.update(kwargs)
        self.logger.warning(json.dumps(entry))

    def error(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log error message."""
        entry = self._build_log_entry("ERROR", message, context)
        entry.update(kwargs)
        self.logger.error(json.dumps(entry))

    def critical(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log critical message."""
        entry = self._build_log_entry("CRITICAL", message, context)
        entry.update(kwargs)
        self.logger.critical(json.dumps(entry))


def get_better_stack_handler() -> Optional[BetterStackHandler]:
    """Get configured Better Stack handler if credentials are available."""
    source_token = os.getenv("BETTERSTACK_SOURCE_TOKEN")
    api_token = os.getenv("BETTERSTACK_API_TOKEN")

    if not source_token:
        logger.debug("Better Stack source token not configured")
        return None

    return BetterStackHandler(api_token=api_token or "", source_token=source_token)


def setup_logging(
    service_name: str = "portkit-backend",
    log_level: str = "INFO",
) -> None:
    """
    Set up logging with Better Stack integration.

    Args:
        service_name: Name of the service for log attribution
        log_level: Minimum log level to capture
    """
    handler = get_better_stack_handler()

    if handler:
        handler.setFormatter(logging.Formatter("%(message)s"))
        logging.root.addHandler(handler)
        logger.info("Better Stack log handler configured")

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        handlers=[handler] if handler else [],
    )


def log_with_trace(func):
    """Decorator to automatically add trace context to log messages."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        trace_id = TRACE_ID_CTX.get()
        span_id = SPAN_ID_CTX.get()

        if hasattr(func, "__name__"):
            extra = {"trace_id": trace_id, "span_id": span_id}
        else:
            extra = {}

        for key, value in extra.items():
            if value:
                setattr(logging, key, value)

        return func(*args, **kwargs)
    return wrapper


def get_log_aggregator():
    """Get the log aggregator instance for testing."""
    return StructuredLogger("portkit")
