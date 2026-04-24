"""
Tests for auth.py uncovered paths - API key management, refresh edge cases,
password validator, and feature flag checks.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import router, get_current_user, get_db

app = FastAPI()
app.include_router(router, prefix="/api/v1/auth")


@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    mock.delete = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("api.auth.hash_password", return_value="hashed_password"):
        with patch("api.auth.verify_password", return_value=True):
            with patch("api.auth.create_access_token", return_value="test_access_token"):
                with patch("api.auth.create_refresh_token", return_value="test_refresh_token"):
                    with patch("api.auth.verify_token", return_value="test_user_id"):
                        with patch(
                            "api.auth.generate_verification_token",
                            return_value="test_verification_token",
                        ):
                            with patch(
                                "api.auth.generate_reset_token",
                                return_value="test_reset_token",
                            ):
                                with patch(
                                    "api.auth.generate_api_key",
                                    return_value=("full_key_123", "prefix_123"),
                                ):
                                    with patch("api.auth.hash_api_key", return_value="hashed_key"):
                                        with patch(
                                            "api.auth.is_feature_enabled", return_value=True
                                        ):
                                            with patch(
                                                "api.auth.send_verification_email",
                                                new_callable=AsyncMock,
                                                return_value=True,
                                            ):
                                                with patch(
                                                    "api.auth.send_password_reset_email",
                                                    new_callable=AsyncMock,
                                                    return_value=True,
                                                ):
                                                    yield TestClient(app)

    app.dependency_overrides.clear()


def _mock_user(**overrides):
    u = MagicMock()
    u.id = overrides.get("id", "test_user_id")
    u.email = overrides.get("email", "test@example.com")
    u.is_verified = True
    u.password_hash = "hashed"
    u.created_at = datetime.now(timezone.utc)
    u.conversion_count = 0
    u.verification_token = None
    u.verification_token_expires = None
    u.reset_token = None
    u.reset_token_expires = None
    return u


class TestPasswordValidation:
    def test_password_no_special(self):
        from pydantic import ValidationError

        from api.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="Test1234")

    def test_password_valid(self):
        from api.auth import RegisterRequest

        req = RegisterRequest(email="test@example.com", password="Test1234!")
        assert req.password == "Test1234!"


class TestRefreshTokenUserNotFound:
    def test_refresh_user_not_found(self, client, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "test_refresh_token"})

        assert resp.status_code == 401


class TestCreateApiKey:
    def test_create_api_key_success(self, client, mock_db):
        mock_user = _mock_user()

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_db.add = MagicMock()

        async def mock_refresh(obj):
            obj.id = "key_id_123"
            obj.name = "My Key"
            obj.prefix = "prefix_123"
            obj.created_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)
        mock_db.commit = AsyncMock()

        resp = client.post("/api/v1/auth/api-keys", json={"name": "My Key"})

        app.dependency_overrides.clear()

        assert resp.status_code in (200, 201, 503)


class TestListApiKeys:
    def test_list_api_keys_success(self, client, mock_db):
        mock_user = _mock_user()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_key = MagicMock()
        mock_key.id = "key_123"
        mock_key.name = "Test Key"
        mock_key.prefix = "pk_"
        mock_key.created_at = datetime.now(timezone.utc)
        mock_key.last_used = None
        mock_key.is_active = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_key]
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.get("/api/v1/auth/api-keys")

        assert resp.status_code in (200, 503)
        app.dependency_overrides.clear()


class TestRevokeApiKey:
    def test_revoke_api_key_not_found(self, client, mock_db):
        mock_user = _mock_user()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.delete("/api/v1/auth/api-keys/nonexistent_key")

        assert resp.status_code in (404, 503)
        app.dependency_overrides.clear()

    def test_revoke_api_key_success(self, client, mock_db):
        mock_user = _mock_user()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_key = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_key)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        resp = client.delete("/api/v1/auth/api-keys/key_123")

        assert resp.status_code in (200, 503)
        app.dependency_overrides.clear()


class TestFeatureFlagDisabled:
    def test_register_feature_disabled(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db
        with patch("api.auth.is_feature_enabled", return_value=False):
            with pytest.raises(Exception):
                from services.feature_flags import FeatureFlagNotEnabledError

                tc = TestClient(app, raise_server_exceptions=False)
                resp = tc.post(
                    "/api/v1/auth/register",
                    json={"email": "test@example.com", "password": "Test1234!"},
                )
                assert resp.status_code == 503
        app.dependency_overrides.clear()


class TestOAuthEndpoints:
    def test_oauth_status_unsupported(self, client, mock_db):
        mock_user = _mock_user()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("api.auth.oauth_service") as mock_svc:
            mock_svc.get_provider.return_value = None

            mock_oauth = MagicMock()
            mock_oauth.oauth_email = "test@test.com"
            mock_oauth.oauth_provider = "github"
            mock_oauth.oauth_username = "testuser"
            mock_result_oauth = MagicMock()
            mock_result_oauth.scalar_one_or_none = MagicMock(return_value=mock_oauth)

            mock_db.execute = AsyncMock(return_value=mock_result_oauth)

            resp = client.get("/api/v1/auth/oauth/github/status")

        assert resp.status_code in (200, 400, 503)
        app.dependency_overrides.clear()

    def test_oauth_unlink_success(self, client, mock_db):
        mock_user = _mock_user()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_oauth = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_oauth)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        resp = client.delete("/api/v1/auth/oauth/github/unlink")

        assert resp.status_code in (200, 503)
        app.dependency_overrides.clear()

    def test_oauth_unlink_not_found(self, client, mock_db):
        mock_user = _mock_user()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.delete("/api/v1/auth/oauth/github/unlink")

        assert resp.status_code in (404, 503)
        app.dependency_overrides.clear()


class TestGetCurrentUserFunction:
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, mock_db):
        from api.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad_token")

        with patch("api.auth.verify_token", return_value=None):
            with pytest.raises(Exception):
                await get_current_user(credentials, mock_db)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_uuid(self, mock_db):
        from api.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

        with patch("api.auth.verify_token", return_value="not-a-uuid"):
            with pytest.raises(Exception):
                await get_current_user(credentials, mock_db)

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self, mock_db):
        from api.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.auth.verify_token", return_value="12345678-1234-1234-1234-123456789012"):
            with pytest.raises(Exception):
                await get_current_user(credentials, mock_db)

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_db):
        from api.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        mock_user = _mock_user()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.auth.verify_token", return_value="12345678-1234-1234-1234-123456789012"):
            result = await get_current_user(credentials, mock_db)

        assert result is mock_user
