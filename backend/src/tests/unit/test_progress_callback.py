"""Tests for the progress_callback module."""

import pytest
from unittest.mock import AsyncMock
from services.progress_callback import (
    ProgressCallback,
    get_progress_callback,
    ConversionStages,
    STAGE_PROGRESS,
)


class TestProgressCallback:
    """Test cases for ProgressCallback class."""

    def test_init(self):
        """Test ProgressCallback initialization."""
        callback = ProgressCallback()
        assert callback._subscribers == {}
        assert callback._progress_history == {}

    def test_subscribe_new_job(self):
        """Test subscribing to a new job."""
        callback = ProgressCallback()
        test_callback = AsyncMock()

        callback.subscribe("job-1", test_callback)

        assert "job-1" in callback._subscribers
        assert test_callback in callback._subscribers["job-1"]
        assert "job-1" in callback._progress_history
        assert callback._progress_history["job-1"] == []

    def test_subscribe_existing_job(self):
        """Test subscribing to an already subscribed job."""
        callback = ProgressCallback()
        callback1 = AsyncMock()
        callback2 = AsyncMock()

        callback.subscribe("job-1", callback1)
        callback.subscribe("job-1", callback2)

        assert len(callback._subscribers["job-1"]) == 2
        assert callback1 in callback._subscribers["job-1"]
        assert callback2 in callback._subscribers["job-1"]

    def test_unsubscribe_callback(self):
        """Test unsubscribing a specific callback."""
        callback = ProgressCallback()
        callback1 = AsyncMock()
        callback2 = AsyncMock()

        callback.subscribe("job-1", callback1)
        callback.subscribe("job-1", callback2)

        callback.unsubscribe("job-1", callback1)

        assert callback1 not in callback._subscribers["job-1"]
        assert callback2 in callback._subscribers["job-1"]

    def test_unsubscribe_last_callback_removes_job(self):
        """Test that removing last callback cleans up job."""
        callback = ProgressCallback()
        test_callback = AsyncMock()

        callback.subscribe("job-1", test_callback)
        callback.unsubscribe("job-1", test_callback)

        assert "job-1" not in callback._subscribers

    def test_unsubscribe_nonexistent_job(self):
        """Test unsubscribing from job that doesn't exist."""
        callback = ProgressCallback()
        test_callback = AsyncMock()

        # Should not raise
        callback.unsubscribe("nonexistent-job", test_callback)

    @pytest.mark.asyncio
    async def test_update_progress_stores_history(self):
        """Test that update_progress stores history."""
        callback = ProgressCallback()
        callback.subscribe("job-1", AsyncMock())

        await callback.update_progress(
            job_id="job-1", progress=50, current_stage="translating", message="Processing files"
        )

        history = callback.get_progress_history("job-1")
        assert len(history) == 1
        assert history[0]["progress"] == 50
        assert history[0]["current_stage"] == "translating"
        assert history[0]["message"] == "Processing files"

    @pytest.mark.asyncio
    async def test_update_progress_notifies_subscribers(self):
        """Test that update_progress calls subscribers."""
        callback = ProgressCallback()
        subscriber = AsyncMock()
        callback.subscribe("job-1", subscriber)

        await callback.update_progress(job_id="job-1", progress=75, current_stage="validating")

        subscriber.assert_called_once()
        call_args = subscriber.call_args[0][0]
        assert call_args["progress"] == 75
        assert call_args["current_stage"] == "validating"

    @pytest.mark.asyncio
    async def test_update_progress_without_subscribers(self):
        """Test update_progress when no subscribers exist."""
        callback = ProgressCallback()

        # Should not raise
        await callback.update_progress(job_id="job-1", progress=25, current_stage="analyzing")

        # Should still store history
        assert "job-1" in callback._progress_history

    @pytest.mark.asyncio
    async def test_update_progress_handles_callback_exception(self):
        """Test that callback exceptions are handled gracefully."""
        callback = ProgressCallback()

        async def failing_callback(progress_data):
            raise Exception("Callback failed!")

        callback.subscribe("job-1", failing_callback)

        # Should not raise
        await callback.update_progress(job_id="job-1", progress=50, current_stage="translating")

    def test_get_progress_history_nonexistent_job(self):
        """Test getting history for job that doesn't exist."""
        callback = ProgressCallback()

        history = callback.get_progress_history("nonexistent-job")

        assert history == []

    def test_cleanup_job(self):
        """Test cleaning up job data."""
        callback = ProgressCallback()
        callback.subscribe("job-1", AsyncMock())

        callback.cleanup_job("job-1")

        assert "job-1" not in callback._subscribers
        assert "job-1" not in callback._progress_history

    def test_cleanup_nonexistent_job(self):
        """Test cleaning up job that doesn't exist."""
        callback = ProgressCallback()

        # Should not raise
        callback.cleanup_job("nonexistent-job")


class TestConversionStages:
    """Test cases for ConversionStages constants."""

    def test_stage_constants(self):
        """Test all stage constants are defined."""
        assert ConversionStages.QUEUED == "queued"
        assert ConversionStages.ANALYZING == "analyzing"
        assert ConversionStages.TRANSLATING == "translating"
        assert ConversionStages.VALIDATING == "validating"
        assert ConversionStages.PACKAGING == "packaging"
        assert ConversionStages.COMPLETED == "completed"
        assert ConversionStages.FAILED == "failed"

    def test_stage_progress_mapping(self):
        """Test stage progress percentages."""
        assert STAGE_PROGRESS[ConversionStages.QUEUED] == 0
        assert STAGE_PROGRESS[ConversionStages.ANALYZING] == 10
        assert STAGE_PROGRESS[ConversionStages.TRANSLATING] == 40
        assert STAGE_PROGRESS[ConversionStages.VALIDATING] == 80
        assert STAGE_PROGRESS[ConversionStages.PACKAGING] == 90
        assert STAGE_PROGRESS[ConversionStages.COMPLETED] == 100
        assert STAGE_PROGRESS[ConversionStages.FAILED] == -1


class TestGetProgressCallback:
    """Test cases for get_progress_callback singleton."""

    def test_returns_singleton(self):
        """Test that get_progress_callback returns same instance."""
        callback1 = get_progress_callback()
        callback2 = get_progress_callback()

        assert callback1 is callback2

    def test_singleton_is_progress_callback_instance(self):
        """Test that singleton is ProgressCallback instance."""
        callback = get_progress_callback()

        assert isinstance(callback, ProgressCallback)
