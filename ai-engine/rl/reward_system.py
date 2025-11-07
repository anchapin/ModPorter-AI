"""
Reward Signal Generation System for Reinforcement Learning
Converts quality assessments and user feedback into training signals.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
from .quality_scorer import QualityMetrics, ConversionQualityScorer

logger = logging.getLogger(__name__)

@dataclass
class RewardSignal:
    """Container for reward signals used in RL training"""
    job_id: str
    agent_type: str
    action_taken: str
    base_reward: float
    quality_bonus: float
    user_feedback_bonus: float
    time_penalty: float
    total_reward: float
    
    # Context information
    quality_metrics: Optional[Dict[str, Any]]
    user_feedback: Optional[Dict[str, Any]]
    conversion_metadata: Optional[Dict[str, Any]]
    
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission."""
        return asdict(self)

class RewardSignalGenerator:
    """
    Generates reward signals for RL training based on conversion outcomes.
    
    Combines multiple signal sources:
    - Automated quality assessment
    - User feedback (thumbs up/down, comments)
    - Conversion success/failure
    - Performance metrics (time, resource usage)
    """
    
    def __init__(self):
        self.quality_scorer = ConversionQualityScorer()
        
        # Reward parameters
        self.reward_config = {
            'base_success_reward': 1.0,
            'base_failure_penalty': -1.0,
            'quality_weight': 2.0,
            'user_feedback_weight': 1.5,
            'time_penalty_factor': 0.1,
            'max_time_threshold': 300.0,  # 5 minutes
            'min_quality_threshold': 0.5,
        }
        
        # Agent-specific reward modifiers
        self.agent_modifiers = {
            'java_analyzer': {
                'quality_weight_multiplier': 1.2,  # Analyzer affects quality heavily
                'completeness_emphasis': 1.5,
            },
            'conversion_planner': {
                'structure_emphasis': 1.3,
                'performance_emphasis': 1.2,
            },
            'asset_converter': {
                'asset_quality_emphasis': 2.0,
                'visual_quality_emphasis': 1.5,
            },
            'behavior_translator': {
                'correctness_emphasis': 1.8,
                'compatibility_emphasis': 1.4,
            },
            'qa_validator': {
                'error_detection_emphasis': 2.0,
                'completeness_emphasis': 1.3,
            }
        }

    def generate_reward_signal(
        self,
        job_id: str,
        agent_type: str,
        action_taken: str,
        original_mod_path: str,
        converted_addon_path: str,
        conversion_metadata: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None,
        quality_metrics: Optional[QualityMetrics] = None
    ) -> RewardSignal:
        """
        Generate a comprehensive reward signal for an agent action.
        
        Args:
            job_id: Unique identifier for the conversion job
            agent_type: Type of agent that took the action
            action_taken: Description of the action performed
            original_mod_path: Path to original mod file
            converted_addon_path: Path to converted addon
            conversion_metadata: Metadata from conversion process
            user_feedback: Optional user feedback data
            quality_metrics: Pre-computed quality metrics (optional)
            
        Returns:
            RewardSignal containing all reward components
        """
        
        logger.info(f"Generating reward signal for job {job_id}, agent {agent_type}")
        
        # Get quality metrics if not provided
        if quality_metrics is None:
            quality_metrics = self.quality_scorer.assess_conversion_quality(
                original_mod_path=original_mod_path,
                converted_addon_path=converted_addon_path,
                conversion_metadata=conversion_metadata,
                user_feedback=user_feedback
            )
        
        # Calculate reward components
        base_reward = self._calculate_base_reward(conversion_metadata, quality_metrics)
        quality_bonus = self._calculate_quality_bonus(quality_metrics, agent_type)
        user_feedback_bonus = self._calculate_user_feedback_bonus(user_feedback)
        time_penalty = self._calculate_time_penalty(conversion_metadata)
        
        # Calculate total reward
        total_reward = base_reward + quality_bonus + user_feedback_bonus - time_penalty
        
        # Apply agent-specific modifiers
        total_reward = self._apply_agent_modifiers(
            total_reward, agent_type, quality_metrics, conversion_metadata
        )
        
        # Create reward signal
        reward_signal = RewardSignal(
            job_id=job_id,
            agent_type=agent_type,
            action_taken=action_taken,
            base_reward=base_reward,
            quality_bonus=quality_bonus,
            user_feedback_bonus=user_feedback_bonus,
            time_penalty=time_penalty,
            total_reward=total_reward,
            quality_metrics=asdict(quality_metrics) if quality_metrics else None,
            user_feedback=user_feedback,
            conversion_metadata=conversion_metadata,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Reward signal generated: {total_reward:.3f} "
                   f"(base: {base_reward:.3f}, quality: {quality_bonus:.3f}, "
                   f"feedback: {user_feedback_bonus:.3f}, time: -{time_penalty:.3f})")
        
        return reward_signal

    def _calculate_base_reward(
        self, 
        conversion_metadata: Dict[str, Any], 
        quality_metrics: QualityMetrics
    ) -> float:
        """Calculate base reward based on conversion success."""
        
        # Check if conversion completed successfully
        status = conversion_metadata.get('status', 'failed')
        
        if status == 'completed':
            # Base success reward, scaled by minimum quality threshold
            if quality_metrics.overall_score >= self.reward_config['min_quality_threshold']:
                return self.reward_config['base_success_reward']
            else:
                # Partial reward for completed but low-quality conversions
                return self.reward_config['base_success_reward'] * 0.3
        else:
            # Penalty for failed conversions
            return self.reward_config['base_failure_penalty']

    def _calculate_quality_bonus(
        self, 
        quality_metrics: QualityMetrics, 
        agent_type: str
    ) -> float:
        """Calculate bonus based on quality assessment."""
        
        if not quality_metrics:
            return 0.0
        
        # Base quality bonus
        quality_bonus = (quality_metrics.overall_score - 0.5) * self.reward_config['quality_weight']
        
        # Agent-specific quality emphasis
        agent_config = self.agent_modifiers.get(agent_type, {})
        
        if agent_type == 'java_analyzer':
            # Analyzer gets bonus for completeness and correct analysis
            completeness_bonus = (quality_metrics.completeness_score - 0.5) * \
                               agent_config.get('completeness_emphasis', 1.0)
            quality_bonus += completeness_bonus
            
        elif agent_type == 'asset_converter':
            # Asset converter gets bonus for asset quality
            asset_bonus = (quality_metrics.asset_conversion_score - 0.5) * \
                         agent_config.get('asset_quality_emphasis', 1.0)
            quality_bonus += asset_bonus
            
        elif agent_type == 'behavior_translator':
            # Behavior translator gets bonus for correctness
            correctness_bonus = (quality_metrics.correctness_score - 0.5) * \
                               agent_config.get('correctness_emphasis', 1.0)
            quality_bonus += correctness_bonus
            
        elif agent_type == 'qa_validator':
            # QA validator gets bonus for error detection and completeness
            error_detection_bonus = 0.0
            if not quality_metrics.critical_errors:
                error_detection_bonus = 0.5  # Bonus for no critical errors
            elif len(quality_metrics.critical_errors) < 3:
                error_detection_bonus = 0.2  # Small bonus for few errors
                
            quality_bonus += error_detection_bonus * \
                           agent_config.get('error_detection_emphasis', 1.0)
        
        return max(0.0, quality_bonus)  # No negative quality bonus

    def _calculate_user_feedback_bonus(self, user_feedback: Optional[Dict[str, Any]]) -> float:
        """Calculate bonus/penalty based on user feedback."""
        
        if not user_feedback:
            return 0.0
        
        feedback_type = user_feedback.get('feedback_type', '')
        feedback_weight = self.reward_config['user_feedback_weight']
        
        if feedback_type == 'thumbs_up':
            bonus = 1.0 * feedback_weight
        elif feedback_type == 'thumbs_down':
            bonus = -0.5 * feedback_weight  # Penalty for negative feedback
        else:
            bonus = 0.0
        
        # Additional bonus for helpful comments
        comment = user_feedback.get('comment', '')
        if comment and len(comment.strip()) > 10:
            # Small bonus for providing detailed feedback
            bonus += 0.1 * feedback_weight
        
        return bonus

    def _calculate_time_penalty(self, conversion_metadata: Dict[str, Any]) -> float:
        """Calculate penalty for slow conversions."""
        
        processing_time = conversion_metadata.get('processing_time_seconds', 0.0)
        max_time = self.reward_config['max_time_threshold']
        penalty_factor = self.reward_config['time_penalty_factor']
        
        if processing_time <= max_time:
            return 0.0
        
        # Linear penalty for time over threshold
        excess_time = processing_time - max_time
        penalty = (excess_time / max_time) * penalty_factor
        
        return min(1.0, penalty)  # Cap penalty at 1.0

    def _apply_agent_modifiers(
        self,
        base_reward: float,
        agent_type: str,
        quality_metrics: QualityMetrics,
        conversion_metadata: Dict[str, Any]
    ) -> float:
        """Apply agent-specific reward modifiers."""
        
        agent_config = self.agent_modifiers.get(agent_type, {})
        modified_reward = base_reward
        
        # Apply quality weight multiplier
        quality_multiplier = agent_config.get('quality_weight_multiplier', 1.0)
        if quality_multiplier != 1.0:
            quality_component = (quality_metrics.overall_score - 0.5) * 0.5
            modified_reward += quality_component * (quality_multiplier - 1.0)
        
        # Apply performance emphasis for conversion planner
        if agent_type == 'conversion_planner':
            performance_emphasis = agent_config.get('performance_emphasis', 1.0)
            performance_component = (quality_metrics.performance_score - 0.5) * 0.3
            modified_reward += performance_component * (performance_emphasis - 1.0)
        
        return modified_reward

    def generate_batch_rewards(
        self,
        conversion_results: List[Dict[str, Any]]
    ) -> List[RewardSignal]:
        """Generate reward signals for a batch of conversions."""
        
        reward_signals = []
        
        for result in conversion_results:
            try:
                reward_signal = self.generate_reward_signal(
                    job_id=result['job_id'],
                    agent_type=result['agent_type'],
                    action_taken=result['action_taken'],
                    original_mod_path=result['original_mod_path'],
                    converted_addon_path=result['converted_addon_path'],
                    conversion_metadata=result['conversion_metadata'],
                    user_feedback=result.get('user_feedback'),
                    quality_metrics=result.get('quality_metrics')
                )
                reward_signals.append(reward_signal)
                
            except Exception as e:
                logger.error(f"Failed to generate reward for job {result.get('job_id')}: {e}")
                
        return reward_signals

    def analyze_reward_trends(
        self, 
        reward_history: List[RewardSignal]
    ) -> Dict[str, Any]:
        """Analyze trends in reward signals for optimization insights."""
        
        if not reward_history:
            return {}
        
        # Group by agent type
        agent_rewards = {}
        for signal in reward_history:
            if signal.agent_type not in agent_rewards:
                agent_rewards[signal.agent_type] = []
            agent_rewards[signal.agent_type].append(signal.total_reward)
        
        analysis = {
            'total_signals': len(reward_history),
            'average_reward': np.mean([s.total_reward for s in reward_history]),
            'reward_std': np.std([s.total_reward for s in reward_history]),
            'agent_performance': {}
        }
        
        # Per-agent analysis
        for agent_type, rewards in agent_rewards.items():
            analysis['agent_performance'][agent_type] = {
                'count': len(rewards),
                'average_reward': np.mean(rewards),
                'std_reward': np.std(rewards),
                'improvement_trend': self._calculate_improvement_trend(rewards)
            }
        
        # Identify best and worst performing agents
        if analysis['agent_performance']:
            best_agent = max(analysis['agent_performance'].items(), 
                           key=lambda x: x[1]['average_reward'])
            worst_agent = min(analysis['agent_performance'].items(), 
                            key=lambda x: x[1]['average_reward'])
            
            analysis['best_performing_agent'] = {
                'type': best_agent[0],
                'average_reward': best_agent[1]['average_reward']
            }
            analysis['worst_performing_agent'] = {
                'type': worst_agent[0],
                'average_reward': worst_agent[1]['average_reward']
            }
        
        return analysis

    def _calculate_improvement_trend(self, rewards: List[float]) -> str:
        """Calculate if an agent's performance is improving, declining, or stable."""
        
        if len(rewards) < 5:
            return "insufficient_data"
        
        # Simple linear trend analysis
        x = np.arange(len(rewards))
        slope = np.polyfit(x, rewards, 1)[0]
        
        if slope > 0.05:
            return "improving"
        elif slope < -0.05:
            return "declining"
        else:
            return "stable"

    def save_reward_signals(
        self, 
        reward_signals: List[RewardSignal], 
        output_path: str
    ) -> None:
        """Save reward signals to JSON file for training data."""
        
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'total_signals': len(reward_signals),
                'signals': [signal.to_dict() for signal in reward_signals]
            }
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved {len(reward_signals)} reward signals to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save reward signals: {e}")

def create_reward_generator() -> RewardSignalGenerator:
    """Factory function to create a reward signal generator."""
    return RewardSignalGenerator()