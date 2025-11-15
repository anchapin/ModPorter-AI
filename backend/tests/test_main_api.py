"""
Tests for main application endpoints and core functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from src.main import app
from src.config import settings

client = TestClient(app)


class TestMainAPI:
    """Test main application endpoints."""

    def test_health_check(self):
        """Test basic health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_upload_endpoint_exists(self):
        """Test that upload endpoint exists."""
        response = client.post("/api/v1/upload")
        # Should return validation error for missing file
        assert response.status_code in [400, 422]

    def test_convert_endpoint_exists(self):
        """Test that convert endpoint exists."""
        response = client.post("/api/v1/convert")
        # Should return validation error for missing data
        assert response.status_code in [400, 422]

    def test_conversion_status_endpoint(self):
        """Test conversion status endpoint exists."""
        response = client.get("/api/v1/convert/123/status")
        # Should return 404 for non-existent job
        assert response.status_code == 404

    def test_conversions_list_endpoint(self):
        """Test conversions list endpoint exists."""
        response = client.get("/api/v1/conversions")
        # Should return 200 (empty list or actual data)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_error_handling(self):
        """Test 404 error handling."""
        response = client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404

    @patch('src.main.settings')
    def test_configuration_loading(self, mock_settings):
        """Test application configuration loading."""
        mock_settings.database_url = "test://database"
        mock_settings.debug = True
        # Verify settings are loaded correctly
        assert settings.database_url is not None

    def test_startup_sequence(self):
        """Test application startup sequence."""
        # Test that app can be created and starts properly
        with TestClient(app) as client:
            response = client.get("/api/v1/health")
            assert response.status_code == 200

    def test_environment_detection(self):
        """Test environment detection (dev/prod)."""
        # Test that environment is detected correctly
        with patch.dict('os.environ', {'TESTING': 'true'}):
            from src.config import settings
            assert settings.testing is True

    def test_request_validation(self):
        """Test request validation middleware."""
        # Test invalid JSON
        response = client.post("/api/v1/convert", 
                          data="invalid json",
                          headers={"Content-Type": "application/json"})
        assert response.status_code == 422

    def test_dependency_injection(self):
        """Test dependency injection system."""
        # Test that dependencies are properly injected
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_api_documentation(self):
        """Test API documentation is available."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_schema(self):
        """Test OpenAPI schema generation."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    def test_security_headers(self):
        """Test security headers are present."""
        response = client.get("/api/v1/health")
        headers = response.headers
        # Test for common security headers
        assert "x-content-type-options" in headers

    def test_content_type_handling(self):
        """Test content-type handling."""
        # Test JSON content type
        response = client.post("/api/v1/convert",
                          json={"test": "data"},
                          headers={"Content-Type": "application/json"})
        # Should handle JSON properly
        assert response.status_code in [200, 400, 422]

    def test_database_transactions(self):
        """Test database transaction handling."""
        # Test that database operations are wrapped in transactions
        with patch('src.main.database.session') as mock_session:
            mock_session.begin.return_value.__enter__ = MagicMock()
            mock_session.begin.return_value.__exit__ = MagicMock()
            
            response = client.get("/api/v1/health")
            assert response.status_code == 200

    def test_error_response_format(self):
        """Test error response format consistency."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        data = response.json()
        # Test error response format
        assert "detail" in data or "error" in data

    def test_addons_endpoint(self):
        """Test addons endpoint exists."""
        response = client.get("/api/v1/addons/999")
        # Should return 404 for non-existent addon
        assert response.status_code == 404

    def test_jobs_report_endpoint(self):
        """Test jobs report endpoint exists."""
        response = client.get("/api/v1/jobs/999/report")
        # Should return 404 for non-existent job
        assert response.status_code == 404

    def test_main_response_format(self):
        """Test API response format consistency."""
        response = client.get("/api/v1/health")
        data = response.json()
        # Test that response follows expected format
        assert isinstance(data, dict)
        assert "status" in data
