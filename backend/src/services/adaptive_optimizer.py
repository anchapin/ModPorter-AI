"""
Adaptive Optimization Engine

This module provides intelligent, self-learning optimization capabilities
that adapt to system behavior and performance patterns.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from collections import defaultdict, deque
from datetime import datetime
import numpy as np
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.model_selection import train_test_split
from enum import Enum

from .performance_monitor import (
    performance_monitor,
    OptimizationAction,
    MetricsCollector,
)

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Optimization strategy types"""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    ADAPTIVE = "adaptive"


@dataclass
class OptimizationPattern:
    """Learned optimization pattern"""

    pattern_id: str
    conditions: Dict[str, Any]
    actions: List[str]
    success_rate: float
    average_improvement: float
    confidence_score: float
    last_applied: datetime
    application_count: int = 0


@dataclass
class PerformanceProfile:
    """Performance profile for different system states"""

    profile_id: str
    characteristics: Dict[str, float]
    optimal_settings: Dict[str, Any]
    performance_score: float
    stability_score: float
    created_at: datetime


class PatternLearner:
    """Machine learning-based pattern recognition for optimization"""

    def __init__(self):
        self.feature_scaler = StandardScaler()
        self.performance_predictor = RandomForestRegressor(
            n_estimators=100, random_state=42
        )
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.clustering_model = DBSCAN(eps=0.5, min_samples=5)

        self.training_data: List[Dict[str, Any]] = []
        self.patterns: List[OptimizationPattern] = []
        self.profiles: List[PerformanceProfile] = []
        self.is_trained = False

    def add_training_sample(
        self,
        system_state: Dict[str, float],
        action_taken: str,
        performance_before: float,
        performance_after: float,
    ) -> None:
        """Add a training sample for learning"""
        improvement = (
            (performance_before - performance_after) / performance_before * 100
        )

        sample = {
            "system_state": system_state,
            "action": action_taken,
            "improvement": improvement,
            "timestamp": datetime.now(),
        }

        self.training_data.append(sample)

        # Keep training data manageable
        if len(self.training_data) > 10000:
            self.training_data = self.training_data[-5000:]

    def train_models(self) -> bool:
        """Train machine learning models"""
        if len(self.training_data) < 50:
            logger.warning("Insufficient training data for model training")
            return False

        try:
            # Prepare features and labels
            features = []
            labels = []

            for sample in self.training_data[-1000:]:  # Use recent samples
                state_features = [
                    sample["system_state"].get("cpu_percent", 0),
                    sample["system_state"].get("memory_percent", 0),
                    sample["system_state"].get("cache_hit_rate", 0),
                    sample["system_state"].get("queue_length", 0),
                    sample["system_state"].get("active_operations", 0),
                ]
                features.append(state_features)
                labels.append(sample["improvement"])

            features = np.array(features)
            labels = np.array(labels)

            if len(features) < 10:
                return False

            # Train performance predictor
            X_train, X_test, y_train, y_test = train_test_split(
                features, labels, test_size=0.2, random_state=42
            )

            # Scale features
            X_train_scaled = self.feature_scaler.fit_transform(X_train)
            X_test_scaled = self.feature_scaler.transform(X_test)

            self.performance_predictor.fit(X_train_scaled, y_train)

            # Evaluate model
            train_score = self.performance_predictor.score(X_train_scaled, y_train)
            test_score = self.performance_predictor.score(X_test_scaled, y_test)

            logger.info(
                f"Performance predictor trained - Train score: {train_score:.3f}, Test score: {test_score:.3f}"
            )

            # Train anomaly detector
            self.anomaly_detector.fit(X_train_scaled)

            # Train clustering model for pattern recognition
            self.clustering_model.fit(X_train_scaled)

            self.is_trained = True

            # Extract optimization patterns
            self._extract_patterns()

            return True

        except Exception as e:
            logger.error(f"Error training models: {e}")
            return False

    def _extract_patterns(self) -> None:
        """Extract optimization patterns from trained models"""
        if not self.is_trained or len(self.training_data) < 100:
            return

        try:
            # Group similar conditions and identify successful actions
            condition_groups = defaultdict(list)

            for sample in self.training_data[-500:]:
                # Create condition signature
                conditions = tuple(
                    sorted(
                        [(k, round(v, 1)) for k, v in sample["system_state"].items()]
                    )
                )
                condition_groups[conditions].append(sample)

            # Identify patterns in successful optimizations
            for conditions, samples in condition_groups.items():
                if len(samples) < 5:
                    continue

                successful_samples = [s for s in samples if s["improvement"] > 5]

                if len(successful_samples) / len(samples) > 0.7:  # 70% success rate
                    # Identify most successful actions
                    action_counts = defaultdict(list)
                    for s in successful_samples:
                        action_counts[s["action"]].append(s["improvement"])

                    best_actions = []
                    for action, improvements in action_counts.items():
                        if len(improvements) >= 3:
                            avg_improvement = np.mean(improvements)
                            if avg_improvement > 10:  # Significant improvement
                                best_actions.append(action)

                    if best_actions:
                        pattern = OptimizationPattern(
                            pattern_id=f"pattern_{len(self.patterns)}_{int(time.time())}",
                            conditions=dict(conditions),
                            actions=best_actions,
                            success_rate=len(successful_samples) / len(samples),
                            average_improvement=np.mean(
                                [s["improvement"] for s in successful_samples]
                            ),
                            confidence_score=min(1.0, len(successful_samples) / 10),
                            last_applied=datetime.now(),
                            application_count=0,
                        )
                        self.patterns.append(pattern)

            # Keep only best patterns
            self.patterns.sort(
                key=lambda p: p.success_rate * p.confidence_score, reverse=True
            )
            self.patterns = self.patterns[:20]  # Keep top 20 patterns

            logger.info(f"Extracted {len(self.patterns)} optimization patterns")

        except Exception as e:
            logger.error(f"Error extracting patterns: {e}")

    def predict_optimal_action(self, current_state: Dict[str, float]) -> Optional[str]:
        """Predict the optimal optimization action for current state"""
        if not self.is_trained:
            return None

        try:
            # Check for matching patterns first
            for pattern in self.patterns:
                if self._state_matches_pattern(current_state, pattern):
                    if pattern.actions:
                        return pattern.actions[0]  # Return most successful action

            # Fall back to ML prediction
            features = np.array(
                [
                    [
                        current_state.get("cpu_percent", 0),
                        current_state.get("memory_percent", 0),
                        current_state.get("cache_hit_rate", 0),
                        current_state.get("queue_length", 0),
                        current_state.get("active_operations", 0),
                    ]
                ]
            )

            self.feature_scaler.transform(features)

            # This would need to be extended to predict actions rather than improvements
            # For now, return None to indicate no specific recommendation
            return None

        except Exception as e:
            logger.error(f"Error predicting optimal action: {e}")
            return None

    def _state_matches_pattern(
        self, state: Dict[str, float], pattern: OptimizationPattern
    ) -> bool:
        """Check if current state matches a pattern"""
        for key, expected_value in pattern.conditions.items():
            actual_value = state.get(key)
            if actual_value is None:
                return False

            # Allow some tolerance in matching
            tolerance = 0.1 * abs(expected_value) + 1.0
            if abs(actual_value - expected_value) > tolerance:
                return False

        return True

    def detect_anomalies(self, current_state: Dict[str, float]) -> bool:
        """Detect if current system state is anomalous"""
        if not self.is_trained:
            return False

        try:
            features = np.array(
                [
                    [
                        current_state.get("cpu_percent", 0),
                        current_state.get("memory_percent", 0),
                        current_state.get("cache_hit_rate", 0),
                        current_state.get("queue_length", 0),
                        current_state.get("active_operations", 0),
                    ]
                ]
            )

            features_scaled = self.feature_scaler.transform(features)
            anomaly_score = self.anomaly_detector.decision_function(features_scaled)[0]

            return anomaly_score < 0  # Negative scores indicate anomalies

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return False


class ResourceOptimizer:
    """Intelligent resource allocation optimizer"""

    def __init__(self):
        self.allocation_history: deque = deque(maxlen=1000)
        self.efficiency_scores: Dict[str, float] = defaultdict(float)
        self.allocation_policies: Dict[str, Callable] = {}

    def register_allocation_policy(
        self, resource_type: str, policy_func: Callable
    ) -> None:
        """Register a resource allocation policy"""
        self.allocation_policies[resource_type] = policy_func

    async def optimize_resource_allocation(
        self, current_load: Dict[str, float], available_resources: Dict[str, float]
    ) -> Dict[str, float]:
        """Optimize resource allocation based on current load"""
        optimized_allocation = {}

        for resource_type, policy_func in self.allocation_policies.items():
            try:
                allocated_amount = await policy_func(current_load, available_resources)
                optimized_allocation[resource_type] = allocated_amount

                # Track efficiency
                self._track_allocation_efficiency(
                    resource_type, allocated_amount, current_load
                )

            except Exception as e:
                logger.error(f"Error in allocation policy for {resource_type}: {e}")
                optimized_allocation[resource_type] = available_resources.get(
                    resource_type, 0
                )

        return optimized_allocation

    def _track_allocation_efficiency(
        self, resource_type: str, allocated: float, load: Dict[str, float]
    ) -> None:
        """Track allocation efficiency for learning"""
        # Calculate efficiency based on load vs allocation
        total_load = sum(load.values())
        if total_load > 0:
            efficiency = min(1.0, allocated / total_load)
            self.efficiency_scores[resource_type] = (
                self.efficiency_scores[resource_type] * 0.9 + efficiency * 0.1
            )


class AdaptiveEngine:
    """Main adaptive optimization engine"""

    def __init__(self, strategy: OptimizationStrategy = OptimizationStrategy.ADAPTIVE):
        self.strategy = strategy
        self.pattern_learner = PatternLearner()
        self.resource_optimizer = ResourceOptimizer()
        self.metrics_collector = MetricsCollector()

        self.optimization_history: deque = deque(maxlen=1000)
        self.performance_baseline: Dict[str, float] = {}
        self.adaptation_rate = 0.1
        self.min_confidence_threshold = 0.7

        self.register_default_optimization_actions()

    def register_default_optimization_actions(self) -> None:
        """Register default optimization actions"""

        # Database connection optimization
        performance_monitor.optimizer.register_optimization_action(
            OptimizationAction(
                action_type="optimize_db_connections",
                description="Optimize database connection pool size",
                priority=8,
                condition="cpu_percent > 80 and db_connections < 20",
                action_func=self._optimize_db_connections,
                cooldown_minutes=15,
            )
        )

        # Cache optimization
        performance_monitor.optimizer.register_optimization_action(
            OptimizationAction(
                action_type="optimize_cache_size",
                description="Adjust cache size based on hit rate",
                priority=7,
                condition="cache_hit_rate < 0.8 and memory_percent < 70",
                action_func=self._optimize_cache_size,
                cooldown_minutes=10,
            )
        )

        # Batch processing optimization
        performance_monitor.optimizer.register_optimization_action(
            OptimizationAction(
                action_type="optimize_batch_size",
                description="Adjust batch processing size",
                priority=6,
                condition="conversion_avg_ms > 1000 and cpu_percent < 60",
                action_func=self._optimize_batch_size,
                cooldown_minutes=20,
            )
        )

        # Memory cleanup
        performance_monitor.optimizer.register_optimization_action(
            OptimizationAction(
                action_type="cleanup_memory",
                description="Perform memory cleanup",
                priority=5,
                condition="memory_percent > 85",
                action_func=self._cleanup_memory,
                cooldown_minutes=5,
            )
        )

    async def _optimize_db_connections(self) -> Dict[str, Any]:
        """Optimize database connection pool size"""
        try:
            # This would integrate with the actual database connection pool
            current_connections = 10  # Placeholder
            optimal_connections = min(50, max(5, int(current_connections * 1.2)))

            return {
                "action": "db_connections_optimized",
                "old_size": current_connections,
                "new_size": optimal_connections,
                "improvement": "increased_pool_capacity",
            }
        except Exception as e:
            logger.error(f"Error optimizing DB connections: {e}")
            raise

    async def _optimize_cache_size(self) -> Dict[str, Any]:
        """Optimize cache size based on hit rate"""
        try:
            # This would integrate with the actual cache system
            current_size = 1000  # Placeholder
            optimal_size = min(5000, max(100, int(current_size * 1.5)))

            return {
                "action": "cache_size_optimized",
                "old_size": current_size,
                "new_size": optimal_size,
                "improvement": "increased_cache_capacity",
            }
        except Exception as e:
            logger.error(f"Error optimizing cache size: {e}")
            raise

    async def _optimize_batch_size(self) -> Dict[str, Any]:
        """Optimize batch processing size"""
        try:
            # This would integrate with the actual batch processing system
            current_batch_size = 50  # Placeholder
            optimal_batch_size = min(200, max(10, int(current_batch_size * 1.3)))

            return {
                "action": "batch_size_optimized",
                "old_size": current_batch_size,
                "new_size": optimal_batch_size,
                "improvement": "optimized_processing_efficiency",
            }
        except Exception as e:
            logger.error(f"Error optimizing batch size: {e}")
            raise

    async def _cleanup_memory(self) -> Dict[str, Any]:
        """Perform memory cleanup"""
        try:
            import gc

            before_cleanup = gc.collect()

            return {
                "action": "memory_cleanup",
                "objects_collected": before_cleanup,
                "improvement": "memory_freed",
            }
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
            raise

    async def analyze_and_adapt(self) -> Dict[str, Any]:
        """Analyze current performance and adapt optimization strategy"""
        current_time = datetime.now()

        # Get current system state
        system_state = performance_monitor.metrics_collector.collect_system_metrics()

        # Check for anomalies
        is_anomalous = self.pattern_learner.detect_anomalies(system_state)

        # Predict optimal actions
        predicted_action = self.pattern_learner.predict_optimal_action(system_state)

        # Get performance trends
        trends = {}
        for op_type in ["conversion", "mod_analysis", "batch_processing"]:
            trend = performance_monitor.metrics_collector.get_trend_analysis(op_type)
            if trend:
                trends[op_type] = trend

        # Adapt strategy based on analysis
        adaptation_result = {
            "timestamp": current_time,
            "system_state": system_state,
            "is_anomalous": is_anomalous,
            "predicted_action": predicted_action,
            "trends": trends,
            "strategy_adjustments": [],
        }

        # Adjust strategy based on conditions
        if is_anomalous:
            adaptation_result["strategy_adjustments"].append(
                {
                    "type": "increase_monitoring_frequency",
                    "reason": "anomalous_state_detected",
                }
            )

        if any(trend.get("trend", 0) > 10 for trend in trends.values()):
            adaptation_result["strategy_adjustments"].append(
                {
                    "type": "activate_aggressive_optimization",
                    "reason": "performance_degradation_detected",
                }
            )

        # Retrain models if we have enough data
        if (
            len(self.pattern_learner.training_data) > 100
            and not self.pattern_learner.is_trained
        ):
            training_success = self.pattern_learner.train_models()
            adaptation_result["models_trained"] = training_success

        # Record adaptation
        self.optimization_history.append(adaptation_result)

        return adaptation_result

    def get_adaptation_summary(self) -> Dict[str, Any]:
        """Get summary of adaptation behavior"""
        recent_adaptations = list(self.optimization_history)[-50:]

        summary = {
            "total_adaptations": len(self.optimization_history),
            "recent_adaptations": len(recent_adaptations),
            "patterns_learned": len(self.pattern_learner.patterns),
            "models_trained": self.pattern_learner.is_trained,
            "strategy": self.strategy.value,
            "adaptation_rate": self.adaptation_rate,
        }

        if recent_adaptations:
            anomalous_count = sum(
                1 for a in recent_adaptations if a.get("is_anomalous", False)
            )
            summary["anomaly_rate"] = anomalous_count / len(recent_adaptations)

        return summary


# Global adaptive engine instance
adaptive_engine = AdaptiveEngine()
