"""
Error Patterns - backward compatibility re-export.

This module now imports from errors.models.
"""

from errors.models import (
    RecoveryStrategy,
    RecoveryAction,
    ErrorPattern,
    ErrorPatternLibrary,
    get_pattern_library,
    get_recovery_actions,
    should_escalate,
    get_fallback_mode,
)

__all__ = [
    "RecoveryStrategy",
    "RecoveryAction",
    "ErrorPattern",
    "ErrorPatternLibrary",
    "get_pattern_library",
    "get_recovery_actions",
    "should_escalate",
    "get_fallback_mode",
]
