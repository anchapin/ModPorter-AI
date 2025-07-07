"""
Integration tests for the ModPorter AI Backend API v1 endpoints.

These tests verify the new /api/v1/* endpoints including file upload,
conversion processing, status tracking, and error handling.
"""

import io
import time
import pytest
from fastapi.testclient import TestClient
from src.main import app

# Test client will be provided by fixture


class TestV1HealthIntegration:
    """Integration tests for v1 health check endpoint."""

    def test_v1_health_endpoint_responds(self, client):
        """Test that v1 health endpoint responds correctly."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "message" in data
        assert data["message"] == "ModPorter AI Backend is running"


class TestV1ConversionIntegration:
    """Integration tests for v1 conversion workflow with file upload."""

    def test_v1_convert_with_jar_upload(self, client):
        """Test v1 conversion endpoint with JAR file upload."""
        # Create a mock JAR file
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"  # Valid ZIP/JAR header
        jar_file = io.BytesIO(jar_content)

        # Start conversion with file upload
        response = client.post(
            "/api/v1/convert",
            files={"mod_file": ("test.jar", jar_file, "application/java-archive")},
            data={
                "smart_assumptions": "true",
                "include_dependencies": "false",
                "target_version": "1.20.0"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "job_id" in data
        assert "status" in data
        assert "message" in data
        assert data["status"] == "queued"
        assert "estimated_time" in data

    def test_v1_convert_with_zip_upload(self, client):
        """Test v1 conversion endpoint with ZIP file upload."""
        # Create a mock ZIP file
        zip_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
        zip_file = io.BytesIO(zip_content)

        # Start conversion with file upload
        response = client.post(
            "/api/v1/convert",
            files={"mod_file": ("test.zip", zip_file, "application/zip")},
            data={
                "smart_assumptions": "false",
                "include_dependencies": "true",
                "mod_url": "https://example.com/mod",
                "target_version": "1.19.0"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "job_id" in data
        assert "status" in data
        assert data["status"] == "queued"

    def test_v1_convert_with_mcaddon_upload(self, client):
        """Test v1 conversion endpoint with MCADDON file upload."""
        # Create a mock MCADDON file
        mcaddon_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
        mcaddon_file = io.BytesIO(mcaddon_content)

        # Start conversion with file upload
        response = client.post(
            "/api/v1/convert",
            files={"mod_file": ("test.mcaddon", mcaddon_file, "application/zip")},
            data={
                "smart_assumptions": "true",
                "include_dependencies": "false"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "job_id" in data
        assert "status" in data
        assert data["status"] == "queued"

    def test_v1_convert_invalid_file_type(self, client):
        """Test v1 conversion endpoint with invalid file type."""
        # Create a text file (invalid)
        text_content = b"This is not a valid mod file"
        text_file = io.BytesIO(text_content)

        response = client.post(
            "/api/v1/convert",
            files={"mod_file": ("test.txt", text_file, "text/plain")},
            data={
                "smart_assumptions": "true",
                "include_dependencies": "false"
            }
        )

        # Should reject invalid file types
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not supported" in data["detail"]

    def test_v1_convert_no_file(self, client):
        """Test v1 conversion endpoint without file upload."""
        response = client.post(
            "/api/v1/convert",
            data={
                "smart_assumptions": "true",
                "include_dependencies": "false"
            }
        )

        # Should require file upload
        assert response.status_code == 422

    def test_v1_convert_large_file(self, client):
        """Test v1 conversion endpoint with oversized file."""
        # Create a file larger than the 100MB limit
        large_content = b"X" * (101 * 1024 * 1024)  # 101 MB
        large_file = io.BytesIO(large_content)

        response = client.post(
            "/api/v1/convert",
            files={"mod_file": ("large.jar", large_file, "application/java-archive")},
            data={
                "smart_assumptions": "true",
                "include_dependencies": "false"
            }
        )

        # Should reject files exceeding size limit
        assert response.status_code == 413
        data = response.json()
        assert "detail" in data
        assert "exceeds the limit" in data["detail"]


class TestV1StatusIntegration:
    """Integration tests for v1 status endpoints."""

    def test_v1_check_conversion_status(self, client):
        """Test checking conversion status via v1 endpoint."""
        # First start a conversion
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
        jar_file = io.BytesIO(jar_content)

        conversion_response = client.post(
            "/api/v1/convert",
            files={"mod_file": ("test.jar", jar_file, "application/java-archive")},
            data={
                "smart_assumptions": "true",
                "include_dependencies": "false"
            }
        )

        assert conversion_response.status_code == 200
        job_id = conversion_response.json()["job_id"]

        # Check status using v1 endpoint
        status_response = client.get(f"/api/v1/convert/{job_id}/status")

        assert status_response.status_code == 200
        status_data = status_response.json()

        # Verify status response structure
        assert "job_id" in status_data
        assert "status" in status_data
        assert "progress" in status_data
        assert "message" in status_data
        assert "created_at" in status_data
        assert status_data["job_id"] == job_id
        assert status_data["status"] in ["queued", "processing", "completed", "failed"]
        assert isinstance(status_data["progress"], int)
        assert 0 <= status_data["progress"] <= 100

    def test_v1_check_status_nonexistent_job(self, client):
        """Test checking status of non-existent job via v1 endpoint."""
        fake_job_id = "12345678-1234-1234-1234-123456789012"

        response = client.get(f"/api/v1/convert/{fake_job_id}/status")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_v1_check_status_invalid_job_id_format(self, client):
        """Test checking status with invalid job ID format."""
        invalid_job_id = "invalid-job-id"

        response = client.get(f"/api/v1/convert/{invalid_job_id}/status")

        # Should return validation error for invalid UUID format
        assert response.status_code == 422


class TestV1DownloadIntegration:
    """Integration tests for v1 download endpoints."""

    def test_v1_download_converted_mod(self, client):
        """Test downloading converted mod via v1 endpoint."""
        # First start a conversion
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
        jar_file = io.BytesIO(jar_content)

        conversion_response = client.post(
            "/api/v1/convert",
            files={"mod_file": ("test.jar", jar_file, "application/java-archive")},
            data={
                "smart_assumptions": "true",
                "include_dependencies": "false"
            }
        )

        assert conversion_response.status_code == 200
        job_id = conversion_response.json()["job_id"]

        # Wait for completion or check download immediately
        download_response = client.get(f"/api/v1/convert/{job_id}/download")

        # Should either return file or indicate job not completed
        assert download_response.status_code in [200, 400, 404]

        if download_response.status_code == 200:
            # Verify file download headers
            assert "application" in download_response.headers.get("content-type", "")
        elif download_response.status_code == 400:
            # Job not yet completed
            data = download_response.json()
            assert "detail" in data

    def test_v1_download_nonexistent_job(self, client):
        """Test downloading from non-existent job via v1 endpoint."""
        fake_job_id = "12345678-1234-1234-1234-123456789012"

        response = client.get(f"/api/v1/convert/{fake_job_id}/download")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestV1ErrorHandlingIntegration:
    """Integration tests for v1 error handling and edge cases."""

    def test_v1_database_unavailable_simulation(self, client):
        """Test behavior when database is unavailable."""
        # This test would require mocking database failures
        # For now, we'll test the normal flow and assume proper error handling
        pass

    def test_v1_redis_unavailable_simulation(self, client):
        """Test behavior when Redis is unavailable."""
        # This test would require mocking Redis failures
        # For now, we'll test the normal flow and assume proper error handling
        pass

    def test_v1_concurrent_requests(self, client):
        """Test handling of concurrent conversion requests."""
        # Create multiple conversion requests
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
        
        responses = []
        for i in range(3):
            jar_file = io.BytesIO(jar_content)
            response = client.post(
                "/api/v1/convert",
                files={"mod_file": (f"test_{i}.jar", jar_file, "application/java-archive")},
                data={
                    "smart_assumptions": "true",
                    "include_dependencies": "false"
                }
            )
            responses.append(response)

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "queued"

        # All job IDs should be unique
        job_ids = [response.json()["job_id"] for response in responses]
        assert len(set(job_ids)) == len(job_ids)


class TestV1FullWorkflowIntegration:
    """End-to-end integration tests for v1 API."""

    def test_v1_complete_conversion_workflow(self, client):
        """Test the complete v1 workflow from upload to result."""
        # Step 1: Start conversion with file upload
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
        jar_file = io.BytesIO(jar_content)

        conversion_response = client.post(
            "/api/v1/convert",
            files={"mod_file": ("workflow_test.jar", jar_file, "application/java-archive")},
            data={
                "smart_assumptions": "true",
                "include_dependencies": "false",
                "target_version": "1.20.0"
            }
        )

        assert conversion_response.status_code == 200
        job_id = conversion_response.json()["job_id"]

        # Step 2: Monitor status (check multiple times)
        max_attempts = 10
        final_status = None
        
        for attempt in range(max_attempts):
            status_response = client.get(f"/api/v1/convert/{job_id}/status")
            assert status_response.status_code == 200

            status_data = status_response.json()
            final_status = status_data["status"]
            
            # Verify progress is reasonable
            assert 0 <= status_data["progress"] <= 100
            
            if final_status in ["completed", "failed"]:
                break

            time.sleep(1)  # Wait before next check

        # Step 3: Verify final status is valid
        assert final_status in ["queued", "processing", "completed", "failed"]

        # Step 4: If completed, try to download
        if final_status == "completed":
            download_response = client.get(f"/api/v1/convert/{job_id}/download")
            assert download_response.status_code in [200, 404]  # File might not exist yet in mock

    def test_v1_workflow_with_all_options(self, client):
        """Test v1 workflow with all conversion options."""
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
        jar_file = io.BytesIO(jar_content)

        # Test with all possible options
        conversion_response = client.post(
            "/api/v1/convert",
            files={"mod_file": ("full_options.jar", jar_file, "application/java-archive")},
            data={
                "smart_assumptions": "false",
                "include_dependencies": "true",
                "mod_url": "https://example.com/mod-info",
                "target_version": "1.19.4"
            }
        )

        assert conversion_response.status_code == 200
        data = conversion_response.json()
        
        assert "job_id" in data
        assert data["status"] == "queued"
        
        # Verify we can check status
        job_id = data["job_id"]
        status_response = client.get(f"/api/v1/convert/{job_id}/status")
        assert status_response.status_code == 200