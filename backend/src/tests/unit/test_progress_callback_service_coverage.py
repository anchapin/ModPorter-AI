"""
Tests for progress_callback module.
Covers: services/progress_callback.py
"""
import pytest
from unittest.mock import AsyncMock, Mock
from services.progress_callback import (
    ProgressCallback,
    get_progress_callback,
    ConversionStages,
    STAGE_PROGRESS,
)


class TestProgressCallback:
    """Test ProgressCallback class."""

    @pytest.fixture
    def callback_system(self):
        return ProgressCallback()

    def test_initialization(self, callback_system):
        assert callback_system._subscribers == {}
        assert callback_system._progress_history == {}

    @pytest.mark.asyncio
    async def test_subscribe(self, callback_system):
        callback = AsyncMock()
        callback_system.subscribe("job-123", callback)
        assert "job-123" in callback_system._subscribers
        assert callback in callback_system._subscribers["job-123"]

    @pytest.mark.asyncio
    async def test_subscribe_multiple_callbacks(self, callback_system):
        callback1 = AsyncMock()
        callback2 = AsyncMock()
        callback_system.subscribe("job-123", callback1)
        callback_system.subscribe("job-123", callback2)
        assert len(callback_system._subscribers["job-123"]) == 2

    @pytest.mark.asyncio
    async def test_unsubscribe(self, callback_system):
        callback = AsyncMock()
        callback_system.subscribe("job-123", callback)
        callback_system.unsubscribe("job-123", callback)
        assert "job-123" not in callback_system._subscribers

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_empty_jobs(self, callback_system):
        callback = AsyncMock()
        callback_system.subscribe("job-123", callback)
        # Progress history should remain even after unsub
        callback_system._progress_history["job-123"] = []
        callback_system.unsubscribe("job-123", callback)
        # After unsubscribe, job should be removed from subscribers
        assert "job-123" not in callback_system._subscribers

    @pytest.mark.asyncio
    async def test_update_progress_notifies_subscribers(self, callback_system):
        callback = AsyncMock()
        callback_system.subscribe("job-123", callback)
        await callback_system.update_progress(
            job_id="job-123",
            progress=50,
            current_stage="translating",
            message="Processing files",
        )
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["progress"] == 50
        assert call_args["current_stage"] == "translating"

    @pytest.mark.asyncio
    async def test_update_progress_stores_history(self, callback_system):
        await callback_system.update_progress(
            job_id="job-123",
            progress=25,
            current_stage="analyzing",
        )
        await callback_system.update_progress(
            job_id="job-123",
            progress=50,
            current_stage="translating",
        )
        history = callback_system.get_progress_history("job-123")
        assert len(history) == 2
        assert history[0]["progress"] == 25
        assert history[1]["progress"] == 50

    @pytest.mark.asyncio
    async def test_update_progress_with_metadata(self, callback_system):
        await callback_system.update_progress(
            job_id="job-123",
            progress=75,
            current_stage="validating",
            metadata={"files_processed": 10},
        )
        history = callback_system.get_progress_history("job-123")
        assert history[0]["metadata"]["files_processed"] == 10

    @pytest.mark.asyncio
    async def test_update_progress_handles_callback_error(self, callback_system):
        callback = AsyncMock(side_effect=Exception("callback failed"))
        callback_system.subscribe("job-123", callback)
        # Should not raise, just log the error
        await callback_system.update_progress(
            job_id="job-123",
            progress=50,
            current_stage="translating",
        )

    @pytest.mark.asyncio
    async def test_update_progress_without_subscribers(self, callback_system):
        # Should not raise
        await callback_system.update_progress(
            job_id="job-123",
            progress=50,
            current_stage="translating",
        )
        # Should still store in history
        history = callback_system.get_progress_history("job-123")
        assert len(history) == 1

    def test_get_progress_history_empty(self, callback_system):
        history = callback_system.get_progress_history("nonexistent")
        assert history == []

    def test_cleanup_job(self, callback_system):
        callback_system.subscribe("job-123", AsyncMock())
        callback_system._progress_history["job-123"] = []
        callback_system.cleanup_job("job-123")
        assert "job-123" not in callback_system._subscribers
        assert "job-123" not in callback_system._progress_history

    def test_cleanup_nonexistent_job(self, callback_system):
        # Should not raise
        callback_system.cleanup_job("nonexistent")


class TestConversionStages:
    """Test ConversionStages constants."""

    def test_stage_constants(self):
        assert ConversionStages.QUEUED == "queued"
        assert ConversionStages.ANALYZING == "analyzing"
        assert ConversionStages.TRANSLATING == "translating"
        assert ConversionStages.VALIDATING == "validating"
        assert ConversionStages.PACKAGING == "packaging"
        assert ConversionStages.COMPLETED == "completed"
        assert ConversionStages.FAILED == "failed"


class TestStageProgress:
    """Test STAGE_PROGRESS constants."""

    def test_stage_progress_mapping(self):
        assert STAGE_PROGRESS[ConversionStages.QUEUED] == 0
        assert STAGE_PROGRESS[ConversionStages.ANALYZING] == 10
        assert STAGE_PROGRESS[ConversionStages.TRANSLATING] == 40
        assert STAGE_PROGRESS[ConversionStages.VALIDATING] == 80
        assert STAGE_PROGRESS[ConversionStages.PACKAGING] == 90
        assert STAGE_PROGRESS[ConversionStages.COMPLETED] == 100
        assert STAGE_PROGRESS[ConversionStages.FAILED] == -1

    def test_all_stages_have_progress(self):
        for stage in [
            ConversionStages.QUEUED,
            ConversionStages.ANALYZING,
            ConversionStages.TRANSLATING,
            ConversionStages.VALIDATING,
            ConversionStages.PACKAGING,
            ConversionStages.COMPLETED,
            ConversionStages.FAILED,
        ]:
            assert stage in STAGE_PROGRESS


class TestGetProgressCallback:
    """Test get_progress_callback singleton."""

    def test_singleton_returns_same_instance(self):
        # Import fresh each time to test singleton
        from services.progress_callback import get_progress_callback
        instance1 = get_progress_callback()
        instance2 = get_progress_callback()
        assert instance1 is instance2

    def test_singleton_is_progress_callback(self):
        from services.progress_callback import get_progress_callback
        instance = get_progress_callback()
        assert isinstance(instance, ProgressCallback)