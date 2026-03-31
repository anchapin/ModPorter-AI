"""
Unit tests for logging_middleware service.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import Request
from services.logging_middleware import LoggingMiddleware, RequestContextMiddleware


class TestLoggingMiddlewareInit:
    def test_logging_middleware_init(self):
        """Test LoggingMiddleware can be initialized."""
        mock_app = MagicMock()
        middleware = LoggingMiddleware(mock_app)
        assert middleware.app is mock_app

    def test_logging_middleware_default_exclude_paths(self):
        """Test default exclude paths are set."""
        mock_app = MagicMock()
        middleware = LoggingMiddleware(mock_app)
        assert len(middleware.exclude_paths) > 0
        assert "/health" in middleware.exclude_paths

    def test_logging_middleware_custom_exclude_paths(self):
        """Test custom exclude paths."""
        mock_app = MagicMock()
        custom = ["/admin", "/private"]
        middleware = LoggingMiddleware(mock_app, exclude_paths=custom)
        assert middleware.exclude_paths == custom


class TestLoggingMiddlewareDispatch:
    def test_middleware_has_dispatch(self):
        """Test LoggingMiddleware has dispatch method."""
        mock_app = MagicMock()
        middleware = LoggingMiddleware(mock_app)
        assert hasattr(middleware, 'dispatch')

    def test_should_exclude_path(self):
        """Test path exclusion logic."""
        mock_app = MagicMock()
        middleware = LoggingMiddleware(mock_app)
        
        assert middleware._should_exclude("/health") is True
        assert middleware._should_exclude("/api/test") is False


class TestRequestContextMiddleware:
    def test_request_context_middleware_init(self):
        """Test RequestContextMiddleware can be initialized."""
        mock_app = MagicMock()
        middleware = RequestContextMiddleware(mock_app)
        assert middleware.app is mock_app

    def test_request_context_middleware_has_dispatch(self):
        """Test RequestContextMiddleware has dispatch method."""
        mock_app = MagicMock()
        middleware = RequestContextMiddleware(mock_app)
        assert hasattr(middleware, 'dispatch')
