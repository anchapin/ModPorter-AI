"""
Texture converter module - handles all texture-related conversion logic.
This module is extracted from asset_converter.py for better organization.
"""

import logging
import json
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

# Import utilities
try:
    from . import converter_utils
    from .converter_utils import is_power_of_2, next_power_of_2, previous_power_of_2
except ImportError:
    import converter_utils
    from converter_utils import is_power_of_2, next_power_of_2, previous_power_of_2

logger = logging.getLogger(__name__)

__all__ = [
    'convert_single_texture', 'detect_texture_atlas', 'extract_texture_atlas',
    'parse_atlas_metadata', 'convert_atlas_to_bedrock', 'convert_java_texture_path',
    'validate_texture', 'validate_textures_batch', 'generate_fallback_texture',
    'generate_fallback_for_jar', 'extract_textures_from_jar',
    'extract_texture_atlas_from_jar', 'convert_jar_textures_to_bedrock',
]



# ============================================================================
# _convert_single_texture
# ============================================================================

def _convert_single_texture(
    self, texture_path: str, metadata: Dict, usage: str, output_dir: Path = None
) -> Dict:
    """
    Convert a single texture file to Bedrock format with enhanced validation and optimization.
    If output_dir is provided, saves the converted texture to disk.
    """
    # Create a cache key
    cache_key = f"{texture_path}_{usage}_{hash(str(metadata))}"

    # Check if we have a cached result
    if cache_key in agent._conversion_cache:
        logger.debug(f"Using cached result for texture conversion: {texture_path}")
        return agent._conversion_cache[cache_key]

    try:
        # Handle missing or corrupted files with fallback generation
        if not Path(texture_path).exists():
            logger.warning(
                f"Texture file not found: {texture_path}. Generating fallback texture."
            )
            img = agent._generate_fallback_texture(usage)
            original_dimensions = img.size
            is_valid_png = False
            optimizations_applied = ["Generated fallback texture"]
        else:
            try:
                # Open and validate the image
                img = Image.open(texture_path)
                original_dimensions = img.size

                # Enhanced PNG validation - check if it's already a valid PNG
                is_valid_png = img.format == "PNG"

                # Convert to RGBA for consistency
                img = img.convert("RGBA")
                optimizations_applied = ["Converted to RGBA"] if not is_valid_png else []
            except Exception as open_error:
                logger.warning(
                    f"Failed to open texture {texture_path}: {open_error}. Generating fallback texture."
                )
                img = agent._generate_fallback_texture(usage)
                original_dimensions = img.size
                is_valid_png = False
                optimizations_applied = ["Generated fallback texture due to open error"]

        width, height = img.size
        resized = False

        max_res = agent.texture_constraints.get("max_resolution", 1024)
        must_be_power_of_2 = agent.texture_constraints.get("must_be_power_of_2", True)

        new_width, new_height = width, height

        needs_pot_resize = must_be_power_of_2 and (
            not agent._is_power_of_2(width) or not agent._is_power_of_2(height)
        )

        if needs_pot_resize:
            new_width = agent._next_power_of_2(width)
            new_height = agent._next_power_of_2(height)
            resized = True

        if new_width > max_res or new_height > max_res:
            new_width = min(new_width, max_res)
            new_height = min(new_height, max_res)
            resized = True

        if resized and must_be_power_of_2:
            if not agent._is_power_of_2(new_width):
                new_width = agent._previous_power_of_2(new_width)
            if not agent._is_power_of_2(new_height):
                new_height = agent._previous_power_of_2(new_height)

        if resized and (new_width != width or new_height != height):
            # Use different resampling filters based on upscaling/downscaling
            if new_width > width or new_height > height:
                # Upscaling - use LANCZOS for better quality
                img = img.resize((new_width, new_height), Image.LANCZOS)
            else:
                # Downscaling - use LANCZOS for better quality
                img = img.resize((new_width, new_height), Image.LANCZOS)
            optimizations_applied.append(
                f"Resized from {original_dimensions} to {(new_width, new_height)}"
            )
        else:
            new_width, new_height = img.size
            resized = False

        # Apply PNG optimization if needed
        if not is_valid_png or resized:
            optimizations_applied.append("Optimized PNG format")

        # MCMETA parsing
        animation_data = None
        mcmeta_path = Path(str(texture_path) + ".mcmeta")
        if mcmeta_path.exists():
            try:
                with open(mcmeta_path, "r") as f:
                    mcmeta_content = json.load(f)
                if "animation" in mcmeta_content:
                    animation_data = mcmeta_content["animation"]
                    optimizations_applied.append("Parsed .mcmeta animation data")
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(
                    "Could not parse .mcmeta file for {}: {}".format(texture_path, e)
                )

        base_name = (
            Path(texture_path).stem if Path(texture_path).exists() else "fallback_texture"
        )
        # Enhanced asset path mapping from Java mod structure to Bedrock structure
        # Handle common Java mod asset paths and map them to Bedrock equivalents
        texture_path_obj = (
            Path(texture_path) if Path(texture_path).exists() else Path(f"fallback_{usage}.png")
        )

        # Try to infer usage from the original path if not explicitly provided
        if usage == "block" and "block" not in str(texture_path_obj).lower():
            # Check if the path contains common block texture indicators
            if any(
                block_indicator in str(texture_path_obj).lower()
                for block_indicator in [
                    "block/",
                    "blocks/",
                    "/block/",
                    "/blocks/",
                    "_block",
                    "-block",
                ]
            ):
                usage = "block"
            # Check for item indicators
            elif any(
                item_indicator in str(texture_path_obj).lower()
                for item_indicator in ["item/", "items/", "/item/", "/items/", "_item", "-item"]
            ):
                usage = "item"
            # Check for entity indicators
            elif any(
                entity_indicator in str(texture_path_obj).lower()
                for entity_indicator in [
                    "entity/",
                    "entities/",
                    "/entity/",
                    "/entities/",
                    "_entity",
                    "-entity",
                ]
            ):
                usage = "entity"
            # Check for particle indicators
            elif "particle" in str(texture_path_obj).lower():
                usage = "particle"
            # Check for GUI indicators
            elif any(
                gui_indicator in str(texture_path_obj).lower()
                for gui_indicator in ["gui/", "ui/", "interface/", "menu/"]
            ):
                usage = "ui"

        # Map to Bedrock structure
        if usage == "block":
            converted_path = f"textures/blocks/{base_name}.png"
        elif usage == "item":
            converted_path = f"textures/items/{base_name}.png"
        elif usage == "entity":
            converted_path = f"textures/entity/{base_name}.png"
        elif usage == "particle":
            converted_path = f"textures/particle/{base_name}.png"
        elif usage == "ui":
            converted_path = f"textures/ui/{base_name}.png"
        else:
            # For other types, try to preserve some structure from the original path
            # Remove common prefixes and map to textures/other/
            try:
                relative_path = texture_path_obj.relative_to(texture_path_obj.anchor).as_posix()
                # Remove common prefixes that indicate source structure
                for prefix in ["assets/minecraft/textures/", "textures/", "images/", "img/"]:
                    if relative_path.startswith(prefix):
                        relative_path = relative_path[len(prefix) :]
                        break
                # Remove file extension
                if "." in relative_path:
                    relative_path = relative_path[: relative_path.rindex(".")]
                converted_path = f"textures/other/{relative_path}.png"
            except Exception:
                # Fallback to a simple path if relative path calculation fails
                converted_path = f"textures/other/{base_name}.png"

        # Save the converted texture if output_dir is provided
        actual_output_path = None
        if output_dir is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            actual_output_path = output_dir / converted_path
            actual_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save with optimization
            img.save(actual_output_path, "PNG", optimize=True)
            logger.info(f"Saved converted texture to {actual_output_path}")

        result = {
            "success": True,
            "original_path": str(texture_path),
            "converted_path": str(actual_output_path) if actual_output_path else converted_path,
            "relative_path": converted_path,
            "original_dimensions": original_dimensions,
            "converted_dimensions": (new_width, new_height),
            "format": "png",
            "resized": resized,
            "optimizations_applied": optimizations_applied,
            "bedrock_reference": f"{usage}_{base_name}",
            "animation_data": animation_data,
            "was_valid_png": is_valid_png,
            "was_fallback": not Path(texture_path).exists(),
        }

        # Cache the result
        agent._conversion_cache[cache_key] = result

        return result
    except Exception as e:
        logger.error(f"Texture conversion error for {texture_path}: {e}")
        error_result = {"success": False, "original_path": str(texture_path), "error": str(e)}
        # Cache error results too to avoid repeated failures
        agent._conversion_cache[cache_key] = error_result
        return error_result

# ============================================================================
# _generate_texture_pack_structure
# ============================================================================

def _generate_texture_pack_structure(agent, textures: List[Dict]) -> Dict:
    """Generate texture pack structure files with enhanced atlas handling"""
    manifest = {
        "format_version": 2,
        "header": {
            "name": "Converted Resource Pack",
            "description": "Assets converted from Java mod",
            "uuid": "f4aeb009-270e-4a11-8137-a916a1a3ea1e",
            "version": [1, 0, 0],
            "min_engine_version": [1, 16, 0],
        },
        "modules": [
            {
                "type": "resources",
                "uuid": "0d28590c-1797-4555-9a19-5ee98def104e",
                "version": [1, 0, 0],
            }
        ],
    }

    item_texture_data = {}
    terrain_texture_data = {}
    flipbook_entries = []

    # Track texture atlases
    texture_atlases = {}

    for t_data in textures:
        if not t_data.get("success"):
            continue

        bedrock_ref = t_data.get("bedrock_reference", Path(t_data["converted_path"]).stem)
        converted_path = t_data["converted_path"]
        texture_entry = {"textures": converted_path}

        # Enhanced atlas handling - group related textures
        # For simplicity, we're using a basic heuristic based on naming
        base_name = Path(converted_path).stem
        if "_" in base_name:
            atlas_name = base_name.split("_")[0]  # Group by prefix
            if atlas_name not in texture_atlases:
                texture_atlases[atlas_name] = []
            texture_atlases[atlas_name].append(
                {"reference": bedrock_ref, "path": converted_path}
            )

        if bedrock_ref.startswith("item_") or "/items/" in converted_path:
            item_texture_data[bedrock_ref] = texture_entry
        elif bedrock_ref.startswith("block_") or "/blocks/" in converted_path:
            terrain_texture_data[bedrock_ref] = texture_entry
        elif bedrock_ref.startswith("entity_") or "/entity/" in converted_path:
            terrain_texture_data[bedrock_ref] = texture_entry
        else:
            terrain_texture_data[bedrock_ref] = texture_entry

        if t_data.get("animation_data"):
            anim_data = t_data["animation_data"]
            frames_list = anim_data.get("frames", [])

            if frames_list and all(isinstance(f, dict) for f in frames_list):
                try:
                    processed_frames = [
                        int(f["index"])
                        for f in frames_list
                        if isinstance(f, dict) and "index" in f
                    ]
                    if not processed_frames:
                        processed_frames = []
                except (TypeError, ValueError):
                    processed_frames = []
            elif frames_list and all(isinstance(f, (int, float)) for f in frames_list):
                processed_frames = [int(f) for f in frames_list]
            else:
                processed_frames = list(range(anim_data.get("frame_count", 1)))

            ticks = anim_data.get("frametime", 1)
            if ticks <= 0:
                ticks = 1

            entry = {
                "flipbook_texture": converted_path,
                "atlas_tile": Path(converted_path).stem,
                "ticks_per_frame": ticks,
                "frames": processed_frames,
            }
            if "interpolate" in anim_data:
                entry["interpolate"] = anim_data["interpolate"]

            flipbook_entries.append(entry)

    result = {"pack_manifest.json": manifest}
    if item_texture_data:
        result["item_texture.json"] = {
            "resource_pack_name": "vanilla",
            "texture_data": item_texture_data,
        }
    if terrain_texture_data:
        result["terrain_texture.json"] = {
            "resource_pack_name": "vanilla",
            "texture_data": terrain_texture_data,
        }
    if flipbook_entries:
        result["flipbook_textures.json"] = flipbook_entries

    # Add texture atlas information if any were detected
    if texture_atlases:
        result["texture_atlases.json"] = texture_atlases

    return result

# ============================================================================
# convert_textures
# ============================================================================

def convert_textures(agent, texture_list: str, output_path: str) -> str:
    """
    Convert textures to Bedrock-compatible format and save to disk.

    Args:
        texture_list: JSON string containing list of texture paths or structured data
        output_path: Output directory path

    Returns:
        JSON string with conversion results
    """
    try:
        # Parse texture_list
        if isinstance(texture_list, str):
            data = (
                json.loads(texture_list)
                if texture_list.startswith("[") or texture_list.startswith("{")
                else texture_list
            )
        else:
            data = texture_list

        # Handle different input formats
        if isinstance(data, list):
            # Simple list of texture paths
            textures = [{"path": path, "usage": "block"} for path in data]
        elif isinstance(data, dict):
            # Structured data
            textures = data.get("textures", [])
        else:
            # Single path
            textures = [{"path": str(data), "usage": "block"}]

        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        result = {
            "converted_textures": [],
            "total_textures": len(textures),
            "successful_conversions": 0,
            "failed_conversions": 0,
            "errors": [],
        }

        for texture_data in textures:
            try:
                if isinstance(texture_data, str):
                    texture_path = texture_data
                    usage = "block"
                    metadata = {}
                else:
                    texture_path = texture_data.get("path", "")
                    usage = texture_data.get("usage", "block")
                    metadata = texture_data.get("metadata", {})

                # Convert the texture and save to output directory
                conversion_result = agent._convert_single_texture(
                    texture_path, metadata, usage, output_path
                )

                if conversion_result.get("success"):
                    result["converted_textures"].append(
                        {
                            "original_path": texture_path,
                            "converted_path": conversion_result["converted_path"],
                            "relative_path": conversion_result["relative_path"],
                            "success": True,
                            "dimensions": conversion_result["converted_dimensions"],
                            "resized": conversion_result["resized"],
                            "optimizations": conversion_result["optimizations_applied"],
                        }
                    )
                    result["successful_conversions"] += 1
                else:
                    result["errors"].append(
                        f"Failed to convert {texture_path}: {conversion_result.get('error', 'Unknown error')}"
                    )
                    result["failed_conversions"] += 1
            except Exception as e:
                logger.error(f"Error converting texture {texture_data}: {e}")
                result["errors"].append(f"Failed to convert {texture_data}: {e}")
                result["failed_conversions"] += 1

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error converting textures: {e}")
        return json.dumps(
            {
                "converted_textures": [],
                "total_textures": 0,
                "successful_conversions": 0,
                "failed_conversions": 0,
                "errors": [str(e)],
            },
            indent=2,
        )

# ============================================================================
# detect_texture_atlas
# ============================================================================

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

        # Common atlas indicators
        is_atlas = False
        atlas_type = None
        tile_size = 16  # Default tile size

        # Check for common atlas patterns
        # 1. Square textures that are multiples of 16x16
        if width == height and width > 16:
            # Could be an atlas if it's a large square
            if width >= 64:  # At least 4x4 tiles
                is_atlas = True
                atlas_type = "grid"
                tile_size = 16

        # 2. Check for common atlas sizes (256x256, 512x512, etc.)
        common_atlas_sizes = [256, 512, 1024]
        if width in common_atlas_sizes or height in common_atlas_sizes:
            is_atlas = True
            atlas_type = "grid"

        # 3. Check for non-square but multiple-of-16 dimensions
        if width != height and (width % 16 == 0 or height % 16 == 0):
            if width >= 64 or height >= 64:
                is_atlas = True
                atlas_type = "strip"  # Horizontal or vertical strip

        # Calculate grid dimensions
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

# ============================================================================
# extract_texture_atlas
# ============================================================================

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

        # Ensure RGBA mode
        img = img.convert("RGBA")

        tiles_x = width // tile_size
        tiles_y = height // tile_size

        extracted_tiles = []

        for y in range(tiles_y):
            for x in range(tiles_x):
                # Calculate crop box
                left = x * tile_size
                upper = y * tile_size
                right = left + tile_size
                lower = upper + tile_size

                # Crop the tile
                tile = img.crop((left, upper, right, lower))

                # Check if tile is not empty (has non-transparent pixels)
                tile_data = list(tile.getdata())
                has_content = any(pixel[3] > 0 for pixel in tile_data)

                if has_content:
                    # Generate filename
                    tile_name = naming_pattern.format(x=x, y=y, index=y * tiles_x + x)
                    tile_filename = f"{tile_name}.png"
                    tile_path = output_path / tile_filename

                    # Save the tile
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

# ============================================================================
# parse_atlas_metadata
# ============================================================================

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

        # Parse animation data
        if "animation" in metadata:
            anim = metadata["animation"]
            result["animation"] = {
                "interpolate": anim.get("interpolate", False),
                "width": anim.get("width"),
                "height": anim.get("height"),
                "frametime": anim.get("frametime", 1),
                "frames": anim.get("frames", []),
            }

        # Parse villager metadata (for entity textures)
        if "villager" in metadata:
            result["villager"] = metadata["villager"]

        # Store any other custom metadata
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

# ============================================================================
# convert_atlas_to_bedrock
# ============================================================================

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
        # First detect if it's an atlas
        detection = agent.detect_texture_atlas(atlas_path)

        if not detection["is_atlas"]:
            # Not an atlas, just convert as single texture
            return agent._convert_single_texture(atlas_path, {}, "block", Path(output_dir))

        # Extract the atlas
        extraction = agent.extract_texture_atlas(
            atlas_path, output_dir, tile_size=detection["tile_size"]
        )

        if not extraction["success"]:
            return extraction

        # Convert each extracted tile
        converted_textures = []
        for tile in extraction["extracted_tiles"]:
            # Determine texture name
            if texture_names and tile["index"] < len(texture_names):
                name = texture_names[tile["index"]]
            else:
                name = tile["name"]

            # Convert the tile
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

# ============================================================================
# convert_java_texture_path
# ============================================================================

def convert_java_texture_path(agent, java_path: str, bedrock_type: str = "blocks") -> str:
    """
    Convert Java texture path to Bedrock texture path.

    Args:
        java_path: Java texture path (e.g., 'assets/modid/textures/block/grass_block_side.png')
        bedrock_type: Target Bedrock texture type ('blocks', 'items', 'entity')

    Returns:
        Bedrock texture path (e.g., 'textures/blocks/grass_block_side')
    """
    # Parse Java path
    parts = java_path.replace("\\", "/").split("/")

    # Find textures index
    try:
        textures_idx = parts.index("textures")
    except ValueError:
        # Try alternative structure
        textures_idx = -1

    if textures_idx >= 0:
        # Extract relative path after textures/
        relative_parts = parts[textures_idx + 1 :]
    else:
        # Try to find the PNG file and use remaining parts
        relative_parts = [p for p in parts if p.endswith(".png")]
        if relative_parts:
            # Use filename only
            relative_parts = [relative_parts[0]]
        else:
            relative_parts = []

    # Extract filename without extension
    if relative_parts:
        filename = relative_parts[-1]
        if filename.endswith(".png"):
            filename = filename[:-4]
    else:
        filename = "unknown"

    # Build Bedrock path
    bedrock_path = f"textures/{bedrock_type}/{filename}"

    logger.debug(f"Converted Java path '{java_path}' to Bedrock path '{bedrock_path}'")
    return bedrock_path

# ============================================================================
# validate_texture
# ============================================================================

def validate_texture(agent, texture_path: str, metadata: Dict = None) -> Dict:
    """
    Validate a texture for Bedrock compatibility.

    Args:
        texture_path: Path to the texture file
        metadata: Optional metadata about the texture

    Returns:
        Dict with validation results
    """
    result = {"valid": True, "errors": [], "warnings": [], "properties": {}}

    try:
        path = Path(texture_path)

        # Check if file exists
        if not path.exists():
            result["valid"] = False
            result["errors"].append(f"Texture file not found: {texture_path}")
            return result

        # Open and analyze image
        with Image.open(path) as img:
            width, height = img.size

            # Store properties
            result["properties"] = {
                "width": width,
                "height": height,
                "format": img.format,
                "mode": img.mode,
                "size_bytes": path.stat().st_size,
            }

            # Validate dimensions
            if width != height:
                result["warnings"].append(f"Non-square texture: {width}x{height}")

            # Check power of 2
            if not agent._is_power_of_2(width):
                result["warnings"].append(f"Width {width} is not a power of 2")
                if agent.texture_constraints.get("must_be_power_of_2", True):
                    result["valid"] = False
                    result["errors"].append(f"Width must be power of 2 for Bedrock")

            if not agent._is_power_of_2(height):
                result["warnings"].append(f"Height {height} is not a power of 2")
                if agent.texture_constraints.get("must_be_power_of_2", True):
                    result["valid"] = False
                    result["errors"].append(f"Height must be power of 2 for Bedrock")

            # Check max resolution
            max_res = agent.texture_constraints.get("max_resolution", 1024)
            if width > max_res or height > max_res:
                result["valid"] = False
                result["errors"].append(
                    f"Texture exceeds maximum resolution {max_res}: {width}x{height}"
                )

            # Check format
            if img.format != "PNG":
                result["warnings"].append(f"Non-PNG format: {img.format}")
                if agent.texture_constraints.get("must_be_png", False):
                    result["valid"] = False
                    result["errors"].append("Texture must be PNG format for Bedrock")

            # Check color mode
            if img.mode not in ["RGB", "RGBA"]:
                result["valid"] = False
                result["errors"].append(f"Unsupported color mode: {img.mode}")

    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Failed to validate texture: {str(e)}")

    return result

# ============================================================================
# generate_fallback_for_jar
# ============================================================================

def generate_fallback_for_jar(
    self, output_path: str, block_name: str, texture_type: str = "blocks"
) -> Dict:
    """
    Generate fallback texture when JAR extraction fails.

    Args:
        output_path: Path to save the fallback texture
        block_name: Name for the fallback texture
        texture_type: Type of texture ('blocks', 'items', 'entity')

    Returns:
        Dict with generation result
    """
    try:
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Generate fallback texture
        img = agent._generate_fallback_texture(texture_type)

        # Resize to appropriate size (16x16 for blocks, 16x16 for items)
        if texture_type == "blocks":
            img = img.resize((16, 16), Image.LANCZOS)
        else:
            img = img.resize((16, 16), Image.LANCZOS)

        # Save
        img.save(output_path, "PNG", optimize=True)

        return {
            "success": True,
            "output_path": output_path,
            "dimensions": img.size,
            "generated": True,
        }

    except Exception as e:
        logger.error(f"Error generating fallback texture: {e}")
        return {"success": False, "error": str(e)}

# ============================================================================
# _get_recommended_resolution
# ============================================================================

def _get_recommended_resolution(agent, width: int, height: int) -> str:
    """Get recommended resolution for texture"""
    # Find the nearest power of 2 that's within constraints
    max_res = agent.texture_constraints["max_resolution"]

    target_width = min(max_res, agent._next_power_of_2(width))
    target_height = min(max_res, agent._next_power_of_2(height))

    return f"{target_width}x{target_height}"

# ============================================================================
# _generate_conversion_recommendations
# ============================================================================

def _generate_conversion_recommendations(agent, analysis: Dict) -> List[str]:
    """Generate conversion recommendations based on analysis"""
    recommendations = []

    texture_count = analysis["textures"]["count"]
    model_count = analysis["models"]["count"]
    audio_count = analysis["audio"]["count"]

    if texture_count > 0:
        recommendations.append(
            f"Convert {texture_count} textures to PNG format with power-of-2 dimensions"
        )

    if model_count > 0:
        recommendations.append(f"Convert {model_count} models to Bedrock geometry format")

    if audio_count > 0:
        recommendations.append(f"Convert {audio_count} audio files to OGG format")

    total_issues = (
        len(analysis["textures"]["issues"])
        + len(analysis["models"]["issues"])
        + len(analysis["audio"]["issues"])
    )

    if total_issues > 0:
        recommendations.append(f"Address {total_issues} compatibility issues")

    return recommendations

# ============================================================================
# _assess_conversion_complexity
# ============================================================================

def _assess_conversion_complexity(agent, analysis: Dict) -> str:
    """Assess the complexity of the conversion task"""
    total_conversions = (
        len(analysis["textures"]["conversions_needed"])
        + len(analysis["models"]["conversions_needed"])
        + len(analysis["audio"]["conversions_needed"])
    )

    total_issues = (
        len(analysis["textures"]["issues"])
        + len(analysis["models"]["issues"])
        + len(analysis["audio"]["issues"])
    )

    if total_conversions == 0 and total_issues == 0:
        return "simple"
    elif total_conversions < 5 and total_issues < 3:
        return "moderate"
    else:
        return "complex"

# ============================================================================
# extract_textures_from_jar
# ============================================================================

def extract_textures_from_jar(
    self, jar_path: str, output_dir: str, namespace: str = None
) -> Dict:
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
            # Get list of all files in the JAR
            file_list = jar.namelist()

            # Find texture files (PNG in assets/*/textures/)
            texture_files = [
                f
                for f in file_list
                if f.startswith("assets/") and "/textures/" in f and f.endswith(".png")
            ]

            # Filter by namespace if provided
            if namespace:
                texture_files = [
                    f for f in texture_files if f.startswith(f"assets/{namespace}/")
                ]

            # Also look for mcmeta animation files
            mcmeta_files = [
                f
                for f in file_list
                if f.startswith("assets/") and "/textures/" in f and f.endswith(".png.mcmeta")
            ]

            for texture_file in texture_files:
                try:
                    # Read texture data from JAR
                    texture_data = jar.read(texture_file)

                    # Determine output path based on Java texture path
                    # assets/namespace/textures/block/name.png -> textures/blocks/name.png
                    bedrock_path = agent._map_java_texture_to_bedrock(texture_file)

                    # Create output subdirectories
                    full_output_dir = output_path / Path(bedrock_path).parent
                    full_output_dir.mkdir(parents=True, exist_ok=True)

                    # Save texture
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

                    # Check for associated mcmeta file
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

# ============================================================================
# _map_java_texture_to_bedrock
# ============================================================================

def _map_java_texture_to_bedrock(agent, java_path: str) -> str:
    """
    Map a Java mod texture path to Bedrock resource pack texture path.

    Java: assets/<namespace>/textures/<type>/<name>.png
    Bedrock: textures/<type>/<name>.png

    Args:
        java_path: Java mod texture path

    Returns:
        Bedrock texture path
    """
    # Parse: assets/namespace/textures/type/name.png
    parts = java_path.split("/")

    if len(parts) >= 5 and parts[0] == "assets" and parts[2] == "textures":
        texture_type = parts[3]  # block, item, entity, etc.
        texture_name = parts[4]  # name.png

        # Map Java texture types to Bedrock
        bedrock_type = agent._map_texture_type(texture_type)

        return f"textures/{bedrock_type}/{texture_name}"

    # Fallback: just use the filename in textures/
    return f"textures/{Path(java_path).name}"

# ============================================================================
# _map_texture_type
# ============================================================================

def _map_texture_type(agent, java_type: str) -> str:
    """
    Map Java texture type to Bedrock texture type.

    Args:
        java_type: Java texture type (block, item, entity, etc.)

    Returns:
        Bedrock texture type
    """
    type_mapping = {
        "block": "blocks",
        "item": "items",
        "entity": "entity",
        "blockentity": "entity",
        "particle": "particle",
        "armor": "armor",
        "misc": "misc",
        "environment": "environment",
        "gui": "gui",
        "painting": "painting",
    }

    return type_mapping.get(java_type.lower(), "misc")

# ============================================================================
# _map_bedrock_texture_to_java
# ============================================================================

def _map_bedrock_texture_to_java(agent, bedrock_path: str, namespace: str) -> str:
    """
    Map a Bedrock texture path back to Java mod texture path.

    Bedrock: textures/blocks/name.png
    Java: assets/<namespace>/textures/block/name.png

    Args:
        bedrock_path: Bedrock texture path
        namespace: Java mod namespace

    Returns:
        Java texture path
    """
    parts = bedrock_path.split("/")

    if len(parts) >= 3 and parts[0] == "textures":
        bedrock_type = parts[1]  # blocks, items, entity, etc.
        texture_name = parts[2]

        # Map Bedrock texture type to Java
        java_type = agent._map_bedrock_type_to_java(bedrock_type)

        return f"assets/{namespace}/textures/{java_type}/{texture_name}"

    return f"assets/{namespace}/textures/misc/{bedrock_path}"

# ============================================================================
# _map_bedrock_type_to_java
# ============================================================================

def _map_bedrock_type_to_java(agent, bedrock_type: str) -> str:
    """
    Map Bedrock texture type to Java texture type.

    Args:
        bedrock_type: Bedrock texture type (blocks, items, entity, etc.)

    Returns:
        Java texture type
    """
    type_mapping = {
        "blocks": "block",
        "items": "item",
        "entity": "entity",
        "particle": "particle",
        "armor": "armor",
        "misc": "misc",
        "environment": "environment",
        "gui": "gui",
    }

    return type_mapping.get(bedrock_type.lower(), "misc")

# ============================================================================
# validate_textures_batch
# ============================================================================

def validate_textures_batch(agent, texture_paths: List[str], metadata: Dict = None) -> Dict:
    """
    Validate multiple textures in batch.

    Args:
        texture_paths: List of texture file paths
        metadata: Optional metadata about textures

    Returns:
        Dict with batch validation results
    """
    results = []
    valid_count = 0
    invalid_count = 0
    warning_count = 0

    for texture_path in texture_paths:
        validation = agent.validate_texture(texture_path, metadata)
        results.append({"path": texture_path, "validation": validation})

        if validation["valid"]:
            valid_count += 1
        else:
            invalid_count += 1

        if validation["warnings"]:
            warning_count += 1

    return {
        "total": len(texture_paths),
        "valid": valid_count,
        "invalid": invalid_count,
        "warnings": warning_count,
        "results": results,
    }

# ============================================================================
# extract_texture_atlas_from_jar
# ============================================================================

def extract_texture_atlas_from_jar(
    self, jar_path: str, atlas_type: str, output_dir: str
) -> Dict:
    """
    Extract and convert a texture atlas from a mod JAR.

    Args:
        jar_path: Path to the JAR file
        atlas_type: Type of atlas ('terrain', 'items', 'entity', etc.)
        output_dir: Directory to save extracted textures

    Returns:
        Dict with extraction results
    """
    extracted_tiles = []
    errors = []

    try:
        jar = zipfile.ZipFile(jar_path, "r")
        file_list = jar.namelist()

        # Find atlas files
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

        # Check if atlas exists in JAR
        if atlas_path not in file_list:
            # Try alternative patterns
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

        # Read atlas image
        atlas_data = jar.read(atlas_path)

        # Save temporarily to process
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_atlas:
            temp_atlas.write(atlas_data)
            temp_atlas_path = temp_atlas.name

        jar.close()

        # Extract tiles from atlas
        result = agent.extract_texture_atlas(temp_atlas_path, output_dir)

        # Clean up temp file
        Path(temp_atlas_path).unlink(missing_ok=True)

        return result

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to extract atlas: {str(e)}",
            "extracted_tiles": [],
        }

# ============================================================================
# convert_jar_textures_to_bedrock
# ============================================================================

def convert_jar_textures_to_bedrock(
    self, jar_path: str, output_dir: str, namespace: str = None
) -> Dict:
    """
    Complete pipeline to extract textures from JAR and convert to Bedrock format.

    Args:
        jar_path: Path to the Java mod JAR file
        output_dir: Directory to save converted textures
        namespace: Optional namespace to filter textures

    Returns:
        Dict with conversion results
    """
    results = {
        "success": False,
        "extracted": [],
        "converted": [],
        "failed": [],
        "warnings": [],
        "errors": [],
    }

    try:
        # Step 1: Extract textures from JAR
        extract_result = agent.extract_textures_from_jar(jar_path, output_dir, namespace)

        if not extract_result["success"]:
            results["errors"].append(
                f"Failed to extract textures: {extract_result.get('error', 'Unknown error')}"
            )
            return results

        results["extracted"] = extract_result["extracted_textures"]

        # Step 2: Convert each texture to Bedrock format
        for texture_info in extract_result["extracted_textures"]:
            texture_path = texture_info["output_path"]

            try:
                # Validate texture
                validation = agent.validate_texture(texture_path)

                if not validation["valid"]:
                    results["failed"].append(
                        {"path": texture_path, "errors": validation["errors"]}
                    )
                    results["warnings"].extend(validation["warnings"])
                    continue

                # Convert texture (resize to power of 2 if needed)
                conversion_result = agent._convert_single_texture(
                    texture_path,
                    {},
                    "block",  # Default usage
                    None,  # Don't save again, already saved
                )

                if conversion_result.get("success"):
                    results["converted"].append(
                        {
                            "original": texture_info["original_path"],
                            "converted": texture_path,
                            "bedrock_path": texture_info["bedrock_path"],
                        }
                    )
                else:
                    # Generate fallback texture
                    fallback = agent._generate_fallback_texture("block")
                    fallback_path = Path(texture_path)
                    fallback.save(fallback_path, "PNG")

                    results["converted"].append(
                        {
                            "original": texture_info["original_path"],
                            "converted": texture_path,
                            "bedrock_path": texture_info["bedrock_path"],
                            "used_fallback": True,
                        }
                    )
                    results["warnings"].append(f"Used fallback texture for {texture_path}")

            except Exception as e:
                results["failed"].append({"path": texture_path, "errors": [str(e)]})

        results["success"] = len(results["converted"]) > 0

    except Exception as e:
        results["errors"].append(f"Conversion pipeline failed: {str(e)}")

    return results

# ============================================================================
# _generate_fallback_texture
# ============================================================================

def _generate_fallback_texture(
    self, usage: str = "block", size: tuple = (16, 16)
) -> Image.Image:
    """Generate a fallback texture for edge cases"""
    # Create a simple colored texture based on usage type
    colors = {
        "block": (128, 128, 128, 255),  # Gray for blocks
        "item": (200, 200, 100, 255),  # Yellowish for items
        "entity": (150, 100, 100, 255),  # Reddish for entities
        "particle": (200, 200, 255, 255),  # Light blue for particles
        "ui": (100, 200, 100, 255),  # Green for UI
        "other": (128, 128, 128, 255),  # Default gray
    }

    color = colors.get(usage, colors["other"])
    img = Image.new("RGBA", size, color)

    # Add a simple pattern to make it identifiable
    for x in range(0, size[0], 4):
        for y in range(0, size[1], 4):
            if (x + y) % 8 == 0:
                img.putpixel(
                    (x, y),
                    (
                        min(255, color[0] + 50),
                        min(255, color[1] + 50),
                        min(255, color[2] + 50),
                        255,
                    ),
                )

    return img

# ============================================================================
# _get_mod_ids_from_jar
# ============================================================================

def _get_mod_ids_from_jar(agent, jar: zipfile.ZipFile) -> List[str]:
    """Extract mod IDs/namespaces from JAR assets directory."""
    mod_ids = set()
    try:
        for file_path in jar.namelist():
            # Match assets/modid/...
            parts = file_path.split("/")
            if len(parts) >= 2 and parts[0] == "assets":
                mod_ids.add(parts[1])
    except Exception as e:
        logger.warning(f"Error reading mod IDs from JAR: {e}")

    # Always include 'minecraft' as fallback
    return list(mod_ids) if mod_ids else ["minecraft"]

# ============================================================================
# _extract_textures_from_alt_locations
# ============================================================================

def _extract_textures_from_alt_locations(
    self, jar: zipfile.ZipFile, output_path: Path
) -> List[Dict]:
    """Extract textures from alternative locations in JAR."""
    extracted = []
    alt_patterns = ["textures/", "assets/textures/", "/textures/"]

    try:
        for file_info in jar.filelist:
            file_path = file_info.filename

            # Only process PNG files
            if not file_path.endswith(".png"):
                continue

            # Check for alternative patterns
            is_alt_texture = any(file_path.startswith(pattern) for pattern in alt_patterns)

            if is_alt_texture:
                try:
                    texture_data = jar.read(file_path)

                    # Determine namespace
                    if "assets/" in file_path:
                        namespace = file_path.split("assets/")[-1].split("/")[0]
                    else:
                        namespace = "minecraft"

                    # Determine relative path
                    if "textures/" in file_path:
                        relative_path = file_path.split("textures/")[-1]
                    else:
                        relative_path = file_path.lstrip("/")

                    # Save
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