"""
Unit tests for error recovery utility.
"""

import pytest
from utils.error_recovery import (
    ErrorRecoverySystem,
    RecoveryStrategy,
    CircuitBreaker,
    get_recovery_system,
)


class TestErrorRecovery:
    """Test error recovery functionality."""

    @pytest.fixture
    def recovery_system(self):
        """Create ErrorRecoverySystem instance."""
        return ErrorRecoverySystem()

    def test_recovery_system_initialization(self, recovery_system):
        """Test ErrorRecoverySystem initializes properly."""
        assert hasattr(recovery_system, 'circuit_breakers')
        assert hasattr(recovery_system, 'recovery_strategies')

    def test_recovery_strategy_is_dataclass(self):
        """Test RecoveryStrategy is a dataclass with retry config."""
        assert hasattr(RecoveryStrategy, 'max_retries')
        assert hasattr(RecoveryStrategy, 'base_delay')
        assert hasattr(RecoveryStrategy, 'max_delay')

    def test_circuit_breaker_exists(self):
        """Test CircuitBreaker class exists."""
        assert CircuitBreaker is not None

    def test_get_recovery_system_returns_instance(self):
        """Test get_recovery_system returns ErrorRecoverySystem."""
        result = get_recovery_system()
        assert isinstance(result, ErrorRecoverySystem)


class TestRecoveryStrategyConfig:
    """Test RecoveryStrategy configuration."""

    def test_retry_strategy_exists(self):
        """Test pre-defined RETRY_IMMEDIATELY strategy exists."""
        from utils.error_recovery import RETRY_IMMEDIATELY
        assert RETRY_IMMEDIATELY is not None
        assert RETRY_IMMEDIATELY.name == "retry_immediately"
        assert RETRY_IMMEDIATELY.max_retries == 5

    def test_recovery_strategy_dataclass_fields(self):
        """Test RecoveryStrategy dataclass has expected fields."""
        strategy = RecoveryStrategy(name="test")
        assert hasattr(strategy, 'name')
        assert hasattr(strategy, 'max_retries')
        assert hasattr(strategy, 'base_delay')
        assert hasattr(strategy, 'max_delay')
        assert hasattr(strategy, 'backoff_factor')
        assert hasattr(strategy, 'jitter')

    def test_get_delay_method(self):
        """Test get_delay method calculates exponential backoff."""
        from utils.error_recovery import RETRY_IMMEDIATELY
        delay = RETRY_IMMEDIATELY.get_delay(0)
        assert delay > 0
        assert delay <= RETRY_IMMEDIATELY.max_delay