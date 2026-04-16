"""
Loot Table Generator for Bedrock Entities

Converts Java loot table JSON format to Bedrock loot table format.
Part of Issue #1003 - Entity converter: full behavior, spawn rules, loot tables, animation
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class LootPool:
    """Represents a loot pool in a Bedrock loot table."""

    name: str
    rolls: int = 1
    entries: List[Dict[str, Any]] = field(default_factory=list)
    bonus_rolls: int = 0
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LootTable:
    """Represents a complete Bedrock loot table."""

    pools: List[LootPool] = field(default_factory=list)


class LootTableGenerator:
    """
    Generates Bedrock loot table JSON files from Java loot tables.

    Java loot tables use a different format with 'pools', 'entries', 'functions'.
    Bedrock uses similar structure but with additional constraints and features.
    """

    def __init__(self):
        self.format_version = "1.16.0"

    def generate_loot_table(
        self, java_loot_table: Dict[str, Any], entity_id: str, namespace: str = "modporter"
    ) -> Dict[str, Any]:
        """
        Generate Bedrock loot table from Java loot table definition.

        Args:
            java_loot_table: Java loot table dictionary
            entity_id: Entity identifier for reference
            namespace: Namespace for the loot table

        Returns:
            Bedrock loot table JSON structure
        """
        pools = java_loot_table.get("pools", [])
        bedrock_pools = []

        for i, pool in enumerate(pools):
            bedrock_pool = self._convert_pool(pool, i)
            if bedrock_pool:
                bedrock_pools.append(bedrock_pool)

        loot_table = {
            "format_version": self.format_version,
            "pools": bedrock_pools,
        }

        return loot_table

    def _convert_pool(self, pool: Dict[str, Any], pool_index: int) -> Optional[Dict[str, Any]]:
        """Convert a single loot pool."""
        entries = pool.get("entries", [])
        if not entries:
            return None

        pool_name = pool.get("name", f"pool_{pool_index}")

        bedrock_pool: Dict[str, Any] = {
            "name": pool_name,
            "rolls": pool.get("rolls", 1),
        }

        if "bonus_rolls" in pool:
            bedrock_pool["bonus_rolls"] = pool["bonus_rolls"]

        bedrock_entries = []
        for entry in entries:
            converted_entry = self._convert_entry(entry)
            if converted_entry:
                bedrock_entries.append(converted_entry)

        if not bedrock_entries:
            return None

        bedrock_pool["entries"] = bedrock_entries

        conditions = pool.get("conditions", [])
        if conditions:
            bedrock_pool["conditions"] = self._convert_conditions(conditions)

        functions = pool.get("functions", [])
        if functions:
            bedrock_pool["functions"] = self._convert_functions(functions)

        return bedrock_pool

    def _convert_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a loot table entry."""
        entry_type = entry.get("type", "item")
        entry_name = entry.get("name", "minecraft:air")

        bedrock_entry: Dict[str, Any] = {
            "type": self._map_entry_type(entry_type),
            "name": entry_name,
        }

        if "weight" in entry:
            bedrock_entry["weight"] = entry["weight"]

        if "quality" in entry:
            bedrock_entry["quality"] = entry["quality"]

        functions = entry.get("functions", [])
        if functions:
            bedrock_entry["functions"] = self._convert_functions(functions)

        return bedrock_entry

    def _map_entry_type(self, java_type: str) -> str:
        """Map Java entry type to Bedrock entry type."""
        type_mapping = {
            "item": "item",
            "loot_table": "loot_table",
            "dynamic": "dynamic",
            "empty": "empty",
            "alternatives": "alternatives",
            "sequence": "sequence",
        }
        return type_mapping.get(java_type.lower(), "item")

    def _convert_conditions(self, conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert loot table conditions to Bedrock format."""
        bedrock_conditions = []

        for condition in conditions:
            condition_type = condition.get("condition", "")
            converted = self._convert_single_condition(condition_type, condition)
            if converted:
                bedrock_conditions.append(converted)

        return bedrock_conditions

    def _convert_single_condition(
        self, condition_type: str, condition: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Convert a single condition to Bedrock format."""
        condition_map = {
            "entity_has_property": {
                "condition": "entity_has_property",
                "domain": condition.get("predicate", {}),
            },
            "entity_scores": {"condition": "entity_scores", "domain": condition.get("scores", {})},
            "killed_by_player": {"condition": "killed_by_player"},
            "random_chance": {"condition": "random_chance", "chance": condition.get("chance", 1.0)},
            "random_chance_with_looting": {
                "condition": "random_chance_with_looting",
                "chance": condition.get("chance", 1.0),
                "looting_multiplier": condition.get("looting_multiplier", 0.0),
            },
        }

        mapped = condition_map.get(condition_type)
        if mapped:
            return mapped

        return {"condition": condition_type, **condition}

    def _convert_functions(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert loot table functions to Bedrock format."""
        bedrock_functions = []

        for function in functions:
            converted = self._convert_single_function(function)
            if converted:
                bedrock_functions.append(converted)

        return bedrock_functions

    def _convert_single_function(self, function: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a single function to Bedrock format."""
        function_type = function.get("function", "")

        function_map = {
            "set_count": {
                "function": "set_count",
                "count": function.get("count", {"min": 1, "max": 1}),
            },
            "set_damage": {
                "function": "set_damage",
                "damage": function.get("damage", {"min": 0.0, "max": 1.0}),
            },
            "set_nbt": {
                "function": "set_nbt",
                "tag": function.get("tag", ""),
            },
            "enchant_randomly": {
                "function": "enchant_randomly",
                "enchantments": function.get("enchantments", []),
            },
            "enchant_with_levels": {
                "function": "enchant_with_levels",
                "treasure": function.get("treasure", False),
                "levels": function.get("levels", {"min": 0, "max": 30}),
            },
            "looting_enchant": {
                "function": "looting_enchant",
                "count": function.get("count", {"min": 0, "max": 1}),
            },
            "furnace_smelt": {"function": "furnace_smelt"},
            "fill_container": {
                "function": "fill_container",
                "loot_table": function.get("loot_table", ""),
            },
            "explosion_decay": {"function": "explosion_decay"},
            "diet": {
                "function": "diet",
                "items": function.get("items", []),
            },
        }

        mapped = function_map.get(function_type)
        if mapped:
            return mapped

        return {"function": function_type, **function}

    def generate_entity_loot_table(
        self,
        entity_id: str,
        namespace: str = "modporter",
        drops: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a basic entity loot table.

        Args:
            entity_id: Entity identifier
            namespace: Namespace
            drops: Optional list of drop definitions

        Returns:
            Bedrock loot table JSON structure
        """
        if drops is None:
            drops = [
                {"item": "minecraft:diamond", "weight": 1, "min": 1, "max": 2},
                {"item": "minecraft:gold_ingot", "weight": 5, "min": 1, "max": 3},
                {"item": "minecraft:iron_ingot", "weight": 10, "min": 1, "max": 5},
            ]

        pool: Dict[str, Any] = {
            "rolls": {"min": 1, "max": 3},
            "entries": [
                {
                    "type": "item",
                    "name": drop["item"],
                    "weight": drop.get("weight", 1),
                    "functions": [
                        {
                            "function": "set_count",
                            "count": {"min": drop.get("min", 1), "max": drop.get("max", 1)},
                        }
                    ],
                }
                for drop in drops
            ],
            "conditions": [
                {
                    "condition": "killed_by_player",
                }
            ],
        }

        return self.generate_loot_table(
            {"pools": [pool]},
            entity_id,
            namespace,
        )

    def write_loot_table(
        self,
        loot_table: Dict[str, Any],
        output_dir: Path,
        table_name: str,
    ) -> Path:
        """
        Write loot table JSON to disk.

        Args:
            loot_table: The loot table JSON structure
            output_dir: Directory to write to (behavior pack root)
            table_name: Name for the loot table file

        Returns:
            Path to written file
        """
        loot_tables_dir = output_dir / "loot_tables" / "entities"
        loot_tables_dir.mkdir(parents=True, exist_ok=True)

        file_path = loot_tables_dir / f"{table_name}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(loot_table, f, indent=2, ensure_ascii=False)

        logger.info(f"Wrote loot table to {file_path}")
        return file_path


def generate_loot_table(
    java_loot_table: Dict[str, Any],
    entity_id: str,
    namespace: str = "modporter",
) -> Dict[str, Any]:
    """
    Convenience function to generate a Bedrock loot table.

    Args:
        java_loot_table: Java loot table dictionary
        entity_id: Entity identifier
        namespace: Namespace

    Returns:
        Bedrock loot table JSON structure
    """
    generator = LootTableGenerator()
    return generator.generate_loot_table(java_loot_table, entity_id, namespace)


def generate_entity_loot_table(
    entity_id: str,
    namespace: str = "modporter",
    drops: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to generate an entity loot table with default drops.

    Args:
        entity_id: Entity identifier
        namespace: Namespace
        drops: Optional list of drop definitions

    Returns:
        Bedrock loot table JSON structure
    """
    generator = LootTableGenerator()
    return generator.generate_entity_loot_table(entity_id, namespace, drops)


def write_loot_table_to_disk(
    loot_table: Dict[str, Any],
    output_dir: Path,
    table_name: str,
) -> Path:
    """
    Convenience function to write loot table to disk.

    Args:
        loot_table: The loot table JSON structure
        output_dir: Directory to write to
        table_name: Name for the loot table file

    Returns:
        Path to written file
    """
    generator = LootTableGenerator()
    return generator.write_loot_table(loot_table, output_dir, table_name)
