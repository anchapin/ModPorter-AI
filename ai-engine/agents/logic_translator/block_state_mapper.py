"""
Block property and state mapping for Java to Bedrock conversion.

Contains JAVA_TO_BEDROCK_BLOCK_PROPERTIES and JAVA_BLOCK_METHOD_MAPPINGS.
"""

from typing import Dict, Any

JAVA_TO_BEDROCK_BLOCK_PROPERTIES = {
    "Material.METAL": {"template": "metal", "destroy_time": 5.0, "explosion_resistance": 6.0},
    "Material.STONE": {"template": "stone", "destroy_time": 3.0, "explosion_resistance": 6.0},
    "Material.WOOD": {
        "template": "wood",
        "destroy_time": 2.0,
        "explosion_resistance": 3.0,
        "flammable": True,
    },
    "Material.GLASS": {"template": "glass", "destroy_time": 0.3, "explosion_resistance": 0.3},
    "Material.EARTH": {"template": "basic", "destroy_time": 0.5, "explosion_resistance": 0.5},
    "Material.GRASS": {"template": "basic", "destroy_time": 0.6, "explosion_resistance": 0.6},
    "Material.SAND": {"template": "basic", "destroy_time": 0.5, "explosion_resistance": 0.5},
    "Material.CLOTH": {
        "template": "basic",
        "destroy_time": 0.8,
        "explosion_resistance": 0.8,
        "flammable": True,
    },
    "Material.ICE": {"template": "glass", "destroy_time": 0.5, "explosion_resistance": 0.5},
    "Material.AIR": {"template": "basic", "destroy_time": 0.0, "explosion_resistance": 0.0},
    "SoundType.METAL": {"sound_category": "metal"},
    "SoundType.STONE": {"sound_category": "stone"},
    "SoundType.WOOD": {"sound_category": "wood"},
    "SoundType.GLASS": {"sound_category": "glass"},
    "SoundType.SAND": {"sound_category": "sand"},
    "SoundType.GRAVEL": {"sound_category": "gravel"},
    "SoundType.GRASS": {"sound_category": "grass"},
    "ToolType.PICKAXE": {"requires_tool": "pickaxe", "tool_tier": "stone"},
    "ToolType.AXE": {"requires_tool": "axe", "tool_tier": "wood"},
    "ToolType.SHOVEL": {"requires_tool": "shovel", "tool_tier": "wood"},
    "ToolType.HOE": {"requires_tool": "hoe", "tool_tier": "wood"},
}

JAVA_BLOCK_METHOD_MAPPINGS = {
    "strength": "minecraft:destroy_time",
    "hardness": "minecraft:destroy_time",
    "resistance": "minecraft:explosion_resistance",
    "lightLevel": "minecraft:light_emission",
    "lightValue": "minecraft:light_emission",
    "luminance": "minecraft:light_emission",
    "sound": "minecraft:block_sound",
    "friction": "minecraft:friction",
    "slipperiness": "minecraft:friction",
}


class BlockStateMapper:
    """Maps Java block properties/states to Bedrock equivalents."""

    def __init__(self):
        self.block_props = JAVA_TO_BEDROCK_BLOCK_PROPERTIES
        self.method_mappings = JAVA_BLOCK_METHOD_MAPPINGS

    def get_bedrock_component(self, java_method: str) -> str:
        """Map a Java block method to a Bedrock component identifier."""
        return self.method_mappings.get(java_method, "")

    def get_material_properties(self, material_key: str) -> Dict[str, Any]:
        """Get Bedrock block properties for a Java material type."""
        return self.block_props.get(material_key, {})

    def map_property_value(self, java_method: str, java_value: Any) -> tuple[str, Any]:
        """Map a Java block property value to Bedrock component and value."""
        component = self.get_bedrock_component(java_method)
        if not component:
            return "", java_value
        return component, java_value


__all__ = [
    "JAVA_TO_BEDROCK_BLOCK_PROPERTIES",
    "JAVA_BLOCK_METHOD_MAPPINGS",
    "BlockStateMapper",
]
