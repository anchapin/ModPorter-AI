"""
Authorization tests for the batch conversion API (issue #1417).

The previous implementation accepted ``user_id`` as a query parameter, which
let any caller impersonate any user. The patched implementation derives the
owner from the authenticated identity. These tests verify both that:

1. user A cannot read user B's batch (returns 404 — no batch matches the
   authenticated user_id, even when the batch_id is correct), and
2. unauthenticated requests no longer accept ``user_id`` as a query string.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.batch_conversion import router
from api._authz import get_current_user
from db.base import get_db


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = str(uuid.uuid4())
    return user


def _make_db_session(scalars_result):
    """Build a mock AsyncSession.execute().scalars().all() returning given results."""
    session = MagicMock()

    result_proxy = MagicMock()
    result_proxy.scalars = MagicMock(
        return_value=MagicMock(
            all=MagicMock(return_value=scalars_result),
            first=MagicMock(return_value=scalars_result[0] if scalars_result else None),
        )
    )
    session.execute = AsyncMock(return_value=result_proxy)
    session.commit = AsyncMock()
    return session


def _build_client(current_user, *, scalars_result):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: _make_db_session(scalars_result)
    return TestClient(app)


class TestBatchConversionAuthorization:
    def test_get_batch_status_404_when_no_jobs_match_user(self):
        # Owner created the batch; attacker queries it; DB returns nothing
        # because the batch_id+user_id WHERE clause excludes them.
        attacker = _make_user()
        client = _build_client(attacker, scalars_result=[])
        batch_id = "batch_1700000000.0"

        response = client.get(f"/batch/{batch_id}/status")

        assert response.status_code == 404

    def test_get_batch_results_404_when_no_jobs_match_user(self):
        attacker = _make_user()
        client = _build_client(attacker, scalars_result=[])
        batch_id = "batch_1700000000.0"

        response = client.get(f"/batch/{batch_id}/results")

        assert response.status_code == 404

    def test_cancel_batch_404_when_no_jobs_match_user(self):
        attacker = _make_user()
        client = _build_client(attacker, scalars_result=[])
        batch_id = "batch_1700000000.0"

        response = client.delete(f"/batch/{batch_id}")

        assert response.status_code == 404

    def test_user_id_query_param_is_no_longer_honored(self):
        """The previous user_id query string is now ignored — auth dep wins.

        Hitting the endpoint without a Bearer token must yield 401/403 even
        if the caller passes ``user_id=<other_user_id>`` as a query string.
        """
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: _make_db_session([])
        client = TestClient(app)

        batch_id = "batch_1700000000.0"
        forged_user_id = str(uuid.uuid4())
        response = client.get(f"/batch/{batch_id}/status", params={"user_id": forged_user_id})

        assert response.status_code in (401, 403), (
            "Auth dependency must be enforced regardless of forged user_id query string"
        )
