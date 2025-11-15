"""
Comprehensive tests for Real-time Collaboration Service

Tests real-time collaboration capabilities for multiple users editing knowledge
graph simultaneously, including conflict resolution, change tracking, and live updates.
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.realtime_collaboration import (
    RealtimeCollaborationService,
    OperationType,
    ConflictType,
    ChangeStatus,
    CollaborativeOperation,
    CollaborationSession,
    ConflictResolution,
    realtime_collaboration_service
)


class TestOperationType:
    """Test OperationType enum."""
    
    def test_operation_type_values(self):
        """Test OperationType enum values."""
        assert OperationType.CREATE_NODE.value == "create_node"
        assert OperationType.UPDATE_NODE.value == "update_node"
        assert OperationType.DELETE_NODE.value == "delete_node"
        assert OperationType.CREATE_RELATIONSHIP.value == "create_relationship"
        assert OperationType.UPDATE_RELATIONSHIP.value == "update_relationship"
        assert OperationType.DELETE_RELATIONSHIP.value == "delete_relationship"
        assert OperationType.CREATE_PATTERN.value == "create_pattern"
        assert OperationType.UPDATE_PATTERN.value == "update_pattern"
        assert OperationType.DELETE_PATTERN.value == "delete_pattern"


class TestConflictType:
    """Test ConflictType enum."""
    
    def test_conflict_type_values(self):
        """Test ConflictType enum values."""
        assert ConflictType.EDIT_CONFLICT.value == "edit_conflict"
        assert ConflictType.DELETE_CONFLICT.value == "delete_conflict"
        assert ConflictType.RELATION_CONFLICT.value == "relation_conflict"
        assert ConflictType.VERSION_CONFLICT.value == "version_conflict"
        assert ConflictType.SCHEMA_CONFLICT.value == "schema_conflict"


class TestChangeStatus:
    """Test ChangeStatus enum."""
    
    def test_change_status_values(self):
        """Test ChangeStatus enum values."""
        assert ChangeStatus.PENDING.value == "pending"
        assert ChangeStatus.APPLIED.value == "applied"
        assert ChangeStatus.CONFLICTED.value == "conflicted"
        assert ChangeStatus.REJECTED.value == "rejected"
        assert ChangeStatus.MERGED.value == "merged"


class TestCollaborativeOperation:
    """Test CollaborativeOperation dataclass."""
    
    def test_collaborative_operation_creation(self):
        """Test CollaborativeOperation creation with all fields."""
        operation = CollaborativeOperation(
            operation_id="op_123",
            operation_type=OperationType.UPDATE_NODE,
            user_id="user_456",
            user_name="Test User",
            timestamp=datetime.utcnow(),
            target_id="node_789",
            data={"name": "Updated Node"},
            previous_data={"name": "Original Node"},
            status=ChangeStatus.PENDING,
            conflicts=[{"type": "edit_conflict"}],
            resolved_by="admin",
            resolution="merge"
        )
        
        assert operation.operation_id == "op_123"
        assert operation.operation_type == OperationType.UPDATE_NODE
        assert operation.user_id == "user_456"
        assert operation.user_name == "Test User"
        assert operation.target_id == "node_789"
        assert operation.data["name"] == "Updated Node"
        assert operation.previous_data["name"] == "Original Node"
        assert operation.status == ChangeStatus.PENDING
        assert len(operation.conflicts) == 1
        assert operation.resolved_by == "admin"
        assert operation.resolution == "merge"
    
    def test_collaborative_operation_defaults(self):
        """Test CollaborativeOperation with default values."""
        operation = CollaborativeOperation(
            operation_id="op_default",
            operation_type=OperationType.CREATE_NODE,
            user_id="user_default",
            user_name="Default User",
            timestamp=datetime.utcnow()
        )
        
        assert operation.target_id is None
        assert operation.data == {}
        assert operation.previous_data == {}
        assert operation.status == ChangeStatus.PENDING
        assert operation.conflicts == []
        assert operation.resolved_by is None
        assert operation.resolution is None


class TestCollaborationSession:
    """Test CollaborationSession dataclass."""
    
    def test_collaboration_session_creation(self):
        """Test CollaborationSession creation with all fields."""
        session = CollaborationSession(
            session_id="session_123",
            graph_id="graph_456",
            created_at=datetime.utcnow()
        )
        
        assert session.session_id == "session_123"
        assert session.graph_id == "graph_456"
        assert session.active_users == {}
        assert session.operations == []
        assert session.pending_changes == {}
        assert session.resolved_conflicts == []
        assert session.websockets == {}


class TestConflictResolution:
    """Test ConflictResolution dataclass."""
    
    def test_conflict_resolution_creation(self):
        """Test ConflictResolution creation with all fields."""
        resolution = ConflictResolution(
            conflict_id="conflict_123",
            conflict_type=ConflictType.EDIT_CONFLICT,
            operations_involved=["op_1", "op_2"],
            resolution_strategy="merge",
            resolved_by="admin_user",
            resolved_at=datetime.utcnow(),
            resolution_data={"merged_data": {"name": "Merged Name"}}
        )
        
        assert resolution.conflict_id == "conflict_123"
        assert resolution.conflict_type == ConflictType.EDIT_CONFLICT
        assert len(resolution.operations_involved) == 2
        assert resolution.resolution_strategy == "merge"
        assert resolution.resolved_by == "admin_user"
        assert resolution.resolution_data["merged_data"]["name"] == "Merged Name"


class TestRealtimeCollaborationService:
    """Test RealtimeCollaborationService class."""
    
    @pytest.fixture
    def service(self):
        """Create fresh service instance for each test."""
        return RealtimeCollaborationService()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket connection."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        return websocket
    
    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.active_sessions == {}
        assert service.user_sessions == {}
        assert service.operation_history == []
        assert service.conflict_resolutions == []
        assert service.websocket_connections == {}
    
    @pytest.mark.asyncio
    async def test_create_collaboration_session_success(self, service, mock_db):
        """Test successful collaboration session creation."""
        result = await service.create_collaboration_session(
            graph_id="graph_123",
            user_id="user_456",
            user_name="Test User",
            db=mock_db
        )
        
        assert result["success"] is True
        assert "session_id" in result
        assert result["graph_id"] == "graph_123"
        assert result["user_info"]["user_id"] == "user_456"
        assert result["user_info"]["user_name"] == "Test User"
        assert result["user_info"]["role"] == "creator"
        assert "color" in result["user_info"]
        assert result["message"] == "Collaboration session created successfully"
        
        # Check session was created
        session_id = result["session_id"]
        assert session_id in service.active_sessions
        assert session_id in service.user_sessions.values()
        
        session = service.active_sessions[session_id]
        assert session.graph_id == "graph_123"
        assert "user_456" in session.active_users
        assert session.active_users["user_456"]["role"] == "creator"
    
    @pytest.mark.asyncio
    async def test_create_collaboration_session_error(self, service, mock_db):
        """Test collaboration session creation with error."""
        with patch.object(service, '_generate_user_color', side_effect=Exception("Color generation failed")):
            result = await service.create_collaboration_session(
                graph_id="graph_error",
                user_id="user_error",
                user_name="Error User",
                db=mock_db
            )
            
            assert result["success"] is False
            assert "Session creation failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_join_collaboration_session_success(self, service, mock_websocket, mock_db):
        """Test successful collaboration session join."""
        # First create a session
        create_result = await service.create_collaboration_session(
            graph_id="graph_join",
            user_id="creator_user",
            user_name="Creator",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        # Now join the session
        result = await service.join_collaboration_session(
            session_id=session_id,
            user_id="joining_user",
            user_name="Joiner",
            websocket=mock_websocket,
            db=mock_db
        )
        
        assert result["success"] is True
        assert result["session_id"] == session_id
        assert result["user_info"]["user_id"] == "joining_user"
        assert result["user_info"]["user_name"] == "Joiner"
        assert result["user_info"]["role"] == "collaborator"
        assert len(result["active_users"]) == 2
        
        # Check user was added to session
        session = service.active_sessions[session_id]
        assert "joining_user" in session.active_users
        assert "joining_user" in session.websockets
        assert service.user_sessions["joining_user"] == session_id
    
    @pytest.mark.asyncio
    async def test_join_collaboration_session_not_found(self, service, mock_websocket, mock_db):
        """Test joining non-existent collaboration session."""
        result = await service.join_collaboration_session(
            session_id="nonexistent_session",
            user_id="user_test",
            user_name="Test User",
            websocket=mock_websocket,
            db=mock_db
        )
        
        assert result["success"] is False
        assert "Session not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_join_collaboration_session_already_joined(self, service, mock_websocket, mock_db):
        """Test joining session when user already in session."""
        # Create session and add user
        create_result = await service.create_collaboration_session(
            graph_id="graph_duplicate",
            user_id="existing_user",
            user_name="Existing User",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        # Try to join again
        result = await service.join_collaboration_session(
            session_id=session_id,
            user_id="existing_user",
            user_name="Existing User",
            websocket=mock_websocket,
            db=mock_db
        )
        
        assert result["success"] is False
        assert "User already in session" in result["error"]
    
    @pytest.mark.asyncio
    async def test_leave_collaboration_session_success(self, service, mock_db):
        """Test successful collaboration session leave."""
        # Create and join session
        create_result = await service.create_collaboration_session(
            graph_id="graph_leave",
            user_id="leaving_user",
            user_name="Leaving User",
            db=mock_db
        )
        
        # Leave the session
        result = await service.leave_collaboration_session(
            user_id="leaving_user",
            db=mock_db
        )
        
        assert result["success"] is True
        assert result["session_id"] == create_result["session_id"]
        assert result["message"] == "Left collaboration session successfully"
        
        # Check user was removed
        assert "leaving_user" not in service.user_sessions
        
        # Session should be archived (no active users)
        assert create_result["session_id"] not in service.active_sessions
    
    @pytest.mark.asyncio
    async def test_leave_collaboration_session_not_in_session(self, service):
        """Test leaving collaboration session when not in any session."""
        result = await service.leave_collaboration_session(
            user_id="nonexistent_user"
        )
        
        assert result["success"] is False
        assert "User not in active session" in result["error"]
    
    @pytest.mark.asyncio
    async def test_leave_collaboration_session_with_other_users(self, service, mock_db):
        """Test leaving session when other users remain."""
        # Create session with creator
        create_result = await service.create_collaboration_session(
            graph_id="graph_multi",
            user_id="creator_multi",
            user_name="Creator",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        # Add second user
        with patch('src.services.realtime_collaboration.WebSocket') as mock_ws_class:
            mock_ws = AsyncMock(spec=WebSocket)
            mock_ws.send_text = AsyncMock()
            
            await service.join_collaboration_session(
                session_id=session_id,
                user_id="second_user",
                user_name="Second User",
                websocket=mock_ws,
                db=mock_db
            )
            
            # First user leaves
            result = await service.leave_collaboration_session(
                user_id="creator_multi",
                db=mock_db
            )
            
            assert result["success"] is True
            
            # Session should still exist with second user
            assert session_id in service.active_sessions
            assert "creator_multi" not in service.active_sessions[session_id].active_users
            assert "second_user" in service.active_sessions[session_id].active_users
    
    @pytest.mark.asyncio
    async def test_apply_operation_success(self, service, mock_db):
        """Test successful operation application."""
        # Create session
        create_result = await service.create_collaboration_session(
            graph_id="graph_op",
            user_id="op_user",
            user_name="Operator",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        # Apply operation
        operation_data = {
            "name": "Test Node",
            "node_type": "entity",
            "platform": "java"
        }
        
        with patch.object(service, '_detect_conflicts', return_value=[]), \
             patch.object(service, '_execute_operation', return_value={"type": "node_created", "node_id": "node_123"}), \
             patch.object(service, '_broadcast_message') as mock_broadcast:
            
            result = await service.apply_operation(
                session_id=session_id,
                user_id="op_user",
                operation_type=OperationType.CREATE_NODE,
                target_id=None,
                data=operation_data,
                db=mock_db
            )
            
            assert result["success"] is True
            assert "operation_id" in result
            assert result["result"]["type"] == "node_created"
            assert result["result"]["node_id"] == "node_123"
            assert result["message"] == "Operation applied successfully"
            
            # Check operation was added to session
            session = service.active_sessions[session_id]
            assert len(session.operations) == 1
            assert session.operations[0].operation_type == OperationType.CREATE_NODE
            assert session.operations[0].status == ChangeStatus.APPLIED
            
            # Check broadcast was called
            mock_broadcast.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_apply_operation_conflict(self, service, mock_db):
        """Test operation application with conflicts."""
        # Create session
        create_result = await service.create_collaboration_session(
            graph_id="graph_conflict",
            user_id="conflict_user",
            user_name="Conflict User",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        # Mock conflicts
        conflicts = [
            {
                "type": ConflictType.EDIT_CONFLICT.value,
                "conflicting_operation": "op_123",
                "conflicting_user": "Other User",
                "description": "Multiple users editing same item"
            }
        ]
        
        with patch.object(service, '_detect_conflicts', return_value=conflicts), \
             patch.object(service, '_broadcast_message') as mock_broadcast:
            
            result = await service.apply_operation(
                session_id=session_id,
                user_id="conflict_user",
                operation_type=OperationType.UPDATE_NODE,
                target_id="node_conflict",
                data={"name": "Updated Name"},
                db=mock_db
            )
            
            assert result["success"] is False
            assert "operation_id" in result
            assert result["conflicts"] == conflicts
            assert "conflicts with existing changes" in result["message"]
            
            # Check operation is pending with conflicts
            session = service.active_sessions[session_id]
            assert len(session.pending_changes) == 1
            pending_op = list(session.pending_changes.values())[0]
            assert pending_op.status == ChangeStatus.CONFLICTED
            assert pending_op.conflicts == conflicts
            
            # Check broadcast was called for conflict
            mock_broadcast.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_apply_operation_session_not_found(self, service, mock_db):
        """Test operation application for non-existent session."""
        result = await service.apply_operation(
            session_id="nonexistent",
            user_id="user_test",
            operation_type=OperationType.CREATE_NODE,
            data={"name": "Test"},
            db=mock_db
        )
        
        assert result["success"] is False
        assert "Session not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_apply_operation_user_not_in_session(self, service, mock_db):
        """Test operation application by user not in session."""
        # Create session
        create_result = await service.create_collaboration_session(
            graph_id="graph_no_user",
            user_id="session_user",
            user_name="Session User",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        # Try to apply operation as different user
        result = await service.apply_operation(
            session_id=session_id,
            user_id="non_session_user",
            operation_type=OperationType.CREATE_NODE,
            data={"name": "Test"},
            db=mock_db
        )
        
        assert result["success"] is False
        assert "User not in session" in result["error"]
    
    @pytest.mark.asyncio
    async def test_resolve_conflict_success(self, service, mock_db):
        """Test successful conflict resolution."""
        # Create session
        create_result = await service.create_collaboration_session(
            graph_id="graph_resolve",
            user_id="resolver_user",
            user_name="Resolver",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        # Create a conflicting operation
        conflict_id = "conflict_123"
        conflict_op = CollaborativeOperation(
            operation_id=conflict_id,
            operation_type=OperationType.UPDATE_NODE,
            user_id="other_user",
            user_name="Other User",
            timestamp=datetime.utcnow(),
            target_id="node_conflict",
            data={"name": "Conflicting Name"},
            status=ChangeStatus.CONFLICTED
        )
        conflict_op.conflicts = [{"type": "edit_conflict"}]
        
        service.active_sessions[session_id].pending_changes[conflict_id] = conflict_op
        
        # Resolve the conflict
        resolution_data = {"merged_name": "Merged Name"}
        
        with patch.object(service, '_apply_conflict_resolution', 
                       return_value={"success": True, "result": {"type": "node_updated"}}), \
             patch.object(service, '_broadcast_message') as mock_broadcast:
            
            result = await service.resolve_conflict(
                session_id=session_id,
                user_id="resolver_user",
                conflict_id=conflict_id,
                resolution_strategy="merge",
                resolution_data=resolution_data,
                db=mock_db
            )
            
            assert result["success"] is True
            assert result["conflict_id"] == conflict_id
            assert result["resolution_strategy"] == "merge"
            assert result["result"]["type"] == "node_updated"
            assert result["message"] == "Conflict resolved successfully"
            
            # Check conflict was resolved
            session = service.active_sessions[session_id]
            assert conflict_id not in session.pending_changes
            assert len(session.resolved_conflicts) == 1
            
            # Check operation was marked as merged
            resolved_op = None
            for op in session.operations:
                if op.operation_id == conflict_id:
                    resolved_op = op
                    break
            
            assert resolved_op is not None
            assert resolved_op.status == ChangeStatus.MERGED
            assert resolved_op.resolved_by == "resolver_user"
            assert resolved_op.resolution == "merge"
            
            # Check global conflict resolutions
            assert len(service.conflict_resolutions) == 1
            
            # Check broadcast was called
            mock_broadcast.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resolve_conflict_not_found(self, service, mock_db):
        """Test resolving non-existent conflict."""
        create_result = await service.create_collaboration_session(
            graph_id="graph_no_conflict",
            user_id="user_test",
            user_name="Test User",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        result = await service.resolve_conflict(
            session_id=session_id,
            user_id="user_test",
            conflict_id="nonexistent_conflict",
            resolution_strategy="merge",
            resolution_data={},
            db=mock_db
        )
        
        assert result["success"] is False
        assert "Conflict not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_session_state_success(self, service, mock_db):
        """Test successful session state retrieval."""
        # Create session with activity
        create_result = await service.create_collaboration_session(
            graph_id="graph_state",
            user_id="state_user",
            user_name="State User",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        # Add some operations
        with patch.object(service, '_execute_operation', return_value={"type": "node_created"}), \
             patch.object(service, '_detect_conflicts', return_value=[]):
            
            await service.apply_operation(
                session_id=session_id,
                user_id="state_user",
                operation_type=OperationType.CREATE_NODE,
                data={"name": "Test Node"},
                db=mock_db
            )
            
            await service.apply_operation(
                session_id=session_id,
                user_id="state_user",
                operation_type=OperationType.UPDATE_NODE,
                target_id="node_123",
                data={"name": "Updated Node"},
                db=mock_db
            )
        
        with patch.object(service, '_get_graph_state', return_value={"nodes": [], "relationships": []}):
            result = await service.get_session_state(session_id, mock_db)
            
            assert result["success"] is True
            assert result["session_id"] == session_id
            assert result["graph_id"] == "graph_state"
            assert len(result["active_users"]) == 1
            assert result["operations_count"] == 2
            assert result["pending_changes_count"] == 0
            assert result["resolved_conflicts_count"] == 0
            assert "graph_state" in result
            assert len(result["recent_operations"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_session_state_not_found(self, service, mock_db):
        """Test session state for non-existent session."""
        result = await service.get_session_state("nonexistent", mock_db)
        
        assert result["success"] is False
        assert "Session not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_user_activity_success(self, service, mock_db):
        """Test successful user activity retrieval."""
        # Create session
        create_result = await service.create_collaboration_session(
            graph_id="graph_activity",
            user_id="activity_user",
            user_name="Activity User",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        # Add operations with different timestamps
        base_time = datetime.utcnow()
        operations_data = [
            (OperationType.CREATE_NODE, {"name": "Node 1"}, None),
            (OperationType.UPDATE_NODE, {"name": "Updated Node"}, "node_1"),
            (OperationType.CREATE_RELATIONSHIP, {"source": "node1", "target": "node2"}, None),
            (OperationType.DELETE_NODE, {}, "node_3"),
            (OperationType.CREATE_PATTERN, {"pattern_type": "entity_conversion"}, None)
        ]
        
        with patch.object(service, '_execute_operation', return_value={"type": "success"}), \
             patch.object(service, '_detect_conflicts', return_value=[]):
            
            for i, (op_type, data, target_id) in enumerate(operations_data):
                # Create operation with specific timestamp
                operation = CollaborativeOperation(
                    operation_id=f"op_{i}",
                    operation_type=op_type,
                    user_id="activity_user",
                    user_name="Activity User",
                    timestamp=base_time + timedelta(minutes=i-5),  # Spread across 5 minutes
                    target_id=target_id,
                    data=data,
                    status=ChangeStatus.APPLIED
                )
                service.active_sessions[session_id].operations.append(operation)
        
        result = await service.get_user_activity(
            session_id=session_id,
            user_id="activity_user",
            minutes=30
        )
        
        assert result["success"] is True
        assert result["session_id"] == session_id
        assert result["user_id"] == "activity_user"
        assert result["user_name"] == "Activity User"
        assert result["activity_period_minutes"] == 30
        assert result["total_operations"] == 5
        
        # Check operation breakdown
        operations_by_type = result["operations_by_type"]
        assert operations_by_type.get("create_node", 0) == 1
        assert operations_by_type.get("update_node", 0) == 1
        assert operations_by_type.get("create_relationship", 0) == 1
        assert operations_by_type.get("delete_node", 0) == 1
        assert operations_by_type.get("create_pattern", 0) == 1
        
        assert result["is_active"] is True  # Recent activity
    
    @pytest.mark.asyncio
    async def test_get_user_activity_not_in_session(self, service, mock_db):
        """Test user activity for user not in session."""
        create_result = await service.create_collaboration_session(
            graph_id="graph_no_activity_user",
            user_id="other_user",
            user_name="Other User",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        result = await service.get_user_activity(
            session_id=session_id,
            user_id="nonexistent_user",
            minutes=30
        )
        
        assert result["success"] is False
        assert "User not in session" in result["error"]
    
    @pytest.mark.asyncio
    async def test_handle_websocket_message_cursor_position(self, service, mock_db):
        """Test WebSocket cursor position message handling."""
        # Create session
        create_result = await service.create_collaboration_session(
            graph_id="graph_cursor",
            user_id="cursor_user",
            user_name="Cursor User",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        # Mock websocket
        mock_websocket = AsyncMock(spec=WebSocket)
        service.websocket_connections["cursor_user"] = mock_websocket
        
        # Send cursor position message
        message = {
            "type": "cursor_position",
            "cursor_position": {"x": 100, "y": 200, "node_id": "node_123"}
        }
        
        result = await service.handle_websocket_message(
            user_id="cursor_user",
            message=message,
            db=mock_db
        )
        
        assert result["success"] is True
        assert "Cursor position updated" in result["message"]
        
        # Check cursor position was updated
        session = service.active_sessions[session_id]
        assert session.active_users["cursor_user"]["cursor_position"] == {"x": 100, "y": 200, "node_id": "node_123"}
    
    @pytest.mark.asyncio
    async def test_handle_websocket_message_operation(self, service, mock_db):
        """Test WebSocket operation message handling."""
        # Create session
        create_result = await service.create_collaboration_session(
            graph_id="graph_ws_op",
            user_id="ws_op_user",
            user_name="WS Op User",
            db=mock_db
        )
        session_id = create_result["session_id"]
        
        # Mock websocket
        mock_websocket = AsyncMock(spec=WebSocket)
        service.websocket_connections["ws_op_user"] = mock_websocket
        
        # Send operation message
        message = {
            "type": "operation",
            "operation_type": "create_node",
            "data": {"name": "WS Created Node", "node_type": "entity"}
        }
        
        with patch.object(service, '_detect_conflicts', return_value=[]), \
             patch.object(service, '_execute_operation', return_value={"type": "node_created", "node_id": "ws_node_123"}), \
             patch.object(service, '_broadcast_message') as mock_broadcast:
            
            result = await service.handle_websocket_message(
                user_id="ws_op_user",
                message=message,
                db=mock_db
            )
            
            assert result["success"] is True
            assert "operation_id" in result
            assert result["result"]["type"] == "node_created"
    
    @pytest.mark.asyncio
    async def test_handle_websocket_message_unknown_type(self, service, mock_db):
        """Test WebSocket message with unknown type."""
        # Create session
        create_result = await service.create_collaboration_session(
            graph_id="graph_unknown",
            user_id="unknown_user",
            user_name="Unknown User",
            db=mock_db
        )
        
        # Mock websocket
        mock_websocket = AsyncMock(spec=WebSocket)
        service.websocket_connections["unknown_user"] = mock_websocket
        
        # Send unknown message type
        message = {
            "type": "unknown_type",
            "data": {"test": "data"}
        }
        
        result = await service.handle_websocket_message(
            user_id="unknown_user",
            message=message,
            db=mock_db
        )
        
        assert result["success"] is False
        assert "Unknown message type" in result["error"]
    
    @pytest.mark.asyncio
    async def test_handle_websocket_disconnect(self, service):
        """Test WebSocket disconnect handling."""
        # Create session and add user with websocket
        create_result = await service.create_collaboration_session(
            graph_id="graph_disconnect",
            user_id="disconnect_user",
            user_name="Disconnect User",
            db=AsyncMock()
        )
        session_id = create_result["session_id"]
        
        # Mock websocket
        mock_websocket = AsyncMock(spec=WebSocket)
        service.websocket_connections["disconnect_user"] = mock_websocket
        service.active_sessions[session_id].websockets["disconnect_user"] = mock_websocket
        
        # Handle disconnect
        result = await service.handle_websocket_disconnect(user_id="disconnect_user")
        
        assert result["success"] is True
        assert "WebSocket disconnection handled" in result["message"]
        
        # Check websocket was removed
        assert "disconnect_user" not in service.websocket_connections
        assert "disconnect_user" not in service.active_sessions[session_id].websockets
        assert service.active_sessions[session_id].active_users["disconnect_user"]["status"] == "disconnected"
    
    def test_generate_user_color(self, service):
        """Test user color generation."""
        color1 = service._generate_user_color("user_123")
        color2 = service._generate_user_color("user_456")
        color3 = service._generate_user_color("user_123")  # Same user again
        
        assert isinstance(color1, str)
        assert isinstance(color2, str)
        assert color1 == color3  # Same user should have same color
        assert color1 != color2  # Different users should have different colors
        
        # Check color format (should be CSS color)
        assert color1.startswith("#") or "hsl(" in color1
        assert len(color1) > 3
    
    @pytest.mark.asyncio
    async def test_get_current_data_node(self, service, mock_db):
        """Test getting current data for a node."""
        # Mock node
        mock_node = MagicMock()
        mock_node.id = "node_123"
        mock_node.name = "Test Node"
        mock_node.node_type = "entity"
        mock_node.description = "Test description"
        mock_node.platform = "java"
        mock_node.minecraft_version = "1.19.2"
        mock_node.properties = '{"feature1": "value1"}'
        mock_node.expert_validated = True
        mock_node.community_rating = 0.8
        
        with patch('src.services.realtime_collaboration.KnowledgeNodeCRUD.get_by_id', 
                  return_value=mock_node):
            
            data = await service._get_current_data(
                OperationType.UPDATE_NODE, "node_123", mock_db
            )
            
            assert data["id"] == "node_123"
            assert data["name"] == "Test Node"
            assert data["node_type"] == "entity"
            assert data["platform"] == "java"
            assert data["expert_validated"] is True
            assert data["community_rating"] == 0.8
            assert data["properties"]["feature1"] == "value1"
    
    @pytest.mark.asyncio
    async def test_get_current_data_pattern(self, service, mock_db):
        """Test getting current data for a pattern."""
        # Mock pattern
        mock_pattern = MagicMock()
        mock_pattern.id = "pattern_123"
        mock_pattern.pattern_type = "entity_conversion"
        mock_pattern.java_concept = "Java Entity"
        mock_pattern.bedrock_concept = "Bedrock Entity"
        mock_pattern.success_rate = 0.85
        mock_pattern.confidence_score = 0.9
        mock_pattern.minecraft_version = "1.19.2"
        mock_pattern.conversion_features = '{"feature": "conversion_data"}'
        mock_pattern.validation_results = '{"valid": true}'
        
        with patch('src.services.realtime_collaboration.ConversionPatternCRUD.get_by_id', 
                  return_value=mock_pattern):
            
            data = await service._get_current_data(
                OperationType.UPDATE_PATTERN, "pattern_123", mock_db
            )
            
            assert data["id"] == "pattern_123"
            assert data["pattern_type"] == "entity_conversion"
            assert data["java_concept"] == "Java Entity"
            assert data["bedrock_concept"] == "Bedrock Entity"
            assert data["success_rate"] == 0.85
            assert data["confidence_score"] == 0.9
            assert data["conversion_features"]["feature"] == "conversion_data"
            assert data["validation_results"]["valid"] is True
    
    @pytest.mark.asyncio
    async def test_detect_conflicts_edit_conflict(self, service):
        """Test conflict detection for edit conflicts."""
        session = CollaborationSession(
            session_id="conflict_session",
            graph_id="graph_conflict",
            created_at=datetime.utcnow()
        )
        
        # Add pending operation for same target
        pending_op = CollaborativeOperation(
            operation_id="pending_op",
            operation_type=OperationType.UPDATE_NODE,
            user_id="other_user",
            user_name="Other User",
            timestamp=datetime.utcnow(),
            target_id="node_conflict",
            data={"name": "Other Update"},
            status=ChangeStatus.PENDING
        )
        session.pending_changes["pending_op"] = pending_op
        
        # Create new operation for same target
        new_op = CollaborativeOperation(
            operation_id="new_op",
            operation_type=OperationType.UPDATE_NODE,
            user_id="current_user",
            user_name="Current User",
            timestamp=datetime.utcnow(),
            target_id="node_conflict",
            data={"name": "Current Update"},
            status=ChangeStatus.PENDING
        )
        
        conflicts = await service._detect_conflicts(new_op, session, AsyncMock())
        
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == ConflictType.EDIT_CONFLICT.value
        assert conflicts[0]["conflicting_operation"] == "pending_op"
        assert conflicts[0]["conflicting_user"] == "Other User"
        assert "editing same item" in conflicts[0]["description"]
    
    @pytest.mark.asyncio
    async def test_detect_conflicts_delete_conflict(self, service):
        """Test conflict detection for delete conflicts."""
        session = CollaborationSession(
            session_id="delete_conflict_session",
            graph_id="graph_delete_conflict",
            created_at=datetime.utcnow()
        )
        
        # Add pending update operation
        pending_op = CollaborativeOperation(
            operation_id="pending_update",
            operation_type=OperationType.UPDATE_NODE,
            user_id="other_user",
            user_name="Other User",
            timestamp=datetime.utcnow(),
            target_id="node_delete_conflict",
            data={"name": "Updated Name"},
            status=ChangeStatus.PENDING
        )
        session.pending_changes["pending_update"] = pending_op
        
        # Create delete operation for same target
        delete_op = CollaborativeOperation(
            operation_id="delete_op",
            operation_type=OperationType.DELETE_NODE,
            user_id="current_user",
            user_name="Current User",
            timestamp=datetime.utcnow(),
            target_id="node_delete_conflict",
            data={},
            status=ChangeStatus.PENDING
        )
        
        conflicts = await service._detect_conflicts(delete_op, session, AsyncMock())
        
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == ConflictType.DELETE_CONFLICT.value
        assert conflicts[0]["conflicting_operation"] == "pending_update"
        assert conflicts[0]["conflicting_user"] == "Other User"
        assert "being edited" in conflicts[0]["description"]
    
    @pytest.mark.asyncio
    async def test_execute_operation_create_node(self, service, mock_db):
        """Test executing create node operation."""
        operation = CollaborativeOperation(
            operation_id="create_op",
            operation_type=OperationType.CREATE_NODE,
            user_id="creator",
            user_name="Creator",
            timestamp=datetime.utcnow(),
            data={
                "name": "Created Node",
                "node_type": "entity",
                "platform": "java",
                "minecraft_version": "1.19.2"
            },
            status=ChangeStatus.PENDING
        )
        
        # Mock node creation
        mock_node = MagicMock()
        mock_node.id = "created_node_123"
        
        with patch('src.services.realtime_collaboration.KnowledgeNodeCRUD.create', 
                  return_value=mock_node):
            
            result = await service._execute_operation(operation, mock_db)
            
            assert result["type"] == "node_created"
            assert result["node_id"] == "created_node_123"
            assert result["node_data"]["name"] == "Created Node"
    
    @pytest.mark.asyncio
    async def test_execute_operation_update_node(self, service, mock_db):
        """Test executing update node operation."""
        operation = CollaborativeOperation(
            operation_id="update_op",
            operation_type=OperationType.UPDATE_NODE,
            user_id="updater",
            user_name="Updater",
            timestamp=datetime.utcnow(),
            target_id="node_to_update",
            data={"name": "Updated Name", "description": "Updated description"},
            status=ChangeStatus.PENDING
        )
        
        with patch('src.services.realtime_collaboration.KnowledgeNodeCRUD.update', 
                  return_value=True):
            
            result = await service._execute_operation(operation, mock_db)
            
            assert result["type"] == "node_updated"
            assert result["node_id"] == "node_to_update"
            assert result["success"] is True
            assert result["node_data"]["name"] == "Updated Name"
    
    @pytest.mark.asyncio
    async def test_execute_operation_delete_node(self, service, mock_db):
        """Test executing delete node operation."""
        operation = CollaborativeOperation(
            operation_id="delete_op",
            operation_type=OperationType.DELETE_NODE,
            user_id="deleter",
            user_name="Deleter",
            timestamp=datetime.utcnow(),
            target_id="node_to_delete",
            data={},
            status=ChangeStatus.PENDING
        )
        
        with patch('src.services.realtime_collaboration.KnowledgeNodeCRUD.delete', 
                  return_value=True):
            
            result = await service._execute_operation(operation, mock_db)
            
            assert result["type"] == "node_deleted"
            assert result["node_id"] == "node_to_delete"
            assert result["success"] is True
    
    def test_merge_operation_data(self, service):
        """Test merging operation data."""
        operation = CollaborativeOperation(
            operation_id="merge_op",
            operation_type=OperationType.UPDATE_NODE,
            user_id="merger",
            user_name="Merger",
            timestamp=datetime.utcnow(),
            target_id="node_merge",
            data={
                "name": "Original Name",
                "description": "Original Description",
                "properties": {"prop1": "value1"}
            },
            status=ChangeStatus.PENDING
        )
        
        resolution_data = {
            "name": "Merged Name",
            "properties": {"prop2": "value2"},
            "new_field": "new_value"
        }
        
        merged_data = service._merge_operation_data(operation, resolution_data)
        
        assert merged_data["name"] == "Merged Name"  # Overwritten by resolution
        assert merged_data["description"] == "Original Description"  # Preserved
        assert merged_data["properties"]["prop1"] == "value1"  # Preserved
        assert merged_data["properties"]["prop2"] == "value2"  # Added
        assert merged_data["new_field"] == "new_value"  # Added


class TestServiceIntegration:
    """Integration tests for Real-time Collaboration service."""
    
    @pytest.mark.asyncio
    async def test_full_collaboration_workflow(self):
        """Test complete collaboration workflow with multiple users."""
        service = RealtimeCollaborationService()
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Create session
        session_result = await service.create_collaboration_session(
            graph_id="integration_graph",
            user_id="creator_user",
            user_name="Creator",
            db=mock_db
        )
        
        assert session_result["success"] is True
        session_id = session_result["session_id"]
        
        # Add second user
        with patch('src.services.realtime_collaboration.WebSocket') as mock_ws_class:
            mock_ws1 = AsyncMock(spec=WebSocket)
            mock_ws1.send_text = AsyncMock()
            
            join_result = await service.join_collaboration_session(
                session_id=session_id,
                user_id="collaborator_user",
                user_name="Collaborator",
                websocket=mock_ws1,
                db=mock_db
            )
            
            assert join_result["success"] is True
        
        # Both users perform operations
        with patch.object(service, '_detect_conflicts', return_value=[]), \
             patch.object(service, '_execute_operation', return_value={"type": "success"}), \
             patch.object(service, '_broadcast_message') as mock_broadcast:
            
            # Creator creates a node
            creator_op_result = await service.apply_operation(
                session_id=session_id,
                user_id="creator_user",
                operation_type=OperationType.CREATE_NODE,
                data={"name": "Creator Node", "node_type": "entity"},
                db=mock_db
            )
            
            assert creator_op_result["success"] is True
            
            # Collaborator creates a relationship
            collab_op_result = await service.apply_operation(
                session_id=session_id,
                user_id="collaborator_user",
                operation_type=OperationType.CREATE_RELATIONSHIP,
                data={"source": "node1", "target": "node2", "type": "relates_to"},
                db=mock_db
            )
            
            assert collab_op_result["success"] is True
        
        # Get session state
        with patch.object(service, '_get_graph_state', 
                       return_value={"nodes": [], "relationships": []}):
            state_result = await service.get_session_state(session_id, mock_db)
            
            assert state_result["success"] is True
            assert state_result["operations_count"] == 2
            assert len(state_result["active_users"]) == 2
        
        # Get user activity
        activity_result = await service.get_user_activity(
            session_id=session_id,
            user_id="creator_user",
            minutes=60
        )
        
        assert activity_result["success"] is True
        assert activity_result["total_operations"] == 1
        assert activity_result["operations_by_type"].get("create_node", 0) == 1
        
        # User leaves session
        leave_result = await service.leave_collaboration_session(
            user_id="collaborator_user",
            db=mock_db
        )
        
        assert leave_result["success"] is True


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        return RealtimeCollaborationService()
    
    @pytest.mark.asyncio
    async def test_operation_execution_error(self, service):
        """Test operation execution with database error."""
        operation = CollaborativeOperation(
            operation_id="error_op",
            operation_type=OperationType.CREATE_NODE,
            user_id="error_user",
            user_name="Error User",
            timestamp=datetime.utcnow(),
            data={"name": "Error Node"},
            status=ChangeStatus.PENDING
        )
        
        mock_db = AsyncMock()
        
        with patch('src.services.realtime_collaboration.KnowledgeNodeCRUD.create', 
                  side_effect=Exception("Database error")):
            
            result = await service._execute_operation(operation, mock_db)
            
            assert result["type"] == "error"
            assert "Database error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_websocket_broadcast_error(self, service):
        """Test WebSocket broadcast error handling."""
        # Create session
        session = CollaborationSession(
            session_id="broadcast_error_session",
            graph_id="graph_broadcast_error",
            created_at=datetime.utcnow()
        )
        
        # Add user with failing websocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_text.side_effect = Exception("WebSocket error")
        
        session.websockets["error_user"] = mock_websocket
        service.websocket_connections["error_user"] = mock_websocket
        service.active_sessions["broadcast_error_session"] = session
        
        # Broadcast message (should not crash)
        message = {"type": "test", "data": "test data"}
        
        # Should handle error gracefully
        await service._broadcast_message("broadcast_error_session", message)
        
        # WebSocket should be removed from connections
        assert "error_user" not in session.websockets
        assert "error_user" not in service.websocket_connections
    
    def test_merge_operation_data_error(self, service):
        """Test merging operation data with problematic data."""
        operation = CollaborativeOperation(
            operation_id="merge_error_op",
            operation_type=OperationType.UPDATE_NODE,
            user_id="merge_error_user",
            user_name="Merge Error User",
            timestamp=datetime.utcnow(),
            data={"name": "Original"},
            status=ChangeStatus.PENDING
        )
        
        # Resolution data with problematic structure
        resolution_data = None
        
        # Should handle gracefully and return original data
        merged_data = service._merge_operation_data(operation, resolution_data)
        
        assert merged_data == operation.data
    
    def test_singleton_instance(self):
        """Test that singleton instance is properly exported."""
        assert realtime_collaboration_service is not None
        assert isinstance(realtime_collaboration_service, RealtimeCollaborationService)
