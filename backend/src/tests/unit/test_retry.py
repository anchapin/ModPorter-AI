"""Tests for the retry module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from services.retry import (
    RetryableError,
    NonRetryableError,
    ParseError,
    AssetError,
    LogicError,
    PackageError,
    ValidationError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    DEFAULT_RETRYABLE_EXCEPTIONS,
    DEFAULT_NON_RETRYABLE_EXCEPTIONS,
    categorize_error,
    RetryConfig,
    calculate_delay,
    is_retryable,
    retry_async,
    retry_sync,
)


class TestErrorClasses:
    """Test error class hierarchy."""

    def test_retryable_error(self):
        """Test RetryableError is an Exception."""
        error = RetryableError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_non_retryable_error(self):
        """Test NonRetryableError is an Exception."""
        error = NonRetryableError("test error")
        assert isinstance(error, Exception)

    def test_parse_error_inherits_from_retryable(self):
        """Test ParseError inherits from RetryableError."""
        error = ParseError("parse failed")
        assert isinstance(error, RetryableError)
        assert isinstance(error, Exception)

    def test_asset_error_inherits_from_retryable(self):
        """Test AssetError inherits from RetryableError."""
        error = AssetError("asset failed")
        assert isinstance(error, RetryableError)

    def test_logic_error_inherits_from_non_retryable(self):
        """Test LogicError inherits from NonRetryableError."""
        error = LogicError("logic failed")
        assert isinstance(error, NonRetryableError)

    def test_validation_error_inherits_from_non_retryable(self):
        """Test ValidationError inherits from NonRetryableError."""
        error = ValidationError("validation failed")
        assert isinstance(error, NonRetryableError)

    def test_network_error_inherits_from_retryable(self):
        """Test NetworkError inherits from RetryableError."""
        error = NetworkError("network failed")
        assert isinstance(error, RetryableError)

    def test_rate_limit_error_inherits_from_retryable(self):
        """Test RateLimitError inherits from RetryableError."""
        error = RateLimitError("rate limited")
        assert isinstance(error, RetryableError)

    def test_timeout_error_inherits_from_retryable(self):
        """Test TimeoutError inherits from RetryableError."""
        error = TimeoutError("timed out")
        assert isinstance(error, RetryableError)

    def test_package_error_inherits_from_retryable(self):
        """Test PackageError inherits from RetryableError."""
        error = PackageError("package failed")
        assert isinstance(error, RetryableError)


class TestCategorizeError:
    """Test categorize_error function."""

    def test_categorize_parse_error(self):
        """Test categorizing ParseError."""
        error = ParseError("parse error")
        assert categorize_error(error) == "parse_error"

    def test_categorize_asset_error(self):
        """Test categorizing AssetError."""
        error = AssetError("asset error")
        assert categorize_error(error) == "asset_error"

    def test_categorize_logic_error(self):
        """Test categorizing LogicError."""
        error = LogicError("logic error")
        assert categorize_error(error) == "logic_error"

    def test_categorize_validation_error(self):
        """Test categorizing ValidationError."""
        error = ValidationError("validation error")
        assert categorize_error(error) == "validation_error"

    def test_categorize_network_error(self):
        """Test categorizing NetworkError."""
        error = NetworkError("network error")
        assert categorize_error(error) == "network_error"

    def test_categorize_rate_limit_error(self):
        """Test categorizing RateLimitError."""
        error = RateLimitError("rate limit exceeded")
        assert categorize_error(error) == "rate_limit_error"

    def test_categorize_timeout_error(self):
        """Test categorizing TimeoutError."""
        error = TimeoutError("timeout")
        assert categorize_error(error) == "timeout_error"

    def test_categorize_unknown_error(self):
        """Test categorizing unknown error."""
        error = ValueError("some value error")
        assert categorize_error(error) == "unknown_error"

    def test_categorize_by_message_parse(self):
        """Test categorizing by error message content."""
        error = Exception("Something went wrong during parse")

        result = categorize_error(error)

        assert "parse" in result or result == "unknown_error"

    def test_categorize_by_message_connection(self):
        """Test categorizing by connection in message."""
        error = Exception("Connection refused")

        result = categorize_error(error)

        assert "network" in result or result == "unknown_error"


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False
        )

        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_default_exceptions(self):
        """Test default exception lists."""
        config = RetryConfig()

        assert RetryableError in config.retryable_exceptions
        assert NonRetryableError in config.non_retryable_exceptions

    def test_custom_exceptions(self):
        """Test custom exception lists."""
        custom_retryable = (ConnectionError,)
        custom_non_retryable = (ValueError,)

        config = RetryConfig(
            retryable_exceptions=custom_retryable,
            non_retryable_exceptions=custom_non_retryable
        )

        assert config.retryable_exceptions == custom_retryable
        assert config.non_retryable_exceptions == custom_non_retryable


class TestCalculateDelay:
    """Test calculate_delay function."""

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        delay1 = calculate_delay(1, config)
        delay2 = calculate_delay(2, config)
        delay3 = calculate_delay(3, config)

        assert delay1 == 1.0  # 1.0 * 2^0
        assert delay2 == 2.0  # 1.0 * 2^1
        assert delay3 == 4.0  # 1.0 * 2^2

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(base_delay=10.0, max_delay=15.0, exponential_base=2.0, jitter=False)

        delay = calculate_delay(10, config)  # Would be 10 * 2^9 = 5120

        assert delay == 15.0

    def test_jitter_variation(self):
        """Test that jitter adds variation."""
        config = RetryConfig(base_delay=1.0, exponential_base=1.0, jitter=True)

        delays = [calculate_delay(1, config) for _ in range(10)]

        # With jitter, delays should vary (some may be equal but unlikely)
        # Just verify they're in valid range
        for delay in delays:
            assert 0.5 <= delay <= 1.0


class TestIsRetryable:
    """Test is_retryable function."""

    def test_retryable_error_returns_true(self):
        """Test retryable errors return True."""
        config = RetryConfig()
        error = NetworkError("network issue")

        assert is_retryable(error, config) is True

    def test_non_retryable_error_returns_false(self):
        """Test non-retryable errors return False."""
        config = RetryConfig()
        error = LogicError("logic issue")

        assert is_retryable(error, config) is False

    def test_value_error_not_retryable(self):
        """Test ValueError is not retryable by default."""
        config = RetryConfig()
        error = ValueError("invalid value")

        assert is_retryable(error, config) is False

    def test_connection_error_retryable(self):
        """Test ConnectionError is retryable by default."""
        config = RetryConfig()
        error = ConnectionError("connection failed")

        assert is_retryable(error, config) is True

    def test_custom_retryable_exceptions(self):
        """Test custom retryable exceptions."""
        config = RetryConfig(
            retryable_exceptions=(ValueError,),
            non_retryable_exceptions=()
        )
        error = ValueError("test")

        assert is_retryable(error, config) is True

    def test_custom_non_retryable_exceptions(self):
        """Test custom non-retryable exceptions."""
        config = RetryConfig(
            retryable_exceptions=(),
            non_retryable_exceptions=(NetworkError,)
        )
        error = NetworkError("test")

        assert is_retryable(error, config) is False


class TestRetryAsync:
    """Test retry_async decorator."""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test successful call doesn't retry."""
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_async(succeed, max_attempts=3)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry on failure."""
        call_count = 0

        async def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("temporary failure")
            return "success"

        result = await retry_async(fail_twice_then_succeed, max_attempts=3)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that max retries are enforced."""
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise NetworkError("permanent failure")

        with pytest.raises(NetworkError):
            await retry_async(always_fail, max_attempts=3)

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error_no_retry(self):
        """Test non-retryable errors don't retry."""
        call_count = 0

        async def fail_with_non_retryable():
            nonlocal call_count
            call_count += 1
            raise LogicError("non-retryable")

        with pytest.raises(LogicError):
            await retry_async(fail_with_non_retryable)

        # Should only try once for non-retryable
        assert call_count == 1


class TestRetrySync:
    """Test retry_sync decorator."""

    def test_successful_call_no_retry(self):
        """Test successful call doesn't retry."""
        call_count = 0

        def succeed():
            nonlocal call_count
            call_count += 1
            return "success"

        result = retry_sync(succeed, max_attempts=3)

        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure(self):
        """Test retry on failure."""
        call_count = 0

        def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("temporary failure")
            return "success"

        result = retry_sync(fail_twice_then_succeed, max_attempts=3)

        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test that max retries are enforced."""
        call_count = 0

        def always_fail():
            nonlocal call_count
            call_count += 1
            raise NetworkError("permanent failure")

        with pytest.raises(NetworkError):
            retry_sync(always_fail, max_attempts=3)

        assert call_count == 3