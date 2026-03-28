"""
Entity Converter for converting Java entities to Bedrock format
Part of the Bedrock Add-on Generation System (Issue #6)
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MobCategory(Enum):
    """Categories for different mob types in Bedrock."""

    HOSTILE = "hostile"
    PASSIVE = "passive"
    NEUTRAL = "neutral"
    BOSS = "boss"


class EntityType(Enum):
    PASSIVE = "passive"
    NEUTRAL = "neutral"
    HOSTILE = "hostile"
    BOSS = "boss"
    AMBIENT = "ambient"
    MISC = "misc"


@dataclass
class EntityProperties:
    health: float = 20.0
    movement_speed: float = 0.25
    follow_range: float = 16.0
    attack_damage: float = 0.0
    armor: float = 0.0
    knockback_resistance: float = 0.0
    can_swim: bool = True
    can_climb: bool = False
    can_fly: bool = False
    breathes_air: bool = True
    breathes_water: bool = False
    pushable: bool = True
    entity_type: EntityType = EntityType.PASSIVE


class EntityConverter:
    """
    Converter for Java entities to Bedrock entity format.
    Handles entity definitions, behaviors, and animations.
    """

    def __init__(self):
        # Bedrock entity definition template
        self.entity_template = {
            "format_version": "1.19.0",
            "": {
                "description": {
                    "identifier": "",
                    "is_spawnable": True,
                    "is_summonable": True,
                    "is_experimental": False,
                },
                "component_groups": {},
                "components": {},
                "events": {},
            },
        }

        # Common Bedrock entity components
        self.base_components = {
            "minecraft:type_family": {"family": ["mob"]},
            "minecraft:collision_box": {"width": 0.6, "height": 1.8},
            "minecraft:health": {"value": 20, "max": 20},
            "minecraft:movement": {"value": 0.25},
            "minecraft:navigation.walk": {
                "can_path_over_water": True,
                "avoid_water": True,
                "avoid_damage_at_all_costs": True,
            },
            "minecraft:movement.basic": {},
            "minecraft:jump.static": {},
            "minecraft:can_climb": {},
            "minecraft:physics": {},
        }

        # Behavior mappings from Java to Bedrock (extended for comprehensive AI behavior conversion)
        self.behavior_mappings = {
            # Movement behaviors
            "follow_player": "minecraft:behavior.follow_player",
            "follow_owner": "minecraft:behavior.follow_owner",
            "look_at_player": "minecraft:behavior.look_at_player",
            "random_look_around": "minecraft:behavior.random_look_around",
            "random_stroll": "minecraft:behavior.random_stroll",
            "random_float": "minecraft:behavior.float",
            "float": "minecraft:behavior.float",
            "swim": "minecraft:behavior.swim",
            "fly": "minecraft:behavior.fly",
            "wander": "minecraft:behavior.wander",
            "move_towards_target": "minecraft:behavior.move_towards_target",
            "move_through_village": "minecraft:behavior.move_through_village",
            "move_to_land": "minecraft:behavior.move_to_land",
            "mount_pathing": "minecraft:behavior.mount_pathing",
            # Combat behaviors
            "panic": "minecraft:behavior.panic",
            "melee_attack": "minecraft:behavior.melee_attack",
            "ranged_attack": "minecraft:behavior.ranged_attack",
            "attack_entity": "minecraft:behavior.attack_entity",
            "attack_with_range": "minecraft:behavior.attack_with_range",
            "knockback_roar": "minecraft:behavior.knockback_roar",
            "charge_attack": "minecraft:behavior.charge",
            "strafing": "minecraft:behavior.strafe",
            "siege": "minecraft:behavior.siege",
            # Social behaviors
            "breed": "minecraft:behavior.breed",
            "tempt": "minecraft:behavior.tempt",
            "nudge": "minecraft:behavior.nudge",
            "celebrate": "minecraft:behavior.celebrate",
            "get_angry": "minecraft:behavior.get_angry",
            "become_angry": "minecraft:behavior.become_angry",
            # Environmental behaviors
            "avoid_entity": "minecraft:behavior.avoid_entity",
            "avoid_block": "minecraft:behavior.avoid_block",
            "flee_sun": "minecraft:behavior.flee_sun",
            "restrict_sun": "minecraft:behavior.restrict_sun",
            "seek_shelter": "minecraft:behavior.seek_shelter",
            "leave_water": "minecraft:behavior.leave_water",
            "play_dead": "minecraft:behavior.play_dead",
            # Entity-specific behaviors
            "tame": "minecraft:behavior.tame",
            "owner_hurt_by_target": "minecraft:behavior.owner_hurt_by_target",
            "owner_hurt_target": "minecraft:behavior.owner_hurt_target",
            "leash": "minecraft:behavior.leash",
            "unleash": "minecraft:behavior.unleash",
            "equipped_item_chance": "minecraft:behavior.equipped_item_chance",
            # Goal compound behaviors
            "find_mount": "minecraft:behavior.find_mount",
            "jump_to_block": "minecraft:behavior.jump_to_block",
            "lay_spawn": "minecraft:behavior.lay_spawn",
            "lay_egg": "minecraft:behavior.lay_egg",
            "item_consume": "minecraft:behavior.item_consume",
            "pickup_items": "minecraft:behavior.pickup_items",
            "trade": "minecraft:behavior.trade_with_player",
            "look_at_trading": "minecraft:behavior.look_at_trading",
            # Miscellaneous behaviors
            "interact": "minecraft:behavior.interact",
            "ocelot_sneeze": "minecraft:behavior.ocelot_sneeze",
            "parrot_poop": "minecraft:behavior.parrot_poop",
            "ram_attack": "minecraft:behavior.ram_attack",
            "skeleton_ride": "minecraft:behavior.skeleton_ride",
            "swell": "minecraft:behavior.swell",
            "spit": "minecraft:behavior.spit",
            "vex_copy_owner_target": "minecraft:behavior.vex_copy_owner_target",
            "fish_jump": "minecraft:behavior.fish_jump",
            "flop": "minecraft:behavior.flop",
        }

        # AI Goal type mappings (Java AI Goal -> Bedrock behavior with priority)
        self.goal_mappings = {
            # Core movement goals
            "move": "minecraft:behavior.move_towards_target",
            "wander": "minecraft:behavior.wander",
            "stroll": "minecraft:behavior.wander",
            "swim": "minecraft:behavior.swim",
            "fly": "minecraft:behavior.fly",
            "climb": "minecraft:behavior.climb",
            "jump": "minecraft:behavior.jump",
            "float": "minecraft:behavior.float",
            # Targeting goals
            "look_at_player": "minecraft:behavior.look_at_player",
            "look_at_target": "minecraft:behavior.look_at_target",
            "look_randomly": "minecraft:behavior.random_look_around",
            # Attack goals
            "melee_attack": "minecraft:behavior.melee_attack",
            "ranged_attack": "minecraft:behavior.attack_with_range",
            "hurt_target": "minecraft:behavior.attack_entity",
            "attack": "minecraft:behavior.melee_attack",
            # Social goals
            "breed": "minecraft:behavior.breed",
            "tempt": "minecraft:behavior.tempt",
            "follow": "minecraft:behavior.follow_player",
            "tame": "minecraft:behavior.tame",
            # Survival goals
            "panic": "minecraft:behavior.panic",
            "flee": "minecraft:behavior.avoid_entity",
            "avoid": "minecraft:behavior.avoid_entity",
            "hide": "minecraft:behavior.seek_shelter",
            "rest": "minecraft:behavior.restrict_sun",
            "seek_water": "minecraft:behavior.leave_water",
            # Interaction goals
            "interact": "minecraft:behavior.interact",
            "trade": "Offers:behavior.trade_with_player",
            "open_door": "minecraft:behavior.door_interact",
            "use_item": "minecraft:behavior.item_consume",
            "pickup": "minecraft:behavior.pickup_items",
            # Specialized goals
            "celebrate": "minecraft:behavior.celebrate",
            "rest": "minecraft:behavior.restrict_sun",
            "eat": "minecraft:behavior.item_consume",
            "graze": "minecraft:behavior.graze",
            "sleep": "minecraft:behavior.sleep",
            "raid": "minecraft:behavior.raid",
        }

    def convert_entities(self, java_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert Java entities to Bedrock format.

        Args:
            java_entities: List of Java entity definitions

        Returns:
            Dictionary of Bedrock entity definitions
        """
        logger.info(f"Converting {len(java_entities)} Java entities to Bedrock format")
        bedrock_entities = {}

        for java_entity in java_entities:
            try:
                bedrock_entity = self._convert_java_entity(java_entity)
                entity_id = bedrock_entity["minecraft:entity"]["description"]["identifier"]
                bedrock_entities[entity_id] = bedrock_entity

                # Also generate behavior and animation files if needed
                behaviors = self._generate_entity_behaviors(java_entity)
                animations = self._generate_entity_animations(java_entity)

                if behaviors:
                    bedrock_entities[f"{entity_id}_behaviors"] = behaviors
                if animations:
                    bedrock_entities[f"{entity_id}_animations"] = animations

            except Exception as e:
                logger.error(f"Failed to convert entity {java_entity.get('id', 'unknown')}: {e}")
                continue

        logger.info(f"Successfully converted {len(bedrock_entities)} entities")
        return bedrock_entities

    # Specialized Entity Template Methods for Issue #452

    def generate_hostile_mob(self, java_entity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a Bedrock hostile mob definition with AI behaviors.

        Args:
            java_entity: Java hostile mob definition

        Returns:
            Bedrock hostile mob entity definition
        """
        return self._create_hostile_mob_entity(java_entity)

    def generate_passive_mob(self, java_entity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a Bedrock passive mob definition with AI behaviors.

        Args:
            java_entity: Java passive mob definition

        Returns:
            Bedrock passive mob entity definition
        """
        return self._create_passive_mob_entity(java_entity)

    def _create_hostile_mob_entity(self, java_entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Bedrock hostile mob entity with aggressive AI behaviors."""
        entity_id = java_entity.get("id", "unknown_hostile")
        namespace = java_entity.get("namespace", "modporter")
        full_id = f"{namespace}:{entity_id}"

        # Parse base properties
        properties = self._parse_java_entity_properties(java_entity)
        properties.entity_type = EntityType.HOSTILE

        # Create entity definition
        bedrock_entity = {
            "format_version": "1.19.0",
            "minecraft:entity": {
                "description": {
                    "identifier": full_id,
                    "is_spawnable": java_entity.get("spawnable", True),
                    "is_summonable": java_entity.get("summonable", True),
                    "is_experimental": False,
                },
                "component_groups": {},
                "components": {},
                "events": {},
            },
        }

        components = bedrock_entity["minecraft:entity"]["components"]

        # Base components
        components.update(self.base_components.copy())

        # Apply properties
        self._apply_entity_properties(components, properties)

        # Add hostile-specific AI behaviors
        self._add_hostile_ai_behaviors(components, java_entity)

        # Add attack behavior
        if java_entity.get("can_attack", True):
            components["minecraft:attack"] = {
                "damage": properties.attack_damage if properties.attack_damage > 0 else 4.0
            }

        # Add hostile type family
        components["minecraft:type_family"]["family"] = ["mob", "monster", "hostile"]

        # Hostile mobs usually have spawn egg
        if java_entity.get("has_spawn_egg", True):
            components["minecraft:spawn_egg"] = {
                "base_color": java_entity.get("spawn_egg_primary", "#5A1D1D"),
                "overlay_color": java_entity.get("spawn_egg_secondary", "#1D1D1D"),
            }

        # Add loot table
        if "loot_table" in java_entity:
            components["minecraft:loot"] = {"table": java_entity["loot_table"]}

        return bedrock_entity

    def _create_passive_mob_entity(self, java_entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Bedrock passive mob entity with peaceful AI behaviors."""
        entity_id = java_entity.get("id", "unknown_passive")
        namespace = java_entity.get("namespace", "modporter")
        full_id = f"{namespace}:{entity_id}"

        # Parse base properties
        properties = self._parse_java_entity_properties(java_entity)
        properties.entity_type = EntityType.PASSIVE

        # Create entity definition
        bedrock_entity = {
            "format_version": "1.19.0",
            "minecraft:entity": {
                "description": {
                    "identifier": full_id,
                    "is_spawnable": java_entity.get("spawnable", True),
                    "is_summonable": java_entity.get("summonable", True),
                    "is_experimental": False,
                },
                "component_groups": {},
                "components": {},
                "events": {},
            },
        }

        components = bedrock_entity["minecraft:entity"]["components"]

        # Base components
        components.update(self.base_components.copy())

        # Apply properties
        self._apply_entity_properties(components, properties)

        # Add passive-specific AI behaviors (no attack, peaceful)
        self._add_passive_ai_behaviors(components, java_entity)

        # Remove attack capabilities for passive mobs
        if "minecraft:attack" in components:
            del components["minecraft:attack"]

        # Add passive type family
        components["minecraft:type_family"]["family"] = ["mob", "passive"]

        # Passive mobs have spawn egg
        if java_entity.get("has_spawn_egg", True):
            components["minecraft:spawn_egg"] = {
                "base_color": java_entity.get("spawn_egg_primary", "#1D5D1D"),
                "overlay_color": java_entity.get("spawn_egg_secondary", "#FFFFFF"),
            }

        # Add breed behavior if applicable
        if java_entity.get("can_breed", True):
            components["minecraft:behavior.breed"] = {"priority": 4}

        # Add tameable component if applicable
        if java_entity.get("is_tameable", False):
            components["minecraft:tameable"] = {
                "probability": java_entity.get("tame_probability", 0.33),
                "tame_event": {"event": "minecraft:on_tame", "target": "self"},
            }

        # Add loot table (for when passive mobs are killed)
        if "loot_table" in java_entity:
            components["minecraft:loot"] = {"table": java_entity["loot_table"]}

        return bedrock_entity

    def _add_hostile_ai_behaviors(self, components: Dict[str, Any], java_entity: Dict[str, Any]):
        """Add AI behaviors specific to hostile mobs."""
        # Melee attack behavior
        components["minecraft:behavior.melee_attack"] = {
            "priority": 3,
            "speed_multiplier": 1.0,
            "track_target": True,
            "reach_multiplier": 0.8,
        }

        # Look at target
        components["minecraft:behavior.look_at_player"] = {
            "priority": 5,
            "look_distance": 8.0,
            "look_time": [2, 4],
        }

        # Move towards target
        components["minecraft:behavior.move_towards_target"] = {
            "priority": 4,
            "speed_multiplier": 1.0,
            "target_distance": 4.0,
        }

        # Wander when idle
        components["minecraft:behavior.wander"] = {
            "priority": 6,
            "speed_multiplier": 0.8,
            "wander_distance": 10,
            "start_chance": 0.2,
        }

        # Panic when hurt
        components["minecraft:behavior.panic"] = {
            "priority": 1,
            "speed_multiplier": 1.25,
            "panic_sound": "mob.hostile.hurt",
        }

        # Add Java entity's custom behaviors
        if "behaviors" in java_entity:
            self._add_entity_behaviors(components, java_entity)

        # Add custom AI goals
        if "ai_goals" in java_entity:
            self._add_ai_goals(components, java_entity["ai_goals"])

    def _add_passive_ai_behaviors(self, components: Dict[str, Any], java_entity: Dict[str, Any]):
        """Add AI behaviors specific to passive mobs."""
        # Follow player if tamed
        components["minecraft:behavior.follow_player"] = {
            "priority": 6,
            "speed_multiplier": 1.0,
            "start_distance": 5.0,
            "stop_distance": 2.0,
        }

        # Random look around
        components["minecraft:behavior.random_look_around"] = {
            "priority": 8,
            "look_distance": 6.0,
            "look_time": [4, 8],
        }

        # Random wander
        components["minecraft:behavior.wander"] = {
            "priority": 7,
            "speed_multiplier": 0.5,
            "wander_distance": 5,
            "start_chance": 0.3,
        }

        # Float (swimming idle)
        components["minecraft:behavior.float"] = {"priority": 0}

        # Add Java entity's custom behaviors
        if "behaviors" in java_entity:
            self._add_entity_behaviors(components, java_entity)

        # Add custom AI goals
        if "ai_goals" in java_entity:
            self._add_ai_goals(components, java_entity["ai_goals"])

    def _convert_java_entity(self, java_entity: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a single Java entity to Bedrock format."""
        entity_id = java_entity.get("id", "unknown_entity")
        namespace = java_entity.get("namespace", "modporter")
        full_id = f"{namespace}:{entity_id}"

        # Create entity definition
        bedrock_entity = {
            "format_version": "1.19.0",
            "minecraft:entity": {
                "description": {
                    "identifier": full_id,
                    "is_spawnable": java_entity.get("spawnable", True),
                    "is_summonable": java_entity.get("summonable", True),
                    "is_experimental": False,
                },
                "component_groups": {},
                "components": {},
                "events": {},
            },
        }

        # Parse Java properties
        properties = self._parse_java_entity_properties(java_entity)

        # Add base components
        components = bedrock_entity["minecraft:entity"]["components"]
        components.update(self.base_components.copy())

        # Update with entity-specific properties
        self._apply_entity_properties(components, properties)

        # Add behaviors
        self._add_entity_behaviors(components, java_entity)

        # Add AI goals if present
        if "ai_goals" in java_entity:
            self._add_ai_goals(components, java_entity["ai_goals"])

        # Add loot table if present
        if "loot_table" in java_entity:
            components["minecraft:loot"] = {"table": java_entity["loot_table"]}

        # Add spawn egg if applicable
        if java_entity.get("has_spawn_egg", False):
            components["minecraft:spawn_egg"] = {
                "base_color": java_entity.get("spawn_egg_primary", "#7F7F7F"),
                "overlay_color": java_entity.get("spawn_egg_secondary", "#FFFFFF"),
            }

        return bedrock_entity

    def _parse_java_entity_properties(self, java_entity: Dict[str, Any]) -> EntityProperties:
        """Parse Java entity properties."""
        properties = EntityProperties()

        if "attributes" in java_entity:
            attrs = java_entity["attributes"]
            properties.health = attrs.get("max_health", 20.0)
            properties.movement_speed = attrs.get("movement_speed", 0.25)
            properties.follow_range = attrs.get("follow_range", 16.0)
            properties.attack_damage = attrs.get("attack_damage", 0.0)
            properties.armor = attrs.get("armor", 0.0)
            properties.knockback_resistance = attrs.get("knockback_resistance", 0.0)

        # Determine entity type
        entity_category = java_entity.get("category", "passive").lower()
        try:
            properties.entity_type = EntityType(entity_category)
        except ValueError:
            logger.warning(f"Unknown entity category: {entity_category}, using passive")
            properties.entity_type = EntityType.PASSIVE

        # Environmental properties
        properties.can_swim = java_entity.get("can_swim", True)
        properties.can_climb = java_entity.get("can_climb", False)
        properties.can_fly = java_entity.get("can_fly", False)
        properties.breathes_air = java_entity.get("breathes_air", True)
        properties.breathes_water = java_entity.get("breathes_water", False)
        properties.pushable = java_entity.get("pushable", True)

        return properties

    def _apply_entity_properties(self, components: Dict[str, Any], properties: EntityProperties):
        """Apply entity properties to Bedrock components."""
        # Health
        components["minecraft:health"]["value"] = properties.health
        components["minecraft:health"]["max"] = properties.health

        # Movement
        components["minecraft:movement"]["value"] = properties.movement_speed

        # Combat properties
        if properties.attack_damage > 0:
            components["minecraft:damage"] = {
                "range": [properties.attack_damage, properties.attack_damage]
            }
            components["minecraft:attack"] = {"damage": properties.attack_damage}

        # Armor
        if properties.armor > 0:
            components["minecraft:damage_sensor"] = {
                "triggers": [
                    {
                        "cause": "all",
                        "damage_modifier": -(properties.armor * 4),  # Convert to damage reduction
                    }
                ]
            }

        # Knockback resistance
        if properties.knockback_resistance > 0:
            components["minecraft:knockback_resistance"] = {
                "value": properties.knockback_resistance
            }

        # Environmental adaptations
        if not properties.can_swim:
            components["minecraft:navigation.walk"]["avoid_water"] = True

        if properties.can_climb:
            components["minecraft:can_climb"] = {}

        if properties.can_fly:
            components["minecraft:can_fly"] = {}
            components["minecraft:movement.fly"] = {}

        if not properties.breathes_air:
            components["minecraft:breathable"] = {
                "breathes_air": False,
                "breathes_water": properties.breathes_water,
                "generates_bubbles": False,
            }

        if not properties.pushable:
            components["minecraft:pushable"] = {
                "is_pushable": False,
                "is_pushable_by_piston": False,
            }

        # Type family based on entity type
        type_families = ["mob"]
        if properties.entity_type == EntityType.HOSTILE:
            type_families.extend(["monster", "hostile"])
        elif properties.entity_type == EntityType.PASSIVE:
            type_families.append("passive")
        elif properties.entity_type == EntityType.NEUTRAL:
            type_families.append("neutral")
        elif properties.entity_type == EntityType.BOSS:
            type_families.extend(["boss", "hostile"])

        components["minecraft:type_family"]["family"] = type_families

    def _add_entity_behaviors(self, components: Dict[str, Any], java_entity: Dict[str, Any]):
        """Add behavior components based on Java entity behaviors."""
        behaviors = java_entity.get("behaviors", [])

        for behavior in behaviors:
            behavior_type = behavior.get("type", "")
            bedrock_behavior = self.behavior_mappings.get(behavior_type)

            if bedrock_behavior:
                behavior_config = behavior.get("config", {})
                components[bedrock_behavior] = behavior_config

    def _add_ai_goals(self, components: Dict[str, Any], ai_goals: List[Dict[str, Any]]):
        """
        Add AI goals as behavior components using comprehensive goal mappings.

        Args:
            components: Bedrock entity components dict
            ai_goals: List of Java AI goal definitions
        """
        for goal in ai_goals:
            goal_type = goal.get("type", "").lower()
            priority = goal.get("priority", 1)
            goal_config = goal.get("config", {})

            # Try to find matching behavior using goal_mappings
            bedrock_behavior = self.goal_mappings.get(goal_type)

            if bedrock_behavior:
                # Build behavior config from goal config and defaults
                behavior_config = self._build_behavior_config(goal_type, priority, goal_config)
                components[bedrock_behavior] = behavior_config
            else:
                # Fallback to legacy if-elif chain for additional goal types
                self._add_legacy_goal(components, goal_type, priority, goal_config)

    def _build_behavior_config(
        self, goal_type: str, priority: int, goal_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build Bedrock behavior config from Java goal config.

        Args:
            goal_type: The goal type (e.g., "melee_attack")
            priority: Goal priority
            goal_config: Goal-specific configuration

        Returns:
            Bedrock behavior configuration dict
        """
        config = {"priority": priority}

        # Common config mappings
        speed_mappings = ["speed", "speed_multiplier", "movement_speed"]
        for key in speed_mappings:
            if key in goal_config:
                config["speed_multiplier"] = goal_config[key]
                break
        else:
            # Set default speed multipliers for common behaviors
            if goal_type in ["melee_attack", "attack", "hurt_target"]:
                config["speed_multiplier"] = 1.0
            elif goal_type in ["follow", "follow_player"]:
                config["speed_multiplier"] = 1.0
            elif goal_type in ["wander", "stroll", "random_stroll"]:
                config["speed_multiplier"] = 0.8
            elif goal_type in ["panic", "flee", "avoid"]:
                config["speed_multiplier"] = 1.25

        # Range/distance mappings
        if "range" in goal_config:
            if goal_type in ["look_at_player", "look", "look_at_target"]:
                config["look_distance"] = goal_config["range"]
            elif goal_type in ["ranged_attack", "attack_with_range"]:
                config["attack_radius"] = goal_config["range"]
            elif goal_type in ["tempt", "follow"]:
                config["within_radius"] = goal_config["range"]

        if "distance" in goal_config:
            if goal_type in ["follow", "follow_player"]:
                config["start_distance"] = goal_config["distance"]
                config["stop_distance"] = goal_config.get(
                    "stop_distance", goal_config["distance"] / 2
                )

        # Track target mappings
        if goal_type in ["melee_attack", "attack", "attack_entity"]:
            config["track_target"] = goal_config.get("track_target", True)

        if "reach_multiplier" in goal_config:
            config["reach_multiplier"] = goal_config["reach_multiplier"]

        # Add remaining config items
        for key, value in goal_config.items():
            if key not in [
                "priority",
                "speed",
                "speed_multiplier",
                "movement_speed",
                "range",
                "distance",
                "stop_distance",
                "track_target",
                "reach_multiplier",
            ]:
                config[key] = value

        return config

    def _add_legacy_goal(
        self, components: Dict[str, Any], goal_type: str, priority: int, goal_config: Dict[str, Any]
    ):
        """Handle legacy goal types not in goal_mappings."""
        # Additional goal type mappings for backwards compatibility
        legacy_mappings = {
            "move": "minecraft:behavior.move_towards_target",
            "look": "minecraft:behavior.look_at_player",
            "swim": "minecraft:behavior.swim",
            "fly": "minecraft:behavior.fly",
            "climb": "minecraft:behavior.climb",
            "jump": "minecraft:behavior.jump",
            "flee": "minecraft:behavior.avoid_entity",
            "hide": "minecraft:behavior.seek_shelter",
            "rest": "minecraft:behavior.restrict_sun",
            "seek_water": "minecraft:behavior.leave_water",
            "breed": "minecraft:behavior.breed",
            "tempt": "minecraft:behavior.tempt",
            "interact": "minecraft:behavior.interact",
            "trade": "Offers:behavior.trade_with_player",
            "pickup": "minecraft:behavior.pickup_items",
            "eat": "minecraft:behavior.item_consume",
        }

        bedrock_behavior = legacy_mappings.get(goal_type)
        if bedrock_behavior:
            config = {"priority": priority}
            if "speed" in goal_config:
                config["speed_multiplier"] = goal_config["speed"]
            if "range" in goal_config:
                config["look_distance"] = goal_config["range"]
            components[bedrock_behavior] = config

    def convert_ai_goals(self, java_goals: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Convert Java AI goals to Bedrock behaviors.

        Args:
            java_goals: List of Java AI goal definitions

        Returns:
            Dictionary of Bedrock behavior components
        """
        result = {}
        for goal in java_goals:
            goal_type = goal.get("type", "").lower()
            priority = goal.get("priority", 1)
            goal_config = goal.get("config", {})

            bedrock_behavior = self.goal_mappings.get(goal_type)
            if bedrock_behavior:
                result[bedrock_behavior] = self._build_behavior_config(
                    goal_type, priority, goal_config
                )

        return result

    def _generate_entity_behaviors(self, java_entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate separate behavior file for complex entities."""
        # For now, return None as behaviors are integrated into main entity file
        # In future versions, complex behaviors could be separated
        return None

    def _generate_entity_animations(self, java_entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate animation definitions for entities."""
        animations = java_entity.get("animations", [])
        if not animations:
            return None

        animation_definitions = {"format_version": "1.19.0", "animations": {}}

        for animation in animations:
            anim_name = animation.get("name", "default")
            animation_definitions["animations"][
                f"animation.{java_entity.get('id', 'entity')}.{anim_name}"
            ] = {
                "loop": animation.get("loop", False),
                "animation_length": animation.get("length", 1.0),
                "bones": animation.get("bones", {}),
            }

        return animation_definitions if animation_definitions["animations"] else None

    def write_entities_to_disk(
        self, entities: Dict[str, Any], bp_path: Path, rp_path: Path
    ) -> Dict[str, List[Path]]:
        """
        Write entity definitions to disk.

        Args:
            entities: Dictionary of entity definitions
            bp_path: Behavior pack path
            rp_path: Resource pack path

        Returns:
            Dictionary of written file paths
        """
        written_files = {"entities": [], "behaviors": [], "animations": []}

        # Create directories
        bp_entities_dir = bp_path / "entities"
        bp_entities_dir.mkdir(parents=True, exist_ok=True)

        rp_entity_dir = rp_path / "entity"
        rp_entity_dir.mkdir(parents=True, exist_ok=True)

        for entity_key, entity_data in entities.items():
            try:
                if entity_key.endswith("_behaviors"):
                    # Write behavior file
                    entity_id = entity_key.replace("_behaviors", "")
                    behavior_file = bp_entities_dir / f"{entity_id.split(':')[-1]}_behaviors.json"
                    with open(behavior_file, "w", encoding="utf-8") as f:
                        json.dump(entity_data, f, indent=2, ensure_ascii=False)
                    written_files["behaviors"].append(behavior_file)

                elif entity_key.endswith("_animations"):
                    # Write animation file to resource pack
                    entity_id = entity_key.replace("_animations", "")
                    anim_file = rp_entity_dir / f"{entity_id.split(':')[-1]}_animations.json"
                    with open(anim_file, "w", encoding="utf-8") as f:
                        json.dump(entity_data, f, indent=2, ensure_ascii=False)
                    written_files["animations"].append(anim_file)

                else:
                    # Write main entity file
                    entity_file = bp_entities_dir / f"{entity_key.split(':')[-1]}.json"
                    with open(entity_file, "w", encoding="utf-8") as f:
                        json.dump(entity_data, f, indent=2, ensure_ascii=False)
                    written_files["entities"].append(entity_file)

            except Exception as e:
                logger.error(f"Failed to write entity {entity_key}: {e}")
                continue

        logger.info(
            f"Written {len(written_files['entities'])} entities, "
            f"{len(written_files['behaviors'])} behaviors, "
            f"{len(written_files['animations'])} animations to disk"
        )

        return written_files
