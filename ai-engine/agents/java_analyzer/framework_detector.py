"""
Framework detection for Forge/Fabric/Quilt mods
"""

import zipfile

from utils.logging_config import get_agent_logger

logger = get_agent_logger("java_analyzer.framework_detector")


class FrameworkDetector:
    """Detects modding framework (Forge/Fabric/Quilt/etc) from JAR contents"""

    FRAMEWORK_INDICATORS = {
        "forge": ["net.minecraftforge", "cpw.mods", "@Mod", "ForgeModContainer"],
        "fabric": ["net.fabricmc", "FabricLoader", "fabric.mod.json"],
        "quilt": ["org.quiltmc", "QuiltLoader", "quilt.mod.json"],
        "bukkit": ["org.bukkit", "plugin.yml", "JavaPlugin"],
        "spigot": ["org.spigotmc", "SpigotAPI"],
        "paper": ["io.papermc", "PaperAPI"],
    }

    def detect_framework_from_jar(self, jar_path: str) -> str:
        """Detect modding framework from JAR file contents"""
        try:
            with zipfile.ZipFile(jar_path, "r") as jar:
                file_list = jar.namelist()
                return self._detect_framework_from_files(file_list, jar)
        except Exception as e:
            logger.warning(f"Error detecting framework: {e}")
            return "unknown"

    def _detect_framework_from_files(self, file_list: list, jar: zipfile.ZipFile) -> str:
        """Detect framework from file list and optionally file contents"""
        for framework, indicators in self.FRAMEWORK_INDICATORS.items():
            for indicator in indicators:
                if any(indicator in file_name for file_name in file_list):
                    return framework

        for file_name in file_list:
            if file_name.endswith(".json") and "mod" in file_name.lower():
                try:
                    content = jar.read(file_name).decode("utf-8")
                    for framework, indicators in self.FRAMEWORK_INDICATORS.items():
                        for indicator in indicators:
                            if indicator in content:
                                return framework
                except (UnicodeDecodeError, KeyError) as e:
                    logger.debug(f"Could not read {file_name}: {e}")
                    continue

        return "unknown"

    def detect_framework_from_source(self, source_path: str) -> str:
        """Detect modding framework from source directory"""
        import os

        try:
            for root, dirs, files in os.walk(source_path):
                for file_name in files:
                    for framework, indicators in self.FRAMEWORK_INDICATORS.items():
                        if file_name in indicators:
                            return framework

                for file_name in files:
                    if file_name.endswith(".java"):
                        try:
                            file_path = os.path.join(root, file_name)
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                                for framework, indicators in self.FRAMEWORK_INDICATORS.items():
                                    for indicator in indicators:
                                        if indicator in content:
                                            return framework
                        except (UnicodeDecodeError, FileNotFoundError, PermissionError) as e:
                            logger.debug(f"Could not read {file_path}: {e}")
                            continue

            return "unknown"
        except Exception as e:
            logger.warning(f"Error in source framework detection: {e}")
            return "unknown"
