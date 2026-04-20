"""
Error Recovery - backward compatibility re-export.

This module now imports from errors.recovery.
"""

from errors.recovery import (
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
    ErrorClassification,
    ErrorClassifier,
    ErrorSeverity,
    ErrorType,
    classify_error,
    get_classifier,
    ErrorPatternLibrary,
    RecoveryAction,
    RecoveryStrategy,
    get_pattern_library,
)

__all__ = [
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
    "ErrorClassification",
    "ErrorClassifier",
    "ErrorSeverity",
    "ErrorType",
    "classify_error",
    "get_classifier",
    "ErrorPatternLibrary",
    "RecoveryAction",
    "RecoveryStrategy",
    "get_pattern_library",
]
