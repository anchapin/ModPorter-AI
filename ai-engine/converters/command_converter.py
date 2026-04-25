"""
Command and Function Converter for converting Java command systems to Bedrock format.

Converts Java command classes, Minecraft functions, commands, and triggers
to Bedrock's .mcfunction format, scoreboard commands, and /trigger system.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Bedrock command types."""

    EXECUTE = "execute"
    FUNCTION = "function"
    TRIGGER = "trigger"
    SCOREBOARD = "scoreboard"
    TAG = "tag"
    DATA = "data"
    TITLE = "title"
    TELLRAW = "tellraw"
    SPAWNPOINT = "spawnpoint"
    TELEPORT = "teleport"
    GIVE = "give"
    CLEAR = "clear"
    REPLACEITEM = "replaceitem"
    EFFECT = "effect"
    XP = "xp"
    SUMMON = "summon"
    KILL = "kill"
    DIFFICULTY = "difficulty"
    TIME = "time"
    WEATHER = "weather"
    GAMERULE = "gamerule"
    SPREADPLAYERS = "spreadplayers"


@dataclass
class FunctionDefinition:
    """Represents a Bedrock function file."""

    name: str
    commands: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class CommandResult:
    """Result of command conversion."""

    bedrock_command: str
    command_type: CommandType
    dependencies: List[str] = field(default_factory=list)


class CommandConverter:
    """
    Converter for Java commands to Bedrock format.

    Handles conversion of Java command classes with @Command annotations,
    CommandSender interfaces, and custom argument types to Bedrock's
    function system and command framework.
    """

    def __init__(self):
        """Initialize the CommandConverter."""
        self.command_map = self._build_command_map()
        self.argument_parser = ArgumentParser()

    def _build_command_map(self) -> Dict[str, str]:
        """Build Java to Bedrock command mapping."""
        return {
            # Movement commands
            "teleport": "tp",
            "teleport_relative": "tp",
            "spawnpoint": "spawnpoint",
            "spreadplayers": "spreadplayers",
            # Entity commands
            "summon": "summon",
            "kill": "kill",
            "effect": "effect",
            "xp": "xp",
            "experience": "xp",
            # Item commands
            "give": "give",
            "clear": "clear",
            "replaceitem": "replaceitem",
            # Game state commands
            "difficulty": "difficulty",
            "time": "time",
            "weather": "weather",
            "gamerule": "gamerule",
        }

    def convert_command(self, java_command: Dict[str, Any]) -> CommandResult:
        """
        Convert Java command to Bedrock command.

        Args:
            java_command: Java command dictionary

        Returns:
            CommandResult with converted command
        """
        command_name = java_command.get("name", "").lower()
        args = java_command.get("args", [])
        options = java_command.get("options", {})

        # Map command name
        bedrock_cmd = self.command_map.get(command_name, command_name)

        # Convert arguments
        converted_args = []
        for arg in args:
            converted = self.convert_argument(arg)
            converted_args.append(converted)

        # Build full command
        full_command = f"/{bedrock_cmd} {' '.join(converted_args)}"

        # Determine command type
        cmd_type = self._determine_command_type(command_name)

        return CommandResult(
            bedrock_command=full_command,
            command_type=cmd_type,
            dependencies=[],
        )

    def convert_function(self, java_method: Dict[str, Any]) -> FunctionDefinition:
        """
        Convert Java method to Bedrock function.

        Args:
            java_method: Java method dictionary

        Returns:
            FunctionDefinition object
        """
        func_name = java_method.get("name", "unnamed_function")
        body = java_method.get("body", [])
        description = java_method.get("description", "")

        commands = []
        for cmd in body:
            if isinstance(cmd, dict):
                result = self.convert_command(cmd)
                commands.append(result.bedrock_command)
            elif isinstance(cmd, str):
                commands.append(cmd)

        return FunctionDefinition(
            name=func_name,
            commands=commands,
            description=description,
        )

    def convert_argument(self, java_arg: Any) -> str:
        """
        Convert Java argument to Bedrock command argument.

        Args:
            java_arg: Java argument (can be string, dict, or list)

        Returns:
            Converted argument string
        """
        if isinstance(java_arg, dict):
            # Handle special argument types
            if "selector" in java_arg:
                return self._convert_selector(java_arg["selector"])
            elif "coordinate" in java_arg:
                return self._convert_coordinate(java_arg["coordinate"])
            elif "nbt" in java_arg:
                return self._convert_nbt(java_arg["nbt"])
            else:
                # Generic key-value
                return str(java_arg.get("value", ""))
        elif isinstance(java_arg, list):
            # Handle coordinate arrays [x, y, z]
            if len(java_arg) == 3 and all(isinstance(c, (int, float)) for c in java_arg):
                return f"{java_arg[0]} {java_arg[1]} {java_arg[2]}"
            return " ".join(str(x) for x in java_arg)
        else:
            return str(java_arg)

    def extract_function_body(self, java_method: Dict[str, Any]) -> List[str]:
        """
        Extract function body from Java method.

        Args:
            java_method: Java method dictionary

        Returns:
            List of command strings
        """
        body = java_method.get("body", [])
        commands = []

        for item in body:
            if isinstance(item, dict):
                result = self.convert_command(item)
                commands.append(result.bedrock_command)
            elif isinstance(item, str):
                commands.append(item)

        return commands

    def map_java_to_bedrock(self, java_command: str) -> str:
        """
        Map Java command name to Bedrock equivalent.

        Args:
            java_command: Java command name

        Returns:
            Bedrock command name
        """
        return self.command_map.get(java_command.lower(), java_command.lower())

    def generate_function_file(self, commands: List[str]) -> str:
        """
        Generate .mcfunction file content.

        Args:
            commands: List of commands

        Returns:
            Function file content as string
        """
        return "\n".join(commands)

    def convert_trigger(self, java_trigger: Dict[str, Any]) -> str:
        """
        Convert Java trigger to /trigger command.

        Args:
            java_trigger: Java trigger dictionary

        Returns:
            /trigger command string
        """
        objective = java_trigger.get("objective", "default")
        action = java_trigger.get("action", "add")
        value = java_trigger.get("value", 1)

        return f"/trigger {objective} {action} {value}"

    def map_scoreboard_objective(self, java_obj: str) -> str:
        """
        Map Java scoreboard objective to Bedrock.

        Args:
            java_obj: Java objective name

        Returns:
            Bedrock objective name
        """
        # Most Java objective names work directly in Bedrock
        return java_obj.lower().replace(".", "_").replace(" ", "_")

    def _determine_command_type(self, command_name: str) -> CommandType:
        """Determine command type from command name."""
        if command_name in ["teleport", "teleport_relative"]:
            return CommandType.TELEPORT
        elif command_name == "spawnpoint":
            return CommandType.SPAWNPOINT
        elif command_name == "spreadplayers":
            return CommandType.SPREADPLAYERS
        elif command_name in ["summon", "kill"]:
            return CommandType.SUMMON
        elif command_name in ["effect", "xp", "experience"]:
            return CommandType.EFFECT
        elif command_name in ["give", "clear", "replaceitem"]:
            return CommandType.GIVE
        elif command_name in ["difficulty", "time", "weather", "gamerule"]:
            return CommandType.GAMERULE
        elif command_name == "execute":
            return CommandType.EXECUTE
        elif command_name == "trigger":
            return CommandType.TRIGGER
        elif command_name == "scoreboard":
            return CommandType.SCOREBOARD
        else:
            return CommandType.FUNCTION

    def _convert_selector(self, selector: str) -> str:
        """Convert entity selector."""
        # Common selector mappings
        selector_map = {
            "@a": "@a",
            "@p": "@p",
            "@s": "@s",
            "@e": "@e",
            "@r": "@r",
        }
        return selector_map.get(selector.lower(), selector)

    def _convert_coordinate(self, coord: Any) -> str:
        """Convert coordinate."""
        if isinstance(coord, (int, float)):
            return str(coord)
        elif isinstance(coord, dict):
            return f"{coord.get('x', 0)} {coord.get('y', 0)} {coord.get('z', 0)}"
        return "0 0 0"

    def _convert_nbt(self, nbt: Dict[str, Any]) -> str:
        """Convert NBT data."""
        nbt_str = []
        for key, value in nbt.items():
            if isinstance(value, dict):
                nbt_str.append(f"{key}:{self._convert_nbt(value)}")
            elif isinstance(value, str):
                nbt_str.append(f'{key}:"{value}"')
            else:
                nbt_str.append(f"{key}:{value}")
        return "{" + ",".join(nbt_str) + "}"


class ArgumentParser:
    """Parser for command arguments."""

    def parse(self, arg_type: str, value: Any) -> str:
        """
        Parse argument based on type.

        Args:
            arg_type: Argument type
            value: Argument value

        Returns:
            Parsed argument string
        """
        parsers = {
            "player": self._parse_player,
            "coordinate": self._parse_coordinate,
            "item": self._parse_item,
            "selector": self._parse_selector,
            "nbt": self._parse_nbt,
            "score": self._parse_score,
            "objective": self._parse_objective,
        }

        parser = parsers.get(arg_type.lower(), self._parse_default)
        return parser(value)

    def _parse_player(self, value: Any) -> str:
        """Parse player argument."""
        if isinstance(value, str):
            return value
        return str(value.get("name", "@p"))

    def _parse_coordinate(self, value: Any) -> str:
        """Parse coordinate argument."""
        if isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            return f"{value[0]} {value[1]} {value[2]}"
        elif isinstance(value, dict):
            x = value.get("x", 0)
            y = value.get("y", 0)
            z = value.get("z", 0)
            return f"{x} {y} {z}"
        return "0 0 0"

    def _parse_item(self, value: Any) -> str:
        """Parse item argument."""
        if isinstance(value, str):
            return value
        item_id = value.get("id", "minecraft:stone")
        count = value.get("count", 1)
        return f"{item_id} {count}"

    def _parse_selector(self, value: Any) -> str:
        """Parse selector argument."""
        if isinstance(value, str):
            return value
        selector_type = value.get("type", "@p")
        return selector_type

    def _parse_nbt(self, value: Any) -> str:
        """Parse NBT argument."""
        if isinstance(value, str):
            return value
        # Simple NBT to string conversion
        nbt_parts = []
        for k, v in value.items():
            if isinstance(v, str):
                nbt_parts.append(f'{k}:"{v}"')
            else:
                nbt_parts.append(f"{k}:{v}")
        return "{" + ",".join(nbt_parts) + "}"

    def _parse_score(self, value: Any) -> str:
        """Parse score argument."""
        if isinstance(value, dict):
            player = value.get("player", "@s")
            objective = value.get("objective", "dummy")
            return f"{player} {objective}"
        return str(value)

    def _parse_objective(self, value: Any) -> str:
        """Parse objective argument."""
        return str(value).lower()

    def _parse_default(self, value: Any) -> str:
        """Default parser."""
        return str(value)


class ScoreboardConverter:
    """
    Converter for Java scoreboard/trigger systems to Bedrock format.

    Handles conversion of scoreboard objectives, player scores, trigger
    commands, team management, and execute command conditions.
    """

    # Scoreboard operation mappings
    OPERATIONS = {
        "=": "=",
        "+=": "+=",
        "-=": "-=",
        "*=": "*=",
        "/=": "/=",
        "%=": "%=",
        "<": "<",
        ">": ">",
        "><": "><",
    }

    # Display slot mappings
    DISPLAY_SLOTS = {
        "sidebar": "sidebar",
        "list": "list",
        "belowname": "belowname",
        "sidebar.team.red": "sidebar.team.red",
        "sidebar.team.blue": "sidebar.team.blue",
        "sidebar.team.green": "sidebar.team.green",
        "sidebar.team.yellow": "sidebar.team.yellow",
    }

    def __init__(self):
        """Initialize the ScoreboardConverter."""
        self.default_criteria = "dummy"

    def convert_objective(self, java_obj: Dict[str, Any]) -> List[str]:
        """
        Convert Java scoreboard objective to Bedrock commands.

        Args:
            java_obj: Java objective dictionary

        Returns:
            List of scoreboard commands
        """
        commands = []

        name = java_obj.get("name", "objective")
        display_name = java_obj.get("displayName", name)
        criteria = java_obj.get("criteria", self.default_criteria)

        # Create objective command
        cmd = f"/scoreboard objectives add {name} {criteria} {display_name}"
        commands.append(cmd)

        # Handle display if specified
        if "displaySlot" in java_obj:
            slot = self.map_display_slot(java_obj["displaySlot"])
            commands.append(f"/scoreboard objectives setdisplay {slot} {name}")

        return commands

    def convert_score(self, java_score: Dict[str, Any]) -> str:
        """
        Convert Java player score to Bedrock command.

        Args:
            java_score: Java score dictionary

        Returns:
            Scoreboard set command
        """
        player = java_score.get("player", "@s")
        objective = java_score.get("objective", "dummy")
        value = java_score.get("value", 0)
        operation = java_score.get("operation", "set")

        if operation == "set":
            return f"/scoreboard players set {player} {objective} {value}"
        elif operation == "add":
            return f"/scoreboard players add {player} {objective} {value}"
        elif operation == "remove":
            return f"/scoreboard players remove {player} {objective} {value}"
        else:
            return f"/scoreboard players set {player} {objective} {value}"

    def convert_player_trigger(self, java_trigger: Dict[str, Any]) -> str:
        """
        Convert Java trigger to /trigger command.

        Args:
            java_trigger: Java trigger dictionary

        Returns:
            /trigger command
        """
        objective = java_trigger.get("objective", "trigger")
        action = java_trigger.get("action", "add")
        value = java_trigger.get("value", 1)

        return f"/trigger {objective} {action} {value}"

    def convert_operation(self, java_op: Dict[str, Any]) -> str:
        """
        Convert Java scoreboard operation to Bedrock command.

        Args:
            java_op: Java operation dictionary

        Returns:
            Scoreboard operation command
        """
        target = java_op.get("target", "@s")
        objective = java_op.get("objective", "dummy")
        operation = java_op.get("operation", "=")
        source = java_op.get("source", "@s")
        source_objective = java_op.get("sourceObjective", "dummy")

        op_symbol = self.OPERATIONS.get(operation, "=")

        return f"/scoreboard players operation {target} {objective} {op_symbol} {source} {source_objective}"

    def map_display_slot(self, slot: str) -> str:
        """
        Map Java display slot to Bedrock.

        Args:
            slot: Display slot name

        Returns:
            Bedrock display slot
        """
        return self.DISPLAY_SLOTS.get(slot.lower(), slot.lower())

    def convert_team(self, java_team: Dict[str, Any]) -> List[str]:
        """
        Convert Java team commands to Bedrock.

        Args:
            java_team: Java team dictionary

        Returns:
            List of team commands
        """
        commands = []
        action = java_team.get("action", "add")

        if action == "add":
            team_name = java_team.get("name", "team")
            display_name = java_team.get("displayName", team_name)
            commands.append(f"/team add {team_name} {display_name}")

        elif action == "remove":
            team_name = java_team.get("name", "team")
            commands.append(f"/team remove {team_name}")

        elif action == "join":
            team_name = java_team.get("name", "team")
            members = java_team.get("members", ["@s"])
            for member in members:
                commands.append(f"/team join {team_name} {member}")

        elif action == "leave":
            members = java_team.get("members", ["@s"])
            for member in members:
                commands.append(f"/team leave {member}")

        elif action == "empty":
            team_name = java_team.get("name", "team")
            commands.append(f"/team empty {team_name}")

        return commands


class ExecuteConverter:
    """
    Converter for Java execute commands to Bedrock format.

    Handles conversion of execute subcommands, conditions, and
    entity selectors.
    """

    # Condition type mappings
    CONDITION_MAP = {
        "entity": "entity",
        "block": "block",
        "score": "score",
        "predicate": "predicate",
        "data": "data",
        "if_unless": "if",
    }

    def __init__(self):
        """Initialize the ExecuteConverter."""
        self.selector_map = self._build_selector_map()

    def _build_selector_map(self) -> Dict[str, str]:
        """Build selector mapping."""
        return {
            "@a": "@a",
            "@p": "@p",
            "@s": "@s",
            "@e": "@e",
            "@r": "@r",
            "@initiator": "@initiator",
        }

    def convert_conditional(self, java_conditional: Dict[str, Any]) -> str:
        """
        Convert Java conditional to execute command.

        Args:
            java_conditional: Java conditional dictionary

        Returns:
            Execute command string
        """
        condition_type = java_conditional.get("type", "entity")
        condition_value = java_conditional.get("value", {})
        command = java_conditional.get("command", "")

        condition_key = self.CONDITION_MAP.get(condition_type, condition_type)

        if condition_type == "entity":
            selector = self.convert_selector(condition_value.get("selector", "@e"))
            return f"/execute as {selector} at @s run {command}"

        elif condition_type == "block":
            pos = condition_value.get("position", "~ ~ ~")
            block_type = condition_value.get("block", "minecraft:air")
            return f"/execute if block {pos} {block_type} run {command}"

        elif condition_type == "score":
            player = condition_value.get("player", "@s")
            objective = condition_value.get("objective", "dummy")
            compare = condition_value.get("compare", ">=")
            target = condition_value.get("target", "0")
            return f"/execute if score {player} {objective} {compare} {target} run {command}"

        return f"/execute run {command}"

    def convert_selector(self, selector: str) -> str:
        """
        Convert entity selector.

        Args:
            selector: Java selector string

        Returns:
            Bedrock selector
        """
        return self.selector_map.get(selector.lower(), selector)

    def map_condition_type(self, java_type: str) -> str:
        """
        Map Java condition type to Bedrock.

        Args:
            java_type: Java condition type

        Returns:
            Bedrock condition type
        """
        return self.CONDITION_MAP.get(java_type.lower(), java_type.lower())


# Convenience functions
def convert_command(java_command: Dict[str, Any]) -> CommandResult:
    """Convert Java command to Bedrock command."""
    converter = CommandConverter()
    return converter.convert_command(java_command)


def convert_function(java_method: Dict[str, Any]) -> FunctionDefinition:
    """Convert Java method to Bedrock function."""
    converter = CommandConverter()
    return converter.convert_function(java_method)


def generate_function_file(java_method: Dict[str, Any]) -> str:
    """Generate .mcfunction file content."""
    converter = CommandConverter()
    func = converter.convert_function(java_method)
    return converter.generate_function_file(func.commands)


def convert_trigger(java_trigger: Dict[str, Any]) -> str:
    """Convert Java trigger to /trigger command."""
    converter = CommandConverter()
    return converter.convert_trigger(java_trigger)
