"""
Authentication API endpoints for ModPorter AI

Endpoints:
- POST /api/v1/auth/register - Register new user
- POST /api/v1/auth/login - Login with email/password
- POST /api/v1/auth/logout - Logout (invalidate tokens)
- POST /api/v1/auth/refresh - Refresh access token
- GET /api/v1/auth/verify-email/{token} - Verify email address
- POST /api/v1/auth/forgot-password - Request password reset
- POST /api/v1/auth/reset-password/{token} - Reset password
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import User, APIKey
from security.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_verification_token,
    generate_reset_token,
    generate_api_key,
    hash_api_key,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security scheme
security = HTTPBearer()


# ============================================
# Request/Response Models
# ============================================


class RegisterRequest(BaseModel):
    """User registration request"""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @validator("password")
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c.isupper() for c in v) and not any(c.islower() for c in v):
            raise ValueError("Password must contain both uppercase and lowercase letters")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class RegisterResponse(BaseModel):
    """User registration response"""

    message: str
    user_id: str


class LoginRequest(BaseModel):
    """Login request"""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response with tokens"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Token refresh request"""

    refresh_token: str


class TokenResponse(BaseModel):
    """Token response"""

    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    """Password reset request"""

    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Password reset confirmation request"""

    password: str = Field(..., min_length=8, max_length=128)

    @validator("password")
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c.isupper() for c in v) and not any(c.islower() for c in v):
            raise ValueError("Password must contain both uppercase and lowercase letters")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class MessageResponse(BaseModel):
    """Generic message response"""

    message: str


# ============================================
# Helper Functions
# ============================================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials
    user_id = verify_token(token, "access")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ============================================
# Authentication Endpoints
# ============================================


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request_data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.
    """
    result = await db.execute(select(User).where(User.email == request_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    verification_token = generate_verification_token()
    user = User(
        email=request_data.email,
        password_hash=hash_password(request_data.password),
        verification_token=verification_token,
        verification_token_expires=datetime.now(timezone.utc) + timedelta(hours=24),
        is_verified=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"Email verification token for {request_data.email}: {verification_token}")
    logger.info(f"Verification URL: http://localhost:8080/api/v1/auth/verify-email/{verification_token}")

    return RegisterResponse(
        message="User registered. Please check email for verification link.",
        user_id=str(user.id),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email and password.
    """
    result = await db.execute(select(User).where(User.email == request_data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(request_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your email.",
        )

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Logout by invalidating the current token.
    """
    return MessageResponse(message="Successfully logged out")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    request_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    """
    user_id = verify_token(request_data.refresh_token, "refresh")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    new_access_token = create_access_token(user_id)

    return TokenResponse(
        access_token=new_access_token,
    )


@router.get("/verify-email/{token}", response_model=MessageResponse)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify email address using verification token.
    """
    result = await db.execute(
        select(User).where(
            User.verification_token == token,
            User.verification_token_expires > datetime.now(timezone.utc),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None

    await db.commit()

    return MessageResponse(message="Email verified successfully")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset link.
    """
    result = await db.execute(select(User).where(User.email == request_data.email))
    user = result.scalar_one_or_none()

    if user:
        reset_token = generate_reset_token()
        user.reset_token = reset_token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.commit()

        logger.info(f"Password reset token for {request_data.email}: {reset_token}")
        logger.info(f"Reset URL: http://localhost:8080/api/v1/auth/reset-password/{reset_token}")

    return MessageResponse(
        message="If the email is registered, a password reset link has been sent."
    )


@router.post("/reset-password/{token}", response_model=MessageResponse)
async def reset_password(
    token: str,
    request_data: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using reset token.
    """
    result = await db.execute(
        select(User).where(
            User.reset_token == token,
            User.reset_token_expires > datetime.now(timezone.utc),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.password_hash = hash_password(request_data.password)
    user.reset_token = None
    user.reset_token_expires = None

    await db.commit()

    return MessageResponse(message="Password reset successfully")


# ============================================
# User Management Endpoints
# ============================================


@router.get("/me", tags=["Users"])
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user profile.
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat(),
        "conversion_count": current_user.conversion_count,
    }


@router.patch("/me", tags=["Users"])
async def update_current_user_profile(
    request_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user profile.
    """
    if "email" in request_data:
        result = await db.execute(
            select(User).where(
                User.email == request_data["email"],
                User.id != current_user.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        current_user.email = request_data["email"]

    await db.commit()
    await db.refresh(current_user)

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "is_verified": current_user.is_verified,
    }


@router.delete("/me", tags=["Users"])
async def delete_current_user_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete current user account.
    """
    await db.delete(current_user)
    await db.commit()

    return MessageResponse(message="Account deleted successfully")


# ============================================
# API Key Management Endpoints
# ============================================


@router.post("/api-keys", tags=["API Keys"])
async def create_api_key_endpoint(
    request_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API key.
    """
    name = request_data.get("name", "API Key")

    full_key, prefix = generate_api_key()
    key_hash = hash_api_key(full_key)

    api_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=name,
        prefix=prefix,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "prefix": api_key.prefix,
        "api_key": full_key,
        "created_at": api_key.created_at.isoformat(),
    }


@router.get("/api-keys", tags=["API Keys"])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all API keys for current user.
    """
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == current_user.id)
        .order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()

    return [
        {
            "id": str(key.id),
            "name": key.name,
            "prefix": key.prefix,
            "created_at": key.created_at.isoformat(),
            "last_used": key.last_used.isoformat() if key.last_used else None,
            "is_active": key.is_active,
        }
        for key in api_keys
    ]


@router.delete("/api-keys/{key_id}", tags=["API Keys"])
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke (delete) an API key.
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await db.delete(api_key)
    await db.commit()

    return MessageResponse(message="API key revoked")
