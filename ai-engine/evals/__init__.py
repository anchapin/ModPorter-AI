"""
Portkit Evaluation System

Implements eval-driven recursive improvement for conversion quality.
Based on the auto-improving agent platform pattern.

Components:
- cases: Test cases with inputs, rubrics, and expected tool call sequences
- rubrics: Rubric-based evaluation scoring
- failure_map: Maps failure modes to fix locations
- hill_climb: The hill climb loop for iterative improvement
- runner: Orchestrates the full eval + hill-climb workflow
"""

from .cases import CaseType, EvalCase, EvalCaseLibrary, FailureMode, get_default_case_library
from .failure_map import FailureMapper, FixAction, FixLocation, FailureMapping
from .hill_climb import HillClimbLoop, HillClimbRun, HillClimbStatus, SimpleHillClimbEngine
from .rubrics import RubricCategory, RubricCheck, RubricEvaluator, RubricResult, RubricScore
from .runner import CaseResult, EvalSuite, EvalSuiteResult, EvalSuiteStatus

__all__ = [
    "CaseType",
    "EvalCase",
    "EvalCaseLibrary",
    "FailureMode",
    "get_default_case_library",
    "FailureMapper",
    "FixAction",
    "FixLocation",
    "FailureMapping",
    "HillClimbLoop",
    "HillClimbRun",
    "HillClimbStatus",
    "SimpleHillClimbEngine",
    "RubricCategory",
    "RubricCheck",
    "RubricEvaluator",
    "RubricResult",
    "RubricScore",
    "CaseResult",
    "EvalSuite",
    "EvalSuiteResult",
    "EvalSuiteStatus",
]