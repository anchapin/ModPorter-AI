"""
Tests for error sanitization - ensuring sensitive details don't leak to clients.
Issue #842: Remove exception details from HTTP error responses
"""

import os
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.services.error_handlers import (
    ModPorterException,
    ConversionException,
    ValidationException,
    create_error_response,
    modporter_exception_handler,
    http_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock(spec=Request)
    request.url.path = "/api/test"
    request.method = "POST"
    return request


class TestErrorResponseSanitization:
    """Test that error responses sanitize sensitive information."""

    def test_modporter_exception_no_details_in_production(self, mock_request):
        """ModPorter exceptions should not include details in production."""
        # Setup: ensure DEBUG_MODE is False
        with patch.dict(os.environ, {"DEBUG": "false"}):
            # Reload module to pick up environment change
            import src.services.error_handlers as eh
            
            exc = ModPorterException(
                message="Database connection failed",
                user_message="An error occurred",
                details={"host": "db.internal", "port": 5432}
            )
            
            response = eh.create_error_response(exc, mock_request)
            
            # User message should be present but not the details
            assert response.user_message == "An error occurred"
            assert response.details == {}  # No internal details exposed
            assert "db.internal" not in str(response.details)
            assert "5432" not in str(response.details)

    def test_modporter_exception_with_details_in_debug(self, mock_request):
        """ModPorter exceptions should include details in DEBUG mode."""
        with patch.dict(os.environ, {"DEBUG": "true"}):
            import importlib
            import src.services.error_handlers as eh
            importlib.reload(eh)
            
            exc = eh.ModPorterException(
                message="Database connection failed",
                user_message="An error occurred",
                details={"host": "db.internal", "port": 5432}
            )
            
            response = eh.create_error_response(exc, mock_request)
            
            # In debug mode, details should be included
            assert response.details == {"host": "db.internal", "port": 5432}

    def test_http_exception_sanitized_in_production(self, mock_request):
        """HTTP exception details should be sanitized in production."""
        with patch.dict(os.environ, {"DEBUG": "false"}):
            import importlib
            import src.services.error_handlers as eh
            importlib.reload(eh)
            
            exc = HTTPException(
                status_code=500,
                detail="Database query failed: connection timeout"
            )
            
            response = eh.create_error_response(exc, mock_request)
            
            # Details should not include status code in production
            assert response.details == {}

    def test_validation_error_sanitized_in_production(self, mock_request):
        """Validation errors should not expose error details in production."""
        with patch.dict(os.environ, {"DEBUG": "false"}):
            import importlib
            import src.services.error_handlers as eh
            importlib.reload(eh)
            
            # Create a mock RequestValidationError instead
            validation_error = RequestValidationError([])
            response = eh.create_error_response(validation_error, mock_request)
            
            # Generic message without error details
            assert response.user_message == "Invalid request data. Please check your input."
            assert response.details == {}  # No error details exposed in production

    def test_traceback_never_in_production(self, mock_request):
        """Tracebacks should NEVER be included in production responses."""
        with patch.dict(os.environ, {"DEBUG": "false"}):
            import importlib
            import src.services.error_handlers as eh
            importlib.reload(eh)
            
            exc = Exception("Something went wrong")
            
            # Even if include_traceback=True, it shouldn't appear in production
            response = eh.create_error_response(exc, mock_request, include_traceback=True)
            
            assert "traceback" not in response.details
            assert "Traceback" not in str(response.details)

    def test_traceback_in_debug_only(self, mock_request):
        """Tracebacks should only appear in DEBUG mode."""
        with patch.dict(os.environ, {"DEBUG": "true"}):
            import importlib
            import src.services.error_handlers as eh
            importlib.reload(eh)
            
            try:
                raise ValueError("Something went wrong internally")
            except ValueError as exc:
                response = eh.create_error_response(exc, mock_request, include_traceback=True)
                
                assert "traceback" in response.details
                assert "ValueError" in response.details["traceback"]


class TestGenericExceptionHandler:
    """Test that the generic exception handler logs but doesn't expose details."""

    @pytest.mark.asyncio
    async def test_generic_exception_logged_fully(self, mock_request):
        """Generic exceptions should be fully logged server-side."""
        exc = Exception("Database connection timeout: host=db.internal port=5432")
        
        with patch.dict(os.environ, {"DEBUG": "false"}):
            import importlib
            import src.services.error_handlers as eh
            importlib.reload(eh)
            
            with patch.object(eh.logger, 'error') as mock_logger_error:
                await eh.generic_exception_handler(mock_request, exc)
                
                # Logger should have recorded the full exception
                mock_logger_error.assert_called_once()
                args, kwargs = mock_logger_error.call_args
                assert "Database connection timeout" in str(args)
                assert kwargs.get('exc_info') == True

    @pytest.mark.asyncio
    async def test_generic_exception_response_sanitized(self, mock_request):
        """Generic exception response should not expose internal details."""
        exc = Exception("Database error: Invalid credentials on db.internal:5432")
        
        with patch.dict(os.environ, {"DEBUG": "false"}):
            import importlib
            import src.services.error_handlers as eh
            importlib.reload(eh)
            
            with patch.object(eh.logger, 'error'):  # Suppress log output
                response = await eh.generic_exception_handler(mock_request, exc)
            
            # Response content should not contain sensitive details
            content = response.body.decode() if hasattr(response.body, 'decode') else str(response.body)
            assert "db.internal" not in content
            assert "5432" not in content
            assert "Invalid credentials" not in content
            assert "db.internal" not in content


class TestConversionException:
    """Test conversion error handling."""

    def test_conversion_exception_user_message_safe(self, mock_request):
        """Conversion exceptions should have safe user messages."""
        exc = ConversionException(
            message="Failed to parse YAML: invalid syntax at line 42",
            user_message="Conversion failed. Please check your mod file."
        )
        
        response = create_error_response(exc, mock_request)
        
        assert response.user_message == "Conversion failed. Please check your mod file."
        assert "YAML" not in response.user_message
        assert "line 42" not in response.user_message


class TestHTTPExceptionMessages:
    """Test that HTTPException details are safe."""

    def test_safe_error_messages_preserved(self, mock_request):
        """Safe, generic error messages should be preserved."""
        exc = HTTPException(
            status_code=400,
            detail="Invalid request format"
        )
        
        response = create_error_response(exc, mock_request)
        
        # Generic message is safe and should be included
        assert response.user_message == "Invalid request format"

    def test_sensitive_error_messages_sanitized(self):
        """Test that actual API handlers sanitize sensitive messages."""
        # This is tested in test_api_endpoints.py
        pass


class TestCorrelationID:
    """Test that correlation IDs are preserved for debugging."""

    def test_error_response_includes_correlation_id(self, mock_request):
        """Error responses should include correlation ID for tracing."""
        exc = Exception("Test error")
        response = create_error_response(exc, mock_request)
        
        assert response.correlation_id is not None
        assert len(response.correlation_id) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
