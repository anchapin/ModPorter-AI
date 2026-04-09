"""
Unit tests for SecurityHeadersMiddleware.

Tests the middleware that adds security headers to all HTTP responses.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from starlette.responses import Response


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware class."""

    @pytest.fixture
    def middleware(self):
        """Create a SecurityHeadersMiddleware instance with a mock app."""
        from services.security_headers import SecurityHeadersMiddleware

        mock_app = MagicMock()
        return SecurityHeadersMiddleware(app=mock_app)

    @pytest.fixture
    def mock_request(self):
        """Create a mock HTTP request."""
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "headers": [],
        }
        request = MagicMock(spec=Request)
        request.scope = mock_scope
        return request

    @pytest.mark.asyncio
    async def test_middleware_instantiation(self):
        """Test that SecurityHeadersMiddleware can be instantiated with an ASGI app."""
        from services.security_headers import SecurityHeadersMiddleware

        mock_app = MagicMock()
        middleware = SecurityHeadersMiddleware(app=mock_app)

        assert middleware.app is mock_app

    @pytest.mark.asyncio
    async def test_dispatch_method_adds_x_content_type_options(self, middleware, mock_request):
        """Test that X-Content-Type-Options header is added with value 'nosniff'."""
        # Use a real Response object so headers can be properly set
        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        # Verify call_next was called with the request
        mock_call_next.assert_called_once_with(mock_request)

        # Check that X-Content-Type-Options was set on the actual response
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_dispatch_method_adds_x_frame_options(self, middleware, mock_request):
        """Test that X-Frame-Options header is added with value 'DENY'."""
        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"

    @pytest.mark.asyncio
    async def test_dispatch_method_adds_x_xss_protection(self, middleware, mock_request):
        """Test that X-XSS-Protection header is added with value '1; mode=block'."""
        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        assert "x-xss-protection" in response.headers
        assert response.headers["x-xss-protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_dispatch_method_adds_referrer_policy(self, middleware, mock_request):
        """Test that Referrer-Policy header is added with value 'strict-origin-when-cross-origin'."""
        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        assert "referrer-policy" in response.headers
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_all_four_security_headers_added(self, middleware, mock_request):
        """Test that all four security headers are added in a single request."""
        response = Response(content=b"OK", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        # Verify all 4 security headers are present
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert "x-xss-protection" in response.headers
        assert "referrer-policy" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_returns_response(self, middleware, mock_request):
        """Test that dispatch method returns the response from call_next."""
        expected_response = Response(content=b"test response", status_code=200)
        mock_call_next = AsyncMock(return_value=expected_response)

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result is expected_response

    @pytest.mark.asyncio
    async def test_dispatch_calls_call_next(self, middleware, mock_request):
        """Test that dispatch properly calls the next middleware/endpoint."""
        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_with_different_request_methods(self, middleware):
        """Test that security headers are added for different HTTP methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

        for method in methods:
            mock_scope = {
                "type": "http",
                "method": method,
                "path": "/api/v1/test",
                "headers": [],
            }
            mock_request = MagicMock(spec=Request)
            mock_request.scope = mock_scope

            response = Response(content=b"", status_code=200)
            mock_call_next = AsyncMock(return_value=response)

            await middleware.dispatch(mock_request, mock_call_next)

            # Verify headers are set for all methods
            assert "x-content-type-options" in response.headers
            assert response.headers["x-content-type-options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_dispatch_with_different_paths(self, middleware):
        """Test that security headers are added for different request paths."""
        paths = ["/", "/api/v1/health", "/api/v1/analyze", "/static/file.js"]

        for path in paths:
            mock_scope = {
                "type": "http",
                "method": "GET",
                "path": path,
                "headers": [],
            }
            mock_request = MagicMock(spec=Request)
            mock_request.scope = mock_scope

            response = Response(content=b"", status_code=200)
            mock_call_next = AsyncMock(return_value=response)

            await middleware.dispatch(mock_request, mock_call_next)

            # Verify headers are set for all paths
            assert "x-content-type-options" in response.headers
            assert response.headers["x-content-type-options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_dispatch_with_different_status_codes(self, middleware):
        """Test that security headers are added regardless of response status code."""
        status_codes = [200, 201, 301, 400, 404, 500]

        for status_code in status_codes:
            mock_scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/v1/test",
                "headers": [],
            }
            mock_request = MagicMock(spec=Request)
            mock_request.scope = mock_scope

            response = Response(content=b"", status_code=status_code)
            mock_call_next = AsyncMock(return_value=response)

            await middleware.dispatch(mock_request, mock_call_next)

            # Verify headers are set for all status codes
            assert "x-content-type-options" in response.headers
            assert response.headers["x-content-type-options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_middleware_inherits_from_base_http_middleware(self):
        """Test that SecurityHeadersMiddleware inherits from BaseHTTPMiddleware."""
        from services.security_headers import SecurityHeadersMiddleware
        from starlette.middleware.base import BaseHTTPMiddleware

        assert issubclass(SecurityHeadersMiddleware, BaseHTTPMiddleware)


class TestSecurityHeadersEdgeCases:
    """Edge case tests for SecurityHeadersMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create a SecurityHeadersMiddleware instance."""
        from services.security_headers import SecurityHeadersMiddleware

        mock_app = MagicMock()
        return SecurityHeadersMiddleware(app=mock_app)

    @pytest.mark.asyncio
    async def test_dispatch_with_empty_request_path(self, middleware):
        """Test that middleware handles empty request path."""
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "",
            "headers": [],
        }
        mock_request = MagicMock(spec=Request)
        mock_request.scope = mock_scope

        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        # Should not raise an exception
        await middleware.dispatch(mock_request, mock_call_next)

    @pytest.mark.asyncio
    async def test_dispatch_with_request_with_query_params(self, middleware):
        """Test that middleware handles requests with query parameters."""
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/analyze?hash=abc123&version=1.0",
            "headers": [],
        }
        mock_request = MagicMock(spec=Request)
        mock_request.scope = mock_scope

        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        assert "x-content-type-options" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_with_request_with_headers(self, middleware):
        """Test that middleware works when request already has headers."""
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "headers": [
                (b"accept", b"application/json"),
                (b"authorization", b"bearer token123"),
            ],
        }
        mock_request = MagicMock(spec=Request)
        mock_request.scope = mock_scope

        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        # Security headers should still be added
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_dispatch_does_not_remove_existing_headers(self, middleware):
        """Test that middleware does not interfere with existing response headers."""
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "headers": [],
        }
        mock_request = MagicMock(spec=Request)
        mock_request.scope = mock_scope

        # Create a response that has existing headers
        response = Response(content=b"test", status_code=200)
        response.headers["Custom-Header"] = "custom-value"

        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        # Custom header should still be present
        assert "custom-header" in response.headers
        assert response.headers["custom-header"] == "custom-value"

        # Security headers should also be present
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"


class TestSecurityHeadersValues:
    """Tests to verify the exact header values set by the middleware."""

    @pytest.fixture
    def middleware(self):
        """Create a SecurityHeadersMiddleware instance."""
        from services.security_headers import SecurityHeadersMiddleware

        mock_app = MagicMock()
        return SecurityHeadersMiddleware(app=mock_app)

    @pytest.mark.asyncio
    async def test_x_content_type_options_value(self, middleware):
        """Verify X-Content-Type-Options is set to 'nosniff'."""
        mock_request = MagicMock(spec=Request)
        mock_request.scope = {"type": "http", "method": "GET", "path": "/", "headers": []}

        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["x-content-type-options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_x_frame_options_value(self, middleware):
        """Verify X-Frame-Options is set to 'DENY'."""
        mock_request = MagicMock(spec=Request)
        mock_request.scope = {"type": "http", "method": "GET", "path": "/", "headers": []}

        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["x-frame-options"] == "DENY"

    @pytest.mark.asyncio
    async def test_x_xss_protection_value(self, middleware):
        """Verify X-XSS-Protection is set to '1; mode=block'."""
        mock_request = MagicMock(spec=Request)
        mock_request.scope = {"type": "http", "method": "GET", "path": "/", "headers": []}

        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["x-xss-protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_referrer_policy_value(self, middleware):
        """Verify Referrer-Policy is set to 'strict-origin-when-cross-origin'."""
        mock_request = MagicMock(spec=Request)
        mock_request.scope = {"type": "http", "method": "GET", "path": "/", "headers": []}

        response = Response(content=b"", status_code=200)
        mock_call_next = AsyncMock(return_value=response)

        await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
