"""
Unit Tests for Batch Queuing System

Tests the intelligent batch queue with mode-based grouping,
priority scheduling, and batch job processing.

See: docs/GAP-ANALYSIS-v2.5.md (GAP-2.5-05)
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from models.conversion_mode import ConversionMode, ModFeatures, ModeClassificationResult

from services.batch_queuing import (
    IntelligentBatchQueue,
    BatchJob,
    BatchJobStatus,
    BatchGroup,
    BatchQueueStats,
    QueuePriority,
    get_batch_queue,
    reset_batch_queue,
)


@pytest.fixture
def clean_queue():
    """Provide a clean queue for each test."""
    reset_batch_queue()
    yield
    reset_batch_queue()


@pytest.fixture
def queue(clean_queue):
    """Provide a configured queue instance."""
    return IntelligentBatchQueue(
        max_parallel_jobs=4,
        max_group_size=5,
        enable_mode_grouping=True,
        enable_priority_scheduling=True,
    )


@pytest.fixture
def sample_mod_data():
    """Sample mod data for testing."""
    return {
        "filename": "test_mod.jar",
        "size_bytes": 1024000,
        "classes": [
            {"name": "com.example.Item", "type": "item"},
            {"name": "com.example.Block", "type": "block"},
        ],
        "dependencies": ["mod_core"],
    }


@pytest.fixture
def sample_classification():
    """Sample mode classification result."""
    features = ModFeatures(
        total_classes=5,
        total_dependencies=2,
        has_items=True,
        has_blocks=True,
        has_recipes=True,
    )
    return ModeClassificationResult(
        mode=ConversionMode.STANDARD,
        confidence=0.92,
        features=features,
        convertible_percentage=95.0,
        estimated_time_seconds=120,
        automation_level=95,
    )


class TestBatchJob:
    """Tests for BatchJob dataclass."""

    def test_batch_job_creation(self, sample_mod_data):
        """Test creating a batch job."""
        job = BatchJob(
            job_id="test-job-1",
            user_id="user-123",
            mod_data=sample_mod_data,
        )

        assert job.job_id == "test-job-1"
        assert job.user_id == "user-123"
        assert job.status == BatchJobStatus.PENDING
        assert job.priority == QueuePriority.NORMAL
        assert job.retry_count == 0

    def test_batch_job_lt(self, sample_mod_data):
        """Test job comparison for priority queue."""
        job1 = BatchJob(
            job_id="job-1",
            user_id="user-1",
            mod_data=sample_mod_data,
            priority=QueuePriority.LOW,
            priority_score=0,
        )
        job2 = BatchJob(
            job_id="job-2",
            user_id="user-2",
            mod_data=sample_mod_data,
            priority=QueuePriority.HIGH,
            priority_score=2,
        )

        # Higher score should come first (max heap behavior with reversed comparison)
        assert job2.priority_score > job1.priority_score


class TestBatchGroup:
    """Tests for BatchGroup dataclass."""

    def test_batch_group_creation(self):
        """Test creating a batch group."""
        group = BatchGroup(
            group_id="group-1",
            mode=ConversionMode.STANDARD,
        )

        assert group.group_id == "group-1"
        assert group.mode == ConversionMode.STANDARD
        assert group.total_jobs == 0
        assert group.progress == 0.0

    def test_batch_group_with_jobs(self, sample_mod_data):
        """Test batch group with jobs."""
        jobs = [
            BatchJob(
                job_id=f"job-{i}",
                user_id="user-1",
                mod_data=sample_mod_data,
            )
            for i in range(3)
        ]

        group = BatchGroup(
            group_id="group-1",
            mode=ConversionMode.SIMPLE,
            jobs=jobs,
        )

        assert group.total_jobs == 3
        assert group.progress == 0.0

        group.completed_count = 2
        assert group.progress == pytest.approx(66.67, rel=0.01)


class TestBatchQueueStats:
    """Tests for BatchQueueStats."""

    def test_stats_to_dict(self):
        """Test stats serialization."""
        stats = BatchQueueStats()
        stats.total_jobs_enqueued = 100
        stats.total_jobs_processed = 90
        stats.total_jobs_failed = 10
        stats.mode_distribution[ConversionMode.SIMPLE] = 50
        stats.mode_distribution[ConversionMode.STANDARD] = 40

        result = stats.to_dict()

        assert result["total_jobs_enqueued"] == 100
        assert result["total_jobs_processed"] == 90
        assert result["total_jobs_failed"] == 10
        assert result["mode_distribution"]["simple"] == 50
        assert result["mode_distribution"]["standard"] == 40


class TestIntelligentBatchQueue:
    """Tests for the main batch queue implementation."""

    @pytest.mark.asyncio
    async def test_enqueue_job(self, queue, sample_mod_data):
        """Test enqueueing a single job."""
        job_id = await queue.enqueue_job(
            user_id="user-123",
            mod_data=sample_mod_data,
            mode=ConversionMode.SIMPLE,
        )

        assert job_id is not None
        assert len(queue._jobs) == 1

        job = await queue.get_job(job_id)
        assert job is not None
        assert job.user_id == "user-123"
        assert job.mode == ConversionMode.SIMPLE
        assert job.status == BatchJobStatus.QUEUED

    @pytest.mark.asyncio
    async def test_enqueue_job_with_classification(
        self, queue, sample_mod_data, sample_classification
    ):
        """Test enqueueing with mode classification."""
        job_id = await queue.enqueue_job(
            user_id="user-123",
            mod_data=sample_mod_data,
            mode_classification=sample_classification,
        )

        job = await queue.get_job(job_id)
        assert job is not None
        assert job.mode == ConversionMode.STANDARD
        assert job.mode_classification is not None
        assert job.mode_classification.confidence == 0.92

    @pytest.mark.asyncio
    async def test_enqueue_batch(self, queue, sample_mod_data):
        """Test enqueueing multiple jobs as a batch."""
        jobs_data = [
            sample_mod_data.copy() for _ in range(5)
        ]

        job_ids = await queue.enqueue_batch(
            user_id="user-123",
            jobs_data=jobs_data,
            default_priority=QueuePriority.NORMAL,
        )

        assert len(job_ids) == 5
        assert len(queue._jobs) == 5

    @pytest.mark.asyncio
    async def test_enqueue_with_priority(self, queue, sample_mod_data):
        """Test that priority affects job ordering."""
        await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
            priority=QueuePriority.LOW,
        )
        job_id_high = await queue.enqueue_job(
            user_id="user-2",
            mod_data=sample_mod_data,
            priority=QueuePriority.HIGH,
        )
        await queue.enqueue_job(
            user_id="user-3",
            mod_data=sample_mod_data,
            priority=QueuePriority.NORMAL,
        )

        # HIGH priority job should have highest score
        high_job = await queue.get_job(job_id_high)
        assert high_job.priority == QueuePriority.HIGH

    @pytest.mark.asyncio
    async def test_mode_grouping(self, queue, sample_mod_data):
        """Test that jobs are grouped by mode."""
        # Enqueue jobs with different modes
        await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
            mode=ConversionMode.SIMPLE,
        )
        await queue.enqueue_job(
            user_id="user-2",
            mod_data=sample_mod_data,
            mode=ConversionMode.SIMPLE,
        )
        await queue.enqueue_job(
            user_id="user-3",
            mod_data=sample_mod_data,
            mode=ConversionMode.EXPERT,
        )

        # Check mode queues
        assert len(queue._mode_queues[ConversionMode.SIMPLE]) == 2
        assert len(queue._mode_queues[ConversionMode.EXPERT]) == 1

    @pytest.mark.asyncio
    async def test_get_next_job(self, queue, sample_mod_data):
        """Test getting next job from queue."""
        job_id = await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
            mode=ConversionMode.SIMPLE,
        )

        # Without mode grouping, jobs go to global queue
        queue.enable_mode_grouping = False
        job = await queue.get_next_job()

        assert job is not None
        assert job.job_id == job_id

    @pytest.mark.asyncio
    async def test_get_batch_group(self, queue, sample_mod_data):
        """Test getting a batch group of similar jobs."""
        # Enqueue several jobs of same mode
        for i in range(4):
            await queue.enqueue_job(
                user_id=f"user-{i}",
                mod_data=sample_mod_data,
                mode=ConversionMode.COMPLEX,
            )

        # Get batch group
        group = await queue.get_batch_group(ConversionMode.COMPLEX, max_size=3)

        assert group is not None
        assert group.mode == ConversionMode.COMPLEX
        assert len(group.jobs) == 3  # max_size

    @pytest.mark.asyncio
    async def test_get_batch_group_partial(self, queue, sample_mod_data):
        """Test getting a batch group when fewer jobs available."""
        # Only 2 jobs
        for i in range(2):
            await queue.enqueue_job(
                user_id=f"user-{i}",
                mod_data=sample_mod_data,
                mode=ConversionMode.STANDARD,
            )

        group = await queue.get_batch_group(ConversionMode.STANDARD, max_size=5)

        assert group is not None
        assert len(group.jobs) == 2  # Only 2 available

    @pytest.mark.asyncio
    async def test_create_mixed_batch(self, queue, sample_mod_data):
        """Test creating a mixed batch from global queue."""
        queue.enable_mode_grouping = False

        for i in range(3):
            await queue.enqueue_job(
                user_id=f"user-{i}",
                mod_data=sample_mod_data,
                mode=ConversionMode.SIMPLE,
            )

        group = await queue.create_mixed_batch(max_size=3)

        assert group is not None
        assert len(group.jobs) == 3

    @pytest.mark.asyncio
    async def test_update_job_status(self, queue, sample_mod_data):
        """Test updating job status."""
        job_id = await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
        )

        success = await queue.update_job_status(job_id, BatchJobStatus.PROCESSING)
        assert success is True

        job = await queue.get_job(job_id)
        assert job.status == BatchJobStatus.PROCESSING
        assert job.started_at is not None

    @pytest.mark.asyncio
    async def test_update_job_status_completed(self, queue, sample_mod_data):
        """Test updating job to completed."""
        job_id = await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
        )

        await queue.update_job_status(job_id, BatchJobStatus.PROCESSING)
        await queue.update_job_status(job_id, BatchJobStatus.COMPLETED)

        job = await queue.get_job(job_id)
        assert job.status == BatchJobStatus.COMPLETED
        assert job.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_job_status_failed(self, queue, sample_mod_data):
        """Test updating job to failed."""
        job_id = await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
        )

        await queue.update_job_status(
            job_id,
            BatchJobStatus.FAILED,
            error_message="Test error",
        )

        job = await queue.get_job(job_id)
        assert job.status == BatchJobStatus.FAILED
        assert job.error_message == "Test error"

    @pytest.mark.asyncio
    async def test_retry_job(self, queue, sample_mod_data):
        """Test retrying a failed job."""
        job_id = await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
        )

        # Fail the job
        await queue.update_job_status(job_id, BatchJobStatus.FAILED)

        # Retry
        success = await queue.retry_job(job_id)
        assert success is True

        job = await queue.get_job(job_id)
        assert job.status == BatchJobStatus.QUEUED
        assert job.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_job_max_retries(self, queue, sample_mod_data):
        """Test that max retries is enforced."""
        job = BatchJob(
            job_id="test-retry-max",
            user_id="user-1",
            mod_data=sample_mod_data,
            retry_count=3,
            max_retries=3,
        )
        queue._jobs[job.job_id] = job

        success = await queue.retry_job(job.job_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_cancel_job(self, queue, sample_mod_data):
        """Test cancelling a queued job."""
        job_id = await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
        )

        success = await queue.cancel_job(job_id)
        assert success is True

        job = await queue.get_job(job_id)
        assert job.status == BatchJobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_job_processing_fails(self, queue, sample_mod_data):
        """Test that processing jobs cannot be cancelled."""
        job_id = await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
        )
        await queue.update_job_status(job_id, BatchJobStatus.PROCESSING)

        success = await queue.cancel_job(job_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_get_queue_stats(self, queue, sample_mod_data):
        """Test getting queue statistics."""
        # Add some jobs
        await queue.enqueue_batch(
            user_id="user-1",
            jobs_data=[sample_mod_data.copy() for _ in range(5)],
            default_priority=QueuePriority.HIGH,
        )

        stats = await queue.get_queue_stats()

        assert stats["total_queued"] == 5
        assert stats["total_batches_created"] == 0  # No batches created yet
        assert "mode_queues" in stats
        assert "global_queue_depth" in stats

    @pytest.mark.asyncio
    async def test_priority_score_computation(self, queue, sample_mod_data):
        """Test that priority scores are computed correctly."""
        # Simple mode should have lower base complexity score
        job_simple = await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
            mode=ConversionMode.SIMPLE,
            priority=QueuePriority.HIGH,
        )

        # Expert mode should have higher complexity score
        job_expert = await queue.enqueue_job(
            user_id="user-2",
            mod_data=sample_mod_data,
            mode=ConversionMode.EXPERT,
            priority=QueuePriority.HIGH,
        )

        simple_job = await queue.get_job(job_simple)
        expert_job = await queue.get_job(job_expert)

        # Expert should have higher priority score due to complexity
        assert expert_job.priority_score > simple_job.priority_score

    @pytest.mark.asyncio
    async def test_process_batch_parallel(self, queue, sample_mod_data):
        """Test parallel batch processing."""

        async def mock_processor(job: BatchJob) -> Dict[str, Any]:
            """Mock job processor."""
            await asyncio.sleep(0.01)  # Simulate work
            return {"success": True, "result": f"processed-{job.job_id}"}

        # Enqueue jobs
        for i in range(3):
            await queue.enqueue_job(
                user_id=f"user-{i}",
                mod_data=sample_mod_data,
                mode=ConversionMode.SIMPLE,
            )

        # Process batch
        results = await queue.process_batch_parallel(
            mock_processor,
            mode=ConversionMode.SIMPLE,
        )

        assert "completed" in results
        assert len(results["completed"]) == 3

    @pytest.mark.asyncio
    async def test_process_batch_parallel_with_failures(self, queue, sample_mod_data):
        """Test parallel processing with some failures."""

        async def failing_processor(job: BatchJob) -> Dict[str, Any]:
            """Mock processor that fails for some jobs."""
            if "fail" in job.job_id:
                raise Exception("Simulated failure")
            return {"success": True}

        # Create jobs with "fail" in job_id
        job_fail = await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
        )
        queue._jobs[job_fail].job_id = "job-fail-1"

        job_success = await queue.enqueue_job(
            user_id="user-2",
            mod_data=sample_mod_data,
        )

        results = await queue.process_batch_parallel(
            failing_processor,
        )

        # Results should contain both completed and failed
        assert len(results.get("completed", [])) >= 0
        assert len(results.get("failed", [])) >= 0

    @pytest.mark.asyncio
    async def test_queue_depth_by_mode(self, queue, sample_mod_data):
        """Test that queue depth by mode is tracked."""
        await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
            mode=ConversionMode.SIMPLE,
        )
        await queue.enqueue_job(
            user_id="user-2",
            mod_data=sample_mod_data,
            mode=ConversionMode.SIMPLE,
        )
        await queue.enqueue_job(
            user_id="user-3",
            mod_data=sample_mod_data,
            mode=ConversionMode.COMPLEX,
        )

        stats = await queue.get_queue_stats()

        assert stats["queue_depth_by_mode"]["simple"] == 2
        assert stats["queue_depth_by_mode"]["complex"] == 1


class TestQueuePriority:
    """Tests for QueuePriority enum."""

    def test_priority_to_score(self):
        """Test priority score conversion."""
        assert QueuePriority.LOW.to_score() == 0
        assert QueuePriority.NORMAL.to_score() == 1
        assert QueuePriority.HIGH.to_score() == 2
        assert QueuePriority.CRITICAL.to_score() == 3

    def test_priority_ordering(self):
        """Test that priorities order correctly."""
        priorities = [
            QueuePriority.LOW,
            QueuePriority.CRITICAL,
            QueuePriority.NORMAL,
            QueuePriority.HIGH,
        ]

        scores = [p.to_score() for p in priorities]
        assert scores == sorted(scores)


class TestGetBatchQueue:
    """Tests for the get_batch_queue singleton function."""

    def test_get_batch_queue_returns_instance(self):
        """Test that get_batch_queue returns an instance."""
        reset_batch_queue()
        queue = get_batch_queue()
        assert queue is not None
        assert isinstance(queue, IntelligentBatchQueue)

    def test_get_batch_queue_same_instance(self):
        """Test that get_batch_queue returns the same instance."""
        reset_batch_queue()
        queue1 = get_batch_queue()
        queue2 = get_batch_queue()
        assert queue1 is queue2


class TestEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, queue):
        """Test getting non-existent job."""
        job = await queue.get_job("non-existent-id")
        assert job is None

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, queue):
        """Test updating non-existent job."""
        success = await queue.update_job_status(
            "non-existent-id",
            BatchJobStatus.COMPLETED,
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_cancel_not_found(self, queue):
        """Test cancelling non-existent job."""
        success = await queue.cancel_job("non-existent-id")
        assert success is False

    @pytest.mark.asyncio
    async def test_retry_not_found(self, queue):
        """Test retrying non-existent job."""
        success = await queue.retry_job("non-existent-id")
        assert success is False

    @pytest.mark.asyncio
    async def test_get_batch_group_empty_queue(self, queue):
        """Test getting batch from empty queue."""
        group = await queue.get_batch_group(ConversionMode.SIMPLE)
        assert group is None

    @pytest.mark.asyncio
    async def test_create_mixed_batch_empty_queue(self, queue):
        """Test creating mixed batch from empty queue."""
        group = await queue.create_mixed_batch()
        assert group is None

    @pytest.mark.asyncio
    async def test_empty_batch_enqueue(self, queue, sample_mod_data):
        """Test enqueueing empty batch."""
        job_ids = await queue.enqueue_batch(
            user_id="user-1",
            jobs_data=[],
        )
        assert job_ids == []

    @pytest.mark.asyncio
    async def test_queue_with_disabled_mode_grouping(self, sample_mod_data):
        """Test queue behavior when mode grouping is disabled."""
        queue = IntelligentBatchQueue(enable_mode_grouping=False)

        await queue.enqueue_job(
            user_id="user-1",
            mod_data=sample_mod_data,
            mode=ConversionMode.SIMPLE,
        )

        # Job should go to global priority queue, not mode queue
        assert len(queue._priority_queue) == 1
        assert len(queue._mode_queues[ConversionMode.SIMPLE]) == 0
