"""
Unit tests for Command/Function Conversion.

Tests the conversion of Java command classes, Minecraft functions,
scoreboard commands, and triggers to Bedrock format.
"""

import pytest
import sys
import json
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from converters.command_converter import (
    CommandConverter,
    CommandType,
    FunctionDefinition,
    CommandResult,
    ScoreboardConverter,
    ExecuteConverter,
    ArgumentParser,
    convert_command,
    convert_function,
    generate_function_file,
    convert_trigger,
)
from knowledge.patterns.command_patterns import (
    CommandPatternLibrary,
    CommandCategory,
    CommandPattern,
    get_command_pattern,
    search_command_patterns,
    get_command_stats,
)


class TestCommandConversion:
    """Test cases for command conversion."""

    def test_command_converter_initialization(self):
        """Test CommandConverter initializes correctly."""
        converter = CommandConverter()
        assert converter is not None
        assert len(converter.command_map) > 0

    def test_command_type_enum(self):
        """Test CommandType enum values."""
        assert CommandType.TELEPORT.value == "teleport"
        assert CommandType.SUMMON.value == "summon"
        assert CommandType.GIVE.value == "give"
        assert CommandType.TRIGGER.value == "trigger"
        assert CommandType.SCOREBOARD.value == "scoreboard"

    def test_convert_command_teleport(self):
        """Test teleport command conversion."""
        converter = CommandConverter()
        java_command = {"name": "teleport", "args": ["@p", 100, 64, 100]}
        result = converter.convert_command(java_command)
        assert result.command_type == CommandType.TELEPORT
        assert "/tp" in result.bedrock_command

    def test_convert_command_summon(self):
        """Test summon command conversion."""
        converter = CommandConverter()
        java_command = {"name": "summon", "args": ["minecraft:zombie", 100, 64, 100]}
        result = converter.convert_command(java_command)
        assert result.command_type == CommandType.SUMMON
        assert "summon" in result.bedrock_command

    def test_convert_command_give(self):
        """Test give command conversion."""
        converter = CommandConverter()
        java_command = {"name": "give", "args": ["@s", "minecraft:diamond_sword", 1]}
        result = converter.convert_command(java_command)
        assert result.command_type == CommandType.GIVE
        assert "/give" in result.bedrock_command


class TestFunctionConversion:
    """Test cases for function conversion."""

    def test_convert_function_basic(self):
        """Test basic function conversion."""
        converter = CommandConverter()
        java_method = {
            "name": "test_function",
            "body": [{"name": "give", "args": ["@s", "minecraft:stone", 1]}, "say Hello"],
            "description": "Test function",
        }
        func = converter.convert_function(java_method)
        assert func.name == "test_function"
        assert len(func.commands) == 2
        assert func.description == "Test function"

    def test_extract_function_body(self):
        """Test function body extraction."""
        converter = CommandConverter()
        java_method = {
            "body": [
                {"name": "teleport", "args": ["@p", 0, 64, 0]},
                {"name": "effect", "args": ["@s", "minecraft:speed", 30, 1]},
            ]
        }
        commands = converter.extract_function_body(java_method)
        assert len(commands) == 2

    def test_generate_function_file(self):
        """Test function file generation."""
        converter = CommandConverter()
        commands = ["/say Hello", "/give @s stone 1"]
        content = converter.generate_function_file(commands)
        assert "say Hello" in content
        assert "give @s stone 1" in content

    def test_map_java_to_bedrock(self):
        """Test Java to Bedrock command mapping."""
        converter = CommandConverter()
        assert converter.map_java_to_bedrock("teleport") == "tp"
        assert converter.map_java_to_bedrock("summon") == "summon"
        assert converter.map_java_to_bedrock("experience") == "xp"

    def test_convert_trigger(self):
        """Test trigger conversion."""
        converter = CommandConverter()
        java_trigger = {"objective": "kills", "action": "add", "value": 1}
        result = converter.convert_trigger(java_trigger)
        assert "/trigger kills add 1" == result


class TestScoreboardConversion:
    """Test cases for scoreboard conversion."""

    def test_scoreboard_converter_initialization(self):
        """Test ScoreboardConverter initializes correctly."""
        converter = ScoreboardConverter()
        assert converter is not None

    def test_convert_objective(self):
        """Test objective conversion."""
        converter = ScoreboardConverter()
        java_obj = {"name": "kills", "displayName": "Kills", "criteria": "dummy"}
        commands = converter.convert_objective(java_obj)
        assert len(commands) > 0
        assert "scoreboard objectives add kills" in commands[0]

    def test_convert_score(self):
        """Test score conversion."""
        converter = ScoreboardConverter()
        java_score = {"player": "@s", "objective": "kills", "value": 5, "operation": "set"}
        result = converter.convert_score(java_score)
        assert "/scoreboard players set @s kills 5" == result

    def test_convert_score_add(self):
        """Test score add operation."""
        converter = ScoreboardConverter()
        java_score = {"player": "@s", "objective": "points", "value": 10, "operation": "add"}
        result = converter.convert_score(java_score)
        assert "/scoreboard players add @s points 10" == result


class TestExecuteConversion:
    """Test cases for execute command conversion."""

    def test_execute_converter_initialization(self):
        """Test ExecuteConverter initializes correctly."""
        converter = ExecuteConverter()
        assert converter is not None

    def test_convert_conditional_entity(self):
        """Test entity conditional conversion."""
        converter = ExecuteConverter()
        java_conditional = {
            "type": "entity",
            "value": {"selector": "@e[type=zombie]"},
            "command": "kill @s",
        }
        result = converter.convert_conditional(java_conditional)
        assert "execute as @e[type=zombie]" in result
        assert "run kill @s" in result

    def test_convert_selector(self):
        """Test selector conversion."""
        converter = ExecuteConverter()
        assert converter.convert_selector("@a") == "@a"
        assert converter.convert_selector("@p") == "@p"
        assert converter.convert_selector("@e") == "@e"


class TestCommandPatterns:
    """Test cases for command patterns."""

    def test_pattern_library_initialization(self):
        """Test CommandPatternLibrary initializes correctly."""
        lib = CommandPatternLibrary()
        assert lib is not None
        assert len(lib.patterns) >= 25

    def test_search_by_java_teleport(self):
        """Test pattern search for teleport commands."""
        lib = CommandPatternLibrary()
        patterns = lib.search_by_java("TeleportCommand")
        assert len(patterns) > 0

    def test_search_by_java_scoreboard(self):
        """Test pattern search for scoreboard commands."""
        lib = CommandPatternLibrary()
        patterns = lib.search_by_java("ScoreboardObjective")
        assert len(patterns) > 0

    def test_get_by_category(self):
        """Test pattern retrieval by category."""
        lib = CommandPatternLibrary()
        movement_patterns = lib.get_by_category(CommandCategory.MOVEMENT)
        assert len(movement_patterns) >= 2
        entity_patterns = lib.get_by_category(CommandCategory.ENTITY)
        assert len(entity_patterns) >= 5

    def test_get_pattern_stats(self):
        """Test pattern statistics."""
        stats = get_command_stats()
        assert stats["total"] >= 25
        assert "by_category" in stats


class TestIntegration:
    """Integration tests for command conversion pipeline."""

    def test_full_command_pipeline(self):
        """Test complete command conversion pipeline."""
        java_command = {"name": "give", "args": ["@s", "minecraft:diamond_sword", 1]}
        result = convert_command(java_command)
        assert isinstance(result, CommandResult)
        assert result.bedrock_command is not None

    def test_full_function_pipeline(self):
        """Test complete function conversion pipeline."""
        java_method = {
            "name": "spawn_creeper",
            "body": [
                {"name": "summon", "args": ["minecraft:creeper", "~ ~ ~"]},
                "say Creeper spawned!",
            ],
        }
        func = convert_function(java_method)
        assert isinstance(func, FunctionDefinition)

    def test_full_function_file_generation(self):
        """Test complete function file generation."""
        java_method = {"name": "test", "body": [{"name": "say", "args": ["test"]}]}
        content = generate_function_file(java_method)
        assert isinstance(content, str)
        assert len(content) > 0


class TestConvenienceFunctions:
    """Test convenience functions for command conversion."""

    def test_convert_command_function(self):
        """Test convert_command convenience function."""
        java_command = {"name": "kill", "args": ["@s"]}
        result = convert_command(java_command)
        assert isinstance(result, CommandResult)

    def test_convert_function_function(self):
        """Test convert_function convenience function."""
        java_method = {"name": "test", "body": []}
        result = convert_function(java_method)
        assert isinstance(result, FunctionDefinition)

    def test_convert_trigger_function(self):
        """Test convert_trigger convenience function."""
        java_trigger = {"objective": "test", "action": "add", "value": 1}
        result = convert_trigger(java_trigger)
        assert "/trigger" in result

    def test_pattern_lookup_function(self):
        """Test pattern lookup function."""
        pattern = get_command_pattern("TeleportCommand")
        assert pattern is not None
        assert "tp" in pattern.bedrock_command


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
