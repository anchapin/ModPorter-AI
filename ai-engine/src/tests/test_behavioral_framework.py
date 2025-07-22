"""
Unit tests for the behavioral testing framework.
"""

import pytest
from unittest.mock import Mock, patch

# Import the framework components to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from testing.behavioral_framework import (
    GameStateTracker,
    TestScenarioExecutor,
    BehavioralAnalyzer,
    TestResultProcessor,
    BehavioralReportGenerator,
    BehavioralTestingFramework
)

from testing.minecraft_environment import MinecraftEnvironmentManager


class TestGameStateTracker:
    """Test suite for GameStateTracker class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.tracker = GameStateTracker()
    
    def test_initialization(self):
        """Test that GameStateTracker initializes correctly."""
        assert self.tracker.current_game_state == {}
        assert self.tracker.state_history == []
    
    def test_update_state(self):
        """Test state updates work correctly."""
        new_state = {"player_health": 100, "player_position": [0, 60, 0]}
        self.tracker.update_state(new_state)
        
        assert self.tracker.current_game_state == new_state
        assert len(self.tracker.state_history) == 1
        assert self.tracker.state_history[0] == new_state
    
    def test_state_history_tracking(self):
        """Test that state history is maintained correctly."""
        state1 = {"health": 100}
        state2 = {"health": 90, "position": [1, 60, 1]}
        
        self.tracker.update_state(state1)
        self.tracker.update_state(state2)
        
        assert len(self.tracker.state_history) == 2
        assert self.tracker.current_game_state == {"health": 90, "position": [1, 60, 1]}
    
    def test_get_current_state(self):
        """Test getting current state with optional key filtering."""
        test_state = {"health": 100, "mana": 50, "position": [0, 60, 0]}
        self.tracker.update_state(test_state)
        
        # Get all state
        all_state = self.tracker.get_current_state()
        assert all_state == test_state
        
        # Get specific keys
        filtered_state = self.tracker.get_current_state(["health", "mana"])
        assert filtered_state == {"health": 100, "mana": 50}
    
    def test_query_state(self):
        """Test querying individual state values."""
        self.tracker.update_state({"test_key": "test_value"})
        
        assert self.tracker.query_state("test_key") == "test_value"
        assert self.tracker.query_state("nonexistent_key") is None
        assert self.tracker.query_state("nonexistent_key", "default") == "default"
    
    def test_reset_state(self):
        """Test state reset functionality."""
        self.tracker.update_state({"some": "data"})
        assert len(self.tracker.state_history) == 1
        
        self.tracker.reset_state()
        assert self.tracker.current_game_state == {}
        assert self.tracker.state_history == []


class TestTestScenarioExecutor:
    """Test suite for TestScenarioExecutor class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.mock_env_manager = Mock(spec=MinecraftEnvironmentManager)
        self.state_tracker = GameStateTracker()
        self.executor = TestScenarioExecutor(self.mock_env_manager, self.state_tracker)
    
    def test_initialization(self):
        """Test that TestScenarioExecutor initializes correctly."""
        assert self.executor.env_manager == self.mock_env_manager
        assert self.executor.state_tracker == self.state_tracker
    
    def test_load_scenario_valid(self):
        """Test loading a valid scenario."""
        valid_scenario = {
            "scenario": "Test Scenario",
            "steps": [{"action": "test_action"}]
        }
        
        loaded = self.executor.load_scenario(valid_scenario)
        assert loaded == valid_scenario
    
    def test_load_scenario_invalid(self):
        """Test loading an invalid scenario raises error."""
        invalid_scenario = {"scenario": "Test"}  # Missing 'steps'
        
        with pytest.raises(ValueError, match="Invalid scenario format"):
            self.executor.load_scenario(invalid_scenario)
    
    def test_execute_scenario_success(self):
        """Test successful scenario execution."""
        scenario = {
            "scenario": "Block Test",
            "steps": [
                {"action": "place_block", "position": [0, 60, 0], "block_type": "stone"}
            ]
        }
        
        result = self.executor.execute_scenario(scenario)
        
        assert result["scenario_name"] == "Block Test"
        assert result["final_status"] == "SUCCESS"
        assert result["steps_executed"] == 1
        assert result["steps_succeeded"] == 1
        assert result["steps_failed"] == 0
    
    def test_execute_scenario_with_verification(self):
        """Test scenario execution with state verification."""
        scenario = {
            "scenario": "Verification Test",
            "steps": [
                {"action": "place_block", "position": [0, 60, 0], "block_type": "stone"},
                {"action": "verify_state", "key": "block_at_[0, 60, 0]", "expected": "stone"}
            ]
        }
        
        result = self.executor.execute_scenario(scenario)
        
        assert result["final_status"] == "SUCCESS"
        assert result["steps_succeeded"] == 2
    
    def test_execute_scenario_with_failure(self):
        """Test scenario execution with a failing step."""
        scenario = {
            "scenario": "Failure Test",
            "steps": [
                {"action": "verify_state", "key": "nonexistent", "expected": "value"}
            ]
        }
        
        result = self.executor.execute_scenario(scenario)
        
        assert result["final_status"] == "FAILED"
        assert result["steps_failed"] == 1


class TestBehavioralAnalyzer:
    """Test suite for BehavioralAnalyzer class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.state_tracker = GameStateTracker()
        self.analyzer = BehavioralAnalyzer(self.state_tracker)
    
    def test_initialization(self):
        """Test that BehavioralAnalyzer initializes correctly."""
        assert self.analyzer.state_tracker == self.state_tracker
    
    def test_compare_behaviors_state_change_match(self):
        """Test behavior comparison for matching state changes."""
        self.state_tracker.update_state({"test_key": "expected_value"})
        
        expected_behavior = {
            "type": "state_change",
            "key": "test_key",
            "expected_value": "expected_value"
        }
        
        result = self.analyzer.compare_behaviors(expected_behavior)
        
        assert result["match"] is True
        assert "matches" in result["details"]
    
    def test_compare_behaviors_state_change_mismatch(self):
        """Test behavior comparison for mismatched state changes."""
        self.state_tracker.update_state({"test_key": "actual_value"})
        
        expected_behavior = {
            "type": "state_change",
            "key": "test_key",
            "expected_value": "expected_value"
        }
        
        result = self.analyzer.compare_behaviors(expected_behavior)
        
        assert result["match"] is False
        assert "mismatch" in result["details"].lower()
    
    def test_compare_behaviors_invalid_type(self):
        """Test behavior comparison with invalid behavior type."""
        expected_behavior = {"type": "invalid_type"}
        
        result = self.analyzer.compare_behaviors(expected_behavior)
        
        assert result["match"] is False
        assert "Unknown behavior type" in result["details"]
    
    def test_analyze_interaction_patterns(self):
        """Test interaction pattern analysis."""
        interactions = [
            {"type": "click", "target": "block"},
            {"type": "click", "target": "entity"},
            {"type": "place", "target": "block"}
        ]
        
        result = self.analyzer.analyze_interaction_patterns(interactions)
        
        assert result["pattern"] == "summary"
        assert result["summary"]["click"] == 2
        assert result["summary"]["place"] == 1


class TestTestResultProcessor:
    """Test suite for TestResultProcessor class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.processor = TestResultProcessor()
    
    def test_initialization(self):
        """Test that TestResultProcessor initializes correctly."""
        assert self.processor.processed_results == []
    
    def test_process_scenario_result_success(self):
        """Test processing a successful scenario result."""
        scenario_output = {
            "scenario_name": "Test Scenario",
            "final_status": "SUCCESS",
            "execution_time_ms": 1000,
            "steps_executed": 3,
            "steps_succeeded": 3,
            "steps_failed": 0,
            "step_results": []
        }
        
        result = self.processor.process_scenario_result(scenario_output)
        
        assert result["scenario_name"] == "Test Scenario"
        assert result["overall_status"] == "SUCCESS"
        assert len(result["issues_detected"]) == 0
    
    def test_process_scenario_result_with_behavior_mismatch(self):
        """Test processing result with behavioral mismatch."""
        scenario_output = {
            "scenario_name": "Test Scenario",
            "final_status": "SUCCESS",
            "execution_time_ms": 1000,
            "steps_executed": 1,
            "steps_succeeded": 1,
            "steps_failed": 0,
            "step_results": []
        }
        
        behavioral_analyses = [{
            "match": False,
            "details": "State mismatch detected",
            "expected": {"key": "value1"},
            "actual": {"key": "value2"}
        }]
        
        result = self.processor.process_scenario_result(scenario_output, behavioral_analyses)
        
        assert result["overall_status"] == "FAILED_BEHAVIOR"
        assert len(result["issues_detected"]) == 1
        assert result["issues_detected"][0]["type"] == "behavior_mismatch"
    
    def test_get_summary(self):
        """Test getting processed results summary."""
        # Process some mock results
        mock_result1 = {
            "scenario_name": "Test1",
            "overall_status": "SUCCESS",
            "execution_time_ms": 1000,
            "steps_total": 2,
            "steps_succeeded": 2,
            "steps_failed": 0,
            "issues_detected": []
        }
        
        mock_result2 = {
            "scenario_name": "Test2", 
            "overall_status": "FAILED",
            "execution_time_ms": 2000,
            "steps_total": 3,
            "steps_succeeded": 2,
            "steps_failed": 1,
            "issues_detected": [{"type": "test_issue"}]
        }
        
        self.processor.processed_results = [mock_result1, mock_result2]
        
        summary = self.processor.get_summary()
        
        assert summary["total_scenarios_processed"] == 2
        assert summary["scenarios_passed"] == 1
        assert summary["scenarios_failed_or_with_issues"] == 1
        assert summary["total_execution_time_ms"] == 3000
        assert summary["total_issues_detected"] == 1


class TestBehavioralReportGenerator:
    """Test suite for BehavioralReportGenerator class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.generator = BehavioralReportGenerator()
    
    def test_initialization(self):
        """Test that BehavioralReportGenerator initializes correctly."""
        assert hasattr(self.generator, 'report_directory')
    
    def test_generate_json_report(self):
        """Test generating JSON format report."""
        test_summary = {
            "total_scenarios_processed": 2,
            "scenarios_passed": 1,
            "scenarios_failed_or_with_issues": 1,
            "total_execution_time_ms": 3000
        }
        
        report = self.generator.generate_report(test_summary, "json")
        
        assert isinstance(report, dict)
        assert report["total_scenarios_processed"] == 2
        assert "report_generated_at" in report
        assert "report_type" in report
    
    def test_generate_text_report(self):
        """Test generating text format report."""
        test_summary = {
            "total_scenarios_processed": 1,
            "scenarios_passed": 1,
            "scenarios_failed_or_with_issues": 0,
            "total_execution_time_ms": 1000
        }
        
        report = self.generator.generate_report(test_summary, "text")
        
        assert isinstance(report, str)
        assert "Behavioral Test Summary" in report
        assert "Total Scenarios Processed: 1" in report
    
    def test_generate_html_report(self):
        """Test generating HTML format report."""
        test_summary = {
            "total_scenarios_processed": 1,
            "scenarios_passed": 1,
            "scenarios_failed_or_with_issues": 0
        }
        
        report = self.generator.generate_report(test_summary, "html")
        
        assert isinstance(report, str)
        assert "<html>" in report
        assert "<h1>" in report
        assert "Behavioral Test Report" in report
    
    def test_unsupported_format_raises_error(self):
        """Test that unsupported format raises ValueError."""
        test_summary = {"test": "data"}
        
        with pytest.raises(ValueError, match="Unsupported format"):
            self.generator.generate_report(test_summary, "pdf")


class TestBehavioralTestingFramework:
    """Test suite for BehavioralTestingFramework class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.config = {
            "server_ip": "localhost",
            "server_port": 19132,
            "report_format": "json"
        }
        
    @patch('testing.behavioral_framework.MinecraftEnvironmentManager')
    def test_initialization(self, mock_env_manager):
        """Test that BehavioralTestingFramework initializes correctly."""
        framework = BehavioralTestingFramework(self.config)
        
        assert framework.config == self.config
        assert hasattr(framework, 'environment_manager')
        assert hasattr(framework, 'game_state_tracker')
        assert hasattr(framework, 'scenario_executor')
        assert hasattr(framework, 'behavior_analyzer')
        assert hasattr(framework, 'result_processor')
        assert hasattr(framework, 'report_generator')
    
    @patch('testing.behavioral_framework.MinecraftEnvironmentManager')
    def test_run_behavioral_test_success(self, mock_env_manager):
        """Test successful behavioral test execution."""
        framework = BehavioralTestingFramework(self.config)
        
        test_scenarios = [{
            "scenario": "Test Block Placement",
            "steps": [{"action": "place_block", "position": [0, 60, 0]}]
        }]
        
        result = framework.run_behavioral_test(test_scenarios)
        
        assert result["status"] == "COMPLETED"
        assert "test_summary" in result
        assert "processed_results" in result
        assert "final_report" in result
    
    @patch('testing.behavioral_framework.MinecraftEnvironmentManager')
    def test_validate_mod_conversion(self, mock_env_manager):
        """Test mod conversion validation method."""
        framework = BehavioralTestingFramework(self.config)
        
        result = framework.validate_mod_conversion(
            "/path/to/original.jar",
            "/path/to/converted.mcaddon"
        )
        
        assert result["validation_status"] == "PENDING"
        assert result["original_mod"] == "/path/to/original.jar"
        assert result["converted_addon"] == "/path/to/converted.mcaddon"


@pytest.fixture
def sample_test_data():
    """Fixture providing sample test data for tests."""
    return {
        "scenarios": [
            {
                "scenario": "Block Test",
                "steps": [{"action": "place_block", "position": [0, 60, 0]}]
            }
        ],
        "expected_behaviors": [
            {
                "type": "state_change",
                "key": "block_placed",
                "expected_value": True
            }
        ]
    }


def test_integration_full_workflow(sample_test_data):
    """Integration test for the complete behavioral testing workflow."""
    # This test demonstrates how all components work together
    tracker = GameStateTracker()
    env_manager = Mock(spec=MinecraftEnvironmentManager)
    executor = TestScenarioExecutor(env_manager, tracker)
    analyzer = BehavioralAnalyzer(tracker)
    processor = TestResultProcessor()
    generator = BehavioralReportGenerator()
    
    # Execute scenario
    scenario_result = executor.execute_scenario(sample_test_data["scenarios"][0])
    
    # Analyze behavior
    behavior_result = analyzer.compare_behaviors(sample_test_data["expected_behaviors"][0])
    
    # Process results
    processed_result = processor.process_scenario_result(scenario_result, [behavior_result])
    
    # Generate report
    summary = processor.get_summary()
    report = generator.generate_report(summary, "json")
    
    # Verify end-to-end workflow
    assert scenario_result["scenario_name"] == "Block Test"
    assert isinstance(processed_result, dict)
    assert isinstance(report, dict)
    assert "report_generated_at" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])