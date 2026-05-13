import base64
import os
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.plugins import router, PluginConversionRequest, _build_status_message, PluginType


@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    # Issue #1417: bypass auth + ownership for plugins endpoints.
    from api._authz import get_current_user
    from db.base import get_db
    from api import plugins as _pl_mod

    _TEST_USER_ID = "11111111-1111-4111-a111-111111111111"  # noqa: N806

    user = MagicMock()
    user.id = _TEST_USER_ID

    owned_job = MagicMock()
    owned_job.user_id = _TEST_USER_ID
    owned_job.status = "completed"
    owned_job.input_data = {"original_filename": "mod.jar"}
    owned_job.created_at = datetime.now(timezone.utc)
    owned_job.updated_at = datetime.now(timezone.utc)
    owned_job.progress = MagicMock()
    owned_job.progress.progress = 100

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    _pl_mod.crud.get_job = AsyncMock(return_value=owned_job)
    return TestClient(app)


@pytest.fixture
def sample_base64_file():
    content = b"PK\x03\x04test jar content"
    return base64.b64encode(content).decode("utf-8")


class TestBuildStatusMessage:
    def test_queued_message(self):
        msg = _build_status_message("queued", 0)
        assert msg == "Job is queued and waiting to start."

    def test_preprocessing_message(self):
        msg = _build_status_message("preprocessing", 0)
        assert msg == "Preprocessing uploaded file."

    def test_processing_message(self):
        msg = _build_status_message("processing", 50)
        assert msg == "AI conversion in progress (50%)."

    def test_postprocessing_message(self):
        msg = _build_status_message("postprocessing", 75)
        assert msg == "Finalizing conversion results."

    def test_completed_message(self):
        msg = _build_status_message("completed", 100)
        assert msg == "Conversion completed successfully."

    def test_failed_with_error(self):
        msg = _build_status_message("failed", 0, "Test error")
        assert msg == "Conversion failed: Test error"

    def test_failed_without_error(self):
        msg = _build_status_message("failed", 0)
        assert msg == "Conversion failed."

    def test_cancelled_message(self):
        msg = _build_status_message("cancelled", 0)
        assert msg == "Job was cancelled by the user."

    def test_unknown_status(self):
        msg = _build_status_message("unknown_status", 50)
        assert msg == "Job status: unknown_status."


class TestPluginConversionRequest:
    def test_valid_request_bridge(self, sample_base64_file):
        request = PluginConversionRequest(
            plugin_type="bridge",
            file_data=sample_base64_file,
            file_name="test-mod.jar",
            target_version="1.20.0",
        )
        assert request.plugin_type.value == "bridge"
        assert request.file_name == "test-mod.jar"

    def test_valid_request_vscode(self, sample_base64_file):
        request = PluginConversionRequest(
            plugin_type="vscode",
            file_data=sample_base64_file,
            file_name="another-mod.zip",
            target_version="1.20.0",
        )
        assert request.plugin_type.value == "vscode"

    def test_valid_request_blockbench(self, sample_base64_file):
        request = PluginConversionRequest(
            plugin_type="blockbench",
            file_data=sample_base64_file,
            file_name="model-mod.jar",
        )
        assert request.plugin_type.value == "blockbench"

    def test_invalid_base64(self):
        with pytest.raises(ValueError, match="Invalid base64"):
            PluginConversionRequest(
                plugin_type="bridge",
                file_data="not-valid-base64!!!",
                file_name="test.jar",
            )

    def test_default_target_version(self, sample_base64_file):
        request = PluginConversionRequest(
            plugin_type="bridge",
            file_data=sample_base64_file,
            file_name="test.jar",
        )
        assert request.target_version == "1.20.0"

    def test_with_options(self, sample_base64_file):
        request = PluginConversionRequest(
            plugin_type="bridge",
            file_data=sample_base64_file,
            file_name="test.jar",
            options={"texture_scale": 2, "optimize_textures": True},
        )
        assert request.options == {"texture_scale": 2, "optimize_textures": True}


class TestPluginConversionEndpoints:
    def test_start_conversion_invalid_plugin_type(self, client, sample_base64_file):
        response = client.post(
            "/convert",
            json={
                "plugin_type": "invalid_plugin",
                "file_data": sample_base64_file,
                "file_name": "test.jar",
            },
        )
        assert response.status_code == 422

    def test_start_conversion_missing_file_data(self, client):
        response = client.post(
            "/convert",
            json={
                "plugin_type": "bridge",
                "file_name": "test.jar",
            },
        )
        assert response.status_code == 422

    def test_start_conversion_missing_file_name(self, client, sample_base64_file):
        response = client.post(
            "/convert",
            json={
                "plugin_type": "bridge",
                "file_data": sample_base64_file,
            },
        )
        assert response.status_code == 422

    @patch("api.plugins.crud")
    @patch("api.plugins.cache")
    def test_get_conversion_status_not_found(self, mock_cache, mock_crud, client):
        non_existent_job_id = str(uuid.uuid4())
        mock_cache.get_job_status = AsyncMock(return_value=None)
        mock_crud.get_job = AsyncMock(return_value=None)

        response = client.get(f"/convert/{non_existent_job_id}/status")

        assert response.status_code == 404

    @patch("api.plugins.crud")
    @patch("api.plugins.cache")
    def test_get_conversion_status_from_cache(self, mock_cache, mock_crud, client):
        # Issue #1417: ownership check now loads the job from db before honoring cache
        owned_job = MagicMock()
        owned_job.user_id = "11111111-1111-4111-a111-111111111111"
        mock_crud.get_job = AsyncMock(return_value=owned_job)
        job_id = str(uuid.uuid4())
        mock_cache.get_job_status = AsyncMock(
            return_value={
                "status": "completed",
                "progress": 100,
                "error_message": None,
                "result_url": f"/api/v1/plugins/convert/{job_id}/download",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        response = client.get(f"/convert/{job_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["result_url"] is not None

    @patch("api.plugins.crud")
    @patch("api.plugins.cache")
    def test_download_conversion_not_found(self, mock_cache, mock_crud, client):
        non_existent_job_id = str(uuid.uuid4())
        mock_cache.get_job_status = AsyncMock(return_value=None)
        mock_crud.get_job = AsyncMock(return_value=None)

        response = client.get(f"/convert/{non_existent_job_id}/download")
        assert response.status_code == 404


class TestPluginTypeEnum:
    def test_plugin_type_values(self):
        assert PluginType.BRIDGE.value == "bridge"
        assert PluginType.VSCODE.value == "vscode"
        assert PluginType.BLOCKBENCH.value == "blockbench"

    def test_plugin_type_from_string(self):
        assert PluginType("bridge") == PluginType.BRIDGE
        assert PluginType("vscode") == PluginType.VSCODE
        assert PluginType("blockbench") == PluginType.BLOCKBENCH
