"""
Tests for LangGraph-based conversion pipeline.

Migration from CrewAI per issue #1201.
"""

import pytest
from unittest.mock import Mock
import json


class TestConversionState:
    """Test ConversionState TypedDict definition."""

    def test_state_initialization(self):
        """Test that ConversionState can be initialized correctly."""
        from orchestration.langgraph_pipeline import ConversionState

        state = ConversionState(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            temp_dir="/tmp/temp",
            max_retries=3,
            retry_count=0,
            errors=[],
            warnings=[],
            node_status={},
            needs_human_review=False,
            hitl_feedback=None,
        )

        assert state["job_id"] == "test_job"
        assert state["max_retries"] == 3
        assert state["retry_count"] == 0
        assert state["needs_human_review"] is False

    def test_state_with_features(self):
        """Test state with features populated."""
        from orchestration.langgraph_pipeline import ConversionState

        state = ConversionState(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            temp_dir="/tmp/temp",
            features={
                "blocks": [{"name": "test_block", "registry_name": "mod:test_block"}],
                "items": [],
                "entities": [],
            },
        )

        assert len(state["features"]["blocks"]) == 1
        assert state["features"]["blocks"][0]["registry_name"] == "mod:test_block"


class TestQARouting:
    """Test QA routing logic for conditional edges."""

    def test_qa_routing_pass(self):
        """Test routing when QA passes threshold."""
        from orchestration.langgraph_pipeline import ConversionPipeline

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            pass_threshold=0.80,
        )

        state = {
            "pass_rate": 0.85,
            "needs_human_review": False,
            "retry_count": 0,
        }

        result = pipeline._qa_routing(state)
        assert result == "complete"

    def test_qa_routing_fail(self):
        """Test routing when QA fails threshold."""
        from orchestration.langgraph_pipeline import ConversionPipeline

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            pass_threshold=0.80,
        )

        state = {
            "pass_rate": 0.60,
            "needs_human_review": False,
            "retry_count": 0,
        }

        result = pipeline._qa_routing(state)
        assert result == "retry"

    def test_qa_routing_hitl(self):
        """Test routing when human review is needed."""
        from orchestration.langgraph_pipeline import ConversionPipeline

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            pass_threshold=0.80,
        )

        state = {
            "pass_rate": 0.70,
            "needs_human_review": True,
            "retry_count": 0,
        }

        result = pipeline._qa_routing(state)
        assert result == "hitl"

    def test_qa_routing_max_retries_exceeded(self):
        """Test routing when max retries exceeded."""
        from orchestration.langgraph_pipeline import ConversionPipeline

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            pass_threshold=0.80,
            max_retries=3,
        )

        state = {
            "pass_rate": 0.60,
            "needs_human_review": False,
            "retry_count": 3,
        }

        result = pipeline._qa_routing(state)
        assert result == "complete"


class TestNodeExecution:
    """Test individual node execution."""

    @pytest.fixture
    def mock_agents(self):
        """Create mock agents."""
        mock_analyzer = Mock()
        mock_analyzer.analyze_mod_file = Mock(
            return_value=json.dumps(
                {
                    "mod_info": {"name": "TestMod", "framework": "forge"},
                    "features": {
                        "blocks": [{"name": "TestBlock", "registry_name": "mod:test_block"}],
                        "items": [],
                        "entities": [],
                    },
                    "assets": {},
                }
            )
        )

        mock_architect = Mock()
        mock_architect.smart_assumption_engine = Mock()

        return {
            "java_analyzer": mock_analyzer,
            "bedrock_architect": mock_architect,
        }

    def test_java_analyzer_node(self, mock_agents):
        """Test Java analyzer node execution."""
        from orchestration.langgraph_pipeline import ConversionPipeline, ConversionState

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )
        pipeline._agent_instances = mock_agents

        state = ConversionState(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            temp_dir="/tmp/temp",
            max_retries=3,
            retry_count=0,
            errors=[],
            warnings=[],
            node_status={},
        )

        result = pipeline._java_analyzer_node(state)

        assert "java_analyzer" in result["node_status"]
        assert result["node_status"]["java_analyzer"] == "completed"
        assert "mod_info" in result
        assert result["mod_info"]["name"] == "TestMod"

    def test_block_converter_node(self):
        """Test block converter node execution."""
        from orchestration.langgraph_pipeline import ConversionPipeline, ConversionState

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        state = ConversionState(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            temp_dir="/tmp/temp",
            max_retries=3,
            retry_count=0,
            errors=[],
            warnings=[],
            node_status={},
            features={
                "blocks": [
                    {"name": "TestBlock", "registry_name": "mod:test_block"},
                    {"name": "AnotherBlock", "registry_name": "mod:another_block"},
                ],
            },
            converted_scripts=[],
        )

        result = pipeline._block_converter_node(state)

        assert "block_converter" in result["node_status"]
        assert result["node_status"]["block_converter"] == "completed"
        assert len(result["converted_scripts"]) == 2


class TestPipelineBuilding:
    """Test pipeline graph building."""

    def test_build_graph(self):
        """Test that graph is built correctly."""
        from orchestration.langgraph_pipeline import ConversionPipeline

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        graph = pipeline.build_graph()

        assert graph is not None
        assert isinstance(graph, type(pipeline._graph))

    def test_compile_graph(self):
        """Test that graph compiles without errors."""
        from orchestration.langgraph_pipeline import ConversionPipeline

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        pipeline.build_graph()
        compiled = pipeline.compile()

        assert compiled is not None

    def test_graph_has_required_nodes(self):
        """Test that graph has all required nodes."""
        from orchestration.langgraph_pipeline import ConversionPipeline

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        pipeline.build_graph()

        expected_nodes = [
            "java_analyzer",
            "strategy_planner",
            "block_converter",
            "entity_converter",
            "recipe_converter",
            "asset_converter",
            "output_assembler",
            "qa_validator",
            "logic_translator_retry",
            "final_report",
        ]

        for node_name in expected_nodes:
            assert node_name in pipeline._graph.nodes


class TestConfidenceSegments:
    """Test confidence segment generation."""

    def test_generate_confidence_segments(self):
        """Test confidence segment generation."""
        from orchestration.langgraph_pipeline import ConversionPipeline

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        state = {
            "converted_scripts": [
                {"type": "block", "name": "block1"},
                {"type": "entity", "name": "entity1"},
                {"type": "recipe", "name": "recipe1"},
            ],
        }

        segments = pipeline._generate_confidence_segments(state)

        assert len(segments) == 3
        assert all("block_id" in s for s in segments)
        assert all("confidence" in s for s in segments)
        assert all("review_flag" in s for s in segments)
        assert all("confidence_level" in s for s in segments)

    def test_high_confidence_threshold(self):
        """Test confidence level assignment for high confidence."""
        from orchestration.langgraph_pipeline import ConversionPipeline

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        state = {
            "converted_scripts": [
                {"type": "block", "name": "test"},
            ],
        }

        segments = pipeline._generate_confidence_segments(state)

        assert segments[0]["confidence"] >= 0.80
        assert segments[0]["confidence_level"] == "high"
        assert segments[0]["review_flag"] is False


class TestFinalReport:
    """Test final report generation."""

    def test_final_report_node(self):
        """Test final report node execution."""
        from orchestration.langgraph_pipeline import ConversionPipeline, ConversionState

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        state = ConversionState(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            temp_dir="/tmp/temp",
            max_retries=3,
            retry_count=0,
            errors=[],
            warnings=[],
            node_status={},
            pass_rate=0.85,
            qa_passed=True,
            confidence_segments=[
                {
                    "block_id": "block_0",
                    "confidence": 0.95,
                    "confidence_level": "high",
                    "review_flag": False,
                },
                {
                    "block_id": "block_1",
                    "confidence": 0.65,
                    "confidence_level": "soft_flag",
                    "review_flag": True,
                },
            ],
            smart_assumptions_applied=[],
            output_path="/tmp/output.mcaddon",
        )

        result = pipeline._final_report_node(state)

        assert "final_report" in result
        assert result["final_report"]["job_id"] == "test_job"
        assert result["final_report"]["overall_success_rate"] == 0.85
        assert result["final_report"]["status"] == "completed"


class TestLangGraphOrchestrator:
    """Test backward-compatible LangGraphOrchestrator wrapper."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        from orchestration.langgraph_pipeline import LangGraphOrchestrator

        orchestrator = LangGraphOrchestrator(enable_monitoring=True)

        assert orchestrator.strategy_selector is None
        assert orchestrator.task_graph is None
        assert len(orchestrator._pipelines) == 0

    def test_create_conversion_workflow(self):
        """Test creating a conversion workflow."""
        from orchestration.langgraph_pipeline import LangGraphOrchestrator

        orchestrator = LangGraphOrchestrator()

        pipeline = orchestrator.create_conversion_workflow(
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            temp_dir="/tmp/temp",
        )

        assert pipeline is not None
        assert len(orchestrator._pipelines) == 1

    def test_get_execution_status(self):
        """Test getting execution status."""
        from orchestration.langgraph_pipeline import LangGraphOrchestrator

        orchestrator = LangGraphOrchestrator()

        status = orchestrator.get_execution_status()

        assert "active_pipelines" in status
        assert status["active_pipelines"] == 0
        assert status["strategy"] == "langgraph"

    def test_register_agent_noop(self):
        """Test that register_agent is a no-op."""
        from orchestration.langgraph_pipeline import LangGraphOrchestrator

        orchestrator = LangGraphOrchestrator()

        orchestrator.register_agent("test_agent", Mock())

        assert True


class TestParallelConverterNodes:
    """Test parallel converter node execution."""

    def test_entity_converter_node(self):
        """Test entity converter node."""
        from orchestration.langgraph_pipeline import ConversionPipeline, ConversionState

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        state = ConversionState(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            temp_dir="/tmp/temp",
            max_retries=3,
            retry_count=0,
            errors=[],
            warnings=[],
            node_status={},
            features={
                "entities": [
                    {"name": "Pig", "registry_name": "mod:pig"},
                    {"name": "Cow", "registry_name": "mod:cow"},
                ],
            },
            converted_scripts=[],
        )

        result = pipeline._entity_converter_node(state)

        assert result["node_status"]["entity_converter"] == "completed"
        assert len(result["converted_scripts"]) == 2

    def test_recipe_converter_node(self):
        """Test recipe converter node."""
        from orchestration.langgraph_pipeline import ConversionPipeline, ConversionState

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        state = ConversionState(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            temp_dir="/tmp/temp",
            max_retries=3,
            retry_count=0,
            errors=[],
            warnings=[],
            node_status={},
            features={
                "recipes": [
                    {"name": "CraftingTable", "registry_name": "mod:crafting_table"},
                ],
            },
            converted_scripts=[],
        )

        result = pipeline._recipe_converter_node(state)

        assert result["node_status"]["recipe_converter"] == "completed"
        assert len(result["converted_scripts"]) == 1

    def test_asset_converter_node(self):
        """Test asset converter node."""
        from orchestration.langgraph_pipeline import ConversionPipeline, ConversionState

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        state = ConversionState(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            temp_dir="/tmp/temp",
            max_retries=3,
            retry_count=0,
            errors=[],
            warnings=[],
            node_status={},
            assets={
                "textures": [{"name": "block_texture"}],
                "models": [{"name": "block_model"}],
            },
        )

        result = pipeline._asset_converter_node(state)

        assert result["node_status"]["asset_converter"] == "completed"
        assert len(result["converted_assets"]) == 2


class TestOutputAssembler:
    """Test output assembler node."""

    def test_output_assembler_node(self):
        """Test output assembler node execution."""
        from orchestration.langgraph_pipeline import ConversionPipeline, ConversionState

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        state = ConversionState(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            temp_dir="/tmp/temp",
            max_retries=3,
            retry_count=0,
            errors=[],
            warnings=[],
            node_status={},
            converted_scripts=[{"type": "block", "name": "test"}],
            converted_assets=[{"type": "texture", "name": "test"}],
            smart_assumptions_applied=[
                {
                    "original_feature": "custom_dimension",
                    "assumption_type": "dimension_to_structure",
                    "bedrock_equivalent": "static_structure",
                    "impact_level": "high",
                    "user_explanation": "Custom dimension converted to static structure",
                }
            ],
        )

        result = pipeline._output_assembler_node(state)

        assert result["node_status"]["output_assembler"] == "completed"
        assert "bedrock_json" in result
        assert result["bedrock_json"]["format_version"] == "1.20.0"


class TestStrategyPlanner:
    """Test strategy planner node."""

    def test_strategy_planner_node(self):
        """Test strategy planner node execution."""
        from orchestration.langgraph_pipeline import ConversionPipeline, ConversionState

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
        )

        mock_architect = Mock()
        mock_engine = Mock()
        mock_result = Mock()
        mock_result.applied_assumption = None
        mock_engine.analyze_feature = Mock(return_value=mock_result)
        mock_engine.apply_assumption = Mock(return_value=None)
        mock_architect.smart_assumption_engine = mock_engine

        pipeline._agent_instances = {
            "bedrock_architect": mock_architect,
        }

        state = ConversionState(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            temp_dir="/tmp/temp",
            max_retries=3,
            retry_count=0,
            errors=[],
            warnings=[],
            node_status={},
            features={
                "blocks": [{"name": "TestBlock", "registry_name": "mod:test_block"}],
            },
        )

        result = pipeline._strategy_planner_node(state)

        assert result["node_status"]["strategy_planner"] == "completed"


class TestRetryLogic:
    """Test retry logic for failed segments."""

    def test_logic_translator_retry_node(self):
        """Test logic translator retry node."""
        from orchestration.langgraph_pipeline import ConversionPipeline, ConversionState

        pipeline = ConversionPipeline(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            max_retries=3,
        )

        state = ConversionState(
            job_id="test_job",
            mod_path="/tmp/mod.jar",
            output_path="/tmp/output",
            temp_dir="/tmp/temp",
            max_retries=3,
            retry_count=1,
            errors=[],
            warnings=[],
            node_status={},
            interrupted_segments=["block_1", "entity_2"],
        )

        result = pipeline._logic_translator_retry_node(state)

        assert result["node_status"]["logic_translator_retry"] == "completed"
        assert result["retry_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
