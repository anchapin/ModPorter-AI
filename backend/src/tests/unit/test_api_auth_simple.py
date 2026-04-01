"""
Simple unit tests for auth API endpoints.

Issue: 0% coverage for src/api/auth.py (188 stmts)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.auth import router, get_current_user, get_db


app = FastAPI()
app.include_router(router, prefix="/api/v1")


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
    from api.auth import get_db, get_current_user

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
                                        yield TestClient(app)

    app.dependency_overrides.clear()


class TestRegisterEndpoint:
    """Tests for POST /register endpoint."""

    def test_register_success(self, client, mock_db):
        """Test successful user registration."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(
            "/api/v1/auth/register", json={"email": "test@example.com", "password": "Test1234!"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert "user_id" in data

    def test_register_duplicate_email(self, client, mock_db):
        """Test registration with duplicate email fails."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(
            "/api/v1/auth/register", json={"email": "existing@example.com", "password": "Test1234!"}
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_weak_password(self, client):
        """Test registration with weak password fails."""
        response = client.post(
            "/api/v1/auth/register", json={"email": "test@example.com", "password": "weak"}
        )

        assert response.status_code == 422


class TestLoginEndpoint:
    """Tests for POST /login endpoint."""

    def test_login_success(self, client, mock_db):
        """Test successful login."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"
        mock_user.email = "test@example.com"
        mock_user.password_hash = "hashed_password"
        mock_user.is_verified = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.auth.verify_password", return_value=True):
            response = client.post(
                "/api/v1/auth/login", json={"email": "test@example.com", "password": "Test1234!"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_invalid_email(self, client, mock_db):
        """Test login with invalid email fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(
            "/api/v1/auth/login", json={"email": "wrong@example.com", "password": "Test1234!"}
        )

        assert response.status_code == 401

    def test_login_invalid_password(self, client, mock_db):
        """Test login with invalid password fails."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"
        mock_user.email = "test@example.com"
        mock_user.password_hash = "hashed_password"
        mock_user.is_verified = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.auth.verify_password", return_value=False):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "WrongPassword1!"},
            )

        assert response.status_code == 401

    def test_login_unverified_email(self, client, mock_db):
        """Test login with unverified email fails."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"
        mock_user.email = "test@example.com"
        mock_user.password_hash = "hashed_password"
        mock_user.is_verified = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.auth.verify_password", return_value=True):
            response = client.post(
                "/api/v1/auth/login", json={"email": "test@example.com", "password": "Test1234!"}
            )

        assert response.status_code == 403


class TestLogoutEndpoint:
    """Tests for POST /logout endpoint."""

    def test_logout_success(self, client):
        """Test successful logout."""
        response = client.post(
            "/api/v1/auth/logout", headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()


class TestRefreshEndpoint:
    """Tests for POST /refresh endpoint."""

    def test_refresh_success(self, client, mock_db):
        """Test successful token refresh."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post("/api/v1/auth/refresh", json={"refresh_token": "test_refresh_token"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_refresh_invalid_token(self, client, mock_db):
        """Test refresh with invalid token fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.auth.verify_token", return_value=None):
            response = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid_token"})

        assert response.status_code == 401


class TestVerifyEmailEndpoint:
    """Tests for GET /verify-email/{token} endpoint."""

    def test_verify_email_success(self, client, mock_db):
        """Test successful email verification."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"
        mock_user.is_verified = False
        mock_user.verification_token = "test_token"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/v1/auth/verify-email/test_token")

        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()

    def test_verify_email_invalid_token(self, client, mock_db):
        """Test verification with invalid token fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.get("/api/v1/auth/verify-email/invalid_token")

        assert response.status_code == 400


class TestForgotPasswordEndpoint:
    """Tests for POST /forgot-password endpoint."""

    def test_forgot_password_existing_user(self, client, mock_db):
        """Test forgot password with existing user."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post("/api/v1/auth/forgot-password", json={"email": "test@example.com"})

        assert response.status_code == 200
        assert "reset" in response.json()["message"].lower()

    def test_forgot_password_nonexistent_user(self, client, mock_db):
        """Test forgot password with non-existent user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(
            "/api/v1/auth/forgot-password", json={"email": "nonexistent@example.com"}
        )

        assert response.status_code == 200


class TestResetPasswordEndpoint:
    """Tests for POST /reset-password/{token} endpoint."""

    def test_reset_password_success(self, client, mock_db):
        """Test successful password reset."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"
        mock_user.reset_token = "test_token"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(
            "/api/v1/auth/reset-password/test_token", json={"password": "NewPassword1!"}
        )

        assert response.status_code == 200
        assert "success" in response.json()["message"].lower()

    def test_reset_password_invalid_token(self, client, mock_db):
        """Test reset with invalid token fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.post(
            "/api/v1/auth/reset-password/invalid_token", json={"password": "NewPassword1!"}
        )

        assert response.status_code == 400


class TestMeEndpoint:
    """Tests for GET /me and PATCH /me endpoints."""

    def test_get_me_success(self, client, mock_db):
        """Test getting current user profile."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"
        mock_user.email = "test@example.com"
        mock_user.is_verified = True
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.conversion_count = 5

        app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["is_verified"] is True

        app.dependency_overrides.clear()

    def test_patch_me_success(self, client, mock_db):
        """Test updating current user profile."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"
        mock_user.email = "test@example.com"
        mock_user.is_verified = True
        mock_user.created_at = datetime.now(timezone.utc)

        app.dependency_overrides[get_current_user] = lambda: mock_user

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.patch("/api/v1/auth/me", json={"email": "newemail@example.com"})

        assert response.status_code == 200

        app.dependency_overrides.clear()

    def test_delete_me_success(self, client, mock_db):
        """Test deleting current user account."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"

        app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.delete("/api/v1/auth/me")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        app.dependency_overrides.clear()

    def test_patch_me_success(self, client, mock_db):
        """Test updating current user profile."""
        from db.models import User
        from api.auth import get_current_user, get_db

        mock_user = MagicMock()
        mock_user.id = "test_id"
        mock_user.email = "test@example.com"
        mock_user.is_verified = True
        mock_user.created_at = datetime.now(timezone.utc)

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.patch("/api/v1/auth/me", json={"email": "newemail@example.com"})

        assert response.status_code == 200

        app.dependency_overrides.clear()

    def test_delete_me_success(self, client, mock_db):
        """Test deleting current user account."""
        from db.models import User
        from api.auth import get_current_user, get_db

        mock_user = MagicMock()
        mock_user.id = "test_id"

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        response = client.delete("/api/v1/auth/me")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        app.dependency_overrides.clear()

    def test_patch_me_success(self, client, mock_db):
        """Test updating current user profile."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"
        mock_user.email = "test@example.com"
        mock_user.is_verified = True
        mock_user.created_at = datetime.now(timezone.utc)

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = client.patch("/api/v1/auth/me", json={"email": "newemail@example.com"})

        assert response.status_code == 200

        app.dependency_overrides.clear()

    def test_delete_me_success(self, client, mock_db):
        """Test deleting current user account."""
        from db.models import User

        mock_user = MagicMock()
        mock_user.id = "test_id"

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        response = client.delete("/api/v1/auth/me")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        app.dependency_overrides.clear()
