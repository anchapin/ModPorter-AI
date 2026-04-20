"""
Error Classifier for ModPorter AI Backend

Provides error type classification with severity levels and pattern matching
to enable intelligent error recovery strategies.

GAP-2.5-04: Enhanced Auto-Recovery
"""

import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Enumeration of error types for classification."""

    NETWORK = "network"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    PARSE = "parse"
    ASSET = "asset"
    LOGIC = "logic"
    PACKAGE = "package"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    QUOTA_EXCEEDED = "quota_exceeded"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


class ErrorSeverity(str, Enum):
    """Enumeration of error severity levels."""

    BLOCKING = "blocking"  # Fatal error, cannot continue
    WARNING = "warning"  # Non-fatal, can try alternative approach
    INFO = "info"  # Informational, no action needed


# Pattern definitions for error type classification
ERROR_PATTERNS: Dict[ErrorType, List[str]] = {
    ErrorType.NETWORK: [
        r"connection.*refused",
        r"connection.*timeout",
        r"network.*unreachable",
        r"dns.*fail",
        r"socket.*error",
        r"broken.*pipe",
        r"connection.*reset",
        r"remote.*close",
        r"host.*unreachable",
        r"no.*route.*host",
        r"httpx\..*connect",
        r"requests\..*connection",
        r"ai_engine.*unavailable",
    ],
    ErrorType.VALIDATION: [
        r"validation.*error",
        r"invalid.*input",
        r"invalid.*parameter",
        r"invalid.*value",
        r"malformed",
        r"schema.*error",
        r"required.*field",
        r"field.*required",
        r"constraint.*violation",
        r"pydantic.*validation",
        r"value.*error",
        r"type.*error",
    ],
    ErrorType.TIMEOUT: [
        r"timeout",
        r"timed.*out",
        r"operation.*timeout",
        r"request.*timeout",
        r"read.*timeout",
        r"connect.*timeout",
        r"asyncio.*timeout",
        r"deadline.*exceeded",
    ],
    ErrorType.PARSE: [
        r"parse.*error",
        r"failed.*parse",
        r"syntax.*error",
        r"invalid.*syntax",
        r"unexpected.*token",
        r"json.*decode",
        r"yaml.*error",
        r"toml.*error",
        r"xml.*parse",
    ],
    ErrorType.ASSET: [
        r"asset.*error",
        r"asset.*not.*found",
        r"missing.*asset",
        r"texture.*error",
        r"model.*error",
        r"sound.*error",
        r"resource.*not.*found",
        r"file.*not.*found",
    ],
    ErrorType.LOGIC: [
        r"logic.*error",
        r"conversion.*error",
        r"internal.*error",
        r"unexpected.*error",
        r"illegal.*state",
        r"null.*pointer",
        r"nil.*reference",
        r"attribute.*error",
        r"key.*error",
        r"index.*error",
    ],
    ErrorType.PACKAGE: [
        r"package.*error",
        r"packaging.*error",
        r"failed.*package",
        r"archive.*error",
        r"zip.*error",
        r"tar.*error",
        r"compression.*error",
        r"zip.*archive",
        r"failed.*zip",
        r"failed.*tar",
        r"failed.*archive",
        r"creating.*zip",
        r"creating.*archive",
    ],
    ErrorType.RATE_LIMIT: [
        r"rate.*limit",
        r"too.*many.*request",
        r"429",
        r"throttle",
        r"quota.*exceeded",
        r"rate.*exceeded",
        r"slow.*down",
    ],
    ErrorType.AUTHENTICATION: [
        r"auth.*error",
        r"authentication.*fail",
        r"invalid.*token",
        r"expired.*token",
        r"missing.*token",
        r"unauthorized",
        r"invalid.*credentials",
        r"login.*fail",
    ],
    ErrorType.AUTHORIZATION: [
        r"permission.*denied",
        r"access.*denied",
        r"forbidden",
        r"insufficient.*privilege",
        r"not.*authorized",
        r"403",
    ],
    ErrorType.NOT_FOUND: [
        r"not.*found",
        r"404",
        r"does.*not.*exist",
        r"resource.*not.*found",
        r"file.*not.*found",
        r"endpoint.*not.*found",
    ],
    ErrorType.CONFLICT: [
        r"conflict",
        r"already.*exist",
        r"duplicate.*entry",
        r"409",
        r"resource.*conflict",
    ],
    ErrorType.QUOTA_EXCEEDED: [
        r"quota.*exceeded",
        r"disk.*quota",
        r"storage.*quota",
        r"limit.*exceeded",
        r"memory.*limit",
        r"cpu.*limit",
    ],
    ErrorType.SERVICE_UNAVAILABLE: [
        r"service.*unavailable",
        r"503",
        r"server.*overloaded",
        r"maintenance",
        r"temporarily.*unavailable",
        r"try.*again.*later",
    ],
    ErrorType.INTERNAL: [
        r"internal.*error",
        r"500",
        r"server.*error",
        r"fatal.*error",
        r"critical.*error",
    ],
}

# Severity mapping for error types
ERROR_SEVERITY: Dict[ErrorType, ErrorSeverity] = {
    ErrorType.NETWORK: ErrorSeverity.WARNING,
    ErrorType.VALIDATION: ErrorSeverity.WARNING,
    ErrorType.TIMEOUT: ErrorSeverity.WARNING,
    ErrorType.PARSE: ErrorSeverity.WARNING,
    ErrorType.ASSET: ErrorSeverity.WARNING,
    ErrorType.LOGIC: ErrorSeverity.BLOCKING,
    ErrorType.PACKAGE: ErrorSeverity.WARNING,
    ErrorType.RATE_LIMIT: ErrorSeverity.WARNING,
    ErrorType.AUTHENTICATION: ErrorSeverity.BLOCKING,
    ErrorType.AUTHORIZATION: ErrorSeverity.BLOCKING,
    ErrorType.NOT_FOUND: ErrorSeverity.INFO,
    ErrorType.CONFLICT: ErrorSeverity.WARNING,
    ErrorType.QUOTA_EXCEEDED: ErrorSeverity.BLOCKING,
    ErrorType.SERVICE_UNAVAILABLE: ErrorSeverity.WARNING,
    ErrorType.INTERNAL: ErrorSeverity.BLOCKING,
    ErrorType.UNKNOWN: ErrorSeverity.WARNING,
}

# Error type to user-friendly message mapping
ERROR_USER_MESSAGES: Dict[ErrorType, str] = {
    ErrorType.NETWORK: "Network error. Please check your connection and try again.",
    ErrorType.VALIDATION: "Invalid input provided. Please check your data and try again.",
    ErrorType.TIMEOUT: "The operation took too long. Please try again.",
    ErrorType.PARSE: "Failed to parse the file. Please check the file format.",
    ErrorType.ASSET: "Error processing mod assets. Some assets may be missing.",
    ErrorType.LOGIC: "An internal conversion error occurred. Please try again.",
    ErrorType.PACKAGE: "Error packaging the converted mod. Please try again.",
    ErrorType.RATE_LIMIT: "Too many requests. Please wait and try again.",
    ErrorType.AUTHENTICATION: "Authentication failed. Please log in again.",
    ErrorType.AUTHORIZATION: "You don't have permission to perform this action.",
    ErrorType.NOT_FOUND: "The requested resource was not found.",
    ErrorType.CONFLICT: "A conflict occurred. Please resolve and try again.",
    ErrorType.QUOTA_EXCEEDED: "Resource limit exceeded. Please upgrade or wait.",
    ErrorType.SERVICE_UNAVAILABLE: "Service temporarily unavailable. Please try again later.",
    ErrorType.INTERNAL: "An internal error occurred. Please try again later.",
    ErrorType.UNKNOWN: "An unexpected error occurred. Please try again.",
}


class ErrorClassification:
    """Result of error classification with type and severity."""

    def __init__(
        self,
        error_type: ErrorType,
        severity: ErrorSeverity,
        confidence: float,
        matched_pattern: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.error_type = error_type
        self.severity = severity
        self.confidence = confidence
        self.matched_pattern = matched_pattern
        self.details = details or {}

    def __repr__(self) -> str:
        return (
            f"ErrorClassification(type={self.error_type.value}, "
            f"severity={self.severity.value}, confidence={self.confidence:.2f})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "matched_pattern": self.matched_pattern,
            "details": self.details,
        }


class ErrorClassifier:
    """
    Classifies errors by type and determines severity.

    Uses pattern matching to identify error types and maps them to
    appropriate severity levels for recovery decision making.
    """

    def __init__(self):
        """Initialize the classifier with compiled patterns."""
        self._compiled_patterns: Dict[ErrorType, List[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for faster matching."""
        for error_type, patterns in ERROR_PATTERNS.items():
            self._compiled_patterns[error_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def _match_patterns(self, text: str) -> List[Tuple[ErrorType, str, float]]:
        """
        Match text against all error patterns.

        Returns list of (error_type, matched_pattern, confidence) tuples.
        Confidence is based on pattern specificity.
        """
        matches = []
        text_lower = text.lower()

        for error_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text_lower):
                    # Higher confidence for exact matches vs partial
                    confidence = 0.9 if pattern.search(text_lower) else 0.7
                    matches.append((error_type, pattern.pattern, confidence))

        return matches

    def classify(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> ErrorClassification:
        """
        Classify an exception into an error type and severity.

        Args:
            error: The exception to classify
            context: Optional context information (job_id, operation, etc.)

        Returns:
            ErrorClassification with type, severity, and confidence
        """
        context = context or {}
        error_type = type(error).__name__
        error_message = str(error)
        full_text = f"{error_type} {error_message}"

        # Check exception type directly first (highest confidence)
        direct_match = self._check_direct_type(error)
        if direct_match:
            return direct_match

        # Fall back to pattern matching
        pattern_matches = self._match_patterns(full_text)

        if pattern_matches:
            # Use the highest confidence match
            best_match = max(pattern_matches, key=lambda x: x[2])
            error_type_enum, matched_pattern, confidence = best_match
            severity = ERROR_SEVERITY[error_type_enum]

            return ErrorClassification(
                error_type=error_type_enum,
                severity=severity,
                confidence=confidence,
                matched_pattern=matched_pattern,
                details={
                    "exception_type": error_type,
                    "exception_message": error_message,
                    "context": context,
                },
            )

        # No match found - classify as unknown
        logger.warning(f"Unclassified error: {error_type}: {error_message}")
        return ErrorClassification(
            error_type=ErrorType.UNKNOWN,
            severity=ErrorSeverity.WARNING,
            confidence=0.5,
            details={
                "exception_type": error_type,
                "exception_message": error_message,
                "context": context,
            },
        )

    def _check_direct_type(self, error: Exception) -> Optional[ErrorClassification]:
        """Check if error is a direct instance of known error types."""
        # Check retry module
        try:
            from services.retry import (
                RetryableError,
                NonRetryableError,
                NetworkError as RetryNetworkError,
                RateLimitError,
                TimeoutError as RetryTimeoutError,
                ParseError as RetryParseError,
                AssetError as RetryAssetError,
                LogicError as RetryLogicError,
                ValidationError as RetryValidationError,
                PackageError as RetryPackageError,
            )

            type_mapping = {
                RetryNetworkError: ErrorType.NETWORK,
                RetryTimeoutError: ErrorType.TIMEOUT,
                RetryParseError: ErrorType.PARSE,
                RetryAssetError: ErrorType.ASSET,
                RetryLogicError: ErrorType.LOGIC,
                RetryValidationError: ErrorType.VALIDATION,
                RetryPackageError: ErrorType.PACKAGE,
                RateLimitError: ErrorType.RATE_LIMIT,
            }

            for retry_type, error_type_enum in type_mapping.items():
                if isinstance(error, retry_type):
                    return ErrorClassification(
                        error_type=error_type_enum,
                        severity=ERROR_SEVERITY[error_type_enum],
                        confidence=1.0,
                        matched_pattern=f"direct_type:{retry_type.__name__}",
                        details={"direct_match": True},
                    )

            if isinstance(error, RetryableError):
                return ErrorClassification(
                    error_type=ErrorType.UNKNOWN,
                    severity=ErrorSeverity.WARNING,
                    confidence=0.8,
                    matched_pattern="RetryableError",
                )
            if isinstance(error, NonRetryableError):
                return ErrorClassification(
                    error_type=ErrorType.UNKNOWN,
                    severity=ErrorSeverity.BLOCKING,
                    confidence=0.8,
                    matched_pattern="NonRetryableError",
                )

        except ImportError:
            pass

        # Check handler module
        try:
            from errors.handler import ModPorterException, RateLimitException

            if isinstance(error, RateLimitException):
                return ErrorClassification(
                    error_type=ErrorType.RATE_LIMIT,
                    severity=ERROR_SEVERITY[ErrorType.RATE_LIMIT],
                    confidence=1.0,
                    matched_pattern="RateLimitException",
                )

            if isinstance(error, ModPorterException):
                error_type_field = getattr(error, "error_type", None)
                if error_type_field:
                    type_mapping = {
                        "network_error": ErrorType.NETWORK,
                        "validation_error": ErrorType.VALIDATION,
                        "timeout_error": ErrorType.TIMEOUT,
                        "parse_error": ErrorType.PARSE,
                        "asset_error": ErrorType.ASSET,
                        "logic_error": ErrorType.LOGIC,
                        "package_error": ErrorType.PACKAGE,
                        "rate_limit_error": ErrorType.RATE_LIMIT,
                        "not_found_error": ErrorType.NOT_FOUND,
                        "conversion_error": ErrorType.LOGIC,
                    }
                    if error_type_field in type_mapping:
                        mapped_type = type_mapping[error_type_field]
                        return ErrorClassification(
                            error_type=mapped_type,
                            severity=ERROR_SEVERITY[mapped_type],
                            confidence=1.0,
                            matched_pattern=f"ModPorterException:{error_type_field}",
                        )

        except ImportError:
            pass

        # Check HTTP exceptions
        try:
            from fastapi import HTTPException

            if isinstance(error, HTTPException):
                status_code = error.status_code
                if status_code == 404:
                    return ErrorClassification(
                        error_type=ErrorType.NOT_FOUND,
                        severity=ErrorSeverity.INFO,
                        confidence=1.0,
                        matched_pattern=f"HTTPException:{status_code}",
                    )
                elif status_code == 403:
                    return ErrorClassification(
                        error_type=ErrorType.AUTHORIZATION,
                        severity=ErrorSeverity.BLOCKING,
                        confidence=1.0,
                        matched_pattern=f"HTTPException:{status_code}",
                    )
                elif status_code == 401:
                    return ErrorClassification(
                        error_type=ErrorType.AUTHENTICATION,
                        severity=ErrorSeverity.BLOCKING,
                        confidence=1.0,
                        matched_pattern=f"HTTPException:{status_code}",
                    )
                elif status_code == 429:
                    return ErrorClassification(
                        error_type=ErrorType.RATE_LIMIT,
                        severity=ErrorSeverity.WARNING,
                        confidence=1.0,
                        matched_pattern=f"HTTPException:{status_code}",
                    )
                elif status_code >= 500:
                    return ErrorClassification(
                        error_type=ErrorType.SERVICE_UNAVAILABLE,
                        severity=ErrorSeverity.WARNING,
                        confidence=0.9,
                        matched_pattern=f"HTTPException:{status_code}",
                    )

        except ImportError:
            pass

        return None

    def get_recovery_priority(self, classification: ErrorClassification) -> int:
        """
        Get recovery priority for an error classification.

        Lower numbers = higher priority for recovery attempts.
        Returns 0-100 where 0 is highest priority.
        """
        priority_map = {
            ErrorType.NETWORK: 10,
            ErrorType.TIMEOUT: 20,
            ErrorType.RATE_LIMIT: 30,
            ErrorType.PARSE: 40,
            ErrorType.ASSET: 50,
            ErrorType.PACKAGE: 60,
            ErrorType.VALIDATION: 70,
            ErrorType.SERVICE_UNAVAILABLE: 80,
            ErrorType.NOT_FOUND: 90,
            ErrorType.CONFLICT: 85,
            ErrorType.LOGIC: 95,
            ErrorType.AUTHENTICATION: 100,
            ErrorType.AUTHORIZATION: 100,
            ErrorType.QUOTA_EXCEEDED: 100,
            ErrorType.INTERNAL: 100,
            ErrorType.UNKNOWN: 100,
        }
        return priority_map.get(classification.error_type, 100)


# Global classifier instance
_classifier: Optional[ErrorClassifier] = None


def get_classifier() -> ErrorClassifier:
    """Get or create the global classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = ErrorClassifier()
    return _classifier


def classify_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> ErrorClassification:
    """
    Convenience function to classify an error using the global classifier.

    Args:
        error: The exception to classify
        context: Optional context information

    Returns:
        ErrorClassification result
    """
    return get_classifier().classify(error, context)
