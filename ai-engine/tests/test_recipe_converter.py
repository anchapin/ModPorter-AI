
import pytest
import json
import sys
import unittest.mock as mock

class TestRecipeConverterAgent:
    """Test the RecipeConverterAgent functionality."""

    @pytest.fixture(autouse=True)
    def setup_agent(self):
        """Set up test environment with mocked crewai."""
        # Create a compatible mock for tool decorator
        def tool_decorator(func):
            # Return something that looks like a Tool object but is also callable
            class MockTool:
                def __init__(self, fn):
                    self.fn = fn
                    self.func = fn # For compatibility with some tests
                    self.name = fn.__name__
                def __call__(self, *args, **kwargs):
                    return self.fn(*args, **kwargs)
            return MockTool(func)

        mock_crewai = mock.MagicMock()
        mock_crewai.Agent = mock.MagicMock()
        mock_crewai.Crew = mock.MagicMock()
        mock_crewai.Task = mock.MagicMock()
        mock_crewai.LLM = mock.MagicMock()
        
        mock_tools = mock.MagicMock()
        mock_tools.tool = tool_decorator
        mock_tools.BaseTool = mock.MagicMock()

        with mock.patch.dict(sys.modules, {"crewai": mock_crewai, "crewai.tools": mock_tools}):
            import agents.recipe_converter
            import importlib
            importlib.reload(agents.recipe_converter)
            from agents.recipe_converter import RecipeConverterAgent

            # Clear singleton instance to ensure it uses our mock
            if hasattr(RecipeConverterAgent, "_instance"):
                RecipeConverterAgent._instance = None
            
            self.agent = RecipeConverterAgent.get_instance()
            yield
            # Clear again after test
            RecipeConverterAgent._instance = None

    def test_agent_singleton(self):
        """Test that agent returns singleton instance."""
        # Already handled by fixture, but let's check
        from agents.recipe_converter import RecipeConverterAgent
        agent2 = RecipeConverterAgent.get_instance()
        assert self.agent is agent2

    def test_convert_shaped_recipe(self):
        """Test conversion of a shaped crafting recipe."""
        java_recipe = {
            "type": "minecraft:crafting_shaped",
            "pattern": ["XXX", " X ", " X "],
            "key": {"X": {"item": "minecraft:diamond", "count": 3}},
            "result": {"item": "minecraft:diamond_pickaxe", "count": 1},
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
            "ingredients": [{"item": "minecraft:apple", "count": 1}],
            "result": {"item": "minecraft:golden_apple", "count": 1},
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
            "ingredient": {"item": "minecraft:chicken"},
            "result": "minecraft:cooked_chicken",
            "experience": 0.35,
            "cookingtime": 200,
        }

        result = self.agent.convert_recipe(java_recipe, "test_mod", "cooked_chicken")

        assert "minecraft:recipe_furnace" in result
        recipe = result["minecraft:recipe_furnace"]
        assert recipe["description"]["identifier"] == "test_mod:cooked_chicken"
        assert recipe["ingredients"][0]["item"] == "minecraft:chicken"
        assert recipe["result"]["item"] == "minecraft:cooked_chicken"

    def test_convert_blasting_recipe(self):
        """Test conversion of a blasting recipe."""
        java_recipe = {
            "type": "minecraft:blasting",
            "ingredient": {"item": "minecraft:iron_ore"},
            "result": "minecraft:iron_ingot",
            "experience": 0.7,
            "cookingtime": 100,
        }

        result = self.agent.convert_recipe(java_recipe, "test_mod", "iron_ingot")

        assert "minecraft:recipe_furnace_blast" in result
        recipe = result["minecraft:recipe_furnace_blast"]
        assert recipe["ingredients"][0]["item"] == "minecraft:iron_ore"

    def test_convert_smoking_recipe(self):
        """Test conversion of a smoking recipe."""
        java_recipe = {
            "type": "minecraft:smoking",
            "ingredient": {"item": "minecraft:beef"},
            "result": "minecraft:cooked_beef",
            "experience": 0.35,
            "cookingtime": 100,
        }

        result = self.agent.convert_recipe(java_recipe, "test_mod", "cooked_beef")

        assert "minecraft:recipe_furnace_smoke" in result

    def test_convert_campfire_recipe(self):
        """Test conversion of a campfire cooking recipe."""
        java_recipe = {
            "type": "minecraft:campfire_cooking",
            "ingredient": {"item": "minecraft:cod"},
            "result": "minecraft:cooked_cod",
            "experience": 0.35,
            "cookingtime": 600,
        }

        result = self.agent.convert_recipe(java_recipe, "test_mod", "cooked_cod")

        assert "minecraft:recipe_campfire" in result


    def test_convert_stonecutter_recipe(self):
        """Test conversion of a stonecutter recipe."""
        java_recipe = {
            "type": "minecraft:stonecutting",
            "ingredient": "minecraft:stone",
            "result": "minecraft:stone_slab",
            "count": 2,
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
                "result": {"item": "minecraft:stone", "count": 1},
            },
        }

        # Handle both direct call and crewai Tool object
        tool_func = self.agent.validate_recipe_tool
        if hasattr(tool_func, "fn"):
            result = tool_func.func(json.dumps(valid_recipe))
        else:
            result = tool_func(json.dumps(valid_recipe))

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
            },
        }

        # Handle both direct call and crewai Tool object
        tool_func = self.agent.validate_recipe_tool
        if hasattr(tool_func, "fn"):
            result = tool_func.func(json.dumps(invalid_recipe))
        else:
            result = tool_func(json.dumps(invalid_recipe))

        result_data = json.loads(result)
        assert result_data["valid"] is False
        assert len(result_data["issues"]) > 0

    def test_convert_recipes_batch(self):
        """Test batch conversion of recipes."""
        recipes = json.dumps(
            [
                {
                    "recipe_data": {
                        "type": "minecraft:crafting_shaped",
                        "pattern": ["X"],
                        "key": {"X": {"item": "minecraft:stone"}},
                        "result": {"item": "minecraft:stone"},
                    },
                    "namespace": "test_mod",
                }
            ]
        )

        # Handle both direct call and crewai Tool object
        tool_func = self.agent.convert_recipes_batch_tool
        if hasattr(tool_func, "fn"):
            result = tool_func.func(recipes)
        else:
            result = tool_func(recipes)

        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["total_count"] == 1

    def test_convert_smithing_recipe(self):
        """Test conversion of a smithing recipe."""
        java_recipe = {
            "type": "minecraft:smithing_transform",
            "base": {"item": "minecraft:netherite_ingot"},
            "addition": {"item": "minecraft:diamond_pickaxe"},
            "template": {"item": "minecraft:netherite_upgrade_smithing_template"},
            "result": {"item": "minecraft:netherite_pickaxe"}
        }

        result = self.agent.convert_recipe(java_recipe, "test_mod", "netherite_pickaxe")

        assert "minecraft:recipe_smithing_transform" in result
        recipe = result["minecraft:recipe_smithing_transform"]
        assert recipe["base"]["item"] == "minecraft:netherite_ingot"
        assert recipe["addition"]["item"] == "minecraft:diamond_pickaxe"

    def test_convert_recipe_no_name(self):
        """Test recipe name extraction when not provided."""
        java_recipe = {
            "type": "minecraft:crafting_shaped",
            "pattern": ["X"],
            "key": {"X": {"item": "minecraft:stone"}},
            "result": {"item": "minecraft:test_item"},
        }
        result = self.agent.convert_recipe(java_recipe, "test_mod")
        assert result["minecraft:recipe_shaped"]["description"]["identifier"] == "test_mod:test_item"

    def test_map_item_id_tool_list(self):
        """Test map_item_id_tool with a list of mappings."""
        from agents.recipe_converter import RecipeConverterAgent
        mappings = json.dumps([
            {"java": "mod:item1", "bedrock": "mod:bedrock1"},
            {"java": "mod:item2", "bedrock": "mod:bedrock2"}
        ])

        tool_func = RecipeConverterAgent.map_item_id_tool
        if hasattr(tool_func, "fn"):
            result = tool_func.func(mappings)
        else:
            result = tool_func(mappings)

        result_data = json.loads(result)
        assert result_data["success"] is True
        assert self.agent._map_java_item_to_bedrock("mod:item1") == "mod:bedrock1"

    def test_validate_recipe_all_types(self):
        """Test validation for various recipe types."""
        types = [
            "minecraft:recipe_shapeless",
            "minecraft:recipe_furnace",
            "minecraft:recipe_furnace_blast",
            "minecraft:recipe_furnace_smoke",
            "minecraft:recipe_campfire",
            "minecraft:recipe_stonecutter",
        ]
        
        for rt in types:
            recipe = {
                "format_version": "1.20.10",
                rt: {
                    "description": {"identifier": "test:recipe"},
                    "ingredients": [{"item": "minecraft:stone"}],
                    "result": {"item": "minecraft:stone"}
                }
            }
            result = self.agent.validate_recipe_tool.func(json.dumps(recipe)) if hasattr(self.agent.validate_recipe_tool, "func") else self.agent.validate_recipe_tool(json.dumps(recipe))
            assert json.loads(result)["valid"] is True

    def test_convert_recipe_tool_nested_data(self):
        """Test convert_recipe_tool with nested recipe_data."""
        from agents.recipe_converter import RecipeConverterAgent
        input_data = json.dumps({
            "recipe_data": {
                "type": "minecraft:crafting_shaped",
                "pattern": ["X"],
                "key": {"X": {"item": "minecraft:stone"}},
                "result": {"item": "minecraft:stone"},
                "namespace": "nested_ns",
                "recipe_name": "nested_name"
            }
        })
        
        result = RecipeConverterAgent.convert_recipe_tool.func(input_data) if hasattr(RecipeConverterAgent.convert_recipe_tool, "func") else RecipeConverterAgent.convert_recipe_tool(input_data)
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "nested_ns:nested_name" in str(result_data["converted_recipe"])

    def test_get_tools(self):
        """Test get_tools returns all tools."""
        tools = self.agent.get_tools()
        assert len(tools) == 4
        assert any(t.name == "convert_recipe_tool" for t in tools)

    def test_convert_unknown_recipe_type(self):
        """Test handling of unknown recipe type."""
        java_recipe = {"type": "minecraft:unknown_type"}
        result = self.agent.convert_recipe(java_recipe, "test_mod", "test")
        assert result["success"] is False
        assert "Unknown recipe category" in result["error"]

    def test_convert_recipe_tool_error(self):
        """Test convert_recipe_tool error handling."""
        from agents.recipe_converter import RecipeConverterAgent
        # Invalid JSON should cause error
        result = RecipeConverterAgent.convert_recipe_tool("invalid json")
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data

    def test_convert_recipes_batch_tool_error(self):
        """Test convert_recipes_batch_tool error handling."""
        from agents.recipe_converter import RecipeConverterAgent
        # Invalid JSON should cause error
        result = RecipeConverterAgent.convert_recipes_batch_tool("invalid json")
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data

    def test_map_item_id_tool_error(self):
        """Test map_item_id_tool error handling."""
        from agents.recipe_converter import RecipeConverterAgent
        # Invalid JSON should cause error
        result = RecipeConverterAgent.map_item_id_tool("invalid json")
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data

    def test_validate_recipe_tool_error(self):
        """Test validate_recipe_tool error handling."""
        from agents.recipe_converter import RecipeConverterAgent
        # Invalid JSON should cause error
        result = RecipeConverterAgent.validate_recipe_tool("invalid json")
        result_data = json.loads(result)
        assert result_data["valid"] is False
        assert len(result_data["issues"]) > 0

    def test_convert_shapeless_string_ingredients(self):
        """Test shapeless conversion with string ingredients."""
        java_recipe = {
            "type": "minecraft:crafting_shapeless",
            "ingredients": ["minecraft:apple"],
            "result": {"item": "minecraft:golden_apple"}
        }
        result = self.agent.convert_recipe(java_recipe, "test_mod", "apple")
        assert result["minecraft:recipe_shapeless"]["ingredients"][0]["item"] == "minecraft:apple"

    def test_convert_smelting_string_ingredient(self):
        """Test smelting conversion with string ingredient."""
        java_recipe = {
            "type": "minecraft:smelting",
            "ingredient": "minecraft:iron_ore",
            "result": "minecraft:iron_ingot"
        }
        result = self.agent.convert_recipe(java_recipe, "test_mod", "iron")
        assert result["minecraft:recipe_furnace"]["ingredients"][0]["item"] == "minecraft:iron_ore"

class TestRecipeConverterTools:
    """Test the CrewAI tools provided by RecipeConverterAgent."""

    @pytest.fixture(autouse=True)
    def setup_tools(self):
        """Set up mocked environment."""
        # Reuse same logic
        def tool_decorator(func):
            class MockTool:
                def __init__(self, fn):
                    self.fn = fn
                    self.func = fn
                    self.name = fn.__name__
                def __call__(self, *args, **kwargs):
                    return self.fn(*args, **kwargs)
            return MockTool(func)

        mock_crewai = mock.MagicMock()
        mock_tools = mock.MagicMock()
        mock_tools.tool = tool_decorator
        
        with mock.patch.dict(sys.modules, {"crewai": mock_crewai, "crewai.tools": mock_tools}):
            import agents.recipe_converter
            import importlib
            importlib.reload(agents.recipe_converter)
            from agents.recipe_converter import RecipeConverterAgent

            if hasattr(RecipeConverterAgent, "_instance"):

                RecipeConverterAgent._instance = None
            yield
            RecipeConverterAgent._instance = None

    def test_convert_recipe_tool(self):
        """Test convert_recipe_tool static method."""
        from agents.recipe_converter import RecipeConverterAgent
        java_recipe = json.dumps(
            {
                "recipe_data": {
                    "type": "minecraft:crafting_shaped",
                    "pattern": ["X"],
                    "key": {"X": {"item": "minecraft:stone"}},
                    "result": {"item": "minecraft:stone"},
                },
                "namespace": "test_mod",
                "recipe_name": "stone",
            }
        )

        # Handle both direct call and crewai Tool object
        tool_func = RecipeConverterAgent.convert_recipe_tool
        if hasattr(tool_func, "func"):
            result = tool_func.func(java_recipe)
        else:
            result = tool_func(java_recipe)

        result_data = json.loads(result)

        assert result_data["success"] is True
        assert "minecraft:recipe_shaped" in result_data["converted_recipe"]

    def test_convert_recipes_batch_tool(self):
        """Test convert_recipes_batch_tool static method."""
        from agents.recipe_converter import RecipeConverterAgent
        recipes = json.dumps(
            [
                {
                    "recipe_data": {
                        "type": "minecraft:crafting_shaped",
                        "pattern": ["X"],
                        "key": {"X": {"item": "minecraft:stone"}},
                        "result": {"item": "minecraft:stone"},
                    },
                    "namespace": "test_mod",
                }
            ]
        )

        # Handle both direct call and crewai Tool object
        tool_func = RecipeConverterAgent.convert_recipes_batch_tool
        if hasattr(tool_func, "fn"):
            result = tool_func.func(recipes)
        else:
            result = tool_func(recipes)

        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["total_count"] == 1

    def test_map_item_id_tool(self):
        """Test map_item_id_tool static method."""
        from agents.recipe_converter import RecipeConverterAgent
        mappings = json.dumps({"mod:custom_item": "mod:custom_bedrock"})

        # Handle both direct call and crewai Tool object
        tool_func = RecipeConverterAgent.map_item_id_tool
        if hasattr(tool_func, "fn"):
            result = tool_func.func(mappings)
        else:
            result = tool_func(mappings)

        result_data = json.loads(result)

        assert result_data["success"] is True
