"""
Error Recovery System for ModPorter AI Backend

Implements the Supervisor + Fallback pattern for automatic error recovery
with intelligent fallback and escalation mechanisms.

GAP-2.5-04: Enhanced Auto-Recovery

Error Handling Pipeline:
1. Error occurs → Supervisor catches
2. Classify error type (ErrorClassifier)
3. Check error pattern library (ErrorPatterns)
4. Attempt recovery strategy (ErrorRecovery)
5. Fallback to degraded mode if recovery fails
6. Escalate to human if all recovery attempts fail
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

from .error_classifier import (
    ErrorClassification,
    ErrorClassifier,
    ErrorSeverity,
    ErrorType,
    classify_error,
    get_classifier,
)
from .error_patterns import (
    ErrorPatternLibrary,
    RecoveryAction,
    RecoveryStrategy,
    get_pattern_library,
)

logger = logging.getLogger(__name__)


class RecoveryStatus(str, Enum):
    """Status of a recovery attempt."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEGRADED = "degraded"
    ESCALATED = "escalated"


@dataclass
class RecoveryAttempt:
    """Record of a single recovery attempt."""

    action_name: str
    strategy: RecoveryStrategy
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: RecoveryStatus = RecoveryStatus.PENDING
    result: Optional[Any] = None
    error: Optional[Exception] = None
    retry_count: int = 0

    @property
    def duration(self) -> float:
        """Get duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


@dataclass
class RecoveryResult:
    """Result of the error recovery process."""

    status: RecoveryStatus
    original_error: Exception
    classification: ErrorClassification
    attempts: List[RecoveryAttempt] = field(default_factory=list)
    final_result: Optional[Any] = None
    fallback_mode: Optional[str] = None
    escalated: bool = False
    escalated_at: Optional[datetime] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    message: str = ""

    @property
    def total_duration(self) -> float:
        """Get total recovery duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def succeeded(self) -> bool:
        """Check if recovery succeeded."""
        return self.status == RecoveryStatus.SUCCEEDED

    @property
    def recovered_with_degraded(self) -> bool:
        """Check if recovered with degraded functionality."""
        return self.status == RecoveryStatus.DEGRADED


class DegradedModeManager:
    """Manages degraded mode states and fallback behaviors."""

    def __init__(self):
        self._degraded_states: Dict[str, bool] = {}
        self._fallback_handlers: Dict[str, Callable] = {}

    def enable_degraded_mode(
        self,
        feature: str,
        reason: str,
        fallback_handler: Optional[Callable] = None,
    ) -> None:
        """Enable degraded mode for a feature."""
        self._degraded_states[feature] = True
        if fallback_handler:
            self._fallback_handlers[feature] = fallback_handler
        logger.warning(f"Degraded mode enabled for {feature}: {reason}")

    def disable_degraded_mode(self, feature: str) -> None:
        """Disable degraded mode for a feature."""
        if feature in self._degraded_states:
            del self._degraded_states[feature]
        if feature in self._fallback_handlers:
            del self._fallback_handlers[feature]
        logger.info(f"Degraded mode disabled for {feature}")

    def is_degraded(self, feature: str) -> bool:
        """Check if a feature is in degraded mode."""
        return self._degraded_states.get(feature, False)

    def get_fallback_handler(self, feature: str) -> Optional[Callable]:
        """Get the fallback handler for a degraded feature."""
        return self._fallback_handlers.get(feature)

    def get_all_degraded_features(self) -> List[str]:
        """Get list of all features in degraded mode."""
        return list(self._degraded_states.keys())


class EscalationManager:
    """Manages error escalation to human review."""

    def __init__(self):
        self._escalation_queue: List[Dict[str, Any]] = []
        self._escalation_handlers: List[Callable] = []

    def register_handler(self, handler: Callable) -> None:
        """Register an escalation handler callback."""
        self._escalation_handlers.append(handler)

    def escalate(
        self,
        error: Exception,
        classification: ErrorClassification,
        recovery_result: RecoveryResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Escalate an error to human review.

        Returns an escalation ID for tracking.
        """
        escalation_id = f"ESC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        escalation_entry = {
            "escalation_id": escalation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(error),
            "error_type": classification.error_type.value,
            "severity": classification.severity.value,
            "recovery_attempts": len(recovery_result.attempts),
            "recovery_duration": recovery_result.total_duration,
            "context": context or {},
        }

        self._escalation_queue.append(escalation_entry)
        logger.error(f"Escalated error {escalation_id}: {classification.error_type.value}")

        # Call registered handlers
        for handler in self._escalation_handlers:
            try:
                handler(escalation_entry)
            except Exception as e:
                logger.error(f"Escalation handler failed: {e}")

        return escalation_id

    def get_pending_escalations(self) -> List[Dict[str, Any]]:
        """Get list of pending escalations."""
        return list(self._escalation_queue)


class RecoveryStrategyExecutor:
    """Executes recovery strategies for errors."""

    def __init__(self, degraded_mode_manager: DegradedModeManager):
        self._degraded_mode = degraded_mode_manager
        self._strategy_handlers: Dict[RecoveryStrategy, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default strategy handlers."""
        self._strategy_handlers[RecoveryStrategy.RETRY] = self._handle_retry
        self._strategy_handlers[RecoveryStrategy.RETRY_WITH_BACKOFF] = (
            self._handle_retry_with_backoff
        )
        self._strategy_handlers[RecoveryStrategy.FALLBACK_SERVICE] = self._handle_fallback_service
        self._strategy_handlers[RecoveryStrategy.FALLBACK_METHOD] = self._handle_fallback_method
        self._strategy_handlers[RecoveryStrategy.DEGRADED_MODE] = self._handle_degraded_mode
        self._strategy_handlers[RecoveryStrategy.SKIP_AND_CONTINUE] = self._handle_skip_and_continue
        self._strategy_handlers[RecoveryStrategy.USE_CACHE] = self._handle_use_cache
        self._strategy_handlers[RecoveryStrategy.USE_DEFAULT] = self._handle_use_default
        self._strategy_handlers[RecoveryStrategy.NOTIFY_USER] = self._handle_notify_user
        self._strategy_handlers[RecoveryStrategy.ESCALATE] = self._handle_escalate
        self._strategy_handlers[RecoveryStrategy.NO_RECOVERY] = self._handle_no_recovery

    def register_handler(self, strategy: RecoveryStrategy, handler: Callable) -> None:
        """Register a custom strategy handler."""
        self._strategy_handlers[strategy] = handler

    async def execute(
        self,
        action: RecoveryAction,
        original_error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]] = None,
    ) -> RecoveryAttempt:
        """
        Execute a recovery action.

        Returns a RecoveryAttempt with the result.
        """
        attempt = RecoveryAttempt(
            action_name=action.name,
            strategy=action.strategy,
            started_at=datetime.now(timezone.utc),
        )

        try:
            handler = self._strategy_handlers.get(action.strategy)
            if not handler:
                raise ValueError(f"No handler for strategy {action.strategy}")

            # Execute the handler
            result = await self._execute_handler(
                handler, action, original_error, context, retry_config
            )

            attempt.status = RecoveryStatus.SUCCEEDED
            attempt.completed_at = datetime.now(timezone.utc)
            attempt.result = result

        except Exception as e:
            attempt.status = RecoveryStatus.FAILED
            attempt.completed_at = datetime.now(timezone.utc)
            attempt.error = e
            logger.warning(f"Recovery action {action.name} failed: {e}")

        return attempt

    async def _execute_handler(
        self,
        handler: Callable,
        action: RecoveryAction,
        original_error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Execute a strategy handler with the given parameters."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(action, original_error, context, retry_config)
        else:
            return handler(action, original_error, context, retry_config)

    async def _handle_retry(
        self,
        action: RecoveryAction,
        error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Handle retry strategy - immediately retry the operation."""
        retry_count = context.get("_retry_count", 0) + 1
        context["_retry_count"] = retry_count

        operation = context.get("operation")
        if not operation:
            raise ValueError("No operation provided for retry")

        # Check if we should proceed with retry
        max_retries = retry_config.get("max_attempts", 3) if retry_config else 3
        if retry_count >= max_retries:
            raise Exception(f"Max retries ({max_retries}) exceeded")

        # Execute the operation
        if asyncio.iscoroutinefunction(operation):
            return await operation()
        else:
            return operation()

    async def _handle_retry_with_backoff(
        self,
        action: RecoveryAction,
        error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Handle retry with exponential backoff."""
        import random

        retry_count = context.get("_retry_count", 0) + 1
        context["_retry_count"] = retry_count

        base_delay = retry_config.get("base_delay", 1.0) if retry_config else 1.0
        max_delay = retry_config.get("max_delay", 60.0) if retry_config else 60.0
        exponential_base = retry_config.get("exponential_base", 2.0) if retry_config else 2.0

        delay = min(base_delay * (exponential_base ** (retry_count - 1)), max_delay)
        # Add jitter
        delay = delay * (0.5 + random.random() * 0.5)

        max_retries = retry_config.get("max_attempts", 3) if retry_config else 3
        if retry_count >= max_retries:
            raise Exception(f"Max retries ({max_retries}) exceeded")

        logger.info(f"Retry with backoff: waiting {delay:.2f}s before retry {retry_count}")
        await asyncio.sleep(delay)

        operation = context.get("operation")
        if not operation:
            raise ValueError("No operation provided for retry")

        if asyncio.iscoroutinefunction(operation):
            return await operation()
        else:
            return operation()

    async def _handle_fallback_service(
        self,
        action: RecoveryAction,
        error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Handle fallback service strategy."""
        fallback_service = context.get("fallback_service")
        if not fallback_service:
            # Try to use cached result
            cache_result = context.get("cached_result")
            if cache_result is not None:
                return cache_result
            raise ValueError("No fallback service or cache available")

        if asyncio.iscoroutinefunction(fallback_service):
            return await fallback_service()
        else:
            return fallback_service()

    async def _handle_fallback_method(
        self,
        action: RecoveryAction,
        error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Handle fallback method strategy."""
        fallback_method = context.get("fallback_method")
        if not fallback_method:
            raise ValueError("No fallback method provided")

        if asyncio.iscoroutinefunction(fallback_method):
            return await fallback_method()
        else:
            return fallback_method()

    async def _handle_degraded_mode(
        self,
        action: RecoveryAction,
        error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Handle degraded mode strategy."""
        feature = context.get("feature", "unknown")
        self._degraded_mode.enable_degraded_mode(
            feature,
            reason=str(error),
            fallback_handler=context.get("fallback_handler"),
        )

        # Return a placeholder result indicating degraded mode
        return {
            "degraded": True,
            "feature": feature,
            "original_error": str(error),
            "message": f"Operation completed in degraded mode for {feature}",
        }

    async def _handle_skip_and_continue(
        self,
        action: RecoveryAction,
        error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Handle skip and continue strategy."""
        skipped_item = context.get("skipped_item")
        return {
            "skipped": True,
            "skipped_item": skipped_item,
            "error": str(error),
            "message": f"Skipped item and continued: {skipped_item}",
        }

    async def _handle_use_cache(
        self,
        action: RecoveryAction,
        error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Handle use cache strategy."""
        cached_result = context.get("cached_result")
        if cached_result is None:
            raise ValueError("No cached result available")
        return cached_result

    async def _handle_use_default(
        self,
        action: RecoveryAction,
        error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Handle use default strategy."""
        default_value = context.get("default_value")
        return {
            "used_default": True,
            "default_value": default_value,
            "original_error": str(error),
        }

    async def _handle_notify_user(
        self,
        action: RecoveryAction,
        error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Handle notify user strategy."""
        return {
            "notification_sent": True,
            "error": str(error),
            "message": "User has been notified of the error",
        }

    async def _handle_escalate(
        self,
        action: RecoveryAction,
        error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Handle escalate strategy."""
        raise error  # Re-raise to trigger escalation

    async def _handle_no_recovery(
        self,
        action: RecoveryAction,
        error: Exception,
        context: Dict[str, Any],
        retry_config: Optional[Dict[str, Any]],
    ) -> Any:
        """Handle no recovery strategy."""
        raise error


class ErrorSupervisor:
    """
    Main supervisor class that orchestrates the error recovery pipeline.

    Error Handling Pipeline:
    1. Error occurs → Supervisor catches
    2. Classify error type (ErrorClassifier)
    3. Check error pattern library (ErrorPatterns)
    4. Attempt recovery strategy (ErrorRecovery)
    5. Fallback to degraded mode if recovery fails
    6. Escalate to human if all recovery attempts fail
    """

    def __init__(
        self,
        classifier: Optional[ErrorClassifier] = None,
        pattern_library: Optional[ErrorPatternLibrary] = None,
        max_recovery_attempts: int = 3,
    ):
        self.classifier = classifier or get_classifier()
        self.pattern_library = pattern_library or get_pattern_library()
        self.max_recovery_attempts = max_recovery_attempts

        self.degraded_mode = DegradedModeManager()
        self.escalation = EscalationManager()
        self.strategy_executor = RecoveryStrategyExecutor(self.degraded_mode)

    async def supervise(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        operation: Optional[Callable] = None,
    ) -> RecoveryResult:
        """
        Supervise error recovery for an exception.

        Args:
            error: The exception to recover from
            context: Additional context for recovery
            operation: Optional operation to retry

        Returns:
            RecoveryResult with status and details
        """
        context = context or {}
        if operation:
            context["operation"] = operation

        result = RecoveryResult(
            status=RecoveryStatus.IN_PROGRESS,
            original_error=error,
            classification=self.classifier.classify(error, context),
        )

        logger.info(f"Supervising error recovery: {type(error).__name__}")

        # Step 2: Classify the error
        classification = result.classification
        logger.info(
            f"Error classified as: {classification.error_type.value} ({classification.severity.value})"
        )

        # Step 3: Get error pattern and recovery actions
        pattern = self.pattern_library.get_pattern(classification.error_type)
        if not pattern:
            logger.warning(f"No pattern found for error type: {classification.error_type}")
            # Use default pattern with basic retry
            actions = [
                RecoveryAction(
                    name="default_retry",
                    strategy=RecoveryStrategy.RETRY,
                    description="Default retry action",
                    success_rate=0.3,
                )
            ]
        else:
            actions = pattern.recovery_actions

        # Step 4: Attempt recovery strategies
        for action in actions[: self.max_recovery_attempts]:
            attempt = await self.strategy_executor.execute(
                action,
                error,
                context,
                retry_config={"max_attempts": pattern.max_recovery_attempts} if pattern else None,
            )

            result.attempts.append(attempt)

            if attempt.status == RecoveryStatus.SUCCEEDED:
                result.status = RecoveryStatus.SUCCEEDED
                result.final_result = attempt.result
                result.completed_at = datetime.now(timezone.utc)
                result.message = f"Recovery succeeded with action: {action.name}"
                logger.info(f"Recovery succeeded: {action.name}")
                return result

            # Check if we should continue trying
            if attempt.status == RecoveryStatus.FAILED:
                logger.warning(f"Recovery attempt {action.name} failed, trying next...")

        # Step 5: Fallback to degraded mode if available
        fallback_mode = self.pattern_library.get_fallback_mode(classification.error_type)
        if fallback_mode and classification.severity != ErrorSeverity.BLOCKING:
            result.status = RecoveryStatus.DEGRADED
            result.fallback_mode = fallback_mode
            result.completed_at = datetime.now(timezone.utc)
            result.message = f"Recovery degraded: using {fallback_mode} mode"
            logger.warning(f"Recovery degraded: {fallback_mode}")
            return result

        # Step 6: Escalate to human if all recovery attempts fail
        if (
            self.pattern_library.should_escalate(classification.error_type)
            or classification.severity == ErrorSeverity.BLOCKING
        ):
            result.status = RecoveryStatus.ESCALATED
            result.escalated = True
            result.escalated_at = datetime.now(timezone.utc)
            result.completed_at = datetime.now(timezone.utc)
            escalation_id = self.escalation.escalate(error, classification, result, context)
            result.message = f"Error escalated to human review: {escalation_id}"
            logger.error(f"Escalated: {escalation_id}")
            return result

        # No more options
        result.status = RecoveryStatus.FAILED
        result.completed_at = datetime.now(timezone.utc)
        result.message = "All recovery attempts failed"
        return result

    def register_escalation_handler(self, handler: Callable) -> None:
        """Register a handler to be called when errors are escalated."""
        self.escalation.register_handler(handler)


# Decorator for automatic error supervision
def with_supervision(
    max_recovery_attempts: int = 3,
    context_provider: Optional[Callable[[], Dict[str, Any]]] = None,
):
    """
    Decorator to wrap a function with error supervision.

    Usage:
        @with_supervision(max_recovery_attempts=3)
        async def my_function():
            ...
    """

    def decorator(func: Callable):
        supervisor = ErrorSupervisor(max_recovery_attempts=max_recovery_attempts)

        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                ctx = context_provider() if context_provider else {}
                ctx["function"] = func.__name__
                result = await supervisor.supervise(e, ctx, lambda: func(*args, **kwargs))
                if result.succeeded:
                    return result.final_result
                elif result.escalated:
                    # Re-raise the original error after escalation
                    raise result.original_error
                elif result.recovered_with_degraded:
                    return result.final_result
                else:
                    raise result.original_error

        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ctx = context_provider() if context_provider else {}
                ctx["function"] = func.__name__
                # For sync functions, we can't do async recovery well
                # Just log and re-raise
                logger.error(f"Sync function {func.__name__} failed: {e}")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Global supervisor instance
_supervisor: Optional[ErrorSupervisor] = None


def get_supervisor() -> ErrorSupervisor:
    """Get or create the global supervisor instance."""
    global _supervisor
    if _supervisor is None:
        _supervisor = ErrorSupervisor()
    return _supervisor


async def recover(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    operation: Optional[Callable] = None,
) -> RecoveryResult:
    """
    Convenience function to recover from an error using the global supervisor.

    Args:
        error: The exception to recover from
        context: Additional context for recovery
        operation: Optional operation to retry

    Returns:
        RecoveryResult with status and details
    """
    return await get_supervisor().supervise(error, context, operation)
