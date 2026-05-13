"""
Unit tests for the bcrypt-based API key hashing/verification helpers
introduced for issue #1414 on ``core.auth.AuthManager``.
"""

import bcrypt
import pytest

from core.auth import AuthManager, default_auth, hash_api_key, verify_api_key


@pytest.mark.unit
class TestAuthManagerApiKeyBcrypt:
    """Behavioural tests for AuthManager.hash_api_key / verify_api_key."""

    def test_hash_api_key_uses_bcrypt_format(self):
        manager = AuthManager()
        full_key, _ = manager.generate_api_key()

        hashed = manager.hash_api_key(full_key)

        # bcrypt modular crypt format: $2[abxy]$<cost>$<22-char-salt><31-char-hash>
        assert isinstance(hashed, str)
        assert len(hashed) == 60
        assert hashed.startswith("$2")

    def test_hash_api_key_is_non_deterministic(self):
        """Each hash uses a fresh salt — calls must not collide."""
        manager = AuthManager()
        full_key, _ = manager.generate_api_key()

        first = manager.hash_api_key(full_key)
        second = manager.hash_api_key(full_key)

        assert first != second
        # …but both must verify against the same plaintext.
        assert bcrypt.checkpw(full_key.encode("utf-8"), first.encode("utf-8"))
        assert bcrypt.checkpw(full_key.encode("utf-8"), second.encode("utf-8"))

    def test_verify_api_key_accepts_correct_key(self):
        manager = AuthManager()
        full_key, _ = manager.generate_api_key()
        hashed = manager.hash_api_key(full_key)

        assert manager.verify_api_key(full_key, hashed) is True

    def test_verify_api_key_rejects_wrong_key(self):
        manager = AuthManager()
        full_key, _ = manager.generate_api_key()
        hashed = manager.hash_api_key(full_key)

        assert manager.verify_api_key("mpk_obviously-wrong-key", hashed) is False

    def test_verify_api_key_rejects_malformed_hash(self):
        manager = AuthManager()
        full_key, _ = manager.generate_api_key()

        # legacy SHA-256 hex hash format (64 chars, not bcrypt)
        legacy_hash = "a" * 64
        assert manager.verify_api_key(full_key, legacy_hash) is False

        # complete garbage
        assert manager.verify_api_key(full_key, "not-a-hash") is False

    def test_verify_api_key_rejects_none_inputs(self):
        manager = AuthManager()

        assert manager.verify_api_key(None, "$2b$12$" + "a" * 53) is False
        assert manager.verify_api_key("mpk_anything", None) is False
        assert manager.verify_api_key(None, None) is False

    def test_module_level_aliases_use_default_auth(self):
        """The module-level ``hash_api_key`` / ``verify_api_key`` are convenience
        wrappers around ``default_auth`` — exercise them end-to-end.
        """
        full_key, _ = default_auth.generate_api_key()

        hashed = hash_api_key(full_key)
        assert verify_api_key(full_key, hashed) is True
        assert verify_api_key("mpk_other", hashed) is False
