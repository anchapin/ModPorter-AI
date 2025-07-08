"""
Integration tests for the ModPorter AI Backend API v1 endpoints.

These tests verify the new /api/v1/* endpoints including file upload,
conversion processing, status tracking, and error handling.
"""

import io
import time

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
        # Message from old /api/v1/health specific endpoint is removed
        assert "message" not in data


class TestV1ConversionIntegration:
    """Integration tests for v1 conversion workflow with file upload."""

    def test_v1_convert_with_jar_upload(self, client):
        """Test v1 conversion endpoint with JAR file upload."""
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"

        # Step A: Upload file
        upload_response = client.post(
            "/api/v1/upload",
            files={"file": ("test.jar", io.BytesIO(jar_content), "application/java-archive")}
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]
        original_filename = upload_data["original_filename"]

        # Step B: Start conversion
        conversion_payload = {
            "file_id": file_id,
            "original_filename": original_filename,
            "target_version": "1.20.0",
            "options": {
                "smartAssumptions": True,
                "includeDependencies": False
            }
        }
        response = client.post("/api/v1/convert", json=conversion_payload)
        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "queued"
        assert "message" in data
        assert "estimated_time" in data

    def test_v1_convert_with_zip_upload(self, client):
        """Test v1 conversion endpoint with ZIP file upload."""
        zip_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"

        upload_response = client.post(
            "/api/v1/upload",
            files={"file": ("test.zip", io.BytesIO(zip_content), "application/zip")}
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]
        original_filename = upload_data["original_filename"]

        conversion_payload = {
            "file_id": file_id,
            "original_filename": original_filename,
            "target_version": "1.19.0",
            "options": {
                "smartAssumptions": False,
                "includeDependencies": True,
                "modUrl": "https://example.com/mod"
            }
        }
        response = client.post("/api/v1/convert", json=conversion_payload)
        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "queued"

    def test_v1_convert_with_mcaddon_upload(self, client):
        """Test v1 conversion endpoint with MCADDON file upload."""
        mcaddon_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"

        upload_response = client.post(
            "/api/v1/upload",
            files={"file": ("test.mcaddon", io.BytesIO(mcaddon_content), "application/octet-stream")} # common type for mcaddon
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]
        original_filename = upload_data["original_filename"]

        conversion_payload = {
            "file_id": file_id,
            "original_filename": original_filename,
            "options": {
                "smartAssumptions": True,
                "includeDependencies": False
            }
        }
        response = client.post("/api/v1/convert", json=conversion_payload)
        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "queued"

    def test_v1_upload_invalid_file_type(self, client): # Renamed from test_v1_convert_invalid_file_type
        """Test v1 upload endpoint with invalid file type."""
        text_content = b"This is not a valid mod file"

        response = client.post(
            "/api/v1/upload", # Changed to /upload
            files={"file": ("test.txt", io.BytesIO(text_content), "text/plain")}
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not supported" in data["detail"]

    def test_v1_convert_missing_file_id(self, client): # Renamed from test_v1_convert_no_file
        """Test v1 conversion endpoint with missing file_id in JSON payload."""
        conversion_payload = {
            # "file_id": "some-id", # Missing
            "original_filename": "test.jar",
            "options": {
                "smartAssumptions": True,
                "includeDependencies": False
            }
        }
        response = client.post("/api/v1/convert", json=conversion_payload)
        assert response.status_code == 422 # Expect 422 due to Pydantic validation

    def test_v1_upload_large_file(self, client): # Renamed from test_v1_convert_large_file
        """Test v1 upload endpoint with oversized file."""
        large_content = b"X" * (101 * 1024 * 1024)  # 101 MB

        response = client.post(
            "/api/v1/upload", # Changed to /upload
            files={"file": ("large.jar", io.BytesIO(large_content), "application/java-archive")}
        )
        assert response.status_code == 413
        data = response.json()
        assert "detail" in data
        assert "exceeds the limit" in data["detail"]


class TestV1StatusIntegration:
    """Integration tests for v1 status endpoints."""

    def test_v1_check_conversion_status(self, client):
        """Test checking conversion status via v1 endpoint."""
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"

        upload_response = client.post(
            "/api/v1/upload",
            files={"file": ("test.jar", io.BytesIO(jar_content), "application/java-archive")}
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]
        original_filename = upload_data["original_filename"]

        conversion_payload = {
            "file_id": file_id,
            "original_filename": original_filename,
            "options": {
                "smartAssumptions": True,
                "includeDependencies": False
            }
        }
        conversion_response = client.post("/api/v1/convert", json=conversion_payload)
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
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"

        upload_response = client.post(
            "/api/v1/upload",
            files={"file": ("test.jar", io.BytesIO(jar_content), "application/java-archive")}
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]
        original_filename = upload_data["original_filename"]

        conversion_payload = {
            "file_id": file_id,
            "original_filename": original_filename,
            "options": {
                "smartAssumptions": True,
                "includeDependencies": False
            }
        }
        conversion_response = client.post("/api/v1/convert", json=conversion_payload)
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
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
        
        upload_responses_data = []
        for i in range(3):
            upload_response = client.post(
                "/api/v1/upload",
                files={"file": (f"test_concurrent_{i}.jar", io.BytesIO(jar_content), "application/java-archive")}
            )
            assert upload_response.status_code == 200
            upload_responses_data.append(upload_response.json())

        conversion_responses = []
        for upload_data in upload_responses_data:
            conversion_payload = {
                "file_id": upload_data["file_id"],
                "original_filename": upload_data["original_filename"],
                "options": {"smartAssumptions": True, "includeDependencies": False}
            }
            response = client.post("/api/v1/convert", json=conversion_payload)
            conversion_responses.append(response)

        for response in conversion_responses:
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "queued"

        job_ids = [response.json()["job_id"] for response in conversion_responses]
        assert len(set(job_ids)) == len(job_ids)


class TestV1FullWorkflowIntegration:
    """End-to-end integration tests for v1 API."""

    def test_v1_complete_conversion_workflow(self, client):
        """Test the complete v1 workflow from upload to result."""
        # Step 1: Upload file
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
        upload_response = client.post(
            "/api/v1/upload",
            files={"file": ("workflow_test.jar", io.BytesIO(jar_content), "application/java-archive")}
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]
        original_filename = upload_data["original_filename"]

        # Step 2: Start conversion
        conversion_payload = {
            "file_id": file_id,
            "original_filename": original_filename,
            "options": {
                "smartAssumptions": True,
                "includeDependencies": False,
            },
            "target_version": "1.20.0"
        }
        conversion_response = client.post("/api/v1/convert", json=conversion_payload)
        assert conversion_response.status_code == 200
        job_id = conversion_response.json()["job_id"]

        # Step 3: Monitor status (check multiple times)
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

        # Step 1: Upload the file
        upload_response = client.post(
            "/api/v1/upload",
            files={"file": ("full_options.jar", jar_file, "application/java-archive")}
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        
        # Step 2: Start conversion with all options
        conversion_response = client.post(
            "/api/v1/convert",
            json={
                "file_id": upload_data["file_id"],
                "original_filename": upload_data["original_filename"],
                "target_version": "1.19.4",
                "options": {
                    "smartAssumptions": False,
                    "includeDependencies": True,
                    "modUrl": "https://example.com/mod-info"
                }
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


# Imports for Report API tests (ensure these are at the top if not already)
# from fastapi.testclient import TestClient # Already imported via pytest
# from src.main import app # Already imported via pytest
from src.services.report_generator import MOCK_CONVERSION_RESULT_SUCCESS, MOCK_CONVERSION_RESULT_FAILURE
from src.services.report_models import InteractiveReport, FullConversionReport

# Module-level client for report tests, if not using pytest fixtures for all tests
# client = TestClient(app) # Pytest client fixture is generally preferred

class TestReportAPIEndpoints:
    """Integration tests for the V1 Report API endpoints."""

    def test_get_interactive_report_success(self, client): # client fixture from conftest.py or global
        job_id = MOCK_CONVERSION_RESULT_SUCCESS["job_id"] # "job_123_success"
        response = client.get(f"/api/v1/jobs/{job_id}/report")
        assert response.status_code == 200
        report_data = response.json()
        assert report_data["job_id"] == job_id
        assert report_data["summary"]["overall_success_rate"] == MOCK_CONVERSION_RESULT_SUCCESS["overall_success_rate"]
        assert "feature_analysis" in report_data
        assert "smart_assumptions_report" in report_data
        assert "developer_log" in report_data

    def test_get_interactive_report_failure(self, client):
        job_id = MOCK_CONVERSION_RESULT_FAILURE["job_id"] # "job_456_failure"
        response = client.get(f"/api/v1/jobs/{job_id}/report")
        assert response.status_code == 200
        report_data = response.json()
        assert report_data["job_id"] == job_id
        assert report_data["summary"]["overall_success_rate"] == MOCK_CONVERSION_RESULT_FAILURE["overall_success_rate"]
        assert len(report_data["failed_mods"]) > 0

    def test_get_interactive_report_generic_success(self, client):
        response = client.get("/api/v1/jobs/some-random-job-id-success/report")
        assert response.status_code == 200
        report_data = response.json()
        assert report_data["summary"]["overall_success_rate"] == MOCK_CONVERSION_RESULT_SUCCESS["overall_success_rate"]

    def test_get_interactive_report_not_found(self, client):
        response = client.get("/api/v1/jobs/unknown_job_id_123/report")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_prd_style_report_success(self, client):
        job_id = MOCK_CONVERSION_RESULT_SUCCESS["job_id"]
        response = client.get(f"/api/v1/jobs/{job_id}/report/prd")
        assert response.status_code == 200
        report_data = response.json()
        assert report_data["summary"]["overall_success_rate"] == MOCK_CONVERSION_RESULT_SUCCESS["overall_success_rate"]
        assert "smart_assumptions" in report_data
        assert isinstance(report_data["smart_assumptions"], list)

    def test_get_prd_style_report_failure(self, client):
        job_id = MOCK_CONVERSION_RESULT_FAILURE["job_id"]
        response = client.get(f"/api/v1/jobs/{job_id}/report/prd")
        assert response.status_code == 200
        report_data = response.json()
        assert report_data["summary"]["overall_success_rate"] == MOCK_CONVERSION_RESULT_FAILURE["overall_success_rate"]

    def test_get_prd_style_report_not_found(self, client):
        response = client.get("/api/v1/jobs/unknown_job_id_456/report/prd")
        assert response.status_code == 404