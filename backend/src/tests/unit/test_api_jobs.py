
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, patch, MagicMock
from api.jobs import router, JobStatus
import uuid

app = FastAPI()
app.include_router(router)

@pytest.fixture
def mock_manager():
    return AsyncMock()

@pytest.fixture
def client(mock_manager):
    from api.jobs import get_job_manager_dep, security
    from db.base import get_db as real_get_db
    from unittest.mock import MagicMock, patch
    from fastapi.security import HTTPAuthorizationCredentials

    mock_user = MagicMock()
    mock_user.id = "test-user-id"
    mock_user.email = "test@example.com"
    mock_user.is_verified = True

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user

    async def mock_execute(*args, **kwargs):
        return mock_result

    mock_session.execute = mock_execute

    app.dependency_overrides[get_job_manager_dep] = lambda: mock_manager
    app.dependency_overrides[real_get_db] = lambda: mock_session

    # Override security to provide a valid mock token
    mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")
    app.dependency_overrides[security] = lambda: mock_credentials

    # Patch verify_token to return our test user id
    with patch("api.jobs.verify_token", return_value="test-user-id"):
        yield TestClient(app)

    app.dependency_overrides.clear()

class TestJobsAPI:
    def test_create_job(self, mock_manager, client):
        mock_manager.create_job.return_value = "job-123"
        
        request_data = {
            "file_path": "/tmp/mod.jar",
            "original_filename": "mod.jar",
            "options": {
                "conversion_mode": "standard",
                "target_version": "1.20",
                "output_format": "mcaddon"
            }
        }
        
        response = client.post("/api/v1/jobs", json=request_data)
        
        assert response.status_code == 201
        assert response.json()["job_id"] == "job-123"
        mock_manager.create_job.assert_called_once()

    def test_list_jobs(self, mock_manager, client):
        mock_job = MagicMock()
        mock_job.job_id = "job-123"
        mock_job.user_id = "test-user-id"
        mock_job.original_filename = "mod.jar"
        mock_job.status = JobStatus.PENDING
        mock_job.progress = 0
        mock_job.current_step = "queued"
        mock_job.result_url = None
        mock_job.error_message = None
        mock_job.created_at = "2023-01-01T00:00:00Z"
        mock_job.updated_at = "2023-01-01T00:00:00Z"
        mock_job.completed_at = None
        
        mock_manager.list_jobs.return_value = [mock_job]
        
        response = client.get("/api/v1/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["job_id"] == "job-123"

    def test_get_job_success(self, mock_manager, client):
        job_id = str(uuid.uuid4())
        mock_job = MagicMock()
        mock_job.job_id = job_id
        mock_job.user_id = "test-user-id"
        mock_job.original_filename = "mod.jar"
        mock_job.status = JobStatus.PROCESSING
        mock_job.progress = 50
        mock_job.current_step = "converting"
        mock_job.result_url = None
        mock_job.error_message = None
        mock_job.created_at = "2023-01-01T00:00:00Z"
        mock_job.updated_at = "2023-01-01T00:00:00Z"
        mock_job.completed_at = None
        
        mock_manager.get_job.return_value = mock_job
        
        response = client.get(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        assert response.json()["job_id"] == job_id

    def test_get_job_not_found(self, mock_manager, client):
        mock_manager.get_job.return_value = None
        
        job_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 404

    def test_cancel_job_success(self, mock_manager, client):
        job_id = str(uuid.uuid4())
        mock_job = MagicMock()
        mock_job.job_id = job_id
        mock_job.user_id = "test-user-id"
        mock_job.status = JobStatus.PROCESSING
        mock_manager.get_job.return_value = mock_job
        mock_manager.cancel_job.return_value = True
        
        response = client.delete(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        assert "cancelled successfully" in response.json()["message"]

    def test_cancel_job_forbidden(self, mock_manager, client):
        job_id = str(uuid.uuid4())
        mock_job = MagicMock()
        mock_job.job_id = job_id
        mock_job.user_id = "other_user"
        mock_manager.get_job.return_value = mock_job
        
        response = client.delete(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 403
