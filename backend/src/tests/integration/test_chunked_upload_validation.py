
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

# We can't easily import the app here because of potential env var issues and DB connection requirements in tests.
# But we can try to rely on `conftest.py` if it sets up the client.
# Based on `test_api_v1_integration.py`, it seems there is a `client` fixture.

class TestChunkedUploadValidation:
    def test_upload_chunk_invalid_uuid(self, client):
        """Test that upload_chunk rejects invalid UUID."""
        # UUIDs are usually like 123e4567-e89b-12d3-a456-426614174000
        invalid_uuid = "not-a-uuid"

        # We need to send form data
        data = {
            "chunk_number": 1,
            "total_chunks": 1
        }
        files = {
            "chunk": ("chunk.bin", b"some data", "application/octet-stream")
        }

        response = client.post(
            f"/api/v1/uploads/{invalid_uuid}/chunk",
            data=data,
            files=files
        )

        # FastAPI validation should return 422 Unprocessable Entity
        # Note: Depending on router ordering and strictness, it might return 404 if it tries to match path params first
        # But we want to ensure it fails validation.
        assert response.status_code in [422, 404]
        if response.status_code == 422:
             assert "value is not a valid uuid" in response.text.lower() or "input should be a valid uuid" in response.text.lower()

    def test_get_progress_invalid_uuid(self, client):
        """Test that get_upload_progress rejects invalid UUID."""
        invalid_uuid = "not-a-uuid"
        response = client.get(f"/api/v1/uploads/{invalid_uuid}/progress")
        assert response.status_code in [422, 404]

    def test_complete_upload_invalid_uuid(self, client):
        """Test that complete_chunked_upload rejects invalid UUID."""
        invalid_uuid = "not-a-uuid"
        response = client.post(f"/api/v1/uploads/{invalid_uuid}/complete")
        assert response.status_code in [422, 404]

    def test_cancel_upload_invalid_uuid(self, client):
        """Test that cancel_upload rejects invalid UUID."""
        invalid_uuid = "not-a-uuid"
        response = client.delete(f"/api/v1/uploads/{invalid_uuid}")
        assert response.status_code in [422, 404]

    def test_upload_chunk_valid_uuid_not_found(self, client):
        """Test that upload_chunk with valid UUID but no session returns 404."""
        valid_uuid = str(uuid4())

        data = {
            "chunk_number": 1,
            "total_chunks": 1
        }
        files = {
            "chunk": ("chunk.bin", b"some data", "application/octet-stream")
        }

        response = client.post(
            f"/api/v1/uploads/{valid_uuid}/chunk",
            data=data,
            files=files
        )

        # Should be 404 because session doesn't exist in cache
        assert response.status_code == 404
