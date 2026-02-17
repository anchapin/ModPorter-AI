"""
Mod Imports API endpoints for CurseForge and Modrinth integration.

Provides endpoints for searching and downloading mods from CurseForge and Modrinth platforms.
"""

import uuid
import logging
import re
import os
import httpx
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, HttpUrl

from db.base import get_db

# Import services
from services.curseforge_service import CurseForgeService, curseforge_service
from services.modrinth_service import ModrinthService, modrinth_service

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Request/Response Models ====================

class ModSearchRequest(BaseModel):
    """Request model for searching mods"""
    query: str = Field(..., description="Search query string")
    platform: str = Field(..., description="Platform: 'curseforge' or 'modrinth'")
    game_version: Optional[str] = Field(None, description="Filter by Minecraft version (e.g., '1.20.1')")
    loader: Optional[str] = Field(None, description="Filter by loader (forge, fabric, quilt) - Modrinth only")
    sort_order: Optional[str] = Field("popularity", description="Sort order")
    page: int = Field(0, description="Page number for pagination")
    limit: int = Field(25, ge=1, le=100, description="Results per page")


class ModInfo(BaseModel):
    """Model for mod information"""
    platform: str
    mod_id: str
    name: str
    description: Optional[str] = None
    author: Optional[str] = None
    download_count: Optional[int] = None
    game_versions: Optional[List[str]] = None
    Loaders: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    url: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ModFile(BaseModel):
    """Model for mod file/version information"""
    file_id: str
    version: str
    game_versions: List[str]
    loaders: Optional[List[str]] = None
    file_name: str
    file_size: int
    download_url: Optional[str] = None
    release_type: Optional[str] = None
    created_at: Optional[str] = None


class URLParseResult(BaseModel):
    """Result of URL parsing"""
    platform: str
    mod_id: Optional[str] = None
    slug: Optional[str] = None
    url: str
    is_valid: bool
    error: Optional[str] = None


class ImportRequest(BaseModel):
    """Request to import a mod from URL"""
    url: str = Field(..., description="CurseForge or Modrinth mod URL")
    target_version: str = Field("1.20.0", description="Target Minecraft version")


class ImportResponse(BaseModel):
    """Response for mod import"""
    status: str
    message: str
    mod_info: Optional[ModInfo] = None
    file_id: Optional[str] = None


# ==================== Helper Functions ====================

def parse_mod_url(url: str) -> URLParseResult:
    """
    Parse a mod URL to determine platform and extract mod information.
    
    Supports:
    - CurseForge: https://curseforge.com/minecraft/mods/mod-name
    - Modrinth: https://modrinth.com/mod/mod-name
    """
    # Try CurseForge
    cf_pattern = r'(?:https?://)?(?:www\.)?curseforge\.com/minecraft/mods/([^/?]+)'
    cf_match = re.search(cf_pattern, url, re.IGNORECASE)
    if cf_match:
        slug = cf_match.group(1)
        return URLParseResult(
            platform="curseforge",
            slug=slug,
            url=f"https://www.curseforge.com/minecraft/mods/{slug}",
            is_valid=True
        )
    
    # Try Modrinth
    mr_pattern = r'(?:https?://)?(?:www\.)?modrinth\.com/(mod|resourcepack|plugin|pack)/([^/?]+)'
    mr_match = re.search(mr_pattern, url, re.IGNORECASE)
    if mr_match:
        project_type = mr_match.group(1)
        slug = mr_match.group(2)
        return URLParseResult(
            platform="modrinth",
            slug=slug,
            url=f"https://modrinth.com/{project_type}/{slug}",
            is_valid=True
        )
    
    # Try direct modrinth short URL
    mr_short_pattern = r'(?:https?://)?modrinth\.com/([^/?]+)'
    mr_short_match = re.search(mr_short_pattern, url, re.IGNORECASE)
    if mr_short_match:
        slug = mr_short_match.group(1)
        return URLParseResult(
            platform="modrinth",
            slug=slug,
            url=f"https://modrinth.com/mod/{slug}",
            is_valid=True
        )
    
    return URLParseResult(
        platform="unknown",
        url=url,
        is_valid=False,
        error="Unable to parse URL. Supported platforms: CurseForge, Modrinth"
    )


def transform_curseforge_mod(data: Dict[str, Any]) -> ModInfo:
    """Transform CurseForge API response to ModInfo"""
    mod_data = data.get("data", {})
    latest_file = mod_data.get("latestFiles", [{}])[0] if mod_data.get("latestFiles") else {}
    
    return ModInfo(
        platform="curseforge",
        mod_id=str(mod_data.get("id", "")),
        name=mod_data.get("name", ""),
        description=mod_data.get("summary", ""),
        author=", ".join([a.get("name", "") for a in mod_data.get("authors", [])]),
        download_count=mod_data.get("downloadCount"),
        game_versions=latest_file.get("gameVersions", []),
        Loaders=latest_file.get("modLoadors", []),
        thumbnail_url=mod_data.get("logo", {}).get("url"),
        url=f"https://www.curseforge.com/minecraft/mods/{mod_data.get('slug', '')}",
        created_at=mod_data.get("dateCreated"),
        updated_at=mod_data.get("dateModified")
    )


def transform_modrinth_mod(data: Dict[str, Any], project_type: str = "mod") -> ModInfo:
    """Transform Modrinth API response to ModInfo"""
    return ModInfo(
        platform="modrinth",
        mod_id=data.get("id", ""),
        name=data.get("title", ""),
        description=data.get("description", ""),
        author=data.get("author", ""),
        download_count=data.get("downloads"),
        game_versions=data.get("versions", []),
        Loaders=data.get("categories", []),
        thumbnail_url=data.get("icon_url"),
        url=f"https://modrinth.com/{project_type}/{data.get('slug', '')}",
        created_at=data.get("published"),
        updated_at=data.get("updated")
    )


def transform_curseforge_file(data: Dict[str, Any]) -> ModFile:
    """Transform CurseForge file response to ModFile"""
    return ModFile(
        file_id=str(data.get("id", "")),
        version=data.get("displayName", ""),
        game_versions=data.get("gameVersions", []),
        loaders=data.get("modLoadors", []),
        file_name=data.get("fileName", ""),
        file_size=data.get("fileLength", 0),
        download_url=data.get("downloadUrl"),
        release_type=data.get("releaseType", ""),
        created_at=data.get("fileDate")
    )


def transform_modrinth_version(data: Dict[str, Any]) -> ModFile:
    """Transform Modrinth version response to ModFile"""
    files = data.get("files", [{}])
    primary_file = files[0] if files else {}
    
    return ModFile(
        file_id=data.get("id", ""),
        version=data.get("version_number", ""),
        game_versions=data.get("game_versions", []),
        loaders=data.get("loaders", []),
        file_name=primary_file.get("filename", ""),
        file_size=primary_file.get("size", 0),
        download_url=primary_file.get("url"),
        release_type=data.get("release_type", ""),
        created_at=data.get("date_published")
    )


# ==================== API Endpoints ====================

@router.get("/parse-url", response_model=URLParseResult)
async def parse_url(url: str = Query(..., description="Mod URL to parse")):
    """
    Parse a CurseForge or Modrinth URL to identify the platform and mod.
    
    Returns platform, mod ID/slug, and validity status.
    """
    logger.info(f"Parsing URL: {url}")
    return parse_mod_url(url)


@router.get("/search", response_model=List[ModInfo])
async def search_mods(
    query: str = Query(..., description="Search query"),
    platform: str = Query(..., description="Platform: 'curseforge' or 'modrinth'"),
    game_version: Optional[str] = Query(None, description="Minecraft version filter"),
    loader: Optional[str] = Query(None, description="Loader filter (Modrinth: forge, fabric, quilt)"),
    sort_order: Optional[str] = Query("popularity", description="Sort order"),
    page: int = Query(0, ge=0, description="Page number"),
    limit: int = Query(25, ge=1, le=100, description="Results per page"),
):
    """
    Search for mods on CurseForge or Modrinth.
    
    Returns a list of mods matching the search criteria.
    """
    logger.info(f"Searching {platform} for: {query}")
    
    if platform not in ["curseforge", "modrinth"]:
        raise HTTPException(
            status_code=400,
            detail="Platform must be 'curseforge' or 'modrinth'"
        )
    
    try:
        if platform == "curseforge":
            results = await curseforge_service.search_mods(
                query=query,
                game_version=game_version,
                sort_order=sort_order,
                page_index=page,
                page_size=limit
            )
            
            mods = []
            for item in results.get("data", []):
                mods.append(transform_curseforge_mod({"data": item}))
            return mods
        
        else:  # modrinth
            results = await modrinth_service.search_mods(
                query=query,
                game_version=game_version,
                loader=loader,
                sort_order=sort_order,
                page=page,
                limit=limit
            )
            
            mods = []
            for item in results.get("hits", []):
                mods.append(transform_modrinth_mod(item))
            return mods
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search mods: {str(e)}"
        )


@router.get("/{platform}/mod/{mod_id}", response_model=ModInfo)
async def get_mod_info(
    platform: str,
    mod_id: str,
):
    """
    Get detailed information about a specific mod.
    """
    logger.info(f"Getting mod info: {platform}/{mod_id}")
    
    if platform not in ["curseforge", "modrinth"]:
        raise HTTPException(
            status_code=400,
            detail="Platform must be 'curseforge' or 'modrinth'"
        )
    
    try:
        if platform == "curseforge":
            cf_id = int(mod_id)
            result = await curseforge_service.get_mod_info(cf_id)
            return transform_curseforge_mod(result)
        
        else:  # modrinth
            result = await modrinth_service.get_project(mod_id)
            return transform_modrinth_mod(result)
    
    except Exception as e:
        logger.error(f"Get mod info error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get mod info: {str(e)}"
        )


@router.get("/{platform}/mod/{mod_id}/files", response_model=List[ModFile])
async def get_mod_files(
    platform: str,
    mod_id: str,
    game_version: Optional[str] = Query(None, description="Filter by game version"),
):
    """
    Get available files/versions for a specific mod.
    """
    logger.info(f"Getting mod files: {platform}/{mod_id}")
    
    if platform not in ["curseforge", "modrinth"]:
        raise HTTPException(
            status_code=400,
            detail="Platform must be 'curseforge' or 'modrinth'"
        )
    
    try:
        if platform == "curseforge":
            cf_id = int(mod_id)
            result = await curseforge_service.get_mod_files(
                cf_id,
                game_version=game_version
            )
            
            files = []
            for item in result.get("data", []):
                files.append(transform_curseforge_file(item))
            return files
        
        else:  # modrinth
            versions = await modrinth_service.get_project_versions(
                mod_id,
                game_version=game_version
            )
            
            files = []
            for item in versions:
                files.append(transform_modrinth_version(item))
            return files
    
    except Exception as e:
        logger.error(f"Get mod files error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get mod files: {str(e)}"
        )


@router.post("/import", response_model=ImportResponse)
async def import_mod(
    request: ImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Import a mod from CurseForge or Modrinth URL.
    
    Downloads the mod file and creates a conversion job.
    """
    logger.info(f"Importing mod from URL: {request.url}")
    
    # Parse the URL
    parse_result = parse_mod_url(request.url)
    
    if not parse_result.is_valid:
        return ImportResponse(
            status="error",
            message=parse_result.error or "Invalid URL",
            mod_info=None
        )
    
    try:
        # Get mod info and download
        if parse_result.platform == "curseforge":
            # Find mod by slug
            search_results = await curseforge_service.search_mods(parse_result.slug or "")
            if not search_results.get("data"):
                return ImportResponse(
                    status="error",
                    message=f"Mod not found: {parse_result.slug}",
                    mod_info=None
                )
            
            mod_data = search_results["data"][0]
            mod_id = mod_data.get("id")
            
            # Get mod details
            mod_details = await curseforge_service.get_mod_info(mod_id)
            mod_info = transform_curseforge_mod(mod_details)
            
            # Get latest file
            files_result = await curseforge_service.get_mod_files(mod_id)
            if not files_result.get("data"):
                return ImportResponse(
                    status="error",
                    message="No files available for this mod",
                    mod_info=mod_info
                )
            
            latest_file = files_result["data"][0]
            file_id = latest_file.get("id")
            
            # Get download URL
            download_url = await curseforge_service.get_file_download_url(mod_id, file_id)
            
        else:  # modrinth
            slug = parse_result.slug
            
            # Get project details
            project = await modrinth_service.get_project(slug)
            mod_info = transform_modrinth_mod(project)
            
            # Get latest version
            versions = await modrinth_service.get_project_versions(slug)
            if not versions:
                return ImportResponse(
                    status="error",
                    message="No versions available for this mod",
                    mod_info=mod_info
                )
            
            latest_version = versions[0]
            version_id = latest_version.get("id")
            
            # Get download URL
            download_url = await modrinth_service.get_file_download_url(version_id)
        
        if not download_url:
            return ImportResponse(
                status="error",
                message="Could not get download URL",
                mod_info=mod_info
            )
        
        # Download the file
        file_id = str(uuid.uuid4())
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, f"{file_id}.jar")
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("GET", download_url) as response:
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
        
        return ImportResponse(
            status="success",
            message=f"Mod downloaded successfully. File ID: {file_id}",
            mod_info=mod_info,
            file_id=file_id
        )
    
    except Exception as e:
        logger.error(f"Import error: {e}")
        return ImportResponse(
            status="error",
            message=f"Failed to import mod: {str(e)}",
            mod_info=None
        )


@router.get("/categories/{platform}")
async def get_categories(platform: str):
    """
    Get available categories for a platform.
    """
    logger.info(f"Getting categories for: {platform}")
    
    if platform not in ["curseforge", "modrinth"]:
        raise HTTPException(
            status_code=400,
            detail="Platform must be 'curseforge' or 'modrinth'"
        )
    
    try:
        if platform == "curseforge":
            result = await curseforge_service.get_categories()
            return result.get("data", [])
        
        else:  # modrinth
            categories = await modrinth_service.get_categories()
            return categories
    
    except Exception as e:
        logger.error(f"Get categories error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get categories: {str(e)}"
        )


@router.get("/loaders")
async def get_loaders():
    """
    Get available loaders for Modrinth.
    """
    try:
        loaders = await modrinth_service.get_loaders()
        return loaders
    except Exception as e:
        logger.error(f"Get loaders error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get loaders: {str(e)}"
        )
