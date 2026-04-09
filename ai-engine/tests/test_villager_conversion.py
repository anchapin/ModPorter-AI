"""
Unit tests for Villager/Trade Conversion.

Tests the conversion of Java villager professions, careers, and trade offers
to Bedrock's villager entities, profession components, and trade tables.
"""

import pytest
import sys
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from converters.villager_converter import (
    VillagerConverter,
    TradeOfferConverter,
    VillagerProfession,
    TradeDefinition,
    convert_profession,
    convert_trade,
)
from knowledge.patterns.villager_patterns import (
    VillagerPatternLibrary,
    VillagerPatternCategory,
    VillagerPattern,
    get_villager_pattern,
    search_villager_patterns,
    get_villager_stats,
)


class TestProfessionConversion:
    """Test cases for profession conversion."""

    def test_villager_converter_initialization(self):
        """Test VillagerConverter initializes correctly."""
        converter = VillagerConverter()
        assert converter is not None
        assert len(converter.profession_map) > 0

    def test_profession_enum(self):
        """Test VillagerProfession enum values."""
        assert VillagerProfession.FARMER.value == "farmer"
        assert VillagerProfession.ARMORER.value == "armorer"
        assert VillagerProfession.LIBRARIAN.value == "librarian"
        assert VillagerProfession.NONE.value == "none"

    def test_convert_profession_basic(self):
        """Test basic profession conversion."""
        converter = VillagerConverter()

        assert converter.convert_profession("farmer") == "farmer"
        assert converter.convert_profession("armorer") == "armorer"
        assert converter.convert_profession("librarian") == "librarian"

    def test_convert_profession_with_namespace(self):
        """Test profession conversion with namespace."""
        converter = VillagerConverter()

        assert converter.convert_profession("minecraft:farmer") == "farmer"
        assert converter.convert_profession("mymod:miner") == "mason"

    def test_convert_profession_mod_fallback(self):
        """Test profession conversion for mod professions."""
        converter = VillagerConverter()

        # Mod professions should map to closest Bedrock equivalent
        assert converter.convert_profession("miner") == "mason"
        assert converter.convert_profession("fisher") == "fisherman"


class TestCareerConversion:
    """Test cases for career conversion."""

    def test_convert_career_basic(self):
        """Test basic career conversion."""
        converter = VillagerConverter()

        assert converter.convert_career("farmer") == "farmer"
        assert converter.convert_career("butcher") == "butcher"

    def test_convert_career_with_profession(self):
        """Test career conversion with profession context."""
        converter = VillagerConverter()

        career = converter.convert_career("armorer", "armorer")
        assert "armorer" in career

    def test_convert_villager_full(self):
        """Test full villager conversion."""
        converter = VillagerConverter()
        java_villager = {
            "profession": "farmer",
            "career": "farmer",
            "level": 2,
            "experience": 50,
        }
        result = converter.convert_villager(java_villager)

        assert result.profession == "farmer"
        assert result.career == "farmer"
        assert result.level == 2
        assert result.experience == 50


class TestTradeConversion:
    """Test cases for trade conversion."""

    def test_trade_converter_initialization(self):
        """Test TradeOfferConverter initializes correctly."""
        converter = TradeOfferConverter()
        assert converter is not None
        assert converter.max_uses_default == 16

    def test_convert_offer_basic(self):
        """Test basic trade offer conversion."""
        converter = TradeOfferConverter()
        result = converter.convert_offer("emerald", "diamond_sword")

        assert result.wants[0]["item"] == "minecraft:emerald"
        assert result.gives["item"] == "minecraft:diamond_sword"
        assert result.tier == 1
        assert result.max_uses == 16

    def test_convert_trade_full(self):
        """Test full trade conversion."""
        converter = TradeOfferConverter()
        java_trade = {
            "wants": [{"item": "minecraft:emerald", "quantity": 10}],
            "gives": {"item": "minecraft:diamond", "quantity": 1},
            "maxUses": 8,
            "experience": True,
            "tier": 2,
            "priceMultiplier": 1.5,
        }
        result = converter.convert_trade(java_trade)

        assert result.wants[0]["item"] == "minecraft:emerald"
        assert result.gives["item"] == "minecraft:diamond"
        assert result.max_uses == 8
        assert result.tier == 2
        assert result.price_multiplier == 1.5

    def test_convert_wants_list(self):
        """Test converting wants list."""
        converter = TradeOfferConverter()
        wants_list = [
            {"item": "minecraft:emerald", "quantity": 5},
            {"item": "minecraft:diamond", "quantity": 1},
        ]
        result = converter.convert_wants(wants_list)

        assert len(result) == 2
        assert result[0]["item"] == "minecraft:emerald"
        assert result[1]["item"] == "minecraft:diamond"

    def test_convert_merchant_recipe(self):
        """Test converting merchant recipe."""
        converter = TradeOfferConverter()
        trade = TradeDefinition(
            wants=[{"item": "minecraft:emerald", "quantity": 10}],
            gives={"item": "minecraft:diamond", "quantity": 1},
            max_uses=12,
            reward_experience=True,
            tier=2,
        )
        result = converter.convert_merchant_recipe(trade)

        assert "buy" in result
        assert "sell" in result
        assert result["maxUses"] == 12
        assert result["tier"] == 2


class TestTradeOfferConversion:
    """Test cases for trade offer conversion properties."""

    def test_convert_trade_level(self):
        """Test trade level conversion."""
        converter = TradeOfferConverter()

        assert converter.convert_trade_level(1) == 1
        assert converter.convert_trade_level(3) == 3
        assert converter.convert_trade_level(0) == 1  # Clamp min
        assert converter.convert_trade_level(10) == 5  # Clamp max

    def test_convert_max_uses(self):
        """Test max uses conversion."""
        converter = TradeOfferConverter()

        assert converter.convert_max_uses(16) == 16
        assert converter.convert_max_uses(0) == 1  # Clamp min
        assert converter.convert_max_uses(200) == 100  # Clamp max

    def test_convert_experience(self):
        """Test experience flag conversion."""
        converter = TradeOfferConverter()

        assert converter.convert_experience(True)
        assert not converter.convert_experience(False)

    def test_convert_price_adjustment(self):
        """Test price multiplier conversion."""
        converter = TradeOfferConverter()

        assert converter.convert_price_adjustment(1.0) == 1.0
        assert converter.convert_price_adjustment(0.5) == 0.5
        assert converter.convert_price_adjustment(-1.0) == 0.0  # Clamp min
        assert converter.convert_price_adjustment(20.0) == 10.0  # Clamp max


class TestVillagerPatterns:
    """Test cases for villager pattern library."""

    def test_pattern_library_initialization(self):
        """Test pattern library loads with patterns."""
        lib = VillagerPatternLibrary()
        assert len(lib.patterns) >= 20, "Should have at least 20 patterns"

    def test_pattern_search(self):
        """Test searching patterns by Java class."""
        lib = VillagerPatternLibrary()
        results = lib.search_by_java("farmer")
        assert len(results) > 0

    def test_category_filtering(self):
        """Test filtering patterns by category."""
        lib = VillagerPatternLibrary()
        agriculture_patterns = lib.get_by_category(VillagerPatternCategory.AGRICULTURE)
        assert len(agriculture_patterns) > 0
        assert all(p.category == VillagerPatternCategory.AGRICULTURE for p in agriculture_patterns)

    def test_exact_pattern_lookup(self):
        """Test exact pattern lookup by Java class."""
        pattern = get_villager_pattern("farmer")
        assert pattern is not None
        assert pattern.bedrock_profession_id == "farmer"

    def test_stats(self):
        """Test getting library statistics."""
        stats = get_villager_stats()
        assert stats["total"] >= 20
        assert "by_category" in stats
        assert "agriculture" in stats["by_category"]

    def test_search_villager_patterns(self):
        """Test searching villager patterns."""
        results = search_villager_patterns("armorer")
        assert len(results) > 0
        assert any("armorer" in p.java_profession_class for p in results)

    def test_pattern_to_dict(self):
        """Test converting pattern to dictionary."""
        pattern = VillagerPattern(
            java_profession_class="test_profession",
            bedrock_profession_id="test",
            category=VillagerPatternCategory.COMBAT,
            conversion_notes="Test pattern",
        )
        result = pattern.__dict__

        assert result["java_profession_class"] == "test_profession"
        assert result["category"] == VillagerPatternCategory.COMBAT

    def test_all_categories_present(self):
        """Test all expected categories are present."""
        lib = VillagerPatternLibrary()
        stats = lib.get_stats()

        expected_categories = [
            "agriculture",
            "combat",
            "commerce",
            "knowledge",
            "crafting",
            "service",
        ]
        for cat in expected_categories:
            assert cat in stats["by_category"], f"Missing category: {cat}"


class TestIntegration:
    """Integration tests for villager conversion."""

    def test_full_villager_conversion(self):
        """Test complete villager conversion workflow."""
        converter = VillagerConverter()

        # Convert villager
        java_villager = {
            "profession": "minecraft:librarian",
            "career": "librarian",
            "level": 3,
            "experience": 100,
        }
        villager = converter.convert_villager(java_villager)

        assert villager.profession == "librarian"
        assert villager.level == 3

    def test_pattern_with_converter(self):
        """Test villager pattern lookup combined with converter."""
        # Get pattern
        pattern = get_villager_pattern("armorer")
        assert pattern is not None

        # Use converter
        converter = VillagerConverter()
        profession = converter.convert_profession(pattern.java_profession_class)

        assert profession == "armorer"

    def test_trade_table_generation(self):
        """Test trade table JSON generation."""
        converter = VillagerConverter()
        trades = [
            TradeDefinition(
                wants=[{"item": "minecraft:emerald", "quantity": 10}],
                gives={"item": "minecraft:diamond", "quantity": 1},
            )
        ]
        result = converter.generate_trade_file("armorer", trades)

        assert "minecraft:villager_trade_table" in result
        assert "trades" in result["minecraft:villager_trade_table"]
        assert len(result["minecraft:villager_trade_table"]["trades"]) == 1

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Test convert_profession
        result = convert_profession("farmer")
        assert result == "farmer"

        # Test convert_trade
        java_trade = {
            "wants": [{"item": "minecraft:emerald", "quantity": 5}],
            "gives": {"item": "minecraft:iron_sword", "quantity": 1},
        }
        trade = convert_trade(java_trade)
        assert trade.gives["item"] == "minecraft:iron_sword"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
