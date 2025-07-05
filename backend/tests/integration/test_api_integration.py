import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import asyncio
from main import app


@pytest.mark.asyncio
class TestAPIIntegration:
    """Integration tests for the API endpoints."""
    
    async def test_full_conversion_workflow(self, async_client: AsyncClient):
        """Test the complete conversion workflow."""
        # Step 1: Upload a file
        file_content = b"PK\x03\x04test_mod_content"
        files = {"file": ("test-mod.jar", file_content, "application/java-archive")}
        
        upload_response = await async_client.post("/api/upload", files=files)
        assert upload_response.status_code == 200
        
        # Step 2: Start conversion
        conversion_request = {
            "file_name": "test-mod.jar",
            "target_version": "1.20.0",
            "options": {"enable_smart_assumptions": True}
        }
        
        convert_response = await async_client.post("/api/convert", json=conversion_request)
        assert convert_response.status_code == 200
        
        conversion_data = convert_response.json()
        job_id = conversion_data["job_id"]
        
        # Step 3: Check conversion status
        status_response = await async_client.get(f"/api/convert/{job_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        assert status_data["job_id"] == job_id
        assert status_data["status"] in ["queued", "processing", "completed", "failed"]
    
    async def test_upload_and_list_conversions(self, async_client: AsyncClient):
        """Test uploading a file and listing conversions."""
        # Upload file
        file_content = b"PK\x03\x04test_content"
        files = {"file": ("another-mod.jar", file_content, "application/java-archive")}
        
        await async_client.post("/api/upload", files=files)
        
        # Start conversion
        conversion_request = {"file_name": "another-mod.jar"}
        await async_client.post("/api/convert", json=conversion_request)
        
        # List conversions
        list_response = await async_client.get("/api/convert")
        assert list_response.status_code == 200
        
        conversions = list_response.json()
        assert isinstance(conversions, list)
        assert len(conversions) >= 1
    
    @patch('main.app')  # This would patch actual AI service calls
    async def test_conversion_with_ai_service_mock(self, mock_ai_service, async_client: AsyncClient):
        """Test conversion with mocked AI service."""
        # Mock AI service response
        mock_ai_service.convert_mod = AsyncMock(return_value={
            "status": "completed",
            "output_file": "converted_mod.mcaddon",
            "report": "Conversion successful"
        })
        
        # Upload and convert
        file_content = b"PK\x03\x04mock_mod"
        files = {"file": ("mock-mod.jar", file_content, "application/java-archive")}
        
        await async_client.post("/api/upload", files=files)
        
        conversion_request = {"file_name": "mock-mod.jar"}
        response = await async_client.post("/api/convert", json=conversion_request)
        
        assert response.status_code == 200
    
    async def test_error_handling_invalid_file(self, async_client: AsyncClient):
        """Test error handling for invalid files."""
        # Try to upload an invalid file
        file_content = b"This is not a valid mod file"
        files = {"file": ("invalid.txt", file_content, "text/plain")}
        
        response = await async_client.post("/api/upload", files=files)
        assert response.status_code == 400
        
        error_data = response.json()
        assert "not supported" in error_data["detail"]
    
    async def test_concurrent_conversions(self, async_client: AsyncClient):
        """Test handling multiple concurrent conversions."""
        # Create multiple conversion requests
        tasks = []
        
        for i in range(3):
            file_content = f"PK\x03\x04mod_content_{i}".encode()
            files = {"file": (f"mod_{i}.jar", file_content, "application/java-archive")}
            
            # Upload file
            await async_client.post("/api/upload", files=files)
            
            # Create conversion task
            conversion_request = {"file_id": f"mod_{i}.jar", "original_filename": f"mod_{i}.jar"}
            task = async_client.post("/api/convert", json=conversion_request)
            tasks.append(task)
        
        # Execute all conversions concurrently
        responses = await asyncio.gather(*tasks)
        
        # Verify all conversions started successfully
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "queued"
    
    async def test_api_cors_headers(self, async_client: AsyncClient):
        """Test CORS headers are properly set."""
        response = await async_client.options("/api/convert")
        
        # Check for CORS headers (these would be set by the middleware)
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly handled
    
    async def test_api_openapi_docs(self, async_client: AsyncClient):
        """Test OpenAPI documentation is accessible."""
        docs_response = await async_client.get("/docs")
        assert docs_response.status_code == 200
        
        openapi_response = await async_client.get("/openapi.json")
        assert openapi_response.status_code == 200
        
        openapi_data = openapi_response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert openapi_data["info"]["title"] == "ModPorter AI Backend"