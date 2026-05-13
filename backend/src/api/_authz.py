"""
Authorization helpers shared by API routers.

Centralises the "require an authenticated user" dependency (so routers can
import a single name regardless of whether the underlying token is a JWT or an
API key) and an `assert_owner` helper that returns a 404 when the requesting
user does not own the resource — never 403, to avoid leaking the existence of
resources to anonymous probers (issue #1417).
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import User
from security.auth import verify_api_key, verify_token

# Re-usable security scheme. ``auto_error=True`` so missing/invalid headers
# produce a clean 401 before our handler even runs.
_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the currently-authenticated user from a Bearer credential.

    Accepts either a JWT access token or a personal API key prefixed with
    ``mpk_``. Raises HTTP 401 in every other case (no token, expired token,
    user no longer exists, etc.) so callers do not need to repeat the check.
    """
    token = credentials.credentials

    # Try API key first when the prefix matches — keeps JWT verification quiet
    # for API-key callers and avoids a spurious "Invalid token" log line.
    if token.startswith("mpk_"):
        user = await verify_api_key(db, token)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    user_id = verify_token(token, "access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _user_id_str(user: User) -> str:
    return str(user.id)


def assert_owner(
    resource: Optional[Any],
    current_user: User,
    *,
    owner_field: str = "user_id",
    not_found_detail: str = "Resource not found",
) -> Any:
    """
    Verify ``resource`` exists and is owned by ``current_user``.

    Returns the resource when the check passes. Raises 404 otherwise — never
    403, because returning a different status for "exists but not yours" leaks
    that the resource exists.

    ``owner_field`` defaults to ``user_id`` but accepts any attribute that
    holds the owning user's id.
    """
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail)

    owner = getattr(resource, owner_field, None)
    if owner is None or str(owner) != _user_id_str(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail)

    return resource


__all__ = ["get_current_user", "assert_owner"]
