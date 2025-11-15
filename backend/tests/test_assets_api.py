
import io
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


@pytest.fixture
def mock_asset():
    return AsyncMock(
        id=uuid.uuid4(),
        conversion_id=uuid.uuid4(),
        asset_type="texture",
        original_path="/path/to/original.png",
        converted_path=None,
        status="pending",
        asset_metadata={"category": "blocks"},
        file_size=12345,
        mime_type="image/png",
        original_filename="original.png",
        error_message=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
@patch("src.api.assets.crud", new_callable=AsyncMock)
async def test_upload_asset_success(mock_crud, mock_asset):
    """
    Tests the asset upload endpoint with a successful upload.
    """
    mock_crud.create_asset.return_value = mock_asset
    file_content = b"dummy png content"
    file_like = io.BytesIO(file_content)
    files = {"file": ("test.png", file_like, "image/png")}
    data = {"asset_type": "texture"}

    response = client.post(
        f"/api/v1/conversions/{mock_asset.conversion_id}/assets", files=files, data=data
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["id"] == str(mock_asset.id)
    assert json_response["conversion_id"] == str(mock_asset.conversion_id)
    assert json_response["asset_type"] == "texture"
    assert json_response["original_filename"] == "test.png"


@pytest.mark.asyncio
@patch("src.api.assets.crud", new_callable=AsyncMock)
async def test_list_conversion_assets_success(mock_crud, mock_asset):
    """
    Tests listing assets for a conversion.
    """
    mock_crud.list_assets_for_conversion.return_value = [mock_asset]

    response = client.get(f"/api/v1/conversions/{mock_asset.conversion_id}/assets")

    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response) == 1
    assert json_response[0]["id"] == str(mock_asset.id)


@pytest.mark.asyncio
@patch("src.api.assets.crud", new_callable=AsyncMock)
async def test_get_asset_success(mock_crud, mock_asset):
    """
    Tests getting a single asset by ID.
    """
    mock_crud.get_asset.return_value = mock_asset

    response = client.get(f"/api/v1/assets/{mock_asset.id}")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["id"] == str(mock_asset.id)


@pytest.mark.asyncio
@patch("src.api.assets.crud", new_callable=AsyncMock)
async def test_get_asset_not_found(mock_crud):
    """
    Tests getting a single asset that does not exist.
    """
    mock_crud.get_asset.return_value = None
    asset_id = uuid.uuid4()

    response = client.get(f"/api/v1/assets/{asset_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
@patch("src.api.assets.crud", new_callable=AsyncMock)
async def test_update_asset_status_success(mock_crud, mock_asset):
    """
    Tests updating the status of an asset.
    """
    mock_asset.status = "converted"
    mock_crud.update_asset_status.return_value = mock_asset

    update_data = {"status": "converted", "converted_path": "/path/to/converted.png"}
    response = client.put(f"/api/v1/assets/{mock_asset.id}/status", json=update_data)

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "converted"
    assert json_response["converted_path"] == "/path/to/converted.png"


@pytest.mark.asyncio
@patch("src.api.assets.crud", new_callable=AsyncMock)
async def test_update_asset_metadata_success(mock_crud, mock_asset):
    """
    Tests updating the metadata of an asset.
    """
    mock_asset.asset_metadata = {"category": "items", "custom": "data"}
    mock_crud.update_asset_metadata.return_value = mock_asset

    update_data = {"category": "items", "custom": "data"}
    response = client.put(f"/api/v1/assets/{mock_asset.id}/metadata", json=update_data)

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["asset_metadata"]["category"] == "items"


@pytest.mark.asyncio
@patch("src.api.assets.crud", new_callable=AsyncMock)
@patch("src.api.assets.os.path.exists")
@patch("src.api.assets.os.remove")
async def test_delete_asset_success(mock_remove, mock_exists, mock_crud, mock_asset):
    """
    Tests deleting an asset.
    """
    mock_crud.get_asset.return_value = mock_asset
    mock_crud.delete_asset.return_value = {"id": mock_asset.id}
    mock_exists.return_value = True

    response = client.delete(f"/api/v1/assets/{mock_asset.id}")

    assert response.status_code == 200
    assert response.json() == {"message": f"Asset {mock_asset.id} deleted successfully"}
    mock_remove.assert_called_with(mock_asset.original_path)
