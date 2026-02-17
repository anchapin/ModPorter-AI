"""
Block and Item Generator for creating Bedrock block and item definitions
Part of the Bedrock Add-on Generation System (Issue #6)
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MaterialType(Enum):
    STONE = "stone"
    WOOD = "wood"
    METAL = "metal"
    GLASS = "glass"
    CLOTH = "cloth"
    DIRT = "dirt"
    SAND = "sand"
    SNOW = "snow"
    ICE = "ice"
    WATER = "water"
    LAVA = "lava"


@dataclass
class BlockProperties:
    hardness: float = 1.0
    resistance: float = 1.0
    light_emission: int = 0
    light_dampening: int = 15
    is_solid: bool = True
    can_contain_liquid: bool = False
    material_type: MaterialType = MaterialType.STONE
    flammable: bool = False
    map_color: str = "#8F7748"


@dataclass
class ItemProperties:
    stack_size: int = 64
    durability: Optional[int] = None
    is_tool: bool = False
    is_food: bool = False
    nutrition: int = 0
    saturation: float = 0.0
    can_always_eat: bool = False


@dataclass
class ToolProperties(ItemProperties):
    """Properties specific to tool items."""
    tool_type: str = "generic"  # pickaxe, axe, shovel, hoe, sword
    mining_speed: float = 1.0
    mining_level: int = 1  # wood=1, stone=2, iron=3, diamond=4, netherite=5
    enchantable: bool = True
    attack_damage: float = 1.0
    attack_speed: float = 1.0


@dataclass
class ArmorProperties(ItemProperties):
    """Properties specific to armor items."""
    armor_type: str = "generic"  # helmet, chestplate, leggings, boots
    armor_value: int = 1
    toughness: float = 0.0
    enchantable: bool = True
    knockback_resistance: float = 0.0
    equipped_ability: Optional[str] = None


@dataclass
class ConsumableProperties(ItemProperties):
    """Properties specific to consumable items."""
    effect: Optional[str] = None
    effect_duration: int = 0  # in ticks
    effect_amplifier: int = 0
    particle_on_consume: Optional[str] = None
    use_animation: bool = True
    container_entity: Optional[str] = None  # for potions


@dataclass
class RangedWeaponProperties(ItemProperties):
    """Properties specific to ranged weapons."""
    ammo_item: Optional[str] = None
    ammo_count: int = 1
    projectile_item: Optional[str] = None
    shoot_power: float = 1.0
    shoot_range: float = 20.0
    charge_time: float = 1.0
    allow_offhand: bool = False


@dataclass
class RareItemProperties(ItemProperties):
    """Properties for special/rare items with unique properties."""
    rarity: str = "common"  # common, uncommon, rare, epic, legendary
    item_properties: Dict[str, Any] = None
    enchantments: List[Dict[str, Any]] = None
    can_destroy_blocks: bool = False
    creative_category: Optional[str] = None
    
    def __post_init__(self):
        if self.item_properties is None:
            self.item_properties = {}
        if self.enchantments is None:
            self.enchantments = []


class BlockItemGenerator:
    """
    Generator for Bedrock block and item definition files.
    Converts Java mod blocks and items to Bedrock format.
    """
    
    def __init__(self):
        # Bedrock block definition template
        self.block_template = {
            "format_version": "1.19.0",
            "": {
                "description": {
                    "identifier": "",
                    "register_to_creative_menu": True
                },
                "components": {},
                "events": {}
            }
        }
        
        # Bedrock item definition template
        self.item_template = {
            "format_version": "1.19.0",
            "": {
                "description": {
                    "identifier": "",
                    "register_to_creative_menu": True
                },
                "components": {}
            }
        }
        
        # Creative menu categories
        self.creative_categories = {
            "building": "itemGroup.name.construction",
            "decoration": "itemGroup.name.decoration", 
            "redstone": "itemGroup.name.redstone",
            "transportation": "itemGroup.name.transportation",
            "misc": "itemGroup.name.misc",
            "food": "itemGroup.name.food",
            "tools": "itemGroup.name.tools",
            "combat": "itemGroup.name.combat",
            "brewing": "itemGroup.name.brewing"
        }
    
    def generate_blocks(self, java_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate Bedrock block definitions from Java blocks.
        
        Args:
            java_blocks: List of Java block definitions
            
        Returns:
            Dictionary of Bedrock block definitions
        """
        logger.info(f"Generating Bedrock blocks for {len(java_blocks)} Java blocks")
        bedrock_blocks = {}
        
        for java_block in java_blocks:
            try:
                bedrock_block = self._convert_java_block(java_block)
                block_id = bedrock_block["minecraft:block"]["description"]["identifier"]
                bedrock_blocks[block_id] = bedrock_block
            except Exception as e:
                logger.error(f"Failed to convert block {java_block.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Successfully generated {len(bedrock_blocks)} Bedrock blocks")
        return bedrock_blocks
    
    def generate_items(self, java_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate Bedrock item definitions from Java items.
        
        Args:
            java_items: List of Java item definitions
            
        Returns:
            Dictionary of Bedrock item definitions
        """
        logger.info(f"Generating Bedrock items for {len(java_items)} Java items")
        bedrock_items = {}
        
        for java_item in java_items:
            try:
                bedrock_item = self._convert_java_item(java_item)
                item_id = bedrock_item["minecraft:item"]["description"]["identifier"]
                bedrock_items[item_id] = bedrock_item
            except Exception as e:
                logger.error(f"Failed to convert item {java_item.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Successfully generated {len(bedrock_items)} Bedrock items")
        return bedrock_items
    
    def generate_recipes(self, java_recipes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert Java recipes to Bedrock format.
        
        Args:
            java_recipes: List of Java recipe definitions
            
        Returns:
            Dictionary of Bedrock recipes
        """
        logger.info(f"Converting {len(java_recipes)} Java recipes to Bedrock format")
        bedrock_recipes = {}
        
        for java_recipe in java_recipes:
            try:
                bedrock_recipe = self._convert_java_recipe(java_recipe)
                if bedrock_recipe:
                    recipe_id = bedrock_recipe.get("identifier", f"recipe_{len(bedrock_recipes)}")
                    bedrock_recipes[recipe_id] = bedrock_recipe
            except Exception as e:
                logger.error(f"Failed to convert recipe {java_recipe.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Successfully converted {len(bedrock_recipes)} recipes")
        return bedrock_recipes
    
    # Specialized Item Template Methods for Issue #451
    
    def generate_tool_item(self, java_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a Bedrock tool item definition from Java tool.
        
        Args:
            java_item: Java tool item definition
            
        Returns:
            Bedrock tool item definition
        """
        tool_props = self._parse_tool_properties(java_item)
        return self._create_bedrock_tool(java_item, tool_props)
    
    def generate_armor_item(self, java_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a Bedrock armor item definition from Java armor.
        
        Args:
            java_item: Java armor item definition
            
        Returns:
            Bedrock armor item definition
        """
        armor_props = self._parse_armor_properties(java_item)
        return self._create_bedrock_armor(java_item, armor_props)
    
    def generate_consumable_item(self, java_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a Bedrock consumable item definition from Java consumable.
        
        Args:
            java_item: Java consumable item definition
            
        Returns:
            Bedrock consumable item definition
        """
        consumable_props = self._parse_consumable_properties(java_item)
        return self._create_bedrock_consumable(java_item, consumable_props)
    
    def generate_ranged_weapon_item(self, java_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a Bedrock ranged weapon item definition from Java ranged weapon.
        
        Args:
            java_item: Java ranged weapon definition
            
        Returns:
            Bedrock ranged weapon item definition
        """
        ranged_props = self._parse_ranged_weapon_properties(java_item)
        return self._create_bedrock_ranged_weapon(java_item, ranged_props)
    
    def generate_rare_item(self, java_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a Bedrock rare/special item definition from Java special item.
        
        Args:
            java_item: Java rare item definition
            
        Returns:
            Bedrock rare item definition
        """
        rare_props = self._parse_rare_item_properties(java_item)
        return self._create_bedrock_rare_item(java_item, rare_props)
    
    def _parse_tool_properties(self, java_item: Dict[str, Any]) -> ToolProperties:
        """Parse Java tool properties."""
        props = ToolProperties()
        
        if 'properties' in java_item:
            java_props = java_item['properties']
            props.stack_size = java_props.get('max_stack_size', 1)
            props.durability = java_props.get('max_damage', 100)
            props.tool_type = java_props.get('tool_type', 'generic')
            props.mining_speed = java_props.get('mining_speed', 1.0)
            props.mining_level = java_props.get('mining_level', 1)
            props.attack_damage = java_props.get('attack_damage', 1.0)
            props.attack_speed = java_props.get('attack_speed', 1.0)
            props.is_tool = True
        
        return props
    
    def _parse_armor_properties(self, java_item: Dict[str, Any]) -> ArmorProperties:
        """Parse Java armor properties."""
        props = ArmorProperties()
        
        if 'properties' in java_item:
            java_props = java_item['properties']
            props.stack_size = java_props.get('max_stack_size', 1)
            props.durability = java_props.get('max_damage', 100)
            props.armor_type = java_props.get('armor_type', 'generic')
            props.armor_value = java_props.get('armor_value', 1)
            props.toughness = java_props.get('toughness', 0.0)
        
        return props
    
    def _parse_consumable_properties(self, java_item: Dict[str, Any]) -> ConsumableProperties:
        """Parse Java consumable properties."""
        props = ConsumableProperties()
        
        if 'properties' in java_item:
            java_props = java_item['properties']
            props.stack_size = java_props.get('max_stack_size', 64)
            props.is_food = True
            props.nutrition = java_props.get('nutrition', 1)
            props.saturation = java_props.get('saturation', 0.6)
            props.can_always_eat = java_props.get('can_always_eat', False)
            props.effect = java_props.get('effect')
            props.effect_duration = java_props.get('effect_duration', 0)
            props.effect_amplifier = java_props.get('effect_amplifier', 0)
            props.container_entity = java_props.get('container_entity')
        
        return props
    
    def _parse_ranged_weapon_properties(self, java_item: Dict[str, Any]) -> RangedWeaponProperties:
        """Parse Java ranged weapon properties."""
        props = RangedWeaponProperties()
        
        if 'properties' in java_item:
            java_props = java_item['properties']
            props.stack_size = java_props.get('max_stack_size', 1)
            props.durability = java_props.get('max_damage', 100)
            props.ammo_item = java_props.get('ammo_item')
            props.ammo_count = java_props.get('ammo_count', 1)
            props.projectile_item = java_props.get('projectile_item')
            props.shoot_power = java_props.get('shoot_power', 1.0)
            props.shoot_range = java_props.get('shoot_range', 20.0)
            props.charge_time = java_props.get('charge_time', 1.0)
        
        return props
    
    def _parse_rare_item_properties(self, java_item: Dict[str, Any]) -> RareItemProperties:
        """Parse Java rare/special item properties."""
        props = RareItemProperties()
        
        if 'properties' in java_item:
            java_props = java_item['properties']
            props.stack_size = java_props.get('max_stack_size', 1)
            props.durability = java_props.get('max_damage')
            props.rarity = java_props.get('rarity', 'common')
            props.item_properties = java_props.get('item_properties', {})
            props.enchantments = java_props.get('enchantments', [])
            props.can_destroy_blocks = java_props.get('can_destroy_blocks', False)
        
        return props
    
    def _create_bedrock_tool(self, java_item: Dict[str, Any], props: ToolProperties) -> Dict[str, Any]:
        """Create Bedrock tool item definition."""
        item_id = java_item.get('id', 'unknown_tool')
        namespace = java_item.get('namespace', 'modporter')
        full_id = f"{namespace}:{item_id}"
        
        # Map tool types to Bedrock item components
        tool_component_map = {
            'pickaxe': 'minecraft:mining_speed',
            'axe': 'minecraft:mining_speed',
            'shovel': 'minecraft:mining_speed',
            'hoe': 'minecraft:mining_speed',
            'sword': 'minecraft:attack_damage'
        }
        
        bedrock_item = {
            "format_version": "1.19.0",
            "minecraft:item": {
                "description": {
                    "identifier": full_id,
                    "register_to_creative_menu": True
                },
                "components": {}
            }
        }
        
        components = bedrock_item["minecraft:item"]["components"]
        
        # Icon
        components["minecraft:icon"] = {"texture": item_id}
        
        # Stack size (tools are typically 1)
        components["minecraft:max_stack_size"] = props.stack_size
        
        # Durability
        if props.durability:
            components["minecraft:durability"] = {"max_durability": props.durability}
            components["minecraft:repairable"] = {
                "repair_items": [
                    {"items": [full_id], "repair_amount": "context.other->q.remaining_durability + 0.05 * context.other->q.max_durability"}
                ]
            }
        
        # Tool-specific components
        if props.tool_type in tool_component_map:
            component_name = tool_component_map[props.tool_type]
            if component_name == 'minecraft:mining_speed':
                components[component_name] = {"speed": props.mining_speed}
            elif component_name == 'minecraft:attack_damage':
                components[component_name] = {"damage": props.attack_damage}
        
        # Weapon/Tool cooldown
        if props.tool_type == 'sword':
            components["minecraft:weapon"] = {"offhand_usable": True}
        
        # Enchantments
        if props.enchantable:
            components["minecraft:enchantable"] = {"slot": "all"}
        
        # Category
        components["minecraft:creative_category"] = {"category": "itemGroup.name.tools"}
        
        return bedrock_item
    
    def _create_bedrock_armor(self, java_item: Dict[str, Any], props: ArmorProperties) -> Dict[str, Any]:
        """Create Bedrock armor item definition."""
        item_id = java_item.get('id', 'unknown_armor')
        namespace = java_item.get('namespace', 'modporter')
        full_id = f"{namespace}:{item_id}"
        
        # Map armor types to Bedrock armor components
        armor_slot_map = {
            'helmet': 'minecraft:armor',
            'chestplate': 'minecraft:armor',
            'leggings': 'minecraft:armor',
            'boots': 'minecraft:armor'
        }
        
        bedrock_item = {
            "format_version": "1.19.0",
            "minecraft:item": {
                "description": {
                    "identifier": full_id,
                    "register_to_creative_menu": True
                },
                "components": {}
            }
        }
        
        components = bedrock_item["minecraft:item"]["components"]
        
        # Icon
        components["minecraft:icon"] = {"texture": item_id}
        
        # Stack size
        components["minecraft:max_stack_size"] = props.stack_size
        
        # Durability
        if props.durability:
            components["minecraft:durability"] = {"max_durability": props.durability}
            components["minecraft:repairable"] = {
                "repair_items": [
                    {"items": [full_id], "repair_amount": "context.other->q.remaining_durability + 0.1 * context.other->q.max_durability"}
                ]
            }
        
        # Armor value
        if props.armor_type in armor_slot_map:
            components["minecraft:armor"] = {
                "slot": props.armor_type,
                "texture_type": "generic",
                "protection": props.armor_value
            }
        
        # Toughness
        if props.toughness > 0:
            components["minecraft:armor_toughness"] = {"toughness": props.toughness}
        
        # Knockback resistance
        if props.knockback_resistance > 0:
            components["minecraft:knockback_resistance"] = {"value": props.knockback_resistance}
        
        # Enchantments
        if props.enchantable:
            components["minecraft:enchantable"] = {"slot": "armor"}
        
        # Category
        components["minecraft:creative_category"] = {"category": "itemGroup.name.combat"}
        
        return bedrock_item
    
    def _create_bedrock_consumable(self, java_item: Dict[str, Any], props: ConsumableProperties) -> Dict[str, Any]:
        """Create Bedrock consumable item definition."""
        item_id = java_item.get('id', 'unknown_consumable')
        namespace = java_item.get('namespace', 'modporter')
        full_id = f"{namespace}:{item_id}"
        
        bedrock_item = {
            "format_version": "1.19.0",
            "minecraft:item": {
                "description": {
                    "identifier": full_id,
                    "register_to_creative_menu": True
                },
                "components": {}
            }
        }
        
        components = bedrock_item["minecraft:item"]["components"]
        
        # Icon
        components["minecraft:icon"] = {"texture": item_id}
        
        # Stack size
        components["minecraft:max_stack_size"] = props.stack_size
        
        # Food component (required for consumables)
        food_component = {
            "nutrition": props.nutrition,
            "saturation_modifier": props.saturation
        }
        if props.can_always_eat:
            food_component["can_always_eat"] = True
        if props.use_animation:
            food_component["using_converts_to"] = java_item.get('container_item', 'minecraft:bowl')
        
        components["minecraft:food"] = food_component
        
        # Effect (using potion component for effects)
        if props.effect:
            components["minecraft:potion"] = {
                "id": props.effect,
                "duration": props.effect_duration / 20.0,  # Convert ticks to seconds
                "amplifier": props.effect_amplifier
            }
        
        # Particle effect
        if props.particle_on_consume:
            components["minecraft:particle_on_consume"] = {"particle": props.particle_on_consume}
        
        # Category
        category = "itemGroup.name.food"
        if props.container_entity:
            category = "itemGroup.name.brewing"
        components["minecraft:creative_category"] = {"category": category}
        
        return bedrock_item
    
    def _create_bedrock_ranged_weapon(self, java_item: Dict[str, Any], props: RangedWeaponProperties) -> Dict[str, Any]:
        """Create Bedrock ranged weapon item definition."""
        item_id = java_item.get('id', 'unknown_ranged')
        namespace = java_item.get('namespace', 'modporter')
        full_id = f"{namespace}:{item_id}"
        
        bedrock_item = {
            "format_version": "1.19.0",
            "minecraft:item": {
                "description": {
                    "identifier": full_id,
                    "register_to_creative_menu": True
                },
                "components": {}
            }
        }
        
        components = bedrock_item["minecraft:item"]["components"]
        
        # Icon
        components["minecraft:icon"] = {"texture": item_id}
        
        # Stack size
        components["minecraft:max_stack_size"] = props.stack_size
        
        # Durability
        if props.durability:
            components["minecraft:durability"] = {"max_durability": props.durability}
            components["minecraft:repairable"] = {
                "repair_items": [
                    {"items": [full_id], "repair_amount": "context.other->q.remaining_durability + 0.05 * context.other->q.max_durability"}
                ]
            }
        
        # Ranged attack component
        if props.projectile_item:
            components["minecraft:shooter"] = {
                "ammunition": [
                    {
                        "item": props.projectile_item,
                        "max_use_count": props.ammo_count
                    }
                ]
            }
        
        # Offhand usability
        if props.allow_offhand:
            components["minecraft:weapon"] = {"offhand_usable": True}
        
        # Category
        components["minecraft:creative_category"] = {"category": "itemGroup.name.combat"}
        
        return bedrock_item
    
    def _create_bedrock_rare_item(self, java_item: Dict[str, Any], props: RareItemProperties) -> Dict[str, Any]:
        """Create Bedrock rare/special item definition."""
        item_id = java_item.get('id', 'unknown_rare')
        namespace = java_item.get('namespace', 'modporter')
        full_id = f"{namespace}:{item_id}"
        
        # Map rarity to display colors
        rarity_colors = {
            'common': '#FFFFFF',
            'uncommon': '#55FF55',
            'rare': '#5555FF',
            'epic': '#FF55FF',
            'legendary': '#FFAA00'
        }
        
        bedrock_item = {
            "format_version": "1.19.0",
            "minecraft:item": {
                "description": {
                    "identifier": full_id,
                    "register_to_creative_menu": True
                },
                "components": {}
            }
        }
        
        components = bedrock_item["minecraft:item"]["components"]
        
        # Icon with rarity color overlay
        icon_component = {"texture": item_id}
        color = rarity_colors.get(props.rarity, '#FFFFFF')
        components["minecraft:icon"] = icon_component
        
        # Stack size
        components["minecraft:max_stack_size"] = props.stack_size
        
        # Durability
        if props.durability:
            components["minecraft:durability"] = {"max_durability": props.durability}
        
        # Custom item properties
        for key, value in props.item_properties.items():
            components[key] = value
        
        # Enchantments
        if props.enchantments:
            components["minecraft:enchantable"] = {"slot": "all"}
            for enchant in props.enchantments:
                enchant_id = enchant.get('id', 'minecraft:unbreaking')
                level = enchant.get('level', 1)
                components[f"minecraft:{enchant_id}"] = {"level": level}
        
        # Block destruction ability
        if props.can_destroy_blocks:
            components["minecraft:can_destroy_in_creative"] = True
        
        # Custom category or default
        category = props.creative_category or "itemGroup.name.misc"
        components["minecraft:creative_category"] = {"category": category}
        
        return bedrock_item
    
    def _convert_java_block(self, java_block: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a single Java block to Bedrock format."""
        block_id = java_block.get('id', 'unknown_block')
        namespace = java_block.get('namespace', 'modporter')
        full_id = f"{namespace}:{block_id}"
        
        # Create block definition
        bedrock_block = {
            "format_version": "1.19.0",
            "minecraft:block": {
                "description": {
                    "identifier": full_id,
                    "register_to_creative_menu": True
                },
                "components": {},
                "events": {}
            }
        }
        
        # Parse Java properties
        properties = self._parse_java_block_properties(java_block)
        
        # Add basic components
        components = bedrock_block["minecraft:block"]["components"]
        
        # Material type and hardness
        if properties.material_type:
            components["minecraft:material_instances"] = {
                "*": {
                    "texture": block_id,
                    "render_method": "opaque"
                }
            }
        
        # Hardness and resistance
        components["minecraft:destructible_by_mining"] = {
            "seconds_to_destroy": properties.hardness
        }
        
        components["minecraft:destructible_by_explosion"] = {
            "explosion_resistance": properties.resistance
        }
        
        # Light properties
        if properties.light_emission > 0:
            components["minecraft:light_emission"] = properties.light_emission
        
        if properties.light_dampening != 15:
            components["minecraft:light_dampening"] = properties.light_dampening
        
        # Collision and geometry
        if properties.is_solid:
            components["minecraft:collision_box"] = True
            components["minecraft:selection_box"] = True
        else:
            components["minecraft:collision_box"] = False
        
        # Flammability
        if properties.flammable:
            components["minecraft:flammable"] = {
                "flame_odds": 5,
                "burn_odds": 5
            }
        
        # Map color
        components["minecraft:map_color"] = properties.map_color
        
        # Creative menu category
        category = self._determine_block_category(java_block)
        if category:
            components["minecraft:creative_category"] = {
                "category": category
            }
        
        return bedrock_block
    
    def _convert_java_item(self, java_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a single Java item to Bedrock format."""
        item_id = java_item.get('id', 'unknown_item')
        namespace = java_item.get('namespace', 'modporter')
        full_id = f"{namespace}:{item_id}"
        
        # Create item definition
        bedrock_item = {
            "format_version": "1.19.0",
            "minecraft:item": {
                "description": {
                    "identifier": full_id,
                    "register_to_creative_menu": True
                },
                "components": {}
            }
        }
        
        # Parse Java properties
        properties = self._parse_java_item_properties(java_item)
        
        # Add basic components
        components = bedrock_item["minecraft:item"]["components"]
        
        # Stack size
        components["minecraft:max_stack_size"] = properties.stack_size
        
        # Icon
        components["minecraft:icon"] = {
            "texture": item_id
        }
        
        # Durability for tools
        if properties.durability and properties.is_tool:
            components["minecraft:durability"] = {
                "max_durability": properties.durability
            }
            components["minecraft:repairable"] = {
                "repair_items": [
                    {
                        "items": [full_id],
                        "repair_amount": "context.other->q.remaining_durability + 0.05 * context.other->q.max_durability"
                    }
                ]
            }
        
        # Food properties
        if properties.is_food:
            components["minecraft:food"] = {
                "nutrition": properties.nutrition,
                "saturation_modifier": properties.saturation
            }
            if properties.can_always_eat:
                components["minecraft:food"]["can_always_eat"] = True
        
        # Creative menu category
        category = self._determine_item_category(java_item)
        if category:
            components["minecraft:creative_category"] = {
                "category": category
            }
        
        return bedrock_item
    
    def _convert_java_recipe(self, java_recipe: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a single Java recipe to Bedrock format."""
        recipe_type = java_recipe.get('type', 'crafting_shaped')
        
        if recipe_type == 'crafting_shaped':
            return self._convert_shaped_recipe(java_recipe)
        elif recipe_type == 'crafting_shapeless':
            return self._convert_shapeless_recipe(java_recipe)
        elif recipe_type == 'smelting':
            return self._convert_smelting_recipe(java_recipe)
        else:
            logger.warning(f"Unsupported recipe type: {recipe_type}")
            return None
    
    def _convert_shaped_recipe(self, java_recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Convert shaped crafting recipe."""
        pattern = java_recipe.get('pattern', [])
        key = java_recipe.get('key', {})
        result = java_recipe.get('result', {})
        
        # Convert pattern to Bedrock format
        bedrock_pattern = []
        for row in pattern:
            bedrock_pattern.append(row)  # Keep the original pattern with key characters
        
        # Build ingredient key
        bedrock_key = {}
        for char, ingredient in key.items():
            if char != ' ':
                bedrock_key[char] = {
                    "item": ingredient.get('item', 'minecraft:air'),
                    "count": ingredient.get('count', 1)
                }
        
        return {
            "format_version": "1.19.0",
            "minecraft:recipe_shaped": {
                "description": {
                    "identifier": java_recipe.get('id', 'unknown_shaped_recipe')
                },
                "pattern": bedrock_pattern,
                "key": bedrock_key,
                "result": {
                    "item": result.get('item', 'minecraft:air'),
                    "count": result.get('count', 1)
                }
            }
        }
    
    def _convert_shapeless_recipe(self, java_recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Convert shapeless crafting recipe."""
        ingredients = java_recipe.get('ingredients', [])
        result = java_recipe.get('result', {})
        
        # Convert ingredients to Bedrock format
        bedrock_ingredients = []
        for ingredient in ingredients:
            if isinstance(ingredient, dict):
                bedrock_ingredients.append({
                    "item": ingredient.get('item', 'minecraft:air'),
                    "count": ingredient.get('count', 1)
                })
            elif isinstance(ingredient, str):
                bedrock_ingredients.append({
                    "item": ingredient,
                    "count": 1
                })
        
        return {
            "format_version": "1.19.0",
            "minecraft:recipe_shapeless": {
                "description": {
                    "identifier": java_recipe.get('id', 'unknown_shapeless_recipe')
                },
                "ingredients": bedrock_ingredients,
                "result": {
                    "item": result.get('item', 'minecraft:air'),
                    "count": result.get('count', 1)
                }
            }
        }
    
    def _convert_smelting_recipe(self, java_recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Convert smelting recipe."""
        ingredient = java_recipe.get('ingredient', {})
        result = java_recipe.get('result', {})
        java_recipe.get('experience', 0.0)
        cooking_time = java_recipe.get('cookingtime', 200)
        
        return {
            "format_version": "1.19.0",
            "minecraft:recipe_furnace": {
                "description": {
                    "identifier": java_recipe.get('id', 'unknown_smelting_recipe')
                },
                "input": ingredient.get('item', 'minecraft:air'),
                "output": result.get('item', 'minecraft:air'),
                "fuel": 1.0,
                "duration": cooking_time / 20.0  # Convert ticks to seconds
            }
        }
    
    def _parse_java_block_properties(self, java_block: Dict[str, Any]) -> BlockProperties:
        """Parse Java block properties and convert to Bedrock-compatible format."""
        properties = BlockProperties()
        
        # Extract properties from Java block data
        if 'properties' in java_block:
            props = java_block['properties']
            
            properties.hardness = props.get('hardness', 1.0)
            properties.resistance = props.get('resistance', properties.hardness)
            properties.light_emission = props.get('light_level', 0)
            properties.is_solid = props.get('solid', True)
            properties.flammable = props.get('flammable', False)
            
            # Determine material type from Java material
            material_str = props.get('material', 'stone').lower()
            try:
                properties.material_type = MaterialType(material_str)
            except ValueError:
                logger.warning(f"Unknown material type: {material_str}, using stone")
                properties.material_type = MaterialType.STONE
        
        return properties
    
    def _parse_java_item_properties(self, java_item: Dict[str, Any]) -> ItemProperties:
        """Parse Java item properties and convert to Bedrock-compatible format."""
        properties = ItemProperties()
        
        if 'properties' in java_item:
            props = java_item['properties']
            
            properties.stack_size = props.get('max_stack_size', 64)
            properties.durability = props.get('max_damage')
            properties.is_tool = props.get('is_tool', False)
            properties.is_food = props.get('is_food', False)
            
            if properties.is_food:
                properties.nutrition = props.get('nutrition', 1)
                properties.saturation = props.get('saturation', 0.6)
                properties.can_always_eat = props.get('can_always_eat', False)
        
        return properties
    
    def _determine_category(self, java_data: Dict[str, Any], default_category: str, 
                          category_rules: Dict[str, tuple]) -> Optional[str]:
        """Helper method to determine creative menu category based on tags and type."""
        tags = java_data.get('tags', [])
        data_type = java_data.get('type', '').lower()
        
        for category, (tag_matches, type_matches) in category_rules.items():
            if any(tag in tag_matches for tag in tags):
                return self.creative_categories[category]
            if any(match in data_type for match in type_matches):
                return self.creative_categories[category]
        
        return self.creative_categories[default_category]
    
    def _determine_block_category(self, java_block: Dict[str, Any]) -> Optional[str]:
        """Determine appropriate creative menu category for block."""
        block_category_rules = {
            'building': (['building', 'construction'], []),
            'decoration': (['decoration', 'decorative'], ['door', 'gate']),
            'redstone': (['redstone', 'power'], [])
        }
        return self._determine_category(java_block, 'building', block_category_rules)
    
    def _determine_item_category(self, java_item: Dict[str, Any]) -> Optional[str]:
        """Determine appropriate creative menu category for item."""
        item_category_rules = {
            'tools': (['tool', 'tools'], ['pickaxe', 'axe', 'shovel', 'hoe']),
            'combat': (['weapon', 'combat'], ['sword', 'bow']),
            'food': (['food', 'edible'], [])
        }
        return self._determine_category(java_item, 'misc', item_category_rules)
    
    def _write_json_files(self, definitions: Dict[str, Any], directory: Path, written_files: List[Path]) -> None:
        """Helper method to write JSON definitions to a directory."""
        directory.mkdir(parents=True, exist_ok=True)
        for item_id, definition in definitions.items():
            file_path = directory / f"{item_id.split(':')[-1]}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(definition, f, indent=2, ensure_ascii=False)
            written_files.append(file_path)

    def write_definitions_to_disk(self, blocks: Dict[str, Any], items: Dict[str, Any], 
                                recipes: Dict[str, Any], bp_path: Path, rp_path: Path) -> Dict[str, List[Path]]:
        """Write block, item, and recipe definitions to disk."""
        written_files = {'blocks': [], 'items': [], 'recipes': []}
        
        # Write blocks to both packs
        if blocks:
            # Behavior pack blocks
            self._write_json_files(blocks, bp_path / "blocks", written_files['blocks'])
            
            # Resource pack blocks (simplified for textures and models)
            rp_blocks = {}
            for block_id, block_def in blocks.items():
                rp_blocks[block_id] = {
                    "format_version": "1.19.0",
                    "minecraft:block": {
                        "description": {
                            "identifier": block_def["minecraft:block"]["description"]["identifier"]
                        }
                    }
                }
            
            self._write_json_files(rp_blocks, rp_path / "blocks", [])
        
        # Write items and recipes to behavior pack
        if items:
            self._write_json_files(items, bp_path / "items", written_files['items'])
        if recipes:
            self._write_json_files(recipes, bp_path / "recipes", written_files['recipes'])
        
        logger.info(f"Written {len(written_files['blocks'])} blocks, "
                   f"{len(written_files['items'])} items, "
                   f"{len(written_files['recipes'])} recipes to disk")
        
        return written_files