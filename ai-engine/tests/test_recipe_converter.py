"""
Tests for RecipeConverterAgent.
"""

import pytest
import json
from agents.recipe_converter import RecipeConverterAgent


class TestRecipeConverterAgent:
    """Test the RecipeConverterAgent functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.agent = RecipeConverterAgent.get_instance()
    
    def test_agent_singleton(self):
        """Test that agent returns singleton instance."""
        agent2 = RecipeConverterAgent.get_instance()
        assert self.agent is agent2
    
    def test_convert_shaped_recipe(self):
        """Test conversion of a shaped crafting recipe."""
        java_recipe = {
            "type": "minecraft:crafting_shaped",
            "pattern": [
                "XXX",
                " X ",
                " X "
            ],
            "key": {
                "X": {
                    "item": "minecraft:diamond",
                    "count": 3
                }
            },
            "result": {
                "item": "minecraft:diamond_pickaxe",
                "count": 1
            }
        }
        
        result = self.agent.convert_recipe(java_recipe, "test_mod", "diamond_pickaxe")
        
        assert "minecraft:recipe_shaped" in result
        recipe = result["minecraft:recipe_shaped"]
        assert recipe["description"]["identifier"] == "test_mod:diamond_pickaxe"
        assert recipe["pattern"] == ["XXX", " X ", " X "]
        assert "X" in recipe["key"]
    
    def test_convert_shapeless_recipe(self):
        """Test conversion of a shapeless crafting recipe."""
        java_recipe = {
            "type": "minecraft:crafting_shapeless",
            "ingredients": [
                {"item": "minecraft:apple", "count": 1}
            ],
            "result": {
                "item": "minecraft:golden_apple",
                "count": 1
            }
        }
        
        result = self.agent.convert_recipe(java_recipe, "test_mod", "golden_apple")
        
        assert "minecraft:recipe_shapeless" in result
        recipe = result["minecraft:recipe_shapeless"]
        assert recipe["description"]["identifier"] == "test_mod:golden_apple"
        assert len(recipe["ingredients"]) == 1
    
    def test_convert_smelting_recipe(self):
        """Test conversion of a furnace/smelting recipe."""
        java_recipe = {
            "type": "minecraft:smelting",
            "ingredient": {"item": "minecraft:iron_ore"},
            "result": "minecraft:iron_ingot",
            "cookingtime": 200,
            "experience": 0.7
        }
        
        result = self.agent.convert_recipe(java_recipe, "test_mod", "iron_ingot")
        
        assert "minecraft:recipe_furnace" in result
        recipe = result["minecraft:recipe_furnace"]
        assert recipe["description"]["identifier"] == "test_mod:iron_ingot"
        assert recipe["cookingtime"] == 200
        assert recipe["experience"] == 0.7
    
    def test_convert_blasting_recipe(self):
        """Test conversion of a blasting recipe."""
        java_recipe = {
            "type": "minecraft:blasting",
            "ingredient": {"item": "minecraft:iron_ore"},
            "result": "minecraft:iron_ingot",
            "cookingtime": 100,
            "experience": 0.7
        }
        
        result = self.agent.convert_recipe(java_recipe, "test_mod", "iron_ingot_blast")
        
        assert "minecraft:recipe_furnace_blast" in result
        recipe = result["minecraft:recipe_furnace_blast"]
        assert recipe["cookingtime"] == 100
    
    def test_convert_smoking_recipe(self):
        """Test conversion of a smoking recipe."""
        java_recipe = {
            "type": "minecraft:smoking",
            "ingredient": {"item": "minecraft:chicken"},
            "result": "minecraft:cooked_chicken",
            "cookingtime": 100,
            "experience": 0.35
        }
        
        result = self.agent.convert_recipe(java_recipe, "test_mod", "cooked_chicken")
        
        assert "minecraft:recipe_furnace_smoke" in result
        recipe = result["minecraft:recipe_furnace_smoke"]
        assert recipe["cookingtime"] == 100
    
    def test_convert_campfire_recipe(self):
        """Test conversion of a campfire recipe."""
        java_recipe = {
            "type": "minecraft:campfire_cooking",
            "ingredient": {"item": "minecraft:porkchop"},
            "result": "minecraft:cooked_porkchop",
            "cookingtime": 600,
            "experience": 0.35
        }
        
        result = self.agent.convert_recipe(java_recipe, "test_mod", "cooked_porkchop")
        
        assert "minecraft:recipe_campfire" in result
        recipe = result["minecraft:recipe_campfire"]
        assert recipe["cookingtime"] == 600
    
    def test_convert_stonecutter_recipe(self):
        """Test conversion of a stonecutter recipe."""
        java_recipe = {
            "type": "minecraft:stonecutting",
            "ingredient": {"item": "minecraft:stone"},
            "result": "minecraft:stone_slab"
        }
        
        result = self.agent.convert_recipe(java_recipe, "test_mod", "stone_slab")
        
        assert "minecraft:recipe_stonecutter" in result
        recipe = result["minecraft:recipe_stonecutter"]
        assert recipe["description"]["identifier"] == "test_mod:stone_slab"
    
    def test_item_mapping(self):
        """Test Java to Bedrock item ID mapping."""
        # Test known mapping
        result = self.agent._map_java_item_to_bedrock("minecraft:iron_ingot")
        assert result == "minecraft:iron_ingot"
        
        # Test unknown item returns original
        result = self.agent._map_java_item_to_bedrock("mod:unknown_item")
        assert result == "mod:unknown_item"
    
    def test_custom_item_mapping(self):
        """Test adding custom item mappings."""
        self.agent.add_custom_item_mapping("mod:custom_item", "mod:custom_bedrock_item")
        
        result = self.agent._map_java_item_to_bedrock("mod:custom_item")
        assert result == "mod:custom_bedrock_item"
    
    def test_validate_recipe_shaped(self):
        """Test validation of shaped recipe."""
        valid_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": "test:recipe"},
                "tags": ["crafting_table"],
                "pattern": ["X", "X"],
                "key": {"X": {"item": "minecraft:stone"}},
                "result": {"item": "minecraft:stone", "count": 1}
            }
        }
        
        result = self.agent.validate_recipe_tool(json.dumps(valid_recipe))
        result_data = json.loads(result)
        assert result_data["valid"] is True
        assert len(result_data["issues"]) == 0
    
    def test_validate_recipe_invalid(self):
        """Test validation catches missing fields."""
        invalid_recipe = {
            "format_version": "1.20.10",
            "minecraft:recipe_shaped": {
                "description": {"identifier": "test:recipe"}
                # Missing pattern, key, result
            }
        }
        
        result = self.agent.validate_recipe_tool(json.dumps(invalid_recipe))
        result_data = json.loads(result)
        assert result_data["valid"] is False
        assert len(result_data["issues"]) > 0
    
    def test_convert_recipes_batch(self):
        """Test batch conversion of recipes."""
        recipes = [
            {
                "type": "minecraft:crafting_shaped",
                "pattern": ["X"],
                "key": {"X": {"item": "minecraft:stone"}},
                "result": {"item": "minecraft:stone"}
            },
            {
                "type": "minecraft:smelting",
                "ingredient": {"item": "minecraft:iron_ore"},
                "result": "minecraft:iron_ingot"
            }
        ]
        
        results = []
        for recipe_data in recipes:
            converted = self.agent.convert_recipe(recipe_data, "test_mod")
            results.append(converted)
        
        assert len(results) == 2
        assert "minecraft:recipe_shaped" in results[0]
        assert "minecraft:recipe_furnace" in results[1]


class TestRecipeConverterTools:
    """Test the CrewAI tools provided by RecipeConverterAgent."""
    
    def test_convert_recipe_tool(self):
        """Test convert_recipe_tool static method."""
        java_recipe = json.dumps({
            "type": "minecraft:crafting_shaped",
            "pattern": ["X"],
            "key": {"X": {"item": "minecraft:stone"}},
            "result": {"item": "minecraft:stone"},
            "namespace": "test_mod",
            "recipe_name": "stone"
        })
        
        result = RecipeConverterAgent.convert_recipe_tool(java_recipe)
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert "minecraft:recipe_shaped" in result_data["converted_recipe"]
    
    def test_convert_recipes_batch_tool(self):
        """Test convert_recipes_batch_tool static method."""
        recipes = json.dumps([
            {
                "type": "minecraft:crafting_shaped",
                "pattern": ["X"],
                "key": {"X": {"item": "minecraft:stone"}},
                "result": {"item": "minecraft:stone"},
                "namespace": "test_mod"
            }
        ])
        
        result = RecipeConverterAgent.convert_recipes_batch_tool(recipes)
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["total_count"] == 1
    
    def test_map_item_id_tool(self):
        """Test map_item_id_tool static method."""
        mappings = json.dumps({
            "mod:custom_item": "mod:custom_bedrock"
        })
        
        result = RecipeConverterAgent.map_item_id_tool(mappings)
        result_data = json.loads(result)
        
        assert result_data["success"] is True


if __name__ == "__main__":
    pytest.main([__file__])
