"""
Real-time Collaboration Service for Knowledge Graph Editing

This service provides real-time collaboration capabilities for multiple users
editing knowledge graph simultaneously, including conflict resolution,
change tracking, and live updates.
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.knowledge_graph_crud import (
    KnowledgeNodeCRUD,
    KnowledgeRelationshipCRUD,
    ConversionPatternCRUD,
)

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of graph operations."""

    CREATE_NODE = "create_node"
    UPDATE_NODE = "update_node"
    DELETE_NODE = "delete_node"
    CREATE_RELATIONSHIP = "create_relationship"
    UPDATE_RELATIONSHIP = "update_relationship"
    DELETE_RELATIONSHIP = "delete_relationship"
    CREATE_PATTERN = "create_pattern"
    UPDATE_PATTERN = "update_pattern"
    DELETE_PATTERN = "delete_pattern"


class ConflictType(Enum):
    """Types of conflicts in collaboration."""

    EDIT_CONFLICT = "edit_conflict"
    DELETE_CONFLICT = "delete_conflict"
    RELATION_CONFLICT = "relation_conflict"
    VERSION_CONFLICT = "version_conflict"
    SCHEMA_CONFLICT = "schema_conflict"


class ChangeStatus(Enum):
    """Status of changes."""

    PENDING = "pending"
    APPLIED = "applied"
    CONFLICTED = "conflicted"
    REJECTED = "rejected"
    MERGED = "merged"


@dataclass
class CollaborativeOperation:
    """Operation performed by a collaborator."""

    operation_id: str
    operation_type: OperationType
    user_id: str
    user_name: str
    timestamp: datetime
    target_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    previous_data: Dict[str, Any] = field(default_factory=dict)
    status: ChangeStatus = ChangeStatus.PENDING
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    resolved_by: Optional[str] = None
    resolution: Optional[str] = None


@dataclass
class CollaborationSession:
    """Active collaboration session."""

    session_id: str
    graph_id: str
    created_at: datetime
    active_users: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    operations: List[CollaborativeOperation] = field(default_factory=list)
    pending_changes: Dict[str, CollaborativeOperation] = field(default_factory=dict)
    resolved_conflicts: List[Dict[str, Any]] = field(default_factory=list)
    websockets: Dict[str, WebSocket] = field(default_factory=dict)


@dataclass
class ConflictResolution:
    """Resolution for a collaboration conflict."""

    conflict_id: str
    conflict_type: ConflictType
    operations_involved: List[str]
    resolution_strategy: str
    resolved_by: str
    resolved_at: datetime
    resolution_data: Dict[str, Any] = field(default_factory=dict)


class RealtimeCollaborationService:
    """Real-time collaboration service for knowledge graph editing."""

    def __init__(self):
        self.active_sessions: Dict[str, CollaborationSession] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.operation_history: List[CollaborativeOperation] = []
        self.conflict_resolutions: List[ConflictResolution] = []
        self.websocket_connections: Dict[str, WebSocket] = {}

    async def create_collaboration_session(
        self, graph_id: str, user_id: str, user_name: str, db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Create a new collaboration session.

        Args:
            graph_id: ID of the knowledge graph
            user_id: ID of the user creating the session
            user_name: Name of the user
            db: Database session

        Returns:
            Session creation result
        """
        try:
            session_id = str(uuid.uuid4())

            # Create new session
            session = CollaborationSession(
                session_id=session_id, graph_id=graph_id, created_at=datetime.utcnow()
            )

            # Add creator as first active user
            session.active_users[user_id] = {
                "user_id": user_id,
                "user_name": user_name,
                "joined_at": datetime.utcnow(),
                "role": "creator",
                "color": self._generate_user_color(user_id),
                "cursor_position": None,
                "last_activity": datetime.utcnow(),
            }

            # Store session
            self.active_sessions[session_id] = session
            self.user_sessions[user_id] = session_id

            return {
                "success": True,
                "session_id": session_id,
                "graph_id": graph_id,
                "user_info": session.active_users[user_id],
                "created_at": session.created_at.isoformat(),
                "message": "Collaboration session created successfully",
            }

        except Exception as e:
            logger.error(f"Error creating collaboration session: {e}")
            return {"success": False, "error": f"Session creation failed: {str(e)}"}

    async def join_collaboration_session(
        self,
        session_id: str,
        user_id: str,
        user_name: str,
        websocket: WebSocket,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Join an existing collaboration session.

        Args:
            session_id: ID of the session to join
            user_id: ID of the user joining
            user_name: Name of the user
            websocket: WebSocket connection for real-time updates
            db: Database session

        Returns:
            Join session result
        """
        try:
            # Check if session exists
            if session_id not in self.active_sessions:
                return {"success": False, "error": "Session not found"}

            session = self.active_sessions[session_id]

            # Check if user already in session
            if user_id in session.active_users:
                return {"success": False, "error": "User already in session"}

            # Add user to session
            session.active_users[user_id] = {
                "user_id": user_id,
                "user_name": user_name,
                "joined_at": datetime.utcnow(),
                "role": "collaborator",
                "color": self._generate_user_color(user_id),
                "cursor_position": None,
                "last_activity": datetime.utcnow(),
            }

            # Store WebSocket connection
            session.websockets[user_id] = websocket
            self.websocket_connections[user_id] = websocket

            # Update user sessions
            self.user_sessions[user_id] = session_id

            # Broadcast user join to other users
            await self._broadcast_message(
                session_id,
                {
                    "type": "user_joined",
                    "user_info": session.active_users[user_id],
                    "timestamp": datetime.utcnow().isoformat(),
                },
                exclude_user=user_id,
            )

            # Send current session state to new user
            await self._send_session_state(user_id, session_id, db)

            return {
                "success": True,
                "session_id": session_id,
                "user_info": session.active_users[user_id],
                "active_users": list(session.active_users.values()),
                "message": "Joined collaboration session successfully",
            }

        except Exception as e:
            logger.error(f"Error joining collaboration session: {e}")
            return {"success": False, "error": f"Failed to join session: {str(e)}"}

    async def leave_collaboration_session(
        self, user_id: str, db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Leave a collaboration session.

        Args:
            user_id: ID of the user leaving
            db: Database session

        Returns:
            Leave session result
        """
        try:
            # Get user's session
            session_id = self.user_sessions.get(user_id)
            if not session_id or session_id not in self.active_sessions:
                return {"success": False, "error": "User not in active session"}

            session = self.active_sessions[session_id]

            # Remove user from session
            user_info = session.active_users.pop(user_id, None)

            # Remove WebSocket connection
            session.websockets.pop(user_id, None)
            self.websocket_connections.pop(user_id, None)

            # Update user sessions
            self.user_sessions.pop(user_id, None)

            # Broadcast user leave to other users
            if user_info:
                await self._broadcast_message(
                    session_id,
                    {
                        "type": "user_left",
                        "user_info": user_info,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            # Check if session should be closed
            if len(session.active_users) == 0:
                # Store session in history and remove
                await self._archive_session(session_id)
                del self.active_sessions[session_id]

            return {
                "success": True,
                "session_id": session_id,
                "message": "Left collaboration session successfully",
            }

        except Exception as e:
            logger.error(f"Error leaving collaboration session: {e}")
            return {"success": False, "error": f"Failed to leave session: {str(e)}"}

    async def apply_operation(
        self,
        session_id: str,
        user_id: str,
        operation_type: OperationType,
        target_id: Optional[str],
        data: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Apply an operation to the knowledge graph with conflict detection.

        Args:
            session_id: ID of the collaboration session
            user_id: ID of the user applying the operation
            operation_type: Type of operation
            target_id: ID of the target item (if applicable)
            data: Operation data
            db: Database session

        Returns:
            Operation application result
        """
        try:
            # Validate session and user
            if session_id not in self.active_sessions:
                return {"success": False, "error": "Session not found"}

            session = self.active_sessions[session_id]
            if user_id not in session.active_users:
                return {"success": False, "error": "User not in session"}

            # Create operation
            operation_id = str(uuid.uuid4())
            operation = CollaborativeOperation(
                operation_id=operation_id,
                operation_type=operation_type,
                user_id=user_id,
                user_name=session.active_users[user_id]["user_name"],
                timestamp=datetime.utcnow(),
                target_id=target_id,
                data=data,
            )

            # Get previous data for conflict detection
            if target_id and operation_type in [
                OperationType.UPDATE_NODE,
                OperationType.UPDATE_RELATIONSHIP,
                OperationType.UPDATE_PATTERN,
            ]:
                operation.previous_data = await self._get_current_data(
                    operation_type, target_id, db
                )

            # Detect conflicts
            conflicts = await self._detect_conflicts(operation, session, db)
            if conflicts:
                operation.status = ChangeStatus.CONFLICTED
                operation.conflicts = conflicts
                session.pending_changes[operation_id] = operation

                # Broadcast conflict to users
                await self._broadcast_message(
                    session_id,
                    {
                        "type": "conflict_detected",
                        "operation": {
                            "operation_id": operation_id,
                            "operation_type": operation_type.value,
                            "user_id": user_id,
                            "user_name": operation.user_name,
                            "target_id": target_id,
                            "conflicts": conflicts,
                        },
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

                return {
                    "success": False,
                    "operation_id": operation_id,
                    "conflicts": conflicts,
                    "message": "Operation conflicts with existing changes",
                }

            # Apply operation
            operation.status = ChangeStatus.APPLIED
            result = await self._execute_operation(operation, db)

            # Add to session operations
            session.operations.append(operation)

            # Broadcast operation to all users
            await self._broadcast_message(
                session_id,
                {
                    "type": "operation_applied",
                    "operation": {
                        "operation_id": operation_id,
                        "operation_type": operation_type.value,
                        "user_id": user_id,
                        "user_name": operation.user_name,
                        "target_id": target_id,
                        "data": data,
                        "result": result,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            # Add to operation history
            self.operation_history.append(operation)

            return {
                "success": True,
                "operation_id": operation_id,
                "result": result,
                "message": "Operation applied successfully",
            }

        except Exception as e:
            logger.error(f"Error applying operation: {e}")
            return {"success": False, "error": f"Operation failed: {str(e)}"}

    async def resolve_conflict(
        self,
        session_id: str,
        user_id: str,
        conflict_id: str,
        resolution_strategy: str,
        resolution_data: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Resolve a conflict in the collaboration session.

        Args:
            session_id: ID of the collaboration session
            user_id: ID of the user resolving the conflict
            conflict_id: ID of the conflict to resolve
            resolution_strategy: Strategy for resolving the conflict
            resolution_data: Additional resolution data
            db: Database session

        Returns:
            Conflict resolution result
        """
        try:
            # Validate session and user
            if session_id not in self.active_sessions:
                return {"success": False, "error": "Session not found"}

            session = self.active_sessions[session_id]
            if user_id not in session.active_users:
                return {"success": False, "error": "User not in session"}

            # Find conflict
            conflict_operation = None
            for op_id, op in session.pending_changes.items():
                if op_id == conflict_id:
                    conflict_operation = op
                    break

            if not conflict_operation:
                return {"success": False, "error": "Conflict not found"}

            # Apply resolution strategy
            resolution_result = await self._apply_conflict_resolution(
                conflict_operation, resolution_strategy, resolution_data, db
            )

            if not resolution_result["success"]:
                return resolution_result

            # Update operation
            conflict_operation.resolved_by = user_id
            conflict_operation.resolution = resolution_strategy
            conflict_operation.status = ChangeStatus.MERGED

            # Create conflict resolution record
            conflict_resolution = ConflictResolution(
                conflict_id=conflict_id,
                conflict_type=ConflictType.EDIT_CONFLICT,  # Simplified
                operations_involved=[conflict_id],
                resolution_strategy=resolution_strategy,
                resolved_by=user_id,
                resolved_at=datetime.utcnow(),
                resolution_data=resolution_data,
            )

            session.resolved_conflicts.append(
                {
                    "conflict_id": conflict_id,
                    "resolved_by": user_id,
                    "resolved_at": datetime.utcnow().isoformat(),
                    "resolution_strategy": resolution_strategy,
                }
            )

            # Remove from pending changes
            session.pending_changes.pop(conflict_id, None)

            # Add to global conflict resolutions
            self.conflict_resolutions.append(conflict_resolution)

            # Broadcast resolution
            await self._broadcast_message(
                session_id,
                {
                    "type": "conflict_resolved",
                    "conflict_id": conflict_id,
                    "resolved_by": session.active_users[user_id]["user_name"],
                    "resolution_strategy": resolution_strategy,
                    "result": resolution_result["result"],
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            return {
                "success": True,
                "conflict_id": conflict_id,
                "resolution_strategy": resolution_strategy,
                "result": resolution_result["result"],
                "message": "Conflict resolved successfully",
            }

        except Exception as e:
            logger.error(f"Error resolving conflict: {e}")
            return {"success": False, "error": f"Conflict resolution failed: {str(e)}"}

    async def get_session_state(
        self, session_id: str, db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get the current state of a collaboration session.

        Args:
            session_id: ID of the session
            db: Database session

        Returns:
            Current session state
        """
        try:
            if session_id not in self.active_sessions:
                return {"success": False, "error": "Session not found"}

            session = self.active_sessions[session_id]

            # Get current graph state
            graph_state = await self._get_graph_state(session.graph_id, db)

            return {
                "success": True,
                "session_id": session_id,
                "graph_id": session.graph_id,
                "created_at": session.created_at.isoformat(),
                "active_users": list(session.active_users.values()),
                "operations_count": len(session.operations),
                "pending_changes_count": len(session.pending_changes),
                "resolved_conflicts_count": len(session.resolved_conflicts),
                "graph_state": graph_state,
                "recent_operations": [
                    {
                        "operation_id": op.operation_id,
                        "operation_type": op.operation_type.value,
                        "user_name": op.user_name,
                        "timestamp": op.timestamp.isoformat(),
                        "status": op.status.value,
                    }
                    for op in session.operations[-10:]  # Last 10 operations
                ],
            }

        except Exception as e:
            logger.error(f"Error getting session state: {e}")
            return {"success": False, "error": f"Failed to get session state: {str(e)}"}

    async def get_user_activity(
        self, session_id: str, user_id: str, minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Get activity for a specific user in a session.

        Args:
            session_id: ID of the session
            user_id: ID of the user
            minutes: Number of minutes to look back

        Returns:
            User activity data
        """
        try:
            if session_id not in self.active_sessions:
                return {"success": False, "error": "Session not found"}

            session = self.active_sessions[session_id]
            if user_id not in session.active_users:
                return {"success": False, "error": "User not in session"}

            # Calculate time cutoff
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

            # Filter user operations
            user_operations = [
                op
                for op in session.operations
                if op.user_id == user_id and op.timestamp >= cutoff_time
            ]

            # Calculate activity metrics
            operations_by_type = {}
            for op in user_operations:
                op_type = op.operation_type.value
                operations_by_type[op_type] = operations_by_type.get(op_type, 0) + 1

            return {
                "success": True,
                "session_id": session_id,
                "user_id": user_id,
                "user_name": session.active_users[user_id]["user_name"],
                "activity_period_minutes": minutes,
                "total_operations": len(user_operations),
                "operations_by_type": operations_by_type,
                "last_activity": max(
                    (op.timestamp for op in user_operations),
                    default=session.active_users[user_id]["joined_at"],
                ).isoformat(),
                "is_active": (
                    datetime.utcnow() - session.active_users[user_id]["last_activity"]
                ).total_seconds()
                < 300,  # Active if last activity < 5 minutes ago
            }

        except Exception as e:
            logger.error(f"Error getting user activity: {e}")
            return {"success": False, "error": f"Failed to get user activity: {str(e)}"}

    async def handle_websocket_message(
        self, user_id: str, message: Dict[str, Any], db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Handle WebSocket message from a user.

        Args:
            user_id: ID of the user
            message: WebSocket message
            db: Database session

        Returns:
            Message handling result
        """
        try:
            # Get user's session
            session_id = self.user_sessions.get(user_id)
            if not session_id or session_id not in self.active_sessions:
                return {"success": False, "error": "User not in active session"}

            session = self.active_sessions[session_id]

            # Update last activity
            if user_id in session.active_users:
                session.active_users[user_id]["last_activity"] = datetime.utcnow()

            # Handle message types
            message_type = message.get("type")

            if message_type == "cursor_position":
                # Update cursor position
                cursor_data = message.get("cursor_position", {})
                session.active_users[user_id]["cursor_position"] = cursor_data

                # Broadcast to other users
                await self._broadcast_message(
                    session_id,
                    {
                        "type": "cursor_update",
                        "user_id": user_id,
                        "cursor_position": cursor_data,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    exclude_user=user_id,
                )

                return {"success": True, "message": "Cursor position updated"}

            elif message_type == "selection_change":
                # Handle selection change
                selection_data = message.get("selection", {})

                # Broadcast to other users
                await self._broadcast_message(
                    session_id,
                    {
                        "type": "selection_update",
                        "user_id": user_id,
                        "selection": selection_data,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    exclude_user=user_id,
                )

                return {"success": True, "message": "Selection updated"}

            elif message_type == "operation":
                # Handle graph operation
                operation_type = OperationType(message.get("operation_type"))
                target_id = message.get("target_id")
                data = message.get("data", {})

                return await self.apply_operation(
                    session_id, user_id, operation_type, target_id, data, db
                )

            elif message_type == "conflict_resolution":
                # Handle conflict resolution
                conflict_id = message.get("conflict_id")
                resolution_strategy = message.get("resolution_strategy")
                resolution_data = message.get("resolution_data", {})

                return await self.resolve_conflict(
                    session_id,
                    user_id,
                    conflict_id,
                    resolution_strategy,
                    resolution_data,
                    db,
                )

            else:
                return {
                    "success": False,
                    "error": f"Unknown message type: {message_type}",
                }

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            return {"success": False, "error": f"Message handling failed: {str(e)}"}

    async def handle_websocket_disconnect(self, user_id: str) -> Dict[str, Any]:
        """
        Handle WebSocket disconnection.

        Args:
            user_id: ID of the user who disconnected

        Returns:
            Disconnect handling result
        """
        try:
            # Remove WebSocket connection
            self.websocket_connections.pop(user_id, None)

            # Update session if user was in one
            session_id = self.user_sessions.get(user_id)
            if session_id and session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session.websockets.pop(user_id, None)

                # Mark user as inactive but keep them in session
                if user_id in session.active_users:
                    session.active_users[user_id]["status"] = "disconnected"

                # Broadcast disconnect to other users
                await self._broadcast_message(
                    session_id,
                    {
                        "type": "user_disconnected",
                        "user_id": user_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            return {"success": True, "message": "WebSocket disconnection handled"}

        except Exception as e:
            logger.error(f"Error handling WebSocket disconnect: {e}")
            return {"success": False, "error": f"Disconnect handling failed: {str(e)}"}

    # Private Helper Methods

    def _generate_user_color(self, user_id: str) -> str:
        """Generate a color for a user based on their ID."""
        try:
            # Simple hash-based color generation
            hash_value = hash(user_id)
            hue = abs(hash_value) % 360
            saturation = 70 + (abs(hash_value // 360) % 30)
            lightness = 45 + (abs(hash_value // 3600) % 20)

            return f"hsl({hue}, {saturation}%, {lightness}%)"
        except Exception:
            return "#666666"  # Default gray color

    async def _get_current_data(
        self, operation_type: OperationType, target_id: str, db: AsyncSession
    ) -> Dict[str, Any]:
        """Get current data for a target item."""
        try:
            if operation_type in [OperationType.UPDATE_NODE, OperationType.DELETE_NODE]:
                node = await KnowledgeNodeCRUD.get_by_id(db, target_id)
                if node:
                    return {
                        "id": str(node.id),
                        "name": node.name,
                        "node_type": node.node_type,
                        "description": node.description,
                        "platform": node.platform,
                        "minecraft_version": node.minecraft_version,
                        "properties": json.loads(node.properties or "{}"),
                        "expert_validated": node.expert_validated,
                        "community_rating": node.community_rating,
                    }

            elif operation_type in [
                OperationType.UPDATE_RELATIONSHIP,
                OperationType.DELETE_RELATIONSHIP,
            ]:
                # This would get relationship data
                pass

            elif operation_type in [
                OperationType.UPDATE_PATTERN,
                OperationType.DELETE_PATTERN,
            ]:
                pattern = await ConversionPatternCRUD.get_by_id(db, target_id)
                if pattern:
                    return {
                        "id": str(pattern.id),
                        "pattern_type": pattern.pattern_type,
                        "java_concept": pattern.java_concept,
                        "bedrock_concept": pattern.bedrock_concept,
                        "success_rate": pattern.success_rate,
                        "confidence_score": pattern.confidence_score,
                        "minecraft_version": pattern.minecraft_version,
                        "conversion_features": json.loads(
                            pattern.conversion_features or "{}"
                        ),
                        "validation_results": json.loads(
                            pattern.validation_results or "{}"
                        ),
                    }

            return {}

        except Exception as e:
            logger.error(f"Error getting current data: {e}")
            return {}

    async def _detect_conflicts(
        self,
        operation: CollaborativeOperation,
        session: CollaborationSession,
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between operations."""
        try:
            conflicts = []

            # Check against pending operations
            for pending_id, pending_op in session.pending_changes.items():
                if pending_id == operation.operation_id:
                    continue

                # Check for edit conflicts
                if operation.target_id == pending_op.target_id:
                    if operation.operation_type in [
                        OperationType.UPDATE_NODE,
                        OperationType.UPDATE_RELATIONSHIP,
                        OperationType.UPDATE_PATTERN,
                    ]:
                        if pending_op.operation_type in [
                            OperationType.UPDATE_NODE,
                            OperationType.UPDATE_RELATIONSHIP,
                            OperationType.UPDATE_PATTERN,
                        ]:
                            conflicts.append(
                                {
                                    "type": ConflictType.EDIT_CONFLICT.value,
                                    "conflicting_operation": pending_id,
                                    "conflicting_user": pending_op.user_name,
                                    "description": "Multiple users trying to edit the same item",
                                }
                            )

                    elif operation.operation_type in [
                        OperationType.DELETE_NODE,
                        OperationType.DELETE_RELATIONSHIP,
                        OperationType.DELETE_PATTERN,
                    ]:
                        if pending_op.operation_type in [
                            OperationType.UPDATE_NODE,
                            OperationType.UPDATE_RELATIONSHIP,
                            OperationType.UPDATE_PATTERN,
                        ]:
                            conflicts.append(
                                {
                                    "type": ConflictType.DELETE_CONFLICT.value,
                                    "conflicting_operation": pending_id,
                                    "conflicting_user": pending_op.user_name,
                                    "description": "User trying to delete an item being edited",
                                }
                            )

            # Check for relationship conflicts
            if operation.operation_type == OperationType.CREATE_RELATIONSHIP:
                relationship_data = operation.data
                source_id = relationship_data.get("source_id")
                target_id = relationship_data.get("target_id")

                # Check if similar relationship already exists
                # This would query the database for existing relationships
                # For now, check against recent operations
                for recent_op in session.operations[-10:]:
                    if recent_op.operation_type == OperationType.CREATE_RELATIONSHIP:
                        recent_data = recent_op.data
                        if (
                            recent_data.get("source_id") == source_id
                            and recent_data.get("target_id") == target_id
                        ):
                            conflicts.append(
                                {
                                    "type": ConflictType.RELATION_CONFLICT.value,
                                    "conflicting_operation": recent_op.operation_id,
                                    "conflicting_user": recent_op.user_name,
                                    "description": "Similar relationship already created",
                                }
                            )

            return conflicts

        except Exception as e:
            logger.error(f"Error detecting conflicts: {e}")
            return []

    async def _execute_operation(
        self, operation: CollaborativeOperation, db: AsyncSession
    ) -> Dict[str, Any]:
        """Execute a collaborative operation."""
        try:
            result = {}

            if operation.operation_type == OperationType.CREATE_NODE:
                node_data = operation.data
                node = await KnowledgeNodeCRUD.create(db, node_data)
                result = {
                    "type": "node_created",
                    "node_id": str(node.id),
                    "node_data": node_data,
                }

            elif operation.operation_type == OperationType.UPDATE_NODE:
                node_data = operation.data
                success = await KnowledgeNodeCRUD.update(
                    db, operation.target_id, node_data
                )
                result = {
                    "type": "node_updated",
                    "node_id": operation.target_id,
                    "success": success,
                    "node_data": node_data,
                }

            elif operation.operation_type == OperationType.DELETE_NODE:
                success = await KnowledgeNodeCRUD.delete(db, operation.target_id)
                result = {
                    "type": "node_deleted",
                    "node_id": operation.target_id,
                    "success": success,
                }

            elif operation.operation_type == OperationType.CREATE_RELATIONSHIP:
                rel_data = operation.data
                relationship = await KnowledgeRelationshipCRUD.create(db, rel_data)
                result = {
                    "type": "relationship_created",
                    "relationship_id": str(relationship.id),
                    "relationship_data": rel_data,
                }

            elif operation.operation_type == OperationType.CREATE_PATTERN:
                pattern_data = operation.data
                pattern = await ConversionPatternCRUD.create(db, pattern_data)
                result = {
                    "type": "pattern_created",
                    "pattern_id": str(pattern.id),
                    "pattern_data": pattern_data,
                }

            return result

        except Exception as e:
            logger.error(f"Error executing operation: {e}")
            return {"type": "error", "error": str(e)}

    async def _apply_conflict_resolution(
        self,
        conflict_operation: CollaborativeOperation,
        resolution_strategy: str,
        resolution_data: Dict[str, Any],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Apply a conflict resolution strategy."""
        try:
            if resolution_strategy == "accept_current":
                # Apply the conflicting operation as is
                result = await self._execute_operation(conflict_operation, db)
                return {"success": True, "strategy": "accept_current", "result": result}

            elif resolution_strategy == "accept_original":
                # Reject the conflicting operation
                return {
                    "success": True,
                    "strategy": "accept_original",
                    "result": {"type": "operation_rejected"},
                }

            elif resolution_strategy == "merge":
                # Merge operation with original data
                merged_data = self._merge_operation_data(
                    conflict_operation, resolution_data
                )
                conflict_operation.data = merged_data
                result = await self._execute_operation(conflict_operation, db)
                return {"success": True, "strategy": "merge", "result": result}

            else:
                return {
                    "success": False,
                    "error": f"Unknown resolution strategy: {resolution_strategy}",
                }

        except Exception as e:
            logger.error(f"Error applying conflict resolution: {e}")
            return {"success": False, "error": f"Resolution failed: {str(e)}"}

    def _merge_operation_data(
        self, operation: CollaborativeOperation, resolution_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge operation data with resolution data."""
        try:
            merged_data = operation.data.copy()

            # Simple field-level merge
            for key, value in resolution_data.items():
                if key in merged_data:
                    if isinstance(merged_data[key], dict) and isinstance(value, dict):
                        merged_data[key].update(value)
                    else:
                        merged_data[key] = value
                else:
                    merged_data[key] = value

            return merged_data

        except Exception as e:
            logger.error(f"Error merging operation data: {e}")
            return operation.data

    async def _broadcast_message(
        self,
        session_id: str,
        message: Dict[str, Any],
        exclude_user: Optional[str] = None,
    ):
        """Broadcast a message to all users in a session."""
        try:
            if session_id not in self.active_sessions:
                return

            session = self.active_sessions[session_id]

            # Send to all connected users
            for user_id, websocket in session.websockets.items():
                if user_id != exclude_user and user_id in self.websocket_connections:
                    try:
                        await websocket.send_text(json.dumps(message))
                    except Exception as e:
                        logger.error(
                            f"Error sending WebSocket message to {user_id}: {e}"
                        )
                        # Remove disconnected websocket
                        session.websockets.pop(user_id, None)
                        self.websocket_connections.pop(user_id, None)

        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")

    async def _send_session_state(
        self, user_id: str, session_id: str, db: AsyncSession
    ):
        """Send current session state to a specific user."""
        try:
            if user_id not in self.websocket_connections:
                return

            websocket = self.websocket_connections[user_id]
            session = self.active_sessions[session_id]

            # Get current graph state
            graph_state = await self._get_graph_state(session.graph_id, db)

            # Send session state
            state_message = {
                "type": "session_state",
                "session_id": session_id,
                "active_users": list(session.active_users.values()),
                "pending_changes": [
                    {
                        "operation_id": op_id,
                        "operation_type": op.operation_type.value,
                        "user_name": op.user_name,
                        "conflicts": op.conflicts,
                    }
                    for op_id, op in session.pending_changes.items()
                ],
                "graph_state": graph_state,
                "timestamp": datetime.utcnow().isoformat(),
            }

            await websocket.send_text(json.dumps(state_message))

        except Exception as e:
            logger.error(f"Error sending session state: {e}")

    async def _get_graph_state(self, graph_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get current state of the knowledge graph."""
        try:
            # This would get the actual graph state from the database
            # For now, return mock data
            return {
                "graph_id": graph_id,
                "nodes": [
                    {
                        "id": "node1",
                        "name": "Example Java Entity",
                        "type": "entity",
                        "platform": "java",
                    }
                ],
                "relationships": [
                    {
                        "id": "rel1",
                        "source": "node1",
                        "target": "node2",
                        "type": "converts_to",
                    }
                ],
                "patterns": [
                    {
                        "id": "pattern1",
                        "java_concept": "Example Java Entity",
                        "bedrock_concept": "Example Bedrock Entity",
                        "pattern_type": "entity_conversion",
                    }
                ],
            }

        except Exception as e:
            logger.error(f"Error getting graph state: {e}")
            return {}

    async def _archive_session(self, session_id: str):
        """Archive a collaboration session."""
        try:
            if session_id not in self.active_sessions:
                return

            session = self.active_sessions[session_id]

            # This would save session data to database for historical purposes
            # For now, just log the archiving
            logger.info(f"Archiving collaboration session: {session_id}")
            logger.info(f"Session duration: {datetime.utcnow() - session.created_at}")
            logger.info(f"Total operations: {len(session.operations)}")
            logger.info(f"Resolved conflicts: {len(session.resolved_conflicts)}")

        except Exception as e:
            logger.error(f"Error archiving session: {e}")


# Singleton instance
realtime_collaboration_service = RealtimeCollaborationService()
