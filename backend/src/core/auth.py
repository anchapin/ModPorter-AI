"""
Authentication Core Module

Provides high-level authentication functionality including:
- JWT token management
- Password hashing with bcrypt
- Token generation and validation
- AuthManager class for easy integration
- Rehash-on-next-use migration path for legacy SHA-256/scrypt API keys (#1428)
"""

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from core.secrets import get_secret

logger = logging.getLogger(__name__)

# JWT settings
SECRET_KEY = get_secret("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in the environment or secrets manager")

# JWT algorithm selection for enterprise scale
# HS256: Symmetric - fast, simple key management (default for backwards compatibility)
# RS256: Asymmetric (RSA) - recommended for enterprise/multi-service architectures
#   - Private key for signing stays on auth server
#   - Public key for verification can be distributed widely
#   - Better key management: compromise of verifier doesn't allow token forgery
# Configure via JWT_ALGORITHM env var (default: HS256)
_JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
if _JWT_ALGORITHM not in ("HS256", "HS384", "HS512", "RS256", "RS384", "RS512"):
    raise ValueError(f"Unsupported JWT_ALGORITHM: {_JWT_ALGORITHM}. Use HS256|HS384|HS512|RS256|RS384|RS512")
ALGORITHM = _JWT_ALGORITHM

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# For RS256/RS384/RS512, load RSA keys from environment or files
_RSA_PRIVATE_KEY: Optional[str] = None
_RSA_PUBLIC_KEY: Optional[str] = None

if ALGORITHM.startswith("RS"):
    _private_key = get_secret("RSA_PRIVATE_KEY")
    _public_key = get_secret("RSA_PUBLIC_KEY")
    if not _private_key or not _public_key:
        _private_key_path = os.getenv("RSA_PRIVATE_KEY_FILE")
        _public_key_path = os.getenv("RSA_PUBLIC_KEY_FILE")
        if _private_key_path and _public_key_path:
            try:
                with open(_private_key_path, "r") as f:
                    _private_key = f.read()
                with open(_public_key_path, "r") as f:
                    _public_key = f.read()
            except OSError as e:
                raise ValueError(f"RS256 requires RSA_PRIVATE_KEY/RSA_PUBLIC_KEY or RSA_PRIVATE_KEY_FILE/RSA_PUBLIC_KEY_FILE: {e}")
        else:
            raise ValueError("RS256 algorithm requires RSA_PRIVATE_KEY and RSA_PUBLIC_KEY environment variables or files")
    _RSA_PRIVATE_KEY = _private_key
    _RSA_PUBLIC_KEY = _public_key

# ---------------------------------------------------------------------------
# Legacy API-key migration support (issue #1428)
# ---------------------------------------------------------------------------
# bcrypt's modular-crypt format always begins with one of these tags. Anything
# else stored in ``api_keys.key_hash`` is assumed to be a pre-#1414 hash
# (SHA-256 hex from this module or scrypt hex from ``security.auth``) and is
# eligible for rehash-on-next-use via :meth:`AuthManager.verify_api_key_with_rehash`.
BCRYPT_HASH_PREFIXES = ("$2a$", "$2b$", "$2y$")

# Pre-#1414 scrypt parameters used by ``security.auth.hash_api_key``. Kept
# here too so the verification primitive in this module can fall back to
# scrypt when an API key was issued via the security path. See PR #1425
# parent commit for the original constants.
_LEGACY_SCRYPT_N = 16384
_LEGACY_SCRYPT_R = 8
_LEGACY_SCRYPT_P = 1
_LEGACY_SCRYPT_DKLEN = 32

# SHA-256 / scrypt-with-dklen=32 hex digest length. Used as the dummy
# placeholder so constant-time comparisons against malformed stored hashes
# touch the same number of bytes as the real path.
_LEGACY_HEX_LEN = 64


def _is_bcrypt_hash(stored_hash: object) -> bool:
    """Return True if ``stored_hash`` looks like a bcrypt modular-crypt string."""
    return isinstance(stored_hash, str) and stored_hash.startswith(BCRYPT_HASH_PREFIXES)


# TODO(security): remove legacy SHA-256/scrypt fallback after 2026-08-13
# (90 days post-deploy of #1428). Tracked in #1428 follow-up. After removal,
# any remaining legacy keys force re-issue (PR #1425 behaviour).
def _matches_legacy_sha256(plain_key: str, stored: object) -> bool:
    """Constant-time SHA-256 hex comparison against a pre-#1414 hash.

    Pre-#1414 ``core.auth.hash_api_key`` was
    ``hashlib.sha256(api_key.encode()).hexdigest()``. This helper always
    computes the digest and always invokes :func:`hmac.compare_digest`, so a
    timing attacker cannot distinguish "stored hash had wrong length" from
    "stored hash had right length but different value".
    """
    try:
        computed = hashlib.sha256(plain_key.encode("utf-8")).hexdigest()
    except (AttributeError, UnicodeError, TypeError):
        computed = "0" * _LEGACY_HEX_LEN

    if not isinstance(stored, str):
        hmac.compare_digest(computed, "0" * _LEGACY_HEX_LEN)
        return False

    return hmac.compare_digest(computed, stored)


# TODO(security): remove legacy SHA-256/scrypt fallback after 2026-08-13
# (90 days post-deploy of #1428). Tracked in #1428 follow-up.
def _matches_legacy_scrypt(plain_key: str, stored: object) -> bool:
    """Constant-time scrypt hex comparison against a pre-#1414 hash.

    Pre-#1414 ``security.auth.hash_api_key`` was::

        hashlib.scrypt(api_key.encode(), salt=SECRET_KEY.encode(),
                       n=16384, r=8, p=1, dklen=32).hex()

    The static-SECRET_KEY salt was one of the reasons we migrated away from
    this scheme. We replicate the parameters here only to drain remaining
    legacy keys.
    """
    try:
        computed = hashlib.scrypt(
            plain_key.encode("utf-8"),
            salt=SECRET_KEY.encode("utf-8"),
            n=_LEGACY_SCRYPT_N,
            r=_LEGACY_SCRYPT_R,
            p=_LEGACY_SCRYPT_P,
            dklen=_LEGACY_SCRYPT_DKLEN,
        ).hex()
    except (AttributeError, UnicodeError, TypeError, ValueError):
        computed = "0" * _LEGACY_HEX_LEN

    if not isinstance(stored, str):
        hmac.compare_digest(computed, "0" * _LEGACY_HEX_LEN)
        return False

    return hmac.compare_digest(computed, stored)


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
        algorithm: Optional[str] = None,
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ):
        """
        Initialize AuthManager with custom settings.

        Args:
            secret_key: JWT secret key (defaults to env SECRET_KEY)
            algorithm: JWT algorithm (defaults to env JWT_ALGORITHM or HS256)
            access_token_expire_minutes: Access token expiry in minutes
            refresh_token_expire_days: Refresh token expiry in days
        """
        self.secret_key = secret_key or SECRET_KEY
        # Allow override, but default to module-level ALGORITHM for RS256 support
        self.algorithm = algorithm or ALGORITHM
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def _get_signing_key(self) -> str:
        """Return the key to use for signing (creating) tokens."""
        if self.algorithm.startswith("RS"):
            return _RSA_PRIVATE_KEY  # type: ignore[return-value]
        return self.secret_key

    def _get_verification_key(self) -> str:
        """Return the key to use for verifying tokens."""
        if self.algorithm.startswith("RS"):
            return _RSA_PUBLIC_KEY  # type: ignore[return-value]
        return self.secret_key

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

        return jwt.encode(to_encode, self._get_signing_key(), algorithm=self.algorithm)

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

        return jwt.encode(to_encode, self._get_signing_key(), algorithm=self.algorithm)

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
            payload = jwt.decode(token, self._get_verification_key(), algorithms=[self.algorithm])
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
            payload = jwt.decode(token, self._get_verification_key(), algorithms=[self.algorithm])
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
        Hash an API key using bcrypt for secure storage.

        bcrypt is intentionally slow (configurable cost factor) which makes
        offline brute-force attacks against a leaked database significantly
        more expensive than fast hashes such as SHA-256.

        Args:
            api_key: Plain text API key

        Returns:
            Bcrypt-hashed API key (UTF-8 string suitable for varchar storage).
        """
        return bcrypt.hashpw(api_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_api_key(self, plain_key: str, hashed_key: str) -> bool:
        """
        Verify an API key against its bcrypt hash.

        Returns False (rather than raising) for malformed or missing input so
        callers can use this as a constant-time comparison primitive without
        leaking information about the hash format via exceptions.

        This method is bcrypt-only and remains byte-identical to the
        behaviour introduced by PR #1425. Use
        :meth:`verify_api_key_with_rehash` if you need to also accept legacy
        SHA-256/scrypt hashes (issue #1428).

        Args:
            plain_key: Plain text API key submitted by the caller.
            hashed_key: Bcrypt hash previously produced by ``hash_api_key``.

        Returns:
            True if the plain key matches the stored hash, False otherwise.
        """
        if plain_key is None or hashed_key is None:
            return False
        try:
            return bcrypt.checkpw(plain_key.encode("utf-8"), hashed_key.encode("utf-8"))
        except (ValueError, TypeError):
            # Invalid hash format (e.g. legacy SHA-256 hex) or encoding error
            # — treat as a failed verification without leaking why.
            return False

    def needs_rehash(self, stored_hash: object) -> bool:
        """Return True if ``stored_hash`` is in a deprecated legacy format.

        Callers can use this as a cheap pre-check before invoking
        :meth:`verify_api_key_with_rehash`. Returns False for bcrypt hashes
        and True for everything else (including malformed strings — those
        also need replacement).
        """
        return not _is_bcrypt_hash(stored_hash)

    def verify_api_key_with_rehash(
        self, plain_key: str, hashed_key: str
    ) -> tuple[bool, Optional[str]]:
        """Verify an API key, accepting legacy SHA-256/scrypt hashes (#1428).

        This is the legacy-tolerant sibling of :meth:`verify_api_key`. It
        does NOT touch the database; the caller is responsible for
        persisting ``new_hash`` when it is non-None.

        Args:
            plain_key: Plain text API key submitted by the caller.
            hashed_key: Stored hash — may be bcrypt (modern) or legacy
                SHA-256/scrypt hex (pre-#1414).

        Returns:
            ``(matched, new_hash)`` where:

            - ``(True, None)`` — bcrypt hash matched; no rehash needed.
              Byte-identical to :meth:`verify_api_key` returning True.
            - ``(True, "<bcrypt hash>")`` — legacy hash matched; the caller
              MUST persist ``new_hash`` to ``api_keys.key_hash`` and SHOULD
              emit the ``legacy_api_key_rehashed`` log/metric.
            - ``(False, None)`` — no match. Do **not** persist anything.
        """
        if plain_key is None or hashed_key is None:
            return (False, None)

        if _is_bcrypt_hash(hashed_key):
            # Modern path — byte-identical to verify_api_key().
            return (self.verify_api_key(plain_key, hashed_key), None)

        # Legacy path: try SHA-256, then scrypt. Both helpers are
        # constant-time even on malformed input.
        if _matches_legacy_sha256(plain_key, hashed_key) or _matches_legacy_scrypt(
            plain_key, hashed_key
        ):
            new_hash = self.hash_api_key(plain_key)
            return (True, new_hash)

        return (False, None)


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
verify_api_key = default_auth.verify_api_key
verify_api_key_with_rehash = default_auth.verify_api_key_with_rehash
needs_rehash = default_auth.needs_rehash
