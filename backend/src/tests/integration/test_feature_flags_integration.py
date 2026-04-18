"""
Integration tests for feature flag system (Issue #972)

Tests:
- FEATURE_USER_ACCOUNTS gates registration/login endpoints
- FEATURE_PREMIUM_FEATURES gates billing endpoints
- FEATURE_API_KEYS gates API key management endpoints
- Graceful fallback when flags are disabled
"""

import pytest
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class TestFeatureFlagGating:
    """Test that feature flags properly gate access to endpoints."""

    async def test_user_registration_blocked_when_flag_disabled(
        self, async_client: AsyncClient, clean_db: AsyncSession
    ):
        """Registration should return 403 when FEATURE_USER_ACCOUNTS is disabled."""
        os.environ["FEATURE_USER_ACCOUNTS"] = "false"

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()

        os.environ["FEATURE_USER_ACCOUNTS"] = "true"

    async def test_user_registration_allowed_when_flag_enabled(
        self, async_client: AsyncClient, clean_db: AsyncSession
    ):
        """Registration should work when FEATURE_USER_ACCOUNTS is enabled."""
        os.environ["FEATURE_USER_ACCOUNTS"] = "true"

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 201
        assert "user_id" in response.json()

    async def test_login_blocked_when_flag_disabled(
        self, async_client: AsyncClient, clean_db: AsyncSession
    ):
        """Login should return 403 when FEATURE_USER_ACCOUNTS is disabled."""
        os.environ["FEATURE_USER_ACCOUNTS"] = "false"

        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()

    async def test_billing_checkout_blocked_when_flag_disabled(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Billing checkout should return 403 when FEATURE_PREMIUM_FEATURES is disabled."""
        os.environ["FEATURE_PREMIUM_FEATURES"] = "false"

        response = await async_client.post(
            "/api/v1/billing/checkout",
            json={"tier": "pro", "trial": True},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()

        os.environ["FEATURE_PREMIUM_FEATURES"] = "true"

    async def test_billing_subscription_blocked_when_flag_disabled(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Billing subscription status should return 403 when FEATURE_PREMIUM_FEATURES is disabled."""
        os.environ["FEATURE_PREMIUM_FEATURES"] = "false"

        response = await async_client.get(
            "/api/v1/billing/subscription",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()

    async def test_api_keys_blocked_when_flag_disabled(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """API key creation should return 403 when FEATURE_API_KEYS is disabled."""
        os.environ["FEATURE_API_KEYS"] = "false"

        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()

        os.environ["FEATURE_API_KEYS"] = "true"

    async def test_api_keys_list_blocked_when_flag_disabled(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """API key listing should return 403 when FEATURE_API_KEYS is disabled."""
        os.environ["FEATURE_API_KEYS"] = "false"

        response = await async_client.get(
            "/api/v1/auth/api-keys",
            headers=auth_headers,
        )

        assert response.status_code == 403


class TestFeatureFlagGracefulFallback:
    """Test that disabled features provide clear error messages."""

    async def test_clear_message_when_user_accounts_disabled(self, async_client: AsyncClient):
        """Error message should indicate feature is disabled, not internal error."""
        os.environ["FEATURE_USER_ACCOUNTS"] = "false"

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 403
        detail = response.json()["detail"].lower()
        assert "disabled" in detail or "contact" in detail

        os.environ["FEATURE_USER_ACCOUNTS"] = "true"

    async def test_clear_message_when_premium_features_disabled(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Error message should indicate premium feature is disabled."""
        os.environ["FEATURE_PREMIUM_FEATURES"] = "false"

        response = await async_client.get(
            "/api/v1/billing/subscription",
            headers=auth_headers,
        )

        assert response.status_code == 403
        detail = response.json()["detail"].lower()
        assert "disabled" in detail or "premium" in detail

    async def test_clear_message_when_api_keys_disabled(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Error message should indicate API keys feature is disabled."""
        os.environ["FEATURE_API_KEYS"] = "false"

        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        detail = response.json()["detail"].lower()
        assert "disabled" in detail or "contact" in detail


class TestFeatureFlagEnvironmentLoading:
    """Test that feature flags load correctly from environment."""

    async def test_flags_loaded_from_env_variables(self):
        """Verify flags load from FEATURE_* environment variables."""
        os.environ["FEATURE_USER_ACCOUNTS"] = "true"
        os.environ["FEATURE_PREMIUM_FEATURES"] = "true"
        os.environ["FEATURE_API_KEYS"] = "true"

        from services.feature_flags import get_feature_flag_manager

        manager = get_feature_flag_manager()

        assert manager.is_enabled("user_accounts") is True
        assert manager.is_enabled("premium_features") is True
        assert manager.is_enabled("api_keys") is True

    async def test_flags_default_to_false(self):
        """Verify flags default to False when not set."""
        os.environ.pop("FEATURE_USER_ACCOUNTS", None)
        os.environ.pop("FEATURE_PREMIUM_FEATURES", None)
        os.environ.pop("FEATURE_API_KEYS", None)

        from services.feature_flags import get_feature_flag_manager

        manager = get_feature_flag_manager()

        assert manager.is_enabled("user_accounts") is False
        assert manager.is_enabled("premium_features") is False
        assert manager.is_enabled("api_keys") is False


class TestFeatureFlagNoCrashOnToggle:
    """Test that toggling flags off doesn't cause crashes."""

    async def test_toggling_user_accounts_off_during_request(
        self, async_client: AsyncClient, clean_db: AsyncSession
    ):
        """Request should fail gracefully if flag is toggled off mid-request."""
        os.environ["FEATURE_USER_ACCOUNTS"] = "true"

        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "toggle_test@example.com",
                "password": "SecurePass123!",
            },
        )

        os.environ["FEATURE_USER_ACCOUNTS"] = "false"

        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "another@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 403

        os.environ["FEATURE_USER_ACCOUNTS"] = "true"
