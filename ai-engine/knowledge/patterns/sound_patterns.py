"""
Sound Pattern Library for RAG-based sound conversion.

Provides pattern matching and retrieval for Java to Bedrock sound conversion
scenarios including block sounds, item sounds, entity sounds, and music.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class SoundCategory(Enum):
    """Sound categories for pattern classification."""

    BLOCK = "block"
    ITEM = "item"
    ENTITY = "entity"
    AMBIENT = "ambient"
    MUSIC = "music"
    WEATHER = "weather"
    CUSTOM = "custom"


@dataclass
class SoundPattern:
    """
    Represents a single sound conversion pattern.

    Contains Java sound reference and corresponding Bedrock sound event
    with conversion notes and metadata.
    """

    java_sound_reference: str
    bedrock_sound_event: str
    category: SoundCategory
    conversion_notes: str
    file_extension: str = "ogg"
    weight: int = 1
    is_stream: bool = False
    is_music: bool = False

    def to_dict(self) -> Dict:
        """Convert pattern to dictionary."""
        return {
            "java_sound_reference": self.java_sound_reference,
            "bedrock_sound_event": self.bedrock_sound_event,
            "category": self.category.value,
            "conversion_notes": self.conversion_notes,
            "file_extension": self.file_extension,
            "weight": self.weight,
            "is_stream": self.is_stream,
            "is_music": self.is_music,
        }


class SoundPatternLibrary:
    """
    Library of sound conversion patterns.

    Provides storage, retrieval, and search functionality for
    Java→Bedrock sound conversion patterns.
    """

    def __init__(self):
        """Initialize pattern library with default patterns."""
        self.patterns: List[SoundPattern] = []
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default sound patterns (25+ patterns)."""

        # Block sounds (8 patterns)
        block_patterns = [
            SoundPattern(
                java_sound_reference="block.stone.break",
                bedrock_sound_event="dig.stone",
                category=SoundCategory.BLOCK,
                conversion_notes="Java stone break maps to Bedrock dig.stone",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="block.stone.place",
                bedrock_sound_event="step.stone",
                category=SoundCategory.BLOCK,
                conversion_notes="Java stone place uses step sound in Bedrock",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="block.stone.hit",
                bedrock_sound_event="hit.stone",
                category=SoundCategory.BLOCK,
                conversion_notes="Java hit uses Bedrock hit.stone",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="block.stone.step",
                bedrock_sound_event="step.stone",
                category=SoundCategory.BLOCK,
                conversion_notes="Java step maps directly to Bedrock step.stone",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="block.wood.break",
                bedrock_sound_event="dig.wood",
                category=SoundCategory.BLOCK,
                conversion_notes="Java wood break maps to Bedrock dig.wood",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="block.grass.break",
                bedrock_sound_event="dig.grass",
                category=SoundCategory.BLOCK,
                conversion_notes="Java grass break maps to Bedrock dig.grass",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="block.glass.break",
                bedrock_sound_event="glass.break",
                category=SoundCategory.BLOCK,
                conversion_notes="Java glass break has direct Bedrock equivalent",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="block.sand.step",
                bedrock_sound_event="step.sand",
                category=SoundCategory.BLOCK,
                conversion_notes="Java sand step maps directly",
                file_extension="ogg",
            ),
        ]

        # Item sounds (5 patterns)
        item_patterns = [
            SoundPattern(
                java_sound_reference="item.armor.equip",
                bedrock_sound_event="armor.equip",
                category=SoundCategory.ITEM,
                conversion_notes="Armor equip is direct mapping",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="item.armor.equip_diamond",
                bedrock_sound_event="armor.equip_diamond",
                category=SoundCategory.ITEM,
                conversion_notes="Diamond armor equip",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="item.bread.eat",
                bedrock_sound_event="eat",
                category=SoundCategory.ITEM,
                conversion_notes="Java eating maps to generic eat sound",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="item.bottle.fill",
                bedrock_sound_event="bottle.fill",
                category=SoundCategory.ITEM,
                conversion_notes="Bottle fill is direct mapping",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="item.crossbow.shoot",
                bedrock_sound_event="crossbow.shoot",
                category=SoundCategory.ITEM,
                conversion_notes="Crossbow shoot is direct mapping",
                file_extension="ogg",
            ),
        ]

        # Entity sounds (5 patterns)
        entity_patterns = [
            SoundPattern(
                java_sound_reference="entity.zombie.hurt",
                bedrock_sound_event="mob.zombie.hurt",
                category=SoundCategory.ENTITY,
                conversion_notes="Java zombie hurt maps to mob.zombie.hurt",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="entity.zombie.death",
                bedrock_sound_event="mob.zombie.death",
                category=SoundCategory.ENTITY,
                conversion_notes="Java zombie death maps to mob.zombie.death",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="entity.skeleton.ambient",
                bedrock_sound_event="mob.skeleton.ambient",
                category=SoundCategory.ENTITY,
                conversion_notes="Skeleton ambient is direct mapping",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="entity.cow.ambient",
                bedrock_sound_event="mob.cow.say",
                category=SoundCategory.ENTITY,
                conversion_notes="Cow ambient maps to mob.cow.say in Bedrock",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="entity.player.attack",
                bedrock_sound_event="player.attack",
                category=SoundCategory.ENTITY,
                conversion_notes="Player attack is direct mapping",
                file_extension="ogg",
            ),
        ]

        # Ambient sounds (4 patterns)
        ambient_patterns = [
            SoundPattern(
                java_sound_reference="ambient.cave",
                bedrock_sound_event="ambient.cave",
                category=SoundCategory.AMBIENT,
                conversion_notes="Cave ambient is direct mapping",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="ambient.underwater",
                bedrock_sound_event="ambient.underwater",
                category=SoundCategory.AMBIENT,
                conversion_notes="Underwater ambient is direct mapping",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="ambient.nether",
                bedrock_sound_event="ambient.nether",
                category=SoundCategory.AMBIENT,
                conversion_notes="Nether ambient is direct mapping",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="ambient.biome.forest",
                bedrock_sound_event="ambient.forest",
                category=SoundCategory.AMBIENT,
                conversion_notes="Forest biome ambient",
                file_extension="ogg",
            ),
        ]

        # Music sounds (3 patterns)
        music_patterns = [
            SoundPattern(
                java_sound_reference="music.menu",
                bedrock_sound_event="music.menu",
                category=SoundCategory.MUSIC,
                conversion_notes="Menu music is direct mapping",
                file_extension="ogg",
                is_stream=True,
                is_music=True,
            ),
            SoundPattern(
                java_sound_reference="music.game",
                bedrock_sound_event="music.game",
                category=SoundCategory.MUSIC,
                conversion_notes="Game music is direct mapping",
                file_extension="ogg",
                is_stream=True,
                is_music=True,
            ),
            SoundPattern(
                java_sound_reference="music.end",
                bedrock_sound_event="music.end",
                category=SoundCategory.MUSIC,
                conversion_notes="End music is direct mapping",
                file_extension="ogg",
                is_stream=True,
                is_music=True,
            ),
        ]

        # Custom/mod sounds (3 patterns)
        custom_patterns = [
            SoundPattern(
                java_sound_reference="custom.mod.sound",
                bedrock_sound_event="custom.mod.sound",
                category=SoundCategory.CUSTOM,
                conversion_notes="Custom sounds keep namespace",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="modid:special_sound",
                bedrock_sound_event="modid.special_sound",
                category=SoundCategory.CUSTOM,
                conversion_notes="Mod namespace preserved, dots replace colons",
                file_extension="ogg",
            ),
            SoundPattern(
                java_sound_reference="event.mod.special",
                bedrock_sound_event="event.mod.special",
                category=SoundCategory.CUSTOM,
                conversion_notes="Custom event sounds use namespace",
                file_extension="ogg",
            ),
        ]

        # Add all patterns
        self.patterns.extend(block_patterns)
        self.patterns.extend(item_patterns)
        self.patterns.extend(entity_patterns)
        self.patterns.extend(ambient_patterns)
        self.patterns.extend(music_patterns)
        self.patterns.extend(custom_patterns)

    def search_by_java(self, java_ref: str) -> List[SoundPattern]:
        """
        Search patterns by Java sound reference.

        Args:
            java_ref: Java sound reference to search for

        Returns:
            List of matching SoundPattern objects
        """
        results = []
        java_ref_lower = java_ref.lower()

        for pattern in self.patterns:
            # Check for partial match
            if java_ref_lower in pattern.java_sound_reference.lower():
                results.append(pattern)
            # Check for exact match
            elif java_ref_lower == pattern.java_sound_reference.lower():
                # Prioritize exact matches
                results.insert(0, results.pop(results.index(pattern)))

        return results

    def get_by_category(self, category: SoundCategory) -> List[SoundPattern]:
        """
        Get all patterns in a category.

        Args:
            category: SoundCategory to filter by

        Returns:
            List of patterns in the category
        """
        return [p for p in self.patterns if p.category == category]

    def add_pattern(self, pattern: SoundPattern) -> None:
        """
        Add a new pattern to the library.

        Args:
            pattern: SoundPattern to add
        """
        # Check for duplicate
        for existing in self.patterns:
            if existing.java_sound_reference == pattern.java_sound_reference:
                # Update existing
                existing.bedrock_sound_event = pattern.bedrock_sound_event
                existing.conversion_notes = pattern.conversion_notes
                return
        self.patterns.append(pattern)

    def get_pattern_by_java_reference(self, java_ref: str) -> Optional[SoundPattern]:
        """
        Get exact pattern by Java reference.

        Args:
            java_ref: Java sound reference

        Returns:
            SoundPattern if found, None otherwise
        """
        for pattern in self.patterns:
            if pattern.java_sound_reference.lower() == java_ref.lower():
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
            "stream_count": sum(1 for p in self.patterns if p.is_stream),
            "music_count": sum(1 for p in self.patterns if p.is_music),
        }

        # Count by category
        for pattern in self.patterns:
            cat = pattern.category.value
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        return stats


# Global pattern instances for easy import
SOUND_PATTERNS = SoundPatternLibrary()


def get_sound_pattern(java_ref: str) -> Optional[SoundPattern]:
    """
    Get a sound pattern by Java reference.

    Args:
        java_ref: Java sound reference

    Returns:
        SoundPattern if found, None otherwise
    """
    return SOUND_PATTERNS.get_pattern_by_java_reference(java_ref)


def search_sound_patterns(query: str) -> List[SoundPattern]:
    """
    Search sound patterns by Java reference.

    Args:
        query: Search query

    Returns:
        List of matching patterns
    """
    return SOUND_PATTERNS.search_by_java(query)


def get_patterns_by_category(category: SoundCategory) -> List[SoundPattern]:
    """
    Get all patterns in a category.

    Args:
        category: Category to filter by

    Returns:
        List of patterns
    """
    return SOUND_PATTERNS.get_by_category(category)


def get_sound_stats() -> Dict[str, int]:
    """
    Get sound pattern library statistics.

    Returns:
        Statistics dictionary
    """
    return SOUND_PATTERNS.get_stats()
