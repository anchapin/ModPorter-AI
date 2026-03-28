"""
E2E Test Package
"""

from .test_scenarios import (
    get_test_scenarios,
    get_scenario_by_id,
    TEST_SCENARIOS,
)

from .test_e2e_conversion import (
    E2ETestRunner,
    run_e2e_tests,
)


def get_scenarios_by_category(category: str):
    """Return test scenarios filtered by category."""
    return [s for s in TEST_SCENARIOS if s.get("category") == category]


def get_scenarios_by_difficulty(difficulty: str):
    """Return test scenarios filtered by difficulty."""
    return [s for s in TEST_SCENARIOS if s.get("difficulty") == difficulty]


__all__ = [
    "TEST_SCENARIOS",
    "get_test_scenarios",
    "get_scenario_by_id",
    "get_scenarios_by_category",
    "get_scenarios_by_difficulty",
    "E2ETestRunner",
    "run_e2e_tests",
]
