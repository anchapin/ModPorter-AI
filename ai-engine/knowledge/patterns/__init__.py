"""
Pattern library for Java→Bedrock conversions.

Provides conversion patterns, pattern registries, and mapping logic.
"""

from .base import ConversionPattern, PatternLibrary
from .java_patterns import JavaPatternRegistry
from .bedrock_patterns import BedrockPatternRegistry
from .mappings import PatternMapping, PatternMappingRegistry

__all__ = [
    "ConversionPattern",
    "PatternLibrary",
    "JavaPatternRegistry",
    "BedrockPatternRegistry",
    "PatternMapping",
    "PatternMappingRegistry",
]
