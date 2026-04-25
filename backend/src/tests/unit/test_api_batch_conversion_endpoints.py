"""
Tests for Batch Conversion API endpoints - src/api/batch_conversion.py
ConversionJob now has native batch_id/user_id columns in the model.
"""

import uuid
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

BATCH_ID = "batch_1700000000.0"
USER_ID = str(uuid.uuid4())


def _make_conversion(status="completed"):
    c = MagicMock()
    c.id = uuid.uuid4()
    c.status = status
    c.input_data = {"filename": "mod.jar"}
    c.progress = MagicMock()
    c.progress.progress = 100 if status == "completed" else 0
    c.error_message = "error" if status == "failed" else None
    return c


class TestBatchConversionModels:
    def test_batch_conversion_request_valid(self):
        from api.batch_conversion import BatchConversionRequest

        req = BatchConversionRequest(
            files=[{"name": "a.jar"}, {"name": "b.jar"}],
            options={"target": "1.20.4"},
        )
        assert len(req.files) == 2
        assert req.priority == "normal"

    def test_batch_conversion_response(self):
        from api.batch_conversion import BatchConversionResponse

        resp = BatchConversionResponse(
            batch_id="b1",
            total_files=5,
            estimated_time_minutes=10,
            status="queued",
            message="Started",
        )
        assert resp.batch_id == "b1"

    def test_batch_status_response(self):
        from api.batch_conversion import BatchStatusResponse

        resp = BatchStatusResponse(
            batch_id="b1",
            total=10,
            completed=5,
            failed=1,
            pending=4,
            progress_percent=50.0,
            conversions=[],
        )
        assert resp.progress_percent == 50.0

    def test_batch_result_response(self):
        from api.batch_conversion import BatchResultResponse

        resp = BatchResultResponse(
            batch_id="b1",
            results=[],
            download_all_url="http://example.com/dl",
            summary={"success": 5, "failed": 1},
        )
        assert resp.download_all_url is not None


class TestGetBatchStatus:
    @pytest.mark.asyncio
    async def test_batch_status_not_found(self):
        from api.batch_conversion import get_batch_status

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception):
            await get_batch_status(BATCH_ID, USER_ID, mock_db)

    @pytest.mark.asyncio
    async def test_batch_status_with_conversions(self):
        from api.batch_conversion import get_batch_status

        mock_db = AsyncMock()
        conversions = [_make_conversion("completed"), _make_conversion("queued")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = conversions
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = await get_batch_status(BATCH_ID, USER_ID, mock_db)

        assert resp.total == 2
        assert resp.completed == 1
        assert resp.pending == 1
        assert resp.progress_percent == 50.0


class TestGetBatchResults:
    @pytest.mark.asyncio
    async def test_batch_results_not_found(self):
        from api.batch_conversion import get_batch_results

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception):
            await get_batch_results(BATCH_ID, USER_ID, mock_db)

    @pytest.mark.asyncio
    async def test_batch_results_mixed(self):
        from api.batch_conversion import get_batch_results

        mock_db = AsyncMock()
        conversions = [_make_conversion("completed"), _make_conversion("failed")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = conversions
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = await get_batch_results(BATCH_ID, USER_ID, mock_db)

        assert resp.summary["successful"] == 1
        assert resp.summary["failed"] == 1
        assert resp.download_all_url is not None

    @pytest.mark.asyncio
    async def test_batch_results_all_failed(self):
        from api.batch_conversion import get_batch_results

        mock_db = AsyncMock()
        conversions = [_make_conversion("failed"), _make_conversion("failed")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = conversions
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = await get_batch_results(BATCH_ID, USER_ID, mock_db)

        assert resp.download_all_url is None
        assert resp.summary["successful"] == 0


class TestDownloadAllBatch:
    @pytest.mark.asyncio
    async def test_download_all_placeholder(self):
        from api.batch_conversion import download_all_batch

        mock_db = AsyncMock()
        result = await download_all_batch(BATCH_ID, USER_ID, mock_db)

        assert result["batch_id"] == BATCH_ID
        assert "filename" in result


class TestCancelBatch:
    @pytest.mark.asyncio
    async def test_cancel_batch_not_found(self):
        from api.batch_conversion import cancel_batch

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(Exception):
            await cancel_batch(BATCH_ID, USER_ID, mock_db)

    @pytest.mark.asyncio
    async def test_cancel_batch_with_pending(self):
        from api.batch_conversion import cancel_batch

        mock_db = AsyncMock()
        queued = _make_conversion("queued")
        completed = _make_conversion("completed")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [queued, completed]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        resp = await cancel_batch(BATCH_ID, USER_ID, mock_db)

        assert resp["cancelled_count"] == 1
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_batch_all_completed(self):
        from api.batch_conversion import cancel_batch

        mock_db = AsyncMock()
        conversions = [_make_conversion("completed"), _make_conversion("completed")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = conversions
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        resp = await cancel_batch(BATCH_ID, USER_ID, mock_db)

        assert resp["cancelled_count"] == 0


class TestProcessBatchConversion:
    @pytest.mark.asyncio
    async def test_process_batch_conversion_logs(self):
        from api.batch_conversion import process_batch_conversion

        await process_batch_conversion("batch_123", ["id1", "id2"], None)
