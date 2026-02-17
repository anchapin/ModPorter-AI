"""
CurseForge API Integration Service

Provides integration with CurseForge API for mod search and download.
API Documentation: https://curseforge.atlassian.net/wiki/spaces/CURSE/pages/2924450435/Game+Versions+v1
"""

import os
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# CurseForge API configuration
CURSEFORGE_API_BASE_URL = "https://api.curseforge.com/v1"
# Note: Requires API key in production - get from https://console.curseforge.com/
CURSEFORGE_API_KEY = os.getenv("CURSEFORGE_API_KEY", "")


class CurseForgeService:
    """Service for interacting with CurseForge API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or CURSEFORGE_API_KEY
        self.base_url = CURSEFORGE_API_BASE_URL
        self.headers = {
            "Accept": "application/json",
            "x-api-key": self.api_key,
        } if self.api_key else {"Accept": "application/json"}
    
    async def search_mods(
        self,
        query: str,
        game_version: Optional[str] = None,
        category_id: Optional[int] = None,
        sort_order: str = "popularity",
        page_index: int = 0,
        page_size: int = 25,
    ) -> Dict[str, Any]:
        """
        Search for mods on CurseForge
        
        Args:
            query: Search query string
            game_version: Filter by Minecraft version (e.g., "1.20.1")
            category_id: Filter by category ID
            sort_order: Sort order - "popularity", "lastUpdated", "name", "totalDownloads"
            page_index: Page number for pagination
            page_size: Number of results per page
            
        Returns:
            Dictionary with search results and metadata
        """
        endpoint = f"{self.base_url}/mods/search"
        
        params = {
            "searchFilter": query,
            "pageIndex": page_index,
            "pageSize": page_size,
            "sortOrder": sort_order,
        }
        
        if game_version:
            params["gameVersion"] = game_version
        if category_id:
            params["categoryId"] = category_id
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self.headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"CurseForge API error: {e}")
                raise
    
    async def get_mod_info(self, mod_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific mod
        
        Args:
            mod_id: The CurseForge mod ID
            
        Returns:
            Dictionary with mod details
        """
        endpoint = f"{self.base_url}/mods/{mod_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"CurseForge API error: {e}")
                raise
    
    async def get_mod_files(
        self,
        mod_id: int,
        game_version: Optional[str] = None,
        page_index: int = 0,
    ) -> Dict[str, Any]:
        """
        Get files/versions for a specific mod
        
        Args:
            mod_id: The CurseForge mod ID
            game_version: Filter by game version
            page_index: Page number for pagination
            
        Returns:
            Dictionary with file list
        """
        endpoint = f"{self.base_url}/mods/{mod_id}/files"
        
        params = {
            "pageIndex": page_index,
        }
        if game_version:
            params["gameVersion"] = game_version
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self.headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"CurseForge API error: {e}")
                raise
    
    async def get_file_download_url(
        self,
        mod_id: int,
        file_id: int,
    ) -> str:
        """
        Get download URL for a specific mod file
        
        Args:
            mod_id: The CurseForge mod ID
            file_id: The file ID to download
            
        Returns:
            Download URL string
        """
        endpoint = f"{self.base_url}/mods/{mod_id}/files/{file_id}/download-url"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", "")
            except httpx.HTTPError as e:
                logger.error(f"CurseForge API error: {e}")
                raise
    
    async def get_categories(self, game_id: int = 432) -> Dict[str, Any]:
        """
        Get available categories for a game
        
        Args:
            game_id: Game ID (432 = Minecraft)
            
        Returns:
            Dictionary with categories
        """
        endpoint = f"{self.base_url}/categories"
        params = {"gameId": game_id}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    endpoint,
                    headers=self.headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"CurseForge API error: {e}")
                raise
    
    def parse_curseforge_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a CurseForge URL to extract mod information
        
        Supports URLs like:
        - https://www.curseforge.com/minecraft/mods/mod-name
        - https://curseforge.com/minecraft/mods/mod-name
        
        Args:
            url: The CurseForge URL to parse
            
        Returns:
            Dictionary with parsed information or None if invalid
        """
        import re
        
        # Pattern for CurseForge mod URLs
        pattern = r'(?:https?://)?(?:www\.)?curseforge\.com/minecraft/mods/([^/?]+)'
        match = re.search(pattern, url, re.IGNORECASE)
        
        if match:
            slug = match.group(1)
            return {
                "platform": "curseforge",
                "slug": slug,
                "url": f"https://www.curseforge.com/minecraft/mods/{slug}",
            }
        
        return None


# Singleton instance
curseforge_service = CurseForgeService()
