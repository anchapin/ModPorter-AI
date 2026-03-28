"""
Weapon and Tool Pattern Library for RAG-based item conversion.

Provides pattern matching and retrieval for Java to Bedrock weapon, tool,
and armor conversion patterns.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class WeaponToolCategory(Enum):
    """Weapon/tool pattern categories."""

    MINING = "mining"
    COMBAT = "combat"
    ARMOR = "armor"
    BOW = "bow"
    TRIDENT = "trident"
    SHIELD = "shield"


@dataclass
class WeaponToolPattern:
    """
    Represents a single weapon/tool conversion pattern.

    Contains Java item class reference and corresponding Bedrock
    item identifier with conversion notes and category.
    """

    java_item_class: str
    bedrock_item_id: str
    category: WeaponToolCategory
    conversion_notes: str
    damage: Optional[int] = None
    durability: Optional[int] = None
    tier: Optional[str] = None


class WeaponToolPatternLibrary:
    """
    Library of weapon/tool conversion patterns.

    Provides storage, retrieval, and search functionality for
    Java→Bedrock item conversion patterns.
    """

    def __init__(self):
        """Initialize pattern library with default patterns."""
        self.patterns: List[WeaponToolPattern] = []
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default weapon/tool patterns (25+ patterns)."""

        # Mining tool patterns - 10 patterns
        mining_patterns = [
            WeaponToolPattern(
                java_item_class="WoodenPickaxe",
                bedrock_item_id="minecraft:wooden_pickaxe",
                category=WeaponToolCategory.MINING,
                conversion_notes="Wooden pickaxe - basic mining tool",
                damage=2,
                durability=59,
                tier="wood",
            ),
            WeaponToolPattern(
                java_item_class="StonePickaxe",
                bedrock_item_id="minecraft:stone_pickaxe",
                category=WeaponToolCategory.MINING,
                conversion_notes="Stone pickaxe - tier 2 mining tool",
                damage=3,
                durability=131,
                tier="stone",
            ),
            WeaponToolPattern(
                java_item_class="IronPickaxe",
                bedrock_item_id="minecraft:iron_pickaxe",
                category=WeaponToolCategory.MINING,
                conversion_notes="Iron pickaxe - tier 3 mining tool",
                damage=4,
                durability=250,
                tier="iron",
            ),
            WeaponToolPattern(
                java_item_class="DiamondPickaxe",
                bedrock_item_id="minecraft:diamond_pickaxe",
                category=WeaponToolCategory.MINING,
                conversion_notes="Diamond pickaxe - tier 4 mining tool",
                damage=5,
                durability=1561,
                tier="diamond",
            ),
            WeaponToolPattern(
                java_item_class="NetheritePickaxe",
                bedrock_item_id="minecraft:netherite_pickaxe",
                category=WeaponToolCategory.MINING,
                conversion_notes="Netherite pickaxe - tier 5 mining tool",
                damage=6,
                durability=2031,
                tier="netherite",
            ),
            WeaponToolPattern(
                java_item_class="WoodenAxe",
                bedrock_item_id="minecraft:wooden_axe",
                category=WeaponToolCategory.MINING,
                conversion_notes="Wooden axe - woodcutting tool",
                damage=3,
                durability=59,
                tier="wood",
            ),
            WeaponToolPattern(
                java_item_class="StoneAxe",
                bedrock_item_id="minecraft:stone_axe",
                category=WeaponToolCategory.MINING,
                conversion_notes="Stone axe - tier 2 woodcutting",
                damage=4,
                durability=131,
                tier="stone",
            ),
            WeaponToolPattern(
                java_item_class="IronAxe",
                bedrock_item_id="minecraft:iron_axe",
                category=WeaponToolCategory.MINING,
                conversion_notes="Iron axe - tier 3 woodcutting",
                damage=5,
                durability=250,
                tier="iron",
            ),
            WeaponToolPattern(
                java_item_class="DiamondAxe",
                bedrock_item_id="minecraft:diamond_axe",
                category=WeaponToolCategory.MINING,
                conversion_notes="Diamond axe - tier 4 woodcutting",
                damage=6,
                durability=1561,
                tier="diamond",
            ),
            WeaponToolPattern(
                java_item_class="NetheriteAxe",
                bedrock_item_id="minecraft:netherite_axe",
                category=WeaponToolCategory.MINING,
                conversion_notes="Netherite axe - tier 5 woodcutting",
                damage=7,
                durability=2031,
                tier="netherite",
            ),
        ]

        # Combat weapon patterns - 10 patterns
        combat_patterns = [
            WeaponToolPattern(
                java_item_class="WoodenSword",
                bedrock_item_id="minecraft:wooden_sword",
                category=WeaponToolCategory.COMBAT,
                conversion_notes="Wooden sword - basic melee weapon",
                damage=5,
                durability=59,
                tier="wood",
            ),
            WeaponToolPattern(
                java_item_class="StoneSword",
                bedrock_item_id="minecraft:stone_sword",
                category=WeaponToolCategory.COMBAT,
                conversion_notes="Stone sword - tier 2 melee weapon",
                damage=6,
                durability=131,
                tier="stone",
            ),
            WeaponToolPattern(
                java_item_class="IronSword",
                bedrock_item_id="minecraft:iron_sword",
                category=WeaponToolCategory.COMBAT,
                conversion_notes="Iron sword - tier 3 melee weapon",
                damage=7,
                durability=250,
                tier="iron",
            ),
            WeaponToolPattern(
                java_item_class="DiamondSword",
                bedrock_item_id="minecraft:diamond_sword",
                category=WeaponToolCategory.COMBAT,
                conversion_notes="Diamond sword - tier 4 melee weapon",
                damage=8,
                durability=1561,
                tier="diamond",
            ),
            WeaponToolPattern(
                java_item_class="NetheriteSword",
                bedrock_item_id="minecraft:netherite_sword",
                category=WeaponToolCategory.COMBAT,
                conversion_notes="Netherite sword - tier 5 melee weapon",
                damage=9,
                durability=2031,
                tier="netherite",
            ),
            WeaponToolPattern(
                java_item_class="Trident",
                bedrock_item_id="minecraft:trident",
                category=WeaponToolCategory.TRIDENT,
                conversion_notes="Trident - ranged thrown weapon",
                damage=9,
                durability=250,
                tier="iron",
            ),
            WeaponToolPattern(
                java_item_class="Shield",
                bedrock_item_id="minecraft:shield",
                category=WeaponToolCategory.SHIELD,
                conversion_notes="Shield - blocking equipment",
                damage=0,
                durability=336,
                tier="wood",
            ),
        ]

        # Armor patterns - 16 patterns (4 pieces x 4 materials)
        armor_patterns = [
            # Leather armor
            WeaponToolPattern(
                java_item_class="LeatherHelmet",
                bedrock_item_id="minecraft:leather_helmet",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Leather helmet - tier 1 head armor",
                durability=55,
                tier="leather",
            ),
            WeaponToolPattern(
                java_item_class="LeatherChestplate",
                bedrock_item_id="minecraft:leather_chestplate",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Leather chestplate - tier 1 body armor",
                durability=80,
                tier="leather",
            ),
            WeaponToolPattern(
                java_item_class="LeatherLeggings",
                bedrock_item_id="minecraft:leather_leggings",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Leather leggings - tier 1 leg armor",
                durability=75,
                tier="leather",
            ),
            WeaponToolPattern(
                java_item_class="LeatherBoots",
                bedrock_item_id="minecraft:leather_boots",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Leather boots - tier 1 foot armor",
                durability=65,
                tier="leather",
            ),
            # Chainmail armor
            WeaponToolPattern(
                java_item_class="ChainmailHelmet",
                bedrock_item_id="minecraft:chainmail_helmet",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Chainmail helmet - tier 2 head armor",
                durability=77,
                tier="chainmail",
            ),
            WeaponToolPattern(
                java_item_class="ChainmailChestplate",
                bedrock_item_id="minecraft:chainmail_chestplate",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Chainmail chestplate - tier 2 body armor",
                durability=112,
                tier="chainmail",
            ),
            WeaponToolPattern(
                java_item_class="ChainmailLeggings",
                bedrock_item_id="minecraft:chainmail_leggings",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Chainmail leggings - tier 2 leg armor",
                durability=105,
                tier="chainmail",
            ),
            WeaponToolPattern(
                java_item_class="ChainmailBoots",
                bedrock_item_id="minecraft:chainmail_boots",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Chainmail boots - tier 2 foot armor",
                durability=91,
                tier="chainmail",
            ),
            # Iron armor
            WeaponToolPattern(
                java_item_class="IronHelmet",
                bedrock_item_id="minecraft:iron_helmet",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Iron helmet - tier 3 head armor",
                durability=165,
                tier="iron",
            ),
            WeaponToolPattern(
                java_item_class="IronChestplate",
                bedrock_item_id="minecraft:iron_chestplate",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Iron chestplate - tier 3 body armor",
                durability=240,
                tier="iron",
            ),
            WeaponToolPattern(
                java_item_class="IronLeggings",
                bedrock_item_id="minecraft:iron_leggings",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Iron leggings - tier 3 leg armor",
                durability=225,
                tier="iron",
            ),
            WeaponToolPattern(
                java_item_class="IronBoots",
                bedrock_item_id="minecraft:iron_boots",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Iron boots - tier 3 foot armor",
                durability=195,
                tier="iron",
            ),
            # Diamond armor
            WeaponToolPattern(
                java_item_class="DiamondHelmet",
                bedrock_item_id="minecraft:diamond_helmet",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Diamond helmet - tier 4 head armor",
                durability=363,
                tier="diamond",
            ),
            WeaponToolPattern(
                java_item_class="DiamondChestplate",
                bedrock_item_id="minecraft:diamond_chestplate",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Diamond chestplate - tier 4 body armor",
                durability=528,
                tier="diamond",
            ),
            WeaponToolPattern(
                java_item_class="DiamondLeggings",
                bedrock_item_id="minecraft:diamond_leggings",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Diamond leggings - tier 4 leg armor",
                durability=495,
                tier="diamond",
            ),
            WeaponToolPattern(
                java_item_class="DiamondBoots",
                bedrock_item_id="minecraft:diamond_boots",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Diamond boots - tier 4 foot armor",
                durability=429,
                tier="diamond",
            ),
            # Netherite armor
            WeaponToolPattern(
                java_item_class="NetheriteHelmet",
                bedrock_item_id="minecraft:netherite_helmet",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Netherite helmet - tier 5 head armor",
                durability=407,
                tier="netherite",
            ),
            WeaponToolPattern(
                java_item_class="NetheriteChestplate",
                bedrock_item_id="minecraft:netherite_chestplate",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Netherite chestplate - tier 5 body armor",
                durability=592,
                tier="netherite",
            ),
            WeaponToolPattern(
                java_item_class="NetheriteLeggings",
                bedrock_item_id="minecraft:netherite_leggings",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Netherite leggings - tier 5 leg armor",
                durability=555,
                tier="netherite",
            ),
            WeaponToolPattern(
                java_item_class="NetheriteBoots",
                bedrock_item_id="minecraft:netherite_boots",
                category=WeaponToolCategory.ARMOR,
                conversion_notes="Netherite boots - tier 5 foot armor",
                durability=481,
                tier="netherite",
            ),
        ]

        # Add all patterns
        self.patterns.extend(mining_patterns)
        self.patterns.extend(combat_patterns)
        self.patterns.extend(armor_patterns)

    def search_by_java(self, java_class: str) -> List[WeaponToolPattern]:
        """
        Search patterns by Java item class.

        Args:
            java_class: Java item class to search for

        Returns:
            List of matching WeaponToolPattern objects
        """
        results = []
        java_class_lower = java_class.lower()

        for pattern in self.patterns:
            # Check primary class
            if java_class_lower in pattern.java_item_class.lower():
                results.append(pattern)

        # Prioritize exact matches
        exact_matches = [p for p in results if p.java_item_class.lower() == java_class_lower]
        for match in exact_matches:
            results.remove(match)
            results.insert(0, match)

        return results

    def get_by_category(self, category: WeaponToolCategory) -> List[WeaponToolPattern]:
        """
        Get all patterns in a category.

        Args:
            category: WeaponToolCategory to filter by

        Returns:
            List of patterns in the category
        """
        return [p for p in self.patterns if p.category == category]

    def get_pattern_by_java_class(self, java_class: str) -> Optional[WeaponToolPattern]:
        """
        Get exact pattern by Java item class.

        Args:
            java_class: Java item class

        Returns:
            WeaponToolPattern if found, None otherwise
        """
        java_class_lower = java_class.lower()
        for pattern in self.patterns:
            if pattern.java_item_class.lower() == java_class_lower:
                return pattern
        return None

    def add_pattern(self, pattern: WeaponToolPattern) -> None:
        """
        Add a new pattern to the library.

        Args:
            pattern: WeaponToolPattern to add
        """
        # Check for duplicate
        for existing in self.patterns:
            if existing.java_item_class == pattern.java_item_class:
                # Update existing
                existing.bedrock_item_id = pattern.bedrock_item_id
                existing.conversion_notes = pattern.conversion_notes
                return
        self.patterns.append(pattern)

    def get_stats(self) -> Dict[str, int]:
        """
        Get library statistics.

        Returns:
            Dictionary with pattern counts
        """
        stats = {
            "total": len(self.patterns),
            "by_category": {},
        }

        # Count by category
        for pattern in self.patterns:
            cat = pattern.category.value
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        return stats


# Global pattern instance for easy import
WEAPON_TOOL_PATTERNS = WeaponToolPatternLibrary()


def get_weapon_tool_pattern(java_class: str) -> Optional[WeaponToolPattern]:
    """
    Get a weapon/tool pattern by Java class.

    Args:
        java_class: Java item class

    Returns:
        WeaponToolPattern if found, None otherwise
    """
    return WEAPON_TOOL_PATTERNS.get_pattern_by_java_class(java_class)


def search_weapon_tool_patterns(query: str) -> List[WeaponToolPattern]:
    """
    Search weapon/tool patterns by Java class.

    Args:
        query: Search query

    Returns:
        List of matching patterns
    """
    return WEAPON_TOOL_PATTERNS.search_by_java(query)


def get_patterns_by_category(
    category: WeaponToolCategory,
) -> List[WeaponToolPattern]:
    """
    Get all patterns in a category.

    Args:
        category: Category to filter by

    Returns:
        List of patterns
    """
    return WEAPON_TOOL_PATTERNS.get_by_category(category)


def get_weapon_tool_stats() -> Dict[str, int]:
    """
    Get weapon/tool pattern library statistics.

    Returns:
        Statistics dictionary
    """
    return WEAPON_TOOL_PATTERNS.get_stats()
