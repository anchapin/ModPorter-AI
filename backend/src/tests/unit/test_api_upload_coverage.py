"""
Tests for Upload API endpoints - src/api/upload.py
Covers chunked upload, status, cancel, and file type validation.
"""

import io
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.upload import router, upload_sessions
from api.auth import get_current_user

app = FastAPI()
app.include_router(router)


def _mock_user():
    u = MagicMock()
    u.id = uuid.uuid4()
    return u


app.dependency_overrides[get_current_user] = lambda: _mock_user()
client = TestClient(app)


class TestValidateFileType:
    def test_valid_jar(self):
        from api.upload import validate_file_type

        assert validate_file_type("test.jar", "application/java-archive") is True

    def test_valid_zip(self):
        from api.upload import validate_file_type

        assert validate_file_type("test.zip", "application/zip") is True

    def test_valid_jar_octet_stream(self):
        from api.upload import validate_file_type

        assert validate_file_type("test.jar", "application/octet-stream") is True

    def test_invalid_extension(self):
        from api.upload import validate_file_type

        assert validate_file_type("test.exe", "application/java-archive") is False

    def test_invalid_content_type(self):
        from api.upload import validate_file_type

        assert validate_file_type("test.jar", "text/plain") is False

    def test_empty_content_type(self):
        from api.upload import validate_file_type

        assert validate_file_type("test.jar", "") is True

    def test_none_extension_check(self):
        from api.upload import validate_file_type

        assert validate_file_type("noext", "application/java-archive") is False

    def test_mcaddon(self):
        from api.upload import validate_file_type

        assert validate_file_type("test.mcaddon", "application/zip") is True


class TestUploadJarFile:
    @patch("api.upload.file_handler")
    @patch("api.upload.storage")
    @patch("api.upload.get_audit_logger")
    def test_upload_jar_success(self, mock_audit, mock_storage, mock_fh):
        mock_audit.return_value = MagicMock()
        mock_storage.save_file = AsyncMock(return_value="/tmp/test.jar")

        file_data = ("test.jar", io.BytesIO(b"PK\x03\x04test"), "application/java-archive")

        resp = client.post("/api/v1/upload", files={"file": file_data})

        assert resp.status_code == 201
        data = resp.json()
        assert data["original_filename"] == "test.jar"
        assert "job_id" in data

    @patch("api.upload.get_audit_logger")
    def test_upload_invalid_file_type(self, mock_audit):
        mock_audit.return_value = MagicMock()

        file_data = ("test.exe", io.BytesIO(b"bad"), "application/exe")

        resp = client.post("/api/v1/upload", files={"file": file_data})

        assert resp.status_code == 400

    @patch("api.upload.get_audit_logger")
    def test_upload_oversized_file(self, mock_audit):
        mock_audit.return_value = MagicMock()

        big_content = b"x" * (101 * 1024 * 1024)
        file_data = ("big.jar", io.BytesIO(big_content), "application/java-archive")

        resp = client.post("/api/v1/upload", files={"file": file_data})

        assert resp.status_code == 413

    @patch("api.upload.file_handler")
    @patch("api.upload.storage")
    @patch("api.upload.get_audit_logger")
    def test_upload_with_background_task(self, mock_audit, mock_storage, mock_fh):
        mock_audit.return_value = MagicMock()
        mock_storage.save_file = AsyncMock(return_value="/tmp/test.jar")

        file_data = ("test.jar", io.BytesIO(b"PK\x03\x04"), "application/java-archive")

        resp = client.post("/api/v1/upload", files={"file": file_data})

        assert resp.status_code == 201

    @patch("api.upload.storage")
    @patch("api.upload.get_audit_logger")
    def test_upload_storage_error(self, mock_audit, mock_storage):
        mock_audit.return_value = MagicMock()
        mock_storage.save_file = AsyncMock(side_effect=Exception("disk full"))

        file_data = ("test.jar", io.BytesIO(b"PK\x03\x04"), "application/java-archive")

        resp = client.post("/api/v1/upload", files={"file": file_data})

        assert resp.status_code == 500

    @patch("api.upload.file_handler")
    @patch("api.upload.storage")
    @patch("api.upload.get_audit_logger")
    def test_upload_with_forwarded_for(self, mock_audit, mock_storage, mock_fh):
        mock_audit.return_value = MagicMock()
        mock_storage.save_file = AsyncMock(return_value="/tmp/test.jar")

        file_data = ("test.jar", io.BytesIO(b"PK\x03\x04"), "application/java-archive")

        resp = client.post(
            "/api/v1/upload",
            files={"file": file_data},
            headers={"X-Forwarded-For": "10.0.0.1, 192.168.1.1"},
        )

        assert resp.status_code == 201


class TestChunkedUpload:
    def test_init_chunked_upload_success(self):
        resp = client.post(
            "/api/v1/upload/chunked/init",
            params={
                "filename": "test.jar",
                "content_type": "application/java-archive",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "upload_id" in data
        assert data["chunk_size"] == 5 * 1024 * 1024
        assert data["message"]

    def test_init_chunked_upload_invalid_type(self):
        resp = client.post(
            "/api/v1/upload/chunked/init",
            params={"filename": "test.exe", "content_type": "application/exe"},
        )

        assert resp.status_code == 400

    def test_init_chunked_upload_with_total_size(self):
        resp = client.post(
            "/api/v1/upload/chunked/init",
            params={
                "filename": "test.jar",
                "content_type": "application/java-archive",
                "total_size": 10000000,
            },
        )

        assert resp.status_code == 200
        assert resp.json()["total_size"] == 10000000

    @patch("api.upload.storage")
    @patch("api.upload.file_handler")
    def test_chunked_upload_full_flow(self, mock_fh, mock_storage):
        mock_storage.save_file = AsyncMock(return_value="/tmp/test.jar")
        mock_fh.process_file = AsyncMock()

        upload_sessions.clear()

        init_resp = client.post(
            "/api/v1/upload/chunked/init",
            params={"filename": "test.jar", "content_type": "application/java-archive"},
        )
        upload_id = init_resp.json()["upload_id"]

        chunk_data = ("chunk", io.BytesIO(b"part1"), "application/octet-stream")
        chunk_resp = client.post(
            f"/api/v1/upload/chunked/{upload_id}",
            files={"chunk": chunk_data},
            params={"chunk_index": 0},
        )

        assert chunk_resp.status_code == 200
        assert chunk_resp.json()["chunks_received"] == 1

        complete_resp = client.post(f"/api/v1/upload/chunked/{upload_id}/complete")

        assert complete_resp.status_code == 200
        data = complete_resp.json()
        assert data["original_filename"] == "test.jar"
        assert data["file_size"] == 5

        upload_sessions.clear()

    def test_upload_chunk_invalid_session(self):
        chunk_data = ("chunk", io.BytesIO(b"data"), "application/octet-stream")
        resp = client.post(
            f"/api/v1/upload/chunked/{str(uuid.uuid4())}",
            files={"chunk": chunk_data},
            params={"chunk_index": 0},
        )

        assert resp.status_code == 404

    def test_complete_chunked_invalid_session(self):
        resp = client.post(f"/api/v1/upload/chunked/{str(uuid.uuid4())}/complete")

        assert resp.status_code == 404

    def test_complete_chunked_missing_content_key(self):
        upload_sessions.clear()
        fake_id = str(uuid.uuid4())
        upload_sessions[fake_id] = {
            "filename": "test.jar",
            "total_size": None,
            "content_type": "application/java-archive",
            "chunks": [{"index": 0}],
            "status": "uploading",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        resp = client.post(f"/api/v1/upload/chunked/{fake_id}/complete")

        assert resp.status_code == 400
        assert "Missing chunk" in resp.json()["detail"]

        upload_sessions.clear()

    @patch("api.upload.storage")
    @patch("api.upload.file_handler")
    def test_multiple_chunks_ordering(self, mock_fh, mock_storage):
        mock_storage.save_file = AsyncMock(return_value="/tmp/test.jar")
        mock_fh.process_file = AsyncMock()

        upload_sessions.clear()

        init_resp = client.post(
            "/api/v1/upload/chunked/init",
            params={"filename": "test.zip", "content_type": "application/zip"},
        )
        upload_id = init_resp.json()["upload_id"]

        for i in range(3):
            chunk_data = (
                "chunk",
                io.BytesIO(f"part{i}".encode()),
                "application/octet-stream",
            )
            resp = client.post(
                f"/api/v1/upload/chunked/{upload_id}",
                files={"chunk": chunk_data},
                params={"chunk_index": i},
            )
            assert resp.status_code == 200

        complete_resp = client.post(f"/api/v1/upload/chunked/{upload_id}/complete")
        assert complete_resp.status_code == 200
        assert complete_resp.json()["file_size"] == 15

        upload_sessions.clear()


class TestUploadStatus:
    @patch("api.upload.storage")
    def test_get_status_found(self, mock_storage):
        mock_storage.get_upload_status = AsyncMock(
            return_value={"status": "completed", "progress": 100, "message": "Done"}
        )

        job_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/upload/{job_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100

    @patch("api.upload.storage")
    def test_get_status_not_found(self, mock_storage):
        mock_storage.get_upload_status = AsyncMock(return_value=None)

        job_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/upload/{job_id}")

        assert resp.status_code == 404

    def test_get_status_invalid_uuid(self):
        resp = client.get("/api/v1/upload/not-a-uuid")

        assert resp.status_code == 422


class TestCancelUpload:
    @patch("api.upload.storage")
    def test_cancel_success(self, mock_storage):
        mock_storage.delete_job_files = AsyncMock()

        job_id = str(uuid.uuid4())
        resp = client.delete(f"/api/v1/upload/{job_id}")

        assert resp.status_code == 200
        assert "cancelled" in resp.json()["message"]

    def test_cancel_invalid_uuid(self):
        resp = client.delete("/api/v1/upload/not-a-uuid")

        assert resp.status_code == 422
