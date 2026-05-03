"""
BYOK Integration Service

Provides integration between user BYOK API keys and the LLM dispatch layer.
Issue: #1227 - Security: BYOK API key vault

This module handles:
- Decrypting user API keys when needed for conversion jobs
- Injecting user keys into LLM requests
- Error handling for BYOK key failures during conversion
"""

import logging
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User
from security.byok_vault import (
    byok_vault,
    LLMProvider,
    BYOKEncryptionError,
)

logger = logging.getLogger(__name__)


@dataclass
class BYOKContext:
    """Context object containing decrypted BYOK key for a conversion job"""

    user_id: str
    api_key: str
    provider: LLMProvider
    is_byok: bool = True


class BYOKIntegrationError(Exception):
    """Raised when BYOK integration fails"""

    pass


class BYOKKeyNotFoundError(Exception):
    """Raised when user has no BYOK key configured"""

    pass


async def get_user_byok_context(
    db: AsyncSession,
    user_id: str,
) -> Optional[BYOKContext]:
    """
    Get the BYOK context for a user if they have a BYOK key configured.

    Args:
        db: Database session
        user_id: User ID to look up

    Returns:
        BYOKContext if user has BYOK key, None otherwise
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return None

    if not user.byok_enabled or not user.llm_api_key_encrypted:
        return None

    try:
        provider_enum = LLMProvider(user.llm_api_key_provider)
    except ValueError:
        logger.error(f"Invalid BYOK provider for user {user_id}: {user.llm_api_key_provider}")
        return None

    try:
        decrypted_key = byok_vault.decrypt(user.llm_api_key_encrypted)
    except BYOKEncryptionError as e:
        logger.error(f"Failed to decrypt BYOK key for user {user_id}: {e}")
        return None

    return BYOKContext(
        user_id=str(user.id),
        api_key=decrypted_key,
        provider=provider_enum,
        is_byok=True,
    )


def format_byok_error(status_code: int, error_message: str) -> str:
    """
    Format a user-facing error message for BYOK key failures during conversion.

    Args:
        status_code: HTTP status code from the LLM API response
        error_message: Error message from the LLM API

    Returns:
        User-friendly error message
    """
    ERROR_MESSAGES: dict[int, str] = {
        401: "Your API key is invalid or has been revoked. Please check your API key settings or submit a new key.",
        403: "Your API key does not have permission for this operation. Please check your API key settings.",
        429: "Your API key is rate-limited. Please check your API key settings or try again later.",
        500: "The LLM provider is experiencing issues. Please try again in a few minutes.",
    }
    if status_code in ERROR_MESSAGES:
        return ERROR_MESSAGES[status_code]
    return f"Your API key failed during conversion: {error_message}. Please check your API key settings."


def get_byok_headers(ctx: BYOKContext) -> dict:
    """
    Get the appropriate headers for a BYOK request.

    Args:
        ctx: BYOK context containing the decrypted API key

    Returns:
        Dictionary of headers to include in LLM requests
    """
    if ctx.provider == LLMProvider.OPENROUTER:
        return {"HTTP-Referer": "https://portkit.com", "X-Title": "Portkit"}
    elif ctx.provider == LLMProvider.OPENAI:
        return {}
    else:
        return {}


async def inject_byok_key_into_ai_engine_request(
    db: AsyncSession,
    user_id: str,
    request_data: dict,
) -> dict:
    """
    Inject a user's BYOK API key into an AI Engine request.

    If the user has a BYOK key, their decrypted key is injected into
    the request headers that will be passed to the AI Engine.

    Args:
        db: Database session
        user_id: User ID
        request_data: Original request data dictionary

    Returns:
        Modified request data with BYOK key injected (if applicable)
    """
    byok_ctx = await get_user_byok_context(db, user_id)

    if not byok_ctx:
        return request_data

    headers = get_byok_headers(byok_ctx)
    headers["X-User-API-Key"] = byok_ctx.api_key
    headers["X-User-API-Provider"] = byok_ctx.provider.value

    if "headers" not in request_data:
        request_data["headers"] = {}
    request_data["headers"].update(headers)
    request_data["_byok_enabled"] = True
    request_data["_byok_provider"] = byok_ctx.provider.value

    logger.info(f"BYOK key injected for user {user_id}, provider: {byok_ctx.provider.value}")

    return request_data


def should_fallback_to_system_key(byok_error: Exception) -> bool:
    """
    Determine if we should fallback to system key when BYOK fails.

    For BYOK users, we generally want to fail rather than fallback
    (to avoid using system key on user's behalf).

    Args:
        byok_error: The exception that occurred

    Returns:
        False for BYOK users (fail rather than fallback)
    """
    return False


def create_byok_error_response(status_code: int, message: str) -> dict:
    """
    Create a standardized error response for BYOK failures.

    Args:
        status_code: HTTP status code
        message: Error message

    Returns:
        Error response dictionary
    """
    return {
        "error": "byok_key_failed",
        "message": format_byok_error(status_code, message),
        "user_action_required": True,
        "can_retry": status_code in (429, 500),
    }
