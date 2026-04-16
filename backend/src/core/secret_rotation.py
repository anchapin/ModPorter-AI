"""
Secret Rotation Framework for ModPorter AI

Provides:
- Support for rotating JWT secret keys
- Grace period for old keys during rotation
- Version tracking for secrets
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from threading import Lock

logger = logging.getLogger(__name__)


class SecretRotationManager:
    """
    Manages secret key rotation with grace periods.

    During rotation:
    1. New secret is introduced
    2. Old secret remains valid for a grace period
    3. After grace period, old secret is invalidated

    Usage:
        manager = SecretRotationManager()
        manager.rotate_secret("new_secret_key", grace_period_hours=24)

        # Later, verify using current secret
        if manager.is_valid_secret(secret_key):
            ...
    """

    def __init__(self, secret_env_var: str = "JWT_SECRET_KEY"):
        self.secret_env_var = secret_env_var
        self._current_secret: Optional[str] = None
        self._previous_secret: Optional[str] = None
        self._secret_version: int = 0
        self._previous_expires: Optional[datetime] = None
        self._lock = Lock()

        # Load initial secret
        self._current_secret = os.getenv(secret_env_var) or os.getenv("SECRET_KEY")
        if self._current_secret:
            self._secret_version = 1

    @property
    def current_secret(self) -> Optional[str]:
        """Get current active secret"""
        return self._current_secret

    @property
    def secret_version(self) -> int:
        """Get current secret version number"""
        return self._secret_version

    def rotate_secret(self, new_secret: str, grace_period_hours: int = 24) -> bool:
        """
        Rotate to a new secret key.

        Args:
            new_secret: New secret key to use
            grace_period_hours: Hours to keep old secret valid

        Returns:
            True if rotation succeeded
        """
        with self._lock:
            if new_secret == self._current_secret:
                logger.warning("New secret is same as current secret, skipping rotation")
                return False

            # Demote current to previous
            self._previous_secret = self._current_secret
            self._previous_expires = datetime.now(timezone.utc) + timedelta(
                hours=grace_period_hours
            )

            # Promote new secret
            self._current_secret = new_secret
            self._secret_version += 1

            # Set environment variable for persistence
            os.environ[self.secret_env_var] = new_secret

            return True

    def is_valid_secret(self, secret: str) -> bool:
        """
        Check if a secret is currently valid.

        Args:
            secret: Secret key to validate

        Returns:
            True if secret is current or within grace period
        """
        if secret == self._current_secret:
            return True

        # Check grace period for previous secret
        if secret == self._previous_secret:
            if self._previous_expires and datetime.now(timezone.utc) < self._previous_expires:
                return True
            else:
                # Grace period expired, clear previous
                self._previous_secret = None
                self._previous_expires = None

        return False

    def get_active_secrets(self) -> List[str]:
        """
        Get list of currently valid secrets (current + valid previous).

        Returns:
            List of valid secret keys
        """
        secrets = []
        if self._current_secret:
            secrets.append(self._current_secret)
        if self._previous_secret and self._previous_expires:
            if datetime.now(timezone.utc) < self._previous_expires:
                secrets.append(self._previous_secret)
        return secrets

    def revoke_previous_secret(self) -> bool:
        """
        Immediately revoke the previous secret (end grace period early).

        Returns:
            True if there was a previous secret to revoke
        """
        if self._previous_secret:
            logger.info("Previous secret revoked immediately")
            self._previous_secret = None
            self._previous_expires = None
            return True
        return False

    def get_status(self) -> Dict:
        """
        Get current rotation status.

        Returns:
            Dictionary with rotation status information
        """
        return {
            "current_version": self._secret_version,
            "has_previous": self._previous_secret is not None,
            "previous_expires": self._previous_expires.isoformat()
            if self._previous_expires
            else None,
            "grace_period_remaining_hours": (
                (self._previous_expires - datetime.now(timezone.utc)).total_seconds() / 3600
                if self._previous_expires and datetime.now(timezone.utc) < self._previous_expires
                else 0
            ),
        }


class JWTSecretValidator:
    """
    Validates JWT tokens against multiple secrets during rotation.

    Tries current secret first, then previous secret during grace period.
    """

    def __init__(self, rotation_manager: Optional[SecretRotationManager] = None):
        self.rotation_manager = rotation_manager or SecretRotationManager()

    def is_valid(self, secret: str) -> bool:
        """Check if secret is valid (current or in grace period)"""
        return self.rotation_manager.is_valid_secret(secret)

    def get_current_secret(self) -> Optional[str]:
        """Get current secret for token creation"""
        return self.rotation_manager.current_secret


# Global instance
_secret_rotation_manager: Optional[SecretRotationManager] = None


def get_secret_rotation_manager() -> SecretRotationManager:
    """Get or create the global secret rotation manager"""
    global _secret_rotation_manager
    if _secret_rotation_manager is None:
        _secret_rotation_manager = SecretRotationManager()
    return _secret_rotation_manager
