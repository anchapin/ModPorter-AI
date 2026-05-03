"""
Atlas Descriptor Parser for Minecraft texture sprite sheets.

This module handles parsing of JSON atlas descriptor files that map sprite names
to regions within texture atlas images. This is used by mods like JEI and JourneyMap
that pack individual textures into sprite sheets.

Minecraft Forge atlas descriptor format:
{
    "sources": [
        {
            "type": "single",
            "resourceLocation": "modid:textures/gui/widgets.png"
        },
        {
            "type": "horizontal",
            "resourceLocation": "modid:textures/gui/buttons.png",
            "index": 0
        }
    ]
}

Alternative mod-specific formats may use:
- "sprites" array with name, x, y, width, height fields
- Direct region definitions within the JSON
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

logger = logging.getLogger(__name__)

__all__ = [
    "AtlasSpriteInfo",
    "parse_atlas_descriptor",
    "find_atlas_descriptors_in_jar",
    "extract_sprites_from_atlas",
]


class AtlasSpriteInfo:
    """Represents a single sprite extracted from an atlas."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        width: int,
        height: int,
        atlas_path: str,
        original_name: Optional[str] = None,
    ):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.atlas_path = atlas_path
        self.original_name = original_name or name

    def __repr__(self) -> str:
        return (
            f"AtlasSpriteInfo(name={self.name}, x={self.x}, y={self.y}, "
            f"width={self.width}, height={self.height})"
        )

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "atlas_path": self.atlas_path,
            "original_name": self.original_name,
        }


def parse_atlas_descriptor(
    descriptor_path: str,
    atlas_base_path: str,
) -> Dict[str, AtlasSpriteInfo]:
    """
    Parse a Minecraft atlas descriptor JSON file.

    Args:
        descriptor_path: Path to the JSON descriptor file
        atlas_base_path: Base path to the atlas image (for resolving relative paths)

    Returns:
        Dict mapping sprite names to AtlasSpriteInfo objects
    """
    sprites = {}

    try:
        with open(descriptor_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle Minecraft format with "sources" array
        if "sources" in data:
            sprites = _parse_minecraft_format(data, atlas_base_path)

        # Handle "sprites" array format (JEI and some other mods)
        elif "sprites" in data:
            sprites = _parse_sprites_format(data, atlas_base_path)

        # Handle direct region format (mod-specific)
        elif "regions" in data:
            sprites = _parse_regions_format(data, atlas_base_path)

        # Handle simple list format with per-sprite metadata
        elif isinstance(data, dict):
            sprites = _parse_direct_dict_format(data, atlas_base_path)

        else:
            logger.warning(f"Unknown atlas descriptor format in {descriptor_path}")
            return sprites

        logger.info(f"Parsed {len(sprites)} sprites from {descriptor_path}")

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in atlas descriptor {descriptor_path}: {e}")
    except Exception as e:
        logger.error(f"Error parsing atlas descriptor {descriptor_path}: {e}")

    return sprites


def _parse_minecraft_format(data: Dict, atlas_base_path: str) -> Dict[str, AtlasSpriteInfo]:
    """Parse Minecraft-style atlas descriptor with sources array."""
    sprites = {}

    for source in data.get("sources", []):
        source_type = source.get("type", "single")
        resource_location = source.get("resourceLocation", "")

        if not resource_location:
            continue

        # Extract modid and path from resourceLocation
        # Format: "modid:textures/gui/widgets.png" or just "textures/gui/widgets.png"
        if ":" in resource_location:
            modid, rel_path = resource_location.split(":", 1)
        else:
            rel_path = resource_location

        # Remove file extension for sprite name
        sprite_name = Path(rel_path).stem.replace("textures/", "").replace("/", "_")

        if source_type == "single":
            # Single texture - may not need extraction if standalone
            sprites[sprite_name] = AtlasSpriteInfo(
                name=sprite_name,
                x=0,
                y=0,
                width=0,  # Will be determined from atlas dimensions
                height=0,
                atlas_path=atlas_base_path,
                original_name=resource_location,
            )

        elif source_type == "horizontal":
            # Horizontal strip of uniform-width sprites
            index = source.get("index", 0)
            width = source.get("width", 16)  # Default tile width
            height = source.get("height", 16)

            # Create sprite name with index
            sprites[f"{sprite_name}_{index}"] = AtlasSpriteInfo(
                name=f"{sprite_name}_{index}",
                x=index * width,
                y=0,
                width=width,
                height=height,
                atlas_path=atlas_base_path,
                original_name=resource_location,
            )

        elif source_type == "direct":
            # Direct region specification
            sprites[sprite_name] = AtlasSpriteInfo(
                name=sprite_name,
                x=source.get("x", 0),
                y=source.get("y", 0),
                width=source.get("width", 16),
                height=source.get("height", 16),
                atlas_path=atlas_base_path,
                original_name=resource_location,
            )

    return sprites


def _parse_sprites_format(data: Dict, atlas_base_path: str) -> Dict[str, AtlasSpriteInfo]:
    """Parse sprites array format."""
    sprites = {}

    for sprite_data in data.get("sprites", []):
        if isinstance(sprite_data, dict):
            sprites[sprite_data["name"]] = AtlasSpriteInfo(
                name=sprite_data["name"],
                x=sprite_data.get("x", 0),
                y=sprite_data.get("y", 0),
                width=sprite_data.get("width", 16),
                height=sprite_data.get("height", 16),
                atlas_path=atlas_base_path,
                original_name=sprite_data.get("originalName", sprite_data["name"]),
            )
        elif isinstance(sprite_data, str):
            # Just a name - placeholder position
            sprites[sprite_data] = AtlasSpriteInfo(
                name=sprite_data,
                x=0,
                y=0,
                width=16,
                height=16,
                atlas_path=atlas_base_path,
                original_name=sprite_data,
            )

    return sprites


def _parse_regions_format(data: Dict, atlas_base_path: str) -> Dict[str, AtlasSpriteInfo]:
    """Parse regions array format."""
    sprites = {}

    for region in data.get("regions", []):
        sprites[region["name"]] = AtlasSpriteInfo(
            name=region["name"],
            x=region.get("x", 0),
            y=region.get("y", 0),
            width=region.get("width", 16),
            height=region.get("height", 16),
            atlas_path=atlas_base_path,
            original_name=region.get("originalName", region["name"]),
        )

    return sprites


def _parse_direct_dict_format(data: Dict, atlas_base_path: str) -> Dict[str, AtlasSpriteInfo]:
    """Parse direct dictionary format where keys are sprite names."""
    sprites = {}

    for sprite_name, sprite_data in data.items():
        if isinstance(sprite_data, dict):
            sprites[sprite_name] = AtlasSpriteInfo(
                name=sprite_name,
                x=sprite_data.get("x", 0),
                y=sprite_data.get("y", 0),
                width=sprite_data.get("width", 16),
                height=sprite_data.get("height", 16),
                atlas_path=atlas_base_path,
                original_name=sprite_data.get("originalName", sprite_name),
            )
        elif isinstance(sprite_data, (list, tuple)) and len(sprite_data) >= 4:
            # [x, y, width, height] format
            sprites[sprite_name] = AtlasSpriteInfo(
                name=sprite_name,
                x=sprite_data[0],
                y=sprite_data[1],
                width=sprite_data[2],
                height=sprite_data[3],
                atlas_path=atlas_base_path,
                original_name=sprite_name,
            )

    return sprites


def find_atlas_descriptors_in_jar(
    jar,
    modid: str,
    texture_type: str = "gui",
) -> Dict[str, str]:
    """
    Find atlas descriptor JSON files in a mod JAR.

    Args:
        jar: ZipFile object of the mod JAR
        modid: The mod's namespace/ID
        texture_type: Type of textures (e.g., 'gui', 'item', 'block')

    Returns:
        Dict mapping texture paths to their descriptor JSON paths
    """
    file_list = jar.namelist()
    descriptors = {}

    # Common atlas descriptor file patterns

    for file_path in file_list:
        # Look for PNG files that might be atlases
        if file_path.endswith(".png") and f"textures/{texture_type}/" in file_path:
            png_name = Path(file_path).stem

            # Look for matching JSON descriptor
            # Pattern 1: same name + .json
            json_path = file_path.replace(".png", ".json")
            if json_path in file_list:
                descriptors[file_path] = json_path
                continue

            # Pattern 2: in a separate "atlases" or "sprites" subdirectory
            alt_json_paths = [
                file_path.replace(
                    f"textures/{texture_type}/", f"textures/{texture_type}/atlases/"
                ).replace(".png", ".json"),
                file_path.replace(
                    f"textures/{texture_type}/", f"textures/{texture_type}/sprites/"
                ).replace(".png", ".json"),
                f"assets/{modid}/atlases/{png_name}.json",
                f"assets/{modid}/textures/atlases/{png_name}.json",
            ]

            for alt_path in alt_json_paths:
                if alt_path in file_list:
                    descriptors[file_path] = alt_path
                    break

    return descriptors


def extract_sprites_from_atlas(
    atlas_path: str,
    sprites: Dict[str, AtlasSpriteInfo],
    output_dir: str,
    naming_pattern: str = "sprite_{name}",
) -> List[Dict]:
    """
    Extract individual sprites from a texture atlas using sprite info from a descriptor.

    Args:
        atlas_path: Path to the atlas texture file
        sprites: Dict of sprite name -> AtlasSpriteInfo
        output_dir: Directory to save extracted sprites
        naming_pattern: Pattern for naming extracted files

    Returns:
        List of extracted sprite info dicts
    """
    extracted = []

    try:
        path = Path(atlas_path)
        if not path.exists():
            logger.error(f"Atlas file not found: {atlas_path}")
            return extracted

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        img = Image.open(atlas_path)
        atlas_width, atlas_height = img.size

        # Ensure RGBA mode
        img = img.convert("RGBA")

        for sprite_name, sprite_info in sprites.items():
            x = sprite_info.x
            y = sprite_info.y
            width = sprite_info.width
            height = sprite_info.height

            # If width/height are 0, assume it's the full atlas size
            if width == 0 or height == 0:
                width = atlas_width
                height = atlas_height

            # Validate bounds
            if x < 0 or y < 0 or x + width > atlas_width or y + height > atlas_height:
                logger.warning(
                    f"Sprite {sprite_name} bounds out of atlas: "
                    f"({x}, {y}, {width}, {height}) vs atlas ({atlas_width}, {atlas_height})"
                )
                continue

            # Crop the sprite region
            tile = img.crop((x, y, x + width, y + height))

            # Check if tile has content (non-transparent pixels)
            tile_data = list(tile.getdata())
            has_content = any(pixel[3] > 0 for pixel in tile_data)

            if not has_content:
                logger.debug(f"Sprite {sprite_name} is empty, skipping")
                continue

            # Generate filename
            tile_name = naming_pattern.format(name=sprite_name)
            tile_filename = f"{tile_name}.png"
            tile_file_path = output_path / tile_filename

            # Save the sprite
            tile.save(tile_file_path, "PNG", optimize=True)

            extracted.append(
                {
                    "path": str(tile_file_path),
                    "name": sprite_name,
                    "original_name": sprite_info.original_name,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "atlas_path": atlas_path,
                }
            )

        logger.info(f"Extracted {len(extracted)} sprites from atlas {atlas_path}")

    except Exception as e:
        logger.error(f"Error extracting sprites from atlas {atlas_path}: {e}")

    return extracted


def is_likely_atlas_texture(
    jar,
    file_path: str,
    min_size: int = 128,
    max_individual_textures: int = 10,
) -> bool:
    """
    Heuristic to detect if a texture file is likely an atlas.

    Args:
        jar: ZipFile object
        file_path: Path to the texture in the JAR
        min_size: Minimum dimension to be considered an atlas
        max_individual_textures: If file_list contains fewer individual textures than this,
                                the atlas might be the main source

    Returns:
        True if the texture is likely an atlas
    """
    try:
        # Read the image dimensions without loading full image
        import io

        texture_data = jar.read(file_path)
        img = Image.open(io.BytesIO(texture_data))
        width, height = img.size

        # Atlases are typically larger than 64x64
        if width < min_size or height < min_size:
            return False

        # Common atlas sizes
        common_sizes = [128, 256, 512, 1024, 2048]
        if width not in common_sizes and height not in common_sizes:
            return False

        # If it's a square or near-square, might be an atlas
        aspect_ratio = width / height if height > 0 else 0
        if 0.5 <= aspect_ratio <= 2.0:
            return True

        return False

    except Exception:
        return False


def find_atlas_textures_in_jar(
    jar,
    modid: Optional[str] = None,
) -> List[Dict]:
    """
    Find all potential atlas textures in a mod JAR.

    Args:
        jar: ZipFile object
        modid: Optional mod ID to filter by namespace

    Returns:
        List of dicts with 'texture_path' and 'descriptor_path' keys
    """
    file_list = jar.namelist()
    atlases = []

    # Find all PNG files in textures directories
    texture_files = [
        f
        for f in file_list
        if f.startswith("assets/")
        and "/textures/" in f
        and f.endswith(".png")
        and (modid is None or f.startswith(f"assets/{modid}/"))
    ]

    for texture_file in texture_files:
        # Skip icons and small images
        try:
            import io

            texture_data = jar.read(texture_file)
            img = Image.open(io.BytesIO(texture_data))
            width, height = img.size

            # Skip small images (likely individual textures, not atlases)
            if width < 128 or height < 128:
                continue

            atlases.append(
                {
                    "texture_path": texture_file,
                    "width": width,
                    "height": height,
                    "descriptor_path": None,  # Will be filled by find_atlas_descriptors_in_jar
                }
            )
        except Exception:
            continue

    return atlases
