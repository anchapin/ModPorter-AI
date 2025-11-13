"""
Tests for assets management API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
import tempfile
import os

from src.main import app
from src.models.addon_models import AddonAsset

client = TestClient(app)


class TestAssetsAPI:
    """Test assets management endpoints."""

    def test_list_assets_empty(self):
        """Test listing assets when none exist."""
        response = client.get("/api/v1/assets")
        assert response.status_code == 200
        data = response.json()
        assert data["assets"] == []

    @patch('src.api.assets.get_assets')
    def test_list_assets_with_data(self, mock_get_assets):
        """Test listing assets with existing data."""
        mock_assets = [
            AddonAsset(id="1", type="texture", path="/path/to/asset1", original_filename="asset1.png"),
            AddonAsset(id="2", type="model", path="/path/to/asset2", original_filename="asset2.json")
        ]
        mock_get_assets.return_value = mock_assets
        
        response = client.get("/api/v1/assets")
        assert response.status_code == 200
        data = response.json()
        assert len(data["assets"]) == 2
        assert data["assets"][0]["type"] == "texture"

    def test_get_asset_not_found(self):
        """Test getting a non-existent asset."""
        response = client.get("/api/v1/assets/999")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @patch('src.api.assets.get_asset_by_id')
    def test_get_asset_found(self, mock_get_asset):
        """Test getting an existing asset."""
        mock_asset = AddonAsset(id="1", type="texture", path="/path/to/test", original_filename="test.png")
        mock_get_asset.return_value = mock_asset
        
        response = client.get("/api/v1/assets/1")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "texture"
        assert data["path"] == "/path/to/test"

    @patch('src.api.assets.create_asset')
    def test_create_asset_success(self, mock_create):
        """Test successful asset creation."""
        mock_asset = AddonAsset(id="1", type="model", path="/path/to/new", original_filename="new_asset.json")
        mock_create.return_value = mock_asset
        
        asset_data = {
            "type": "model",
            "path": "/path/to/new",
            "original_filename": "new_asset.json"
        }
        
        response = client.post("/api/v1/assets", json=asset_data)
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "model"
        mock_create.assert_called_once()

    def test_create_asset_validation_error(self):
        """Test asset creation with invalid data."""
        invalid_data = {
            "type": "",  # Empty type
            "path": "/path/to/asset",
            "original_filename": "asset.png"
        }
        
        response = client.post("/api/v1/assets", json=invalid_data)
        assert response.status_code == 422

    @patch('src.api.assets.upload_asset_file')
    def test_upload_asset_file(self, mock_upload):
        """Test asset file upload."""
        mock_upload.return_value = AddonAsset(id="1", type="texture", path="/uploads/test.png", original_filename="test.png")
        
        # Create a temporary file for upload
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_file.write(b"fake image data")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as f:
                response = client.post(
                    "/api/v1/assets/upload",
                    files={"file": ("test.png", f, "image/png")}
                )
            
            assert response.status_code == 201
            data = response.json()
            assert data["type"] == "texture"
        finally:
            os.unlink(temp_file_path)

    def test_upload_invalid_file_type(self):
        """Test upload with invalid file type."""
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as temp_file:
            temp_file.write(b"fake exe data")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as f:
                response = client.post(
                    "/api/v1/assets/upload",
                    files={"file": ("malware.exe", f, "application/x-executable")}
                )
            
            assert response.status_code == 400
            data = response.json()
            assert "file type" in data["detail"].lower()
        finally:
            os.unlink(temp_file_path)

    @patch('src.api.assets.update_asset')
    def test_update_asset_success(self, mock_update):
        """Test successful asset update."""
        mock_asset = AddonAsset(id="1", type="texture", path="/path/to/updated", original_filename="updated.png")
        mock_update.return_value = mock_asset
        
        update_data = {
            "type": "texture",
            "path": "/path/to/updated",
            "original_filename": "updated.png"
        }
        
        response = client.put("/api/v1/assets/1", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "texture"

    def test_update_asset_not_found(self):
        """Test updating a non-existent asset."""
        update_data = {"name": "updated_asset"}
        
        response = client.put("/api/v1/assets/999", json=update_data)
        assert response.status_code == 404

    @patch('src.api.assets.delete_asset')
    def test_delete_asset_success(self, mock_delete):
        """Test successful asset deletion."""
        mock_delete.return_value = True
        
        response = client.delete("/api/v1/assets/1")
        assert response.status_code == 204
        mock_delete.assert_called_once_with(1)

    def test_delete_asset_not_found(self):
        """Test deleting a non-existent asset."""
        response = client.delete("/api/v1/assets/999")
        assert response.status_code == 404

    @patch('src.api.assets.search_assets')
    def test_search_assets(self, mock_search):
        """Test asset search functionality."""
        mock_assets = [
            AddonAsset(id="1", type="texture", path="/path/to/oak", original_filename="oak_texture.png"),
            AddonAsset(id="2", type="model", path="/path/to/oak_model", original_filename="oak_model.json")
        ]
        mock_search.return_value = mock_assets
        
        response = client.get("/api/v1/assets/search?query=oak")
        assert response.status_code == 200
        data = response.json()
        assert len(data["assets"]) == 2
        assert all("oak" in asset["path"] for asset in data["assets"])

    @patch('src.api.assets.get_asset_metadata')
    def test_get_asset_metadata(self, mock_metadata):
        """Test getting asset metadata."""
        mock_metadata.return_value = {
            "file_size": 1024,
            "file_type": "image/png",
            "created_at": "2023-01-01T00:00:00Z",
            "checksum": "abc123"
        }
        
        response = client.get("/api/v1/assets/1/metadata")
        assert response.status_code == 200
        data = response.json()
        assert data["file_size"] == 1024
        assert data["file_type"] == "image/png"

    @patch('src.api.assets.get_assets_by_type')
    def test_get_assets_by_type(self, mock_get_by_type):
        """Test filtering assets by type."""
        mock_assets = [
            AddonAsset(id="1", type="texture", path="/path/to/tex1", original_filename="texture1.png"),
            AddonAsset(id="2", type="texture", path="/path/to/tex2", original_filename="texture2.png")
        ]
        mock_get_by_type.return_value = mock_assets
        
        response = client.get("/api/v1/assets?type=texture")
        assert response.status_code == 200
        data = response.json()
        assert len(data["assets"]) == 2
        assert all(asset["asset_type"] == "texture" for asset in data["assets"])

    def test_get_assets_pagination(self):
        """Test assets list pagination."""
        response = client.get("/api/v1/assets?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert "pagination" in data

    @patch('src.api.assets.compress_asset')
    def test_compress_asset(self, mock_compress):
        """Test asset compression."""
        mock_compress.return_value = {
            "original_size": 2048,
            "compressed_size": 1024,
            "compression_ratio": 0.5,
            "compressed_path": "/compressed/test.png"
        }
        
        response = client.post("/api/v1/assets/1/compress")
        assert response.status_code == 200
        data = response.json()
        assert data["compression_ratio"] == 0.5

    @patch('src.api.assets.validate_asset_file')
    def test_validate_asset_file(self, mock_validate):
        """Test asset file validation."""
        mock_validate.return_value = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        response = client.post("/api/v1/assets/1/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_error_handling_database_failure(self):
        """Test error handling during database failures."""
        with patch('src.api.assets.get_assets', side_effect=Exception("Database error")):
            response = client.get("/api/v1/assets")
            assert response.status_code == 500
            data = response.json()
            assert "internal server error" in data["detail"].lower()

    def test_concurrent_asset_operations(self):
        """Test handling concurrent asset operations."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/api/v1/assets")
            results.append(response.status_code)
        
        # Create multiple threads
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed or fail consistently
        assert all(status == results[0] for status in results)

    @patch('src.api.assets.get_asset_usage_stats')
    def test_get_asset_usage_stats(self, mock_stats):
        """Test getting asset usage statistics."""
        mock_stats.return_value = {
            "total_downloads": 100,
            "unique_users": 25,
            "most_downloaded": "texture1.png",
            "download_trend": "increasing"
        }
        
        response = client.get("/api/v1/assets/1/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_downloads"] == 100
        assert data["unique_users"] == 25

    def test_asset_response_headers(self):
        """Test that asset responses have appropriate headers."""
        response = client.get("/api/v1/assets")
        headers = response.headers
        # Test for CORS headers
        assert "access-control-allow-origin" in headers
        # Test for cache control
        assert "cache-control" in headers
