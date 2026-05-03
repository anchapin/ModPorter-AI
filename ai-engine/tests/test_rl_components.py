"""
Test suite for RL components: AgentOptimizer, TrainingLoop, QualityScorer
"""

import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
from pathlib import Path

# Ensure ai-engine is in path
ai_engine_root = Path(__file__).parent.parent
if str(ai_engine_root) not in sys.path:
    sys.path.insert(0, str(ai_engine_root))


class TestAgentOptimizer:
    """Tests for AgentPerformanceOptimizer in rl/agent_optimizer.py"""

    @pytest.fixture
    def optimizer(self):
        from rl.agent_optimizer import AgentPerformanceOptimizer

        return AgentPerformanceOptimizer()

    def test_initialization(self, optimizer):
        """Test optimizer initializes correctly"""
        assert optimizer.performance_history == {}
        assert optimizer.episode_database == {}
        assert "excellent" in optimizer.performance_thresholds

    def test_calculate_comprehensive_metrics_minimal(self, optimizer):
        """Test _calculate_comprehensive_metrics with minimal episodes"""
        # Create mock episodes
        mock_episodes = []
        for i in range(5):
            mock_ep = MagicMock()
            mock_ep.reward_signal.total_reward = 0.5
            mock_ep.reward_signal.quality_metrics = {"overall_score": 0.7}
            mock_ep.reward_signal.conversion_metadata = {}
            mock_episodes.append(mock_ep)

        optimizer.episode_database["test_agent"] = mock_episodes

        metrics = optimizer._calculate_comprehensive_metrics("test_agent")
        assert metrics.agent_type == "test_agent"
        assert metrics.total_episodes == 5

    def test_create_minimal_metrics(self, optimizer):
        """Test _create_minimal_metrics creates valid metrics"""
        mock_episodes = []
        for i in range(3):
            mock_ep = MagicMock()
            mock_ep.reward_signal.total_reward = 0.5
            mock_ep.reward_signal.quality_metrics = None
            mock_ep.reward_signal.conversion_metadata = {}
            mock_episodes.append(mock_ep)

        optimizer.episode_database["test_agent"] = mock_episodes
        metrics = optimizer._create_minimal_metrics("test_agent", mock_episodes)

        assert metrics.agent_type == "test_agent"
        assert metrics.total_episodes == 3

    def test_track_agent_performance(self, optimizer):
        """Test track_agent_performance adds episodes and returns metrics"""
        mock_episodes = []
        for i in range(12):
            mock_ep = MagicMock()
            mock_ep.reward_signal.total_reward = 0.5 + (i * 0.01)
            mock_ep.reward_signal.quality_metrics = {"overall_score": 0.7}
            mock_ep.reward_signal.conversion_metadata = {"processing_time_seconds": 1.0}
            mock_episodes.append(mock_ep)

        metrics = optimizer.track_agent_performance("test_agent", mock_episodes)

        assert metrics.agent_type == "test_agent"
        assert "test_agent" in optimizer.episode_database
        assert "test_agent" in optimizer.performance_history

    def test_calculate_improvement_trend(self, optimizer):
        """Test _calculate_improvement_trend"""
        # Improving rewards
        improving = [0.3, 0.4, 0.5, 0.6, 0.7]
        trend = optimizer._calculate_improvement_trend(improving)
        assert trend == "improving"

        # Declining rewards
        declining = [0.7, 0.6, 0.5, 0.4, 0.3]
        trend = optimizer._calculate_improvement_trend(declining)
        assert trend == "declining"

        # Stable rewards
        stable = [0.5, 0.5, 0.5, 0.5, 0.5]
        trend = optimizer._calculate_improvement_trend(stable)
        assert trend == "stable"

    def test_calculate_recent_performance(self, optimizer):
        """Test _calculate_recent_performance"""
        rewards = [0.3] * 10 + [0.8] * 5
        recent = optimizer._calculate_recent_performance(rewards)
        assert recent > 0.7  # Should be high due to recent high rewards

    def test_calculate_stability(self, optimizer):
        """Test _calculate_stability calculation"""
        stable_rewards = [0.5, 0.51, 0.49, 0.5, 0.5]
        stability = optimizer._calculate_stability(stable_rewards)
        assert stability > 0.9  # High stability

    def test_calculate_learning_velocity(self, optimizer):
        """Test _calculate_learning_velocity - requires 10+ rewards"""
        # Need 10+ rewards for calculation
        improving = [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75]
        velocity = optimizer._calculate_learning_velocity(improving)
        assert velocity > 0  # Positive velocity with enough data

    def test_calculate_convergence_score(self, optimizer):
        """Test _calculate_convergence_score - requires 20+ rewards"""
        # Need 20+ rewards for convergence calculation (trend_analysis_window=20)
        converged = [0.5] * 20
        score = optimizer._calculate_convergence_score(converged)
        assert score > 0.9  # High convergence with stable rewards


class TestTrainingLoop:
    """Tests for RLTrainingLoop in rl/training_loop.py"""

    @pytest.fixture
    def training_loop(self):
        from rl.training_loop import RLTrainingLoop

        return RLTrainingLoop()

    def test_initialization(self, training_loop):
        """Test training loop initializes correctly"""
        assert training_loop.backend_url == "http://localhost:8000"
        assert training_loop.config["batch_size"] == 10
        assert training_loop.episodes == []
        assert training_loop.training_metrics is None

    def test_create_empty_metrics(self, training_loop):
        """Test _create_empty_metrics"""
        metrics = training_loop._create_empty_metrics()
        assert metrics.episode_count == 0
        assert metrics.average_reward == 0.0
        assert metrics.total_reward == 0.0

    @pytest.mark.asyncio
    async def test_run_training_cycle_no_data(self, training_loop):
        """Test run_training_cycle with no training data"""
        with patch.object(
            training_loop, "_fetch_training_data", new_callable=AsyncMock, return_value=[]
        ):
            metrics = await training_loop.run_training_cycle()
            assert metrics.episode_count == 0

    def test_calculate_training_metrics(self, training_loop):
        """Test _calculate_training_metrics"""
        # Create mock episodes with agent_type
        mock_episodes = []
        for i in range(10):
            mock_ep = MagicMock()
            mock_ep.agent_type = "test_agent"
            mock_ep.reward_signal.total_reward = 0.5
            mock_episodes.append(mock_ep)

        training_loop.episodes = mock_episodes

        # Patch the methods that require more complex setup
        with (
            patch.object(training_loop, "_calculate_overall_improvement_rate", return_value=0.1),
            patch.object(training_loop, "_calculate_convergence_score", return_value=0.5),
        ):
            metrics = training_loop._calculate_training_metrics()

        assert metrics.episode_count == 10
        assert metrics.total_reward > 0

    def test_training_config_values(self, training_loop):
        """Test training configuration values"""
        assert training_loop.config["learning_rate"] == 0.001
        assert training_loop.config["discount_factor"] == 0.95
        assert training_loop.config["exploration_rate"] == 0.1


class TestQualityScorer:
    """Tests for ConversionQualityScorer in rl/quality_scorer.py"""

    @pytest.fixture
    def scorer(self):
        from rl.quality_scorer import ConversionQualityScorer

        return ConversionQualityScorer()

    def test_initialization(self, scorer):
        """Test quality scorer initializes correctly"""
        assert "completeness" in scorer.weights
        assert "correctness" in scorer.weights
        assert scorer.weights["completeness"] == 0.25

    def test_quality_thresholds(self, scorer):
        """Test quality thresholds are set"""
        assert scorer.quality_thresholds["excellent"] == 0.9
        assert scorer.quality_thresholds["good"] == 0.75
        assert scorer.quality_thresholds["acceptable"] == 0.6

    def test_assess_conversion_quality_empty_paths(self, scorer):
        """Test assess_conversion_quality with empty/invalid paths"""
        # This test generates warnings - just verify it returns metrics
        result = scorer.assess_conversion_quality(
            original_mod_path="nonexistent.jar",
            converted_addon_path="nonexistent.zip",
            conversion_metadata={},
        )

        # Should return a valid QualityMetrics object (score may be > 0 based on defaults)
        assert result is not None
        assert hasattr(result, "overall_score")
        assert hasattr(result, "critical_errors")

    def test_calculate_completeness_score(self, scorer):
        """Test _calculate_completeness_score"""
        # Need to pass lists, not integers
        original = {"blocks": ["block1", "block2"], "items": ["item1"], "recipes": []}
        converted = {"blocks": ["block1"], "items": ["item1"], "recipes": []}

        # Create a proper QualityMetrics object
        from rl.quality_scorer import QualityMetrics

        metrics = QualityMetrics(
            overall_score=0.0,
            completeness_score=0.0,
            correctness_score=0.0,
            performance_score=0.0,
            compatibility_score=0.0,
            user_experience_score=0.0,
            file_structure_score=0.0,
            manifest_validity_score=0.0,
            asset_conversion_score=0.0,
            behavior_correctness_score=0.0,
            recipe_correctness_score=0.0,
            total_blocks=0,
            converted_blocks=0,
            total_items=0,
            converted_items=0,
            total_recipes=0,
            converted_recipes=0,
            total_assets=0,
            converted_assets=0,
            critical_errors=[],
            warnings=[],
            missing_features=[],
            timestamp="",
            conversion_time_seconds=0.0,
        )

        score = scorer._calculate_completeness_score(original, converted, metrics)
        assert 0 <= score <= 1.0

    def test_calculate_correctness_score(self, scorer):
        """Test _calculate_correctness_score"""
        converted = {"valid_json": True, "manifest": {"format_version": "1.20.10"}}
        metrics = MagicMock()

        score = scorer._calculate_correctness_score(converted, metrics)
        assert 0 <= score <= 1.0

    def test_calculate_performance_score(self, scorer):
        """Test _calculate_performance_score"""
        converted = {"files": []}
        metadata = {"processing_time_seconds": 5.0}
        metrics = MagicMock()

        score = scorer._calculate_performance_score(converted, metadata, metrics)
        assert 0 <= score <= 1.0

    def test_calculate_compatibility_score(self, scorer):
        """Test _calculate_compatibility_score"""
        converted = {"format_version": "1.20.10", "components": []}
        metrics = MagicMock()

        score = scorer._calculate_compatibility_score(converted, metrics)
        assert 0 <= score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
