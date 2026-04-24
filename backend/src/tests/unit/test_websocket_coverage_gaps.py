"""
Tests for remaining WebSocket coverage gaps in enhanced_manager and progress_handler.

Targets uncovered lines:
- enhanced_manager: 137-139, 156-157, 343, 353-354, 365, 409, 464-466, 518-519, 557, 564-565, 595-596
- progress_handler: 77, 116-127, 139, 165, 186, 204, 222-240, 251-269
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from websocket.enhanced_manager import (
    EnhancedConnectionManager,
    ConnectionInfo,
    ConnectionState,
    MessageType,
    RateLimiter,
    RateLimitConfig,
    HealthConfig,
)
from websocket.progress_handler import (
    ProgressHandler,
    ProgressMessage,
    ProgressMessageData,
    AgentStatus,
    progress_message,
)


class TestRateLimiterEdgeCases:
    """Cover lines 137-139 (cooldown expiry), 156-157 (per-minute limit)."""

    def test_cooldown_expires_and_allows(self):
        limiter = RateLimiter(
            RateLimitConfig(
                max_messages_per_second=1,
                max_messages_per_minute=100,
                cooldown_seconds=0.01,
            )
        )
        assert limiter.is_allowed("c1") is True
        assert limiter.is_allowed("c1") is False

        import time

        time.sleep(0.02)

        limiter2 = RateLimiter(
            RateLimitConfig(
                max_messages_per_second=1,
                max_messages_per_minute=100,
                cooldown_seconds=0.01,
            )
        )
        assert limiter2.is_allowed("c1") is True

    def test_per_minute_limit_blocks(self):
        limiter = RateLimiter(
            RateLimitConfig(
                max_messages_per_second=100,
                max_messages_per_minute=3,
                cooldown_seconds=1.0,
            )
        )
        for _ in range(3):
            limiter.is_allowed("c1")
        assert limiter.is_allowed("c1") is False


class TestEnhancedManagerHandleMessageGaps:
    """Cover lines 343 (not connected), 353-354 (rate limit), 365 (subscribe)."""

    @pytest.fixture
    def manager(self):
        return EnhancedConnectionManager()

    @pytest.fixture
    def mock_ws(self):
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_handle_message_not_connected(self, manager, mock_ws):
        resp = await manager.handle_message(mock_ws, "no-exist", {"type": "ping"})
        assert resp["type"] == MessageType.ERROR.value
        assert "Not connected" in resp["data"]["error"]

    @pytest.mark.asyncio
    async def test_handle_message_rate_limited(self, manager, mock_ws):
        await manager.connect(mock_ws, "conv1")
        manager._rate_limiter = RateLimiter(
            RateLimitConfig(
                max_messages_per_second=1,
                max_messages_per_minute=100,
                cooldown_seconds=60,
            )
        )
        manager._rate_limiter.is_allowed("x")
        info = manager._connections["conv1"][mock_ws]
        info.client_id = "x"

        resp = await manager.handle_message(mock_ws, "conv1", {"type": "ping"})
        assert resp["type"] == MessageType.ERROR.value
        assert "Rate limit" in resp["data"]["error"]
        assert "retry_after" in resp["data"]

    @pytest.mark.asyncio
    async def test_handle_subscribe(self, manager, mock_ws):
        await manager.connect(mock_ws, "conv1")
        resp = await manager.handle_message(mock_ws, "conv1", {"type": MessageType.SUBSCRIBE.value})
        assert resp["type"] == MessageType.CONNECTED.value


class TestEnhancedManagerBroadcastThrottle:
    """Cover line 409 (broadcast throttle skip)."""

    @pytest.mark.asyncio
    async def test_broadcast_throttled_client(self):
        manager = EnhancedConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        info = await manager.connect(ws, "conv1")
        manager._rate_limiter = RateLimiter(
            RateLimitConfig(
                max_messages_per_second=1,
                max_messages_per_minute=100,
                cooldown_seconds=60,
            )
        )
        manager._rate_limiter.is_allowed(info.client_id)

        count = await manager.broadcast({"type": "test"}, "conv1", throttle=True)
        assert count == 0


class TestEnhancedManagerSendPersonalMessageError:
    """Cover lines 464-466 (exception in send_personal_message)."""

    @pytest.mark.asyncio
    async def test_send_personal_message_exception(self):
        manager = EnhancedConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        await manager.connect(ws, "conv1")

        ws.send_json = AsyncMock(side_effect=Exception("boom"))

        with patch("websocket.enhanced_manager.logger") as mock_logger:
            result = await manager.send_personal_message({"type": "x"}, ws, "conv1")
            assert result is False
            mock_logger.error.assert_called()


class TestEnhancedManagerStaleDetection:
    """Cover lines 518-519 (stale connection in check_connection_health)."""

    @pytest.mark.asyncio
    async def test_stale_connection_health(self):
        manager = EnhancedConnectionManager(health_config=HealthConfig(stale_connection_seconds=1))
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        info = await manager.connect(ws, "conv1")
        info.last_activity = datetime.now(timezone.utc) - timedelta(seconds=60)

        health = await manager.check_connection_health("conv1")
        assert health["healthy"] is False
        assert len(health["issues"]) == 1
        assert "stale" in health["issues"][0].lower()


class TestEnhancedManagerHeartbeatSuccess:
    """Cover line 557 (heartbeat send success → update last_heartbeat)."""

    @pytest.mark.asyncio
    async def test_heartbeat_updates_last_heartbeat(self):
        manager = EnhancedConnectionManager(
            health_config=HealthConfig(heartbeat_interval_seconds=0.01)
        )
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        info = await manager.connect(ws, "conv1")
        old_hb = info.last_heartbeat

        await manager.start()
        await asyncio.sleep(0.05)
        await manager.stop()

        assert info.last_heartbeat > old_hb


class TestEnhancedManagerLoopExceptions:
    """Cover lines 564-565 (heartbeat loop exception), 595-596 (cleanup loop exception)."""

    @pytest.mark.asyncio
    async def test_heartbeat_loop_exception_handling(self):
        manager = EnhancedConnectionManager(
            health_config=HealthConfig(heartbeat_interval_seconds=0.01)
        )
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        await manager.connect(ws, "conv1")

        original_send = ws.send_json
        call_count = 0
        original_fn = manager._send_message

        async def failing_send(websocket, message):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise RuntimeError("boom")
            await original_send(websocket, message)

        manager._send_message = failing_send

        await manager.start()
        await asyncio.sleep(0.05)
        await manager.stop()

    @pytest.mark.asyncio
    async def test_cleanup_loop_exception_handling(self):
        manager = EnhancedConnectionManager()
        manager._running = True

        with patch.object(manager, "_connections", side_effect=RuntimeError("boom")):
            with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError()]):
                try:
                    await manager._cleanup_loop()
                except asyncio.CancelledError:
                    pass


class TestProgressHandlerFull:
    """Cover all progress_handler uncovered lines."""

    @pytest.mark.asyncio
    async def test_progress_message_function(self):
        msg = progress_message(
            agent="TestAgent",
            status=AgentStatus.IN_PROGRESS,
            progress=50,
            message="Halfway there",
            details={"key": "val"},
        )
        assert msg.type == "agent_progress"
        assert msg.data.agent == "TestAgent"
        assert msg.data.progress == 50

    @pytest.mark.asyncio
    async def test_broadcast_progress_success(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock()
            await ProgressHandler.broadcast_progress(
                "conv1", "Agent1", AgentStatus.IN_PROGRESS, 50, "working"
            )
            mock_mgr.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_progress_failure(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock(side_effect=Exception("fail"))
            await ProgressHandler.broadcast_progress(
                "conv1", "Agent1", AgentStatus.FAILED, 0, "error"
            )

    @pytest.mark.asyncio
    async def test_broadcast_agent_start(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock()
            await ProgressHandler.broadcast_agent_start("conv1", "Agent1")
            call_args = mock_mgr.broadcast.call_args[0][0]
            assert call_args["data"]["status"] == "in_progress"
            assert call_args["data"]["progress"] == 0

    @pytest.mark.asyncio
    async def test_broadcast_agent_start_custom_message(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock()
            await ProgressHandler.broadcast_agent_start("conv1", "Agent1", "custom msg")
            call_args = mock_mgr.broadcast.call_args[0][0]
            assert call_args["data"]["message"] == "custom msg"

    @pytest.mark.asyncio
    async def test_broadcast_agent_update(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock()
            await ProgressHandler.broadcast_agent_update(
                "conv1", "Agent1", 75, "almost done", {"extra": "info"}
            )
            call_args = mock_mgr.broadcast.call_args[0][0]
            assert call_args["data"]["progress"] == 75
            assert call_args["data"]["details"] == {"extra": "info"}

    @pytest.mark.asyncio
    async def test_broadcast_agent_complete(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock()
            await ProgressHandler.broadcast_agent_complete("conv1", "Agent1")
            call_args = mock_mgr.broadcast.call_args[0][0]
            assert call_args["data"]["status"] == "completed"
            assert call_args["data"]["progress"] == 100

    @pytest.mark.asyncio
    async def test_broadcast_agent_complete_custom_message(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock()
            await ProgressHandler.broadcast_agent_complete("conv1", "Agent1", "all done!")
            call_args = mock_mgr.broadcast.call_args[0][0]
            assert call_args["data"]["message"] == "all done!"

    @pytest.mark.asyncio
    async def test_broadcast_agent_failed(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock()
            await ProgressHandler.broadcast_agent_failed("conv1", "Agent1", "crashed")
            call_args = mock_mgr.broadcast.call_args[0][0]
            assert call_args["data"]["status"] == "failed"
            assert call_args["data"]["details"]["error"] == "crashed"

    @pytest.mark.asyncio
    async def test_broadcast_conversion_complete(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock()
            await ProgressHandler.broadcast_conversion_complete("conv1", "/download/123")
            call_args = mock_mgr.broadcast.call_args[0][0]
            assert call_args["type"] == "conversion_complete"
            assert call_args["data"]["details"]["download_url"] == "/download/123"

    @pytest.mark.asyncio
    async def test_broadcast_conversion_complete_failure(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock(side_effect=Exception("fail"))
            await ProgressHandler.broadcast_conversion_complete("conv1", "/dl")

    @pytest.mark.asyncio
    async def test_broadcast_conversion_failed(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock()
            await ProgressHandler.broadcast_conversion_failed("conv1", "timeout")
            call_args = mock_mgr.broadcast.call_args[0][0]
            assert call_args["type"] == "conversion_failed"
            assert call_args["data"]["details"]["error"] == "timeout"

    @pytest.mark.asyncio
    async def test_broadcast_conversion_failed_failure(self):
        with patch("websocket.progress_handler.manager") as mock_mgr:
            mock_mgr.broadcast = AsyncMock(side_effect=Exception("fail"))
            await ProgressHandler.broadcast_conversion_failed("conv1", "timeout")
