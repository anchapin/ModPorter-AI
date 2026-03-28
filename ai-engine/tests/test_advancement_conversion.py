"""
Unit tests for Advancement System Conversion.

Tests the conversion of Java advancements, criteria, rewards,
and achievements to Bedrock's achievement system.
"""

import pytest
import sys
import json
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from converters.advancement_converter import (
    AdvancementConverter,
    AdvancementCategory,
    AdvancementDefinition,
    AdvancementDisplay,
    AdvancementCriteria,
    AdvancementRewards,
    CriteriaConverter,
    ToastNotification,
)
from knowledge.patterns.advancement_patterns import (
    AdvancementPatternLibrary,
    AdvancementPatternCategory,
    AdvancementPattern,
    get_advancement_pattern,
    search_advancement_patterns,
    get_advancement_stats,
)


class TestAdvancementConversion:
    """Test cases for advancement conversion."""

    def test_advancement_converter_initialization(self):
        """Test AdvancementConverter initializes correctly."""
        converter = AdvancementConverter()
        assert converter is not None
        assert len(converter.trigger_map) > 0

    def test_advancement_category_enum(self):
        """Test AdvancementCategory enum values."""
        assert AdvancementCategory.TASK.value == "task"
        assert AdvancementCategory.CHALLENGE.value == "challenge"
        assert AdvancementCategory.GOAL.value == "goal"

    def test_convert_advancement_basic(self):
        """Test basic advancement conversion."""
        converter = AdvancementConverter()
        java_adv = {
            "id": "test_advancement",
            "parent": "minecraft:story/root",
            "display": {
                "title": "Test Achievement",
                "description": "A test achievement",
                "icon": {"item": "minecraft:stone"},
                "frame": "task",
            },
            "criteria": {
                "test_criterion": {
                    "trigger": "minecraft:inventory_changed",
                    "conditions": {"items": ["minecraft:stone"]},
                }
            },
        }
        result = converter.convert_advancement(java_adv)

        assert result.advancement_id == "test_advancement"
        assert result.parent == "story/root"
        assert result.display is not None

    def test_convert_parent(self):
        """Test parent advancement conversion."""
        converter = AdvancementConverter()

        # Test with namespace
        result = converter.convert_parent("minecraft:story/root")
        assert result == "story/root"

        # Test without namespace
        result = converter.convert_parent("story/root")
        assert result == "story/root"

        # Test None
        result = converter.convert_parent(None)
        assert result is None

    def test_map_display_info(self):
        """Test display info mapping."""
        converter = AdvancementConverter()
        java_display = {
            "title": "Stone Miner",
            "description": "Mine a piece of stone",
            "icon": {"item": "minecraft:stone"},
            "frame": "task",
        }
        result = converter.map_display_info(java_display)

        assert result.title == "Stone Miner"
        assert result.description == "Mine a piece of stone"
        assert "stone" in result.icon
        assert result.frame_type == "task"

    def test_generate_advancement_file(self):
        """Test generating advancement JSON file."""
        converter = AdvancementConverter()
        advancement = AdvancementDefinition(
            advancement_id="test",
            display=AdvancementDisplay(
                title="Test",
                description="Test description",
                icon="textures/blocks/stone.png",
            ),
            criteria=AdvancementCriteria(
                criteria={"test": {"trigger": "minecraft:tick", "conditions": {}}},
                requirements=[["test"]],
            ),
        )
        result = converter.generate_advancement_file(advancement)

        assert "minecraft:advancement" in result
        assert result["minecraft:advancement"]["id"] == "modporter:test"


class TestCriteriaConversion:
    """Test cases for criteria conversion."""

    def test_criteria_converter_initialization(self):
        """Test CriteriaConverter initializes correctly."""
        converter = CriteriaConverter()
        assert converter is not None

    def test_convert_trigger_inventory_changed(self):
        """Test converting inventory_changed trigger."""
        converter = CriteriaConverter()
        result = converter.convert_trigger("minecraft:inventory_changed")
        assert result == "minecraft:inventory_changed"

    def test_convert_trigger_player_killed_entity(self):
        """Test converting player_killed_entity trigger."""
        converter = CriteriaConverter()
        result = converter.convert_trigger("minecraft:player_killed_entity")
        assert result == "minecraft:player_killed_entity"

    def test_convert_trigger_tick(self):
        """Test converting tick trigger."""
        converter = CriteriaConverter()
        result = converter.convert_trigger("minecraft:tick")
        assert result == "minecraft:tick"

    def test_convert_trigger_location(self):
        """Test converting location trigger."""
        converter = CriteriaConverter()
        result = converter.convert_trigger("minecraft:location")
        assert result == "minecraft:location"

    def test_convert_conditions(self):
        """Test converting conditions."""
        converter = CriteriaConverter()
        java_conditions = {
            "items": ["minecraft:stone", "minecraft:dirt"],
        }
        result = converter.convert_conditions(java_conditions)

        assert "items" in result
        assert len(result["items"]) == 2


class TestRewardConversion:
    """Test cases for reward conversion."""

    def test_convert_item_rewards(self):
        """Test converting item rewards."""
        converter = AdvancementConverter()
        java_items = [
            {"id": "minecraft:diamond", "count": 1},
            {"id": "minecraft:iron_ingot", "count": 5},
        ]
        result = converter.convert_rewards({"items": java_items})

        assert len(result.items) == 2

    def test_convert_recipe_rewards(self):
        """Test converting recipe rewards."""
        converter = AdvancementConverter()
        java_rewards = {
            "recipes": ["minecraft:iron_sword", "minecraft:iron_pickaxe"],
        }
        result = converter.convert_rewards(java_rewards)

        assert len(result.recipes) == 2

    def test_convert_experience_rewards(self):
        """Test converting experience rewards."""
        converter = AdvancementConverter()
        java_rewards = {"experience": 50}
        result = converter.convert_rewards(java_rewards)

        assert result.experience == 50

    def test_convert_empty_rewards(self):
        """Test converting empty rewards."""
        converter = AdvancementConverter()
        result = converter.convert_rewards({})

        assert result.items == []
        assert result.recipes == []
        assert result.experience == 0


class TestAdvancementPatterns:
    """Test cases for advancement pattern library."""

    def test_pattern_library_initialization(self):
        """Test pattern library loads with patterns."""
        lib = AdvancementPatternLibrary()
        assert len(lib.patterns) >= 25, "Should have at least 25 patterns"

    def test_pattern_search(self):
        """Test searching patterns by Java class."""
        lib = AdvancementPatternLibrary()
        results = lib.search_by_java("mine_stone")
        assert len(results) > 0

    def test_category_filtering(self):
        """Test filtering patterns by category."""
        lib = AdvancementPatternLibrary()
        inventory_patterns = lib.get_by_category(AdvancementPatternCategory.INVENTORY)
        assert len(inventory_patterns) > 0
        assert all(p.category == AdvancementPatternCategory.INVENTORY for p in inventory_patterns)

    def test_exact_pattern_lookup(self):
        """Test exact pattern lookup by Java class."""
        pattern = get_advancement_pattern("mine_stone")
        assert pattern is not None
        assert pattern.bedrock_requirement == "minecraft:inventory_changed"

    def test_stats(self):
        """Test getting library statistics."""
        stats = get_advancement_stats()
        assert stats["total"] >= 25
        assert "by_category" in stats
        assert "inventory" in stats["by_category"]

    def test_search_advancement_patterns(self):
        """Test searching advancement patterns."""
        results = search_advancement_patterns("kill_mob")
        assert len(results) > 0
        assert any("kill_mob" in p.java_criteria_class for p in results)

    def test_pattern_to_dict(self):
        """Test converting pattern to dictionary."""
        pattern = AdvancementPattern(
            java_criteria_class="test",
            bedrock_requirement="minecraft:test",
            category=AdvancementPatternCategory.INVENTORY,
            conversion_notes="Test pattern",
        )
        result = pattern.to_dict()

        assert result["java_criteria_class"] == "test"
        assert result["category"] == "inventory"


class TestIntegration:
    """Integration tests for advancement conversion."""

    def test_full_advancement_conversion(self):
        """Test complete advancement conversion workflow."""
        converter = AdvancementConverter()

        # Convert advancement
        java_adv = {
            "id": "mine_stone",
            "parent": "minecraft:story/mine_stone",
            "display": {
                "title": "Stone Miner",
                "description": "Mine a piece of stone",
                "icon": {"item": "minecraft:stone"},
                "frame": "task",
            },
            "criteria": {
                "mine_stone": {
                    "trigger": "minecraft:inventory_changed",
                    "conditions": {"items": ["minecraft:stone"]},
                }
            },
            "rewards": {
                "items": [{"id": "minecraft:stone", "count": 1}],
                "experience": 10,
            },
        }
        advancement = converter.convert_advancement(java_adv)

        # Generate JSON
        adv_json = converter.generate_advancement_file(advancement)

        assert "minecraft:advancement" in adv_json
        assert "display" in adv_json["minecraft:advancement"]
        assert "criteria" in adv_json["minecraft:advancement"]

    def test_advancement_pattern_with_converter(self):
        """Test advancement pattern lookup combined with converter."""
        # Get pattern
        pattern = get_advancement_pattern("mine_stone")
        assert pattern is not None

        # Use converter
        converter = CriteriaConverter()
        requirement = converter.convert_trigger(pattern.bedrock_requirement)

        assert requirement == "minecraft:inventory_changed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
