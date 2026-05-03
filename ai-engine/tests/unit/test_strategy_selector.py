"""
Unit tests for StrategySelector and OrchestrationStrategy.
"""

import pytest
import time
from unittest.mock import patch
from orchestration.strategy_selector import (
    StrategySelector,
    OrchestrationStrategy,
    StrategyConfig,
    BanditAlgorithm,
)


class TestStrategyConfig:
    def test_to_dict(self):
        config = StrategyConfig(max_parallel_tasks=10)
        d = config.to_dict()
        assert d["max_parallel_tasks"] == 10
        assert "adaptive_threshold" in d


class TestStrategySelector:
    @pytest.fixture
    def selector(self):
        return StrategySelector()

    def test_get_strategy_from_variant_direct(self, selector):
        assert selector._get_strategy_from_variant("control") == OrchestrationStrategy.SEQUENTIAL
        assert (
            selector._get_strategy_from_variant("parallel_basic")
            == OrchestrationStrategy.PARALLEL_BASIC
        )
        assert (
            selector._get_strategy_from_variant("parallel_adaptive")
            == OrchestrationStrategy.PARALLEL_ADAPTIVE
        )
        assert selector._get_strategy_from_variant("hybrid") == OrchestrationStrategy.HYBRID

    def test_get_strategy_from_variant_legacy(self, selector):
        assert (
            selector._get_strategy_from_variant("variant_enhanced_logic")
            == OrchestrationStrategy.PARALLEL_ADAPTIVE
        )
        assert selector._get_strategy_from_variant("baseline") == OrchestrationStrategy.SEQUENTIAL

    def test_get_strategy_from_variant_inferred(self, selector):
        assert (
            selector._get_strategy_from_variant("new_parallel_variant")
            == OrchestrationStrategy.PARALLEL_BASIC
        )
        assert (
            selector._get_strategy_from_variant("some_parallel_adaptive")
            == OrchestrationStrategy.PARALLEL_ADAPTIVE
        )
        assert selector._get_strategy_from_variant("my_hybrid_test") == OrchestrationStrategy.HYBRID
        assert (
            selector._get_strategy_from_variant("old_sequential_path")
            == OrchestrationStrategy.SEQUENTIAL
        )
        assert selector._get_strategy_from_variant("unknown") is None

    def test_analyze_task_complexity(self, selector):
        # Simple: score = 1 * 0.3 = 0.3 < 5
        assert (
            selector._analyze_task_complexity({"num_features": 1})
            == OrchestrationStrategy.SEQUENTIAL
        )
        # Moderate: score = 20 * 0.3 = 6.0 (between 5 and 15)
        assert (
            selector._analyze_task_complexity({"num_features": 20})
            == OrchestrationStrategy.PARALLEL_BASIC
        )
        # High dependencies: score = 50 * 0.3 + 10 * 0.2 = 15.0 + 2.0 = 17.0 (>= 15) AND num_dependencies = 10 (> 5)
        assert (
            selector._analyze_task_complexity({"num_features": 50, "num_dependencies": 10})
            == OrchestrationStrategy.HYBRID
        )
        # High complexity: score = 100 * 0.3 = 30.0 (>= 15) AND num_dependencies = 0 (<= 5)
        assert (
            selector._analyze_task_complexity({"num_features": 100})
            == OrchestrationStrategy.PARALLEL_ADAPTIVE
        )

    def test_analyze_system_resources(self, selector):
        # Low resources
        assert (
            selector._analyze_system_resources({"cpu_count": 1, "memory_gb": 2})
            == OrchestrationStrategy.SEQUENTIAL
        )
        # Containerized low resources
        assert (
            selector._analyze_system_resources({"cpu_count": 2, "is_containerized": True})
            == OrchestrationStrategy.PARALLEL_BASIC
        )
        # High resources
        assert (
            selector._analyze_system_resources({"cpu_count": 16, "memory_gb": 32})
            == OrchestrationStrategy.PARALLEL_ADAPTIVE
        )
        # Normal resources
        assert (
            selector._analyze_system_resources({"cpu_count": 4, "memory_gb": 8})
            == OrchestrationStrategy.PARALLEL_BASIC
        )

    def test_record_and_get_best_strategy(self, selector):
        # Record some performance
        selector.record_performance(OrchestrationStrategy.SEQUENTIAL, 0.9, 10.0, 5)
        selector.record_performance(OrchestrationStrategy.PARALLEL_BASIC, 0.95, 5.0, 5)

        # Parallel Basic should be better (higher success, lower duration)
        assert selector._get_best_performing_strategy() == OrchestrationStrategy.PARALLEL_BASIC

    def test_get_best_performing_strategy_empty(self, selector):
        assert selector._get_best_performing_strategy() is None

    def test_select_strategy_order(self, selector):
        # 1. Variant first
        s, c = selector.select_strategy(variant_id="sequential")
        assert s == OrchestrationStrategy.SEQUENTIAL

        # 2. Complexity second
        s, c = selector.select_strategy(task_complexity={"num_features": 100})
        assert s == OrchestrationStrategy.PARALLEL_ADAPTIVE

        # 3. Resources third
        s, c = selector.select_strategy(system_resources={"cpu_count": 1})
        assert s == OrchestrationStrategy.SEQUENTIAL

        # 4. History fourth
        selector.record_performance(OrchestrationStrategy.HYBRID, 1.0, 1.0, 1)
        s, c = selector.select_strategy()
        assert s == OrchestrationStrategy.HYBRID

        # 5. Default last
        empty_selector = StrategySelector(default_strategy=OrchestrationStrategy.PARALLEL_BASIC)
        s, c = empty_selector.select_strategy()
        assert s == OrchestrationStrategy.PARALLEL_BASIC

    def test_update_and_get_config(self, selector):
        new_config = StrategyConfig(max_parallel_tasks=99)
        selector.update_strategy_config(OrchestrationStrategy.SEQUENTIAL, new_config)
        assert (
            selector.get_strategy_config(OrchestrationStrategy.SEQUENTIAL).max_parallel_tasks == 99
        )

        # Missing strategy returns default config
        assert selector.get_strategy_config("missing").max_parallel_tasks == 4

    def test_get_performance_summary(self, selector):
        selector.record_performance(OrchestrationStrategy.SEQUENTIAL, 0.8, 20.0, 5)
        summary = selector.get_performance_summary()
        assert "sequential" in summary
        assert summary["sequential"]["total_runs"] == 1
        assert summary["sequential"]["avg_success_rate"] == 0.8

    def test_get_best_performing_strategy_invalid_name(self, selector):
        # Inject invalid strategy name into history
        selector.performance_history["invalid_strategy"] = [
            {"success_rate": 1.0, "total_duration": 1.0}
        ]
        # Should catch ValueError and return None (or best other)
        assert selector._get_best_performing_strategy() is None

    def test_get_performance_summary_empty_runs(self, selector):
        # Strategy with no runs (should not happen normally but for coverage)
        selector.performance_history["sequential"] = []
        summary = selector.get_performance_summary()
        assert "sequential" not in summary

    def test_update_strategy_config_logging(self, selector):
        config = StrategyConfig()
        with patch("logging.Logger.info") as mock_log:
            selector.update_strategy_config(OrchestrationStrategy.SEQUENTIAL, config)
            assert mock_log.called
            assert "Updated configuration" in mock_log.call_args[0][0]


class TestBanditAlgorithms:
    @pytest.fixture
    def ucb_selector(self):
        return StrategySelector(bandit_algorithm=BanditAlgorithm.UCB1)

    @pytest.fixture
    def epsilon_selector(self):
        return StrategySelector(bandit_algorithm=BanditAlgorithm.EPSILON_GREEDY, epsilon=0.1)

    @pytest.fixture
    def simple_selector(self):
        return StrategySelector(bandit_algorithm=BanditAlgorithm.SIMPLE_AVERAGE)

    def test_ucb1_selection(self, ucb_selector):
        """UCB1 should select strategy based on reward + confidence bound"""
        ucb_selector.record_performance(OrchestrationStrategy.SEQUENTIAL, 0.8, 10.0, 5)
        ucb_selector.record_performance(OrchestrationStrategy.PARALLEL_BASIC, 0.95, 5.0, 5)

        result = ucb_selector._get_best_performing_strategy()
        assert result == OrchestrationStrategy.PARALLEL_BASIC

    def test_ucb1_prefers_unexplored_strategies(self, ucb_selector):
        """UCB1 should initially prefer less-explored strategies when rewards are comparable"""
        ucb_selector.record_performance(OrchestrationStrategy.SEQUENTIAL, 0.9, 10.0, 100)
        ucb_selector.record_performance(OrchestrationStrategy.PARALLEL_BASIC, 0.89, 8.0, 2)

        result = ucb_selector._get_best_performing_strategy()
        assert result == OrchestrationStrategy.PARALLEL_BASIC

    def test_epsilon_greedy_exploitation(self, epsilon_selector):
        """Epsilon-greedy with low epsilon should mostly exploit best known"""
        epsilon_selector.epsilon = 0.0
        epsilon_selector.record_performance(OrchestrationStrategy.SEQUENTIAL, 0.8, 10.0, 5)
        epsilon_selector.record_performance(OrchestrationStrategy.PARALLEL_BASIC, 0.95, 5.0, 5)

        result = epsilon_selector._get_best_performing_strategy()
        assert result == OrchestrationStrategy.PARALLEL_BASIC

    def test_epsilon_greedy_exploration(self, epsilon_selector):
        """Epsilon-greedy with epsilon=1.0 should explore randomly"""
        epsilon_selector.epsilon = 1.0
        epsilon_selector.record_performance(OrchestrationStrategy.SEQUENTIAL, 0.8, 10.0, 5)
        epsilon_selector.record_performance(OrchestrationStrategy.PARALLEL_BASIC, 0.95, 5.0, 5)

        results = set()
        for _ in range(50):
            result = epsilon_selector._get_best_performing_strategy()
            if result:
                results.add(result)

        assert len(results) > 1

    def test_simple_average_selection(self, simple_selector):
        """Simple average should pick highest reward without exploration bonus"""
        simple_selector.record_performance(OrchestrationStrategy.SEQUENTIAL, 0.9, 10.0, 5)
        simple_selector.record_performance(OrchestrationStrategy.PARALLEL_BASIC, 0.95, 5.0, 5)

        result = simple_selector._get_best_performing_strategy()
        assert result == OrchestrationStrategy.PARALLEL_BASIC

    def test_complexity_multiplier_low_complexity(self):
        """Low complexity tasks should prefer sequential"""
        selector = StrategySelector(bandit_algorithm=BanditAlgorithm.SIMPLE_AVERAGE)
        selector.record_performance(OrchestrationStrategy.SEQUENTIAL, 0.9, 5.0, 5)
        selector.record_performance(OrchestrationStrategy.PARALLEL_BASIC, 0.9, 5.0, 5)

        complexity = {"num_features": 2, "num_dependencies": 1}
        result = selector._get_best_performing_strategy(complexity)
        assert result == OrchestrationStrategy.SEQUENTIAL

    def test_complexity_multiplier_high_complexity(self):
        """High complexity tasks should prefer parallel adaptive"""
        selector = StrategySelector(bandit_algorithm=BanditAlgorithm.SIMPLE_AVERAGE)
        selector.record_performance(OrchestrationStrategy.PARALLEL_ADAPTIVE, 0.85, 10.0, 5)
        selector.record_performance(OrchestrationStrategy.SEQUENTIAL, 0.9, 20.0, 5)

        complexity = {"num_features": 100, "num_dependencies": 0}
        result = selector._get_best_performing_strategy(complexity)
        assert result == OrchestrationStrategy.PARALLEL_ADAPTIVE

    def test_bandit_selection_increments_counters(self, ucb_selector):
        """select_strategy should increment selection counters when using historical data"""
        ucb_selector.record_performance(OrchestrationStrategy.SEQUENTIAL, 0.9, 10.0, 5)
        ucb_selector.record_performance(OrchestrationStrategy.PARALLEL_BASIC, 0.95, 5.0, 5)

        initial_total = ucb_selector.total_selections
        s, _ = ucb_selector.select_strategy()

        assert ucb_selector.total_selections == initial_total + 1
        assert s.value in ucb_selector.strategy_selections

    def test_get_best_performing_strategy_with_complexity(self, simple_selector):
        """_get_best_performing_strategy should accept task_complexity parameter"""
        simple_selector.record_performance(OrchestrationStrategy.SEQUENTIAL, 0.8, 10.0, 5)

        result = simple_selector._get_best_performing_strategy(task_complexity={"num_features": 5})
        assert result == OrchestrationStrategy.SEQUENTIAL
