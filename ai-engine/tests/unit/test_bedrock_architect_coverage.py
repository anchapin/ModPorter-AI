import pytest
import json
from unittest.mock import MagicMock, patch
from agents.bedrock_architect import BedrockArchitectAgent

class TestBedrockArchitectAgent:
    @pytest.fixture
    def agent(self):
        # Reset singleton for testing
        BedrockArchitectAgent._instance = None
        return BedrockArchitectAgent.get_instance()

    def test_singleton(self):
        agent1 = BedrockArchitectAgent.get_instance()
        agent2 = BedrockArchitectAgent.get_instance()
        assert agent1 is agent2

    def test_get_tools(self, agent):
        tools = agent.get_tools()
        assert len(tools) > 0
        assert any(t.name == "analyze_java_feature_tool" for t in tools)

    def test_analyze_java_feature_tool(self, agent):
        feature_data = json.dumps({
            "feature_id": "test_block",
            "feature_type": "block",
            "name": "Test Block"
        })
        
        with patch.object(agent.smart_assumption_engine, "analyze_feature") as mock_analyze:
            mock_result = MagicMock()
            mock_result.applied_assumption = None
            mock_result.conflicting_assumptions = []
            mock_result.conflict_resolution_reason = None
            mock_analyze.return_value = mock_result
            
            # Call the tool's run method
            result_str = BedrockArchitectAgent.analyze_java_feature_tool.run(feature_data=feature_data)
            result = json.loads(result_str)
            
            assert result["feature_id"] == "test_block"
            assert "directly convertible" in result["recommendation"]

    def test_analyze_java_feature_tool_with_assumption(self, agent):
        feature_data = json.dumps({
            "feature_id": "test_high",
            "feature_type": "complex"
        })
        
        with patch.object(agent.smart_assumption_engine, "analyze_feature") as mock_analyze:
            mock_result = MagicMock()
            mock_assumption = MagicMock()
            mock_assumption.java_feature = "High Feature"
            mock_assumption.impact.value = "high"
            mock_result.applied_assumption = mock_assumption
            mock_result.conflicting_assumptions = []
            mock_result.conflict_resolution_reason = None
            mock_analyze.return_value = mock_result
            
            result_str = BedrockArchitectAgent.analyze_java_feature_tool.run(feature_data=feature_data)
            result = json.loads(result_str)
            
            assert "High-impact conversion" in result["recommendation"]
            assert "High Feature" in result["recommendation"]

    def test_apply_smart_assumption_tool(self, agent):
        assumption_data = json.dumps({
            "feature_context": {
                "feature_id": "test_id",
                "feature_type": "block",
                "name": "Test Block"
            }
        })
        
        with patch.object(agent.smart_assumption_engine, "analyze_feature") as mock_analyze, \
             patch.object(agent.smart_assumption_engine, "apply_assumption") as mock_apply:
            
            mock_result = MagicMock()
            mock_result.applied_assumption = MagicMock()
            mock_analyze.return_value = mock_result
            
            mock_component = MagicMock()
            mock_component.original_feature_id = "test_id"
            mock_component.original_feature_type = "block"
            mock_component.assumption_type = "test_assumption"
            mock_component.bedrock_equivalent = "bedrock_block"
            mock_component.impact_level = "low"
            mock_component.user_explanation = "test explanation"
            mock_component.technical_notes = "test notes"
            mock_apply.return_value = mock_component
            
            result_str = BedrockArchitectAgent.apply_smart_assumption_tool.run(assumption_data=assumption_data)
            result = json.loads(result_str)
            
            assert result["success"] is True
            assert result["conversion_plan_component"]["original_feature_id"] == "test_id"

    def test_create_conversion_plan_tool(self, agent):
        plan_data = json.dumps([
            {"feature_id": "f1", "feature_type": "block"},
            {"feature_id": "f2", "feature_type": "item"}
        ])
        
        with patch.object(agent.smart_assumption_engine, "analyze_feature") as mock_analyze, \
             patch.object(agent.smart_assumption_engine, "apply_assumption") as mock_apply, \
             patch.object(agent.smart_assumption_engine, "generate_assumption_report") as mock_report:
            
            mock_result = MagicMock()
            mock_result.applied_assumption = MagicMock()
            mock_analyze.return_value = mock_result
            
            mock_component = MagicMock()
            mock_component.original_feature_id = "f1"
            mock_component.original_feature_type = "block"
            mock_component.assumption_type = "t"
            mock_component.bedrock_equivalent = "b"
            mock_component.impact_level = "l"
            mock_component.user_explanation = "e"
            mock_component.technical_notes = "n"
            mock_apply.return_value = mock_component
            
            mock_report_obj = MagicMock()
            mock_report_obj.assumptions_applied = []
            mock_report.return_value = mock_report_obj
            
            result_str = BedrockArchitectAgent.create_conversion_plan_tool.run(plan_data=plan_data)
            result = json.loads(result_str)
            
            assert result["success"] is True
            assert result["conversion_plan_components"] == 2

    def test_get_assumption_conflicts_tool(self, agent):
        conflict_data = json.dumps({"feature_type": "block"})
        with patch.object(agent.smart_assumption_engine, "get_conflict_analysis") as mock_conflicts:
            mock_conflicts.return_value = {"conflicts": []}
            result_str = BedrockArchitectAgent.get_assumption_conflicts_tool.run(conflict_data=conflict_data)
            result = json.loads(result_str)
            assert "conflicts" in result

    def test_validate_bedrock_compatibility_tool(self, agent):
        compatibility_data = json.dumps({
            "components": [
                {"original_feature_id": "c1", "impact_level": "high", "assumption_type": "dimension"},
                {"original_feature_id": "c2", "assumption_type": "machinery"},
                {"original_feature_id": "c3", "assumption_type": "gui"}
            ]
        })
        result_str = BedrockArchitectAgent.validate_bedrock_compatibility_tool.run(compatibility_data=compatibility_data)
        result = json.loads(result_str)
        assert result["is_compatible"] is True
        assert len(result["component_validations"]) == 3
        assert len(result["warnings"]) > 0

    def test_generate_placeholder_definitions(self, agent):
        block_data = json.dumps({"id": "test_block", "name": "Test Block"})
        
        # Test block
        result_str = BedrockArchitectAgent.generate_block_definitions_tool.run(block_data=block_data)
        result = json.loads(result_str)
        assert result["success"] is True
        assert result["component_type"] == "block"
        
        # Test item
        result_str = BedrockArchitectAgent.generate_item_definitions_tool.run(item_data=block_data)
        result = json.loads(result_str)
        assert result["success"] is True
        
        # Test recipe
        result_str = BedrockArchitectAgent.generate_recipe_definitions_tool.run(recipe_data=block_data)
        result = json.loads(result_str)
        assert result["success"] is True
        
        # Test entity
        result_str = BedrockArchitectAgent.generate_entity_definitions_tool.run(entity_data=block_data)
        result = json.loads(result_str)
        assert result["success"] is True

    def test_generate_placeholder_definition_error(self, agent):
        result_str = BedrockArchitectAgent.generate_block_definitions_tool.run(block_data="invalid json")
        result = json.loads(result_str)
        assert result["success"] is False
        assert "Invalid JSON" in result["error"]
