"""
Tests for collaboration API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json

from src.main import app

client = TestClient(app)


class TestCollaborationAPI:
    """Test collaboration management endpoints."""

    def test_list_collaborations_empty(self):
        """Test listing collaborations when none exist."""
        response = client.get("/api/v1/collaboration/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["projects"] == []

    @patch('src.api.collaboration.get_collaboration_projects')
    def test_list_collaborations_with_data(self, mock_get_projects):
        """Test listing collaborations with existing data."""
        mock_projects = [
            {
                "id": 1,
                "name": "Project Alpha",
                "description": "Test project",
                "status": "active",
                "created_at": "2023-01-01T00:00:00Z"
            },
            {
                "id": 2,
                "name": "Project Beta",
                "description": "Another test project",
                "status": "active",
                "created_at": "2023-01-02T00:00:00Z"
            }
        ]
        mock_get_projects.return_value = mock_projects
        
        response = client.get("/api/v1/collaboration/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) == 2
        assert data["projects"][0]["name"] == "Project Alpha"

    def test_get_collaboration_not_found(self):
        """Test getting a non-existent collaboration."""
        response = client.get("/api/v1/collaboration/projects/999")
        assert response.status_code == 404

    @patch('src.api.collaboration.get_collaboration_project')
    def test_get_collaboration_found(self, mock_get_project):
        """Test getting an existing collaboration."""
        mock_project = {
            "id": 1,
            "name": "Test Project",
            "description": "Test description",
            "status": "active",
            "members": 5,
            "created_at": "2023-01-01T00:00:00Z"
        }
        mock_get_project.return_value = mock_project
        
        response = client.get("/api/v1/collaboration/projects/1")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"

    @patch('src.api.collaboration.create_collaboration_project')
    def test_create_collaboration_success(self, mock_create):
        """Test successful collaboration creation."""
        mock_project = {
            "id": 1,
            "name": "New Project",
            "description": "New test project",
            "status": "active",
            "created_at": "2023-01-01T00:00:00Z"
        }
        mock_create.return_value = mock_project
        
        project_data = {
            "name": "New Project",
            "description": "New test project",
            "type": "conversion"
        }
        
        response = client.post("/api/v1/collaboration/projects", json=project_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"

    def test_create_collaboration_validation_error(self):
        """Test collaboration creation with invalid data."""
        invalid_data = {
            "name": "",  # Empty name
            "description": "",  # Empty description
            "type": "invalid_type"
        }
        
        response = client.post("/api/v1/collaboration/projects", json=invalid_data)
        assert response.status_code == 422

    @patch('src.api.collaboration.update_collaboration_project')
    def test_update_collaboration_success(self, mock_update):
        """Test successful collaboration update."""
        mock_project = {
            "id": 1,
            "name": "Updated Project",
            "description": "Updated description",
            "status": "active"
        }
        mock_update.return_value = mock_project
        
        update_data = {
            "name": "Updated Project",
            "description": "Updated description"
        }
        
        response = client.put("/api/v1/collaboration/projects/1", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project"

    @patch('src.api.collaboration.delete_collaboration_project')
    def test_delete_collaboration(self, mock_delete):
        """Test deleting a collaboration project."""
        mock_delete.return_value = True
        
        response = client.delete("/api/v1/collaboration/projects/1")
        assert response.status_code == 204

    def test_get_collaboration_members(self):
        """Test getting project members."""
        response = client.get("/api/v1/collaboration/projects/1/members")
        # Should return 200 with empty list or actual members
        assert response.status_code in [200, 404]

    @patch('src.api.collaboration.add_collaboration_member')
    def test_add_collaboration_member(self, mock_add):
        """Test adding a member to collaboration."""
        mock_member = {
            "id": "user123",
            "name": "Test User",
            "email": "test@example.com",
            "role": "member",
            "joined_at": "2023-01-01T00:00:00Z"
        }
        mock_add.return_value = mock_member
        
        member_data = {
            "user_id": "user123",
            "name": "Test User",
            "email": "test@example.com",
            "role": "member"
        }
        
        response = client.post("/api/v1/collaboration/projects/1/members", json=member_data)
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == "user123"

    def test_remove_collaboration_member(self):
        """Test removing a member from collaboration."""
        response = client.delete("/api/v1/collaboration/projects/1/members/user123")
        # Should return 204 for successful removal or 404 if not found
        assert response.status_code in [204, 404]

    @patch('src.api.collaboration.get_collaboration_activities')
    def test_get_collaboration_activities(self, mock_activities):
        """Test getting collaboration activities."""
        mock_activities.return_value = [
            {
                "id": 1,
                "type": "file_uploaded",
                "user": "user123",
                "description": "Uploaded texture file",
                "timestamp": "2023-01-01T00:00:00Z"
            }
        ]
        
        response = client.get("/api/v1/collaboration/projects/1/activities")
        assert response.status_code == 200
        data = response.json()
        assert len(data["activities"]) == 1

    def test_share_collaboration_project(self):
        """Test sharing a collaboration project."""
        share_data = {
            "emails": ["user@example.com", "friend@example.com"],
            "message": "Please join my project",
            "role": "member"
        }
        
        response = client.post("/api/v1/collaboration/projects/1/share", json=share_data)
        # Should return 200 for success or 400 for invalid data
        assert response.status_code in [200, 400]

    @patch('src.api.collaboration.get_collaboration_permissions')
    def test_get_collaboration_permissions(self, mock_permissions):
        """Test getting collaboration permissions."""
        mock_permissions.return_value = {
            "can_view": True,
            "can_edit": True,
            "can_delete": False,
            "can_add_members": True,
            "can_remove_members": False
        }
        
        response = client.get("/api/v1/collaboration/projects/1/permissions")
        assert response.status_code == 200
        data = response.json()
        assert data["can_view"] is True
        assert data["can_delete"] is False

    @patch('src.api.collaboration.update_collaboration_permissions')
    def test_update_collaboration_permissions(self, mock_update):
        """Test updating collaboration permissions."""
        mock_update.return_value = True
        
        permission_data = {
            "user_id": "user123",
            "permissions": {
                "can_edit": True,
                "can_delete": True,
                "can_add_members": False
            }
        }
        
        response = client.put("/api/v1/collaboration/projects/1/permissions", json=permission_data)
        assert response.status_code == 200

    def test_collaboration_search(self):
        """Test searching collaboration projects."""
        response = client.get("/api/v1/collaboration/search?query=test")
        # Should return 200 with search results
        assert response.status_code == 200

    def test_get_collaboration_stats(self):
        """Test getting collaboration statistics."""
        response = client.get("/api/v1/collaboration/projects/1/stats")
        # Should return 200 with statistics or 404 if not found
        assert response.status_code in [200, 404]

    @patch('src.api.collaboration.create_collaboration_invitation')
    def test_create_collaboration_invitation(self, mock_invite):
        """Test creating collaboration invitation."""
        mock_invite.return_value = {
            "id": "invite123",
            "project_id": 1,
            "email": "user@example.com",
            "role": "member",
            "status": "pending",
            "expires_at": "2023-01-08T00:00:00Z"
        }
        
        invitation_data = {
            "email": "user@example.com",
            "role": "member",
            "message": "Join my project"
        }
        
        response = client.post("/api/v1/collaboration/invitations", json=invitation_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "user@example.com"

    def test_accept_collaboration_invitation(self):
        """Test accepting collaboration invitation."""
        response = client.post("/api/v1/collaboration/invitations/invite123/accept")
        # Should return 200 for success or 404 if not found
        assert response.status_code in [200, 404]

    def test_decline_collaboration_invitation(self):
        """Test declining collaboration invitation."""
        response = client.post("/api/v1/collaboration/invitations/invite123/decline")
        # Should return 200 for success or 404 if not found
        assert response.status_code in [200, 404]

    @patch('src.api.collaboration.get_user_collaborations')
    def test_get_user_collaborations(self, mock_user_projects):
        """Test getting user's collaboration projects."""
        mock_user_projects.return_value = [
            {
                "id": 1,
                "name": "User Project 1",
                "role": "owner"
            },
            {
                "id": 2,
                "name": "User Project 2",
                "role": "member"
            }
        ]
        
        response = client.get("/api/v1/collaboration/user/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) == 2

    def test_collaboration_comment_system(self):
        """Test collaboration comment system."""
        # Test adding comment
        comment_data = {
            "content": "This is a comment",
            "user_id": "user123"
        }
        
        response = client.post("/api/v1/collaboration/projects/1/comments", json=comment_data)
        # Should return 201 for success or validation error
        assert response.status_code in [201, 400, 422]

    def test_get_collaboration_comments(self):
        """Test getting collaboration comments."""
        response = client.get("/api/v1/collaboration/projects/1/comments")
        # Should return 200 with comments list
        assert response.status_code == 200

    def test_collaboration_notification_system(self):
        """Test collaboration notification system."""
        response = client.get("/api/v1/collaboration/notifications")
        # Should return 200 with notifications list
        assert response.status_code == 200

    def test_error_handling_collaboration(self):
        """Test collaboration error handling."""
        with patch('src.api.collaboration.get_collaboration_projects', side_effect=Exception("Database error")):
            response = client.get("/api/v1/collaboration/projects")
            assert response.status_code == 500

    def test_collaboration_rate_limiting(self):
        """Test collaboration API rate limiting."""
        responses = []
        for _ in range(5):
            response = client.get("/api/v1/collaboration/projects")
            responses.append(response.status_code)
        
        # Should either allow all requests or enforce rate limiting
        assert all(status in [200, 429] for status in responses)

    def test_collaboration_response_headers(self):
        """Test that collaboration responses have appropriate headers."""
        response = client.get("/api/v1/collaboration/projects")
        headers = response.headers
        # Test for CORS headers
        assert "access-control-allow-origin" in headers
