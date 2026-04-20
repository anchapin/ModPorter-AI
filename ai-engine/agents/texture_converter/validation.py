"""
Texture validation module.
"""

import logging
from pathlib import Path
from typing import Dict, List

from PIL import Image

logger = logging.getLogger(__name__)


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

        if not path.exists():
            result["valid"] = False
            result["errors"].append(f"Texture file not found: {texture_path}")
            return result

        with Image.open(path) as img:
            width, height = img.size

            result["properties"] = {
                "width": width,
                "height": height,
                "format": img.format,
                "mode": img.mode,
                "size_bytes": path.stat().st_size,
            }

            if width != height:
                result["warnings"].append(f"Non-square texture: {width}x{height}")

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

            max_res = agent.texture_constraints.get("max_resolution", 1024)
            if width > max_res or height > max_res:
                result["valid"] = False
                result["errors"].append(
                    f"Texture exceeds maximum resolution {max_res}: {width}x{height}"
                )

            if img.format != "PNG":
                result["warnings"].append(f"Non-PNG format: {img.format}")
                if agent.texture_constraints.get("must_be_png", False):
                    result["valid"] = False
                    result["errors"].append("Texture must be PNG format for Bedrock")

            if img.mode not in ["RGB", "RGBA"]:
                result["valid"] = False
                result["errors"].append(f"Unsupported color mode: {img.mode}")

    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Failed to validate texture: {str(e)}")

    return result


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
