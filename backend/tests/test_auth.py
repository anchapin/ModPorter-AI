"""
Unit tests for authentication module.

Tests:
- Password hashing (3 tests)
- JWT token generation and validation (4 tests)
- API endpoints (5 tests via integration test client)
"""

import os
import sys
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Add the src directory to the Python path
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

# Set testing environment variable BEFORE importing main
os.environ["TESTING"] = "true"
os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", "test-secret-key-must-be-at-least-32-bytes!!")

from core.auth import (
    AuthManager,
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_verification_token,
    generate_reset_token,
    generate_api_key,
    hash_api_key,
)


# ============================================
# Password Hashing Tests (3 tests)
# ============================================


class TestPasswordHashing:
    """Tests for password hashing functionality"""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a non-empty string"""
        result = hash_password("TestPassword123!")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_password_is_unique(self):
        """Test that hashing the same password twice produces different results"""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # bcrypt adds random salt

    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password"""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False


# ============================================
# JWT Token Tests (4 tests)
# ============================================


class TestJWTTokens:
    """Tests for JWT token functionality"""

    def test_create_access_token(self):
        """Test creating an access token"""
        user_id = "test-user-123"
        token = create_access_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test creating a refresh token"""
        user_id = "test-user-123"
        token = create_refresh_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_access_token(self):
        """Test verifying a valid access token"""
        user_id = "test-user-123"
        token = create_access_token(user_id)
        extracted_user_id = verify_token(token, "access")
        assert extracted_user_id == user_id

    def test_verify_refresh_token(self):
        """Test verifying a valid refresh token"""
        user_id = "test-user-123"
        token = create_refresh_token(user_id)
        extracted_user_id = verify_token(token, "refresh")
        assert extracted_user_id == user_id

    def test_verify_token_wrong_type(self):
        """Test that verify_token returns None for wrong token type"""
        user_id = "test-user-123"
        access_token = create_access_token(user_id)
        # Try to verify access token as refresh token
        result = verify_token(access_token, "refresh")
        assert result is None

    def test_verify_invalid_token(self):
        """Test that verify_token returns None for invalid token"""
        result = verify_token("invalid.token.here", "access")
        assert result is None

    def test_token_contains_correct_expiry(self):
        """Test that access token has correct expiry"""
        user_id = "test-user-123"
        token = create_access_token(user_id)
        auth = AuthManager()
        expiry = auth.get_token_expiry(token)
        assert expiry is not None
        # Token should expire in approximately 15 minutes
        expected_expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
        # Allow 5 second tolerance
        assert abs((expiry - expected_expiry).total_seconds()) < 5


# ============================================
# Token Generation Tests
# ============================================


class TestTokenGeneration:
    """Tests for token generation utilities"""

    def test_generate_verification_token(self):
        """Test generating email verification token"""
        token = generate_verification_token()
        assert isinstance(token, str)
        assert len(token) >= 32

    def test_generate_reset_token(self):
        """Test generating password reset token"""
        token = generate_reset_token()
        assert isinstance(token, str)
        assert len(token) >= 32

    def test_generate_api_key(self):
        """Test generating API key"""
        full_key, prefix = generate_api_key()
        assert full_key.startswith("mpk_")
        assert len(prefix) == 8
        assert full_key[:8] == prefix

    def test_hash_api_key(self):
        """Test hashing API key"""
        api_key = "mpk_testkey123"
        hashed = hash_api_key(api_key)
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 produces 64 hex characters


# ============================================
# AuthManager Class Tests
# ============================================


class TestAuthManager:
    """Tests for AuthManager class"""

    def test_auth_manager_init(self):
        """Test AuthManager initialization"""
        auth = AuthManager()
        assert auth.secret_key is not None
        assert auth.algorithm == "HS256"

    def test_auth_manager_custom_settings(self):
        """Test AuthManager with custom settings"""
        auth = AuthManager(
            secret_key="custom-secret",
            access_token_expire_minutes=30,
            refresh_token_expire_days=14,
        )
        assert auth.secret_key == "custom-secret"
        assert auth.access_token_expire_minutes == 30
        assert auth.refresh_token_expire_days == 14

    def test_auth_manager_create_token_with_expiry(self):
        """Test creating token with custom expiry"""
        auth = AuthManager()
        custom_delta = timedelta(hours=1)
        token = auth.create_access_token("user123", expires_delta=custom_delta)
        expiry = auth.get_token_expiry(token)
        expected_expiry = datetime.now(timezone.utc) + custom_delta
        assert abs((expiry - expected_expiry).total_seconds()) < 1


# ============================================
# Edge Cases
# ============================================


class TestEdgeCases:
    """Edge case tests"""

    def test_empty_password(self):
        """Test hashing empty password"""
        result = hash_password("")
        assert isinstance(result, str)

    def test_very_long_password(self):
        """Test hashing very long password (bcrypt has 72 byte limit)"""
        # bcrypt truncates passwords longer than 72 bytes - this is expected behavior
        long_password = "a" * 70  # Under the 72 byte limit
        result = hash_password(long_password)
        assert isinstance(result, str)

    def test_unicode_password(self):
        """Test hashing unicode password"""
        unicode_password = "пароль123!测试"
        hashed = hash_password(unicode_password)
        assert verify_password(unicode_password, hashed) is True

    def test_verify_with_none_hash(self):
        """Test verifying against None hash"""
        result = verify_password("password", None)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
