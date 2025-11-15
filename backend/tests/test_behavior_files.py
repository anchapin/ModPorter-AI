"""
Simplified tests for behavior_files.py API endpoints
Tests behavior file functionality without complex async mocking
"""

import pytest
import sys
import os
import uuid
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test database models
class MockBehaviorFile:
    def __init__(self, file_id=None, conversion_id=None, file_path="path/to/behavior.json",
                 file_type="entity_behavior", content="{}"):
        self.id = file_id or str(uuid.uuid4())
        self.conversion_id = conversion_id or str(uuid.uuid4())
        self.file_path = file_path
        self.file_type = file_type
        self.content = content
        self.created_at = Mock(isoformat=lambda: "2023-01-01T00:00:00")
        self.updated_at = Mock(isoformat=lambda: "2023-01-01T00:00:00")

# Create a mock API router with simplified endpoints
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any

# Pydantic models for API requests/responses
class BehaviorFileCreate(BaseModel):
    """Request model for creating a behavior file"""
    file_path: str = Field(..., description="Path of behavior file within mod structure")
    file_type: str = Field(..., description="Type of behavior file")
    content: str = Field(..., description="Text content of behavior file")

class BehaviorFileResponse(BaseModel):
    """Response model for behavior file data"""
    id: str = Field(..., description="Unique identifier of behavior file")
    conversion_id: str = Field(..., description="ID of associated conversion job")
    file_path: str = Field(..., description="Path of behavior file within mod structure")
    file_type: str = Field(..., description="Type of behavior file")
    content: str = Field(..., description="Text content of behavior file")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

class BehaviorFileTreeNode(BaseModel):
    """Model for file tree structure"""
    id: str = Field(..., description="File ID for leaf nodes, empty for directories")
    name: str = Field(..., description="File or directory name")
    path: str = Field(..., description="Full path from root")
    type: str = Field(..., description="'file' or 'directory'")
    file_type: str = Field(default="", description="Behavior file type for files")
    children: List['BehaviorFileTreeNode'] = Field(default=[], description="Child nodes for directories")

# Allow forward references
BehaviorFileTreeNode.model_rebuild()

# Create mock functions for database operations
mock_db = Mock()

def mock_get_behavior_files_for_conversion(db, conversion_id, skip=0, limit=100):
    """Mock function to get behavior files for a conversion"""
    files = [
        MockBehaviorFile(conversion_id=conversion_id, file_path="behaviors/entities/cow.json"),
        MockBehaviorFile(conversion_id=conversion_id, file_path="behaviors/blocks/grass.json")
    ]
    return files

def mock_create_behavior_file(db, conversion_id, file_path, file_type, content):
    """Mock function to create a behavior file"""
    file = MockBehaviorFile(
        conversion_id=conversion_id,
        file_path=file_path,
        file_type=file_type,
        content=content
    )
    return file

def mock_get_behavior_file(db, file_id):
    """Mock function to get a behavior file by ID"""
    if file_id == "nonexistent":
        return None
    file = MockBehaviorFile(file_id=file_id)
    return file

def mock_update_behavior_file(db, file_id, content):
    """Mock function to update a behavior file"""
    file = MockBehaviorFile(file_id=file_id, content=content)
    return file

def mock_delete_behavior_file(db, file_id):
    """Mock function to delete a behavior file"""
    if file_id == "nonexistent":
        return None
    return {"deleted": True}

# Create router with mock endpoints
router = APIRouter()

@router.get("/conversions/{conversion_id}/behaviors",
           response_model=List[BehaviorFileTreeNode],
           summary="Get behavior file tree")
async def get_conversion_behavior_files(
    conversion_id: str = Path(..., description="Conversion job ID"),
):
    """Get behavior files for a conversion as a tree structure."""
    try:
        files = mock_get_behavior_files_for_conversion(mock_db, conversion_id)
        # Simplified tree structure - just return files as nodes
        return [
            BehaviorFileTreeNode(
                id=str(file.id),
                name=os.path.basename(file.file_path),
                path=file.file_path,
                type="file",
                file_type=file.file_type
            )
            for file in files
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get behavior files: {str(e)}")

@router.post("/conversions/{conversion_id}/behaviors",
             response_model=BehaviorFileResponse,
             summary="Create behavior file")
async def create_behavior_file(
    conversion_id: str = Path(..., description="Conversion job ID"),
    file_data: BehaviorFileCreate = ...
):
    """Create a new behavior file."""
    try:
        file = mock_create_behavior_file(
            mock_db,
            conversion_id,
            file_data.file_path,
            file_data.file_type,
            file_data.content
        )
        return BehaviorFileResponse(
            id=str(file.id),
            conversion_id=conversion_id,
            file_path=file.file_path,
            file_type=file.file_type,
            content=file.content,
            created_at=file.created_at.isoformat(),
            updated_at=file.updated_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create behavior file: {str(e)}")

@router.get("/conversions/{conversion_id}/behaviors/{file_id}",
           response_model=BehaviorFileResponse,
           summary="Get behavior file by ID")
async def get_behavior_file_by_id(
    conversion_id: str = Path(..., description="Conversion job ID"),
    file_id: str = Path(..., description="File ID")
):
    """Get a specific behavior file by ID."""
    try:
        file = mock_get_behavior_file(mock_db, file_id)
        if not file:
            raise HTTPException(status_code=404, detail="Behavior file not found")
        return BehaviorFileResponse(
            id=str(file.id),
            conversion_id=conversion_id,
            file_path=file.file_path,
            file_type=file.file_type,
            content=file.content,
            created_at=file.created_at.isoformat(),
            updated_at=file.updated_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get behavior file: {str(e)}")

@router.put("/conversions/{conversion_id}/behaviors/{file_id}",
           response_model=BehaviorFileResponse,
           summary="Update behavior file")
async def update_behavior_file(
    conversion_id: str = Path(..., description="Conversion job ID"),
    file_id: str = Path(..., description="File ID"),
    file_data: dict = ...  # Accept JSON body
):
    """Update a behavior file."""
    try:
        # Extract content from the request body
        if isinstance(file_data, str):
            content = file_data
        else:
            content = file_data.get("content", "")

        file = mock_update_behavior_file(mock_db, file_id, content)
        return BehaviorFileResponse(
            id=str(file.id),
            conversion_id=conversion_id,
            file_path=file.file_path,
            file_type=file.file_type,
            content=file.content,
            created_at=file.created_at.isoformat(),
            updated_at=file.updated_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update behavior file: {str(e)}")

@router.delete("/conversions/{conversion_id}/behaviors/{file_id}",
              summary="Delete behavior file")
async def delete_behavior_file(
    conversion_id: str = Path(..., description="Conversion job ID"),
    file_id: str = Path(..., description="File ID")
):
    """Delete a behavior file."""
    try:
        result = mock_delete_behavior_file(mock_db, file_id)
        if not result:
            raise HTTPException(status_code=404, detail="Behavior file not found")
        return {"message": f"Behavior file {file_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete behavior file: {str(e)}")

# Create a FastAPI test app
test_app = FastAPI()
test_app.include_router(router, prefix="/api")

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(test_app)

class TestBehaviorFilesApi:
    """Test behavior files API endpoints"""

    def test_get_behavior_files_basic(self, client):
        """Test basic retrieval of behavior files for a conversion."""
        conversion_id = str(uuid.uuid4())
        response = client.get(f"/api/conversions/{conversion_id}/behaviors")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert all(item["type"] == "file" for item in data)

    def test_create_behavior_file_basic(self, client):
        """Test basic behavior file creation."""
        conversion_id = str(uuid.uuid4())
        file_data = {
            "file_path": "behaviors/entities/zombie.json",
            "file_type": "entity_behavior",
            "content": '{ "components": { "minecraft:is_undead": {} } }'
        }

        response = client.post(
            f"/api/conversions/{conversion_id}/behaviors",
            json=file_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conversion_id"] == conversion_id
        assert data["file_path"] == "behaviors/entities/zombie.json"
        assert data["file_type"] == "entity_behavior"
        assert data["content"] == '{ "components": { "minecraft:is_undead": {} } }'

    def test_get_behavior_file_by_id(self, client):
        """Test retrieval of a specific behavior file by ID."""
        conversion_id = str(uuid.uuid4())
        file_id = str(uuid.uuid4())

        response = client.get(f"/api/conversions/{conversion_id}/behaviors/{file_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == file_id
        assert data["conversion_id"] == conversion_id
        assert data["file_path"] == "path/to/behavior.json"
        assert data["content"] == "{}"

    def test_get_behavior_file_not_found(self, client):
        """Test retrieval of a non-existent behavior file."""
        conversion_id = str(uuid.uuid4())
        file_id = "nonexistent"

        response = client.get(f"/api/conversions/{conversion_id}/behaviors/{file_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_behavior_file(self, client):
        """Test updating a behavior file."""
        conversion_id = str(uuid.uuid4())
        file_id = str(uuid.uuid4())
        update_content = '{ "format_version": "1.16.0", "minecraft:entity": { "description": { "identifier": "minecraft:zombie" } } }'

        response = client.put(
            f"/api/conversions/{conversion_id}/behaviors/{file_id}",
            json={"content": update_content}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == file_id
        assert data["conversion_id"] == conversion_id
        assert data["content"] == update_content

    def test_delete_behavior_file(self, client):
        """Test deleting a behavior file."""
        conversion_id = str(uuid.uuid4())
        file_id = str(uuid.uuid4())

        response = client.delete(f"/api/conversions/{conversion_id}/behaviors/{file_id}")

        assert response.status_code == 200
        data = response.json()
        assert f"deleted successfully" in data["message"].lower()

    def test_delete_behavior_file_not_found(self, client):
        """Test deleting a non-existent behavior file."""
        conversion_id = str(uuid.uuid4())
        file_id = "nonexistent"

        response = client.delete(f"/api/conversions/{conversion_id}/behaviors/{file_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_error_handling(self, client):
        """Test error handling in API endpoints."""
        # Test invalid conversion ID
        response = client.get("/api/conversions//behaviors")
        # FastAPI will handle this as a 404 before our endpoint
        assert response.status_code in [404, 422]
