
import pytest
from unittest.mock import MagicMock, patch
from agents.qa_agent import QAAgent, BehavioralTestEngine, PerformanceAnalyzer, CompatibilityTester

class TestQAAgent:
    @pytest.fixture
    def mock_framework(self):
        framework = MagicMock()
        framework.execute_scenario.return_value = (True, "Success", 100)
        framework.test_results_summary = []
        
        def mock_collect(scenario, success, details, exec_time, **kwargs):
            res = {
                "test_name": scenario.get("name"),
                "status": "passed" if success else "failed",
                "execution_time_ms": exec_time,
                **kwargs
            }
            framework.test_results_summary.append(res)
            return res
            
        framework.collect_results.side_effect = mock_collect
        return framework

    def test_behavioral_test_engine(self, mock_framework):
        engine = BehavioralTestEngine()
        scenarios = [
            {"name": "Test 1", "category": "functional"},
            {"name": "Test 2", "category": "performance"}
        ]
        
        results = engine.run_functional_tests(scenarios, mock_framework)
        
        assert len(results) == 1
        assert results[0]["test_name"] == "Test 1"
        mock_framework.execute_scenario.assert_called_once_with(scenarios[0])

    def test_performance_analyzer(self, mock_framework):
        engine = PerformanceAnalyzer()
        scenarios = [
            {"name": "Test 1", "category": "functional"},
            {"name": "Test 2", "category": "performance"}
        ]
        
        results = engine.analyze_performance(scenarios, mock_framework)
        
        assert len(results) == 1
        assert results[0]["test_name"] == "Test 2"
        assert "performance_metrics" in results[0]

    def test_compatibility_tester(self, mock_framework):
        engine = CompatibilityTester()
        scenarios = [
            {"name": "Test 1", "category": "compatibility"}
        ]
        
        results = engine.check_compatibility(scenarios, mock_framework)
        
        assert len(results) == 1
        assert results[0]["test_name"] == "Test 1"
        assert "performance_metrics" in results[0] # Actually compatibility metrics

    @patch("agents.qa_agent.TestScenarioGenerator")
    @patch("agents.qa_agent.TestFramework")
    def test_run_qa_pipeline(self, mock_framework_class, mock_generator_class):
        mock_framework = mock_framework_class.return_value
        mock_generator = mock_generator_class.return_value
        
        mock_framework.test_results_summary = []
        def mock_collect(scenario, success, details, exec_time, **kwargs):
            res = {"name": scenario.get("name")}
            mock_framework.test_results_summary.append(res)
            return res
        mock_framework.collect_results.side_effect = mock_collect
        mock_framework.execute_scenario.return_value = (True, "OK", 50)

        mock_generator.load_scenarios_from_file.return_value = [
            {"name": "F1", "category": "functional"},
            {"name": "P1", "category": "performance"},
            {"name": "C1", "category": "compatibility"}
        ]
        
        agent = QAAgent()
        results = agent.run_qa_pipeline("fake_path.json")
        
        assert len(results["functional_specific_results"]) == 1
        assert len(results["performance_specific_results"]) == 1
        assert len(results["compatibility_specific_results"]) == 1
        assert len(results["all_collected_by_framework"]) == 3

    @patch("agents.qa_agent.TestScenarioGenerator")
    def test_run_qa_pipeline_no_scenarios(self, mock_generator_class):
        mock_generator = mock_generator_class.return_value
        mock_generator.load_scenarios_from_file.return_value = []
        
        agent = QAAgent()
        results = agent.run_qa_pipeline("empty.json")
        
        assert "errors" in results
        assert results["errors"] == ["No scenarios loaded"]
