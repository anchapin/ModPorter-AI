"""
Unit tests for logging configuration and middleware.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from utils.logging_config import setup_logging, get_logger, StructlogMiddleware


class TestLoggingConfig:
    @patch("utils.logging_config.structlog.configure")
    @patch("logging.getLogger")
    def test_setup_logging_json(self, mock_get_logger, mock_configure):
        setup_logging(log_level="DEBUG", json_format=True)

        mock_configure.assert_called_once()
        # Verify log level was set
        mock_get_logger.return_value.setLevel.assert_called()

    @patch("utils.logging_config.structlog.configure")
    @patch("logging.getLogger")
    def test_setup_logging_console(self, mock_get_logger, mock_configure):
        setup_logging(log_level="INFO", json_format=False)

        mock_configure.assert_called_once()

    @patch("utils.logging_config.structlog.get_logger")
    def test_get_logger(self, mock_get_logger):
        get_logger("test_name")
        mock_get_logger.assert_called_once_with("test_name")


class TestStructlogMiddleware:
    @pytest.mark.asyncio
    @patch("utils.logging_config.get_logger")
    async def test_middleware_http(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        app = AsyncMock()
        middleware = StructlogMiddleware(app)

        scope = {"type": "http", "method": "GET", "path": "/test", "client": ("127.0.0.1", 12345)}
        receive = AsyncMock()
        send = AsyncMock()

        # We need to simulate the app calling send with response start
        async def mock_app(s, r, sn):
            await sn({"type": "http.response.start", "status": 200})

        app.side_effect = mock_app

        await middleware(scope, receive, send)

        # Verify logger was called
        assert mock_logger.info.call_count == 2
        mock_logger.info.assert_any_call(
            "request_started",
            method="GET",
            path="/test",
            client_ip="127.0.0.1",
            correlation_id=scope["correlation_id"],
        )

        # Verify status_code was captured in the second call
        # The second call should have status_code=200
        completion_call = [
            c for c in mock_logger.info.call_args_list if c[0][0] == "request_completed"
        ][0]
        assert completion_call[1]["status_code"] == 200

    @pytest.mark.asyncio
    async def test_middleware_non_http(self):
        app = AsyncMock()
        middleware = StructlogMiddleware(app)

        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        app.assert_called_once_with(scope, receive, send)
