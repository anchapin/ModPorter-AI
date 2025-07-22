# ai-engine/src/agents/qa_agent.py
import logging
import random # For PerformanceAnalyzer
import json # For main block dummy data
import os # For main block dummy data file check
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Attempt relative import, assuming standard package structure
# where 'agents' and 'testing' are sibling directories under 'src'
try:
    from ..testing.qa_framework import TestFramework, TestScenarioGenerator
except ImportError:
    # Fallback for environments where the structure might be flatter or path is different
    # This might happen if the subtask runs the file directly not as part of a package
    logger.warning("Relative import failed. Attempting direct import for qa_framework. This might indicate execution outside a package.")
    try:
        from testing.qa_framework import TestFramework, TestScenarioGenerator
    except ImportError:
        # Last resort, assuming ai_engine.src is in python path
        logger.warning("Direct import from testing.qa_framework failed. Attempting import from ai_engine.src.testing.qa_framework.")
        from ai_engine.src.testing.qa_framework import TestFramework, TestScenarioGenerator

# --- Placeholder classes for engines not yet detailed ---
class RiskAnalysisEngine:
    def __init__(self):
        logger.debug("RiskAnalysisEngine initialized (placeholder).")
    pass

class QALearningEngine:
    def __init__(self):
        logger.debug("QALearningEngine initialized (placeholder).")
    pass

# --- Core QA Engine Implementations ---
class BehavioralTestEngine:
    def __init__(self):
        logger.debug("BehavioralTestEngine initialized.")

    def run_functional_tests(self, scenarios: List[Dict[str, Any]], framework: TestFramework) -> List[Dict[str, Any]]:
        logger.info("BehavioralTestEngine: Running functional tests...")
        functional_scenarios = [s for s in scenarios if s.get('category') == 'functional']
        if not functional_scenarios:
            logger.info("No functional test scenarios found for BehavioralTestEngine.")
            return []

        logger.info(f"BehavioralTestEngine: Found {len(functional_scenarios)} functional scenarios.")
        results = []
        for scenario in functional_scenarios:
            success, details, exec_time = framework.execute_scenario(scenario)
            error_msg = details if not success else None
            result = framework.collect_results(scenario, success, details, exec_time, error_message_arg=error_msg)
            results.append(result)
        logger.info(f"BehavioralTestEngine: Functional tests completed. {len(results)} results collected.")
        return results

class PerformanceAnalyzer:
    def __init__(self):
        logger.debug("PerformanceAnalyzer initialized.")

    def analyze_performance(self, scenarios: List[Dict[str, Any]], framework: TestFramework) -> List[Dict[str, Any]]:
        logger.info("PerformanceAnalyzer: Analyzing performance...")
        performance_scenarios = [s for s in scenarios if s.get('category') == 'performance']
        if not performance_scenarios:
            logger.info("No performance test scenarios found for PerformanceAnalyzer.")
            return []

        logger.info(f"PerformanceAnalyzer: Found {len(performance_scenarios)} performance scenarios.")
        results = []
        for scenario in performance_scenarios:
            success, details, exec_time = framework.execute_scenario(scenario)
            perf_metrics = {
                "cpu_load_avg_percent": round(random.uniform(5, 75), 2),
                "memory_peak_mb": random.randint(80, 600),
                "simulated_fps_avg": random.randint(25, 120) if success else random.randint(10,40)
            }
            error_msg = details if not success else None
            result = framework.collect_results(scenario, success, details, exec_time, error_message_arg=error_msg, performance_metrics=perf_metrics)
            results.append(result)
        logger.info(f"PerformanceAnalyzer: Performance analysis completed. {len(results)} results collected.")
        return results

class CompatibilityTester:
    def __init__(self):
        logger.debug("CompatibilityTester initialized.")

    def check_compatibility(self, scenarios: List[Dict[str, Any]], framework: TestFramework) -> List[Dict[str, Any]]:
        logger.info("CompatibilityTester: Checking compatibility...")
        compatibility_scenarios = [s for s in scenarios if s.get('category') == 'compatibility']
        if not compatibility_scenarios:
            logger.info("No compatibility test scenarios found for CompatibilityTester.")
            return []

        logger.info(f"CompatibilityTester: Found {len(compatibility_scenarios)} compatibility scenarios.")
        results = []
        for scenario in compatibility_scenarios:
            success, details, exec_time = framework.execute_scenario(scenario)
            comp_metrics = {
                "tested_on_version_sim": f"1.{random.randint(18, 20)}.{random.randint(0,5)}",
                "compatibility_issues_found": 0 if success else random.randint(1,3),
                "notes": "Simulated environment check."
            }
            error_msg = details if not success else None
            result = framework.collect_results(scenario, success, details, exec_time, error_message_arg=error_msg, performance_metrics=comp_metrics) # Note: qa_framework uses 'performance_metrics' field for any additional metrics
            results.append(result)
        logger.info(f"CompatibilityTester: Compatibility check completed. {len(results)} results collected.")
        return results

# --- QAAgent Class ---
class QAAgent:
    def __init__(self):
        self.test_framework: TestFramework = TestFramework()
        self.scenario_generator: TestScenarioGenerator = TestScenarioGenerator(self.test_framework)

        self.behavioral_tester: BehavioralTestEngine = BehavioralTestEngine()
        self.performance_analyzer: PerformanceAnalyzer = PerformanceAnalyzer()
        self.compatibility_checker: CompatibilityTester = CompatibilityTester()

        self.risk_assessor: RiskAnalysisEngine = RiskAnalysisEngine() # Placeholder
        self.learning_system: QALearningEngine = QALearningEngine() # Placeholder

        logger.info("QAAgent initialized with core testing engines, framework, and scenario generator.")

    def run_qa_pipeline(self, scenario_file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        logger.info(f"QAAgent: Starting QA pipeline with scenario file: {scenario_file_path}")

        all_scenarios = self.scenario_generator.load_scenarios_from_file(scenario_file_path)
        if not all_scenarios:
            logger.error("QAAgent: No scenarios loaded from file. Aborting QA pipeline.")
            return {
                "functional": [], "performance": [], "compatibility": [],
                "all_collected_by_framework": [], "errors": ["No scenarios loaded"]
            }

        self.test_framework.test_results_summary = [] # Clear previous results
        logger.debug("QAAgent: Cleared previous results from TestFramework summary.")

        functional_results = self.behavioral_tester.run_functional_tests(all_scenarios, self.test_framework)
        performance_results = self.performance_analyzer.analyze_performance(all_scenarios, self.test_framework)
        compatibility_results = self.compatibility_checker.check_compatibility(all_scenarios, self.test_framework)

        # All results are already collected in self.test_framework.test_results_summary by the engines
        pipeline_results = {
            "functional_specific_results": functional_results, # Results specifically from this engine's call
            "performance_specific_results": performance_results,
            "compatibility_specific_results": compatibility_results,
            "all_collected_by_framework": self.test_framework.test_results_summary # Consolidated list
        }

        logger.info("QAAgent: QA pipeline finished.")
        return pipeline_results

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(name)s:%(module)s:%(lineno)d] - %(message)s'
    )

    # Determine the base path for scenarios relative to this file's location
    # Assuming this script is in ai-engine/src/agents/
    # And scenarios are in ai-engine/src/testing/scenarios/
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    base_project_dir = os.path.join(current_script_dir, '..', '..') # Up to ai-engine/
    scenario_file_path = os.path.join(base_project_dir, "src", "testing", "scenarios", "example_scenarios.json")
    scenario_file_path = os.path.normpath(scenario_file_path)


    created_dummy_file_for_main = False

    if not os.path.exists(scenario_file_path):
        logger.warning(
            f"Main block: Scenario file '{scenario_file_path}' not found. "
            "Creating a temporary dummy scenario file for this demonstration."
        )
        dummy_scenario_dir = os.path.dirname(scenario_file_path)
        if dummy_scenario_dir and not os.path.exists(dummy_scenario_dir):
            os.makedirs(dummy_scenario_dir, exist_ok=True)
            logger.info(f"Main block: Created directory '{dummy_scenario_dir}'.")

        with open(scenario_file_path, 'w') as f:
            json.dump({
                "scenarios": [
                    {"name": "Dummy Functional Test", "category": "functional",
                     "steps": ["Action A", "Check A"], "expected_outcome": "A works"},
                    {"name": "Dummy Performance Test", "category": "performance",
                     "steps": ["Load Stress", "Measure Time"], "expected_outcome": "Loads quickly"},
                    {"name": "Dummy Compatibility Test", "category": "compatibility",
                     "steps": ["Load on OldSim", "Check Features"], "expected_outcome": "Compatible"}
                ]
            }, f, indent=2)
        created_dummy_file_for_main = True

    qa_agent = QAAgent()

    logger.info(f"Main block: Running QA Pipeline with QAAgent using scenario file: '{scenario_file_path}'")
    pipeline_output = qa_agent.run_qa_pipeline(scenario_file_path=scenario_file_path)

    print("\n--- QAAgent Pipeline Execution Summary ---")

    # Use the 'all_collected_by_framework' for the primary summary as it's the consolidated list
    all_results_from_framework = pipeline_output.get("all_collected_by_framework", [])

    # Separate display for engine-specific views if needed, but main summary from consolidated list
    # For example, to show which engine processed which category:
    categories_processed = {}
    for res in all_results_from_framework:
        cat = res.get('test_category', 'unknown')
        if cat not in categories_processed:
            categories_processed[cat] = []
        categories_processed[cat].append(res)

    for category_name, cat_results_list in categories_processed.items():
        print(f"\nCategory: '{category_name.upper()}' (Processed Scenarios: {len(cat_results_list)})")
        if not cat_results_list:
            print("  No results for this category.")
            continue
        for i, result in enumerate(cat_results_list):
            status_icon = "✅" if result.get('status') == 'passed' else "❌"
            print(f"  {status_icon} Test: {result.get('test_name')} - Status: {result.get('status')}")
            if result.get('status') == 'failed':
                print(f"    Reason: {result.get('error_message', 'No specific error message.')}")
            if result.get('performance_metrics'): # Note: compatibility metrics also use this field in qa_framework
                metrics_label = "Performance Metrics"
                if category_name == "compatibility":
                    metrics_label = "Compatibility Metrics"
                print(f"    {metrics_label}: {result.get('performance_metrics')}")
            print(f"    Execution Time: {result.get('execution_time_ms')}ms")

    print("\n--- Overall Summary (from Framework's perspective) ---")
    total_tests_collected_by_framework = len(all_results_from_framework)
    print(f"Total Scenarios Processed & Collected by Framework: {total_tests_collected_by_framework}")

    total_passed_from_framework = sum(1 for r in all_results_from_framework if r.get('status') == 'passed')
    print(f"Total Passed: {total_passed_from_framework}")

    if total_tests_collected_by_framework > 0:
        pass_rate = (total_passed_from_framework / total_tests_collected_by_framework) * 100
        print(f"Pass Rate: {pass_rate:.2f}%")
    else:
        print("No tests were collected by the framework.")

    if created_dummy_file_for_main:
        logger.info(f"Main block: Cleaning up temporary dummy scenario file: '{scenario_file_path}'")
        try:
            os.remove(scenario_file_path)
        except OSError as e:
            logger.error(f"Main block: Error removing dummy file '{scenario_file_path}': {e}")
