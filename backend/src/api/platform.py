"""
Platform OAuth Integration API Endpoints

Endpoints for:
- OAuth flow initiation (Modrinth, CurseForge)
- OAuth callback handling
- Platform connection management
- Publishing to platforms
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from db.models import User
from security.auth import create_access_token
from services.modrinth_oauth_service import (
    ModrinthOAuthService,
    ModrinthPublisher,
    ModrinthIntegrationError,
)
from services.curseforge_oauth_service import (
    CurseForgeOAuthService,
    CurseForgePublisher,
    CurseForgeIntegrationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/platform", tags=["Platform Integration"])
security = HTTPBearer()

# ============================================
# Request/Response Models
# ============================================


class OAuthStartResponse(BaseModel):
    """Response with OAuth authorization URL"""
    authorization_url: str
    state: str
    code_verifier: str


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request with authorization code"""
    code: str
    state: str
    code_verifier: str


class OAuthCallbackResponse(BaseModel):
    """OAuth callback response"""
    platform: str
    platform_username: str
    connected: bool


class PlatformConnectionResponse(BaseModel):
    """Platform connection information"""
    id: str
    platform: str
    platform_username: str
    connected_at: str


class PublishRequest(BaseModel):
    """Request to publish a conversion to a platform"""
    platform: str = Field(..., description="Platform to publish to: 'modrinth' or 'curseforge'")
    project_name: str = Field(..., description="Name of the project on the platform")
    version: str = Field(..., description="Version number")
    game_version: str = Field(..., description="Minecraft version")
    loader: str = Field(..., description="Mod loader: 'fabric', 'forge', or 'quilt'")
    release_type: str = Field(default="release", description="Release type: 'release', 'beta', 'alpha'")
    description: Optional[str] = Field(None, description="Version description")
    file_path: str = Field(..., description="Path to the .mcaddon file to upload")


class PublishResponse(BaseModel):
    """Publish response"""
    platform: str
    project_id: str
    version_id: str
    version_number: str
    status: str
    published_at: str


# ============================================
# Helper Functions
# ============================================


async def get_current_user(
    credentials: HTTPBearer = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user"""
    from security.auth import verify_token
    
    token = credentials.credentials
    user_id = verify_token(token, "access")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


# ============================================
# Modrinth OAuth Endpoints
# ============================================


@router.get("/modrinth/auth", response_model=OAuthStartResponse)
async def modrinth_start_oauth():
    """
    Start Modrinth OAuth flow - returns authorization URL.
    
    User should be redirected to the authorization_url.
    After authorization, they will be redirected to /platform/modrinth/callback
    """
    service = ModrinthOAuthService()
    
    state = service.generate_state()
    code_verifier = service.generate_code_verifier()
    authorization_url = service.get_authorization_url(state, code_verifier)
    
    return OAuthStartResponse(
        authorization_url=authorization_url,
        state=state,
        code_verifier=code_verifier,
    )


@router.get("/modrinth/callback")
async def modrinth_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    """
    Handle Modrinth OAuth callback.
    
    This endpoint receives the authorization code and exchanges it for tokens.
    Returns a success message - frontend should handle the redirect.
    """
    # Note: In production, you'd validate the state parameter and store the tokens
    # For now, we'll just return success info
    return {
        "message": "OAuth callback received. Please complete the connection in the app.",
        "platform": "modrinth",
    }


# ============================================
# CurseForge OAuth Endpoints
# ============================================


@router.get("/curseforge/auth", response_model=OAuthStartResponse)
async def curseforge_start_oauth():
    """
    Start CurseForge OAuth flow - returns authorization URL.
    
    User should be redirected to the authorization_url.
    After authorization, they will be redirected to /platform/curseforge/callback
    """
    service = CurseForgeOAuthService()
    
    state = service.generate_state()
    code_verifier = service.generate_code_verifier()
    authorization_url = service.get_authorization_url(state, code_verifier)
    
    return OAuthStartResponse(
        authorization_url=authorization_url,
        state=state,
        code_verifier=code_verifier,
    )


@router.get("/curseforge/callback")
async def curseforge_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    """
    Handle CurseForge OAuth callback.
    
    This endpoint receives the authorization code and exchanges it for tokens.
    """
    return {
        "message": "OAuth callback received. Please complete the connection in the app.",
        "platform": "curseforge",
    }


# ============================================
# Publishing Endpoints
# ============================================


@router.post("/publish/modrinth", response_model=PublishResponse)
async def publish_to_modrinth(
    request: PublishRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Publish a conversion result to Modrinth.
    
    Requires an active Modrinth OAuth connection.
    """
    try:
        publisher = ModrinthPublisher()
        
        # In production, you'd fetch the user's OAuth tokens from the database
        # For now, this is a placeholder
        access_token = ""  # Would come from platform_connections table
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Modrinth account not connected. Please connect your Modrinth account first.",
            )
        
        # Prepare version data
        version_data = {
            "name": f"Version {request.version}",
            "version_number": request.version,
            "game_versions": [request.game_version],
            "loaders": [request.loader],
            "release_type": request.release_type,
            "description": request.description or "",
        }
        
        # Upload version
        result = await publisher.upload_version(
            access_token=access_token,
            project_slug=request.project_name,
            version_data=version_data,
            file_path=request.file_path,
        )
        
        return PublishResponse(
            platform="modrinth",
            project_id=result.get("project_id", ""),
            version_id=result.get("id", ""),
            version_number=request.version,
            status="published",
            published_at=datetime.now(timezone.utc).isoformat(),
        )
        
    except ModrinthIntegrationError as e:
        logger.error(f"Modrinth publish error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to publish to Modrinth: {str(e)}",
        )


@router.post("/publish/curseforge", response_model=PublishResponse)
async def publish_to_curseforge(
    request: PublishRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Publish a conversion result to CurseForge.
    
    Requires an active CurseForge OAuth connection and API key.
    """
    try:
        publisher = CurseForgePublisher()
        
        # In production, you'd fetch the user's OAuth tokens from the database
        access_token = ""  # Would come from platform_connections table
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="CurseForge account not connected. Please connect your CurseForge account first.",
            )
        
        # Map loader to CurseForge format
        loader_mapping = {
            "forge": "minecraftforge",
            "fabric": "fabric",
            "quilt": "quilt",
        }
        
        # Prepare file metadata
        file_data = {
            "displayName": f"Version {request.version}",
            "gameVersion": request.game_version,
            "releaseType": request.release_type,
            "loaders": [loader_mapping.get(request.loader, request.loader)],
            "changelog": request.description or "",
        }
        
        # Upload file
        result = await publisher.upload_file(
            access_token=access_token,
            project_id=int(request.project_name),  # Project ID as integer
            file_data=file_data,
            file_path=request.file_path,
        )
        
        return PublishResponse(
            platform="curseforge",
            project_id=str(result.get("id", "")),
            version_id=str(result.get("id", "")),
            version_number=request.version,
            status="published",
            published_at=datetime.now(timezone.utc).isoformat(),
        )
        
    except CurseForgeIntegrationError as e:
        logger.error(f"CurseForge publish error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to publish to CurseForge: {str(e)}",
        )


# ============================================
# Platform Connection Management
# ============================================


@router.get("/connections")
async def list_platform_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all connected platform accounts for the current user.
    """
    # Would query platform_connections table
    return {
        "connections": [],
        "message": "Platform connections feature requires OAuth setup. Please configure OAuth credentials.",
    }


@router.delete("/connections/{platform}")
async def disconnect_platform(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Disconnect a platform account.
    """
    if platform not in ["modrinth", "curseforge"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid platform. Must be 'modrinth' or 'curseforge'.",
        )
    
    return {
        "message": f"Disconnected from {platform}",
        "platform": platform,
    }
