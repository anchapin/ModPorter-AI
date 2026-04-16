"""
Tests for HTTPS Enforcement Middleware

Tests:
- HTTPS redirect in production
- No redirect in development
- HSTS header enforcement in production
"""

import pytest
from unittest.mock import MagicMock, patch
from starlette.requests import Request
from starlette.responses import Response

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.https_enforcement import HTTPSRedirectMiddleware, HSTSStrictMiddleware


class TestHTTPSRedirectMiddleware:
    """Tests for HTTPSRedirectMiddleware"""

    def setup_method(self):
        """Set up test environment"""
        self.orig_env = os.environ.get("ENVIRONMENT")

    def teardown_method(self):
        """Restore environment"""
        if self.orig_env is not None:
            os.environ["ENVIRONMENT"] = self.orig_env
        elif "ENVIRONMENT" in os.environ:
            del os.environ["ENVIRONMENT"]

    @pytest.mark.asyncio
    async def test_no_redirect_in_development(self):
        """Test that HTTP requests are not redirected in development"""
        os.environ["ENVIRONMENT"] = "development"

        app = MagicMock()
        middleware = HTTPSRedirectMiddleware(app)

        request = MagicMock(spec=Request)
        request.headers = {"Host": "localhost:8000"}
        request.url.path = "/api/v1/health"
        request.url.query = ""

        async def call_next(request):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redirect_in_production(self):
        """Test that HTTP requests are redirected to HTTPS in production"""
        os.environ["ENVIRONMENT"] = "production"

        app = MagicMock()
        middleware = HTTPSRedirectMiddleware(app)

        request = MagicMock(spec=Request)
        request.headers = {"Host": "api.modporter.ai", "X-Forwarded-Proto": "http"}
        request.url.path = "/api/v1/conversions"
        request.url.query = "page=1"
        request.url.__str__ = lambda self: "/api/v1/conversions?page=1"

        async def call_next(request):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 301
        assert "https://" in response.headers.get("Location", "")

    @pytest.mark.asyncio
    async def test_no_redirect_when_https_header(self):
        """Test that requests with HTTPS proto are not redirected"""
        os.environ["ENVIRONMENT"] = "production"

        app = MagicMock()
        middleware = HTTPSRedirectMiddleware(app)

        request = MagicMock(spec=Request)
        request.headers = {"Host": "api.modporter.ai", "X-Forwarded-Proto": "https"}
        request.url.path = "/api/v1/health"
        request.url.query = ""

        async def call_next(request):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200


class TestHSTSStrictMiddleware:
    """Tests for HSTSStrictMiddleware"""

    def setup_method(self):
        """Set up test environment"""
        self.orig_env = os.environ.get("ENVIRONMENT")
        self.orig_force = os.environ.get("FORCE_HSTS")

    def teardown_method(self):
        """Restore environment"""
        if self.orig_env is not None:
            os.environ["ENVIRONMENT"] = self.orig_env
        elif "ENVIRONMENT" in os.environ:
            del os.environ["ENVIRONMENT"]

        if self.orig_force is not None:
            os.environ["FORCE_HSTS"] = self.orig_force
        elif "FORCE_HSTS" in os.environ:
            del os.environ["FORCE_HSTS"]

    @pytest.mark.asyncio
    async def test_hsts_header_in_production(self):
        """Test that HSTS header is set in production"""
        os.environ["ENVIRONMENT"] = "production"

        app = MagicMock()
        middleware = HSTSStrictMiddleware(app)

        request = MagicMock(spec=Request)

        async def call_next(request):
            response = Response(content="OK", status_code=200)
            return response

        response = await middleware.dispatch(request, call_next)
        assert "Strict-Transport-Security" in response.headers
        assert "max-age=63072000" in response.headers["Strict-Transport-Security"]
        assert "includeSubDomains" in response.headers["Strict-Transport-Security"]
        assert "preload" in response.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_no_hsts_header_in_development(self):
        """Test that HSTS header is not set in development"""
        os.environ["ENVIRONMENT"] = "development"

        app = MagicMock()
        middleware = HSTSStrictMiddleware(app)

        request = MagicMock(spec=Request)

        async def call_next(request):
            response = Response(content="OK", status_code=200)
            return response

        response = await middleware.dispatch(request, call_next)
        # In development, HSTS should NOT be set
        assert "Strict-Transport-Security" not in response.headers

    @pytest.mark.asyncio
    async def test_hsts_with_force_flag(self):
        """Test that HSTS can be forced via FORCE_HSTS env var"""
        os.environ["ENVIRONMENT"] = "development"
        os.environ["FORCE_HSTS"] = "true"

        app = MagicMock()
        middleware = HSTSStrictMiddleware(app)

        request = MagicMock(spec=Request)

        async def call_next(request):
            response = Response(content="OK", status_code=200)
            return response

        response = await middleware.dispatch(request, call_next)
        assert "Strict-Transport-Security" in response.headers

    @pytest.mark.asyncio
    async def test_hsts_not_duplicated(self):
        """Test that HSTS header is not duplicated if already set"""
        os.environ["ENVIRONMENT"] = "production"

        app = MagicMock()
        middleware = HSTSStrictMiddleware(app)

        request = MagicMock(spec=Request)

        async def call_next(request):
            response = Response(content="OK", status_code=200)
            # Simulate already set by SecurityHeadersMiddleware
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
            return response

        response = await middleware.dispatch(request, call_next)
        # Should still be present, not overwritten
        assert "Strict-Transport-Security" in response.headers
