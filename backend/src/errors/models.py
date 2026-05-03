"""
Error Patterns Library for Portkit Backend

Provides a known error pattern library with recovery strategies and
pattern-to-solution mappings for the Enhanced Auto-Recovery system.

GAP-2.5-04: Enhanced Auto-Recovery
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from .classifier import ErrorSeverity, ErrorType

logger = logging.getLogger(__name__)


class RecoveryStrategy(str, Enum):
    """Enumeration of recovery strategy types."""

    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    FALLBACK_SERVICE = "fallback_service"
    FALLBACK_METHOD = "fallback_method"
    DEGRADED_MODE = "degraded_mode"
    SKIP_AND_CONTINUE = "skip_and_continue"
    USE_CACHE = "use_cache"
    USE_DEFAULT = "use_default"
    NOTIFY_USER = "notify_user"
    ESCALATE = "escalate"
    NO_RECOVERY = "no_recovery"


@dataclass
class RecoveryAction:
    """A single recovery action to attempt."""

    name: str
    strategy: RecoveryStrategy
    description: str
    action: Optional[Callable] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    success_rate: float = 0.5
    estimated_duration: float = 0.0


@dataclass
class ErrorPattern:
    """A known error pattern with its recovery strategy."""

    error_type: ErrorType
    pattern_description: str
    recovery_actions: List[RecoveryAction]
    max_recovery_attempts: int = 3
    fallback_mode: Optional[str] = None
    escalation_required: bool = False
    tags: List[str] = field(default_factory=list)

    def get_primary_recovery(self) -> Optional[RecoveryAction]:
        """Get the primary recovery action (highest success rate)."""
        if not self.recovery_actions:
            return None
        return max(self.recovery_actions, key=lambda a: a.success_rate)


class ErrorPatternLibrary:
    """
    Library of known error patterns and their recovery strategies.

    This class maintains a collection of error patterns with associated
    recovery actions that can be looked up by error type.
    """

    def __init__(self):
        """Initialize the pattern library with built-in patterns."""
        self._patterns: Dict[ErrorType, ErrorPattern] = {}
        self._build_builtin_patterns()

    def _build_builtin_patterns(self) -> None:
        """Build the built-in error patterns and recovery strategies."""

        # Network errors
        self._patterns[ErrorType.NETWORK] = ErrorPattern(
            error_type=ErrorType.NETWORK,
            pattern_description="Network connectivity issues",
            recovery_actions=[
                RecoveryAction(
                    name="retry_immediate",
                    strategy=RecoveryStrategy.RETRY,
                    description="Retry the operation immediately",
                    success_rate=0.3,
                    estimated_duration=1.0,
                ),
                RecoveryAction(
                    name="retry_with_backoff",
                    strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                    description="Retry with exponential backoff",
                    success_rate=0.6,
                    estimated_duration=10.0,
                ),
                RecoveryAction(
                    name="fallback_service",
                    strategy=RecoveryStrategy.FALLBACK_SERVICE,
                    description="Use alternative service endpoint",
                    success_rate=0.8,
                    estimated_duration=5.0,
                ),
                RecoveryAction(
                    name="degraded_mode",
                    strategy=RecoveryStrategy.DEGRADED_MODE,
                    description="Continue with reduced functionality",
                    success_rate=0.9,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=3,
            fallback_mode="degraded",
            escalation_required=False,
            tags=["network", "connectivity", "ai-engine"],
        )

        # Timeout errors
        self._patterns[ErrorType.TIMEOUT] = ErrorPattern(
            error_type=ErrorType.TIMEOUT,
            pattern_description="Operation timed out",
            recovery_actions=[
                RecoveryAction(
                    name="retry_with_extended_timeout",
                    strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                    description="Retry with longer timeout",
                    success_rate=0.5,
                    estimated_duration=15.0,
                ),
                RecoveryAction(
                    name="fallback_method",
                    strategy=RecoveryStrategy.FALLBACK_METHOD,
                    description="Use alternative method",
                    success_rate=0.7,
                    estimated_duration=10.0,
                ),
                RecoveryAction(
                    name="degraded_mode",
                    strategy=RecoveryStrategy.DEGRADED_MODE,
                    description="Continue with timeout disabled",
                    success_rate=0.85,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=2,
            fallback_mode="no-timeout",
            escalation_required=False,
            tags=["timeout", "performance", "ai-engine"],
        )

        # Rate limit errors
        self._patterns[ErrorType.RATE_LIMIT] = ErrorPattern(
            error_type=ErrorType.RATE_LIMIT,
            pattern_description="Rate limit exceeded",
            recovery_actions=[
                RecoveryAction(
                    name="wait_and_retry",
                    strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                    description="Wait for rate limit window and retry",
                    success_rate=0.8,
                    estimated_duration=60.0,
                ),
                RecoveryAction(
                    name="use_cache",
                    strategy=RecoveryStrategy.USE_CACHE,
                    description="Use cached results if available",
                    success_rate=0.9,
                    estimated_duration=0.0,
                ),
                RecoveryAction(
                    name="degraded_mode",
                    strategy=RecoveryStrategy.DEGRADED_MODE,
                    description="Continue with reduced request rate",
                    success_rate=0.95,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=2,
            fallback_mode="cached",
            escalation_required=False,
            tags=["rate-limit", "throttle", "api"],
        )

        # Validation errors
        self._patterns[ErrorType.VALIDATION] = ErrorPattern(
            error_type=ErrorType.VALIDATION,
            pattern_description="Input validation failed",
            recovery_actions=[
                RecoveryAction(
                    name="sanitize_and_retry",
                    strategy=RecoveryStrategy.RETRY,
                    description="Sanitize input and retry",
                    success_rate=0.4,
                    estimated_duration=1.0,
                ),
                RecoveryAction(
                    name="use_default",
                    strategy=RecoveryStrategy.USE_DEFAULT,
                    description="Use default values for invalid fields",
                    success_rate=0.7,
                    estimated_duration=0.0,
                ),
                RecoveryAction(
                    name="notify_user",
                    strategy=RecoveryStrategy.NOTIFY_USER,
                    description="Notify user of validation issues",
                    success_rate=1.0,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=1,
            fallback_mode="defaults",
            escalation_required=False,
            tags=["validation", "input", "user-error"],
        )

        # Parse errors
        self._patterns[ErrorType.PARSE] = ErrorPattern(
            error_type=ErrorType.PARSE,
            pattern_description="Failed to parse input",
            recovery_actions=[
                RecoveryAction(
                    name="retry_with_alternative_parser",
                    strategy=RecoveryStrategy.FALLBACK_METHOD,
                    description="Try alternative parsing method",
                    success_rate=0.3,
                    estimated_duration=5.0,
                ),
                RecoveryAction(
                    name="skip_invalid",
                    strategy=RecoveryStrategy.SKIP_AND_CONTINUE,
                    description="Skip invalid parts and continue",
                    success_rate=0.5,
                    estimated_duration=2.0,
                ),
                RecoveryAction(
                    name="degraded_mode",
                    strategy=RecoveryStrategy.DEGRADED_MODE,
                    description="Continue with partial parsing",
                    success_rate=0.6,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=2,
            fallback_mode="partial",
            escalation_required=False,
            tags=["parse", "format", "file"],
        )

        # Asset errors
        self._patterns[ErrorType.ASSET] = ErrorPattern(
            error_type=ErrorType.ASSET,
            pattern_description="Asset processing error",
            recovery_actions=[
                RecoveryAction(
                    name="use_placeholder",
                    strategy=RecoveryStrategy.USE_DEFAULT,
                    description="Use placeholder for missing asset",
                    success_rate=0.7,
                    estimated_duration=0.0,
                ),
                RecoveryAction(
                    name="retry_asset_load",
                    strategy=RecoveryStrategy.RETRY,
                    description="Retry loading the asset",
                    success_rate=0.4,
                    estimated_duration=3.0,
                ),
                RecoveryAction(
                    name="skip_asset",
                    strategy=RecoveryStrategy.SKIP_AND_CONTINUE,
                    description="Skip missing asset and continue",
                    success_rate=0.8,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=2,
            fallback_mode="skip-missing",
            escalation_required=False,
            tags=["asset", "texture", "model", "resource"],
        )

        # Package errors
        self._patterns[ErrorType.PACKAGE] = ErrorPattern(
            error_type=ErrorType.PACKAGE,
            pattern_description="Mod packaging error",
            recovery_actions=[
                RecoveryAction(
                    name="retry_package",
                    strategy=RecoveryStrategy.RETRY,
                    description="Retry packaging operation",
                    success_rate=0.5,
                    estimated_duration=10.0,
                ),
                RecoveryAction(
                    name="use_cache",
                    strategy=RecoveryStrategy.USE_CACHE,
                    description="Use cached package if available",
                    success_rate=0.7,
                    estimated_duration=1.0,
                ),
                RecoveryAction(
                    name="partial_package",
                    strategy=RecoveryStrategy.DEGRADED_MODE,
                    description="Create partial package",
                    success_rate=0.6,
                    estimated_duration=15.0,
                ),
            ],
            max_recovery_attempts=2,
            fallback_mode="partial",
            escalation_required=True,
            tags=["package", "zip", "archive"],
        )

        # Logic errors
        self._patterns[ErrorType.LOGIC] = ErrorPattern(
            error_type=ErrorType.LOGIC,
            pattern_description="Internal logic error",
            recovery_actions=[
                RecoveryAction(
                    name="retry_logic",
                    strategy=RecoveryStrategy.RETRY,
                    description="Retry the operation",
                    success_rate=0.2,
                    estimated_duration=5.0,
                ),
                RecoveryAction(
                    name="escalate",
                    strategy=RecoveryStrategy.ESCALATE,
                    description="Escalate to human review",
                    success_rate=1.0,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=1,
            fallback_mode=None,
            escalation_required=True,
            tags=["logic", "internal", "critical"],
        )

        # Authentication errors
        self._patterns[ErrorType.AUTHENTICATION] = ErrorPattern(
            error_type=ErrorType.AUTHENTICATION,
            pattern_description="Authentication failed",
            recovery_actions=[
                RecoveryAction(
                    name="retry_auth",
                    strategy=RecoveryStrategy.RETRY,
                    description="Retry authentication",
                    success_rate=0.3,
                    estimated_duration=2.0,
                ),
                RecoveryAction(
                    name="refresh_token",
                    strategy=RecoveryStrategy.FALLBACK_METHOD,
                    description="Refresh authentication token",
                    success_rate=0.6,
                    estimated_duration=3.0,
                ),
                RecoveryAction(
                    name="notify_user",
                    strategy=RecoveryStrategy.NOTIFY_USER,
                    description="Request user re-authentication",
                    success_rate=1.0,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=2,
            fallback_mode=None,
            escalation_required=True,
            tags=["auth", "security", "user"],
        )

        # Authorization errors
        self._patterns[ErrorType.AUTHORIZATION] = ErrorPattern(
            error_type=ErrorType.AUTHORIZATION,
            pattern_description="Authorization failed",
            recovery_actions=[
                RecoveryAction(
                    name="notify_user",
                    strategy=RecoveryStrategy.NOTIFY_USER,
                    description="Notify user of permission issue",
                    success_rate=1.0,
                    estimated_duration=0.0,
                ),
                RecoveryAction(
                    name="escalate",
                    strategy=RecoveryStrategy.ESCALATE,
                    description="Escalate for access review",
                    success_rate=1.0,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=1,
            fallback_mode=None,
            escalation_required=True,
            tags=["auth", "permission", "security"],
        )

        # Not found errors
        self._patterns[ErrorType.NOT_FOUND] = ErrorPattern(
            error_type=ErrorType.NOT_FOUND,
            pattern_description="Resource not found",
            recovery_actions=[
                RecoveryAction(
                    name="notify_user",
                    strategy=RecoveryStrategy.NOTIFY_USER,
                    description="Notify user resource not found",
                    success_rate=1.0,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=0,
            fallback_mode=None,
            escalation_required=False,
            tags=["404", "missing", "user"],
        )

        # Service unavailable
        self._patterns[ErrorType.SERVICE_UNAVAILABLE] = ErrorPattern(
            error_type=ErrorType.SERVICE_UNAVAILABLE,
            pattern_description="Service temporarily unavailable",
            recovery_actions=[
                RecoveryAction(
                    name="retry_with_backoff",
                    strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                    description="Retry with exponential backoff",
                    success_rate=0.5,
                    estimated_duration=60.0,
                ),
                RecoveryAction(
                    name="fallback_service",
                    strategy=RecoveryStrategy.FALLBACK_SERVICE,
                    description="Use alternative service",
                    success_rate=0.7,
                    estimated_duration=5.0,
                ),
                RecoveryAction(
                    name="degraded_mode",
                    strategy=RecoveryStrategy.DEGRADED_MODE,
                    description="Continue in degraded mode",
                    success_rate=0.8,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=3,
            fallback_mode="degraded",
            escalation_required=False,
            tags=["503", "maintenance", "overload"],
        )

        # Unknown errors
        self._patterns[ErrorType.UNKNOWN] = ErrorPattern(
            error_type=ErrorType.UNKNOWN,
            pattern_description="Unknown error",
            recovery_actions=[
                RecoveryAction(
                    name="retry",
                    strategy=RecoveryStrategy.RETRY,
                    description="Retry the operation",
                    success_rate=0.3,
                    estimated_duration=5.0,
                ),
                RecoveryAction(
                    name="escalate",
                    strategy=RecoveryStrategy.ESCALATE,
                    description="Escalate to human review",
                    success_rate=1.0,
                    estimated_duration=0.0,
                ),
            ],
            max_recovery_attempts=1,
            fallback_mode=None,
            escalation_required=True,
            tags=["unknown", "critical"],
        )

    def get_pattern(self, error_type: ErrorType) -> Optional[ErrorPattern]:
        """Get the error pattern for a given error type."""
        return self._patterns.get(error_type)

    def get_recovery_actions(
        self,
        error_type: ErrorType,
        max_actions: Optional[int] = None,
    ) -> List[RecoveryAction]:
        """
        Get recovery actions for an error type, sorted by success rate.

        Args:
            error_type: The type of error
            max_actions: Maximum number of actions to return

        Returns:
            List of RecoveryAction objects, sorted by success rate
        """
        pattern = self._patterns.get(error_type)
        if not pattern:
            return []

        actions = sorted(
            pattern.recovery_actions,
            key=lambda a: a.success_rate,
            reverse=True,
        )

        if max_actions:
            actions = actions[:max_actions]

        return actions

    def should_escalate(self, error_type: ErrorType) -> bool:
        """Check if errors of this type should be escalated to human review."""
        pattern = self._patterns.get(error_type)
        if not pattern:
            return True  # Default to escalate for unknown patterns
        return pattern.escalation_required

    def get_fallback_mode(self, error_type: ErrorType) -> Optional[str]:
        """Get the fallback mode for an error type."""
        pattern = self._patterns.get(error_type)
        if not pattern:
            return None
        return pattern.fallback_mode

    def register_pattern(self, pattern: ErrorPattern) -> None:
        """Register a new error pattern."""
        self._patterns[pattern.error_type] = pattern
        logger.info(f"Registered error pattern for {pattern.error_type.value}")

    def unregister_pattern(self, error_type: ErrorType) -> bool:
        """Unregister an error pattern. Returns True if it existed."""
        if error_type in self._patterns:
            del self._patterns[error_type]
            logger.info(f"Unregistered error pattern for {error_type.value}")
            return True
        return False

    def get_patterns_by_tag(self, tag: str) -> List[ErrorPattern]:
        """Get all patterns that have a specific tag."""
        return [pattern for pattern in self._patterns.values() if tag in pattern.tags]

    def get_all_patterns(self) -> Dict[ErrorType, ErrorPattern]:
        """Get all registered patterns."""
        return dict(self._patterns)


# Global pattern library instance
_library: Optional[ErrorPatternLibrary] = None


def get_pattern_library() -> ErrorPatternLibrary:
    """Get or create the global pattern library instance."""
    global _library
    if _library is None:
        _library = ErrorPatternLibrary()
    return _library


def get_recovery_actions(
    error_type: ErrorType,
    max_actions: Optional[int] = None,
) -> List[RecoveryAction]:
    """Convenience function to get recovery actions from global library."""
    return get_pattern_library().get_recovery_actions(error_type, max_actions)


def should_escalate(error_type: ErrorType) -> bool:
    """Convenience function to check if error type should escalate."""
    return get_pattern_library().should_escalate(error_type)


def get_fallback_mode(error_type: ErrorType) -> Optional[str]:
    """Convenience function to get fallback mode for error type."""
    return get_pattern_library().get_fallback_mode(error_type)
