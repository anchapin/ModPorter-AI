import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from src.db import crud
from src.db.models import ConversionJob, ConversionFeedback


@pytest_asyncio.fixture
async def test_conversion_job(db_session: AsyncSession) -> ConversionJob:
    """Fixture to create a sample ConversionJob for feedback tests."""
    # Use the existing crud.create_job function
    # Ensure input_data has file_id and original_filename as get_training_data endpoint might use it
    job_input_data = {
        "file_id": str(uuid.uuid4()),
        "original_filename": "test_mod.zip",
        "target_version": "1.20.0",
        "options": {},
    }
    job = ConversionJob(
        status="completed", # Or any status, doesn't matter much for feedback itself
        input_data=job_input_data
    )
    job.progress = crud.models.JobProgress(progress=100) # Assuming progress is part of job creation or can be added

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job

@pytest.mark.asyncio
async def test_create_feedback(db_session: AsyncSession, test_conversion_job: ConversionJob):
    """Test creating a feedback entry."""
    job_id = test_conversion_job.id
    feedback_type = "thumbs_up"
    comment = "Great conversion!"
    user_id = "user123"

    feedback = await crud.create_feedback(
        db=db_session,
        job_id=job_id,
        feedback_type=feedback_type,
        comment=comment,
        user_id=user_id,
    )

    assert feedback is not None
    assert feedback.id is not None
    assert feedback.job_id == job_id
    assert feedback.feedback_type == feedback_type
    assert feedback.comment == comment
    assert feedback.user_id == user_id
    assert feedback.created_at is not None

    # Verify it's in the DB
    fetched_feedback = await db_session.get(ConversionFeedback, feedback.id)
    assert fetched_feedback is not None
    assert fetched_feedback.comment == comment


@pytest.mark.asyncio
async def test_get_feedback_by_job_id(db_session: AsyncSession, test_conversion_job: ConversionJob):
    """Test retrieving feedback by job_id."""
    job_id = test_conversion_job.id

    feedback1 = await crud.create_feedback(
        db=db_session, job_id=job_id, feedback_type="thumbs_up", comment="Excellent"
    )
    feedback2 = await crud.create_feedback(
        db=db_session, job_id=job_id, feedback_type="thumbs_down", comment="Could be better"
    )

    # Create feedback for another job to ensure filtering works
    other_job_input_data = {
        "file_id": str(uuid.uuid4()), "original_filename": "other_mod.zip", "target_version": "1.19"
    }
    other_job = ConversionJob(status="completed", input_data=other_job_input_data)
    other_job.progress = crud.models.JobProgress(progress=100)
    db_session.add(other_job)
    await db_session.commit()
    await crud.create_feedback(db=db_session, job_id=other_job.id, feedback_type="thumbs_up")

    feedbacks = await crud.get_feedback_by_job_id(db=db_session, job_id=job_id)

    assert feedbacks is not None
    assert len(feedbacks) == 2
    feedback_comments = {f.comment for f in feedbacks}
    assert "Excellent" in feedback_comments
    assert "Could be better" in feedback_comments

    # Check that the feedback items are correctly ordered (newest first by default in crud)
    assert feedbacks[0].created_at >= feedbacks[1].created_at


@pytest.mark.asyncio
async def test_list_all_feedback(db_session: AsyncSession, test_conversion_job: ConversionJob):
    """Test listing all feedback entries with pagination."""
    job1_id = test_conversion_job.id

    other_job_input_data = {
        "file_id": str(uuid.uuid4()), "original_filename": "another_mod.zip", "target_version": "1.18"
    }
    job2 = ConversionJob(status="completed", input_data=other_job_input_data)
    job2.progress = crud.models.JobProgress(progress=100)
    db_session.add(job2)
    await db_session.commit()
    job2_id = job2.id

    fb1 = await crud.create_feedback(db=db_session, job_id=job1_id, feedback_type="thumbs_up", comment="Job1 Feedback1")
    await asyncio.sleep(0.01) # ensure different timestamps for ordering
    fb2 = await crud.create_feedback(db=db_session, job_id=job2_id, feedback_type="thumbs_down", comment="Job2 Feedback1")
    await asyncio.sleep(0.01)
    fb3 = await crud.create_feedback(db=db_session, job_id=job1_id, feedback_type="thumbs_up", comment="Job1 Feedback2")
    await asyncio.sleep(0.01)
    fb4 = await crud.create_feedback(db=db_session, job_id=job2_id, feedback_type="thumbs_up", comment="Job2 Feedback2")

    all_feedback_ids_desc = [fb4.id, fb3.id, fb2.id, fb1.id] # Newest first

    # Test listing all
    feedbacks_all = await crud.list_all_feedback(db=db_session, skip=0, limit=10)
    assert len(feedbacks_all) == 4
    assert [f.id for f in feedbacks_all] == all_feedback_ids_desc

    # Test pagination: skip 1, limit 2
    feedbacks_paginated = await crud.list_all_feedback(db=db_session, skip=1, limit=2)
    assert len(feedbacks_paginated) == 2
    assert [f.id for f in feedbacks_paginated] == [all_feedback_ids_desc[1], all_feedback_ids_desc[2]] # fb3, fb2

    # Test pagination: skip enough to get none
    feedbacks_empty = await crud.list_all_feedback(db=db_session, skip=4, limit=10)
    assert len(feedbacks_empty) == 0

    # Test limit
    feedbacks_limit_1 = await crud.list_all_feedback(db=db_session, skip=0, limit=1)
    assert len(feedbacks_limit_1) == 1
    assert feedbacks_limit_1[0].id == all_feedback_ids_desc[0] # fb4

    # Test listing with default limit
    # To make this testable, we need to know the default limit in crud.list_all_feedback (assume 100)
    # For this test, we have 4 items, so default limit of 100 should return all.
    feedbacks_default_limit = await crud.list_all_feedback(db=db_session) # skip=0, limit=100
    assert len(feedbacks_default_limit) == 4
    assert [f.id for f in feedbacks_default_limit] == all_feedback_ids_desc

    # Test order (created_at desc by default)
    assert feedbacks_all[0].created_at >= feedbacks_all[1].created_at
    assert feedbacks_all[1].created_at >= feedbacks_all[2].created_at
    assert feedbacks_all[2].created_at >= feedbacks_all[3].created_at

# Need to import asyncio for sleep
import asyncio
