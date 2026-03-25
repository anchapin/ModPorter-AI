"""
Error Auto-Recovery System

Automatically recovers from common conversion errors with:
- Error pattern detection
- Auto-recovery strategies
- Fallback mechanisms
- Recovery success tracking
"""

import logging
<<<<<<< HEAD
from typing import Dict, List, Optional, Any
=======
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import random
import time

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for errors."""
<<<<<<< HEAD

=======
    LOW = "low"  # Can retry immediately
    MEDIUM = "medium"  # Retry with backoff
    HIGH = "high"  # May need intervention
    CRITICAL = "critical"  # Stop execution


class ErrorType(Enum):
    """Types of conversion errors."""
<<<<<<< HEAD

=======
    SYNTAX_ERROR = "syntax_error"
    MISSING_PATTERN = "missing_pattern"
    TYPE_MISMATCH = "type_mismatch"
    RESOURCE_ERROR = "resource_error"
    TIMEOUT_ERROR = "timeout_error"
    DEPENDENCY_ERROR = "dependency_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


@dataclass
class ConversionError:
    """Represents a conversion error."""
<<<<<<< HEAD

=======
    error_id: str
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    mod_path: Optional[str] = None
    stack_trace: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3
<<<<<<< HEAD

=======
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "type": self.error_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "retry_count": self.retry_count,
            "can_retry": self.retry_count < self.max_retries,
        }


@dataclass
class RecoveryResult:
    """Result of error recovery attempt."""
<<<<<<< HEAD

=======
    success: bool
    recovery_strategy: str
    message: str
    retry_count: int = 0
    fallback_used: bool = False
    manual_intervention_required: bool = False
<<<<<<< HEAD

=======
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "strategy": self.recovery_strategy,
            "message": self.message,
            "retry_count": self.retry_count,
            "fallback_used": self.fallback_used,
            "manual_intervention": self.manual_intervention_required,
        }


class ErrorPatternDetector:
    """
    Detects error patterns from conversion errors.
<<<<<<< HEAD

    Identifies common error types and suggests recovery strategies.
    """

=======
    
    Identifies common error types and suggests recovery strategies.
    """
    
    def __init__(self):
        # Error pattern mappings
        self.patterns = self._initialize_patterns()
        logger.info("ErrorPatternDetector initialized")
<<<<<<< HEAD

=======
    
    def _initialize_patterns(self) -> Dict[str, ErrorType]:
        """Initialize error pattern mappings."""
        return {
            # Syntax errors
            "syntax error": ErrorType.SYNTAX_ERROR,
            "parse error": ErrorType.SYNTAX_ERROR,
            "unexpected token": ErrorType.SYNTAX_ERROR,
            "missing semicolon": ErrorType.SYNTAX_ERROR,
<<<<<<< HEAD
=======
            
            # Missing pattern errors
            "no pattern found": ErrorType.MISSING_PATTERN,
            "pattern not found": ErrorType.MISSING_PATTERN,
            "unsupported feature": ErrorType.MISSING_PATTERN,
<<<<<<< HEAD
=======
            
            # Type mismatch errors
            "type mismatch": ErrorType.TYPE_MISMATCH,
            "incompatible types": ErrorType.TYPE_MISMATCH,
            "cannot convert": ErrorType.TYPE_MISMATCH,
<<<<<<< HEAD
=======
            
            # Resource errors
            "out of memory": ErrorType.RESOURCE_ERROR,
            "resource not found": ErrorType.RESOURCE_ERROR,
            "file not found": ErrorType.RESOURCE_ERROR,
<<<<<<< HEAD
=======
            
            # Timeout errors
            "timeout": ErrorType.TIMEOUT_ERROR,
            "timed out": ErrorType.TIMEOUT_ERROR,
            "deadline exceeded": ErrorType.TIMEOUT_ERROR,
<<<<<<< HEAD
=======
            
            # Dependency errors
            "dependency not found": ErrorType.DEPENDENCY_ERROR,
            "missing dependency": ErrorType.DEPENDENCY_ERROR,
            "import error": ErrorType.DEPENDENCY_ERROR,
<<<<<<< HEAD
=======
            
            # Validation errors
            "validation failed": ErrorType.VALIDATION_ERROR,
            "invalid format": ErrorType.VALIDATION_ERROR,
            "checksum mismatch": ErrorType.VALIDATION_ERROR,
        }
<<<<<<< HEAD

    def detect_error_type(self, error_message: str) -> ErrorType:
        """Detect error type from error message."""
        message_lower = error_message.lower()

        for pattern, error_type in self.patterns.items():
            if pattern in message_lower:
                return error_type

        return ErrorType.UNKNOWN

=======
    
    def detect_error_type(self, error_message: str) -> ErrorType:
        """Detect error type from error message."""
        message_lower = error_message.lower()
        
        for pattern, error_type in self.patterns.items():
            if pattern in message_lower:
                return error_type
        
        return ErrorType.UNKNOWN
    
    def get_severity(self, error_type: ErrorType, retry_count: int) -> ErrorSeverity:
        """Determine error severity based on type and retry count."""
        # Critical errors
        if error_type in [ErrorType.RESOURCE_ERROR, ErrorType.TIMEOUT_ERROR]:
            return ErrorSeverity.HIGH if retry_count > 1 else ErrorSeverity.MEDIUM
<<<<<<< HEAD

        # High severity errors
        if error_type in [ErrorType.DEPENDENCY_ERROR, ErrorType.VALIDATION_ERROR]:
            return ErrorSeverity.HIGH

        # Medium severity errors
        if error_type in [ErrorType.TYPE_MISMATCH, ErrorType.MISSING_PATTERN]:
            return ErrorSeverity.MEDIUM

        # Low severity errors
        if error_type == ErrorType.SYNTAX_ERROR:
            return ErrorSeverity.LOW

=======
        
        # High severity errors
        if error_type in [ErrorType.DEPENDENCY_ERROR, ErrorType.VALIDATION_ERROR]:
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if error_type in [ErrorType.TYPE_MISMATCH, ErrorType.MISSING_PATTERN]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors
        if error_type == ErrorType.SYNTAX_ERROR:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM


class RecoveryStrategy:
    """Base class for recovery strategies."""
<<<<<<< HEAD

=======
    
    def __init__(self, name: str, success_rate: float = 0.8):
        self.name = name
        self.success_rate = success_rate
        self.execution_count = 0
        self.success_count = 0
<<<<<<< HEAD

=======
    
    def execute(self, error: ConversionError) -> RecoveryResult:
        """Execute recovery strategy."""
        self.execution_count += 1
        raise NotImplementedError
<<<<<<< HEAD

=======
    
    def record_success(self):
        """Record successful recovery."""
        self.success_count += 1
        if self.execution_count > 0:
            self.success_rate = self.success_count / self.execution_count
<<<<<<< HEAD

=======
    
    def record_failure(self):
        """Record failed recovery."""
        if self.execution_count > 0:
            self.success_rate = self.success_count / self.execution_count


class RetryStrategy(RecoveryStrategy):
    """Retry the operation with exponential backoff."""
<<<<<<< HEAD

    def __init__(self):
        super().__init__("retry_with_backoff", success_rate=0.9)

=======
    
    def __init__(self):
        super().__init__("retry_with_backoff", success_rate=0.9)
    
    def execute(self, error: ConversionError) -> RecoveryResult:
        """Execute retry with backoff."""
        if error.retry_count >= error.max_retries:
            return RecoveryResult(
                success=False,
                recovery_strategy=self.name,
                message=f"Max retries ({error.max_retries}) exceeded",
                retry_count=error.retry_count,
            )
<<<<<<< HEAD

        # Calculate backoff delay
        base_delay = 1.0
        max_delay = 30.0
        delay = min(base_delay * (2**error.retry_count) + random.uniform(0, 1), max_delay)

        logger.info(
            f"Retrying after {delay:.1f}s (attempt {error.retry_count + 1}/{error.max_retries})"
        )
        time.sleep(delay)

        error.retry_count += 1

=======
        
        # Calculate backoff delay
        base_delay = 1.0
        max_delay = 30.0
        delay = min(base_delay * (2 ** error.retry_count) + random.uniform(0, 1), max_delay)
        
        logger.info(f"Retrying after {delay:.1f}s (attempt {error.retry_count + 1}/{error.max_retries})")
        time.sleep(delay)
        
        error.retry_count += 1
        
        return RecoveryResult(
            success=True,  # Will be retried
            recovery_strategy=self.name,
            message=f"Retry scheduled (delay={delay:.1f}s)",
            retry_count=error.retry_count,
        )


class FallbackStrategy(RecoveryStrategy):
    """Use fallback mechanism when primary fails."""
<<<<<<< HEAD

    def __init__(self, fallback_name: str):
        super().__init__(f"use_fallback_{fallback_name}", success_rate=0.7)
        self.fallback_name = fallback_name

=======
    
    def __init__(self, fallback_name: str):
        super().__init__(f"use_fallback_{fallback_name}", success_rate=0.7)
        self.fallback_name = fallback_name
    
    def execute(self, error: ConversionError) -> RecoveryResult:
        """Execute fallback."""
        return RecoveryResult(
            success=True,
            recovery_strategy=self.name,
            message=f"Using fallback: {self.fallback_name}",
            fallback_used=True,
        )


class SimplifyStrategy(RecoveryStrategy):
    """Simplify the conversion to avoid complex features."""
<<<<<<< HEAD

    def __init__(self):
        super().__init__("simplify_conversion", success_rate=0.6)

=======
    
    def __init__(self):
        super().__init__("simplify_conversion", success_rate=0.6)
    
    def execute(self, error: ConversionError) -> RecoveryResult:
        """Execute simplification."""
        return RecoveryResult(
            success=True,
            recovery_strategy=self.name,
            message="Simplified conversion applied (some features may be omitted)",
            fallback_used=False,
        )


class ManualInterventionStrategy(RecoveryStrategy):
    """Flag for manual review when auto-recovery fails."""
<<<<<<< HEAD

    def __init__(self):
        super().__init__("manual_review", success_rate=1.0)

=======
    
    def __init__(self):
        super().__init__("manual_review", success_rate=1.0)
    
    def execute(self, error: ConversionError) -> RecoveryResult:
        """Flag for manual review."""
        return RecoveryResult(
            success=False,
            recovery_strategy=self.name,
            message="Manual review required - auto-recovery exhausted",
            manual_intervention_required=True,
        )


class AutoRecoveryEngine:
    """
    Main engine for automatic error recovery.
<<<<<<< HEAD

=======
    
    Coordinates:
    - Error detection
    - Strategy selection
    - Recovery execution
    - Success tracking
    """
<<<<<<< HEAD

=======
    
    def __init__(self):
        self.detector = ErrorPatternDetector()
        self.strategies = self._initialize_strategies()
        self.recovery_history: List[Dict[str, Any]] = []
        logger.info("AutoRecoveryEngine initialized")
<<<<<<< HEAD

=======
    
    def _initialize_strategies(self) -> Dict[ErrorType, List[RecoveryStrategy]]:
        """Initialize recovery strategies by error type."""
        return {
            ErrorType.SYNTAX_ERROR: [
                RetryStrategy(),
                SimplifyStrategy(),
                ManualInterventionStrategy(),
            ],
            ErrorType.MISSING_PATTERN: [
                FallbackStrategy("generic_pattern"),
                SimplifyStrategy(),
                ManualInterventionStrategy(),
            ],
            ErrorType.TYPE_MISMATCH: [
                RetryStrategy(),
                FallbackStrategy("type_coercion"),
                ManualInterventionStrategy(),
            ],
            ErrorType.RESOURCE_ERROR: [
                RetryStrategy(),
                FallbackStrategy("resource_cleanup"),
                ManualInterventionStrategy(),
            ],
            ErrorType.TIMEOUT_ERROR: [
                RetryStrategy(),
                FallbackStrategy("extended_timeout"),
                ManualInterventionStrategy(),
            ],
            ErrorType.DEPENDENCY_ERROR: [
                FallbackStrategy("missing_dependency"),
                SimplifyStrategy(),
                ManualInterventionStrategy(),
            ],
            ErrorType.VALIDATION_ERROR: [
                RetryStrategy(),
                FallbackStrategy("relaxed_validation"),
                ManualInterventionStrategy(),
            ],
            ErrorType.UNKNOWN: [
                RetryStrategy(),
                ManualInterventionStrategy(),
            ],
        }
<<<<<<< HEAD

    def attempt_recovery(self, error: ConversionError) -> RecoveryResult:
        """
        Attempt to recover from an error.

        Args:
            error: The conversion error to recover from

=======
    
    def attempt_recovery(self, error: ConversionError) -> RecoveryResult:
        """
        Attempt to recover from an error.
        
        Args:
            error: The conversion error to recover from
            
        Returns:
            RecoveryResult with recovery status
        """
        # Detect error type if not set
        if error.error_type == ErrorType.UNKNOWN:
            error.error_type = self.detector.detect_error_type(error.message)
<<<<<<< HEAD

        # Get severity
        error.severity = self.detector.get_severity(error.error_type, error.retry_count)

        # Get strategies for this error type
        strategies = self.strategies.get(error.error_type, self.strategies[ErrorType.UNKNOWN])

        # Try each strategy in order
        for strategy in strategies:
            result = strategy.execute(error)

            # Record in history
            self.recovery_history.append(
                {
                    "error_id": error.error_id,
                    "error_type": error.error_type.value,
                    "strategy": strategy.name,
                    "success": result.success,
                    "timestamp": datetime.now().isoformat(),
                }
            )

=======
        
        # Get severity
        error.severity = self.detector.get_severity(error.error_type, error.retry_count)
        
        # Get strategies for this error type
        strategies = self.strategies.get(error.error_type, self.strategies[ErrorType.UNKNOWN])
        
        # Try each strategy in order
        for strategy in strategies:
            result = strategy.execute(error)
            
            # Record in history
            self.recovery_history.append({
                "error_id": error.error_id,
                "error_type": error.error_type.value,
                "strategy": strategy.name,
                "success": result.success,
                "timestamp": datetime.now().isoformat(),
            })
            
            if result.success:
                strategy.record_success()
                logger.info(f"Recovery successful: {strategy.name}")
                return result
            else:
                strategy.record_failure()
<<<<<<< HEAD

        # All strategies failed
        logger.warning(f"All recovery strategies failed for error {error.error_id}")

=======
        
        # All strategies failed
        logger.warning(f"All recovery strategies failed for error {error.error_id}")
        
        return RecoveryResult(
            success=False,
            recovery_strategy="all_exhausted",
            message="All auto-recovery strategies failed",
            manual_intervention_required=True,
        )
<<<<<<< HEAD

=======
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        total = len(self.recovery_history)
        successful = sum(1 for r in self.recovery_history if r["success"])
<<<<<<< HEAD

=======
        
        # Strategy success rates
        strategy_stats = {}
        for error_type, strategies in self.strategies.items():
            for strategy in strategies:
                if strategy.execution_count > 0:
                    key = f"{error_type.value}:{strategy.name}"
                    strategy_stats[key] = {
                        "executions": strategy.execution_count,
                        "success_rate": strategy.success_rate,
                    }
<<<<<<< HEAD

=======
        
        return {
            "total_recoveries": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "strategy_stats": strategy_stats,
        }


class ConversionErrorHandler:
    """
    High-level error handler for conversions.
<<<<<<< HEAD

    Integrates with the conversion pipeline to provide
    seamless error recovery.
    """

=======
    
    Integrates with the conversion pipeline to provide
    seamless error recovery.
    """
    
    def __init__(self, auto_recovery_enabled: bool = True):
        self.recovery_engine = AutoRecoveryEngine()
        self.auto_recovery_enabled = auto_recovery_enabled
        self.error_log: List[ConversionError] = []
        logger.info(f"ConversionErrorHandler initialized (auto_recovery={auto_recovery_enabled})")
<<<<<<< HEAD

=======
    
    def handle_error(
        self,
        error_message: str,
        mod_path: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ) -> RecoveryResult:
        """
        Handle a conversion error.
<<<<<<< HEAD

=======
        
        Args:
            error_message: Error message
            mod_path: Path to mod being converted
            stack_trace: Optional stack trace
<<<<<<< HEAD

=======
            
        Returns:
            RecoveryResult with recovery status
        """
        # Create error object
        error = ConversionError(
            error_id=f"err_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}",
            error_type=ErrorType.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            message=error_message,
            mod_path=mod_path,
            stack_trace=stack_trace,
        )
<<<<<<< HEAD

        # Log error
        self.error_log.append(error)
        logger.error(f"Conversion error: {error_message} (mod={mod_path})")

        # Attempt auto-recovery if enabled
        if self.auto_recovery_enabled:
            result = self.recovery_engine.attempt_recovery(error)

=======
        
        # Log error
        self.error_log.append(error)
        logger.error(f"Conversion error: {error_message} (mod={mod_path})")
        
        # Attempt auto-recovery if enabled
        if self.auto_recovery_enabled:
            result = self.recovery_engine.attempt_recovery(error)
            
            if result.success:
                logger.info(f"Auto-recovery successful: {result.recovery_strategy}")
            elif result.manual_intervention_required:
                logger.warning(f"Manual intervention required for error {error.error_id}")
<<<<<<< HEAD

=======
            
            return result
        else:
            # Auto-recovery disabled
            return RecoveryResult(
                success=False,
                recovery_strategy="none",
                message="Auto-recovery disabled",
                manual_intervention_required=True,
            )
<<<<<<< HEAD

=======
    
    def can_continue(self) -> bool:
        """Check if conversion can continue after errors."""
        if not self.error_log:
            return True
<<<<<<< HEAD

        # Check recent errors
        recent_errors = self.error_log[-5:]
        critical_count = sum(1 for e in recent_errors if e.severity == ErrorSeverity.CRITICAL)

        # Stop if multiple critical errors
        return critical_count < 2

=======
        
        # Check recent errors
        recent_errors = self.error_log[-5:]
        critical_count = sum(1 for e in recent_errors if e.severity == ErrorSeverity.CRITICAL)
        
        # Stop if multiple critical errors
        return critical_count < 2
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors."""
        by_type = {}
        by_severity = {}
<<<<<<< HEAD

=======
        
        for error in self.error_log:
            # Count by type
            type_key = error.error_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
<<<<<<< HEAD

            # Count by severity
            sev_key = error.severity.value
            by_severity[sev_key] = by_severity.get(sev_key, 0) + 1

=======
            
            # Count by severity
            sev_key = error.severity.value
            by_severity[sev_key] = by_severity.get(sev_key, 0) + 1
        
        return {
            "total_errors": len(self.error_log),
            "by_type": by_type,
            "by_severity": by_severity,
            "can_continue": self.can_continue(),
            "recovery_stats": self.recovery_engine.get_recovery_stats(),
        }


# Convenience functions
def recover_from_error(
    error_message: str,
    mod_path: Optional[str] = None,
    auto_retry: bool = True,
) -> RecoveryResult:
    """
    Attempt to recover from a conversion error.
<<<<<<< HEAD

=======
    
    Args:
        error_message: Error message
        mod_path: Path to mod being converted
        auto_retry: Whether to automatically retry
<<<<<<< HEAD

=======
        
    Returns:
        RecoveryResult with recovery status
    """
    handler = ConversionErrorHandler(auto_recovery_enabled=auto_retry)
    return handler.handle_error(error_message, mod_path)


def get_recovery_stats() -> Dict[str, Any]:
    """Get recovery statistics."""
    handler = ConversionErrorHandler()
    return handler.recovery_engine.get_recovery_stats()
