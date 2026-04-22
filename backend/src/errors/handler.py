"""
Error Handler with Retry Logic and Exception Handlers

Handles errors with exponential backoff, categorization, and FastAPI exception handlers.
"""

import logging
import os
import traceback
from typing import Any, Callable, Dict, Optional, TypeVar
from functools import wraps

import uuid
from datetime import datetime, timezone

import asyncio
import time

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from .classifier import ErrorType, ErrorSeverity, ErrorClassification
from .models import RecoveryAction, RecoveryStrategy

logger = logging.getLogger(__name__)

T = TypeVar("T")


# --- Error Handler (from error_handler.py) ---


class ConversionError(Exception):
    """Base exception for conversion errors."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable
        self.message = message


class AIEngineUnavailableError(ConversionError):
    """AI Engine is unavailable."""

    def __init__(self, message: str = "AI Engine unavailable"):
        super().__init__(message, retryable=True)


class ConversionTimeoutError(ConversionError):
    """Conversion timed out."""

    def __init__(self, message: str = "Conversion timed out"):
        super().__init__(message, retryable=True)


class InvalidInputError(ConversionError):
    """Invalid input provided."""

    def __init__(self, message: str):
        super().__init__(message, retryable=False)


class ModelUnavailableError(ConversionError):
    """Translation model unavailable."""

    def __init__(self, message: str = "Model unavailable"):
        super().__init__(message, retryable=True)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (
        AIEngineUnavailableError,
        ConversionTimeoutError,
        ModelUnavailableError,
    ),
):
    """
    Decorator for retrying with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        retryable_exceptions: Tuple of exceptions that trigger retry
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except retryable_exceptions as e:
                    last_exception = e

                    if attempt >= max_retries:
                        logger.error(f"Max retries exceeded for {func.__name__}: {e}")
                        raise

                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    jitter = delay * 0.1 * (0.5 + asyncio.get_event_loop().time() % 1)
                    total_delay = delay + jitter

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {total_delay:.2f}s"
                    )

                    await asyncio.sleep(total_delay)

                except ConversionError as e:
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise

                except Exception as e:
                    logger.exception(f"Unexpected error in {func.__name__}: {e}")
                    raise ConversionError(f"Unexpected error: {e}", retryable=False)

            raise last_exception

        return wrapper

    return decorator


def categorize_error(error: Exception) -> dict:
    """
    Categorize an error for user-friendly messaging.
    """
    if isinstance(error, InvalidInputError):
        return {
            "category": "invalid_input",
            "user_message": "The provided mod file has issues. Please check the file and try again.",
            "technical_details": error.message,
            "retryable": False,
        }

    elif isinstance(error, (AIEngineUnavailableError, ModelUnavailableError)):
        return {
            "category": "service_unavailable",
            "user_message": "The conversion service is temporarily unavailable. Please try again in a few moments.",
            "technical_details": error.message,
            "retryable": True,
        }

    elif isinstance(error, ConversionTimeoutError):
        return {
            "category": "timeout",
            "user_message": "The conversion took too long. Please try again with a smaller mod file.",
            "technical_details": error.message,
            "retryable": True,
        }

    elif isinstance(error, ConversionError):
        return {
            "category": "conversion_error",
            "user_message": "An error occurred during conversion. Please try again.",
            "technical_details": error.message,
            "retryable": error.retryable,
        }

    else:
        return {
            "category": "unknown",
            "user_message": "An unexpected error occurred. Our team has been notified.",
            "technical_details": str(error),
            "retryable": False,
        }


def get_user_friendly_error(error: Exception) -> str:
    """Get user-friendly error message."""
    category = categorize_error(error)
    return category["user_message"]


class ErrorHandler:
    """Centralized error handler for conversion service."""

    def __init__(self):
        self._error_counts = {}
        self._last_error_time = {}

    def record_error(self, error: Exception, job_id: Optional[str] = None):
        """Record an error for monitoring."""
        error_type = type(error).__name__

        if error_type not in self._error_counts:
            self._error_counts[error_type] = 0

        self._error_counts[error_type] += 1
        self._last_error_time[error_type] = time.time()

        logger.error(
            f"Error recorded: {error_type} - {error}", extra={"job_id": job_id} if job_id else {}
        )

    def get_error_stats(self) -> dict:
        """Get error statistics."""
        return {
            "error_counts": self._error_counts.copy(),
            "last_error_times": self._last_error_time.copy(),
            "total_errors": sum(self._error_counts.values()),
        }

    def should_alert(self, error_type: str, threshold: int = 10, window_seconds: int = 300) -> bool:
        """Check if we should alert on this error type."""
        count = self._error_counts.get(error_type, 0)
        last_time = self._last_error_time.get(error_type, 0)

        if count >= threshold and (time.time() - last_time) < window_seconds:
            return True

        return False


_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get or create error handler singleton."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


# --- Error Handlers (from error_handlers.py) ---


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return os.getenv("DEBUG", "false").lower() == "true"


DEBUG_MODE = is_debug_mode()


try:
    from services.metrics import record_error

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

try:
    from services.structured_logging import correlation_id_var, set_correlation_id
except ImportError:
    correlation_id_var = None

    def set_correlation_id() -> str:
        return str(uuid.uuid4())[:8]


class ErrorResponse(BaseModel):
    """Structured error response model"""

    error_id: str
    error_code: str
    error_type: str
    error_category: str
    message: str
    user_message: str
    is_retryable: bool
    timestamp: str
    path: Optional[str] = None
    method: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None


class PortkitException(Exception):
    """Base exception for Portkit-specific errors"""

    def __init__(
        self,
        message: str,
        user_message: str = "An error occurred. Please try again.",
        error_type: str = "internal_error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.user_message = user_message
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ConversionException(PortkitException):
    """Exception raised during mod conversion"""

    def __init__(
        self,
        message: str,
        user_message: str = "Conversion failed. Please check your mod file and try again.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="conversion_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class FileProcessingException(PortkitException):
    """Exception raised during file processing"""

    def __init__(
        self,
        message: str,
        user_message: str = "Failed to process file. Please ensure it's a valid mod file.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="file_processing_error",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class ValidationException(PortkitException):
    """Exception raised during validation"""

    def __init__(
        self,
        message: str,
        user_message: str = "Validation failed. Please check your input.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="validation_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class NotFoundException(PortkitException):
    """Exception raised when a resource is not found"""

    def __init__(self, resource: str, resource_id: str, user_message: Optional[str] = None):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            user_message=user_message or f"Requested {resource} not found.",
            error_type="not_found_error",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "resource_id": resource_id},
        )


ERROR_CATEGORIES = {
    "parse_error": "Failed to parse the mod file. Please check the file format.",
    "asset_error": "Error processing mod assets. Some assets may be missing.",
    "logic_error": "An internal conversion error occurred. Please try again.",
    "package_error": "Error packaging the converted mod. Please try again.",
    "validation_error": "Validation failed. Please check your input.",
    "network_error": "Network error. Please check your connection and try again.",
    "rate_limit_error": "Too many requests. Please wait and try again.",
    "timeout_error": "Operation timed out. Please try again.",
    "unknown_error": "An unexpected error occurred. Please try again later.",
    "conversion_error": "Conversion failed. Please check your mod file.",
    "http_error": "An error occurred while processing your request.",
}

ERROR_CODES = {
    "parse_error": "PARSE_ERROR",
    "asset_error": "ASSET_ERROR",
    "logic_error": "LOGIC_ERROR",
    "package_error": "PACKAGE_ERROR",
    "validation_error": "VALIDATION_ERROR",
    "network_error": "NETWORK_ERROR",
    "rate_limit_error": "RATE_LIMIT_ERROR",
    "timeout_error": "TIMEOUT_ERROR",
    "unknown_error": "UNKNOWN_ERROR",
    "conversion_error": "CONVERSION_ERROR",
    "http_error": "HTTP_ERROR",
    "file_processing_error": "FILE_PROCESSING_ERROR",
    "internal_error": "INTERNAL_ERROR",
}

RETRYABLE_ERROR_CATEGORIES = {
    "parse_error",
    "asset_error",
    "package_error",
    "network_error",
    "rate_limit_error",
    "timeout_error",
}

NON_RETRYABLE_ERROR_CATEGORIES = {
    "logic_error",
    "validation_error",
    "unknown_error",
    "conversion_error",
    "http_error",
    "file_processing_error",
    "internal_error",
}


class RateLimitException(PortkitException):
    """Exception raised when rate limit is exceeded"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        user_message: str = "Too many requests. Please wait a moment and try again.",
        retry_after: Optional[int] = None,
    ):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="rate_limit_error",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class ParseError(PortkitException):
    """Error during file parsing"""

    def __init__(
        self,
        message: str,
        user_message: str = "Failed to parse the mod file. Please check the file format.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="parse_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class AssetError(PortkitException):
    """Error with asset processing"""

    def __init__(
        self,
        message: str,
        user_message: str = "Error processing mod assets. Some assets may be missing.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="asset_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class LogicError(PortkitException):
    """Error in conversion logic"""

    def __init__(
        self,
        message: str,
        user_message: str = "An internal conversion error occurred. Please try again.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="logic_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class PackageError(PortkitException):
    """Error during packaging"""

    def __init__(
        self,
        message: str,
        user_message: str = "Error packaging the converted mod. Please try again.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="package_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


def _categorize_error(error: Exception) -> str:
    """Categorize an error based on its type."""
    error_type = type(error).__name__
    error_msg = str(error).lower()

    if isinstance(error, ParseError):
        return "parse_error"
    if isinstance(error, AssetError):
        return "asset_error"
    if isinstance(error, LogicError):
        return "logic_error"
    if isinstance(error, PackageError):
        return "package_error"
    if isinstance(error, ValidationError):
        return "validation_error"
    if isinstance(error, RateLimitException):
        return "rate_limit_error"
    if isinstance(error, ConversionError):
        return "conversion_error"

    if "parse" in error_type.lower() or "parse" in error_msg:
        return "parse_error"
    if "asset" in error_type.lower() or "asset" in error_msg:
        return "asset_error"
    if "logic" in error_type.lower() or "convert" in error_msg:
        return "logic_error"
    if "package" in error_type.lower() or "packag" in error_msg:
        return "package_error"
    if "valid" in error_type.lower() or "validation" in error_msg or "invalid" in error_msg:
        return "validation_error"
    if "network" in error_type.lower() or "connection" in error_msg:
        return "network_error"
    if "rate limit" in error_msg or "429" in error_msg:
        return "rate_limit_error"
    if "timeout" in error_type.lower() or "timeout" in error_msg:
        return "timeout_error"

    return "unknown_error"


def create_error_response(
    error: Exception, request: Request, include_traceback: bool = False
) -> ErrorResponse:
    """Create a structured error response."""
    error_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).isoformat()

    correlation_id = None
    if correlation_id_var:
        correlation_id = correlation_id_var.get()
    if not correlation_id:
        correlation_id = set_correlation_id()

    if isinstance(error, PortkitException):
        error_type = error.error_type
        error_category = _categorize_error(error)
        user_message = error.user_message
        message = error.message
        details = error.details if is_debug_mode() else {}
    elif isinstance(error, HTTPException):
        error_type = "http_error"
        error_category = _categorize_error(error)
        user_message = error.detail
        message = str(error.detail)
        details = {"status_code": error.status_code} if is_debug_mode() else {}
    elif isinstance(error, RequestValidationError):
        error_type = "validation_error"
        error_category = "validation_error"
        user_message = "Invalid request data. Please check your input."
        message = str(error)
        details = {"errors": error.errors()} if is_debug_mode() else {}
    else:
        error_type = "internal_error"
        error_category = _categorize_error(error)
        user_message = ERROR_CATEGORIES.get(
            error_category, "An unexpected error occurred. Please try again later."
        )
        message = str(error) if is_debug_mode() else "An internal server error occurred"
        details = {}

    if include_traceback and is_debug_mode():
        details["traceback"] = traceback.format_exc()

    error_code = ERROR_CODES.get(error_category, "UNKNOWN_ERROR")
    is_retryable = error_category in RETRYABLE_ERROR_CATEGORIES

    return ErrorResponse(
        error_id=error_id,
        error_code=error_code,
        error_type=error_type,
        error_category=error_category,
        message=message,
        user_message=user_message,
        is_retryable=is_retryable,
        timestamp=timestamp,
        path=str(request.url.path),
        method=request.method,
        details=details,
        correlation_id=correlation_id,
    )


def _record_error_metric(error_category: str, error_type: str, source: str = "api"):
    """Record error metrics if metrics are available."""
    if METRICS_AVAILABLE:
        try:
            record_error(error_category, error_type, source)
        except Exception:
            pass


async def portkit_exception_handler(request: Request, exc: PortkitException) -> JSONResponse:
    """Handler for Portkit-specific exceptions"""
    error_response = create_error_response(exc, request)
    logger.error(
        f"[{error_response.error_id}] {error_response.error_type}: {error_response.message}"
    )

    _record_error_metric(
        error_category=error_response.error_category,
        error_type=error_response.error_type,
        source="api",
    )

    return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler for HTTP exceptions"""
    error_response = create_error_response(exc, request)
    logger.warning(f"[{error_response.error_id}] HTTP {exc.status_code}: {error_response.message}")

    if exc.status_code >= 400:
        _record_error_metric(
            error_category=error_response.error_category, error_type="HTTPException", source="api"
        )

    return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handler for validation exceptions"""
    error_response = create_error_response(exc, request)
    logger.warning(f"[{error_response.error_id}] Validation error: {error_response.message}")

    _record_error_metric(
        error_category="validation_error", error_type="RequestValidationError", source="api"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_response.model_dump()
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for all other exceptions"""
    logger.error(f"[{exc.__class__.__name__}] Unhandled exception: {str(exc)}", exc_info=True)

    error_response = create_error_response(exc, request, include_traceback=False)

    _record_error_metric(
        error_category=error_response.error_category, error_type=type(exc).__name__, source="api"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_response.model_dump()
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app"""
    import inspect

    handlers_to_register = [
        (PortkitException, portkit_exception_handler, "PortkitException"),
        (HTTPException, http_exception_handler, "HTTPException"),
        (RequestValidationError, validation_exception_handler, "RequestValidationError"),
        (Exception, generic_exception_handler, "Exception"),
    ]

    for exception_class, handler_func, handler_name in handlers_to_register:
        if not callable(handler_func):
            raise TypeError(
                f"Cannot register handler '{handler_name}': not callable. "
                f"Got type: {type(handler_func)}"
            )

        try:
            sig = inspect.signature(handler_func)
            params = list(sig.parameters.keys())
            if len(params) < 2:
                raise TypeError(
                    f"Cannot register handler '{handler_name}': expected at least 2 parameters "
                    f"(request, exc), but handler has {len(params)} parameter(s): {params}. "
                    f"Full signature: {sig}"
                )
        except ValueError:
            pass

        app.add_exception_handler(exception_class, handler_func)


def verify_exception_handlers(app) -> Dict[str, bool]:
    """Verify that exception handlers are properly registered."""
    handlers_to_check = [
        ("PortkitException", PortkitException),
        ("HTTPException", HTTPException),
        ("RequestValidationError", RequestValidationError),
        ("Generic Exception", Exception),
    ]

    result = {}
    for name, exc_class in handlers_to_check:
        has_handler = exc_class in getattr(app, "exception_handlers", {})
        result[name] = has_handler

    return result
