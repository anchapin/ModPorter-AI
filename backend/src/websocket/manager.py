"""
WebSocket connection manager for handling multiple concurrent clients.

This module provides a connection manager that:
- Maintains active WebSocket connections
- Broadcasts messages to all connected clients
- Supports connection-specific messaging
- Handles connection lifecycle (connect/disconnect)
"""

import logging
from typing import Dict, Set, List
from fastapi import WebSocket, WebSocketDisconnect
from uuid import UUID
import json

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time progress updates.

    Supports multiple concurrent connections per conversion job,
    allowing multiple clients to listen to the same conversion progress.
    """

    def __init__(self):
        # Maps conversion_id (UUID) to set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversion_id: str):
        """
        Accept a new WebSocket connection and register it for a conversion.

        Args:
            websocket: The WebSocket connection to accept
            conversion_id: UUID of the conversion job to listen to
        """
        await websocket.accept()

        if conversion_id not in self.active_connections:
            self.active_connections[conversion_id] = set()

        self.active_connections[conversion_id].add(websocket)
        logger.info(
            f"WebSocket connected for conversion {conversion_id}. "
            f"Total connections: {len(self.active_connections[conversion_id])}"
        )

    def disconnect(self, websocket: WebSocket, conversion_id: str):
        """
        Remove a WebSocket connection from the active connections.

        Args:
            websocket: The WebSocket connection to remove
            conversion_id: UUID of the conversion job
        """
        if conversion_id in self.active_connections:
            self.active_connections[conversion_id].discard(websocket)

            # Clean up empty conversion_id entries
            if not self.active_connections[conversion_id]:
                del self.active_connections[conversion_id]
                logger.info(f"All connections closed for conversion {conversion_id}")

            logger.info(
                f"WebSocket disconnected for conversion {conversion_id}. "
                f"Remaining connections: {len(self.active_connections.get(conversion_id, set()))}"
            )

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.

        Args:
            message: Dictionary message to send (will be JSON serialized)
            websocket: Specific WebSocket connection to send to
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            raise

    async def broadcast(self, message: dict, conversion_id: str):
        """
        Broadcast a message to all connected clients for a specific conversion.

        Args:
            message: Dictionary message to broadcast (will be JSON serialized)
            conversion_id: UUID of the conversion job
        """
        if conversion_id not in self.active_connections:
            logger.debug(f"No active connections for conversion {conversion_id}")
            return

        # Create a list of connections to iterate safely while modifying
        connections = list(self.active_connections[conversion_id])
        disconnected = []

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    f"Failed to send message to connection for {conversion_id}: {e}"
                )
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, conversion_id)

    async def broadcast_to_all(self, message: dict):
        """
        Broadcast a message to all connected clients across all conversions.

        Args:
            message: Dictionary message to broadcast (will be JSON serialized)
        """
        for conversion_id in list(self.active_connections.keys()):
            await self.broadcast(message, conversion_id)

    def get_connection_count(self, conversion_id: str) -> int:
        """
        Get the number of active connections for a specific conversion.

        Args:
            conversion_id: UUID of the conversion job

        Returns:
            Number of active WebSocket connections
        """
        return len(self.active_connections.get(conversion_id, set()))

    def get_total_connection_count(self) -> int:
        """
        Get the total number of active connections across all conversions.

        Returns:
            Total number of active WebSocket connections
        """
        return sum(len(conns) for conns in self.active_connections.values())

    def get_active_conversions(self) -> List[str]:
        """
        Get a list of conversion IDs with active connections.

        Returns:
            List of conversion ID strings
        """
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()
