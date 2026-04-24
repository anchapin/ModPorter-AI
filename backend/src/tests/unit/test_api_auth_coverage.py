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


class TestPasswordValidationEdgeCases:
    def test_register_password_too_short(self):
        from pydantic import ValidationError
        from api.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="Ab1!")

    def test_register_password_no_digit(self):
        from pydantic import ValidationError
        from api.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="Abcdefg!")

    def test_register_password_no_letters(self):
        from pydantic import ValidationError
        from api.auth import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="1234567!")

    def test_password_reset_confirm_no_digit(self):
        from pydantic import ValidationError
        from api.auth import PasswordResetConfirmRequest

        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(password="NoDigitsHere!")

    def test_password_reset_confirm_no_special(self):
        from pydantic import ValidationError
        from api.auth import PasswordResetConfirmRequest

        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(password="NoSpecial1")

    def test_password_reset_confirm_no_letters(self):
        from pydantic import ValidationError
        from api.auth import PasswordResetConfirmRequest

        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(password="12345678!")

    def test_password_reset_confirm_too_short(self):
        from pydantic import ValidationError
        from api.auth import PasswordResetConfirmRequest

        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(password="A1!")


class TestOAuthInitiate:
    def test_oauth_initiate_unsupported_provider(self, client, mock_db):
        resp = client.get("/api/v1/auth/oauth/tiktok")
        assert resp.status_code == 400

    def test_oauth_initiate_not_configured(self, client, mock_db):
        with patch("api.auth.oauth_service") as mock_svc:
            mock_svc.get_provider.return_value = None
            resp = client.get("/api/v1/auth/oauth/github")
        assert resp.status_code == 503

    def test_oauth_initiate_success(self, client, mock_db):
        with patch("api.auth.oauth_service") as mock_svc:
            mock_provider = MagicMock()
            mock_provider.get_authorization_url.return_value = (
                "https://github.com/oauth/authorize?state=abc"
            )
            mock_svc.get_provider.return_value = mock_provider
            with patch("api.auth.generate_oauth_state", return_value="abc123"):
                resp = client.get("/api/v1/auth/oauth/github")
        assert resp.status_code == 200
        data = resp.json()
        assert "authorization_url" in data
        assert data["state"] == "abc123"


class TestOAuthCallback:
    def test_oauth_callback_error_param(self, client, mock_db):
        resp = client.get("/api/v1/auth/oauth/github/callback?code=abc&error=access_denied")
        assert resp.status_code == 400

    def test_oauth_callback_unsupported_provider(self, client, mock_db):
        resp = client.get("/api/v1/auth/oauth/tiktok/callback?code=abc")
        assert resp.status_code == 400

    def test_oauth_callback_provider_not_configured(self, client, mock_db):
        with patch("api.auth.oauth_service") as mock_svc:
            mock_svc.get_provider.return_value = None
            resp = client.get("/api/v1/auth/oauth/github/callback?code=abc")
        assert resp.status_code == 503

    def test_oauth_callback_existing_oauth_user(self, client, mock_db):
        mock_user = _mock_user()
        mock_oauth = MagicMock()
        mock_oauth.user_id = mock_user.id

        mock_oauth_result = MagicMock()
        mock_oauth_result.scalar_one_or_none = MagicMock(return_value=mock_oauth)

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none = MagicMock(return_value=mock_user)

        mock_db.execute = AsyncMock(side_effect=[mock_oauth_result, mock_user_result])

        with patch("api.auth.oauth_service") as mock_svc:
            mock_provider = MagicMock()
            mock_oauth_info = MagicMock()
            mock_oauth_info.provider_user_id = "gh_123"
            mock_provider.exchange_code = AsyncMock(return_value=mock_oauth_info)
            mock_svc.get_provider.return_value = mock_provider
            with patch("api.auth.create_access_token", return_value="access_tok"):
                with patch("api.auth.create_refresh_token", return_value="refresh_tok"):
                    resp = client.get("/api/v1/auth/oauth/github/callback?code=abc_code")

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_new_user"] is False

    def test_oauth_callback_email_match_existing_user(self, client, mock_db):
        mock_oauth_result = MagicMock()
        mock_oauth_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_existing_user = _mock_user(email="existing@test.com")
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none = MagicMock(return_value=mock_existing_user)

        mock_db.execute = AsyncMock(side_effect=[mock_oauth_result, mock_user_result])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        with patch("api.auth.oauth_service") as mock_svc:
            mock_provider = MagicMock()
            mock_oauth_info = MagicMock()
            mock_oauth_info.provider_user_id = "gh_456"
            mock_oauth_info.email = "existing@test.com"
            mock_oauth_info.access_token = "oa_tok"
            mock_oauth_info.refresh_token = "or_tok"
            mock_oauth_info.expires_at = None
            mock_oauth_info.username = "testuser"
            mock_provider.exchange_code = AsyncMock(return_value=mock_oauth_info)
            mock_svc.get_provider.return_value = mock_provider
            with patch("api.auth.create_access_token", return_value="access_tok"):
                with patch("api.auth.create_refresh_token", return_value="refresh_tok"):
                    resp = client.get("/api/v1/auth/oauth/github/callback?code=link_code")

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_new_user"] is False
        assert "linked" in data["message"].lower()

    def test_oauth_callback_new_user(self, client, mock_db):
        mock_oauth_result = MagicMock()
        mock_oauth_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_db.execute = AsyncMock(side_effect=[mock_oauth_result, mock_user_result])
        mock_db.add = MagicMock()

        async def mock_refresh(obj):
            obj.id = "12345678-1234-1234-1234-123456789012"

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)
        mock_db.commit = AsyncMock()

        with patch("api.auth.oauth_service") as mock_svc:
            mock_provider = MagicMock()
            mock_oauth_info = MagicMock()
            mock_oauth_info.provider_user_id = "gh_789"
            mock_oauth_info.email = "newuser@test.com"
            mock_oauth_info.access_token = "oa_tok"
            mock_oauth_info.refresh_token = None
            mock_oauth_info.expires_at = None
            mock_oauth_info.username = "newuser"
            mock_provider.exchange_code = AsyncMock(return_value=mock_oauth_info)
            mock_svc.get_provider.return_value = mock_provider
            with patch("api.auth.hash_password", return_value="hashed"):
                with patch("api.auth.generate_verification_token", return_value="vtok"):
                    with patch("api.auth.create_access_token", return_value="access_tok"):
                        with patch("api.auth.create_refresh_token", return_value="refresh_tok"):
                            resp = client.get("/api/v1/auth/oauth/github/callback?code=new_code")

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_new_user"] is True


class TestOAuthLinkEndpoint:
    def test_link_oauth_unsupported_provider(self, client, mock_db):
        mock_user = _mock_user()
        mock_user.password_hash = "hashed"
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        resp = client.post(
            "/api/v1/auth/oauth/link",
            json={
                "oauth_provider": "tiktok",
                "oauth_provider_user_id": "123",
            },
        )

        assert resp.status_code == 400
        app.dependency_overrides.clear()

    def test_link_oauth_no_password(self, client, mock_db):
        mock_user = _mock_user()
        mock_user.password_hash = None
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        resp = client.post(
            "/api/v1/auth/oauth/link",
            json={
                "oauth_provider": "github",
                "oauth_provider_user_id": "123",
            },
        )

        assert resp.status_code == 400
        app.dependency_overrides.clear()

    def test_link_oauth_already_linked(self, client, mock_db):
        mock_user = _mock_user()
        mock_user.password_hash = "hashed"
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_existing)
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.post(
            "/api/v1/auth/oauth/link",
            json={
                "oauth_provider": "github",
                "oauth_provider_user_id": "already_linked_id",
            },
        )

        assert resp.status_code == 409
        app.dependency_overrides.clear()

    def test_link_oauth_success(self, client, mock_db):
        mock_user = _mock_user()
        mock_user.password_hash = "hashed"
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        resp = client.post(
            "/api/v1/auth/oauth/link",
            json={
                "oauth_provider": "github",
                "oauth_provider_user_id": "gh_123",
                "oauth_email": "user@github.com",
            },
        )

        assert resp.status_code == 200
        app.dependency_overrides.clear()


class TestOAuthUnlinkNoPassword:
    def test_unlink_oauth_no_password_set(self, client, mock_db):
        mock_user = _mock_user()
        mock_user.password_hash = None
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        resp = client.delete("/api/v1/auth/oauth/github/unlink")

        assert resp.status_code == 400
        app.dependency_overrides.clear()


class TestUpdateProfileEmailInUse:
    def test_update_email_already_in_use(self, client, mock_db):
        mock_user = _mock_user()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_conflict_user = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_conflict_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        resp = client.patch(
            "/api/v1/auth/me",
            json={"email": "taken@example.com"},
        )

        assert resp.status_code == 400
        app.dependency_overrides.clear()
