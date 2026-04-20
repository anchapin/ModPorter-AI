"""
JAR texture extraction module.
"""

import logging
import zipfile
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def extract_textures_from_jar(self, jar_path: str, output_dir: str, namespace: str = None) -> Dict:
    """
    Extract all textures from a Java mod JAR file.

    Args:
        jar_path: Path to the JAR file
        output_dir: Directory to extract textures to
        namespace: Optional namespace to filter textures (e.g., 'simple_copper')

    Returns:
        Dict with extraction results including list of extracted textures
    """
    extracted_textures = []
    errors = []
    warnings = []

    try:
        jar_path_obj = Path(jar_path)
        if not jar_path_obj.exists():
            return {
                "success": False,
                "error": f"JAR file not found: {jar_path}",
                "extracted_textures": [],
            }

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(jar_path, "r") as jar:
            file_list = jar.namelist()

            texture_files = [
                f
                for f in file_list
                if f.startswith("assets/") and "/textures/" in f and f.endswith(".png")
            ]

            if namespace:
                texture_files = [f for f in texture_files if f.startswith(f"assets/{namespace}/")]

            mcmeta_files = [
                f
                for f in file_list
                if f.startswith("assets/") and "/textures/" in f and f.endswith(".png.mcmeta")
            ]

            for texture_file in texture_files:
                try:
                    texture_data = jar.read(texture_file)

                    bedrock_path = agent._map_java_texture_to_bedrock(texture_file)

                    full_output_dir = output_path / Path(bedrock_path).parent
                    full_output_dir.mkdir(parents=True, exist_ok=True)

                    output_file = output_path / bedrock_path
                    with open(output_file, "wb") as f:
                        f.write(texture_data)

                    extracted_textures.append(
                        {
                            "original_path": texture_file,
                            "bedrock_path": bedrock_path,
                            "output_path": str(output_file),
                            "success": True,
                        }
                    )

                    mcmeta_path = texture_file + ".mcmeta"
                    if mcmeta_path in mcmeta_files:
                        mcmeta_data = jar.read(mcmeta_path)
                        mcmeta_output = output_file.with_suffix(".png.mcmeta")
                        with open(mcmeta_output, "wb") as f:
                            f.write(mcmeta_data)

                except Exception as e:
                    errors.append(f"Failed to extract {texture_file}: {str(e)}")

        return {
            "success": len(extracted_textures) > 0,
            "extracted_textures": extracted_textures,
            "errors": errors,
            "warnings": warnings,
            "count": len(extracted_textures),
        }

    except zipfile.BadZipFile:
        return {
            "success": False,
            "error": f"Invalid JAR file: {jar_path}",
            "extracted_textures": [],
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to extract textures: {str(e)}",
            "extracted_textures": [],
        }


def _get_mod_ids_from_jar(agent, jar: zipfile.ZipFile) -> List[str]:
    """Extract mod IDs/namespaces from JAR assets directory."""
    mod_ids = set()
    try:
        for file_path in jar.namelist():
            parts = file_path.split("/")
            if len(parts) >= 2 and parts[0] == "assets":
                mod_ids.add(parts[1])
    except Exception as e:
        logger.warning(f"Error reading mod IDs from JAR: {e}")

    return list(mod_ids) if mod_ids else ["minecraft"]


def _extract_textures_from_alt_locations(
    self, jar: zipfile.ZipFile, output_path: Path
) -> List[Dict]:
    """Extract textures from alternative locations in JAR."""
    extracted = []
    alt_patterns = ["textures/", "assets/textures/", "/textures/"]

    try:
        for file_info in jar.filelist:
            file_path = file_info.filename

            if not file_path.endswith(".png"):
                continue

            is_alt_texture = any(file_path.startswith(pattern) for pattern in alt_patterns)

            if is_alt_texture:
                try:
                    texture_data = jar.read(file_path)

                    if "assets/" in file_path:
                        namespace = file_path.split("assets/")[-1].split("/")[0]
                    else:
                        namespace = "minecraft"

                    if "textures/" in file_path:
                        relative_path = file_path.split("textures/")[-1]
                    else:
                        relative_path = file_path.lstrip("/")

                    output_subdir = (
                        output_path / namespace / "textures" / relative_path.rsplit("/", 1)[0]
                    )
                    output_subdir.mkdir(parents=True, exist_ok=True)
                    output_file = output_path / namespace / "textures" / relative_path

                    output_file.write_bytes(texture_data)

                    extracted.append(
                        {
                            "original_path": file_path,
                            "saved_path": str(output_file),
                            "namespace": namespace,
                            "relative_path": relative_path,
                            "type": relative_path.rsplit("/", 1)[0]
                            if "/" in relative_path
                            else "root",
                            "filename": file_path.rsplit("/", 1)[-1],
                        }
                    )

                except Exception as e:
                    logger.warning(f"Failed to extract alternative texture {file_path}: {e}")

    except Exception as e:
        logger.warning(f"Error scanning alternative texture locations: {e}")

    return extracted
