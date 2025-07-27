"""
Agent Performance Tracking and Optimization System
Monitors individual agent performance and provides optimization recommendations.
"""

import logging
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import statistics

from .reward_system import RewardSignal
from .training_loop import TrainingEpisode

logger = logging.getLogger(__name__)

@dataclass
class AgentPerformanceMetrics:
    """Comprehensive performance metrics for a single agent"""
    agent_type: str
    total_episodes: int
    success_rate: float
    average_reward: float
    reward_variance: float
    improvement_trend: str
    convergence_score: float
    
    # Detailed performance breakdown
    quality_scores: Dict[str, float]
    processing_speeds: List[float]
    error_rates: Dict[str, float]
    
    # Temporal analysis
    recent_performance: float
    performance_stability: float
    learning_velocity: float
    
    # Recommendations
    optimization_recommendations: List[str]
    training_priority: str
    
    last_updated: str

@dataclass
class AgentComparisonReport:
    """Comparative analysis between different agents"""
    comparison_timestamp: str
    agents_compared: List[str]
    performance_rankings: Dict[str, int]
    relative_strengths: Dict[str, List[str]]
    relative_weaknesses: Dict[str, List[str]]
    transfer_learning_opportunities: List[Dict[str, str]]
    ensemble_recommendations: List[str]

class AgentPerformanceOptimizer:
    """
    Monitors and optimizes individual AI agent performance.
    
    Provides:
    - Real-time performance tracking
    - Trend analysis and predictions
    - Optimization recommendations
    - A/B testing support
    - Transfer learning identification
    """
    
    def __init__(self):
        self.performance_history: Dict[str, List[AgentPerformanceMetrics]] = {}
        self.episode_database: Dict[str, List[TrainingEpisode]] = {}
        
        # Performance thresholds
        self.performance_thresholds = {
            'excellent': 0.85,
            'good': 0.70,
            'acceptable': 0.55,
            'poor': 0.40,
            'critical': 0.25
        }
        
        # Optimization parameters
        self.optimization_config = {
            'min_episodes_for_analysis': 10,
            'trend_analysis_window': 20,
            'stability_threshold': 0.15,
            'improvement_threshold': 0.05,
            'convergence_threshold': 0.02,
        }
        
        # File paths
        self.metrics_dir = Path("agent_metrics")
        self.metrics_dir.mkdir(exist_ok=True)

    def track_agent_performance(
        self, 
        agent_type: str, 
        episodes: List[TrainingEpisode]
    ) -> AgentPerformanceMetrics:
        """
        Analyze and track performance for a specific agent type.
        
        Args:
            agent_type: Type of agent to analyze
            episodes: List of training episodes for this agent
            
        Returns:
            Comprehensive performance metrics
        """
        
        logger.info(f"Analyzing performance for {agent_type} with {len(episodes)} episodes")
        
        if agent_type not in self.episode_database:
            self.episode_database[agent_type] = []
        
        # Add new episodes
        self.episode_database[agent_type].extend(episodes)
        
        # Calculate comprehensive metrics
        metrics = self._calculate_comprehensive_metrics(agent_type)
        
        # Store metrics history
        if agent_type not in self.performance_history:
            self.performance_history[agent_type] = []
        self.performance_history[agent_type].append(metrics)
        
        # Save metrics to disk
        self._save_agent_metrics(agent_type, metrics)
        
        logger.info(f"Performance analysis completed for {agent_type}. "
                   f"Average reward: {metrics.average_reward:.3f}, "
                   f"Success rate: {metrics.success_rate:.1%}")
        
        return metrics

    def _calculate_comprehensive_metrics(self, agent_type: str) -> AgentPerformanceMetrics:
        """Calculate comprehensive performance metrics for an agent."""
        
        episodes = self.episode_database[agent_type]
        
        if len(episodes) < self.optimization_config['min_episodes_for_analysis']:
            return self._create_minimal_metrics(agent_type, episodes)
        
        # Basic statistics
        rewards = [ep.reward_signal.total_reward for ep in episodes]
        quality_scores = []
        processing_times = []
        
        for ep in episodes:
            if ep.reward_signal.quality_metrics:
                quality_scores.append(ep.reward_signal.quality_metrics.get('overall_score', 0.0))
            
            # Extract processing time from metadata
            metadata = ep.reward_signal.conversion_metadata or {}
            proc_time = metadata.get('processing_time_seconds', 0.0)
            if proc_time > 0:
                processing_times.append(proc_time)
        
        # Calculate core metrics
        average_reward = statistics.mean(rewards)
        reward_variance = statistics.variance(rewards) if len(rewards) > 1 else 0.0
        success_rate = len([r for r in rewards if r > 0]) / len(rewards)
        
        # Quality score breakdown
        quality_breakdown = self._analyze_quality_breakdown(episodes)
        
        # Error rate analysis
        error_rates = self._analyze_error_rates(episodes)
        
        # Temporal analysis
        improvement_trend = self._calculate_improvement_trend(rewards)
        recent_performance = self._calculate_recent_performance(rewards)
        performance_stability = self._calculate_stability(rewards)
        learning_velocity = self._calculate_learning_velocity(rewards)
        convergence_score = self._calculate_convergence_score(rewards)
        
        # Generate optimization recommendations
        recommendations = self._generate_optimization_recommendations(
            agent_type, rewards, quality_breakdown, error_rates, improvement_trend
        )
        
        # Determine training priority
        training_priority = self._determine_training_priority(
            average_reward, improvement_trend, success_rate
        )
        
        return AgentPerformanceMetrics(
            agent_type=agent_type,
            total_episodes=len(episodes),
            success_rate=success_rate,
            average_reward=average_reward,
            reward_variance=reward_variance,
            improvement_trend=improvement_trend,
            convergence_score=convergence_score,
            quality_scores=quality_breakdown,
            processing_speeds=processing_times,
            error_rates=error_rates,
            recent_performance=recent_performance,
            performance_stability=performance_stability,
            learning_velocity=learning_velocity,
            optimization_recommendations=recommendations,
            training_priority=training_priority,
            last_updated=datetime.now().isoformat()
        )

    def _create_minimal_metrics(
        self, 
        agent_type: str, 
        episodes: List[TrainingEpisode]
    ) -> AgentPerformanceMetrics:
        """Create minimal metrics when insufficient data is available."""
        
        rewards = [ep.reward_signal.total_reward for ep in episodes] if episodes else [0.0]
        
        return AgentPerformanceMetrics(
            agent_type=agent_type,
            total_episodes=len(episodes),
            success_rate=0.0,
            average_reward=statistics.mean(rewards),
            reward_variance=0.0,
            improvement_trend="insufficient_data",
            convergence_score=0.0,
            quality_scores={},
            processing_speeds=[],
            error_rates={},
            recent_performance=0.0,
            performance_stability=0.0,
            learning_velocity=0.0,
            optimization_recommendations=["Insufficient data for analysis - need more episodes"],
            training_priority="low",
            last_updated=datetime.now().isoformat()
        )

    def _analyze_quality_breakdown(self, episodes: List[TrainingEpisode]) -> Dict[str, float]:
        """Analyze quality score breakdown across different dimensions."""
        
        quality_aspects = {
            'completeness': [],
            'correctness': [],
            'performance': [],
            'compatibility': [],
            'user_experience': []
        }
        
        for episode in episodes:
            if episode.reward_signal.quality_metrics:
                qm = episode.reward_signal.quality_metrics
                quality_aspects['completeness'].append(qm.get('completeness_score', 0.0))
                quality_aspects['correctness'].append(qm.get('correctness_score', 0.0))
                quality_aspects['performance'].append(qm.get('performance_score', 0.0))
                quality_aspects['compatibility'].append(qm.get('compatibility_score', 0.0))
                quality_aspects['user_experience'].append(qm.get('user_experience_score', 0.0))
        
        # Calculate averages
        breakdown = {}
        for aspect, scores in quality_aspects.items():
            if scores:
                breakdown[aspect] = statistics.mean(scores)
            else:
                breakdown[aspect] = 0.0
        
        return breakdown

    def _analyze_error_rates(self, episodes: List[TrainingEpisode]) -> Dict[str, float]:
        """Analyze error patterns and rates."""
        
        total_episodes = len(episodes)
        error_counts = {
            'critical_errors': 0,
            'conversion_failures': 0,
            'quality_failures': 0,
            'timeout_errors': 0
        }
        
        for episode in episodes:
            reward = episode.reward_signal.total_reward
            metadata = episode.reward_signal.conversion_metadata or {}
            
            # Count different error types
            if reward < -0.5:
                error_counts['critical_errors'] += 1
            
            if metadata.get('status') == 'failed':
                error_counts['conversion_failures'] += 1
            
            if episode.reward_signal.quality_metrics:
                overall_quality = episode.reward_signal.quality_metrics.get('overall_score', 0.0)
                if overall_quality < 0.3:
                    error_counts['quality_failures'] += 1
            
            processing_time = metadata.get('processing_time_seconds', 0.0)
            if processing_time > 300:  # 5 minutes threshold
                error_counts['timeout_errors'] += 1
        
        # Convert to rates
        error_rates = {}
        for error_type, count in error_counts.items():
            error_rates[error_type] = count / total_episodes if total_episodes > 0 else 0.0
        
        return error_rates

    def _calculate_improvement_trend(self, rewards: List[float]) -> str:
        """Calculate the improvement trend over time."""
        
        if len(rewards) < 5:
            return "insufficient_data"
        
        # Use linear regression to determine trend
        x = np.arange(len(rewards))
        slope = np.polyfit(x, rewards, 1)[0]
        
        if slope > self.optimization_config['improvement_threshold']:
            return "improving"
        elif slope < -self.optimization_config['improvement_threshold']:
            return "declining"
        else:
            return "stable"

    def _calculate_recent_performance(self, rewards: List[float]) -> float:
        """Calculate recent performance (last 25% of episodes)."""
        
        if len(rewards) < 4:
            return statistics.mean(rewards) if rewards else 0.0
        
        recent_count = max(1, len(rewards) // 4)
        recent_rewards = rewards[-recent_count:]
        return statistics.mean(recent_rewards)

    def _calculate_stability(self, rewards: List[float]) -> float:
        """Calculate performance stability (inverse of coefficient of variation)."""
        
        if len(rewards) < 2:
            return 0.0
        
        mean_reward = statistics.mean(rewards)
        if mean_reward == 0:
            return 0.0
        
        std_dev = statistics.stdev(rewards)
        cv = std_dev / abs(mean_reward)
        
        # Convert to stability score (0-1, higher is more stable)
        stability = max(0.0, 1.0 - cv)
        return stability

    def _calculate_learning_velocity(self, rewards: List[float]) -> float:
        """Calculate how quickly the agent is learning (rate of improvement)."""
        
        if len(rewards) < 10:
            return 0.0
        
        # Compare first and second halves
        mid_point = len(rewards) // 2
        first_half = rewards[:mid_point]
        second_half = rewards[mid_point:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        # Calculate learning velocity as improvement per episode
        episodes_span = len(second_half)
        velocity = (second_avg - first_avg) / episodes_span if episodes_span > 0 else 0.0
        
        return velocity

    def _calculate_convergence_score(self, rewards: List[float]) -> float:
        """Calculate how close the agent is to convergence."""
        
        if len(rewards) < self.optimization_config['trend_analysis_window']:
            return 0.0
        
        # Look at recent rewards variance
        recent_rewards = rewards[-self.optimization_config['trend_analysis_window']:]
        
        if len(recent_rewards) < 2:
            return 0.0
        
        # Calculate coefficient of variation for recent performance
        mean_recent = statistics.mean(recent_rewards)
        if mean_recent == 0:
            return 0.0
        
        std_recent = statistics.stdev(recent_rewards)
        cv = std_recent / abs(mean_recent)
        
        # Convert to convergence score (lower variance = higher convergence)
        convergence = max(0.0, 1.0 - cv / self.optimization_config['convergence_threshold'])
        return min(1.0, convergence)

    def _generate_optimization_recommendations(
        self,
        agent_type: str,
        rewards: List[float],
        quality_breakdown: Dict[str, float],
        error_rates: Dict[str, float],
        improvement_trend: str
    ) -> List[str]:
        """Generate specific optimization recommendations for the agent."""
        
        recommendations = []
        avg_reward = statistics.mean(rewards) if rewards else 0.0
        
        # Performance level recommendations
        if avg_reward < self.performance_thresholds['poor']:
            recommendations.append("Critical: Agent performance is below acceptable threshold")
            recommendations.append("Recommend: Immediate model retraining with enhanced reward signals")
        elif avg_reward < self.performance_thresholds['acceptable']:
            recommendations.append("Warning: Agent performance needs improvement")
            recommendations.append("Recommend: Increase training data variety and feedback quality")
        
        # Trend-based recommendations
        if improvement_trend == "declining":
            recommendations.append("Alert: Performance is declining - investigate for overfitting")
            recommendations.append("Recommend: Reduce learning rate or add regularization")
        elif improvement_trend == "stable" and avg_reward < self.performance_thresholds['good']:
            recommendations.append("Suggest: Performance has plateaued - try new training strategies")
        
        # Quality-specific recommendations
        weak_areas = [area for area, score in quality_breakdown.items() if score < 0.6]
        if weak_areas:
            recommendations.append(f"Focus on: {', '.join(weak_areas)} quality improvement")
        
        # Error-specific recommendations
        if error_rates.get('critical_errors', 0) > 0.1:
            recommendations.append("Critical: High error rate - review training data quality")
        
        if error_rates.get('timeout_errors', 0) > 0.05:
            recommendations.append("Performance: Optimize for faster processing times")
        
        # Agent-specific recommendations
        agent_specific = self._get_agent_specific_recommendations(agent_type, quality_breakdown)
        recommendations.extend(agent_specific)
        
        return recommendations if recommendations else ["Performance is within normal parameters"]

    def _get_agent_specific_recommendations(
        self, 
        agent_type: str, 
        quality_breakdown: Dict[str, float]
    ) -> List[str]:
        """Get recommendations specific to the agent type."""
        
        recommendations = []
        
        if agent_type == 'java_analyzer':
            if quality_breakdown.get('completeness', 0) < 0.7:
                recommendations.append("Java Analyzer: Improve parsing accuracy for complex mod structures")
        
        elif agent_type == 'asset_converter':
            if quality_breakdown.get('user_experience', 0) < 0.6:
                recommendations.append("Asset Converter: Focus on texture quality and visual fidelity")
        
        elif agent_type == 'behavior_translator':
            if quality_breakdown.get('correctness', 0) < 0.7:
                recommendations.append("Behavior Translator: Improve logic conversion accuracy")
        
        elif agent_type == 'conversion_planner':
            if quality_breakdown.get('performance', 0) < 0.6:
                recommendations.append("Conversion Planner: Optimize planning algorithms for efficiency")
        
        elif agent_type == 'qa_validator':
            if quality_breakdown.get('compatibility', 0) < 0.7:
                recommendations.append("QA Validator: Enhance compatibility checking mechanisms")
        
        return recommendations

    def _determine_training_priority(
        self, 
        average_reward: float, 
        improvement_trend: str, 
        success_rate: float
    ) -> str:
        """Determine training priority level for the agent."""
        
        # Critical priority
        if (average_reward < self.performance_thresholds['critical'] or 
            success_rate < 0.3 or 
            improvement_trend == "declining"):
            return "critical"
        
        # High priority
        if (average_reward < self.performance_thresholds['poor'] or 
            success_rate < 0.5):
            return "high"
        
        # Medium priority
        if (average_reward < self.performance_thresholds['good'] or 
            improvement_trend == "stable"):
            return "medium"
        
        # Low priority
        return "low"

    def compare_agents(self, agent_types: List[str]) -> AgentComparisonReport:
        """Generate comparative analysis between different agents."""
        
        logger.info(f"Comparing performance across {len(agent_types)} agent types")
        
        # Get latest metrics for each agent
        agent_metrics = {}
        for agent_type in agent_types:
            if (agent_type in self.performance_history and 
                self.performance_history[agent_type]):
                agent_metrics[agent_type] = self.performance_history[agent_type][-1]
        
        if len(agent_metrics) < 2:
            logger.warning("Insufficient agents for comparison")
            return self._create_empty_comparison_report(agent_types)
        
        # Calculate performance rankings
        rankings = self._calculate_performance_rankings(agent_metrics)
        
        # Identify strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(agent_metrics)
        
        # Find transfer learning opportunities
        transfer_opportunities = self._find_transfer_learning_opportunities(agent_metrics)
        
        # Generate ensemble recommendations
        ensemble_recommendations = self._generate_ensemble_recommendations(agent_metrics)
        
        comparison_report = AgentComparisonReport(
            comparison_timestamp=datetime.now().isoformat(),
            agents_compared=list(agent_metrics.keys()),
            performance_rankings=rankings,
            relative_strengths=strengths,
            relative_weaknesses=weaknesses,
            transfer_learning_opportunities=transfer_opportunities,
            ensemble_recommendations=ensemble_recommendations
        )
        
        # Save comparison report
        self._save_comparison_report(comparison_report)
        
        return comparison_report

    def _calculate_performance_rankings(
        self, 
        agent_metrics: Dict[str, AgentPerformanceMetrics]
    ) -> Dict[str, int]:
        """Calculate performance rankings across agents."""
        
        # Sort agents by average reward
        sorted_agents = sorted(
            agent_metrics.items(),
            key=lambda x: x[1].average_reward,
            reverse=True
        )
        
        rankings = {}
        for rank, (agent_type, _) in enumerate(sorted_agents, 1):
            rankings[agent_type] = rank
        
        return rankings

    def _identify_strengths_weaknesses(
        self, 
        agent_metrics: Dict[str, AgentPerformanceMetrics]
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """Identify relative strengths and weaknesses of each agent."""
        
        strengths = {}
        weaknesses = {}
        
        # Calculate average performance across all agents for each metric
        all_quality_scores = {}
        for agent_type, metrics in agent_metrics.items():
            for aspect, score in metrics.quality_scores.items():
                if aspect not in all_quality_scores:
                    all_quality_scores[aspect] = []
                all_quality_scores[aspect].append(score)
        
        # Calculate averages
        avg_quality_scores = {}
        for aspect, scores in all_quality_scores.items():
            avg_quality_scores[aspect] = statistics.mean(scores) if scores else 0.0
        
        # Identify strengths and weaknesses for each agent
        for agent_type, metrics in agent_metrics.items():
            agent_strengths = []
            agent_weaknesses = []
            
            # Compare quality scores
            for aspect, score in metrics.quality_scores.items():
                avg_score = avg_quality_scores.get(aspect, 0.0)
                if score > avg_score + 0.1:  # 10% above average
                    agent_strengths.append(f"Excellent {aspect} performance")
                elif score < avg_score - 0.1:  # 10% below average
                    agent_weaknesses.append(f"Poor {aspect} performance")
            
            # Compare other metrics
            avg_reward = statistics.mean([m.average_reward for m in agent_metrics.values()])
            if metrics.average_reward > avg_reward + 0.1:
                agent_strengths.append("High overall reward performance")
            elif metrics.average_reward < avg_reward - 0.1:
                agent_weaknesses.append("Low overall reward performance")
            
            # Learning characteristics
            if metrics.improvement_trend == "improving":
                agent_strengths.append("Positive learning trend")
            elif metrics.improvement_trend == "declining":
                agent_weaknesses.append("Declining performance trend")
            
            if metrics.performance_stability > 0.8:
                agent_strengths.append("High performance stability")
            elif metrics.performance_stability < 0.5:
                agent_weaknesses.append("Unstable performance")
            
            strengths[agent_type] = agent_strengths if agent_strengths else ["No significant strengths identified"]
            weaknesses[agent_type] = agent_weaknesses if agent_weaknesses else ["No significant weaknesses identified"]
        
        return strengths, weaknesses

    def _find_transfer_learning_opportunities(
        self, 
        agent_metrics: Dict[str, AgentPerformanceMetrics]
    ) -> List[Dict[str, str]]:
        """Identify opportunities for knowledge transfer between agents."""
        
        opportunities = []
        
        # Find high-performing agents
        high_performers = [
            agent_type for agent_type, metrics in agent_metrics.items()
            if metrics.average_reward > self.performance_thresholds['good']
        ]
        
        # Find low-performing agents
        low_performers = [
            agent_type for agent_type, metrics in agent_metrics.items()
            if metrics.average_reward < self.performance_thresholds['acceptable']
        ]
        
        # Suggest transfer opportunities
        for high_performer in high_performers:
            for low_performer in low_performers:
                # Find specific areas where transfer could help
                high_metrics = agent_metrics[high_performer]
                low_metrics = agent_metrics[low_performer]
                
                for aspect, high_score in high_metrics.quality_scores.items():
                    low_score = low_metrics.quality_scores.get(aspect, 0.0)
                    if high_score > low_score + 0.2:  # Significant difference
                        opportunities.append({
                            'source_agent': high_performer,
                            'target_agent': low_performer,
                            'knowledge_area': aspect,
                            'improvement_potential': f"{((high_score - low_score) * 100):.1f}%"
                        })
        
        return opportunities

    def _generate_ensemble_recommendations(
        self, 
        agent_metrics: Dict[str, AgentPerformanceMetrics]
    ) -> List[str]:
        """Generate recommendations for ensemble approaches."""
        
        recommendations = []
        
        # Identify complementary strengths
        strong_areas = {}
        for agent_type, metrics in agent_metrics.items():
            for aspect, score in metrics.quality_scores.items():
                if score > 0.7:  # Strong performance
                    if aspect not in strong_areas:
                        strong_areas[aspect] = []
                    strong_areas[aspect].append(agent_type)
        
        # Suggest ensemble strategies
        if len(strong_areas) > 1:
            recommendations.append("Consider ensemble approach leveraging different agent strengths")
            
            for aspect, agents in strong_areas.items():
                if len(agents) == 1:
                    recommendations.append(f"Use {agents[0]} for {aspect}-critical tasks")
                else:
                    recommendations.append(f"Combine {', '.join(agents)} for {aspect} tasks")
        
        # Suggest parallel processing
        fast_agents = [
            agent_type for agent_type, metrics in agent_metrics.items()
            if (metrics.processing_speeds and statistics.mean(metrics.processing_speeds) < 60)
        ]
        
        if fast_agents:
            recommendations.append(f"Use {', '.join(fast_agents)} for time-sensitive processing")
        
        return recommendations if recommendations else ["No specific ensemble recommendations at this time"]

    def _create_empty_comparison_report(self, agent_types: List[str]) -> AgentComparisonReport:
        """Create an empty comparison report when insufficient data is available."""
        
        return AgentComparisonReport(
            comparison_timestamp=datetime.now().isoformat(),
            agents_compared=agent_types,
            performance_rankings={},
            relative_strengths={},
            relative_weaknesses={},
            transfer_learning_opportunities=[],
            ensemble_recommendations=["Insufficient data for comparison"]
        )

    def _save_agent_metrics(self, agent_type: str, metrics: AgentPerformanceMetrics) -> None:
        """Save agent metrics to disk."""
        
        try:
            metrics_file = self.metrics_dir / f"{agent_type}_metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump(asdict(metrics), f, indent=2)
            
            logger.debug(f"Saved metrics for {agent_type} to {metrics_file}")
            
        except Exception as e:
            logger.error(f"Failed to save metrics for {agent_type}: {e}")

    def _save_comparison_report(self, report: AgentComparisonReport) -> None:
        """Save comparison report to disk."""
        
        try:
            report_file = self.metrics_dir / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(asdict(report), f, indent=2)
            
            logger.info(f"Saved comparison report to {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to save comparison report: {e}")

    def get_system_wide_metrics(self) -> Dict[str, Any]:
        """Get system-wide performance metrics across all agents."""
        
        all_agents = list(self.performance_history.keys())
        if not all_agents:
            return {"status": "no_agents_tracked"}
        
        # Get latest metrics for all agents
        latest_metrics = {}
        for agent_type in all_agents:
            if self.performance_history[agent_type]:
                latest_metrics[agent_type] = self.performance_history[agent_type][-1]
        
        if not latest_metrics:
            return {"status": "no_recent_metrics"}
        
        # Calculate system-wide statistics
        all_rewards = [metrics.average_reward for metrics in latest_metrics.values()]
        all_success_rates = [metrics.success_rate for metrics in latest_metrics.values()]
        
        system_metrics = {
            "status": "active",
            "total_agents": len(latest_metrics),
            "system_performance": {
                "average_reward": statistics.mean(all_rewards),
                "best_agent_reward": max(all_rewards),
                "worst_agent_reward": min(all_rewards),
                "reward_variance": statistics.variance(all_rewards) if len(all_rewards) > 1 else 0.0,
                "average_success_rate": statistics.mean(all_success_rates),
            },
            "agent_breakdown": {
                agent_type: {
                    "average_reward": metrics.average_reward,
                    "success_rate": metrics.success_rate,
                    "total_episodes": metrics.total_episodes,
                    "training_priority": metrics.training_priority,
                    "improvement_trend": metrics.improvement_trend
                }
                for agent_type, metrics in latest_metrics.items()
            },
            "recommendations": self._generate_system_recommendations(latest_metrics)
        }
        
        return system_metrics

    def _generate_system_recommendations(
        self, 
        latest_metrics: Dict[str, AgentPerformanceMetrics]
    ) -> List[str]:
        """Generate system-wide optimization recommendations."""
        
        recommendations = []
        
        # Identify critical issues
        critical_agents = [
            agent_type for agent_type, metrics in latest_metrics.items()
            if metrics.training_priority == "critical"
        ]
        
        if critical_agents:
            recommendations.append(f"Critical: {', '.join(critical_agents)} require immediate attention")
        
        # Identify best practices to share
        top_performers = [
            agent_type for agent_type, metrics in latest_metrics.items()
            if metrics.average_reward > self.performance_thresholds['excellent']
        ]
        
        if top_performers:
            recommendations.append(f"Share best practices from: {', '.join(top_performers)}")
        
        # Check for system-wide issues
        all_rewards = [metrics.average_reward for metrics in latest_metrics.values()]
        if statistics.mean(all_rewards) < self.performance_thresholds['acceptable']:
            recommendations.append("System-wide performance below threshold - review training data quality")
        
        # Check training balance
        episodes_per_agent = [metrics.total_episodes for metrics in latest_metrics.values()]
        if max(episodes_per_agent) > 2 * min(episodes_per_agent):
            recommendations.append("Unbalanced training data - ensure all agents receive adequate episodes")
        
        return recommendations if recommendations else ["System performance is within normal parameters"]

def create_agent_optimizer() -> AgentPerformanceOptimizer:
    """Factory function to create an agent performance optimizer."""
    return AgentPerformanceOptimizer()