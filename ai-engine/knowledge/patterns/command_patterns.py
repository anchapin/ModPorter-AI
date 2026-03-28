"""
Command Pattern Library for RAG-based command conversion.

Provides pattern matching and retrieval for Java to Bedrock command
and function conversion patterns.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class CommandCategory(Enum):
    """Command pattern categories."""

    MOVEMENT = "movement"
    TELEPORT = "teleport"
    ENTITY = "entity"
    ITEM = "item"
    GAMESTATE = "gamestate"
    SCOREBOARD = "scoreboard"
    TRIGGER = "trigger"
    FUNCTION = "function"
    DATA = "data"
    TITLE = "title"


@dataclass
class CommandPattern:
    """
    Represents a single command conversion pattern.

    Contains Java command class reference and corresponding Bedrock
    command with conversion notes and category.
    """

    java_command_class: str
    bedrock_command: str
    category: CommandCategory
    conversion_notes: str
    arguments: Optional[List[str]] = None
    examples: Optional[List[str]] = None


class CommandPatternLibrary:
    """
    Library of command conversion patterns.

    Provides storage, retrieval, and search functionality for
    Java→Bedrock command conversion patterns.
    """

    def __init__(self):
        """Initialize pattern library with default patterns."""
        self.patterns: List[CommandPattern] = []
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default command patterns (25+ patterns)."""

        # Movement commands - 3 patterns
        movement_patterns = [
            CommandPattern(
                java_command_class="TeleportCommand",
                bedrock_command="/tp <targets> <destination>",
                category=CommandCategory.TELEPORT,
                conversion_notes="Teleport entities to coordinates or other entities",
                arguments=["targets", "destination"],
                examples=["/tp @p 100 64 100", "/tp @s @r"],
            ),
            CommandPattern(
                java_command_class="SpawnpointCommand",
                bedrock_command="/spawnpoint [player] [pos]",
                category=CommandCategory.MOVEMENT,
                conversion_notes="Set spawn point for player",
                arguments=["player", "x", "y", "z"],
                examples=["/spawnpoint @a 0 64 0"],
            ),
            CommandPattern(
                java_command_class="SpreadplayersCommand",
                bedrock_command="/spreadplayers <x> <z> <spreadDistance> <maxRange> <team>",
                category=CommandCategory.MOVEMENT,
                conversion_notes="Spread entities across the world",
                arguments=["x", "z", "spreadDistance", "maxRange"],
                examples=["/spreadplayers 0 0 5 20 true"],
            ),
        ]

        # Entity commands - 5 patterns
        entity_patterns = [
            CommandPattern(
                java_command_class="SummonCommand",
                bedrock_command="/summon <entity> [pos] [nbt]",
                category=CommandCategory.ENTITY,
                conversion_notes="Summon an entity at location",
                arguments=["entity", "x", "y", "z", "nbt"],
                examples=[
                    "/summon minecraft:zombie 100 64 100",
                    "/summon minecraft:creeper ~ ~ ~ {powered:1b}",
                ],
            ),
            CommandPattern(
                java_command_class="KillCommand",
                bedrock_command="/kill [targets]",
                category=CommandCategory.ENTITY,
                conversion_notes="Kill entities",
                arguments=["targets"],
                examples=["/kill @e[type=zombie]", "/kill @s"],
            ),
            CommandPattern(
                java_command_class="EffectCommand",
                bedrock_command="/effect <target> <effect> [seconds] [amplifier] [hideParticles]",
                category=CommandCategory.ENTITY,
                conversion_notes="Apply or remove status effects",
                arguments=["target", "effect", "duration", "amplifier"],
                examples=["/effect @s minecraft:speed 30 2", "/effect @a minecraft:clear"],
            ),
            CommandPattern(
                java_command_class="ExperienceCommand",
                bedrock_command="/xp <amount> [player]",
                category=CommandCategory.ENTITY,
                conversion_notes="Add or remove experience",
                arguments=["amount", "player"],
                examples=["/xp 10 @s", "/xp -5 @s"],
            ),
            CommandPattern(
                java_command_class="TeamCommand",
                bedrock_command="/team <add|remove|empty|join|leave> <team> [members]",
                category=CommandCategory.ENTITY,
                conversion_notes="Manage teams for entity grouping",
                arguments=["action", "team", "members"],
                examples=["/team add red", "/team join red @a"],
            ),
        ]

        # Item commands - 3 patterns
        item_patterns = [
            CommandPattern(
                java_command_class="GiveCommand",
                bedrock_command="/give <player> <item> [count] [data] [dataTag]",
                category=CommandCategory.ITEM,
                conversion_notes="Give item to player",
                arguments=["player", "item", "count"],
                examples=["/give @s minecraft:diamond_sword 1", "/give @a minecraft:apple 64"],
            ),
            CommandPattern(
                java_command_class="ClearCommand",
                bedrock_command="/clear [player] [item] [data] [maxCount]",
                category=CommandCategory.ITEM,
                conversion_notes="Clear items from player inventory",
                arguments=["player", "item", "maxCount"],
                examples=["/clear @s", "/clear @s minecraft:diamond 0"],
            ),
            CommandPattern(
                java_command_class="ReplaceItemCommand",
                bedrock_command="/replaceitem <entity|block> <slot> <item> [count] [data] [dataTag]",
                category=CommandCategory.ITEM,
                conversion_notes="Replace item in slot",
                arguments=["type", "slot", "item"],
                examples=["/replaceitem entity @s slot.armor.head minecraft:diamond_helmet"],
            ),
        ]

        # Gamestate commands - 4 patterns
        gamestate_patterns = [
            CommandPattern(
                java_command_class="DifficultyCommand",
                bedrock_command="/difficulty <peaceful|easy|normal|hard>",
                category=CommandCategory.GAMESTATE,
                conversion_notes="Set game difficulty",
                arguments=["difficulty"],
                examples=["/difficulty hard", "/difficulty peaceful"],
            ),
            CommandPattern(
                java_command_class="TimeCommand",
                bedrock_command="/time <set|add> <value>",
                category=CommandCategory.GAMESTATE,
                conversion_notes="Set or add time",
                arguments=["action", "value"],
                examples=["/time set day", "/time set 1000", "/time add 100"],
            ),
            CommandPattern(
                java_command_class="WeatherCommand",
                bedrock_command="/weather <clear|rain|thunder> [duration]",
                category=CommandCategory.GAMESTATE,
                conversion_notes="Set weather",
                arguments=["type", "duration"],
                examples=["/weather rain 6000", "/weather clear"],
            ),
            CommandPattern(
                java_command_class="GameruleCommand",
                bedrock_command="/gamerule <rule> [value]",
                category=CommandCategory.GAMESTATE,
                conversion_notes="Set or query game rule",
                arguments=["rule", "value"],
                examples=["/gamerule doDaylightCycle false", "/gamerule showDeathMessages"],
            ),
        ]

        # Scoreboard commands - 6 patterns
        scoreboard_patterns = [
            CommandPattern(
                java_command_class="ScoreboardObjective",
                bedrock_command="/scoreboard objectives add <name> [displayName]",
                category=CommandCategory.SCOREBOARD,
                conversion_notes="Create scoreboard objective",
                arguments=["name", "displayName"],
                examples=["/scoreboard objectives add kills dummy Kills"],
            ),
            CommandPattern(
                java_command_class="ScoreboardPlayersSet",
                bedrock_command="/scoreboard players set <player> <objective> <score>",
                category=CommandCategory.SCOREBOARD,
                conversion_notes="Set player score",
                arguments=["player", "objective", "score"],
                examples=["/scoreboard players set @s kills 5"],
            ),
            CommandPattern(
                java_command_class="ScoreboardPlayersAdd",
                bedrock_command="/scoreboard players add <player> <objective> <score>",
                category=CommandCategory.SCOREBOARD,
                conversion_notes="Add to player score",
                arguments=["player", "objective", "score"],
                examples=["/scoreboard players add @s kills 1"],
            ),
            CommandPattern(
                java_command_class="ScoreboardPlayersRemove",
                bedrock_command="/scoreboard players remove <player> <objective> <score>",
                category=CommandCategory.SCOREBOARD,
                conversion_notes="Remove from player score",
                arguments=["player", "objective", "score"],
                examples=["/scoreboard players remove @s health 1"],
            ),
            CommandPattern(
                java_command_class="ScoreboardPlayersOperation",
                bedrock_command="/scoreboard players operation <target> <objective> <operation> <source> <sourceObjective>",
                category=CommandCategory.SCOREBOARD,
                conversion_notes="Perform operation on scores",
                arguments=["target", "objective", "operation", "source", "sourceObjective"],
                examples=["/scoreboard players operation @s points += @r points"],
            ),
            CommandPattern(
                java_command_class="ScoreboardDisplay",
                bedrock_command="/scoreboard objectives setdisplay <slot> [objective]",
                category=CommandCategory.SCOREBOARD,
                conversion_notes="Display objective on slot",
                arguments=["slot", "objective"],
                examples=[
                    "/scoreboard objectives setdisplay sidebar kills",
                    "/scoreboard objectives setdisplay list",
                ],
            ),
        ]

        # Trigger commands - 2 patterns
        trigger_patterns = [
            CommandPattern(
                java_command_class="TriggerCommand",
                bedrock_command="/trigger <objective> <add|set> <value>",
                category=CommandCategory.TRIGGER,
                conversion_notes="Set or modify trigger objective",
                arguments=["objective", "action", "value"],
                examples=["/trigger kills add 1", "/trigger mytrigger set 5"],
            ),
            CommandPattern(
                java_command_class="TriggerObjective",
                bedrock_command="/scoreboard objectives add <name> trigger",
                category=CommandCategory.TRIGGER,
                conversion_notes="Create trigger-type objective for player triggers",
                arguments=["name", "displayName"],
                examples=["/scoreboard objectives add mytrigger trigger My Trigger"],
            ),
        ]

        # Execute command patterns - 2 patterns
        execute_patterns = [
            CommandPattern(
                java_command_class="ExecuteCommand",
                bedrock_command="/execute <subcommand> <args>",
                category=CommandCategory.FUNCTION,
                conversion_notes="Execute command with conditions",
                arguments=["subcommand", "args"],
                examples=["/execute as @a at @s run setblock ~ ~-1 ~ stone"],
            ),
            CommandPattern(
                java_command_class="ExecuteIfCommand",
                bedrock_command="/execute if <condition> <command>",
                category=CommandCategory.FUNCTION,
                conversion_notes="Conditional execution",
                arguments=["condition", "command"],
                examples=["/execute if entity @e[type=zombie] kill @e[type=zombie]"],
            ),
        ]

        # Tag commands - 2 patterns
        tag_patterns = [
            CommandPattern(
                java_command_class="TagCommand",
                bedrock_command="/tag <target> add <tag>",
                category=CommandCategory.DATA,
                conversion_notes="Add tag to entity",
                arguments=["target", "tag"],
                examples=["/tag @s add boss", "/tag @a add VIP"],
            ),
            CommandPattern(
                java_command_class="TagRemoveCommand",
                bedrock_command="/tag <target> remove <tag>",
                category=CommandCategory.DATA,
                conversion_notes="Remove tag from entity",
                arguments=["target", "tag"],
                examples=["/tag @s remove boss"],
            ),
        ]

        # Title commands - 1 pattern
        title_patterns = [
            CommandPattern(
                java_command_class="TitleCommand",
                bedrock_command="/title <player> <title|subtitle|actionbar|clear|reset> [text]",
                category=CommandCategory.TITLE,
                conversion_notes="Display title to player",
                arguments=["player", "action", "text"],
                examples=[
                    '/title @a title {"text":"Hello!"}',
                    '/title @s subtitle {"text":"Subtitle"}',
                ],
            ),
        ]

        # Add all patterns to library
        self.patterns.extend(movement_patterns)
        self.patterns.extend(entity_patterns)
        self.patterns.extend(item_patterns)
        self.patterns.extend(gamestate_patterns)
        self.patterns.extend(scoreboard_patterns)
        self.patterns.extend(trigger_patterns)
        self.patterns.extend(execute_patterns)
        self.patterns.extend(tag_patterns)
        self.patterns.extend(title_patterns)

    def search_by_java(self, java_class: str) -> List[CommandPattern]:
        """
        Search patterns by Java command class.

        Args:
            java_class: Java command class to search for

        Returns:
            List of matching CommandPattern objects
        """
        results = []
        java_class_lower = java_class.lower()

        for pattern in self.patterns:
            # Check primary class
            if java_class_lower in pattern.java_command_class.lower():
                results.append(pattern)

        # Prioritize exact matches
        exact_matches = [p for p in results if p.java_command_class.lower() == java_class_lower]
        for match in exact_matches:
            results.remove(match)
            results.insert(0, match)

        return results

    def get_by_category(self, category: CommandCategory) -> List[CommandPattern]:
        """
        Get all patterns in a category.

        Args:
            category: CommandCategory to filter by

        Returns:
            List of patterns in the category
        """
        return [p for p in self.patterns if p.category == category]

    def get_pattern_by_java_class(self, java_class: str) -> Optional[CommandPattern]:
        """
        Get exact pattern by Java command class.

        Args:
            java_class: Java command class

        Returns:
            CommandPattern if found, None otherwise
        """
        java_class_lower = java_class.lower()
        for pattern in self.patterns:
            if pattern.java_command_class.lower() == java_class_lower:
                return pattern
        return None

    def add_pattern(self, pattern: CommandPattern) -> None:
        """
        Add a new pattern to the library.

        Args:
            pattern: CommandPattern to add
        """
        # Check for duplicate
        for existing in self.patterns:
            if existing.java_command_class == pattern.java_command_class:
                # Update existing
                existing.bedrock_command = pattern.bedrock_command
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
COMMAND_PATTERNS = CommandPatternLibrary()


def get_command_pattern(java_class: str) -> Optional[CommandPattern]:
    """
    Get a command pattern by Java class.

    Args:
        java_class: Java command class

    Returns:
        CommandPattern if found, None otherwise
    """
    return COMMAND_PATTERNS.get_pattern_by_java_class(java_class)


def search_command_patterns(query: str) -> List[CommandPattern]:
    """
    Search command patterns by Java class.

    Args:
        query: Search query

    Returns:
        List of matching patterns
    """
    return COMMAND_PATTERNS.search_by_java(query)


def get_patterns_by_category(category: CommandCategory) -> List[CommandPattern]:
    """
    Get all patterns in a category.

    Args:
        category: Category to filter by

    Returns:
        List of patterns
    """
    return COMMAND_PATTERNS.get_by_category(category)


def get_command_stats() -> Dict[str, int]:
    """
    Get command pattern library statistics.

    Returns:
        Statistics dictionary
    """
    return COMMAND_PATTERNS.get_stats()
