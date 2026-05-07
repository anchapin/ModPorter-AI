"""
Premium Conversion API Endpoints

Uses frontier AI models via OpenRouter for high-quality Java→Bedrock conversion.
Integrates with ai_engine/mmsd/premium_client.py.

Endpoints:
- POST /api/v1/premium/convert - Premium conversion using frontier models
- GET /api/v1/premium/models - List available premium models
- POST /api/v1/premium/estimate - Estimate cost for a conversion
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import User
from security.auth import get_current_user, verify_api_key
from services.feature_flags import is_feature_enabled, FeatureFlagNotEnabledError

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/premium", tags=["Premium Conversion"])


class PremiumConvertRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=5000)
    java_source: str = Field(..., min_length=1)
    model: Optional[str] = Field(None, description="Model to use: deepseek-v4-pro, kimi-k2, etc.")


class PremiumConvertResponse(BaseModel):
    success: bool
    reasoning: str = ""
    bedrock_manifest: str = ""
    bedrock_script: str = ""
    model_used: str = ""
    latency_ms: int = 0
    error: str = ""


class PremiumModelsResponse(BaseModel):
    models: dict


class PremiumEstimateResponse(BaseModel):
    model: str
    input_tokens_est: int
    output_tokens_est: int
    cost_usd_est: float


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Optional authentication for premium conversion."""
    if not credentials:
        return None

    token = credentials.credentials
    from uuid import UUID

    if token.startswith("mpk_"):
        return await verify_api_key(db, token)

    from security.auth import verify_token

    user_id = verify_token(token)
    if not user_id:
        return None

    try:
        user_uuid = UUID(user_id)
    except (ValueError, TypeError):
        return None

    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_uuid))
    return result.scalar_one_or_none()


def require_feature_flag(flag_name: str):
    """Dependency that checks if a feature flag is enabled."""

    async def check_flag():
        if not is_feature_enabled(flag_name):
            raise FeatureFlagNotEnabledError(f"Feature '{flag_name}' is not enabled")
        return True

    return check_flag


@router.post("/convert", response_model=PremiumConvertResponse)
async def premium_convert(
    request: PremiumConvertRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    _: bool = Depends(require_feature_flag("premium_features")),
):
    """
    Premium conversion using frontier AI models.

    Uses OpenRouter API with frontier models (DeepSeek V4 Pro, Kimi K2, GLM-5)
    for high-quality Java→Bedrock mod conversion with few-shot prompting.

    **Request Body:**
    ```json
    {
        "instruction": "Custom swords mod that adds glowing diamond swords",
        "java_source": "public class MyMod { ... }",
        "model": "deepseek-v4-pro"
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "reasoning": "## Conversion Plan\n\n1. Block registration...",
        "bedrock_manifest": "{\"format_version\": 2, ...}",
        "bedrock_script": "import { world } from '@minecraft/server';\\n...",
        "model_used": "deepseek-v4-pro",
        "latency_ms": 4500,
        "error": ""
    }
    ```
    """
    from ai_engine.mmsd.premium_client import PortKitPremium, ConversionResult

    api_key = os.environ.get("OPENROUTER_API_KEY", "")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Premium conversion is not configured. Set OPENROUTER_API_KEY env var.",
        )

    try:
        client = PortKitPremium(api_key=api_key, model=request.model or "deepseek-v4-pro")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    try:
        result = client.convert(
            instruction=request.instruction,
            java_source=request.java_source,
            model=request.model,
        )

        return PremiumConvertResponse(
            success=result.success,
            reasoning=result.reasoning,
            bedrock_manifest=result.bedrock_manifest,
            bedrock_script=result.bedrock_script,
            model_used=result.model_used,
            latency_ms=result.latency_ms,
            error=result.error,
        )
    finally:
        client.close()


@router.get("/models", response_model=PremiumModelsResponse)
async def list_premium_models(
    current_user: Optional[User] = Depends(get_optional_user),
    _: bool = Depends(require_feature_flag("premium_features")),
):
    """
    List available premium conversion models.

    **Response:**
    ```json
    {
        "models": {
            "deepseek-v4-pro": "deepseek/deepseek-chat-v3.1",
            "kimi-k2": "moonshotai/kimi-k2",
            "glm-5": "thudm/glm-4-32b",
            "deepseek-v4-flash": "deepseek/deepseek-chat-v3-0324"
        }
    }
    ```
    """
    from ai_engine.mmsd.premium_client import MODEL_CONFIGS

    return PremiumModelsResponse(models={k: v["model_id"] for k, v in MODEL_CONFIGS.items()})


@router.post("/estimate", response_model=PremiumEstimateResponse)
async def estimate_premium_cost(
    request: PremiumConvertRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    _: bool = Depends(require_feature_flag("premium_features")),
):
    """
    Estimate the API cost for a premium conversion.

    **Request Body:**
    ```json
    {
        "instruction": "Custom swords mod",
        "java_source": "public class MyMod {}",
        "model": "deepseek-v4-pro"
    }
    ```

    **Response:**
    ```json
    {
        "model": "deepseek-v4-pro",
        "input_tokens_est": 1200,
        "output_tokens_est": 2048,
        "cost_usd_est": 0.0054
    }
    ```
    """
    from ai_engine.mmsd.premium_client import PortKitPremium

    api_key = os.environ.get("OPENROUTER_API_KEY", "dummy-key-for-estimate")

    try:
        client = PortKitPremium(api_key=api_key)
        cost = client.estimate_cost(
            instruction=request.instruction,
            java_source=request.java_source,
            model=request.model,
        )
        client.close()

        return PremiumEstimateResponse(
            model=cost["model"],
            input_tokens_est=cost["input_tokens_est"],
            output_tokens_est=cost["output_tokens_est"],
            cost_usd_est=cost["cost_usd_est"],
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API key for estimation",
        )
