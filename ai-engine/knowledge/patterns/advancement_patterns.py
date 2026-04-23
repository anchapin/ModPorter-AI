"""
Advancement Pattern Library for RAG-based advancement conversion.

Provides pattern matching and retrieval for Java to Bedrock advancement
conversion including criteria, rewards, and requirements.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class AdvancementPatternCategory(Enum):
    """Advancement pattern categories."""

    INVENTORY = "inventory"
    EXPLORATION = "exploration"
    COMBAT = "combat"
    BREWING = "brewing"
    FARMING = "farming"
    MINING = "mining"
    CRAFTING = "crafting"
    ENCHANTING = "enchanting"
    NETHER = "nether"
    END = "end"


@dataclass
class AdvancementPattern:
    """
    Represents a single advancement conversion pattern.

    Contains Java criteria class reference and corresponding Bedrock
    requirement with conversion notes and metadata.
    """

    java_criteria_class: str
    bedrock_requirement: str
    category: AdvancementPatternCategory
    conversion_notes: str
    rarity: int = 1  # 1-100, how common

    def to_dict(self) -> Dict:
        """Convert pattern to dictionary."""
        return {
            "java_criteria_class": self.java_criteria_class,
            "bedrock_requirement": self.bedrock_requirement,
            "category": self.category.value,
            "conversion_notes": self.conversion_notes,
            "rarity": self.rarity,
        }


class AdvancementPatternLibrary:
    """
    Library of advancement conversion patterns.

    Provides storage, retrieval, and search functionality for
    Java→Bedrock advancement pattern conversion.
    """

    def __init__(self):
        """Initialize pattern library with default patterns."""
        self.patterns: List[AdvancementPattern] = []
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default advancement patterns (25+ patterns)."""

        # Inventory patterns (5 patterns)
        inventory_patterns = [
            AdvancementPattern(
                java_criteria_class="mine_stone",
                bedrock_requirement="minecraft:inventory_changed",
                category=AdvancementPatternCategory.INVENTORY,
                conversion_notes="Mine stone → inventory_changed with stone item",
                rarity=90,
            ),
            AdvancementPattern(
                java_criteria_class="craft_planks",
                bedrock_requirement="minecraft:inventory_changed",
                category=AdvancementPatternCategory.INVENTORY,
                conversion_notes="Craft planks → inventory_changed with planks item",
                rarity=95,
            ),
            AdvancementPattern(
                java_criteria_class="build_sword",
                bedrock_requirement="minecraft:inventory_changed",
                category=AdvancementPatternCategory.INVENTORY,
                conversion_notes="Build sword → inventory_changed with sword item",
                rarity=85,
            ),
            AdvancementPattern(
                java_criteria_class="build_pickaxe",
                bedrock_requirement="minecraft:inventory_changed",
                category=AdvancementPatternCategory.INVENTORY,
                conversion_notes="Build pickaxe → inventory_changed with pickaxe item",
                rarity=85,
            ),
            AdvancementPattern(
                java_criteria_class="acquire_iron",
                bedrock_requirement="minecraft:inventory_changed",
                category=AdvancementPatternCategory.INVENTORY,
                conversion_notes="Acquire iron → inventory_changed with iron ingot",
                rarity=80,
            ),
        ]

        # Exploration patterns (5 patterns)
        exploration_patterns = [
            AdvancementPattern(
                java_criteria_class="enter_nether",
                bedrock_requirement="minecraft:location",
                category=AdvancementPatternCategory.EXPLORATION,
                conversion_notes="Enter nether → location in nether dimension",
                rarity=75,
            ),
            AdvancementPattern(
                java_criteria_class="find_treasure",
                bedrock_requirement="minecraft:location",
                category=AdvancementPatternCategory.EXPLORATION,
                conversion_notes="Find treasure → location check for treasure biome",
                rarity=65,
            ),
            AdvancementPattern(
                java_criteria_class="exploring",
                bedrock_requirement="minecraft:tick",
                category=AdvancementPatternCategory.EXPLORATION,
                conversion_notes="Exploring → tick with biome tracking",
                rarity=70,
            ),
            AdvancementPattern(
                java_criteria_class="farlands",
                bedrock_requirement="minecraft:location",
                category=AdvancementPatternCategory.EXPLORATION,
                conversion_notes="Reach farlands → location in farlands biome",
                rarity=30,
            ),
            AdvancementPattern(
                java_criteria_class="mount_hoglin",
                bedrock_requirement="minecraft:interacted_with_entity",
                category=AdvancementPatternCategory.EXPLORATION,
                conversion_notes="Mount hoglin → interacted_with_entity with hoglin",
                rarity=60,
            ),
        ]

        # Combat patterns (5 patterns)
        combat_patterns = [
            AdvancementPattern(
                java_criteria_class="kill_mob",
                bedrock_requirement="minecraft:player_killed_entity",
                category=AdvancementPatternCategory.COMBAT,
                conversion_notes="Kill mob → player_killed_entity",
                rarity=85,
            ),
            AdvancementPattern(
                java_criteria_class="raid_win",
                bedrock_requirement="minecraft:player_killed_entity",
                category=AdvancementPatternCategory.COMBAT,
                conversion_notes="Win raid → player_killed_entity with raid victory",
                rarity=50,
            ),
            AdvancementPattern(
                java_criteria_class="totem",
                bedrock_requirement="minecraft:death",
                category=AdvancementPatternCategory.COMBAT,
                conversion_notes="Totem → death with totem in inventory",
                rarity=70,
            ),
            AdvancementPattern(
                java_criteria_class="kill_elder_guardian",
                bedrock_requirement="minecraft:player_killed_entity",
                category=AdvancementPatternCategory.COMBAT,
                conversion_notes="Kill elder guardian → player_killed_entity with guardian",
                rarity=55,
            ),
            AdvancementPattern(
                java_criteria_class="win_betrayal",
                bedrock_requirement="minecraft:player_killed_entity",
                category=AdvancementPatternCategory.COMBAT,
                conversion_notes="Win betrayal → player_killed_entity with wither",
                rarity=45,
            ),
        ]

        # Brewing patterns (4 patterns)
        brewing_patterns = [
            AdvancementPattern(
                java_criteria_class="brew_potion",
                bedrock_requirement="minecraft:consume_item",
                category=AdvancementPatternCategory.BREWING,
                conversion_notes="Brew potion → consume_item in brewing stand",
                rarity=80,
            ),
            AdvancementPattern(
                java_criteria_class="all_potions",
                bedrock_requirement="minecraft:inventory_changed",
                category=AdvancementPatternCategory.BREWING,
                conversion_notes="All potions → inventory_changed with all potion types",
                rarity=40,
            ),
            AdvancementPattern(
                java_criteria_class="brew_splash",
                bedrock_requirement="minecraft:consume_item",
                category=AdvancementPatternCategory.BREWING,
                conversion_notes="Brew splash → consume_item with splash potion",
                rarity=70,
            ),
            AdvancementPattern(
                java_criteria_class="brew_lingering",
                bedrock_requirement="minecraft:consume_item",
                category=AdvancementPatternCategory.BREWING,
                conversion_notes="Brew lingering → consume_item with lingering potion",
                rarity=60,
            ),
        ]

        # Mining patterns (3 patterns)
        mining_patterns = [
            AdvancementPattern(
                java_criteria_class="mine_diamond",
                bedrock_requirement="minecraft:inventory_changed",
                category=AdvancementPatternCategory.MINING,
                conversion_notes="Mine diamond → inventory_changed with diamond",
                rarity=70,
            ),
            AdvancementPattern(
                java_criteria_class="mine_emerald",
                bedrock_requirement="minecraft:inventory_changed",
                category=AdvancementPatternCategory.MINING,
                conversion_notes="Mine emerald → inventory_changed with emerald",
                rarity=55,
            ),
            AdvancementPattern(
                java_criteria_class="mine_coal",
                bedrock_requirement="minecraft:inventory_changed",
                category=AdvancementPatternCategory.MINING,
                conversion_notes="Mine coal → inventory_changed with coal",
                rarity=90,
            ),
        ]

        # Farming patterns (3 patterns)
        farming_patterns = [
            AdvancementPattern(
                java_criteria_class="harvest_crops",
                bedrock_requirement="minecraft:inventory_changed",
                category=AdvancementPatternCategory.FARMING,
                conversion_notes="Harvest crops → inventory_changed with crops",
                rarity=85,
            ),
            AdvancementPattern(
                java_criteria_class="breed_animals",
                bedrock_requirement="minecraft:interacted_with_entity",
                category=AdvancementPatternCategory.FARMING,
                conversion_notes="Breed animals → interacted_with_entity for breeding",
                rarity=80,
            ),
            AdvancementPattern(
                java_criteria_class="tame_animal",
                bedrock_requirement="minecraft:interacted_with_entity",
                category=AdvancementPatternCategory.FARMING,
                conversion_notes="Tame animal → interacted_with_entity with tame result",
                rarity=75,
            ),
        ]

        # Add all patterns
        self.patterns.extend(inventory_patterns)
        self.patterns.extend(exploration_patterns)
        self.patterns.extend(combat_patterns)
        self.patterns.extend(brewing_patterns)
        self.patterns.extend(mining_patterns)
        self.patterns.extend(farming_patterns)

    def search_by_java(self, java_class: str) -> List[AdvancementPattern]:
        """
        Search patterns by Java criteria class.

        Args:
            java_class: Java criteria class to search for

        Returns:
            List of matching AdvancementPattern objects
        """
        results = []
        java_class_lower = java_class.lower()

        for pattern in self.patterns:
            # Check for partial match
            if java_class_lower in pattern.java_criteria_class.lower():
                results.append(pattern)
            # Check for exact match
            elif java_class_lower == pattern.java_criteria_class.lower():
                # Prioritize exact matches
                results.insert(0, results.pop(results.index(pattern)))

        return results

    def get_by_category(self, category: AdvancementPatternCategory) -> List[AdvancementPattern]:
        """
        Get all patterns in a category.

        Args:
            category: AdvancementPatternCategory to filter by

        Returns:
            List of patterns in the category
        """
        return [p for p in self.patterns if p.category == category]

    def get_pattern_by_java_class(self, java_class: str) -> Optional[AdvancementPattern]:
        """
        Get exact pattern by Java criteria class.

        Args:
            java_class: Java criteria class

        Returns:
            AdvancementPattern if found, None otherwise
        """
        for pattern in self.patterns:
            if pattern.java_criteria_class.lower() == java_class.lower():
                return pattern
        return None

    def add_pattern(self, pattern: AdvancementPattern) -> None:
        """
        Add a new pattern to the library.

        Args:
            pattern: AdvancementPattern to add
        """
        # Check for duplicate
        for existing in self.patterns:
            if existing.java_criteria_class == pattern.java_criteria_class:
                # Update existing
                existing.bedrock_requirement = pattern.bedrock_requirement
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
ADVANCEMENT_PATTERNS = AdvancementPatternLibrary()


def get_advancement_pattern(java_class: str) -> Optional[AdvancementPattern]:
    """
    Get an advancement pattern by Java class.

    Args:
        java_class: Java criteria class

    Returns:
        AdvancementPattern if found, None otherwise
    """
    return ADVANCEMENT_PATTERNS.get_pattern_by_java_class(java_class)


def search_advancement_patterns(query: str) -> List[AdvancementPattern]:
    """
    Search advancement patterns by Java class.

    Args:
        query: Search query

    Returns:
        List of matching patterns
    """
    return ADVANCEMENT_PATTERNS.search_by_java(query)


def get_patterns_by_category(category: AdvancementPatternCategory) -> List[AdvancementPattern]:
    """
    Get all patterns in a category.

    Args:
        category: Category to filter by

    Returns:
        List of patterns
    """
    return ADVANCEMENT_PATTERNS.get_by_category(category)


def get_advancement_stats() -> Dict[str, int]:
    """
    Get advancement pattern library statistics.

    Returns:
        Statistics dictionary
    """
    return ADVANCEMENT_PATTERNS.get_stats()
