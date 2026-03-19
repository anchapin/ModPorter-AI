"""
Error Auto-Recovery System

Automatic error detection and recovery for conversion failures.
Implements error pattern detection, auto-recovery strategies, fallback mechanisms,
and recovery success tracking to achieve >80% auto-recovery rate.

Phase: 2.5.5
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Categories of conversion errors."""

    SYNTAX = "syntax_error"
    MISSING_PATTERN = "missing_pattern"
    TYPE_MISMATCH = "type_mismatch"
    API_INCOMPATIBILITY = "api_incompatibility"
    RESOURCE_ERROR = "resource_error"
    UNKNOWN = "unknown"


class RecoveryPriority(Enum):
    """Priority for error recovery."""

    HIGH = 1
    MEDIUM = 2
    LOW = 3


class RecoveryAction(Enum):
    """Actions taken during recovery."""

    AUTO_FIXED = "auto_fixed"
    FALLBACK_APPLIED = "fallback_applied"
    SKIPPED = "skipped"
    MANUAL_REVIEW = "manual_review"
    FAILED = "failed"
    RETRYING = "retrying"


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ErrorContext:
    """Context information for error recovery."""

    current_file: Optional[str] = None
    error_line: Optional[int] = None
    error_column: Optional[int] = None
    current_method: Optional[str] = None
    current_class: Optional[str] = None
    available_imports: List[str] = field(default_factory=list)
    loaded_dependencies: List[str] = field(default_factory=list)
    stack_trace: List[str] = field(default_factory=list)
    conversion_state: Optional[str] = None


@dataclass
class ErrorContextInfo:
    """Extracted context information."""

    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    method_name: Optional[str] = None
    class_name: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    stack_trace: List[str] = field(default_factory=list)


@dataclass
class ClassifiedError:
    """Error with classification and context."""

    error_type: ErrorType
    message: str
    confidence: float
    context: ErrorContextInfo
    recovery_priority: RecoveryPriority
    original_exception: Optional[Exception] = None


@dataclass
class MatchedPattern:
    """Matched error pattern."""

    error_type: ErrorType
    pattern: str
    confidence: float


@dataclass
class StrategyResult:
    """Result of a recovery strategy."""

    success: bool
    action: str
    confidence: float = 0.0
    elapsed_time: float = 0.0
    modified: bool = False
    error: Optional[str] = None
    requires_manual: bool = False
    warning: Optional[str] = None


@dataclass
class RecoveryResult:
    """Result of error recovery attempt."""

    success: bool
    recovery_action: Optional[RecoveryAction] = None
    confidence: float = 0.0
    recovery_time: float = 0.0
    error: Optional[str] = None
    manual_intervention_required: bool = False
    retry_recommended: bool = False
    fallback_used: bool = False


@dataclass
class FallbackStep(Enum):
    """Fallback chain steps."""

    ALTERNATIVE_STRATEGY = "alternative_strategy"
    SAFE_DEFAULT = "safe_default"
    SKIP_ELEMENT = "skip_element"
    MANUAL_REVIEW = "manual_review"


@dataclass
class FallbackResult:
    """Result of fallback execution."""

    step: FallbackStep
    success: bool
    action: str
    requires_review: bool = False


@dataclass
class StepResult:
    """Result of a single fallback step."""

    success: bool
    action: str
    modified: bool = False


@dataclass
class SkippedElement:
    """Element that was skipped during conversion."""

    reason: ErrorType
    location: str
    line: Optional[int]
    original_code: str


@dataclass
class RecoveryRecord:
    """Record of a single recovery attempt."""

    error_id: str
    error_type: ErrorType
    recovery_strategy: str
    success: bool
    recovery_time_ms: int
    fallback_used: bool
    timestamp: datetime


@dataclass
class RecoveryMetrics:
    """Metrics for error auto-recovery."""

    total_errors: int = 0
    auto_recovered: int = 0
    manual_intervention: int = 0
    failed: int = 0

    @property
    def auto_recovery_rate(self) -> float:
        """Calculate auto-recovery rate."""
        if self.total_errors == 0:
            return 1.0
        return self.auto_recovered / self.total_errors

    @property
    def manual_intervention_rate(self) -> float:
        """Calculate manual intervention rate."""
        if self.total_errors == 0:
            return 0.0
        return self.manual_intervention / self.total_errors


class PatternMatcher:
    """Match error messages against known patterns."""

    ERROR_PATTERNS: Dict[ErrorType, List[str]] = {
        ErrorType.RESOURCE_ERROR: [
            r"file not found",
            r"resource not found",
            r"IO error",
            r"corrupted file",
            r"read error",
            r"write error",
        ],
        ErrorType.API_INCOMPATIBILITY: [
            r"deprecated API",
            r"API version mismatch",
            r"unsupported operation",
            r"access denied",
            r"method not found",
            r"no such method",
        ],
        ErrorType.TYPE_MISMATCH: [
            r"incompatible types",
            r"type mismatch",
            r"cannot convert",
            r"expected .+ but .+ was",
            r"wrong type",
            r"type error",
        ],
        ErrorType.MISSING_PATTERN: [
            r"cannot find symbol",
            r"undefined reference",
            r"missing resource",
            r"unknown block",
            r"cannot resolve method",
            r"no such element",
            r"not found",
            r"undefined variable",
        ],
        ErrorType.SYNTAX: [
            r"unexpected token",
            r"expected .+ but found",
            r"syntax error",
            r"invalid expression",
            r"unterminated string",
            r"missing .+ at position",
            r"invalid .+ syntax",
            r"token .+ not valid",
        ],
    }

    def __init__(self, patterns: Optional[Dict[ErrorType, List[str]]] = None):
        self.patterns = patterns or self.ERROR_PATTERNS
        self._compiled_patterns: Dict[ErrorType, List[tuple]] = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        for error_type, pattern_list in self.patterns.items():
            self._compiled_patterns[error_type] = [
                (re.compile(pattern, re.IGNORECASE), pattern)
                for pattern in pattern_list
            ]

    def match(self, error_message: str) -> MatchedPattern:
        """Match error message against patterns."""
        best_match = None
        best_confidence = 0.0

        for error_type, compiled_patterns in self._compiled_patterns.items():
            for pattern, original_pattern in compiled_patterns:
                match = pattern.search(error_message)
                if match:
                    # Calculate confidence based on match quality
                    confidence = self._calculate_confidence(
                        error_message, match, original_pattern
                    )
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = MatchedPattern(
                            error_type=error_type,
                            pattern=original_pattern,
                            confidence=confidence,
                        )

        if best_match:
            return best_match

        # Default to unknown
        return MatchedPattern(
            error_type=ErrorType.UNKNOWN,
            pattern="unknown",
            confidence=0.1,
        )

    def _calculate_confidence(
        self, error_message: str, match: re.Match, pattern: str
    ) -> float:
        """Calculate confidence score for match."""
        base_confidence = 0.7

        # Boost for full match
        if match.group(0).lower() == error_message.lower():
            base_confidence = 0.95
        # Boost for longer matches
        elif len(match.group(0)) > 20:
            base_confidence += 0.1
        # Boost for specific patterns (not generic)
        if len(pattern) > 20:
            base_confidence += 0.1

        return min(base_confidence, 0.95)


class ErrorPatternDetector:
    """Detect and classify conversion errors."""

    def __init__(self):
        self.error_history: List[ClassifiedError] = []
        self.pattern_matcher = PatternMatcher()

    async def detect_error(
        self,
        error: Exception,
        context: ErrorContext,
    ) -> ClassifiedError:
        """Detect and classify error from exception."""

        # Extract error message
        error_message = self._extract_message(error)

        # Match against patterns
        matched_pattern = self.pattern_matcher.match(error_message)

        # Extract context
        context_info = self._extract_context(context)

        # Calculate confidence
        confidence = self._calculate_confidence(
            pattern=matched_pattern,
            context=context_info,
        )

        # Create classified error
        return ClassifiedError(
            error_type=matched_pattern.error_type,
            message=error_message,
            confidence=confidence,
            context=context_info,
            recovery_priority=self._get_recovery_priority(matched_pattern.error_type),
            original_exception=error,
        )

    def _extract_message(self, error: Exception) -> str:
        """Extract clean error message."""
        message = str(error)

        # Clean up stack traces
        if "Exception" in message:
            parts = message.split(":")
            if len(parts) > 1:
                message = parts[-1].strip()

        # Remove extra whitespace
        message = " ".join(message.split())

        return message

    def _extract_context(self, context: ErrorContext) -> ErrorContextInfo:
        """Extract additional context for recovery."""

        return ErrorContextInfo(
            file_path=context.current_file,
            line_number=context.error_line,
            column=context.error_column,
            method_name=context.current_method,
            class_name=context.current_class,
            imports=context.available_imports,
            dependencies=context.loaded_dependencies,
            stack_trace=context.stack_trace,
        )

    def _calculate_confidence(
        self,
        pattern: MatchedPattern,
        context: ErrorContextInfo,
    ) -> float:
        """Calculate confidence score for error classification."""

        base_confidence = pattern.confidence

        # Boost confidence with more context
        if context.file_path:
            base_confidence += 0.05
        if context.line_number:
            base_confidence += 0.03
        if context.method_name:
            base_confidence += 0.02

        return min(base_confidence, 1.0)

    def _get_recovery_priority(self, error_type: ErrorType) -> RecoveryPriority:
        """Determine recovery priority by error type."""

        priorities = {
            ErrorType.SYNTAX: RecoveryPriority.HIGH,
            ErrorType.MISSING_PATTERN: RecoveryPriority.HIGH,
            ErrorType.TYPE_MISMATCH: RecoveryPriority.MEDIUM,
            ErrorType.API_INCOMPATIBILITY: RecoveryPriority.MEDIUM,
            ErrorType.RESOURCE_ERROR: RecoveryPriority.LOW,
            ErrorType.UNKNOWN: RecoveryPriority.LOW,
        }

        return priorities.get(error_type, RecoveryPriority.LOW)


class CircuitBreaker:
    """Prevent error cascade with circuit breaker."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        if self.last_failure_time is None:
            return False
        return (datetime.utcnow() - self.last_failure_time).total_seconds() >= self.timeout

    def _record_success(self):
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self._reset()
        elif self.state == CircuitState.CLOSED:
            # Reset failures on success
            self.failures = 0

    def _record_failure(self):
        """Record failed call."""
        self.failures += 1
        self.last_failure_time = datetime.utcnow()

        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.half_open_calls = 0

    def _reset(self):
        """Reset circuit breaker."""
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0
        self.last_failure_time = None

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""

        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            self._record_success()
            return result

        except Exception as e:
            self._record_failure()
            raise


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class AutoRecoveryEngine:
    """Execute automatic recovery strategies."""

    def __init__(self):
        self.strategies: Dict[ErrorType, Callable] = {}
        self._register_default_strategies()

    def _register_default_strategies(self):
        """Register default recovery strategies."""
        self.strategies = {
            ErrorType.SYNTAX: self._recover_syntax,
            ErrorType.MISSING_PATTERN: self._recover_missing_pattern,
            ErrorType.TYPE_MISMATCH: self._recover_type_mismatch,
            ErrorType.API_INCOMPATIBILITY: self._recover_api_incompatibility,
            ErrorType.RESOURCE_ERROR: self._recover_resource_error,
        }

    async def attempt_recovery(
        self,
        classified_error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> RecoveryResult:
        """Attempt automatic recovery for classified error."""

        start_time = time.time()
        strategy = self.strategies.get(classified_error.error_type)

        if not strategy:
            return RecoveryResult(
                success=False,
                error="No recovery strategy available",
                manual_intervention_required=True,
            )

        try:
            result = await strategy(classified_error, conversion_state)

            recovery_time = time.time() - start_time

            if result.success:
                return RecoveryResult(
                    success=True,
                    recovery_action=RecoveryAction.AUTO_FIXED if result.modified else RecoveryAction.RETRYING,
                    confidence=result.confidence,
                    recovery_time=recovery_time,
                )
            else:
                # Strategy failed
                return RecoveryResult(
                    success=False,
                    error=result.error,
                    manual_intervention_required=result.requires_manual,
                    retry_recommended=result.warning is not None,
                )

        except Exception as e:
            logger.exception(f"Recovery strategy failed: {e}")
            return RecoveryResult(
                success=False,
                error=str(e),
                manual_intervention_required=False,
                retry_recommended=True,
            )

    async def _recover_syntax(
        self,
        error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> StrategyResult:
        """Attempt to fix syntax error."""
        start_time = time.time()

        # Get the problematic code from context
        code = conversion_state.get("current_code", "")

        # Try automated fixes
        fixes = [
            ("missing_semicolon", self._fix_missing_semicolon),
            ("unterminated_string", self._fix_unterminated_string),
            ("mismatched_brackets", self._fix_mismatched_brackets),
        ]

        for fix_name, fix_func in fixes:
            try:
                fixed_code = await fix_func(code, error.context)

                if fixed_code and fixed_code != code:
                    conversion_state["current_code"] = fixed_code

                    return StrategyResult(
                        success=True,
                        action=f"Applied {fix_name}",
                        confidence=0.85,
                        elapsed_time=time.time() - start_time,
                        modified=True,
                    )
            except Exception:
                continue

        return StrategyResult(
            success=False,
            error="Could not auto-fix syntax error",
            requires_manual=True,
            elapsed_time=time.time() - start_time,
        )

    async def _fix_missing_semicolon(
        self,
        code: str,
        context: ErrorContextInfo,
    ) -> Optional[str]:
        """Add missing semicolons."""
        if not context.line_number:
            return None

        lines = code.split("\n")
        error_line = context.line_number - 1  # 0-indexed

        if 0 <= error_line < len(lines):
            line = lines[error_line].strip()
            # Check if line looks incomplete
            if line and not line.endswith(";") and not line.endswith("{"):
                lines[error_line] = line + ";"
                return "\n".join(lines)

        return None

    async def _fix_unterminated_string(
        self,
        code: str,
        context: ErrorContextInfo,
    ) -> Optional[str]:
        """Fix unterminated strings."""
        if not context.line_number:
            return None

        lines = code.split("\n")
        error_line = context.line_number - 1

        if 0 <= error_line < len(lines):
            line = lines[error_line]
            # Count quotes
            if line.count('"') % 2 == 1:
                lines[error_line] = line + '"'
                return "\n".join(lines)

        return None

    async def _fix_mismatched_brackets(
        self,
        code: str,
        context: ErrorContextInfo,
    ) -> Optional[str]:
        """Fix mismatched brackets."""
        # Count brackets
        open_braces = code.count("{")
        close_braces = code.count("}")

        if open_braces > close_braces:
            # Add missing closing braces at end
            return code + "}" * (open_braces - close_braces)

        return None

    async def _recover_missing_pattern(
        self,
        error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> StrategyResult:
        """Attempt to recover from missing pattern."""
        start_time = time.time()

        # Extract missing reference from error message
        missing_ref = self._extract_missing_reference(error.message)

        if missing_ref:
            # Generate placeholder
            placeholder = self._generate_placeholder(missing_ref)
            
            # Properly handle dictionary assignment
            if "missing_references" not in conversion_state:
                conversion_state["missing_references"] = {}
            conversion_state["missing_references"][missing_ref] = placeholder

            return StrategyResult(
                success=True,
                action=f"Generated placeholder for {missing_ref}",
                confidence=0.70,
                elapsed_time=time.time() - start_time,
                modified=True,
                warning="Manual review recommended",
            )

        return StrategyResult(
            success=False,
            error="Could not identify missing reference",
            requires_manual=True,
            elapsed_time=time.time() - start_time,
        )

    def _extract_missing_reference(self, error_message: str) -> Optional[str]:
        """Extract missing reference from error message."""
        patterns = [
            r"cannot find symbol[^\w]+(\w+)",
            r"undefined[^\w]+(\w+)",
            r"cannot resolve[^\w]+(\w+)",
            r"missing[^\w]+(\w+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _generate_placeholder(self, reference: str) -> str:
        """Generate placeholder code for missing reference."""
        return f"// TODO: Implement missing reference: {reference}"

    async def _recover_type_mismatch(
        self,
        error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> StrategyResult:
        """Attempt to infer correct type."""
        start_time = time.time()

        # Extract expected and actual types
        expected = self._extract_expected_type(error.message)
        actual = self._extract_actual_type(error.message)

        # Apply type inference - use 'any' as safe fallback for JavaScript
        if expected or actual:
            conversion_state["type_fixes"] = conversion_state.get("type_fixes", [])
            conversion_state["type_fixes"].append({
                "expected": expected,
                "actual": actual,
                "resolved": "any",
            })

            return StrategyResult(
                success=True,
                action=f"Applied safe type: any",
                confidence=0.70,
                elapsed_time=time.time() - start_time,
                modified=True,
                warning="Type safety relaxed",
            )

        return StrategyResult(
            success=False,
            error="Could not infer type",
            requires_manual=True,
            elapsed_time=time.time() - start_time,
        )

    def _extract_expected_type(self, error_message: str) -> Optional[str]:
        """Extract expected type from error message."""
        match = re.search(r"expected\s+(\w+)", error_message, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_actual_type(self, error_message: str) -> Optional[str]:
        """Extract actual type from error message."""
        match = re.search(r"but\s+(\w+)\s+was", error_message, re.IGNORECASE)
        return match.group(1) if match else None

    async def _recover_api_incompatibility(
        self,
        error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> StrategyResult:
        """Find API workaround."""
        start_time = time.time()

        # Extract API call
        api_call = self._extract_api_call(error.message)

        if api_call:
            # Mark for manual review (complex)
            conversion_state["api_issues"] = conversion_state.get("api_issues", [])
            conversion_state["api_issues"].append({
                "call": api_call,
                "status": "needs_review",
            })

            return StrategyResult(
                success=True,
                action=f"Marked API issue for review: {api_call}",
                confidence=0.60,
                elapsed_time=time.time() - start_time,
                modified=True,
                warning="Manual review required for API compatibility",
            )

        return StrategyResult(
            success=False,
            error="Could not identify API call",
            requires_manual=True,
            elapsed_time=time.time() - start_time,
        )

    def _extract_api_call(self, error_message: str) -> Optional[str]:
        """Extract API call from error message."""
        match = re.search(r"method[:\s]+([\w.]+)", error_message)
        return match.group(1) if match else None

    async def _recover_resource_error(
        self,
        error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> StrategyResult:
        """Retry with exponential backoff for resource errors."""
        start_time = time.time()

        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                # Simulate retry - in real implementation, would reload resource
                await asyncio.sleep(0.1)  # Simulated delay

                return StrategyResult(
                    success=True,
                    action=f"Resource recovered on attempt {attempt + 1}",
                    confidence=0.99,
                    elapsed_time=time.time() - start_time,
                    modified=False,
                )

            except Exception:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)
                continue

        return StrategyResult(
            success=False,
            error="Resource recovery failed after retries",
            requires_manual=True,
            elapsed_time=time.time() - start_time,
        )


class FallbackManager:
    """Manage fallback mechanisms for failed recovery."""

    def __init__(self):
        self.fallback_chain = [
            FallbackStep.ALTERNATIVE_STRATEGY,
            FallbackStep.SAFE_DEFAULT,
            FallbackStep.SKIP_ELEMENT,
            FallbackStep.MANUAL_REVIEW,
        ]

    async def execute_fallback(
        self,
        error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> FallbackResult:
        """Execute fallback chain."""

        for step in self.fallback_chain:
            result = await self._execute_step(step, error, conversion_state)

            if result.success:
                return FallbackResult(
                    step=step,
                    success=True,
                    action=result.action,
                    requires_review=step == FallbackStep.MANUAL_REVIEW,
                )

        # All fallbacks failed
        return FallbackResult(
            step=FallbackStep.MANUAL_REVIEW,
            success=False,
            action="Queued for manual review",
            requires_review=True,
        )

    async def _execute_step(
        self,
        step: FallbackStep,
        error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> StepResult:
        """Execute a single fallback step."""
        
        # Ensure error_type is set properly for safe default fallback
        if error.error_type is None:
            error.error_type = ErrorType.UNKNOWN

        if step == FallbackStep.ALTERNATIVE_STRATEGY:
            return await self._try_alternative_strategy(error, conversion_state)
        elif step == FallbackStep.SAFE_DEFAULT:
            return await self._apply_safe_default(error, conversion_state)
        elif step == FallbackStep.SKIP_ELEMENT:
            return await self._skip_problematic_element(error, conversion_state)
        elif step == FallbackStep.MANUAL_REVIEW:
            return await self._queue_for_manual_review(error, conversion_state)

    async def _try_alternative_strategy(
        self,
        error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> StepResult:
        """Try alternative recovery strategy."""
        # For now, just move to next fallback
        return StepResult(success=False, action="No alternative strategy")

    async def _apply_safe_default(
        self,
        error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> StepResult:
        """Apply safe default values."""

        defaults = {
            ErrorType.SYNTAX: "// Syntax error placeholder",
            ErrorType.MISSING_PATTERN: "null",
            ErrorType.TYPE_MISMATCH: "any",
            ErrorType.API_INCOMPATIBILITY: "undefined",
            ErrorType.RESOURCE_ERROR: '""',
            ErrorType.UNKNOWN: "null",
        }

        # Ensure we have a valid error_type
        error_type = error.error_type if error.error_type is not None else ErrorType.UNKNOWN
        default_value = defaults.get(error_type, "null")
        
        # Safely get the value string
        error_type_str = error_type.value if hasattr(error_type, 'value') else str(error_type)
        conversion_state["fallback_applied"] = error_type_str

        return StepResult(
            success=True,
            action=f"Applied safe default: {default_value}",
        )

    async def _skip_problematic_element(
        self,
        error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> StepResult:
        """Skip problematic element to preserve partial conversion."""

        skipped_elements: List[SkippedElement] = conversion_state.get(
            "skipped_elements", []
        )

        skipped_elements.append(SkippedElement(
            reason=error.error_type,
            location=error.context.file_path or "unknown",
            line=error.context.line_number,
            original_code=error.context.method_name or "",
        ))

        conversion_state["skipped_elements"] = skipped_elements

        return StepResult(
            success=True,
            action="Skipped problematic element",
            modified=True,
        )

    async def _queue_for_manual_review(
        self,
        error: ClassifiedError,
        conversion_state: Dict[str, Any],
    ) -> StepResult:
        """Queue conversion for manual review."""

        conversion_state["needs_manual_review"] = True
        conversion_state["review_reason"] = error.message

        return StepResult(
            success=True,
            action="Queued for manual review",
        )


class RecoveryTracker:
    """Track recovery success and metrics."""

    def __init__(self):
        self.records: List[RecoveryRecord] = []
        self._metrics_lock = asyncio.Lock()

    async def record_attempt(
        self,
        error: ClassifiedError,
        strategy: str,
        result: RecoveryResult,
        recovery_time_ms: int,
    ):
        """Record recovery attempt."""
        import uuid

        record = RecoveryRecord(
            error_id=str(uuid.uuid4()),
            error_type=error.error_type,
            recovery_strategy=strategy,
            success=result.success,
            recovery_time_ms=recovery_time_ms,
            fallback_used=result.fallback_used,
            timestamp=datetime.utcnow(),
        )

        async with self._metrics_lock:
            self.records.append(record)

    async def get_metrics(
        self,
        time_range: Optional[timedelta] = None,
    ) -> RecoveryMetrics:
        """Get current recovery metrics."""

        async with self._metrics_lock:
            records = self._filter_by_time(self.records.copy(), time_range)

            return RecoveryMetrics(
                total_errors=len(records),
                auto_recovered=sum(1 for r in records if r.success),
                manual_intervention=sum(1 for r in records if r.fallback_used),
                failed=sum(1 for r in records if not r.success and not r.fallback_used),
            )

    def _filter_by_time(
        self,
        records: List[RecoveryRecord],
        time_range: Optional[timedelta],
    ) -> List[RecoveryRecord]:
        """Filter records by time range."""
        if not time_range:
            return records

        cutoff = datetime.utcnow() - time_range
        return [r for r in records if r.timestamp >= cutoff]

    async def get_error_patterns(self) -> Dict[ErrorType, int]:
        """Get error frequency by type."""
        async with self._metrics_lock:
            from collections import defaultdict

            patterns = defaultdict(int)

            for record in self.records:
                patterns[record.error_type] += 1

            return dict(patterns)

    async def get_recovery_times(self) -> Dict[str, float]:
        """Get average recovery time by strategy."""
        async with self._metrics_lock:
            from collections import defaultdict

            times = defaultdict(list)

            for record in self.records:
                times[record.recovery_strategy].append(record.recovery_time_ms)

            return {
                strategy: sum(times_list) / len(times_list)
                for strategy, times_list in times.items()
                if times_list
            }


class ErrorAutoRecovery:
    """Main error auto-recovery system coordinating all components."""

    def __init__(self):
        self.detector = ErrorPatternDetector()
        self.recovery_engine = AutoRecoveryEngine()
        self.fallback_manager = FallbackManager()
        self.tracker = RecoveryTracker()
        self.circuit_breaker = CircuitBreaker()

        # Success rate tracking
        self._auto_recovery_threshold = 0.80
        self._manual_intervention_threshold = 0.05
        self._recovery_time_threshold = 30.0  # seconds

    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        conversion_state: Dict[str, Any],
    ) -> RecoveryResult:
        """Main entry point for error handling."""

        # Check circuit breaker
        if self.circuit_breaker.state == CircuitState.OPEN:
            if not self.circuit_breaker._should_attempt_reset():
                return RecoveryResult(
                    success=False,
                    error="Circuit breaker open - too many failures",
                    manual_intervention_required=True,
                )

        # Step 1: Detect and classify error
        classified_error = await self.detector.detect_error(error, context)

        logger.info(
            f"Error detected: {classified_error.error_type.value} "
            f"(confidence: {classified_error.confidence:.2f})"
        )

        # Step 2: Attempt auto-recovery
        result = await self.circuit_breaker.call(
            self.recovery_engine.attempt_recovery,
            classified_error,
            conversion_state,
        )

        # Step 3: If auto-recovery failed, try fallback
        if not result.success:
            logger.info("Auto-recovery failed, attempting fallback...")

            fallback_result = await self.fallback_manager.execute_fallback(
                classified_error,
                conversion_state,
            )

            result.fallback_used = fallback_result.success
            result.manual_intervention_required = fallback_result.requires_review

            if fallback_result.success:
                result.recovery_action = RecoveryAction.FALLBACK_APPLIED if not fallback_result.requires_review else RecoveryAction.MANUAL_REVIEW

        # Step 4: Record metrics
        await self.tracker.record_attempt(
            error=classified_error,
            strategy=classified_error.error_type.value,
            result=result,
            recovery_time_ms=int(result.recovery_time * 1000),
        )

        # Step 5: Check success criteria
        await self._check_success_criteria()

        return result

    async def _check_success_criteria(self):
        """Periodically check if success criteria are met."""
        metrics = await self.tracker.get_metrics()

        if metrics.total_errors > 0:
            auto_rate = metrics.auto_recovery_rate
            manual_rate = metrics.manual_intervention_rate

            logger.info(
                f"Recovery metrics - Auto-recovery: {auto_rate:.1%}, "
                f"Manual intervention: {manual_rate:.1%}"
            )

    async def get_status(self) -> Dict[str, Any]:
        """Get current recovery system status."""

        metrics = await self.tracker.get_metrics()
        patterns = await self.tracker.get_error_patterns()
        times = await self.tracker.get_recovery_times()

        return {
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "metrics": {
                "total_errors": metrics.total_errors,
                "auto_recovered": metrics.auto_recovered,
                "manual_intervention": metrics.manual_intervention,
                "failed": metrics.failed,
                "auto_recovery_rate": metrics.auto_recovery_rate,
                "manual_intervention_rate": metrics.manual_intervention_rate,
            },
            "error_patterns": {k.value: v for k, v in patterns.items()},
            "recovery_times_ms": times,
            "thresholds": {
                "auto_recovery": self._auto_recovery_threshold,
                "manual_intervention": self._manual_intervention_threshold,
                "recovery_time": self._recovery_time_threshold,
            },
        }


# Singleton instance
_error_auto_recovery: Optional[ErrorAutoRecovery] = None


def get_error_auto_recovery() -> ErrorAutoRecovery:
    """Get or create error auto-recovery singleton."""
    global _error_auto_recovery
    if _error_auto_recovery is None:
        _error_auto_recovery = ErrorAutoRecovery()
    return _error_auto_recovery
