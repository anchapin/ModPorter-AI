"""
Tests for retry module - retry logic with exponential backoff.
Covers: retry.py
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from services.retry import (
    RetryConfig,
    calculate_delay,
    is_retryable,
    categorize_error,
    retry_async,
    retry_sync,
    with_retry,
    with_retry_sync,
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
)


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_default_config(self):
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_config(self):
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_custom_exceptions(self):
        custom_retryable = (ValueError,)
        custom_non_retryable = (TypeError,)
        config = RetryConfig(
            retryable_exceptions=custom_retryable,
            non_retryable_exceptions=custom_non_retryable,
        )
        assert config.retryable_exceptions == custom_retryable
        assert config.non_retryable_exceptions == custom_non_retryable


class TestCalculateDelay:
    """Test calculate_delay function."""

    def test_exponential_backoff_without_jitter(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        # Attempt 1: 1.0 * 2^0 = 1.0
        assert calculate_delay(1, config) == 1.0
        # Attempt 2: 1.0 * 2^1 = 2.0
        assert calculate_delay(2, config) == 2.0
        # Attempt 3: 1.0 * 2^2 = 4.0
        assert calculate_delay(3, config) == 4.0

    def test_max_delay_cap(self):
        config = RetryConfig(base_delay=10.0, max_delay=5.0, exponential_base=2.0, jitter=False)
        # Should be capped at max_delay
        assert calculate_delay(3, config) == 5.0

    def test_jitter_variation(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=True)
        delays = [calculate_delay(1, config) for _ in range(10)]
        # With jitter, delays should vary (between 0.5 and 1.5)
        assert min(delays) >= 0.4
        assert max(delays) <= 1.6


class TestIsRetryable:
    """Test is_retryable function."""

    def test_retryable_error_returns_true(self):
        config = RetryConfig()
        assert is_retryable(NetworkError("test"), config) is True

    def test_non_retryable_error_returns_false(self):
        config = RetryConfig()
        assert is_retryable(LogicError("test"), config) is False

    def test_value_error_is_non_retryable(self):
        config = RetryConfig()
        assert is_retryable(ValueError("test"), config) is False

    def test_connection_error_is_retryable(self):
        config = RetryConfig()
        assert is_retryable(ConnectionError("test"), config) is True

    def test_unknown_error_defaults_to_retryable(self):
        config = RetryConfig()
        assert is_retryable(RuntimeError("test"), config) is True


class TestCategorizeError:
    """Test categorize_error function."""

    def test_parse_error(self):
        assert categorize_error(ParseError("parse failed")) == "parse_error"

    def test_asset_error(self):
        assert categorize_error(AssetError("asset missing")) == "asset_error"

    def test_logic_error(self):
        assert categorize_error(LogicError("logic invalid")) == "logic_error"

    def test_package_error(self):
        assert categorize_error(PackageError("packaging failed")) == "package_error"

    def test_validation_error(self):
        assert categorize_error(ValidationError("invalid input")) == "validation_error"

    def test_network_error(self):
        assert categorize_error(NetworkError("connection refused")) == "network_error"

    def test_rate_limit_error(self):
        assert categorize_error(RateLimitError("rate limit exceeded")) == "rate_limit_error"

    def test_timeout_error(self):
        assert categorize_error(TimeoutError("operation timed out")) == "timeout_error"

    def test_unknown_error(self):
        assert categorize_error(RuntimeError("unexpected")) == "unknown_error"

    def test_error_message_pattern_matching(self):
        # Test message-based categorization for custom errors
        error = RuntimeError("parse error in file")
        assert categorize_error(error) == "parse_error"


class TestRetryAsync:
    """Test retry_async function."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        async def successful_func():
            return "success"

        result = await retry_async(successful_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure_then_success(self):
        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise NetworkError("temporary failure")
            return "success"

        result = await retry_async(flaky_func, config=RetryConfig(max_attempts=3))
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exhaust_all_retries(self):
        async def always_fail():
            raise NetworkError("always fails")

        with pytest.raises(NetworkError):
            await retry_async(always_fail, config=RetryConfig(max_attempts=2))

    @pytest.mark.asyncio
    async def test_non_retryable_error_raises_immediately(self):
        async def non_retryable_func():
            raise LogicError("cannot retry")

        with pytest.raises(LogicError):
            await retry_async(non_retryable_func)

    @pytest.mark.asyncio
    async def test_on_retry_callback(self):
        retry_calls = []

        def on_retry(error, attempt):
            retry_calls.append((error, attempt))

        async def flaky_func():
            if len(retry_calls) < 2:
                raise NetworkError("fail")
            return "success"

        await retry_async(flaky_func, config=RetryConfig(max_attempts=3), on_retry=on_retry)
        assert len(retry_calls) == 2

    @pytest.mark.asyncio
    async def test_with_kwargs(self):
        async def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = await retry_async(
            func_with_args,
            "hello",
            "world",
            c="test",
            config=RetryConfig(max_attempts=1),
        )
        assert result == "hello-world-test"


class TestRetrySync:
    """Test retry_sync function."""

    def test_successful_first_attempt(self):
        def successful_func():
            return "success"

        result = retry_sync(successful_func)
        assert result == "success"

    def test_retry_on_transient_failure_then_success(self):
        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise NetworkError("temporary failure")
            return "success"

        result = retry_sync(flaky_func, config=RetryConfig(max_attempts=3))
        assert result == "success"
        assert call_count == 2

    def test_exhaust_all_retries(self):
        def always_fail():
            raise NetworkError("always fails")

        with pytest.raises(NetworkError):
            retry_sync(always_fail, config=RetryConfig(max_attempts=2))

    def test_non_retryable_error_raises_immediately(self):
        def non_retryable_func():
            raise LogicError("cannot retry")

        with pytest.raises(LogicError):
            retry_sync(non_retryable_func)

    def test_on_retry_callback(self):
        retry_calls = []

        def on_retry(error, attempt):
            retry_calls.append((error, attempt))

        def flaky_func():
            if len(retry_calls) < 2:
                raise NetworkError("fail")
            return "success"

        retry_sync(flaky_func, config=RetryConfig(max_attempts=3), on_retry=on_retry)
        assert len(retry_calls) == 2


class TestWithRetryDecorator:
    """Test with_retry and with_retry_sync decorators."""

    @pytest.mark.asyncio
    async def test_with_retry_async_decorator(self):
        call_count = 0

        @with_retry(RetryConfig(max_attempts=3, base_delay=0.1))
        async def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise NetworkError("fail")
            return "success"

        result = await decorated_func()
        assert result == "success"
        assert call_count == 2

    def test_with_retry_sync_decorator(self):
        call_count = 0

        @with_retry_sync(RetryConfig(max_attempts=3, base_delay=0.1))
        def decorated_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise NetworkError("fail")
            return "success"

        result = decorated_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_name(self):
        @with_retry()
        async def my_function():
            return "result"

        assert my_function.__name__ == "my_function"


class TestErrorClasses:
    """Test custom error classes."""

    def test_retryable_error_inheritance(self):
        assert issubclass(RetryableError, Exception)
        assert issubclass(ParseError, RetryableError)
        assert issubclass(AssetError, RetryableError)
        assert issubclass(NetworkError, RetryableError)
        assert issubclass(RateLimitError, RetryableError)
        assert issubclass(TimeoutError, RetryableError)

    def test_non_retryable_error_inheritance(self):
        assert issubclass(NonRetryableError, Exception)
        assert issubclass(LogicError, NonRetryableError)
        assert issubclass(ValidationError, NonRetryableError)