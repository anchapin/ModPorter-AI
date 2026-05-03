"""
End-to-End Test Scenarios

Test scenarios for complete conversion pipeline testing.
"""

TEST_SCENARIOS = [
    {
        "id": "e2e-001",
        "name": "Simple Item Conversion",
        "category": "items",
        "difficulty": "simple",
        "input": {
            "java_code": """
public class ModItem extends Item {
    public ModItem() {
        super(new Properties().tab(CreativeModeTab.MISC));
    }
}
""",
            "mod_info": {
                "name": "Test Mod",
                "version": "1.0.0",
            },
        },
    },
]


def get_test_scenarios():
    """Return all test scenarios."""
    return TEST_SCENARIOS


def get_scenario_by_id(scenario_id: str):
    """Return a specific test scenario by ID."""
    for scenario in TEST_SCENARIOS:
        if scenario.get("id") == scenario_id:
            return scenario
    return None