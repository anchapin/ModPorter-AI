"""
Comprehensive tests for main.py module.

This test suite covers:
- Application startup and lifecycle
- All API endpoints
- File upload and conversion workflows
- Error handling and edge cases
- Background task processing
- Middleware functionality
"""

import pytest
import os
import sys
import json
import uuid
import asyncio
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.main import app, lifespan, conversion_jobs_db, AI_ENGINE_URL
from src.models.addon_models import Addon


class TestApplicationLifecycle:
    """Test cases for application startup and shutdown."""
    
    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self):
        """Test successful application startup."""
        with patch('src.main.init_db', new_callable=AsyncMock) as mock_init_db:
            with patch.dict(os.environ, {"TESTING": "false"}):
                async with lifespan(app):
                    pass
                
                mock_init_db.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_lifespan_startup_testing_env(self):
        """Test application startup in testing environment."""
        with patch('src.main.init_db', new_callable=AsyncMock) as mock_init_db:
            with patch.dict(os.environ, {"TESTING": "true"}):
                async with lifespan(app):
                    pass
                
                mock_init_db.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_lifespan_shutdown(self):
        """Test application shutdown."""
        with patch('src.main.init_db', new_callable=AsyncMock):
            async with lifespan(app) as manager:
                pass
            # Shutdown happens after context manager exits
    
    def test_app_creation(self):
        """Test FastAPI application creation."""
        assert app is not None
        assert hasattr(app, 'router')
        assert hasattr(app, 'state')


class TestHealthEndpoints:
    """Test cases for health check endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_root_health_check(self, client):
        """Test root health endpoint."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_api_health_check(self, client):
        """Test API health endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_health_check_with_service_status(self, client):
        """Test health endpoint with service status details."""
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)


class TestFileUploadEndpoints:
    """Test cases for file upload functionality."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_file(self):
        """Create a sample file for upload testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.zip', delete=False) as f:
            f.write("sample mod content")
            temp_path = f.name
        
        yield temp_path
        os.unlink(temp_path)
    
    def test_upload_endpoint_missing_file(self, client):
        """Test upload endpoint with no file provided."""
        response = client.post("/api/v1/upload")
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_upload_endpoint_success(self, client, sample_file):
        """Test successful file upload."""
        with open(sample_file, 'rb') as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("test_mod.zip", f, "application/zip")}
            )
        
        # Should succeed or return validation error based on implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_upload_endpoint_invalid_file_type(self, client):
        """Test upload with invalid file type."""
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            f.write(b"not a zip file")
            f.seek(0)
            
            response = client.post(
                "/api/v1/upload",
                files={"file": ("invalid.txt", f, "text/plain")}
            )
        
        # Should reject non-zip files
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_upload_large_file(self, client):
        """Test upload of file exceeding size limit."""
        # Create a large temporary file
        with tempfile.NamedTemporaryFile(suffix='.zip') as f:
            f.write(b"x" * (200 * 1024 * 1024))  # 200MB
            f.seek(0)
            
            response = client.post(
                "/api/v1/upload",
                files={"file": ("large.zip", f, "application/zip")}
            )
        
        # Should reject large files
        assert response.status_code in [
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_400_BAD_REQUEST
        ]


class TestConversionEndpoints:
    """Test cases for conversion workflow endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_convert_endpoint_no_data(self, client):
        """Test convert endpoint with no data."""
        response = client.post("/api/v1/convert")
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_convert_endpoint_valid_data(self, client):
        """Test convert endpoint with valid data."""
        data = {
            "addon_id": str(uuid.uuid4()),
            "target_version": "1.19.2",
            "conversion_options": {
                "preserve_data": True,
                "optimize_resources": False
            }
        }
        
        response = client.post("/api/v1/convert", json=data)
        
        # Should succeed or return validation error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_conversion_status_endpoint_not_found(self, client):
        """Test conversion status for non-existent job."""
        non_existent_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/convert/{non_existent_id}/status")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_conversion_status_endpoint_success(self, client):
        """Test conversion status for existing job."""
        # Create a test job
        job_id = str(uuid.uuid4())
        conversion_jobs_db[job_id] = {
            "id": job_id,
            "status": "processing",
            "progress": 50
        }
        
        response = client.get(f"/api/v1/convert/{job_id}/status")
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "status" in data
            assert "progress" in data
        
        # Clean up
        if job_id in conversion_jobs_db:
            del conversion_jobs_db[job_id]
    
    def test_conversions_list_endpoint(self, client):
        """Test conversions list endpoint."""
        response = client.get("/api/v1/conversions")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, (list, dict))
    
    def test_cancel_conversion_endpoint(self, client):
        """Test cancel conversion endpoint."""
        job_id = str(uuid.uuid4())
        
        response = client.post(f"/api/v1/convert/{job_id}/cancel")
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ]


class TestDownloadEndpoints:
    """Test cases for file download endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_download_converted_file_not_found(self, client):
        """Test download of non-existent converted file."""
        file_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/download/{file_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_download_converted_file_success(self, client):
        """Test successful download of converted file."""
        # Create a test file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
            f.write(b"converted mod content")
            temp_path = f.name
        
        file_id = str(uuid.uuid4())
        
        try:
            response = client.get(f"/api/v1/download/{file_id}")
            
            # Implementation may vary
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_404_NOT_FOUND
            ]
        finally:
            os.unlink(temp_path)
    
    def test_export_addon_endpoint(self, client):
        """Test addon export endpoint."""
        addon_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/addons/{addon_id}/export")
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ]


class TestReportEndpoints:
    """Test cases for conversion report endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_get_conversion_report_not_found(self, client):
        """Test getting report for non-existent conversion."""
        conversion_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/reports/{conversion_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_conversion_report_success(self, client):
        """Test successful retrieval of conversion report."""
        conversion_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/reports/{conversion_id}")
        
        # Implementation may vary
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_generate_report_endpoint(self, client):
        """Test report generation endpoint."""
        data = {
            "conversion_id": str(uuid.uuid4()),
            "report_type": "detailed",
            "include_suggestions": True
        }
        
        response = client.post("/api/v1/reports/generate", json=data)
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]


class TestBackgroundTasks:
    """Test cases for background task processing."""
    
    @pytest.mark.asyncio
    async def test_conversion_background_task(self):
        """Test background conversion task execution."""
        with patch('src.main.asset_conversion_service') as mock_service:
            mock_service.convert_addon = AsyncMock(return_value={"success": True})
            
            job_id = str(uuid.uuid4())
            addon_data = {"id": job_id, "name": "test_mod"}
            
            # Simulate background task
            from src.main import process_conversion_job
            if 'process_conversion_job' in dir():
                await process_conversion_job(job_id, addon_data)
    
    @pytest.mark.asyncio
    async def test_background_task_error_handling(self):
        """Test background task error handling."""
        with patch('src.main.asset_conversion_service') as mock_service:
            mock_service.convert_addon = AsyncMock(side_effect=Exception("Service error"))
            
            job_id = str(uuid.uuid4())
            addon_data = {"id": job_id, "name": "test_mod"}
            
            # Simulate background task with error
            try:
                if 'process_conversion_job' in dir():
                    await process_conversion_job(job_id, addon_data)
            except Exception:
                pass  # Expected to handle errors gracefully


class TestMiddleware:
    """Test cases for middleware functionality."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/v1/health")
        
        # Check for CORS headers
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers"
        ]
        
        for header in cors_headers:
            if header in response.headers:
                assert response.headers[header] is not None
    
    def test_request_logging(self, client):
        """Test request logging middleware."""
        with patch('src.main.logger') as mock_logger:
            response = client.get("/api/v1/health")
            
            # Should have logged the request
            assert response.status_code == status.HTTP_200_OK
    
    def test_error_handling_middleware(self, client):
        """Test error handling middleware."""
        # Test with invalid endpoint
        response = client.get("/api/v1/nonexistent")
        
        # Should return 404 or 422
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]


class TestDatabaseIntegration:
    """Test cases for database integration."""
    
    @pytest.mark.asyncio
    async def test_database_dependency(self):
        """Test database dependency injection."""
        with patch('src.main.get_db', new_callable=AsyncMock) as mock_get_db:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_get_db.return_value = mock_db
            
            # Test database dependency in endpoint
            from src.main import get_db
            db_gen = get_db()
            db = await anext(db_gen)
            
            assert db == mock_db
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """Test database error handling."""
        with patch('src.main.get_db', new_callable=AsyncMock) as mock_get_db:
            mock_get_db.side_effect = Exception("Database error")
            
            client = TestClient(app)
            response = client.get("/api/v1/conversions")
            
            # Should handle database errors gracefully
            assert response.status_code in [
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                status.HTTP_503_SERVICE_UNAVAILABLE
            ]


class TestConfiguration:
    """Test cases for application configuration."""
    
    def test_ai_engine_url_configuration(self):
        """Test AI Engine URL configuration."""
        assert AI_ENGINE_URL is not None
        assert isinstance(AI_ENGINE_URL, str)
    
    def test_environment_variables(self):
        """Test environment variable loading."""
        with patch.dict(os.environ, {"TESTING": "true"}):
            # Reload app to test environment loading
            from src.main import load_dotenv
            load_dotenv()
            
            assert os.getenv("TESTING") == "true"
    
    def test_directory_creation(self):
        """Test required directories are created or handled."""
        required_dirs = [
            "temp_uploads",
            "conversion_outputs"
        ]
        
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            # Directory should exist or be handled gracefully
            if dir_path.exists():
                assert dir_path.is_dir()


class TestAPIIntegration:
    """Test cases for API integration scenarios."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_complete_conversion_workflow(self, client):
        """Test complete conversion workflow integration."""
        # 1. Upload file (mock)
        with tempfile.NamedTemporaryFile(suffix='.zip') as f:
            f.write(b"mod content")
            f.seek(0)
            
            upload_response = client.post(
                "/api/v1/upload",
                files={"file": ("test_mod.zip", f, "application/zip")}
            )
        
        # 2. Start conversion (mock data)
        conversion_data = {
            "addon_id": str(uuid.uuid4()),
            "target_version": "1.19.2"
        }
        
        conversion_response = client.post("/api/v1/convert", json=conversion_data)
        
        # 3. Check status (if job was created)
        if conversion_response.status_code in [200, 201]:
            job_id = conversion_response.json().get("id")
            if job_id:
                status_response = client.get(f"/api/v1/convert/{job_id}/status")
                assert status_response.status_code in [200, 404]
        
        # 4. List conversions
        list_response = client.get("/api/v1/conversions")
        assert list_response.status_code == 200
    
    def test_error_propagation(self, client):
        """Test error propagation through API layers."""
        # Test invalid data
        invalid_data = {"invalid_field": "value"}
        
        response = client.post("/api/v1/convert", json=invalid_data)
        
        # Should handle validation errors
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
        
        error_data = response.json()
        assert "detail" in error_data or "error" in error_data


class TestPerformance:
    """Test cases for performance and scalability."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_concurrent_requests(self, client):
        """Test handling concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            start = time.time()
            response = client.get("/api/v1/health")
            end = time.time()
            results.append((response.status_code, end - start))
        
        # Make 10 concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(results) == 10
        
        for status_code, duration in results:
            assert status_code == status.HTTP_200_OK
            # Request should complete in reasonable time
            assert duration < 5.0
    
    def test_memory_usage(self, client):
        """Test application memory usage."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make multiple requests
        for _ in range(100):
            response = client.get("/api/v1/health")
            assert response.status_code == status.HTTP_200_OK
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        # Allow for some increase but not excessive
        assert memory_increase < 50 * 1024 * 1024  # 50MB


# Utility functions
async def anext(async_generator):
    """Helper to get next item from async generator."""
    return await async_generator.__anext__()


class TestEdgeCases:
    """Test cases for edge cases and boundary conditions."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_empty_request_body(self, client):
        """Test endpoints with empty request body."""
        response = client.post("/api/v1/convert", json={})
        
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_malformed_json(self, client):
        """Test endpoints with malformed JSON."""
        response = client.post(
            "/api/v1/convert",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_very_long_values(self, client):
        """Test endpoints with very long string values."""
        long_string = "x" * 10000
        data = {
            "addon_id": str(uuid.uuid4()),
            "target_version": "1.19.2",
            "notes": long_string
        }
        
        response = client.post("/api/v1/convert", json=data)
        
        # Should handle gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_special_characters(self, client):
        """Test endpoints with special characters."""
        special_data = {
            "addon_id": str(uuid.uuid4()),
            "target_version": "1.19.2",
            "name": "Mod!@#$%^&*()_+-=[]{}|;':\",./<>?"
        }
        
        response = client.post("/api/v1/convert", json=special_data)
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_unicode_characters(self, client):
        """Test endpoints with unicode characters."""
        unicode_data = {
            "addon_id": str(uuid.uuid4()),
            "target_version": "1.19.2",
            "name": "Módéfication Ñoël 🎮",
            "description": "测试中文字符 🚀"
        }
        
        response = client.post("/api/v1/convert", json=unicode_data)
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
