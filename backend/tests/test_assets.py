"""
Comprehensive tests for assets.py API endpoints
Tests asset upload, listing, status updates, and conversion functionality
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os
import tempfile
import uuid
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from fastapi import UploadFile

# Import the actual modules we're testing
from src.api.assets import (
    router, AssetResponse, AssetUploadRequest, AssetStatusUpdate,
    _asset_to_response, ASSETS_STORAGE_DIR, MAX_ASSET_SIZE
)

# Test database models
class MockAsset:
    def __init__(self, asset_id=None, conversion_id=None, asset_type="texture",
                 original_path=None, converted_path=None, status="pending"):
        self.id = asset_id or str(uuid.uuid4())
        self.conversion_id = conversion_id or str(uuid.uuid4())
        self.asset_type = asset_type
        self.original_path = original_path or "/path/to/original/file.png"
        self.converted_path = converted_path or "/path/to/converted/file.png"
        self.status = status
        self.asset_metadata = {"category": "test"}
        self.file_size = 1024
        self.mime_type = "image/png"
        self.original_filename = "test.png"
        self.error_message = None
        self.created_at = Mock(isoformat=lambda: "2023-01-01T00:00:00")
        self.updated_at = Mock(isoformat=lambda: "2023-01-01T00:00:00")


# Create a FastAPI test app
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()
app.include_router(router, prefix="/api")


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_asset():
    """Create a mock asset object."""
    return MockAsset()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestAssetHelpers:
    """Test helper functions in assets.py"""

    def test_asset_to_response(self, mock_asset):
        """Test conversion of database asset to API response."""
        response = _asset_to_response(mock_asset)

        assert isinstance(response, AssetResponse)
        assert response.id == str(mock_asset.id)
        assert response.conversion_id == str(mock_asset.conversion_id)
        assert response.asset_type == mock_asset.asset_type
        assert response.original_path == mock_asset.original_path
        assert response.converted_path == mock_asset.converted_path
        assert response.status == mock_asset.status
        assert response.asset_metadata == mock_asset.asset_metadata
        assert response.file_size == mock_asset.file_size
        assert response.mime_type == mock_asset.mime_type
        assert response.original_filename == mock_asset.original_filename
        assert response.error_message == mock_asset.error_message
        assert response.created_at == "2023-01-01T00:00:00"
        assert response.updated_at == "2023-01-01T00:00:00"


class TestListConversionAssets:
    """Test list_conversion_assets endpoint"""

    @patch('backend.src.api.assets.crud.list_assets_for_conversion')
    async def test_list_conversion_assets_basic(self, mock_list_assets, mock_db):
        """Test basic listing of conversion assets."""
        # Setup mock
        asset1 = MockAsset(asset_id="123")
        asset2 = MockAsset(asset_id="456")
        mock_list_assets.return_value = [asset1, asset2]

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.get("/api/conversions/test-conversion/assets")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "123"
        assert data[1]["id"] == "456"
        # Verify the mock was called (actual db session may differ)
        mock_list_assets.assert_called_once()

    @patch('backend.src.api.assets.crud.list_assets_for_conversion')
    async def test_list_conversion_assets_with_filters(self, mock_list_assets, mock_db):
        """Test listing assets with type and status filters."""
        # Setup mock
        mock_list_assets.return_value = [MockAsset()]

        # Execute API call with filters
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.get(
                "/api/conversions/test-conversion/assets",
                params={"asset_type": "texture", "status": "pending", "limit": 50}
            )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # Verify the mock was called with the right parameters
        mock_list_assets.assert_called_once()
        call_args = mock_list_assets.call_args
        assert call_args[1]['conversion_id'] == "test-conversion"
        assert call_args[1]['asset_type'] == "texture"
        assert call_args[1]['status'] == "pending"
        assert call_args[1]['limit'] == 50

    @patch('backend.src.api.assets.crud.list_assets_for_conversion')
    async def test_list_conversion_assets_error_handling(self, mock_list_assets, mock_db):
        """Test error handling in asset listing."""
        # Setup mock to raise exception
        mock_list_assets.side_effect = Exception("Database error")

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.get("/api/conversions/test-conversion/assets")

        # Assertions
        assert response.status_code == 500
        assert "Failed to retrieve assets" in response.json()["detail"]


class TestUploadAsset:
    """Test upload_asset endpoint"""

    @patch('backend.src.api.assets.crud.create_asset')
    def test_upload_asset_basic(self, mock_create_asset, mock_db):
        """Test basic asset upload."""
        # Setup mocks
        asset_id = str(uuid.uuid4())
        mock_create_asset.return_value = MockAsset(asset_id=asset_id)

        # Create a temporary file to simulate upload
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            tmp.write(b"test image data")
            tmp.seek(0)

            # Execute API call
            with tempfile.TemporaryDirectory() as temp_dir:
                with patch('backend.src.api.assets.get_db', return_value=mock_db), \
                     patch('backend.src.api.assets.ASSETS_STORAGE_DIR', temp_dir):
                    client = TestClient(app)
                    response = client.post(
                        "/api/conversions/test-conversion/assets",
                        data={"asset_type": "texture"},
                        files={"file": ("test.png", tmp.read(), "image/png")}
                    )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["asset_type"] == "texture"
        assert data["id"] == asset_id
        assert data["conversion_id"] == str(MockAsset(asset_id=asset_id).conversion_id)

    def test_upload_asset_no_file(self):
        """Test upload with no file provided."""
        client = TestClient(app)
        response = client.post(
            "/api/conversions/test-conversion/assets",
            data={"asset_type": "texture"}
        )

        # Assertions
        assert response.status_code == 422
        # FastAPI returns 422 for validation errors when required file is missing

    @patch('backend.src.api.assets.crud.create_asset')
    def test_upload_asset_file_size_limit(self, mock_create_asset):
        """Test upload with file exceeding size limit."""
        # Setup mock to be called when file is small enough
        mock_create_asset.return_value = MockAsset()

        # Create a large temporary file
        large_size = MAX_ASSET_SIZE + 1024  # 1KB over limit
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            tmp.write(b"x" * large_size)
            tmp.seek(0)

            # Execute API call
            with tempfile.TemporaryDirectory() as tmp_dir:
                with patch('backend.src.api.assets.ASSETS_STORAGE_DIR', tmp_dir):
                    client = TestClient(app)
                    response = client.post(
                        "/api/conversions/test-conversion/assets",
                        data={"asset_type": "texture"},
                        files={"file": ("large.png", tmp.read(), "image/png")}
                    )

        # Assertions
        assert response.status_code == 413
        assert "File size exceeds the limit" in response.json()["detail"]
        # Ensure the asset creation was not called
        mock_create_asset.assert_not_called()

    @patch('backend.src.api.assets.crud.create_asset')
    def test_upload_asset_database_error(self, mock_create_asset, mock_db):
        """Test upload when database creation fails."""
        # Setup mock to raise exception
        mock_create_asset.side_effect = ValueError("Invalid conversion ID")

        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            tmp.write(b"test image data")
            tmp.seek(0)

            # Execute API call
            with tempfile.TemporaryDirectory() as tmp_dir:
                with patch('backend.src.api.assets.get_db', return_value=mock_db), \
                     patch('backend.src.api.assets.ASSETS_STORAGE_DIR', tmp_dir):
                    client = TestClient(app)
                    response = client.post(
                        "/api/conversions/test-conversion/assets",
                        data={"asset_type": "texture"},
                        files={"file": ("test.png", tmp.read(), "image/png")}
                    )

        # Assertions
        assert response.status_code == 400
        assert "Invalid conversion ID" in response.json()["detail"]


class TestGetAsset:
    """Test get_asset endpoint"""

    @patch('backend.src.api.assets.crud.get_asset')
    async def test_get_asset_basic(self, mock_get_asset, mock_db):
        """Test getting an existing asset."""
        # Setup mock
        asset_id = str(uuid.uuid4())
        mock_asset = MockAsset(asset_id=asset_id)
        mock_get_asset.return_value = mock_asset

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.get(f"/api/assets/{asset_id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == asset_id
        assert data["asset_type"] == "texture"
        mock_get_asset.assert_called_once()
        call_args = mock_get_asset.call_args
        assert call_args[0][1] == asset_id  # Second argument should be asset_id

    @patch('backend.src.api.assets.crud.get_asset')
    async def test_get_asset_not_found(self, mock_get_asset, mock_db):
        """Test getting a non-existent asset."""
        # Setup mock to return None
        asset_id = str(uuid.uuid4())
        mock_get_asset.return_value = None

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.get(f"/api/assets/{asset_id}")

        # Assertions
        assert response.status_code == 404
        assert "Asset not found" in response.json()["detail"]


class TestUpdateAssetStatus:
    """Test update_asset_status endpoint"""

    @patch('backend.src.api.assets.crud.update_asset_status')
    async def test_update_asset_status_basic(self, mock_update_asset, mock_db):
        """Test basic asset status update."""
        # Setup mock
        asset_id = str(uuid.uuid4())
        mock_asset = MockAsset(asset_id=asset_id)
        mock_update_asset.return_value = mock_asset

        # Status update data
        status_data = {
            "status": "converted",
            "converted_path": "/path/to/converted/file"
        }

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.put(
                f"/api/assets/{asset_id}/status",
                json=status_data
            )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == asset_id
        assert data["status"] == "converted"
        assert data["converted_path"] == "/path/to/converted/file"
        mock_update_asset.assert_called_once()
        call_args = mock_update_asset.call_args
        assert call_args[0][1] == asset_id  # Second argument should be asset_id
        assert call_args[1]['status'] == "converted"
        assert call_args[1]['converted_path'] == "/path/to/converted/file"
        assert call_args[1]['error_message'] is None

    @patch('backend.src.api.assets.crud.update_asset_status')
    async def test_update_asset_status_with_error(self, mock_update_asset, mock_db):
        """Test asset status update with error message."""
        # Setup mock
        asset_id = str(uuid.uuid4())
        mock_asset = MockAsset(asset_id=asset_id)
        mock_update_asset.return_value = mock_asset

        # Status update data with error
        status_data = {
            "status": "failed",
            "error_message": "Conversion failed due to invalid format"
        }

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.put(
                f"/api/assets/{asset_id}/status",
                json=status_data
            )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == asset_id
        assert data["status"] == "failed"
        assert data["error_message"] == "Conversion failed due to invalid format"
        mock_update_asset.assert_called_once()
        call_args = mock_update_asset.call_args
        assert call_args[0][1] == asset_id  # Second argument should be asset_id
        assert call_args[1]['status'] == "failed"
        assert call_args[1]['converted_path'] is None
        assert call_args[1]['error_message'] == "Conversion failed due to invalid format"

    @patch('backend.src.api.assets.crud.update_asset_status')
    async def test_update_asset_status_not_found(self, mock_update_asset, mock_db):
        """Test status update for non-existent asset."""
        # Setup mock to return None
        asset_id = str(uuid.uuid4())
        mock_update_asset.return_value = None

        # Status update data
        status_data = {
            "status": "converted"
        }

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.put(
                f"/api/assets/{asset_id}/status",
                json=status_data
            )

        # Assertions
        assert response.status_code == 404
        assert "Asset not found" in response.json()["detail"]


class TestUpdateAssetMetadata:
    """Test update_asset_metadata endpoint"""

    @patch('backend.src.api.assets.crud.update_asset_metadata')
    async def test_update_asset_metadata_basic(self, mock_update_metadata, mock_db):
        """Test basic asset metadata update."""
        # Setup mock
        asset_id = str(uuid.uuid4())
        mock_asset = MockAsset(asset_id=asset_id)
        mock_update_metadata.return_value = mock_asset

        # Metadata update data
        metadata_data = {
            "category": "blocks",
            "resolution": "16x16",
            "tags": ["minecraft", "texture"]
        }

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.put(
                f"/api/assets/{asset_id}/metadata",
                json=metadata_data
            )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == asset_id
        mock_update_metadata.assert_called_once()
        call_args = mock_update_metadata.call_args
        assert call_args[0][1] == asset_id  # Second argument should be asset_id
        assert call_args[1]['metadata'] == metadata_data

    @patch('backend.src.api.assets.crud.update_asset_metadata')
    async def test_update_asset_metadata_not_found(self, mock_update_metadata, mock_db):
        """Test metadata update for non-existent asset."""
        # Setup mock to return None
        asset_id = str(uuid.uuid4())
        mock_update_metadata.return_value = None

        # Metadata update data
        metadata_data = {
            "category": "blocks"
        }

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.put(
                f"/api/assets/{asset_id}/metadata",
                json=metadata_data
            )

        # Assertions
        assert response.status_code == 404
        assert "Asset not found" in response.json()["detail"]


class TestDeleteAsset:
    """Test delete_asset endpoint"""

    @patch('backend.src.api.assets.crud.delete_asset')
    @patch('backend.src.api.assets.crud.get_asset')
    async def test_delete_asset_basic(self, mock_get_asset, mock_delete_asset, mock_db):
        """Test basic asset deletion."""
        # Setup mocks
        asset_id = str(uuid.uuid4())
        mock_asset = MockAsset(asset_id=asset_id)
        mock_get_asset.return_value = mock_asset
        mock_delete_asset.return_value = {"deleted": True}

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove') as mock_remove:
            client = TestClient(app)
            response = client.delete(f"/api/assets/{asset_id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert f"Asset {asset_id} deleted successfully" in data["message"]
        mock_get_asset.assert_called_once()
        mock_delete_asset.assert_called_once()
        # Verify the arguments were called correctly
        get_call = mock_get_asset.call_args
        delete_call = mock_delete_asset.call_args
        assert get_call[0][1] == asset_id  # Second argument should be asset_id
        assert delete_call[0][1] == asset_id  # Second argument should be asset_id
        # Should try to remove both original and converted files
        assert mock_remove.call_count == 2

    @patch('src.api.assets.crud.get_asset')
    async def test_delete_asset_not_found(self, mock_get_asset, mock_db):
        """Test deletion of non-existent asset."""
        # Setup mock to return None
        asset_id = str(uuid.uuid4())
        mock_get_asset.return_value = None

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.delete(f"/api/assets/{asset_id}")

        # Assertions
        assert response.status_code == 404
        assert "Asset not found" in response.json()["detail"]

    @patch('backend.src.api.assets.crud.get_asset')
    async def test_delete_asset_with_missing_file(self, mock_get_asset, mock_db):
        """Test deletion when file doesn't exist on disk."""
        # Setup mocks
        asset_id = str(uuid.uuid4())
        mock_asset = MockAsset(asset_id=asset_id)
        mock_get_asset.return_value = mock_asset

        # Mock file doesn't exist
        with patch('backend.src.api.assets.crud.delete_asset', return_value={"deleted": True}), \
             patch('backend.src.api.assets.get_db', return_value=mock_db), \
             patch('os.path.exists', return_value=False), \
             patch('os.remove') as mock_remove:
            client = TestClient(app)
            response = client.delete(f"/api/assets/{asset_id}")

        # Assertions
        assert response.status_code == 200
        assert f"Asset {asset_id} deleted successfully" in response.json()["message"]
        mock_remove.assert_not_called()


class TestTriggerAssetConversion:
    """Test trigger_asset_conversion endpoint"""

    @patch('backend.src.api.assets.asset_conversion_service')
    @patch('backend.src.api.assets.crud.get_asset')
    async def test_trigger_asset_conversion_basic(self, mock_get_asset, mock_service, mock_db):
        """Test basic asset conversion trigger."""
        # Setup mocks
        asset_id = str(uuid.uuid4())
        mock_asset = MockAsset(asset_id=asset_id, status="pending")
        mock_get_asset.return_value = mock_asset
        mock_service.convert_asset.return_value = {
            "success": True
        }

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.post(f"/api/assets/{asset_id}/convert")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == asset_id
        mock_get_asset.assert_called()
        mock_service.convert_asset.assert_called_once_with(asset_id)

    @patch('backend.src.api.assets.crud.get_asset')
    async def test_trigger_asset_conversion_not_found(self, mock_get_asset, mock_db):
        """Test conversion trigger for non-existent asset."""
        # Setup mock to return None
        asset_id = str(uuid.uuid4())
        mock_get_asset.return_value = None

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.post(f"/api/assets/{asset_id}/convert")

        # Assertions
        assert response.status_code == 404
        assert "Asset not found" in response.json()["detail"]

    @patch('backend.src.api.assets.asset_conversion_service')
    @patch('backend.src.api.assets.crud.get_asset')
    async def test_trigger_asset_conversion_already_converted(self, mock_get_asset, mock_service, mock_db):
        """Test conversion trigger for already converted asset."""
        # Setup mocks
        asset_id = str(uuid.uuid4())
        mock_asset = MockAsset(asset_id=asset_id, status="converted")
        mock_get_asset.return_value = mock_asset

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.post(f"/api/assets/{asset_id}/convert")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == asset_id
        assert data["status"] == "converted"
        mock_get_asset.assert_called()
        mock_service.convert_asset.assert_not_called()

    @patch('backend.src.api.assets.asset_conversion_service')
    @patch('backend.src.api.assets.crud.get_asset')
    async def test_trigger_asset_conversion_service_error(self, mock_get_asset, mock_service, mock_db):
        """Test conversion trigger when service returns failure."""
        # Setup mocks
        asset_id = str(uuid.uuid4())
        mock_asset = MockAsset(asset_id=asset_id, status="pending")
        mock_get_asset.return_value = mock_asset
        mock_service.convert_asset.return_value = {
            "success": False,
            "error": "Asset format not supported"
        }

        # Execute API call
        with patch('backend.src.api.assets.get_db', return_value=mock_db):
            client = TestClient(app)
            response = client.post(f"/api/assets/{asset_id}/convert")

        # Assertions
        assert response.status_code == 500
        assert "Asset format not supported" in response.json()["detail"]
        mock_service.convert_asset.assert_called_once_with(asset_id)


class TestConvertAllConversionAssets:
    """Test convert_all_conversion_assets endpoint"""

    @patch('src.api.assets.asset_conversion_service')
    async def test_convert_all_conversion_assets_basic(self, mock_service):
        """Test batch conversion for all assets in a conversion."""
        # Setup mock
        conversion_id = str(uuid.uuid4())
        mock_service.convert_assets_for_conversion.return_value = {
            "success": True,
            "total_assets": 10,
            "converted_count": 8,
            "failed_count": 2
        }

        # Execute API call
        client = TestClient(app)
        response = client.post(f"/api/conversions/{conversion_id}/assets/convert-all")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["conversion_id"] == conversion_id
        assert data["total_assets"] == 10
        assert data["converted_count"] == 8
        assert data["failed_count"] == 2
        assert data["success"] is True
        mock_service.convert_assets_for_conversion.assert_called_once()
        call_args = mock_service.convert_assets_for_conversion.call_args
        assert call_args[0][0] == conversion_id

    @patch('backend.src.api.assets.asset_conversion_service')
    async def test_convert_all_conversion_assets_service_error(self, mock_service):
        """Test batch conversion when service fails."""
        # Setup mock
        conversion_id = str(uuid.uuid4())
        mock_service.convert_assets_for_conversion.side_effect = Exception("Service unavailable")

        # Execute API call
        client = TestClient(app)
        response = client.post(f"/api/conversions/{conversion_id}/assets/convert-all")

        # Assertions
        assert response.status_code == 500
        assert "Failed to convert assets" in response.json()["detail"]
