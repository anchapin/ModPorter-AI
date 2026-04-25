"""
Tests for Email Verification API - src/api/email_verification.py
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.email_verification import router


def _make_app():
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_user(**overrides):
    user = MagicMock()
    user.id = overrides.get("id", uuid.uuid4())
    user.email = overrides.get("email", "test@example.com")
    user.is_verified = overrides.get("is_verified", False)
    user.verification_token = overrides.get("verification_token", "tok123")
    user.verification_token_expires = overrides.get(
        "verification_token_expires",
        datetime.now(timezone.utc) + timedelta(hours=24),
    )
    return user


def _override_db(app, mock_db):
    async def _get_db():
        return mock_db

    from db.base import get_db

    app.dependency_overrides[get_db] = _get_db
    return app


class TestRegisterWithVerification:
    def test_register_new_user_success(self):
        app = _make_app()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        new_user = _mock_user(email="new@example.com")
        mock_db.refresh = AsyncMock(side_effect=lambda u: setattr(u, "id", uuid.uuid4()))

        mock_email_svc = AsyncMock()
        mock_email_svc.send = AsyncMock()

        with (
            patch("api.email_verification.get_email_service", return_value=mock_email_svc),
            patch("api.email_verification.generate_verification_token", return_value="tok_new"),
            patch("api.email_verification.hash_password", return_value="hashed"),
        ):
            _override_db(app, mock_db)
            client = TestClient(app)
            resp = client.post(
                "/auth/register-verify",
                json={"email": "new@example.com", "password": "StrongPass123!"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "user_id" in data
        assert "check your email" in data["message"].lower()

    def test_register_already_verified_user_returns_400(self):
        app = _make_app()
        existing = _mock_user(is_verified=True, email="exists@example.com")
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing)
        mock_db.execute = AsyncMock(return_value=mock_result)

        _override_db(app, mock_db)
        with (
            patch("api.email_verification.get_email_service"),
            patch("api.email_verification.generate_verification_token"),
            patch("api.email_verification.hash_password"),
        ):
            client = TestClient(app)
            resp = client.post(
                "/auth/register-verify",
                json={"email": "exists@example.com", "password": "StrongPass123!"},
            )

        assert resp.status_code == 400
        assert "already registered and verified" in resp.json()["detail"].lower()

    def test_register_replaces_unverified_user(self):
        app = _make_app()
        existing = _mock_user(is_verified=False, email="unverified@example.com")
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        mock_email_svc = AsyncMock()
        mock_email_svc.send = AsyncMock()

        with (
            patch("api.email_verification.get_email_service", return_value=mock_email_svc),
            patch("api.email_verification.generate_verification_token", return_value="tok_re"),
            patch("api.email_verification.hash_password", return_value="hashed"),
        ):
            _override_db(app, mock_db)
            client = TestClient(app)
            resp = client.post(
                "/auth/register-verify",
                json={"email": "unverified@example.com", "password": "StrongPass123!"},
            )

        assert resp.status_code == 200
        mock_db.delete.assert_called_once_with(existing)
        assert mock_db.commit.call_count >= 1


class TestVerifyEmail:
    def test_verify_valid_token(self):
        app = _make_app()
        user = _mock_user(verification_token="valid_tok", is_verified=False)
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=user)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        _override_db(app, mock_db)
        client = TestClient(app)
        resp = client.get("/auth/verify-email/valid_tok")

        assert resp.status_code == 200
        assert resp.json()["message"] == "Email verified successfully"
        assert user.is_verified is True
        assert user.verification_token is None

    def test_verify_invalid_token_returns_400(self):
        app = _make_app()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        _override_db(app, mock_db)
        client = TestClient(app)
        resp = client.get("/auth/verify-email/invalid_tok")

        assert resp.status_code == 400
        assert "invalid or expired" in resp.json()["detail"].lower()

    def test_verify_expired_token_returns_400(self):
        app = _make_app()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        _override_db(app, mock_db)
        client = TestClient(app)
        resp = client.get("/auth/verify-email/expired_tok")

        assert resp.status_code == 400


class TestResendVerification:
    def test_resend_unverified_user_success(self):
        app = _make_app()
        expired = datetime.now(timezone.utc) - timedelta(hours=1)
        user = _mock_user(is_verified=False, verification_token_expires=expired)
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=user)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        mock_email_svc = AsyncMock()
        mock_email_svc.send = AsyncMock()

        with (
            patch("api.email_verification.get_email_service", return_value=mock_email_svc),
            patch("api.email_verification.generate_verification_token", return_value="new_tok"),
        ):
            _override_db(app, mock_db)
            client = TestClient(app)
            resp = client.post(
                "/auth/resend-verification",
                json={"email": "test@example.com"},
            )

        assert resp.status_code == 200
        assert "new verification link" in resp.json()["message"].lower()
        mock_email_svc.send.assert_called_once()

    def test_resend_nonexistent_user_returns_success(self):
        app = _make_app()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        _override_db(app, mock_db)
        client = TestClient(app)
        resp = client.post(
            "/auth/resend-verification",
            json={"email": "nobody@example.com"},
        )

        assert resp.status_code == 200

    def test_resend_token_still_valid_no_resend(self):
        app = _make_app()
        future = datetime.now(timezone.utc) + timedelta(hours=12)
        user = _mock_user(is_verified=False, verification_token_expires=future)
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        _override_db(app, mock_db)
        client = TestClient(app)
        resp = client.post(
            "/auth/resend-verification",
            json={"email": "test@example.com"},
        )

        assert resp.status_code == 200
        assert "already sent" in resp.json()["message"].lower()
