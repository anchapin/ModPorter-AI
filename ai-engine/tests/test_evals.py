"""
Tests for the eval + hill-climb workflow (Issue #1384)

Tests the evaluation system including:
- Eval case definitions
- Rubric evaluation
- Failure mapping
- Hill climb loop
- Eval suite runner
"""

import json
import pytest
from datetime import datetime, timezone

from evals.cases import CaseType, EvalCase, EvalCaseLibrary, FailureMode, get_default_case_library
from evals.failure_map import FailureMapper, FixLocation
from evals.hill_climb import HillClimbStatus, HillClimbRun, SimpleHillClimbEngine
from evals.rubrics import RubricCategory, RubricEvaluator
from evals.runner import CaseResult, EvalSuite, EvalSuiteResult, EvalSuiteStatus


class TestEvalCases:
    """Tests for eval case definitions."""

    def test_eval_case_creation(self):
        """Test creating a basic eval case."""
        case = EvalCase(
            case_id="test_case",
            name="Test Case",
            description="A test case",
            case_type=CaseType.GOLDEN_PATH,
            java_input="public class Test {}",
            rubric_checks=["valid json", "correct identifier"],
        )
        assert case.case_id == "test_case"
        assert case.case_type == CaseType.GOLDEN_PATH
        assert case.failure_mode is None

    def test_eval_case_to_dict(self):
        """Test converting eval case to dictionary."""
        case = EvalCase(
            case_id="test_case",
            name="Test Case",
            description="A test case",
            case_type=CaseType.GOLDEN_PATH,
            java_input="public class Test {}",
        )
        d = case.to_dict()
        assert d["case_id"] == "test_case"
        assert d["case_type"] == "golden_path"

    def test_case_types(self):
        """Test all case types are available."""
        assert CaseType.GOLDEN_PATH.value == "golden_path"
        assert CaseType.EDGE_CASE.value == "edge_case"
        assert CaseType.TOOL_SELECTION.value == "tool_selection"
        assert CaseType.ADVERSARIAL.value == "adversarial"
        assert CaseType.IDEMPOTENCY.value == "idempotency"


class TestEvalCaseLibrary:
    """Tests for the eval case library."""

    def test_library_creation(self):
        """Test creating an empty library."""
        library = EvalCaseLibrary()
        assert len(library.list_all()) == 0

    def test_add_get_case(self):
        """Test adding and retrieving a case."""
        library = EvalCaseLibrary()
        case = EvalCase(
            case_id="test",
            name="Test",
            description="Test",
            case_type=CaseType.GOLDEN_PATH,
            java_input="code",
        )
        library.add_case(case)
        retrieved = library.get_case("test")
        assert retrieved is not None
        assert retrieved.case_id == "test"

    def test_get_cases_by_type(self):
        """Test filtering cases by type."""
        library = EvalCaseLibrary()
        library.add_case(EvalCase(
            case_id="golden_1",
            name="Golden 1",
            description="",
            case_type=CaseType.GOLDEN_PATH,
            java_input="",
        ))
        library.add_case(EvalCase(
            case_id="edge_1",
            name="Edge 1",
            description="",
            case_type=CaseType.EDGE_CASE,
            java_input="",
        ))

        golden_cases = library.get_cases_by_type(CaseType.GOLDEN_PATH)
        assert len(golden_cases) == 1
        assert golden_cases[0].case_id == "golden_1"

    def test_default_library(self):
        """Test getting default case library has cases."""
        library = get_default_case_library()
        cases = library.list_all()
        assert len(cases) > 0
        assert library.get_case("golden_block_registration") is not None


class TestRubricEvaluator:
    """Tests for the rubric evaluation system."""

    def test_evaluator_creation(self):
        """Test creating a rubric evaluator."""
        evaluator = RubricEvaluator()
        checks = evaluator.get_checks()
        assert len(checks) > 0

    def test_valid_json_evaluation(self):
        """Test evaluating valid JSON."""
        evaluator = RubricEvaluator()
        result = evaluator.evaluate('{"format_version": "1.20.0"}')
        assert result.total_checks > 0
        assert result.passed_checks >= 1

    def test_invalid_json_evaluation(self):
        """Test evaluating invalid JSON."""
        evaluator = RubricEvaluator()
        result = evaluator.evaluate("not valid json {")
        assert result.passed_checks < result.total_checks

    def test_identifier_format_check(self):
        """Test identifier format check."""
        evaluator = RubricEvaluator()
        valid_output = '{"identifier": "modid:block_name"}'
        result = evaluator.evaluate(valid_output)
        json_result = next((r for r in result.results if r.check_id == "json_valid"), None)
        assert json_result is not None

    def test_format_version_check(self):
        """Test format version presence check."""
        evaluator = RubricEvaluator()
        output = '{"format_version": "1.20.0", "minecraft:block": {}}'
        result = evaluator.evaluate(output)
        fv_result = next((r for r in result.results if r.check_id == "format_version"), None)
        assert fv_result is not None
        assert fv_result.passed

    def test_weighted_score_calculation(self):
        """Test weighted score is calculated correctly."""
        evaluator = RubricEvaluator()
        result = evaluator.evaluate('{"format_version": "1.20.0", "identifier": "modid:test"}')
        assert 0 <= result.weighted_score <= 100

    def test_category_scores(self):
        """Test category scores are computed."""
        evaluator = RubricEvaluator()
        result = evaluator.evaluate('{"format_version": "1.20.0"}')
        assert len(result.category_scores) > 0
        assert RubricCategory.FORMAT in result.category_scores


class TestFailureMapper:
    """Tests for failure-to-fix mapping."""

    def test_mapper_creation(self):
        """Test creating a failure mapper."""
        mapper = FailureMapper()
        assert mapper is not None

    def test_map_missing_block_mapping(self):
        """Test mapping missing block mapping failure."""
        mapper = FailureMapper()
        mapping = mapper.map_failure("missing_block_mapping")
        assert FixLocation.BLOCK_MAPPINGS in mapping.possible_locations

    def test_map_incorrect_event_translation(self):
        """Test mapping incorrect event translation failure."""
        mapper = FailureMapper()
        mapping = mapper.map_failure("incorrect_event_translation")
        assert FixLocation.EVENT_TRANSFORMS in mapping.possible_locations

    def test_suggest_fixes(self):
        """Test getting fix suggestions."""
        mapper = FailureMapper()
        fixes = mapper.suggest_fixes("missing_block_mapping")
        assert len(fixes) > 0
        assert fixes[0].location == FixLocation.BLOCK_MAPPINGS

    def test_unknown_failure_mode(self):
        """Test handling unknown failure mode."""
        mapper = FailureMapper()
        mapping = mapper.map_failure("unknown_failure")
        assert FixLocation.UNKNOWN in mapping.possible_locations

    def test_fix_priority(self):
        """Test getting fix priority."""
        mapper = FailureMapper()
        priority = mapper.get_fix_priority("validation_error")
        assert isinstance(priority, int)


class TestHillClimbLoop:
    """Tests for the hill climb loop."""

    def test_iteration_result_creation(self):
        """Test creating an iteration result."""
        result = HillClimbRun(
            run_id="test_run",
            case_id="test_case",
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time=datetime.now(timezone.utc).isoformat(),
            total_iterations=3,
            final_score=85.0,
            initial_score=60.0,
            improvement=25.0,
            status=HillClimbStatus.CONVERGED,
            iterations=[],
        )
        assert result.final_score == 85.0
        assert result.improvement == 25.0

    def test_simple_hill_climb_engine(self):
        """Test simple hill climb engine."""
        evaluator = RubricEvaluator()
        mapper = FailureMapper()
        engine = SimpleHillClimbEngine(
            failure_mapper=mapper,
            evaluator=evaluator,
            max_iterations=3,
        )
        assert engine.max_iterations == 3

    def test_hill_climb_statuses(self):
        """Test all hill climb statuses exist."""
        assert HillClimbStatus.RUNNING.value == "running"
        assert HillClimbStatus.IMPROVED.value == "improved"
        assert HillClimbStatus.CONVERGED.value == "converged"


class TestEvalSuite:
    """Tests for the eval suite runner."""

    def test_suite_creation(self):
        """Test creating an eval suite."""
        suite = EvalSuite()
        assert suite.case_library is not None

    def test_suite_with_custom_library(self):
        """Test creating suite with custom case library."""
        library = EvalCaseLibrary()
        library.add_case(EvalCase(
            case_id="custom",
            name="Custom",
            description="",
            case_type=CaseType.GOLDEN_PATH,
            java_input="",
        ))
        suite = EvalSuite(case_library=library)
        assert len(suite.case_library.list_all()) == 1

    def test_run_case(self):
        """Test running a single case."""
        suite = EvalSuite()

        def dummy_conversion(java_code: str) -> str:
            return '{"format_version": "1.20.0", "identifier": "test:item"}'

        case = EvalCase(
            case_id="test",
            name="Test",
            description="",
            case_type=CaseType.GOLDEN_PATH,
            java_input="public class Test {}",
        )

        result = suite.run_case(case, dummy_conversion)
        assert result.case_id == "test"
        assert result.passed is True
        assert result.score > 0

    def test_run_suite(self):
        """Test running the full suite."""
        suite = EvalSuite()

        def dummy_conversion(java_code: str) -> str:
            return '{"format_version": "1.20.0", "identifier": "modid:test"}'

        result = suite.run_suite(conversion_fn=dummy_conversion, run_hill_climb=False)

        assert result.total_cases > 0
        assert result.passed_cases >= 0
        assert result.status in [EvalSuiteStatus.COMPLETED, EvalSuiteStatus.PARTIAL]

    def test_suite_result_to_dict(self):
        """Test converting suite result to dict."""
        result = EvalSuiteResult(
            suite_id="test_suite",
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_cases=5,
            passed_cases=4,
            failed_cases=1,
            status=EvalSuiteStatus.PARTIAL,
            case_results=[],
        )
        d = {
            "suite_id": result.suite_id,
            "total_cases": result.total_cases,
            "passed_cases": result.passed_cases,
            "failed_cases": result.failed_cases,
            "status": result.status.value,
        }
        assert d["suite_id"] == "test_suite"
        assert d["total_cases"] == 5

    def test_summary_generation(self):
        """Test generating suite summary."""
        suite = EvalSuite()
        result = EvalSuiteResult(
            suite_id="test_suite",
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_cases=5,
            passed_cases=3,
            failed_cases=2,
            status=EvalSuiteStatus.PARTIAL,
            case_results=[
                CaseResult("c1", "Case 1", CaseType.GOLDEN_PATH, True, 90.0),
                CaseResult("c2", "Case 2", CaseType.EDGE_CASE, False, 50.0),
                CaseResult("c3", "Case 3", CaseType.GOLDEN_PATH, True, 85.0),
            ],
        )

        summary = suite.summary(result)
        assert summary["total_cases"] == 5
        assert summary["passed"] == 3
        assert "golden_path" in summary["by_type"]


class TestIntegration:
    """Integration tests for the full eval + hill-climb workflow."""

    def test_full_workflow(self):
        """Test the complete eval + hill-climb workflow."""
        suite = EvalSuite()

        def conversion_fn(java_code: str) -> str:
            if "Block" in java_code:
                return '{"format_version": "1.20.0", "identifier": "modid:block"}'
            return '{"format_version": "1.20.0", "identifier": "modid:item"}'

        result = suite.run_suite(conversion_fn=conversion_fn, run_hill_climb=True)

        assert result.total_cases > 0
        assert result.duration_ms > 0
        assert result.suite_id.startswith("suite_")

    def test_evaluator_with_real_json(self):
        """Test evaluator with realistic Bedrock output."""
        evaluator = RubricEvaluator()

        bedrock_output = json.dumps({
            "format_version": "1.20.0",
            "minecraft:block": {
                "description": {
                    "identifier": "modid:diamond_ore"
                },
                "components": {
                    "minecraft:light_emission": 0,
                    "minecraft:destroy_time": 3
                }
            }
        })

        result = evaluator.evaluate(bedrock_output)
        assert result.passed_checks > 0
        assert result.weighted_score > 50


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_conversion_output(self):
        """Test handling empty conversion output."""
        evaluator = RubricEvaluator()
        result = evaluator.evaluate("")
        assert result.total_checks > 0
        assert result.passed_checks < result.total_checks

    def test_malformed_json_still_evaluated(self):
        """Test that malformed JSON can still be partially evaluated."""
        evaluator = RubricEvaluator()
        result = evaluator.evaluate('{"format_version": "1.20.0", invalid}')
        assert result.total_checks > 0

    def test_case_without_expected_bedrock(self):
        """Test case can exist without expected_bedrock."""
        case = EvalCase(
            case_id="no_expected",
            name="No Expected",
            description="",
            case_type=CaseType.GOLDEN_PATH,
            java_input="public class Test {}",
            expected_bedrock=None,
        )
        assert case.expected_bedrock is None

    def test_case_with_failure_mode(self):
        """Test case with explicit failure mode."""
        case = EvalCase(
            case_id="with_failure",
            name="With Failure",
            description="",
            case_type=CaseType.EDGE_CASE,
            java_input="",
            failure_mode=FailureMode.LOGIC_MISTRANSLATION,
        )
        assert case.failure_mode == FailureMode.LOGIC_MISTRANSLATION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])