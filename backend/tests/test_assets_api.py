
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
import tempfile
import os
import uuid
from datetime import datetime

# Import the app from the main module
from src.main import app

client = TestClient(app)


@pytest.fixture
def mock_db_session():
    """Fixture to mock the database session."""
    with patch("src.api.assets.get_db", new_callable=MagicMock) as mock_get_db:
        mock_session = AsyncMock()
        mock_get_db.return_value = mock_session
        yield mock_session


@pytest.fixture
def mock_asset_conversion_service():
    """Fixture to mock the asset conversion service."""
    with patch(
        "src.api.assets.asset_conversion_service", new_callable=MagicMock
    ) as mock_service:
        mock_service.convert_asset = AsyncMock()
        mock_service.convert_assets_for_conversion = AsyncMock()
        yield mock_service


class TestAssetsAPI:
    """Test assets management endpoints."""

    def test_list_assets_empty(self, mock_db_session):
        """Test listing assets when none exist."""
        conversion_id = str(uuid.uuid4())

        async def mock_list_assets(*args, **kwargs):
            return []

        with patch("src.api.assets.crud.list_assets_for_conversion", new=mock_list_assets):
            response = client.get(f"/api/v1/conversions/{conversion_id}/assets")

        assert response.status_code == 200
        assert response.json() == []

    @patch("src.api.assets.crud.create_asset", new_callable=AsyncMock)
    def test_upload_asset_success(self, mock_create_asset, mock_db_session):
        """Test successful asset upload."""
        conversion_id = str(uuid.uuid4())
        asset_id = str(uuid.uuid4())
        original_filename = "test.png"

        mock_asset_data = {
            "id": asset_id,
            "conversion_id": conversion_id,
            "asset_type": "texture",
            "original_path": f"conversion_assets/{asset_id}.png",
            "converted_path": None,
            "status": "pending",
            "asset_metadata": {},
            "file_size": 123,
            "mime_type": "image/png",
            "original_filename": original_filename,
            "error_message": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mock_asset = MagicMock()
        for key, value in mock_asset_data.items():
            setattr(mock_asset, key, value)

        mock_create_asset.return_value = mock_asset

        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as temp_file:
            temp_file.write(b"fake image data")
            temp_file.seek(0)
            response = client.post(
                f"/api/v1/conversions/{conversion_id}/assets",
                files={"file": (original_filename, temp_file, "image/png")},
                data={"asset_type": "texture"},
            )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] is not None
        assert response_data["conversion_id"] == conversion_id
        assert response_data["asset_type"] == "texture"
        assert response_data["original_filename"] == original_filename

    @patch("src.api.assets.crud.get_asset", new_callable=AsyncMock)
    def test_get_asset_not_found(self, mock_get_asset, mock_db_session):
        """Test getting a non-existent asset."""
        asset_id = str(uuid.uuid4())
        mock_get_asset.return_value = None

        response = client.get(f"/api/v1/assets/{asset_id}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Asset not found"}

    @patch("src.api.assets.crud.update_asset_status", new_callable=AsyncMock)
    def test_update_asset_status_not_found(self, mock_update_status, mock_db_session):
        """Test updating status for a non-existent asset."""
        asset_id = str(uuid.uuid4())
        mock_update_status.return_value = None

        response = client.put(
            f"/api/v1/assets/{asset_id}/status",
            json={"status": "converted"},
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "Asset not found"}

    @patch("src.api.assets.crud.update_asset_metadata", new_callable=AsyncMock)
    def test_update_asset_metadata_not_found(self, mock_update_metadata, mock_db_session):
        """Test updating metadata for a non-existent asset."""
        asset_id = str(uuid.uuid4())
        mock_update_metadata.return_value = None

        response = client.put(
            f"/api/v1/assets/{asset_id}/metadata",
            json={"key": "value"},
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "Asset not found"}

    @patch("src.api.assets.crud.get_asset", new_callable=AsyncMock)
    @patch("src.api.assets.crud.delete_asset", new_callable=AsyncMock)
    def test_delete_asset_not_found(self, mock_delete_asset, mock_get_asset, mock_db_session):
        """Test deleting a non-existent asset."""
        asset_id = str(uuid.uuid4())
        mock_get_asset.return_value = None
        mock_delete_asset.return_value = None

        response = client.delete(f"/api/v1/assets/{asset_id}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Asset not found"}

    @patch("src.api.assets.crud.get_asset", new_callable=AsyncMock)
    def test_trigger_asset_conversion_not_found(self, mock_get_asset, mock_db_session):
        """Test triggering conversion for a non-existent asset."""
        asset_id = str(uuid.uuid4())
        mock_get_asset.return_value = None

        response = client.post(f"/api/v1/assets/{asset_id}/convert")

        assert response.status_code == 404
        assert response.json() == {"detail": "Asset not found"}

    def test_convert_all_assets_not_found(self, mock_db_session):
        """Test converting all assets for a non-existent conversion."""
        conversion_id = str(uuid.uuid4())

        with patch(
            "src.api.assets.asset_conversion_service.convert_assets_for_conversion",
            new_callable=AsyncMock,
        ) as mock_convert_all:
            mock_convert_all.return_value = {
                "total_assets": 0,
                "converted_count": 0,
                "failed_count": 0,
                "success": True,
            }
            response = client.post(
                f"/api/v1/conversions/{conversion_id}/assets/convert-all"
            )

        assert response.status_code == 200
        assert response.json()["total_assets"] == 0

    def test_upload_asset_no_file(self, mock_db_session):
        """Test uploading with no file."""
        conversion_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/conversions/{conversion_id}/assets",
            data={"asset_type": "texture"},
        )
        assert response.status_code == 422

    @patch("src.api.assets.crud.create_asset", new_callable=AsyncMock)
    def test_upload_asset_file_too_large(self, mock_create_asset, mock_db_session):
        """Test uploading a file that is too large."""
        conversion_id = str(uuid.uuid4())
        original_filename = "large_file.png"

        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as temp_file:
            temp_file.write(b"a" * (51 * 1024 * 1024))
            temp_file.seek(0)
            response = client.post(
                f"/api/v1/conversions/{conversion_id}/assets",
                files={"file": (original_filename, temp_file, "image/png")},
                data={"asset_type": "texture"},
            )

        assert response.status_code == 413
        assert "exceeds the limit" in response.json()["detail"]

    @patch("src.api.assets.crud.get_asset", new_callable=AsyncMock)
    @patch("src.api.assets.crud.delete_asset", new_callable=AsyncMock)
    @patch("os.path.exists")
    @patch("os.remove")
    def test_delete_asset_success(
        self, mock_os_remove, mock_os_path_exists, mock_delete_asset, mock_get_asset, mock_db_session
    ):
        """Test successful deletion of an asset and its files."""
        asset_id = str(uuid.uuid4())
        original_path = "path/to/original.png"
        converted_path = "path/to/converted.png"

        mock_asset = MagicMock()
        mock_asset.id = asset_id
        mock_asset.original_path = original_path
        mock_asset.converted_path = converted_path
        mock_get_asset.return_value = mock_asset
        mock_delete_asset.return_value = {"id": asset_id}
        mock_os_path_exists.return_value = True

        response = client.delete(f"/api/v1/assets/{asset_id}")

        assert response.status_code == 200
        assert response.json() == {"message": f"Asset {asset_id} deleted successfully"}
        mock_os_remove.assert_any_call(original_path)
        mock_os_remove.assert_any_call(converted_path)
