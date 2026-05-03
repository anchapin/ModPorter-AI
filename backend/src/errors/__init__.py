"""
Error Handling Package for Portkit Backend

This package consolidates all error handling code into a single location:
- classifier.py: Error type classification and severity
- models.py: Error patterns and recovery strategies
- handler.py: Error handler with retry logic + exception handlers
- recovery.py: Error recovery system with supervisor pattern

For backward compatibility, this __init__.py re-exports all public symbols
from the legacy services/ location.
"""

from .classifier import (
    ErrorType,
    ErrorSeverity,
    ErrorClassification,
    ErrorClassifier,
    get_classifier,
    classify_error,
    ERROR_PATTERNS,
    ERROR_SEVERITY,
    ERROR_USER_MESSAGES,
)

from .models import (
    RecoveryStrategy,
    RecoveryAction,
    ErrorPattern,
    ErrorPatternLibrary,
    get_pattern_library,
    get_recovery_actions,
    should_escalate,
    get_fallback_mode,
)

from .handler import (
    ConversionError,
    AIEngineUnavailableError,
    ConversionTimeoutError,
    InvalidInputError,
    ModelUnavailableError,
    retry_with_backoff,
    categorize_error,
    get_user_friendly_error,
    ErrorHandler,
    get_error_handler,
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

from .recovery import (
    RecoveryStatus,
    RecoveryAttempt,
    RecoveryResult,
    DegradedModeManager,
    EscalationManager,
    RecoveryStrategyExecutor,
    ErrorSupervisor,
    with_supervision,
    get_supervisor,
    recover,
)

__all__ = [
    # classifier
    "ErrorType",
    "ErrorSeverity",
    "ErrorClassification",
    "ErrorClassifier",
    "get_classifier",
    "classify_error",
    "ERROR_PATTERNS",
    "ERROR_SEVERITY",
    "ERROR_USER_MESSAGES",
    # models
    "RecoveryStrategy",
    "RecoveryAction",
    "ErrorPattern",
    "ErrorPatternLibrary",
    "get_pattern_library",
    "get_recovery_actions",
    "should_escalate",
    "get_fallback_mode",
    # handler (error_handler.py)
    "ConversionError",
    "AIEngineUnavailableError",
    "ConversionTimeoutError",
    "InvalidInputError",
    "ModelUnavailableError",
    "retry_with_backoff",
    "categorize_error",
    "get_user_friendly_error",
    "ErrorHandler",
    "get_error_handler",
    # handler (error_handlers.py)
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
    # recovery
    "RecoveryStatus",
    "RecoveryAttempt",
    "RecoveryResult",
    "DegradedModeManager",
    "EscalationManager",
    "RecoveryStrategyExecutor",
    "ErrorSupervisor",
    "with_supervision",
    "get_supervisor",
    "recover",
]
