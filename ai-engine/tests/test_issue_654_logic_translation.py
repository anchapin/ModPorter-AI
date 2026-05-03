"""
Comprehensive Tests for Issue #654: Complex Logic Translation
Tests for LogicTranslatorAgent expanded capabilities based on actual available API.

This file tests the actual methods available on LogicTranslatorAgent:
- translate_java_method, convert_java_class, map_java_apis
- generate_event_handlers, validate_javascript_syntax
- translate_crafting_recipe_json, generate_bedrock_block_json
- validate_block_json, map_block_properties
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from agents.logic_translator import (
    LogicTranslatorAgent,
    BEDROCK_BLOCK_TEMPLATES,
    BEDROCK_ITEM_TEMPLATES,
    BEDROCK_ENTITY_TEMPLATES,
    BEDROCK_RECIPE_TEMPLATES,
    SMART_ASSUMPTIONS,
    TREE_SITTER_AVAILABLE,
)


# ========== Test Fixtures ==========


@pytest.fixture
def agent():
    """Create a LogicTranslatorAgent instance with mocked dependencies"""
    with (
        patch("models.smart_assumptions.SmartAssumptionEngine"),
        patch("agents.java_analyzer.JavaAnalyzerAgent"),
    ):
        return LogicTranslatorAgent()


# ========== Template Availability Tests ==========


class TestTemplateAvailability:
    """Test that all required templates are available"""

    def test_item_templates_exist(self):
        """Test that item templates are defined"""
        required_templates = ["basic", "tool", "sword", "armor", "food"]
        for template in required_templates:
            assert template in BEDROCK_ITEM_TEMPLATES, f"Missing item template: {template}"

    def test_entity_templates_exist(self):
        """Test that entity templates are defined"""
        required_templates = ["hostile_mob", "passive_mob", "ambient_mob"]
        for template in required_templates:
            assert template in BEDROCK_ENTITY_TEMPLATES, f"Missing entity template: {template}"

    def test_recipe_templates_exist(self):
        """Test that recipe templates are defined"""
        required_templates = ["shaped", "shapeless", "smelting", "stonecutter"]
        for template in required_templates:
            assert template in BEDROCK_RECIPE_TEMPLATES, f"Missing recipe template: {template}"

    def test_smart_assumptions_exist(self):
        """Test that smart assumptions are documented"""
        required_assumptions = [
            "item_custom_model_data",
            "item_nbt_tags",
            "entity_custom_ai",
            "recipe_conditions",
        ]
        for assumption in required_assumptions:
            assert assumption in SMART_ASSUMPTIONS, f"Missing assumption: {assumption}"


# ========== Core Agent Tests ==========


class TestAgentCore:
    """Test core agent functionality"""

    def test_agent_initialization(self, agent):
        """Test that agent initializes correctly"""
        assert agent is not None
        assert hasattr(agent, "type_mappings")
        assert hasattr(agent, "api_mappings")
        assert hasattr(agent, "enum_mappings")

    def test_get_tools(self, agent):
        """Test that agent returns expected tools"""
        tools = agent.get_tools()
        assert len(tools) > 0

    def test_type_mappings(self, agent):
        """Test Java to JavaScript type conversion"""
        assert agent._get_javascript_type("int") == "number"
        assert agent._get_javascript_type("String") == "string"
        assert agent._get_javascript_type("List") == "Array"
        assert agent._get_javascript_type("Map") == "Map"

    def test_translate_java_method(self, agent):
        """Test Java method translation"""
        method_data = json.dumps(
            {"method_name": "testMethod", "method_body": 'System.out.println("Hello");'}
        )
        result = agent.translate_java_method(method_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True
        assert "translated_javascript" in result_data

    def test_convert_java_class(self, agent):
        """Test Java class conversion"""
        class_data = json.dumps({"class_name": "TestBlock", "methods": [{"name": "onActivate"}]})
        result = agent.convert_java_class(class_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True
        assert "javascript_class" in result_data

    def test_map_java_apis(self, agent):
        """Test API mapping"""
        api_data = json.dumps({"apis": ["player.getHealth()", "world.getBlockAt("]})
        result = agent.map_java_apis(api_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True
        assert "mapped_apis" in result_data

    def test_generate_event_handlers(self, agent):
        """Test event handler generation"""
        event_data = json.dumps({"events": ["BlockBreakEvent", "PlayerJoinEvent"]})
        result = agent.generate_event_handlers(event_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True
        assert "event_handlers" in result_data

    def test_validate_javascript_syntax(self, agent):
        """Test JavaScript syntax validation"""
        valid_js = json.dumps({"javascript_code": "function test() { return 1; }"})
        result = agent.validate_javascript_syntax(valid_js)
        result_data = json.loads(result)
        assert result_data.get("success") is True

        invalid_js = json.dumps({"javascript_code": "function test {"})
        result = agent.validate_javascript_syntax(invalid_js)
        result_data = json.loads(result)
        assert not result_data.get("is_valid")


# ========== Recipe Conversion Tests ==========


class TestRecipeConversion:
    """Test recipe conversion using translate_crafting_recipe_json"""

    def test_translate_shaped_recipe(self, agent):
        """Test translating a shaped crafting recipe"""
        recipe = {
            "type": "minecraft:crafting_shaped",
            "pattern": ["A", "A", "A"],
            "key": {"A": {"item": "minecraft:stick"}},
            "result": {"item": "minecraft:sword"},
        }
        result = agent.translate_crafting_recipe_json(json.dumps(recipe))
        result_data = json.loads(result)
        assert result_data.get("success") is True
        assert "bedrock_recipe" in result_data
        assert "minecraft:recipe_shaped" in result_data["bedrock_recipe"]

    def test_translate_shapeless_recipe(self, agent):
        """Test translating a shapeless crafting recipe"""
        recipe = {
            "type": "minecraft:crafting_shapeless",
            "ingredients": [{"item": "minecraft:stick"}],
            "result": {"item": "minecraft:sword"},
        }
        result = agent.translate_crafting_recipe_json(json.dumps(recipe))
        result_data = json.loads(result)
        assert result_data.get("success") is True
        assert "minecraft:recipe_shapeless" in result_data["bedrock_recipe"]


# ========== Block Generation Tests ==========


class TestBlockGeneration:
    """Test block generation using generate_bedrock_block_json"""

    def test_generate_basic_block(self, agent):
        """Test generating a basic block"""
        analysis = {
            "registry_name": "mod:copper_block",
            "properties": {"material": "metal", "hardness": 5.0},
        }
        result = agent.generate_bedrock_block_json(analysis)
        assert result.get("success") is True
        assert result.get("block_json") is not None
        assert "minecraft:block" in result["block_json"]

    def test_determine_block_template(self, agent):
        """Test block template determination"""
        assert agent._determine_block_template({"light_level": 10}) == "light_emitting"
        assert agent._determine_block_template({"material": "metal"}) == "metal"
        assert agent._determine_block_template({"material": "wood"}) == "wooden"

    def test_validate_block_json(self, agent):
        """Test block JSON validation"""
        block_json = json.dumps(
            {
                "block_json": {
                    "format_version": "1.17.0",
                    "minecraft:block": {
                        "description": {"identifier": "test:block"},
                        "components": {"minecraft:destroy_time": 3.0},
                    },
                }
            }
        )
        result = agent.validate_block_json(block_json)
        result_data = json.loads(result)
        assert result_data.get("success") is True
        assert result_data.get("is_valid") is True


# ========== Property Mapping Tests ==========


class TestPropertyMapping:
    """Test property mapping using map_block_properties"""

    def test_map_block_properties(self, agent):
        """Test mapping Java block properties to Bedrock"""
        props_data = json.dumps({"properties": {"material": "metal", "hardness": 5.0}})
        result = agent.map_block_properties(props_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True
        assert "bedrock_properties" in result_data


# ========== AST Analysis Tests ==========


class TestASTAnalysis:
    """Test AST analysis functionality"""

    @pytest.mark.skipif(not TREE_SITTER_AVAILABLE, reason="tree-sitter not available")
    def test_analyze_java_code_ast(self, agent):
        """Test Java code AST analysis"""
        java_code = "public class Test {}"
        result = agent.analyze_java_code_ast(java_code)
        assert result.get("success") is True
        assert "ast_tree" in result

    @pytest.mark.skipif(not TREE_SITTER_AVAILABLE, reason="tree-sitter not available")
    def test_generate_nl_summary_from_ast(self, agent):
        """Test generating NL summary from AST"""
        java_code = """
        package com.example;
        public class TestBlock extends Block {
            public TestBlock() {
                super(Material.STONE);
            }
        }
        """
        result = agent.generate_nl_summary_from_ast(java_code)
        assert result is not None


# ========== Smart Assumptions Tests ==========


class TestSmartAssumptions:
    """Test smart assumptions integration"""

    def test_smart_assumptions_loaded(self):
        """Test that smart assumptions are loaded"""
        assert SMART_ASSUMPTIONS is not None
        assert len(SMART_ASSUMPTIONS) > 0

    def test_smart_assumptions_structure(self):
        """Test that smart assumptions have proper structure"""
        for key, assumption in SMART_ASSUMPTIONS.items():
            assert "description" in assumption or "handled_by" in assumption


# ========== Edge Cases ==========


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_translate_method_with_empty_data(self, agent):
        """Test handling empty method data"""
        method_data = json.dumps({})
        result = agent.translate_java_method(method_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True

    def test_map_apis_with_empty_list(self, agent):
        """Test handling empty API list"""
        api_data = json.dumps({"apis": []})
        result = agent.map_java_apis(api_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True
        assert result_data.get("mapped_apis") == {}

    def test_unknown_recipe_type(self, agent):
        """Test handling unknown recipe type"""
        recipe = {"type": "unknown_type", "result": {"item": "test"}}
        result = agent.translate_crafting_recipe_json(json.dumps(recipe))
        result_data = json.loads(result)
        assert result_data.get("success") is False

    def test_block_generation_with_minimal_properties(self, agent):
        """Test block generation with minimal properties"""
        analysis = {"registry_name": "test:block"}
        result = agent.generate_bedrock_block_json(analysis)
        assert result.get("success") is True


# ========== Template Tests ==========


class TestTemplates:
    """Test template structure"""

    def test_block_templates_structure(self):
        """Test that block templates are loaded and have format_version"""
        assert len(BEDROCK_BLOCK_TEMPLATES) > 0
        for template_name, template in BEDROCK_BLOCK_TEMPLATES.items():
            assert "format_version" in template
            assert "minecraft:block" in template

    def test_item_templates_structure(self):
        """Test that item templates are loaded and have format_version"""
        assert len(BEDROCK_ITEM_TEMPLATES) > 0
        for template_name, template in BEDROCK_ITEM_TEMPLATES.items():
            assert "format_version" in template
            assert "minecraft:item" in template

    def test_entity_templates_structure(self):
        """Test that entity templates are loaded and have format_version"""
        assert len(BEDROCK_ENTITY_TEMPLATES) > 0
        for template_name, template in BEDROCK_ENTITY_TEMPLATES.items():
            assert "format_version" in template
            assert "minecraft:entity" in template


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
