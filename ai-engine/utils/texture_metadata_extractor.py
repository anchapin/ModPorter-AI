"""
Texture metadata extractor for PNG/JPG texture files.

This module provides functionality to extract metadata from Minecraft texture files
including dimensions, format, transparency detection, color palette extraction,
category classification, tileability detection, and animation frame analysis.
"""

import logging
import os
from typing import List, Optional

# Try to import PIL for image processing
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not installed. Texture metadata extraction will not be available.")

from schemas.multimodal_schema import ImageMetadata

logger = logging.getLogger(__name__)


class TextureMetadataExtractor:
    """
    Extracts metadata from texture files (PNG, JPG) for the multi-modal RAG system.

    Supports:
    - Dimension extraction (width, height)
    - Transparency detection (alpha channel presence)
    - Dominant color extraction (top 5 colors as hex palette)
    - Category classification (blocks, items, entities, gui, environment)
    - Tileability detection (edge matching analysis)
    - Animation frame count detection (for animated PNGs)
    - Visual complexity score calculation
    """

    # Minecraft texture category patterns
    # Note: Order matters! More specific or longer patterns should come first,
    # and categories that might be substrings of others should be handled carefully.
    CATEGORY_PATTERNS = {
        "gui": [
            "gui",
            "inventory",
            "icons",
            "widgets",
            "button",
            "menu",
            "container",
            "slot",
            "hotbar",
            "crafting",
            "ender_chest",
        ],
        "environment": [
            "environment",
            "sky",
            "sun",
            "moon",
            "star",
            "cloud",
            "fog",
            "particle",
            "effect",
            "font",
            "colormap",
        ],
        "entities": [
            "entity",
            "entities",
            "mob",
            "player",
            "slime",
            "creeper",
            "zombie",
            "skeleton",
            "spider",
            "ender",
            "dragon",
            "villager",
            "animal",
            "hostile",
            "passive",
            "boss",
        ],
        "blocks": [
            "block",
            "blocks",
            "stone",
            "dirt",
            "grass",
            "wood",
            "log",
            "leaves",
            "cobblestone",
            "sandstone",
            "brick",
            "planks",
            "wool",
            "concrete",
            "terracotta",
            "glass",
            "ice",
            "snow",
            "nether",
            "deepslate",
        ],
        "items": [
            "item",
            "items",
            "sword",
            "pickaxe",
            "axe",
            "shovel",
            "hoe",
            "food",
            "potion",
            "tool",
            "armor",
            "book",
            "paper",
            "bow",
            "fishing_rod",
            "carrot",
            "stick",
            "coal",
            "iron",
            "gold",
            "diamond",
        ],
    }

    def __init__(self):
        """Initialize the texture metadata extractor."""
        self.supported_formats = {"png", "jpg", "jpeg", "gif", "bmp"}

    def extract(self, file_path: str) -> Optional[ImageMetadata]:
        """
        Extract metadata from a texture file.

        Args:
            file_path: Path to the texture file

        Returns:
            Dictionary containing extracted metadata, or None if extraction failed
        """
        if not PIL_AVAILABLE:
            logger.error("PIL not available - cannot extract texture metadata")
            return None

        if not os.path.exists(file_path):
            logger.error(f"Texture file not found: {file_path}")
            return None

        try:
            with Image.open(file_path) as img:
                # Extract basic properties
                width, height = img.size
                channels = len(img.getbands())
                format_str = img.format or os.path.splitext(file_path)[1][1:].upper()
                file_size = os.path.getsize(file_path)

                # Detect transparency
                has_transparency = self._detect_transparency(img)

                # Extract color palette
                color_palette = self._extract_color_palette(img)

                # Classify category
                category = self._classify_category(file_path)

                # Detect tileability (only for large enough images)
                is_tileable = None
                if width >= 16 and height >= 16:
                    is_tileable = self._detect_tileability(img)

                # Detect animation frames
                animation_frames = self._detect_animation_frames(img)

                # Calculate complexity score
                complexity_score = self._calculate_complexity(img)

                # Add to image metadata - return as ImageMetadata model
                return ImageMetadata(
                    document_id="",  # Will be set by caller when stored
                    width=width,
                    height=height,
                    channels=channels,
                    format=format_str,
                    file_size_bytes=file_size,
                    has_transparency=has_transparency,
                    color_palette=color_palette,
                    texture_category=category,
                    is_tileable=is_tileable,
                    animation_frames=animation_frames,
                    complexity_score=complexity_score,
                )

        except Exception as e:
            logger.error(f"Failed to extract texture metadata from {file_path}: {e}")
            return None

    def _detect_transparency(self, img: Image.Image) -> bool:
        """
        Detect if the image has transparency.

        Args:
            img: PIL Image object

        Returns:
            True if image has transparency, False otherwise
        """
        if img.mode == "RGBA":
            # Check if there's any pixel with alpha < 255
            alpha_band = img.split()[3]
            # Convert to list and check minimum
            alpha_values = list(alpha_band.getdata())
            return min(alpha_values) < 255
        elif img.mode == "P":
            # Palette mode - check for transparency in palette
            if "transparency" in img.info:
                return True
        elif img.mode in ("LA", "PA"):
            # LA = Luminance + Alpha, PA = Palette + Alpha
            return True

        return False

    def _extract_color_palette(self, img: Image.Image, num_colors: int = 5) -> List[str]:
        """
        Extract dominant colors from the image as hex values.

        Args:
            img: PIL Image object
            num_colors: Number of dominant colors to extract

        Returns:
            List of hex color codes
        """
        try:
            # Reduce colors using quantization
            img_copy = img.copy()
            if img_copy.mode != "RGB":
                img_copy = img_copy.convert("RGB")

            # Use PIL's quantize method
            img_copy = img_copy.convert("P", palette=Image.ADAPTIVE, colors=num_colors)

            # Get the color palette
            palette = img_copy.getpalette()
            if not palette:
                return []

            # Extract the most common colors (first num_colors * 3 values)
            colors = []
            for i in range(num_colors):
                r = palette[i * 3]
                g = palette[i * 3 + 1]
                b = palette[i * 3 + 2]
                colors.append(f"#{r:02x}{g:02x}{b:02x}")

            return colors

        except Exception as e:
            logger.warning(f"Failed to extract color palette: {e}")
            return []

    def _classify_category(self, file_path: str) -> Optional[str]:
        """
        Classify the texture into a Minecraft category based on path.

        Args:
            file_path: Path to the texture file

        Returns:
            Category string (blocks, items, entities, gui, environment) or None
        """
        path_lower = file_path.lower()

        # Check each category pattern
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if pattern in path_lower:
                    return category

        # Default to blocks if we can't determine
        return "blocks"

    def _detect_tileability(self, img: Image.Image, edge_threshold: float = 0.1) -> bool:
        """
        Detect if the texture is tileable by comparing edge pixels.

        Args:
            img: PIL Image object
            edge_threshold: Maximum allowed difference ratio for tileability

        Returns:
            True if texture appears tileable, False otherwise
        """
        try:
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            width, height = img.size
            pixels = list(img.getdata())

            # Compare left edge with right edge
            left_edge = [pixels[i * width] for i in range(height)]
            right_edge = [pixels[(i + 1) * width - 1] for i in range(height)]

            # Compare top edge with bottom edge
            top_edge = pixels[:width]
            bottom_edge = pixels[width * (height - 1) : width * height]

            # Calculate differences
            left_right_diff = sum(
                abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
                for a, b in zip(left_edge, right_edge)
            ) / (height * 3 * 255)

            top_bottom_diff = sum(
                abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
                for a, b in zip(top_edge, bottom_edge)
            ) / (width * 3 * 255)

            avg_diff = (left_right_diff + top_bottom_diff) / 2

            return avg_diff < edge_threshold

        except Exception as e:
            logger.warning(f"Failed to detect tileability: {e}")
            return None

    def _detect_animation_frames(self, img: Image.Image) -> Optional[int]:
        """
        Detect the number of animation frames in an animated image.

        Args:
            img: PIL Image object

        Returns:
            Number of frames, or None if not animated
        """
        try:
            if hasattr(img, "n_frames"):
                n_frames = img.n_frames
                return n_frames if n_frames > 1 else None
            return None
        except Exception:
            return None

    def _calculate_complexity(self, img: Image.Image) -> float:
        """
        Calculate a visual complexity score based on color variance.

        Args:
            img: PIL Image object

        Returns:
            Complexity score between 0 and 1
        """
        try:
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Resize to small size for faster processing
            img_small = img.resize((32, 32), Image.Resampling.LANCZOS)
            pixels = list(img_small.getdata())

            # Calculate variance in each channel
            r_values = [p[0] for p in pixels]
            g_values = [p[1] for p in pixels]
            b_values = [p[2] for p in pixels]

            r_var = sum((r - sum(r_values) / len(r_values)) ** 2 for r in r_values) / len(r_values)
            g_var = sum((g - sum(g_values) / len(g_values)) ** 2 for g in g_values) / len(g_values)
            b_var = sum((b - sum(b_values) / len(b_values)) ** 2 for b in b_values) / len(b_values)

            # Normalize to 0-1 range (max variance for 8-bit is 16384)
            max_variance = 16384
            avg_variance = (r_var + g_var + b_var) / 3
            complexity = min(avg_variance / max_variance, 1.0)

            return round(complexity, 3)

        except Exception as e:
            logger.warning(f"Failed to calculate complexity: {e}")
            return None


def extract_texture_metadata(file_path: str) -> Optional[ImageMetadata]:
    """
    Convenience function to extract texture metadata.

    Args:
        file_path: Path to the texture file

    Returns:
        ImageMetadata instance containing extracted metadata, or None if extraction failed
    """
    extractor = TextureMetadataExtractor()
    return extractor.extract(file_path)
