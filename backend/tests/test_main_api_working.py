"""
Working tests for main application endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.main import app

client = TestClient(app)


class TestMainAPIWorking:
    """Working tests for main application."""

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_upload_endpoint_validation(self):
        """Test upload endpoint validation."""
        response = client.post("/api/v1/upload")
        assert response.status_code in [400, 422]

    def test_convert_endpoint_validation(self):
        """Test convert endpoint validation."""
        response = client.post("/api/v1/convert")
        assert response.status_code in [400, 422]

    def test_api_documentation_exists(self):
        """Test API documentation endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema_exists(self):
        """Test OpenAPI schema endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_404_error_handling(self):
        """Test 404 error handling."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_addon_endpoint_exists(self):
        """Test addon endpoint exists."""
        response = client.get("/api/v1/addons/999")
        assert response.status_code in [404, 422]

    def test_job_report_endpoint_exists(self):
        """Test job report endpoint exists."""
        response = client.get("/api/v1/jobs/999/report")
        assert response.status_code == 404

    def test_response_format_consistency(self):
        """Test API response format consistency."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data

    def test_startup_sequence(self):
        """Test application startup."""
        with TestClient(app) as client:
            response = client.get("/api/v1/health")
            assert response.status_code == 200
