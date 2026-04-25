import io
import os
import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.assets import router, MAX_ASSET_SIZE

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


@pytest.fixture
def mock_asset_with_converted():
    asset = MagicMock()
    asset.id = uuid.uuid4()
    asset.conversion_id = uuid.uuid4()
    asset.asset_type = "texture"
    asset.original_path = "path/to/original.png"
    asset.converted_path = "path/to/converted.png"
    asset.status = "converted"
    asset.asset_metadata = None
    asset.file_size = 2048
    asset.mime_type = "image/png"
    asset.original_filename = "original.png"
    asset.error_message = None
    asset.created_at = datetime.now()
    asset.updated_at = datetime.now()
    return asset


# ---- list_conversion_assets ----


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


@patch("db.crud.list_assets_for_conversion", new_callable=AsyncMock)
def test_list_conversion_assets_with_filters(mock_list, mock_asset):
    mock_list.return_value = [mock_asset]
    conversion_id = str(uuid.uuid4())

    response = client.get(
        f"/conversions/{conversion_id}/assets",
        params={"asset_type": "texture", "status": "pending", "skip": 0, "limit": 10},
    )

    assert response.status_code == 200
    mock_list.assert_called_once()


@patch("db.crud.list_assets_for_conversion", new_callable=AsyncMock)
def test_list_conversion_assets_error(mock_list):
    mock_list.side_effect = RuntimeError("db down")
    conversion_id = str(uuid.uuid4())

    response = client.get(f"/conversions/{conversion_id}/assets")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to retrieve assets"


@patch("db.crud.list_assets_for_conversion", new_callable=AsyncMock)
def test_list_conversion_assets_empty(mock_list):
    mock_list.return_value = []
    conversion_id = str(uuid.uuid4())

    response = client.get(f"/conversions/{conversion_id}/assets")

    assert response.status_code == 200
    assert response.json() == []


# ---- upload_asset ----


@patch("db.crud.create_asset", new_callable=AsyncMock)
@patch("os.makedirs")
def test_upload_asset_success(mock_makedirs, mock_create, mock_asset, tmp_path):
    mock_create.return_value = mock_asset
    file_content = b"fake png data"
    conversion_id = str(uuid.uuid4())

    with patch.object(api_assets_module(), "ASSETS_STORAGE_DIR", str(tmp_path)):
        response = client.post(
            f"/conversions/{conversion_id}/assets",
            files={"file": ("test.png", io.BytesIO(file_content), "image/png")},
            data={"asset_type": "texture"},
        )

    assert response.status_code == 200
    assert response.json()["asset_type"] == "texture"
    mock_create.assert_called_once()


def test_upload_asset_no_filename():
    from starlette.datastructures import UploadFile as StarletteUploadFile

    original_init = StarletteUploadFile.__init__

    def _force_no_filename(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.filename = None

    conversion_id = str(uuid.uuid4())
    with patch.object(StarletteUploadFile, "__init__", _force_no_filename):
        response = client.post(
            f"/conversions/{conversion_id}/assets",
            files={"file": ("test.png", io.BytesIO(b"data"), "image/png")},
            data={"asset_type": "texture"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "No file provided"


@patch("os.path.exists", return_value=True)
@patch("os.remove")
@patch("os.makedirs")
def test_upload_asset_oversized_file(mock_makedirs, mock_remove, mock_exists):
    conversion_id = str(uuid.uuid4())
    big_size = MAX_ASSET_SIZE + 1024
    big_data = b"x" * big_size

    response = client.post(
        f"/conversions/{conversion_id}/assets",
        files={"file": ("big.png", io.BytesIO(big_data), "image/png")},
        data={"asset_type": "texture"},
    )

    assert response.status_code == 413


@patch("db.crud.create_asset", new_callable=AsyncMock)
@patch("os.makedirs")
def test_upload_asset_db_value_error(mock_makedirs, mock_create, tmp_path):
    mock_create.side_effect = ValueError("bad conversion_id")
    conversion_id = str(uuid.uuid4())

    with patch.object(api_assets_module(), "ASSETS_STORAGE_DIR", str(tmp_path)):
        response = client.post(
            f"/conversions/{conversion_id}/assets",
            files={"file": ("test.png", io.BytesIO(b"data"), "image/png")},
            data={"asset_type": "texture"},
        )

    assert response.status_code == 400


@patch("db.crud.create_asset", new_callable=AsyncMock)
@patch("os.makedirs")
def test_upload_asset_db_general_error(mock_makedirs, mock_create, tmp_path):
    mock_create.side_effect = Exception("db exploded")
    conversion_id = str(uuid.uuid4())

    with patch.object(api_assets_module(), "ASSETS_STORAGE_DIR", str(tmp_path)):
        response = client.post(
            f"/conversions/{conversion_id}/assets",
            files={"file": ("test.png", io.BytesIO(b"data"), "image/png")},
            data={"asset_type": "texture"},
        )

    assert response.status_code == 500


@patch("os.makedirs")
def test_upload_asset_file_write_error(mock_makedirs, tmp_path):
    conversion_id = str(uuid.uuid4())

    with patch.object(api_assets_module(), "ASSETS_STORAGE_DIR", str(tmp_path)):
        with patch("builtins.open", side_effect=OSError("disk full")):
            response = client.post(
                f"/conversions/{conversion_id}/assets",
                files={"file": ("test.png", io.BytesIO(b"data"), "image/png")},
                data={"asset_type": "texture"},
            )

    assert response.status_code == 500
    assert response.json()["detail"] == "Could not save file"


# ---- get_asset ----


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


# ---- update_asset_status ----


@patch("db.crud.update_asset_status", new_callable=AsyncMock)
def test_update_asset_status_success(mock_update, mock_asset):
    mock_asset.status = "converted"
    mock_update.return_value = mock_asset
    asset_id = str(mock_asset.id)

    response = client.put(
        f"/assets/{asset_id}/status",
        json={"status": "converted", "converted_path": "path/to/conv.png"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "converted"


@patch("db.crud.update_asset_status", new_callable=AsyncMock)
def test_update_asset_status_not_found(mock_update):
    mock_update.return_value = None
    asset_id = str(uuid.uuid4())

    response = client.put(
        f"/assets/{asset_id}/status",
        json={"status": "failed", "error_message": "something went wrong"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"


# ---- update_asset_metadata ----


@patch("db.crud.update_asset_metadata", new_callable=AsyncMock)
def test_update_asset_metadata_success(mock_update, mock_asset):
    mock_asset.asset_metadata = {"new": "meta"}
    mock_update.return_value = mock_asset
    asset_id = str(mock_asset.id)

    response = client.put(f"/assets/{asset_id}/metadata", json={"new": "meta"})

    assert response.status_code == 200
    assert response.json()["asset_metadata"] == {"new": "meta"}


@patch("db.crud.update_asset_metadata", new_callable=AsyncMock)
def test_update_asset_metadata_not_found(mock_update):
    mock_update.return_value = None
    asset_id = str(uuid.uuid4())

    response = client.put(f"/assets/{asset_id}/metadata", json={"new": "meta"})

    assert response.status_code == 404


# ---- delete_asset ----


@patch("db.crud.get_asset", new_callable=AsyncMock)
@patch("db.crud.delete_asset", new_callable=AsyncMock)
@patch("os.path.exists")
@patch("os.remove")
def test_delete_asset_success(mock_remove, mock_exists, mock_delete, mock_get, mock_asset):
    mock_get.return_value = mock_asset
    mock_delete.return_value = {"id": str(mock_asset.id)}
    mock_exists.return_value = True
    asset_id = str(mock_asset.id)

    response = client.delete(f"/assets/{asset_id}")

    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]
    mock_delete.assert_called_once()


@patch("db.crud.get_asset", new_callable=AsyncMock)
def test_delete_asset_not_found(mock_get):
    mock_get.return_value = None
    asset_id = str(uuid.uuid4())

    response = client.delete(f"/assets/{asset_id}")

    assert response.status_code == 404


@patch("db.crud.get_asset", new_callable=AsyncMock)
@patch("db.crud.delete_asset", new_callable=AsyncMock)
def test_delete_asset_already_removed_from_db(mock_delete, mock_get, mock_asset):
    mock_get.return_value = mock_asset
    mock_delete.return_value = None
    asset_id = str(mock_asset.id)

    response = client.delete(f"/assets/{asset_id}")

    assert response.status_code == 404


@patch("db.crud.get_asset", new_callable=AsyncMock)
@patch("db.crud.delete_asset", new_callable=AsyncMock)
@patch("os.path.exists", return_value=True)
@patch("os.remove")
def test_delete_asset_with_converted_path_cleanup(
    mock_remove, mock_exists, mock_delete, mock_get, mock_asset_with_converted
):
    mock_get.return_value = mock_asset_with_converted
    mock_delete.return_value = {"id": str(mock_asset_with_converted.id)}

    response = client.delete(f"/assets/{mock_asset_with_converted.id}")

    assert response.status_code == 200
    assert mock_remove.call_count == 2


@patch("db.crud.get_asset", new_callable=AsyncMock)
@patch("db.crud.delete_asset", new_callable=AsyncMock)
@patch("os.path.exists", return_value=True)
@patch("os.remove")
def test_delete_asset_converted_file_cleanup_error(
    mock_remove, mock_exists, mock_delete, mock_get, mock_asset_with_converted
):
    mock_get.return_value = mock_asset_with_converted
    mock_delete.return_value = {"id": str(mock_asset_with_converted.id)}
    mock_remove.side_effect = [None, OSError("permission denied")]

    response = client.delete(f"/assets/{mock_asset_with_converted.id}")

    assert response.status_code == 200


# ---- trigger_asset_conversion ----


@patch("db.crud.get_asset", new_callable=AsyncMock)
@patch(
    "services.asset_conversion_service.asset_conversion_service.convert_asset",
    new_callable=AsyncMock,
)
def test_trigger_asset_conversion_success(mock_convert, mock_get, mock_asset):
    mock_get.side_effect = [mock_asset, mock_asset]
    mock_convert.return_value = {"success": True}
    asset_id = str(mock_asset.id)

    response = client.post(f"/assets/{asset_id}/convert")

    assert response.status_code == 200
    mock_convert.assert_called_once_with(asset_id)


@patch("db.crud.get_asset", new_callable=AsyncMock)
def test_trigger_asset_conversion_not_found(mock_get):
    mock_get.return_value = None
    asset_id = str(uuid.uuid4())

    response = client.post(f"/assets/{asset_id}/convert")

    assert response.status_code == 404


@patch("db.crud.get_asset", new_callable=AsyncMock)
def test_trigger_asset_conversion_already_converted(mock_get, mock_asset_with_converted):
    mock_get.return_value = mock_asset_with_converted
    asset_id = str(mock_asset_with_converted.id)

    response = client.post(f"/assets/{asset_id}/convert")

    assert response.status_code == 200
    assert response.json()["status"] == "converted"


@patch("db.crud.get_asset", new_callable=AsyncMock)
@patch(
    "services.asset_conversion_service.asset_conversion_service.convert_asset",
    new_callable=AsyncMock,
)
def test_trigger_asset_conversion_failure(mock_convert, mock_get, mock_asset):
    mock_get.return_value = mock_asset
    mock_convert.return_value = {"success": False, "error": "engine timeout"}
    asset_id = str(mock_asset.id)

    response = client.post(f"/assets/{asset_id}/convert")

    assert response.status_code == 500
    assert "engine timeout" in response.json()["detail"]


@patch("db.crud.get_asset", new_callable=AsyncMock)
@patch(
    "services.asset_conversion_service.asset_conversion_service.convert_asset",
    new_callable=AsyncMock,
)
def test_trigger_asset_conversion_exception(mock_convert, mock_get, mock_asset):
    mock_get.return_value = mock_asset
    mock_convert.side_effect = Exception("unexpected error")
    asset_id = str(mock_asset.id)

    response = client.post(f"/assets/{asset_id}/convert")

    assert response.status_code == 500


# ---- convert_all_conversion_assets ----


@patch(
    "services.asset_conversion_service.asset_conversion_service.convert_assets_for_conversion",
    new_callable=AsyncMock,
)
def test_convert_all_conversion_assets_success(mock_convert_all):
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


@patch(
    "services.asset_conversion_service.asset_conversion_service.convert_assets_for_conversion",
    new_callable=AsyncMock,
)
def test_convert_all_conversion_assets_error(mock_convert_all):
    mock_convert_all.side_effect = Exception("batch failed")
    conversion_id = str(uuid.uuid4())

    response = client.post(f"/conversions/{conversion_id}/assets/convert-all")

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to convert assets"


@patch(
    "services.asset_conversion_service.asset_conversion_service.convert_assets_for_conversion",
    new_callable=AsyncMock,
)
def test_convert_all_conversion_assets_partial_failure(mock_convert_all):
    mock_convert_all.return_value = {
        "success": True,
        "total_assets": 3,
        "converted_count": 2,
        "failed_count": 1,
    }
    conversion_id = str(uuid.uuid4())

    response = client.post(f"/conversions/{conversion_id}/assets/convert-all")

    assert response.status_code == 200
    data = response.json()
    assert data["converted_count"] == 2
    assert data["failed_count"] == 1


# ---- remaining edge-case coverage ----


@patch("db.crud.get_asset", new_callable=AsyncMock)
@patch("db.crud.delete_asset", new_callable=AsyncMock)
@patch("os.path.exists", return_value=True)
@patch("os.remove")
def test_delete_asset_original_file_cleanup_warning(
    mock_remove, mock_exists, mock_delete, mock_get, mock_asset
):
    mock_get.return_value = mock_asset
    mock_delete.return_value = {"id": str(mock_asset.id)}
    mock_remove.side_effect = OSError("permission denied")
    asset_id = str(mock_asset.id)

    response = client.delete(f"/assets/{asset_id}")

    assert response.status_code == 200


@patch("os.remove")
@patch("os.path.exists", return_value=True)
@patch("os.makedirs")
def test_upload_asset_file_write_error_with_existing_file(
    mock_makedirs, mock_exists, mock_remove, tmp_path
):
    conversion_id = str(uuid.uuid4())

    with patch.object(api_assets_module(), "ASSETS_STORAGE_DIR", str(tmp_path)):
        with patch("builtins.open", side_effect=OSError("disk full")):
            response = client.post(
                f"/conversions/{conversion_id}/assets",
                files={"file": ("test.png", io.BytesIO(b"data"), "image/png")},
                data={"asset_type": "texture"},
            )

    assert response.status_code == 500
    assert response.json()["detail"] == "Could not save file"
    mock_remove.assert_called()


def api_assets_module():
    import api.assets as m

    return m
