"""
Comprehensive tests for BatchProcessingService.

This module tests the core functionality of the BatchProcessingService,
including job submission, tracking, execution, and management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import uuid

from src.services.batch_processing import (
    BatchProcessingService, BatchJob, BatchOperationType,
    BatchStatus, ProcessingMode, BatchProgress, BatchResult
)


class TestBatchProcessingService:
    """Test cases for BatchProcessingService class."""

    @pytest.fixture
    def service(self):
        """Create a BatchProcessingService instance for testing."""
        return BatchProcessingService()

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session for testing."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def sample_batch_job(self):
        """Sample batch job for testing."""
        return BatchJob(
            job_id=str(uuid.uuid4()),
            operation_type=BatchOperationType.IMPORT_NODES,
            status=BatchStatus.PENDING,
            created_at=datetime.utcnow(),
            total_items=100,
            processed_items=0,
            failed_items=0,
            chunk_size=10,
            processing_mode=ProcessingMode.PARALLEL,
            parallel_workers=4,
            parameters={"source": "test_file.json"}
        )

    @pytest.fixture
    def sample_batch_progress(self):
        """Sample batch progress for testing."""
        return BatchProgress(
            job_id=str(uuid.uuid4()),
            total_items=100,
            processed_items=50,
            failed_items=5,
            current_chunk=5,
            total_chunks=10,
            progress_percentage=50.0,
            estimated_remaining_seconds=120.0,
            processing_rate_items_per_second=5.0,
            last_update=datetime.utcnow()
        )

    @pytest.fixture
    def sample_batch_result(self):
        """Sample batch result for testing."""
        return BatchResult(
            success=True,
            job_id="test_job_123",
            operation_type=BatchOperationType.IMPORT_NODES,
            total_processed=95,
            total_failed=5,
            execution_time_seconds=180.0,
            result_data={"chunks_processed": 10},
            errors=[
                "item_10: Invalid data format",
                "item_25: Missing required field"
            ],
            metadata={"source": "test_file.json", "target": "knowledge_graph"}
        )

    @pytest.mark.asyncio
    async def test_init(self, service):
        """Test BatchProcessingService initialization."""
        assert service.active_jobs == {}
        assert service.job_history == []
        assert service.max_concurrent_jobs == 5
        assert service.default_chunk_size == 100
        assert service.default_processing_mode == ProcessingMode.SEQUENTIAL

    @pytest.mark.asyncio
    async def test_submit_batch_job(self, service, mock_db_session):
        """Test submitting a new batch job."""
        # Job parameters
        job_params = {
            "operation_type": BatchOperationType.IMPORT_NODES,
            "total_items": 100,
            "chunk_size": 10,
            "processing_mode": ProcessingMode.PARALLEL,
            "parallel_workers": 4,
            "parameters": {"source": "test_file.json"}
        }

        # Mock database operations
        with patch('src.services.batch_processing.get_async_session', return_value=mock_db_session):
            # Call the method
            result = await service.submit_batch_job(job_params)

            # Verify the result
            assert result is not None
            assert "job_id" in result
            assert result["status"] == BatchStatus.PENDING.value
            assert result["operation_type"] == BatchOperationType.IMPORT_NODES.value
            assert result["total_items"] == 100
            assert result["chunk_size"] == 10
            assert result["processing_mode"] == ProcessingMode.PARALLEL.value

            # Verify the job is added to active jobs
            job_id = result["job_id"]
            assert job_id in service.active_jobs
            assert service.active_jobs[job_id].status == BatchStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_job_status(self, service, sample_batch_job):
        """Test getting the status of a batch job."""
        job_id = sample_batch_job.job_id

        # Add job to active jobs
        service.active_jobs[job_id] = sample_batch_job

        # Call the method
        result = await service.get_job_status(job_id)

        # Verify the result
        assert result is not None
        assert result["job_id"] == job_id
        assert result["status"] == BatchStatus.PENDING.value
        assert result["total_items"] == 100
        assert result["processed_items"] == 0
        assert result["failed_items"] == 0
        assert result["progress_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, service):
        """Test getting status of a non-existent job."""
        # Call with a non-existent job ID
        result = await service.get_job_status("non_existent_job")

        # Verify the result
        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_job(self, service, sample_batch_job):
        """Test cancelling a batch job."""
        job_id = sample_batch_job.job_id

        # Add job to active jobs
        service.active_jobs[job_id] = sample_batch_job

        # Mock job execution
        with patch.object(service, '_stop_job_execution', return_value=True):
            # Call the method
            result = await service.cancel_job(job_id)

            # Verify the result
            assert result is True
            assert service.active_jobs[job_id].status == BatchStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_job_not_found(self, service):
        """Test cancelling a non-existent job."""
        # Call with a non-existent job ID
        result = await service.cancel_job("non_existent_job")

        # Verify the result
        assert result is False

    @pytest.mark.asyncio
    async def test_get_job_progress(self, service, sample_batch_job, sample_batch_progress):
        """Test getting the progress of a batch job."""
        job_id = sample_batch_job.job_id

        # Add job to active jobs
        service.active_jobs[job_id] = sample_batch_job

        # Mock progress calculation
        with patch.object(service, '_calculate_progress', return_value=sample_batch_progress):
            # Call the method
            result = await service.get_job_progress(job_id)

            # Verify the result
            assert result is not None
            assert result["job_id"] == job_id
            assert result["total_items"] == 100
            assert result["processed_items"] == 50
            assert result["failed_items"] == 5
            assert result["progress_percentage"] == 50.0
            assert result["estimated_remaining_seconds"] == 120.0
            assert result["processing_rate_items_per_second"] == 5.0

    @pytest.mark.asyncio
    async def test_get_job_result(self, service, sample_batch_job, sample_batch_result):
        """Test getting the result of a completed batch job."""
        job_id = sample_batch_job.job_id

        # Set job to completed status
        sample_batch_job.status = BatchStatus.COMPLETED
        sample_batch_job.result = {
            "success": True,
            "total_items": 100,
            "processed_items": 95,
            "failed_items": 5,
            "processing_time_seconds": 180.0
        }

        # Add job to active jobs
        service.active_jobs[job_id] = sample_batch_job

        # Call the method
        result = await service.get_job_result(job_id)

        # Verify the result
        assert result is not None
        assert result["success"] is True
        assert result["total_items"] == 100
        assert result["processed_items"] == 95
        assert result["failed_items"] == 5
        assert result["processing_time_seconds"] == 180.0

    @pytest.mark.asyncio
    async def test_get_job_result_not_completed(self, service, sample_batch_job):
        """Test getting result of a job that hasn't completed."""
        job_id = sample_batch_job.job_id

        # Add job to active jobs (still in PENDING status)
        service.active_jobs[job_id] = sample_batch_job

        # Call the method
        result = await service.get_job_result(job_id)

        # Verify the result
        assert result is None

    @pytest.mark.asyncio
    async def test_get_active_jobs(self, service):
        """Test getting all active jobs."""
        # Create multiple jobs
        job1 = BatchJob(
            job_id=str(uuid.uuid4()),
            operation_type=BatchOperationType.IMPORT_NODES,
            status=BatchStatus.RUNNING,
            created_at=datetime.utcnow()
        )

        job2 = BatchJob(
            job_id=str(uuid.uuid4()),
            operation_type=BatchOperationType.EXPORT_GRAPH,
            status=BatchStatus.PENDING,
            created_at=datetime.utcnow()
        )

        # Add jobs to active jobs
        service.active_jobs[job1.job_id] = job1
        service.active_jobs[job2.job_id] = job2

        # Call the method
        result = await service.get_active_jobs()

        # Verify the result
        assert result is not None
        assert len(result) == 2
        job_ids = [job["job_id"] for job in result]
        assert job1.job_id in job_ids
        assert job2.job_id in job_ids

    @pytest.mark.asyncio
    async def test_get_job_history(self, service):
        """Test getting job history."""
        # Create completed jobs
        completed_job1 = BatchJob(
            job_id=str(uuid.uuid4()),
            operation_type=BatchOperationType.IMPORT_NODES,
            status=BatchStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(hours=2),
            completed_at=datetime.utcnow() - timedelta(hours=1)
        )

        completed_job2 = BatchJob(
            job_id=str(uuid.uuid4()),
            operation_type=BatchOperationType.IMPORT_RELATIONSHIPS,
            status=BatchStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(hours=4),
            completed_at=datetime.utcnow() - timedelta(hours=3)
        )

        # Add jobs to history
        service.job_history = [completed_job1, completed_job2]

        # Call the method
        result = await service.get_job_history(limit=10)

        # Verify the result
        assert result is not None
        assert len(result) == 2
        job_ids = [job["job_id"] for job in result]
        assert completed_job1.job_id in job_ids
        assert completed_job2.job_id in job_ids

        # Check ordering (most recent first)
        assert result[0]["job_id"] == completed_job1.job_id
        assert result[1]["job_id"] == completed_job2.job_id

    @pytest.mark.asyncio
    async def test_execute_batch_job_sequential(self, service, sample_batch_job):
        """Test executing a batch job in sequential mode."""
        job_id = sample_batch_job.job_id
        sample_batch_job.processing_mode = ProcessingMode.SEQUENTIAL

        # Add job to active jobs
        service.active_jobs[job_id] = sample_batch_job

        # Mock the execution process
        with patch.object(service, '_process_job_sequential', return_value=True):
            with patch.object(service, '_update_job_progress') as mock_update:
                # Call the method
                result = await service.execute_batch_job(job_id)

                # Verify the result
                assert result is True
                mock_update.assert_called()

                # Verify job status is updated
                assert service.active_jobs[job_id].status == BatchStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_batch_job_parallel(self, service, sample_batch_job):
        """Test executing a batch job in parallel mode."""
        job_id = sample_batch_job.job_id
        sample_batch_job.processing_mode = ProcessingMode.PARALLEL

        # Add job to active jobs
        service.active_jobs[job_id] = sample_batch_job

        # Mock the execution process
        with patch.object(service, '_process_job_parallel', return_value=True):
            with patch.object(service, '_update_job_progress') as mock_update:
                # Call the method
                result = await service.execute_batch_job(job_id)

                # Verify the result
                assert result is True
                mock_update.assert_called()

                # Verify job status is updated
                assert service.active_jobs[job_id].status == BatchStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_batch_job_chunked(self, service, sample_batch_job):
        """Test executing a batch job in chunked mode."""
        job_id = sample_batch_job.job_id
        sample_batch_job.processing_mode = ProcessingMode.CHUNKED

        # Add job to active jobs
        service.active_jobs[job_id] = sample_batch_job

        # Mock the execution process
        with patch.object(service, '_process_job_chunked', return_value=True):
            with patch.object(service, '_update_job_progress') as mock_update:
                # Call the method
                result = await service.execute_batch_job(job_id)

                # Verify the result
                assert result is True
                mock_update.assert_called()

                # Verify job status is updated
                assert service.active_jobs[job_id].status == BatchStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_calculate_progress(self, service, sample_batch_job):
        """Test calculating job progress."""
        # Update job with some progress
        sample_batch_job.processed_items = 45
        sample_batch_job.failed_items = 5
        sample_batch_job.started_at = datetime.utcnow() - timedelta(minutes=5)

        job_id = sample_batch_job.job_id

        # Call the method
        result = service._calculate_progress(job_id)

        # Verify the result
        assert result is not None
        assert result.job_id == job_id
        assert result.total_items == 100
        assert result.processed_items == 45
        assert result.failed_items == 5
        assert result.progress_percentage == 50.0  # (45+5)/100 * 100
        assert result.processing_rate_items_per_second > 0

    @pytest.mark.asyncio
    async def test_estimate_completion_time(self, service, sample_batch_job):
        """Test estimating job completion time."""
        # Update job with some progress
        sample_batch_job.processed_items = 45
        sample_batch_job.failed_items = 5
        sample_batch_job.started_at = datetime.utcnow() - timedelta(minutes=5)

        job_id = sample_batch_job.job_id

        # Mock progress calculation
        with patch.object(service, '_calculate_progress') as mock_progress:
            mock_progress.return_value = BatchProgress(
                job_id=job_id,
                total_items=100,
                processed_items=45,
                failed_items=5,
                current_chunk=5,
                total_chunks=10,
                progress_percentage=50.0,
                estimated_remaining_seconds=120.0,
                processing_rate_items_per_second=5.0,
                last_update=datetime.utcnow()
            )

            # Call the method
            result = service._estimate_completion_time(job_id)

            # Verify the result
            assert result is not None
            assert result["estimated_remaining_seconds"] == 120.0
            assert result["estimated_completion_time"] is not None

    @pytest.mark.asyncio
    async def test_process_job_sequential(self, service, sample_batch_job):
        """Test processing a job in sequential mode."""
        job_id = sample_batch_job.job_id

        # Mock the item processing
        with patch.object(service, '_process_item', return_value=True):
            with patch.object(service, '_update_job_progress'):
                # Call the method
                result = await service._process_job_sequential(job_id)

                # Verify the result
                assert result is True

    @pytest.mark.asyncio
    async def test_process_job_parallel(self, service, sample_batch_job):
        """Test processing a job in parallel mode."""
        job_id = sample_batch_job.job_id

        # Mock the item processing
        with patch.object(service, '_process_item', return_value=True):
            with patch.object(service, '_update_job_progress'):
                # Call the method
                result = await service._process_job_parallel(job_id)

                # Verify the result
                assert result is True

    @pytest.mark.asyncio
    async def test_process_job_chunked(self, service, sample_batch_job):
        """Test processing a job in chunked mode."""
        job_id = sample_batch_job.job_id

        # Mock the chunk processing
        with patch.object(service, '_process_chunk', return_value=True):
            with patch.object(service, '_update_job_progress'):
                # Call the method
                result = await service._process_job_chunked(job_id)

                # Verify the result
                assert result is True

    @pytest.mark.asyncio
    async def test_retry_failed_items(self, service, sample_batch_job):
        """Test retrying failed items in a batch job."""
        job_id = sample_batch_job.job_id

        # Set some failed items
        failed_items = [
            {"item_id": "item_10", "error": "Invalid data format"},
            {"item_id": "item_25", "error": "Missing required field"}
        ]

        # Mock item processing
        with patch.object(service, '_process_item', return_value=True):
            # Call the method
            result = await service.retry_failed_items(job_id, failed_items)

            # Verify the result
            assert result is not None
            assert "success_count" in result
            assert "failed_count" in result
            assert "results" in result

    @pytest.mark.asyncio
    async def test_get_batch_statistics(self, service):
        """Test getting batch processing statistics."""
        # Create some jobs with different statuses
        running_job = BatchJob(
            job_id=str(uuid.uuid4()),
            operation_type=BatchOperationType.IMPORT_NODES,
            status=BatchStatus.RUNNING,
            created_at=datetime.utcnow() - timedelta(minutes=10)
        )

        completed_job = BatchJob(
            job_id=str(uuid.uuid4()),
            operation_type=BatchOperationType.IMPORT_RELATIONSHIPS,
            status=BatchStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(hours=2),
            completed_at=datetime.utcnow() - timedelta(hours=1),
            total_items=100,
            processed_items=95,
            failed_items=5
        )

        failed_job = BatchJob(
            job_id=str(uuid.uuid4()),
            operation_type=BatchOperationType.EXPORT_GRAPH,
            status=BatchStatus.FAILED,
            created_at=datetime.utcnow() - timedelta(hours=3),
            completed_at=datetime.utcnow() - timedelta(hours=2),
            total_items=50,
            processed_items=25,
            failed_items=25
        )

        # Add jobs to active and history
        service.active_jobs[running_job.job_id] = running_job
        service.job_history = [completed_job, failed_job]

        # Call the method
        result = await service.get_batch_statistics()

        # Verify the result
        assert result is not None
        assert "active_jobs" in result
        assert "completed_jobs" in result
        assert "failed_jobs" in result
        assert "total_jobs" in result
        assert "success_rate" in result

        assert result["active_jobs"] == 1
        assert result["completed_jobs"] == 1
        assert result["failed_jobs"] == 1
        assert result["total_jobs"] == 3
        assert result["success_rate"] == 0.5  # 1 success / 2 completed jobs

    @pytest.mark.asyncio
    async def test_cleanup_completed_jobs(self, service):
        """Test cleaning up completed jobs."""
        # Create some completed jobs
        old_completed_job = BatchJob(
            job_id=str(uuid.uuid4()),
            operation_type=BatchOperationType.IMPORT_NODES,
            status=BatchStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=2),
            completed_at=datetime.utcnow() - timedelta(days=1)
        )

        recent_completed_job = BatchJob(
            job_id=str(uuid.uuid4()),
            operation_type=BatchOperationType.IMPORT_RELATIONSHIPS,
            status=BatchStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(hours=1),
            completed_at=datetime.utcnow() - timedelta(minutes=30)
        )

        # Add jobs to history
        service.job_history = [old_completed_job, recent_completed_job]

        # Call the method to clean up jobs older than 1 day
        result = await service.cleanup_completed_jobs(days_old=1)

        # Verify the result
        assert result is not None
        assert "cleaned_count" in result
        assert result["cleaned_count"] == 1

        # Verify only the recent job remains
        assert len(service.job_history) == 1
        assert service.job_history[0].job_id == recent_completed_job.job_id

    def test_generate_job_report(self, service, sample_batch_job, sample_batch_result):
        """Test generating a report for a batch job."""
        job_id = sample_batch_job.job_id

        # Set job to completed status with result
        sample_batch_job.status = BatchStatus.COMPLETED
        sample_batch_job.result = {
            "success": True,
            "total_items": 100,
            "processed_items": 95,
            "failed_items": 5,
            "processing_time_seconds": 180.0
        }

        # Generate the report
        result = service.generate_job_report(job_id)

        # Verify the report
        assert result is not None
        assert "job_id" in result
        assert "summary" in result
        assert "details" in result
        assert "metrics" in result

        assert result["job_id"] == job_id
        assert result["summary"]["status"] == BatchStatus.COMPLETED.value
        assert result["summary"]["success"] is True
        assert result["metrics"]["success_rate"] == 0.95  # 95/100
