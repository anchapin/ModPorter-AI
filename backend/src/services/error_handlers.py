"""
Error Handlers - backward compatibility re-export.

This module re-exports the canonical error handling components from errors/.

All error handling has been consolidated into the errors/ package:
- errors/handler.py: Exception classes and FastAPI handlers
- errors/classifier.py: Error type classification
- errors/models.py: Recovery strategies
- errors/recovery.py: Error recovery system
"""

from errors import (
    ErrorResponse,
    PortkitException,
    ConversionException,
    FileProcessingException,
    ValidationException,
    NotFoundException,
    RateLimitException,
    ParseError,
    AssetError,
    LogicError,
    PackageError,
    ERROR_CATEGORIES,
    ERROR_CODES,
    RETRYABLE_ERROR_CATEGORIES,
    NON_RETRYABLE_ERROR_CATEGORIES,
    _categorize_error,
    create_error_response,
    register_exception_handlers,
    verify_exception_handlers,
    portkit_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    is_debug_mode,
    DEBUG_MODE,
)

__all__ = [
    "ErrorResponse",
    "PortkitException",
    "ConversionException",
    "FileProcessingException",
    "ValidationException",
    "NotFoundException",
    "RateLimitException",
    "ParseError",
    "AssetError",
    "LogicError",
    "PackageError",
    "ERROR_CATEGORIES",
    "ERROR_CODES",
    "RETRYABLE_ERROR_CATEGORIES",
    "NON_RETRYABLE_ERROR_CATEGORIES",
    "_categorize_error",
    "create_error_response",
    "register_exception_handlers",
    "verify_exception_handlers",
    "portkit_exception_handler",
    "http_exception_handler",
    "validation_exception_handler",
    "generic_exception_handler",
    "is_debug_mode",
    "DEBUG_MODE",
]
