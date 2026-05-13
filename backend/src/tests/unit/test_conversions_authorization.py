"""
Authorization tests for the conversions API (issue #1417).

Verifies that user A cannot fetch / delete / download user B's conversion
job, and that the failure mode is a 404 (not 403) so the existence of
foreign jobs is never leaked.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.conversions import router
from api._authz import get_current_user
from db.base import get_db


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.email = f"user-{uuid.uuid4().hex[:6]}@example.com"
    user.subscription_tier = "free"
    return user


def _make_job(owner_id: str) -> MagicMock:
    job = MagicMock()
    job.id = str(uuid.uuid4())
    job.user_id = owner_id
    job.status = "completed"
    job.created_at = datetime.now()
    job.updated_at = datetime.now()
    job.input_data = {"original_filename": "mod.jar"}
    job.progress = MagicMock()
    job.progress.progress = 100
    return job


def _build_client(current_user, *, job=None, monkeypatch=None) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    if monkeypatch is not None:
        from api import conversions as conv_mod

        monkeypatch.setattr(conv_mod.crud, "get_job", AsyncMock(return_value=job), raising=True)
        monkeypatch.setattr(
            conv_mod.cache, "get_job_status", AsyncMock(return_value=None), raising=False
        )

    return TestClient(app)


class TestConversionsAuthorization:
    def test_get_conversion_404_when_owner_differs(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        job = _make_job(owner_id=owner.id)
        client = _build_client(attacker, job=job, monkeypatch=monkeypatch)

        response = client.get(f"/api/v1/conversions/{job.id}")

        assert response.status_code == 404, (
            "Foreign conversion access must yield 404 (not 403) per issue #1417"
        )

    def test_get_conversion_404_when_missing(self, monkeypatch):
        attacker = _make_user()
        client = _build_client(attacker, job=None, monkeypatch=monkeypatch)
        job_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/conversions/{job_id}")

        assert response.status_code == 404

    def test_delete_conversion_404_when_owner_differs(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        job = _make_job(owner_id=owner.id)
        client = _build_client(attacker, job=job, monkeypatch=monkeypatch)

        response = client.delete(f"/api/v1/conversions/{job.id}")

        assert response.status_code == 404

    def test_download_conversion_404_when_owner_differs(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        job = _make_job(owner_id=owner.id)
        client = _build_client(attacker, job=job, monkeypatch=monkeypatch)

        response = client.get(f"/api/v1/conversions/{job.id}/download")

        assert response.status_code == 404

    def test_download_report_404_when_owner_differs(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        job = _make_job(owner_id=owner.id)
        client = _build_client(attacker, job=job, monkeypatch=monkeypatch)

        response = client.get(f"/api/v1/conversions/{job.id}/report")

        assert response.status_code == 404

    def test_unauthenticated_request_yields_401(self, monkeypatch):
        # No auth dependency override — bearer token missing -> 401
        from api import conversions as conv_mod

        monkeypatch.setattr(conv_mod.crud, "get_job", AsyncMock(return_value=None), raising=True)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: MagicMock()
        client = TestClient(app)

        job_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/conversions/{job_id}")

        assert response.status_code in (401, 403), (
            "Missing bearer token should produce 401/403, not 200"
        )
