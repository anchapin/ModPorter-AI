import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ConversionJob, ConversionFeedback, JobProgress # Added JobProgress
from src.main import TEMP_UPLOADS_DIR, CONVERSION_OUTPUTS_DIR # Import constants
from pathlib import Path
import os # For os.path.splitext

# Assume test_client fixture is provided by conftest.py
# Assume db_session fixture for direct DB access is provided by conftest.py

@pytest_asyncio.fixture
async def setup_job_for_feedback(db_session: AsyncSession) -> ConversionJob:
    """Fixture to create a ConversionJob directly in the DB for integration tests."""
    job_input_data = {
        "file_id": str(uuid.uuid4()),
        "original_filename": "integration_test_mod.jar",
        "target_version": "1.20.1",
        "options": {},
    }
    # Create related JobProgress instance
    progress_entry = JobProgress(progress=0)

    job = ConversionJob(
        status="completed", # Or any relevant status
        input_data=job_input_data,
        progress=progress_entry # Associate JobProgress
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job

@pytest.mark.asyncio
async def test_submit_feedback_success(
    test_client: AsyncClient, setup_job_for_feedback: ConversionJob
):
    """Test successful feedback submission."""
    job_id = str(setup_job_for_feedback.id)
    feedback_payload = {
        "job_id": job_id,
        "feedback_type": "thumbs_up",
        "comment": "API test: Excellent!",
        "user_id": "api_user_001",
    }
    response = await test_client.post("/api/v1/feedback", json=feedback_payload)
    assert response.status_code == 200 # Assuming endpoint returns 200 OK

    data = response.json()
    assert data["job_id"] == job_id
    assert data["feedback_type"] == feedback_payload["feedback_type"]
    assert data["comment"] == feedback_payload["comment"]
    assert data["user_id"] == feedback_payload["user_id"]
    assert "id" in data
    assert "created_at" in data

@pytest.mark.asyncio
async def test_submit_feedback_invalid_job_id(test_client: AsyncClient):
    """Test feedback submission with a non-existent job_id."""
    invalid_job_id = str(uuid.uuid4())
    feedback_payload = {
        "job_id": invalid_job_id,
        "feedback_type": "thumbs_down",
        "comment": "This job does not exist.",
    }
    response = await test_client.post("/api/v1/feedback", json=feedback_payload)
    # This relies on the foreign key constraint in DB leading to an error
    # that the endpoint handler converts to 404.
    assert response.status_code == 404
    assert f"Conversion job with ID '{invalid_job_id}' not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_feedback_missing_fields(test_client: AsyncClient):
    """Test feedback submission with missing required fields."""
    # Missing feedback_type
    feedback_payload = {
        "job_id": str(uuid.uuid4()), # job_id doesn't need to exist for this validation error
        "comment": "Missing type.",
    }
    response = await test_client.post("/api/v1/feedback", json=feedback_payload)
    assert response.status_code == 422 # Unprocessable Entity for Pydantic validation

    data = response.json()
    assert any(err["type"] == "missing" and err["loc"] == ["body", "feedback_type"] for err in data["detail"])

# --- Tests for GET /api/v1/ai/training_data ---

@pytest.mark.asyncio
async def test_get_training_data_empty(test_client: AsyncClient, db_session: AsyncSession):
    """Test fetching training data when no feedback exists."""
    # Ensure no feedback data
    await db_session.execute(ConversionFeedback.__table__.delete())
    await db_session.commit()

    response = await test_client.get("/api/v1/ai/training_data")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["total"] == -1 # Current placeholder for total
    assert data["limit"] == 100 # Default limit
    assert data["skip"] == 0   # Default skip

@pytest.mark.asyncio
async def test_get_training_data_with_items(
    test_client: AsyncClient, db_session: AsyncSession, setup_job_for_feedback: ConversionJob
):
    """Test fetching training data with existing feedback."""
    job = setup_job_for_feedback # Re-use the job
    job_id_str = str(job.id)

    # Submit some feedback via API to ensure it's created correctly
    feedback_payload1 = {
        "job_id": job_id_str, "feedback_type": "thumbs_up", "comment": "Training data item 1"
    }
    await test_client.post("/api/v1/feedback", json=feedback_payload1)

    # Create another job and feedback for more variety
    other_job_input_data = {
        "file_id": str(uuid.uuid4()), "original_filename": "training_mod2.zip", "target_version": "1.19"
    }
    other_progress = JobProgress(progress=100)
    other_job = ConversionJob(status="completed", input_data=other_job_input_data, progress=other_progress)
    db_session.add(other_job)
    await db_session.commit()
    await db_session.refresh(other_job)
    other_job_id_str = str(other_job.id)

    feedback_payload2 = {
        "job_id": other_job_id_str, "feedback_type": "thumbs_down", "comment": "Needs improvement"
    }
    await test_client.post("/api/v1/feedback", json=feedback_payload2)

    response = await test_client.get("/api/v1/ai/training_data?limit=10")
    assert response.status_code == 200

    r_data = response.json()
    assert len(r_data["data"]) == 2
    assert r_data["total"] == -1 # Current placeholder
    assert r_data["limit"] == 10
    assert r_data["skip"] == 0

    # Check structure of items (order might vary depending on DB/creation time)
    item_job_ids = {item["job_id"] for item in r_data["data"]}
    assert job_id_str in item_job_ids
    assert other_job_id_str in item_job_ids

    for item in r_data["data"]:
        assert "input_file_path" in item
        assert "output_file_path" in item
        assert "feedback" in item
        assert "feedback_type" in item["feedback"]
        assert "comment" in item["feedback"]

        # Verify path construction logic
        if item["job_id"] == job_id_str:
            assert item["feedback"]["comment"] == "Training data item 1"
            assert item["input_file_path"].endswith(f"{job.input_data['file_id']}{os.path.splitext(job.input_data['original_filename'])[1]}")
            assert item["input_file_path"].startswith(TEMP_UPLOADS_DIR)
            assert item["output_file_path"].endswith(f"{job_id_str}_converted.zip")
            assert item["output_file_path"].startswith(CONVERSION_OUTPUTS_DIR)
        elif item["job_id"] == other_job_id_str:
            assert item["feedback"]["comment"] == "Needs improvement"
            assert item["input_file_path"].endswith(f"{other_job.input_data['file_id']}{os.path.splitext(other_job.input_data['original_filename'])[1]}")
            assert item["output_file_path"].endswith(f"{other_job_id_str}_converted.zip")


@pytest.mark.asyncio
async def test_get_training_data_pagination(
    test_client: AsyncClient, db_session: AsyncSession, setup_job_for_feedback: ConversionJob
):
    """Test pagination for training data."""
    # Create 3 feedback entries
    job_ids = []
    for i in range(3):
        input_data = {"file_id": str(uuid.uuid4()), "original_filename": f"page_mod_{i}.zip"}
        progress = JobProgress(progress=100)
        job = ConversionJob(status="completed", input_data=input_data, progress=progress)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        job_ids.append(str(job.id))

        await test_client.post("/api/v1/feedback", json={
            "job_id": str(job.id), "feedback_type": "thumbs_up", "comment": f"Feedback {i}"
        })

    # Fetch all (limit > 3)
    response_all = await test_client.get("/api/v1/ai/training_data?limit=5")
    assert response_all.status_code == 200
    data_all = response_all.json()["data"]
    assert len(data_all) == 3 # Assuming these are the only feedback items

    # Fetch limit 1, page 1 (skip 0)
    response_p1 = await test_client.get("/api/v1/ai/training_data?skip=0&limit=1")
    assert response_p1.status_code == 200
    data_p1 = response_p1.json()["data"]
    assert len(data_p1) == 1
    item1_id = data_p1[0]["job_id"] # Actually feedback ID, but job_id is what we have

    # Fetch limit 1, page 2 (skip 1)
    response_p2 = await test_client.get("/api/v1/ai/training_data?skip=1&limit=1")
    assert response_p2.status_code == 200
    data_p2 = response_p2.json()["data"]
    assert len(data_p2) == 1
    item2_id = data_p2[0]["job_id"]
    assert item1_id != item2_id

    # Fetch limit 1, page 3 (skip 2)
    response_p3 = await test_client.get("/api/v1/ai/training_data?skip=2&limit=1")
    assert response_p3.status_code == 200
    data_p3 = response_p3.json()["data"]
    assert len(data_p3) == 1
    item3_id = data_p3[0]["job_id"]
    assert item3_id != item1_id and item3_id != item2_id

    # Ensure the items are indeed different ones from the created jobs
    # Order is determined by feedback creation time (newest first)
    # So data_all[0] is newest, data_p1[0] is newest, data_p2[0] is second newest etc.
    assert data_p1[0]["feedback"]["comment"] == data_all[0]["feedback"]["comment"]
    assert data_p2[0]["feedback"]["comment"] == data_all[1]["feedback"]["comment"]
    assert data_p3[0]["feedback"]["comment"] == data_all[2]["feedback"]["comment"]


    # Fetch limit 1, page 4 (skip 3) - should be empty
    response_p4 = await test_client.get("/api/v1/ai/training_data?skip=3&limit=1")
    assert response_p4.status_code == 200
    data_p4 = response_p4.json()["data"]
    assert len(data_p4) == 0
