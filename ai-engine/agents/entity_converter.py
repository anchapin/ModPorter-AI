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
                    "is_experimental": False
                },
                "component_groups": {},
                "components": {},
                "events": {}
            }
        }
        
        # Common Bedrock entity components
        self.base_components = {
            "minecraft:type_family": {
                "family": ["mob"]
            },
            "minecraft:collision_box": {
                "width": 0.6,
                "height": 1.8
            },
            "minecraft:health": {
                "value": 20,
                "max": 20
            },
            "minecraft:movement": {
                "value": 0.25
            },
            "minecraft:navigation.walk": {
                "can_path_over_water": True,
                "avoid_water": True,
                "avoid_damage_at_all_costs": True
            },
            "minecraft:movement.basic": {},
            "minecraft:jump.static": {},
            "minecraft:can_climb": {},
            "minecraft:physics": {}
        }
        
        # Behavior mappings from Java to Bedrock
        self.behavior_mappings = {
            "follow_player": "minecraft:behavior.follow_player",
            "look_at_player": "minecraft:behavior.look_at_player", 
            "random_look_around": "minecraft:behavior.random_look_around",
            "random_stroll": "minecraft:behavior.random_stroll",
            "panic": "minecraft:behavior.panic",
            "float": "minecraft:behavior.float",
            "avoid_entity": "minecraft:behavior.avoid_entity",
            "melee_attack": "minecraft:behavior.melee_attack",
            "ranged_attack": "minecraft:behavior.ranged_attack",
            "breed": "minecraft:behavior.breed",
            "tempt": "minecraft:behavior.tempt"
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
    
    def _convert_java_entity(self, java_entity: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a single Java entity to Bedrock format."""
        entity_id = java_entity.get('id', 'unknown_entity')
        namespace = java_entity.get('namespace', 'modporter')
        full_id = f"{namespace}:{entity_id}"
        
        # Create entity definition
        bedrock_entity = {
            "format_version": "1.19.0",
            "minecraft:entity": {
                "description": {
                    "identifier": full_id,
                    "is_spawnable": java_entity.get('spawnable', True),
                    "is_summonable": java_entity.get('summonable', True),
                    "is_experimental": False
                },
                "component_groups": {},
                "components": {},
                "events": {}
            }
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
        if 'ai_goals' in java_entity:
            self._add_ai_goals(components, java_entity['ai_goals'])
        
        # Add loot table if present
        if 'loot_table' in java_entity:
            components["minecraft:loot"] = {
                "table": java_entity['loot_table']
            }
        
        # Add spawn egg if applicable
        if java_entity.get('has_spawn_egg', False):
            components["minecraft:spawn_egg"] = {
                "base_color": java_entity.get('spawn_egg_primary', "#7F7F7F"),
                "overlay_color": java_entity.get('spawn_egg_secondary', "#FFFFFF")
            }
        
        return bedrock_entity
    
    def _parse_java_entity_properties(self, java_entity: Dict[str, Any]) -> EntityProperties:
        """Parse Java entity properties."""
        properties = EntityProperties()
        
        if 'attributes' in java_entity:
            attrs = java_entity['attributes']
            properties.health = attrs.get('max_health', 20.0)
            properties.movement_speed = attrs.get('movement_speed', 0.25)
            properties.follow_range = attrs.get('follow_range', 16.0)
            properties.attack_damage = attrs.get('attack_damage', 0.0)
            properties.armor = attrs.get('armor', 0.0)
            properties.knockback_resistance = attrs.get('knockback_resistance', 0.0)
        
        # Determine entity type
        entity_category = java_entity.get('category', 'passive').lower()
        try:
            properties.entity_type = EntityType(entity_category)
        except ValueError:
            logger.warning(f"Unknown entity category: {entity_category}, using passive")
            properties.entity_type = EntityType.PASSIVE
        
        # Environmental properties
        properties.can_swim = java_entity.get('can_swim', True)
        properties.can_climb = java_entity.get('can_climb', False)
        properties.can_fly = java_entity.get('can_fly', False)
        properties.breathes_air = java_entity.get('breathes_air', True)
        properties.breathes_water = java_entity.get('breathes_water', False)
        properties.pushable = java_entity.get('pushable', True)
        
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
            components["minecraft:attack"] = {
                "damage": properties.attack_damage
            }
        
        # Armor
        if properties.armor > 0:
            components["minecraft:damage_sensor"] = {
                "triggers": [
                    {
                        "cause": "all",
                        "damage_modifier": -(properties.armor * 4)  # Convert to damage reduction
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
                "generates_bubbles": False
            }
        
        if not properties.pushable:
            components["minecraft:pushable"] = {
                "is_pushable": False,
                "is_pushable_by_piston": False
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
        behaviors = java_entity.get('behaviors', [])
        
        for behavior in behaviors:
            behavior_type = behavior.get('type', '')
            bedrock_behavior = self.behavior_mappings.get(behavior_type)
            
            if bedrock_behavior:
                behavior_config = behavior.get('config', {})
                components[bedrock_behavior] = behavior_config
    
    def _add_ai_goals(self, components: Dict[str, Any], ai_goals: List[Dict[str, Any]]):
        """Add AI goals as behavior components."""
        for goal in ai_goals:
            goal_type = goal.get('type', '')
            priority = goal.get('priority', 1)
            
            # Map Java AI goals to Bedrock behaviors
            if goal_type == "look_at_player":
                components["minecraft:behavior.look_at_player"] = {
                    "priority": priority,
                    "look_distance": goal.get('range', 6.0)
                }
            elif goal_type == "random_look_around":
                components["minecraft:behavior.random_look_around"] = {
                    "priority": priority
                }
            elif goal_type == "random_stroll":
                components["minecraft:behavior.random_stroll"] = {
                    "priority": priority,
                    "speed_multiplier": goal.get('speed', 1.0)
                }
            elif goal_type == "panic":
                components["minecraft:behavior.panic"] = {
                    "priority": priority,
                    "speed_multiplier": goal.get('speed_multiplier', 1.25)
                }
            elif goal_type == "melee_attack":
                components["minecraft:behavior.melee_attack"] = {
                    "priority": priority,
                    "speed_multiplier": goal.get('speed_multiplier', 1.0),
                    "track_target": goal.get('track_target', True)
                }
    
    def _generate_entity_behaviors(self, java_entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate separate behavior file for complex entities."""
        # For now, return None as behaviors are integrated into main entity file
        # In future versions, complex behaviors could be separated
        return None
    
    def _generate_entity_animations(self, java_entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate animation definitions for entities."""
        animations = java_entity.get('animations', [])
        if not animations:
            return None
        
        animation_definitions = {
            "format_version": "1.19.0",
            "animations": {}
        }
        
        for animation in animations:
            anim_name = animation.get('name', 'default')
            animation_definitions["animations"][f"animation.{java_entity.get('id', 'entity')}.{anim_name}"] = {
                "loop": animation.get('loop', False),
                "animation_length": animation.get('length', 1.0),
                "bones": animation.get('bones', {})
            }
        
        return animation_definitions if animation_definitions["animations"] else None
    
    def write_entities_to_disk(self, entities: Dict[str, Any], bp_path: Path, rp_path: Path) -> Dict[str, List[Path]]:
        """
        Write entity definitions to disk.
        
        Args:
            entities: Dictionary of entity definitions
            bp_path: Behavior pack path
            rp_path: Resource pack path
            
        Returns:
            Dictionary of written file paths
        """
        written_files = {
            'entities': [],
            'behaviors': [],
            'animations': []
        }
        
        # Create directories
        bp_entities_dir = bp_path / "entities"
        bp_entities_dir.mkdir(parents=True, exist_ok=True)
        
        rp_entity_dir = rp_path / "entity"
        rp_entity_dir.mkdir(parents=True, exist_ok=True)
        
        for entity_key, entity_data in entities.items():
            try:
                if entity_key.endswith('_behaviors'):
                    # Write behavior file
                    entity_id = entity_key.replace('_behaviors', '')
                    behavior_file = bp_entities_dir / f"{entity_id.split(':')[-1]}_behaviors.json"
                    with open(behavior_file, 'w', encoding='utf-8') as f:
                        json.dump(entity_data, f, indent=2, ensure_ascii=False)
                    written_files['behaviors'].append(behavior_file)
                    
                elif entity_key.endswith('_animations'):
                    # Write animation file to resource pack
                    entity_id = entity_key.replace('_animations', '')
                    anim_file = rp_entity_dir / f"{entity_id.split(':')[-1]}_animations.json"
                    with open(anim_file, 'w', encoding='utf-8') as f:
                        json.dump(entity_data, f, indent=2, ensure_ascii=False)
                    written_files['animations'].append(anim_file)
                    
                else:
                    # Write main entity file
                    entity_file = bp_entities_dir / f"{entity_key.split(':')[-1]}.json"
                    with open(entity_file, 'w', encoding='utf-8') as f:
                        json.dump(entity_data, f, indent=2, ensure_ascii=False)
                    written_files['entities'].append(entity_file)
                    
            except Exception as e:
                logger.error(f"Failed to write entity {entity_key}: {e}")
                continue
        
        logger.info(f"Written {len(written_files['entities'])} entities, "
                   f"{len(written_files['behaviors'])} behaviors, "
                   f"{len(written_files['animations'])} animations to disk")
        
        return written_files