"""
Dimension Pattern Library for RAG-based world generation conversion.

Provides pattern matching and retrieval for Java to Bedrock world generation
including biomes, structures, features, and ore conversions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class WorldGenCategory(Enum):
    """World generation pattern categories."""

    BIOME = "biome"
    STRUCTURE = "structure"
    FEATURE = "feature"
    ORE = "ore"
    CARVER = "carver"
    DECORATOR = "decorator"
    CUSTOM = "custom"


@dataclass
class WorldGenPattern:
    """
    Represents a single world generation conversion pattern.

    Contains Java generator type reference and corresponding Bedrock feature
    with conversion notes and metadata.
    """

    java_generator_type: str
    bedrock_feature_id: str
    category: WorldGenCategory
    conversion_notes: str
    dimension: str = "overworld"  # Which dimension this applies to
    rarity: int = 1  # 1-100, how common

    def to_dict(self) -> Dict:
        """Convert pattern to dictionary."""
        return {
            "java_generator_type": self.java_generator_type,
            "bedrock_feature_id": self.bedrock_feature_id,
            "category": self.category.value,
            "conversion_notes": self.conversion_notes,
            "dimension": self.dimension,
            "rarity": self.rarity,
        }


class WorldGenPatternLibrary:
    """
    Library of world generation conversion patterns.

    Provides storage, retrieval, and search functionality for
    Java→Bedrock world generation pattern conversion.
    """

    def __init__(self):
        """Initialize pattern library with default patterns."""
        self.patterns: List[WorldGenPattern] = []
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default world generation patterns (30+ patterns)."""

        # Biome patterns (8 patterns)
        biome_patterns = [
            WorldGenPattern(
                java_generator_type="biome.plains",
                bedrock_feature_id="plains",
                category=WorldGenCategory.BIOME,
                conversion_notes="Java plains biome maps to Bedrock plains",
                dimension="overworld",
                rarity=20,
            ),
            WorldGenPattern(
                java_generator_type="biome.forest",
                bedrock_feature_id="forest",
                category=WorldGenCategory.BIOME,
                conversion_notes="Java forest biome maps to Bedrock forest",
                dimension="overworld",
                rarity=15,
            ),
            WorldGenPattern(
                java_generator_type="biome.desert",
                bedrock_feature_id="desert",
                category=WorldGenCategory.BIOME,
                conversion_notes="Java desert biome maps to Bedrock desert",
                dimension="overworld",
                rarity=12,
            ),
            WorldGenPattern(
                java_generator_type="biome.tundra",
                bedrock_feature_id="snowy_plains",
                category=WorldGenCategory.BIOME,
                conversion_notes="Java tundra biome maps to Bedrock snowy_plains",
                dimension="overworld",
                rarity=8,
            ),
            WorldGenPattern(
                java_generator_type="biome.jungle",
                bedrock_feature_id="jungle",
                category=WorldGenCategory.BIOME,
                conversion_notes="Java jungle biome maps to Bedrock jungle",
                dimension="overworld",
                rarity=6,
            ),
            WorldGenPattern(
                java_generator_type="biome.taiga",
                bedrock_feature_id="taiga",
                category=WorldGenCategory.BIOME,
                conversion_notes="Java taiga biome maps to Bedrock taiga",
                dimension="overworld",
                rarity=10,
            ),
            WorldGenPattern(
                java_generator_type="biome.savanna",
                bedrock_feature_id="savanna",
                category=WorldGenCategory.BIOME,
                conversion_notes="Java savanna biome maps to Bedrock savanna",
                dimension="overworld",
                rarity=8,
            ),
            WorldGenPattern(
                java_generator_type="biome.mushroom",
                bedrock_feature_id="mushroom_island",
                category=WorldGenCategory.BIOME,
                conversion_notes="Java mushroom biome maps to Bedrock mushroom_island",
                dimension="overworld",
                rarity=2,
            ),
        ]

        # Structure patterns (10 patterns)
        structure_patterns = [
            WorldGenPattern(
                java_generator_type="village",
                bedrock_feature_id="village",
                category=WorldGenCategory.STRUCTURE,
                conversion_notes="Java village maps to Bedrock village",
                dimension="overworld",
                rarity=30,
            ),
            WorldGenPattern(
                java_generator_type="ruins",
                bedrock_feature_id="ruined_portal",
                category=WorldGenCategory.STRUCTURE,
                conversion_notes="Java ruins map to Bedrock ruined_portal",
                dimension="overworld",
                rarity=20,
            ),
            WorldGenPattern(
                java_generator_type="desert_temple",
                bedrock_feature_id="desert_pyramid",
                category=WorldGenCategory.STRUCTURE,
                conversion_notes="Java desert temple maps to Bedrock desert_pyramid",
                dimension="overworld",
                rarity=15,
            ),
            WorldGenPattern(
                java_generator_type="jungle_temple",
                bedrock_feature_id="jungle_temple",
                category=WorldGenCategory.STRUCTURE,
                conversion_notes="Java jungle temple maps to Bedrock jungle_temple",
                dimension="overworld",
                rarity=15,
            ),
            WorldGenPattern(
                java_generator_type="mansion",
                bedrock_feature_id="mansion",
                category=WorldGenCategory.STRUCTURE,
                conversion_notes="Java woodland mansion maps to Bedrock mansion",
                dimension="overworld",
                rarity=5,
            ),
            WorldGenPattern(
                java_generator_type="pillager_outpost",
                bedrock_feature_id="pillager_outpost",
                category=WorldGenCategory.STRUCTURE,
                conversion_notes="Java pillager outpost maps to Bedrock pillager_outpost",
                dimension="overworld",
                rarity=25,
            ),
            WorldGenPattern(
                java_generator_type="mineshaft",
                bedrock_feature_id="mineshaft",
                category=WorldGenCategory.STRUCTURE,
                conversion_notes="Java mineshaft maps to Bedrock mineshaft",
                dimension="overworld",
                rarity=40,
            ),
            WorldGenPattern(
                java_generator_type="fortress",
                bedrock_feature_id="fortress",
                category=WorldGenCategory.STRUCTURE,
                conversion_notes="Java nether fortress maps to Bedrock fortress",
                dimension="nether",
                rarity=25,
            ),
            WorldGenPattern(
                java_generator_type="stronghold",
                bedrock_feature_id="stronghold",
                category=WorldGenCategory.STRUCTURE,
                conversion_notes="Java stronghold maps to Bedrock stronghold",
                dimension="overworld",
                rarity=3,
            ),
            WorldGenPattern(
                java_generator_type="end_city",
                bedrock_feature_id="end_city",
                category=WorldGenCategory.STRUCTURE,
                conversion_notes="Java end city maps to Bedrock end_city",
                dimension="the_end",
                rarity=10,
            ),
        ]

        # Feature patterns (8 patterns)
        feature_patterns = [
            WorldGenPattern(
                java_generator_type="ore_vein",
                bedrock_feature_id="ore",
                category=WorldGenCategory.FEATURE,
                conversion_notes="Java ore vein maps to Bedrock ore feature",
                dimension="overworld",
                rarity=50,
            ),
            WorldGenPattern(
                java_generator_type="cave_carver",
                bedrock_feature_id="cave",
                category=WorldGenCategory.CARVER,
                conversion_notes="Java cave carver maps to Bedrock cave",
                dimension="overworld",
                rarity=80,
            ),
            WorldGenPattern(
                java_generator_type="tree",
                bedrock_feature_id="tree",
                category=WorldGenCategory.FEATURE,
                conversion_notes="Java tree feature maps to Bedrock tree",
                dimension="overworld",
                rarity=60,
            ),
            WorldGenPattern(
                java_generator_type="flower",
                bedrock_feature_id="flower",
                category=WorldGenCategory.FEATURE,
                conversion_notes="Java flower feature maps to Bedrock flower",
                dimension="overworld",
                rarity=40,
            ),
            WorldGenPattern(
                java_generator_type="grass",
                bedrock_feature_id="grass",
                category=WorldGenCategory.FEATURE,
                conversion_notes="Java grass feature maps to Bedrock grass",
                dimension="overworld",
                rarity=50,
            ),
            WorldGenPattern(
                java_generator_type="water_lake",
                bedrock_feature_id="water_lake",
                category=WorldGenCategory.FEATURE,
                conversion_notes="Java water lake maps to Bedrock water_lake",
                dimension="overworld",
                rarity=20,
            ),
            WorldGenPattern(
                java_generator_type="lava_lake",
                bedrock_feature_id="lava_lake",
                category=WorldGenCategory.FEATURE,
                conversion_notes="Java lava lake maps to Bedrock lava_lake in nether",
                dimension="nether",
                rarity=15,
            ),
            WorldGenPattern(
                java_generator_type="ravine",
                bedrock_feature_id="ravine",
                category=WorldGenCategory.CARVER,
                conversion_notes="Java ravine maps to Bedrock ravine",
                dimension="overworld",
                rarity=30,
            ),
        ]

        # Ore patterns (7 patterns)
        ore_patterns = [
            WorldGenPattern(
                java_generator_type="ore_coal",
                bedrock_feature_id="ore_coal",
                category=WorldGenCategory.ORE,
                conversion_notes="Java coal ore maps to Bedrock coal ore",
                dimension="overworld",
                rarity=60,
            ),
            WorldGenPattern(
                java_generator_type="ore_iron",
                bedrock_feature_id="ore_iron",
                category=WorldGenCategory.ORE,
                conversion_notes="Java iron ore maps to Bedrock iron ore",
                dimension="overworld",
                rarity=40,
            ),
            WorldGenPattern(
                java_generator_type="ore_gold",
                bedrock_feature_id="ore_gold",
                category=WorldGenCategory.ORE,
                conversion_notes="Java gold ore maps to Bedrock gold ore",
                dimension="overworld",
                rarity=20,
            ),
            WorldGenPattern(
                java_generator_type="ore_diamond",
                bedrock_feature_id="ore_diamond",
                category=WorldGenCategory.ORE,
                conversion_notes="Java diamond ore maps to Bedrock diamond ore",
                dimension="overworld",
                rarity=10,
            ),
            WorldGenPattern(
                java_generator_type="ore_emerald",
                bedrock_feature_id="ore_emerald",
                category=WorldGenCategory.ORE,
                conversion_notes="Java emerald ore maps to Bedrock emerald ore in extreme hills",
                dimension="overworld",
                rarity=5,
            ),
            WorldGenPattern(
                java_generator_type="ore_copper",
                bedrock_feature_id="ore_copper",
                category=WorldGenCategory.ORE,
                conversion_notes="Java copper ore maps to Bedrock copper ore",
                dimension="overworld",
                rarity=35,
            ),
            WorldGenPattern(
                java_generator_type="ore_lapis",
                bedrock_feature_id="ore_lapis",
                category=WorldGenCategory.ORE,
                conversion_notes="Java lapis ore maps to Bedrock lapis ore",
                dimension="overworld",
                rarity=15,
            ),
        ]

        # Add all patterns
        self.patterns.extend(biome_patterns)
        self.patterns.extend(structure_patterns)
        self.patterns.extend(feature_patterns)
        self.patterns.extend(ore_patterns)

    def search_by_java(self, java_type: str) -> List[WorldGenPattern]:
        """
        Search patterns by Java generator type.

        Args:
            java_type: Java generator type to search for

        Returns:
            List of matching WorldGenPattern objects
        """
        results = []
        java_type_lower = java_type.lower()

        for pattern in self.patterns:
            # Check for partial match
            if java_type_lower in pattern.java_generator_type.lower():
                results.append(pattern)
            # Check for exact match
            elif java_type_lower == pattern.java_generator_type.lower():
                # Prioritize exact matches
                results.insert(0, results.pop(results.index(pattern)))

        return results

    def get_by_category(self, category: WorldGenCategory) -> List[WorldGenPattern]:
        """
        Get all patterns in a category.

        Args:
            category: WorldGenCategory to filter by

        Returns:
            List of patterns in the category
        """
        return [p for p in self.patterns if p.category == category]

    def get_by_dimension(self, dimension: str) -> List[WorldGenPattern]:
        """
        Get all patterns for a specific dimension.

        Args:
            dimension: Dimension to filter by

        Returns:
            List of patterns in the dimension
        """
        return [p for p in self.patterns if p.dimension == dimension]

    def add_pattern(self, pattern: WorldGenPattern) -> None:
        """
        Add a new pattern to the library.

        Args:
            pattern: WorldGenPattern to add
        """
        # Check for duplicate
        for existing in self.patterns:
            if existing.java_generator_type == pattern.java_generator_type:
                # Update existing
                existing.bedrock_feature_id = pattern.bedrock_feature_id
                existing.conversion_notes = pattern.conversion_notes
                return
        self.patterns.append(pattern)

    def get_pattern_by_java_type(self, java_type: str) -> Optional[WorldGenPattern]:
        """
        Get exact pattern by Java generator type.

        Args:
            java_type: Java generator type

        Returns:
            WorldGenPattern if found, None otherwise
        """
        for pattern in self.patterns:
            if pattern.java_generator_type.lower() == java_type.lower():
                return pattern
        return None

    def get_stats(self) -> Dict[str, int]:
        """
        Get library statistics.

        Returns:
            Dictionary with pattern counts
        """
        stats = {
            "total": len(self.patterns),
            "by_category": {},
            "by_dimension": {"overworld": 0, "nether": 0, "the_end": 0, "custom": 0},
        }

        # Count by category
        for pattern in self.patterns:
            cat = pattern.category.value
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

            dim = pattern.dimension
            stats["by_dimension"][dim] = stats["by_dimension"].get(dim, 0) + 1

        return stats


# Global pattern instance for easy import
WORLDGEN_PATTERNS = WorldGenPatternLibrary()


def get_worldgen_pattern(java_type: str) -> Optional[WorldGenPattern]:
    """
    Get a world generation pattern by Java type.

    Args:
        java_type: Java generator type

    Returns:
        WorldGenPattern if found, None otherwise
    """
    return WORLDGEN_PATTERNS.get_pattern_by_java_type(java_type)


def search_worldgen_patterns(query: str) -> List[WorldGenPattern]:
    """
    Search world generation patterns by Java type.

    Args:
        query: Search query

    Returns:
        List of matching patterns
    """
    return WORLDGEN_PATTERNS.search_by_java(query)


def get_patterns_by_category(category: WorldGenCategory) -> List[WorldGenPattern]:
    """
    Get all patterns in a category.

    Args:
        category: Category to filter by

    Returns:
        List of patterns
    """
    return WORLDGEN_PATTERNS.get_by_category(category)


def get_patterns_by_dimension(dimension: str) -> List[WorldGenPattern]:
    """
    Get all patterns for a dimension.

    Args:
        dimension: Dimension to filter by

    Returns:
        List of patterns
    """
    return WORLDGEN_PATTERNS.get_by_dimension(dimension)


def get_worldgen_stats() -> Dict[str, int]:
    """
    Get world generation pattern library statistics.

    Returns:
        Statistics dictionary
    """
    return WORLDGEN_PATTERNS.get_stats()
