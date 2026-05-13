"""
Authorization tests for the jobs API (issue #1417).

Verifies that user A cannot access user B's job: the endpoint returns 404
(NOT 403) so the existence of foreign jobs is never leaked.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.jobs import router, get_current_user_id, get_job_manager_dep
from services.job_manager import JobStatus


def _build_client(user_id: str, job: MagicMock | None) -> TestClient:
    """Build a TestClient with auth + job_manager dependency overrides."""
    app = FastAPI()
    app.include_router(router)

    async def _user_id_override():
        return user_id

    job_manager = MagicMock()
    job_manager.get_job = AsyncMock(return_value=job)
    job_manager.cancel_job = AsyncMock(return_value=True)
    job_manager.list_jobs = AsyncMock(return_value=[])

    async def _job_manager_override():
        return job_manager

    app.dependency_overrides[get_current_user_id] = _user_id_override
    app.dependency_overrides[get_job_manager_dep] = _job_manager_override
    return TestClient(app)


def _make_job(owner_id: str) -> MagicMock:
    job = MagicMock()
    job.job_id = str(uuid.uuid4())
    job.user_id = owner_id
    job.original_filename = "mod.jar"
    job.status = JobStatus.PENDING
    job.progress = 0
    job.current_step = "queued"
    job.result_url = None
    job.error_message = None
    job.created_at = "2024-01-01T00:00:00Z"
    job.updated_at = "2024-01-01T00:00:00Z"
    job.completed_at = None
    return job


class TestJobAuthorization:
    """Cross-user access must yield 404 (not 403) for issue #1417."""

    def test_get_job_404_when_owner_differs(self):
        owner = str(uuid.uuid4())
        attacker = str(uuid.uuid4())
        job = _make_job(owner_id=owner)
        client = _build_client(user_id=attacker, job=job)

        response = client.get(f"/api/v1/jobs/{job.job_id}")

        assert response.status_code == 404, (
            "Cross-user job access must return 404 to avoid leaking job existence"
        )
        assert "not found" in response.json()["detail"].lower()

    def test_get_job_404_when_job_missing(self):
        attacker = str(uuid.uuid4())
        client = _build_client(user_id=attacker, job=None)
        job_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/jobs/{job_id}")

        assert response.status_code == 404

    def test_get_job_succeeds_for_owner(self):
        owner = str(uuid.uuid4())
        job = _make_job(owner_id=owner)
        client = _build_client(user_id=owner, job=job)

        response = client.get(f"/api/v1/jobs/{job.job_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["job_id"] == job.job_id
        assert body["user_id"] == owner

    def test_cancel_job_404_when_owner_differs(self):
        owner = str(uuid.uuid4())
        attacker = str(uuid.uuid4())
        job = _make_job(owner_id=owner)
        client = _build_client(user_id=attacker, job=job)

        response = client.delete(f"/api/v1/jobs/{job.job_id}")

        assert response.status_code == 404, "Cross-user cancel must return 404, never 403"

    def test_cancel_job_succeeds_for_owner(self):
        owner = str(uuid.uuid4())
        job = _make_job(owner_id=owner)
        client = _build_client(user_id=owner, job=job)

        response = client.delete(f"/api/v1/jobs/{job.job_id}")

        assert response.status_code == 200
