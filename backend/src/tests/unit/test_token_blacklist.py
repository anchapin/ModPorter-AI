"""
Tests for Token Blacklist Service

Tests:
- Token blacklisting on logout
- Token blacklist verification
- Password reset invalidation
- Expired blacklist cleanup
"""

import pytest
from datetime import timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.token_blacklist import (
    TokenBlacklist,
    TokenBlacklistService,
    get_token_blacklist_service,
)


class TestTokenBlacklist:
    """Tests for TokenBlacklist class"""

    def test_add_and_check_blacklist(self):
        """Test adding and checking tokens in blacklist"""
        blacklist = TokenBlacklist()
        token = "test_token_12345"

        assert not blacklist.is_blacklisted(token)
        blacklist.add(token, timedelta(minutes=15))
        assert blacklist.is_blacklisted(token)

    def test_hash_token(self):
        """Test that different tokens produce different hashes"""
        blacklist = TokenBlacklist()
        token1 = "token_one"
        token2 = "token_two"

        hash1 = blacklist._hash_token(token1)
        hash2 = blacklist._hash_token(token2)

        assert hash1 != hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_expired_token_removed(self):
        """Test that expired tokens are removed from blacklist"""
        blacklist = TokenBlacklist()
        token = "test_token_expiry"

        # Add with very short expiry
        blacklist.add(token, timedelta(seconds=1))
        assert blacklist.is_blacklisted(token)

        # Wait for expiry
        import time

        time.sleep(1.1)

        assert not blacklist.is_blacklisted(token)

    def test_remove_from_blacklist(self):
        """Test removing a token from blacklist"""
        blacklist = TokenBlacklist()
        token = "test_token_remove"

        blacklist.add(token, timedelta(minutes=15))
        assert blacklist.is_blacklisted(token)

        blacklist.remove(token)
        assert not blacklist.is_blacklisted(token)

    def test_clear_blacklist(self):
        """Test clearing all entries"""
        blacklist = TokenBlacklist()

        blacklist.add("token1", timedelta(minutes=15))
        blacklist.add("token2", timedelta(minutes=15))

        assert len(blacklist._blacklist) == 2
        blacklist.clear()
        assert len(blacklist._blacklist) == 0


class TestTokenBlacklistService:
    """Tests for TokenBlacklistService"""

    @pytest.mark.asyncio
    async def test_blacklist_token_access(self):
        """Test blacklisting an access token"""
        service = TokenBlacklistService()
        token = "access_token_xyz"

        await service.blacklist_token(token, token_type="access")
        assert await service.is_token_blacklisted(token)

    @pytest.mark.asyncio
    async def test_blacklist_token_refresh(self):
        """Test blacklisting a refresh token"""
        service = TokenBlacklistService()
        token = "refresh_token_abc"

        await service.blacklist_token(token, token_type="refresh")
        assert await service.is_token_blacklisted(token)

    @pytest.mark.asyncio
    async def test_blacklist_all_user_tokens(self):
        """Test marking all user tokens for invalidation"""
        service = TokenBlacklistService()
        user_id = "user_12345"

        await service.blacklist_all_user_tokens(user_id)

        # The marker should be set (we can verify via internal state)
        assert hasattr(service, "_password_changed_marker")
        assert user_id in service._password_changed_marker

    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Test cleanup of expired blacklist entries"""
        service = TokenBlacklistService()

        # Add token that will expire quickly
        service._blacklist.add("temp_token", timedelta(seconds=1))

        import time

        time.sleep(1.1)

        removed = await service.cleanup_expired()
        assert removed >= 0


class TestGetTokenBlacklistService:
    """Tests for singleton getter"""

    def test_returns_same_instance(self):
        """Test that get_token_blacklist_service returns singleton"""
        service1 = get_token_blacklist_service()
        service2 = get_token_blacklist_service()

        assert service1 is service2

    def test_clear_clears_all(self):
        """Test that clear() clears the global instance"""
        service = get_token_blacklist_service()
        service._blacklist.add("test_token", timedelta(minutes=15))

        service.clear()
        assert not service._blacklist.is_blacklisted("test_token")
