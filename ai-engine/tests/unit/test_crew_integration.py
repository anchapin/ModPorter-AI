"""
Unit tests for EnhancedConversionCrew.
Tests integration between parallel orchestrator and CrewAI agents.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from orchestration.crew_integration import EnhancedConversionCrew

class TestEnhancedConversionCrew:
    @pytest.fixture
    def mock_agents(self):
        with patch('orchestration.crew_integration.JavaAnalyzerAgent') as mock_java, \
             patch('orchestration.crew_integration.BedrockArchitectAgent') as mock_bedrock, \
             patch('orchestration.crew_integration.LogicTranslatorAgent') as mock_logic, \
             patch('orchestration.crew_integration.AssetConverterAgent') as mock_asset, \
             patch('orchestration.crew_integration.PackagingAgent') as mock_pkg, \
             patch('orchestration.crew_integration.QAValidatorAgent') as mock_qa:
            yield {
                'java': mock_java,
                'bedrock': mock_bedrock,
                'logic': mock_logic,
                'asset': mock_asset,
                'pkg': mock_pkg,
                'qa': mock_qa
            }

    @pytest.fixture
    def crew(self, mock_agents):
        with patch('orchestration.crew_integration.ParallelOrchestrator'), \
             patch('orchestration.crew_integration.StrategySelector'):
            return EnhancedConversionCrew()

    def test_initialization(self, crew):
        """Test basic initialization."""
        assert crew.java_analyzer_agent is not None
        assert crew.orchestrator.register_agent.called

    def test_java_analyzer_executor(self, crew):
        """Test Java analyzer executor logic."""
        executor = crew._create_java_analyzer_executor()
        
        # Mock tools
        mock_tool = MagicMock()
        mock_tool.name = "extract_assets"
        mock_tool.run.return_value = ["asset1"]
        crew.java_analyzer_agent.get_tools.return_value = [mock_tool]
        
        result = executor({"mod_path": "test.jar"})
        assert result["assets"] == ["asset1"]
        mock_tool.run.assert_called_once_with(mod_path="test.jar")

    def test_java_analyzer_executor_no_path(self, crew):
        """Test Java analyzer executor error when mod_path is missing."""
        executor = crew._create_java_analyzer_executor()
        with pytest.raises(ValueError, match="mod_path is required"):
            executor({})

    def test_bedrock_architect_executor(self, crew):
        """Test Bedrock architect executor logic."""
        executor = crew._create_bedrock_architect_executor()
        
        mock_tool = MagicMock()
        mock_tool.name = "create_conversion_plan"
        mock_tool.run.return_value = {"plan": "v1"}
        crew.bedrock_architect_agent.get_tools.return_value = [mock_tool]
        
        result = executor({"analysis_result": {"features": {}}})
        assert result["conversion_plan"] == {"plan": "v1"}

    def test_logic_translator_executor(self, crew):
        """Test logic translator executor logic."""
        executor = crew._create_logic_translator_executor()
        
        mock_tool = MagicMock()
        mock_tool.name = "translate_java_to_javascript"
        mock_tool.run.return_value = ["script1"]
        crew.logic_translator_agent.get_tools.return_value = [mock_tool]
        
        result = executor({"analysis_result": {}, "planning_result": {}})
        assert result["converted_scripts"] == ["script1"]

    def test_asset_converter_executor(self, crew):
        """Test asset converter executor logic."""
        executor = crew._create_asset_converter_executor()
        
        mock_tool = MagicMock()
        mock_tool.name = "convert_texture_assets"
        mock_tool.run.return_value = ["tex1"]
        crew.asset_converter_agent.get_tools.return_value = [mock_tool]
        
        result = executor({"analysis_result": {"assets": []}})
        assert "tex1" in result["converted_assets"]

    def test_packaging_agent_executor(self, crew):
        """Test packaging agent executor logic."""
        executor = crew._create_packaging_agent_executor()
        
        mock_tool = MagicMock()
        mock_tool.name = "package_enhanced_addon"
        mock_tool.run.return_value = {"package_path": "out.mcaddon"}
        crew.packaging_agent_instance.get_tools.return_value = [mock_tool]
        
        result = executor({"translation_result": {}, "asset_result": {}, "output_path": "out/"})
        assert result["package_path"] == "out.mcaddon"

    def test_qa_validator_executor(self, crew):
        """Test QA validator executor logic."""
        executor = crew._create_qa_validator_executor()
        
        mock_tool = MagicMock()
        mock_tool.name = "validate_conversion_quality"
        mock_tool.run.return_value = {"score": 0.9}
        crew.qa_validator_agent.get_tools.return_value = [mock_tool]
        
        result = executor({"packaging_result": {"package_path": "p"}})
        assert result["validation_score"] == 0.9

    def test_convert_mod_success(self, crew):
        """Test successful convert_mod workflow."""
        mock_task_graph = MagicMock()
        mock_task_graph.get_completion_stats.return_value = {
            "completion_rate": 1.0, "total_tasks": 5, "completed_tasks": 5, 
            "failed_tasks": 0, "average_task_duration": 1.0, "total_duration": 5.0
        }
        crew.orchestrator.create_conversion_workflow.return_value = mock_task_graph
        crew.orchestrator.execute_workflow.return_value = {"plan": {"smart_assumptions": []}}
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('shutil.rmtree'):
            res = crew.convert_mod(Path("in.jar"), Path("out/"))
            assert res["status"] == "completed"
            assert res["overall_success_rate"] == 1.0

    def test_convert_mod_failure(self, crew):
        """Test convert_mod with exception."""
        crew.orchestrator.create_conversion_workflow.side_effect = Exception("Workflow fail")
        
        res = crew.convert_mod(Path("in.jar"), Path("out/"))
        assert res["status"] == "failed"
        assert "Workflow fail" in res["error"]

    def test_format_results_with_assumptions(self, crew):
        """Test result formatting with smart assumptions."""
        mock_graph = MagicMock()
        mock_graph.get_completion_stats.return_value = {
            "completion_rate": 0.9, "total_tasks": 1, "completed_tasks": 1, "failed_tasks": 0,
            "average_task_duration": 1, "total_duration": 1
        }
        mock_task = MagicMock()
        mock_task.agent_name = "agent"
        mock_task.status.value = "completed"
        mock_task.duration = 1.0
        mock_task.error = None
        mock_graph.nodes = {"task1": mock_task}
        
        exec_results = {
            "plan": {
                "smart_assumptions": [
                    {"java_feature": "feat", "type": "proxy", "bedrock_workaround": "wa", "impact": "low", "description": "desc"}
                ]
            }
        }
        
        res = crew._format_results(mock_graph, exec_results, Path("in"), Path("out"), 2.0)
        assert len(res["smart_assumptions_applied"]) == 1
        assert res["smart_assumptions_applied"][0]["original_feature"] == "feat"

    def test_calculate_parallel_efficiency(self, crew):
        """Test efficiency calculation."""
        mock_graph = MagicMock()
        mock_graph.get_completion_stats.return_value = {"total_duration": 10.0}
        
        # Sequential 10s, Parallel 5s -> Speedup 2.0
        eff = crew._calculate_parallel_efficiency(mock_graph, 5.0)
        assert eff == 2.0
        
        # Zero duration
        mock_graph.get_completion_stats.return_value = {"total_duration": 0.0}
        assert crew._calculate_parallel_efficiency(mock_graph, 5.0) == 0.0

    def test_get_orchestration_status(self, crew):
        """Test status retrieval."""
        crew.orchestrator.get_execution_status.return_value = {"active": True}
        assert crew.get_orchestration_status() == {"active": True}

    def test_get_strategy_performance_summary(self, crew):
        """Test performance summary retrieval."""
        crew.strategy_selector.get_performance_summary.return_value = {"summary": "..."}
        assert crew.get_strategy_performance_summary() == {"summary": "..."}

    def test_entity_converter_executor(self, crew):
        """Test entity converter executor logic."""
        # Need to have the agent attribute
        crew.entity_converter_agent = MagicMock()
        crew._register_agents() # Re-register to include entity_converter
        
        executor = crew._create_entity_converter_executor()
        result = executor({"entity_data": {"id": "creeper"}, "entity_index": 1})
        assert result["entity_id"] == "creeper"
        assert "behavior_pack" in result["converted_entity"]

    def test_java_analyzer_executor_varied_tools(self, crew):
        """Test Java analyzer executor with different tool names."""
        executor = crew._create_java_analyzer_executor()
        
        # Tools with different names to hit all branches
        t1 = MagicMock(); t1.name = "identify_features"; t1.run.return_value = {"feat": "v1"}
        t2 = MagicMock(); t2.name = "analyze_mod_structure"; t2.run.return_value = {"dependencies": ["dep1"]}
        t3 = MagicMock(); t3.name = "fail_tool"; t3.run.side_effect = Exception("Tool fail")
        
        crew.java_analyzer_agent.get_tools.return_value = [t1, t2, t3]
        
        result = executor({"mod_path": "test.jar"})
        assert result["features"] == {"feat": "v1"}
        assert "dep1" in result["dependencies"]

    def test_bedrock_architect_executor_assumption_tool(self, crew):
        """Test Bedrock architect executor with smart assumption tool."""
        executor = crew._create_bedrock_architect_executor()
        
        mock_tool = MagicMock()
        mock_tool.name = "apply_smart_assumption"
        mock_tool.run.return_value = [{"java_feature": "f"}]
        crew.bedrock_architect_agent.get_tools.return_value = [mock_tool]
        
        result = executor({"analysis_result": {"features": {"f1": {}}}})
        assert len(result["smart_assumptions"]) == 1

    def test_asset_converter_executor_model_tool(self, crew):
        """Test asset converter executor with model conversion tool."""
        executor = crew._create_asset_converter_executor()
        
        mock_tool = MagicMock()
        mock_tool.name = "convert_model_assets"
        mock_tool.run.return_value = ["model1"]
        crew.asset_converter_agent.get_tools.return_value = [mock_tool]
        
        result = executor({"analysis_result": {"assets": []}})
        assert "model1" in result["converted_assets"]

    def test_qa_validator_executor_functionality_tool(self, crew):
        """Test QA validator executor with functionality tests tool."""
        executor = crew._create_qa_validator_executor()
        
        mock_tool = MagicMock()
        mock_tool.name = "run_functionality_tests"
        mock_tool.run.return_value = ["test1"]
        crew.qa_validator_agent.get_tools.return_value = [mock_tool]
        
        result = executor({"packaging_result": {"package_path": "p"}})
        assert "test1" in result["functionality_tests"]

    def test_executor_exceptions(self, crew):
        """Test exception handling in all executors."""
        # Java
        crew.java_analyzer_agent.get_tools.side_effect = Exception("Fail")
        with pytest.raises(Exception):
            crew._create_java_analyzer_executor()({"mod_path": "p"})
            
        # Bedrock
        crew.bedrock_architect_agent.get_tools.side_effect = Exception("Fail")
        with pytest.raises(Exception):
            crew._create_bedrock_architect_executor()({})

        # Logic
        crew.logic_translator_agent.get_tools.side_effect = Exception("Fail")
        with pytest.raises(Exception):
            crew._create_logic_translator_executor()({})

        # Asset
        crew.asset_converter_agent.get_tools.side_effect = Exception("Fail")
        with pytest.raises(Exception):
            crew._create_asset_converter_executor()({})

        # Packaging
        crew.packaging_agent_instance.get_tools.side_effect = Exception("Fail")
        with pytest.raises(Exception):
            crew._create_packaging_agent_executor()({})

        # QA
        crew.qa_validator_agent.get_tools.side_effect = Exception("Fail")
        with pytest.raises(Exception):
            crew._create_qa_validator_executor()({})
