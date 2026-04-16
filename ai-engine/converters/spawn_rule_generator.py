"""
Spawn Rule Generator for Bedrock Entities

Converts Java entity spawn conditions to Bedrock spawn_rules JSON format.
Part of Issue #1003 - Entity converter: full behavior, spawn rules, loot tables, animation
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


@dataclass
class SpawnCondition:
    """Represents a spawn condition for entity spawning."""

    biome: Optional[str] = None
    min_height: int = 0
    max_height: int = 256
    min_light: Optional[int] = None
    max_light: Optional[int] = None
    min_cloud_distance: Optional[int] = None
    block_filter: Optional[List[str]] = None
    dimension: Optional[str] = None
    spawn_type: str = "natural"


@dataclass
class SpawnRule:
    """Represents a complete Bedrock spawn rule."""

    entity_identifier: str
    conditions: List[SpawnCondition]
    experimental: bool = False
    permission_level: str = "member"


class SpawnRuleGenerator:
    """
    Generates Bedrock spawn_rules JSON files for entities.

    Bedrock spawn rules define where and when an entity can naturally spawn,
    including biome restrictions, light levels, and block requirements.
    """

    def __init__(self):
        self.format_version = "1.19.0"

        self.biome_category_map = {
            "plains": "plains",
            "forest": "forest",
            "desert": "desert",
            "jungle": "jungle",
            "snow": "snow",
            "taiga": "taiga",
            "mountain": "extreme_hills",
            "ocean": "ocean",
            "river": "river",
            "swamp": "swamp",
            "savanna": "savanna",
            "mushroom": "mushroom_island",
            "nether": "nether",
            "end": "the_end",
        }

        self.entity_spawn_type_map = {
            "ambient": "ambient",
            "creature": "creature",
            "monster": "monster",
            "water": "water_creature",
            "ambient_flying": "ambient",
        }

    def generate_spawn_rules(
        self, java_entity: Dict[str, Any], namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate Bedrock spawn_rules JSON from Java entity definition.

        Args:
            java_entity: Java entity definition with spawn properties
            namespace: Optional namespace override

        Returns:
            Bedrock spawn_rules JSON structure
        """
        entity_id = java_entity.get("id", "unknown")
        ns = namespace or java_entity.get("namespace", "modporter")
        full_id = f"{ns}:{entity_id}"

        spawn_conditions = self._extract_spawn_conditions(java_entity)

        spawn_rule = {
            "format_version": self.format_version,
            "minecraft:spawn_rules": {
                "description": {
                    "identifier": full_id,
                    "min_radio_tick": java_entity.get("min_radio_tick", 0),
                    "max_radio_tick": java_entity.get("max_radio_tick", 0),
                },
                "conditions": [],
            },
        }

        if java_entity.get("experimental", False):
            spawn_rule["minecraft:spawn_rules"]["description"]["experimental"] = True

        for condition in spawn_conditions:
            bedrock_condition = self._convert_condition(condition)
            if bedrock_condition:
                spawn_rule["minecraft:spawn_rules"]["conditions"].append(bedrock_condition)

        return spawn_rule

    def _extract_spawn_conditions(self, java_entity: Dict[str, Any]) -> List[SpawnCondition]:
        """Extract spawn conditions from Java entity definition."""
        conditions = []

        spawn_data = java_entity.get("spawn_data", {})
        if not spawn_data:
            conditions.append(self._create_default_condition(java_entity))
            return conditions

        biomes = spawn_data.get("biomes", [])
        dimensions = spawn_data.get("dimensions", [])
        min_height = spawn_data.get("min_height", 0)
        max_height = spawn_data.get("max_height", 256)
        min_light = spawn_data.get("min_light", None)
        max_light = spawn_data.get("max_light", None)
        block_filters = spawn_data.get("block_filters", None)

        if biomes:
            for biome in biomes:
                condition = SpawnCondition(
                    biome=biome,
                    min_height=min_height,
                    max_height=max_height,
                    min_light=min_light,
                    max_light=max_light,
                    block_filter=block_filters,
                )
                conditions.append(condition)
        elif dimensions:
            for dim in dimensions:
                condition = SpawnCondition(
                    biome=None,
                    dimension=dim,
                    min_height=min_height,
                    max_height=max_height,
                    min_light=min_light,
                    max_light=max_light,
                    block_filter=block_filters,
                )
                conditions.append(condition)
        else:
            conditions.append(self._create_default_condition(java_entity))

        return conditions

    def _create_default_condition(self, java_entity: Dict[str, Any]) -> SpawnCondition:
        """Create a default spawn condition based on entity type."""
        entity_type = java_entity.get("category", "creature").lower()

        if entity_type == "hostile" or entity_type == "monster":
            return SpawnCondition(
                biome="monster",
                min_height=0,
                max_height=256,
                min_light=None,
                max_light=7,
                spawn_type="monster",
            )
        elif entity_type == "passive":
            return SpawnCondition(
                biome="plains",
                min_height=0,
                max_height=256,
                min_light=9,
                max_light=None,
                spawn_type="creature",
            )
        elif entity_type == "ambient":
            return SpawnCondition(
                biome="plains",
                min_height=0,
                max_height=256,
                min_light=0,
                max_light=None,
                spawn_type="ambient",
            )
        else:
            return SpawnCondition(
                biome=None,
                min_height=0,
                max_height=256,
                spawn_type="creature",
            )

    def _convert_condition(self, condition: SpawnCondition) -> Optional[Dict[str, Any]]:
        """Convert internal SpawnCondition to Bedrock spawn rule condition."""
        bedrock_condition: Dict[str, Any] = {}

        if condition.biome:
            bedrock_condition["minecraft:biome_filter"] = {
                "test": "has_biome_tag",
                "subject": "self",
                "value": condition.biome,
            }

        if condition.dimension:
            bedrock_condition["minecraft:delay_filter"] = {
                "test": "equals",
                "subject": "self",
                "domain": condition.dimension,
            }

        height_filter: Dict[str, Any] = {
            "test": "in_range",
            "subject": "origin",
            "operator": "between",
            "value": [condition.min_height, condition.max_height],
        }
        bedrock_condition["minecraft:height_filter"] = height_filter

        if condition.min_light is not None or condition.max_light is not None:
            light_filter: Dict[str, Any] = {
                "test": "in_range",
                "subject": "block",
                "operator": "between",
            }
            if condition.min_light is not None and condition.max_light is not None:
                light_filter["value"] = [condition.min_light, condition.max_light]
            elif condition.min_light is not None:
                light_filter["value"] = [condition.min_light, 15]
            elif condition.max_light is not None:
                light_filter["value"] = [0, condition.max_light]
            bedrock_condition["minecraft:brightness_filter"] = light_filter

        if condition.block_filter:
            block_names = condition.block_filter
            if len(block_names) == 1:
                bedrock_condition["minecraft:block_filter"] = {
                    "test": "equals",
                    "subject": "block",
                    "value": block_names[0],
                }
            else:
                bedrock_condition["minecraft:block_filter"] = {
                    "test": "any_of",
                    "subject": "block",
                    "values": [{"test": "equals", "value": b} for b in block_names],
                }

        return bedrock_condition

    def write_spawn_rules(
        self,
        spawn_rules: Dict[str, Any],
        output_dir: Path,
        entity_id: str,
    ) -> Path:
        """
        Write spawn rules JSON to disk.

        Args:
            spawn_rules: The spawn rules JSON structure
            output_dir: Directory to write to (behavior pack root)
            entity_id: Entity identifier for filename

        Returns:
            Path to written file
        """
        spawn_rules_dir = output_dir / "spawn_rules"
        spawn_rules_dir.mkdir(parents=True, exist_ok=True)

        safe_name = entity_id.split(":")[-1]
        file_path = spawn_rules_dir / f"{safe_name}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(spawn_rules, f, indent=2, ensure_ascii=False)

        logger.info(f"Wrote spawn rules to {file_path}")
        return file_path


def generate_spawn_rules(
    java_entity: Dict[str, Any], namespace: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate spawn rules for a Java entity.

    Args:
        java_entity: Java entity definition with spawn properties
        namespace: Optional namespace override

    Returns:
        Bedrock spawn_rules JSON structure
    """
    generator = SpawnRuleGenerator()
    return generator.generate_spawn_rules(java_entity, namespace)


def write_spawn_rules_to_disk(
    spawn_rules: Dict[str, Any],
    output_dir: Path,
    entity_id: str,
) -> Path:
    """
    Convenience function to write spawn rules to disk.

    Args:
        spawn_rules: The spawn rules JSON structure
        output_dir: Directory to write to
        entity_id: Entity identifier for filename

    Returns:
        Path to written file
    """
    generator = SpawnRuleGenerator()
    return generator.write_spawn_rules(spawn_rules, output_dir, entity_id)
