"""
Tag resolver for Forge tag to Bedrock ID resolution.

Provides FORGE_TAG_MAPPINGS for translating Forge tags to Bedrock item IDs,
and loads Java to Bedrock item ID mappings from bundled JSON.
"""

import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def _load_forge_tags() -> Dict[str, str]:
    """Load Forge tag to Bedrock item ID mappings from the bundled JSON file.

    Returns:
        Dictionary mapping Forge tags to Bedrock item IDs

    The mappings are loaded from data/forge_tag_mappings.json.
    """
    try:
        data_dir = Path(__file__).parent.parent.parent / "data"
        mappings_file = data_dir / "forge_tag_mappings.json"

        if not mappings_file.exists():
            logger.warning(
                f"Forge tag mappings file not found at {mappings_file}. Falling back to empty mappings."
            )
            return {}

        with open(mappings_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        mappings = data.get("mappings", {})
        metadata = data.get("metadata", {})
        logger.info(
            f"Loaded {len(mappings)} Forge tag mappings from {mappings_file} "
            f"(tag_count: {metadata.get('tag_count', 'unknown')})"
        )
        return mappings

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing Forge tag mappings JSON: {e}. Falling back to empty mappings.")
        return {}
    except Exception as e:
        logger.error(f"Error loading Forge tag mappings: {e}. Falling back to empty mappings.")
        return {}


def _load_item_mappings() -> Dict[str, str]:
    """Load Java to Bedrock item ID mappings from the bundled JSON file.

    Returns:
        Dictionary mapping Java item IDs to Bedrock item IDs

    The mappings are loaded from data/item_mappings.json which is generated
    by scripts/generate_item_mappings.py using minecraft-data.
    """
    try:
        data_dir = Path(__file__).parent.parent.parent / "data"
        mappings_file = data_dir / "item_mappings.json"

        if not mappings_file.exists():
            logger.warning(
                f"Item mappings file not found at {mappings_file}. Falling back to empty mappings."
            )
            return {}

        with open(mappings_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        mappings = data.get("mappings", {})
        metadata = data.get("metadata", {})
        logger.info(
            f"Loaded {len(mappings)} item mappings from {mappings_file} "
            f"(version: {metadata.get('version', 'unknown')})"
        )
        return mappings

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing item mappings JSON: {e}. Falling back to empty mappings.")
        return {}
    except Exception as e:
        logger.error(f"Error loading item mappings: {e}. Falling back to empty mappings.")
        return {}


JAVA_TO_BEDROCK_ITEM_MAP = _load_item_mappings()


FORGE_TAG_MAPPINGS = _load_forge_tags()


__all__ = [
    "FORGE_TAG_MAPPINGS",
    "JAVA_TO_BEDROCK_ITEM_MAP",
    "_load_item_mappings",
    "_load_forge_tags",
]