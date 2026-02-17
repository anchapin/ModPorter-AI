"""
Custom Exception Handlers for ModPorter AI Backend

Provides comprehensive error handling with user-friendly messages,
graceful degradation, and structured logging.

Issue: #455 - Comprehensive Error Handling (Phase 3)
"""

import logging
import traceback
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from datetime import datetime
import uuid

from .structured_logging import correlation_id_var, set_correlation_id

# Configure logging
logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Structured error response model"""
    error_id: str
    error_type: str
    error_category: str  # New: parse_error, asset_error, logic_error, etc.
    message: str
    user_message: str
    timestamp: str
    path: Optional[str] = None
    method: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None  # New: correlation ID for tracing


class ModPorterException(Exception):
    """Base exception for ModPorter-specific errors"""
    def __init__(
        self,
        message: str,
        user_message: str = "An error occurred. Please try again.",
        error_type: str = "internal_error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.user_message = user_message
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ConversionException(ModPorterException):
    """Exception raised during mod conversion"""
    def __init__(
        self,
        message: str,
        user_message: str = "Conversion failed. Please check your mod file and try again.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="conversion_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class FileProcessingException(ModPorterException):
    """Exception raised during file processing"""
    def __init__(
        self,
        message: str,
        user_message: str = "Failed to process file. Please ensure it's a valid mod file.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="file_processing_error",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class ValidationException(ModPorterException):
    """Exception raised during validation"""
    def __init__(
        self,
        message: str,
        user_message: str = "Validation failed. Please check your input.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="validation_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class NotFoundException(ModPorterException):
    """Exception raised when a resource is not found"""
    def __init__(
        self,
        resource: str,
        resource_id: str,
        user_message: Optional[str] = None
    ):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            user_message=user_message or f"Requested {resource} not found.",
            error_type="not_found_error",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "resource_id": resource_id}
        )


# Error categories matching Issue #455
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
}


class RateLimitException(ModPorterException):
    """Exception raised when rate limit is exceeded"""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        user_message: str = "Too many requests. Please wait a moment and try again.",
        retry_after: Optional[int] = None
    ):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="rate_limit_error",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


# New error categories for Issue #455
class ParseError(ModPorterException):
    """Error during file parsing"""
    def __init__(
        self,
        message: str,
        user_message: str = "Failed to parse the mod file. Please check the file format.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="parse_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class AssetError(ModPorterException):
    """Error with asset processing"""
    def __init__(
        self,
        message: str,
        user_message: str = "Error processing mod assets. Some assets may be missing.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="asset_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class LogicError(ModPorterException):
    """Error in conversion logic"""
    def __init__(
        self,
        message: str,
        user_message: str = "An internal conversion error occurred. Please try again.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="logic_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class PackageError(ModPorterException):
    """Error during packaging"""
    def __init__(
        self,
        message: str,
        user_message: str = "Error packaging the converted mod. Please try again.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            user_message=user_message,
            error_type="package_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


def _categorize_error(error: Exception) -> str:
    """
    Categorize an error based on its type.
    
    Returns one of: parse_error, asset_error, logic_error, 
                    package_error, validation_error, network_error,
                    rate_limit_error, timeout_error, unknown_error
    """
    error_type = type(error).__name__
    error_msg = str(error).lower()
    
    # Check specific error types
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
    
    # Check error message patterns
    if "parse" in error_type.lower() or "parse" in error_msg:
        return "parse_error"
    if "asset" in error_type.lower() or "asset" in error_msg:
        return "asset_error"
    if "logic" in error_type.lower() or "convert" in error_msg:
        return "logic_error"
    if "package" in error_type.lower() or "packag" in error_msg:
        return "package_error"
    if "valid" in error_type.lower() or "valid" in error_msg:
        return "validation_error"
    if "network" in error_type.lower() or "connection" in error_msg:
        return "network_error"
    if "rate limit" in error_msg or "429" in error_msg:
        return "rate_limit_error"
    if "timeout" in error_type.lower() or "timeout" in error_msg:
        return "timeout_error"
    
    return "unknown_error"


def create_error_response(
    error: Exception,
    request: Request,
    include_traceback: bool = False
) -> ErrorResponse:
    """Create a structured error response"""
    error_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow().isoformat()
    
    # Get or create correlation ID
    correlation_id = correlation_id_var.get()
    if not correlation_id:
        correlation_id = set_correlation_id()
    
    # Determine error type, category and user message
    if isinstance(error, ModPorterException):
        error_type = error.error_type
        error_category = _categorize_error(error)
        user_message = error.user_message
        message = error.message
        details = error.details
    elif isinstance(error, HTTPException):
        error_type = "http_error"
        error_category = _categorize_error(error)
        user_message = error.detail
        message = str(error.detail)
        details = {"status_code": error.status_code}
    elif isinstance(error, RequestValidationError):
        error_type = "validation_error"
        error_category = "validation_error"
        user_message = "Invalid request data. Please check your input."
        message = str(error)
        details = {"errors": error.errors()}
    else:
        error_type = "internal_error"
        error_category = _categorize_error(error)
        user_message = ERROR_CATEGORIES.get(error_category, "An unexpected error occurred. Please try again later.")
        message = str(error)
        details = {}
    
    # Add traceback in development
    if include_traceback:
        details["traceback"] = traceback.format_exc()
    
    return ErrorResponse(
        error_id=error_id,
        error_type=error_type,
        error_category=error_category,
        message=message,
        user_message=user_message,
        timestamp=timestamp,
        path=str(request.url.path),
        method=request.method,
        details=details,
        correlation_id=correlation_id
    )


async def modporter_exception_handler(
    request: Request,
    exc: ModPorterException
) -> JSONResponse:
    """Handler for ModPorter-specific exceptions"""
    error_response = create_error_response(exc, request)
    logger.error(
        f"[{error_response.error_id}] {error_response.error_type}: {error_response.message}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """Handler for HTTP exceptions"""
    error_response = create_error_response(exc, request)
    logger.warning(
        f"[{error_response.error_id}] HTTP {exc.status_code}: {error_response.message}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handler for validation exceptions"""
    error_response = create_error_response(exc, request)
    logger.warning(
        f"[{error_response.error_id}] Validation error: {error_response.message}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handler for all other exceptions"""
    error_response = create_error_response(exc, request, include_traceback=True)
    logger.error(
        f"[{error_response.error_id}] Unhandled exception: {error_response.message}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app"""
    from fastapi import FastAPI
    from fastapi.exceptions import RequestValidationError
    
    app.add_exception_handler(ModPorterException, modporter_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
