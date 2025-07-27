"""
Reinforcement Learning Training Loop for AI Agents
Implements the core RL training pipeline with feedback integration.
"""

import asyncio
import logging
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import httpx
from pathlib import Path

from .quality_scorer import ConversionQualityScorer, QualityMetrics
from .reward_system import RewardSignalGenerator, RewardSignal
# Note: This will be imported dynamically to avoid circular imports
# from ..training_manager import fetch_training_data_from_backend

logger = logging.getLogger(__name__)

@dataclass
class TrainingEpisode:
    """Represents a single training episode"""
    episode_id: str
    job_id: str
    agent_type: str
    state_before: Dict[str, Any]
    action_taken: str
    state_after: Dict[str, Any]
    reward_signal: RewardSignal
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TrainingMetrics:
    """Training performance metrics"""
    episode_count: int
    total_reward: float
    average_reward: float
    improvement_rate: float
    convergence_score: float
    best_episode_reward: float
    worst_episode_reward: float
    agent_performance: Dict[str, Dict[str, float]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class RLTrainingLoop:
    """
    Main RL training loop that processes conversion outcomes and improves agent performance.
    
    Integrates with:
    - Backend API for training data
    - Quality assessment system
    - Reward signal generation
    - Agent performance tracking
    """
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.quality_scorer = ConversionQualityScorer()
        self.reward_generator = RewardSignalGenerator()
        
        # Training configuration
        self.config = {
            'batch_size': 10,
            'learning_rate': 0.001,
            'discount_factor': 0.95,
            'exploration_rate': 0.1,
            'min_episodes_for_training': 5,
            'convergence_threshold': 0.01,
            'max_episodes_per_cycle': 100,
            'training_data_limit': 50,
        }
        
        # Training state
        self.episodes: List[TrainingEpisode] = []
        self.training_metrics: Optional[TrainingMetrics] = None
        self.model_checkpoints: Dict[str, str] = {}  # agent_type -> checkpoint_path
        
        # File paths
        self.training_data_dir = Path("training_data")
        self.model_dir = Path("models")
        self.training_data_dir.mkdir(exist_ok=True)
        self.model_dir.mkdir(exist_ok=True)

    async def run_training_cycle(self) -> TrainingMetrics:
        """
        Run a complete training cycle:
        1. Fetch new training data from backend
        2. Process conversions and generate rewards
        3. Update agent models
        4. Evaluate performance
        """
        
        logger.info("Starting RL training cycle")
        
        try:
            # 1. Fetch training data
            training_data = await self._fetch_training_data()
            if not training_data:
                logger.warning("No training data available")
                return self._create_empty_metrics()
            
            # 2. Generate episodes from training data
            new_episodes = await self._process_training_data(training_data)
            self.episodes.extend(new_episodes)
            
            # 3. Perform training if enough episodes
            if len(self.episodes) >= self.config['min_episodes_for_training']:
                await self._train_agents()
            
            # 4. Calculate metrics
            self.training_metrics = self._calculate_training_metrics()
            
            # 5. Save training state
            await self._save_training_state()
            
            logger.info(f"Training cycle completed. Episodes: {len(self.episodes)}, "
                       f"Average reward: {self.training_metrics.average_reward:.3f}")
            
            return self.training_metrics
            
        except Exception as e:
            logger.error(f"Training cycle failed: {e}", exc_info=True)
            return self._create_empty_metrics()

    async def _fetch_training_data(self) -> List[Dict[str, Any]]:
        """Fetch training data from backend API."""
        
        try:
            # Import dynamically to avoid circular imports
            import sys
            import os
            parent_dir = os.path.dirname(os.path.dirname(__file__))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            from training_manager import fetch_training_data_from_backend
            
            training_data = await fetch_training_data_from_backend(
                backend_url=self.backend_url,
                skip=0,
                limit=self.config['training_data_limit']
            )
            
            if training_data:
                logger.info(f"Fetched {len(training_data)} training data items")
                return training_data
            else:
                logger.warning("No training data returned from backend")
                return []
                
        except Exception as e:
            logger.error(f"Failed to fetch training data: {e}")
            return []

    async def _process_training_data(self, training_data: List[Dict[str, Any]]) -> List[TrainingEpisode]:
        """Process training data into RL episodes."""
        
        episodes = []
        
        for item in training_data:
            try:
                episode = await self._create_episode_from_data(item)
                if episode:
                    episodes.append(episode)
            except Exception as e:
                logger.error(f"Failed to process training item {item.get('job_id')}: {e}")
        
        logger.info(f"Processed {len(episodes)} episodes from training data")
        return episodes

    async def _create_episode_from_data(self, training_item: Dict[str, Any]) -> Optional[TrainingEpisode]:
        """Create a training episode from a single training data item."""
        
        job_id = training_item.get('job_id')
        if not job_id:
            logger.warning("Training item missing job_id")
            return None
        
        # Extract paths and metadata
        input_path = training_item.get('input_file_path', '')
        output_path = training_item.get('output_file_path', '')
        feedback_data = training_item.get('feedback', {})
        
        # Determine agent type (could be extracted from metadata or inferred)
        agent_type = self._infer_agent_type(training_item)
        
        # Create conversion metadata
        conversion_metadata = {
            'job_id': job_id,
            'status': 'completed' if output_path else 'failed',
            'processing_time_seconds': 30.0,  # Default, could be extracted from actual data
            'input_file_size': self._get_file_size(input_path),
            'output_file_size': self._get_file_size(output_path),
        }
        
        # Generate quality assessment and reward
        try:
            quality_metrics = None
            if output_path and os.path.exists(output_path):
                quality_metrics = self.quality_scorer.assess_conversion_quality(
                    original_mod_path=input_path,
                    converted_addon_path=output_path,
                    conversion_metadata=conversion_metadata,
                    user_feedback=feedback_data
                )
            
            # Generate reward signal
            reward_signal = self.reward_generator.generate_reward_signal(
                job_id=job_id,
                agent_type=agent_type,
                action_taken="conversion",
                original_mod_path=input_path,
                converted_addon_path=output_path,
                conversion_metadata=conversion_metadata,
                user_feedback=feedback_data,
                quality_metrics=quality_metrics
            )
            
            # Create episode
            episode = TrainingEpisode(
                episode_id=f"{job_id}_{agent_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                job_id=job_id,
                agent_type=agent_type,
                state_before=self._extract_state_from_input(input_path),
                action_taken="conversion",
                state_after=self._extract_state_from_output(output_path),
                reward_signal=reward_signal,
                timestamp=datetime.now().isoformat()
            )
            
            return episode
            
        except Exception as e:
            logger.error(f"Failed to create episode for job {job_id}: {e}")
            return None

    def _infer_agent_type(self, training_item: Dict[str, Any]) -> str:
        """Infer the agent type from training data."""
        
        # Could be enhanced to look at actual conversion steps or metadata
        # For now, rotate through agent types or use a default
        input_path = training_item.get('input_file_path', '')
        
        if 'complex' in input_path.lower():
            return 'java_analyzer'
        elif 'texture' in input_path.lower():
            return 'asset_converter'
        elif 'behavior' in input_path.lower():
            return 'behavior_translator'
        else:
            return 'conversion_planner'  # Default

    def _get_file_size(self, file_path: str) -> int:
        """Get file size, return 0 if file doesn't exist."""
        try:
            if file_path and os.path.exists(file_path):
                return os.path.getsize(file_path)
        except Exception:
            pass
        return 0

    def _extract_state_from_input(self, input_path: str) -> Dict[str, Any]:
        """Extract state representation from input file."""
        
        state = {
            'file_exists': os.path.exists(input_path) if input_path else False,
            'file_size': self._get_file_size(input_path),
            'file_type': os.path.splitext(input_path)[1].lower() if input_path else '',
            'complexity_indicators': []
        }
        
        # Add more sophisticated state extraction here
        if input_path and input_path.endswith('.jar'):
            state['complexity_indicators'] = self._analyze_jar_complexity(input_path)
        
        return state

    def _extract_state_from_output(self, output_path: str) -> Dict[str, Any]:
        """Extract state representation from output file."""
        
        state = {
            'file_exists': os.path.exists(output_path) if output_path else False,
            'file_size': self._get_file_size(output_path),
            'file_type': os.path.splitext(output_path)[1].lower() if output_path else '',
            'structure_indicators': []
        }
        
        # Add more sophisticated state extraction here
        if output_path and output_path.endswith('.mcaddon'):
            state['structure_indicators'] = self._analyze_mcaddon_structure(output_path)
        
        return state

    def _analyze_jar_complexity(self, jar_path: str) -> List[str]:
        """Analyze JAR file complexity indicators."""
        indicators = []
        
        try:
            if os.path.exists(jar_path):
                file_size = os.path.getsize(jar_path)
                if file_size > 1024 * 1024:  # > 1MB
                    indicators.append('large_file')
                if file_size > 10 * 1024 * 1024:  # > 10MB
                    indicators.append('very_large_file')
        except Exception:
            indicators.append('analysis_error')
        
        return indicators

    def _analyze_mcaddon_structure(self, mcaddon_path: str) -> List[str]:
        """Analyze .mcaddon file structure indicators."""
        indicators = []
        
        try:
            if os.path.exists(mcaddon_path):
                file_size = os.path.getsize(mcaddon_path)
                if file_size > 0:
                    indicators.append('valid_output')
                if file_size > 100 * 1024:  # > 100KB
                    indicators.append('substantial_content')
        except Exception:
            indicators.append('analysis_error')
        
        return indicators

    async def _train_agents(self) -> None:
        """Perform agent training using collected episodes."""
        
        logger.info(f"Training agents with {len(self.episodes)} episodes")
        
        # Group episodes by agent type
        agent_episodes = {}
        for episode in self.episodes:
            if episode.agent_type not in agent_episodes:
                agent_episodes[episode.agent_type] = []
            agent_episodes[episode.agent_type].append(episode)
        
        # Train each agent type
        for agent_type, episodes in agent_episodes.items():
            await self._train_single_agent(agent_type, episodes)

    async def _train_single_agent(self, agent_type: str, episodes: List[TrainingEpisode]) -> None:
        """Train a single agent type with its episodes."""
        
        logger.info(f"Training {agent_type} with {len(episodes)} episodes")
        
        # For now, implement a simple reward-based learning
        # In a real implementation, this would integrate with actual ML frameworks
        
        # Calculate average reward for this agent
        rewards = [ep.reward_signal.total_reward for ep in episodes]
        avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
        
        # Simulate model update (placeholder)
        await self._update_agent_model(agent_type, episodes, avg_reward)
        
        logger.info(f"Updated {agent_type} model. Average reward: {avg_reward:.3f}")

    async def _update_agent_model(
        self, 
        agent_type: str, 
        episodes: List[TrainingEpisode], 
        avg_reward: float
    ) -> None:
        """Update the agent's model based on episodes."""
        
        # This is a placeholder for actual model training
        # In practice, this would:
        # 1. Prepare training data from episodes
        # 2. Update neural network weights
        # 3. Save updated model checkpoint
        
        model_path = self.model_dir / f"{agent_type}_model.json"
        
        # Save training metadata
        model_data = {
            'agent_type': agent_type,
            'last_updated': datetime.now().isoformat(),
            'episode_count': len(episodes),
            'average_reward': avg_reward,
            'training_episodes': len(self.episodes),
            'performance_trend': self._calculate_performance_trend(agent_type)
        }
        
        try:
            with open(model_path, 'w') as f:
                json.dump(model_data, f, indent=2)
            
            self.model_checkpoints[agent_type] = str(model_path)
            logger.info(f"Saved {agent_type} model checkpoint to {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to save model for {agent_type}: {e}")

    def _calculate_performance_trend(self, agent_type: str) -> str:
        """Calculate performance trend for an agent."""
        
        # Get recent episodes for this agent
        agent_episodes = [ep for ep in self.episodes if ep.agent_type == agent_type]
        
        if len(agent_episodes) < 3:
            return "insufficient_data"
        
        # Sort by timestamp and get recent rewards
        agent_episodes.sort(key=lambda x: x.timestamp)
        recent_rewards = [ep.reward_signal.total_reward for ep in agent_episodes[-10:]]
        
        if len(recent_rewards) < 3:
            return "insufficient_data"
        
        # Simple trend calculation
        first_half_avg = sum(recent_rewards[:len(recent_rewards)//2]) / (len(recent_rewards)//2)
        second_half_avg = sum(recent_rewards[len(recent_rewards)//2:]) / (len(recent_rewards) - len(recent_rewards)//2)
        
        if second_half_avg > first_half_avg + 0.1:
            return "improving"
        elif second_half_avg < first_half_avg - 0.1:
            return "declining"
        else:
            return "stable"

    def _calculate_training_metrics(self) -> TrainingMetrics:
        """Calculate comprehensive training metrics."""
        
        if not self.episodes:
            return self._create_empty_metrics()
        
        # Overall metrics
        total_reward = sum(ep.reward_signal.total_reward for ep in self.episodes)
        avg_reward = total_reward / len(self.episodes)
        
        rewards = [ep.reward_signal.total_reward for ep in self.episodes]
        best_reward = max(rewards)
        worst_reward = min(rewards)
        
        # Agent-specific metrics
        agent_performance = {}
        agent_episodes = {}
        
        for episode in self.episodes:
            agent_type = episode.agent_type
            if agent_type not in agent_episodes:
                agent_episodes[agent_type] = []
            agent_episodes[agent_type].append(episode)
        
        for agent_type, episodes in agent_episodes.items():
            agent_rewards = [ep.reward_signal.total_reward for ep in episodes]
            agent_performance[agent_type] = {
                'episode_count': len(episodes),
                'average_reward': sum(agent_rewards) / len(agent_rewards),
                'best_reward': max(agent_rewards),
                'worst_reward': min(agent_rewards),
                'improvement_rate': self._calculate_improvement_rate(agent_rewards)
            }
        
        # Calculate improvement rate and convergence
        improvement_rate = self._calculate_overall_improvement_rate()
        convergence_score = self._calculate_convergence_score()
        
        return TrainingMetrics(
            episode_count=len(self.episodes),
            total_reward=total_reward,
            average_reward=avg_reward,
            improvement_rate=improvement_rate,
            convergence_score=convergence_score,
            best_episode_reward=best_reward,
            worst_episode_reward=worst_reward,
            agent_performance=agent_performance
        )

    def _calculate_improvement_rate(self, rewards: List[float]) -> float:
        """Calculate improvement rate for a reward sequence."""
        
        if len(rewards) < 2:
            return 0.0
        
        # Simple linear improvement calculation
        first_quarter = rewards[:len(rewards)//4] if len(rewards) >= 4 else rewards[:1]
        last_quarter = rewards[-len(rewards)//4:] if len(rewards) >= 4 else rewards[-1:]
        
        first_avg = sum(first_quarter) / len(first_quarter)
        last_avg = sum(last_quarter) / len(last_quarter)
        
        return (last_avg - first_avg) / max(abs(first_avg), 0.1)

    def _calculate_overall_improvement_rate(self) -> float:
        """Calculate overall improvement rate across all episodes."""
        
        if len(self.episodes) < 5:
            return 0.0
        
        # Sort episodes by timestamp
        sorted_episodes = sorted(self.episodes, key=lambda x: x.timestamp)
        rewards = [ep.reward_signal.total_reward for ep in sorted_episodes]
        
        return self._calculate_improvement_rate(rewards)

    def _calculate_convergence_score(self) -> float:
        """Calculate how close the training is to convergence."""
        
        if len(self.episodes) < 10:
            return 0.0
        
        # Look at reward variance in recent episodes
        recent_episodes = self.episodes[-10:]
        recent_rewards = [ep.reward_signal.total_reward for ep in recent_episodes]
        
        # Calculate coefficient of variation
        mean_reward = sum(recent_rewards) / len(recent_rewards)
        variance = sum((r - mean_reward) ** 2 for r in recent_rewards) / len(recent_rewards)
        std_dev = variance ** 0.5
        
        if mean_reward == 0:
            return 0.0
        
        cv = std_dev / abs(mean_reward)
        
        # Convert to convergence score (lower variance = higher convergence)
        convergence_score = max(0.0, 1.0 - cv)
        
        return convergence_score

    def _create_empty_metrics(self) -> TrainingMetrics:
        """Create empty metrics for when no training data is available."""
        
        return TrainingMetrics(
            episode_count=0,
            total_reward=0.0,
            average_reward=0.0,
            improvement_rate=0.0,
            convergence_score=0.0,
            best_episode_reward=0.0,
            worst_episode_reward=0.0,
            agent_performance={}
        )

    async def _save_training_state(self) -> None:
        """Save training state and metrics to disk."""
        
        try:
            # Save episodes
            episodes_file = self.training_data_dir / "episodes.json"
            episodes_data = {
                'timestamp': datetime.now().isoformat(),
                'episode_count': len(self.episodes),
                'episodes': [ep.to_dict() for ep in self.episodes]
            }
            
            with open(episodes_file, 'w') as f:
                json.dump(episodes_data, f, indent=2)
            
            # Save metrics
            if self.training_metrics:
                metrics_file = self.training_data_dir / "training_metrics.json"
                with open(metrics_file, 'w') as f:
                    json.dump(self.training_metrics.to_dict(), f, indent=2)
            
            logger.info(f"Saved training state: {len(self.episodes)} episodes")
            
        except Exception as e:
            logger.error(f"Failed to save training state: {e}")

    async def load_training_state(self) -> None:
        """Load existing training state from disk."""
        
        try:
            episodes_file = self.training_data_dir / "episodes.json"
            if episodes_file.exists():
                with open(episodes_file, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct episodes
                self.episodes = []
                for ep_dict in data.get('episodes', []):
                    # Reconstruct RewardSignal
                    reward_data = ep_dict['reward_signal']
                    reward_signal = RewardSignal(**reward_data)
                    
                    # Reconstruct TrainingEpisode
                    ep_dict['reward_signal'] = reward_signal
                    episode = TrainingEpisode(**ep_dict)
                    self.episodes.append(episode)
                
                logger.info(f"Loaded {len(self.episodes)} training episodes from disk")
            
        except Exception as e:
            logger.error(f"Failed to load training state: {e}")

    def get_agent_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of agent performance for monitoring."""
        
        if not self.training_metrics:
            return {"status": "no_training_data"}
        
        summary = {
            "status": "active",
            "total_episodes": self.training_metrics.episode_count,
            "overall_performance": {
                "average_reward": self.training_metrics.average_reward,
                "improvement_rate": self.training_metrics.improvement_rate,
                "convergence_score": self.training_metrics.convergence_score,
            },
            "agent_breakdown": self.training_metrics.agent_performance,
            "recommendations": self._generate_training_recommendations()
        }
        
        return summary

    def _generate_training_recommendations(self) -> List[str]:
        """Generate recommendations based on training performance."""
        
        recommendations = []
        
        if not self.training_metrics:
            return ["Insufficient training data for recommendations"]
        
        # Check overall performance
        if self.training_metrics.average_reward < 0.3:
            recommendations.append("Overall performance is low - consider adjusting reward parameters")
        
        if self.training_metrics.improvement_rate < 0.05:
            recommendations.append("Learning rate appears slow - consider increasing exploration")
        
        if self.training_metrics.convergence_score > 0.8:
            recommendations.append("Training may be converging - consider adding new challenges")
        
        # Check agent-specific performance
        for agent_type, perf in self.training_metrics.agent_performance.items():
            if perf['average_reward'] < 0.2:
                recommendations.append(f"{agent_type} agent underperforming - needs attention")
            elif perf['average_reward'] > 0.8:
                recommendations.append(f"{agent_type} agent performing well - good candidate for knowledge transfer")
        
        if not recommendations:
            recommendations.append("Training is progressing normally")
        
        return recommendations

async def create_training_loop(backend_url: str = "http://localhost:8000") -> RLTrainingLoop:
    """Factory function to create and initialize a training loop."""
    
    training_loop = RLTrainingLoop(backend_url)
    await training_loop.load_training_state()
    return training_loop