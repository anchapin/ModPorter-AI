import pytest
import json
from agents.logic_translator import LogicTranslatorAgent

class TestLogicTranslatorAgentComprehensive:
    @pytest.fixture
    def agent(self):
        LogicTranslatorAgent._instance = None
        return LogicTranslatorAgent.get_instance()

    def test_translate_java_method_tool_basic(self, agent):
        java_method = """
        public void onBlockPlaced(World world, BlockPos pos) {
            System.out.println("Block placed at " + pos.getX() + ", " + pos.getY() + ", " + pos.getZ());
        }
        """
        method_data = json.dumps({"method_name": "onBlockPlaced", "method_body": java_method})
        
        # Bypassing Tool wrapper
        result_json = agent.translate_java_method_tool.func(method_data)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert "translated_javascript" in result

    def test_translate_crafting_recipe_tool_shaped(self, agent):
        java_recipe = {
            "type": "minecraft:crafting_shaped",
            "pattern": ["#", "#", "#"],
            "key": {"#": {"item": "minecraft:stick"}},
            "result": {"item": "minecraft:ladder", "count": 3}
        }
        recipe_data = json.dumps(java_recipe)
        
        result_json = agent.translate_crafting_recipe_tool.func(recipe_data)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert "minecraft:recipe_shaped" in result["bedrock_recipe"]

    def test_map_java_apis_tool(self, agent):
        api_data = json.dumps({
            "apis": ["net.minecraft.block.Block", "net.minecraft.world.World"]
        })
        
        result_json = agent.map_java_apis_tool.func(api_data)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert "mapped_apis" in result

    def test_validate_javascript_syntax_tool(self, agent):
        js_code = "function test() { }"
        js_data = json.dumps({"javascript_code": js_code})
        
        result_json = agent.validate_javascript_syntax_tool.func(js_data)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert result["is_valid"] is True

    def test_validate_javascript_syntax_tool_invalid(self, agent):
        js_code = "invalid code" # No () and no {
        js_data = json.dumps({"javascript_code": js_code})
        
        result_json = agent.validate_javascript_syntax_tool.func(js_data)
        result = json.loads(result_json)
        
        assert result["is_valid"] is False
        assert len(result["syntax_errors"]) > 0
