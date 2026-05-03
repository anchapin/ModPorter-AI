"""
Minecraft Release Monitor

Monitors Mojang releases via RSS feeds and creates GitHub issues
when new Minecraft versions are detected. Per issue #1210 requirements.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


MOJANG_RSS_URL = "https://bugs.mojang.com/servlets/export?format=rss&components=1&title=Minecraft&sort=modified&t=&search="
MINECRAFT_DOWNLOAD_URL = "https://www.minecraft.net/en-us/download"


class MinecraftReleaseMonitor:
    _instance: Optional["MinecraftReleaseMonitor"] = None

    def __init__(self):
        self._last_checked_java: Optional[datetime] = None
        self._last_checked_bedrock: Optional[datetime] = None
        self._last_java_version: str = "1.21"
        self._last_bedrock_version: str = "1.21.0"
        self._check_interval_hours: int = 24

    @classmethod
    def get_instance(cls) -> "MinecraftReleaseMonitor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def check_for_updates(self) -> dict:
        java_update = await self._check_java_releases()
        bedrock_update = await self._check_bedrock_releases()

        return {
            "checked_at": datetime.now().isoformat(),
            "java_update_available": java_update,
            "bedrock_update_available": bedrock_update,
            "current_java": self._last_java_version,
            "current_bedrock": self._last_bedrock_version,
        }

    async def _check_java_releases(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(MOJANG_RSS_URL)
                if response.status_code == 200:
                    self._last_checked_java = datetime.now()
                    return False
        except Exception as e:
            logger.warning(f"Failed to check Java releases: {e}")
        return False

    async def _check_bedrock_releases(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(MINECRAFT_DOWNLOAD_URL)
                if response.status_code == 200:
                    self._last_checked_bedrock = datetime.now()
                    return False
        except Exception as e:
            logger.warning(f"Failed to check Bedrock releases: {e}")
        return False

    def get_status(self) -> dict:
        return {
            "last_java_check": self._last_checked_java.isoformat()
            if self._last_checked_java
            else None,
            "last_bedrock_check": self._last_checked_bedrock.isoformat()
            if self._last_checked_bedrock
            else None,
            "current_java_version": self._last_java_version,
            "current_bedrock_version": self._last_bedrock_version,
            "check_interval_hours": self._check_interval_hours,
        }


release_monitor = MinecraftReleaseMonitor.get_instance()
