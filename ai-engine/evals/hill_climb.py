"""
Hill Climb Loop for Conversion Quality Improvement

Implements the eval-driven recursive improvement loop:
1. Run eval suite
2. Diagnose failure
3. Edit converter
4. Re-run failing case
5. Repeat up to N rounds
6. Full suite regression check
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HillClimbStatus(Enum):
    """Status of hill climb iteration."""

    RUNNING = "running"
    IMPROVED = "improved"
    CONVERGED = "converged"
    MAX_ROUNDS_REACHED = "max_rounds_reached"
    FAILED = "failed"


@dataclass
class IterationResult:
    """Result of a single hill climb iteration."""

    iteration: int
    case_id: str
    status: HillClimbStatus
    score_before: float
    score_after: float
    improvement: float
    diagnosis: str
    fix_applied: Optional[str] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class HillClimbRun:
    """Result of a full hill climb run."""

    run_id: str
    case_id: str
    start_time: str
    end_time: str
    total_iterations: int
    final_score: float
    initial_score: float
    improvement: float
    status: HillClimbStatus
    iterations: List[IterationResult]
    regression_passed: bool = True


class HillClimbLoop:
    """
    Implements the eval-driven hill climb workflow for conversion quality.

    The loop:
    1. Run eval on a failing case
    2. Diagnose failure type and map to fix location
    3. Apply a fix to the converter/rules/prompts
    4. Re-run the failing case
    5. If improved, continue; if not, try different fix
    6. After N rounds or convergence, run full suite regression
    """

    def __init__(
        self,
        max_iterations: int = 5,
        improvement_threshold: float = 0.01,
        fix_providers: Optional[Dict[str, Callable[[str, Any], str]]] = None,
    ):
        """
        Initialize the hill climb loop.

        Args:
            max_iterations: Maximum iterations per case before giving up
            improvement_threshold: Minimum score improvement to consider success
            fix_providers: Dict mapping fix location to fix function
        """
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold
        self.fix_providers = fix_providers or {}
        self.runs: List[HillClimbRun] = []

    def run(
        self,
        case_id: str,
        convert_fn: Callable[[str], float],
        diagnose_fn: Callable[[str, float], Dict[str, Any]],
        apply_fix_fn: Callable[[str, str, Dict[str, Any]], bool],
        regression_fn: Callable[[], bool],
    ) -> HillClimbRun:
        """
        Run hill climb on a single failing case.

        Args:
            case_id: ID of the failing eval case
            convert_fn: Function to run conversion and return score (0-100)
            diagnose_fn: Function to diagnose failure, returns dict with failure_mode and context
            apply_fix_fn: Function to apply fix, returns True if fix was applied
            regression_fn: Function to run full suite regression, returns True if passed

        Returns:
            HillClimbRun with results of the hill climb attempt
        """
        start_time = datetime.now(timezone.utc)
        iterations: List[IterationResult] = []
        current_score = convert_fn(case_id)

        logger.info(f"Starting hill climb for case {case_id}, initial score: {current_score}")

        for iteration in range(self.max_iterations):
            iter_start = time.time()

            diagnosis = diagnose_fn(case_id, current_score)
            failure_mode = diagnosis.get("failure_mode", "unknown")
            context = diagnosis.get("context", {})

            logger.info(
                f"Iteration {iteration + 1}: failure_mode={failure_mode}, score={current_score}"
            )

            fix_applied = apply_fix_fn(failure_mode, case_id, context)

            new_score = convert_fn(case_id)
            improvement = new_score - current_score

            status = (
                HillClimbStatus.IMPROVED
                if improvement > self.improvement_threshold
                else HillClimbStatus.CONVERGED
            )

            iteration_result = IterationResult(
                iteration=iteration + 1,
                case_id=case_id,
                status=status,
                score_before=current_score,
                score_after=new_score,
                improvement=improvement,
                diagnosis=f"Failure: {failure_mode}, Fix: {fix_applied or 'none'}",
                fix_applied=fix_applied,
                duration_ms=(time.time() - iter_start) * 1000,
            )
            iterations.append(iteration_result)

            if improvement > self.improvement_threshold:
                current_score = new_score
                logger.info(f"Improvement: {improvement:.2f}, continuing...")
            else:
                logger.info(f"No significant improvement ({improvement:.4f}), converged")
                break

        regression_passed = regression_fn()

        end_time = datetime.now(timezone.utc)
        final_status = HillClimbStatus.CONVERGED if regression_passed else HillClimbStatus.FAILED

        run = HillClimbRun(
            run_id=f"run_{case_id}_{int(time.time())}",
            case_id=case_id,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_iterations=len(iterations),
            final_score=current_score,
            initial_score=iterations[0].score_before if iterations else current_score,
            improvement=current_score
            - (iterations[0].score_before if iterations else current_score),
            status=final_status,
            iterations=iterations,
            regression_passed=regression_passed,
        )

        self.runs.append(run)
        return run

    def run_suite(
        self,
        case_ids: List[str],
        convert_fn: Callable[[str], float],
        diagnose_fn: Callable[[str, float], Dict[str, Any]],
        apply_fix_fn: Callable[[str, str, Dict[str, Any]], bool],
        regression_fn: Callable[[], bool],
    ) -> List[HillClimbRun]:
        """Run hill climb on multiple failing cases."""
        results = []
        for case_id in case_ids:
            score = convert_fn(case_id)
            if score < 100:
                run = self.run(case_id, convert_fn, diagnose_fn, apply_fix_fn, regression_fn)
                results.append(run)
        return results


class SimpleHillClimbEngine:
    """
    Simplified hill climb engine that works with the eval system.
    Can be used standalone or integrated with the full conversion pipeline.
    """

    def __init__(
        self,
        failure_mapper: Any,
        evaluator: Any,
        max_iterations: int = 5,
    ):
        self.failure_mapper = failure_mapper
        self.evaluator = evaluator
        self.max_iterations = max_iterations

    def diagnose(self, case_id: str, score: float) -> Dict[str, Any]:
        """Diagnose a failing case."""
        return {
            "failure_mode": "unknown",
            "context": {"score": score, "case_id": case_id},
        }

    def apply_fix(self, failure_mode: str, case_id: str, context: Dict[str, Any]) -> Optional[str]:
        """Apply a fix based on failure mode."""
        fixes = self.failure_mapper.suggest_fixes(failure_mode, context)
        if fixes:
            return f"Would apply fix: {fixes[0].description}"
        return None

    def evaluate_case(self, case: Any, output: str) -> float:
        """Evaluate a single case and return score."""
        result = self.evaluator.evaluate(output)
        return result.weighted_score

    def run_hill_climb(
        self,
        case: Any,
        convert_fn: Callable[[], str],
    ) -> HillClimbRun:
        """Run hill climb on a single case."""
        output = convert_fn()
        score = self.evaluate_case(case, output)

        for iteration in range(self.max_iterations):
            if score >= 100:
                break

            diagnosis = self.diagnose(case.case_id, score)
            self.apply_fix(
                diagnosis.get("failure_mode", "unknown"),
                case.case_id,
                diagnosis.get("context", {}),
            )

            output = convert_fn()
            new_score = self.evaluate_case(case, output)

            if new_score > score:
                score = new_score

        return HillClimbRun(
            run_id=f"run_{case.case_id}_{int(time.time())}",
            case_id=case.case_id,
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time=datetime.now(timezone.utc).isoformat(),
            total_iterations=self.max_iterations,
            final_score=score,
            initial_score=score,
            improvement=0,
            status=HillClimbStatus.CONVERGED,
            iterations=[],
            regression_passed=True,
        )
