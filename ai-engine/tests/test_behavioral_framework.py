"""
Test suite for Behavioral Framework in testing/behavioral_framework.py
"""

import pytest
from unittest.mock import MagicMock
import sys
from pathlib import Path

# Ensure ai-engine is in path
ai_engine_root = Path(__file__).parent.parent
if str(ai_engine_root) not in sys.path:
    sys.path.insert(0, str(ai_engine_root))


class TestGameStateTracker:
    """Tests for GameStateTracker in testing/behavioral_framework.py"""

    @pytest.fixture
    def tracker(self):
        from testing.behavioral_framework import GameStateTracker

        return GameStateTracker()

    def test_initialization(self, tracker):
        """Test GameStateTracker initializes correctly"""
        assert tracker.current_game_state == {}
        assert tracker.state_history == []

    def test_update_state(self, tracker):
        """Test update_state adds new state variables"""
        new_state = {"player_health": 100, "player_position": {"x": 0, "y": 64, "z": 0}}
        tracker.update_state(new_state)

        assert tracker.current_game_state["player_health"] == 100
        assert tracker.current_game_state["player_position"]["y"] == 64
        assert len(tracker.state_history) > 0

    def test_get_current_state_no_filter(self, tracker):
        """Test get_current_state without specific keys"""
        tracker.update_state({"key1": "value1", "key2": "value2"})
        state = tracker.get_current_state()

        assert "key1" in state
        assert "key2" in state

    def test_get_current_state_with_filter(self, tracker):
        """Test get_current_state with specific keys"""
        tracker.update_state({"key1": "value1", "key2": "value2", "key3": "value3"})
        state = tracker.get_current_state(specific_keys=["key1", "key3"])

        assert "key1" in state
        assert "key3" in state
        assert "key2" not in state

    def test_get_state_history(self, tracker):
        """Test get_state_history returns all history"""
        tracker.update_state({"state": 1})
        tracker.update_state({"state": 2})
        tracker.update_state({"state": 3})

        history = tracker.get_state_history()
        assert len(history) >= 3

    def test_reset_state(self, tracker):
        """Test reset_state clears state and history"""
        tracker.update_state({"key": "value"})
        tracker.reset_state()

        assert tracker.current_game_state == {}
        assert tracker.state_history == []

    def test_query_state(self, tracker):
        """Test query_state retrieves specific keys"""
        tracker.update_state({"health": 100, "hunger": 80})

        assert tracker.query_state("health") == 100
        assert tracker.query_state("hunger") == 80
        assert tracker.query_state("missing", "default") == "default"


class TestTestScenarioExecutor:
    """Tests for TestScenarioExecutor in testing/behavioral_framework.py"""

    @pytest.fixture
    def executor(self):
        from testing.behavioral_framework import TestScenarioExecutor, GameStateTracker

        # Create mock environment manager
        mock_env = MagicMock()
        mock_env.execute_command.return_value = {"success": True}

        tracker = GameStateTracker()
        return TestScenarioExecutor(mock_env, tracker)

    def test_initialization(self, executor):
        """Test executor initializes correctly"""
        assert executor.env_manager is not None
        assert executor.state_tracker is not None

    def test_load_scenario_valid(self, executor):
        """Test load_scenario with valid data"""
        scenario = {
            "scenario": "Test Scenario",
            "steps": [
                {"action": "spawn_player", "params": {}},
                {"action": "give_item", "params": {"item": "diamond"}},
            ],
        }

        result = executor.load_scenario(scenario)
        assert result == scenario

    def test_load_scenario_invalid(self, executor):
        """Test load_scenario with invalid data"""
        scenario = {"scenario": "Missing steps"}

        with pytest.raises(ValueError):
            executor.load_scenario(scenario)

    def test_execute_scenario_success(self, executor):
        """Test execute_scenario with successful steps"""
        scenario = {
            "scenario": "Test Scenario",
            "steps": [
                {"action": "spawn_entity", "params": {"type": "player"}},
                {"action": "right_click", "params": {"block": "chest"}},
            ],
        }

        # Mock environment to return success
        executor.env_manager.execute_command.return_value = {"success": True, "result": "ok"}

        result = executor.execute_scenario(scenario)

        assert result["scenario_name"] == "Test Scenario"
        assert result["steps_executed"] == 2
        assert result["final_status"] == "SUCCESS"

    def test_execute_scenario_failure(self, executor):
        """Test execute_scenario with failed steps"""
        # verify_state fails when state doesn't match
        scenario = {
            "scenario": "Test Failure",
            "steps": [{"action": "verify_state", "key": "nonexistent", "expected": "value"}],
        }

        result = executor.execute_scenario(scenario)

        assert result["final_status"] == "FAILED"
        assert result["steps_failed"] > 0

    def test_execute_scenario_fail_fast(self, executor):
        """Test execute_scenario with fail_fast enabled"""
        scenario = {
            "scenario": "Fail Fast Test",
            "steps": [
                {"action": "spawn_entity", "params": {"type": "zombie"}},
                {"action": "verify_state", "key": "nonexistent", "expected": "value"},
                {"action": "verify_behavior", "expected_behavior_id": "attack"},
            ],
            "fail_fast": True,
        }

        result = executor.execute_scenario(scenario)

        # Should stop at first failure (verify_state with no matching state)
        assert result["steps_executed"] == 2
        assert result["steps_failed"] == 1
        assert result["final_status"] == "FAILED"


class TestBehavioralFramework:
    """Integration tests for the behavioral framework"""

    def test_framework_components_work_together(self):
        """Test that framework components integrate properly"""
        from testing.behavioral_framework import GameStateTracker

        # Create components
        tracker = GameStateTracker()

        # Test state tracking workflow
        tracker.update_state(
            {"test_started": True, "entities": [{"type": "zombie", "position": [0, 64, 0]}]}
        )

        state = tracker.get_current_state()
        assert state["test_started"] is True
        assert len(state["entities"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
