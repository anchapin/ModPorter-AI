"""
Modrinth API Integration Service

Provides integration with Modrinth API for mod search and download.
API Documentation: https://docs.modrinth.app/api-v2/
"""

import os
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import hashlib

logger = logging.getLogger(__name__)

# Modrinth API configuration
MODRINTH_API_BASE_URL = "https://api.modrinth.com/v2"
MODRINTH_APP_BASE_URL = "https://modrinth.com"
# Optional: Set environment variable for authenticated requests
MODRINTH_TOKEN = os.getenv("MODRINTH_TOKEN", "")


class ModrinthService:
    """Service for interacting with Modrinth API v2"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or MODRINTH_TOKEN
        self.base_url = MODRINTH_API_BASE_URL
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "ModPorter-AI/1.0",
        }
        if self.token:
            self.headers["Authorization"] = self.token
    
    async def search_mods(
        self,
        query: str,
        game_version: Optional[str] = None,
        loader: Optional[str] = None,
        sort_order: str = "relevance",
        page: int = 0,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """
        Search for mods on Modrinth
        
        Args:
            query: Search query string
            game_version: Filter by Minecraft version (e.g., "1.20.1")
            loader: Filter by loader (forge, fabric, quilt)
            sort_order: Sort order - "relevance", "downloads", "follows", "newest", "updated"
            page: Page number for pagination
            limit: Number of results per page
            
        Returns:
            Dictionary with search results and metadata
        """
        endpoint = f"{self.base_url}/search"
        
        params = {
            "query": query,
            "offset": page * limit,
            "limit": limit,
            "sort": sort_order,
        }
        
        # Add filters
        facets = []
        if game_version:
            facets.append(f'["versions:{game_version}"]')
        if loader:
            facets.append(f'["categories:{loader}"]')
        
        if facets:
            params["facets"] = facets
        
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
                logger.error(f"Modrinth API error: {e}")
                raise
    
    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific project
        
        Args:
            project_id: The Modrinth project ID or slug
            
        Returns:
            Dictionary with project details
        """
        endpoint = f"{self.base_url}/project/{project_id}"
        
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
                logger.error(f"Modrinth API error: {e}")
                raise
    
    async def get_project_versions(
        self,
        project_id: str,
        game_version: Optional[str] = None,
        loader: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get versions for a specific project
        
        Args:
            project_id: The Modrinth project ID or slug
            game_version: Filter by game version
            loader: Filter by loader
            
        Returns:
            List of version dictionaries
        """
        endpoint = f"{self.base_url}/project/{project_id}/version"
        
        params = {}
        if game_version:
            params["game_version"] = game_version
        if loader:
            params["loaders"] = f'["{loader}"]'
        
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
                logger.error(f"Modrinth API error: {e}")
                raise
    
    async def get_version(self, version_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific version
        
        Args:
            version_id: The Modrinth version ID
            
        Returns:
            Dictionary with version details
        """
        endpoint = f"{self.base_url}/version/{version_id}"
        
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
                logger.error(f"Modrinth API error: {e}")
                raise
    
    async def get_file_download_url(
        self,
        version_id: str,
        file_hash: Optional[str] = None,
    ) -> str:
        """
        Get download URL for a specific file
        
        Args:
            version_id: The Modrinth version ID
            file_hash: SHA1 hash of the file (optional, for verification)
            
        Returns:
            Download URL string
        """
        version = await self.get_version(version_id)
        
        # Find the file with matching hash or return first file
        for file_info in version.get("files", []):
            if file_hash is None or file_info.get("hashes", {}).get("sha1") == file_hash:
                return file_info.get("url", "")
        
        return ""
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get available categories on Modrinth
        
        Returns:
            List of category dictionaries
        """
        endpoint = f"{self.base_url}/tag/category"
        
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
                logger.error(f"Modrinth API error: {e}")
                raise
    
    async def get_loaders(self) -> List[Dict[str, Any]]:
        """
        Get available loaders on Modrinth
        
        Returns:
            List of loader dictionaries
        """
        endpoint = f"{self.base_url}/tag/loader"
        
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
                logger.error(f"Modrinth API error: {e}")
                raise
    
    def parse_modrinth_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a Modrinth URL to extract project information
        
        Supports URLs like:
        - https://modrinth.com/mod/mod-name
        - https://modrinth.com/resourcepack/resourcepack-name
        - https://modrinth.com/plugin/plugin-name
        
        Args:
            url: The Modrinth URL to parse
            
        Returns:
            Dictionary with parsed information or None if invalid
        """
        import re
        
        # Handle None or empty input
        if not url:
            return None
        
        # Pattern for Modrinth URLs
        patterns = [
            r'(?:https?://)?(?:www\.)?modrinth\.com/(mod|resourcepack|plugin|pack)/([^/?]+)',
            r'(?:https?://)?modrinth\.com/([^/?]+)',  # Simplified pattern
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 2:
                    project_type = match.group(1)
                    slug = match.group(2)
                else:
                    project_type = "mod"
                    slug = match.group(1)
                
                return {
                    "platform": "modrinth",
                    "project_type": project_type,
                    "slug": slug,
                    "url": f"{MODRINTH_APP_BASE_URL}/{project_type}/{slug}",
                }
        
        return None


# Singleton instance
modrinth_service = ModrinthService()
