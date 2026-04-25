"""
JAR/ZIP archive extraction for Java mod analysis
"""

import json
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from utils.logging_config import get_agent_logger

logger = get_agent_logger("java_analyzer.archive_reader")


FEATURE_ANALYSIS_FILE_LIMIT = 10
METADATA_AST_FILE_LIMIT = 5
DEPENDENCY_ANALYSIS_FILE_LIMIT = 10


class ArchiveReader:
    """Handles JAR/ZIP extraction and analysis"""

    def __init__(self, feature_patterns: Dict[str, List[str]]):
        self.feature_patterns = feature_patterns

    def read_java_sources_from_jar(self, jar_path: str) -> List[tuple]:
        """Read all .java source files from a JAR.

        Returns:
            List of (name, code) tuples
        """
        sources = []
        try:
            with zipfile.ZipFile(jar_path, "r") as jar:
                for name in jar.namelist():
                    if name.endswith(".java"):
                        try:
                            code = jar.read(name).decode("utf-8", errors="replace")
                            sources.append((name, code))
                        except Exception as exc:
                            logger.warning(f"Skipping {name}: {exc}")
        except Exception as exc:
            logger.error(f"Cannot open JAR for chunking: {exc}")
        return sources

    def extract_mod_info_from_jar(self, jar: zipfile.ZipFile, file_list: list) -> dict:
        """Extract mod information from metadata files"""
        mod_info = {}

        if "fabric.mod.json" in file_list:
            try:
                content = jar.read("fabric.mod.json").decode("utf-8")
                fabric_data = json.loads(content)
                mod_info["name"] = fabric_data.get("id", fabric_data.get("name", "unknown")).lower()
                mod_info["version"] = fabric_data.get("version", "1.0.0")
                return mod_info
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                logger.debug(f"Could not parse fabric.mod.json: {e}")

        if "quilt.mod.json" in file_list:
            try:
                content = jar.read("quilt.mod.json").decode("utf-8")
                quilt_data = json.loads(content)
                mod_info["name"] = quilt_data.get("quilt_loader", {}).get("id", "unknown").lower()
                mod_info["version"] = quilt_data.get("quilt_loader", {}).get("version", "1.0.0")
                return mod_info
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                logger.debug(f"Could not parse quilt.mod.json: {e}")

        if "mcmod.info" in file_list:
            try:
                content = jar.read("mcmod.info").decode("utf-8")
                mcmod_data = json.loads(content)
                if isinstance(mcmod_data, list) and len(mcmod_data) > 0:
                    mod_data = mcmod_data[0]
                    mod_info["name"] = mod_data.get("modid", "unknown").lower()
                    mod_info["version"] = mod_data.get("version", "1.0.0")
                    return mod_info
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                logger.debug(f"Could not parse mcmod.info: {e}")

        for file_name in file_list:
            if file_name.endswith("mods.toml"):
                try:
                    content = jar.read(file_name).decode("utf-8")
                    for line in content.split("\n"):
                        if "modId" in line and "=" in line:
                            mod_id = line.split("=")[1].strip().strip("\"'")
                            mod_info["name"] = mod_id.lower()
                            break
                    return mod_info
                except Exception as e:
                    logger.debug(f"Could not parse mods.toml: {e}")

        return mod_info

    def analyze_assets_from_jar(self, file_list: list) -> dict:
        """Analyze assets in the JAR file"""
        assets = {
            "textures": [],
            "models": [],
            "sounds": [],
            "lang": [],
            "sounds_json": [],
            "other": [],
        }

        for file_name in file_list:
            if "/textures/" in file_name and file_name.endswith((".png", ".jpg", ".jpeg")):
                assets["textures"].append(file_name)
            elif "/models/" in file_name and file_name.endswith((".json", ".obj")):
                assets["models"].append(file_name)
            elif "/sounds/" in file_name and file_name.endswith((".ogg", ".wav")):
                assets["sounds"].append(file_name)
            elif "/lang/" in file_name and file_name.endswith(".json"):
                assets["lang"].append(file_name)
            elif file_name.endswith("sounds.json") and "/sounds" in file_name:
                assets["sounds_json"].append(file_name)
            elif any(
                file_name.endswith(ext) for ext in [".png", ".jpg", ".ogg", ".wav", ".obj", ".mtl"]
            ):
                assets["other"].append(file_name)

        return assets

    def find_block_texture(self, file_list: list) -> Optional[str]:
        """Find a block texture in the JAR file list."""
        for file_path in file_list:
            if (
                file_path.startswith("assets/")
                and "/textures/block/" in file_path
                and file_path.endswith(".png")
            ):
                return file_path
        return None

    def extract_registry_name_from_jar(self, jar: zipfile.ZipFile, file_list: list) -> str:
        """Extract block registry name from JAR."""
        mod_id = self._extract_mod_id_from_metadata(jar, file_list)
        if mod_id:
            block_class = self._find_block_class_name(file_list)
            if block_class:
                block_name = self._class_name_to_registry_name(block_class)
                return f"{mod_id}:{block_name}"
            return f"{mod_id}:unknown_block"

        block_class = self._find_block_class_name(file_list)
        if block_class:
            block_name = self._class_name_to_registry_name(block_class)
            return f"modporter:{block_name}"

        return "modporter:unknown_block"

    def _extract_mod_id_from_metadata(self, jar: zipfile.ZipFile, file_list: list) -> Optional[str]:
        """Extract mod ID from metadata files."""
        if "fabric.mod.json" in file_list:
            try:
                content = jar.read("fabric.mod.json").decode("utf-8")
                data = json.loads(content)
                return data.get("id", "").lower()
            except Exception as e:
                logger.warning(f"Error reading fabric.mod.json: {e}")

        if "mcmod.info" in file_list:
            try:
                content = jar.read("mcmod.info").decode("utf-8")
                data = json.loads(content)
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("modid", "").lower()
            except Exception as e:
                logger.warning(f"Error reading mcmod.info: {e}")

        for file_name in file_list:
            if file_name.endswith("mods.toml"):
                try:
                    content = jar.read(file_name).decode("utf-8")
                    for line in content.split("\n"):
                        if "modId" in line and "=" in line:
                            mod_id = line.split("=")[1].strip().strip("\"'")
                            return mod_id.lower()
                except Exception as e:
                    logger.warning(f"Error reading {file_name}: {e}")

        return None

    def _find_block_class_name(self, file_list: list) -> Optional[str]:
        """Find the main block class name from file paths."""
        block_candidates = []

        for file_name in file_list:
            if file_name.endswith(".class") or file_name.endswith(".java"):
                class_name = Path(file_name).stem
                if "Block" in class_name and not class_name.startswith("Abstract"):
                    block_candidates.append(class_name)

        if block_candidates:
            block_candidates.sort(key=lambda x: (len(x), x.count("_")))
            return block_candidates[0]

        return None

    def _class_name_to_registry_name(self, class_name: str) -> str:
        """Convert Java class name to registry name format."""
        name = class_name
        if name.endswith("Block") and len(name) > 5:
            name = name[:-5]
        elif name.startswith("Block") and len(name) > 5 and name[5].isupper():
            name = name[5:]

        name = _snake_case(name)

        if not name:
            return "unknown"
        return name

    def extract_registry_name_from_jar_simple(self, jar: zipfile.ZipFile, file_list: list) -> str:
        """Extract block registry name from JAR metadata (simple version)."""
        mod_id = self._extract_mod_id_from_metadata(jar, file_list)
        if mod_id:
            block_class = self._find_block_class_name(file_list)
            if block_class:
                block_name = self._class_name_to_registry_name(block_class)
                return f"{mod_id}:{block_name}"
            return f"{mod_id}:copper_block"

        block_class = self._find_block_class_name(file_list)
        if block_class:
            block_name = self._class_name_to_registry_name(block_class)
            return f"modporter:{block_name}"

        return "modporter:copper_block"


def _snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    import re

    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()
    name = re.sub(r"_+", "_", name).strip("_")
    return name
