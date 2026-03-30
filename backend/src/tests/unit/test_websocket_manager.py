"""
Unit tests for the basic WebSocket connection manager.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from websocket.manager import ConnectionManager

class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_connect(self):
        manager = ConnectionManager()
        websocket = AsyncMock()
        conversion_id = "test-conv-123"
        
        await manager.connect(websocket, conversion_id)
        
        websocket.accept.assert_called_once()
        assert conversion_id in manager.active_connections
        assert websocket in manager.active_connections[conversion_id]

    def test_disconnect(self):
        manager = ConnectionManager()
        websocket = MagicMock()
        conversion_id = "test-conv-123"
        
        # Manually setup connection
        manager.active_connections[conversion_id] = {websocket}
        
        manager.disconnect(websocket, conversion_id)
        
        assert conversion_id not in manager.active_connections

    def test_disconnect_non_existent(self):
        manager = ConnectionManager()
        websocket = MagicMock()
        # Should not raise exception
        manager.disconnect(websocket, "non-existent")

    @pytest.mark.asyncio
    async def test_send_personal_message(self):
        manager = ConnectionManager()
        websocket = AsyncMock()
        message = {"type": "test", "data": "hello"}
        
        await manager.send_personal_message(message, websocket)
        
        websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_success(self):
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        conversion_id = "test-conv-123"
        manager.active_connections[conversion_id] = {ws1, ws2}
        
        message = {"type": "progress", "value": 50}
        await manager.broadcast(message, conversion_id)
        
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_partial_failure(self):
        manager = ConnectionManager()
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_json.side_effect = Exception("Connection closed")
        
        conversion_id = "test-conv-123"
        manager.active_connections[conversion_id] = {ws_good, ws_bad}
        
        message = {"type": "progress", "value": 50}
        await manager.broadcast(message, conversion_id)
        
        ws_good.send_json.assert_called_once_with(message)
        # ws_bad should be removed
        assert ws_bad not in manager.active_connections.get(conversion_id, set())
        assert ws_good in manager.active_connections[conversion_id]

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self):
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        manager.active_connections["id1"] = {ws1}
        manager.active_connections["id2"] = {ws2}
        
        message = {"global": "msg"}
        await manager.broadcast_to_all(message)
        
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_failure(self):
        manager = ConnectionManager()
        websocket = AsyncMock()
        websocket.send_json.side_effect = Exception("Send failed")
        message = {"type": "test"}
        
        with pytest.raises(Exception, match="Send failed"):
            await manager.send_personal_message(message, websocket)

    @pytest.mark.asyncio
    async def test_broadcast_unknown_id(self):
        manager = ConnectionManager()
        # Should return early and not raise anything
        await manager.broadcast({"msg": "hi"}, "unknown-id")

    def test_get_counts(self):
        manager = ConnectionManager()
        ws1 = MagicMock()
        ws2 = MagicMock()
        manager.active_connections["id1"] = {ws1}
        manager.active_connections["id2"] = {ws2, MagicMock()}
        
        assert manager.get_connection_count("id1") == 1
        assert manager.get_connection_count("id2") == 2
        assert manager.get_connection_count("unknown") == 0
        assert manager.get_total_connection_count() == 3
        
        active = manager.get_active_conversions()
        assert "id1" in active
        assert "id2" in active
        assert len(active) == 2
