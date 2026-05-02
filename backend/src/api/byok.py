"""
BYOK (Bring Your Own Key) API Key Management

Endpoints for secure submission, validation, and management of user-supplied LLM API keys.
Issue: #1227 - Security: BYOK API key vault

Endpoints:
- POST /api/v1/byok/keys - Submit and validate a new API key
- GET /api/v1/byok/keys - List BYOK key status (masked)
- DELETE /api/v1/byok/keys - Remove user's BYOK key
- POST /api/v1/byok/keys/test - Test connection with BYOK key
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import User
from security.auth import get_current_user
from security.byok_vault import (
    LLMProvider,
    byok_vault,
    validate_api_key,
    BYOKValidationError,
    BYOKEncryptionError,
)
from services.feature_flags import is_feature_enabled, FeatureFlagNotEnabledError

logger = logging.getLogger(__name__)
security = HTTPBearer()


def require_feature_flag(flag_name: str):
    """Dependency that checks if a feature flag is enabled."""

    async def check_flag():
        if not is_feature_enabled(flag_name):
            raise FeatureFlagNotEnabledError(f"Feature '{flag_name}' is not enabled")
        return True

    return check_flag


router = APIRouter(prefix="/byok", tags=["BYOK"])


class BYOKKeySubmitRequest(BaseModel):
    """Request to submit a new BYOK API key"""

    api_key: str = Field(..., min_length=10, max_length=500)
    provider: str = Field(..., pattern="^(openrouter|openai)$")
    label: Optional[str] = Field(None, max_length=100)

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v):
        if not v or v.strip() == "":
            raise ValueError("API key cannot be empty")
        return v.strip()

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v):
        return v.lower()


class BYOKKeyResponse(BaseModel):
    """Response for BYOK key operations"""

    success: bool
    message: str
    provider: Optional[str] = None
    label: Optional[str] = None
    masked_key: Optional[str] = None
    key_exists: bool = False


class BYOKKeyStatusResponse(BaseModel):
    """Response for BYOK key status check"""

    enabled: bool
    provider: Optional[str] = None
    label: Optional[str] = None
    has_key: bool


class BYOKTestResponse(BaseModel):
    """Response for BYOK key test"""

    success: bool
    message: str
    provider: str


@router.post("/keys", response_model=BYOKKeyResponse, status_code=status.HTTP_201_CREATED)
async def submit_byok_key(
    request_data: BYOKKeySubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_feature_flag("byok_api_keys")),
):
    """
    Submit and validate a new BYOK API key.

    The key is validated by making a test call to the provider before storage.
    On success, the key is encrypted and stored securely.
    """
    logger.info(f"BYOK key submission for user {current_user.id}")

    try:
        provider_enum = LLMProvider(request_data.provider)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider. Supported: openrouter, openai",
        )

    try:
        await validate_api_key(request_data.api_key, provider_enum)
    except BYOKValidationError as e:
        logger.warning(f"BYOK key validation failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"BYOK validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate API key. Please try again later.",
        )

    try:
        encrypted_key = byok_vault.encrypt(request_data.api_key)
    except BYOKEncryptionError as e:
        logger.error(f"BYOK encryption failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to encrypt API key",
        )

    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(
            llm_api_key_encrypted=encrypted_key,
            llm_api_key_provider=request_data.provider,
            llm_api_key_label=request_data.label,
            byok_enabled=True,
        )
    )
    await db.commit()

    masked = byok_vault.mask_key(request_data.api_key)

    logger.info(f"BYOK key stored successfully for user {current_user.id}")

    return BYOKKeyResponse(
        success=True,
        message="API key validated and stored securely",
        provider=request_data.provider,
        label=request_data.label,
        masked_key=masked,
        key_exists=True,
    )


@router.get("/keys", response_model=BYOKKeyStatusResponse)
async def get_byok_key_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_feature_flag("byok_api_keys")),
):
    """
    Get BYOK key status for the current user.

    Returns masked key identifier (last 4 chars only) if key exists.
    """
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    masked_key = None
    if user.llm_api_key_encrypted:
        try:
            decrypted = byok_vault.decrypt(user.llm_api_key_encrypted)
            masked_key = byok_vault.mask_key(decrypted)
        except BYOKEncryptionError:
            masked_key = "**** (corrupted)"

    return BYOKKeyStatusResponse(
        enabled=user.byok_enabled,
        provider=user.llm_api_key_provider,
        label=user.llm_api_key_label,
        has_key=user.llm_api_key_encrypted is not None,
    )


@router.delete("/keys", response_model=BYOKKeyResponse)
async def delete_byok_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_feature_flag("byok_api_keys")),
):
    """
    Delete the user's BYOK API key.

    This downgrades them to standard billing (PortKit-managed inference).
    """
    logger.info(f"BYOK key deletion for user {current_user.id}")

    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.llm_api_key_encrypted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No BYOK API key found",
        )

    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(
            llm_api_key_encrypted=None,
            llm_api_key_provider=None,
            llm_api_key_label=None,
            byok_enabled=False,
        )
    )
    await db.commit()

    logger.info(f"BYOK key deleted for user {current_user.id}")

    return BYOKKeyResponse(
        success=True,
        message="BYOK API key removed. You are now on standard billing.",
        key_exists=False,
    )


@router.post("/keys/test", response_model=BYOKTestResponse)
async def test_byok_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_feature_flag("byok_api_keys")),
):
    """
    Test the user's BYOK API key by making a validation call.

    Returns success or error message based on key validity.
    """
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.llm_api_key_encrypted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No BYOK API key configured",
        )

    if not user.llm_api_key_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider not set for BYOK key",
        )

    try:
        decrypted_key = byok_vault.decrypt(user.llm_api_key_encrypted)
    except BYOKEncryptionError as e:
        logger.error(f"Failed to decrypt BYOK key for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt stored API key",
        )

    try:
        provider_enum = LLMProvider(user.llm_api_key_provider)
        await validate_api_key(decrypted_key, provider_enum)
    except BYOKValidationError as e:
        return BYOKTestResponse(
            success=False,
            message=str(e),
            provider=user.llm_api_key_provider,
        )
    except Exception as e:
        logger.error(f"BYOK test failed: {e}")
        return BYOKTestResponse(
            success=False,
            message="Failed to test API key. Please try again.",
            provider=user.llm_api_key_provider,
        )

    return BYOKTestResponse(
        success=True,
        message="API key is valid and working",
        provider=user.llm_api_key_provider,
    )
