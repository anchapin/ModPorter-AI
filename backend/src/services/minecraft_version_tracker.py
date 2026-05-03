"""
Minecraft Version Tracking Service

Tracks supported Java and Bedrock Edition versions for PortKit converter.
Implements version compatibility tracking per issue #1210.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MinecraftVersions:
    java_min_version: str
    java_max_version: str
    bedrock_target_version: str
    last_updated: datetime
    update_source: str
    notes: Optional[str] = None


class MinecraftVersionTracker:
    _instance: Optional['MinecraftVersionTracker'] = None

    def __init__(self):
        self._versions = MinecraftVersions(
            java_min_version="1.18",
            java_max_version="1.21",
            bedrock_target_version="1.21.0",
            last_updated=datetime.now(),
            update_source="manual",
            notes="Initial version tracking setup"
        )

    @classmethod
    def get_instance(cls) -> 'MinecraftVersionTracker':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def supported_java_range(self) -> str:
        return f"{self._versions.java_min_version}-{self._versions.java_max_version}"

    @property
    def java_versions(self) -> tuple[str, str]:
        return (self._versions.java_min_version, self._versions.java_max_version)

    @property
    def bedrock_version(self) -> str:
        return self._versions.bedrock_target_version

    def get_version_display(self) -> str:
        return f"Java {self.supported_java_range} → Bedrock {self._versions.bedrock_target_version}"

    def update_versions(
        self,
        java_min: Optional[str] = None,
        java_max: Optional[str] = None,
        bedrock: Optional[str] = None,
        source: str = "manual",
        notes: Optional[str] = None
    ) -> None:
        if java_min:
            self._versions.java_min_version = java_min
        if java_max:
            self._versions.java_max_version = java_max
        if bedrock:
            self._versions.bedrock_target_version = bedrock

        self._versions.last_updated = datetime.now()
        self._versions.update_source = source
        if notes:
            self._versions.notes = notes

        logger.info(f"Version tracker updated: {self.get_version_display()}")

    def get_version_info(self) -> dict:
        return {
            "java_range": self.supported_java_range,
            "java_min": self._versions.java_min_version,
            "java_max": self._versions.java_max_version,
            "bedrock_target": self._versions.bedrock_target_version,
            "display_string": self.get_version_display(),
            "last_updated": self._versions.last_updated.isoformat(),
            "update_source": self._versions.update_source,
            "notes": self._versions.notes
        }


version_tracker = MinecraftVersionTracker.get_instance()