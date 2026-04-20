"""
Error Classifier - backward compatibility re-export.

This module now imports from errors.classifier.
"""

from errors.classifier import (
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

__all__ = [
    "ErrorType",
    "ErrorSeverity",
    "ErrorClassification",
    "ErrorClassifier",
    "get_classifier",
    "classify_error",
    "ERROR_PATTERNS",
    "ERROR_SEVERITY",
    "ERROR_USER_MESSAGES",
]
