"""
Unit tests for Dimension and World Generation Conversion.

Tests the conversion of Java dimensions, biomes, structures, and world features
to Bedrock's dimension files, biome definitions, and world generation.
"""

import pytest
import sys
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from converters.dimension_converter import (
    DimensionConverter,
    StructureConverter,
    DimensionType,
    BiomeCategory,
)
from knowledge.patterns.dimension_patterns import (
    WorldGenPatternLibrary,
    WorldGenCategory,
    WorldGenPattern,
    get_worldgen_pattern,
    search_worldgen_patterns,
    get_worldgen_stats,
)


class TestDimensionConversion:
    """Test cases for dimension conversion."""

    def test_overworld_dimension(self):
        """Test overworld dimension creation."""
        converter = DimensionConverter()
        dim = converter.create_overworld_dimension()

        assert "minecraft:dimension" in dim
        desc = dim["minecraft:dimension"]["description"]
        assert "overworld" in desc["identifier"]

    def test_nether_dimension(self):
        """Test nether dimension creation."""
        converter = DimensionConverter()
        dim = converter.create_nether_dimension()

        assert "minecraft:dimension" in dim
        desc = dim["minecraft:dimension"]["description"]
        assert "nether" in desc["identifier"]

    def test_end_dimension(self):
        """Test end dimension creation."""
        converter = DimensionConverter()
        dim = converter.create_end_dimension()

        assert "minecraft:dimension" in dim
        desc = dim["minecraft:dimension"]["description"]
        assert "the_end" in desc["identifier"]

    def test_custom_dimension(self):
        """Test custom dimension creation."""
        converter = DimensionConverter()
        props = {
            "ambient_light": 0.1,
            "has_sky_light": False,
            "has_ceiling": True,
            "ultrawarm": True,
        }
        dim = converter.create_custom_dimension(props)

        assert "minecraft:dimension" in dim
        comp = dim["minecraft:dimension"]["components"]
        assert comp["minecraft:ambient"] == 0.1
        assert comp["minecraft:has_ceiling"]

    def test_dimension_type_enum(self):
        """Test dimension type enum values."""
        assert DimensionType.OVERWORLD.value == "overworld"
        assert DimensionType.NETHER.value == "nether"
        assert DimensionType.THE_END.value == "the_end"
        assert DimensionType.CUSTOM.value == "custom"

    def test_java_dimension_conversion(self):
        """Test converting Java dimension to Bedrock."""
        converter = DimensionConverter()
        java_dim = {
            "type": "minecraft:nether",
            "ambient_light": 0.1,
            "has_sky_light": False,
        }
        result = converter.convert_dimension(java_dim)
        assert result is not None


class TestBiomeConversion:
    """Test cases for biome conversion."""

    def test_biome_mapping(self):
        """Test biome category mapping."""
        converter = DimensionConverter()

        # Test mapping
        assert converter.map_biome_category("plains") == BiomeCategory.PLAINS
        assert converter.map_biome_category("desert") == BiomeCategory.DESERT
        assert converter.map_biome_category("forest") == BiomeCategory.FOREST
        assert converter.map_biome_category("taiga") == BiomeCategory.TAIGA
        assert converter.map_biome_category("jungle") == BiomeCategory.JUNGLE

    def test_climate_settings(self):
        """Test climate settings conversion."""
        converter = DimensionConverter()
        climate = {"temperature": 0.8, "rainfall": 0.4}

        result = converter.convert_climate_settings(climate)

        assert "temperature" in result
        assert "rainfall" in result
        assert "grass_color" in result
        assert "foliage_color" in result

    def test_biome_category(self):
        """Test biome category enum values."""
        assert BiomeCategory.PLAINS.value == "plains"
        assert BiomeCategory.DESERT.value == "desert"
        assert BiomeCategory.FOREST.value == "forest"
        assert BiomeCategory.TAIGA.value == "taiga"
        assert BiomeCategory.JUNGLE.value == "jungle"

    def test_grass_color_conversion(self):
        """Test grass color based on temperature."""
        converter = DimensionConverter()

        # Cold
        color = converter.convert_grass_color(0.1, 0.5)
        assert color == 0x8BBD6B

        # Medium
        color = converter.convert_grass_color(0.5, 0.5)
        assert color == 0x91BD59

        # Warm
        color = converter.convert_grass_color(0.8, 0.5)
        assert color == 0x7BC96F

    def test_java_biome_conversion(self):
        """Test converting Java biome to Bedrock."""
        converter = DimensionConverter()
        java_biome = {
            "id": "custom_plains",
            "name": "Custom Plains",
            "category": "plains",
            "temperature": 0.8,
            "rainfall": 0.4,
        }
        result = converter.convert_biome(java_biome)

        assert result.identifier == "custom_plains"
        assert result.category == BiomeCategory.PLAINS


class TestStructureConversion:
    """Test cases for structure conversion."""

    def test_village_conversion(self):
        """Test village structure conversion."""
        converter = StructureConverter()
        result = converter.convert_structure("village")

        assert "minecraft:structure" in result
        assert "description" in result["minecraft:structure"]

    def test_ruins_conversion(self):
        """Test ruins/portal conversion."""
        converter = StructureConverter()
        java_ruins = {"type": "ruined_portal"}
        result = converter.convert_ruins(java_ruins)

        assert "minecraft:structure_template" in result

    def test_mineshaft_conversion(self):
        """Test mineshaft conversion."""
        converter = StructureConverter()
        java_mineshaft = {"type": "normal"}
        result = converter.convert_mineshaft(java_mineshaft)

        assert "minecraft:structure" in result
        assert "pool" in result["minecraft:structure"]

    def test_structure_mappings(self):
        """Test structure type mappings."""
        converter = StructureConverter()

        assert converter.get_structure_id("village") == "village"
        assert converter.get_structure_id("desert_pyramid") == "desert_pyramid"
        assert converter.get_structure_id("mineshaft") == "mineshaft"
        assert converter.get_structure_id("fortress") == "fortress"

    def test_world_preset_conversion(self):
        """Test world preset conversion."""
        converter = StructureConverter()
        result = converter.convert_world_preset("normal")

        assert "minecraft:world_generation_rules" in result


class TestFeatureConversion:
    """Test cases for feature conversion."""

    def test_tree_feature(self):
        """Test tree feature conversion."""
        converter = StructureConverter()
        java_tree = {"type": "oak", "height": 5}
        result = converter.convert_tree_feature(java_tree)

        assert "minecraft:tree" in result
        assert "trunk_provider" in result["minecraft:tree"]

    def test_ore_vein(self):
        """Test ore vein conversion."""
        converter = StructureConverter()
        java_ore = {"type": "diamond", "count": 8}
        result = converter.convert_ore_vein(java_ore)

        assert "minecraft:ore" in result
        assert "ore_provider" in result["minecraft:ore"]

    def test_cave_carver(self):
        """Test cave carver conversion."""
        converter = StructureConverter()
        result = converter.convert_world_feature("cave_carver")

        assert "minecraft:feature" in result

    def test_feature_mappings(self):
        """Test feature type mappings."""
        converter = StructureConverter()

        assert converter.get_feature_id("tree") == "tree"
        assert converter.get_feature_id("ore_coal") == "ore"
        assert converter.get_feature_id("flower") == "flower"
        assert converter.get_feature_id("grass") == "grass"

    def test_biome_layout_generation(self):
        """Test biome layout generation."""
        converter = StructureConverter()
        biomes = [
            {"name": "plains", "id": 1},
            {"name": "desert", "id": 2},
        ]
        result = converter.generate_biome_layout(biomes)

        assert "minecraft:biome" in result


class TestWorldGenPatterns:
    """Test cases for WorldGenPatternLibrary."""

    def test_pattern_library_initialization(self):
        """Test pattern library loads with patterns."""
        lib = WorldGenPatternLibrary()

        assert len(lib.patterns) >= 30, "Should have at least 30 patterns"

    def test_pattern_search(self):
        """Test searching patterns by Java type."""
        lib = WorldGenPatternLibrary()

        results = lib.search_by_java("village")

        assert len(results) > 0, "Should find village patterns"

    def test_category_filtering(self):
        """Test filtering patterns by category."""
        lib = WorldGenPatternLibrary()

        biome_patterns = lib.get_by_category(WorldGenCategory.BIOME)

        assert len(biome_patterns) > 0
        assert all(p.category == WorldGenCategory.BIOME for p in biome_patterns)

    def test_dimension_filtering(self):
        """Test filtering patterns by dimension."""
        lib = WorldGenPatternLibrary()

        overworld_patterns = lib.get_by_dimension("overworld")

        assert len(overworld_patterns) > 0
        assert all(p.dimension == "overworld" for p in overworld_patterns)

    def test_add_pattern(self):
        """Test adding new patterns."""
        lib = WorldGenPatternLibrary()

        new_pattern = WorldGenPattern(
            java_generator_type="test.custom",
            bedrock_feature_id="custom_test",
            category=WorldGenCategory.CUSTOM,
            conversion_notes="Custom test pattern",
        )

        lib.add_pattern(new_pattern)

        found = lib.get_pattern_by_java_type("test.custom")
        assert found is not None

    def test_stats(self):
        """Test getting library statistics."""
        lib = WorldGenPatternLibrary()

        stats = lib.get_stats()

        assert stats["total"] >= 30
        assert "by_category" in stats
        assert "biome" in stats["by_category"]
        assert "structure" in stats["by_category"]


class TestIntegration:
    """Integration tests for dimension/world gen conversion."""

    def test_full_dimension_pack(self):
        """Test complete dimension pack generation."""
        # Create converter
        dim_converter = DimensionConverter()
        struct_converter = StructureConverter()

        # Create dimensions
        overworld = dim_converter.create_overworld_dimension()
        nether = dim_converter.create_nether_dimension()
        end = dim_converter.create_end_dimension()

        # Create structures
        village = struct_converter.convert_structure("village")
        mineshaft = struct_converter.convert_mineshaft({"type": "normal"})

        # Verify all created
        assert overworld is not None
        assert nether is not None
        assert end is not None
        assert village is not None
        assert mineshaft is not None

    def test_pattern_lookup_integration(self):
        """Test pattern library lookup with converter."""
        # Get pattern from library
        pattern = get_worldgen_pattern("village")

        # Use pattern in converter
        if pattern:
            converter = StructureConverter()
            result = converter.convert_structure(pattern.java_generator_type)
            assert result is not None

    def test_worldgen_pattern_search_integration(self):
        """Test pattern search returns useful results."""
        results = search_worldgen_patterns("ore")

        assert len(results) > 0
        # All results should contain 'ore' in reference
        for r in results:
            assert "ore" in r.java_generator_type.lower()

    def test_worldgen_stats_integration(self):
        """Test getting worldgen statistics."""
        stats = get_worldgen_stats()

        assert stats["total"] >= 30
        assert "by_category" in stats
        assert stats["by_category"].get("ore", 0) >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
