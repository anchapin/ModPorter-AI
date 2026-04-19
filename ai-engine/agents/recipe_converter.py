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


def _load_item_mappings() -> Dict[str, str]:
    """Load Java to Bedrock item ID mappings from the bundled JSON file.

    Returns:
        Dictionary mapping Java item IDs to Bedrock item IDs

    The mappings are loaded from data/item_mappings.json which is generated
    by scripts/generate_item_mappings.py using minecraft-data.
    """
    try:
        data_dir = Path(__file__).parent.parent / "data"
        mappings_file = data_dir / "item_mappings.json"

        if not mappings_file.exists():
            logger.warning(
                f"Item mappings file not found at {mappings_file}. Falling back to empty mappings."
            )
            return {}

        with open(mappings_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        mappings = data.get("mappings", {})
        metadata = data.get("metadata", {})
        logger.info(
            f"Loaded {len(mappings)} item mappings from {mappings_file} "
            f"(version: {metadata.get('version', 'unknown')})"
        )
        return mappings

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing item mappings JSON: {e}. Falling back to empty mappings.")
        return {}
    except Exception as e:
        logger.error(f"Error loading item mappings: {e}. Falling back to empty mappings.")
        return {}


JAVA_TO_BEDROCK_ITEM_MAP = _load_item_mappings()


CUSTOM_RECIPE_TYPES = {
    # Farmer's Delight
    "farmersdelight:cooking": {
        "category": "cooking_pot",
        "description": "Cooking pot recipe",
        "convertible": True,
    },
    "farmersdelight:cutting": {
        "category": "cutting_board",
        "description": "Cutting board recipe",
        "convertible": True,
    },
    # Create
    "create:sequenced_assembly": {
        "category": "sequenced_assembly",
        "description": "Sequenced assembly recipe",
        "convertible": False,
    },
    "create:mechanical_crafting": {
        "category": "mechanical_crafting",
        "description": "Mechanical crafting (9x9 grid)",
        "convertible": True,
    },
    "create:mixing": {
        "category": "mixing",
        "description": "Mixing recipe",
        "convertible": False,
    },
    "create:pressing": {
        "category": "pressing",
        "description": "Pressing recipe",
        "convertible": True,
    },
    "create:deploying": {
        "category": "deploying",
        "description": "Deploying recipe",
        "convertible": True,
    },
    "create:milling": {
        "category": "milling",
        "description": "Milling recipe (Millstone)",
        "convertible": True,
    },
    "create:crushing": {
        "category": "crushing",
        "description": "Crushing recipe (Crushing Wheels)",
        "convertible": True,
    },
    "create:splashing": {
        "category": "splashing",
        "description": "Splashing recipe (Water)",
        "convertible": True,
    },
    "create:compacting": {
        "category": "compacting",
        "description": "Compacting recipe",
        "convertible": True,
    },
    "create:filling": {
        "category": "filling",
        "description": "Filling recipe",
        "convertible": False,
    },
    "create:emptying": {
        "category": "emptying",
        "description": "Emptying recipe",
        "convertible": False,
    },
    # Generic Forge patterns
    "forge:conditional": {
        "category": "conditional",
        "description": "Conditional recipe",
        "convertible": False,
    },
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
    - Custom Forge recipe types (Farmer's Delight, Create, etc.)
    """

    _instance = None

    def __init__(self):
        self.item_mapping = JAVA_TO_BEDROCK_ITEM_MAP.copy()
        self.custom_mappings = {}
        self.manual_review_reasons = []

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
        recipe_type = recipe_data.get("type", "")

        normalized = {
            "original_type": recipe_type,
            "result_item": None,
            "result_count": 1,
            "result_data": 0,
            "ingredients": [],
            "pattern": [],
            "key": {},
            "cooking_time": None,
            "experience": 0.0,
            "requires_manual_review": False,
            "manual_review_reason": None,
            "container": None,
            "tool": None,
        }

        # Handle forge:conditional - unwrap inner recipe
        if "forge:conditional" in recipe_type:
            recipe_data = self._unwrap_conditional_recipe(recipe_data)
            recipe_type = recipe_data.get("type", "")

        # Parse result - handle multi-output recipes (result array)
        result = recipe_data.get("result", {})
        if isinstance(result, dict):
            normalized["result_item"] = result.get("item", result.get("id", ""))
            normalized["result_count"] = result.get("count", 1)
            normalized["result_data"] = result.get("data", 0)
        elif isinstance(result, str):
            normalized["result_item"] = result
        elif isinstance(result, list) and len(result) > 0:
            first_result = result[0] if isinstance(result[0], dict) else {"item": result[0]}
            normalized["result_item"] = first_result.get("item", first_result.get("id", ""))
            normalized["result_count"] = first_result.get("count", 1)
            normalized["result_data"] = first_result.get("data", 0)

        # Handle different recipe types
        if "crafting_shaped" in recipe_type:
            normalized["recipe_category"] = "shaped"
            normalized["pattern"] = recipe_data.get("pattern", [])
            normalized["key"] = recipe_data.get("key", {})
        elif "crafting_shapeless" in recipe_type:
            normalized["recipe_category"] = "shapeless"
            normalized["ingredients"] = recipe_data.get("ingredients", [])
        elif "smelting" in recipe_type:
            normalized["recipe_category"] = "smelting"
            normalized["cooking_time"] = recipe_data.get("cookingtime", 200)
            normalized["experience"] = recipe_data.get("experience", 0.0)
            ingredient = recipe_data.get("ingredient")
            if ingredient:
                normalized["ingredients"] = [ingredient]
        elif "blasting" in recipe_type:
            normalized["recipe_category"] = "blasting"
            normalized["cooking_time"] = recipe_data.get("cookingtime", 100)
            normalized["experience"] = recipe_data.get("experience", 0.0)
            ingredient = recipe_data.get("ingredient")
            if ingredient:
                normalized["ingredients"] = [ingredient]
        elif "smoking" in recipe_type:
            normalized["recipe_category"] = "smoking"
            normalized["cooking_time"] = recipe_data.get("cookingtime", 100)
            normalized["experience"] = recipe_data.get("experience", 0.0)
            ingredient = recipe_data.get("ingredient")
            if ingredient:
                normalized["ingredients"] = [ingredient]
        elif "campfire_cooking" in recipe_type:
            normalized["recipe_category"] = "campfire"
            normalized["cooking_time"] = recipe_data.get("cookingtime", 600)
            normalized["experience"] = recipe_data.get("experience", 0.0)
            ingredient = recipe_data.get("ingredient")
            if ingredient:
                normalized["ingredients"] = [ingredient]
        elif "stonecutting" in recipe_type:
            normalized["recipe_category"] = "stonecutter"
            ingredient = recipe_data.get("ingredient")
            if ingredient:
                normalized["ingredients"] = [ingredient]
        elif "smithing_transform" in recipe_type:
            normalized["recipe_category"] = "smithing"
            normalized["base"] = recipe_data.get("base")
            normalized["addition"] = recipe_data.get("addition")
            normalized["template"] = recipe_data.get("template")
        # Custom Forge recipe types
        elif "farmersdelight:cooking" in recipe_type:
            normalized["recipe_category"] = "cooking_pot"
            normalized["cooking_time"] = recipe_data.get("cookingtime", 200)
            normalized["experience"] = recipe_data.get("experience", 0.0)
            normalized["container"] = recipe_data.get("container")
            ingredients = recipe_data.get("ingredients") or []
            if not ingredients:
                ingredient = recipe_data.get("ingredient")
                if ingredient:
                    ingredients = [ingredient]
            normalized["ingredients"] = ingredients
        elif "farmersdelight:cutting" in recipe_type:
            normalized["recipe_category"] = "cutting_board"
            normalized["tool"] = recipe_data.get("tool")
            ingredients = recipe_data.get("ingredients", [])
            normalized["ingredients"] = ingredients
        elif "create:mechanical_crafting" in recipe_type:
            normalized["recipe_category"] = "mechanical_crafting"
            normalized["pattern"] = recipe_data.get("pattern", [])
            normalized["key"] = recipe_data.get("key", {})
        elif "create:pressing" in recipe_type:
            normalized["recipe_category"] = "pressing"
            ingredient = recipe_data.get("ingredient")
            if ingredient:
                normalized["ingredients"] = [ingredient]
        elif "create:sequenced_assembly" in recipe_type:
            normalized["recipe_category"] = "sequenced_assembly"
            normalized["requires_manual_review"] = True
            normalized["manual_review_reason"] = (
                "Sequenced assembly requires multi-step crafting not supported in Bedrock"
            )
        elif "create:mixing" in recipe_type:
            normalized["recipe_category"] = "mixing"
            normalized["requires_manual_review"] = True
            normalized["manual_review_reason"] = (
                "Mixing recipes require Create's mixer block not available in Bedrock"
            )
        elif "create:deploying" in recipe_type:
            normalized["recipe_category"] = "deploying"
            normalized["ingredients"] = recipe_data.get("ingredients", [])
            normalized["tool"] = recipe_data.get("tool")
        elif "create:milling" in recipe_type:
            normalized["recipe_category"] = "milling"
            ingredient = recipe_data.get("ingredient")
            if ingredient:
                normalized["ingredients"] = [ingredient]
        elif "create:crushing" in recipe_type:
            normalized["recipe_category"] = "crushing"
            ingredient = recipe_data.get("ingredient")
            if ingredient:
                normalized["ingredients"] = [ingredient]
        elif "create:splashing" in recipe_type:
            normalized["recipe_category"] = "splashing"
            normalized["ingredients"] = recipe_data.get("ingredients", [])
        elif "create:compacting" in recipe_type:
            normalized["recipe_category"] = "compacting"
            normalized["ingredients"] = recipe_data.get("ingredients", [])
        elif "create:filling" in recipe_type or "create:emptying" in recipe_type:
            normalized["recipe_category"] = "fluid_interaction"
            normalized["requires_manual_review"] = True
            normalized["manual_review_reason"] = (
                "Fluid interaction recipes require Create's fluid mechanisms not available in Bedrock"
            )
        elif self._is_custom_recipe_type(recipe_type):
            normalized["recipe_category"] = "custom"
            normalized["requires_manual_review"] = True
            normalized["manual_review_reason"] = (
                f"Custom Forge recipe type '{recipe_type}' requires manual review"
            )
        else:
            normalized["recipe_category"] = "unknown"
            normalized["requires_manual_review"] = True
            normalized["manual_review_reason"] = f"Unknown recipe type: {recipe_type}"
            logger.warning(f"Unknown recipe type: {recipe_type}")

        return normalized

    def _is_custom_recipe_type(self, recipe_type: str) -> bool:
        """Check if a recipe type is a known custom Forge recipe type."""
        for custom_type in CUSTOM_RECIPE_TYPES.keys():
            if custom_type in recipe_type:
                return True
        return False

    def _unwrap_conditional_recipe(self, recipe_data: Dict) -> Dict:
        """Unwrap a forge:conditional recipe to get the inner recipe."""
        if "recipe" in recipe_data:
            inner = recipe_data["recipe"]
            if isinstance(inner, dict):
                return inner
        return recipe_data

    def _convert_shaped_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a shaped recipe to Bedrock format."""
        pattern = normalized_recipe.get("pattern", [])
        key = normalized_recipe.get("key", {})

        # Build Bedrock key mapping
        bedrock_key = {}
        for key_char, ingredient in key.items():
            # Handle both string (item ID or tag), list (alternatives), and dict formats
            if isinstance(ingredient, list):
                # List of alternatives - use the first item
                item_data = ingredient[0] if ingredient else "minecraft:air"
                item_count = 1
                item_data_val = 0
            elif isinstance(ingredient, str):
                item_data = ingredient
                item_count = 1
                item_data_val = 0
            else:
                item_data = ingredient.get("item", "")
                item_count = ingredient.get("count", 1)
                item_data_val = ingredient.get("data", 0)

            bedrock_item = self._map_java_item_to_bedrock(item_data)

            key_entry = {"item": bedrock_item, "data": item_data_val}
            if item_count > 1:
                key_entry["count"] = item_count

            bedrock_key[key_char] = key_entry

        # Build result
        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        # Build Bedrock recipe
        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"{namespace}:{recipe_name}"},
                "tags": ["crafting_table"],
                "pattern": pattern,
                "key": bedrock_key,
                "result": bedrock_result,
            },
        }

        return bedrock_recipe

    def _convert_shapeless_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a shapeless recipe to Bedrock format."""
        ingredients = normalized_recipe.get("ingredients", [])

        bedrock_ingredients = []
        for ingredient in ingredients:
            if isinstance(ingredient, dict):
                item_data = ingredient.get("item", "")
                item_count = ingredient.get("count", 1)
                item_data_val = ingredient.get("data", 0)

                bedrock_item = self._map_java_item_to_bedrock(item_data)

                ingredient_entry = {"item": bedrock_item, "data": item_data_val}
                if item_count > 1:
                    ingredient_entry["count"] = item_count

                bedrock_ingredients.append(ingredient_entry)
            elif isinstance(ingredient, str):
                bedrock_ingredients.append(
                    {"item": self._map_java_item_to_bedrock(ingredient), "data": 0}
                )

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shapeless": {
                "description": {"identifier": f"{namespace}:{recipe_name}"},
                "tags": ["crafting_table"],
                "ingredients": bedrock_ingredients,
                "result": bedrock_result,
            },
        }

        return bedrock_recipe

    def _convert_smelting_to_bedrock(
        self,
        normalized_recipe: Dict,
        namespace: str,
        recipe_name: str,
        recipe_type: str = "smelting",
    ) -> Dict:
        """Convert a furnace-type recipe to Bedrock format."""
        ingredients = normalized_recipe.get("ingredients", [])

        if not ingredients:
            return None

        ingredient = ingredients[0]

        if isinstance(ingredient, dict):
            item_data = ingredient.get("item", "")
            item_data_val = ingredient.get("data", 0)
        else:
            item_data = ingredient
            item_data_val = 0

        bedrock_ingredient = {
            "item": self._map_java_item_to_bedrock(item_data),
            "data": item_data_val,
        }

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        cooking_time = normalized_recipe.get("cooking_time", 200)
        experience = normalized_recipe.get("experience", 0.0)

        # Determine Bedrock recipe type
        bedrock_type_map = {
            "smelting": "minecraft:recipe_furnace",
            "blasting": "minecraft:recipe_furnace_blast",
            "smoking": "minecraft:recipe_furnace_smoke",
            "campfire": "minecraft:recipe_campfire",
        }

        bedrock_recipe_type = bedrock_type_map.get(recipe_type, "minecraft:recipe_furnace")

        bedrock_recipe = {
            "format_version": "1.20.10",
            bedrock_recipe_type: {
                "description": {"identifier": f"{namespace}:{recipe_name}"},
                "tags": [recipe_type],
                "ingredients": [bedrock_ingredient],
                "result": bedrock_result,
                "cookingtime": cooking_time,
                "experience": experience,
            },
        }

        return bedrock_recipe

    def _convert_stonecutter_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a stonecutter recipe to Bedrock format."""
        ingredients = normalized_recipe.get("ingredients", [])

        if not ingredients:
            return None

        ingredient = ingredients[0]

        if isinstance(ingredient, dict):
            item_data = ingredient.get("item", "")
            item_data_val = ingredient.get("data", 0)
        else:
            item_data = ingredient
            item_data_val = 0

        bedrock_ingredient = {
            "item": self._map_java_item_to_bedrock(item_data),
            "data": item_data_val,
        }

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_stonecutter": {
                "description": {"identifier": f"{namespace}:{recipe_name}"},
                "tags": ["stonecutter"],
                "ingredients": [bedrock_ingredient],
                "result": bedrock_result,
            },
        }

        return bedrock_recipe

    def _convert_smithing_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a smithing recipe to Bedrock format."""
        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_smithing_transform": {
                "description": {"identifier": f"{namespace}:{recipe_name}"},
                "tags": ["smithing_table"],
                "template": normalized_recipe.get("template", {"item": "minecraft:air"}),
                "base": normalized_recipe.get("base", {"item": "minecraft:air"}),
                "addition": normalized_recipe.get("addition", {"item": "minecraft:air"}),
                "result": bedrock_result,
            },
        }

        return bedrock_recipe

    def _convert_cooking_pot_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a Farmer's Delight cooking pot recipe to Bedrock format.

        Cooking pot recipes are converted to furnace recipes with additional
        container and cooking time info preserved in comments/tags.
        """
        ingredients = normalized_recipe.get("ingredients", [])
        if not ingredients:
            return self._create_manual_review_result(
                namespace, recipe_name, "Cooking pot recipe has no ingredients"
            )

        ingredient = ingredients[0]
        if isinstance(ingredient, dict):
            item_data = ingredient.get("item", "")
            item_data_val = ingredient.get("data", 0)
        else:
            item_data = ingredient
            item_data_val = 0

        bedrock_ingredient = {
            "item": self._map_java_item_to_bedrock(item_data),
            "data": item_data_val,
        }

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        container = normalized_recipe.get("container")
        cooking_time = normalized_recipe.get("cooking_time", 200)
        experience = normalized_recipe.get("experience", 0.0)

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_furnace": {
                "description": {"identifier": f"{namespace}:{recipe_name}"},
                "tags": ["crafting_table", "cooking_pot"],
                "ingredients": [bedrock_ingredient],
                "result": bedrock_result,
                "cookingtime": cooking_time,
                "experience": experience,
                "备注": f"Original container: {container}"
                if container
                else "Farmer's Delight cooking pot recipe",
            },
        }

        return bedrock_recipe

    def _convert_cutting_board_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a Farmer's Delight cutting board recipe to Bedrock format.

        Cutting board recipes use a tool + ingredients -> result pattern.
        We convert to a shaped recipe with the tool as part of the key.
        """
        ingredients = normalized_recipe.get("ingredients", [])
        tool = normalized_recipe.get("tool")

        if not ingredients:
            return self._create_manual_review_result(
                namespace, recipe_name, "Cutting board recipe has no ingredients"
            )

        bedrock_ingredients = []
        for ingredient in ingredients:
            if isinstance(ingredient, dict):
                item_data = ingredient.get("item", "")
                item_count = ingredient.get("count", 1)
                item_data_val = ingredient.get("data", 0)
            elif isinstance(ingredient, str):
                item_data = ingredient
                item_count = 1
                item_data_val = 0
            else:
                continue

            bedrock_item = self._map_java_item_to_bedrock(item_data)
            entry = {"item": bedrock_item, "data": item_data_val}
            if item_count > 1:
                entry["count"] = item_count
            bedrock_ingredients.append(entry)

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        tool_info = ""
        if tool:
            tool_item = tool.get("item", tool) if isinstance(tool, dict) else tool
            tool_info = f" - Requires tool: {tool_item}"

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"{namespace}:{recipe_name}"},
                "tags": ["crafting_table", "cutting_board"],
                "pattern": ["A", "B"],
                "key": {
                    "A": bedrock_ingredients[0]
                    if len(bedrock_ingredients) > 0
                    else {"item": "minecraft:air"},
                    "B": {"item": "minecraft:air"}
                    if len(bedrock_ingredients) <= 1
                    else bedrock_ingredients[1],
                },
                "result": bedrock_result,
                "备注": f"Cutting board recipe{tool_info}",
            },
        }

        return bedrock_recipe

    def _convert_mechanical_crafting_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a Create mechanical crafting recipe to Bedrock format.

        Mechanical crafting supports up to 9x9 grids. We convert to a standard
        shaped recipe (Bedrock supports 3x3 max).
        """
        pattern = normalized_recipe.get("pattern", [])
        key = normalized_recipe.get("key", {})

        if not pattern or not key:
            return self._create_manual_review_result(
                namespace, recipe_name, "Mechanical crafting recipe has no pattern or key"
            )

        # Check if pattern exceeds 3x3 (Bedrock limit)
        max_row_len = max(len(row) for row in pattern) if pattern else 0
        if max_row_len > 3 or len(pattern) > 3:
            return self._create_manual_review_result(
                namespace,
                recipe_name,
                f"Mechanical crafting uses {max_row_len}x{len(pattern)} grid, Bedrock supports max 3x3",
            )

        bedrock_key = {}
        for key_char, ingredient in key.items():
            if isinstance(ingredient, list):
                item_data = ingredient[0].get("item", "") if ingredient else "minecraft:air"
                item_count = 1
                item_data_val = 0
            elif isinstance(ingredient, str):
                item_data = ingredient
                item_count = 1
                item_data_val = 0
            elif isinstance(ingredient, dict):
                item_data = ingredient.get("item", "")
                item_count = ingredient.get("count", 1)
                item_data_val = ingredient.get("data", 0)
            else:
                continue

            bedrock_item = self._map_java_item_to_bedrock(item_data)
            entry = {"item": bedrock_item, "data": item_data_val}
            if item_count > 1:
                entry["count"] = item_count
            bedrock_key[key_char] = entry

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"{namespace}:{recipe_name}"},
                "tags": ["crafting_table", "mechanical_crafting"],
                "pattern": pattern,
                "key": bedrock_key,
                "result": bedrock_result,
            },
        }

        return bedrock_recipe

    def _convert_pressing_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a Create pressing recipe to Bedrock format.

        Pressing recipes are converted to a shaped recipe with the ingredient
        as the main input.
        """
        ingredients = normalized_recipe.get("ingredients", [])
        if not ingredients:
            return self._create_manual_review_result(
                namespace, recipe_name, "Pressing recipe has no ingredients"
            )

        ingredient = ingredients[0]
        if isinstance(ingredient, dict):
            item_data = ingredient.get("item", "")
            item_data_val = ingredient.get("data", 0)
        else:
            item_data = ingredient
            item_data_val = 0

        bedrock_ingredient = {
            "item": self._map_java_item_to_bedrock(item_data),
            "data": item_data_val,
        }

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"{namespace}:{recipe_name}"},
                "tags": ["crafting_table", "pressing"],
                "pattern": ["A"],
                "key": {"A": bedrock_ingredient},
                "result": bedrock_result,
                "备注": "Create pressing recipe",
            },
        }

        return bedrock_recipe

    def _convert_milling_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a Create milling recipe to Bedrock format.

        Milling recipes use Millstone to crush ores into materials.
        Converted to a shaped recipe approximating the crushing operation.
        """
        ingredients = normalized_recipe.get("ingredients", [])
        if not ingredients:
            return self._create_manual_review_result(
                namespace, recipe_name, "Milling recipe has no ingredients"
            )

        ingredient = ingredients[0]
        if isinstance(ingredient, dict):
            item_data = ingredient.get("item", "")
            item_data_val = ingredient.get("data", 0)
        else:
            item_data = ingredient
            item_data_val = 0

        bedrock_ingredient = {
            "item": self._map_java_item_to_bedrock(item_data),
            "data": item_data_val,
        }

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"{namespace}:{recipe_name}_converted_from_create"},
                "tags": ["crafting_table", "milling"],
                "pattern": ["A"],
                "key": {"A": bedrock_ingredient},
                "result": bedrock_result,
                "备注": "Create milling recipe (Millstone) - approximated",
            },
        }

        return bedrock_recipe

    def _convert_crushing_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a Create crushing recipe to Bedrock format.

        Crushing recipes use Crushing Wheels for ore doubling.
        Converted to a shaped recipe approximating the crushing operation.
        """
        ingredients = normalized_recipe.get("ingredients", [])
        if not ingredients:
            return self._create_manual_review_result(
                namespace, recipe_name, "Crushing recipe has no ingredients"
            )

        ingredient = ingredients[0]
        if isinstance(ingredient, dict):
            item_data = ingredient.get("item", "")
            item_data_val = ingredient.get("data", 0)
        else:
            item_data = ingredient
            item_data_val = 0

        bedrock_ingredient = {
            "item": self._map_java_item_to_bedrock(item_data),
            "data": item_data_val,
        }

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"{namespace}:{recipe_name}_converted_from_create"},
                "tags": ["crafting_table", "crushing"],
                "pattern": ["A"],
                "key": {"A": bedrock_ingredient},
                "result": bedrock_result,
                "备注": "Create crushing recipe (Crushing Wheels) - approximated",
            },
        }

        return bedrock_recipe

    def _convert_deploying_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a Create deploying recipe to Bedrock format.

        Deploying recipes combine an item with a catalyst (block) to produce output.
        Converted to a shaped recipe using ingredient + catalyst pattern.
        """
        ingredients = normalized_recipe.get("ingredients", [])
        tool = normalized_recipe.get("tool")

        if not ingredients:
            return self._create_manual_review_result(
                namespace, recipe_name, "Deploying recipe has no ingredients"
            )

        bedrock_ingredients = []
        for i, ingredient in enumerate(ingredients):
            if isinstance(ingredient, dict):
                item_data = ingredient.get("item", "")
                item_count = ingredient.get("count", 1)
                item_data_val = ingredient.get("data", 0)
            elif isinstance(ingredient, str):
                item_data = ingredient
                item_count = 1
                item_data_val = 0
            else:
                continue

            bedrock_item = self._map_java_item_to_bedrock(item_data)
            entry = {"item": bedrock_item, "data": item_data_val}
            if item_count > 1:
                entry["count"] = item_count
            bedrock_ingredients.append(entry)

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        catalyst_info = ""
        if tool:
            tool_item = tool.get("item", tool) if isinstance(tool, dict) else tool
            bedrock_tool = self._map_java_item_to_bedrock(tool_item)
            catalyst_info = f" - Catalyst: {bedrock_tool}"

        pattern = ["AB"] if len(bedrock_ingredients) >= 2 else ["A"]
        key = {
            "A": bedrock_ingredients[0]
            if len(bedrock_ingredients) > 0
            else {"item": "minecraft:air"},
            "B": bedrock_ingredients[1]
            if len(bedrock_ingredients) > 1
            else {"item": "minecraft:air"},
        }

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"{namespace}:{recipe_name}_converted_from_create"},
                "tags": ["crafting_table", "deploying"],
                "pattern": pattern,
                "key": key,
                "result": bedrock_result,
                "备注": f"Create deploying recipe{catalyst_info} - approximated",
            },
        }

        return bedrock_recipe

    def _convert_splashing_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a Create splashing recipe to Bedrock format.

        Splashing recipes use water to wash items (ore washing, etc.).
        Converted to a shapeless recipe with water bucket as an implicit ingredient.
        """
        ingredients = normalized_recipe.get("ingredients", [])

        if not ingredients:
            return self._create_manual_review_result(
                namespace, recipe_name, "Splashing recipe has no ingredients"
            )

        bedrock_ingredients = []
        for ingredient in ingredients:
            if isinstance(ingredient, dict):
                item_data = ingredient.get("item", "")
                item_count = ingredient.get("count", 1)
                item_data_val = ingredient.get("data", 0)
            elif isinstance(ingredient, str):
                item_data = ingredient
                item_count = 1
                item_data_val = 0
            else:
                continue

            bedrock_item = self._map_java_item_to_bedrock(item_data)
            entry = {"item": bedrock_item, "data": item_data_val}
            if item_count > 1:
                entry["count"] = item_count
            bedrock_ingredients.append(entry)

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shapeless": {
                "description": {"identifier": f"{namespace}:{recipe_name}_converted_from_create"},
                "tags": ["crafting_table", "splashing"],
                "ingredients": bedrock_ingredients,
                "result": bedrock_result,
                "备注": "Create splashing recipe (Water) - approximated",
            },
        }

        return bedrock_recipe

    def _convert_compacting_to_bedrock(
        self, normalized_recipe: Dict, namespace: str, recipe_name: str
    ) -> Dict:
        """Convert a Create compacting recipe to Bedrock format.

        Compacting recipes compress items into blocks.
        Converted to a shaped recipe.
        """
        ingredients = normalized_recipe.get("ingredients", [])

        if not ingredients:
            return self._create_manual_review_result(
                namespace, recipe_name, "Compacting recipe has no ingredients"
            )

        bedrock_ingredients = []
        for ingredient in ingredients:
            if isinstance(ingredient, dict):
                item_data = ingredient.get("item", "")
                item_count = ingredient.get("count", 1)
                item_data_val = ingredient.get("data", 0)
            elif isinstance(ingredient, str):
                item_data = ingredient
                item_count = 1
                item_data_val = 0
            else:
                continue

            bedrock_item = self._map_java_item_to_bedrock(item_data)
            entry = {"item": bedrock_item, "data": item_data_val}
            if item_count > 1:
                entry["count"] = item_count
            bedrock_ingredients.append(entry)

        bedrock_result = {
            "item": self._map_java_item_to_bedrock(normalized_recipe.get("result_item", "")),
            "data": normalized_recipe.get("result_data", 0),
            "count": normalized_recipe.get("result_count", 1),
        }

        pattern = ["A"] * min(len(bedrock_ingredients), 3)
        key = {}
        for i, char in enumerate(["A", "B", "C"][: len(bedrock_ingredients)]):
            key[char] = bedrock_ingredients[i]

        bedrock_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"{namespace}:{recipe_name}_converted_from_create"},
                "tags": ["crafting_table", "compacting"],
                "pattern": pattern,
                "key": key,
                "result": bedrock_result,
                "备注": "Create compacting recipe - approximated",
            },
        }

        return bedrock_recipe

    def _create_manual_review_result(self, namespace: str, recipe_name: str, reason: str) -> Dict:
        """Create a result indicating the recipe requires manual review."""
        return {
            "format_version": "1.20.10",
            "manual_review_required": True,
            "reason": reason,
            "original_recipe": f"{namespace}:{recipe_name}",
            "description": {"identifier": f"{namespace}:{recipe_name}"},
        }

    def convert_recipe(
        self, recipe_data: Dict, namespace: str = "mod", recipe_name: str = None
    ) -> Dict:
        """Convert a Java recipe to Bedrock format."""
        normalized = self._parse_java_recipe(recipe_data)

        if not recipe_name:
            result_item = normalized.get("result_item", "unknown")
            if ":" in result_item:
                _, item_name = result_item.split(":", 1)
                recipe_name = item_name
            else:
                recipe_name = result_item

        category = normalized.get("recipe_category", "unknown")

        if category == "shaped":
            return self._convert_shaped_to_bedrock(normalized, namespace, recipe_name)
        elif category == "shapeless":
            return self._convert_shapeless_to_bedrock(normalized, namespace, recipe_name)
        elif category == "smelting":
            return self._convert_smelting_to_bedrock(normalized, namespace, recipe_name, "smelting")
        elif category == "blasting":
            return self._convert_smelting_to_bedrock(normalized, namespace, recipe_name, "blasting")
        elif category == "smoking":
            return self._convert_smelting_to_bedrock(normalized, namespace, recipe_name, "smoking")
        elif category == "campfire":
            return self._convert_smelting_to_bedrock(normalized, namespace, recipe_name, "campfire")
        elif category == "stonecutter":
            return self._convert_stonecutter_to_bedrock(normalized, namespace, recipe_name)
        elif category == "smithing":
            return self._convert_smithing_to_bedrock(normalized, namespace, recipe_name)
        elif category == "cooking_pot":
            return self._convert_cooking_pot_to_bedrock(normalized, namespace, recipe_name)
        elif category == "cutting_board":
            return self._convert_cutting_board_to_bedrock(normalized, namespace, recipe_name)
        elif category == "mechanical_crafting":
            return self._convert_mechanical_crafting_to_bedrock(normalized, namespace, recipe_name)
        elif category == "pressing":
            return self._convert_pressing_to_bedrock(normalized, namespace, recipe_name)
        elif category == "milling":
            return self._convert_milling_to_bedrock(normalized, namespace, recipe_name)
        elif category == "crushing":
            return self._convert_crushing_to_bedrock(normalized, namespace, recipe_name)
        elif category == "deploying":
            return self._convert_deploying_to_bedrock(normalized, namespace, recipe_name)
        elif category == "splashing":
            return self._convert_splashing_to_bedrock(normalized, namespace, recipe_name)
        elif category == "compacting":
            return self._convert_compacting_to_bedrock(normalized, namespace, recipe_name)
        elif category in ("sequenced_assembly", "mixing", "fluid_interaction"):
            reason = normalized.get(
                "manual_review_reason", "Custom recipe type requires manual review"
            )
            return self._create_manual_review_result(namespace, recipe_name, reason)
        elif category == "custom":
            reason = normalized.get("manual_review_reason", "Unknown custom Forge recipe type")
            return self._create_manual_review_result(namespace, recipe_name, reason)
        else:
            logger.warning(f"Cannot convert unknown recipe category: {category}")
            return {"success": False, "error": f"Unknown recipe category: {category}"}

    def add_custom_item_mapping(self, java_item_id: str, bedrock_item_id: str):
        """Add a custom Java to Bedrock item mapping."""
        self.custom_mappings[java_item_id] = bedrock_item_id

    @tool
    @staticmethod
    def convert_recipe_tool(recipe_json: str) -> str:
        """Convert a Java recipe to Bedrock format."""
        try:
            input_data = json.loads(recipe_json)
            agent = RecipeConverterAgent.get_instance()

            # Handle case where data is wrapped in "recipe_data"
            if "recipe_data" in input_data and isinstance(input_data["recipe_data"], dict):
                recipe_data = input_data["recipe_data"]
                # Prefer namespace/recipe_name from top level, fall back to nested
                namespace = input_data.get("namespace") or recipe_data.pop("namespace", "mod")
                recipe_name = input_data.get("recipe_name") or recipe_data.pop("recipe_name", None)
            else:
                recipe_data = input_data
                namespace = recipe_data.pop("namespace", "mod")
                recipe_name = recipe_data.pop("recipe_name", None)

            result = agent.convert_recipe(recipe_data, namespace, recipe_name)

            return json.dumps({"success": True, "converted_recipe": result}, indent=2)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, indent=2)

    @tool
    @staticmethod
    def convert_recipes_batch_tool(recipes_json: str) -> str:
        """Convert multiple Java recipes to Bedrock format in batch."""
        try:
            recipes = json.loads(recipes_json)
            agent = RecipeConverterAgent.get_instance()

            results = []
            for item in recipes:
                # Handle case where item is wrapped in "recipe_data"
                if "recipe_data" in item and isinstance(item["recipe_data"], dict):
                    recipe_data = item["recipe_data"]
                    namespace = item.get("namespace") or recipe_data.pop("namespace", "mod")
                    recipe_name = item.get("recipe_name") or recipe_data.pop("recipe_name", None)
                else:
                    recipe_data = item
                    namespace = recipe_data.pop("namespace", "mod")
                    recipe_name = recipe_data.pop("recipe_name", None)

                converted = agent.convert_recipe(recipe_data, namespace, recipe_name)
                results.append(converted)

            return json.dumps(
                {"success": True, "converted_recipes": results, "total_count": len(results)},
                indent=2,
            )

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, indent=2)

    @tool
    @staticmethod
    def map_item_id_tool(item_mapping_json: str) -> str:
        """Add custom Java to Bedrock item ID mappings."""
        try:
            mappings = json.loads(item_mapping_json)
            agent = RecipeConverterAgent.get_instance()

            if isinstance(mappings, list):
                for mapping in mappings:
                    if isinstance(mapping, dict) and "java" in mapping and "bedrock" in mapping:
                        agent.add_custom_item_mapping(mapping["java"], mapping["bedrock"])
            elif isinstance(mappings, dict):
                for java_id, bedrock_id in mappings.items():
                    agent.add_custom_item_mapping(java_id, bedrock_id)

            return json.dumps({"success": True, "message": "Custom item mappings added"}, indent=2)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)}, indent=2)

    @tool
    @staticmethod
    def validate_recipe_tool(recipe_json: str) -> str:
        """Validate a Bedrock recipe for correctness."""
        try:
            recipe = json.loads(recipe_json)
            issues = []

            if "format_version" not in recipe:
                issues.append("Missing format_version")

            recipe_types = [
                "minecraft:recipe_shaped",
                "minecraft:recipe_shapeless",
                "minecraft:recipe_furnace",
                "minecraft:recipe_furnace_blast",
                "minecraft:recipe_furnace_smoke",
                "minecraft:recipe_campfire",
                "minecraft:recipe_stonecutter",
                "minecraft:recipe_smithing_transform",
            ]

            found_type = None
            for rt in recipe_types:
                if rt in recipe:
                    found_type = rt
                    break

            if not found_type:
                issues.append(f"Unknown recipe type")
                return json.dumps({"valid": False, "issues": issues}, indent=2)

            recipe_content = recipe.get(found_type, {})

            if "description" not in recipe_content:
                issues.append("Missing description")
            elif "identifier" not in recipe_content.get("description", {}):
                issues.append("Missing description.identifier")

            if found_type == "minecraft:recipe_shaped":
                if "pattern" not in recipe_content:
                    issues.append("Missing pattern")
                if "key" not in recipe_content:
                    issues.append("Missing key")
                if "result" not in recipe_content:
                    issues.append("Missing result")
            elif found_type == "minecraft:recipe_shapeless":
                if "ingredients" not in recipe_content:
                    issues.append("Missing ingredients")
                if "result" not in recipe_content:
                    issues.append("Missing result")
            elif "recipe_furnace" in found_type or found_type == "minecraft:recipe_campfire":
                if "ingredients" not in recipe_content:
                    issues.append("Missing ingredients")
                if "result" not in recipe_content:
                    issues.append("Missing result")
            elif found_type == "minecraft:recipe_stonecutter":
                if "ingredients" not in recipe_content:
                    issues.append("Missing ingredients")
                if "result" not in recipe_content:
                    issues.append("Missing result")

            is_valid = len(issues) == 0

            return json.dumps(
                {"valid": is_valid, "recipe_type": found_type, "issues": issues}, indent=2
            )

        except Exception as e:
            return json.dumps({"valid": False, "issues": [str(e)]}, indent=2)
