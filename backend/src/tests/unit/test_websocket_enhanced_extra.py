import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from websocket.enhanced_manager import (
    EnhancedConnectionManager,
    MessageType,
    RateLimiter,
    RateLimitConfig,
    HealthConfig,
    get_enhanced_manager,
    start_websocket_manager,
    stop_websocket_manager,
    ConnectionState,
)


@pytest.fixture
def manager():
    return EnhancedConnectionManager()


@pytest.fixture
def mock_websocket():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_manager_start_stop(manager):
    """Test start and stop methods and background loops."""
    # Start manager
    await manager.start()
    assert manager._running is True
    assert manager._heartbeat_task is not None
    assert manager._cleanup_task is not None

    # Stop manager
    await manager.stop()
    assert manager._running is False
    assert manager._heartbeat_task.done()
    assert manager._cleanup_task.done()


@pytest.mark.asyncio
async def test_broadcast_to_all(manager, mock_websocket):
    """Test broadcast_to_all method."""
    await manager.connect(mock_websocket, "conv1")
    ws2 = AsyncMock()
    await manager.connect(ws2, "conv2")

    msg = {"type": "test"}
    count = await manager.broadcast_to_all(msg)
    assert count == 2
    mock_websocket.send_json.assert_called()
    ws2.send_json.assert_called()


@pytest.mark.asyncio
async def test_send_personal_message(manager, mock_websocket):
    """Test send_personal_message method."""
    await manager.connect(mock_websocket, "conv1")

    msg = {"type": "personal"}
    success = await manager.send_personal_message(msg, mock_websocket, "conv1")
    assert success is True

    # Test with non-existent websocket
    success = await manager.send_personal_message(msg, AsyncMock(), "conv1")
    assert success is False


@pytest.mark.asyncio
async def test_get_connection_info(manager, mock_websocket):
    """Test get_connection_info method."""
    await manager.connect(mock_websocket, "conv1")

    info_list = manager.get_connection_info("conv1")
    assert len(info_list) == 1
    assert info_list[0]["conversion_id"] == "conv1"

    # Test non-existent conversion
    assert manager.get_connection_info("none") == []


@pytest.mark.asyncio
async def test_handle_message_errors(manager, mock_websocket):
    """Test error handling in handle_message."""
    await manager.connect(mock_websocket, "conv1")

    # Unknown message type
    resp = await manager.handle_message(mock_websocket, "conv1", {"type": "unknown"})
    assert resp["type"] == MessageType.ERROR.value
    assert "Unknown message type" in resp["data"]["error"]

    # Unsubscribe
    resp = await manager.handle_message(
        mock_websocket, "conv1", {"type": MessageType.UNSUBSCRIBE.value}
    )
    assert resp["type"] == MessageType.DISCONNECTED.value
    assert manager.get_total_connection_count() == 0


@pytest.mark.asyncio
async def test_broadcast_exception_handling(manager, mock_websocket):
    """Test exception handling during broadcast."""
    await manager.connect(mock_websocket, "conv1")

    # Force exception on send
    mock_websocket.send_json.side_effect = Exception("Send failed")

    count = await manager.broadcast({"type": "test"}, "conv1")
    assert count == 0
    # Should be disconnected
    assert manager.get_total_connection_count() == 0


@pytest.mark.asyncio
async def test_global_instance_helpers():
    """Test global manager helpers."""
    m = get_enhanced_manager()
    assert m is not None
    assert get_enhanced_manager() is m

    with patch.object(m, "start", new_callable=AsyncMock) as mock_start:
        await start_websocket_manager()
        mock_start.assert_called_once()

    with patch.object(m, "stop", new_callable=AsyncMock) as mock_stop:
        await stop_websocket_manager()
        mock_stop.assert_called_once()


@pytest.mark.asyncio
async def test_heartbeat_loop_cleanup(mock_websocket):
    """Test that heartbeat loop cleans up dead connections."""
    health_config = HealthConfig(heartbeat_interval_seconds=0.01)
    manager = EnhancedConnectionManager(health_config=health_config)

    await manager.connect(mock_websocket, "conv1")

    # Mock send_json to fail in loop
    mock_websocket.send_json.side_effect = Exception("Dead")

    # Start manager (this starts the loop)
    await manager.start()

    # Wait a bit for loop to run
    await asyncio.sleep(0.05)

    await manager.stop()

    # Connection should be removed
    assert manager.get_total_connection_count() == 0


@pytest.mark.asyncio
async def test_cleanup_loop(mock_websocket):
    """Test stale connection cleanup loop."""
    health_config = HealthConfig(stale_connection_seconds=0.01)
    manager = EnhancedConnectionManager(health_config=health_config)
    manager._running = True

    info = await manager.connect(mock_websocket, "conv1")
    info.last_activity = datetime.now(timezone.utc) - timedelta(seconds=10)

    with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError()]):
        try:
            await manager._cleanup_loop()
        except asyncio.CancelledError:
            pass

    assert manager.get_total_connection_count() == 0


def test_rate_limiter_cooldown_expiry():
    """Test that blocked client cooldown entry is deleted after expiry (lines 137-139)."""
    limiter = RateLimiter(
        RateLimitConfig(
            max_messages_per_second=100, max_messages_per_minute=100, cooldown_seconds=0.01
        )
    )

    assert limiter.is_allowed("client-1") is True

    limiter._blocked_until["client-1"] = time.time() - 1.0

    assert limiter.is_allowed("client-1") is True
    assert "client-1" not in limiter._blocked_until


@pytest.mark.asyncio
async def test_send_personal_message_exception(mock_websocket):
    """Test send_personal_message returns False on send exception."""
    manager = EnhancedConnectionManager()
    await manager.connect(mock_websocket, "conv1")

    mock_websocket.send_json.side_effect = Exception("Send failed")

    success = await manager.send_personal_message({"type": "test"}, mock_websocket, "conv1")
    assert success is False


@pytest.mark.asyncio
async def test_heartbeat_loop_general_exception():
    """Test heartbeat loop handles general exceptions in outer try block."""
    health_config = HealthConfig(heartbeat_interval_seconds=0.01)
    manager = EnhancedConnectionManager(health_config=health_config)
    manager._running = True

    with patch("asyncio.sleep", side_effect=[RuntimeError("unexpected"), asyncio.CancelledError()]):
        try:
            await manager._heartbeat_loop()
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_cleanup_loop_general_exception():
    """Test cleanup loop handles general exceptions in outer try block."""
    manager = EnhancedConnectionManager()
    manager._running = True

    with patch("asyncio.sleep", side_effect=[RuntimeError("unexpected"), asyncio.CancelledError()]):
        try:
            await manager._cleanup_loop()
        except asyncio.CancelledError:
            pass
