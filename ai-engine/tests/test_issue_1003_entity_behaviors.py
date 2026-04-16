"""
Unit tests for Issue #1003 - Entity converter: spawn rules, loot tables, animation controllers

Tests the conversion of Java entity spawn conditions, loot tables, and
animation controllers to Bedrock format.
"""

import pytest
import sys
import json
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from converters.spawn_rule_generator import (
    SpawnRuleGenerator,
    SpawnCondition,
    generate_spawn_rules,
    write_spawn_rules_to_disk,
)
from converters.loot_table_generator import (
    LootTableGenerator,
    generate_loot_table,
    generate_entity_loot_table,
)


class TestSpawnRuleGenerator:
    """Test cases for SpawnRuleGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SpawnRuleGenerator()

    def test_spawn_rule_generator_initialization(self):
        """Test that SpawnRuleGenerator initializes correctly."""
        assert self.generator.format_version == "1.19.0"
        assert self.generator.biome_category_map is not None
        assert len(self.generator.biome_category_map) > 0

    def test_generate_spawn_rules_basic(self):
        """Test basic spawn rules generation."""
        java_entity = {
            "id": "test_zombie",
            "namespace": "testmod",
            "category": "hostile",
        }

        result = self.generator.generate_spawn_rules(java_entity)

        assert "format_version" in result
        assert "minecraft:spawn_rules" in result
        rules = result["minecraft:spawn_rules"]
        assert rules["description"]["identifier"] == "testmod:test_zombie"
        assert "conditions" in rules

    def test_generate_spawn_rules_with_biomes(self):
        """Test spawn rules with biome restrictions."""
        java_entity = {
            "id": "forest_mob",
            "namespace": "testmod",
            "category": "passive",
            "spawn_data": {
                "biomes": ["forest", "dark_forest"],
                "min_light": 7,
                "max_light": 15,
            },
        }

        result = self.generator.generate_spawn_rules(java_entity)
        conditions = result["minecraft:spawn_rules"]["conditions"]

        assert len(conditions) == 2
        assert conditions[0].get("minecraft:biome_filter") is not None

    def test_generate_spawn_rules_with_height_filter(self):
        """Test spawn rules with height restrictions."""
        java_entity = {
            "id": "cave_mob",
            "namespace": "testmod",
            "category": "hostile",
            "spawn_data": {
                "min_height": 0,
                "max_height": 50,
            },
        }

        result = self.generator.generate_spawn_rules(java_entity)
        conditions = result["minecraft:spawn_rules"]["conditions"]

        assert len(conditions) > 0
        assert conditions[0].get("minecraft:height_filter") is not None

    def test_generate_spawn_rules_hostile_defaults(self):
        """Test that hostile mobs get monster spawn conditions."""
        java_entity = {
            "id": "hostile_mob",
            "namespace": "testmod",
            "category": "hostile",
        }

        result = self.generator.generate_spawn_rules(java_entity)
        conditions = result["minecraft:spawn_rules"]["conditions"]

        assert len(conditions) > 0
        # Hostile should have light restrictions
        has_light_filter = any(
            cond.get("minecraft:brightness_filter") is not None for cond in conditions
        )
        assert has_light_filter

    def test_generate_spawn_rules_passive_defaults(self):
        """Test that passive mobs get creature spawn conditions."""
        java_entity = {
            "id": "passive_mob",
            "namespace": "testmod",
            "category": "passive",
        }

        result = self.generator.generate_spawn_rules(java_entity)
        conditions = result["minecraft:spawn_rules"]["conditions"]

        assert len(conditions) > 0

    def test_write_spawn_rules_to_disk(self, tmp_path):
        """Test writing spawn rules to disk."""
        spawn_rules = {
            "format_version": "1.19.0",
            "minecraft:spawn_rules": {
                "description": {"identifier": "testmod:test_entity"},
                "conditions": [],
            },
        }

        file_path = write_spawn_rules_to_disk(spawn_rules, tmp_path, "testmod:test_entity")

        assert file_path.exists()
        with open(file_path) as f:
            loaded = json.load(f)
        assert loaded["format_version"] == "1.19.0"


class TestLootTableGenerator:
    """Test cases for LootTableGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = LootTableGenerator()

    def test_loot_table_generator_initialization(self):
        """Test that LootTableGenerator initializes correctly."""
        assert self.generator.format_version == "1.16.0"

    def test_generate_loot_table_basic(self):
        """Test basic loot table generation."""
        java_loot_table = {
            "pools": [
                {
                    "rolls": 1,
                    "entries": [
                        {"type": "item", "name": "minecraft:diamond", "weight": 1},
                    ],
                },
            ],
        }

        result = self.generator.generate_loot_table(java_loot_table, "test_entity")

        assert result["format_version"] == "1.16.0"
        assert "pools" in result
        assert len(result["pools"]) == 1
        assert result["pools"][0]["entries"][0]["name"] == "minecraft:diamond"

    def test_generate_loot_table_with_functions(self):
        """Test loot table with functions."""
        java_loot_table = {
            "pools": [
                {
                    "rolls": 1,
                    "entries": [
                        {
                            "type": "item",
                            "name": "minecraft:diamond",
                            "weight": 1,
                            "functions": [
                                {"function": "set_count", "count": {"min": 1, "max": 3}},
                            ],
                        },
                    ],
                },
            ],
        }

        result = self.generator.generate_loot_table(java_loot_table, "test_entity")

        entry = result["pools"][0]["entries"][0]
        assert "functions" in entry
        assert entry["functions"][0]["function"] == "set_count"

    def test_generate_entity_loot_table_default(self):
        """Test default entity loot table generation."""
        result = self.generator.generate_entity_loot_table("testmod:test_entity")

        assert result["format_version"] == "1.16.0"
        assert "pools" in result
        assert len(result["pools"]) >= 1

    def test_generate_entity_loot_table_custom_drops(self):
        """Test entity loot table with custom drops."""
        drops = [
            {"item": "testmod:rare_drop", "weight": 1, "min": 1, "max": 1},
        ]

        result = self.generator.generate_entity_loot_table(
            "testmod:custom_entity",
            "testmod",
            drops,
        )

        assert "pools" in result

    def test_write_loot_table_to_disk(self, tmp_path):
        """Test writing loot table to disk."""
        loot_table = {
            "format_version": "1.16.0",
            "pools": [
                {
                    "rolls": 1,
                    "entries": [
                        {"type": "item", "name": "minecraft:diamond", "weight": 1},
                    ],
                },
            ],
        }

        file_path = self.generator.write_loot_table(loot_table, tmp_path, "test_entity")

        assert file_path.exists()
        assert "loot_tables" in str(file_path)
        assert "entities" in str(file_path)


class TestEntityConverterSpawnRulesIntegration:
    """Integration tests for spawn rules in EntityConverter."""

    def setup_method(self):
        """Set up test fixtures."""
        from agents.entity_converter import EntityConverter

        self.converter = EntityConverter()

    def test_convert_entities_generates_spawn_rules(self):
        """Test that convert_entities generates spawn rules for hostile mobs."""
        java_entities = [
            {
                "id": "hostile_zombie",
                "namespace": "testmod",
                "category": "hostile",
                "attributes": {"max_health": 30},
            },
        ]

        result = self.converter.convert_entities(java_entities)

        # Check entity was created
        assert "testmod:hostile_zombie" in result

        # Check spawn rules were generated
        spawn_rules_key = "testmod:hostile_zombie_spawn_rules"
        assert spawn_rules_key in result
        assert (
            result[spawn_rules_key]["minecraft:spawn_rules"]["description"]["identifier"]
            == "testmod:hostile_zombie"
        )

    def test_convert_entities_generates_loot_table(self):
        """Test that convert_entities generates loot tables when specified."""
        java_entities = [
            {
                "id": "loot_mob",
                "namespace": "testmod",
                "category": "hostile",
                "has_loot_table": True,
            },
        ]

        result = self.converter.convert_entities(java_entities)

        # Check loot table was generated
        loot_table_key = "testmod:loot_mob_loot_table"
        assert loot_table_key in result
        assert result[loot_table_key]["format_version"] == "1.16.0"

    def test_write_entities_to_disk_includes_spawn_rules(self, tmp_path):
        """Test that write_entities_to_disk writes spawn rules files."""
        java_entities = [
            {
                "id": "spawn_mob",
                "namespace": "testmod",
                "category": "hostile",
            },
        ]

        result = self.converter.convert_entities(java_entities)

        bp_path = tmp_path / "behavior_pack"
        rp_path = tmp_path / "resource_pack"

        written = self.converter.write_entities_to_disk(result, bp_path, rp_path)

        assert "spawn_rules" in written
        assert len(written["spawn_rules"]) > 0
        assert (bp_path / "spawn_rules").exists()

    def test_write_entities_to_disk_includes_loot_tables(self, tmp_path):
        """Test that write_entities_to_disk writes loot table files."""
        java_entities = [
            {
                "id": "loot_mob",
                "namespace": "testmod",
                "category": "hostile",
                "has_loot_table": True,
            },
        ]

        result = self.converter.convert_entities(java_entities)

        bp_path = tmp_path / "behavior_pack"
        rp_path = tmp_path / "resource_pack"

        written = self.converter.write_entities_to_disk(result, bp_path, rp_path)

        assert "loot_tables" in written


class TestAnimationControllerIntegration:
    """Integration tests for animation controllers in EntityConverter."""

    def setup_method(self):
        """Set up test fixtures."""
        from agents.entity_converter import EntityConverter

        self.converter = EntityConverter()

    def test_convert_entities_generates_animation_controllers(self):
        """Test that convert_entities generates animation controllers."""
        java_entities = [
            {
                "id": "animated_mob",
                "namespace": "testmod",
                "category": "passive",
                "animation_controllers": [
                    {
                        "controllerId": "move_controller",
                        "initialState": "idle",
                        "states": {
                            "idle": {
                                "animations": ["anim_idle"],
                                "transitions": [{"to": "walking", "condition": "is_moving"}],
                            },
                            "walking": {
                                "animations": ["anim_walk"],
                                "transitions": [{"to": "idle", "condition": "not is_moving"}],
                            },
                        },
                    },
                ],
            },
        ]

        result = self.converter.convert_entities(java_entities)

        anim_key = "testmod:animated_mob_animation_controllers"
        assert anim_key in result
        anim_data = result[anim_key]
        assert "animation_controller.move_controller" in anim_data
        assert anim_data["animation_controller.move_controller"]["initial_state"] == "idle"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
