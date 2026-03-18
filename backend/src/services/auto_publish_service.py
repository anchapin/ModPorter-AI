"""
Auto-Publish Service

Handles automatic publishing of converted mods to platforms:
- Platform selection
- Auto-generate descriptions
- Version management
- Publishing workflow
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum

from services.modrinth_oauth_service import ModrinthPublisher, ModrinthOAuthService
from services.curseforge_oauth_service import CurseForgePublisher, CurseForgeOAuthService

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    """Supported publishing platforms"""
    MODRINTH = "modrinth"
    CURSEFORGE = "curseforge"


class ReleaseType(str, Enum):
    """Release types for mod publishing"""
    RELEASE = "release"
    BETA = "beta"
    ALPHA = "alpha"


class AutoPublishService:
    """Service for auto-publishing converted mods to platforms"""

    def __init__(
        self,
        modrinth_oauth: Optional[ModrinthOAuthService] = None,
        curseforge_oauth: Optional[CurseForgeOAuthService] = None,
    ):
        self.modrinth_oauth = modrinth_oauth or ModrinthOAuthService()
        self.curseforge_oauth = curseforge_oauth or CurseForgeOAuthService()
        self.modrinth_publisher = ModrinthPublisher()
        self.curseforge_publisher = CurseForgePublisher()

    async def get_user_platforms(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get list of connected platforms for a user.
        
        In production, this would query the platform_connections table.
        """
        # Placeholder - would fetch from database
        return []

    def generate_description(
        self,
        conversion_data: Dict[str, Any],
    ) -> str:
        """
        Auto-generate a description for the published mod based on conversion data.
        
        Args:
            conversion_data: Dictionary containing conversion results and metadata
            
        Returns:
            Generated description string
        """
        parts = []
        
        # Add mod name/title
        if conversion_data.get("mod_name"):
            parts.append(f"## {conversion_data['mod_name']}")
            parts.append("")
        
        # Add conversion info
        parts.append("This mod was automatically converted from Java Edition to Bedrock Edition using ModPorter AI.")
        parts.append("")
        
        # Add original source info
        if conversion_data.get("original_mod"):
            parts.append(f"**Original Mod**: {conversion_data['original_mod']}")
        
        if conversion_data.get("source_version"):
            parts.append(f"**Original Version**: {conversion_data['source_version']}")
        
        if conversion_data.get("target_version"):
            parts.append(f"**Target Version**: {conversion_data['target_version']}")
        
        parts.append("")
        
        # Add conversion stats
        if conversion_data.get("stats"):
            stats = conversion_data["stats"]
            parts.append("### Conversion Summary")
            
            if stats.get("files_converted"):
                parts.append(f"- Files converted: {stats['files_converted']}")
            
            if stats.get("blocks_converted"):
                parts.append(f"- Blocks converted: {stats['blocks_converted']}")
            
            if stats.get("items_converted"):
                parts.append(f"- Items converted: {stats['items_converted']}")
            
            if stats.get("recipes_converted"):
                parts.append(f"- Recipes converted: {stats['recipes_converted']}")
            
            if stats.get("warnings"):
                parts.append(f"- Warnings: {stats['warnings']}")
            
            parts.append("")
        
        # Add features note
        if conversion_data.get("features"):
            parts.append("### Features")
            for feature in conversion_data["features"][:5]:  # Limit to 5 features
                parts.append(f"- {feature}")
            parts.append("")
        
        # Add disclaimer
        parts.append("---")
        parts.append("*Auto-converted by ModPorter AI. Some manual adjustments may be required.*")
        
        return "\n".join(parts)

    def get_game_version_for_platform(
        self,
        game_version: str,
        platform: Platform,
    ) -> str:
        """
        Normalize game version string for the target platform.
        
        Args:
            game_version: Standard version string (e.g., "1.20.1")
            platform: Target platform
            
        Returns:
            Platform-specific version string
        """
        # Modrinth and CurseForge use similar version formats
        # but there might be edge cases
        return game_version

    def get_loader_for_platform(
        self,
        loader: str,
        platform: Platform,
    ) -> str:
        """
        Convert loader name to platform-specific format.
        
        Args:
            loader: Standard loader name ("fabric", "forge", "quilt")
            platform: Target platform
            
        Returns:
            Platform-specific loader string
        """
        if platform == Platform.MODRINTH:
            return loader.lower()
        elif platform == Platform.CURSEFORGE:
            mapping = {
                "forge": "minecraftforge",
                "fabric": "fabric",
                "quilt": "quilt",
            }
            return mapping.get(loader.lower(), loader.lower())
        return loader

    async def publish_to_modrinth(
        self,
        access_token: str,
        project_slug: str,
        version: str,
        game_version: str,
        loader: str,
        release_type: str,
        file_path: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish to Modrinth platform.
        
        Args:
            access_token: OAuth access token
            project_slug: Project slug on Modrinth
            version: Version number
            game_version: Minecraft version
            loader: Mod loader
            release_type: Release type (release/beta/alpha)
            file_path: Path to .mcaddon file
            description: Version description (optional)
            
        Returns:
            Publication result
        """
        version_data = {
            "name": f"Version {version}",
            "version_number": version,
            "game_versions": [game_version],
            "loaders": [self.get_loader_for_platform(loader, Platform.MODRINTH)],
            "release_type": release_type,
            "description": description or "",
        }

        try:
            result = await self.modrinth_publisher.upload_version(
                access_token=access_token,
                project_slug=project_slug,
                version_data=version_data,
                file_path=file_path,
            )
            
            return {
                "success": True,
                "platform": Platform.MODRINTH.value,
                "project_id": result.get("project_id", ""),
                "version_id": result.get("id", ""),
                "version_number": version,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to publish to Modrinth: {e}")
            return {
                "success": False,
                "platform": Platform.MODRINTH.value,
                "error": str(e),
            }

    async def publish_to_curseforge(
        self,
        access_token: str,
        project_id: int,
        version: str,
        game_version: str,
        loader: str,
        release_type: str,
        file_path: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish to CurseForge platform.
        
        Args:
            access_token: OAuth access token
            project_id: Project ID on CurseForge
            version: Version number
            game_version: Minecraft version
            loader: Mod loader
            release_type: Release type (release/beta/alpha)
            file_path: Path to .mcaddon file
            description: File description (optional)
            
        Returns:
            Publication result
        """
        loader_mapped = self.get_loader_for_platform(loader, Platform.CURSEFORGE)
        
        file_data = {
            "displayName": f"Version {version}",
            "gameVersion": game_version,
            "releaseType": release_type,
            "loaders": [loader_mapped],
            "changelog": description or "",
        }

        try:
            result = await self.curseforge_publisher.upload_file(
                access_token=access_token,
                project_id=project_id,
                file_data=file_data,
                file_path=file_path,
            )
            
            return {
                "success": True,
                "platform": Platform.CURSEFORGE.value,
                "project_id": str(project_id),
                "version_id": str(result.get("id", "")),
                "version_number": version,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to publish to CurseForge: {e}")
            return {
                "success": False,
                "platform": Platform.CURSEFORGE.value,
                "error": str(e),
            }

    async def auto_publish(
        self,
        user_id: str,
        platforms: List[Platform],
        conversion_data: Dict[str, Any],
        file_path: str,
    ) -> List[Dict[str, Any]]:
        """
        Auto-publish a conversion to multiple platforms.
        
        Args:
            user_id: User ID
            platforms: List of platforms to publish to
            conversion_data: Conversion metadata and results
            file_path: Path to the .mcaddon file
            
        Returns:
            List of publication results
        """
        results = []
        
        # Generate description
        description = self.generate_description(conversion_data)
        
        # Extract version info
        version = conversion_data.get("version", "1.0.0")
        game_version = conversion_data.get("game_version", "1.20.1")
        loader = conversion_data.get("loader", "fabric")
        
        # Get access tokens (would come from database in production)
        modrinth_token = os.getenv("MODRINTH_TOKEN", "")
        curseforge_token = os.getenv("CURSEFORGE_TOKEN", "")
        
        for platform in platforms:
            if platform == Platform.MODRINTH:
                project_slug = conversion_data.get("modrinth_slug", "")
                if project_slug and modrinth_token:
                    result = await self.publish_to_modrinth(
                        access_token=modrinth_token,
                        project_slug=project_slug,
                        version=version,
                        game_version=game_version,
                        loader=loader,
                        release_type=conversion_data.get("release_type", "release"),
                        file_path=file_path,
                        description=description,
                    )
                    results.append(result)
                    
            elif platform == Platform.CURSEFORGE:
                project_id = conversion_data.get("curseforge_project_id")
                if project_id and curseforge_token:
                    result = await self.publish_to_curseforge(
                        access_token=curseforge_token,
                        project_id=int(project_id),
                        version=version,
                        game_version=game_version,
                        loader=loader,
                        release_type=conversion_data.get("release_type", "release"),
                        file_path=file_path,
                        description=description,
                    )
                    results.append(result)
        
        return results


# Singleton instance
auto_publish_service = AutoPublishService()
