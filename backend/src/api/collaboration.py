"""
Real-time Collaboration API Endpoints

This module provides REST API and WebSocket endpoints for real-time
collaboration on knowledge graph editing.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from ..services.realtime_collaboration import (
    realtime_collaboration_service, OperationType, ConflictType
)

logger = logging.getLogger(__name__)

router = APIRouter()


# REST API Endpoints

@router.post("/sessions")
async def create_collaboration_session(
    session_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new collaboration session."""
    try:
        graph_id = session_data.get("graph_id")
        user_id = session_data.get("user_id")
        user_name = session_data.get("user_name")
        
        if not all([graph_id, user_id, user_name]):
            raise HTTPException(
                status_code=400, 
                detail="graph_id, user_id, and user_name are required"
            )
        
        result = await realtime_collaboration_service.create_collaboration_session(
            graph_id, user_id, user_name, db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating collaboration session: {e}")
        raise HTTPException(status_code=500, detail=f"Session creation failed: {str(e)}")


@router.post("/sessions/{session_id}/join")
async def join_collaboration_session(
    session_id: str,
    join_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Join an existing collaboration session."""
    try:
        user_id = join_data.get("user_id")
        user_name = join_data.get("user_name")
        
        if not all([user_id, user_name]):
            raise HTTPException(
                status_code=400,
                detail="user_id and user_name are required"
            )
        
        # For REST API, we can't establish WebSocket here
        # User will need to connect via WebSocket for real-time features
        result = await realtime_collaboration_service.join_collaboration_session(
            session_id, user_id, user_name, None, db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Session joined. Connect via WebSocket for real-time collaboration.",
            "websocket_url": f"/api/v1/collaboration/ws/{session_id}",
            "user_info": result.get("user_info")
        }
        
    except Exception as e:
        logger.error(f"Error joining collaboration session: {e}")
        raise HTTPException(status_code=500, detail=f"Session join failed: {str(e)}")


@router.post("/sessions/{session_id}/leave")
async def leave_collaboration_session(
    session_id: str,
    leave_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Leave a collaboration session."""
    try:
        user_id = leave_data.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="user_id is required"
            )
        
        result = await realtime_collaboration_service.leave_collaboration_session(user_id, db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error leaving collaboration session: {e}")
        raise HTTPException(status_code=500, detail=f"Session leave failed: {str(e)}")


@router.get("/sessions/{session_id}/state")
async def get_session_state(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get current state of a collaboration session."""
    try:
        result = await realtime_collaboration_service.get_session_state(session_id, db)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting session state: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session state: {str(e)}")


@router.post("/sessions/{session_id}/operations")
async def apply_operation(
    session_id: str,
    operation_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Apply an operation to the knowledge graph."""
    try:
        user_id = operation_data.get("user_id")
        operation_type_str = operation_data.get("operation_type")
        target_id = operation_data.get("target_id")
        data = operation_data.get("data", {})
        
        if not all([user_id, operation_type_str]):
            raise HTTPException(
                status_code=400,
                detail="user_id and operation_type are required"
            )
        
        # Parse operation type
        try:
            operation_type = OperationType(operation_type_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid operation_type: {operation_type_str}"
            )
        
        result = await realtime_collaboration_service.apply_operation(
            session_id, user_id, operation_type, target_id, data, db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying operation: {e}")
        raise HTTPException(status_code=500, detail=f"Operation failed: {str(e)}")


@router.post("/sessions/{session_id}/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    session_id: str,
    conflict_id: str,
    resolution_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Resolve a conflict in the collaboration session."""
    try:
        user_id = resolution_data.get("user_id")
        resolution_strategy = resolution_data.get("resolution_strategy")
        resolution_data_content = resolution_data.get("resolution_data", {})
        
        if not all([user_id, resolution_strategy]):
            raise HTTPException(
                status_code=400,
                detail="user_id and resolution_strategy are required"
            )
        
        result = await realtime_collaboration_service.resolve_conflict(
            session_id, user_id, conflict_id, resolution_strategy, 
            resolution_data_content, db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error resolving conflict: {e}")
        raise HTTPException(status_code=500, detail=f"Conflict resolution failed: {str(e)}")


@router.get("/sessions/{session_id}/users/{user_id}/activity")
async def get_user_activity(
    session_id: str,
    user_id: str,
    minutes: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get activity for a specific user in a session."""
    try:
        result = await realtime_collaboration_service.get_user_activity(
            session_id, user_id, minutes
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user activity: {str(e)}")


@router.get("/sessions/active")
async def get_active_sessions():
    """Get list of active collaboration sessions."""
    try:
        active_sessions = []
        
        for session_id, session in realtime_collaboration_service.active_sessions.items():
            active_sessions.append({
                "session_id": session_id,
                "graph_id": session.graph_id,
                "created_at": session.created_at.isoformat(),
                "active_users": len(session.active_users),
                "operations_count": len(session.operations),
                "pending_changes": len(session.pending_changes)
            })
        
        return {
            "success": True,
            "active_sessions": active_sessions,
            "total_active": len(active_sessions)
        }
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active sessions: {str(e)}")


@router.get("/conflicts/types")
async def get_conflict_types():
    """Get available conflict resolution strategies."""
    try:
        conflict_types = [
            {
                "type": ConflictType.EDIT_CONFLICT.value,
                "description": "Multiple users editing the same item",
                "resolution_strategies": ["accept_current", "accept_original", "merge"]
            },
            {
                "type": ConflictType.DELETE_CONFLICT.value,
                "description": "User trying to delete an item being edited",
                "resolution_strategies": ["accept_current", "accept_original"]
            },
            {
                "type": ConflictType.RELATION_CONFLICT.value,
                "description": "Conflicting relationship operations",
                "resolution_strategies": ["accept_current", "accept_original", "merge"]
            },
            {
                "type": ConflictType.VERSION_CONFLICT.value,
                "description": "Version conflicts during editing",
                "resolution_strategies": ["accept_current", "accept_original", "merge"]
            }
        ]
        
        return {
            "success": True,
            "conflict_types": conflict_types
        }
        
    except Exception as e:
        logger.error(f"Error getting conflict types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conflict types: {str(e)}")


@router.get("/operations/types")
async def get_operation_types():
    """Get available operation types."""
    try:
        operation_types = [
            {
                "type": OperationType.CREATE_NODE.value,
                "description": "Create a new knowledge node",
                "required_fields": ["name", "node_type", "platform"],
                "optional_fields": ["description", "minecraft_version", "properties"]
            },
            {
                "type": OperationType.UPDATE_NODE.value,
                "description": "Update an existing knowledge node",
                "required_fields": ["target_id"],
                "optional_fields": ["name", "description", "properties", "expert_validated"]
            },
            {
                "type": OperationType.DELETE_NODE.value,
                "description": "Delete a knowledge node",
                "required_fields": ["target_id"],
                "optional_fields": []
            },
            {
                "type": OperationType.CREATE_RELATIONSHIP.value,
                "description": "Create a new relationship between nodes",
                "required_fields": ["source_id", "target_id", "relationship_type"],
                "optional_fields": ["confidence_score", "properties"]
            },
            {
                "type": OperationType.UPDATE_RELATIONSHIP.value,
                "description": "Update an existing relationship",
                "required_fields": ["target_id"],
                "optional_fields": ["relationship_type", "confidence_score", "properties"]
            },
            {
                "type": OperationType.DELETE_RELATIONSHIP.value,
                "description": "Delete a relationship",
                "required_fields": ["target_id"],
                "optional_fields": []
            },
            {
                "type": OperationType.CREATE_PATTERN.value,
                "description": "Create a new conversion pattern",
                "required_fields": ["java_concept", "bedrock_concept", "pattern_type"],
                "optional_fields": ["minecraft_version", "success_rate", "conversion_features"]
            },
            {
                "type": OperationType.UPDATE_PATTERN.value,
                "description": "Update an existing conversion pattern",
                "required_fields": ["target_id"],
                "optional_fields": ["bedrock_concept", "success_rate", "conversion_features"]
            },
            {
                "type": OperationType.DELETE_PATTERN.value,
                "description": "Delete a conversion pattern",
                "required_fields": ["target_id"],
                "optional_fields": []
            }
        ]
        
        return {
            "success": True,
            "operation_types": operation_types
        }
        
    except Exception as e:
        logger.error(f"Error getting operation types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get operation types: {str(e)}")


# WebSocket Endpoint

@router.websocket("/ws/{session_id}")
async def websocket_collaboration(
    websocket: WebSocket,
    session_id: str,
    user_id: str,
    user_name: str
):
    """WebSocket endpoint for real-time collaboration."""
    try:
        # Accept WebSocket connection
        await websocket.accept()
        
        # Create database session for WebSocket operations
        async with get_async_session() as db:
            # Join collaboration session
            result = await realtime_collaboration_service.join_collaboration_session(
                session_id, user_id, user_name, websocket, db
            )
            
            if not result["success"]:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": result["error"]
                }))
                await websocket.close()
                return
            
            # Send welcome message
            await websocket.send_text(json.dumps({
                "type": "welcome",
                "session_id": session_id,
                "user_info": result.get("user_info"),
                "message": "Connected to collaboration session"
            }))
            
            # Handle WebSocket messages
            try:
                while True:
                    # Receive message
                    message = await websocket.receive_text()
                    message_data = json.loads(message)
                    
                    # Handle message
                    response = await realtime_collaboration_service.handle_websocket_message(
                        user_id, message_data, db
                    )
                    
                    # Send response if needed
                    if response.get("success") and response.get("message"):
                        await websocket.send_text(json.dumps({
                            "type": "response",
                            "message": response["message"],
                            "timestamp": message_data.get("timestamp")
                        }))
                    elif not response.get("success"):
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "error": response.get("error"),
                            "timestamp": message_data.get("timestamp")
                        }))
            
            except WebSocketDisconnect:
                # Handle disconnection
                logger.info(f"WebSocket disconnected for user {user_id}")
                await realtime_collaboration_service.handle_websocket_disconnect(user_id)
            
            except Exception as e:
                logger.error(f"Error in WebSocket collaboration: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": f"WebSocket error: {str(e)}"
                }))
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id} in session {session_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket endpoint: {e}")
        try:
            await websocket.close()
        except:
            pass


# Utility Endpoints

@router.get("/stats")
async def get_collaboration_stats():
    """Get collaboration service statistics."""
    try:
        total_sessions = len(realtime_collaboration_service.active_sessions)
        total_users = len(realtime_collaboration_service.user_sessions)
        total_connections = len(realtime_collaboration_service.websocket_connections)
        total_operations = len(realtime_collaboration_service.operation_history)
        total_conflicts = len(realtime_collaboration_service.conflict_resolutions)
        
        # Calculate sessions by user count
        sessions_by_users = {}
        for session in realtime_collaboration_service.active_sessions.values():
            user_count = len(session.active_users)
            sessions_by_users[user_count] = sessions_by_users.get(user_count, 0) + 1
        
        return {
            "success": True,
            "stats": {
                "total_active_sessions": total_sessions,
                "total_active_users": total_users,
                "total_websocket_connections": total_connections,
                "total_operations": total_operations,
                "total_conflicts_resolved": total_conflicts,
                "sessions_by_user_count": sessions_by_users,
                "average_users_per_session": total_users / total_sessions if total_sessions > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting collaboration stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
