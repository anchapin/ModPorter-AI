"""
Unit tests for rate_limiter service.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import Request
from services.rate_limiter import (
    RateLimitConfig,
    RateLimitState,
    RateLimiter,
    RateLimitMiddleware,
    create_global_limiter,
    get_rate_limiter,
    check_rate_limit,
)


class TestRateLimitConfig:
    def test_rate_limit_config_init(self):
        """Test RateLimitConfig can be created."""
        config = RateLimitConfig(requests_per_minute=100, requests_per_hour=1000)
        assert config.requests_per_minute == 100
        assert config.requests_per_hour == 1000

    def test_rate_limit_config_defaults(self):
        """Test RateLimitConfig default values."""
        config = RateLimitConfig()
        assert config.requests_per_minute > 0
        assert config.requests_per_hour > 0
        assert config.burst_size > 0


class TestRateLimitState:
    def test_rate_limit_state_init(self):
        """Test RateLimitState can be created."""
        state = RateLimitState()
        assert state.request_count == 0
        assert state.tokens == 0.0

    def test_rate_limit_state_reset(self):
        """Test RateLimitState reset."""
        state = RateLimitState()
        state.request_count = 5
        state.reset_window()
        assert state.request_count == 0


class TestRateLimiter:
    @pytest.fixture
    def limiter(self):
        return RateLimiter()

    def test_limiter_init(self, limiter):
        """Test RateLimiter initializes."""
        assert limiter is not None

    def test_limiter_has_config(self, limiter):
        """Test RateLimiter has config."""
        assert hasattr(limiter, 'config') or hasattr(limiter, '_config')

    def test_limiter_has_check_rate_limit(self, limiter):
        """Test RateLimiter has check_rate_limit method."""
        assert hasattr(limiter, 'check_rate_limit')


class TestRateLimitMiddleware:
    def test_middleware_init(self):
        """Test RateLimitMiddleware can be initialized."""
        mock_app = MagicMock()
        mock_limiter = MagicMock()
        middleware = RateLimitMiddleware(mock_app, mock_limiter)
        assert middleware.app is mock_app
        assert middleware.rate_limiter is mock_limiter


class TestModuleFunctions:
    def test_create_global_limiter(self):
        """Test create_global_limiter returns a limiter."""
        limiter = create_global_limiter()
        assert limiter is not None

    def test_get_rate_limiter(self):
        """Test get_rate_limiter is callable."""
        assert callable(get_rate_limiter)

    def test_check_rate_limit_function(self):
        """Test check_rate_limit function exists."""
        assert callable(check_rate_limit)
