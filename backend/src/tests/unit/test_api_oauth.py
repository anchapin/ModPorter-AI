"""
Unit tests for OAuth functionality.

Issue #980: Add OAuth login (Discord, GitHub, Google)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.auth import router, get_current_user, get_db


app = FastAPI()
app.include_router(router, prefix="/api/v1/auth")


@pytest.fixture
def mock_db():
    """Mock database session."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    mock.delete = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture
def client(mock_db):
    """Create test client with mocked dependencies."""
    from api.auth import get_db

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
                                "api.auth.generate_reset_token", return_value="test_reset_token"
                            ):
                                with patch(
                                    "api.auth.generate_api_key",
                                    return_value=("full_key_123", "prefix_123"),
                                ):
                                    with patch("api.auth.hash_api_key", return_value="hashed_key"):
                                        with patch(
                                            "api.auth.is_feature_enabled", return_value=True
                                        ):
                                            yield TestClient(app)

    app.dependency_overrides.clear()


class TestOAuthAuthorizationEndpoint:
    """Tests for GET /oauth/{provider} endpoint."""

    def test_get_unsupported_provider(self, client, mock_db):
        """Test getting authorization URL for unsupported provider."""
        response = client.get("/api/v1/auth/oauth/invalid_provider")

        assert response.status_code == 400
        assert "Unsupported OAuth provider" in response.json()["detail"]

    def test_get_discord_auth_url_success(self, client, mock_db):
        """Test getting Discord authorization URL returns valid structure."""
        mock_oauth_provider = MagicMock()
        mock_oauth_provider.get_authorization_url.return_value = (
            "https://discord.com/api/oauth2/authorize?client_id=test"
        )

        with patch("api.auth.oauth_service") as mock_oauth_service:
            mock_oauth_instance = MagicMock()
            mock_oauth_instance.get_provider.return_value = mock_oauth_provider
            mock_oauth_service.return_value = mock_oauth_instance

            response = client.get("/api/v1/auth/oauth/discord")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data

    def test_get_github_auth_url_success(self, client, mock_db):
        """Test getting GitHub authorization URL returns valid structure."""
        mock_oauth_provider = MagicMock()
        mock_oauth_provider.get_authorization_url.return_value = (
            "https://github.com/login/oauth/authorize?client_id=test"
        )

        with patch("api.auth.oauth_service") as mock_oauth_service:
            mock_oauth_instance = MagicMock()
            mock_oauth_instance.get_provider.return_value = mock_oauth_provider
            mock_oauth_service.return_value = mock_oauth_instance

            response = client.get("/api/v1/auth/oauth/github")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data

    def test_get_google_auth_url_success(self, client, mock_db):
        """Test getting Google authorization URL returns valid structure."""
        mock_oauth_provider = MagicMock()
        mock_oauth_provider.get_authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?client_id=test"
        )

        with patch("api.auth.oauth_service") as mock_oauth_service:
            mock_oauth_instance = MagicMock()
            mock_oauth_instance.get_provider.return_value = mock_oauth_provider
            mock_oauth_service.return_value = mock_oauth_instance

            response = client.get("/api/v1/auth/oauth/google")

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data


class TestOAuthStatusEndpoint:
    """Tests for GET /oauth/{provider}/status endpoint."""

    def test_get_oauth_status_connected(self, client, mock_db):
        """Test getting OAuth status when connected."""
        mock_user = MagicMock()
        mock_user.id = "test_user_id"

        mock_oauth_account = MagicMock()
        mock_oauth_account.oauth_email = "test@example.com"
        mock_oauth_account.oauth_username = "testuser"

        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_oauth_account)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.auth.oauth_service") as mock_oauth_service:
            mock_oauth_instance = MagicMock()
            mock_oauth_instance.is_provider_enabled.return_value = True
            mock_oauth_service.return_value = mock_oauth_instance

            response = client.get(
                "/api/v1/auth/oauth/discord/status",
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "discord"
        assert data["enabled"] is True
        assert data["connected"] is True
        assert data["email"] == "test@example.com"

        app.dependency_overrides.clear()

    def test_get_oauth_status_not_connected(self, client, mock_db):
        """Test getting OAuth status when not connected."""
        mock_user = MagicMock()
        mock_user.id = "test_user_id"

        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.auth.oauth_service") as mock_oauth_service:
            mock_oauth_instance = MagicMock()
            mock_oauth_instance.is_provider_enabled.return_value = True
            mock_oauth_service.return_value = mock_oauth_instance

            response = client.get(
                "/api/v1/auth/oauth/github/status",
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "github"
        assert data["enabled"] is True
        assert data["connected"] is False

        app.dependency_overrides.clear()


class TestOAuthUnlinkEndpoint:
    """Tests for DELETE /oauth/{provider}/unlink endpoint."""

    def test_unlink_oauth_success(self, client, mock_db):
        """Test successfully unlinking OAuth account."""
        mock_user = MagicMock()
        mock_user.id = "test_user_id"
        mock_user.password_hash = "hashed_password"

        mock_oauth_account = MagicMock()
        mock_oauth_account.id = "oauth_id"

        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_oauth_account)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.auth.oauth_service") as mock_oauth_service:
            mock_oauth_instance = MagicMock()
            mock_oauth_instance.is_provider_enabled.return_value = True
            mock_oauth_service.return_value = mock_oauth_instance

            response = client.delete(
                "/api/v1/auth/oauth/discord/unlink",
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == 200
        assert "unlinked" in response.json()["message"]

        app.dependency_overrides.clear()

    def test_unlink_oauth_no_password(self, client, mock_db):
        """Test unlinking OAuth when user has no password fails."""
        mock_user = MagicMock()
        mock_user.id = "test_user_id"
        mock_user.password_hash = None

        app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.delete(
            "/api/v1/auth/oauth/discord/unlink",
            headers={"Authorization": "Bearer test_token"},
        )

        assert response.status_code == 400
        assert "last authentication method" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_unlink_oauth_not_linked(self, client, mock_db):
        """Test unlinking OAuth that is not linked fails."""
        mock_user = MagicMock()
        mock_user.id = "test_user_id"
        mock_user.password_hash = "hashed_password"

        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.auth.oauth_service") as mock_oauth_service:
            mock_oauth_instance = MagicMock()
            mock_oauth_instance.is_provider_enabled.return_value = True
            mock_oauth_service.return_value = mock_oauth_instance

            response = client.delete(
                "/api/v1/auth/oauth/discord/unlink",
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == 404

        app.dependency_overrides.clear()
