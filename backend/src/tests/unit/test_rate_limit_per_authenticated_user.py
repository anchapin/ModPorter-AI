"""Tests for per-authenticated-user rate limiting on endpoint-specific limits.

Issue #1486: Rate limits must scale by user tier even for endpoints with
override configs (e.g. /api/v1/conversions).
"""

import pytest
from unittest.mock import MagicMock
from starlette.datastructures import State

from services.rate_limiter import RateLimiter, RateLimitConfig


@pytest.fixture
def limiter():
    return RateLimiter(config=RateLimitConfig(requests_per_minute=60, requests_per_hour=1000, burst_size=10))


def _make_request(user_id=None, user_tier=None):
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {}
    request.state = State()
    if user_id:
        request.state.user_id = user_id
    if user_tier:
        request.state.user_tier = user_tier
    return request


class TestTierScalingOnEndpointOverrides:
    """Verify that endpoint-specific base configs are scaled by tier."""

    CONVERSION_BASE = RateLimitConfig(requests_per_minute=30, requests_per_hour=300, burst_size=5)

    def test_free_tier_gets_base_config(self, limiter):
        request = _make_request(user_id="u1", user_tier="free")
        config = limiter._get_user_config(request, base_config=self.CONVERSION_BASE)

        assert config.requests_per_minute == 30
        assert config.requests_per_hour == 300
        assert config.burst_size == 5

    def test_pro_tier_gets_6x_base(self, limiter):
        request = _make_request(user_id="u2", user_tier="pro")
        config = limiter._get_user_config(request, base_config=self.CONVERSION_BASE)

        assert config.requests_per_minute == 180  # 30 * 6
        assert config.requests_per_hour == 1800  # 300 * 6
        assert config.burst_size == 30  # 5 * 6

    def test_enterprise_tier_gets_30x_base(self, limiter):
        request = _make_request(user_id="u3", user_tier="enterprise")
        config = limiter._get_user_config(request, base_config=self.CONVERSION_BASE)

        assert config.requests_per_minute == 900  # 30 * 30
        assert config.requests_per_hour == 9000  # 300 * 30
        assert config.burst_size == 150  # 5 * 30

    def test_studio_tier_gets_12x_base(self, limiter):
        request = _make_request(user_id="u4", user_tier="studio")
        config = limiter._get_user_config(request, base_config=self.CONVERSION_BASE)

        assert config.requests_per_minute == 360  # 30 * 12
        assert config.requests_per_hour == 3600  # 300 * 12
        assert config.burst_size == 60  # 5 * 12

    def test_creator_tier_gets_3x_base(self, limiter):
        request = _make_request(user_id="u5", user_tier="creator")
        config = limiter._get_user_config(request, base_config=self.CONVERSION_BASE)

        assert config.requests_per_minute == 90  # 30 * 3
        assert config.requests_per_hour == 900  # 300 * 3
        assert config.burst_size == 15  # 5 * 3

    def test_premium_tier_gets_30x_base(self, limiter):
        request = _make_request(user_id="u6", user_tier="premium")
        config = limiter._get_user_config(request, base_config=self.CONVERSION_BASE)

        assert config.requests_per_minute == 900
        assert config.requests_per_hour == 9000
        assert config.burst_size == 150

    def test_unknown_tier_gets_base(self, limiter):
        request = _make_request(user_id="u7", user_tier="unknown")
        config = limiter._get_user_config(request, base_config=self.CONVERSION_BASE)

        assert config.requests_per_minute == 30
        assert config.requests_per_hour == 300
        assert config.burst_size == 5


class TestNoBaseConfigUsesTierDirectly:
    """Without endpoint-specific override, tier limits apply directly."""

    def test_free_tier_no_override(self, limiter):
        request = _make_request(user_id="u1", user_tier="free")
        config = limiter._get_user_config(request)

        assert config.requests_per_minute == 10
        assert config.requests_per_hour == 50

    def test_pro_tier_no_override(self, limiter):
        request = _make_request(user_id="u2", user_tier="pro")
        config = limiter._get_user_config(request)

        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 500

    def test_enterprise_tier_no_override(self, limiter):
        request = _make_request(user_id="u3", user_tier="enterprise")
        config = limiter._get_user_config(request)

        assert config.requests_per_minute == 300
        assert config.requests_per_hour == 5000


class TestClientKeyPerUser:
    """Authenticated users get per-user keys, not per-IP."""

    def test_authenticated_user_key(self, limiter):
        request = _make_request(user_id="user-42", user_tier="pro")
        key = limiter._get_client_key(request)

        assert key == "user:user-42"

    def test_anonymous_user_key(self, limiter):
        request = _make_request()
        key = limiter._get_client_key(request)

        assert key.startswith("ip:")


class TestApplyTierToBaseUnit:
    """Unit tests for the _apply_tier_to_base helper."""

    def test_zero_free_rpm_falls_back(self, limiter):
        tier_limits = {"free": RateLimitConfig(requests_per_minute=0, requests_per_hour=0, burst_size=0)}
        base = RateLimitConfig(requests_per_minute=30, requests_per_hour=300, burst_size=5)

        result = limiter._apply_tier_to_base(base, "free", tier_limits)
        assert result.requests_per_minute == 30  # falls back to base

    def test_minimum_floor_of_one(self, limiter):
        tier_limits = {
            "free": RateLimitConfig(requests_per_minute=10, requests_per_hour=50, burst_size=3),
            "free": RateLimitConfig(requests_per_minute=1, requests_per_hour=1, burst_size=1),
        }
        base = RateLimitConfig(requests_per_minute=1, requests_per_hour=1, burst_size=1)

        result = limiter._apply_tier_to_base(base, "free", tier_limits)
        assert result.requests_per_minute >= 1
        assert result.requests_per_hour >= 1
        assert result.burst_size >= 1
