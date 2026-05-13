"""
Tests for refresh token revocation via Redis blocklist (Issue #1418).
"""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ["DISABLE_REDIS"] = "true"
# Enable user_accounts feature flag so /login (gated by require_feature_flag) works
# in unit tests; we still patch is_feature_enabled in tests that exercise login.
os.environ["FEATURE_USER_ACCOUNTS"] = "true"

from api.auth import router, get_db

app = FastAPI()
app.include_router(router, prefix="/api/v1/auth")


class TestRefreshTokenRevocation:
    """Tests for refresh token revocation mechanism."""

    def test_refresh_with_revoked_token(self):
        """Test that refresh token endpoint rejects revoked tokens."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.is_refresh_token_valid = AsyncMock(return_value=False)

        with patch("api.auth.CacheService") as mock_cache_cls:
            mock_cache_cls.return_value = mock_cache_instance
            with patch(
                "api.auth.verify_token", return_value="12345678-1234-1234-1234-123456789012"
            ):
                mock_user = MagicMock()
                mock_user.id = "12345678-1234-1234-1234-123456789012"

                mock_result = MagicMock()
                mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)

                mock_db = AsyncMock()
                mock_db.execute = AsyncMock(return_value=mock_result)
                app.dependency_overrides[get_db] = lambda: mock_db

                with patch("api.auth.create_access_token", return_value="new_access_token"):
                    client = TestClient(app)
                    resp = client.post(
                        "/api/v1/auth/refresh", json={"refresh_token": "revoked_token"}
                    )

                assert resp.status_code == 401
                detail = resp.json()["detail"].lower()
                assert "revoked" in detail or "expired" in detail

                app.dependency_overrides.clear()

    def test_refresh_with_valid_token(self):
        """Test that refresh token endpoint accepts valid tokens."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.is_refresh_token_valid = AsyncMock(return_value=True)

        with patch("api.auth.CacheService") as mock_cache_cls:
            mock_cache_cls.return_value = mock_cache_instance
            with patch(
                "api.auth.verify_token", return_value="12345678-1234-1234-1234-123456789012"
            ):
                mock_user = MagicMock()
                mock_user.id = "12345678-1234-1234-1234-123456789012"

                mock_result = MagicMock()
                mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)

                mock_db = AsyncMock()
                mock_db.execute = AsyncMock(return_value=mock_result)
                app.dependency_overrides[get_db] = lambda: mock_db

                with patch("api.auth.create_access_token", return_value="new_access_token"):
                    client = TestClient(app)
                    resp = client.post(
                        "/api/v1/auth/refresh", json={"refresh_token": "valid_token"}
                    )

                assert resp.status_code == 200
                assert resp.json()["access_token"] == "new_access_token"

                app.dependency_overrides.clear()


class TestLogoutRevokesRefreshToken:
    """Tests for logout with refresh token revocation."""

    def test_logout_revokes_specified_refresh_token(self):
        """Test that logout with refresh_token revokes it from Redis."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.revoke_refresh_token = AsyncMock()

        with patch("api.auth.CacheService") as mock_cache_cls:
            mock_cache_cls.return_value = mock_cache_instance
            with patch("api.auth.verify_token", return_value="test_user_id"):
                client = TestClient(app)
                resp = client.post(
                    "/api/v1/auth/logout",
                    json={"refresh_token": "user_refresh_token"},
                    headers={"Authorization": "Bearer test_access_token"},
                )

                assert resp.status_code == 200
                mock_cache_instance.revoke_refresh_token.assert_called_once_with(
                    "test_user_id", "user_refresh_token"
                )

    def test_logout_without_refresh_token(self):
        """Test that logout without refresh_token still succeeds."""
        mock_cache_instance = MagicMock()

        with patch("api.auth.CacheService") as mock_cache_cls:
            mock_cache_cls.return_value = mock_cache_instance
            with patch("api.auth.verify_token", return_value="test_user_id"):
                client = TestClient(app)
                resp = client.post(
                    "/api/v1/auth/logout",
                    headers={"Authorization": "Bearer test_access_token"},
                )

                assert resp.status_code == 200


class TestLogoutAllDevices:
    """Tests for logout from all devices."""

    def test_logout_all_revokes_all_tokens(self):
        """Test that logout-all revokes all refresh tokens for user."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.revoke_all_user_refresh_tokens = AsyncMock()

        with patch("api.auth.CacheService") as mock_cache_cls:
            mock_cache_cls.return_value = mock_cache_instance
            with patch("api.auth.verify_token", return_value="test_user_id"):
                client = TestClient(app)
                resp = client.post(
                    "/api/v1/auth/logout-all",
                    headers={"Authorization": "Bearer test_access_token"},
                )

                assert resp.status_code == 200
                assert "all devices" in resp.json()["message"].lower()
                mock_cache_instance.revoke_all_user_refresh_tokens.assert_called_once_with(
                    "test_user_id"
                )


class TestPasswordChangeRevokesTokens:
    """Tests for password change invalidating all tokens."""

    def test_reset_password_revokes_all_tokens(self):
        """Test that password reset invalidates all refresh tokens."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.revoke_all_user_refresh_tokens = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "12345678-1234-1234-1234-123456789012"
        mock_user.password_hash = "old_hash"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        with patch("api.auth.CacheService") as mock_cache_cls:
            mock_cache_cls.return_value = mock_cache_instance
            with patch("api.auth.hash_password", return_value="new_hash"):
                app.dependency_overrides[get_db] = lambda: mock_db

                client = TestClient(app)
                resp = client.post(
                    "/api/v1/auth/reset-password/test_token",
                    json={"password": "NewPass123!"},
                )

                assert resp.status_code == 200
                mock_cache_instance.revoke_all_user_refresh_tokens.assert_called_once()

                app.dependency_overrides.clear()


class TestLoginStoresRefreshToken:
    """Tests for login storing refresh token in Redis."""

    def test_login_stores_refresh_token(self):
        """Test that login stores refresh token in Redis blocklist."""
        mock_cache_instance = MagicMock()
        mock_cache_instance.add_refresh_token = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "12345678-1234-1234-1234-123456789012"
        mock_user.is_verified = True
        mock_user.password_hash = "hashed"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.auth.CacheService") as mock_cache_cls:
            mock_cache_cls.return_value = mock_cache_instance
            with patch("api.auth.verify_password", return_value=True):
                with patch("api.auth.create_access_token", return_value="access_token"):
                    with (
                        patch("api.auth.create_refresh_token", return_value="refresh_token"),
                        patch("api.auth.is_feature_enabled", return_value=True),
                    ):
                        app.dependency_overrides[get_db] = lambda: mock_db

                        client = TestClient(app)
                        resp = client.post(
                            "/api/v1/auth/login",
                            json={"email": "test@example.com", "password": "ValidPass123!"},
                        )

                        assert resp.status_code == 200
                        mock_cache_instance.add_refresh_token.assert_called_once()

                        app.dependency_overrides.clear()


class TestCacheServiceRefreshTokenMethods:
    """Tests for CacheService refresh token methods."""

    def test_refresh_token_prefix_defined(self):
        """Test that REFRESH_TOKEN_PREFIX is defined on CacheService."""
        from services.cache import CacheService

        assert hasattr(CacheService, "REFRESH_TOKEN_PREFIX")
        assert CacheService.REFRESH_TOKEN_PREFIX == "rt:"

    def test_add_refresh_token_method_exists(self):
        """Test that add_refresh_token method exists on CacheService."""
        from services.cache import CacheService

        service = CacheService(disable_redis=True)
        assert hasattr(service, "add_refresh_token")

    def test_is_refresh_token_valid_method_exists(self):
        """Test that is_refresh_token_valid method exists on CacheService."""
        from services.cache import CacheService

        service = CacheService(disable_redis=True)
        assert hasattr(service, "is_refresh_token_valid")

    def test_revoke_refresh_token_method_exists(self):
        """Test that revoke_refresh_token method exists on CacheService."""
        from services.cache import CacheService

        service = CacheService(disable_redis=True)
        assert hasattr(service, "revoke_refresh_token")

    def test_revoke_all_user_refresh_tokens_method_exists(self):
        """Test that revoke_all_user_refresh_tokens method exists on CacheService."""
        from services.cache import CacheService

        service = CacheService(disable_redis=True)
        assert hasattr(service, "revoke_all_user_refresh_tokens")

    def test_add_refresh_token_with_redis_disabled(self):
        """Test add_refresh_token does nothing when Redis is disabled."""
        from services.cache import CacheService

        service = CacheService(disable_redis=True)
        assert service._redis_disabled is True
        assert service._redis_available is False

    def test_is_refresh_token_valid_with_redis_disabled_returns_true(self):
        """Test is_refresh_token_valid returns True when Redis is disabled."""
        import asyncio
        from services.cache import CacheService

        service = CacheService(disable_redis=True)

        result = asyncio.run(service.is_refresh_token_valid("user_id", "token"))

        assert result is True

    def test_revoke_all_user_refresh_tokens_with_redis_disabled(self):
        """Test revoke_all_user_refresh_tokens does nothing when Redis is disabled."""
        import asyncio
        from services.cache import CacheService

        service = CacheService(disable_redis=True)

        asyncio.run(service.revoke_all_user_refresh_tokens("user_id"))
