"""
Custom Exception Handlers for ModPorter AI Backend

Provides comprehensive error handling with user-friendly messages,
graceful degradation, and structured logging.
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

# Configure logging
logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Structured error response model"""
    error_id: str
    error_type: str
    message: str
    user_message: str
    timestamp: str
    path: Optional[str] = None
    method: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ModPorterException(Exception):
    """Base exception for ModPorter-specific errors"""
    default_user_message = "An error occurred. Please try again."
    default_error_type = "internal_error"
    default_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def __init__(
        self,
        message: str,
        user_message: Optional[str] = None,
        error_type: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.user_message = user_message or getattr(self, 'default_user_message', self.default_user_message)
        self.error_type = error_type or getattr(self, 'default_error_type', self.default_error_type)
        self.status_code = status_code or getattr(self, 'default_status_code', self.default_status_code)
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


# ============================================
# Error Categories (Issue #455)
# ============================================

class ParseError(ModPorterException):
    """Exception raised when parsing fails (e.g., invalid mod file format)"""
    default_user_message = "Unable to parse the mod file. Please ensure it's a valid Java mod archive."
    default_error_type = "parse_error"
    default_status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class AssetError(ModPorterException):
    """Exception raised when asset processing fails"""
    default_user_message = "Failed to process mod assets. Some textures or models may not have converted."
    default_error_type = "asset_error"
    default_status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class LogicError(ModPorterException):
    """Exception raised when mod logic cannot be translated"""
    default_user_message = "Some mod logic could not be converted. The mod may not function identically."
    default_error_type = "logic_error"
    default_status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class PackageError(ModPorterException):
    """Exception raised when packaging the mod fails"""
    default_user_message = "Failed to package the converted mod. Please try again."
    default_error_type = "package_error"
    default_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


def create_error_response(
    error: Exception,
    request: Request,
    include_traceback: bool = False
) -> ErrorResponse:
    """Create a structured error response"""
    error_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow().isoformat()
    
    # Determine error type and user message
    if isinstance(error, ModPorterException):
        error_type = error.error_type
        user_message = error.user_message
        message = error.message
        details = error.details
    elif isinstance(error, HTTPException):
        error_type = "http_error"
        user_message = error.detail
        message = str(error.detail)
        details = {"status_code": error.status_code}
    elif isinstance(error, RequestValidationError):
        error_type = "validation_error"
        user_message = "Invalid request data. Please check your input."
        message = str(error)
        details = {"errors": error.errors()}
    else:
        error_type = "internal_error"
        user_message = "An unexpected error occurred. Please try again later."
        message = str(error)
        details = {}
    
    # Add traceback in development
    if include_traceback:
        details["traceback"] = traceback.format_exc()
    
    return ErrorResponse(
        error_id=error_id,
        error_type=error_type,
        message=message,
        user_message=user_message,
        timestamp=timestamp,
        path=str(request.url.path),
        method=request.method,
        details=details
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
    
    # Register base exception handlers
    # Note: ParseError, AssetError, LogicError, PackageError are handled
    # automatically by ModPorterException handler via isinstance dispatch
    app.add_exception_handler(ModPorterException, modporter_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
