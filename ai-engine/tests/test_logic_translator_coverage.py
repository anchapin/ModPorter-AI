import pytest
import json
from unittest.mock import MagicMock, patch
from agents.logic_translator import LogicTranslatorAgent


class TestLogicTranslatorCoverage:
    @pytest.fixture
    def agent(self):
        with (
            patch("models.smart_assumptions.SmartAssumptionEngine"),
            patch("agents.java_analyzer.JavaAnalyzerAgent"),
        ):
            return LogicTranslatorAgent()

    def test_get_instance(self):
        instance1 = LogicTranslatorAgent.get_instance()
        instance2 = LogicTranslatorAgent.get_instance()
        assert instance1 is instance2

    def test_get_tools(self, agent):
        tools = agent.get_tools()
        assert len(tools) > 0
        assert any("translate_java_method_tool" in str(t) for t in tools)

    def test_get_javascript_type(self, agent):
        assert agent._get_javascript_type("int") == "number"
        assert agent._get_javascript_type("String") == "string"

        mock_type = MagicMock()
        mock_type.name = "int"
        mock_type.dimensions = []
        assert agent._get_javascript_type(mock_type) == "number"

        mock_type.dimensions = [1]
        assert agent._get_javascript_type(mock_type) == "number[]"

    def test_translate_java_method(self, agent):
        data = {"method_name": "myMethod", "method_body": "return 1;"}
        res_json = agent.translate_java_method(json.dumps(data))
        res = json.loads(res_json)
        assert res["success"] is True
        assert "myMethod" in res["translated_javascript"]

        mock_node = MagicMock()
        mock_node.name = "astMethod"
        mock_node.parameters = []
        mock_node.return_type = None
        res_json = agent.translate_java_method(mock_node)
        res = json.loads(res_json)
        assert res["success"] is True
        assert "astMethod" in res["javascript_method"]

    def test_convert_java_class(self, agent):
        data = {
            "class_name": "MyClass",
            "methods": [{"name": "onItemRightClick"}, {"name": "regularMethod"}],
        }
        res_json = agent.convert_java_class(json.dumps(data))
        res = json.loads(res_json)
        assert res["success"] is True
        assert "MyClass" in res["javascript_class"]

    def test_map_java_apis(self, agent):
        data = {"apis": ["player.getHealth()", "world.getBlockAt("]}
        res_json = agent.map_java_apis(json.dumps(data))
        res = json.loads(res_json)
        assert res["success"] is True
        assert any("minecraft:health" in val for val in res["mapped_apis"].values())

    def test_generate_event_handlers(self, agent):
        data = {"java_events": [{"type": "PlayerInteractEvent"}], "events": ["tick"]}
        res_json = agent.generate_event_handlers(json.dumps(data))
        res = json.loads(res_json)
        assert res["success"] is True

    def test_validate_javascript_syntax(self, agent):
        data = {"javascript_code": "function test() {}"}
        res_json = agent.validate_javascript_syntax(json.dumps(data))
        res = json.loads(res_json)
        assert res["is_valid"] is True

        data = {"javascript_code": "invalid code"}
        res_json = agent.validate_javascript_syntax(json.dumps(data))
        res = json.loads(res_json)
        assert res["is_valid"] is False

    def test_translate_crafting_recipe_json(self, agent):
        shaped = {
            "type": "minecraft:crafting_shaped",
            "pattern": ["A"],
            "key": {"A": {"item": "minecraft:stick"}},
            "result": {"item": "minecraft:sword"},
        }
        res_json = agent.translate_crafting_recipe_json(json.dumps(shaped))
        res = json.loads(res_json)
        assert res["success"] is True
        assert "minecraft:recipe_shaped" in res["bedrock_recipe"]

        shapeless = {
            "type": "minecraft:crafting_shapeless",
            "ingredients": [{"item": "minecraft:stick"}],
            "result": {"item": "minecraft:sword"},
        }
        res_json = agent.translate_crafting_recipe_json(json.dumps(shapeless))
        res = json.loads(res_json)
        assert res["success"] is True
        assert "minecraft:recipe_shapeless" in res["bedrock_recipe"]

    def test_generate_bedrock_block_json(self, agent):
        analysis = {
            "registry_name": "test:copper_block",
            "properties": {"material": "metal", "hardness": 4.0},
        }
        res = agent.generate_bedrock_block_json(analysis)
        assert res["success"] is True
        assert res["block_name"] == "test:copper_block"
        assert res["block_json"]["minecraft:block"]["components"]["minecraft:destroy_time"] == 4.0

    def test_determine_block_template(self, agent):
        assert agent._determine_block_template({"light_level": 10}) == "light_emitting"
        assert agent._determine_block_template({"material": "metal"}) == "metal"
        assert agent._determine_block_template({"material": "unknown"}) == "basic"

    def test_validate_block_json(self, agent):
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
        res_json = agent.validate_block_json(block_json)
        res = json.loads(res_json)
        assert res["success"] is True
        assert res["is_valid"] is True

    def test_analyze_java_code_ast(self, agent):
        result = agent.analyze_java_code_ast("public class Test {}")
        assert "success" in result
        assert "ast_tree" in result

    def test_generate_nl_summary_from_ast(self, agent):
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


if __name__ == "__main__":
    pytest.main([__file__])
