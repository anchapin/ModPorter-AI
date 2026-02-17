"""
Mod Import Service - Unified API for CurseForge and Modrinth

Provides a unified interface for importing mods from both platforms.
"""

import re
from typing import Optional, Dict, Any, List
from enum import Enum

from .curseforge_service import curseforge_service, CurseForgeService
from .modrinth_service import modrinth_service, ModrinthService


class ModPlatform(Enum):
    """Supported mod platforms"""
    CURSEFORGE = "curseforge"
    MODRINTH = "modrinth"
    UNKNOWN = "unknown"


class ModImportService:
    """Unified service for importing mods from various platforms"""
    
    def __init__(self):
        self.curseforge = curseforge_service
        self.modrinth = modrinth_service
    
    def detect_platform(self, url: str) -> ModPlatform:
        """
        Detect which platform a URL belongs to
        
        Args:
            url: The URL to check
            
        Returns:
            ModPlatform enum value
        """
        url_lower = url.lower()
        
        if "curseforge.com" in url_lower:
            return ModPlatform.CURSEFORGE
        elif "modrinth.com" in url_lower:
            return ModPlatform.MODRINTH
        else:
            return ModPlatform.UNKNOWN
    
    def parse_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a mod URL to extract platform and mod information
        
        Args:
            url: The mod URL to parse
            
        Returns:
            Dictionary with parsed information or None if invalid
        """
        platform = self.detect_platform(url)
        
        if platform == ModPlatform.CURSEFORGE:
            return self.curseforge.parse_curseforge_url(url)
        elif platform == ModPlatform.MODRINTH:
            return self.modrinth.parse_modrinth_url(url)
        
        return None
    
    async def search_mods(
        self,
        query: str,
        platform: Optional[ModPlatform] = None,
        game_version: Optional[str] = None,
        loader: Optional[str] = None,
        sort_order: str = "popularity",
        page: int = 0,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """
        Search for mods across platforms
        
        Args:
            query: Search query string
            platform: Specific platform to search (None for all)
            game_version: Filter by game version
            loader: Filter by loader (forge, fabric)
            sort_order: Sort order
            page: Page number
            limit: Results per page
            
        Returns:
            Dictionary with search results from specified platform(s)
        """
        results = {
            "query": query,
            "platform": platform.value if platform else "all",
            "game_version": game_version,
            "results": [],
        }
        
        # Search CurseForge
        if platform is None or platform == ModPlatform.CURSEFORGE:
            try:
                cf_results = await self.curseforge.search_mods(
                    query=query,
                    game_version=game_version,
                    sort_order=sort_order,
                    page_index=page,
                    page_size=limit,
                )
                results["curseforge"] = cf_results.get("data", {}).get("mods", [])
            except Exception as e:
                results["curseforge_error"] = str(e)
                results["curseforge"] = []
        
        # Search Modrinth
        if platform is None or platform == ModPlatform.MODRINTH:
            try:
                mr_results = await self.modrinth.search_mods(
                    query=query,
                    game_version=game_version,
                    loader=loader,
                    sort_order=sort_order,
                    page=page,
                    limit=limit,
                )
                results["modrinth"] = mr_results.get("hits", [])
            except Exception as e:
                results["modrinth_error"] = str(e)
                results["modrinth"] = []
        
        # Combine results if searching all platforms
        if platform is None:
            combined = []
            if "curseforge" in results:
                for mod in results["curseforge"]:
                    combined.append({
                        **mod,
                        "source": "curseforge",
                    })
            if "modrinth" in results:
                for mod in results["modrinth"]:
                    combined.append({
                        **mod,
                        "source": "modrinth",
                    })
            results["results"] = combined
            results["total"] = len(combined)
        else:
            results["results"] = results.get(platform.value, [])
            results["total"] = len(results["results"])
        
        return results
    
    async def get_mod_info(
        self,
        platform: ModPlatform,
        mod_id: str,
    ) -> Dict[str, Any]:
        """
        Get detailed information about a mod
        
        Args:
            platform: The platform (curseforge or modrinth)
            mod_id: The mod ID or slug
            
        Returns:
            Dictionary with mod details
        """
        if platform == ModPlatform.CURSEFORGE:
            # For CurseForge, mod_id is numeric
            try:
                cf_id = int(mod_id)
                return await self.curseforge.get_mod_info(cf_id)
            except ValueError:
                # Try to search for the mod first
                search_results = await self.curseforge.search_mods(query=mod_id)
                mods = search_results.get("data", {}).get("mods", [])
                if mods:
                    return await self.curseforge.get_mod_info(mods[0]["id"])
                raise ValueError(f"Mod not found: {mod_id}")
        
        elif platform == ModPlatform.MODRINTH:
            return await self.modrinth.get_project(mod_id)
        
        raise ValueError(f"Unsupported platform: {platform}")
    
    async def get_mod_versions(
        self,
        platform: ModPlatform,
        mod_id: str,
        game_version: Optional[str] = None,
        loader: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get available versions for a mod
        
        Args:
            platform: The platform (curseforge or modrinth)
            mod_id: The mod ID or slug
            game_version: Filter by game version
            loader: Filter by loader
            
        Returns:
            List of version dictionaries
        """
        if platform == ModPlatform.CURSEFORGE:
            try:
                cf_id = int(mod_id)
                result = await self.curseforge.get_mod_files(cf_id, game_version)
                return result.get("data", {}).get("files", [])
            except ValueError:
                return []
        
        elif platform == ModPlatform.MODRINTH:
            return await self.modrinth.get_project_versions(mod_id, game_version, loader)
        
        return []
    
    async def get_download_url(
        self,
        platform: ModPlatform,
        mod_id: str,
        file_id: str,
    ) -> str:
        """
        Get download URL for a mod file
        
        Args:
            platform: The platform (curseforge or modrinth)
            mod_id: The mod ID
            file_id: The file/version ID
            
        Returns:
            Download URL string
        """
        if platform == ModPlatform.CURSEFORGE:
            cf_id = int(mod_id)
            file_id_int = int(file_id)
            return await self.curseforge.get_file_download_url(cf_id, file_id_int)
        
        elif platform == ModPlatform.MODRINTH:
            return await self.modrinth.get_file_download_url(file_id)
        
        return ""
    
    async def get_categories(
        self,
        platform: Optional[ModPlatform] = None,
    ) -> Dict[str, Any]:
        """
        Get available categories from platforms
        
        Args:
            platform: Specific platform or None for all
            
        Returns:
            Dictionary with categories from each platform
        """
        results = {}
        
        if platform is None or platform == ModPlatform.CURSEFORGE:
            try:
                results["curseforge"] = await self.curseforge.get_categories()
            except Exception as e:
                results["curseforge_error"] = str(e)
        
        if platform is None or platform == ModPlatform.MODRINTH:
            try:
                results["modrinth"] = await self.modrinth.get_categories()
            except Exception as e:
                results["modrinth_error"] = str(e)
        
        return results


# Singleton instance
mod_import_service = ModImportService()
