"""
Unit tests for HTTPSRedirectMiddleware.

Tests the middleware that enforces HTTPS for production traffic.

Issue: #1535 - security(backend): force HTTPS in production by default
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response


class TestHTTPSRedirectMiddleware:
    """Tests for HTTPSRedirectMiddleware class."""

    @pytest.fixture
    def middleware(self):
        """Create an HTTPSRedirectMiddleware instance with a mock app."""
        from services.security_headers import HTTPSRedirectMiddleware

        mock_app = MagicMock()
        return HTTPSRedirectMiddleware(app=mock_app)

    @pytest.fixture
    def mock_request(self):
        """Create a mock HTTP request."""
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "headers": [(b"host", b"example.com")],
            "query_string": b"",
            "server": ("example.com", 80),
            "scheme": "http",
        }
        request = MagicMock(spec=Request)
        request.scope = mock_scope
        request.url = MagicMock()
        request.url.scheme = "http"
        request.url.path = "/api/v1/test"
        request.url.replace = MagicMock(return_value=MagicMock(__str__=lambda self: "https://" + request.url.netloc + request.url.path))
        request.url.netloc = "example.com"
        request.headers = {"host": "example.com"}
        return request

    def _create_request_for_path(self, path="/api/v1/test", host="example.com"):
        """Helper to create mock request."""
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [(b"host", host.encode())],
            "query_string": b"",
            "server": (host, 80),
            "scheme": "http",
        }
        request = MagicMock(spec=Request)
        request.scope = mock_scope
        request.url = MagicMock()
        request.url.scheme = "http"
        request.url.path = path
        request.url.netloc = host
        request.headers = {"host": host}
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create a mock call_next function."""
        async def call_next(request):
            return Response(content="OK", status_code=200)

        return call_next

    # --- Instantiation Tests ---

    @pytest.mark.asyncio
    async def test_middleware_instantiation(self):
        """Test that HTTPSRedirectMiddleware can be instantiated with an ASGI app."""
        from services.security_headers import HTTPSRedirectMiddleware

        mock_app = MagicMock()
        middleware = HTTPSRedirectMiddleware(app=mock_app)

        assert middleware.app is mock_app

    # --- Production Detection Tests ---

    @pytest.mark.asyncio
    async def test_is_production_with_environment_production(self, middleware):
        """Test that ENVIRONMENT=production triggers HTTPS redirect."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            assert middleware._is_production() is True

    @pytest.mark.asyncio
    async def test_is_production_with_environment_production_uppercase(self, middleware):
        """Test that ENVIRONMENT=PRODUCTION triggers HTTPS redirect."""
        with patch.dict("os.environ", {"ENVIRONMENT": "PRODUCTION"}):
            assert middleware._is_production() is True

    @pytest.mark.asyncio
    async def test_is_production_with_force_https_true(self, middleware):
        """Test that FORCE_HTTPS=true triggers HTTPS redirect."""
        with patch.dict("os.environ", {"FORCE_HTTPS": "true"}):
            assert middleware._is_production() is True

    @pytest.mark.asyncio
    async def test_is_production_false_for_development(self, middleware):
        """Test that development environment does not trigger redirect."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            assert middleware._is_production() is False

    @pytest.mark.asyncio
    async def test_is_production_false_for_empty_environment(self, middleware):
        """Test that empty environment does not trigger redirect."""
        with patch.dict("os.environ", {"ENVIRONMENT": ""}, clear=False):
            if "ENVIRONMENT" in __import__("os").environ:
                del __import__("os").environ["ENVIRONMENT"]
            assert middleware._is_production() is False

    # --- Should Redirect Tests ---

    @pytest.mark.asyncio
    async def test_should_not_redirect_https_requests(self, middleware, mock_request):
        """Test that HTTPS requests are not redirected."""
        mock_request.url.scheme = "https"
        assert middleware._should_redirect(mock_request) is False

    @pytest.mark.asyncio
    async def test_should_not_redirect_in_development(self, middleware, mock_request):
        """Test that HTTP requests in non-production are not redirected."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            assert middleware._should_redirect(mock_request) is False

    @pytest.mark.asyncio
    async def test_should_redirect_http_in_production(self, middleware, mock_request):
        """Test that HTTP requests in production are redirected."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            assert middleware._should_redirect(mock_request) is True

    @pytest.mark.asyncio
    async def test_should_redirect_with_force_https(self, middleware, mock_request):
        """Test that HTTP requests are redirected when FORCE_HTTPS=true."""
        with patch.dict("os.environ", {"FORCE_HTTPS": "true"}):
            assert middleware._should_redirect(mock_request) is True

    @pytest.mark.asyncio
    async def test_should_not_redirect_excluded_paths(self, middleware):
        """Test that excluded paths are not redirected."""
        excluded_paths = [
            "/api/v1/health",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",
            "/api/v1/metrics",
            "/metrics",
        ]
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            for path in excluded_paths:
                mock_req = self._create_request_for_path(path=path)
                assert middleware._should_redirect(mock_req) is False, f"Path {path} should be excluded"

    @pytest.mark.asyncio
    async def test_should_not_redirect_localhost(self, middleware):
        """Test that localhost requests are not redirected."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            mock_req = self._create_request_for_path(host="localhost")
            assert middleware._should_redirect(mock_req) is False

            mock_req = self._create_request_for_path(host="127.0.0.1")
            assert middleware._should_redirect(mock_req) is False

            mock_req = self._create_request_for_path(host="[::1]")
            assert middleware._should_redirect(mock_req) is False

    # --- Dispatch Tests ---

    @pytest.mark.asyncio
    async def test_dispatch_redirects_in_production(self, middleware, mock_request, mock_call_next):
        """Test that dispatch redirects HTTP to HTTPS in production."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            response = await middleware.dispatch(mock_request, mock_call_next)

            assert isinstance(response, RedirectResponse)
            assert response.status_code == 307
            # RedirectResponse stores URL in Location header
            assert response.headers.get("Location", "").startswith("https://")

    @pytest.mark.asyncio
    async def test_dispatch_does_not_redirect_in_development(self, middleware, mock_request, mock_call_next):
        """Test that dispatch does not redirect in development."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            response = await middleware.dispatch(mock_request, mock_call_next)

            # Should pass through to call_next
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_does_not_redirect_https(self, middleware, mock_request, mock_call_next):
        """Test that dispatch does not redirect HTTPS requests even in production."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            mock_request.url.scheme = "https"
            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_preserves_request_method(self, middleware, mock_request, mock_call_next):
        """Test that dispatch uses 307 to preserve request method."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            response = await middleware.dispatch(mock_request, mock_call_next)

            # 307 = Temporary Redirect (preserves method)
            # 301 = Permanent Redirect (may change POST to GET)
            assert response.status_code == 307

    @pytest.mark.asyncio
    async def test_dispatch_redirects_post_requests(self, middleware, mock_request, mock_call_next):
        """Test that POST requests are properly redirected with 307."""
        mock_request.scope["method"] = "POST"
        mock_request.url.scheme = "http"

        async def mock_call_next_post(request):
            return Response(content="Created", status_code=201)

        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            response = await middleware.dispatch(mock_request, mock_call_next_post)

            assert isinstance(response, RedirectResponse)
            assert response.status_code == 307

    # --- URL Construction Tests ---

    @pytest.mark.asyncio
    async def test_dispatch_constructs_correct_https_url(self, middleware, mock_request, mock_call_next):
        """Test that HTTPS URL is correctly constructed."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            response = await middleware.dispatch(mock_request, mock_call_next)

            # Verify redirect happened and URL starts with https
            assert isinstance(response, RedirectResponse)
            assert response.headers.get("Location", "").startswith("https://")
            assert "example.com" in response.headers.get("Location", "")

    # --- Excluded Paths Dispatch Tests ---

    @pytest.mark.asyncio
    async def test_dispatch_health_endpoint_not_redirected(self, middleware, mock_call_next):
        """Test that health endpoint is not redirected."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            mock_req = self._create_request_for_path(path="/api/v1/health")
            response = await middleware.dispatch(mock_req, mock_call_next)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_docs_endpoint_not_redirected(self, middleware, mock_call_next):
        """Test that docs endpoint is not redirected."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            mock_req = self._create_request_for_path(path="/api/v1/docs")
            response = await middleware.dispatch(mock_req, mock_call_next)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_does_not_redirect_https(self, middleware, mock_request, mock_call_next):
        """Test that dispatch does not redirect HTTPS requests even in production."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            mock_request.url.scheme = "https"
            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_preserves_request_method(self, middleware, mock_request, mock_call_next):
        """Test that dispatch uses 307 to preserve request method."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            response = await middleware.dispatch(mock_request, mock_call_next)

            # 307 = Temporary Redirect (preserves method)
            # 301 = Permanent Redirect (may change POST to GET)
            assert response.status_code == 307

    @pytest.mark.asyncio
    async def test_dispatch_redirects_post_requests(self, middleware, mock_request, mock_call_next):
        """Test that POST requests are properly redirected with 307."""
        mock_request.scope["method"] = "POST"
        mock_request.url.scheme = "http"

        async def mock_call_next_post(request):
            return Response(content="Created", status_code=201)

        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            response = await middleware.dispatch(mock_request, mock_call_next_post)

            assert isinstance(response, RedirectResponse)
            assert response.status_code == 307

    # --- URL Construction Tests ---

    @pytest.mark.asyncio
    async def test_dispatch_constructs_correct_https_url(self, middleware, mock_request, mock_call_next):
        """Test that HTTPS URL is correctly constructed."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            response = await middleware.dispatch(mock_request, mock_call_next)

            # Verify redirect happened and URL starts with https
            assert isinstance(response, RedirectResponse)
            assert response.headers.get("Location", "").startswith("https://")
            assert "example.com" in response.headers.get("Location", "")

    # --- Excluded Paths Dispatch Tests ---

    @pytest.mark.asyncio
    async def test_dispatch_health_endpoint_not_redirected(self, middleware, mock_call_next):
        """Test that health endpoint is not redirected."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            mock_req = self._create_request_for_path("/api/v1/health")
            response = await middleware.dispatch(mock_req, mock_call_next)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_docs_endpoint_not_redirected(self, middleware, mock_call_next):
        """Test that docs endpoint is not redirected."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            mock_req = self._create_request_for_path("/api/v1/docs")
            response = await middleware.dispatch(mock_req, mock_call_next)

            assert response.status_code == 200

    # --- Middleware Order Tests ---

    @pytest.mark.asyncio
    async def test_excluded_paths_constant(self):
        """Test that EXCLUDED_PATHS contains expected paths."""
        from services.security_headers import HTTPSRedirectMiddleware

        expected_paths = {
            "/api/v1/health",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",
            "/api/v1/metrics",
            "/metrics",
        }
        assert HTTPSRedirectMiddleware.EXCLUDED_PATHS == expected_paths