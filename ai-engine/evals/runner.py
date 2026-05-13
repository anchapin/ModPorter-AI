"""
Eval Suite Runner

Orchestrates the full eval + hill-climb workflow:
1. Run eval suite on conversion cases
2. Identify failures
3. Run hill-climb on failing cases
4. Perform regression check on full suite
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .cases import CaseType, EvalCase, EvalCaseLibrary, get_default_case_library
from .failure_map import FailureMapper
from .hill_climb import HillClimbRun, SimpleHillClimbEngine
from .rubrics import RubricEvaluator

logger = logging.getLogger(__name__)


class EvalSuiteStatus(Enum):
    """Status of an eval suite run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class CaseResult:
    """Result of evaluating a single case."""

    case_id: str
    case_name: str
    case_type: CaseType
    passed: bool
    score: float
    rubric_results: Optional[List[Any]] = None
    error: Optional[str] = None
    hill_climb_run: Optional[HillClimbRun] = None


@dataclass
class EvalSuiteResult:
    """Result of a full eval suite run."""

    suite_id: str
    timestamp: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    status: EvalSuiteStatus
    case_results: List[CaseResult]
    hill_climb_runs: List[HillClimbRun] = field(default_factory=list)
    regression_passed: bool = True
    duration_ms: float = 0.0


class EvalSuite:
    """
    Main eval suite that runs evaluation + hill-climb workflow.

    Usage:
        suite = EvalSuite()
        result = suite.run_suite(conversion_fn, eval_cases=None)
    """

    def __init__(
        self,
        case_library: Optional[EvalCaseLibrary] = None,
        rubric_evaluator: Optional[RubricEvaluator] = None,
        failure_mapper: Optional[FailureMapper] = None,
        max_hill_climb_iterations: int = 5,
    ):
        self.case_library = case_library or get_default_case_library()
        self.rubric_evaluator = rubric_evaluator or RubricEvaluator()
        self.failure_mapper = failure_mapper or FailureMapper()
        self.max_hill_climb_iterations = max_hill_climb_iterations
        self._conversion_fn: Optional[Callable[[str], str]] = None

    def set_conversion_fn(self, fn: Callable[[str], str]) -> None:
        """Set the conversion function to use."""
        self._conversion_fn = fn

    def run_case(
        self,
        case: EvalCase,
        conversion_fn: Optional[Callable[[str], str]] = None,
    ) -> CaseResult:
        """Run evaluation on a single case."""
        fn = conversion_fn or self._conversion_fn
        if not fn:
            raise ValueError("No conversion function provided")

        try:
            output = fn(case.java_input)
            score = self.rubric_evaluator.evaluate(output).weighted_score

            passed = score >= 80.0

            return CaseResult(
                case_id=case.case_id,
                case_name=case.name,
                case_type=case.case_type,
                passed=passed,
                score=score,
            )

        except Exception as e:
            logger.error(f"Error running case {case.case_id}: {e}")
            return CaseResult(
                case_id=case.case_id,
                case_name=case.name,
                case_type=case.case_type,
                passed=False,
                score=0.0,
                error=str(e),
            )

    def run_suite(
        self,
        conversion_fn: Optional[Callable[[str], str]] = None,
        eval_cases: Optional[List[EvalCase]] = None,
        run_hill_climb: bool = True,
        regression_threshold: float = 80.0,
    ) -> EvalSuiteResult:
        """
        Run the full eval suite.

        Args:
            conversion_fn: Function that converts Java code to Bedrock output
            eval_cases: Specific cases to run (default: all in library)
            run_hill_climb: Whether to run hill-climb on failures
            regression_threshold: Minimum score for regression pass

        Returns:
            EvalSuiteResult with all case results and hill-climb runs
        """
        import time

        start_time = time.time()
        suite_id = f"suite_{int(start_time)}"

        fn = conversion_fn or self._conversion_fn
        if not fn:
            raise ValueError("No conversion function provided")

        cases_to_run = eval_cases or self.case_library.list_all()

        logger.info(f"Running eval suite {suite_id} with {len(cases_to_run)} cases")

        case_results: List[CaseResult] = []
        hill_climb_runs: List[HillClimbRun] = []

        for case in cases_to_run:
            result = self.run_case(case, fn)
            case_results.append(result)

            if not result.passed and run_hill_climb and result.error is None:
                logger.info(f"Case {case.case_id} failed, running hill-climb")
                hill_climb_run = self._run_hill_climb(case, fn)
                result.hill_climb_run = hill_climb_run
                if hill_climb_run.regression_passed:
                    result.passed = True
                    result.score = hill_climb_run.final_score
                hill_climb_runs.append(hill_climb_run)

        passed = sum(1 for r in case_results if r.passed)
        failed = len(case_results) - passed

        status = EvalSuiteStatus.COMPLETED if failed == 0 else EvalSuiteStatus.PARTIAL

        regression_passed = all(r.score >= regression_threshold for r in case_results)

        duration_ms = (time.time() - start_time) * 1000

        result = EvalSuiteResult(
            suite_id=suite_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_cases=len(case_results),
            passed_cases=passed,
            failed_cases=failed,
            status=status,
            case_results=case_results,
            hill_climb_runs=hill_climb_runs,
            regression_passed=regression_passed,
            duration_ms=duration_ms,
        )

        logger.info(
            f"Suite {suite_id} completed: {passed}/{len(case_results)} passed, "
            f"regression={'PASSED' if regression_passed else 'FAILED'}, "
            f"duration={duration_ms:.0f}ms"
        )

        return result

    def _run_hill_climb(
        self, case: EvalCase, conversion_fn: Callable[[str], str]
    ) -> Optional[HillClimbRun]:
        """Run hill-climb on a failing case."""
        try:
            hill_climb = SimpleHillClimbEngine(
                failure_mapper=self.failure_mapper,
                evaluator=self.rubric_evaluator,
                max_iterations=self.max_hill_climb_iterations,
            )

            def convert_fn():
                return conversion_fn(case.java_input)

            return hill_climb.run_hill_climb(case, convert_fn)
        except Exception as e:
            logger.error(f"Error in hill-climb for case {case.case_id}: {e}")
            return None

    def get_failing_cases(self, results: List[CaseResult]) -> List[CaseResult]:
        """Get list of failing cases from results."""
        return [r for r in results if not r.passed]

    def summary(self, result: EvalSuiteResult) -> Dict[str, Any]:
        """Generate a summary of eval suite results."""
        by_type: Dict[str, Dict[str, int]] = {}
        for case_result in result.case_results:
            type_name = case_result.case_type.value
            if type_name not in by_type:
                by_type[type_name] = {"passed": 0, "failed": 0}
            if case_result.passed:
                by_type[type_name]["passed"] += 1
            else:
                by_type[type_name]["failed"] += 1

        return {
            "suite_id": result.suite_id,
            "total_cases": result.total_cases,
            "passed": result.passed_cases,
            "failed": result.failed_cases,
            "pass_rate": result.passed_cases / result.total_cases if result.total_cases > 0 else 0,
            "regression_passed": result.regression_passed,
            "duration_ms": result.duration_ms,
            "by_type": by_type,
        }
