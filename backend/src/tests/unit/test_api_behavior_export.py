"""
Tests for Behavior Export API - src/api/behavior_export.py
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pydantic import ValidationError


class TestExportRequest:
    """Tests for ExportRequest model."""

    def test_valid_export_request(self):
        """Test valid behavior export request."""
        from api.behavior_export import ExportRequest
        
        request = ExportRequest(
            conversion_id="conv-123"
        )
        assert request.conversion_id == "conv-123"
        assert request.export_format == "mcaddon"

    def test_export_request_with_file_types(self):
        """Test export request with specific file types."""
        from api.behavior_export import ExportRequest
        
        request = ExportRequest(
            conversion_id="conv-123",
            file_types=["blocks", "items", "recipes"]
        )
        assert len(request.file_types) == 3

    def test_export_request_with_options(self):
        """Test export request with options."""
        from api.behavior_export import ExportRequest
        
        request = ExportRequest(
            conversion_id="conv-123",
            include_templates=False
        )
        assert request.include_templates is False

    def test_export_request_default_format(self):
        """Test export request default format."""
        from api.behavior_export import ExportRequest
        
        request = ExportRequest(conversion_id="conv-123")
        assert request.export_format == "mcaddon"


class TestExportResponse:
    """Tests for ExportResponse model."""

    def test_export_response(self):
        """Test behavior export response model."""
        from api.behavior_export import ExportResponse
        
        response = ExportResponse(
            conversion_id="conv-123",
            export_format="mcaddon",
            file_count=10,
            template_count=5,
            export_size=1024,
            exported_at="2024-01-01T00:00:00Z"
        )
        assert response.file_count == 10
        assert response.export_size == 1024


class TestExportFormatValidation:
    """Tests for export format validation."""

    def test_valid_mcaddon_format(self):
        """Test valid mcaddon format."""
        from api.behavior_export import ExportRequest
        
        request = ExportRequest(
            conversion_id="conv-123",
            export_format="mcaddon"
        )
        assert request.export_format == "mcaddon"

    def test_valid_zip_format(self):
        """Test valid zip format."""
        from api.behavior_export import ExportRequest
        
        request = ExportRequest(
            conversion_id="conv-123",
            export_format="zip"
        )
        assert request.export_format == "zip"

    def test_valid_json_format(self):
        """Test valid JSON format."""
        from api.behavior_export import ExportRequest
        
        request = ExportRequest(
            conversion_id="conv-123",
            export_format="json"
        )
        assert request.export_format == "json"