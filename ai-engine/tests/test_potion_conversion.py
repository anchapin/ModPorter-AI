"""
Unit tests for Potion/Effect System Conversion.

Tests the conversion of Java potions, MobEffects, and status effects
to Bedrock's entity effects component and potion items.
"""

import pytest
import sys
import json
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from converters.potion_converter import (
    PotionConverter,
    CustomEffectConverter,
    EffectType,
    EffectDefinition,
    PotionItem,
    convert_effect,
    convert_potion,
    convert_custom_effect,
)
from knowledge.patterns.potion_patterns import (
    PotionPatternLibrary,
    PotionPatternCategory,
    PotionPattern,
    get_potion_pattern,
    search_potion_patterns,
    get_potion_stats,
)


class TestEffectConversion:
    """Test cases for effect conversion."""

    def test_potion_converter_initialization(self):
        """Test PotionConverter initializes correctly."""
        converter = PotionConverter()
        assert converter is not None
        assert len(converter.effect_map) > 0

    def test_effect_type_enum(self):
        """Test EffectType enum values."""
        assert EffectType.SPEED.value == "speed"
        assert EffectType.REGENERATION.value == "regeneration"
        assert EffectType.STRENGTH.value == "strength"

    def test_convert_effect_basic(self):
        """Test basic effect conversion."""
        converter = PotionConverter()
        java_effect = {
            "id": "minecraft:speed",
            "duration": 200,
            "amplifier": 0,
        }
        result = converter.convert_effect(java_effect)

        assert result.effect_id == "speed"
        assert result.duration == 10  # 200 ticks / 20 = 10 seconds
        assert result.amplifier == 0

    def test_map_mob_effect(self):
        """Test mapping Java MobEffect to Bedrock."""
        converter = PotionConverter()

        # Test standard effects
        assert converter.map_mob_effect("speed") == "speed"
        assert converter.map_mob_effect("regeneration") == "regeneration"
        assert converter.map_mob_effect("strength") == "strength"

        # Test alias
        assert converter.map_mob_effect("resistance") == "damage_resistance"

    def test_convert_duration(self):
        """Test duration conversion from ticks to seconds."""
        converter = PotionConverter()

        # 200 ticks = 10 seconds
        assert converter.convert_duration(200) == 10
        # 20 ticks = 1 second
        assert converter.convert_duration(20) == 1
        # 0 ticks should return at least 1 second
        assert converter.convert_duration(0) == 1

    def test_convert_amplifier(self):
        """Test amplifier conversion."""
        converter = PotionConverter()

        # Level 0 = amplifier 0 (Level I)
        assert converter.convert_amplifier(0) == 0
        # Level 1 = amplifier 1 (Level II)
        assert converter.convert_amplifier(1) == 1
        # Negative should clamp to 0
        assert converter.convert_amplifier(-1) == 0


class TestPotionConversion:
    """Test cases for potion conversion."""

    def test_convert_potion_basic(self):
        """Test basic potion conversion."""
        converter = PotionConverter()
        java_potion = {
            "type": "minecraft:potion",
            "effects": [{"id": "minecraft:speed", "duration": 200, "amplifier": 0}],
        }
        result = converter.convert_potion(java_potion)

        assert result.potion_type == "potion"
        assert len(result.effects) == 1
        assert result.effects[0].effect_id == "speed"

    def test_convert_potion_type(self):
        """Test potion type conversion."""
        converter = PotionConverter()

        assert converter.convert_potion_type("water") == "potion"
        assert converter.convert_potion_type("swiftness") == "potion"
        assert converter.convert_potion_type("splash") == "splash_potion"
        assert converter.convert_potion_type("lingering") == "lingering_potion"

    def test_create_potion_item(self):
        """Test creating potion item JSON."""
        converter = PotionConverter()
        effects = [
            EffectDefinition(effect_id="speed", duration=10, amplifier=0),
            EffectDefinition(effect_id="strength", duration=30, amplifier=1),
        ]
        result = converter.create_potion_item(effects)

        assert "minecraft:item" in result
        assert "minecraft:potion" in result["minecraft:item"]["components"]
        assert "effects" in result["minecraft:item"]["components"]["minecraft:potion"]

    def test_create_entity_effect_component(self):
        """Test creating entity effects component."""
        converter = PotionConverter()
        effects = [
            EffectDefinition(effect_id="speed", duration=10, amplifier=0),
        ]
        result = converter.create_entity_effect_component(effects)

        assert "minecraft:entity" in result
        assert "minecraft:entity_effects" in result["minecraft:entity"]["components"]
        assert (
            "speed"
            in result["minecraft:entity"]["components"]["minecraft:entity_effects"]["effects"]
        )

    def test_convert_empty_potion(self):
        """Test converting empty potion."""
        converter = PotionConverter()
        java_potion = {"type": "minecraft:potion", "effects": []}
        result = converter.convert_potion(java_potion)

        assert result.effects == []


class TestCustomEffectConversion:
    """Test cases for custom effect conversion."""

    def test_custom_effect_converter_initialization(self):
        """Test CustomEffectConverter initializes correctly."""
        converter = CustomEffectConverter()
        assert converter is not None

    def test_convert_custom_effect(self):
        """Test converting custom effect."""
        converter = CustomEffectConverter()
        result = converter.convert_custom_effect("my_custom_effect")

        assert result == "modporter:custom_my_custom_effect"

    def test_convert_custom_effect_with_namespace(self):
        """Test converting custom effect with namespace."""
        converter = CustomEffectConverter()
        result = converter.convert_custom_effect("mymod:my_effect")

        assert result == "modporter:custom_my_effect"

    def test_convert_particle_effect(self):
        """Test converting particle effect."""
        converter = CustomEffectConverter()
        java_particle = {
            "type": "minecraft:particle_flame",
            "offset": [0, 0.5, 0],
            "rate": 5,
        }
        result = converter.convert_particle_effect(java_particle)

        assert result["particle_type"] == "minecraft:particle_flame"
        assert result["rate"] == 5


class TestPotionPatterns:
    """Test cases for potion pattern library."""

    def test_pattern_library_initialization(self):
        """Test pattern library loads with patterns."""
        lib = PotionPatternLibrary()
        assert len(lib.patterns) >= 25, "Should have at least 25 patterns"

    def test_pattern_search(self):
        """Test searching patterns by Java class."""
        lib = PotionPatternLibrary()
        results = lib.search_by_java("speed")
        assert len(results) > 0

    def test_category_filtering(self):
        """Test filtering patterns by category."""
        lib = PotionPatternLibrary()
        positive_patterns = lib.get_by_category(PotionPatternCategory.POSITIVE)
        assert len(positive_patterns) > 0
        assert all(p.category == PotionPatternCategory.POSITIVE for p in positive_patterns)

    def test_exact_pattern_lookup(self):
        """Test exact pattern lookup by Java class."""
        pattern = get_potion_pattern("speed")
        assert pattern is not None
        assert pattern.bedrock_effect_id == "speed"

    def test_stats(self):
        """Test getting library statistics."""
        stats = get_potion_stats()
        assert stats["total"] >= 25
        assert "by_category" in stats
        assert "positive" in stats["by_category"]

    def test_search_potion_patterns(self):
        """Test searching potion patterns."""
        results = search_potion_patterns("regeneration")
        assert len(results) > 0
        assert any("regeneration" in p.java_effect_class for p in results)

    def test_pattern_to_dict(self):
        """Test converting pattern to dictionary."""
        pattern = PotionPattern(
            java_effect_class="test_effect",
            bedrock_effect_id="test",
            category=PotionPatternCategory.POSITIVE,
            conversion_notes="Test pattern",
        )
        result = pattern.__dict__

        assert result["java_effect_class"] == "test_effect"
        assert result["category"] == PotionPatternCategory.POSITIVE


class TestIntegration:
    """Integration tests for potion conversion."""

    def test_full_effect_conversion(self):
        """Test complete effect conversion workflow."""
        converter = PotionConverter()

        # Convert effect
        java_effect = {
            "id": "minecraft:regeneration",
            "duration": 400,  # 20 seconds
            "amplifier": 1,  # Level II
        }
        effect = converter.convert_effect(java_effect)

        # Create entity component
        component = converter.create_entity_effect_component([effect])

        assert "minecraft:entity_effects" in component["minecraft:entity"]["components"]
        assert (
            "regeneration"
            in component["minecraft:entity"]["components"]["minecraft:entity_effects"]["effects"]
        )

    def test_potion_pattern_with_converter(self):
        """Test potion pattern lookup combined with converter."""
        # Get pattern
        pattern = get_potion_pattern("speed")
        assert pattern is not None

        # Use converter
        converter = PotionConverter()
        effect_id = converter.map_mob_effect(pattern.java_effect_class)

        assert effect_id == "speed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
