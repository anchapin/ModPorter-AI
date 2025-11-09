"""
Production WebSocket Server
Real-time features for conversion progress, collaboration, and notifications
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import asyncpg
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """WebSocket message types"""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    CONVERSION_UPDATE = "conversion_update"
    COLLABORATION = "collaboration"
    NOTIFICATION = "notification"
    HEARTBEAT = "heartbeat"
    ERROR = "error"

@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: datetime
    message_id: str = None
    session_id: str = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'type': self.type.value,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'message_id': self.message_id,
            'session_id': self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebSocketMessage':
        """Create from dictionary"""
        return cls(
            type=MessageType(data['type']),
            data=data['data'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            message_id=data.get('message_id'),
            session_id=data.get('session_id')
        )

class ConnectionManager:
    """Manages WebSocket connections and subscriptions"""
    
    def __init__(self, redis_client: redis.Redis):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        self.subscriptions: Dict[str, Set[str]] = {}  # channel -> set of connection_ids
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.redis = redis_client
        
    async def connect(self, websocket: WebSocket, user_id: str, session_id: str = None) -> str:
        """Connect a new WebSocket client"""
        connection_id = str(uuid.uuid4())
        
        # Accept connection
        await websocket.accept()
        
        # Store connection
        self.active_connections[connection_id] = websocket
        
        # Update user sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(connection_id)
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            'user_id': user_id,
            'session_id': session_id or connection_id,
            'connected_at': datetime.utcnow(),
            'last_heartbeat': datetime.utcnow()
        }
        
        # Store in Redis for multi-server support
        await self._store_connection_in_redis(connection_id, user_id, session_id)
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
        
        # Send welcome message
        welcome_msg = WebSocketMessage(
            type=MessageType.CONNECT,
            data={'connection_id': connection_id, 'user_id': user_id},
            timestamp=datetime.utcnow(),
            session_id=session_id
        )
        await self.send_personal_message(welcome_msg, connection_id)
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket client"""
        if connection_id not in self.active_connections:
            return
        
        # Get metadata before removal
        metadata = self.connection_metadata.get(connection_id, {})
        user_id = metadata.get('user_id')
        
        # Remove from active connections
        del self.active_connections[connection_id]
        
        # Remove from user sessions
        if user_id and user_id in self.user_sessions:
            self.user_sessions[user_id].discard(connection_id)
            if not self.user_sessions[user_id]:
                del self.user_sessions[user_id]
        
        # Remove subscriptions
        for channel, subscribers in self.subscriptions.items():
            subscribers.discard(connection_id)
        
        # Remove metadata
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        # Remove from Redis
        await self._remove_connection_from_redis(connection_id)
        
        logger.info(f"WebSocket disconnected: {connection_id} for user {user_id}")
    
    async def send_personal_message(self, message: WebSocketMessage, connection_id: str):
        """Send message to specific connection"""
        if connection_id not in self.active_connections:
            return
        
        websocket = self.active_connections[connection_id]
        if websocket.client_state == WebSocketState.DISCONNECTED:
            await self.disconnect(connection_id)
            return
        
        try:
            await websocket.send_text(json.dumps(message.to_dict()))
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            await self.disconnect(connection_id)
    
    async def send_user_message(self, message: WebSocketMessage, user_id: str):
        """Send message to all connections for a user"""
        if user_id not in self.user_sessions:
            return
        
        # Send to each connection for the user
        for connection_id in list(self.user_sessions[user_id]):
            await self.send_personal_message(message, connection_id)
    
    async def subscribe(self, connection_id: str, channel: str):
        """Subscribe connection to channel"""
        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()
        self.subscriptions[channel].add(connection_id)
        
        # Store in Redis
        await self.redis.sadd(f"ws_subscriptions:{channel}", connection_id)
        
        logger.info(f"Connection {connection_id} subscribed to {channel}")
    
    async def unsubscribe(self, connection_id: str, channel: str):
        """Unsubscribe connection from channel"""
        if channel in self.subscriptions:
            self.subscriptions[channel].discard(connection_id)
            if not self.subscriptions[channel]:
                del self.subscriptions[channel]
        
        # Remove from Redis
        await self.redis.srem(f"ws_subscriptions:{channel}", connection_id)
        
        logger.info(f"Connection {connection_id} unsubscribed from {channel}")
    
    async def broadcast_to_channel(self, message: WebSocketMessage, channel: str):
        """Broadcast message to all subscribers of a channel"""
        if channel not in self.subscriptions:
            return
        
        # Send to local subscribers
        for connection_id in list(self.subscriptions[channel]):
            await self.send_personal_message(message, connection_id)
        
        # Broadcast to other servers via Redis
        await self.redis.publish(f"ws_channel:{channel}", json.dumps(message.to_dict()))
    
    async def handle_redis_broadcast(self, channel: str, message: str):
        """Handle broadcast from Redis"""
        try:
            message_data = json.loads(message)
            ws_message = WebSocketMessage.from_dict(message_data)
            
            # Extract channel name from Redis channel
            ws_channel = channel.replace("ws_channel:", "")
            
            # Send to local subscribers
            if ws_channel in self.subscriptions:
                for connection_id in list(self.subscriptions[ws_channel]):
                    await self.send_personal_message(ws_message, connection_id)
                    
        except Exception as e:
            logger.error(f"Failed to handle Redis broadcast: {e}")
    
    async def _store_connection_in_redis(self, connection_id: str, user_id: str, session_id: str):
        """Store connection info in Redis for multi-server support"""
        connection_data = {
            'connection_id': connection_id,
            'user_id': user_id,
            'session_id': session_id,
            'server_id': await self._get_server_id(),
            'connected_at': datetime.utcnow().isoformat()
        }
        await self.redis.hset(f"ws_connections:{connection_id}", mapping=connection_data)
        await self.redis.expire(f"ws_connections:{connection_id}", 3600)  # 1 hour TTL
    
    async def _remove_connection_from_redis(self, connection_id: str):
        """Remove connection info from Redis"""
        await self.redis.delete(f"ws_connections:{connection_id}")
    
    async def _get_server_id(self) -> str:
        """Get unique server ID"""
        server_id = await self.redis.get("ws_server_id")
        if not server_id:
            server_id = str(uuid.uuid4())
            await self.redis.set("ws_server_id", server_id, ex=86400)  # 24 hours
        return server_id
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            'active_connections': len(self.active_connections),
            'connected_users': len(self.user_sessions),
            'active_subscriptions': len(self.subscriptions),
            'subscriptions_by_channel': {
                channel: len(subscribers) 
                for channel, subscribers in self.subscriptions.items()
            }
        }

class ConversionProgressTracker:
    """Tracks and broadcasts conversion progress"""
    
    def __init__(self, connection_manager: ConnectionManager, redis_client: redis.Redis):
        self.connection_manager = connection_manager
        self.redis = redis_client
    
    async def update_conversion_progress(
        self,
        conversion_id: str,
        user_id: str,
        status: str,
        progress: int = None,
        message: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Update and broadcast conversion progress"""
        # Update progress in Redis
        progress_data = {
            'conversion_id': conversion_id,
            'user_id': user_id,
            'status': status,
            'progress': progress,
            'message': message,
            'metadata': metadata or {},
            'updated_at': datetime.utcnow().isoformat()
        }
        
        await self.redis.hset(
            f"conversion_progress:{conversion_id}",
            mapping={k: json.dumps(v) if isinstance(v, dict) else str(v) for k, v in progress_data.items()}
        )
        await self.redis.expire(f"conversion_progress:{conversion_id}", 86400)  # 24 hours
        
        # Create WebSocket message
        ws_message = WebSocketMessage(
            type=MessageType.CONVERSION_UPDATE,
            data=progress_data,
            timestamp=datetime.utcnow()
        )
        
        # Send to user
        await self.connection_manager.send_user_message(ws_message, user_id)
        
        # Broadcast to conversion channel
        await self.connection_manager.broadcast_to_channel(
            ws_message, 
            f"conversion:{conversion_id}"
        )
        
        logger.info(f"Updated progress for conversion {conversion_id}: {status} ({progress}%)")
    
    async def get_conversion_progress(self, conversion_id: str) -> Optional[Dict[str, Any]]:
        """Get current conversion progress"""
        try:
            data = await self.redis.hgetall(f"conversion_progress:{conversion_id}")
            if data:
                # Parse JSON fields
                result = {}
                for key, value in data.items():
                    try:
                        if key in ['metadata']:
                            result[key] = json.loads(value)
                        else:
                            result[key] = value
                    except:
                        result[key] = value
                return result
        except Exception as e:
            logger.error(f"Failed to get conversion progress: {e}")
        return None

class CollaborationManager:
    """Manages real-time collaboration features"""
    
    def __init__(self, connection_manager: ConnectionManager, redis_client: redis.Redis):
        self.connection_manager = connection_manager
        self.redis = redis_client
    
    async def join_collaboration(self, user_id: str, project_id: str, connection_id: str):
        """User joins collaboration session"""
        # Add user to project collaboration
        await self.redis.sadd(f"collaboration:{project_id}:users", user_id)
        await self.redis.hset(
            f"collaboration:{project_id}:user:{user_id}",
            mapping={
                'connection_id': connection_id,
                'joined_at': datetime.utcnow().isoformat(),
                'last_seen': datetime.utcnow().isoformat()
            }
        )
        
        # Subscribe to project channel
        await self.connection_manager.subscribe(connection_id, f"project:{project_id}")
        
        # Notify others
        notification = WebSocketMessage(
            type=MessageType.COLLABORATION,
            data={
                'action': 'user_joined',
                'user_id': user_id,
                'project_id': project_id
            },
            timestamp=datetime.utcnow()
        )
        await self.connection_manager.broadcast_to_channel(
            notification,
            f"project:{project_id}"
        )
    
    async def leave_collaboration(self, user_id: str, project_id: str, connection_id: str):
        """User leaves collaboration session"""
        # Remove user from project collaboration
        await self.redis.srem(f"collaboration:{project_id}:users", user_id)
        await self.redis.delete(f"collaboration:{project_id}:user:{user_id}")
        
        # Unsubscribe from project channel
        await self.connection_manager.unsubscribe(connection_id, f"project:{project_id}")
        
        # Notify others
        notification = WebSocketMessage(
            type=MessageType.COLLABORATION,
            data={
                'action': 'user_left',
                'user_id': user_id,
                'project_id': project_id
            },
            timestamp=datetime.utcnow()
        )
        await self.connection_manager.broadcast_to_channel(
            notification,
            f"project:{project_id}"
        )
    
    async def send_cursor_update(
        self,
        user_id: str,
        project_id: str,
        cursor_position: Dict[str, Any]
    ):
        """Broadcast cursor position update"""
        # Update user's cursor position
        await self.redis.hset(
            f"collaboration:{project_id}:cursor:{user_id}",
            mapping={
                **cursor_position,
                'updated_at': datetime.utcnow().isoformat()
            }
        )
        await self.redis.expire(f"collaboration:{project_id}:cursor:{user_id}", 300)  # 5 minutes
        
        # Broadcast to project
        notification = WebSocketMessage(
            type=MessageType.COLLABORATION,
            data={
                'action': 'cursor_update',
                'user_id': user_id,
                'project_id': project_id,
                'cursor': cursor_position
            },
            timestamp=datetime.utcnow()
        )
        await self.connection_manager.broadcast_to_channel(
            notification,
            f"project:{project_id}"
        )
    
    async def send_edit_operation(
        self,
        user_id: str,
        project_id: str,
        operation: Dict[str, Any]
    ):
        """Broadcast edit operation"""
        # Store operation in history
        operation_id = str(uuid.uuid4())
        await self.redis.hset(
            f"collaboration:{project_id}:operations:{operation_id}",
            mapping={
                **operation,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        await self.redis.expire(f"collaboration:{project_id}:operations:{operation_id}", 3600)  # 1 hour
        
        # Add to operations list
        await self.redis.lpush(f"collaboration:{project_id}:operations", operation_id)
        await self.redis.ltrim(f"collaboration:{project_id}:operations", 0, 999)  # Keep last 1000
        
        # Broadcast to project
        notification = WebSocketMessage(
            type=MessageType.COLLABORATION,
            data={
                'action': 'edit_operation',
                'operation_id': operation_id,
                'user_id': user_id,
                'project_id': project_id,
                'operation': operation
            },
            timestamp=datetime.utcnow()
        )
        await self.connection_manager.broadcast_to_channel(
            notification,
            f"project:{project_id}"
        )
    
    async def get_project_collaborators(self, project_id: str) -> List[Dict[str, Any]]:
        """Get active collaborators for a project"""
        try:
            users = await self.redis.smembers(f"collaboration:{project_id}:users")
            collaborators = []
            
            for user_id in users:
                user_data = await self.redis.hgetall(f"collaboration:{project_id}:user:{user_id}")
                if user_data:
                    cursor_data = await self.redis.hgetall(f"collaboration:{project_id}:cursor:{user_id}")
                    collaborators.append({
                        'user_id': user_id,
                        'connection_id': user_data.get('connection_id'),
                        'joined_at': user_data.get('joined_at'),
                        'cursor': dict(cursor_data) if cursor_data else None
                    })
            
            return collaborators
        except Exception as e:
            logger.error(f"Failed to get project collaborators: {e}")
            return []

class NotificationManager:
    """Manages real-time notifications"""
    
    def __init__(self, connection_manager: ConnectionManager, redis_client: redis.Redis):
        self.connection_manager = connection_manager
        self.redis = redis_client
    
    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
        metadata: Dict[str, Any] = None
    ):
        """Send notification to user"""
        notification_data = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'title': title,
            'message': message,
            'type': notification_type,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat(),
            'read': False
        }
        
        # Store notification
        await self.redis.hset(
            f"notifications:{user_id}:{notification_data['id']}",
            mapping={k: json.dumps(v) if isinstance(v, dict) else str(v) for k, v in notification_data.items()}
        )
        
        # Add to user's notification list
        await self.redis.lpush(f"notifications:{user_id}", notification_data['id'])
        await self.redis.ltrim(f"notifications:{user_id}", 0, 99)  # Keep last 100
        
        # Send WebSocket notification
        ws_message = WebSocketMessage(
            type=MessageType.NOTIFICATION,
            data=notification_data,
            timestamp=datetime.utcnow()
        )
        await self.connection_manager.send_user_message(ws_message, user_id)
        
        logger.info(f"Sent notification to user {user_id}: {title}")
    
    async def get_notifications(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's notifications"""
        try:
            notification_ids = await self.redis.lrange(f"notifications:{user_id}", 0, limit - 1)
            notifications = []
            
            for notification_id in notification_ids:
                notification_data = await self.redis.hgetall(f"notifications:{user_id}:{notification_id}")
                if notification_data:
                    # Parse JSON fields
                    notification = {}
                    for key, value in notification_data.items():
                        try:
                            if key in ['metadata']:
                                notification[key] = json.loads(value)
                            else:
                                notification[key] = value
                        except:
                            notification[key] = value
                    notifications.append(notification)
            
            return notifications
        except Exception as e:
            logger.error(f"Failed to get notifications for user {user_id}: {e}")
            return []
    
    async def mark_notification_read(self, user_id: str, notification_id: str):
        """Mark notification as read"""
        await self.redis.hset(f"notifications:{user_id}:{notification_id}", "read", "true")

class ProductionWebSocketServer:
    """Production WebSocket server with all features"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.connection_manager = ConnectionManager(redis_client)
        self.progress_tracker = ConversionProgressTracker(self.connection_manager, redis_client)
        self.collaboration_manager = CollaborationManager(self.connection_manager, redis_client)
        self.notification_manager = NotificationManager(self.connection_manager, redis_client)
        
        self.heartbeat_interval = 30  # seconds
        
    async def handle_websocket(self, websocket: WebSocket, user_id: str, session_id: str = None):
        """Handle WebSocket connection"""
        connection_id = await self.connection_manager.connect(websocket, user_id, session_id)
        
        try:
            while True:
                # Wait for message with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=self.heartbeat_interval + 10)
                
                try:
                    # Parse message
                    message_data = json.loads(data)
                    message = WebSocketMessage.from_dict(message_data)
                    message.session_id = session_id
                    
                    await self._handle_message(message, connection_id, user_id)
                    
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received from {connection_id}")
                except Exception as e:
                    logger.error(f"Error handling message from {connection_id}: {e}")
                    
        except asyncio.TimeoutError:
            logger.info(f"WebSocket timeout for {connection_id}")
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnect for {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
        finally:
            await self.connection_manager.disconnect(connection_id)
    
    async def _handle_message(self, message: WebSocketMessage, connection_id: str, user_id: str):
        """Handle incoming WebSocket message"""
        try:
            if message.type == MessageType.SUBSCRIBE:
                channel = message.data.get('channel')
                if channel:
                    await self.connection_manager.subscribe(connection_id, channel)
                    
            elif message.type == MessageType.UNSUBSCRIBE:
                channel = message.data.get('channel')
                if channel:
                    await self.connection_manager.unsubscribe(connection_id, channel)
                    
            elif message.type == MessageType.HEARTBEAT:
                # Update last heartbeat
                if connection_id in self.connection_manager.connection_metadata:
                    self.connection_manager.connection_metadata[connection_id]['last_heartbeat'] = datetime.utcnow()
                
                # Send heartbeat response
                heartbeat_response = WebSocketMessage(
                    type=MessageType.HEARTBEAT,
                    data={'timestamp': datetime.utcnow().isoformat()},
                    timestamp=datetime.utcnow()
                )
                await self.connection_manager.send_personal_message(heartbeat_response, connection_id)
                
            elif message.type == MessageType.COLLABORATION:
                action = message.data.get('action')
                project_id = message.data.get('project_id')
                
                if action == 'join_project' and project_id:
                    await self.collaboration_manager.join_collaboration(user_id, project_id, connection_id)
                elif action == 'leave_project' and project_id:
                    await self.collaboration_manager.leave_collaboration(user_id, project_id, connection_id)
                elif action == 'cursor_update' and project_id:
                    cursor_position = message.data.get('cursor', {})
                    await self.collaboration_manager.send_cursor_update(user_id, project_id, cursor_position)
                elif action == 'edit_operation' and project_id:
                    operation = message.data.get('operation', {})
                    await self.collaboration_manager.send_edit_operation(user_id, project_id, operation)
            
            else:
                logger.warning(f"Unhandled message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error handling message {message.type}: {e}")
    
    async def start_heartbeat_monitor(self):
        """Start heartbeat monitoring task"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Check for stale connections
                current_time = datetime.utcnow()
                stale_connections = []
                
                for connection_id, metadata in self.connection_manager.connection_metadata.items():
                    last_heartbeat = metadata.get('last_heartbeat')
                    if last_heartbeat:
                        time_diff = (current_time - last_heartbeat).total_seconds()
                        if time_diff > (self.heartbeat_interval * 2):
                            stale_connections.append(connection_id)
                
                # Disconnect stale connections
                for connection_id in stale_connections:
                    logger.warning(f"Disconnecting stale connection: {connection_id}")
                    await self.connection_manager.disconnect(connection_id)
                    
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
    
    async def start_redis_listener(self):
        """Start Redis pub/sub listener for cross-server communication"""
        pubsub = self.redis.pubsub()
        
        # Subscribe to channels
        channels = ["ws_channel:*"]  # This would be expanded with actual channel patterns
        await pubsub.psubscribe(*channels)
        
        async for message in pubsub.listen():
            if message['type'] == 'pmessage':
                channel = message['channel']
                data = message['data']
                await self.connection_manager.handle_redis_broadcast(channel, data)
    
    async def get_server_stats(self) -> Dict[str, Any]:
        """Get comprehensive server statistics"""
        return {
            'connection_stats': await self.connection_manager.get_connection_stats(),
            'timestamp': datetime.utcnow().isoformat()
        }
