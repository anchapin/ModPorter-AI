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