"""Tests for the per-endpoint rate-limit branch on /register and /login.

PR #1422 / issue #1417 added strict rate limiting to those two endpoints, but
the surrounding test suite forces ``TESTING=true`` (see ``conftest.py``) which
short-circuits the rate-limit block entirely. These tests temporarily flip
``TESTING=false`` and stub :class:`RateLimiter` so the 429 path is exercised:

* status code is exactly ``429``;
* ``X-RateLimit-Limit``, ``X-RateLimit-Remaining`` and ``X-RateLimit-Reset``
  headers are propagated from the limiter's metadata;
* the value used for ``X-RateLimit-Limit`` differs between /register
  (``limit_hour``) and /login (``limit_minute``).
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure DISABLE_REDIS is set before importing api.auth (mirrors the pattern in
# the sibling refresh-token test module).
os.environ["DISABLE_REDIS"] = "true"
os.environ["FEATURE_USER_ACCOUNTS"] = "true"

from api.auth import router  # noqa: E402

app = FastAPI()
app.include_router(router, prefix="/api/v1/auth")


def _build_blocked_limiter(metadata: dict) -> MagicMock:
    """Return a ``RateLimiter`` mock whose ``check_rate_limit`` says *denied*."""
    mock_limiter = MagicMock()
    mock_limiter.initialize = AsyncMock()
    mock_limiter.close = AsyncMock()
    mock_limiter.check_rate_limit = AsyncMock(return_value=(False, metadata))
    return mock_limiter


# ---------------------------------------------------------------------------
# /register
# ---------------------------------------------------------------------------


class TestRegisterRateLimitDenied:
    """Exercise the 429 branch in :func:`api.auth.register`."""

    def test_register_returns_429_when_rate_limit_denied(self):
        metadata = {
            "limit_hour": 10,
            "remaining_hour": 0,
            "reset_at_hour": 1_700_000_060,
            "limit_minute": 10,
            "remaining_minute": 0,
            "reset_at_minute": 1_700_000_060,
            "retry_after": 60,
        }
        mock_limiter = _build_blocked_limiter(metadata)

        with patch.dict(os.environ, {"TESTING": "false"}, clear=False):
            with patch("services.rate_limiter.RateLimiter", return_value=mock_limiter) as cls_patch:
                with patch("api.auth.is_feature_enabled", return_value=True):
                    client = TestClient(app)
                    resp = client.post(
                        "/api/v1/auth/register",
                        json={
                            "email": "blocked@test.com",
                            "password": "ValidPass123!",
                        },
                    )

        assert resp.status_code == 429, resp.text
        # The endpoint constructed *exactly one* RateLimiter and asked it once.
        assert cls_patch.call_count == 1
        mock_limiter.check_rate_limit.assert_awaited_once()
        mock_limiter.initialize.assert_awaited_once()
        mock_limiter.close.assert_awaited_once()

        body = resp.json()
        assert "registration" in body["detail"].lower()

        # /register reports the *hour* window in its X-RateLimit-* headers.
        assert resp.headers["x-ratelimit-limit"] == str(metadata["limit_hour"])
        assert resp.headers["x-ratelimit-remaining"] == str(metadata["remaining_hour"])
        assert resp.headers["x-ratelimit-reset"] == str(metadata["reset_at_hour"])

    def test_register_does_not_touch_db_when_rate_limit_denied(self):
        """A 429 must short-circuit before any DB query happens."""
        from api.auth import get_db

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()

        metadata = {
            "limit_hour": 10,
            "remaining_hour": 0,
            "reset_at_hour": 1_700_000_060,
            "retry_after": 60,
        }
        mock_limiter = _build_blocked_limiter(metadata)

        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            with patch.dict(os.environ, {"TESTING": "false"}, clear=False):
                with patch(
                    "services.rate_limiter.RateLimiter",
                    return_value=mock_limiter,
                ):
                    with patch("api.auth.is_feature_enabled", return_value=True):
                        client = TestClient(app)
                        resp = client.post(
                            "/api/v1/auth/register",
                            json={
                                "email": "blocked@test.com",
                                "password": "ValidPass123!",
                            },
                        )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 429
        mock_db.execute.assert_not_called()
        mock_db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# /login
# ---------------------------------------------------------------------------


class TestLoginRateLimitDenied:
    """Exercise the 429 branch in :func:`api.auth.login`."""

    def test_login_returns_429_when_rate_limit_denied(self):
        metadata = {
            "limit_minute": 5,
            "remaining_minute": 0,
            "reset_at_minute": 1_700_000_005,
            "limit_hour": 20,
            "remaining_hour": 0,
            "reset_at_hour": 1_700_003_600,
            "retry_after": 5,
        }
        mock_limiter = _build_blocked_limiter(metadata)

        with patch.dict(os.environ, {"TESTING": "false"}, clear=False):
            with patch("services.rate_limiter.RateLimiter", return_value=mock_limiter) as cls_patch:
                with patch("api.auth.is_feature_enabled", return_value=True):
                    client = TestClient(app)
                    resp = client.post(
                        "/api/v1/auth/login",
                        json={
                            "email": "blocked@test.com",
                            "password": "ValidPass123!",
                        },
                    )

        assert resp.status_code == 429, resp.text
        assert cls_patch.call_count == 1
        mock_limiter.check_rate_limit.assert_awaited_once()

        body = resp.json()
        assert "login" in body["detail"].lower()

        # /login reports the *minute* window in its X-RateLimit-* headers.
        assert resp.headers["x-ratelimit-limit"] == str(metadata["limit_minute"])
        assert resp.headers["x-ratelimit-remaining"] == str(metadata["remaining_minute"])
        assert resp.headers["x-ratelimit-reset"] == str(metadata["reset_at_minute"])

    def test_login_does_not_touch_db_when_rate_limit_denied(self):
        from api.auth import get_db

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        metadata = {
            "limit_minute": 5,
            "remaining_minute": 0,
            "reset_at_minute": 1_700_000_005,
            "retry_after": 5,
        }
        mock_limiter = _build_blocked_limiter(metadata)

        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            with patch.dict(os.environ, {"TESTING": "false"}, clear=False):
                with patch(
                    "services.rate_limiter.RateLimiter",
                    return_value=mock_limiter,
                ):
                    with patch("api.auth.is_feature_enabled", return_value=True):
                        client = TestClient(app)
                        resp = client.post(
                            "/api/v1/auth/login",
                            json={
                                "email": "blocked@test.com",
                                "password": "ValidPass123!",
                            },
                        )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 429
        mock_db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Sanity: the bypass when TESTING=true still works.
# ---------------------------------------------------------------------------


class TestRateLimiterIsBypassedInTestingMode:
    """When ``TESTING=true``, the endpoints must NOT instantiate a RateLimiter
    at all -- otherwise any test that doesn't mock Redis would hit the network.
    """

    @pytest.mark.parametrize(
        "endpoint, payload",
        [
            (
                "/api/v1/auth/register",
                {"email": "bypass@test.com", "password": "ValidPass123!"},
            ),
            (
                "/api/v1/auth/login",
                {"email": "bypass@test.com", "password": "ValidPass123!"},
            ),
        ],
    )
    def test_rate_limiter_not_constructed_in_testing_mode(self, endpoint, payload):
        from api.auth import get_db

        # Stub the DB; we only care that the rate-limiter wasn't instantiated.
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()  # SQLAlchemy .add() is sync, not async.
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            with patch.dict(os.environ, {"TESTING": "true"}, clear=False):
                with patch("services.rate_limiter.RateLimiter") as cls_patch:
                    with patch("api.auth.is_feature_enabled", return_value=True):
                        client = TestClient(app, raise_server_exceptions=False)
                        # Response status is irrelevant: it can be 401 (login,
                        # unknown email), 4xx (validation), 5xx (other) -- we
                        # only assert the limiter was never constructed.
                        client.post(endpoint, json=payload)
        finally:
            app.dependency_overrides.clear()

        cls_patch.assert_not_called()
