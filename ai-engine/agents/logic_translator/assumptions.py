"""
Smart assumptions for untranslatable Java features.

Documents fallback behavior when Java features cannot be directly
translated to Bedrock equivalents.
"""

import json
from typing import Dict, Any

SMART_ASSUMPTIONS: Dict[str, Dict[str, str]] = {
    "item_custom_model_data": {
        "description": "Custom model data cannot be directly translated from Java",
        "assumption": "Using default model rendering",
        "fallback": "texture_name mapping",
        "note": "Custom models require separate resource pack work",
    },
    "item_nbt_tags": {
        "description": "NBT tags are handled differently in Bedrock",
        "assumption": "Basic item properties only",
        "fallback": "component-based properties",
        "note": "Advanced NBT requires script-based handling",
    },
    "item_enchantments": {
        "description": "Enchantments have different ID systems",
        "assumption": "Standard Bedrock enchantments only",
        "fallback": "Enchantability from repair material",
        "note": "Custom enchantments need behavior pack",
    },
    "entity_custom_ai": {
        "description": "Complex AI goals don't map 1:1 to Bedrock",
        "assumption": "Using nearest target + melee attack behaviors",
        "fallback": "Basic pathfinding + random stroll",
        "note": "Advanced AI requires behavior pack scripts",
    },
    "entity_pathfinding": {
        "description": "Java pathfindgoals differ from Bedrock navigation",
        "assumption": "Using standard navigation components",
        "fallback": "Basic walk/fly navigation",
        "note": "Complex pathfinding needs custom navigation",
    },
    "recipe_conditions": {
        "description": "Recipe conditions (player level, weather) not supported",
        "assumption": "Basic recipe only",
        "fallback": "Standard recipe tags",
        "note": "Conditional recipes need custom crafting table",
    },
    "block_tile_entities": {
        "description": "Tile entities (furnaces, hoppers) are complex",
        "assumption": "Basic block only",
        "fallback": "Container blocks available in vanilla",
        "note": "Complex tile entities need custom implementation",
    },
    "block_entity_triggers": {
        "description": "Block state change triggers differ",
        "assumption": "Event-based interaction only",
        "fallback": "onPlayerInteract + custom commands",
        "note": "Complex triggers need behavior scripts",
    },
}


def get_smart_assumptions() -> str:
    """Get documented smart assumptions for untranslatable features."""
    return json.dumps({"success": True, "assumptions": SMART_ASSUMPTIONS}, indent=2)


__all__ = [
    "SMART_ASSUMPTIONS",
    "get_smart_assumptions",
]
