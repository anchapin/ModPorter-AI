"""
Authentication API endpoints for Portkit

Endpoints:
- POST /api/v1/auth/register - Register new user
- POST /api/v1/auth/login - Login with email/password
- POST /api/v1/auth/logout - Logout (invalidate tokens)
- POST /api/v1/auth/refresh - Refresh access token
- GET /api/v1/auth/verify-email/{token} - Verify email address
- POST /api/v1/auth/forgot-password - Request password reset
- POST /api/v1/auth/reset-password/{token} - Reset password
OAuth Endpoints (Issue #980):
- GET /api/v1/auth/oauth/{provider} - Get OAuth authorization URL
- GET /api/v1/auth/oauth/{provider}/callback - OAuth callback
- GET /api/v1/auth/oauth/{provider}/status - Get OAuth connection status
- DELETE /api/v1/auth/oauth/{provider}/unlink - Unlink OAuth account
- POST /api/v1/auth/oauth/link - Link OAuth account to user
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import User, APIKey, OAuthAccount
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
)
from services.feature_flags import is_feature_enabled
from services.email_service import send_verification_email, send_password_reset_email
from services.oauth_service import oauth_service, generate_oauth_state
from config import settings

logger = logging.getLogger(__name__)


def require_feature_flag(flag_name: str):
    """Dependency that checks if a feature flag is enabled."""

    async def check_flag():
        if not is_feature_enabled(flag_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature is currently disabled. Please contact support if you believe this is an error.",
            )
        return True

    return check_flag


router = APIRouter(tags=["Authentication"])

# Security scheme
security = HTTPBearer()


# ============================================
# Request/Response Models
# ============================================


class RegisterRequest(BaseModel):
    """User registration request"""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
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

    @field_validator("password")
    @classmethod
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
    from uuid import UUID

    token = credentials.credentials
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
    _: bool = Depends(require_feature_flag("user_accounts")),
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
    # Auto-verify if skip_email_verification is enabled (for smoke testing)
    auto_verify = settings.skip_email_verification

    user = User(
        email=request_data.email,
        password_hash=hash_password(request_data.password),
        verification_token=verification_token,
        verification_token_expires=datetime.now(timezone.utc) + timedelta(hours=24),
        is_verified=auto_verify,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"Email verification token generated for {request_data.email}")

    # Skip email sending in test mode
    if not auto_verify:
        await send_verification_email(
            email=user.email,
            verification_token=verification_token,
            expiry_hours=24,
        )

    message = "User registered." + (" Account verified automatically (test mode)." if auto_verify else " Please check email for verification link.")

    return RegisterResponse(
        message=message,
        user_id=str(user.id),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_feature_flag("user_accounts")),
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

        logger.info(f"Password reset token generated for {request_data.email}")

        await send_password_reset_email(
            email=user.email,
            reset_token=reset_token,
            expiry_hours=1,
        )

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
    _: bool = Depends(require_feature_flag("api_keys")),
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
    _: bool = Depends(require_feature_flag("api_keys")),
):
    """
    List all API keys for current user.
    """
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id).order_by(APIKey.created_at.desc())
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
    _: bool = Depends(require_feature_flag("api_keys")),
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


# ============================================
# OAuth Endpoints (Issue #980)
# ============================================


class OAuthAuthorizationRequest(BaseModel):
    """Optional request to link OAuth to existing account"""

    email: Optional[EmailStr] = None


class OAuthLinkRequest(BaseModel):
    """Request to link OAuth account to existing user"""

    oauth_provider: str
    oauth_provider_user_id: str
    oauth_email: Optional[str] = None


class OAuthCallbackResponse(BaseModel):
    """OAuth callback response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool
    message: str


class OAuthProviderStatus(BaseModel):
    """OAuth provider connection status"""

    provider: str
    enabled: bool
    connected: bool
    email: Optional[str] = None
    username: Optional[str] = None


@router.get("/oauth/{provider}", tags=["OAuth"])
async def get_oauth_authorization_url(
    provider: str,
    response: Response,
):
    """
    Get OAuth authorization URL for the specified provider.

    Providers: discord, github, google
    """
    provider = provider.lower()

    if provider not in ["discord", "github", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}. Supported: discord, github, google",
        )

    oauth_service_instance = oauth_service
    oauth_provider = oauth_service_instance.get_provider(provider)

    if not oauth_provider:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider.title()} OAuth is not configured",
        )

    oauth_state: str = generate_oauth_state()
    oauth_authorization_url: str = oauth_provider.get_authorization_url(oauth_state)
    cookie_val: str = oauth_state
    cookie_key: str = f"oauth_state_{provider.lower()}"
    response.set_cookie(
        key=cookie_key,
        value=cookie_val,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600,
    )

    return {"authorization_url": oauth_authorization_url, "state": oauth_state}


@router.get("/oauth/{provider}/callback", tags=["OAuth"])
async def oauth_callback(
    provider: str,
    code: str,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth callback endpoint.

    Handles the OAuth callback from the provider and either:
    - Creates a new user account
    - Logs in existing user via OAuth
    - Links OAuth account to existing user (if email matches)
    """
    provider = provider.lower()

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}",
        )

    if provider not in ["discord", "github", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )

    oauth_provider = oauth_service.get_provider(provider)
    if not oauth_provider:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider.title()} OAuth is not configured",
        )

    oauth_user_info = await oauth_provider.exchange_code(code)

    existing_oauth_account = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.oauth_provider == provider,
            OAuthAccount.oauth_provider_user_id == oauth_user_info.provider_user_id,
        )
    )
    oauth_account = existing_oauth_account.scalar_one_or_none()

    if oauth_account:
        result = await db.execute(select(User).where(User.id == oauth_account.user_id))
        user = result.scalar_one_or_none()
        if user:
            access_token = create_access_token(str(user.id))
            refresh_token = create_refresh_token(str(user.id))
            return OAuthCallbackResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                is_new_user=False,
                message="Logged in successfully",
            )

    if oauth_user_info.email:
        result = await db.execute(select(User).where(User.email == oauth_user_info.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            new_oauth_account = OAuthAccount(
                user_id=existing_user.id,
                oauth_provider=provider,
                oauth_provider_user_id=oauth_user_info.provider_user_id,
                oauth_access_token=oauth_user_info.access_token,
                oauth_refresh_token=oauth_user_info.refresh_token,
                oauth_token_expires_at=oauth_user_info.expires_at,
                oauth_email=oauth_user_info.email,
                oauth_username=oauth_user_info.username,
            )
            db.add(new_oauth_account)
            await db.commit()

            access_token = create_access_token(str(existing_user.id))
            refresh_token = create_refresh_token(str(existing_user.id))
            return OAuthCallbackResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                is_new_user=False,
                message="OAuth account linked to existing user",
            )

    verification_token = generate_verification_token()
    temp_password = secrets.token_urlsafe(32)

    new_user = User(
        email=oauth_user_info.email or f"{provider}_{oauth_user_info.provider_user_id}@oauth.local",
        password_hash=hash_password(temp_password),
        is_verified=True,
        verification_token=verification_token,
        verification_token_expires=datetime.now(timezone.utc) + timedelta(hours=24),
        oauth_provider=provider,
        oauth_provider_user_id=oauth_user_info.provider_user_id,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    new_oauth_account = OAuthAccount(
        user_id=new_user.id,
        oauth_provider=provider,
        oauth_provider_user_id=oauth_user_info.provider_user_id,
        oauth_access_token=oauth_user_info.access_token,
        oauth_refresh_token=oauth_user_info.refresh_token,
        oauth_token_expires_at=oauth_user_info.expires_at,
        oauth_email=oauth_user_info.email,
        oauth_username=oauth_user_info.username,
    )
    db.add(new_oauth_account)
    await db.commit()

    access_token = create_access_token(str(new_user.id))
    refresh_token = create_refresh_token(str(new_user.id))
    return OAuthCallbackResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        is_new_user=True,
        message="Account created successfully",
    )


@router.get("/oauth/{provider}/status", tags=["OAuth"])
async def get_oauth_status(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get OAuth connection status for a provider.
    """
    provider = provider.lower()

    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.user_id == current_user.id,
            OAuthAccount.oauth_provider == provider,
        )
    )
    oauth_account = result.scalar_one_or_none()

    return OAuthProviderStatus(
        provider=provider,
        enabled=oauth_service.is_provider_enabled(provider),
        connected=oauth_account is not None,
        email=oauth_account.oauth_email if oauth_account else None,
        username=oauth_account.oauth_username if oauth_account else None,
    )


@router.delete("/oauth/{provider}/unlink", tags=["OAuth"])
async def unlink_oauth_account(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Unlink OAuth account from user.

    User must have a password set to unlink OAuth.
    """
    provider = provider.lower()

    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink last authentication method. Please set a password first.",
        )

    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.user_id == current_user.id,
            OAuthAccount.oauth_provider == provider,
        )
    )
    oauth_account = result.scalar_one_or_none()

    if not oauth_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {provider} account linked",
        )

    await db.delete(oauth_account)
    await db.commit()

    return MessageResponse(message=f"{provider.title()} account unlinked successfully")


@router.post("/oauth/link", tags=["OAuth"])
async def link_oauth_account(
    request_data: OAuthLinkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Link an OAuth account to the current user.
    """
    provider = request_data.oauth_provider.lower()

    if provider not in ["discord", "github", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )

    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link OAuth to account without password. Please set a password first.",
        )

    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.oauth_provider == provider,
            OAuthAccount.oauth_provider_user_id == request_data.oauth_provider_user_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This OAuth account is already linked to another user",
        )

    new_oauth_account = OAuthAccount(
        user_id=current_user.id,
        oauth_provider=provider,
        oauth_provider_user_id=request_data.oauth_provider_user_id,
        oauth_email=request_data.oauth_email,
    )
    db.add(new_oauth_account)
    await db.commit()

    return MessageResponse(message=f"{provider.title()} account linked successfully")
