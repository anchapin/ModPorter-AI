"""
Security utilities for ModPorter AI

Provides:
- Password hashing and verification using bcrypt
- JWT token creation and verification
- Token type constants
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt

from core.secrets import get_secret

# bcrypt cost factor (12 = ~250ms per hash on modern hardware)
BCRYPT_COST = 12

# JWT settings - loaded from environment for production hardening
SECRET_KEY = get_secret("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in the environment or secrets manager")
ALGORITHM = "HS256"

# JWT expiry times - configurable via environment
# Defaults: 15 minutes access, 7 days refresh
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_COST)).decode(
        "utf-8"
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to check against

    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        # Invalid hash format
        return False


def create_access_token(
    user_id: str, expires_delta: Optional[timedelta] = None, extra_claims: Optional[dict] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to encode in token
        expires_delta: Optional custom expiry time
        extra_claims: Optional additional claims to include

    Returns:
        Encoded JWT token string
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "type": "access",
    }

    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User ID to encode in token
        expires_delta: Optional custom expiry time

    Returns:
        Encoded JWT token string
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Verify a JWT token and extract user ID.

    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")

    Returns:
        User ID if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type_payload = payload.get("type")

        if token_type_payload != token_type:
            return None

        user_id = payload.get("sub")
        if user_id is None:
            return None

        return user_id
    except jwt.PyJWTError:
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get the expiry time of a JWT token.

    Args:
        token: JWT token string

    Returns:
        Expiry datetime if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp is None:
            return None
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    except jwt.PyJWTError:
        return None


def generate_verification_token() -> str:
    """
    Generate a secure email verification token.

    Returns:
        Random verification token string
    """
    return secrets.token_urlsafe(32)


def generate_reset_token() -> str:
    """
    Generate a secure password reset token.

    Returns:
        Random reset token string
    """
    return secrets.token_urlsafe(32)


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, prefix)
        - full_key: Complete API key (store hashed version)
        - prefix: First 8 characters for identification
    """
    key = f"mpk_{secrets.token_urlsafe(24)}"
    return key, key[:8]


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.

    Args:
        api_key: Plain text API key

    Returns:
        Hashed API key using SHA-256
    """
    import hashlib

    return hashlib.sha256(api_key.encode()).hexdigest()
