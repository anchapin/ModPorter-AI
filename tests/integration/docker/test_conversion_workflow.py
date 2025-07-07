import pytest
import requests
import io
import json
import time


@pytest.mark.integration_docker
@pytest.mark.docker_workflow
class TestConversionWorkflow:
    """
    Tests for verifying the complete conversion workflow in the Docker environment.
    """

    def test_complete_conversion_workflow(self, docker_environment):
        """
        Test the complete file upload -> convert -> status workflow.
        This test verifies that the frontend can communicate with the backend
        and that the AI engine integration works in a real Docker environment.
        """
        backend_api_url = docker_environment.get("backend_api")
        assert backend_api_url, "Backend API URL not provided by docker_environment fixture"

        # Step 1: Upload a test JAR file
        jar_content = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"  # Valid ZIP/JAR header
        jar_file = io.BytesIO(jar_content)

        upload_response = requests.post(
            f"{backend_api_url}/upload",
            files={"file": ("test_workflow.jar", jar_file, "application/java-archive")},
            timeout=30
        )

        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        upload_data = upload_response.json()
        assert "filename" in upload_data
        assert upload_data["filename"] == "test_workflow.jar"

        # Step 2: Start conversion
        conversion_response = requests.post(
            f"{backend_api_url}/convert",
            json={
                "file_name": "test_workflow.jar",
                "target_version": "1.20.0",
                "smart_assumptions": {
                    "enable_smart_assumptions": True,
                    "assumption_confidence": 0.8
                }
            },
            timeout=30
        )

        assert conversion_response.status_code == 200, f"Conversion start failed: {conversion_response.text}"
        conversion_data = conversion_response.json()
        assert "job_id" in conversion_data
        assert "status" in conversion_data
        job_id = conversion_data["job_id"]

        # Step 3: Check conversion status
        # Poll for status with timeout
        max_attempts = 10
        poll_interval = 5
        
        for attempt in range(max_attempts):
            status_response = requests.get(
                f"{backend_api_url}/convert/{job_id}",
                timeout=30
            )
            
            assert status_response.status_code == 200, f"Status check failed: {status_response.text}"
            status_data = status_response.json()
            
            assert "job_id" in status_data
            assert "status" in status_data
            assert "progress" in status_data
            assert status_data["job_id"] == job_id
            
            # Check if job is complete or failed
            if status_data["status"] in ["completed", "failed"]:
                break
            
            # Wait before next poll
            if attempt < max_attempts - 1:
                time.sleep(poll_interval)
        
        # Verify we got a final status
        final_status = status_data["status"]
        assert final_status in ["completed", "failed"], f"Job did not reach final state: {final_status}"

        # Step 4: List conversions to verify job appears in list
        list_response = requests.get(f"{backend_api_url}/convert", timeout=30)
        assert list_response.status_code == 200, f"List conversions failed: {list_response.text}"
        
        conversions = list_response.json()
        assert isinstance(conversions, list), "Conversions should be a list"
        
        # Find our job in the list
        our_job = None
        for conversion in conversions:
            if conversion.get("job_id") == job_id:
                our_job = conversion
                break
        
        assert our_job is not None, f"Job {job_id} not found in conversions list"
        assert our_job["status"] == final_status

    def test_frontend_backend_communication(self, docker_environment):
        """
        Test that the frontend can successfully communicate with the backend.
        This addresses the core issue where integration tests were passing
        but real-world frontend-backend communication was failing.
        """
        frontend_url = docker_environment.get("frontend")
        backend_api_url = docker_environment.get("backend_api")
        
        assert frontend_url, "Frontend URL not provided by docker_environment fixture"
        assert backend_api_url, "Backend API URL not provided by docker_environment fixture"

        # Test 1: Frontend serves the application
        frontend_response = requests.get(frontend_url, timeout=30)
        assert frontend_response.status_code == 200
        
        # Verify it's serving a React app
        content = frontend_response.text.lower()
        assert "<!doctype html>" in content or "vite" in content or "react" in content
        
        # Test 2: Backend API is accessible
        health_response = requests.get(f"{backend_api_url}/health", timeout=30)
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        assert health_data.get("status") == "healthy"

        # Test 3: Test CORS configuration by making a request that would typically fail
        # This simulates what the frontend would do when calling the backend
        headers = {
            "Origin": frontend_url,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        
        # OPTIONS preflight request
        options_response = requests.options(
            f"{backend_api_url}/upload",
            headers=headers,
            timeout=30
        )
        
        # Should not fail due to CORS issues
        assert options_response.status_code in [200, 204]

    def test_error_handling_in_docker_environment(self, docker_environment):
        """
        Test error handling scenarios in the real Docker environment.
        """
        backend_api_url = docker_environment.get("backend_api")
        assert backend_api_url, "Backend API URL not provided by docker_environment fixture"

        # Test 1: Invalid file upload
        invalid_file = io.BytesIO(b"This is not a valid mod file")
        
        upload_response = requests.post(
            f"{backend_api_url}/upload",
            files={"file": ("invalid.txt", invalid_file, "text/plain")},
            timeout=30
        )
        
        # Should handle invalid file types gracefully
        assert upload_response.status_code == 400
        error_data = upload_response.json()
        assert "detail" in error_data

        # Test 2: Non-existent job status check
        fake_job_id = "12345678-1234-1234-1234-123456789012"
        
        status_response = requests.get(
            f"{backend_api_url}/convert/{fake_job_id}",
            timeout=30
        )
        
        assert status_response.status_code == 404
        error_data = status_response.json()
        assert "detail" in error_data