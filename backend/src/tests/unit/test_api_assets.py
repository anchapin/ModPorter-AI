# backend/src/tests/unit/test_api_assets.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from api.assets import router
from fastapi import FastAPI
import uuid
from datetime import datetime

# Create a small FastAPI app for testing the router
app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def mock_asset():
    asset = MagicMock()
    asset.id = uuid.uuid4()
    asset.conversion_id = uuid.uuid4()
    asset.asset_type = "texture"
    asset.original_path = "path/to/original.png"
    asset.converted_path = None
    asset.status = "pending"
    asset.asset_metadata = {"res": "16x16"}
    asset.file_size = 1024
    asset.mime_type = "image/png"
    asset.original_filename = "original.png"
    asset.error_message = None
    asset.created_at = datetime.now()
    asset.updated_at = datetime.now()
    return asset


@patch("db.crud.list_assets_for_conversion", new_callable=AsyncMock)
def test_list_conversion_assets(mock_list, mock_asset):
    mock_list.return_value = [mock_asset]
    conversion_id = str(uuid.uuid4())

    response = client.get(f"/conversions/{conversion_id}/assets")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["asset_type"] == "texture"
    mock_list.assert_called_once()


@patch("db.crud.get_asset", new_callable=AsyncMock)
def test_get_asset_success(mock_get, mock_asset):
    mock_get.return_value = mock_asset
    asset_id = str(mock_asset.id)

    response = client.get(f"/assets/{asset_id}")

    assert response.status_code == 200
    assert response.json()["id"] == asset_id


@patch("db.crud.get_asset", new_callable=AsyncMock)
def test_get_asset_not_found(mock_get):
    mock_get.return_value = None
    asset_id = str(uuid.uuid4())

    response = client.get(f"/assets/{asset_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


@patch("db.crud.update_asset_status", new_callable=AsyncMock)
def test_update_asset_status(mock_update, mock_asset):
    mock_asset.status = "converted"
    mock_update.return_value = mock_asset
    asset_id = str(mock_asset.id)

    response = client.put(
        f"/assets/{asset_id}/status",
        json={"status": "converted", "converted_path": "path/to/conv.png"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "converted"


@patch("db.crud.update_asset_metadata", new_callable=AsyncMock)
def test_update_asset_metadata(mock_update, mock_asset):
    mock_asset.asset_metadata = {"new": "meta"}
    mock_update.return_value = mock_asset
    asset_id = str(mock_asset.id)

    response = client.put(f"/assets/{asset_id}/metadata", json={"new": "meta"})

    assert response.status_code == 200
    assert response.json()["asset_metadata"] == {"new": "meta"}


@patch("db.crud.get_asset", new_callable=AsyncMock)
@patch("db.crud.delete_asset", new_callable=AsyncMock)
@patch("os.path.exists")
@patch("os.remove")
def test_delete_asset(mock_remove, mock_exists, mock_delete, mock_get, mock_asset):
    mock_get.return_value = mock_asset
    mock_delete.return_value = {"id": str(mock_asset.id)}
    mock_exists.return_value = True
    asset_id = str(mock_asset.id)

    response = client.delete(f"/assets/{asset_id}")

    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]
    mock_delete.assert_called_once()


@patch("db.crud.get_asset", new_callable=AsyncMock)
@patch(
    "services.asset_conversion_service.asset_conversion_service.convert_asset",
    new_callable=AsyncMock,
)
def test_trigger_asset_conversion(mock_convert, mock_get, mock_asset):
    mock_get.side_effect = [mock_asset, mock_asset]  # Before and after trigger
    mock_convert.return_value = {"success": True}
    asset_id = str(mock_asset.id)

    response = client.post(f"/assets/{asset_id}/convert")

    assert response.status_code == 200
    mock_convert.assert_called_once_with(asset_id)


@patch(
    "services.asset_conversion_service.asset_conversion_service.convert_assets_for_conversion",
    new_callable=AsyncMock,
)
def test_convert_all_conversion_assets(mock_convert_all):
    mock_convert_all.return_value = {
        "success": True,
        "total_assets": 5,
        "converted_count": 5,
        "failed_count": 0,
    }
    conversion_id = str(uuid.uuid4())

    response = client.post(f"/conversions/{conversion_id}/assets/convert-all")

    assert response.status_code == 200
    assert response.json()["total_assets"] == 5
