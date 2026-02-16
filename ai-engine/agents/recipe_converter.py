"""
Recipe Converter Agent for converting Java mod recipes to Bedrock format.

This agent handles conversion of Java crafting recipes (shaped, shapeless, furnace)
to Bedrock-compatible recipe JSON files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

from crewai.tools import tool

logger = logging.getLogger(__name__)


# Java to Bedrock item ID mapping (simplified - would need expansion)
JAVA_TO_BEDROCK_ITEM_MAP = {
    # Ores and ingots
    'minecraft:iron_ingot': 'minecraft:iron_ingot',
    'minecraft:gold_ingot': 'minecraft:gold_ingot',
    'minecraft:copper_ingot': 'minecraft:copper_ingot',
    'minecraft:diamond': 'minecraft:diamond',
    'minecraft:emerald': 'minecraft:emerald',
    # Blocks
    'minecraft:iron_block': 'minecraft:iron_block',
    'minecraft:gold_block': 'minecraft:gold_block',
    'minecraft:diamond_block': 'minecraft:diamond_block',
    'minecraft:emerald_block': 'minecraft:emerald_block',
    'minecraft:copper_block': 'minecraft:copper_block',
    # Materials
    'minecraft:cobblestone': 'minecraft:cobblestone',
    'minecraft:stone': 'minecraft:stone',
    'minecraft:wooden_planks': 'minecraft:planks',
    'minecraft:oak_planks': 'minecraft:planks',
    'minecraft:spruce_planks': 'minecraft:spruce_planks',
    'minecraft:birch_planks': 'minecraft:birch_planks',
    'minecraft:jungle_planks': 'minecraft:jungle_planks',
    'minecraft:acacia_planks': 'minecraft:acacia_planks',
    'minecraft:dark_oak_planks': 'minecraft:dark_oak_planks',
    # Sticks and rods
    'minecraft:stick': 'minecraft:stick',
    'minecraft:bamboo': 'minecraft:bamboo',
    # Wool
    'minecraft:white_wool': 'minecraft:wool',
    'minecraft:orange_wool': 'minecraft:orange_wool',
    'minecraft:magenta_wool': 'minecraft:magenta_wool',
    'minecraft:light_blue_wool': 'minecraft:light_blue_wool',
    'minecraft:yellow_wool': 'minecraft:yellow_wool',
    'minecraft:lime_wool': 'minecraft:lime_wool',
    'minecraft:pink_wool': 'minecraft:pink_wool',
    'minecraft:gray_wool': 'minecraft:gray_wool',
    'minecraft:light_gray_wool': 'minecraft:light_gray_wool',
    'minecraft:cyan_wool': 'minecraft:cyan_wool',
    'minecraft:purple_wool': 'minecraft:purple_wool',
    'minecraft:blue_wool': 'minecraft:blue_wool',
    'minecraft:brown_wool': 'minecraft:brown_wool',
    'minecraft:green_wool': 'minecraft:green_wool',
    'minecraft:red_wool': 'minecraft:red_wool',
    'minecraft:black_wool': 'minecraft:black_wool',
    # Glass
    'minecraft:glass': 'minecraft:glass',
    'minecraft:glass_pane': 'minecraft:glass_pane',
    # Other common items
    'minecraft:paper': 'minecraft:paper',
    'minecraft:book': 'minecraft:book',
    'minecraft:slime_ball': 'minecraft:slime_ball',
    'minecraft:ender_pearl': 'minecraft:ender_pearl',
    'minecraft:blaze_rod': 'minecraft:blaze_rod',
    'minecraft:ghast_tear': 'minecraft:ghast_tear',
    'minecraft:nether_wart': 'minecraft:nether_wart',
    'minecraft:spider_eye': 'minecraft:spider_eye',
    'minecraft:fermented_spider_eye': 'minecraft:fermented_spider_eye',
    'minecraft:magma_cream': 'minecraft:magma_cream',
    'minecraft:dragon_breath': 'minecraft:dragon_breath',
    'minecraft:shulker_shell': 'minecraft:shulker_shell',
    'minecraft:prismarine_shard': 'minecraft:prismarine_shard',
    'minecraft:prismarine_crystals': 'minecraft:prismarine_crystals',
    # Dyes
    'minecraft:ink_sac': 'minecraft:ink_sac',
    'minecraft:red_dye': 'minecraft:red_dye',
    'minecraft:lapis_lazuli': 'minecraft:lapis_lazuli',
}


class RecipeConverterAgent:
    """
    Agent responsible for converting Java mod recipes to Bedrock format.
    
    Supports:
    - Shaped recipes (crafting table)
    - Shapeless recipes
    - Furnace/smelting recipes
    - Blast furnace recipes
    - Smithing recipes
    - Campfire and smoking recipes
    - Stonecutter recipes
    """
    
    _instance = None
    
    def __init__(self):
        self.item_mapping = JAVA_TO_BEDROCK_ITEM_MAP.copy()
        self.custom_mappings = {}
        
    @classmethod
    def get_instance(cls):
        """Get singleton instance of RecipeConverterAgent"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            RecipeConverterAgent.convert_recipe_tool,
            RecipeConverterAgent.convert_recipes_batch_tool,
            RecipeConverterAgent.map_item_id_tool,
            RecipeConverterAgent.validate_recipe_tool,
        ]
    
    def _map_java_item_to_bedrock(self, java_item_id: str) -> str:
        """Map a Java item ID to its Bedrock equivalent."""
        if java_item_id in self.custom_mappings:
            return self.custom_mappings[java_item_id]
        if java_item_id in self.item_mapping:
            return self.item_mapping[java_item_id]
        # Try case-insensitive match
        java_lower = java_item_id.lower()
        for key, value in self.item_mapping.items():
            if key.lower() == java_lower:
                return value
        # Return original if no mapping found
        logger.warning(f"No mapping found for item: {java_item_id}")
        return java_item_id
    
    def _parse_java_recipe(self, recipe_data: Dict) -> Dict:
        """Parse a Java recipe JSON into a normalized format."""
        recipe_type = recipe_data.get('type', '')
        
        normalized = {
            'original_type': recipe_type,
            'result_item': None,
            'result_count': 1,
            'result_data': 0,
            'ingredients': [],
            'pattern': [],
            'key': {},
            'cooking_time': None,
            'experience': 0.0,
        }
        
        # Parse result
        result = recipe_data.get('result', {})
        if isinstance(result, dict):
            normalized['result_item'] = result.get('item', '')
            normalized['result_count'] = result.get('count', 1)
            normalized['result_data'] = result.get('data', 0)
        elif isinstance(result, str):
            normalized['result_item'] = result
        
        # Handle different recipe types
        if 'crafting_shaped' in recipe_type:
            normalized['recipe_category'] = 'shaped'
            normalized['pattern'] = recipe_data.get('pattern', [])
            normalized['key'] = recipe_data.get('key', {})
        elif 'crafting_shapeless' in recipe_type:
            normalized['recipe_category'] = 'shapeless'
            normalized['ingredients'] = recipe_data.get('ingredients', [])
        elif 'smelting' in recipe_type:
            normalized['recipe_category'] = 'smelting'
            normalized['cooking_time'] = recipe_data.get('cookingtime', 200)
            normalized['experience'] = recipe_data.get('experience', 0.0)
            ingredient = recipe_data.get('ingredient')
            if ingredient:
                normalized['ingredients'] = [ingredient]
        elif 'blasting' in recipe_type:
            normalized['recipe_category'] = 'blasting'
            normalized['cooking_time'] = recipe_data.get('cookingtime', 100)
            normalized['experience'] = recipe_data.get('experience', 0.0)
            ingredient = recipe_data.get('ingredient')
            if ingredient:
                normalized['ingredients'] = [ingredient]
        elif 'smoking' in recipe_type:
            normalized['recipe_category'] = 'smoking'
            normalized['cooking_time'] = recipe_data.get('cookingtime', 100)
            normalized['experience'] = recipe_data.get('experience', 0.0)
            ingredient = recipe_data.get('ingredient')
            if ingredient:
                normalized['ingredients'] = [ingredient]
        elif 'campfire_cooking' in recipe_type:
            normalized['recipe_category'] = 'campfire'
            normalized['cooking_time'] = recipe_data.get('cookingtime', 600)
            normalized['experience'] = recipe_data.get('experience', 0.0)
            ingredient = recipe_data.get('ingredient')
            if ingredient:
                normalized['ingredients'] = [ingredient]
        elif 'stonecutting' in recipe_type:
            normalized['recipe_category'] = 'stonecutter'
            ingredient = recipe_data.get('ingredient')
            if ingredient:
                normalized['ingredients'] = [ingredient]
        elif 'smithing_transform' in recipe_type:
            normalized['recipe_category'] = 'smithing'
            normalized['base'] = recipe_data.get('base')
            normalized['addition'] = recipe_data.get('addition')
            normalized['template'] = recipe_data.get('template')
        else:
            normalized['recipe_category'] = 'unknown'
            logger.warning(f"Unknown recipe type: {recipe_type}")
        
        return normalized
    
    def _convert_shaped_to_bedrock(self, normalized_recipe: Dict, namespace: str, recipe_name: str) -> Dict:
        """Convert a shaped recipe to Bedrock format."""
        pattern = normalized_recipe.get('pattern', [])
        key = normalized_recipe.get('key', {})
        
        # Build Bedrock key mapping
        bedrock_key = {}
        for key_char, ingredient in key.items():
            item_data = ingredient.get('item', '')
            item_count = ingredient.get('count', 1)
            item_data_val = ingredient.get('data', 0)
            
            bedrock_item = self._map_java_item_to_bedrock(item_data)
            
            key_entry = {'item': bedrock_item, 'data': item_data_val}
            if item_count > 1:
                key_entry['count'] = item_count
                
            bedrock_key[key_char] = key_entry
        
        # Build result
        bedrock_result = {
            'item': self._map_java_item_to_bedrock(normalized_recipe.get('result_item', '')),
            'data': normalized_recipe.get('result_data', 0),
            'count': normalized_recipe.get('result_count', 1)
        }
        
        # Build Bedrock recipe
        bedrock_recipe = {
            'format_version': '1.20.10',
            'minecraft:recipe_shaped': {
                'description': {
                    'identifier': f'{namespace}:{recipe_name}'
                },
                'tags': ['crafting_table'],
                'pattern': pattern,
                'key': bedrock_key,
                'result': bedrock_result
            }
        }
        
        return bedrock_recipe
    
    def _convert_shapeless_to_bedrock(self, normalized_recipe: Dict, namespace: str, recipe_name: str) -> Dict:
        """Convert a shapeless recipe to Bedrock format."""
        ingredients = normalized_recipe.get('ingredients', [])
        
        bedrock_ingredients = []
        for ingredient in ingredients:
            if isinstance(ingredient, dict):
                item_data = ingredient.get('item', '')
                item_count = ingredient.get('count', 1)
                item_data_val = ingredient.get('data', 0)
                
                bedrock_item = self._map_java_item_to_bedrock(item_data)
                
                ingredient_entry = {'item': bedrock_item, 'data': item_data_val}
                if item_count > 1:
                    ingredient_entry['count'] = item_count
                    
                bedrock_ingredients.append(ingredient_entry)
            elif isinstance(ingredient, str):
                bedrock_ingredients.append({
                    'item': self._map_java_item_to_bedrock(ingredient),
                    'data': 0
                })
        
        bedrock_result = {
            'item': self._map_java_item_to_bedrock(normalized_recipe.get('result_item', '')),
            'data': normalized_recipe.get('result_data', 0),
            'count': normalized_recipe.get('result_count', 1)
        }
        
        bedrock_recipe = {
            'format_version': '1.20.10',
            'minecraft:recipe_shapeless': {
                'description': {
                    'identifier': f'{namespace}:{recipe_name}'
                },
                'tags': ['crafting_table'],
                'ingredients': bedrock_ingredients,
                'result': bedrock_result
            }
        }
        
        return bedrock_recipe
    
    def _convert_smelting_to_bedrock(self, normalized_recipe: Dict, namespace: str, recipe_name: str, recipe_type: str = 'smelting') -> Dict:
        """Convert a furnace-type recipe to Bedrock format."""
        ingredients = normalized_recipe.get('ingredients', [])
        
        if not ingredients:
            return None
            
        ingredient = ingredients[0]
        
        if isinstance(ingredient, dict):
            item_data = ingredient.get('item', '')
            item_data_val = ingredient.get('data', 0)
        else:
            item_data = ingredient
            item_data_val = 0
        
        bedrock_ingredient = {
            'item': self._map_java_item_to_bedrock(item_data),
            'data': item_data_val
        }
        
        bedrock_result = {
            'item': self._map_java_item_to_bedrock(normalized_recipe.get('result_item', '')),
            'data': normalized_recipe.get('result_data', 0),
            'count': normalized_recipe.get('result_count', 1)
        }
        
        cooking_time = normalized_recipe.get('cooking_time', 200)
        experience = normalized_recipe.get('experience', 0.0)
        
        # Determine Bedrock recipe type
        bedrock_type_map = {
            'smelting': 'minecraft:recipe_furnace',
            'blasting': 'minecraft:recipe_furnace_blast',
            'smoking': 'minecraft:recipe_furnace_smoke',
            'campfire': 'minecraft:recipe_campfire'
        }
        
        bedrock_recipe_type = bedrock_type_map.get(recipe_type, 'minecraft:recipe_furnace')
        
        bedrock_recipe = {
            'format_version': '1.20.10',
            bedrock_recipe_type: {
                'description': {
                    'identifier': f'{namespace}:{recipe_name}'
                },
                'tags': [recipe_type],
                'ingredients': [bedrock_ingredient],
                'result': bedrock_result,
                'cookingtime': cooking_time,
                'experience': experience
            }
        }
        
        return bedrock_recipe
    
    def _convert_stonecutter_to_bedrock(self, normalized_recipe: Dict, namespace: str, recipe_name: str) -> Dict:
        """Convert a stonecutter recipe to Bedrock format."""
        ingredients = normalized_recipe.get('ingredients', [])
        
        if not ingredients:
            return None
            
        ingredient = ingredients[0]
        
        if isinstance(ingredient, dict):
            item_data = ingredient.get('item', '')
            item_data_val = ingredient.get('data', 0)
        else:
            item_data = ingredient
            item_data_val = 0
        
        bedrock_ingredient = {
            'item': self._map_java_item_to_bedrock(item_data),
            'data': item_data_val
        }
        
        bedrock_result = {
            'item': self._map_java_item_to_bedrock(normalized_recipe.get('result_item', '')),
            'data': normalized_recipe.get('result_data', 0),
            'count': normalized_recipe.get('result_count', 1)
        }
        
        bedrock_recipe = {
            'format_version': '1.20.10',
            'minecraft:recipe_stonecutter': {
                'description': {
                    'identifier': f'{namespace}:{recipe_name}'
                },
                'tags': ['stonecutter'],
                'ingredients': [bedrock_ingredient],
                'result': bedrock_result
            }
        }
        
        return bedrock_recipe
    
    def _convert_smithing_to_bedrock(self, normalized_recipe: Dict, namespace: str, recipe_name: str) -> Dict:
        """Convert a smithing recipe to Bedrock format."""
        bedrock_result = {
            'item': self._map_java_item_to_bedrock(normalized_recipe.get('result_item', '')),
            'data': normalized_recipe.get('result_data', 0),
            'count': normalized_recipe.get('result_count', 1)
        }
        
        bedrock_recipe = {
            'format_version': '1.20.10',
            'minecraft:recipe_smithing_transform': {
                'description': {
                    'identifier': f'{namespace}:{recipe_name}'
                },
                'tags': ['smithing_table'],
                'template': normalized_recipe.get('template', {'item': 'minecraft:air'}),
                'base': normalized_recipe.get('base', {'item': 'minecraft:air'}),
                'addition': normalized_recipe.get('addition', {'item': 'minecraft:air'}),
                'result': bedrock_result
            }
        }
        
        return bedrock_recipe
    
    def convert_recipe(self, recipe_data: Dict, namespace: str = 'mod', recipe_name: str = None) -> Dict:
        """Convert a Java recipe to Bedrock format."""
        normalized = self._parse_java_recipe(recipe_data)
        
        if not recipe_name:
            result_item = normalized.get('result_item', 'unknown')
            if ':' in result_item:
                _, item_name = result_item.split(':', 1)
                recipe_name = item_name
            else:
                recipe_name = result_item
        
        category = normalized.get('recipe_category', 'unknown')
        
        if category == 'shaped':
            return self._convert_shaped_to_bedrock(normalized, namespace, recipe_name)
        elif category == 'shapeless':
            return self._convert_shapeless_to_bedrock(normalized, namespace, recipe_name)
        elif category == 'smelting':
            return self._convert_smelting_to_bedrock(normalized, namespace, recipe_name, 'smelting')
        elif category == 'blasting':
            return self._convert_smelting_to_bedrock(normalized, namespace, recipe_name, 'blasting')
        elif category == 'smoking':
            return self._convert_smelting_to_bedrock(normalized, namespace, recipe_name, 'smoking')
        elif category == 'campfire':
            return self._convert_smelting_to_bedrock(normalized, namespace, recipe_name, 'campfire')
        elif category == 'stonecutter':
            return self._convert_stonecutter_to_bedrock(normalized, namespace, recipe_name)
        elif category == 'smithing':
            return self._convert_smithing_to_bedrock(normalized, namespace, recipe_name)
        else:
            logger.warning(f"Cannot convert unknown recipe category: {category}")
            return {'success': False, 'error': f'Unknown recipe category: {category}'}
    
    def add_custom_item_mapping(self, java_item_id: str, bedrock_item_id: str):
        """Add a custom Java to Bedrock item mapping."""
        self.custom_mappings[java_item_id] = bedrock_item_id
    
    @tool
    @staticmethod
    def convert_recipe_tool(recipe_json: str) -> str:
        """Convert a Java recipe to Bedrock format."""
        try:
            recipe_data = json.loads(recipe_json)
            agent = RecipeConverterAgent.get_instance()
            
            namespace = recipe_data.pop('namespace', 'mod')
            recipe_name = recipe_data.pop('recipe_name', None)
            
            result = agent.convert_recipe(recipe_data, namespace, recipe_name)
            
            return json.dumps({'success': True, 'converted_recipe': result}, indent=2)
            
        except Exception as e:
            return json.dumps({'success': False, 'error': str(e)}, indent=2)
    
    @tool
    @staticmethod
    def convert_recipes_batch_tool(recipes_json: str) -> str:
        """Convert multiple Java recipes to Bedrock format in batch."""
        try:
            recipes = json.loads(recipes_json)
            agent = RecipeConverterAgent.get_instance()
            
            results = []
            for recipe_data in recipes:
                namespace = recipe_data.pop('namespace', 'mod')
                recipe_name = recipe_data.pop('recipe_name', None)
                
                converted = agent.convert_recipe(recipe_data, namespace, recipe_name)
                results.append(converted)
            
            return json.dumps({'success': True, 'converted_recipes': results, 'total_count': len(results)}, indent=2)
            
        except Exception as e:
            return json.dumps({'success': False, 'error': str(e)}, indent=2)
    
    @tool
    @staticmethod
    def map_item_id_tool(item_mapping_json: str) -> str:
        """Add custom Java to Bedrock item ID mappings."""
        try:
            mappings = json.loads(item_mapping_json)
            agent = RecipeConverterAgent.get_instance()
            
            if isinstance(mappings, list):
                for mapping in mappings:
                    if isinstance(mapping, dict) and 'java' in mapping and 'bedrock' in mapping:
                        agent.add_custom_item_mapping(mapping['java'], mapping['bedrock'])
            elif isinstance(mappings, dict):
                for java_id, bedrock_id in mappings.items():
                    agent.add_custom_item_mapping(java_id, bedrock_id)
            
            return json.dumps({'success': True, 'message': 'Custom item mappings added'}, indent=2)
            
        except Exception as e:
            return json.dumps({'success': False, 'error': str(e)}, indent=2)
    
    @tool
    @staticmethod
    def validate_recipe_tool(recipe_json: str) -> str:
        """Validate a Bedrock recipe for correctness."""
        try:
            recipe = json.loads(recipe_json)
            issues = []
            
            if 'format_version' not in recipe:
                issues.append('Missing format_version')
            
            recipe_types = [
                'minecraft:recipe_shaped', 'minecraft:recipe_shapeless',
                'minecraft:recipe_furnace', 'minecraft:recipe_furnace_blast',
                'minecraft:recipe_furnace_smoke', 'minecraft:recipe_campfire',
                'minecraft:recipe_stonecutter', 'minecraft:recipe_smithing_transform'
            ]
            
            found_type = None
            for rt in recipe_types:
                if rt in recipe:
                    found_type = rt
                    break
            
            if not found_type:
                issues.append(f'Unknown recipe type')
                return json.dumps({'valid': False, 'issues': issues}, indent=2)
            
            recipe_content = recipe.get(found_type, {})
            
            if 'description' not in recipe_content:
                issues.append('Missing description')
            elif 'identifier' not in recipe_content.get('description', {}):
                issues.append('Missing description.identifier')
            
            if found_type == 'minecraft:recipe_shaped':
                if 'pattern' not in recipe_content:
                    issues.append('Missing pattern')
                if 'key' not in recipe_content:
                    issues.append('Missing key')
                if 'result' not in recipe_content:
                    issues.append('Missing result')
            elif found_type == 'minecraft:recipe_shapeless':
                if 'ingredients' not in recipe_content:
                    issues.append('Missing ingredients')
                if 'result' not in recipe_content:
                    issues.append('Missing result')
            elif 'recipe_furnace' in found_type or found_type == 'minecraft:recipe_campfire':
                if 'ingredients' not in recipe_content:
                    issues.append('Missing ingredients')
                if 'result' not in recipe_content:
                    issues.append('Missing result')
            elif found_type == 'minecraft:recipe_stonecutter':
                if 'ingredients' not in recipe_content:
                    issues.append('Missing ingredients')
                if 'result' not in recipe_content:
                    issues.append('Missing result')
            
            is_valid = len(issues) == 0
            
            return json.dumps({'valid': is_valid, 'recipe_type': found_type, 'issues': issues}, indent=2)
            
        except Exception as e:
            return json.dumps({'valid': False, 'issues': [str(e)]}, indent=2)
