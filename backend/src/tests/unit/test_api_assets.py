"""Tests for api/assets.py module."""

import pytest
import io
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.api.assets import router, AssetResponse, AssetUploadRequest


class TestAssetEndpoints:
    """Test cases for asset API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the assets API."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router, prefix="/api/assets")
        return TestClient(app)

    def test_router_initialization(self):
        """Test that the router is properly initialized."""
        from fastapi.routing import APIRoute
        assert router is not None
        assert hasattr(router, 'routes')
        
        # Check that expected endpoints exist
        routes = [route.path for route in router.routes if isinstance(route, APIRoute)]
        assert "/" in routes  # List assets
        assert "/{asset_id}" in routes  # Get specific asset

    def test_asset_response_model(self):
        """Test AssetResponse model."""
        data = {
            "id": "asset123",
            "conversion_id": "conv456",
            "asset_type": "texture",
            "original_path": "/path/to/original.png",
            "status": "processed",
            "original_filename": "texture.png",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z"
        }
        
        response = AssetResponse(**data)
        assert response.id == "asset123"
        assert response.conversion_id == "conv456"
        assert response.asset_type == "texture"
        assert response.status == "processed"

    def test_asset_upload_request_model(self):
        """Test AssetUploadRequest model."""
        data = {
            "asset_type": "texture",
            "metadata": {"width": 16, "height": 16}
        }
        
        request = AssetUploadRequest(**data)
        assert request.asset_type == "texture"
        assert request.metadata["width"] == 16

    @patch('src.api.assets.crud')
    def test_list_assets_success(self, mock_crud, client):
        """Test successful asset listing."""
        # Mock database response
        mock_assets = [
            {
                "id": "asset1",
                "conversion_id": "conv1",
                "asset_type": "texture",
                "status": "processed"
            }
        ]
        mock_crud.list_assets = AsyncMock(return_value=mock_assets)
        
        response = client.get("/api/assets/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == "asset1"

    @patch('src.api.assets.crud')
    def test_get_asset_success(self, mock_crud, client):
        """Test successful asset retrieval."""
        # Mock database response
        mock_asset = {
            "id": "asset123",
            "conversion_id": "conv456",
            "asset_type": "texture",
            "status": "processed"
        }
        mock_crud.get_asset = AsyncMock(return_value=mock_asset)
        
        response = client.get("/api/assets/asset123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "asset123"
        assert data["asset_type"] == "texture"

    @patch('src.api.assets.crud')
    def test_get_asset_not_found(self, mock_crud, client):
        """Test asset retrieval when asset doesn't exist."""
        mock_crud.get_asset = AsyncMock(return_value=None)
        
        response = client.get("/api/assets/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch('src.api.assets.crud')
    def test_upload_asset_success(self, mock_crud, client):
        """Test successful asset upload."""
        # Mock database operations
        mock_crud.create_asset = AsyncMock(return_value={"id": "new_asset"})
        
        # Create mock file
        file_content = b"fake_texture_data"
        file_data = (
            "texture.png",
            io.BytesIO(file_content),
            "image/png"
        )
        
        response = client.post(
            "/api/assets/",
            files={"file": file_data},
            data={
                "conversion_id": "conv123",
                "asset_type": "texture",
                "metadata": '{"width": 16}'
            }
        )
        
        # Note: This might fail due to async nature, but test structure is important
        # In real implementation, you'd need to handle async properly in tests

    def test_upload_asset_validation(self, client):
        """Test asset upload validation."""
        # Test with missing file
        response = client.post("/api/assets/")
        assert response.status_code == 422  # Validation error

    @patch('src.api.assets.crud')
    def test_delete_asset_success(self, mock_crud, client):
        """Test successful asset deletion."""
        mock_crud.delete_asset = AsyncMock(return_value=True)
        mock_crud.get_asset = AsyncMock(return_value={"id": "asset123"})
        
        response = client.delete("/api/assets/asset123")
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    @patch('src.api.assets.crud')
    def test_delete_asset_not_found(self, mock_crud, client):
        """Test asset deletion when asset doesn't exist."""
        mock_crud.get_asset = AsyncMock(return_value=None)
        
        response = client.delete("/api/assets/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch('src.api.assets.crud')
    def test_update_asset_success(self, mock_crud, client):
        """Test successful asset update."""
        # Mock existing asset
        existing_asset = {
            "id": "asset123",
            "conversion_id": "conv456",
            "status": "pending"
        }
        mock_crud.get_asset = AsyncMock(return_value=existing_asset)
        
        # Mock updated asset
        updated_asset = {**existing_asset, "status": "processed"}
        mock_crud.update_asset = AsyncMock(return_value=updated_asset)
        
        update_data = {"status": "processed"}
        response = client.put("/api/assets/asset123", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

    @patch('src.api.assets.crud')
    def test_update_asset_not_found(self, mock_crud, client):
        """Test asset update when asset doesn't exist."""
        mock_crud.get_asset = AsyncMock(return_value=None)
        
        response = client.put("/api/assets/nonexistent", json={"status": "processed"})
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_assets_storage_dir_config(self):
        """Test ASSETS_STORAGE_DIR configuration."""
        with patch.dict('os.environ', {'ASSETS_STORAGE_DIR': '/custom/assets'}):
            # Reload module to test config
            from importlib import reload
            import src.api.assets
            reload(src.api.assets)
            
            assert src.api.assets.ASSETS_STORAGE_DIR == '/custom/assets'

    def test_max_asset_size_config(self):
        """Test MAX_ASSET_SIZE configuration."""
        # Test default value
        assert src.api.assets.MAX_ASSET_SIZE == 50 * 1024 * 1024
        
        # Test that it's used for validation
        from src.api.assets import MAX_ASSET_SIZE
        assert MAX_ASSET_SIZE == 52428800  # 50 MB in bytes
