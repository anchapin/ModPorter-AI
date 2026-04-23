"""
Weapon and Tool Converter for converting Java item systems to Bedrock format.

Converts Java item classes, tool types, weapons, armor, and their attributes
to Bedrock's item components system including damage, durability, enchantments,
armor, and weapon components.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Bedrock tool types."""

    PICKAXE = "pickaxe"
    AXE = "axe"
    SHOVEL = "shovel"
    HOE = "hoe"
    SWORD = "sword"
    BOW = "bow"
    CROSSBOW = "crossbow"
    TRIDENT = "trident"
    SHIELD = "shield"
    HELMET = "helmet"
    CHESTPLATE = "chestplate"
    LEGGINGS = "leggings"
    BOOTS = "boots"


class ArmorType(Enum):
    """Bedrock armor types."""

    HELMET = "helmet"
    CHESTPLATE = "chestplate"
    LEGGINGS = "leggings"
    BOOTS = "boots"


class ItemTier(Enum):
    """Java item tier levels."""

    WOOD = "wood"
    STONE = "stone"
    IRON = "iron"
    GOLD = "gold"
    DIAMOND = "diamond"
    NETHERITE = "netherite"


# Java to Bedrock tool mapping
JAVA_TO_BEDROCK_TOOL = {
    "wooden_pickaxe": "wooden_pickaxe",
    "stone_pickaxe": "stone_pickaxe",
    "iron_pickaxe": "iron_pickaxe",
    "diamond_pickaxe": "diamond_pickaxe",
    "netherite_pickaxe": "netherite_pickaxe",
    "wooden_axe": "wooden_axe",
    "stone_axe": "stone_axe",
    "iron_axe": "iron_axe",
    "diamond_axe": "diamond_axe",
    "netherite_axe": "netherite_axe",
    "wooden_shovel": "wooden_shovel",
    "stone_shovel": "stone_shovel",
    "iron_shovel": "iron_shovel",
    "diamond_shovel": "diamond_shovel",
    "netherite_shovel": "netherite_shovel",
    "wooden_hoe": "wooden_hoe",
    "stone_hoe": "stone_hoe",
    "iron_hoe": "iron_hoe",
    "diamond_hoe": "diamond_hoe",
    "netherite_hoe": "netherite_hoe",
    "wooden_sword": "wooden_sword",
    "stone_sword": "stone_sword",
    "iron_sword": "iron_sword",
    "diamond_sword": "diamond_sword",
    "netherite_sword": "netherite_sword",
    "bow": "bow",
    "crossbow": "crossbow",
    "trident": "trident",
    "shield": "shield",
}

# Java to Bedrock armor mapping
JAVA_TO_BEDROCK_ARMOR = {
    "leather_helmet": "leather_helmet",
    "leather_chestplate": "leather_chestplate",
    "leather_leggings": "leather_leggings",
    "leather_boots": "leather_boots",
    "chainmail_helmet": "chainmail_helmet",
    "chainmail_chestplate": "chainmail_chestplate",
    "chainmail_leggings": "chainmail_leggings",
    "chainmail_boots": "chainmail_boots",
    "iron_helmet": "iron_helmet",
    "iron_chestplate": "iron_chestplate",
    "iron_leggings": "iron_leggings",
    "iron_boots": "iron_boots",
    "diamond_helmet": "diamond_helmet",
    "diamond_chestplate": "diamond_chestplate",
    "diamond_leggings": "diamond_leggings",
    "diamond_boots": "diamond_boots",
    "netherite_helmet": "netherite_helmet",
    "netherite_chestplate": "netherite_chestplate",
    "netherite_leggings": "netherite_leggings",
    "netherite_boots": "netherite_boots",
}

# Tier damage values
TIER_DAMAGE = {
    "wood": 2,
    "stone": 3,
    "iron": 4,
    "gold": 4,
    "diamond": 5,
    "netherite": 6,
}

# Tier durability values
TIER_DURABILITY = {
    "wood": 59,
    "stone": 131,
    "iron": 250,
    "gold": 32,
    "diamond": 1561,
    "netherite": 2031,
}

# Tier mining speeds
TIER_MINING_SPEED = {
    "wood": 2.0,
    "stone": 4.0,
    "iron": 6.0,
    "gold": 12.0,
    "diamond": 8.0,
    "netherite": 9.0,
}

# Tier attack speeds
TIER_ATTACK_SPEED = {
    "wood": 0.8,
    "stone": 0.8,
    "iron": 0.8,
    "gold": 0.8,
    "diamond": 0.8,
    "netherite": 0.8,
    "sword": 1.4,
    "bow": 1.0,
    "crossbow": 1.25,
}


@dataclass
class ItemDefinition:
    """Represents a Bedrock item definition."""

    item_id: str
    item_name: str
    components: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolDefinition:
    """Represents a Bedrock tool definition."""

    tool_type: ToolType
    tier: ItemTier
    damage: int
    max_durability: int
    mining_speed: float = 2.0


@dataclass
class WeaponDefinition:
    """Represents a Bedrock weapon definition."""

    weapon_type: ToolType
    damage: int
    attack_speed: float
    damage_type: str = "entity"


@dataclass
class ArmorDefinition:
    """Represents a Bedrock armor definition."""

    armor_type: ArmorType
    tier: ItemTier
    armor_points: int
    toughness: int
    max_durability: int


class WeaponToolConverter:
    """
    Converter for Java items, tools, weapons, and armor to Bedrock format.

    Handles conversion of Java Item classes, ItemTier, ItemStack with ItemProperty,
    and Armor materials to Bedrock's item components system.
    """

    def __init__(self):
        """Initialize the WeaponToolConverter."""
        self.tool_map = JAVA_TO_BEDROCK_TOOL.copy()
        self.armor_map = JAVA_TO_BEDROCK_ARMOR.copy()
        self.attribute_converter = ToolAttributeConverter()

    def convert_item(self, java_item: Dict[str, Any]) -> ItemDefinition:
        """
        Convert Java item to Bedrock item definition.

        Args:
            java_item: Java item dictionary containing item type and properties

        Returns:
            ItemDefinition object
        """
        item_id = java_item.get("itemId", "minecraft:stick")
        item_name = java_item.get("name", "item.name")
        item_type = java_item.get("type", "generic")

        components = {}

        # Handle damage
        if "damage" in java_item:
            components["minecraft:damage"] = java_item["damage"]

        # Handle durability
        if "durability" in java_item or "maxDamage" in java_item:
            max_damage = java_item.get("maxDamage", java_item.get("durability", 100))
            components["minecraft:durability"] = {"max_durability": max_damage}

        # Handle enchantments
        if "enchantments" in java_item or "enchantmentLevels" in java_item:
            components["minecraft:enchantments"] = self.convert_enchantments(
                java_item.get("enchantments", java_item.get("enchantmentLevels", {}))
            )

        # Handle tool type
        if "toolType" in java_item or "type" in java_item:
            tool_type_str = java_item.get("toolType", java_item.get("type", "generic"))
            tool_type = self._parse_tool_type(tool_type_str)

            if tool_type:
                components.update(self._get_tool_components(tool_type, java_item))

        return ItemDefinition(
            item_id=item_id,
            item_name=item_name,
            components=components,
        )

    def convert_tool(self, java_tool: Dict[str, Any]) -> ToolDefinition:
        """
        Convert Java tool to Bedrock tool definition.

        Args:
            java_tool: Java tool dictionary containing tool properties

        Returns:
            ToolDefinition object
        """
        tool_name = java_tool.get("name", "wooden_pickaxe").lower()
        tier = self._extract_tier(tool_name)

        # Determine damage from tier
        damage = TIER_DAMAGE.get(tier.value, 2)

        # Get durability
        max_durability = TIER_DURABILITY.get(tier.value, 59)

        # Get mining speed
        mining_speed = TIER_MINING_SPEED.get(tier.value, 2.0)

        # Determine tool type
        tool_type = self._determine_tool_type(tool_name)

        return ToolDefinition(
            tool_type=tool_type,
            tier=tier,
            damage=damage,
            max_durability=max_durability,
            mining_speed=mining_speed,
        )

    def convert_weapon(self, java_weapon: Dict[str, Any]) -> WeaponDefinition:
        """
        Convert Java weapon to Bedrock weapon component.

        Args:
            java_weapon: Java weapon dictionary

        Returns:
            WeaponDefinition object
        """
        weapon_name = java_weapon.get("name", "wooden_sword").lower()

        # Determine damage from tier
        tier = self._extract_tier(weapon_name)
        damage = TIER_DAMAGE.get(tier.value, 4)

        # Override for swords
        if "sword" in weapon_name:
            damage = TIER_DAMAGE.get(tier.value, 4)
            damage += 3  # Base sword damage

        # Get attack speed - check crossbow before bow since crossbow contains "bow"
        if "crossbow" in weapon_name:
            attack_speed = TIER_ATTACK_SPEED["crossbow"]
        elif "bow" in weapon_name:
            attack_speed = TIER_ATTACK_SPEED["bow"]
        else:
            attack_speed = TIER_ATTACK_SPEED.get(tier.value, 1.4)

        # Determine weapon type
        weapon_type = self._determine_tool_type(weapon_name)

        damage_type = "entity"  # Default damage type

        return WeaponDefinition(
            weapon_type=weapon_type,
            damage=damage,
            attack_speed=attack_speed,
            damage_type=damage_type,
        )

    def convert_armor(self, java_armor: Dict[str, Any]) -> ArmorDefinition:
        """
        Convert Java armor to Bedrock armor component.

        Args:
            java_armor: Java armor dictionary

        Returns:
            ArmorDefinition object
        """
        armor_name = java_armor.get("name", "iron_helmet").lower()
        tier = self._extract_tier(armor_name)

        # Determine armor type and points
        armor_type = self._determine_armor_type(armor_name)
        armor_points = self._get_armor_points(armor_type, tier)

        # Get toughness
        toughness = self.convert_toughness(tier)

        # Get durability
        max_durability = self._get_armor_durability(armor_type, tier)

        return ArmorDefinition(
            armor_type=armor_type,
            tier=tier,
            armor_points=armor_points,
            toughness=toughness,
            max_durability=max_durability,
        )

    def convert_damage(self, java_damage: int) -> Dict[str, Any]:
        """
        Convert damage value to Bedrock damage component.

        Args:
            java_damage: Java damage value

        Returns:
            Bedrock damage component
        """
        return {"value": java_damage}

    def convert_durability(self, java_durability: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert durability to Bedrock durability component.

        Args:
            java_durability: Java durability dictionary

        Returns:
            Bedrock durability component
        """
        max_durability = java_durability.get("maxDamage", 100)
        current_damage = java_durability.get("damage", 0)

        return {
            "max_durability": max_durability,
            "damage_chance": java_durability.get("damageChance", -1),
        }

    def convert_enchantments(self, java_enchantments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert enchantments to Bedrock enchantments component.

        Args:
            java_enchantments: Java enchantments dictionary

        Returns:
            Bedrock enchantments component
        """
        # Map Java enchantment IDs to Bedrock
        enchantment_map = {
            "mending": "mending",
            "unbreaking": "unbreaking",
            "efficiency": "silktouch",
            "silk_touch": "silktouch",
            "fortune": "fortune",
            "looting": "looting",
            "sharpness": "sharpness",
            "smite": "smite",
            "bane_of_arthropods": "bane_of_arthropods",
            "knockback": "knockback",
            "fire_aspect": "fire_aspect",
            "sweeping_edge": "sweeping",
            "power": "power",
            "punch": "punch",
            "flame": "flame",
            "infinity": "infinity",
            "thorns": "thorns",
            "protection": "protection",
            "fire_protection": "fire_protection",
            "blast_protection": "blast_protection",
            "projectile_protection": "projectile_protection",
            "respiration": "respiration",
            "depth_strider": "depth_strider",
            "frost_walker": "frost_walker",
            "soul_speed": "soul_speed",
            "channeling": "channeling",
            "riptide": "riptide",
            "loyalty": "loyalty",
            "impaling": "impaling",
        }

        converted = {}
        for enchant, level in java_enchantments.items():
            bedrock_enchant = enchantment_map.get(enchant.lower(), enchant.lower())
            converted[bedrock_enchant] = level

        return {"stored_enchantments": converted}

    def convert_toughness(self, tier: ItemTier) -> int:
        """
        Convert armor tier to Bedrock toughness value.

        Args:
            tier: ItemTier enum

        Returns:
            Armor toughness value
        """
        toughness_map = {
            ItemTier.WOOD: 0,
            ItemTier.STONE: 0,
            ItemTier.IRON: 0,
            ItemTier.GOLD: 0,
            ItemTier.DIAMOND: 8,
            ItemTier.NETHERITE: 10,
        }
        return toughness_map.get(tier, 0)

    def _parse_tool_type(self, tool_type_str: str) -> Optional[ToolType]:
        """Parse tool type string to ToolType enum."""
        tool_type_lower = tool_type_str.lower()

        try:
            return ToolType(tool_type_lower)
        except ValueError:
            return None

    def _determine_tool_type(self, tool_name: str) -> ToolType:
        """Determine tool type from tool name."""
        if "pickaxe" in tool_name:
            return ToolType.PICKAXE
        elif "axe" in tool_name:
            return ToolType.AXE
        elif "shovel" in tool_name:
            return ToolType.SHOVEL
        elif "hoe" in tool_name:
            return ToolType.HOE
        elif "sword" in tool_name:
            return ToolType.SWORD
        elif tool_name == "bow":
            return ToolType.BOW
        elif tool_name == "crossbow":
            return ToolType.CROSSBOW
        elif tool_name == "trident":
            return ToolType.TRIDENT
        elif tool_name == "shield":
            return ToolType.SHIELD
        else:
            return ToolType.PICKAXE  # Default

    def _determine_armor_type(self, armor_name: str) -> ArmorType:
        """Determine armor type from armor name."""
        if "helmet" in armor_name or "helem" in armor_name:
            return ArmorType.HELMET
        elif "chestplate" in armor_name or "plate" in armor_name:
            return ArmorType.CHESTPLATE
        elif "leggings" in armor_name or "leggins" in armor_name:
            return ArmorType.LEGGINGS
        elif "boots" in armor_name:
            return ArmorType.BOOTS
        else:
            return ArmorType.CHESTPLATE  # Default

    def _extract_tier(self, tool_name: str) -> ItemTier:
        """Extract tier from tool name."""
        if "netherite" in tool_name:
            return ItemTier.NETHERITE
        elif "diamond" in tool_name:
            return ItemTier.DIAMOND
        elif "iron" in tool_name:
            return ItemTier.IRON
        elif "stone" in tool_name:
            return ItemTier.STONE
        elif "gold" in tool_name:
            return ItemTier.GOLD
        else:
            return ItemTier.WOOD

    def _get_armor_points(self, armor_type: ArmorType, tier: ItemTier) -> int:
        """Get armor points for armor type and tier."""
        base_points = {
            ArmorType.HELMET: 2,
            ArmorType.CHESTPLATE: 6,
            ArmorType.LEGGINGS: 5,
            ArmorType.BOOTS: 2,
        }

        tier_multiplier = {
            ItemTier.WOOD: 1,
            ItemTier.STONE: 1,
            ItemTier.IRON: 2,
            ItemTier.GOLD: 2,
            ItemTier.DIAMOND: 3,
            ItemTier.NETHERITE: 3,
        }

        base = base_points.get(armor_type, 1)
        multiplier = tier_multiplier.get(tier, 1)
        return base * multiplier

    def _get_armor_durability(self, armor_type: ArmorType, tier: ItemTier) -> int:
        """Get armor durability for armor type and tier."""
        base_durability = {
            ArmorType.HELMET: 11,
            ArmorType.CHESTPLATE: 16,
            ArmorType.LEGGINGS: 15,
            ArmorType.BOOTS: 13,
        }

        tier_multiplier = {
            ItemTier.WOOD: 1,
            ItemTier.STONE: 1,
            ItemTier.IRON: 2,
            ItemTier.GOLD: 2,
            ItemTier.DIAMOND: 3,
            ItemTier.NETHERITE: 4,
        }

        base = base_durability.get(armor_type, 10)
        multiplier = tier_multiplier.get(tier, 1)
        return base * multiplier

    def _get_tool_components(
        self, tool_type: ToolType, java_item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get tool-specific components."""
        components = {}

        # Add mining speed
        tier = self._extract_tier(java_item.get("name", ""))
        if tier:
            mining_speed = TIER_MINING_SPEED.get(tier.value, 2.0)
            components["minecraft:mining_speed"] = {"speed": mining_speed}

        return components

    def generate_item_json(self, item: ItemDefinition) -> Dict[str, Any]:
        """
        Generate Bedrock item JSON file.

        Args:
            item: ItemDefinition object

        Returns:
            Bedrock item JSON structure
        """
        item_json = {
            "format_version": "1.16.0",
            "minecraft:item": {
                "description": {
                    "identifier": item.item_id,
                },
                "components": item.components,
            },
        }

        return item_json

    def generate_tool_json(self, tool: ToolDefinition) -> Dict[str, Any]:
        """Generate tool definition JSON."""
        return {
            "format_version": "1.16.0",
            "minecraft:item": {
                "description": {
                    "identifier": f"minecraft:{tool.tool_type.value}",
                },
                "components": {
                    "minecraft:damage": tool.damage,
                    "minecraft:durability": {"max_durability": tool.max_durability},
                    "minecraft:mining_speed": {"speed": tool.mining_speed},
                },
            },
        }

    def generate_weapon_json(self, weapon: WeaponDefinition) -> Dict[str, Any]:
        """Generate weapon definition JSON."""
        return {
            "format_version": "1.16.0",
            "minecraft:item": {
                "description": {
                    "identifier": f"minecraft:{weapon.weapon_type.value}",
                },
                "components": {
                    "minecraft:damage": weapon.damage,
                    "minecraft:attack_speed": weapon.attack_speed,
                },
            },
        }

    def generate_armor_json(self, armor: ArmorDefinition) -> Dict[str, Any]:
        """Generate armor definition JSON."""
        return {
            "format_version": "1.16.0",
            "minecraft:item": {
                "description": {
                    "identifier": f"minecraft:{armor.armor_type.value}",
                },
                "components": {
                    "minecraft:armor": {"value": armor.armor_points},
                    "minecraft:armor_toughness": {"toughness": armor.toughness},
                    "minecraft:durability": {"max_durability": armor.max_durability},
                },
            },
        }


class ToolAttributeConverter:
    """
    Converter for custom tool attributes from Java to Bedrock format.

    Handles ItemTier mapping, mining speed, enchantability, attribute modifiers,
    and other custom tool attributes.
    """

    def __init__(self):
        """Initialize the ToolAttributeConverter."""
        self.tier_map = self._build_tier_map()

    def _build_tier_map(self) -> Dict[str, Dict[str, Any]]:
        """Build tier mapping dictionary."""
        return {
            "wood": {
                "tier": ItemTier.WOOD,
                "uses": 59,
                "speed": 2.0,
                "damage": 2,
                "enchantability": 15,
            },
            "stone": {
                "tier": ItemTier.STONE,
                "uses": 131,
                "speed": 4.0,
                "damage": 3,
                "enchantability": 5,
            },
            "iron": {
                "tier": ItemTier.IRON,
                "uses": 250,
                "speed": 6.0,
                "damage": 4,
                "enchantability": 14,
            },
            "gold": {
                "tier": ItemTier.GOLD,
                "uses": 32,
                "speed": 12.0,
                "damage": 4,
                "enchantability": 22,
            },
            "diamond": {
                "tier": ItemTier.DIAMOND,
                "uses": 1561,
                "speed": 8.0,
                "damage": 5,
                "enchantability": 10,
            },
            "netherite": {
                "tier": ItemTier.NETHERITE,
                "uses": 2031,
                "speed": 9.0,
                "damage": 6,
                "enchantability": 15,
            },
        }

    def convert_custom_attributes(self, java_attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert custom Java attributes to Bedrock item components.

        Args:
            java_attrs: Java attributes dictionary

        Returns:
            Bedrock item components dictionary
        """
        components = {}

        # Convert mining speed
        if "miningSpeed" in java_attrs or "speed" in java_attrs:
            mining_speed = java_attrs.get("miningSpeed", java_attrs.get("speed", 2.0))
            components["minecraft:mining_speed"] = {"speed": mining_speed}

        # Convert enchantability
        if "enchantability" in java_attrs or "enchant" in java_attrs:
            enchantability = java_attrs.get("enchantability", java_attrs.get("enchant", 10))
            components["minecraft:enchantable"] = {"value": enchantability}

        # Convert custom damage
        if "damage" in java_attrs:
            components["minecraft:damage"] = {"value": java_attrs["damage"]}

        # Convert durability
        if "maxDamage" in java_attrs:
            components["minecraft:durability"] = {"max_durability": java_attrs["maxDamage"]}

        # Convert attack speed
        if "attackSpeed" in java_attrs:
            components["minecraft:attack_speed"] = {"speed": java_attrs["attackSpeed"]}

        return components

    def convert_mining_speed(self, tier: str) -> float:
        """
        Convert mining speed for a tier.

        Args:
            tier: Tier name (wood, stone, iron, diamond, netherite)

        Returns:
            Mining speed value
        """
        tier_data = self.tier_map.get(tier.lower(), self.tier_map["wood"])
        return tier_data["speed"]

    def convert_enchantability(self, tier: str) -> int:
        """
        Convert enchantability for a tier.

        Args:
            tier: Tier name

        Returns:
            Enchantability value
        """
        tier_data = self.tier_map.get(tier.lower(), self.tier_map["wood"])
        return tier_data["enchantability"]

    def map_tier_to_bedrock(self, java_tier: str) -> Dict[str, Any]:
        """
        Map Java ItemTier to Bedrock tier definition.

        Args:
            java_tier: Java tier string

        Returns:
            Bedrock tier definition
        """
        tier_lower = java_tier.lower()
        if "netherite" in tier_lower:
            return self.tier_map["netherite"]
        elif "diamond" in tier_lower:
            return self.tier_map["diamond"]
        elif "iron" in tier_lower:
            return self.tier_map["iron"]
        elif "gold" in tier_lower or "golden" in tier_lower:
            return self.tier_map["gold"]
        elif "stone" in tier_lower:
            return self.tier_map["stone"]
        else:
            return self.tier_map["wood"]

    def convert_uses(self, tier: str) -> int:
        """
        Convert uses/durability for a tier.

        Args:
            tier: Tier name

        Returns:
            Max damage value
        """
        tier_data = self.tier_map.get(tier.lower(), self.tier_map["wood"])
        return tier_data["uses"]

    def convert_speed(self, tier: str) -> float:
        """
        Convert attack speed for a tier.

        Args:
            tier: Tier name

        Returns:
            Attack speed value
        """
        tier_data = self.tier_map.get(tier.lower(), self.tier_map["wood"])
        return tier_data["speed"]

    def convert_attribute_modifiers(self, modifiers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert Java attribute modifiers to Bedrock format.

        Args:
            modifiers: List of attribute modifier dictionaries

        Returns:
            List of converted attribute modifiers
        """
        converted = []

        for mod in modifiers:
            converted_mod = {
                "name": mod.get("name", "modifier"),
                "attribute": mod.get("attribute", "minecraft:attack_damage"),
                "operation": mod.get("operation", "add"),
                "amount": mod.get("amount", 0),
            }

            # Add UUID if present
            if "uuid" in mod:
                converted_mod["uuid"] = mod["uuid"]

            converted.append(converted_mod)

        return converted

    def convert_knockback(self, knockback_strength: int) -> Dict[str, Any]:
        """
        Convert knockback to Bedrock knockback resistance.

        Args:
            knockback_strength: Knockback strength value

        Returns:
            Knockback resistance component
        """
        return {"minecraft:knockback_resistance": {"value": min(knockback_strength / 10.0, 1.0)}}


# Convenience functions
def convert_item(java_item: Dict[str, Any]) -> ItemDefinition:
    """Convert Java item to Bedrock item definition."""
    converter = WeaponToolConverter()
    return converter.convert_item(java_item)


def convert_tool(java_tool: Dict[str, Any]) -> ToolDefinition:
    """Convert Java tool to Bedrock tool definition."""
    converter = WeaponToolConverter()
    return converter.convert_tool(java_tool)


def convert_weapon(java_weapon: Dict[str, Any]) -> WeaponDefinition:
    """Convert Java weapon to Bedrock weapon definition."""
    converter = WeaponToolConverter()
    return converter.convert_weapon(java_weapon)


def convert_armor(java_armor: Dict[str, Any]) -> ArmorDefinition:
    """Convert Java armor to Bedrock armor definition."""
    converter = WeaponToolConverter()
    return converter.convert_armor(java_armor)


def generate_item_file(java_item: Dict[str, Any]) -> Dict[str, Any]:
    """Generate complete Bedrock item JSON file."""
    converter = WeaponToolConverter()
    item = converter.convert_item(java_item)
    return converter.generate_item_json(item)


def generate_tool_file(java_tool: Dict[str, Any]) -> Dict[str, Any]:
    """Generate complete Bedrock tool JSON file."""
    converter = WeaponToolConverter()
    tool = converter.convert_tool(java_tool)
    return converter.generate_tool_json(tool)


def generate_weapon_file(java_weapon: Dict[str, Any]) -> Dict[str, Any]:
    """Generate complete Bedrock weapon JSON file."""
    converter = WeaponToolConverter()
    weapon = converter.convert_weapon(java_weapon)
    return converter.generate_weapon_json(weapon)


def generate_armor_file(java_armor: Dict[str, Any]) -> Dict[str, Any]:
    """Generate complete Bedrock armor JSON file."""
    converter = WeaponToolConverter()
    armor = converter.convert_armor(java_armor)
    return converter.generate_armor_json(armor)
