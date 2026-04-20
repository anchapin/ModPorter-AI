"""
Atlas detection and extraction module.
"""

import json
import logging
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

logger = logging.getLogger(__name__)


def detect_texture_atlas(agent, texture_path: str) -> Dict:
    """
    Detect if a texture is a texture atlas (combined multiple textures).

    Args:
        texture_path: Path to the texture file

    Returns:
        Dict with atlas detection results
    """
    try:
        path = Path(texture_path)
        if not path.exists():
            return {"is_atlas": False, "error": "File not found"}

        img = Image.open(texture_path)
        width, height = img.size

        is_atlas = False
        atlas_type = None
        tile_size = 16

        if width == height and width > 16:
            if width >= 64:
                is_atlas = True
                atlas_type = "grid"
                tile_size = 16

        common_atlas_sizes = [256, 512, 1024]
        if width in common_atlas_sizes or height in common_atlas_sizes:
            is_atlas = True
            atlas_type = "grid"

        if width != height and (width % 16 == 0 or height % 16 == 0):
            if width >= 64 or height >= 64:
                is_atlas = True
                atlas_type = "strip"

        tiles_x = width // tile_size if tile_size > 0 else 1
        tiles_y = height // tile_size if tile_size > 0 else 1

        return {
            "is_atlas": is_atlas,
            "atlas_type": atlas_type,
            "width": width,
            "height": height,
            "tile_size": tile_size,
            "tiles_x": tiles_x,
            "tiles_y": tiles_y,
            "total_tiles": tiles_x * tiles_y if is_atlas else 1,
        }

    except Exception as e:
        logger.error(f"Error detecting texture atlas: {e}")
        return {"is_atlas": False, "error": str(e)}


def extract_texture_atlas(
    self,
    atlas_path: str,
    output_dir: str,
    tile_size: int = 16,
    naming_pattern: str = "tile_{x}_{y}",
) -> Dict:
    """
    Extract individual textures from a texture atlas.

    Args:
        atlas_path: Path to the atlas texture file
        output_dir: Directory to save extracted textures
        tile_size: Size of each tile (default 16x16)
        naming_pattern: Pattern for naming extracted files

    Returns:
        Dict with extraction results
    """
    try:
        path = Path(atlas_path)
        if not path.exists():
            return {"success": False, "error": "Atlas file not found"}

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        img = Image.open(atlas_path)
        width, height = img.size

        img = img.convert("RGBA")

        tiles_x = width // tile_size
        tiles_y = height // tile_size

        extracted_tiles = []

        for y in range(tiles_y):
            for x in range(tiles_x):
                left = x * tile_size
                upper = y * tile_size
                right = left + tile_size
                lower = upper + tile_size

                tile = img.crop((left, upper, right, lower))

                tile_data = list(tile.getdata())
                has_content = any(pixel[3] > 0 for pixel in tile_data)

                if has_content:
                    tile_name = naming_pattern.format(x=x, y=y, index=y * tiles_x + x)
                    tile_filename = f"{tile_name}.png"
                    tile_path = output_path / tile_filename

                    tile.save(tile_path, "PNG", optimize=True)

                    extracted_tiles.append(
                        {
                            "path": str(tile_path),
                            "name": tile_name,
                            "grid_x": x,
                            "grid_y": y,
                            "index": y * tiles_x + x,
                            "size": tile_size,
                        }
                    )

        return {
            "success": True,
            "atlas_path": atlas_path,
            "output_dir": str(output_path),
            "total_tiles": tiles_x * tiles_y,
            "extracted_count": len(extracted_tiles),
            "extracted_tiles": extracted_tiles,
            "tile_size": tile_size,
        }

    except Exception as e:
        logger.error(f"Error extracting texture atlas: {e}")
        return {"success": False, "error": str(e)}


def parse_atlas_metadata(agent, mcmeta_path: str) -> Dict:
    """
    Parse .mcmeta file for texture atlas animation or configuration data.

    Args:
        mcmeta_path: Path to the .mcmeta file

    Returns:
        Dict with parsed metadata
    """
    try:
        path = Path(mcmeta_path)
        if not path.exists():
            return {"success": False, "error": "Mcmeta file not found"}

        with open(path, "r") as f:
            metadata = json.load(f)

        result = {
            "success": True,
            "path": mcmeta_path,
            "animation": None,
            "villager": None,
            "custom": {},
        }

        if "animation" in metadata:
            anim = metadata["animation"]
            result["animation"] = {
                "interpolate": anim.get("interpolate", False),
                "width": anim.get("width"),
                "height": anim.get("height"),
                "frametime": anim.get("frametime", 1),
                "frames": anim.get("frames", []),
            }

        if "villager" in metadata:
            result["villager"] = metadata["villager"]

        for key, value in metadata.items():
            if key not in ["animation", "villager"]:
                result["custom"][key] = value

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in mcmeta file: {e}")
        return {"success": False, "error": f"Invalid JSON: {e}"}
    except Exception as e:
        logger.error(f"Error parsing mcmeta file: {e}")
        return {"success": False, "error": str(e)}


def convert_atlas_to_bedrock(
    self, atlas_path: str, output_dir: str, texture_names: List[str] = None
) -> Dict:
    """
    Convert a texture atlas to individual Bedrock-compatible textures.

    Args:
        atlas_path: Path to the atlas texture
        output_dir: Output directory for extracted textures
        texture_names: Optional list of names for each tile

    Returns:
        Dict with conversion results
    """
    try:
        detection = agent.detect_texture_atlas(atlas_path)

        if not detection["is_atlas"]:
            return agent._convert_single_texture(atlas_path, {}, "block", Path(output_dir))

        extraction = agent.extract_texture_atlas(
            atlas_path, output_dir, tile_size=detection["tile_size"]
        )

        if not extraction["success"]:
            return extraction

        converted_textures = []
        for tile in extraction["extracted_tiles"]:
            if texture_names and tile["index"] < len(texture_names):
                name = texture_names[tile["index"]]
            else:
                name = tile["name"]

            result = agent._convert_single_texture(tile["path"], {}, "block", Path(output_dir))

            if result["success"]:
                result["texture_name"] = name
                converted_textures.append(result)

        return {
            "success": True,
            "atlas_path": atlas_path,
            "output_dir": output_dir,
            "total_extracted": extraction["extracted_count"],
            "total_converted": len(converted_textures),
            "converted_textures": converted_textures,
            "atlas_info": detection,
        }

    except Exception as e:
        logger.error(f"Error converting texture atlas: {e}")
        return {"success": False, "error": str(e)}


def extract_texture_atlas_from_jar(self, jar_path: str, atlas_type: str, output_dir: str) -> Dict:
    """
    Extract and convert a texture atlas from a mod JAR.

    Args:
        jar_path: Path to the JAR file
        atlas_type: Type of atlas ('terrain', 'items', 'entity', etc.)
        output_dir: Directory to save extracted textures

    Returns:
        Dict with extraction results
    """
    try:
        jar = zipfile.ZipFile(jar_path, "r")
        file_list = jar.namelist()

        atlas_patterns = {
            "terrain": "assets/minecraft/textures/terrain.png",
            "items": "assets/minecraft/textures/items.png",
            "entity": "assets/minecraft/textures/entity.png",
        }

        atlas_path = atlas_patterns.get(atlas_type.lower())
        if not atlas_path:
            return {
                "success": False,
                "error": f"Unknown atlas type: {atlas_type}",
                "extracted_tiles": [],
            }

        if atlas_path not in file_list:
            alt_patterns = [
                f"assets/minecraft/textures/{atlas_type}.png",
                f"assets/vanilla/textures/{atlas_type}.png",
            ]
            for pattern in alt_patterns:
                if pattern in file_list:
                    atlas_path = pattern
                    break
            else:
                return {
                    "success": False,
                    "error": f"Atlas not found in JAR: {atlas_type}",
                    "extracted_tiles": [],
                }

        atlas_data = jar.read(atlas_path)

        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_atlas:
            temp_atlas.write(atlas_data)
            temp_atlas_path = temp_atlas.name

        jar.close()

        result = agent.extract_texture_atlas(temp_atlas_path, output_dir)

        Path(temp_atlas_path).unlink(missing_ok=True)

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to extract atlas: {str(e)}",
            "extracted_tiles": [],
        }
