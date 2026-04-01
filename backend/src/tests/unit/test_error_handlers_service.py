"""
Unit tests for error_handlers service.

Tests custom exceptions and error handling utilities.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request, status
from fastapi.responses import JSONResponse
from services.error_handlers import (
    is_debug_mode,
    ErrorResponse,
    ModPorterException,
    ConversionException,
    FileProcessingException,
    ValidationException,
    NotFoundException,
    RateLimitException,
    ParseError,
    AssetError,
    LogicError,
    PackageError,
    _categorize_error,
    create_error_response,
    register_exception_handlers,
    verify_exception_handlers,
)


class TestIsDebugMode:
    def test_is_debug_mode_default(self):
        with patch.dict('os.environ', {}, clear=True):
            assert is_debug_mode() is False

    def test_is_debug_mode_true(self):
        with patch.dict('os.environ', {'DEBUG': 'true'}):
            assert is_debug_mode() is True


class TestErrorResponse:
    def test_error_response_init(self):
        response = ErrorResponse(
            error_id="123",
            error_type="test_error",
            error_category="test",
            message="Test message",
            user_message="User message",
            timestamp="2024-01-01T00:00:00Z"
        )
        assert response.error_id == "123"
        assert response.message == "Test message"

    def test_error_response_to_dict(self):
        response = ErrorResponse(
            error_id="123",
            error_type="test",
            error_category="test",
            message="msg",
            user_message="user",
            timestamp="now"
        )
        data = response.model_dump()
        assert "error_id" in data


class TestCustomExceptions:
    def test_mod_porter_exception(self):
        exc = ModPorterException("Test error", error_type="test_error")
        assert str(exc) == "Test error"
        assert exc.error_type == "test_error"

    def test_conversion_exception(self):
        exc = ConversionException("Conversion failed")
        assert isinstance(exc, ModPorterException)

    def test_file_processing_exception(self):
        exc = FileProcessingException("File not found")
        assert "File not found" in str(exc)

    def test_validation_exception(self):
        exc = ValidationException("Invalid input")
        assert isinstance(exc, ModPorterException)

    def test_not_found_exception(self):
        exc = NotFoundException("Not found", resource_id="123")
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_rate_limit_exception(self):
        exc = RateLimitException("Too many requests", retry_after=60)
        assert exc.status_code == 429
        assert exc.details.get("retry_after") == 60

    def test_parse_error(self):
        exc = ParseError("Failed to parse JSON")
        assert isinstance(exc, ModPorterException)

    def test_asset_error(self):
        exc = AssetError("Invalid asset")
        assert isinstance(exc, ModPorterException)

    def test_logic_error(self):
        exc = LogicError("Invalid state")
        assert isinstance(exc, ModPorterException)

    def test_package_error(self):
        exc = PackageError("Packaging failed")
        assert isinstance(exc, ModPorterException)


class TestCategorizeError:
    def test_categorize_validation_error(self):
        error = ValidationException("Invalid")
        category = _categorize_error(error)
        assert category is not None

    def test_categorize_generic_exception(self):
        error = ValueError("Some error")
        category = _categorize_error(error)
        assert category is not None


class TestCreateErrorResponse:
    @pytest.mark.xfail(reason="Flaky - has singleton pollution in parallel test runs")
    def test_create_error_response_from_exception(self):
        exc = ModPorterException("Test error")
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/test"
        mock_request.method = "GET"

        response = create_error_response(exc, mock_request)
        assert isinstance(response, ErrorResponse)


class TestRegisterExceptionHandlers:
    def test_register_exception_handlers(self):
        mock_app = MagicMock()
        register_exception_handlers(mock_app)
        assert mock_app.add_exception_handler.call_count >= 2


class TestVerifyExceptionHandlers:
    def test_verify_exception_handlers(self):
        mock_app = MagicMock()
        result = verify_exception_handlers(mock_app)
        assert isinstance(result, dict)
