"""
Potion Pattern Library for RAG-based potion/effect conversion.

Provides pattern matching and retrieval for Java to Bedrock potion
and effect conversion including status effects, durations, and amplifiers.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class PotionPatternCategory(Enum):
    """Potion pattern categories."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    BUFF = "buff"
    DEBUFF = "debuff"
    AMBIENT = "ambient"


@dataclass
class PotionPattern:
    """
    Represents a single potion/effect conversion pattern.

    Contains Java effect class reference and corresponding Bedrock
    effect identifier with conversion notes and category.
    """

    java_effect_class: str
    bedrock_effect_id: str
    category: PotionPatternCategory
    conversion_notes: str
    default_duration: int = 180  # seconds
    max_amplifier: int = 255


class PotionPatternLibrary:
    """
    Library of potion/effect conversion patterns.

    Provides storage, retrieval, and search functionality for
    Java→Bedrock potion and effect pattern conversion.
    """

    def __init__(self):
        """Initialize pattern library with default patterns."""
        self.patterns: List[PotionPattern] = []
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default potion/effect patterns (25+ patterns)."""

        # Positive effects (buffs) - 9 patterns
        positive_patterns = [
            PotionPattern(
                java_effect_class="speed",
                bedrock_effect_id="speed",
                category=PotionPatternCategory.POSITIVE,
                conversion_notes="Speed effect - increases movement speed",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="strength",
                bedrock_effect_id="strength",
                category=PotionPatternCategory.POSITIVE,
                conversion_notes="Strength effect - increases melee damage",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="regeneration",
                bedrock_effect_id="regeneration",
                category=PotionPatternCategory.POSITIVE,
                conversion_notes="Regeneration effect - restores health over time",
                default_duration=90,
            ),
            PotionPattern(
                java_effect_class="damage_resistance",
                bedrock_effect_id="damage_resistance",
                category=PotionPatternCategory.POSITIVE,
                conversion_notes="Resistance effect - reduces damage taken",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="fire_resistance",
                bedrock_effect_id="fire_resistance",
                category=PotionPatternCategory.POSITIVE,
                conversion_notes="Fire resistance - immunity to fire damage",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="water_breathing",
                bedrock_effect_id="water_breathing",
                category=PotionPatternCategory.POSITIVE,
                conversion_notes="Water breathing - underwater oxygen",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="night_vision",
                bedrock_effect_id="night_vision",
                category=PotionPatternCategory.POSITIVE,
                conversion_notes="Night vision - enhanced underwater visibility",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="absorption",
                bedrock_effect_id="absorption",
                category=PotionPatternCategory.POSITIVE,
                conversion_notes="Absorption - extra health pool",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="luck",
                bedrock_effect_id="luck",
                category=PotionPatternCategory.POSITIVE,
                conversion_notes="Luck effect - better loot and fishing",
                default_duration=300,
            ),
        ]

        # Negative effects (debuffs) - 8 patterns
        negative_patterns = [
            PotionPattern(
                java_effect_class="poison",
                bedrock_effect_id="poison",
                category=PotionPatternCategory.NEGATIVE,
                conversion_notes="Poison effect - damages health over time",
                default_duration=90,
            ),
            PotionPattern(
                java_effect_class="wither",
                bedrock_effect_id="wither",
                category=PotionPatternCategory.NEGATIVE,
                conversion_notes="Wither effect - damages wither health",
                default_duration=90,
            ),
            PotionPattern(
                java_effect_class="hunger",
                bedrock_effect_id="hunger",
                category=PotionPatternCategory.NEGATIVE,
                conversion_notes="Hunger effect - increases hunger drain",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="weakness",
                bedrock_effect_id="weakness",
                category=PotionPatternCategory.NEGATIVE,
                conversion_notes="Weakness effect - reduces melee damage",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="slowness",
                bedrock_effect_id="slowness",
                category=PotionPatternCategory.NEGATIVE,
                conversion_notes="Slowness effect - reduces movement speed",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="mining_fatigue",
                bedrock_effect_id="mining_fatigue",
                category=PotionPatternCategory.NEGATIVE,
                conversion_notes="Mining fatigue - reduces mining speed",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="blindness",
                bedrock_effect_id="blindness",
                category=PotionPatternCategory.NEGATIVE,
                conversion_notes="Blindness effect - limits vision",
                default_duration=120,
            ),
            PotionPattern(
                java_effect_class="nausea",
                bedrock_effect_id="nausea",
                category=PotionPatternCategory.NEGATIVE,
                conversion_notes="Nausea effect - warps screen",
                default_duration=120,
            ),
        ]

        # Neutral effects - 6 patterns
        neutral_patterns = [
            PotionPattern(
                java_effect_class="jump_boost",
                bedrock_effect_id="jump_boost",
                category=PotionPatternCategory.NEUTRAL,
                conversion_notes="Jump boost - increases jump height",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="dolphins_grace",
                bedrock_effect_id="dolphins_grace",
                category=PotionPatternCategory.NEUTRAL,
                conversion_notes="Dolphin's grace - faster swimming",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="haste",
                bedrock_effect_id="haste",
                category=PotionPatternCategory.NEUTRAL,
                conversion_notes="Haste effect - increases mining speed",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="saturation",
                bedrock_effect_id="saturation",
                category=PotionPatternCategory.NEUTRAL,
                conversion_notes="Saturation effect - restores hunger",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="glowing",
                bedrock_effect_id="glowing",
                category=PotionPatternCategory.NEUTRAL,
                conversion_notes="Glowing effect - highlights entity",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="levitation",
                bedrock_effect_id="levitation",
                category=PotionPatternCategory.NEUTRAL,
                conversion_notes="Levitation effect - floats upward",
                default_duration=90,
            ),
        ]

        # Buffs (additional) - 4 patterns
        buff_patterns = [
            PotionPattern(
                java_effect_class="invisibility",
                bedrock_effect_id="invisibility",
                category=PotionPatternCategory.BUFF,
                conversion_notes="Invisibility effect - makes entity invisible",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="slow_falling",
                bedrock_effect_id="slow_falling",
                category=PotionPatternCategory.BUFF,
                conversion_notes="Slow falling - reduces fall damage",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="conduit_power",
                bedrock_effect_id="conduit_power",
                category=PotionPatternCategory.BUFF,
                conversion_notes="Conduit power - underwater abilities",
                default_duration=180,
            ),
            PotionPattern(
                java_effect_class="hero_of_the_village",
                bedrock_effect_id="hero_of_the_village",
                category=PotionPatternCategory.BUFF,
                conversion_notes="Hero of the village - village discounts",
                default_duration=180,
            ),
        ]

        # Debuffs (additional) - 2 patterns
        debuff_patterns = [
            PotionPattern(
                java_effect_class="bad_omen",
                bedrock_effect_id="bad_omen",
                category=PotionPatternCategory.DEBUFF,
                conversion_notes="Bad omen - triggers raids",
                default_duration=300,
            ),
            PotionPattern(
                java_effect_class="darkness",
                bedrock_effect_id="darkness",
                category=PotionPatternCategory.DEBUFF,
                conversion_notes="Darkness effect - reduces visibility",
                default_duration=120,
            ),
        ]

        # Add all patterns
        self.patterns.extend(positive_patterns)
        self.patterns.extend(negative_patterns)
        self.patterns.extend(neutral_patterns)
        self.patterns.extend(buff_patterns)
        self.patterns.extend(debuff_patterns)

    def search_by_java(self, java_class: str) -> List[PotionPattern]:
        """
        Search patterns by Java effect class.

        Args:
            java_class: Java effect class to search for

        Returns:
            List of matching PotionPattern objects
        """
        results = []
        java_class_lower = java_class.lower()

        for pattern in self.patterns:
            # Check for partial match
            if java_class_lower in pattern.java_effect_class.lower():
                results.append(pattern)
            # Check for exact match - prioritize
            elif java_class_lower == pattern.java_effect_class.lower():
                results.insert(0, results.pop(results.index(pattern)))

        return results

    def get_by_category(self, category: PotionPatternCategory) -> List[PotionPattern]:
        """
        Get all patterns in a category.

        Args:
            category: PotionPatternCategory to filter by

        Returns:
            List of patterns in the category
        """
        return [p for p in self.patterns if p.category == category]

    def get_pattern_by_java_class(self, java_class: str) -> Optional[PotionPattern]:
        """
        Get exact pattern by Java effect class.

        Args:
            java_class: Java effect class

        Returns:
            PotionPattern if found, None otherwise
        """
        for pattern in self.patterns:
            if pattern.java_effect_class.lower() == java_class.lower():
                return pattern
        return None

    def add_pattern(self, pattern: PotionPattern) -> None:
        """
        Add a new pattern to the library.

        Args:
            pattern: PotionPattern to add
        """
        # Check for duplicate
        for existing in self.patterns:
            if existing.java_effect_class == pattern.java_effect_class:
                # Update existing
                existing.bedrock_effect_id = pattern.bedrock_effect_id
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
POTION_PATTERNS = PotionPatternLibrary()


def get_potion_pattern(java_class: str) -> Optional[PotionPattern]:
    """
    Get a potion pattern by Java class.

    Args:
        java_class: Java effect class

    Returns:
        PotionPattern if found, None otherwise
    """
    return POTION_PATTERNS.get_pattern_by_java_class(java_class)


def search_potion_patterns(query: str) -> List[PotionPattern]:
    """
    Search potion patterns by Java class.

    Args:
        query: Search query

    Returns:
        List of matching patterns
    """
    return POTION_PATTERNS.search_by_java(query)


def get_patterns_by_category(category: PotionPatternCategory) -> List[PotionPattern]:
    """
    Get all patterns in a category.

    Args:
        category: Category to filter by

    Returns:
        List of patterns
    """
    return POTION_PATTERNS.get_by_category(category)


def get_potion_stats() -> Dict[str, int]:
    """
    Get potion pattern library statistics.

    Returns:
        Statistics dictionary
    """
    return POTION_PATTERNS.get_stats()
