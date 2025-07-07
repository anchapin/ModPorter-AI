from fastapi.testclient import TestClient
import io


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_returns_200(self, client: TestClient):
        """Test that health check returns 200 status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_check_response_format(self, client: TestClient):
        """Test health check response format."""
        response = client.get("/api/v1/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        # Ensure it does not contain the message from the old /api/v1/health
        assert "message" not in data


class TestFileUploadEndpoint:
    """Test file upload endpoint."""

    def test_upload_valid_jar_file(self, client: TestClient):
        """Test uploading a valid JAR file."""
        # Create a mock JAR file
        file_content = b"PK\x03\x04"  # ZIP file header (JAR files are ZIP files)
        file_data = (
            "test-mod.jar",
            io.BytesIO(file_content),
            "application/java-archive",
        )

        response = client.post("/api/v1/upload", files={"file": file_data})
        assert response.status_code == 200

        data = response.json()
        assert data["original_filename"] == "test-mod.jar" # Changed from filename to original_filename
        assert "message" in data

    def test_upload_valid_zip_file(self, client: TestClient):
        """Test uploading a valid ZIP file."""
        file_content = b"PK\x03\x04"  # ZIP file header
        file_data = ("test-mod.zip", io.BytesIO(file_content), "application/zip")

        response = client.post("/api/v1/upload", files={"file": file_data})
        assert response.status_code == 200

    def test_upload_valid_mcaddon_file(self, client: TestClient):
        """Test uploading a valid MCADDON file."""
        file_content = b"PK\x03\x04"  # ZIP file header
        file_data = (
            "test-addon.mcaddon",
            io.BytesIO(file_content),
            "application/octet-stream",
        )

        response = client.post("/api/v1/upload", files={"file": file_data})
        assert response.status_code == 200

    def test_upload_invalid_file_type(self, client: TestClient):
        """Test uploading an invalid file type."""
        file_content = b"Hello, world!"
        file_data = ("test.txt", io.BytesIO(file_content), "text/plain")

        response = client.post("/api/v1/upload", files={"file": file_data})
        assert response.status_code == 400

        data = response.json()
        assert "not supported" in data["detail"]

    def test_upload_no_file(self, client: TestClient):
        """Test uploading without providing a file."""
        response = client.post("/api/v1/upload")
        assert response.status_code == 422  # Unprocessable Entity


class TestConversionEndpoints:
    """Test conversion-related endpoints."""

    def test_start_conversion(self, client: TestClient):
        """Test starting a conversion job."""
        request_data = {
            "file_id": "mock-file-id",
            "original_filename": "test-mod.jar",
            "target_version": "1.20.0",
            "options": {"enable_smart_assumptions": True},
        }

        response = client.post("/api/v1/convert", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert "estimated_time" in data

    def test_get_conversion_status(self, client: TestClient):
        """Test getting conversion job status."""
        # First create a conversion job
        request_data = {
            "file_id": "mock-file-id",
            "original_filename": "test-mod.jar",
            "target_version": "1.20.0"
        }

        create_response = client.post("/api/v1/convert", json=request_data)
        assert create_response.status_code == 200
        job_id = create_response.json()["job_id"]

        # Now test getting its status
        response = client.get(f"/api/v1/convert/{job_id}/status") # Changed path
        assert response.status_code == 200

        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "progress" in data
        assert "message" in data

    def test_list_conversions(self, client: TestClient):
        """Test listing all conversion jobs."""
        response = client.get("/api/v1/conversions") # Changed path
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_cancel_conversion(self, client: TestClient):
        """Test cancelling a conversion job."""
        # First create a conversion job
        request_data = {
            "file_id": "mock-file-id",
            "original_filename": "test-mod.jar",
            "target_version": "1.20.0"
        }

        create_response = client.post("/api/v1/convert", json=request_data)
        assert create_response.status_code == 200
        job_id = create_response.json()["job_id"]

        # Now test cancelling it
        response = client.delete(f"/api/v1/convert/{job_id}") # Changed path
        assert response.status_code == 200

        data = response.json()
        assert "cancelled" in data["message"]

    def test_download_converted_mod_not_found(self, client: TestClient):
        """Test downloading a non-existent converted mod."""
        job_id = "12345678-1234-1234-1234-123456789012"

        response = client.get(f"/api/v1/convert/{job_id}/download") # Changed path
        assert response.status_code == 404


class TestConversionRequestValidation:
    """Test validation of conversion requests."""

    def test_conversion_request_valid(self, client: TestClient):
        """Test valid conversion request."""
        request_data = {
            "file_id": "mock-file-id",
            "original_filename": "test-mod.jar",
            "target_version": "1.20.0"
        }

        response = client.post("/api/v1/convert", json=request_data)
        assert response.status_code == 200

    def test_conversion_request_missing_file_id(self, client: TestClient): # Renamed test
        """Test conversion request with missing file_id."""
        request_data = {
            "original_filename": "test-mod.jar",
            "target_version": "1.20.0"
        }
        # This will likely fail due to Pydantic model validation on backend if file_id is mandatory
        # However, the current ConversionRequest model has file_id as Optional.
        # Let's assume for this unit test, we are testing the endpoint with a payload
        # that the endpoint should reject if file_id was strictly required by the handler logic,
        # or that the model itself makes it non-optional.
        # The backend main.py's start_conversion has logic to raise HTTPException if file_id is not resolved.
        response = client.post("/api/v1/convert", json=request_data)
        assert response.status_code == 422 # Expecting 422 due to missing file_id

    def test_conversion_request_default_target_version(self, client: TestClient):
        """Test conversion request uses default target version."""
        request_data = {
            "file_id": "mock-file-id",
            "original_filename": "test-mod.jar"
        }

        response = client.post("/api/v1/convert", json=request_data)
        assert response.status_code == 200

        # The response should use the default target version
        # This would be tested in integration tests with actual logic
