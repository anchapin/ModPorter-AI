"""
Real-service integration tests for PostgreSQL database operations.

These tests verify ACTUAL database behavior against PostgreSQL,
testing the full conversion pipeline, CRUD operations, and
database constraints that can't be tested with SQLite mocks.

To run: USE_REAL_SERVICES=1 pytest tests/integration/test_real_postgresql_crud.py -v
"""

import pytest
import uuid
from datetime import datetime, timezone


pytestmark = pytest.mark.real_service


class TestRealPostgreSQLConversionJob:
    """Integration tests for conversion job operations with real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_conversion_job(self, real_db_session):
        """Test creating and retrieving a conversion job."""
        from db.models import ConversionJob

        job_id = str(uuid.uuid4())
        input_data = {
            "original_filename": "test_mod.jar",
            "target_version": "1.20.0",
            "file_path": "/tmp/test.jar",
        }

        # Create a conversion job record
        job = ConversionJob(
            id=job_id,
            status="queued",
            input_data=input_data,
        )
        real_db_session.add(job)
        await real_db_session.commit()

        # Retrieve it
        from sqlalchemy import select

        result = await real_db_session.execute(
            select(ConversionJob).where(ConversionJob.id == job_id)
        )
        retrieved = result.scalar_one_or_none()

        assert retrieved is not None
        assert str(retrieved.id) == job_id
        assert retrieved.status == "queued"
        assert retrieved.input_data["original_filename"] == "test_mod.jar"
        assert retrieved.input_data["target_version"] == "1.20.0"

    @pytest.mark.asyncio
    async def test_conversion_job_status_update(self, real_db_session):
        """Test updating conversion job status."""
        from db.models import ConversionJob

        job_id = str(uuid.uuid4())
        job = ConversionJob(
            id=job_id,
            status="queued",
            input_data={"test": "data"},
        )
        real_db_session.add(job)
        await real_db_session.commit()

        # Update status
        job.status = "processing"
        await real_db_session.commit()

        # Verify update
        from sqlalchemy import select

        result = await real_db_session.execute(
            select(ConversionJob).where(ConversionJob.id == job_id)
        )
        retrieved = result.scalar_one_or_none()

        assert retrieved.status == "processing"

    @pytest.mark.asyncio
    async def test_conversion_job_completion(self, real_db_session):
        """Test marking a conversion job as completed."""
        from db.models import ConversionJob

        job_id = str(uuid.uuid4())
        job = ConversionJob(
            id=job_id,
            status="processing",
            input_data={"test": "data"},
        )
        real_db_session.add(job)
        await real_db_session.commit()

        # Mark as completed
        job.status = "completed"
        await real_db_session.commit()

        # Verify
        from sqlalchemy import select

        result = await real_db_session.execute(
            select(ConversionJob).where(ConversionJob.id == job_id)
        )
        retrieved = result.scalar_one_or_none()

        assert retrieved.status == "completed"

    @pytest.mark.asyncio
    async def test_conversion_job_failure_recording(self, real_db_session):
        """Test recording a conversion job failure."""
        from db.models import ConversionJob

        job_id = str(uuid.uuid4())
        job = ConversionJob(
            id=job_id,
            status="processing",
            input_data={"test": "data"},
        )
        real_db_session.add(job)
        await real_db_session.commit()

        # Note: ConversionJob doesn't have error_message field
        # So we store it in input_data or just mark as failed
        job.status = "failed"
        await real_db_session.commit()

        # Verify
        from sqlalchemy import select

        result = await real_db_session.execute(
            select(ConversionJob).where(ConversionJob.id == job_id)
        )
        retrieved = result.scalar_one_or_none()

        assert retrieved.status == "failed"


class TestRealPostgreSQLBatchConversion:
    """Integration tests for batch conversion operations."""

    @pytest.mark.asyncio
    async def test_create_multiple_conversion_jobs(self, real_db_session):
        """Test creating multiple conversion jobs in a batch."""
        from db.models import ConversionJob

        # Create multiple conversion jobs without explicit IDs
        # Let the default generate them
        for i in range(5):
            job = ConversionJob(
                status="queued",
                input_data={"index": i, "test": "data"},
            )
            real_db_session.add(job)

        await real_db_session.commit()

        # Verify all were created
        from sqlalchemy import select, func

        result = await real_db_session.execute(select(func.count(ConversionJob.id)))
        count = result.scalar()
        assert count >= 5

    @pytest.mark.asyncio
    async def test_query_conversion_jobs_by_status(self, real_db_session):
        """Test querying conversion jobs by status."""
        from db.models import ConversionJob

        job_id = str(uuid.uuid4())
        job = ConversionJob(
            id=job_id,
            status="queued",
            input_data={"test": "data"},
        )
        real_db_session.add(job)
        await real_db_session.commit()

        # Query by status
        from sqlalchemy import select

        result = await real_db_session.execute(
            select(ConversionJob).where(ConversionJob.status == "queued")
        )
        jobs = result.scalars().all()

        # Should have at least the one we just created
        queued_ids = [str(j.id) for j in jobs]
        assert job_id in queued_ids


class TestRealPostgreSQLUserFeedback:
    """Integration tests for user feedback with real database."""

    @pytest.mark.asyncio
    async def test_create_feedback(self, real_db_session):
        """Test creating user feedback on a conversion job."""
        from db.models import ConversionFeedback, ConversionJob

        # First create a conversion job
        job_id = str(uuid.uuid4())
        job = ConversionJob(
            id=job_id,
            status="completed",
            input_data={"test": "data"},
        )
        real_db_session.add(job)
        await real_db_session.commit()

        # Create feedback
        feedback_id = str(uuid.uuid4())
        feedback = ConversionFeedback(
            id=feedback_id,
            job_id=job_id,
            feedback_type="thumbs_up",
            comment="Great conversion quality!",
        )
        real_db_session.add(feedback)
        await real_db_session.commit()

        # Verify
        from sqlalchemy import select

        result = await real_db_session.execute(
            select(ConversionFeedback).where(ConversionFeedback.id == feedback_id)
        )
        retrieved = result.scalar_one_or_none()

        assert retrieved is not None
        assert str(retrieved.job_id) == job_id
        assert retrieved.feedback_type == "thumbs_up"


class TestRealPostgreSQLPerformance:
    """Performance-related tests with real PostgreSQL."""

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, real_db_session):
        """Test bulk insert performance for large batches."""
        import time
        from db.models import ConversionJob

        start = time.time()

        # Create 100 conversion jobs without explicit IDs
        for i in range(100):
            job = ConversionJob(
                status="queued",
                input_data={"index": i, "test": "data"},
            )
            real_db_session.add(job)

        await real_db_session.commit()

        elapsed = time.time() - start

        # Should complete in reasonable time (< 5 seconds for 100 inserts)
        assert elapsed < 5.0, f"Bulk insert took {elapsed}s, should be < 5s"
