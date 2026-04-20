"""
Fallback texture generation module.
"""

import logging
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


def _generate_fallback_texture(
    self, usage: str = "block", size: Tuple[int, int] = (16, 16)
) -> Image.Image:
    """Generate a fallback texture for edge cases"""
    colors = {
        "block": (128, 128, 128, 255),
        "item": (200, 200, 100, 255),
        "entity": (150, 100, 100, 255),
        "particle": (200, 200, 255, 255),
        "ui": (100, 200, 100, 255),
        "other": (128, 128, 128, 255),
    }

    color = colors.get(usage, colors["other"])
    img = Image.new("RGBA", size, color)

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

        img = agent._generate_fallback_texture(texture_type)

        if texture_type == "blocks":
            img = img.resize((16, 16), Image.LANCZOS)
        else:
            img = img.resize((16, 16), Image.LANCZOS)

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
