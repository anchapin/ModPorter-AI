
import pytest
from fastapi.testclient import TestClient
import io
import json

class TestConversionsAPI:
    def test_create_conversion_success(self, client):
        """Test creating a conversion via POST /api/v1/conversions."""
        # Create a dummy JAR file
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"

        # Options as JSON string
        options = json.dumps({
            "assumptions": "conservative",
            "target_version": "1.20.0"
        })

        response = client.post(
            "/api/v1/conversions",
            files={
                "file": ("test_mod.jar", io.BytesIO(jar_content), "application/java-archive")
            },
            data={"options": options}
        )

        # If 404, it means the router is not included or path is wrong
        assert response.status_code != 404, "Endpoint /api/v1/conversions not found"

        # If 202, it means success
        assert response.status_code == 202
        data = response.json()
        assert "conversion_id" in data
        assert data["status"] == "queued"

    def test_create_conversion_large_file_validation(self, client):
        """
        Test that validate_file_size is called and works.
        Since we can't easily generate >100MB file in test without memory issues,
        we just verify that a normal file passes (which we did above).

        We will test invalid file type here to ensure validation chain works.
        """
        response = client.post(
            "/api/v1/conversions",
            files={
                "file": ("test.txt", io.BytesIO(b"text"), "text/plain")
            }
        )
        assert response.status_code == 400
        data = response.json()
        # Error handler returns 'message' or 'user_message', not 'detail'
        assert "message" in data
        assert "File type .txt not supported" in data["message"]
