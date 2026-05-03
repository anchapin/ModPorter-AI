"""
Rendering Pattern Library for RAG-based entity rendering conversion.

Provides pattern matching and retrieval for Java to Bedrock entity rendering,
model definitions, texture mappings, and animation conversion patterns.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class RenderingPatternCategory(Enum):
    """Rendering pattern categories."""

    MODEL = "model"
    ANIMATION = "animation"
    TEXTURE = "texture"
    RENDER_CONTROLLER = "render_controller"
    PARTICLE = "particle"


@dataclass
class RenderingPattern:
    """
    Represents a single rendering conversion pattern.

    Contains Java rendering class reference and corresponding Bedrock
    render identifier with conversion notes and category.
    """

    java_rendering_class: str
    bedrock_render_id: str
    category: RenderingPatternCategory
    conversion_notes: str
    model_type: Optional[str] = None
    animation_type: Optional[str] = None
    texture_mapping: Optional[str] = None


class RenderingPatternLibrary:
    """
    Library of rendering conversion patterns.

    Provides storage, retrieval, and search functionality for
    Java→Bedrock entity rendering, model, texture, and animation
    pattern conversion.
    """

    def __init__(self):
        """Initialize pattern library with default patterns."""
        self.patterns: List[RenderingPattern] = []
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default rendering patterns (20+ patterns)."""

        # Model patterns - 6 patterns
        model_patterns = [
            RenderingPattern(
                java_rendering_class="BipedModel",
                bedrock_render_id="geometry.biped",
                category=RenderingPatternCategory.MODEL,
                conversion_notes="Standard biped model - humanoids, zombies, skeletons",
                model_type="biped",
            ),
            RenderingPattern(
                java_rendering_class="QuadrupedModel",
                bedrock_render_id="geometry.quadruped",
                category=RenderingPatternCategory.MODEL,
                conversion_notes="Four-legged animal model - cows, pigs, horses",
                model_type="quadruped",
            ),
            RenderingPattern(
                java_rendering_class="ArmorStandModel",
                bedrock_render_id="geometry.armorstand",
                category=RenderingPatternCategory.MODEL,
                conversion_notes="Armor stand model - poses like a player",
                model_type="biped",
            ),
            RenderingPattern(
                java_rendering_class="ArmorsmithModel",
                bedrock_render_id="geometry.armorsmith",
                category=RenderingPatternCategory.MODEL,
                conversion_notes="Armor display model - shows armor pieces",
                model_type="armorsmith",
            ),
            RenderingPattern(
                java_rendering_class="ItemDisplayModel",
                bedrock_render_id="geometry.item_display",
                category=RenderingPatternCategory.MODEL,
                conversion_notes="Item display model - for display entities",
                model_type="item_display",
            ),
            RenderingPattern(
                java_rendering_class="SlimeModel",
                bedrock_render_id="geometry.slime",
                category=RenderingPatternCategory.MODEL,
                conversion_notes="Slime model - cubic bouncing entity",
                model_type="custom",
            ),
        ]

        # Animation patterns - 7 patterns
        animation_patterns = [
            RenderingPattern(
                java_rendering_class="IdleAnimation",
                bedrock_render_id="animation.idle",
                category=RenderingPatternCategory.ANIMATION,
                conversion_notes="Idle breathing animation - subtle body movement",
                animation_type="idle",
            ),
            RenderingPattern(
                java_rendering_class="WalkAnimation",
                bedrock_render_id="animation.walk",
                category=RenderingPatternCategory.ANIMATION,
                conversion_notes="Walk cycle animation - limb movement",
                animation_type="walk",
            ),
            RenderingPattern(
                java_rendering_class="RunAnimation",
                bedrock_render_id="animation.run",
                category=RenderingPatternCategory.ANIMATION,
                conversion_notes="Run cycle animation - faster limb movement",
                animation_type="run",
            ),
            RenderingPattern(
                java_rendering_class="AttackAnimation",
                bedrock_render_id="animation.attack",
                category=RenderingPatternCategory.ANIMATION,
                conversion_notes="Attack animation - melee strike or ranged",
                animation_type="attack",
            ),
            RenderingPattern(
                java_rendering_class="DeathAnimation",
                bedrock_render_id="animation.death",
                category=RenderingPatternCategory.ANIMATION,
                conversion_notes="Death animation - entity death sequence",
                animation_type="death",
            ),
            RenderingPattern(
                java_rendering_class="SwimAnimation",
                bedrock_render_id="animation.swim",
                category=RenderingPatternCategory.ANIMATION,
                conversion_notes="Swim animation - water movement",
                animation_type="swim",
            ),
            RenderingPattern(
                java_rendering_class="FlyAnimation",
                bedrock_render_id="animation.fly",
                category=RenderingPatternCategory.ANIMATION,
                conversion_notes="Fly animation - flying entity movement",
                animation_type="fly",
            ),
        ]

        # Texture patterns - 5 patterns
        texture_patterns = [
            RenderingPattern(
                java_rendering_class="ColorTexture",
                bedrock_render_id="texture.color",
                category=RenderingPatternCategory.TEXTURE,
                conversion_notes="Standard color texture - entity base texture",
                texture_mapping="color",
            ),
            RenderingPattern(
                java_rendering_class="EmissiveTexture",
                bedrock_render_id="texture.emissive",
                category=RenderingPatternCategory.TEXTURE,
                conversion_notes="Emissive texture - glowing parts like eyes",
                texture_mapping="emissive",
            ),
            RenderingPattern(
                java_rendering_class="ArmorTexture",
                bedrock_render_id="texture.armor",
                category=RenderingPatternCategory.TEXTURE,
                conversion_notes="Armor overlay texture - armor piece rendering",
                texture_mapping="armor",
            ),
            RenderingPattern(
                java_rendering_class="NormalMapTexture",
                bedrock_render_id="texture.normal",
                category=RenderingPatternCategory.TEXTURE,
                conversion_notes="Normal map texture - surface detail",
                texture_mapping="normal",
            ),
            RenderingPattern(
                java_rendering_class="LeatherArmorTexture",
                bedrock_render_id="texture.leather",
                category=RenderingPatternCategory.TEXTURE,
                conversion_notes="Leather armor texture - brownish base",
                texture_mapping="color",
            ),
        ]

        # Render controller patterns - 3 patterns
        render_controller_patterns = [
            RenderingPattern(
                java_rendering_class="EntityRender",
                bedrock_render_id="controller.render.entity",
                category=RenderingPatternCategory.RENDER_CONTROLLER,
                conversion_notes="Entity render controller - standard entity rendering",
            ),
            RenderingPattern(
                java_rendering_class="BlockRender",
                bedrock_render_id="controller.render.block",
                category=RenderingPatternCategory.RENDER_CONTROLLER,
                conversion_notes="Block render controller - block entity rendering",
            ),
            RenderingPattern(
                java_rendering_class="ItemRender",
                bedrock_render_id="controller.render.item",
                category=RenderingPatternCategory.RENDER_CONTROLLER,
                conversion_notes="Item render controller - item entity rendering",
            ),
        ]

        # Particle patterns - 2 patterns
        particle_patterns = [
            RenderingPattern(
                java_rendering_class="ParticleEffect",
                bedrock_render_id="particle.effect",
                category=RenderingPatternCategory.PARTICLE,
                conversion_notes="Particle effect - entity-attached particles",
            ),
            RenderingPattern(
                java_rendering_class="TrailParticle",
                bedrock_render_id="particle.trail",
                category=RenderingPatternCategory.PARTICLE,
                conversion_notes="Trail particle - movement trail effect",
            ),
        ]

        # Add all patterns
        self.patterns.extend(model_patterns)
        self.patterns.extend(animation_patterns)
        self.patterns.extend(texture_patterns)
        self.patterns.extend(render_controller_patterns)
        self.patterns.extend(particle_patterns)

    def search_by_java(self, java_class: str) -> List[RenderingPattern]:
        """
        Search patterns by Java rendering class.

        Args:
            java_class: Java rendering class to search for

        Returns:
            List of matching RenderingPattern objects
        """
        results = []
        java_class_lower = java_class.lower()

        for pattern in self.patterns:
            # Check primary class
            if java_class_lower in pattern.java_rendering_class.lower():
                results.append(pattern)

        # Prioritize exact matches
        exact_matches = [p for p in results if p.java_rendering_class.lower() == java_class_lower]
        for match in exact_matches:
            results.remove(match)
            results.insert(0, match)

        return results

    def get_by_category(self, category: RenderingPatternCategory) -> List[RenderingPattern]:
        """
        Get all patterns in a category.

        Args:
            category: RenderingPatternCategory to filter by

        Returns:
            List of patterns in the category
        """
        return [p for p in self.patterns if p.category == category]

    def get_pattern_by_java_class(self, java_class: str) -> Optional[RenderingPattern]:
        """
        Get exact pattern by Java rendering class.

        Args:
            java_class: Java rendering class

        Returns:
            RenderingPattern if found, None otherwise
        """
        java_class_lower = java_class.lower()
        for pattern in self.patterns:
            if pattern.java_rendering_class.lower() == java_class_lower:
                return pattern
        return None

    def add_pattern(self, pattern: RenderingPattern) -> None:
        """
        Add a new pattern to the library.

        Args:
            pattern: RenderingPattern to add
        """
        # Check for duplicate
        for existing in self.patterns:
            if existing.java_rendering_class == pattern.java_rendering_class:
                # Update existing
                existing.bedrock_render_id = pattern.bedrock_render_id
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
RENDERING_PATTERNS = RenderingPatternLibrary()


def get_rendering_pattern(java_class: str) -> Optional[RenderingPattern]:
    """
    Get a rendering pattern by Java class.

    Args:
        java_class: Java rendering class

    Returns:
        RenderingPattern if found, None otherwise
    """
    return RENDERING_PATTERNS.get_pattern_by_java_class(java_class)


def search_rendering_patterns(query: str) -> List[RenderingPattern]:
    """
    Search rendering patterns by Java class.

    Args:
        query: Search query

    Returns:
        List of matching patterns
    """
    return RENDERING_PATTERNS.search_by_java(query)


def get_patterns_by_category(
    category: RenderingPatternCategory,
) -> List[RenderingPattern]:
    """
    Get all patterns in a category.

    Args:
        category: Category to filter by

    Returns:
        List of patterns
    """
    return RENDERING_PATTERNS.get_by_category(category)


def get_rendering_stats() -> Dict[str, int]:
    """
    Get rendering pattern library statistics.

    Returns:
        Statistics dictionary
    """
    return RENDERING_PATTERNS.get_stats()
