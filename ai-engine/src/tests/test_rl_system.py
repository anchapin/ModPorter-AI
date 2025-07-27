"""
Comprehensive tests for the RL feedback loop system.
"""

import pytest
import asyncio
import tempfile
import os
import json
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Import the RL components
from rl.quality_scorer import ConversionQualityScorer, QualityMetrics
from rl.reward_system import RewardSignalGenerator, RewardSignal
from rl.training_loop import RLTrainingLoop, TrainingEpisode
from rl.agent_optimizer import AgentPerformanceOptimizer

class TestQualityScorer:
    """Test the conversion quality scoring system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = ConversionQualityScorer()
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_mock_jar_file(self, path: str, complexity: str = "simple"):
        """Create a mock JAR file for testing."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Create a simple text file to simulate JAR content
        with open(path, 'w') as f:
            if complexity == "complex":
                f.write("Mock complex JAR with many features\n" * 100)
            else:
                f.write("Mock simple JAR file\n")
    
    def create_mock_addon_directory(self, path: str, quality: str = "good"):
        """Create a mock addon directory structure for testing."""
        os.makedirs(path, exist_ok=True)
        
        # Create behavior pack structure
        bp_dir = os.path.join(path, "TestMod_BP")
        os.makedirs(os.path.join(bp_dir, "blocks"), exist_ok=True)
        os.makedirs(os.path.join(bp_dir, "recipes"), exist_ok=True)
        
        # Create resource pack structure
        rp_dir = os.path.join(path, "TestMod_RP")
        os.makedirs(os.path.join(rp_dir, "textures", "blocks"), exist_ok=True)
        
        # Create manifest files
        manifest_bp = {
            "format_version": 2,
            "header": {"name": "Test BP", "uuid": "test-uuid-bp", "version": [1, 0, 0]},
            "modules": [{"type": "data", "uuid": "test-module-bp", "version": [1, 0, 0]}]
        }
        with open(os.path.join(bp_dir, "manifest.json"), 'w') as f:
            json.dump(manifest_bp, f)
        
        manifest_rp = {
            "format_version": 2,
            "header": {"name": "Test RP", "uuid": "test-uuid-rp", "version": [1, 0, 0]},
            "modules": [{"type": "resources", "uuid": "test-module-rp", "version": [1, 0, 0]}]
        }
        with open(os.path.join(rp_dir, "manifest.json"), 'w') as f:
            json.dump(manifest_rp, f)
        
        if quality == "good":
            # Add some content files
            with open(os.path.join(bp_dir, "blocks", "test_block.json"), 'w') as f:
                json.dump({"minecraft:block": {"description": {"identifier": "test:block"}}}, f)
            
            with open(os.path.join(rp_dir, "textures", "blocks", "test_texture.png"), 'w') as f:
                f.write("mock texture content")
    
    def test_quality_scorer_initialization(self):
        """Test that quality scorer initializes correctly."""
        assert self.scorer.weights['completeness'] == 0.25
        assert self.scorer.weights['correctness'] == 0.30
        assert len(self.scorer.quality_thresholds) == 5
    
    def test_assess_conversion_quality_good_conversion(self):
        """Test quality assessment for a good conversion."""
        # Create mock files
        original_path = os.path.join(self.temp_dir, "test_mod.jar")
        converted_path = os.path.join(self.temp_dir, "converted_addon")
        
        self.create_mock_jar_file(original_path)
        self.create_mock_addon_directory(converted_path, quality="good")
        
        # Test conversion metadata
        conversion_metadata = {
            "status": "completed",
            "processing_time_seconds": 25.0,
            "job_id": "test-job-123"
        }
        
        # Assess quality
        metrics = self.scorer.assess_conversion_quality(
            original_mod_path=original_path,
            converted_addon_path=converted_path,
            conversion_metadata=conversion_metadata
        )
        
        # Assertions
        assert isinstance(metrics, QualityMetrics)
        assert metrics.overall_score > 0.5  # Should be decent quality
        assert metrics.file_structure_score > 0.0
        assert metrics.manifest_validity_score > 0.0
        assert len(metrics.critical_errors) == 0  # No critical errors expected
    
    def test_assess_conversion_quality_poor_conversion(self):
        """Test quality assessment for a poor conversion."""
        # Create mock files with poor quality
        original_path = os.path.join(self.temp_dir, "test_mod.jar")
        converted_path = os.path.join(self.temp_dir, "converted_addon")
        
        self.create_mock_jar_file(original_path, complexity="complex")
        
        # Create empty/poor quality addon
        os.makedirs(converted_path, exist_ok=True)
        
        conversion_metadata = {
            "status": "completed",
            "processing_time_seconds": 120.0,  # Slow conversion
            "job_id": "test-job-456"
        }
        
        metrics = self.scorer.assess_conversion_quality(
            original_mod_path=original_path,
            converted_addon_path=converted_path,
            conversion_metadata=conversion_metadata
        )
        
        # Poor quality should be reflected in scores
        assert metrics.overall_score < 0.5
        assert len(metrics.missing_features) > 0
    
    def test_get_quality_category(self):
        """Test quality category determination."""
        assert self.scorer.get_quality_category(0.95) == "excellent"
        assert self.scorer.get_quality_category(0.75) == "good"
        assert self.scorer.get_quality_category(0.60) == "acceptable"
        assert self.scorer.get_quality_category(0.40) == "poor"
        assert self.scorer.get_quality_category(0.20) == "failed"


class TestRewardSystem:
    """Test the reward signal generation system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.reward_generator = RewardSignalGenerator()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_mock_quality_metrics(self, overall_score: float = 0.8) -> QualityMetrics:
        """Create mock quality metrics for testing."""
        return QualityMetrics(
            overall_score=overall_score,
            completeness_score=0.85,
            correctness_score=0.75,
            performance_score=0.80,
            compatibility_score=0.85,
            user_experience_score=0.70,
            file_structure_score=0.90,
            manifest_validity_score=0.95,
            asset_conversion_score=0.70,
            behavior_correctness_score=0.80,
            recipe_correctness_score=0.75,
            total_blocks=5,
            converted_blocks=4,
            total_items=3,
            converted_items=3,
            total_recipes=2,
            converted_recipes=2,
            total_assets=10,
            converted_assets=8,
            critical_errors=[],
            warnings=["Minor warning"],
            missing_features=[],
            timestamp=datetime.now().isoformat(),
            conversion_time_seconds=30.0
        )
    
    def test_reward_generator_initialization(self):
        """Test reward generator initialization."""
        assert self.reward_generator.reward_config['base_success_reward'] == 1.0
        assert self.reward_generator.reward_config['base_failure_penalty'] == -1.0
        assert 'java_analyzer' in self.reward_generator.agent_modifiers
    
    def test_generate_reward_signal_successful_conversion(self):
        """Test reward generation for successful conversion."""
        quality_metrics = self.create_mock_quality_metrics(overall_score=0.85)
        
        conversion_metadata = {
            "status": "completed",
            "processing_time_seconds": 25.0,
            "job_id": "test-job-789"
        }
        
        user_feedback = {
            "feedback_type": "thumbs_up",
            "comment": "Great conversion!",
            "quality_rating": 4
        }
        
        reward_signal = self.reward_generator.generate_reward_signal(
            job_id="test-job-789",
            agent_type="java_analyzer",
            action_taken="mod_conversion",
            original_mod_path="test_mod.jar",
            converted_addon_path="converted_addon",
            conversion_metadata=conversion_metadata,
            user_feedback=user_feedback,
            quality_metrics=quality_metrics
        )
        
        # Assertions
        assert isinstance(reward_signal, RewardSignal)
        assert reward_signal.total_reward > 0.5  # Should be positive for good conversion
        assert reward_signal.base_reward > 0
        assert reward_signal.user_feedback_bonus > 0
        assert reward_signal.agent_type == "java_analyzer"
    
    def test_generate_reward_signal_failed_conversion(self):
        """Test reward generation for failed conversion."""
        quality_metrics = self.create_mock_quality_metrics(overall_score=0.2)
        
        conversion_metadata = {
            "status": "failed",
            "processing_time_seconds": 180.0,  # Very slow
            "job_id": "test-job-fail"
        }
        
        user_feedback = {
            "feedback_type": "thumbs_down",
            "comment": "Conversion failed completely",
            "quality_rating": 1
        }
        
        reward_signal = self.reward_generator.generate_reward_signal(
            job_id="test-job-fail",
            agent_type="conversion_planner",
            action_taken="mod_conversion",
            original_mod_path="test_mod.jar",
            converted_addon_path="converted_addon",
            conversion_metadata=conversion_metadata,
            user_feedback=user_feedback,
            quality_metrics=quality_metrics
        )
        
        # Failed conversion should have negative reward
        assert reward_signal.total_reward < 0
        assert reward_signal.base_reward < 0
        assert reward_signal.user_feedback_bonus < 0
        assert reward_signal.time_penalty > 0  # Penalty for slow processing


class TestTrainingLoop:
    """Test the RL training loop system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.training_loop = RLTrainingLoop(backend_url="http://localhost:8000")
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_training_loop_initialization(self):
        """Test training loop initialization."""
        assert self.training_loop.backend_url == "http://localhost:8000"
        assert self.training_loop.config['batch_size'] == 10
        assert len(self.training_loop.episodes) == 0
    
    def create_mock_training_data(self) -> list:
        """Create mock training data for testing."""
        return [
            {
                "job_id": "test-job-1",
                "input_file_path": "test_mod_1.jar",
                "output_file_path": "converted_addon_1.mcaddon",
                "feedback": {
                    "feedback_type": "thumbs_up",
                    "comment": "Good conversion",
                    "created_at": datetime.now().isoformat()
                }
            },
            {
                "job_id": "test-job-2", 
                "input_file_path": "test_mod_2.jar",
                "output_file_path": "converted_addon_2.mcaddon",
                "feedback": {
                    "feedback_type": "thumbs_down",
                    "comment": "Poor quality",
                    "created_at": datetime.now().isoformat()
                }
            }
        ]
    
    @pytest.mark.asyncio
    async def test_process_training_data(self):
        """Test processing of training data into episodes."""
        training_data = self.create_mock_training_data()
        
        with patch.object(self.training_loop, '_create_episode_from_data') as mock_create:
            # Mock episode creation
            mock_episode_1 = Mock()
            mock_episode_1.agent_type = "java_analyzer"
            mock_episode_2 = Mock()
            mock_episode_2.agent_type = "asset_converter"
            
            mock_create.side_effect = [mock_episode_1, mock_episode_2]
            
            episodes = await self.training_loop._process_training_data(training_data)
            
            assert len(episodes) == 2
            assert mock_create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_fetch_training_data_success(self):
        """Test successful training data fetching."""
        mock_training_data = self.create_mock_training_data()
        
        with patch('training_manager.fetch_training_data_from_backend') as mock_fetch:
            mock_fetch.return_value = mock_training_data
            
            result = await self.training_loop._fetch_training_data()
            
            assert len(result) == 2
            assert result[0]['job_id'] == "test-job-1"
    
    @pytest.mark.asyncio
    async def test_fetch_training_data_failure(self):
        """Test handling of training data fetch failure."""
        with patch('training_manager.fetch_training_data_from_backend') as mock_fetch:
            mock_fetch.return_value = None
            
            result = await self.training_loop._fetch_training_data()
            
            assert result == []


class TestAgentOptimizer:
    """Test the agent performance optimizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = AgentPerformanceOptimizer()
    
    def create_mock_episodes(self, agent_type: str, count: int = 10) -> list:
        """Create mock training episodes for testing."""
        episodes = []
        
        for i in range(count):
            # Create mock reward signal
            reward_signal = Mock()
            reward_signal.total_reward = 0.7 + (i * 0.02)  # Improving trend
            reward_signal.quality_metrics = {
                "overall_score": 0.75,
                "completeness_score": 0.8,
                "correctness_score": 0.7
            }
            reward_signal.conversion_metadata = {
                "processing_time_seconds": 30.0,
                "status": "completed"
            }
            
            # Create mock episode
            episode = Mock()
            episode.episode_id = f"test-episode-{i}"
            episode.job_id = f"test-job-{i}"
            episode.agent_type = agent_type
            episode.reward_signal = reward_signal
            episode.timestamp = datetime.now().isoformat()
            
            episodes.append(episode)
        
        return episodes
    
    def test_optimizer_initialization(self):
        """Test optimizer initialization."""
        assert self.optimizer.performance_thresholds['excellent'] == 0.85
        assert self.optimizer.optimization_config['min_episodes_for_analysis'] == 10
        assert len(self.optimizer.performance_history) == 0
    
    def test_track_agent_performance(self):
        """Test agent performance tracking."""
        episodes = self.create_mock_episodes("java_analyzer", count=15)
        
        metrics = self.optimizer.track_agent_performance("java_analyzer", episodes)
        
        # Assertions
        assert metrics.agent_type == "java_analyzer"
        assert metrics.total_episodes == 15
        assert metrics.average_reward > 0.5
        assert metrics.improvement_trend in ["improving", "stable", "declining", "insufficient_data"]
        assert len(metrics.optimization_recommendations) > 0
    
    def test_compare_agents(self):
        """Test agent comparison functionality."""
        # Track performance for multiple agents
        java_episodes = self.create_mock_episodes("java_analyzer", count=12)
        asset_episodes = self.create_mock_episodes("asset_converter", count=10)
        
        self.optimizer.track_agent_performance("java_analyzer", java_episodes)
        self.optimizer.track_agent_performance("asset_converter", asset_episodes)
        
        # Compare agents
        comparison_report = self.optimizer.compare_agents(["java_analyzer", "asset_converter"])
        
        # Assertions
        assert len(comparison_report.agents_compared) == 2
        assert "java_analyzer" in comparison_report.performance_rankings
        assert "asset_converter" in comparison_report.performance_rankings
        assert len(comparison_report.ensemble_recommendations) > 0
    
    def test_get_system_wide_metrics(self):
        """Test system-wide metrics calculation."""
        # Add performance data for multiple agents
        for agent_type in ["java_analyzer", "asset_converter", "behavior_translator"]:
            episodes = self.create_mock_episodes(agent_type, count=10)
            self.optimizer.track_agent_performance(agent_type, episodes)
        
        system_metrics = self.optimizer.get_system_wide_metrics()
        
        # Assertions
        assert system_metrics["status"] == "active"
        assert system_metrics["total_agents"] == 3
        assert "system_performance" in system_metrics
        assert "agent_breakdown" in system_metrics
        assert len(system_metrics["recommendations"]) > 0


@pytest.mark.asyncio
async def test_integration_full_rl_pipeline():
    """Integration test for the full RL pipeline."""
    # This test verifies that all components work together
    
    # Create temporary directory for test files
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Initialize all components
        scorer = ConversionQualityScorer()
        reward_generator = RewardSignalGenerator()
        optimizer = AgentPerformanceOptimizer()
        
        # Create mock conversion scenario
        original_path = os.path.join(temp_dir, "test_mod.jar")
        converted_path = os.path.join(temp_dir, "converted_addon")
        
        # Create mock files (simplified for test)
        with open(original_path, 'w') as f:
            f.write("mock jar content")
        
        os.makedirs(converted_path, exist_ok=True)
        with open(os.path.join(converted_path, "manifest.json"), 'w') as f:
            json.dump({"format_version": 2}, f)
        
        # Test quality assessment
        conversion_metadata = {
            "status": "completed",
            "processing_time_seconds": 30.0,
            "job_id": "integration-test"
        }
        
        user_feedback = {
            "feedback_type": "thumbs_up",
            "comment": "Good conversion",
            "quality_rating": 4
        }
        
        quality_metrics = scorer.assess_conversion_quality(
            original_mod_path=original_path,
            converted_addon_path=converted_path,
            conversion_metadata=conversion_metadata,
            user_feedback=user_feedback
        )
        
        # Test reward generation
        reward_signal = reward_generator.generate_reward_signal(
            job_id="integration-test",
            agent_type="java_analyzer",
            action_taken="mod_conversion",
            original_mod_path=original_path,
            converted_addon_path=converted_path,
            conversion_metadata=conversion_metadata,
            user_feedback=user_feedback,
            quality_metrics=quality_metrics
        )
        
        # Verify integration
        assert quality_metrics.overall_score >= 0.0
        assert reward_signal.total_reward != 0.0
        assert reward_signal.quality_metrics is not None
        
        print(f"Integration test passed:")
        print(f"  Quality Score: {quality_metrics.overall_score:.3f}")
        print(f"  Reward Signal: {reward_signal.total_reward:.3f}")
        print(f"  Agent Type: {reward_signal.agent_type}")
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run a simple integration test
    asyncio.run(test_integration_full_rl_pipeline())