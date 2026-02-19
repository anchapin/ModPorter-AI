import pytest
import asyncio
from unittest.mock import MagicMock
from services.rate_limiter import RateLimiter, RateLimitConfig, RateLimitState

@pytest.mark.asyncio
async def test_rate_limiter_override_config_no_side_effects():
    """
    Verify that passing an override_config to check_rate_limit uses that config
    but does NOT modify the global limiter.config.
    This prevents the race condition where concurrent requests would see the wrong config.
    """
    # Setup
    default_config = RateLimitConfig(requests_per_minute=10, requests_per_hour=100)
    limiter = RateLimiter(config=default_config)

    # Mock request
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "127.0.0.1"
    mock_request.client.host = "127.0.0.1"
    # Mock state for user_id/tier checks
    mock_request.state = MagicMock()
    mock_request.state.user_id = None
    mock_request.state.user_tier = "free"

    # Define an override config
    override_config = RateLimitConfig(requests_per_minute=1000, requests_per_hour=10000)

    # Call check_rate_limit with override (this will fail until we implement the fix)
    # The fix is to add override_config parameter to check_rate_limit
    try:
        is_allowed, metadata = await limiter.check_rate_limit(
            mock_request,
            override_config=override_config
        )
    except TypeError:
        # If the method signature hasn't been updated yet, this test fails as expected
        pytest.fail("check_rate_limit does not accept override_config yet")

    # Assertions
    # 1. The check should have used the override config (limit=1000)
    assert metadata["limit_minute"] == 1000

    # 2. The global config should remain unchanged (limit=10)
    assert limiter.config.requests_per_minute == 10

    # 3. Verify subsequent call without override uses default
    is_allowed_default, metadata_default = await limiter.check_rate_limit(mock_request)
    assert metadata_default["limit_minute"] == 10

@pytest.mark.asyncio
async def test_concurrent_requests_isolation():
    """
    Simulate concurrent requests where one uses default config and another uses override.
    """
    default_config = RateLimitConfig(requests_per_minute=10)
    limiter = RateLimiter(config=default_config)

    mock_req1 = MagicMock()
    mock_req1.headers.get.return_value = "1.1.1.1"
    mock_req1.client.host = "1.1.1.1"
    mock_req1.state.user_id = "user1"
    mock_req1.state.user_tier = "free"

    mock_req2 = MagicMock()
    mock_req2.headers.get.return_value = "2.2.2.2"
    mock_req2.client.host = "2.2.2.2"
    mock_req2.state.user_id = "user2"
    mock_req2.state.user_tier = "free"

    override_config = RateLimitConfig(requests_per_minute=1000)

    # Task 1: Uses default (limit 10)
    async def task1():
        # Add a small delay to ensure overlap if needed, or just run
        await asyncio.sleep(0.01)
        _, meta = await limiter.check_rate_limit(mock_req1)
        return meta["limit_minute"]

    # Task 2: Uses override (limit 1000)
    async def task2():
        await asyncio.sleep(0.01)
        # We need to implement the override_config parameter first
        try:
            _, meta = await limiter.check_rate_limit(mock_req2, override_config=override_config)
            return meta["limit_minute"]
        except TypeError:
             return -1

    # Run concurrently
    limit1, limit2 = await asyncio.gather(task1(), task2())

    assert limit1 == 10, f"Task 1 should see limit 10, saw {limit1}"
    if limit2 != -1:
        assert limit2 == 1000, f"Task 2 should see limit 1000, saw {limit2}"
    else:
        pytest.fail("check_rate_limit signature not updated")
