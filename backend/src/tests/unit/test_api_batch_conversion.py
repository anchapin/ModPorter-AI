"""
Tests for Batch Conversion API - src/api/batch_conversion.py
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport


class TestBatchConversionRequest:
    """Tests for BatchConversionRequest model."""

    def test_valid_batch_request(self):
        """Test valid batch conversion request."""
        from api.batch_conversion import BatchConversionRequest
        
        request = BatchConversionRequest(
            files=[{"name": "mod1.jar"}, {"name": "mod2.jar"}],
            options={"target": "1.20.4"}
        )
        assert len(request.files) == 2
        assert request.priority == "normal"

    def test_batch_request_with_priority(self):
        """Test batch request with custom priority."""
        from api.batch_conversion import BatchConversionRequest
        
        request = BatchConversionRequest(
            files=[{"name": "mod1.jar"}, {"name": "mod2.jar"}],
            priority="high"
        )
        assert request.priority == "high"

    def test_batch_request_invalid_min_items(self):
        """Test batch request with less than 2 files."""
        from api.batch_conversion import BatchConversionRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            BatchConversionRequest(files=[{"name": "mod1.jar"}])

    def test_batch_request_invalid_max_items(self):
        """Test batch request with more than 20 files."""
        from api.batch_conversion import BatchConversionRequest
        from pydantic import ValidationError
        
        files = [{"name": f"mod{i}.jar"} for i in range(25)]
        with pytest.raises(ValidationError):
            BatchConversionRequest(files=files)


class TestBatchConversionResponse:
    """Tests for BatchConversionResponse model."""

    def test_response_model(self):
        """Test batch conversion response model."""
        from api.batch_conversion import BatchConversionResponse
        
        response = BatchConversionResponse(
            batch_id="batch-123",
            total_files=5,
            estimated_time_minutes=30,
            status="processing",
            message="Batch conversion started"
        )
        assert response.batch_id == "batch-123"
        assert response.total_files == 5


class TestBatchStatusResponse:
    """Tests for BatchStatusResponse model."""

    def test_status_response_model(self):
        """Test batch status response model."""
        from api.batch_conversion import BatchStatusResponse
        
        response = BatchStatusResponse(
            batch_id="batch-123",
            total=10,
            completed=5,
            failed=1,
            pending=4,
            progress_percent=50.0,
            conversions=[]
        )
        assert response.progress_percent == 50.0
        assert response.completed == 5


class TestBatchResultResponse:
    """Tests for BatchResultResponse model."""

    def test_result_response_model(self):
        """Test batch result response model."""
        from api.batch_conversion import BatchResultResponse
        
        response = BatchResultResponse(
            batch_id="batch-123",
            results=[],
            download_all_url="https://example.com/download/batch-123",
            summary={"success": 5, "failed": 1}
        )
        assert response.batch_id == "batch-123"