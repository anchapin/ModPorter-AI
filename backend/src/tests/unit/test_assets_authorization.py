"""
Authorization tests for the assets API (issue #1417).

Verifies that assets inherit the owning conversion's ownership: user A cannot
access user B's assets and the failure mode is a 404 (not 403).
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.assets import router
from api._authz import get_current_user
from db.base import get_db


def _make_user(user_id: str | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or str(uuid.uuid4())
    return user


def _make_job(owner_id: str) -> MagicMock:
    job = MagicMock()
    job.id = str(uuid.uuid4())
    job.user_id = owner_id
    return job


def _make_asset(conversion_id: str) -> MagicMock:
    asset = MagicMock()
    asset.id = uuid.uuid4()
    asset.conversion_id = (
        uuid.UUID(conversion_id) if isinstance(conversion_id, str) else conversion_id
    )
    asset.asset_type = "texture"
    asset.original_path = "path/orig.png"
    asset.converted_path = None
    asset.status = "pending"
    asset.asset_metadata = None
    asset.file_size = 1024
    asset.mime_type = "image/png"
    asset.original_filename = "orig.png"
    asset.error_message = None
    asset.created_at = datetime.now()
    asset.updated_at = datetime.now()
    return asset


def _build_client(current_user, job_owner_id: str | None):
    """Build a TestClient where ``crud.get_job`` returns a job with ``job_owner_id``."""
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_current_user] = lambda: current_user
    # ``get_db`` is required by the route signature; we never actually use it
    # because ``crud`` calls are patched via the assets module namespace.
    app.dependency_overrides[get_db] = lambda: MagicMock()
    return app


def _patch_crud(monkeypatch, *, job=None, asset=None):
    """Patch the crud lookups used by assets.py."""
    from api import assets as assets_mod

    monkeypatch.setattr(assets_mod.crud, "get_job", AsyncMock(return_value=job), raising=True)
    monkeypatch.setattr(assets_mod.crud, "get_asset", AsyncMock(return_value=asset), raising=True)
    monkeypatch.setattr(
        assets_mod.crud,
        "list_assets_for_conversion",
        AsyncMock(return_value=[asset] if asset else []),
        raising=True,
    )


class TestAssetsAuthorization:
    def test_list_assets_404_when_conversion_owned_by_other(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        owner_job = _make_job(owner_id=str(owner.id))
        _patch_crud(monkeypatch, job=owner_job)

        app = _build_client(attacker, job_owner_id=str(owner.id))
        client = TestClient(app)

        response = client.get(f"/conversions/{owner_job.id}/assets")

        assert response.status_code == 404

    def test_list_assets_succeeds_for_owner(self, monkeypatch):
        owner = _make_user()
        owner_job = _make_job(owner_id=str(owner.id))
        asset = _make_asset(conversion_id=owner_job.id)
        _patch_crud(monkeypatch, job=owner_job, asset=asset)

        app = _build_client(owner, job_owner_id=str(owner.id))
        client = TestClient(app)

        response = client.get(f"/conversions/{owner_job.id}/assets")

        assert response.status_code == 200

    def test_get_asset_404_when_parent_conversion_not_owned(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        owner_job = _make_job(owner_id=str(owner.id))
        asset = _make_asset(conversion_id=owner_job.id)
        _patch_crud(monkeypatch, job=owner_job, asset=asset)

        app = _build_client(attacker, job_owner_id=str(owner.id))
        client = TestClient(app)

        response = client.get(f"/assets/{asset.id}")

        assert response.status_code == 404

    def test_get_asset_succeeds_for_owner(self, monkeypatch):
        owner = _make_user()
        owner_job = _make_job(owner_id=str(owner.id))
        asset = _make_asset(conversion_id=owner_job.id)
        _patch_crud(monkeypatch, job=owner_job, asset=asset)

        app = _build_client(owner, job_owner_id=str(owner.id))
        client = TestClient(app)

        response = client.get(f"/assets/{asset.id}")

        assert response.status_code == 200

    def test_delete_asset_404_when_parent_conversion_not_owned(self, monkeypatch):
        owner = _make_user()
        attacker = _make_user()
        owner_job = _make_job(owner_id=str(owner.id))
        asset = _make_asset(conversion_id=owner_job.id)
        _patch_crud(monkeypatch, job=owner_job, asset=asset)

        from api import assets as assets_mod

        monkeypatch.setattr(
            assets_mod.crud, "delete_asset", AsyncMock(return_value=True), raising=True
        )

        app = _build_client(attacker, job_owner_id=str(owner.id))
        client = TestClient(app)

        response = client.delete(f"/assets/{asset.id}")

        assert response.status_code == 404
