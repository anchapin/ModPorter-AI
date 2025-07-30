"""
Strategy Selector for choosing optimal orchestration approaches.
Part of Phase 4: Integration with A/B Testing Framework
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
import time

logger = logging.getLogger(__name__)


class OrchestrationStrategy(Enum):
    """Available orchestration strategies"""
    SEQUENTIAL = "sequential"  # Original CrewAI sequential execution (control)
    PARALLEL_BASIC = "parallel_basic"  # Basic parallel execution
    PARALLEL_ADAPTIVE = "parallel_adaptive"  # Adaptive parallel with dynamic spawning
    HYBRID = "hybrid"  # Mix of sequential and parallel based on dependencies
    
    
@dataclass
class StrategyConfig:
    """Configuration for orchestration strategies"""
    max_parallel_tasks: int = 4
    enable_dynamic_spawning: bool = True
    task_timeout: float = 300.0  # 5 minutes
    retry_failed_tasks: bool = True
    use_process_pool: bool = False  # Use threads by default for I/O-bound LLM calls
    priority_scheduling: bool = True
    
    # Strategy-specific settings
    adaptive_threshold: float = 0.8  # Success rate threshold for adaptation
    hybrid_dependency_limit: int = 2  # Max dependencies before forcing sequential
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'max_parallel_tasks': self.max_parallel_tasks,
            'enable_dynamic_spawning': self.enable_dynamic_spawning,
            'task_timeout': self.task_timeout,
            'retry_failed_tasks': self.retry_failed_tasks,
            'use_process_pool': self.use_process_pool,
            'priority_scheduling': self.priority_scheduling,
            'adaptive_threshold': self.adaptive_threshold,
            'hybrid_dependency_limit': self.hybrid_dependency_limit
        }


class StrategySelector:
    """
    Selects the optimal orchestration strategy based on:
    1. A/B testing configuration
    2. Task complexity analysis
    3. Historical performance data
    4. System resource availability
    """
    
    def __init__(self, default_strategy: OrchestrationStrategy = OrchestrationStrategy.PARALLEL_ADAPTIVE):
        self.default_strategy = default_strategy
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.strategy_configs: Dict[OrchestrationStrategy, StrategyConfig] = {
            OrchestrationStrategy.SEQUENTIAL: StrategyConfig(
                max_parallel_tasks=1,
                enable_dynamic_spawning=False,
                use_process_pool=False
            ),
            OrchestrationStrategy.PARALLEL_BASIC: StrategyConfig(
                max_parallel_tasks=4,
                enable_dynamic_spawning=False,
                use_process_pool=False
            ),
            OrchestrationStrategy.PARALLEL_ADAPTIVE: StrategyConfig(
                max_parallel_tasks=6,
                enable_dynamic_spawning=True,
                use_process_pool=False,
                adaptive_threshold=0.8
            ),
            OrchestrationStrategy.HYBRID: StrategyConfig(
                max_parallel_tasks=4,
                enable_dynamic_spawning=True,
                use_process_pool=False,
                hybrid_dependency_limit=2
            )
        }
    
    def select_strategy(
        self,
        variant_id: Optional[str] = None,
        task_complexity: Optional[Dict[str, Any]] = None,
        system_resources: Optional[Dict[str, Any]] = None
    ) -> tuple[OrchestrationStrategy, StrategyConfig]:
        """
        Select the optimal orchestration strategy
        
        Args:
            variant_id: A/B testing variant identifier
            task_complexity: Analysis of the conversion task complexity
            system_resources: Current system resource availability
            
        Returns:
            Tuple of (strategy, config)
        """
        
        # 1. Check A/B testing variant first
        if variant_id:
            strategy = self._get_strategy_from_variant(variant_id)
            if strategy:
                config = self.strategy_configs[strategy]
                logger.info(f"Selected strategy {strategy.value} from A/B variant {variant_id}")
                return strategy, config
        
        # 2. Analyze task complexity to inform decision
        if task_complexity:
            strategy = self._analyze_task_complexity(task_complexity)
            if strategy:
                config = self.strategy_configs[strategy]
                logger.info(f"Selected strategy {strategy.value} based on task complexity")
                return strategy, config
        
        # 3. Consider system resources
        if system_resources:
            strategy = self._analyze_system_resources(system_resources)
            if strategy:
                config = self.strategy_configs[strategy]
                logger.info(f"Selected strategy {strategy.value} based on system resources")
                return strategy, config
        
        # 4. Use historical performance data
        best_strategy = self._get_best_performing_strategy()
        if best_strategy:
            config = self.strategy_configs[best_strategy]
            logger.info(f"Selected strategy {best_strategy.value} based on historical performance")
            return best_strategy, config
        
        # 5. Fall back to default
        config = self.strategy_configs[self.default_strategy]
        logger.info(f"Using default strategy {self.default_strategy.value}")
        return self.default_strategy, config
    
    def _get_strategy_from_variant(self, variant_id: str) -> Optional[OrchestrationStrategy]:
        """Map A/B testing variant to orchestration strategy"""
        
        # Define variant to strategy mapping
        variant_strategy_map = {
            'control': OrchestrationStrategy.SEQUENTIAL,
            'sequential': OrchestrationStrategy.SEQUENTIAL,
            'parallel_basic': OrchestrationStrategy.PARALLEL_BASIC,
            'parallel_adaptive': OrchestrationStrategy.PARALLEL_ADAPTIVE,
            'hybrid': OrchestrationStrategy.HYBRID,
            
            # Legacy mappings for existing variants
            'variant_enhanced_logic': OrchestrationStrategy.PARALLEL_ADAPTIVE,
            'baseline': OrchestrationStrategy.SEQUENTIAL,
        }
        
        # Check direct mapping first
        if variant_id in variant_strategy_map:
            return variant_strategy_map[variant_id]
        
        # Try to infer from variant name patterns
        variant_lower = variant_id.lower()
        if 'parallel' in variant_lower:
            if 'adaptive' in variant_lower:
                return OrchestrationStrategy.PARALLEL_ADAPTIVE
            else:
                return OrchestrationStrategy.PARALLEL_BASIC
        elif 'hybrid' in variant_lower:
            return OrchestrationStrategy.HYBRID
        elif 'sequential' in variant_lower or 'control' in variant_lower:
            return OrchestrationStrategy.SEQUENTIAL
        
        return None
    
    def _analyze_task_complexity(self, complexity: Dict[str, Any]) -> Optional[OrchestrationStrategy]:
        """Analyze task complexity to recommend strategy"""
        
        # Extract complexity metrics
        num_features = complexity.get('num_features', 0)
        num_dependencies = complexity.get('num_dependencies', 0)
        has_complex_assets = complexity.get('has_complex_assets', False)
        estimated_entities = complexity.get('estimated_entities', 0)
        
        # Calculate complexity score
        complexity_score = (
            num_features * 0.3 +
            num_dependencies * 0.2 +
            estimated_entities * 0.4 +
            (10 if has_complex_assets else 0)
        )
        
        logger.debug(f"Task complexity score: {complexity_score}")
        
        # Recommend strategy based on complexity
        if complexity_score < 5:
            # Simple tasks - sequential is fine
            return OrchestrationStrategy.SEQUENTIAL
        elif complexity_score < 15:
            # Moderate complexity - basic parallel
            return OrchestrationStrategy.PARALLEL_BASIC
        elif num_dependencies > 5:
            # High dependencies - hybrid approach
            return OrchestrationStrategy.HYBRID
        else:
            # High complexity - adaptive parallel
            return OrchestrationStrategy.PARALLEL_ADAPTIVE
    
    def _analyze_system_resources(self, resources: Dict[str, Any]) -> Optional[OrchestrationStrategy]:
        """Analyze system resources to recommend strategy"""
        
        cpu_count = resources.get('cpu_count', 1)
        memory_gb = resources.get('memory_gb', 4)
        is_containerized = resources.get('is_containerized', False)
        
        # Conservative approach in containers or low-resource environments
        if is_containerized and cpu_count < 4:
            return OrchestrationStrategy.PARALLEL_BASIC
        elif cpu_count < 2 or memory_gb < 4:
            return OrchestrationStrategy.SEQUENTIAL
        elif cpu_count >= 8 and memory_gb >= 16:
            return OrchestrationStrategy.PARALLEL_ADAPTIVE
        else:
            return OrchestrationStrategy.PARALLEL_BASIC
    
    def _get_best_performing_strategy(self) -> Optional[OrchestrationStrategy]:
        """Get the best performing strategy based on historical data"""
        
        if not self.performance_history:
            return None
        
        strategy_scores = {}
        
        for strategy_name, runs in self.performance_history.items():
            if not runs:
                continue
            
            # Calculate average performance metrics
            avg_success_rate = sum(run.get('success_rate', 0) for run in runs) / len(runs)
            avg_duration = sum(run.get('total_duration', float('inf')) for run in runs) / len(runs)
            
            # Composite score (higher is better)
            # Weight success rate more heavily than speed
            score = (avg_success_rate * 0.7) + ((1 / avg_duration) * 0.3 if avg_duration > 0 else 0)
            strategy_scores[strategy_name] = score
        
        if strategy_scores:
            best_strategy_name = max(strategy_scores.keys(), key=lambda k: strategy_scores[k])
            try:
                return OrchestrationStrategy(best_strategy_name)
            except ValueError:
                logger.warning(f"Unknown strategy in performance history: {best_strategy_name}")
        
        return None
    
    def record_performance(
        self,
        strategy: OrchestrationStrategy,
        success_rate: float,
        total_duration: float,
        task_count: int,
        additional_metrics: Optional[Dict[str, Any]] = None
    ):
        """Record performance data for a strategy"""
        
        performance_record = {
            'success_rate': success_rate,
            'total_duration': total_duration,
            'task_count': task_count,
            'timestamp': time.time(),
            **(additional_metrics or {})
        }
        
        strategy_name = strategy.value
        if strategy_name not in self.performance_history:
            self.performance_history[strategy_name] = []
        
        self.performance_history[strategy_name].append(performance_record)
        
        # Keep only recent history (last 50 runs per strategy)
        if len(self.performance_history[strategy_name]) > 50:
            self.performance_history[strategy_name] = self.performance_history[strategy_name][-50:]
        
        logger.debug(f"Recorded performance for {strategy_name}: "
                    f"success_rate={success_rate:.2%}, duration={total_duration:.2f}s")
    
    def get_strategy_config(self, strategy: OrchestrationStrategy) -> StrategyConfig:
        """Get configuration for a specific strategy"""
        return self.strategy_configs.get(strategy, StrategyConfig())
    
    def update_strategy_config(self, strategy: OrchestrationStrategy, config: StrategyConfig):
        """Update configuration for a specific strategy"""
        self.strategy_configs[strategy] = config
        logger.info(f"Updated configuration for strategy {strategy.value}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of strategy performance history"""
        summary = {}
        
        for strategy_name, runs in self.performance_history.items():
            if not runs:
                continue
            
            success_rates = [run.get('success_rate', 0) for run in runs]
            durations = [run.get('total_duration', 0) for run in runs]
            
            summary[strategy_name] = {
                'total_runs': len(runs),
                'avg_success_rate': sum(success_rates) / len(success_rates),
                'avg_duration': sum(durations) / len(durations),
                'best_success_rate': max(success_rates) if success_rates else 0,
                'fastest_duration': min(durations) if durations else 0,
                'latest_run': max(run.get('timestamp', 0) for run in runs)
            }
        
        return summary