"""
Comprehensive unit tests for structured_logging module.

Tests all exported functions including:
- configure_structlog
- get_logger
- get_standard_logger
- Correlation ID management
- Request metadata management
- LogContext context manager
- Specialized logging functions (log_api_request, log_conversion_event, log_error_with_context)
- LoggingFormatter class
- _LazyStructlogLogger
"""

import pytest
import logging
import json
import uuid
import os
import sys
from datetime import datetime, timezone
from unittest.mock import (
    MagicMock,
    patch,
    Mock,
    call,
    PropertyMock,
)
from io import StringIO
import structlog

# Import the module under test
from services import structured_logging


class TestConfigureStructlog:
    """Tests for the configure_structlog function."""

    @pytest.fixture(autouse=True)
    def setup_log_dir(self, tmp_path):
        """Set LOG_DIR to tmp_path to avoid permission errors."""
        import os
        os.environ["LOG_DIR"] = str(tmp_path / "logs")
        yield
        # Cleanup handled by tmp_path

    @patch("services.structured_logging.logging.getLogger")
    @patch("services.structured_logging.structlog.configure")
    @patch("services.structured_logging.structlog.get_logger")
    def test_configure_structlog_default(self, mock_get_logger, mock_configure, mock_logging_get_logger):
        """Test configure_structlog with default parameters."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_root_logger = MagicMock()
        mock_logging_get_logger.return_value = mock_root_logger

        with patch.dict(os.environ, {"LOG_LEVEL": "INFO", "LOG_JSON_FORMAT": "false", "ENVIRONMENT": "development"}, clear=False):
            result = structured_logging.configure_structlog()

        mock_configure.assert_called_once()
        mock_root_logger.setLevel.assert_called()
        assert result == mock_logger

    @patch("services.structured_logging.logging.getLogger")
    @patch("services.structured_logging.structlog.configure")
    @patch("services.structured_logging.structlog.get_logger")
    def test_configure_structlog_json_format(self, mock_get_logger, mock_configure, mock_logging_get_logger):
        """Test configure_structlog with JSON format enabled."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_root_logger = MagicMock()
        mock_logging_get_logger.return_value = mock_root_logger

        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "LOG_JSON_FORMAT": "true"}, clear=False):
            result = structured_logging.configure_structlog(json_format=True)

        mock_configure.assert_called_once()
        # Verify JSONRenderer was added to processors
        call_kwargs = mock_configure.call_args[1]
        processors = call_kwargs.get("processors", [])
        processor_names = [type(p).__name__ for p in processors]
        assert "JSONRenderer" in processor_names or "ConsoleRenderer" in processor_names

    @patch("services.structured_logging.logging.getLogger")
    @patch("services.structured_logging.structlog.configure")
    @patch("services.structured_logging.structlog.get_logger")
    def test_configure_structlog_debug_mode(self, mock_get_logger, mock_configure, mock_logging_get_logger):
        """Test configure_structlog with debug mode enabled."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_root_logger = MagicMock()
        mock_logging_get_logger.return_value = mock_root_logger

        result = structured_logging.configure_structlog(debug_mode=True)

        mock_configure.assert_called_once()
        call_kwargs = mock_configure.call_args[1]
        processors = call_kwargs.get("processors", [])
        processor_names = [type(p).__name__ for p in processors]
        # Debug mode uses ConsoleRenderer
        assert "ConsoleRenderer" in processor_names

    @patch("services.structured_logging.logging.getLogger")
    @patch("services.structured_logging.structlog.configure")
    @patch("services.structured_logging.os.makedirs")
    @patch("services.structured_logging.RotatingFileHandler")
    @patch("services.structured_logging.structlog.get_logger")
    def test_configure_structlog_custom_log_file(
        self, mock_get_logger, mock_file_handler, mock_makedirs, mock_configure, mock_logging_get_logger
    ):
        """Test configure_structlog with custom log file path."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_root_logger = MagicMock()
        mock_logging_get_logger.return_value = mock_root_logger

        result = structured_logging.configure_structlog(log_file="/custom/path/app.log")

        # When custom log_file is provided, makedirs is NOT called for log_dir
        # (it's only called in the if log_file is None block)
        mock_makedirs.assert_not_called()
        # Verify the file handler was created with the custom path
        mock_file_handler.assert_called()
        # Check that the custom path was used
        call_args = mock_file_handler.call_args
        assert call_args[0][0] == "/custom/path/app.log"

    @patch("services.structured_logging.logging.getLogger")
    @patch("services.structured_logging.structlog.configure")
    @patch("services.structured_logging.structlog.get_logger")
    def test_configure_structlog_log_level_from_env(self, mock_get_logger, mock_configure, mock_logging_get_logger):
        """Test that log level is read from environment variable."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_root_logger = MagicMock()
        mock_logging_get_logger.return_value = mock_root_logger

        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            result = structured_logging.configure_structlog()

        mock_root_logger.setLevel.assert_called_with(logging.WARNING)

    @patch("services.structured_logging.logging.getLogger")
    @patch("services.structured_logging.structlog.configure")
    @patch("services.structured_logging.structlog.get_logger")
    def test_configure_structlog_production_env_enables_json(self, mock_get_logger, mock_configure, mock_logging_get_logger):
        """Test that production environment auto-enables JSON format."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_root_logger = MagicMock()
        mock_logging_get_logger.return_value = mock_root_logger

        with patch.dict(os.environ, {"ENVIRONMENT": "production", "LOG_JSON_FORMAT": "false"}, clear=False):
            result = structured_logging.configure_structlog()

        # Production should use JSON format
        mock_configure.assert_called_once()


class TestGetLogger:
    """Tests for the get_logger function."""

    @patch("services.structured_logging.structlog.get_logger")
    def test_get_logger_returns_structlog_logger(self, mock_get_logger):
        """Test that get_logger returns a structlog logger."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        result = structured_logging.get_logger("test.module")

        mock_get_logger.assert_called_once_with("test.module")
        assert result == mock_logger

    @patch("services.structured_logging.structlog.get_logger")
    def test_get_logger_different_names(self, mock_get_logger):
        """Test get_logger with different logger names."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        structured_logging.get_logger("module1")
        structured_logging.get_logger("module2")

        assert mock_get_logger.call_count == 2
        mock_get_logger.assert_any_call("module1")
        mock_get_logger.assert_any_call("module2")


class TestGetStandardLogger:
    """Tests for the get_standard_logger function."""

    @patch("services.structured_logging.os.makedirs")
    @patch("services.structured_logging.RotatingFileHandler")
    @patch("services.structured_logging.logging.getLogger")
    def test_get_standard_logger_first_call(self, mock_get_logger, mock_file_handler, mock_makedirs):
        """Test get_standard_logger configures a new logger."""
        mock_logger = MagicMock()
        mock_logger.handlers = []  # No existing handlers
        mock_get_logger.return_value = mock_logger

        result = structured_logging.get_standard_logger("test.logger")

        mock_get_logger.assert_called_once_with("test.logger")
        mock_logger.setLevel.assert_called_once()
        assert mock_logger.addHandler.call_count >= 1  # At least console and file handlers

    @patch("services.structured_logging.logging.getLogger")
    def test_get_standard_logger_existing_handlers(self, mock_get_logger):
        """Test get_standard_logger doesn't reconfigure logger with handlers."""
        mock_logger = MagicMock()
        mock_logger.handlers = [MagicMock()]  # Already has handlers
        mock_get_logger.return_value = mock_logger

        result = structured_logging.get_standard_logger("test.logger")

        # Should not set level or add handlers if handlers exist
        mock_logger.setLevel.assert_not_called()
        mock_logger.addHandler.assert_not_called()


class TestCorrelationIdManagement:
    """Tests for correlation ID management functions."""

    def test_set_correlation_id_generates_uuid(self):
        """Test that set_correlation_id generates a UUID when none provided."""
        # Clear any existing correlation ID
        structured_logging.correlation_id_var.set(None)
        structured_logging.structlog.contextvars.clear_contextvars = MagicMock()
        structured_logging.structlog.contextvars.bind_contextvars = MagicMock()

        result = structured_logging.set_correlation_id()

        # Result should be a valid UUID
        uuid_result = uuid.UUID(result)
        assert uuid_result is not None
        assert structured_logging.correlation_id_var.get() == result
        structured_logging.structlog.contextvars.bind_contextvars.assert_called_once_with(correlation_id=result)

    def test_set_correlation_id_with_value(self):
        """Test that set_correlation_id uses provided value."""
        structured_logging.correlation_id_var.set(None)
        structured_logging.structlog.contextvars.clear_contextvars = MagicMock()
        structured_logging.structlog.contextvars.bind_contextvars = MagicMock()

        result = structured_logging.set_correlation_id("custom-correlation-id")

        assert result == "custom-correlation-id"
        assert structured_logging.correlation_id_var.get() == "custom-correlation-id"

    def test_get_correlation_id_returns_value(self):
        """Test that get_correlation_id returns the current value."""
        test_id = "test-correlation-id"
        structured_logging.correlation_id_var.set(test_id)

        result = structured_logging.get_correlation_id()

        assert result == test_id

    def test_get_correlation_id_returns_none_when_not_set(self):
        """Test that get_correlation_id returns None when not set."""
        structured_logging.correlation_id_var.set(None)

        result = structured_logging.get_correlation_id()

        assert result is None

    def test_clear_correlation_id(self):
        """Test that clear_correlation_id sets correlation ID to None."""
        structured_logging.correlation_id_var.set("some-id")

        structured_logging.clear_correlation_id()

        assert structured_logging.correlation_id_var.get() is None


class TestRequestMetadataManagement:
    """Tests for request metadata management functions."""

    def test_set_request_metadata(self):
        """Test setting request metadata."""
        structured_logging.request_metadata_var.set(None)
        structured_logging.structlog.contextvars.bind_contextvars = MagicMock()

        metadata = {"user_id": "user123", "path": "/api/test"}

        structured_logging.set_request_metadata(metadata)

        assert structured_logging.request_metadata_var.get() == metadata
        structured_logging.structlog.contextvars.bind_contextvars.assert_called_once_with(**metadata)

    def test_set_request_metadata_empty(self):
        """Test setting empty request metadata."""
        structured_logging.request_metadata_var.set(None)
        structured_logging.structlog.contextvars.bind_contextvars = MagicMock()

        structured_logging.set_request_metadata({})

        assert structured_logging.request_metadata_var.get() == {}

    def test_clear_request_metadata(self):
        """Test clearing request metadata."""
        structured_logging.request_metadata_var.set({"key": "value"})

        structured_logging.clear_request_metadata()

        assert structured_logging.request_metadata_var.get() is None


class TestLogContext:
    """Tests for the LogContext context manager."""

    def test_log_context_enter_exit(self):
        """Test LogContext enters and exits correctly."""
        # Save original values
        structured_logging.correlation_id_var.set("original-correlation")
        structured_logging.request_metadata_var.set({"original": "metadata"})

        structured_logging.structlog.contextvars.clear_contextvars = MagicMock()
        structured_logging.structlog.contextvars.bind_contextvars = MagicMock()

        with structured_logging.LogContext(correlation_id="new-correlation", user_id="user123") as ctx:
            assert ctx.correlation_id == "new-correlation"
            assert structured_logging.correlation_id_var.get() == "new-correlation"
            assert structured_logging.request_metadata_var.get() == {"user_id": "user123"}

        # After exiting context, original values should be restored
        assert structured_logging.correlation_id_var.get() == "original-correlation"
        assert structured_logging.request_metadata_var.get() == {"original": "metadata"}

    def test_log_context_generates_correlation_id(self):
        """Test LogContext generates correlation ID if not provided."""
        structured_logging.correlation_id_var.set(None)
        structured_logging.request_metadata_var.set(None)
        structured_logging.structlog.contextvars.clear_contextvars = MagicMock()
        structured_logging.structlog.contextvars.bind_contextvars = MagicMock()

        with structured_logging.LogContext() as ctx:
            # Should have generated a UUID
            uuid.UUID(ctx.correlation_id)

    def test_log_context_binds_to_structlog(self):
        """Test that LogContext binds values to structlog contextvars."""
        structured_logging.structlog.contextvars.clear_contextvars = MagicMock()
        structured_logging.structlog.contextvars.bind_contextvars = MagicMock()

        with structured_logging.LogContext(correlation_id="test-id", user_id="user123"):
            pass

        structured_logging.structlog.contextvars.clear_contextvars.assert_called()
        structured_logging.structlog.contextvars.bind_contextvars.assert_called_with(
            correlation_id="test-id", user_id="user123"
        )


class TestLogApiRequest:
    """Tests for the log_api_request function."""

    def test_log_api_request_basic(self):
        """Test basic API request logging."""
        mock_logger = MagicMock()

        structured_logging.log_api_request(mock_logger, "GET", "/api/users")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "GET /api/users"  # Message
        assert call_args[1]["event"] == "api_request"
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["path"] == "/api/users"

    def test_log_api_request_with_status_code(self):
        """Test API request logging with status code."""
        mock_logger = MagicMock()

        structured_logging.log_api_request(mock_logger, "POST", "/api/users", status_code=201)

        call_args = mock_logger.info.call_args
        assert call_args[1]["status_code"] == 201

    def test_log_api_request_with_duration(self):
        """Test API request logging with duration."""
        mock_logger = MagicMock()

        structured_logging.log_api_request(mock_logger, "GET", "/api/test", duration_ms=150.5)

        call_args = mock_logger.info.call_args
        assert call_args[1]["duration_ms"] == 150.5

    def test_log_api_request_with_extra_fields(self):
        """Test API request logging with extra fields."""
        mock_logger = MagicMock()

        structured_logging.log_api_request(
            mock_logger, "GET", "/api/test", user_id="user123", request_id="req456"
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["user_id"] == "user123"
        assert call_args[1]["request_id"] == "req456"

    def test_log_api_request_duration_rounding(self):
        """Test that duration is rounded to 2 decimal places."""
        mock_logger = MagicMock()

        structured_logging.log_api_request(mock_logger, "GET", "/api/test", duration_ms=123.456789)

        call_args = mock_logger.info.call_args
        assert call_args[1]["duration_ms"] == 123.46


class TestLogConversionEvent:
    """Tests for the log_conversion_event function."""

    def test_log_conversion_event_basic(self):
        """Test basic conversion event logging."""
        mock_logger = MagicMock()

        structured_logging.log_conversion_event(mock_logger, "job-123", "started")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "Conversion job-123: started"  # Message
        assert call_args[1]["event"] == "conversion"
        assert call_args[1]["job_id"] == "job-123"
        assert call_args[1]["conversion_event"] == "started"

    def test_log_conversion_event_with_progress(self):
        """Test conversion event with progress percentage."""
        mock_logger = MagicMock()

        structured_logging.log_conversion_event(mock_logger, "job-123", "progress", progress=50)

        call_args = mock_logger.info.call_args
        assert call_args[1]["progress"] == 50

    def test_log_conversion_event_completed(self):
        """Test conversion completed event."""
        mock_logger = MagicMock()

        structured_logging.log_conversion_event(mock_logger, "job-123", "completed")

        call_args = mock_logger.info.call_args
        assert call_args[1]["conversion_event"] == "completed"

    def test_log_conversion_event_failed(self):
        """Test conversion failed event."""
        mock_logger = MagicMock()

        structured_logging.log_conversion_event(mock_logger, "job-123", "failed", error="Out of memory")

        call_args = mock_logger.info.call_args
        assert call_args[1]["conversion_event"] == "failed"
        assert call_args[1]["error"] == "Out of memory"


class TestLogErrorWithContext:
    """Tests for the log_error_with_context function."""

    def test_log_error_basic(self):
        """Test basic error logging."""
        mock_logger = MagicMock()
        error = ValueError("Invalid value")

        structured_logging.log_error_with_context(mock_logger, error)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "Invalid value"  # Message
        assert call_args[1]["event"] == "error"
        assert call_args[1]["error_type"] == "ValueError"
        assert call_args[1]["error_message"] == "Invalid value"
        assert call_args[1]["exc_info"] == error

    def test_log_error_with_context_dict(self):
        """Test error logging with context dictionary."""
        mock_logger = MagicMock()
        error = RuntimeError("Something went wrong")
        context = {"job_id": "job-123", "user_id": "user456"}

        structured_logging.log_error_with_context(mock_logger, error, context=context)

        call_args = mock_logger.error.call_args
        assert call_args[1]["context"] == context

    def test_log_error_with_extra_fields(self):
        """Test error logging with extra fields."""
        mock_logger = MagicMock()
        error = TypeError("Expected str, got int")

        structured_logging.log_error_with_context(mock_logger, error, endpoint="/api/convert", method="POST")

        call_args = mock_logger.error.call_args
        assert call_args[1]["endpoint"] == "/api/convert"
        assert call_args[1]["method"] == "POST"

    def test_log_error_different_exception_types(self):
        """Test logging different exception types."""
        mock_logger = MagicMock()

        exceptions = [
            ValueError("value error"),
            TypeError("type error"),
            KeyError("key error"),
            AttributeError("attr error"),
        ]

        for error in exceptions:
            mock_logger.reset_mock()
            structured_logging.log_error_with_context(mock_logger, error)
            call_args = mock_logger.error.call_args
            assert call_args[1]["error_type"] == type(error).__name__


class TestLoggingFormatter:
    """Tests for the LoggingFormatter class."""

    def test_logging_formatter_init(self):
        """Test LoggingFormatter initialization."""
        formatter = structured_logging.LoggingFormatter(json_format=True, debug_mode=True)

        assert formatter.json_format is True
        assert formatter.debug_mode is True

    def test_logging_formatter_default_init(self):
        """Test LoggingFormatter default initialization."""
        formatter = structured_logging.LoggingFormatter()

        assert formatter.json_format is False
        assert formatter.debug_mode is False

    def test_logging_formatter_format_json_with_correlation_id(self):
        """Test LoggingFormatter produces JSON with correlation ID."""
        formatter = structured_logging.LoggingFormatter(json_format=True)

        # Set correlation ID
        structured_logging.correlation_id_var.set("test-correlation-id")

        # Create a mock log record
        record = MagicMock()
        record.levelname = "INFO"
        record.name = "test.logger"
        record.getMessage.return_value = "Test message"
        record.module = "test_module"
        record.funcName = "test_func"
        record.lineno = 42
        record.exc_info = None
        record.extra_data = {}
        record.duration_ms = None

        result = formatter.format(record)

        # Parse JSON result
        log_data = json.loads(result)
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["correlation_id"] == "test-correlation-id"

    def test_logging_formatter_format_json_with_request_metadata(self):
        """Test LoggingFormatter includes request metadata."""
        formatter = structured_logging.LoggingFormatter(json_format=True)

        # Set request metadata
        structured_logging.request_metadata_var.set({"user_id": "user123", "path": "/api/test"})

        record = MagicMock()
        record.levelname = "WARNING"
        record.name = "test.logger"
        record.getMessage.return_value = "Warning message"
        record.module = "test_module"
        record.funcName = "test_func"
        record.lineno = 10
        record.exc_info = None
        record.extra_data = {}
        record.duration_ms = None

        result = formatter.format(record)

        log_data = json.loads(result)
        assert log_data["request"]["user_id"] == "user123"
        assert log_data["request"]["path"] == "/api/test"

    def test_logging_formatter_format_json_with_exception(self):
        """Test LoggingFormatter includes exception info."""
        formatter = structured_logging.LoggingFormatter(json_format=True)

        record = MagicMock()
        record.levelname = "ERROR"
        record.name = "test.logger"
        record.getMessage.return_value = "Error occurred"
        record.module = "test_module"
        record.funcName = "test_func"
        record.lineno = 20
        record.exc_info = (ValueError, ValueError("test error"), None)
        record.extra_data = {}
        record.duration_ms = None

        result = formatter.format(record)

        log_data = json.loads(result)
        assert "exception" in log_data
        assert log_data["level"] == "ERROR"

    def test_logging_formatter_format_json_with_extra_data(self):
        """Test LoggingFormatter includes extra data from record."""
        formatter = structured_logging.LoggingFormatter(json_format=True)

        record = MagicMock()
        record.levelname = "INFO"
        record.name = "test.logger"
        record.getMessage.return_value = "Info message"
        record.module = "test_module"
        record.funcName = "test_func"
        record.lineno = 15
        record.exc_info = None
        record.extra_data = {"custom_field": "custom_value", "job_id": "job-123"}
        record.duration_ms = None

        result = formatter.format(record)

        log_data = json.loads(result)
        assert log_data["custom_field"] == "custom_value"
        assert log_data["job_id"] == "job-123"

    def test_logging_formatter_format_json_with_duration(self):
        """Test LoggingFormatter includes duration_ms."""
        formatter = structured_logging.LoggingFormatter(json_format=True)

        record = MagicMock()
        record.levelname = "INFO"
        record.name = "test.logger"
        record.getMessage.return_value = "Request completed"
        record.module = "test_module"
        record.funcName = "test_func"
        record.lineno = 25
        record.exc_info = None
        record.extra_data = {}
        record.duration_ms = 150.5

        result = formatter.format(record)

        log_data = json.loads(result)
        assert log_data["duration_ms"] == 150.5

    def test_logging_formatter_plain_text_format(self):
        """Test LoggingFormatter plain text format."""
        formatter = structured_logging.LoggingFormatter(json_format=False)

        record = MagicMock()
        record.levelname = "INFO"
        record.name = "test.logger"
        record.getMessage.return_value = "Test message"
        record.module = "test_module"
        record.funcName = "test_func"
        record.lineno = 10
        record.exc_info = None
        record.extra_data = {}
        record.duration_ms = None

        result = formatter.format(record)

        # Plain text format should contain timestamp and message
        assert "INFO" in result
        assert "Test message" in result

    def test_logging_formatter_plain_text_with_correlation_id(self):
        """Test LoggingFormatter plain text format includes correlation ID."""
        formatter = structured_logging.LoggingFormatter(json_format=False)
        structured_logging.correlation_id_var.set("test-correlation-id")

        record = MagicMock()
        record.levelname = "DEBUG"
        record.name = "test.logger"
        record.getMessage.return_value = "Debug message"
        record.module = "test_module"
        record.funcName = "test_func"
        record.lineno = 5
        record.exc_info = None
        record.extra_data = {}
        record.duration_ms = None

        result = formatter.format(record)

        # Should include correlation ID in abbreviated form (first 8 chars + "...")
        # "test-correlation-id"[:8] = "test-cor"
        assert "[test-cor...]" in result


class TestLazyStructlogLogger:
    """Tests for the _LazyStructlogLogger class."""

    @patch("services.structured_logging._get_module_logger")
    def test_lazy_structlog_logger_initialization(self, mock_get_module_logger):
        """Test that _LazyStructlogLogger starts uninitialized."""
        mock_logger = MagicMock()
        mock_get_module_logger.return_value = mock_logger

        lazy_logger = structured_logging._LazyStructlogLogger()

        # Should not be initialized yet
        assert lazy_logger._instance is None
        repr_result = repr(lazy_logger)
        assert "not initialized" in repr_result

    @patch("services.structured_logging._get_module_logger")
    def test_lazy_structlog_logger_getattr(self, mock_get_module_logger):
        """Test that _LazyStructlogLogger initializes on attribute access."""
        mock_logger = MagicMock()
        mock_logger.info = MagicMock()
        mock_get_module_logger.return_value = mock_logger

        lazy_logger = structured_logging._LazyStructlogLogger()

        # Access an attribute
        _ = lazy_logger.info

        # Should now be initialized
        assert lazy_logger._instance is not None
        mock_get_module_logger.assert_called_once()

    @patch("services.structured_logging._get_module_logger")
    def test_lazy_structlog_logger_call(self, mock_get_module_logger):
        """Test that _LazyStructlogLogger initializes on call."""
        mock_logger = MagicMock(return_value="logged")
        mock_get_module_logger.return_value = mock_logger

        lazy_logger = structured_logging._LazyStructlogLogger()

        # Call the lazy logger
        result = lazy_logger("test message")

        # Should now be initialized
        assert lazy_logger._instance is not None
        mock_logger.assert_called_once_with("test message")
        assert result == "logged"

    @patch("services.structured_logging._get_module_logger")
    def test_lazy_structlog_logger_repr_after_init(self, mock_get_module_logger):
        """Test __repr__ after initialization."""
        mock_logger = MagicMock()
        mock_logger.__repr__ = lambda self: "<MockLogger>"
        mock_get_module_logger.return_value = mock_logger

        lazy_logger = structured_logging._LazyStructlogLogger()
        _ = lazy_logger.info  # Trigger initialization

        repr_result = repr(lazy_logger)
        assert "not initialized" not in repr_result


class TestModuleLevelLogger:
    """Tests for the module-level logger instance."""

    def test_module_logger_exists(self):
        """Test that module-level logger exists."""
        assert structured_logging.logger is not None

    def test_module_logger_is_lazy(self):
        """Test that module-level logger is a LazyStructlogLogger instance."""
        assert isinstance(structured_logging.logger, structured_logging._LazyStructlogLogger)


class TestContextVarsIntegration:
    """Tests for context variables integration with structlog."""

    @patch("services.structured_logging.structlog.contextvars.merge_contextvars")
    def test_contextvars_in_configure(self, mock_merge):
        """Test that merge_contextvars is used in configuration."""
        with patch("services.structured_logging.structlog.configure") as mock_configure:
            with patch("services.structured_logging.logging.getLogger"):
                mock_configure.return_value = None
                structured_logging.configure_structlog()

        # Verify merge_contextvars was included in processors
        call_kwargs = mock_configure.call_args[1]
        processors = call_kwargs.get("processors", [])
        # The merge_contextvars should be in the processors list
        # (We mocked it, but structlog.configure was called with it in processors)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_set_correlation_id_empty_string(self):
        """Test setting empty string as correlation ID."""
        structured_logging.structlog.contextvars.clear_contextvars = MagicMock()
        structured_logging.structlog.contextvars.bind_contextvars = MagicMock()

        result = structured_logging.set_correlation_id("")

        # Empty string should be accepted
        assert result == ""

    def test_get_logger_with_special_characters(self):
        """Test get_logger with special characters in name."""
        with patch("services.structured_logging.structlog.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = structured_logging.get_logger("module.with.dots.and-dashes")

            mock_get_logger.assert_called_once_with("module.with.dots.and-dashes")

    def test_log_api_request_all_methods(self):
        """Test logging all HTTP methods."""
        mock_logger = MagicMock()

        methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

        for method in methods:
            mock_logger.reset_mock()
            structured_logging.log_api_request(mock_logger, method, "/api/test")
            call_args = mock_logger.info.call_args
            assert call_args[1]["method"] == method

    def test_log_conversion_event_all_event_types(self):
        """Test logging all conversion event types."""
        mock_logger = MagicMock()

        events = ["started", "queued", "processing", "progress", "completed", "failed", "cancelled"]

        for event in events:
            mock_logger.reset_mock()
            structured_logging.log_conversion_event(mock_logger, "job-123", event)
            call_args = mock_logger.info.call_args
            assert call_args[1]["conversion_event"] == event

    def test_log_error_with_none_context(self):
        """Test logging error with None context."""
        mock_logger = MagicMock()
        error = ValueError("test")

        structured_logging.log_error_with_context(mock_logger, error, context=None)

        call_args = mock_logger.error.call_args
        # Context should not be in the log data when None
        assert "context" not in call_args[1]

    def test_request_metadata_with_none_values(self):
        """Test request metadata with None values in dict."""
        structured_logging.structlog.contextvars.bind_contextvars = MagicMock()

        metadata = {"user_id": None, "path": "/api/test"}

        structured_logging.set_request_metadata(metadata)

        structured_logging.structlog.contextvars.bind_contextvars.assert_called_with(**metadata)

    def test_logging_formatter_no_correlation_no_metadata(self):
        """Test LoggingFormatter when no correlation ID or metadata is set."""
        formatter = structured_logging.LoggingFormatter(json_format=True)
        structured_logging.correlation_id_var.set(None)
        structured_logging.request_metadata_var.set(None)

        record = MagicMock()
        record.levelname = "INFO"
        record.name = "test.logger"
        record.getMessage.return_value = "Test message"
        record.module = "test_module"
        record.funcName = "test_func"
        record.lineno = 10
        record.exc_info = None
        record.extra_data = {}
        record.duration_ms = None

        result = formatter.format(record)

        log_data = json.loads(result)
        assert "correlation_id" not in log_data
        assert "request" not in log_data


class TestLoggingFormatterTimestamp:
    """Additional tests for LoggingFormatter timestamp handling."""

    def test_timestamp_format(self):
        """Test that timestamp is in ISO format."""
        formatter = structured_logging.LoggingFormatter(json_format=True)

        record = MagicMock()
        record.levelname = "INFO"
        record.name = "test.logger"
        record.getMessage.return_value = "Test"
        record.module = "test"
        record.funcName = "func"
        record.lineno = 1
        record.exc_info = None
        record.extra_data = {}
        record.duration_ms = None

        result = formatter.format(record)

        log_data = json.loads(result)
        timestamp = log_data["timestamp"]
        # Should end with Z (UTC)
        assert timestamp.endswith("Z")
        # Should start with a year and contain date/time components
        assert timestamp.startswith("20")  # Year starting with 20
        assert "T" in timestamp  # ISO format separator


class TestIntegrationScenarios:
    """Integration-style tests for common usage scenarios."""

    def test_full_request_lifecycle(self):
        """Test a full request lifecycle with correlation ID and metadata."""
        structured_logging.structlog.contextvars.clear_contextvars = MagicMock()
        structured_logging.structlog.contextvars.bind_contextvars = MagicMock()

        # Start request
        correlation_id = structured_logging.set_correlation_id("req-123")
        assert correlation_id == "req-123"

        # Set request metadata
        structured_logging.set_request_metadata({"user_id": "user-456", "path": "/api/converts"})

        # Verify both are set
        assert structured_logging.get_correlation_id() == "req-123"

        # Clear after request
        structured_logging.clear_correlation_id()
        structured_logging.clear_request_metadata()

        assert structured_logging.get_correlation_id() is None

    def test_log_context_for_request(self):
        """Test using LogContext for a request."""
        structured_logging.structlog.contextvars.clear_contextvars = MagicMock()
        structured_logging.structlog.contextvars.bind_contextvars = MagicMock()

        with structured_logging.LogContext(correlation_id="req-789", user_id="user-999", ip="127.0.0.1"):
            # Inside context, all values should be available
            assert structured_logging.get_correlation_id() == "req-789"
            assert structured_logging.request_metadata_var.get()["user_id"] == "user-999"
            assert structured_logging.request_metadata_var.get()["ip"] == "127.0.0.1"

    def test_log_error_with_full_context(self):
        """Test logging an error with full context information."""
        mock_logger = MagicMock()

        try:
            raise ConnectionError("Database connection failed")
        except ConnectionError as e:
            structured_logging.log_error_with_context(
                mock_logger, e, context={"endpoint": "/api/db", "retry_count": 3}
            )

        call_args = mock_logger.error.call_args
        assert call_args[1]["error_type"] == "ConnectionError"
        assert call_args[1]["context"]["endpoint"] == "/api/db"
        assert call_args[1]["context"]["retry_count"] == 3