import pytest
import json
import uuid
import os
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from datetime import datetime, timezone
from pathlib import Path

# Import the router to test
from api.conversions import router, ConversionOptions

# Create a test FastAPI app
app = FastAPI()
app.include_router(router)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_cache():
    return MagicMock()


@pytest.fixture
def mock_security_scanner():
    scanner = MagicMock()
    result = MagicMock()
    result.has_critical_threats = False
    result.has_high_threats = False
    scanner.scan_file.return_value = result
    return scanner


class TestConversionsAPITargeted:
    @patch("api.conversions.get_db")
    @patch("api.conversions.get_security_scanner")
    @patch("api.conversions.enqueue_task", new_callable=AsyncMock)
    @patch("api.conversions.crud")
    @patch("api.conversions.get_conversion_service")
    @patch("api.conversions.os.makedirs")
    @patch("api.conversions.shutil.copyfileobj")
    @patch("builtins.open", new_callable=mock_open)
    async def test_create_conversion_success(
        self,
        mock_file_open,
        mock_copyfileobj,
        mock_makedirs,
        mock_get_conversion_service,
        mock_crud,
        mock_enqueue,
        mock_get_scanner,
        mock_get_db,
        client,
        mock_security_scanner,
    ):
        # Setup mocks
        mock_get_db.return_value = AsyncMock()
        mock_get_scanner.return_value = mock_security_scanner

        mock_conv_service = MagicMock()
        mock_get_conversion_service.return_value = mock_conv_service

        conversion_id = str(uuid.uuid4())
        mock_job = MagicMock()
        mock_job.id = conversion_id
        mock_job.status = "queued"
        mock_job.created_at = datetime.now(timezone.utc)

        # Make create_job an AsyncMock
        mock_crud.create_job = AsyncMock(return_value=mock_job)

        # Test data
        file_content = b"fake jar content"
        files = {"file": ("test.jar", file_content, "application/java-archive")}
        options = json.dumps({"assumptions": "aggressive", "target_version": "1.21.0"})
        data = {"options": options}

        # We need to bypass some async file operations or mock them
        # Since we're using TestClient, it's synchronous but the endpoint is async

        with patch("api.conversions.validate_file_size", return_value=(True, "")):
            response = client.post("/api/v1/conversions", files=files, data=data)

        assert response.status_code == 202
        assert response.json()["conversion_id"] == conversion_id
        assert response.json()["status"] == "queued"

        mock_crud.create_job.assert_called_once()
        mock_enqueue.assert_called_once()

    @patch("api.conversions.get_db")
    @patch("api.conversions.crud")
    def test_list_conversions(self, mock_crud, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()

        from types import SimpleNamespace

        mock_job = SimpleNamespace(
            id=uuid.uuid4(),
            status="completed",
            progress=SimpleNamespace(progress=100),
            message="Done",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            original_filename="test.jar",
            input_data={"original_filename": "test.jar"},
            error_message=None,
        )

        mock_crud.list_jobs = AsyncMock(return_value=([mock_job], 1))
        mock_crud.count_jobs = AsyncMock(return_value=1)

        response = client.get("/api/v1/conversions")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["conversions"]) == 1
        assert data["conversions"][0]["conversion_id"] == str(mock_job.id)

    @patch("api.conversions.get_db")
    @patch("api.conversions.crud")
    def test_get_conversion_success(self, mock_crud, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()

        from types import SimpleNamespace

        conversion_id = str(uuid.uuid4())
        mock_job = SimpleNamespace(
            id=conversion_id,
            status="processing",
            progress=SimpleNamespace(progress=45),
            message="Converting assets...",
            created_at=datetime.now(timezone.utc),
            updated_at=None,
            original_filename="test.jar",
            input_data={"original_filename": "test.jar"},
            error_message=None,
        )

        mock_crud.get_job = AsyncMock(return_value=mock_job)

        response = client.get(f"/api/v1/conversions/{conversion_id}")

        assert response.status_code == 200
        assert response.json()["conversion_id"] == conversion_id
        assert response.json()["status"] == "processing"
        assert response.json()["progress"] == 45

    @patch("api.conversions.get_db")
    @patch("api.conversions.crud")
    def test_get_conversion_not_found(self, mock_crud, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()
        mock_crud.get_job = AsyncMock(return_value=None)

        conversion_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/conversions/{conversion_id}")

        assert response.status_code == 404

    @patch("api.conversions.get_db")
    @patch("api.conversions.crud")
    @patch("api.conversions.os.path.exists")
    def test_download_conversion_success(self, mock_exists, mock_crud, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()
        mock_exists.return_value = True

        conversion_id = str(uuid.uuid4())
        mock_job = MagicMock()
        mock_job.id = conversion_id
        mock_job.status = "completed"
        mock_job.output_path = "outputs/test.mcaddon"
        mock_job.original_filename = "test.jar"

        mock_crud.get_job = AsyncMock(return_value=mock_job)

        with patch("api.conversions.FileResponse") as mock_file_response:
            mock_file_response.return_value = MagicMock()
            response = client.get(f"/api/v1/conversions/{conversion_id}/download")
            assert response.status_code == 200

    @patch("api.conversions.get_db")
    @patch("api.conversions.crud")
    def test_delete_conversion_success(self, mock_crud, mock_get_db, client):
        mock_get_db.return_value = AsyncMock()

        conversion_id = str(uuid.uuid4())
        mock_job = MagicMock()
        mock_job.id = conversion_id
        mock_crud.get_job = AsyncMock(return_value=mock_job)
        mock_crud.delete_job = AsyncMock(return_value=True)
        mock_crud.update_job_status = AsyncMock()

        response = client.delete(f"/api/v1/conversions/{conversion_id}")

        assert response.status_code == 204

    def test_sanitize_filename(self):
        from api.conversions import sanitize_filename

        assert sanitize_filename("test.jar") == "test.jar"
        assert sanitize_filename("../../../etc/passwd") == "passwd"
        assert sanitize_filename("test space.jar") == "testspace.jar"
        assert sanitize_filename(".hidden") == "file.hidden"
        assert sanitize_filename("") == "uploaded_file"

    def test_validate_file_type(self):
        from api.conversions import validate_file_type

        is_valid, _ = validate_file_type("test.jar")
        assert is_valid is True
        is_valid, _ = validate_file_type("test.zip")
        assert is_valid is True
        is_valid, _ = validate_file_type("test.txt")
        assert is_valid is False
