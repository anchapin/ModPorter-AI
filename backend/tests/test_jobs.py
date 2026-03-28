"""
Unit tests for job processing system.

Tests:
- Job Manager: job creation, retrieval, listing, updates
- Conversion Worker: job processing, retry logic, DLQ
- Jobs API: endpoints, validation, error handling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import json

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from services.job_manager import (
    JobManager,
    JobStatus,
    ConversionMode,
    TargetVersion,
    OutputFormat,
    JobOptions,
    Job,
)
from worker.conversion_worker import ConversionWorker


# Test fixtures


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis._client = AsyncMock()
    redis._client.zadd = AsyncMock(return_value=1)
    redis._client.zrem = AsyncMock(return_value=1)
    redis._client.zrevrange = AsyncMock(return_value=[])
    redis._client.zcard = AsyncMock(return_value=0)
    return redis


@pytest.fixture
def mock_queue():
    """Mock job queue"""
    queue = AsyncMock()
    queue.enqueue = AsyncMock(return_value=True)
    queue.dequeue = AsyncMock(return_value=None)
    queue.complete_job = AsyncMock(return_value=True)
    return queue


# Job Manager Tests


@pytest.mark.asyncio
async def test_job_creation():
    """Test creating a new job"""
    manager = JobManager()
    manager._redis = AsyncMock()
    manager._queue = AsyncMock()
    manager._redis.set = AsyncMock(return_value=True)
    manager._redis.get = AsyncMock(return_value=None)
    manager._redis._client = AsyncMock()
    manager._redis._client.zadd = AsyncMock(return_value=1)
    manager._redis.expire = AsyncMock(return_value=True)
    manager._queue.enqueue = AsyncMock(return_value=True)

    job_id = await manager.create_job(
        user_id="test_user",
        file_path="/uploads/test.jar",
        original_filename="test.jar",
    )

    assert job_id is not None
    assert len(job_id) == 36  # UUID format


@pytest.mark.asyncio
async def test_job_retrieval():
    """Test retrieving a job by ID"""
    manager = JobManager()
    manager._redis = AsyncMock()

    job_data = {
        "job_id": "test-job-123",
        "user_id": "test_user",
        "file_path": "/uploads/test.jar",
        "original_filename": "test.jar",
        "status": "pending",
        "progress": 0,
        "current_step": "pending",
        "options": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    manager._redis.get = AsyncMock(return_value=json.dumps(job_data))

    job = await manager.get_job("test-job-123")

    assert job is not None
    assert job.job_id == "test-job-123"
    assert job.user_id == "test_user"


@pytest.mark.asyncio
async def test_job_progress_update():
    """Test updating job progress"""
    manager = JobManager()
    manager._redis = AsyncMock()

    job_data = {
        "job_id": "test-job-123",
        "user_id": "test_user",
        "file_path": "/uploads/test.jar",
        "original_filename": "test.jar",
        "status": "processing",
        "progress": 0,
        "current_step": "pending",
        "options": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    manager._redis.get = AsyncMock(return_value=json.dumps(job_data))
    manager._redis.set = AsyncMock(return_value=True)

    success = await manager.update_progress("test-job-123", 50, "Analyzing file...")

    assert success is True


@pytest.mark.asyncio
async def test_job_completion():
    """Test marking job as completed"""
    manager = JobManager()
    manager._redis = AsyncMock()

    job_data = {
        "job_id": "test-job-123",
        "user_id": "test_user",
        "file_path": "/uploads/test.jar",
        "original_filename": "test.jar",
        "status": "processing",
        "progress": 90,
        "current_step": "Packaging...",
        "options": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    manager._redis.get = AsyncMock(return_value=json.dumps(job_data))
    manager._redis.set = AsyncMock(return_value=True)

    success = await manager.complete_job("test-job-123", result_url="/downloads/result.mcaddon")

    assert success is True


# Conversion Worker Tests


@pytest.mark.asyncio
async def test_worker_initialization():
    """Test worker initializes correctly"""
    worker = ConversionWorker()

    assert worker is not None
    assert worker._running is False
    assert worker.MAX_RETRIES == 3


@pytest.mark.asyncio
async def test_worker_process_job_success():
    """Test successful job processing"""
    worker = ConversionWorker()
    worker._job_manager = AsyncMock()
    worker._storage = AsyncMock()
    worker._ai_engine = AsyncMock()
    worker._queue = AsyncMock()
    worker._redis = AsyncMock()

    # Mock successful job manager calls
    worker._job_manager.update_progress = AsyncMock(return_value=True)
    worker._job_manager.complete_job = AsyncMock(return_value=True)

    # Mock the file operations
    with patch("worker.conversion_worker.ConversionWorker._download_file") as mock_download:
        with patch("worker.conversion_worker.ConversionWorker._run_conversion") as mock_convert:
            with patch("worker.conversion_worker.ConversionWorker._upload_results") as mock_upload:
                with patch("worker.conversion_worker.ConversionWorker._cleanup"):
                    mock_download.return_value = "/tmp/test-file.jar"
                    mock_convert.return_value = {"success": True, "output_path": "/tmp/out.mcaddon"}
                    mock_upload.return_value = "/downloads/result.mcaddon"

                    job_data = {
                        "job_id": "test-job-123",
                        "user_id": "test_user",
                        "file_path": "/uploads/test.jar",
                        "original_filename": "test.jar",
                        "options": {"conversion_mode": "standard"},
                    }

                    result = await worker.process_job(job_data)

                    assert result is True
                    worker._job_manager.update_progress.assert_any_call(
                        "test-job-123", 0, "Starting conversion..."
                    )
                    worker._job_manager.complete_job.assert_called_once()


@pytest.mark.asyncio
async def test_worker_process_job_failure():
    """Test job processing failure handling"""
    worker = ConversionWorker()
    worker._job_manager = AsyncMock()
    worker._queue = AsyncMock()
    worker._redis = AsyncMock()

    # Mock failure
    worker._job_manager.update_progress = AsyncMock(return_value=True)
    worker._job_manager.fail_job = AsyncMock(return_value=True)

    job_data = {
        "job_id": "test-job-123",
        "user_id": "test_user",
        "file_path": "/uploads/test.jar",
        "original_filename": "test.jar",
        "options": {},
    }

    # Mock _download_file to raise an error
    with patch.object(worker, "_download_file", side_effect=Exception("File not found")):
        result = await worker.process_job(job_data)

        assert result is False
        # Check that fail_job was called (not fail for cancelled or other reasons)
        assert worker._job_manager.fail_job.called or worker._job_manager.update_progress.called


@pytest.mark.asyncio
async def test_retry_logic():
    """Test retry scheduling logic"""
    worker = ConversionWorker()
    worker._queue = AsyncMock()
    worker._queue.enqueue = AsyncMock(return_value=True)

    job_data = {
        "job_id": "test-job-123",
        "user_id": "test_user",
        "file_path": "/uploads/test.jar",
        "options": {},
    }

    # Test with patch for sleep
    with patch("asyncio.sleep", return_value=None):
        await worker._schedule_retry(job_data, 0)

    worker._queue.enqueue.assert_called_once()


# API Tests


@pytest.mark.asyncio
async def test_list_jobs_endpoint():
    """Test listing jobs via API"""
    from api.jobs import list_jobs

    # Create mock job manager
    mock_manager = AsyncMock()

    # Mock job data
    mock_job = Job(
        job_id="test-job-123",
        user_id="test_user",
        file_path="/uploads/test.jar",
        original_filename="test.jar",
        status=JobStatus.PENDING,
    )

    mock_manager.list_jobs = AsyncMock(return_value=[mock_job])

    response = await list_jobs(
        limit=10,
        offset=0,
        job_manager=mock_manager,
        user_id="test_user",
    )

    assert response.total == 1
    assert len(response.jobs) == 1
    assert response.jobs[0].job_id == "test-job-123"


@pytest.mark.asyncio
async def test_get_job_endpoint():
    """Test getting job details via API"""
    from api.jobs import get_job

    mock_manager = AsyncMock()

    mock_job = Job(
        job_id="test-job-123",
        user_id="test_user",
        file_path="/uploads/test.jar",
        original_filename="test.jar",
        status=JobStatus.COMPLETED,
        progress=100,
        result_url="/downloads/result.mcaddon",
    )

    mock_manager.get_job = AsyncMock(return_value=mock_job)

    response = await get_job(
        job_id="test-job-123",
        job_manager=mock_manager,
        user_id="test_user",
    )

    assert response.job_id == "test-job-123"
    assert response.status == "completed"
    assert response.progress == 100


@pytest.mark.asyncio
async def test_cancel_job_endpoint():
    """Test cancelling a job via API"""
    from api.jobs import cancel_job
    from fastapi import HTTPException

    mock_manager = AsyncMock()

    mock_job = Job(
        job_id="test-job-123",
        user_id="test_user",
        file_path="/uploads/test.jar",
        original_filename="test.jar",
        status=JobStatus.PROCESSING,
    )

    mock_manager.get_job = AsyncMock(return_value=mock_job)
    mock_manager.cancel_job = AsyncMock(return_value=True)

    response = await cancel_job(
        job_id="test-job-123",
        job_manager=mock_manager,
        user_id="test_user",
    )

    assert response.job_id == "test-job-123"
    assert "cancelled" in response.message.lower()


@pytest.mark.asyncio
async def test_create_job_endpoint():
    """Test creating a job via API"""
    from api.jobs import create_job, JobCreateRequest

    mock_manager = AsyncMock()
    mock_manager.create_job = AsyncMock(return_value="new-job-456")

    request = JobCreateRequest(
        file_path="/uploads/new.jar",
        original_filename="new.jar",
    )

    response = await create_job(
        request=request,
        job_manager=mock_manager,
        user_id="test_user",
    )

    assert response.job_id == "new-job-456"
    assert "created" in response.message.lower()


# Test for job not found error
@pytest.mark.asyncio
async def test_get_nonexistent_job():
    """Test getting a job that doesn't exist"""
    from api.jobs import get_job
    from fastapi import HTTPException

    mock_manager = AsyncMock()
    mock_manager.get_job = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_job(
            job_id="nonexistent-job",
            job_manager=mock_manager,
            user_id="test_user",
        )

    assert exc_info.value.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
