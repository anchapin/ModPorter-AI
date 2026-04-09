"""
Unit tests for Command/Function Conversion.

Tests the conversion of Java command classes, Minecraft functions,
scoreboard commands, and triggers to Bedrock format.
"""

import pytest
import sys
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
    get_command_pattern,
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

    def test_determine_command_type_all(self):
        """Test all branches of _determine_command_type."""
        converter = CommandConverter()
        assert converter._determine_command_type("teleport") == CommandType.TELEPORT
        assert converter._determine_command_type("spawnpoint") == CommandType.SPAWNPOINT
        assert converter._determine_command_type("spreadplayers") == CommandType.SPREADPLAYERS
        assert converter._determine_command_type("execute") == CommandType.EXECUTE
        assert converter._determine_command_type("trigger") == CommandType.TRIGGER
        assert converter._determine_command_type("scoreboard") == CommandType.SCOREBOARD
        assert converter._determine_command_type("effect") == CommandType.EFFECT
        assert converter._determine_command_type("give") == CommandType.GIVE
        assert converter._determine_command_type("difficulty") == CommandType.GAMERULE
        assert converter._determine_command_type("unknown") == CommandType.FUNCTION


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

    def test_extract_function_body_with_strings(self):
        """Test function body extraction with mix of dicts and strings."""
        converter = CommandConverter()
        java_method = {
            "body": [
                {"name": "say", "args": ["hello"]},
                "say world"
            ]
        }
        commands = converter.extract_function_body(java_method)
        assert len(commands) == 2
        assert "/say hello" in commands[0]
        assert "say world" == commands[1]

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

    def test_convert_objective_with_display(self):
        """Test objective conversion with display slot."""
        converter = ScoreboardConverter()
        java_obj = {
            "name": "test",
            "displaySlot": "sidebar"
        }
        commands = converter.convert_objective(java_obj)
        assert any("setdisplay sidebar test" in c for c in commands)

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

    def test_convert_score_operations(self):
        """Test all score operation branches."""
        converter = ScoreboardConverter()
        assert "remove" in converter.convert_score({"operation": "remove", "value": 1})
        assert "set" in converter.convert_score({"operation": "other"})

    def test_convert_operation(self):
        """Test scoreboard operation conversion."""
        converter = ScoreboardConverter()
        java_op = {
            "target": "@s",
            "objective": "obj1",
            "operation": "+=",
            "source": "@a",
            "sourceObjective": "obj2"
        }
        result = converter.convert_operation(java_op)
        assert "/scoreboard players operation @s obj1 += @a obj2" == result

    def test_convert_player_trigger(self):
        """Test ScoreboardConverter.convert_player_trigger."""
        converter = ScoreboardConverter()
        res = converter.convert_player_trigger({"objective": "obj", "value": 5})
        assert "/trigger obj add 5" == res

    def test_map_display_slot(self):
        """Test display slot mapping."""
        converter = ScoreboardConverter()
        assert converter.map_display_slot("SIDEBAR") == "sidebar"
        assert converter.map_display_slot("custom") == "custom"

    def test_convert_team_add(self):
        """Test team add command."""
        converter = ScoreboardConverter()
        java_team = {"action": "add", "name": "red", "displayName": "Red Team"}
        commands = converter.convert_team(java_team)
        assert "/team add red Red Team" in commands

    def test_convert_team_join(self):
        """Test team join command."""
        converter = ScoreboardConverter()
        java_team = {"action": "join", "name": "blue", "members": ["Alex", "Steve"]}
        commands = converter.convert_team(java_team)
        assert "/team join blue Alex" in commands
        assert "/team join blue Steve" in commands

    def test_convert_team_leave(self):
        """Test team leave command."""
        converter = ScoreboardConverter()
        java_team = {"action": "leave", "members": ["Alex"]}
        commands = converter.convert_team(java_team)
        assert "/team leave Alex" in commands

    def test_convert_team_remove_empty(self):
        """Test team remove and empty commands."""
        converter = ScoreboardConverter()
        assert "/team remove red" in converter.convert_team({"action": "remove", "name": "red"})
        assert "/team empty blue" in converter.convert_team({"action": "empty", "name": "blue"})


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

    def test_convert_conditional_block(self):
        """Test block conditional conversion."""
        converter = ExecuteConverter()
        java_conditional = {
            "type": "block",
            "value": {"position": "10 20 30", "block": "stone"},
            "command": "say yes"
        }
        result = converter.convert_conditional(java_conditional)
        assert "/execute if block 10 20 30 stone run say yes" == result

    def test_convert_conditional_score(self):
        """Test score conditional conversion."""
        converter = ExecuteConverter()
        java_conditional = {
            "type": "score",
            "value": {"player": "@p", "objective": "test", "compare": "=", "target": "10"},
            "command": "say winner"
        }
        result = converter.convert_conditional(java_conditional)
        assert "/execute if score @p test = 10 run say winner" == result

    def test_convert_conditional_fallback(self):
        """Test execute conditional fallback."""
        converter = ExecuteConverter()
        assert "/execute run say hi" == converter.convert_conditional({"type": "unknown", "command": "say hi"})

    def test_convert_selector(self):
        """Test selector conversion."""
        converter = ExecuteConverter()
        assert converter.convert_selector("@a") == "@a"
        assert converter.convert_selector("@p") == "@p"
        assert converter.convert_selector("@e") == "@e"

    def test_map_condition_type(self):
        """Test condition type mapping."""
        converter = ExecuteConverter()
        assert converter.map_condition_type("ENTITY") == "entity"


class TestArgumentParser:
    """Test cases for ArgumentParser."""

    def test_parse_player(self):
        """Test player argument parsing."""
        parser = ArgumentParser()
        assert parser.parse("player", "Alex") == "Alex"
        assert parser.parse("player", {"name": "Steve"}) == "Steve"
        assert parser.parse("player", {}) == "@p"

    def test_parse_coordinate(self):
        """Test coordinate argument parsing."""
        parser = ArgumentParser()
        assert parser.parse("coordinate", 10) == "10"
        assert parser.parse("coordinate", [1, 2, 3]) == "1 2 3"
        assert parser.parse("coordinate", {"x": 10, "y": 20, "z": 30}) == "10 20 30"
        assert parser.parse("coordinate", "invalid") == "0 0 0"

    def test_parse_item(self):
        """Test item argument parsing."""
        parser = ArgumentParser()
        assert parser.parse("item", "minecraft:apple") == "minecraft:apple"
        assert parser.parse("item", {"id": "diamond", "count": 64}) == "diamond 64"

    def test_parse_selector(self):
        """Test selector argument parsing."""
        parser = ArgumentParser()
        assert parser.parse("selector", "@a[m=creative]") == "@a[m=creative]"
        assert parser.parse("selector", {"type": "@e"}) == "@e"

    def test_parse_nbt(self):
        """Test NBT argument parsing."""
        parser = ArgumentParser()
        assert parser.parse("nbt", "{}") == "{}"
        assert parser.parse("nbt", {"Health": 20, "Name": "Zombie"}) == '{Health:20,Name:"Zombie"}'

    def test_parse_score(self):
        """Test score argument parsing."""
        parser = ArgumentParser()
        assert parser.parse("score", {"player": "@s", "objective": "test"}) == "@s test"
        assert parser.parse("score", "10") == "10"

    def test_parse_objective(self):
        """Test objective argument parsing."""
        parser = ArgumentParser()
        assert parser.parse("objective", "Kills") == "kills"

    def test_parse_default(self):
        """Test default argument parsing."""
        parser = ArgumentParser()
        assert parser.parse("unknown", "value") == "value"


class TestCommandConverterExtended:
    """Extended test cases for CommandConverter."""

    def test_convert_argument_complex(self):
        """Test complex argument conversion in CommandConverter."""
        converter = CommandConverter()
        # Test selector dict
        assert converter.convert_argument({"selector": "@a"}) == "@a"
        # Test coordinate dict
        assert converter.convert_argument({"coordinate": {"x": 1, "y": 2, "z": 3}}) == "1 2 3"
        # Test NBT dict
        assert converter.convert_argument({"nbt": {"key": "val"}}) == '{key:"val"}'
        # Test generic dict
        assert converter.convert_argument({"value": "generic"}) == "generic"
        # Test coordinate list
        assert converter.convert_argument([1.5, 2.5, 3.5]) == "1.5 2.5 3.5"
        # Test generic list
        assert converter.convert_argument(["a", "b", "c"]) == "a b c"
        # Test direct value
        assert converter.convert_argument(42) == "42"

    def test_convert_coordinate_types(self):
        """Test different coordinate input types in CommandConverter."""
        converter = CommandConverter()
        assert converter._convert_coordinate(10.5) == "10.5"
        assert converter._convert_coordinate("invalid") == "0 0 0"

    def test_convert_nbt_nested(self):
        """Test nested NBT conversion."""
        converter = CommandConverter()
        nbt = {"Outer": {"Inner": 1}, "List": "val", "Num": 42}
        result = converter._convert_nbt(nbt)
        assert "{Outer:{Inner:1},List:\"val\",Num:42}" == result

    def test_map_scoreboard_objective_complex(self):
        """Test scoreboard objective mapping with dots and spaces."""
        converter = CommandConverter()
        assert converter.map_scoreboard_objective("My Objective.1") == "my_objective_1"


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
