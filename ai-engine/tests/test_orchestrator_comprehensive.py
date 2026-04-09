"""
Comprehensive unit tests for ParallelOrchestrator.
"""

import pytest
import time
import json
from unittest.mock import MagicMock, patch
from orchestration.orchestrator import ParallelOrchestrator
from orchestration.strategy_selector import OrchestrationStrategy, StrategyConfig
from orchestration.task_graph import TaskGraph, TaskNode


class MockAgent:
    def __call__(self, *args, **kwargs):
        return {"success": True, "result": "mocked"}


@pytest.fixture
def orchestrator():
    return ParallelOrchestrator(enable_monitoring=True)


class TestParallelOrchestrator:
    """Test cases for ParallelOrchestrator."""

    def test_register_agent(self, orchestrator):
        """Test agent registration."""
        mock_agent = MockAgent()
        orchestrator.register_agent("test_agent", mock_agent)
        assert "test_agent" in orchestrator.agent_executors

    def test_create_conversion_workflow_all_strategies(self, orchestrator):
        """Test creating workflow for all strategies."""
        strategies = [
            OrchestrationStrategy.SEQUENTIAL,
            OrchestrationStrategy.PARALLEL_BASIC,
            OrchestrationStrategy.PARALLEL_ADAPTIVE,
            OrchestrationStrategy.HYBRID
        ]
        
        for strategy in strategies:
            with patch.object(orchestrator.strategy_selector, 'select_strategy') as mock_select:
                mock_select.return_value = (strategy, StrategyConfig())
                
                graph = orchestrator.create_conversion_workflow(
                    mod_path="test.jar",
                    output_path="out",
                    temp_dir="tmp"
                )
                assert orchestrator.current_strategy == strategy
                assert "analyze" in graph.nodes

    def test_create_workflow_invalid_strategy(self, orchestrator):
        with patch.object(orchestrator.strategy_selector, 'select_strategy') as mock_select:
            # Must return something that has .value if we get past selection
            # but here we test the final 'else' raise in create_conversion_workflow
            mock_select.return_value = (MagicMock(value="invalid"), StrategyConfig())
            with pytest.raises(ValueError, match="Unsupported strategy"):
                orchestrator.create_conversion_workflow("p", "o", "t")

    def test_execute_workflow_sequential(self, orchestrator):
        """Test executing sequential workflow."""
        orchestrator.register_agent("java_analyzer", MockAgent())
        orchestrator.register_agent("bedrock_architect", MockAgent())
        orchestrator.register_agent("logic_translator", MockAgent())
        orchestrator.register_agent("asset_converter", MockAgent())
        orchestrator.register_agent("packaging_agent", MockAgent())
        orchestrator.register_agent("qa_validator", MockAgent())

        orchestrator.current_strategy = OrchestrationStrategy.SEQUENTIAL
        orchestrator.current_config = StrategyConfig(max_parallel_tasks=1)
        
        graph = orchestrator._create_sequential_workflow(TaskGraph(), {"base": "data"})
        
        results = orchestrator.execute_workflow(graph)
        assert "analyze" in results
        assert "validate" in results

    def test_execute_workflow_exception(self, orchestrator):
        """Test execute_workflow when an exception occurs."""
        orchestrator.current_config = StrategyConfig()
        orchestrator.current_strategy = OrchestrationStrategy.SEQUENTIAL
        
        with patch.object(orchestrator, '_execute_sequential', side_effect=RuntimeError("Exec fail")):
            with pytest.raises(RuntimeError, match="Exec fail"):
                orchestrator.execute_workflow(TaskGraph())
            assert orchestrator.execution_end_time is not None

    @pytest.mark.asyncio
    async def test_execute_workflow_parallel(self, orchestrator):
        """Test executing parallel workflow."""
        orchestrator.register_agent("java_analyzer", MockAgent())
        orchestrator.register_agent("bedrock_architect", MockAgent())
        orchestrator.register_agent("logic_translator", MockAgent())
        orchestrator.register_agent("asset_converter", MockAgent())
        orchestrator.register_agent("packaging_agent", MockAgent())
        orchestrator.register_agent("qa_validator", MockAgent())

        orchestrator.current_strategy = OrchestrationStrategy.PARALLEL_BASIC
        orchestrator.current_config = StrategyConfig(max_parallel_tasks=2)
        
        graph = orchestrator._create_parallel_basic_workflow(TaskGraph(), {"base": "data"})
        
        results = orchestrator.execute_workflow(graph)
        assert "analyze" in results
        assert "validate" in results

    def test_analysis_spawn_callback_json(self, orchestrator):
        """Test analysis spawn callback with JSON string."""
        callback = orchestrator._create_analysis_spawn_callback({"base": "input"})
        result = json.dumps({"features": {"entities": [{"id": "e1", "complex": True}]}})
        spawned = callback(result)
        assert len(spawned) == 1
        assert spawned[0].agent_name == "entity_converter"

    def test_analysis_spawn_callback_error(self, orchestrator):
        callback = orchestrator._create_analysis_spawn_callback({})
        assert callback(123) == []
        assert callback("invalid json") == []

    def test_planning_spawn_callback(self, orchestrator):
        callback = orchestrator._create_planning_spawn_callback({})
        mock_res = MagicMock()
        f1 = MagicMock(); f1.id = "f1"; f1.requires_specialized_processing = True
        mock_res.complex_features = [f1]
        spawned = callback(mock_res)
        assert len(spawned) == 1
        assert spawned[0].task_id == "specialized_f1"

    def test_planning_spawn_callback_error(self, orchestrator):
        callback = orchestrator._create_planning_spawn_callback({})
        # result without complex_features
        assert callback(None) == []

    def test_execute_sequential_no_executor(self, orchestrator):
        orchestrator.current_config = StrategyConfig()
        graph = TaskGraph()
        # Use one of the standard task IDs that _execute_sequential processes
        graph.add_task(TaskNode("analyze", "missing", "type", {}))
        res = orchestrator._execute_sequential(graph, MagicMock())
        assert res == {}
        assert graph.nodes["analyze"].status.value == "failed"

    def test_execute_parallel_timeout(self, orchestrator):
        orchestrator.register_agent("a", MockAgent())
        orchestrator.current_config = StrategyConfig(task_timeout=0.01)
        graph = TaskGraph()
        graph.add_task(TaskNode("t1", "a", "type", {}))
        
        mock_pool = MagicMock()
        mock_future = MagicMock()
        mock_future.result.side_effect = TimeoutError()
        mock_pool.submit_task.return_value = mock_future
        
        with patch('orchestration.orchestrator.as_completed', return_value=[mock_future]):
            orchestrator._execute_parallel(graph, mock_pool)
            assert graph.nodes["t1"].status.value == "failed"

    def test_execute_parallel_stuck(self, orchestrator):
        orchestrator.current_config = StrategyConfig()
        graph = TaskGraph()
        graph.add_task(TaskNode("t1", "missing", "type", {}))
        # No ready tasks because no executors for 'missing'
        res = orchestrator._execute_parallel(graph, MagicMock())
        assert res == {}

    def test_analyze_mod_complexity(self, orchestrator):
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.stat") as mock_stat:
            
            mock_stat.return_value.st_size = 1 * 1024 * 1024
            complexity = orchestrator._analyze_mod_complexity("small.jar")
            assert complexity["num_features"] == 5
            
            mock_stat.return_value.st_size = 7 * 1024 * 1024
            complexity = orchestrator._analyze_mod_complexity("med.jar")
            assert complexity["num_features"] == 10

            mock_stat.return_value.st_size = 15 * 1024 * 1024
            complexity = orchestrator._analyze_mod_complexity("large.jar")
            assert complexity["num_features"] == 15

    def test_get_system_resources(self, orchestrator):
        with patch('os.path.exists', return_value=True):
            res = orchestrator._get_system_resources()
            assert res["is_containerized"] is True

    def test_get_execution_status(self, orchestrator):
        orchestrator.execution_start_time = time.time()
        orchestrator.worker_pool = MagicMock()
        status = orchestrator.get_execution_status()
        assert "worker_stats" in status

    def test_record_metrics_no_time(self, orchestrator):
        orchestrator.execution_start_time = None
        orchestrator.strategy_selector = MagicMock()
        orchestrator._record_performance_metrics(MagicMock(), {})
        assert not orchestrator.strategy_selector.record_performance.called
