"""
Unit tests for enhanced WebSocket connection manager.

Issue: #573 - Backend: WebSocket Real-Time Progress - Connection Management and State Sync
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.src.websocket.enhanced_manager import (
    EnhancedConnectionManager,
    ConnectionInfo,
    ConnectionState,
    MessageType,
    RateLimiter,
    RateLimitConfig,
    HealthConfig,
)


class TestMessageType:
    """Tests for MessageType enum."""
    
    def test_client_to_server_types(self):
        """Test client-to-server message types."""
        assert MessageType.PING.value == "ping"
        assert MessageType.SUBSCRIBE.value == "subscribe"
        assert MessageType.UNSUBSCRIBE.value == "unsubscribe"
    
    def test_server_to_client_types(self):
        """Test server-to-client message types."""
        assert MessageType.PONG.value == "pong"
        assert MessageType.AGENT_PROGRESS.value == "agent_progress"
        assert MessageType.CONVERSION_COMPLETE.value == "conversion_complete"
        assert MessageType.CONVERSION_FAILED.value == "conversion_failed"
        assert MessageType.ERROR.value == "error"
        assert MessageType.HEARTBEAT.value == "heartbeat"


class TestConnectionState:
    """Tests for ConnectionState enum."""
    
    def test_all_states(self):
        """Test all connection states exist."""
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.RECONNECTING.value == "reconnecting"
        assert ConnectionState.STALE.value == "stale"


class TestConnectionInfo:
    """Tests for ConnectionInfo dataclass."""
    
    def test_creation(self):
        """Test creating connection info."""
        websocket = MagicMock()
        info = ConnectionInfo(
            websocket=websocket,
            conversion_id="test-conversion-id"
        )
        
        assert info.websocket == websocket
        assert info.conversion_id == "test-conversion-id"
        assert info.state == ConnectionState.CONNECTED
        assert info.messages_sent == 0
        assert info.messages_received == 0
    
    def test_to_dict(self):
        """Test serialization."""
        info = ConnectionInfo(
            websocket=MagicMock(),
            conversion_id="test-id",
            client_id="client-123",
            messages_sent=10,
            messages_received=5
        )
        
        data = info.to_dict()
        
        assert data["conversion_id"] == "test-id"
        assert data["client_id"] == "client-123"
        assert data["messages_sent"] == 10
        assert data["messages_received"] == 5
        assert "connected_at" in data


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""
    
    def test_default_config(self):
        """Test default rate limit configuration."""
        config = RateLimitConfig()
        
        assert config.max_messages_per_second == 10
        assert config.max_messages_per_minute == 100
        assert config.burst_allowance == 20
        assert config.cooldown_seconds == 1.0
    
    def test_custom_config(self):
        """Test custom rate limit configuration."""
        config = RateLimitConfig(
            max_messages_per_second=5,
            max_messages_per_minute=50
        )
        
        assert config.max_messages_per_second == 5
        assert config.max_messages_per_minute == 50


class TestHealthConfig:
    """Tests for HealthConfig."""
    
    def test_default_config(self):
        """Test default health configuration."""
        config = HealthConfig()
        
        assert config.heartbeat_interval_seconds == 30.0
        assert config.heartbeat_timeout_seconds == 60.0
        assert config.stale_connection_seconds == 120.0
        assert config.max_reconnect_attempts == 5
    
    def test_custom_config(self):
        """Test custom health configuration."""
        config = HealthConfig(
            heartbeat_interval_seconds=15.0,
            stale_connection_seconds=60.0
        )
        
        assert config.heartbeat_interval_seconds == 15.0
        assert config.stale_connection_seconds == 60.0


class TestRateLimiter:
    """Tests for RateLimiter."""
    
    def test_allows_within_limit(self):
        """Test that messages within limit are allowed."""
        limiter = RateLimiter(RateLimitConfig(
            max_messages_per_second=10,
            max_messages_per_minute=100
        ))
        
        # Should allow several messages
        for _ in range(5):
            assert limiter.is_allowed("client-1") is True
    
    def test_blocks_over_limit(self):
        """Test that messages over limit are blocked."""
        limiter = RateLimiter(RateLimitConfig(
            max_messages_per_second=3,
            max_messages_per_minute=10
        ))
        
        # Use up the limit
        for _ in range(3):
            limiter.is_allowed("client-1")
        
        # Should be blocked now
        assert limiter.is_allowed("client-1") is False
    
    def test_different_clients_independent(self):
        """Test that different clients have independent limits."""
        limiter = RateLimiter(RateLimitConfig(
            max_messages_per_second=2,
            max_messages_per_minute=10
        ))
        
        # Use up limit for client-1
        limiter.is_allowed("client-1")
        limiter.is_allowed("client-1")
        
        # client-1 should be blocked
        assert limiter.is_allowed("client-1") is False
        
        # client-2 should still be allowed
        assert limiter.is_allowed("client-2") is True
    
    def test_get_wait_time(self):
        """Test getting wait time for blocked clients."""
        limiter = RateLimiter(RateLimitConfig(
            max_messages_per_second=2,
            max_messages_per_minute=10,
            cooldown_seconds=2.0
        ))
        
        # Use up limit
        limiter.is_allowed("client-1")
        limiter.is_allowed("client-1")
        limiter.is_allowed("client-1")  # This triggers block
        
        # Should have a wait time
        wait_time = limiter.get_wait_time("client-1")
        assert wait_time > 0
        assert wait_time <= 2.0
    
    def test_wait_time_zero_for_unblocked(self):
        """Test that unblocked clients have zero wait time."""
        limiter = RateLimiter()
        
        assert limiter.get_wait_time("unknown-client") == 0.0


class TestEnhancedConnectionManager:
    """Tests for EnhancedConnectionManager."""
    
    @pytest.fixture
    def manager(self):
        """Create a connection manager."""
        return EnhancedConnectionManager()
    
    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.get_total_connection_count() == 0
        assert len(manager.get_active_conversions()) == 0
    
    def test_get_metrics(self, manager):
        """Test getting metrics."""
        metrics = manager.get_metrics()
        
        assert "active_connections" in metrics
        assert "active_conversions" in metrics
        assert "total_connections_created" in metrics
        assert "total_messages_sent" in metrics
        assert "total_messages_received" in metrics
    
    @pytest.mark.asyncio
    async def test_connect(self, manager):
        """Test connecting a client."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        
        info = await manager.connect(websocket, "conversion-123")
        
        assert info.conversion_id == "conversion-123"
        assert info.state == ConnectionState.CONNECTED
        assert manager.get_connection_count("conversion-123") == 1
        
        # Verify connected message was sent
        websocket.send_json.assert_called_once()
        call_args = websocket.send_json.call_args[0][0]
        assert call_args["type"] == MessageType.CONNECTED.value
    
    @pytest.mark.asyncio
    async def test_disconnect(self, manager):
        """Test disconnecting a client."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        
        await manager.connect(websocket, "conversion-123")
        assert manager.get_connection_count("conversion-123") == 1
        
        manager.disconnect(websocket, "conversion-123")
        assert manager.get_connection_count("conversion-123") == 0
    
    @pytest.mark.asyncio
    async def test_multiple_connections_same_conversion(self, manager):
        """Test multiple connections for same conversion."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        
        await manager.connect(ws1, "conversion-123")
        await manager.connect(ws2, "conversion-123")
        
        assert manager.get_connection_count("conversion-123") == 2
        assert manager.get_total_connection_count() == 2
    
    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Test broadcasting a message."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        
        await manager.connect(websocket, "conversion-123")
        
        message = {
            "type": MessageType.AGENT_PROGRESS.value,
            "data": {"progress": 50}
        }
        
        sent_count = await manager.broadcast(message, "conversion-123")
        
        assert sent_count == 1
        # 2 calls: connected message + broadcast
        assert websocket.send_json.call_count == 2
    
    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self, manager):
        """Test broadcasting with no connections."""
        message = {"type": "test"}
        sent_count = await manager.broadcast(message, "nonexistent")
        assert sent_count == 0
    
    @pytest.mark.asyncio
    async def test_handle_ping_message(self, manager):
        """Test handling ping message."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        
        await manager.connect(websocket, "conversion-123")
        
        response = await manager.handle_message(
            websocket,
            "conversion-123",
            {"type": MessageType.PING.value}
        )
        
        assert response["type"] == MessageType.PONG.value
    
    @pytest.mark.asyncio
    async def test_check_connection_health(self, manager):
        """Test checking connection health."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        
        await manager.connect(websocket, "conversion-123")
        
        health = await manager.check_connection_health("conversion-123")
        
        assert health["healthy"] is True
        assert health["total_connections"] == 1
    
    @pytest.mark.asyncio
    async def test_check_connection_health_no_connections(self, manager):
        """Test health check with no connections."""
        health = await manager.check_connection_health("nonexistent")
        
        assert health["healthy"] is False
        assert "reason" in health


class TestConnectionLifecycle:
    """Tests for connection lifecycle."""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full connection lifecycle."""
        manager = EnhancedConnectionManager()
        
        # Connect
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        
        info = await manager.connect(websocket, "conversion-123")
        assert info.state == ConnectionState.CONNECTED
        
        # Activity
        await manager.handle_message(
            websocket,
            "conversion-123",
            {"type": MessageType.PING.value}
        )
        assert info.messages_received == 1
        
        # Broadcast
        await manager.broadcast(
            {"type": MessageType.AGENT_PROGRESS.value, "data": {}},
            "conversion-123"
        )
        assert info.messages_sent >= 1
        
        # Disconnect
        manager.disconnect(websocket, "conversion-123")
        assert manager.get_connection_count("conversion-123") == 0


class TestMessageProtocol:
    """Tests for WebSocket message protocol."""
    
    def test_message_format(self):
        """Test that messages follow the expected format."""
        # All messages should have type and optional data/timestamp
        message = {
            "type": MessageType.AGENT_PROGRESS.value,
            "data": {
                "agent": "JavaAnalyzerAgent",
                "status": "in_progress",
                "progress": 50
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        assert "type" in message
        assert message["type"] in [t.value for t in MessageType]
    
    def test_progress_message_structure(self):
        """Test progress message structure."""
        message = {
            "type": MessageType.AGENT_PROGRESS.value,
            "data": {
                "agent": "JavaAnalyzerAgent",
                "status": "in_progress",
                "progress": 75,
                "message": "Analyzing Java classes"
            }
        }
        
        assert message["type"] == "agent_progress"
        assert "agent" in message["data"]
        assert "progress" in message["data"]
        assert 0 <= message["data"]["progress"] <= 100


class TestMemoryLeakPrevention:
    """Tests for memory leak prevention."""
    
    @pytest.mark.asyncio
    async def test_cleanup_on_disconnect(self):
        """Test that disconnected clients are cleaned up."""
        manager = EnhancedConnectionManager()
        
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        
        await manager.connect(websocket, "conversion-123")
        
        # Verify connection exists
        assert "conversion-123" in manager._connections
        
        # Disconnect
        manager.disconnect(websocket, "conversion-123")
        
        # Verify cleanup
        assert "conversion-123" not in manager._connections
    
    @pytest.mark.asyncio
    async def test_empty_conversion_cleanup(self):
        """Test that empty conversion entries are removed."""
        manager = EnhancedConnectionManager()
        
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        
        await manager.connect(ws1, "conversion-123")
        await manager.connect(ws2, "conversion-123")
        
        assert "conversion-123" in manager._connections
        
        # Disconnect both
        manager.disconnect(ws1, "conversion-123")
        manager.disconnect(ws2, "conversion-123")
        
        # Conversion entry should be removed
        assert "conversion-123" not in manager._connections


# Integration tests would require actual WebSocket connections
@pytest.mark.integration
class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint(self):
        """Test WebSocket endpoint integration."""
        # This would require actual WebSocket client
        pass
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test handling concurrent connections."""
        pass
    
    @pytest.mark.asyncio
    async def test_heartbeat_mechanism(self):
        """Test heartbeat mechanism."""
        pass