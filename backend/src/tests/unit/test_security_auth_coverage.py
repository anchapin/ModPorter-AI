"""
Comprehensive unit tests for security/auth.py to improve coverage.
"""

import pytest
from datetime import timedelta, datetime, timezone
import jwt
from unittest.mock import patch, MagicMock
from security.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_token_expiry,
    generate_verification_token,
    generate_reset_token,
    generate_api_key,
    hash_api_key,
    SECRET_KEY,
    ALGORITHM
)


class TestSecurityAuth:
    """Tests for security auth utilities."""

    @patch('security.auth.bcrypt.hashpw')
    @patch('security.auth.bcrypt.gensalt')
    @patch('security.auth.bcrypt.checkpw')
    def test_password_hashing(self, mock_checkpw, mock_gensalt, mock_hashpw):
        """Test password hashing and verification."""
        password = "my_secure_password"
        mock_hashpw.return_value = b"hashed_val"
        mock_gensalt.return_value = b"salt"
        mock_checkpw.side_effect = lambda p, h: p == password.encode("utf-8") and h == b"hashed_val"
        
        hashed = hash_password(password)
        assert hashed == "hashed_val"
        assert verify_password(password, "hashed_val") is True
        assert verify_password("wrong", "hashed_val") is False

    def test_create_access_token_basic(self):
        """Test basic access token creation."""
        user_id = "user-123"
        token = create_access_token(user_id)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_access_token_with_delta(self):
        """Test access token with custom expiry."""
        user_id = "user-123"
        expires = timedelta(minutes=30)
        token = create_access_token(user_id, expires_delta=expires)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == user_id
        # exp - iat should be around 1800s (30m)
        assert 1790 <= (payload["exp"] - payload["iat"]) <= 1810

    def test_create_access_token_with_claims(self):
        """Test access token with extra claims."""
        user_id = "user-123"
        claims = {"role": "admin", "org": "acme"}
        token = create_access_token(user_id, extra_claims=claims)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["role"] == "admin"
        assert payload["org"] == "acme"

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = "user-123"
        token = create_refresh_token(user_id)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_verify_token_success(self):
        """Test successful token verification."""
        user_id = "user-123"
        token = create_access_token(user_id)
        
        verified_user_id = verify_token(token, token_type="access")
        assert verified_user_id == user_id

    def test_verify_token_wrong_type(self):
        """Test token verification with wrong expected type."""
        user_id = "user-123"
        token = create_access_token(user_id) # Type is 'access'
        
        # Expecting 'refresh'
        verified_user_id = verify_token(token, token_type="refresh")
        assert verified_user_id is None

    def test_verify_token_invalid(self):
        """Test verification of invalid token."""
        assert verify_token("invalid.token.here") is None

    def test_verify_token_missing_sub(self):
        """Test verification of token missing 'sub' claim."""
        # Manually create token without 'sub'
        payload = {"type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        assert verify_token(token) is None

    def test_get_token_expiry(self):
        """Test extracting expiry from token."""
        user_id = "user-123"
        token = create_access_token(user_id)
        
        expiry = get_token_expiry(token)
        assert isinstance(expiry, datetime)
        assert expiry > datetime.now(timezone.utc)

    def test_get_token_expiry_invalid(self):
        """Test getting expiry from invalid token."""
        assert get_token_expiry("invalid") is None

    def test_get_token_expiry_missing_exp(self):
        """Test get_token_expiry with token missing 'exp' claim."""
        payload = {"sub": "user"}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        assert get_token_expiry(token) is None

    def test_generate_tokens(self):
        """Test generation of random tokens."""
        v_token = generate_verification_token()
        r_token = generate_reset_token()
        
        assert len(v_token) >= 32
        assert len(r_token) >= 32
        assert v_token != r_token

    def test_api_key_generation(self):
        """Test API key generation and hashing."""
        full_key, prefix = generate_api_key()
        
        assert full_key.startswith("mpk_")
        assert prefix == full_key[:8]
        assert len(full_key) > 20
        
        hashed = hash_api_key(full_key)
        assert len(hashed) == 64 # SHA-256 hex
        assert hashed == hash_api_key(full_key) # Deterministic
