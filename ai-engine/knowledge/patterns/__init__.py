"""
Pattern library for Java→Bedrock conversions.

Provides conversion patterns, pattern registries, and mapping logic.
"""

from .base import ConversionPattern, PatternLibrary
from .java_patterns import JavaPatternRegistry
from .bedrock_patterns import BedrockPatternRegistry
from .mappings import PatternMapping, PatternMappingRegistry
from .sound_patterns import (
    SoundPattern,
    SoundPatternLibrary,
    SoundCategory,
    SOUND_PATTERNS,
    get_sound_pattern,
    search_sound_patterns,
    get_patterns_by_category,
    get_sound_stats,
)

__all__ = [
    "ConversionPattern",
    "PatternLibrary",
    "JavaPatternRegistry",
    "BedrockPatternRegistry",
    "PatternMapping",
    "PatternMappingRegistry",
    # Sound patterns
    "SoundPattern",
    "SoundPatternLibrary",
    "SoundCategory",
    "SOUND_PATTERNS",
    "get_sound_pattern",
    "search_sound_patterns",
    "get_patterns_by_category",
    "get_sound_stats",
]
