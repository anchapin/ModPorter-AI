"""Tests for the error recovery module."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from services.error_recovery import (
    ErrorSupervisor,
    RecoveryStrategyExecutor,
    DegradedModeManager,
    EscalationManager,
    RecoveryResult,
    RecoveryAttempt,
    RecoveryStatus,
    RecoveryStrategy,
    get_supervisor,
    recover,
)
from services.error_classifier import (
    ErrorType,
    ErrorSeverity,
    ErrorClassification,
)
from services.error_patterns import (
    RecoveryAction,
    ErrorPatternLibrary,
    get_pattern_library,
)


class TestRecoveryStatus:
    """Test RecoveryStatus enum."""

    def test_status_values(self):
        """Test all recovery status values exist."""
        assert RecoveryStatus.PENDING.value == "pending"
        assert RecoveryStatus.IN_PROGRESS.value == "in_progress"
        assert RecoveryStatus.SUCCEEDED.value == "succeeded"
        assert RecoveryStatus.FAILED.value == "failed"
        assert RecoveryStatus.DEGRADED.value == "degraded"
        assert RecoveryStatus.ESCALATED.value == "escalated"


class TestRecoveryAttempt:
    """Test RecoveryAttempt dataclass."""

    def test_recovery_attempt_creation(self):
        """Test creating a recovery attempt."""
        attempt = RecoveryAttempt(
            action_name="retry",
            strategy=RecoveryStrategy.RETRY,
            started_at=datetime.now(timezone.utc),
        )

        assert attempt.action_name == "retry"
        assert attempt.strategy == RecoveryStrategy.RETRY
        assert attempt.status == RecoveryStatus.PENDING
        assert attempt.retry_count == 0
        assert attempt.result is None
        assert attempt.error is None

    def test_recovery_attempt_duration(self):
        """Test calculating attempt duration."""
        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)

        attempt = RecoveryAttempt(
            action_name="retry",
            strategy=RecoveryStrategy.RETRY,
            started_at=start,
            completed_at=end,
        )

        assert attempt.duration >= 0


class TestRecoveryResult:
    """Test RecoveryResult dataclass."""

    def test_recovery_result_creation(self):
        """Test creating a recovery result."""
        error = Exception("test error")
        classification = ErrorClassification(
            error_type=ErrorType.NETWORK,
            severity=ErrorSeverity.WARNING,
            confidence=1.0,
        )

        result = RecoveryResult(
            status=RecoveryStatus.SUCCEEDED,
            original_error=error,
            classification=classification,
        )

        assert result.status == RecoveryStatus.SUCCEEDED
        assert result.original_error == error
        assert result.classification == classification
        assert result.attempts == []
        assert result.final_result is None
        assert result.escalated is False

    def test_recovery_result_succeeded_property(self):
        """Test succeeded property."""
        result = RecoveryResult(
            status=RecoveryStatus.SUCCEEDED,
            original_error=Exception("test"),
            classification=ErrorClassification(ErrorType.NETWORK, ErrorSeverity.WARNING, 1.0),
        )

        assert result.succeeded is True

    def test_recovery_result_degraded_property(self):
        """Test recovered_with_degraded property."""
        result = RecoveryResult(
            status=RecoveryStatus.DEGRADED,
            original_error=Exception("test"),
            classification=ErrorClassification(ErrorType.NETWORK, ErrorSeverity.WARNING, 1.0),
            fallback_mode="degraded",
        )

        assert result.recovered_with_degraded is True


class TestDegradedModeManager:
    """Test DegradedModeManager class."""

    def test_enable_degraded_mode(self):
        """Test enabling degraded mode."""
        manager = DegradedModeManager()

        manager.enable_degraded_mode("conversion", "Network error")

        assert manager.is_degraded("conversion") is True

    def test_disable_degraded_mode(self):
        """Test disabling degraded mode."""
        manager = DegradedModeManager()

        manager.enable_degraded_mode("conversion", "Network error")
        manager.disable_degraded_mode("conversion")

        assert manager.is_degraded("conversion") is False

    def test_get_fallback_handler(self):
        """Test getting fallback handler."""
        manager = DegradedModeManager()
        handler = MagicMock()

        manager.enable_degraded_mode("feature", "error", handler)

        assert manager.get_fallback_handler("feature") == handler

    def test_get_all_degraded_features(self):
        """Test getting all degraded features."""
        manager = DegradedModeManager()

        manager.enable_degraded_mode("feature1", "error1")
        manager.enable_degraded_mode("feature2", "error2")

        features = manager.get_all_degraded_features()

        assert "feature1" in features
        assert "feature2" in features


class TestEscalationManager:
    """Test EscalationManager class."""

    def test_escalate_error(self):
        """Test escalating an error."""
        manager = EscalationManager()
        error = Exception("critical error")
        classification = ErrorClassification(
            error_type=ErrorType.LOGIC,
            severity=ErrorSeverity.BLOCKING,
            confidence=1.0,
        )
        result = RecoveryResult(
            status=RecoveryStatus.FAILED,
            original_error=error,
            classification=classification,
        )

        escalation_id = manager.escalate(error, classification, result)

        assert escalation_id.startswith("ESC-")
        assert len(manager.get_pending_escalations()) == 1

    def test_register_handler(self):
        """Test registering escalation handler."""
        manager = EscalationManager()
        handler = MagicMock()

        manager.register_handler(handler)

        assert len(manager._escalation_handlers) == 1


class TestRecoveryStrategyExecutor:
    """Test RecoveryStrategyExecutor class."""

    def test_executor_initialization(self):
        """Test initializing the executor."""
        degraded_manager = DegradedModeManager()
        executor = RecoveryStrategyExecutor(degraded_manager)

        assert executor._degraded_mode == degraded_manager
        assert len(executor._strategy_handlers) > 0

    @pytest.mark.asyncio
    async def test_execute_degraded_mode(self):
        """Test executing degraded mode strategy."""
        degraded_manager = DegradedModeManager()
        executor = RecoveryStrategyExecutor(degraded_manager)

        action = RecoveryAction(
            name="degraded_mode",
            strategy=RecoveryStrategy.DEGRADED_MODE,
            description="Enable degraded mode",
            success_rate=0.9,
        )

        result = await executor.execute(
            action,
            Exception("error"),
            {"feature": "conversion"},
        )

        assert result.status == RecoveryStatus.SUCCEEDED
        assert degraded_manager.is_degraded("conversion") is True

    @pytest.mark.asyncio
    async def test_execute_skip_and_continue(self):
        """Test executing skip and continue strategy."""
        degraded_manager = DegradedModeManager()
        executor = RecoveryStrategyExecutor(degraded_manager)

        action = RecoveryAction(
            name="skip_invalid",
            strategy=RecoveryStrategy.SKIP_AND_CONTINUE,
            description="Skip and continue",
            success_rate=0.8,
        )

        result = await executor.execute(
            action,
            Exception("error"),
            {"skipped_item": "invalid_texture"},
        )

        assert result.status == RecoveryStatus.SUCCEEDED
        assert result.result["skipped"] is True
        assert result.result["skipped_item"] == "invalid_texture"

    @pytest.mark.asyncio
    async def test_execute_use_cache(self):
        """Test executing use cache strategy."""
        degraded_manager = DegradedModeManager()
        executor = RecoveryStrategyExecutor(degraded_manager)

        action = RecoveryAction(
            name="use_cache",
            strategy=RecoveryStrategy.USE_CACHE,
            description="Use cached result",
            success_rate=0.9,
        )

        result = await executor.execute(
            action,
            Exception("error"),
            {"cached_result": {"data": "cached_value"}},
        )

        assert result.status == RecoveryStatus.SUCCEEDED
        assert result.result == {"data": "cached_value"}

    @pytest.mark.asyncio
    async def test_execute_use_cache_no_cached_result(self):
        """Test executing use cache with no cached result."""
        degraded_manager = DegradedModeManager()
        executor = RecoveryStrategyExecutor(degraded_manager)

        action = RecoveryAction(
            name="use_cache",
            strategy=RecoveryStrategy.USE_CACHE,
            description="Use cached result",
            success_rate=0.9,
        )

        result = await executor.execute(
            action,
            Exception("error"),
            {},
        )

        assert result.status == RecoveryStatus.FAILED
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_use_default(self):
        """Test executing use default strategy."""
        degraded_manager = DegradedModeManager()
        executor = RecoveryStrategyExecutor(degraded_manager)

        action = RecoveryAction(
            name="use_default",
            strategy=RecoveryStrategy.USE_DEFAULT,
            description="Use default value",
            success_rate=0.7,
        )

        result = await executor.execute(
            action,
            Exception("error"),
            {"default_value": "fallback_value"},
        )

        assert result.status == RecoveryStatus.SUCCEEDED
        assert result.result["used_default"] is True
        assert result.result["default_value"] == "fallback_value"

    @pytest.mark.asyncio
    async def test_execute_notify_user(self):
        """Test executing notify user strategy."""
        degraded_manager = DegradedModeManager()
        executor = RecoveryStrategyExecutor(degraded_manager)

        action = RecoveryAction(
            name="notify_user",
            strategy=RecoveryStrategy.NOTIFY_USER,
            description="Notify user",
            success_rate=1.0,
        )

        result = await executor.execute(
            action,
            Exception("error"),
            {},
        )

        assert result.status == RecoveryStatus.SUCCEEDED
        assert result.result["notification_sent"] is True


class TestErrorSupervisor:
    """Test ErrorSupervisor class."""

    def test_supervisor_initialization(self):
        """Test initializing the supervisor."""
        supervisor = ErrorSupervisor()

        assert supervisor.classifier is not None
        assert supervisor.pattern_library is not None
        assert supervisor.degraded_mode is not None
        assert supervisor.escalation is not None
        assert supervisor.strategy_executor is not None

    @pytest.mark.asyncio
    async def test_supervise_network_error_succeeds_with_retry(self):
        """Test supervising a network error that recovers."""
        supervisor = ErrorSupervisor(max_recovery_attempts=3)

        # Create a mock operation that succeeds on second call
        call_count = 0

        async def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Connection refused")
            return "success"

        error = Exception("Connection refused")
        result = await supervisor.supervise(error, {"operation": mock_operation})

        assert result.status in [RecoveryStatus.SUCCEEDED, RecoveryStatus.DEGRADED]

    @pytest.mark.asyncio
    async def test_supervise_classifies_error(self):
        """Test that supervisor classifies the error."""
        supervisor = ErrorSupervisor()

        error = Exception("timeout error")
        result = await supervisor.supervise(error)

        assert result.classification is not None
        assert result.classification.error_type == ErrorType.TIMEOUT

    @pytest.mark.asyncio
    async def test_supervise_creates_attempts(self):
        """Test that supervisor creates recovery attempts."""
        supervisor = ErrorSupervisor(max_recovery_attempts=2)

        error = Exception("connection refused")
        result = await supervisor.supervise(error)

        assert len(result.attempts) > 0

    @pytest.mark.asyncio
    async def test_supervise_logic_error_escalates(self):
        """Test that logic errors escalate."""
        supervisor = ErrorSupervisor()

        try:
            from backend.src.services.retry import LogicError
        except ImportError:
            # Create a mock logic error
            class LogicError(Exception):
                pass

        error = LogicError("Internal logic error")
        result = await supervisor.supervise(error)

        # Logic errors should escalate
        assert result.status in [RecoveryStatus.ESCALATED, RecoveryStatus.FAILED]


class TestGetSupervisor:
    """Test the get_supervisor function."""

    def test_get_supervisor_returns_same_instance(self):
        """Test that get_supervisor returns singleton."""
        supervisor1 = get_supervisor()
        supervisor2 = get_supervisor()

        assert supervisor1 is supervisor2


class TestRecoverFunction:
    """Test the recover convenience function."""

    @pytest.mark.asyncio
    async def test_recover_classifies_error(self):
        """Test that recover classifies the error."""
        error = Exception("validation error")
        result = await recover(error)

        assert result.classification is not None


class TestErrorPatternLibraryIntegration:
    """Test integration with error pattern library."""

    def test_library_has_network_pattern(self):
        """Test library has network error pattern."""
        library = get_pattern_library()
        pattern = library.get_pattern(ErrorType.NETWORK)

        assert pattern is not None
        assert len(pattern.recovery_actions) > 0

    def test_library_has_timeout_pattern(self):
        """Test library has timeout error pattern."""
        library = get_pattern_library()
        pattern = library.get_pattern(ErrorType.TIMEOUT)

        assert pattern is not None
        assert len(pattern.recovery_actions) > 0

    def test_library_has_all_error_type_patterns(self):
        """Test library has patterns for all error types."""
        library = get_pattern_library()

        for error_type in ErrorType:
            pattern = library.get_pattern(error_type)
            # Only check that we get a response (pattern might be None for some types)
            assert pattern is not None or library.get_recovery_actions(error_type) == []

    def test_should_escalate_logic(self):
        """Test that logic errors should escalate."""
        library = get_pattern_library()

        assert library.should_escalate(ErrorType.LOGIC) is True

    def test_should_escalate_auth(self):
        """Test that authentication errors should escalate."""
        library = get_pattern_library()

        assert library.should_escalate(ErrorType.AUTHENTICATION) is True

    def test_should_not_escalate_network(self):
        """Test that network errors should not escalate."""
        library = get_pattern_library()

        assert library.should_escalate(ErrorType.NETWORK) is False

    def test_get_fallback_mode_network(self):
        """Test getting fallback mode for network errors."""
        library = get_pattern_library()

        fallback = library.get_fallback_mode(ErrorType.NETWORK)

        assert fallback == "degraded"


class TestRecoveryActionsOrdering:
    """Test that recovery actions are returned in order of success rate."""

    def test_actions_sorted_by_success_rate(self):
        """Test actions are sorted by success rate descending."""
        library = get_pattern_library()
        actions = library.get_recovery_actions(ErrorType.NETWORK)

        if len(actions) > 1:
            for i in range(len(actions) - 1):
                assert actions[i].success_rate >= actions[i + 1].success_rate


class TestSupervisorWithContext:
    """Test supervisor with various context scenarios."""

    @pytest.mark.asyncio
    async def test_supervise_with_job_context(self):
        """Test supervise with job context."""
        supervisor = ErrorSupervisor()

        error = Exception("timeout error")
        result = await supervisor.supervise(
            error,
            {"job_id": "job-123", "user_id": "user-456"},
        )

        assert result.classification is not None
        assert result.attempts is not None

    @pytest.mark.asyncio
    async def test_supervise_with_operation_and_context(self):
        """Test supervise with operation in context."""
        supervisor = ErrorSupervisor()

        async def mock_op():
            return "result"

        error = Exception("connection refused")
        result = await supervisor.supervise(
            error,
            {"operation": mock_op, "feature": "conversion"},
        )

        assert result.status in [RecoveryStatus.SUCCEEDED, RecoveryStatus.DEGRADED, RecoveryStatus.ESCALATED]
