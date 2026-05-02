"""
Tests for billing API endpoints (Issue #1226)

Tests:
- PAYG credit pack checkout
- Credit balance retrieval
- BYOK subscription tiers
- Updated Free tier limits (1 conversion/month)
"""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4, UUID


@pytest.mark.asyncio
async def test_create_credits_checkout(async_client, auth_headers):
    """Test creating a PAYG credit pack checkout session"""
    with patch("services.feature_flags.is_feature_enabled") as mock_feature:
        mock_feature.return_value = True

        with patch("api.billing.get_stripe") as mock_stripe:
            mock_stripe_instance = MagicMock()
            mock_stripe.return_value = mock_stripe_instance

            mock_customer = MagicMock()
            mock_customer.id = "cus_test_123"
            mock_stripe_instance.Customer.create.return_value = mock_customer

            mock_session = MagicMock()
            mock_session.id = "cs_test_123"
            mock_session.url = "https://checkout.stripe.com/cs_test_123"

            mock_stripe_instance.checkout.sessions.create.return_value = mock_session

            response = await async_client.post(
                "/api/v1/billing/credits/checkout",
                json={"credit_pack": "credits_5"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "cs_test_123"
            assert data["credits"] == 5


@pytest.mark.asyncio
async def test_create_credits_checkout_invalid_pack(async_client, auth_headers):
    """Test creating checkout with invalid credit pack"""
    with patch("services.feature_flags.is_feature_enabled") as mock_feature:
        mock_feature.return_value = True

        response = await async_client.post(
            "/api/v1/billing/credits/checkout",
            json={"credit_pack": "invalid_pack"},
            headers=auth_headers,
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_credits_checkout_feature_disabled(async_client, auth_headers):
    """Test creating credits checkout when feature is disabled"""
    with patch("services.feature_flags.is_feature_enabled") as mock_feature:
        mock_feature.return_value = False

        response = await async_client.post(
            "/api/v1/billing/credits/checkout",
            json={"credit_pack": "credits_5"},
            headers=auth_headers,
        )

        assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_credit_balance(async_client, auth_headers, db_session):
    """Test retrieving credit balance"""
    from db.models import UserCredits
    from security.auth import verify_token

    token = auth_headers["Authorization"].replace("Bearer ", "")
    user_id_str = verify_token(token)
    user_id = UUID(user_id_str)

    credit_record = UserCredits(
        user_id=user_id,
        balance=10,
        lifetime_purchased=25,
    )
    db_session.add(credit_record)
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/billing/credits/balance",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 10
    assert data["lifetime_purchased"] == 25


@pytest.mark.asyncio
async def test_get_credit_balance_no_credits(async_client, auth_headers):
    """Test retrieving credit balance when user has no credits"""
    response = await async_client.get(
        "/api/v1/billing/credits/balance",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 0
    assert data["lifetime_purchased"] == 0


@pytest.mark.asyncio
async def test_free_tier_limits_in_metering():
    """Test that Free tier has correct limits (1 conversion/month, 5MB JAR)"""
    from services.metering_service import TIER_LIMITS

    free_limits = TIER_LIMITS.get("free", {})
    assert free_limits["monthly_conversions"] == 1
    assert free_limits["max_jar_size_mb"] == 5


@pytest.mark.asyncio
async def test_byok_tier_limits():
    """Test that BYOK tiers have correct limits"""
    from services.metering_service import TIER_LIMITS

    creator_byok = TIER_LIMITS.get("creator_byok", {})
    assert creator_byok["monthly_conversions"] == -1
    assert creator_byok["has_api_access"] == False

    studio_byok = TIER_LIMITS.get("studio_byok", {})
    assert studio_byok["monthly_api_calls"] == 500
    assert studio_byok["has_api_access"] == True


@pytest.mark.asyncio
async def test_checkout_with_byok_tier(async_client, auth_headers):
    """Test creating checkout for BYOK tier"""
    with patch("services.feature_flags.is_feature_enabled") as mock_feature:
        mock_feature.return_value = True

        with patch("api.billing.get_stripe") as mock_stripe:
            mock_stripe_instance = MagicMock()
            mock_stripe.return_value = mock_stripe_instance

            mock_customer = MagicMock()
            mock_customer.id = "cus_test_byok"
            mock_stripe_instance.Customer.create.return_value = mock_customer

            mock_session = MagicMock()
            mock_session.id = "cs_test_byok"
            mock_session.url = "https://checkout.stripe.com/cs_test_byok"

            mock_stripe_instance.checkout.sessions.create.return_value = mock_session

            response = await async_client.post(
                "/api/v1/billing/checkout",
                json={"tier": "creator_byok", "trial": True},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "cs_test_byok"


@pytest.mark.asyncio
async def test_webhook_handles_credits_purchase():
    """Test that webhook handler processes credit purchases correctly"""
    from api.billing import handle_credits_purchase
    from unittest.mock import AsyncMock
    import uuid

    mock_db = AsyncMock()

    session_data = {
        "metadata": {
            "user_id": str(uuid.uuid4()),
            "credits": "12",
        }
    }

    with patch("api.billing.UUID") as mock_uuid:
        mock_uuid.return_value = uuid.uuid4()

        with patch("api.billing.select") as mock_select:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result

            await handle_credits_purchase(session_data, mock_db)

            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()


def test_byok_feature_flag_registered():
    """Test that byok_enabled flag is registered"""
    from services.feature_flags import get_feature_flag_manager

    manager = get_feature_flag_manager()
    flag = manager.get_flag("byok_enabled")

    assert flag is not None
    assert flag.description == "Enable BYOK (Bring Your Own Key) functionality for users to supply their own LLM API keys"


def test_payg_credits_feature_flag_registered():
    """Test that payg_credits flag is registered"""
    from services.feature_flags import get_feature_flag_manager

    manager = get_feature_flag_manager()
    flag = manager.get_flag("payg_credits")

    assert flag is not None
    assert "PAYG credit pack purchases" in flag.description


def test_updated_free_tier_in_usage_response():
    """Test Free tier shows 1 conversion limit in usage info"""
    from services.metering_service import TIER_LIMITS, UPGRADE_THRESHOLD

    free = TIER_LIMITS["free"]
    assert free["monthly_conversions"] == 1
    assert free["max_jar_size_mb"] == 5