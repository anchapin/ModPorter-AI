"""
Particle Pattern Library for RAG-based particle conversion.

Provides pattern matching and retrieval for Java to Bedrock particle
conversion including particle types, emitters, and effects.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ParticleCategory(Enum):
    """Particle pattern categories."""

    AMBIENT = "ambient"
    COMBAT = "combat"
    ENVIRONMENT = "environment"
    MAGIC = "magic"
    WEATHER = "weather"
    BLOCK = "block"
    ITEM = "item"


@dataclass
class ParticlePattern:
    """
    Represents a single particle conversion pattern.

    Contains Java particle class reference and corresponding Bedrock
    particle type with conversion notes and metadata.
    """

    java_particle_class: str
    bedrock_particle_id: str
    category: ParticleCategory
    conversion_notes: str
    rarity: int = 1  # 1-100, how common

    def to_dict(self) -> Dict:
        """Convert pattern to dictionary."""
        return {
            "java_particle_class": self.java_particle_class,
            "bedrock_particle_id": self.bedrock_particle_id,
            "category": self.category.value,
            "conversion_notes": self.conversion_notes,
            "rarity": self.rarity,
        }


class ParticlePatternLibrary:
    """
    Library of particle conversion patterns.

    Provides storage, retrieval, and search functionality for
    Java→Bedrock particle pattern conversion.
    """

    def __init__(self):
        """Initialize pattern library with default patterns."""
        self.patterns: List[ParticlePattern] = []
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default particle patterns (25+ patterns)."""

        # Ambient particles (5 patterns)
        ambient_patterns = [
            ParticlePattern(
                java_particle_class="ParticleFlame",
                bedrock_particle_id="minecraft:flame",
                category=ParticleCategory.AMBIENT,
                conversion_notes="Java ParticleFlame maps to Bedrock flame particle",
                rarity=70,
            ),
            ParticlePattern(
                java_particle_class="ParticleSmoke",
                bedrock_particle_id="minecraft:smoke",
                category=ParticleCategory.AMBIENT,
                conversion_notes="Java ParticleSmoke maps to Bedrock smoke particle",
                rarity=75,
            ),
            ParticlePattern(
                java_particle_class="ParticlePortal",
                bedrock_particle_id="minecraft:portal",
                category=ParticleCategory.AMBIENT,
                conversion_notes="Java ParticlePortal maps to Bedrock portal particle",
                rarity=60,
            ),
            ParticlePattern(
                java_particle_class="ParticleEnchant",
                bedrock_particle_id="minecraft:enchant",
                category=ParticleCategory.AMBIENT,
                conversion_notes="Java ParticleEnchant maps to Bedrock enchant particle",
                rarity=55,
            ),
            ParticlePattern(
                java_particle_class="ParticleWarning",
                bedrock_particle_id="minecraft:warning",
                category=ParticleCategory.AMBIENT,
                conversion_notes="Java ParticleWarning maps to Bedrock warning particle",
                rarity=50,
            ),
        ]

        # Combat particles (5 patterns)
        combat_patterns = [
            ParticlePattern(
                java_particle_class="ParticleHit",
                bedrock_particle_id="minecraft:crit",
                category=ParticleCategory.COMBAT,
                conversion_notes="Java ParticleHit maps to Bedrock crit particle",
                rarity=80,
            ),
            ParticlePattern(
                java_particle_class="ParticleAttack",
                bedrock_particle_id="minecraft:explosion",
                category=ParticleCategory.COMBAT,
                conversion_notes="Java ParticleAttack maps to Bedrock explosion particle",
                rarity=70,
            ),
            ParticlePattern(
                java_particle_class="ParticleDamage",
                bedrock_particle_id="minecraft:crit",
                category=ParticleCategory.COMBAT,
                conversion_notes="Java ParticleDamage maps to Bedrock crit particle",
                rarity=75,
            ),
            ParticlePattern(
                java_particle_class="ParticleMagic",
                bedrock_particle_id="minecraft:spell",
                category=ParticleCategory.COMBAT,
                conversion_notes="Java ParticleMagic maps to Bedrock spell particle",
                rarity=65,
            ),
            ParticlePattern(
                java_particle_class="ParticleExplosion",
                bedrock_particle_id="minecraft:explosion",
                category=ParticleCategory.COMBAT,
                conversion_notes="Java ParticleExplosion maps to Bedrock explosion particle",
                rarity=70,
            ),
        ]

        # Environment particles (6 patterns)
        environment_patterns = [
            ParticlePattern(
                java_particle_class="ParticleRain",
                bedrock_particle_id="minecraft:rain",
                category=ParticleCategory.ENVIRONMENT,
                conversion_notes="Java ParticleRain maps to Bedrock rain particle",
                rarity=80,
            ),
            ParticlePattern(
                java_particle_class="ParticleSnow",
                bedrock_particle_id="minecraft:snow",
                category=ParticleCategory.ENVIRONMENT,
                conversion_notes="Java ParticleSnow maps to Bedrock snow particle",
                rarity=70,
            ),
            ParticlePattern(
                java_particle_class="ParticleWater",
                bedrock_particle_id="minecraft:dripping_water",
                category=ParticleCategory.ENVIRONMENT,
                conversion_notes="Java ParticleWater maps to Bedrock dripping water",
                rarity=85,
            ),
            ParticlePattern(
                java_particle_class="ParticleLava",
                bedrock_particle_id="minecraft:dripping_lava",
                category=ParticleCategory.ENVIRONMENT,
                conversion_notes="Java ParticleLava maps to Bedrock dripping lava",
                rarity=75,
            ),
            ParticlePattern(
                java_particle_class="ParticleFire",
                bedrock_particle_id="minecraft:flame",
                category=ParticleCategory.ENVIRONMENT,
                conversion_notes="Java ParticleFire maps to Bedrock flame particle",
                rarity=80,
            ),
            ParticlePattern(
                java_particle_class="ParticleBubble",
                bedrock_particle_id="minecraft:bubble",
                category=ParticleCategory.ENVIRONMENT,
                conversion_notes="Java ParticleBubble maps to Bedrock bubble particle",
                rarity=70,
            ),
        ]

        # Magic particles (5 patterns)
        magic_patterns = [
            ParticlePattern(
                java_particle_class="ParticleSpell",
                bedrock_particle_id="minecraft:spell",
                category=ParticleCategory.MAGIC,
                conversion_notes="Java ParticleSpell maps to Bedrock spell particle",
                rarity=75,
            ),
            ParticlePattern(
                java_particle_class="ParticleWitch",
                bedrock_particle_id="minecraft:spell",
                category=ParticleCategory.MAGIC,
                conversion_notes="Java ParticleWitch maps to Bedrock spell particle",
                rarity=60,
            ),
            ParticlePattern(
                java_particle_class="ParticleDragon",
                bedrock_particle_id="minecraft:dragon_death",
                category=ParticleCategory.MAGIC,
                conversion_notes="Java ParticleDragon maps to Bedrock dragon death",
                rarity=50,
            ),
            ParticlePattern(
                java_particle_class="ParticleGuardian",
                bedrock_particle_id="minecraft:crit",
                category=ParticleCategory.MAGIC,
                conversion_notes="Java ParticleGuardian maps to Bedrock crit particle",
                rarity=55,
            ),
            ParticlePattern(
                java_particle_class="ParticleEndRod",
                bedrock_particle_id="minecraft:end_rod",
                category=ParticleCategory.MAGIC,
                conversion_notes="Java ParticleEndRod maps to Bedrock end rod particle",
                rarity=65,
            ),
        ]

        # Block particles (4 patterns)
        block_patterns = [
            ParticlePattern(
                java_particle_class="ParticleBlock",
                bedrock_particle_id="minecraft:block",
                category=ParticleCategory.BLOCK,
                conversion_notes="Java ParticleBlock maps to Bedrock block particle",
                rarity=85,
            ),
            ParticlePattern(
                java_particle_class="ParticleFallingDust",
                bedrock_particle_id="minecraft:falling_dust",
                category=ParticleCategory.BLOCK,
                conversion_notes="Java ParticleFallingDust maps to Bedrock falling dust",
                rarity=75,
            ),
            ParticlePattern(
                java_particle_class="ParticleLanding",
                bedrock_particle_id="minecraft:landing",
                category=ParticleCategory.BLOCK,
                conversion_notes="Java ParticleLanding maps to Bedrock landing particle",
                rarity=70,
            ),
            ParticlePattern(
                java_particle_class="ParticleDust",
                bedrock_particle_id="minecraft:basic_particle",
                category=ParticleCategory.BLOCK,
                conversion_notes="Java ParticleDust maps to Bedrock basic particle",
                rarity=80,
            ),
        ]

        # Item particles (4 patterns)
        item_patterns = [
            ParticlePattern(
                java_particle_class="ParticleItem",
                bedrock_particle_id="minecraft:item",
                category=ParticleCategory.ITEM,
                conversion_notes="Java ParticleItem maps to Bedrock item particle",
                rarity=75,
            ),
            ParticlePattern(
                java_particle_class="ParticleSlime",
                bedrock_particle_id="minecraft:slime",
                category=ParticleCategory.ITEM,
                conversion_notes="Java ParticleSlime maps to Bedrock slime particle",
                rarity=65,
            ),
            ParticlePattern(
                java_particle_class="ParticleHeart",
                bedrock_particle_id="minecraft:heart",
                category=ParticleCategory.ITEM,
                conversion_notes="Java ParticleHeart maps to Bedrock heart particle",
                rarity=70,
            ),
            ParticlePattern(
                java_particle_class="ParticleRedstone",
                bedrock_particle_id="minecraft:redstone",
                category=ParticleCategory.ITEM,
                conversion_notes="Java ParticleRedstone maps to Bedrock redstone particle",
                rarity=80,
            ),
        ]

        # Add all patterns
        self.patterns.extend(ambient_patterns)
        self.patterns.extend(combat_patterns)
        self.patterns.extend(environment_patterns)
        self.patterns.extend(magic_patterns)
        self.patterns.extend(block_patterns)
        self.patterns.extend(item_patterns)

    def search_by_java(self, java_class: str) -> List[ParticlePattern]:
        """
        Search patterns by Java particle class.

        Args:
            java_class: Java particle class to search for

        Returns:
            List of matching ParticlePattern objects
        """
        results = []
        java_class_lower = java_class.lower()

        for pattern in self.patterns:
            # Check for partial match
            if java_class_lower in pattern.java_particle_class.lower():
                results.append(pattern)
            # Check for exact match
            elif java_class_lower == pattern.java_particle_class.lower():
                # Prioritize exact matches
                results.insert(0, results.pop(results.index(pattern)))

        return results

    def get_by_category(self, category: ParticleCategory) -> List[ParticlePattern]:
        """
        Get all patterns in a category.

        Args:
            category: ParticleCategory to filter by

        Returns:
            List of patterns in the category
        """
        return [p for p in self.patterns if p.category == category]

    def get_pattern_by_java_class(self, java_class: str) -> Optional[ParticlePattern]:
        """
        Get exact pattern by Java particle class.

        Args:
            java_class: Java particle class

        Returns:
            ParticlePattern if found, None otherwise
        """
        for pattern in self.patterns:
            if pattern.java_particle_class.lower() == java_class.lower():
                return pattern
        return None

    def add_pattern(self, pattern: ParticlePattern) -> None:
        """
        Add a new pattern to the library.

        Args:
            pattern: ParticlePattern to add
        """
        # Check for duplicate
        for existing in self.patterns:
            if existing.java_particle_class == pattern.java_particle_class:
                # Update existing
                existing.bedrock_particle_id = pattern.bedrock_particle_id
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
PARTICLE_PATTERNS = ParticlePatternLibrary()


def get_particle_pattern(java_class: str) -> Optional[ParticlePattern]:
    """
    Get a particle pattern by Java class.

    Args:
        java_class: Java particle class

    Returns:
        ParticlePattern if found, None otherwise
    """
    return PARTICLE_PATTERNS.get_pattern_by_java_class(java_class)


def search_particle_patterns(query: str) -> List[ParticlePattern]:
    """
    Search particle patterns by Java class.

    Args:
        query: Search query

    Returns:
        List of matching patterns
    """
    return PARTICLE_PATTERNS.search_by_java(query)


def get_patterns_by_category(category: ParticleCategory) -> List[ParticlePattern]:
    """
    Get all patterns in a category.

    Args:
        category: Category to filter by

    Returns:
        List of patterns
    """
    return PARTICLE_PATTERNS.get_by_category(category)


def get_particle_stats() -> Dict[str, int]:
    """
    Get particle pattern library statistics.

    Returns:
        Statistics dictionary
    """
    return PARTICLE_PATTERNS.get_stats()
