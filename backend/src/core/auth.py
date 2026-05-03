"""
Authentication Core Module

Provides high-level authentication functionality including:
- JWT token management
- Password hashing with bcrypt
- Token generation and validation
- AuthManager class for easy integration
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from core.secrets import get_secret

# JWT settings
SECRET_KEY = get_secret("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in the environment or secrets manager")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthManager:
    """
    High-level authentication manager for JWT tokens and password hashing.

    Usage:
        auth = AuthManager()
        hashed = auth.hash_password("mypassword")
        auth.verify_password("mypassword", hashed)
        token = auth.create_access_token("user123")
        user_id = auth.verify_token(token)
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ):
        """
        Initialize AuthManager with custom settings.

        Args:
            secret_key: JWT secret key (defaults to env SECRET_KEY)
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token expiry in minutes
            refresh_token_expire_days: Refresh token expiry in days
        """
        self.secret_key = secret_key or SECRET_KEY
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        # bcrypt requires bytes, so encode the password
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to check against

        Returns:
            True if password matches, False otherwise
        """
        if hashed_password is None:
            return False
        try:
            password_bytes = plain_password.encode("utf-8")
            hashed_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except (ValueError, TypeError) as e:
            # Invalid hash format or encoding error - treat as wrong password
            # Don't log to avoid timing attacks
            return False

    def create_access_token(
        self,
        user_id: str,
        expires_delta: Optional[timedelta] = None,
        extra_claims: Optional[dict] = None,
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
            expire = now + timedelta(minutes=self.access_token_expire_minutes)

        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "access",
        }

        if extra_claims:
            to_encode.update(extra_claims)

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        user_id: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
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
            expire = now + timedelta(days=self.refresh_token_expire_days)

        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "refresh",
        }

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str, token_type: str = "access") -> Optional[str]:
        """
        Verify a JWT token and extract user ID.

        Args:
            token: JWT token string
            token_type: Expected token type ("access" or "refresh")

        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            token_type_payload = payload.get("type")

            if token_type_payload != token_type:
                return None

            user_id = payload.get("sub")
            if user_id is None:
                return None

            return user_id
        except jwt.PyJWTError:
            return None

    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        Get the expiry time of a JWT token.

        Args:
            token: JWT token string

        Returns:
            Expiry datetime if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            exp = payload.get("exp")
            if exp is None:
                return None
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        except jwt.PyJWTError:
            return None

    def generate_verification_token(self) -> str:
        """
        Generate a secure email verification token.

        Returns:
            Random verification token string
        """
        return secrets.token_urlsafe(32)

    def generate_reset_token(self) -> str:
        """
        Generate a secure password reset token.

        Returns:
            Random reset token string
        """
        return secrets.token_urlsafe(32)

    def generate_api_key(self) -> tuple[str, str]:
        """
        Generate a new API key.

        Returns:
            Tuple of (full_key, prefix)
            - full_key: Complete API key (store hashed version)
            - prefix: First 8 characters for identification
        """
        key = f"mpk_{secrets.token_urlsafe(24)}"
        return key, key[:8]

    def hash_api_key(self, api_key: str) -> str:
        """
        Hash an API key for storage.

        Args:
            api_key: Plain text API key

        Returns:
            Hashed API key using SHA-256
        """
        import hashlib

        return hashlib.sha256(api_key.encode()).hexdigest()


# Default instance for easy import
default_auth = AuthManager()

# Convenience functions
hash_password = default_auth.hash_password
verify_password = default_auth.verify_password
create_access_token = default_auth.create_access_token
create_refresh_token = default_auth.create_refresh_token
verify_token = default_auth.verify_token
generate_verification_token = default_auth.generate_verification_token
generate_reset_token = default_auth.generate_reset_token
generate_api_key = default_auth.generate_api_key
hash_api_key = default_auth.hash_api_key
