"""
Security utilities for Portkit

Provides:
- Password hashing and verification using bcrypt
- JWT token creation and verification
- Token type constants
- Rehash-on-next-use migration path for legacy SHA-256/scrypt API keys (#1428)
"""

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

import bcrypt
import jwt

from core.secrets import get_secret

logger = logging.getLogger(__name__)

# bcrypt cost factor (12 = ~250ms per hash on modern hardware)
BCRYPT_COST = 12

# JWT settings - loaded from environment for production hardening
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
    raise ValueError(
        f"Unsupported JWT_ALGORITHM: {_JWT_ALGORITHM}. Use HS256|HS384|HS512|RS256|RS384|RS512"
    )
ALGORITHM = _JWT_ALGORITHM

# For RS256/RS384/RS512, load RSA keys from environment or files
# RSA_PRIVATE_KEY: Base64-encoded PKCS#8 PEM (for signing)
# RSA_PUBLIC_KEY: Base64-encoded public key PEM (for verification)
_RSA_PRIVATE_KEY: Optional[str] = None
_RSA_PUBLIC_KEY: Optional[str] = None

if ALGORITHM.startswith("RS"):
    _private_key = get_secret("RSA_PRIVATE_KEY")
    _public_key = get_secret("RSA_PUBLIC_KEY")
    if not _private_key or not _public_key:
        # Try loading from files (for Kubernetes secrets / mounted certs)
        _private_key_path = os.getenv("RSA_PRIVATE_KEY_FILE")
        _public_key_path = os.getenv("RSA_PUBLIC_KEY_FILE")
        if _private_key_path and _public_key_path:
            try:
                with open(_private_key_path, "r") as f:
                    _private_key = f.read()
                with open(_public_key_path, "r") as f:
                    _public_key = f.read()
            except OSError as e:
                raise ValueError(
                    f"RS256 requires RSA_PRIVATE_KEY/RSA_PUBLIC_KEY or RSA_PRIVATE_KEY_FILE/RSA_PUBLIC_KEY_FILE: {e}"
                )
        else:
            raise ValueError(
                "RS256 algorithm requires RSA_PRIVATE_KEY and RSA_PUBLIC_KEY environment variables or files"
            )
    _RSA_PRIVATE_KEY = _private_key
    _RSA_PUBLIC_KEY = _public_key

# JWT expiry times - configurable via environment for production hardening
# Production: 5 minutes access, 1 day refresh (more secure)
# Development: 15 minutes access, 7 days refresh (more convenient)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "1"))

# ---------------------------------------------------------------------------
# Legacy API-key migration support (issue #1428)
# ---------------------------------------------------------------------------
# bcrypt's modular-crypt format always begins with one of these tags. Anything
# else stored in ``api_keys.key_hash`` is assumed to be a pre-#1414 hash
# (SHA-256 hex from ``core.auth`` or scrypt hex from ``security.auth``) and is
# eligible for rehash-on-next-use. The list mirrors what passlib accepts so we
# don't accidentally treat a valid bcrypt variant as legacy.
BCRYPT_HASH_PREFIXES = ("$2a$", "$2b$", "$2y$")

# Pre-#1414 scrypt parameters used by ``security.auth.hash_api_key``.
# Source of truth: parent commit of PR #1425 — ``hashlib.scrypt(api_key.encode(),
# salt=SECRET_KEY.encode(), n=16384, r=8, p=1, dklen=32).hex()``. The static
# SECRET_KEY salt is one of the reasons we migrated away from this scheme; we
# only replicate it here so existing keys can still authenticate during drain.
_LEGACY_SCRYPT_N = 16384
_LEGACY_SCRYPT_R = 8
_LEGACY_SCRYPT_P = 1
_LEGACY_SCRYPT_DKLEN = 32

# Length of a SHA-256 / scrypt-with-dklen=32 hex digest. Used as the dummy
# placeholder so constant-time comparisons against malformed stored hashes
# still touch the same number of bytes as the real path.
_LEGACY_HEX_LEN = 64


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


def _get_signing_key() -> str:
    """Return the key to use for signing (creating) tokens."""
    if ALGORITHM.startswith("RS"):
        return _RSA_PRIVATE_KEY  # type: ignore[return-value]
    return SECRET_KEY


def _get_verification_key() -> str:
    """Return the key to use for verifying tokens."""
    if ALGORITHM.startswith("RS"):
        return _RSA_PUBLIC_KEY  # type: ignore[return-value]
    return SECRET_KEY


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

    return jwt.encode(to_encode, _get_signing_key(), algorithm=ALGORITHM)


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

    return jwt.encode(to_encode, _get_signing_key(), algorithm=ALGORITHM)


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
        payload = jwt.decode(token, _get_verification_key(), algorithms=[ALGORITHM])
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
        payload = jwt.decode(token, _get_verification_key(), algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp is None:
            return None
        return datetime.fromtimestamp(exp, tz=timezone.utc)
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
    Hash an API key using bcrypt for secure storage.

    bcrypt uses a random per-call salt, so two calls with the same input
    produce different output. This means callers cannot look the hash up
    directly in the database — use :func:`verify_api_key` to authenticate
    a submitted key against stored hashes.

    Args:
        api_key: Plain text API key

    Returns:
        Bcrypt-hashed API key as a UTF-8 string suitable for varchar storage.
    """
    return bcrypt.hashpw(api_key.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_COST)).decode(
        "utf-8"
    )


def _check_api_key(plain_key: str, hashed_key: str) -> bool:
    """Constant-time bcrypt comparison that swallows malformed-hash errors.

    NOTE: This helper remains bcrypt-only and byte-identical to the behaviour
    introduced by PR #1425. The legacy SHA-256/scrypt fallback lives in
    :func:`verify_api_key` because the rehash + DB write must happen alongside
    the candidate row, not in a pure verification primitive.
    """
    try:
        return bcrypt.checkpw(plain_key.encode("utf-8"), hashed_key.encode("utf-8"))
    except (ValueError, TypeError):
        # Invalid hash format (e.g. legacy SHA-256/scrypt hex) or bad encoding —
        # treat as a verification failure without leaking why.
        return False


def _is_bcrypt_hash(stored_hash: object) -> bool:
    """Return True if ``stored_hash`` looks like a bcrypt modular-crypt string.

    Format-only (``$2a$`` / ``$2b$`` / ``$2y$`` prefix). We do *not* try to
    parse the body — bcrypt itself will validate the structure during
    :func:`bcrypt.checkpw`. Any non-string input is rejected so the legacy
    fallback path can take over.
    """
    return isinstance(stored_hash, str) and stored_hash.startswith(BCRYPT_HASH_PREFIXES)


# TODO(security): remove legacy SHA-256/scrypt fallback after 2026-08-13
# (90 days post-deploy of #1428). Tracked in #1428 follow-up. After removal,
# any remaining legacy keys force re-issue (the original PR #1425 behaviour).
def _matches_legacy_sha256(plain_key: str, stored: object) -> bool:
    """Constant-time SHA-256 hex comparison against a pre-#1414 hash.

    Pre-#1414 ``core.auth.hash_api_key`` was::

        hashlib.sha256(api_key.encode()).hexdigest()

    The function is constant-time even when ``stored`` is malformed: we
    always compute the SHA-256 digest of ``plain_key`` and always invoke
    :func:`hmac.compare_digest`, so a timing attacker cannot distinguish
    "stored hash had wrong length" from "stored hash had right length but
    different value".
    """
    try:
        computed = hashlib.sha256(plain_key.encode("utf-8")).hexdigest()
    except (AttributeError, UnicodeError, TypeError):
        # Plain key was not a usable string; still keep timing flat by
        # comparing a placeholder of the expected length.
        computed = "0" * _LEGACY_HEX_LEN

    if not isinstance(stored, str):
        # Always perform the dummy comparison so this branch costs the same
        # number of bytes as the real path.
        hmac.compare_digest(computed, "0" * _LEGACY_HEX_LEN)
        return False

    return hmac.compare_digest(computed, stored)


# TODO(security): remove legacy SHA-256/scrypt fallback after 2026-08-13
# (90 days post-deploy of #1428). Tracked in #1428 follow-up.
def _matches_legacy_scrypt(plain_key: str, stored: object) -> bool:
    """Constant-time scrypt hex comparison against a pre-#1414 hash.

    Pre-#1414 ``security.auth.hash_api_key`` was::

        hashlib.scrypt(
            api_key.encode(),
            salt=SECRET_KEY.encode(),
            n=16384, r=8, p=1, dklen=32,
        ).hex()

    The static-SECRET_KEY salt was one of the reasons we migrated away from
    this scheme (it allows precomputed rainbow tables once the secret leaks).
    We replicate the parameters here only to drain remaining legacy keys.
    Like :func:`_matches_legacy_sha256` this is constant-time even when
    ``stored`` is malformed.
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


async def _rehash_legacy_key(db, record, plain_key: str, legacy_format: str) -> bool:
    """Rehash a legacy API-key row to bcrypt and persist it.

    Returns ``True`` on a successful commit, ``False`` if persistence failed
    (in which case the session is rolled back). The caller authenticates the
    user either way — a transient DB hiccup must not lock a valid key out;
    the next call simply retries the upgrade.
    """
    new_hash = bcrypt.hashpw(plain_key.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_COST)).decode(
        "utf-8"
    )

    try:
        record.key_hash = new_hash
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            # Rollback failures are themselves logged; don't mask the original.
            pass
        logger.exception(
            "legacy_api_key_rehash_persist_failed",
            extra={"user_id": str(record.user_id), "old_format": legacy_format},
        )
        return False

    logger.info(
        "legacy_api_key_rehashed",
        extra={"user_id": str(record.user_id), "old_format": legacy_format},
    )
    # Best-effort metric — services.metrics is optional in some test contexts.
    try:
        from services.metrics import record_legacy_api_key_rehashed

        record_legacy_api_key_rehashed(legacy_format)
    except ImportError:
        pass
    return True


async def verify_api_key(db, api_key: str) -> "Optional[User]":
    """
    Verify an API key and return the associated user.

    Because :func:`hash_api_key` uses bcrypt with a random per-call salt,
    we cannot look the row up by hash directly. Instead we narrow the
    candidate set using the public prefix (the first 8 characters of every
    issued key, persisted on :class:`APIKey.prefix`) and then run
    :func:`bcrypt.checkpw` against each candidate.

    Tradeoff: we may run bcrypt up to N times, where N is the number of
    active keys sharing the same 8-character prefix. The prefix
    (``mpk_`` + 4 base64url chars) gives ~24 bits of entropy, so in
    practice N is almost always 1. If many users ever shared a prefix
    we would need to add an indexed lookup column (e.g. an HMAC
    fingerprint of the key) — out of scope for this change.

    Legacy migration (#1428): if a candidate row stores a pre-#1414
    SHA-256 or scrypt hash and the key matches under the legacy scheme,
    the row is transparently rehashed with bcrypt and persisted before
    the user is returned. The bcrypt fast-path is byte-identical to the
    pre-rehash behaviour: bcrypt-format hashes never touch the legacy
    helpers and never trigger a DB write.

    Args:
        db: Async database session
        api_key: Plain text API key submitted by the caller

    Returns:
        User if API key is valid and active, None otherwise.
    """
    from sqlalchemy import select

    from db.models import APIKey, User

    if not api_key or len(api_key) < 8:
        return None

    prefix = api_key[:8]
    result = await db.execute(
        select(APIKey).where(
            APIKey.prefix == prefix,
            APIKey.is_active == True,  # noqa: E712 — SQLAlchemy needs `==` here
        )
    )
    candidates = result.scalars().all()

    for record in candidates:
        stored_hash = record.key_hash

        if _is_bcrypt_hash(stored_hash):
            # Modern path — byte-identical to PR #1425 behaviour. No DB write,
            # no metric, no log; this is the common case at steady state.
            if _check_api_key(api_key, stored_hash):
                user_result = await db.execute(select(User).where(User.id == record.user_id))
                return user_result.scalar_one_or_none()
            continue

        # Legacy path (#1428): try SHA-256 first (cheaper), then scrypt.
        # Both helpers are constant-time even on malformed stored hashes.
        legacy_format: Optional[str] = None
        if _matches_legacy_sha256(api_key, stored_hash):
            legacy_format = "sha256"
        elif _matches_legacy_scrypt(api_key, stored_hash):
            legacy_format = "scrypt"

        if legacy_format is None:
            # Stored hash isn't bcrypt and isn't a legacy match — could be
            # corruption or a hash from a future scheme; skip without
            # writing anything and let the next candidate try.
            continue

        # Match — rehash with bcrypt, persist, and emit telemetry. Auth
        # succeeds whether or not the rehash commit succeeds (see helper).
        await _rehash_legacy_key(db, record, api_key, legacy_format)

        user_result = await db.execute(select(User).where(User.id == record.user_id))
        return user_result.scalar_one_or_none()

    return None
