"""
Tests for Error Handler Service - src/services/error_handler.py
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
import time

from errors import (
    ConversionError,
    AIEngineUnavailableError,
    ConversionTimeoutError,
    InvalidInputError,
    ModelUnavailableError,
    retry_with_backoff,
    categorize_error,
    get_user_friendly_error,
    ErrorHandler,
    get_error_handler,
)


class TestConversionErrors:
    """Tests for conversion error classes."""

    def test_conversion_error_default(self):
        """Test ConversionError with defaults."""
        error = ConversionError("Test error")
        assert error.message == "Test error"
        assert error.retryable is False
        assert str(error) == "Test error"

    def test_conversion_error_retryable(self):
        """Test ConversionError with retryable=True."""
        error = ConversionError("Test error", retryable=True)
        assert error.retryable is True

    def test_ai_engine_unavailable_error(self):
        """Test AIEngineUnavailableError."""
        error = AIEngineUnavailableError()
        assert "AI Engine unavailable" in str(error)
        assert error.retryable is True

    def test_ai_engine_unavailable_error_custom_message(self):
        """Test AIEngineUnavailableError with custom message."""
        error = AIEngineUnavailableError("Custom message")
        assert "Custom message" in str(error)

    def test_conversion_timeout_error(self):
        """Test ConversionTimeoutError."""
        error = ConversionTimeoutError()
        assert "timed out" in str(error).lower()
        assert error.retryable is True

    def test_conversion_timeout_error_custom_message(self):
        """Test ConversionTimeoutError with custom message."""
        error = ConversionTimeoutError("Custom timeout")
        assert "Custom timeout" in str(error)

    def test_invalid_input_error(self):
        """Test InvalidInputError."""
        error = InvalidInputError("Invalid data")
        assert "Invalid data" in str(error)
        assert error.retryable is False

    def test_model_unavailable_error(self):
        """Test ModelUnavailableError."""
        error = ModelUnavailableError()
        assert "Model unavailable" in str(error)
        assert error.retryable is True

    def test_error_inheritance(self):
        """Test error class inheritance."""
        error = ConversionError("test")
        assert isinstance(error, Exception)
        assert isinstance(error, ConversionError)


class TestRetryWithBackoff:
    """Tests for retry_with_backoff decorator."""

    @pytest.mark.asyncio
    async def test_successful_first_try(self):
        """Test function succeeds on first try."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_retryable_error(self):
        """Test function retries on retryable error."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def retryable_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise AIEngineUnavailableError("Try again")
            return "success"

        result = await retryable_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test max retries exceeded."""

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def always_fails():
            raise AIEngineUnavailableError("Always fails")

        with pytest.raises(AIEngineUnavailableError):
            await always_fails()

    @pytest.mark.asyncio
    async def test_non_retryable_error_raises_immediately(self):
        """Test non-retryable error raises immediately."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        async def non_retryable_func():
            nonlocal call_count
            call_count += 1
            raise InvalidInputError("Not retryable")

        with pytest.raises(InvalidInputError):
            await non_retryable_func()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_unexpected_error_wrapped(self):
        """Test unexpected error is wrapped."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        async def unexpected_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Unexpected")

        with pytest.raises(ConversionError) as exc_info:
            await unexpected_error_func()

        assert "Unexpected" in str(exc_info.value.message)
        assert exc_info.value.retryable is False

    @pytest.mark.asyncio
    async def test_retry_with_conversion_timeout(self):
        """Test retry with ConversionTimeoutError."""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def timeout_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConversionTimeoutError()
            return "success"

        result = await timeout_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_with_model_unavailable(self):
        """Test retry with ModelUnavailableError."""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        async def model_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ModelUnavailableError()
            return "success"

        result = await model_func()
        assert result == "success"


class TestCategorizeError:
    """Tests for categorize_error function."""

    def test_categorize_invalid_input_error(self):
        """Test categorizing InvalidInputError."""
        error = InvalidInputError("Invalid mod file")
        result = categorize_error(error)

        assert result["category"] == "invalid_input"
        assert result["retryable"] is False
        assert "mod file" in result["user_message"]

    def test_categorize_ai_engine_error(self):
        """Test categorizing AIEngineUnavailableError."""
        error = AIEngineUnavailableError("Engine down")
        result = categorize_error(error)

        assert result["category"] == "service_unavailable"
        assert result["retryable"] is True
        assert "temporarily unavailable" in result["user_message"]

    def test_categorize_model_unavailable_error(self):
        """Test categorizing ModelUnavailableError."""
        error = ModelUnavailableError("Model not found")
        result = categorize_error(error)

        assert result["category"] == "service_unavailable"
        assert result["retryable"] is True

    def test_categorize_timeout_error(self):
        """Test categorizing ConversionTimeoutError."""
        error = ConversionTimeoutError()
        result = categorize_error(error)

        assert result["category"] == "timeout"
        assert result["retryable"] is True

    def test_categorize_generic_conversion_error(self):
        """Test categorizing generic ConversionError."""
        error = ConversionError("Some error", retryable=True)
        result = categorize_error(error)

        assert result["category"] == "conversion_error"
        assert result["retryable"] is True

    def test_categorize_generic_conversion_error_not_retryable(self):
        """Test categorizing non-retryable ConversionError."""
        error = ConversionError("Some error", retryable=False)
        result = categorize_error(error)

        assert result["category"] == "conversion_error"
        assert result["retryable"] is False

    def test_categorize_unknown_error(self):
        """Test categorizing unknown error."""
        error = ValueError("Unknown error")
        result = categorize_error(error)

        assert result["category"] == "unknown"
        assert result["retryable"] is False
        assert "unexpected" in result["user_message"].lower()


class TestGetUserFriendlyError:
    """Tests for get_user_friendly_error function."""

    def test_invalid_input_message(self):
        """Test user-friendly message for invalid input."""
        error = InvalidInputError("Test")
        message = get_user_friendly_error(error)

        assert "mod file" in message.lower() or "check" in message.lower()

    def test_service_unavailable_message(self):
        """Test user-friendly message for service unavailable."""
        error = AIEngineUnavailableError()
        message = get_user_friendly_error(error)

        assert "unavailable" in message.lower() or "try again" in message.lower()

    def test_timeout_message(self):
        """Test user-friendly message for timeout."""
        error = ConversionTimeoutError()
        message = get_user_friendly_error(error)

        assert "long" in message.lower() or "timeout" in message.lower()

    def test_unknown_error_message(self):
        """Test user-friendly message for unknown error."""
        error = RuntimeError("Unknown")
        message = get_user_friendly_error(error)

        assert "unexpected" in message.lower() or "error" in message.lower()


class TestErrorHandler:
    """Tests for ErrorHandler class."""

    @pytest.fixture
    def handler(self):
        """Create an error handler instance."""
        return ErrorHandler()

    def test_init(self, handler):
        """Test error handler initialization."""
        assert handler._error_counts == {}
        assert handler._last_error_time == {}

    def test_record_error(self, handler):
        """Test recording an error."""
        error = ValueError("Test error")
        handler.record_error(error, job_id="job-123")

        assert "ValueError" in handler._error_counts
        assert handler._error_counts["ValueError"] == 1

    def test_record_error_multiple(self, handler):
        """Test recording multiple errors."""
        for _ in range(5):
            handler.record_error(ValueError("Test"))

        assert handler._error_counts["ValueError"] == 5

    def test_record_error_different_types(self, handler):
        """Test recording different error types."""
        handler.record_error(ValueError("Error 1"))
        handler.record_error(TypeError("Error 2"))
        handler.record_error(RuntimeError("Error 3"))

        assert len(handler._error_counts) == 3

    def test_record_error_with_job_id(self, handler):
        """Test recording error with job ID."""
        error = Exception("Test")
        handler.record_error(error, job_id="job-456")
        # Should not raise

    def test_get_error_stats(self, handler):
        """Test getting error statistics."""
        handler.record_error(ValueError("Error 1"))
        handler.record_error(ValueError("Error 2"))
        handler.record_error(TypeError("Error 3"))

        stats = handler.get_error_stats()

        assert "error_counts" in stats
        assert "last_error_times" in stats
        assert "total_errors" in stats
        assert stats["total_errors"] == 3

    def test_should_alert_below_threshold(self, handler):
        """Test alert check below threshold."""
        handler._error_counts["TestError"] = 5
        handler._last_error_time["TestError"] = time.time()

        result = handler.should_alert("TestError", threshold=10, window_seconds=300)
        assert result is False

    def test_should_alert_above_threshold(self, handler):
        """Test alert check above threshold."""
        handler._error_counts["TestError"] = 15
        handler._last_error_time["TestError"] = time.time()

        result = handler.should_alert("TestError", threshold=10, window_seconds=300)
        assert result is True

    def test_should_alert_outside_window(self, handler):
        """Test alert check outside time window."""
        handler._error_counts["TestError"] = 15
        handler._last_error_time["TestError"] = time.time() - 400  # Older than window

        result = handler.should_alert("TestError", threshold=10, window_seconds=300)
        assert result is False

    def test_should_alert_no_errors(self, handler):
        """Test alert check with no errors recorded."""
        result = handler.should_alert("UnknownError", threshold=10, window_seconds=300)
        assert result is False


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_error_handler_singleton(self):
        """Test getting singleton instance."""
        with patch("services.error_handler._error_handler", None):
            handler1 = get_error_handler()
            handler2 = get_error_handler()
            assert handler1 is handler2

    def test_get_error_handler_returns_same_instance(self):
        """Test singleton returns same instance."""
        with patch("services.error_handler._error_handler", None):
            handler1 = get_error_handler()
            handler2 = get_error_handler()
            assert handler1 is handler2


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_retry_with_zero_max_retries(self):
        """Test retry with zero max retries."""
        call_count = 0

        @retry_with_backoff(max_retries=0, base_delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            raise AIEngineUnavailableError()

        with pytest.raises(AIEngineUnavailableError):
            await func()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self):
        """Test exponential backoff is applied."""
        import time

        call_times = []

        @retry_with_backoff(max_retries=2, base_delay=0.05, exponential_base=2.0)
        async def func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise AIEngineUnavailableError()
            return "success"

        start = time.time()
        await func()

        # Check that delays increase exponentially
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            # Second delay should be roughly double the first
            assert delay2 > delay1

    def test_error_handler_with_empty_stats(self):
        """Test error handler with no errors."""
        handler = ErrorHandler()
        stats = handler.get_error_stats()

        assert stats["total_errors"] == 0
        assert stats["error_counts"] == {}

    def test_categorize_error_with_none_message(self):
        """Test categorizing error with None message."""
        error = ConversionError(None)
        result = categorize_error(error)

        assert result["category"] == "conversion_error"

    @pytest.mark.asyncio
    async def test_retry_with_custom_exceptions(self):
        """Test retry with custom exception tuple."""
        call_count = 0

        class CustomRetryableError(Exception):
            pass

        @retry_with_backoff(
            max_retries=2, base_delay=0.01, retryable_exceptions=(CustomRetryableError,)
        )
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise CustomRetryableError()
            return "success"

        result = await func()
        assert result == "success"

    def test_multiple_error_handler_instances(self):
        """Test multiple error handler instances are independent."""
        handler1 = ErrorHandler()
        handler2 = ErrorHandler()

        handler1.record_error(ValueError("Error 1"))

        assert "ValueError" in handler1._error_counts
        assert "ValueError" not in handler2._error_counts
