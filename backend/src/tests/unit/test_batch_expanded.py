"""
Expanded unit tests for api/batch_conversion.py module.

Covers batch conversion creation, status polling, and cancellation.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException
from datetime import datetime, timezone

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api import batch_conversion
from api.batch_conversion import (
    BatchConversionRequest,
    BatchConversionResponse,
    BatchStatusResponse,
    BatchResultResponse,
    start_batch_conversion,
    process_batch_conversion,
    get_batch_status,
    get_batch_results,
    download_all_batch,
    cancel_batch,
)


class TestBatchConversionRequest:
    """Tests for BatchConversionRequest model."""

    def test_valid_request(self):
        """Test valid batch conversion request."""
        request = BatchConversionRequest(
            files=[
                {"file_id": "file1", "name": "mod1.jar"},
                {"file_id": "file2", "name": "mod2.jar"},
            ]
        )
        assert len(request.files) == 2
        assert request.priority == "normal"

    def test_request_with_options(self):
        """Test request with custom options."""
        request = BatchConversionRequest(
            files=[
                {"file_id": "file1", "name": "mod1.jar"},
                {"file_id": "file2", "name": "mod2.jar"},
            ],
            options={"optimize": True},
            priority="high",
        )
        assert request.options == {"optimize": True}
        assert request.priority == "high"

    def test_request_min_files_validation(self):
        """Test that at least 2 files are required."""
        with pytest.raises(ValueError):
            BatchConversionRequest(files=[{"file_id": "file1", "name": "mod1.jar"}])

    def test_request_max_files_validation(self):
        """Test that maximum 20 files are allowed."""
        with pytest.raises(ValueError):
            BatchConversionRequest(
                files=[{"file_id": f"file{i}", "name": f"mod{i}.jar"} for i in range(21)]
            )


class TestBatchConversionResponse:
    """Tests for BatchConversionResponse model."""

    def test_response_creation(self):
        """Test batch conversion response creation."""
        response = BatchConversionResponse(
            batch_id="batch_123",
            total_files=5,
            estimated_time_minutes=10,
            status="queued",
            message="Batch conversion started",
        )
        assert response.batch_id == "batch_123"
        assert response.total_files == 5
        assert response.status == "queued"


class TestBatchStatusResponse:
    """Tests for BatchStatusResponse model."""

    def test_status_response_creation(self):
        """Test batch status response creation."""
        response = BatchStatusResponse(
            batch_id="batch_123",
            total=5,
            completed=2,
            failed=0,
            pending=3,
            progress_percent=40.0,
            conversions=[],
        )
        assert response.progress_percent == 40.0
        assert response.completed == 2


class TestBatchResultResponse:
    """Tests for BatchResultResponse model."""

    def test_result_response_creation(self):
        """Test batch result response creation."""
        response = BatchResultResponse(
            batch_id="batch_123",
            results=[],
            download_all_url="https://example.com/download/batch_123.zip",
            summary={"total": 5, "successful": 4, "failed": 1},
        )
        assert response.batch_id == "batch_123"
        assert response.summary["total"] == 5


class TestProcessBatchConversion:
    """Tests for process_batch_conversion function."""

    @pytest.mark.asyncio
    async def test_process_batch_basic(self):
        """Test basic batch processing."""
        batch_id = "batch_test_123"
        conversion_ids = [str(uuid.uuid4()) for _ in range(3)]
        options = {"optimize": True}

        # Should complete without error
        await process_batch_conversion(batch_id, conversion_ids, options)

    @pytest.mark.asyncio
    async def test_process_batch_empty(self):
        """Test batch processing with empty conversion list."""
        batch_id = "batch_empty"
        conversion_ids = []
        options = None

        await process_batch_conversion(batch_id, conversion_ids, options)

    @pytest.mark.asyncio
    async def test_process_batch_with_options(self):
        """Test batch processing with various options."""
        batch_id = "batch_options"
        conversion_ids = [str(uuid.uuid4())]
        options = {
            "validation": "strict",
            "optimize": True,
            "validation_level": "comprehensive",
        }

        await process_batch_conversion(batch_id, conversion_ids, options)


class TestStartBatchConversionEndpoint:
    @pytest.mark.asyncio
    async def test_start_batch_user_not_found(self):
        from api.batch_conversion import start_batch_conversion, BatchConversionRequest

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        request = BatchConversionRequest(
            files=[{"name": "a.jar"}, {"name": "b.jar"}],
        )

        with pytest.raises(HTTPException) as exc_info:
            await start_batch_conversion(
                request=request,
                user_id=str(uuid.uuid4()),
                background_tasks=MagicMock(),
                db=mock_db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_start_batch_success(self):
        from api.batch_conversion import start_batch_conversion, BatchConversionRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_bg = MagicMock()

        request = BatchConversionRequest(
            files=[{"name": "mod1.jar"}, {"name": "mod2.jar"}],
            options={"target": "1.20.0"},
        )

        resp = await start_batch_conversion(
            request=request,
            user_id=str(mock_user.id),
            background_tasks=mock_bg,
            db=mock_db,
        )

        assert resp.total_files == 2
        assert resp.status == "queued"
        assert resp.batch_id.startswith("batch_")
        mock_db.commit.assert_called_once()
        mock_bg.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_batch_max_files_validation(self):
        from pydantic import ValidationError
        from api.batch_conversion import BatchConversionRequest

        with pytest.raises(ValidationError):
            BatchConversionRequest(
                files=[{"name": f"mod{i}.jar"} for i in range(21)],
            )
