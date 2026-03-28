"""
Villager Pattern Library for RAG-based villager/profession conversion.

Provides pattern matching and retrieval for Java to Bedrock villager
professions, careers, and trade conversion patterns.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class VillagerPatternCategory(Enum):
    """Villager pattern categories."""

    AGRICULTURE = "agriculture"
    COMBAT = "combat"
    COMMERCE = "commerce"
    KNOWLEDGE = "knowledge"
    CRAFTING = "crafting"
    SERVICE = "service"


@dataclass
class VillagerPattern:
    """
    Represents a single villager conversion pattern.

    Contains Java profession/career class reference and corresponding Bedrock
    profession identifier with conversion notes and category.
    """

    java_profession_class: str
    bedrock_profession_id: str
    category: VillagerPatternCategory
    conversion_notes: str
    default_trades: List[str] = None
    career_aliases: List[str] = None


class VillagerPatternLibrary:
    """
    Library of villager conversion patterns.

    Provides storage, retrieval, and search functionality for
    Java→Bedrock villager profession and career pattern conversion.
    """

    def __init__(self):
        """Initialize pattern library with default patterns."""
        self.patterns: List[VillagerPattern] = []
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default villager patterns (20+ patterns)."""

        # Agriculture category - 5 patterns
        agriculture_patterns = [
            VillagerPattern(
                java_profession_class="farmer",
                bedrock_profession_id="farmer",
                category=VillagerPatternCategory.AGRICULTURE,
                conversion_notes="Farmer profession - trades crops, food items, and bone meal",
                default_trades=["emerald", "wheat", "bread", "carrot", "potato"],
                career_aliases=["harvester", "agriculturist"],
            ),
            VillagerPattern(
                java_profession_class="fisherman",
                bedrock_profession_id="fisherman",
                category=VillagerPatternCategory.AGRICULTURE,
                conversion_notes="Fisherman profession - trades fish, boats, and fishing rods",
                default_trades=["emerald", "cod", "salmon", "tropical_fish", "fishing_rod"],
                career_aliases=["fisher", "angler"],
            ),
            VillagerPattern(
                java_profession_class="shepherd",
                bedrock_profession_id="shepherd",
                category=VillagerPatternCategory.AGRICULTURE,
                conversion_notes="Shepherd profession - trades wool, carpets, and beds",
                default_trades=["emerald", "wool", "carpet", "bed", "mutton"],
                career_aliases=["wool_worker", "textile"],
            ),
            VillagerPattern(
                java_profession_class="butcher",
                bedrock_profession_id="butcher",
                category=VillagerPatternCategory.AGRICULTURE,
                conversion_notes="Butcher profession - trades raw/cooked meat and rabbit hide",
                default_trades=["emerald", "porkchop", "beef", "rabbit", "cooked_meat"],
                career_aliases=["meat_trader", "provender"],
            ),
            VillagerPattern(
                java_profession_class="gardener",
                bedrock_profession_id="farmer",
                category=VillagerPatternCategory.AGRICULTURE,
                conversion_notes="Gardener - maps to farmer in Bedrock",
                default_trades=["emerald", "sweet_berries", "glow_berries"],
                career_aliases=["horticulturist", "vegetable_farmer"],
            ),
        ]

        # Combat category - 4 patterns
        combat_patterns = [
            VillagerPattern(
                java_profession_class="armorer",
                bedrock_profession_id="armorer",
                category=VillagerPatternCategory.COMBAT,
                conversion_notes="Armorer profession - trades iron/diamond/netherite armor",
                default_trades=["emerald", "iron_helmet", "diamond_chestplate", "chainmail"],
                career_aliases=["armor_smelt", "metalworker"],
            ),
            VillagerPattern(
                java_profession_class="weaponsmith",
                bedrock_profession_id="weaponsmith",
                category=VillagerPatternCategory.COMBAT,
                conversion_notes="Weaponsmith profession - trades swords, axes, and bells",
                default_trades=["emerald", "iron_sword", "diamond_axe", "bell"],
                career_aliases=["weapon_smelt", "bladesmith"],
            ),
            VillagerPattern(
                java_profession_class="toolsmith",
                bedrock_profession_id="toolsmith",
                category=VillagerPatternCategory.COMBAT,
                conversion_notes="Toolsmith profession - trades tools and weapons",
                default_trades=["emerald", "iron_pickaxe", "iron_shovel", "iron_axe"],
                career_aliases=["tool_smelt", "smith"],
            ),
            VillagerPattern(
                java_profession_class="hunter",
                bedrock_profession_id="farmer",
                category=VillagerPatternCategory.COMBAT,
                conversion_notes="Hunter - maps to farmer in Bedrock",
                default_trades=["emerald", "rabbit_hide", "rabbit_foot", "arrow"],
                career_aliases=["tracker", "hunter_trader"],
            ),
        ]

        # Commerce category - 3 patterns
        commerce_patterns = [
            VillagerPattern(
                java_profession_class="cartographer",
                bedrock_profession_id="cartographer",
                category=VillagerPatternCategory.COMMERCE,
                conversion_notes="Cartographer profession - trades maps, banners, and compasses",
                default_trades=["emerald", "map", "banner_pattern", "compass", "paper"],
                career_aliases=["map_maker", "explorer"],
            ),
            VillagerPattern(
                java_profession_class="merchant",
                bedrock_profession_id="unemployed",
                category=VillagerPatternCategory.COMMERCE,
                conversion_notes="Generic merchant - starts unemployed until assigned profession",
                default_trades=["emerald", "trades_vary"],
                career_aliases=["trader", "peddler"],
            ),
            VillagerPattern(
                java_profession_class="wandering_trader",
                bedrock_profession_id="none",
                category=VillagerPatternCategory.COMMERCE,
                conversion_notes="Wandering trader - special entity, not a standard profession",
                default_trades=["emerald", "various"],
                career_aliases=["nomad_trader", "traveling_merchant"],
            ),
        ]

        # Knowledge category - 3 patterns
        knowledge_patterns = [
            VillagerPattern(
                java_profession_class="librarian",
                bedrock_profession_id="librarian",
                category=VillagerPatternCategory.KNOWLEDGE,
                conversion_notes="Librarian profession - trades books, bookshelves, and enchanted books",
                default_trades=["emerald", "book", "bookshelf", "enchanted_book", "compass"],
                career_aliases=["book_seller", "scholar"],
            ),
            VillagerPattern(
                java_profession_class="cleric",
                bedrock_profession_id="cleric",
                category=VillagerPatternCategory.KNOWLEDGE,
                conversion_notes="Cleric profession - trades redstone, lapis, and brewing items",
                default_trades=["emerald", "redstone", "lapis_lazuli", "rabbit_foot", "poppy"],
                career_aliases=["priest", "alchemist"],
            ),
            VillagerPattern(
                java_profession_class="scholar",
                bedrock_profession_id="librarian",
                category=VillagerPatternCategory.KNOWLEDGE,
                conversion_notes="Scholar - maps to librarian in Bedrock",
                default_trades=["emerald", "paper", "map", "name_tag"],
                career_aliases=["academic", "researcher"],
            ),
        ]

        # Crafting category - 3 patterns
        crafting_patterns = [
            VillagerPattern(
                java_profession_class="leatherworker",
                bedrock_profession_id="leatherworker",
                category=VillagerPatternCategory.CRAFTING,
                conversion_notes="Leatherworker profession - trades leather items and horse armor",
                default_trades=["emerald", "leather", "leather_chestplate", "horse_armor"],
                career_aliases=["tanner", "harness_maker"],
            ),
            VillagerPattern(
                java_profession_class="mason",
                bedrock_profession_id="mason",
                category=VillagerPatternCategory.CRAFTING,
                conversion_notes="Mason profession - trades stone bricks, stairs, and walls",
                default_trades=["emerald", "stone_bricks", "stairs", "walls", "polished_andesite"],
                career_aliases=["stone_mason", "bricklayer"],
            ),
            VillagerPattern(
                java_profession_class=" Fletcher",
                bedrock_profession_id="fletcher",
                category=VillagerPatternCategory.CRAFTING,
                conversion_notes="Fletcher profession - trades arrows, bows, and crossbows",
                default_trades=["emerald", "arrow", "bow", "crossbow", "flint"],
                career_aliases=["arrow_maker", "archer_supplier"],
            ),
        ]

        # Service category - 2 patterns
        service_patterns = [
            VillagerPattern(
                java_profession_class="nitwit",
                bedrock_profession_id="nitwit",
                category=VillagerPatternCategory.SERVICE,
                conversion_notes="Nitwit profession - no trades, only idle villager behavior",
                default_trades=[],
                career_aliases=["unemployable", "idler"],
            ),
            VillagerPattern(
                java_profession_class="unemployed",
                bedrock_profession_id="unemployed",
                category=VillagerPatternCategory.SERVICE,
                conversion_notes="Unemployed - no profession, can be assigned a career",
                default_trades=[],
                career_aliases=["jobless", "seeking_work"],
            ),
        ]

        # Add all patterns
        self.patterns.extend(agriculture_patterns)
        self.patterns.extend(combat_patterns)
        self.patterns.extend(commerce_patterns)
        self.patterns.extend(knowledge_patterns)
        self.patterns.extend(crafting_patterns)
        self.patterns.extend(service_patterns)

    def search_by_java(self, java_class: str) -> List[VillagerPattern]:
        """
        Search patterns by Java profession class.

        Args:
            java_class: Java profession class to search for

        Returns:
            List of matching VillagerPattern objects
        """
        results = []
        java_class_lower = java_class.lower()

        for pattern in self.patterns:
            # Check primary class
            if java_class_lower in pattern.java_profession_class.lower():
                results.append(pattern)
            # Check aliases
            if pattern.career_aliases:
                for alias in pattern.career_aliases:
                    if java_class_lower in alias.lower():
                        if pattern not in results:
                            results.append(pattern)

        # Prioritize exact matches
        exact_matches = [p for p in results if p.java_profession_class.lower() == java_class_lower]
        for match in exact_matches:
            results.remove(match)
            results.insert(0, match)

        return results

    def get_by_category(self, category: VillagerPatternCategory) -> List[VillagerPattern]:
        """
        Get all patterns in a category.

        Args:
            category: VillagerPatternCategory to filter by

        Returns:
            List of patterns in the category
        """
        return [p for p in self.patterns if p.category == category]

    def get_pattern_by_java_class(self, java_class: str) -> Optional[VillagerPattern]:
        """
        Get exact pattern by Java profession class.

        Args:
            java_class: Java profession class

        Returns:
            VillagerPattern if found, None otherwise
        """
        java_class_lower = java_class.lower()
        for pattern in self.patterns:
            if pattern.java_profession_class.lower() == java_class_lower:
                return pattern
            # Check aliases
            if pattern.career_aliases:
                for alias in pattern.career_aliases:
                    if alias.lower() == java_class_lower:
                        return pattern
        return None

    def add_pattern(self, pattern: VillagerPattern) -> None:
        """
        Add a new pattern to the library.

        Args:
            pattern: VillagerPattern to add
        """
        # Check for duplicate
        for existing in self.patterns:
            if existing.java_profession_class == pattern.java_profession_class:
                # Update existing
                existing.bedrock_profession_id = pattern.bedrock_profession_id
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
VILLAGER_PATTERNS = VillagerPatternLibrary()


def get_villager_pattern(java_class: str) -> Optional[VillagerPattern]:
    """
    Get a villager pattern by Java class.

    Args:
        java_class: Java profession class

    Returns:
        VillagerPattern if found, None otherwise
    """
    return VILLAGER_PATTERNS.get_pattern_by_java_class(java_class)


def search_villager_patterns(query: str) -> List[VillagerPattern]:
    """
    Search villager patterns by Java class.

    Args:
        query: Search query

    Returns:
        List of matching patterns
    """
    return VILLAGER_PATTERNS.search_by_java(query)


def get_patterns_by_category(category: VillagerPatternCategory) -> List[VillagerPattern]:
    """
    Get all patterns in a category.

    Args:
        category: Category to filter by

    Returns:
        List of patterns
    """
    return VILLAGER_PATTERNS.get_by_category(category)


def get_villager_stats() -> Dict[str, int]:
    """
    Get villager pattern library statistics.

    Returns:
        Statistics dictionary
    """
    return VILLAGER_PATTERNS.get_stats()
