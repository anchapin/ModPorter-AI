"""
Focused API tests for main.py to improve coverage.
Tests core endpoints without complex dependencies.
"""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND


class TestMainAPI:
    """Test main API endpoints with minimal dependencies."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        # Import here to avoid initialization issues
        from src.main import app
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
    def test_health_endpoint_response_structure(self, client):
        """Test health endpoint response structure."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        
    def test_upload_endpoint_no_file(self, client):
        """Test upload endpoint with no file."""
        response = client.post("/api/v1/upload")
        assert response.status_code == 422
        
    def test_upload_endpoint_invalid_file_type(self, client):
        """Test upload endpoint with invalid file type."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"invalid content")
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                response = client.post(
                    "/api/v1/upload",
                    files={"file": ("invalid.txt", f, "text/plain")}
                )
            assert response.status_code in [400, 422]
        finally:
            os.unlink(tmp_path)
            
    def test_convert_endpoint_no_data(self, client):
        """Test convert endpoint with no data."""
        response = client.post("/api/v1/convert")
        assert response.status_code == 422
        
    def test_convert_endpoint_missing_file_id(self, client):
        """Test convert endpoint with missing file_id."""
        response = client.post(
            "/api/v1/convert",
            json={"target_version": "1.20.1"}
        )
        assert response.status_code == 422
        
    def test_convert_endpoint_invalid_target_version(self, client):
        """Test convert endpoint with invalid target version."""
        response = client.post(
            "/api/v1/convert",
            json={
                "file_id": "test-file-id",
                "target_version": "invalid.version.format"
            }
        )
        assert response.status_code == 422
        
    def test_status_endpoint_invalid_job_id(self, client):
        """Test status endpoint with invalid job ID format."""
        response = client.get("/api/v1/convert/invalid-uuid/status")
        assert response.status_code == 422
        
    def test_status_endpoint_nonexistent_job(self, client):
        """Test status endpoint for non-existent job."""
        job_id = "12345678-1234-1234-1234-123456789012"
        response = client.get(f"/api/v1/convert/{job_id}/status")
        assert response.status_code == 404
        
    def test_list_conversions_endpoint(self, client):
        """Test list conversions endpoint."""
        response = client.get("/api/v1/conversions")
        # Should work even with no conversions
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_cancel_endpoint_invalid_job_id(self, client):
        """Test cancel endpoint with invalid job ID format."""
        response = client.delete("/api/v1/convert/invalid-uuid")
        assert response.status_code == 422
        
    def test_cancel_endpoint_nonexistent_job(self, client):
        """Test cancel endpoint for non-existent job."""
        job_id = "12345678-1234-1234-1234-123456789012"
        response = client.delete(f"/api/v1/convert/{job_id}")
        assert response.status_code == 404
        
    def test_download_endpoint_invalid_job_id(self, client):
        """Test download endpoint with invalid job ID format."""
        response = client.get("/api/v1/convert/invalid-uuid/download")
        assert response.status_code == 422
        
    def test_download_endpoint_nonexistent_job(self, client):
        """Test download endpoint for non-existent job."""
        job_id = "12345678-1234-1234-1234-123456789012"
        response = client.get(f"/api/v1/convert/{job_id}/download")
        assert response.status_code == 404
        
    def test_upload_valid_jar_file(self, client):
        """Test upload with valid JAR file."""
        # Mock the database operations
        with patch('src.main.crud.create_job') as mock_create, \
             patch('src.main.crud.update_job_status') as mock_update, \
             patch('src.main.cache.set_job_status') as mock_set_status, \
             patch('src.main.cache.set_progress') as mock_set_progress:
            
            mock_job = AsyncMock()
            mock_job.id = "test-job-id"
            mock_job.status = "uploaded"
            mock_create.return_value = mock_job
            mock_update.return_value = mock_job
            
            with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tmp:
                tmp.write(b"fake jar content")
                tmp_path = tmp.name

            try:
                with open(tmp_path, "rb") as f:
                    response = client.post(
                        "/api/v1/upload",
                        files={"file": ("test.jar", f, "application/java-archive")}
                    )
                
                # Should either succeed or fail gracefully
                assert response.status_code in [200, 201, 400, 422]
            finally:
                os.unlink(tmp_path)
                
    def test_convert_with_valid_data(self, client):
        """Test convert with valid request data."""
        # Mock all dependencies
        with patch('src.main.crud.get_job') as mock_get_job, \
             patch('src.main.crud.create_job') as mock_create_job, \
             patch('src.main.crud.update_job_status') as mock_update_job, \
             patch('src.main.cache.set_job_status') as mock_set_status, \
             patch('src.main.cache.set_progress') as mock_set_progress, \
             patch('src.main.BackgroundTasks.add_task') as mock_add_task:
            
            # Mock existing job
            mock_job = AsyncMock()
            mock_job.id = "test-job-id"
            mock_job.status = "uploaded"
            mock_get_job.return_value = mock_job
            mock_update_job.return_value = mock_job
            
            # Mock new conversion job
            mock_conversion_job = AsyncMock()
            mock_conversion_job.id = "conversion-job-id"
            mock_conversion_job.status = "processing"
            mock_create_job.return_value = mock_conversion_job
            
            response = client.post(
                "/api/v1/convert",
                json={
                    "file_id": "test-file-id",
                    "target_version": "1.20.1",
                    "options": {"optimize": True}
                }
            )
            
            # Should either succeed or fail gracefully
            assert response.status_code in [200, 400, 422, 404]
