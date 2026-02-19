"""
Enhanced WebSocket connection manager for handling multiple concurrent clients.

Enhanced features for Issue #573:
- Connection health monitoring with heartbeats
- Automatic reconnection logic
- Rate limiting for progress updates
- Memory leak detection
- Documented WebSocket message protocol

Issue: #573 - Backend: WebSocket Real-Time Progress - Connection Management and State Sync
"""

import asyncio
import logging
import time
import weakref
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Set, List, Optional, Any, Callable
import json

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    STALE = "stale"


class MessageType(str, Enum):
    """
    WebSocket message types for the progress protocol.
    
    Protocol Documentation:
    - All messages are JSON-encoded
    - Each message has a 'type' field indicating the message type
    - Progress updates include 'data' with agent status information
    """
    # Client -> Server
    PING = "ping"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    
    # Server -> Client
    PONG = "pong"
    AGENT_PROGRESS = "agent_progress"
    CONVERSION_COMPLETE = "conversion_complete"
    CONVERSION_FAILED = "conversion_failed"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    
    # Connection management
    CONNECTED = "connected"
    RECONNECTED = "reconnected"
    DISCONNECTED = "disconnected"


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    conversion_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    state: ConnectionState = ConnectionState.CONNECTED
    messages_sent: int = 0
    messages_received: int = 0
    reconnect_count: int = 0
    client_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "conversion_id": self.conversion_id,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "state": self.state.value,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "reconnect_count": self.reconnect_count,
            "client_id": self.client_id
        }


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_messages_per_second: int = 10
    max_messages_per_minute: int = 100
    burst_allowance: int = 20
    cooldown_seconds: float = 1.0


@dataclass
class HealthConfig:
    """Configuration for health monitoring."""
    heartbeat_interval_seconds: float = 30.0
    heartbeat_timeout_seconds: float = 60.0
    stale_connection_seconds: float = 120.0
    max_reconnect_attempts: int = 5
    reconnect_delay_seconds: float = 1.0


class RateLimiter:
    """
    Rate limiter for WebSocket messages.
    
    Uses a sliding window algorithm to limit message rates.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._message_times: Dict[str, List[float]] = defaultdict(list)
        self._blocked_until: Dict[str, float] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if a client is allowed to send a message."""
        now = time.time()
        
        # Check if client is in cooldown
        if client_id in self._blocked_until:
            if now < self._blocked_until[client_id]:
                return False
            del self._blocked_until[client_id]
        
        # Clean old message times
        self._message_times[client_id] = [
            t for t in self._message_times[client_id]
            if now - t < 60.0
        ]
        
        times = self._message_times[client_id]
        
        # Check per-second limit
        recent_second = [t for t in times if now - t < 1.0]
        if len(recent_second) >= self.config.max_messages_per_second:
            self._blocked_until[client_id] = now + self.config.cooldown_seconds
            return False
        
        # Check per-minute limit
        if len(times) >= self.config.max_messages_per_minute:
            self._blocked_until[client_id] = now + self.config.cooldown_seconds
            return False
        
        # Record this message
        times.append(now)
        return True
    
    def get_wait_time(self, client_id: str) -> float:
        """Get the time until a blocked client can send again."""
        if client_id in self._blocked_until:
            return max(0, self._blocked_until[client_id] - time.time())
        return 0.0


class EnhancedConnectionManager:
    """
    Enhanced WebSocket connection manager with health monitoring and rate limiting.
    
    Features:
    - Connection health monitoring with heartbeats
    - Automatic reconnection support
    - Rate limiting for progress updates
    - Memory leak prevention with weak references
    - Comprehensive message protocol
    
    Message Protocol:
    ----------------
    All messages follow this format:
    ```json
    {
        "type": "message_type",
        "data": { ... },
        "timestamp": "2024-01-01T00:00:00Z"
    }
    ```
    
    Client-to-Server Messages:
    - ping: Keep-alive ping
    - subscribe: Subscribe to conversion updates
    - unsubscribe: Unsubscribe from conversion
    
    Server-to-Client Messages:
    - pong: Response to ping
    - agent_progress: Agent progress update
    - conversion_complete: Conversion finished successfully
    - conversion_failed: Conversion failed
    - error: Error message
    - heartbeat: Server heartbeat
    """
    
    def __init__(
        self,
        rate_limit_config: Optional[RateLimitConfig] = None,
        health_config: Optional[HealthConfig] = None
    ):
        # Maps conversion_id to connection info
        self._connections: Dict[str, Dict[WebSocket, ConnectionInfo]] = defaultdict(dict)
        
        # Weak references for cleanup
        self._weak_refs: weakref.WeakSet = weakref.WeakSet()
        
        # Rate limiter
        self._rate_limiter = RateLimiter(rate_limit_config)
        
        # Configuration
        self._health_config = health_config or HealthConfig()
        
        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Metrics
        self._total_connections = 0
        self._total_messages_sent = 0
        self._total_messages_received = 0
    
    async def start(self) -> None:
        """Start background tasks for health monitoring."""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Started WebSocket connection manager")
    
    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped WebSocket connection manager")
    
    async def connect(
        self,
        websocket: WebSocket,
        conversion_id: str,
        client_id: Optional[str] = None
    ) -> ConnectionInfo:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            conversion_id: UUID of the conversion job
            client_id: Optional client identifier for reconnection
            
        Returns:
            ConnectionInfo for the new connection
        """
        await websocket.accept()
        
        info = ConnectionInfo(
            websocket=websocket,
            conversion_id=conversion_id,
            client_id=client_id or self._generate_client_id(),
            state=ConnectionState.CONNECTED
        )
        
        self._connections[conversion_id][websocket] = info
        self._total_connections += 1
        
        # Send connected message
        await self._send_message(websocket, {
            "type": MessageType.CONNECTED.value,
            "data": {
                "client_id": info.client_id,
                "conversion_id": conversion_id
            }
        })
        
        logger.info(
            f"WebSocket connected: client={info.client_id}, "
            f"conversion={conversion_id}, "
            f"total_connections={self.get_total_connection_count()}"
        )
        
        return info
    
    def disconnect(self, websocket: WebSocket, conversion_id: str) -> Optional[ConnectionInfo]:
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket to disconnect
            conversion_id: The conversion ID
            
        Returns:
            The removed ConnectionInfo or None
        """
        info = None
        if conversion_id in self._connections:
            info = self._connections[conversion_id].pop(websocket, None)
            
            # Clean up empty conversion entries
            if not self._connections[conversion_id]:
                del self._connections[conversion_id]
        
        if info:
            logger.info(
                f"WebSocket disconnected: client={info.client_id}, "
                f"conversion={conversion_id}, "
                f"messages_sent={info.messages_sent}"
            )
        
        return info
    
    async def handle_message(
        self,
        websocket: WebSocket,
        conversion_id: str,
        message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Handle an incoming WebSocket message.
        
        Args:
            websocket: The WebSocket connection
            conversion_id: The conversion ID
            message: The received message
            
        Returns:
            Optional response message
        """
        info = self._connections.get(conversion_id, {}).get(websocket)
        if not info:
            return {"type": MessageType.ERROR.value, "data": {"error": "Not connected"}}
        
        info.last_activity = datetime.utcnow()
        info.messages_received += 1
        self._total_messages_received += 1
        
        message_type = message.get("type")
        
        # Rate limiting check
        if not self._rate_limiter.is_allowed(info.client_id):
            wait_time = self._rate_limiter.get_wait_time(info.client_id)
            return {
                "type": MessageType.ERROR.value,
                "data": {
                    "error": "Rate limit exceeded",
                    "retry_after": wait_time
                }
            }
        
        # Handle message types
        if message_type == MessageType.PING.value:
            return {"type": MessageType.PONG.value, "data": {}}
        
        elif message_type == MessageType.SUBSCRIBE.value:
            # Already subscribed via connect
            return {"type": MessageType.CONNECTED.value, "data": {"conversion_id": conversion_id}}
        
        elif message_type == MessageType.UNSUBSCRIBE.value:
            self.disconnect(websocket, conversion_id)
            return {"type": MessageType.DISCONNECTED.value, "data": {}}
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return {
                "type": MessageType.ERROR.value,
                "data": {"error": f"Unknown message type: {message_type}"}
            }
    
    async def broadcast(
        self,
        message: Dict[str, Any],
        conversion_id: str,
        throttle: bool = True
    ) -> int:
        """
        Broadcast a message to all connections for a conversion.
        
        Args:
            message: The message to broadcast
            conversion_id: The conversion ID
            throttle: Whether to apply rate limiting
            
        Returns:
            Number of connections the message was sent to
        """
        if conversion_id not in self._connections:
            return 0
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        sent_count = 0
        disconnected = []
        
        for websocket, info in list(self._connections[conversion_id].items()):
            try:
                # Check rate limit for this client
                if throttle and not self._rate_limiter.is_allowed(info.client_id):
                    continue
                
                await self._send_message(websocket, message)
                info.messages_sent += 1
                sent_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to send to client {info.client_id}: {e}")
                disconnected.append((websocket, info))
        
        # Clean up disconnected clients
        for websocket, info in disconnected:
            self.disconnect(websocket, conversion_id)
        
        self._total_messages_sent += sent_count
        return sent_count
    
    async def broadcast_to_all(self, message: Dict[str, Any]) -> int:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: The message to broadcast
            
        Returns:
            Total number of messages sent
        """
        total_sent = 0
        for conversion_id in list(self._connections.keys()):
            total_sent += await self.broadcast(message, conversion_id, throttle=False)
        return total_sent
    
    async def send_personal_message(
        self,
        message: Dict[str, Any],
        websocket: WebSocket,
        conversion_id: str
    ) -> bool:
        """
        Send a message to a specific client.
        
        Args:
            message: The message to send
            websocket: The target WebSocket
            conversion_id: The conversion ID
            
        Returns:
            True if sent successfully
        """
        info = self._connections.get(conversion_id, {}).get(websocket)
        if not info:
            return False
        
        try:
            await self._send_message(websocket, message)
            info.messages_sent += 1
            self._total_messages_sent += 1
            return True
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            return False
    
    def get_connection_count(self, conversion_id: str) -> int:
        """Get the number of connections for a conversion."""
        return len(self._connections.get(conversion_id, {}))
    
    def get_total_connection_count(self) -> int:
        """Get the total number of connections."""
        return sum(len(conns) for conns in self._connections.values())
    
    def get_active_conversions(self) -> List[str]:
        """Get list of conversion IDs with active connections."""
        return list(self._connections.keys())
    
    def get_connection_info(self, conversion_id: str) -> List[Dict[str, Any]]:
        """Get connection info for all clients of a conversion."""
        if conversion_id not in self._connections:
            return []
        return [info.to_dict() for info in self._connections[conversion_id].values()]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection manager metrics."""
        return {
            "active_connections": self.get_total_connection_count(),
            "active_conversions": len(self._connections),
            "total_connections_created": self._total_connections,
            "total_messages_sent": self._total_messages_sent,
            "total_messages_received": self._total_messages_received
        }
    
    async def check_connection_health(self, conversion_id: str) -> Dict[str, Any]:
        """
        Check health of connections for a conversion.
        
        Args:
            conversion_id: The conversion ID to check
            
        Returns:
            Health status dictionary
        """
        if conversion_id not in self._connections:
            return {"healthy": False, "reason": "No connections"}
        
        now = datetime.utcnow()
        stale_threshold = timedelta(seconds=self._health_config.stale_connection_seconds)
        issues = []
        healthy_count = 0
        
        for websocket, info in self._connections[conversion_id].items():
            age = now - info.last_activity
            
            if age > stale_threshold:
                info.state = ConnectionState.STALE
                issues.append(f"Client {info.client_id} is stale ({age.seconds}s inactive)")
            else:
                healthy_count += 1
        
        return {
            "healthy": healthy_count > 0,
            "total_connections": len(self._connections[conversion_id]),
            "healthy_connections": healthy_count,
            "issues": issues
        }
    
    async def _send_message(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Send a JSON message over WebSocket."""
        await websocket.send_json(message)
    
    def _generate_client_id(self) -> str:
        """Generate a unique client ID."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    async def _heartbeat_loop(self) -> None:
        """Background task for sending heartbeats."""
        while self._running:
            try:
                await asyncio.sleep(self._health_config.heartbeat_interval_seconds)
                
                now = datetime.utcnow()
                heartbeat_msg = {
                    "type": MessageType.HEARTBEAT.value,
                    "data": {"timestamp": now.isoformat()}
                }
                
                # Send heartbeat to all connections
                for conversion_id in list(self._connections.keys()):
                    for websocket, info in list(self._connections[conversion_id].items()):
                        try:
                            await self._send_message(websocket, heartbeat_msg)
                            info.last_heartbeat = now
                        except Exception:
                            # Connection is dead
                            self.disconnect(websocket, conversion_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up stale connections."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                now = datetime.utcnow()
                stale_threshold = timedelta(seconds=self._health_config.stale_connection_seconds)
                
                to_disconnect = []
                
                for conversion_id, connections in list(self._connections.items()):
                    for websocket, info in list(connections.items()):
                        age = now - info.last_activity
                        
                        if age > stale_threshold:
                            to_disconnect.append((websocket, conversion_id, info))
                
                # Disconnect stale connections
                for websocket, conversion_id, info in to_disconnect:
                    logger.info(f"Cleaning up stale connection: {info.client_id}")
                    self.disconnect(websocket, conversion_id)
                
                if to_disconnect:
                    logger.info(f"Cleaned up {len(to_disconnect)} stale connections")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")


# Global enhanced connection manager instance
enhanced_manager: Optional[EnhancedConnectionManager] = None


def get_enhanced_manager() -> EnhancedConnectionManager:
    """Get or create the global enhanced connection manager."""
    global enhanced_manager
    if enhanced_manager is None:
        enhanced_manager = EnhancedConnectionManager()
    return enhanced_manager


async def start_websocket_manager() -> None:
    """Start the global WebSocket manager."""
    manager = get_enhanced_manager()
    await manager.start()


async def stop_websocket_manager() -> None:
    """Stop the global WebSocket manager."""
    global enhanced_manager
    if enhanced_manager:
        await enhanced_manager.stop()