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


FORGE_TAG_MAPPINGS = {
    "#forge:ingots/iron": "minecraft:iron_ingot",
    "#forge:ingots/gold": "minecraft:gold_ingot",
    "#forge:ingots/copper": "minecraft:copper_ingot",
    "#forge:ingots/netherite": "minecraft:netherite_ingot",
    "#forge:nuggets/iron": "minecraft:iron_nugget",
    "#forge:nuggets/gold": "minecraft:gold_nugget",
    "#forge:nuggets/copper": "minecraft:copper_nugget",
    "#forge:nuggets/tin": "minecraft:tin_nugget",
    "#forge:ores/iron": "minecraft:iron_ore",
    "#forge:ores/gold": "minecraft:gold_ore",
    "#forge:ores/copper": "minecraft:copper_ore",
    "#forge:ores/coal": "minecraft:coal_ore",
    "#forge:ores/diamond": "minecraft:diamond_ore",
    "#forge:ores/emerald": "minecraft:emerald_ore",
    "#forge:ores/lapis": "minecraft:lapis_ore",
    "#forge:ores/redstone": "minecraft:redstone_ore",
    "#forge:storage_blocks/iron": "minecraft:iron_block",
    "#forge:storage_blocks/gold": "minecraft:gold_block",
    "#forge:storage_blocks/copper": "minecraft:copper_block",
    "#forge:storage_blocks/diamond": "minecraft:diamond_block",
    "#forge:storage_blocks/netherite": "minecraft:netherite_block",
    "#forge:dusts/iron": "minecraft:iron_nugget",
    "#forge:dusts/gold": "minecraft:gold_nugget",
    "#forge:dusts/copper": "minecraft:copper_nugget",
    "#forge:gems/diamond": "minecraft:diamond",
    "#forge:gems/emerald": "minecraft:emerald",
    "#forge:gems/lapis": "minecraft:lapis_lazuli",
    "#forge:gems/quartz": "minecraft:quartz",
    "#forge:crops/wheat": "minecraft:wheat",
    "#forge:crops/carrot": "minecraft:carrot",
    "#forge:crops/potato": "minecraft:potato",
    "#forge:crops/beetroot": "minecraft:beetroot",
    "#forge:leather": "minecraft:leather",
    "#forge:paper": "minecraft:paper",
    "#forge:seeds/wheat": "minecraft:wheat_seeds",
    "#forge:seeds/pumpkin": "minecraft:pumpkin_seeds",
    "#forge:seeds/melon": "minecraft:melon_seeds",
    "#forge:seeds/rice": "minecraft:rice",
    "#forge:wood/oak": "minecraft:oak_log",
    "#forge:wood/spruce": "minecraft:spruce_log",
    "#forge:wood/birch": "minecraft:birch_log",
    "#forge:wood/jungle": "minecraft:jungle_log",
    "#forge:wood/acacia": "minecraft:acacia_log",
    "#forge:wood/dark_oak": "minecraft:dark_oak_log",
    "#forge:planks/oak": "minecraft:oak_planks",
    "#forge:planks/spruce": "minecraft:spruce_planks",
    "#forge:planks/birch": "minecraft:birch_planks",
    "#forge:planks/jungle": "minecraft:jungle_planks",
    "#forge:planks/acacia": "minecraft:acacia_planks",
    "#forge:planks/dark_oak": "minecraft:dark_oak_planks",
}


__all__ = [
    "FORGE_TAG_MAPPINGS",
    "JAVA_TO_BEDROCK_ITEM_MAP",
    "_load_item_mappings",
]