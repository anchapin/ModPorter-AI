"""
Authorization tests for the behavior_files API (issue #1417).

Behavior files inherit ownership from their parent conversion job. This
test verifies that a user cannot list / read / mutate behavior files that
belong to another user's conversion, and that the failure mode is 404.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.behavior_files import router
from api._authz import get_current_user
from db.base import get_db


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = str(uuid.uuid4())
    return user


def _make_job(owner_id: str) -> MagicMock:
    job = MagicMock()
    job.id = str(uuid.uuid4())
    job.user_id = owner_id
    return job


def _make_behavior_file(conversion_id) -> MagicMock:
    bf = MagicMock()
    bf.id = uuid.uuid4()
    bf.conversion_id = conversion_id
    bf.file_path = "scripts/test.js"
    bf.file_type = "script"
    bf.content = "// test"
    bf.created_at = datetime.now()
    bf.updated_at = datetime.now()
    return bf


def _build_client(current_user, *, job=None, behavior_file=None, monkeypatch=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    if monkeypatch is not None:
        from api import behavior_files as bf_mod

        monkeypatch.setattr(bf_mod.crud, "get_job", AsyncMock(return_value=job), raising=True)
        monkeypatch.setattr(
            bf_mod.crud,
            "get_behavior_file",
            AsyncMock(return_value=behavior_file),
            raising=True,
        )
        monkeypatch.setattr(
            bf_mod.crud,
            "get_behavior_files_by_conversion",
            AsyncMock(return_value=[behavior_file] if behavior_file else []),
            raising=True,
        )
        monkeypatch.setattr(
            bf_mod.crud,
            "get_behavior_files_by_type",
            AsyncMock(return_value=[behavior_file] if behavior_file else []),
            raising=True,
        )

    return TestClient(app)


class TestBehaviorFilesAuthorization:
    def test_list_files_404_when_conversion_owned_by_other(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        job = _make_job(owner_id=owner.id)
        client = _build_client(attacker, job=job, monkeypatch=monkeypatch)

        response = client.get(f"/conversions/{job.id}/behaviors")

        assert response.status_code == 404

    def test_list_files_succeeds_for_owner(self, monkeypatch):
        owner = _make_user()
        job = _make_job(owner_id=owner.id)
        client = _build_client(owner, job=job, monkeypatch=monkeypatch)

        response = client.get(f"/conversions/{job.id}/behaviors")

        assert response.status_code == 200

    def test_get_file_404_when_parent_not_owned(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        job = _make_job(owner_id=owner.id)
        bf = _make_behavior_file(conversion_id=job.id)
        client = _build_client(attacker, job=job, behavior_file=bf, monkeypatch=monkeypatch)

        response = client.get(f"/behaviors/{bf.id}")

        assert response.status_code == 404

    def test_get_file_succeeds_for_owner(self, monkeypatch):
        owner = _make_user()
        job = _make_job(owner_id=owner.id)
        bf = _make_behavior_file(conversion_id=job.id)
        client = _build_client(owner, job=job, behavior_file=bf, monkeypatch=monkeypatch)

        response = client.get(f"/behaviors/{bf.id}")

        assert response.status_code == 200

    def test_delete_file_404_when_parent_not_owned(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        job = _make_job(owner_id=owner.id)
        bf = _make_behavior_file(conversion_id=job.id)

        from api import behavior_files as bf_mod

        monkeypatch.setattr(
            bf_mod.crud, "delete_behavior_file", AsyncMock(return_value=True), raising=True
        )

        client = _build_client(attacker, job=job, behavior_file=bf, monkeypatch=monkeypatch)

        response = client.delete(f"/behaviors/{bf.id}")

        assert response.status_code == 404
