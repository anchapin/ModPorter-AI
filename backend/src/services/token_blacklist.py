"""
JWT Token Blacklist Service for ModPorter AI

Provides:
- Token invalidation on logout
- Token invalidation on password reset
- Blacklist checking during token verification
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Set
import hashlib

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """
    In-memory token blacklist for invalidating JWTs.

    In production, this should be backed by Redis for persistence
    and cross-instance access.

    Stores token hashes rather than full tokens to minimize memory.
    """

    def __init__(self):
        self._blacklist: Set[str] = set()
        self._expiry: dict[str, datetime] = {}

    def _hash_token(self, token: str) -> str:
        """Create SHA-256 hash of token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()

    def add(self, token: str, expires_delta: Optional[timedelta] = None) -> None:
        """
        Add a token to the blacklist.

        Args:
            token: JWT token to blacklist
            expires_delta: How long to keep in blacklist (default: 15 minutes)
        """
        token_hash = self._hash_token(token)
        self._blacklist.add(token_hash)

        # Set expiry for cleanup
        if expires_delta is None:
            expires_delta = timedelta(minutes=15)
        self._expiry[token_hash] = datetime.now(timezone.utc) + expires_delta

        logger.info(f"Token blacklisted: {token_hash[:16]}...")

    def is_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        token_hash = self._hash_token(token)

        # Cleanup expired entries
        if token_hash in self._expiry:
            if datetime.now(timezone.utc) > self._expiry[token_hash]:
                self._blacklist.discard(token_hash)
                del self._expiry[token_hash]
                return False

        return token_hash in self._blacklist

    def remove(self, token: str) -> bool:
        """
        Remove a token from the blacklist (if needed for testing).

        Args:
            token: JWT token to remove

        Returns:
            True if token was in blacklist, False otherwise
        """
        token_hash = self._hash_token(token)
        if token_hash in self._blacklist:
            self._blacklist.discard(token_hash)
            self._expiry.pop(token_hash, None)
            return True
        return False

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the blacklist.

        Returns:
            Number of entries removed
        """
        now = datetime.now(timezone.utc)
        expired = [token_hash for token_hash, expiry in self._expiry.items() if now > expiry]

        for token_hash in expired:
            self._blacklist.discard(token_hash)
            self._expiry.pop(token_hash, None)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired blacklist entries")

        return len(expired)

    def clear(self) -> None:
        """Clear all entries from the blacklist"""
        self._blacklist.clear()
        self._expiry.clear()


class TokenBlacklistService:
    """
    Service for managing JWT token blacklisting.

    Provides integration points for:
    - Logout endpoint (blacklist access + refresh tokens)
    - Password reset (blacklist all user tokens)
    - Token verification (check blacklist before accepting)
    """

    def __init__(self):
        self._blacklist = TokenBlacklist()

    async def blacklist_token(
        self, token: str, token_type: str = "access", user_id: Optional[str] = None
    ) -> None:
        """
        Blacklist a single JWT token.

        Args:
            token: JWT token to blacklist
            token_type: Type of token (access, refresh)
            user_id: Optional user ID for logging
        """
        # Access tokens expire in 15 min, refresh in 7 days
        if token_type == "refresh":
            expires_delta = timedelta(days=7)
        else:
            expires_delta = timedelta(minutes=15)

        self._blacklist.add(token, expires_delta)

        if user_id:
            logger.info(f"Token blacklisted for user {user_id}: {token_type}")

    async def blacklist_all_user_tokens(self, user_id: str) -> None:
        """
        Blacklist all tokens for a user (e.g., on password reset).

        Note: This only blacklists tokens we see. For full invalidation,
        consider implementing token families or version counters.

        Args:
            user_id: User ID whose tokens should be invalidated
        """
        # For comprehensive token invalidation on password reset,
        # the recommended approach is to increment a user token version
        # and check it during token verification. This method just
        # provides a marker that password was changed.
        logger.info(f"All tokens for user {user_id} should be invalidated via token version check")

        # Store a "password changed" timestamp marker
        # Token verification should check if token was issued before this timestamp
        self._password_changed_marker[user_id] = datetime.now(timezone.utc)

    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted
        """
        return self._blacklist.is_blacklisted(token)

    async def cleanup_expired(self) -> int:
        """Remove expired entries from blacklist"""
        return self._blacklist.cleanup_expired()

    def clear(self) -> None:
        """Clear all blacklist entries (for testing)"""
        self._blacklist.clear()


# Global instance
_token_blacklist_service: Optional[TokenBlacklistService] = None


def get_token_blacklist_service() -> TokenBlacklistService:
    """Get or create the global token blacklist service"""
    global _token_blacklist_service
    if _token_blacklist_service is None:
        _token_blacklist_service = TokenBlacklistService()
    return _token_blacklist_service


# Instance attribute for password change tracking
TokenBlacklistService._password_changed_marker = {}
