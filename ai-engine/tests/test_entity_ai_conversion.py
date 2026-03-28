"""
Unit tests for Entity AI Behavior Conversion

Tests the conversion of Java entity AI goals to Bedrock behaviors.
"""

import pytest
import sys
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from agents.entity_converter import EntityConverter, EntityType, EntityProperties
from knowledge.patterns.entity_behavior_patterns import (
    ENTITY_BEHAVIOR_PATTERNS,
    get_behavior_pattern,
    convert_java_goal_to_bedrock,
    get_entity_ai_templates,
    get_behavior_stats,
    EntityBehaviorType,
    get_behaviors_by_type,
)


class TestEntityConverter:
    """Test cases for EntityConverter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = EntityConverter()

    def test_behavior_mappings_extended(self):
        """Test that behavior_mappings has at least 25 mappings."""
        assert len(self.converter.behavior_mappings) >= 25, (
            f"Expected at least 25 behavior mappings, got {len(self.converter.behavior_mappings)}"
        )

    def test_goal_mappings_exist(self):
        """Test that goal_mappings dictionary exists and has mappings."""
        assert hasattr(self.converter, "goal_mappings"), "goal_mappings should exist"
        assert len(self.converter.goal_mappings) >= 15, (
            f"Expected at least 15 goal mappings, got {len(self.converter.goal_mappings)}"
        )

    def test_behavior_mappings_contain_common_behaviors(self):
        """Test that common behaviors are in behavior_mappings."""
        common_behaviors = [
            "follow_player",
            "melee_attack",
            "panic",
            "wander",
            "look_at_player",
            "float",
        ]
        for behavior in common_behaviors:
            assert behavior in self.converter.behavior_mappings, (
                f"Missing behavior mapping: {behavior}"
            )

    def test_hostile_mob_generation(self):
        """Test hostile mob entity generation."""
        java_entity = {
            "id": "angry_zombie",
            "namespace": "testmod",
            "category": "hostile",
            "attributes": {
                "max_health": 30.0,
                "movement_speed": 0.3,
                "attack_damage": 5.0,
            },
            "can_attack": True,
        }

        result = self.converter.generate_hostile_mob(java_entity)
        assert "minecraft:entity" in result
        assert result["minecraft:entity"]["description"]["identifier"] == "testmod:angry_zombie"

        # Check hostile components
        components = result["minecraft:entity"]["components"]
        assert "minecraft:health" in components
        assert components["minecraft:health"]["value"] == 30.0
        assert "minecraft:type_family" in components
        assert "hostile" in components["minecraft:type_family"]["family"]
        assert "minecraft:behavior.melee_attack" in components

    def test_passive_mob_generation(self):
        """Test passive mob entity generation."""
        java_entity = {
            "id": "friendly_chicken",
            "namespace": "testmod",
            "category": "passive",
            "attributes": {
                "max_health": 10.0,
                "movement_speed": 0.2,
            },
            "can_breed": True,
        }

        result = self.converter.generate_passive_mob(java_entity)
        assert "minecraft:entity" in result
        components = result["minecraft:entity"]["components"]

        # Check passive components
        assert "passive" in components["minecraft:type_family"]["family"]
        assert "minecraft:behavior.breed" in components

    def test_water_mob_generation(self):
        """Test water mob entity generation."""
        java_entity = {
            "id": "fish",
            "namespace": "testmod",
            "category": "passive",
            "can_swim": True,
            "breathes_water": True,
            "behaviors": [
                {"type": "swim", "config": {"priority": 2}},
                {"type": "flop", "config": {"priority": 1}},
            ],
        }

        result = self.converter._convert_java_entity(java_entity)
        assert "minecraft:entity" in result

    def test_ai_goals_conversion(self):
        """Test AI goals conversion to Bedrock behaviors."""
        ai_goals = [
            {"type": "look_at_player", "priority": 5, "config": {"range": 10.0}},
            {"type": "melee_attack", "priority": 3, "config": {"speed_multiplier": 1.2}},
            {"type": "wander", "priority": 6, "config": {"speed_multiplier": 0.5}},
        ]

        components = {}
        self.converter._add_ai_goals(components, ai_goals)

        assert "minecraft:behavior.look_at_player" in components
        assert components["minecraft:behavior.look_at_player"]["priority"] == 5
        assert components["minecraft:behavior.look_at_player"]["look_distance"] == 10.0

        assert "minecraft:behavior.melee_attack" in components
        assert components["minecraft:behavior.melee_attack"]["speed_multiplier"] == 1.2

        assert "minecraft:behavior.wander" in components

    def test_ai_goals_with_legacy_types(self):
        """Test AI goals with legacy/extended goal types."""
        ai_goals = [
            {"type": "move", "priority": 4, "config": {"speed": 1.0}},
            {"type": "swim", "priority": 2},
            {"type": "flee", "priority": 3, "config": {"speed": 1.5}},
        ]

        components = {}
        self.converter._add_ai_goals(components, ai_goals)

        assert "minecraft:behavior.move_towards_target" in components
        assert "minecraft:behavior.swim" in components
        assert "minecraft:behavior.avoid_entity" in components

    def test_convert_ai_goals_method(self):
        """Test the convert_ai_goals public method."""
        java_goals = [
            {"type": "panic", "priority": 1, "config": {"speed_multiplier": 1.5}},
            {"type": "breed", "priority": 4},
        ]

        result = self.converter.convert_ai_goals(java_goals)

        assert "minecraft:behavior.panic" in result
        assert "minecraft:behavior.breed" in result

    def test_behavior_config_builder(self):
        """Test behavior config building from goal config."""
        # Test melee attack config
        config = self.converter._build_behavior_config(
            "melee_attack", 3, {"speed_multiplier": 1.5, "track_target": False}
        )
        assert config["priority"] == 3
        assert config["speed_multiplier"] == 1.5
        assert config["track_target"] == False

        # Test follow config
        config = self.converter._build_behavior_config("follow", 5, {"distance": 8.0})
        assert config["priority"] == 5
        assert config["start_distance"] == 8.0
        assert config["stop_distance"] == 4.0

    def test_entity_properties_parsing(self):
        """Test entity properties parsing from Java entity."""
        java_entity = {
            "attributes": {
                "max_health": 50.0,
                "movement_speed": 0.35,
                "attack_damage": 10.0,
            },
            "category": "hostile",
            "can_swim": True,
            "can_fly": False,
        }

        properties = self.converter._parse_java_entity_properties(java_entity)

        assert properties.health == 50.0
        assert properties.movement_speed == 0.35
        assert properties.attack_damage == 10.0
        assert properties.entity_type == EntityType.HOSTILE
        assert properties.can_swim == True
        assert properties.can_fly == False


class TestEntityBehaviorPatterns:
    """Test cases for entity behavior patterns module."""

    def test_patterns_exist(self):
        """Test that entity behavior patterns are defined."""
        assert len(ENTITY_BEHAVIOR_PATTERNS) >= 20

    def test_get_behavior_pattern(self):
        """Test getting a specific behavior pattern."""
        pattern = get_behavior_pattern("melee_attack")
        assert pattern is not None
        assert pattern.bedrock_behavior == "minecraft:behavior.melee_attack"

    def test_get_behavior_pattern_not_found(self):
        """Test getting non-existent behavior pattern."""
        pattern = get_behavior_pattern("nonexistent_goal")
        assert pattern is None

    def test_convert_java_goal_to_bedrock(self):
        """Test converting Java goal to Bedrock behavior."""
        java_goal = {
            "type": "panic",
            "priority": 2,
            "config": {"speed_multiplier": 1.5},
        }

        result = convert_java_goal_to_bedrock(java_goal)

        assert "minecraft:behavior.panic" in result
        assert result["minecraft:behavior.panic"]["priority"] == 2
        assert result["minecraft:behavior.panic"]["speed_multiplier"] == 1.5

    def test_entity_ai_templates(self):
        """Test entity AI templates."""
        templates = get_entity_ai_templates()

        assert "hostile_mob" in templates
        assert "passive_mob" in templates
        assert "water_mob" in templates
        assert "flying_mob" in templates
        assert "tameable_mob" in templates
        assert "villager" in templates

    def test_hostile_mob_template(self):
        """Test hostile mob template structure."""
        templates = get_entity_ai_templates()
        hostile = templates["hostile_mob"]

        assert "behaviors" in hostile
        behavior_types = [b["type"] for b in hostile["behaviors"]]
        assert "melee_attack" in behavior_types
        assert "panic" in behavior_types

    def test_behavior_stats(self):
        """Test behavior statistics."""
        stats = get_behavior_stats()

        assert stats["total_patterns"] >= 20
        assert stats["movement_behaviors"] > 0
        assert stats["combat_behaviors"] > 0
        assert stats["entity_templates"] >= 5

    def test_get_behaviors_by_type(self):
        """Test filtering behaviors by type."""
        combat_behaviors = get_behaviors_by_type(EntityBehaviorType.COMBAT)
        assert len(combat_behaviors) > 0

        movement_behaviors = get_behaviors_by_type(EntityBehaviorType.MOVEMENT)
        assert len(movement_behaviors) > 0


class TestIntegration:
    """Integration tests for entity AI conversion."""

    def test_full_entity_conversion_with_ai_goals(self):
        """Test full entity conversion with AI goals."""
        converter = EntityConverter()

        java_entities = [
            {
                "id": "smart_zombie",
                "namespace": "testmod",
                "category": "hostile",
                "attributes": {
                    "max_health": 40.0,
                    "movement_speed": 0.28,
                    "attack_damage": 6.0,
                },
                "ai_goals": [
                    {"type": "melee_attack", "priority": 3},
                    {"type": "look_at_player", "priority": 5, "config": {"range": 10.0}},
                    {"type": "move", "priority": 4},
                    {"type": "panic", "priority": 1},
                    {"type": "wander", "priority": 6},
                ],
            }
        ]

        result = converter.convert_entities(java_entities)

        assert "testmod:smart_zombie" in result
        entity = result["testmod:smart_zombie"]
        components = entity["minecraft:entity"]["components"]

        # Verify behaviors were added
        assert "minecraft:behavior.melee_attack" in components
        assert "minecraft:behavior.look_at_player" in components
        assert "minecraft:behavior.move_towards_target" in components
        assert "minecraft:behavior.panic" in components
        assert "minecraft:behavior.wander" in components

    def test_mixed_entity_types(self):
        """Test converting different entity types."""
        converter = EntityConverter()

        entities = [
            {
                "id": "hostile_creeper",
                "namespace": "testmod",
                "category": "hostile",
            },
            {
                "id": "passive_cow",
                "namespace": "testmod",
                "category": "passive",
                "can_breed": True,
            },
        ]

        result = converter.convert_entities(entities)

        assert "testmod:hostile_creeper" in result
        assert "testmod:passive_cow" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
