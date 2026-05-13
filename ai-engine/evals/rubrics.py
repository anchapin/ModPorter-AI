"""
Rubric evaluation framework for Portkit conversion quality.

Defines rubric-based evaluation criteria and scoring for conversion outputs.
"""

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class RubricCategory(Enum):
    """Categories of rubric checks."""

    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    FORMAT = "format"
    STYLE = "style"
    PERFORMANCE = "performance"


class RubricSeverity(Enum):
    """Severity of rubric failure."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class RubricCheck:
    """A single rubric evaluation check."""

    check_id: str
    name: str
    description: str
    category: RubricCategory
    severity: RubricSeverity
    weight: float = 1.0
    validator: Optional[Callable[[str], bool]] = None


@dataclass
class RubricResult:
    """Result of a rubric evaluation."""

    check_id: str
    check_name: str
    passed: bool
    score: float
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class RubricScore:
    """Overall rubric evaluation score."""

    total_checks: int
    passed_checks: int
    failed_checks: int
    weighted_score: float
    category_scores: Dict[RubricCategory, float]
    results: List[RubricResult]
    timestamp: str


class RubricEvaluator:
    """Evaluates conversion output against defined rubrics."""

    def __init__(self):
        self.checks: List[RubricCheck] = []
        self._register_default_checks()

    def _register_default_checks(self):
        self.checks = [
            RubricCheck(
                check_id="json_valid",
                name="Valid JSON Structure",
                description="Output must be valid JSON",
                category=RubricCategory.FORMAT,
                severity=RubricSeverity.CRITICAL,
                weight=2.0,
            ),
            RubricCheck(
                check_id="identifier_format",
                name="Correct Identifier Format",
                description="Block/item/entity identifiers follow modid:name format",
                category=RubricCategory.FORMAT,
                severity=RubricSeverity.CRITICAL,
                weight=1.5,
            ),
            RubricCheck(
                check_id="format_version",
                name="Format Version Present",
                description="All Bedrock definition files have format_version",
                category=RubricCategory.FORMAT,
                severity=RubricSeverity.CRITICAL,
                weight=1.5,
            ),
            RubricCheck(
                check_id="component_completeness",
                name="Component Completeness",
                description="All required components are present",
                category=RubricCategory.COMPLETENESS,
                severity=RubricSeverity.WARNING,
                weight=1.0,
            ),
            RubricCheck(
                check_id="behavior_preserved",
                name="Behavior Preservation",
                description="Java behavior is correctly translated to Bedrock",
                category=RubricCategory.CORRECTNESS,
                severity=RubricSeverity.CRITICAL,
                weight=2.0,
            ),
            RubricCheck(
                check_id="bedrock_idioms",
                name="Bedrock Idioms",
                description="Output follows Bedrock scripting idioms",
                category=RubricCategory.STYLE,
                severity=RubricSeverity.INFO,
                weight=0.5,
            ),
            RubricCheck(
                check_id="no_hallucination",
                name="No Hallucination",
                description="No fabricated or non-existent references",
                category=RubricCategory.CORRECTNESS,
                severity=RubricSeverity.CRITICAL,
                weight=2.0,
            ),
        ]

    def evaluate(self, output: str, expected_output: Optional[str] = None) -> RubricScore:
        """Evaluate output against all registered rubrics."""
        from datetime import datetime, timezone

        results = []
        category_scores: Dict[RubricCategory, List[float]] = {cat: [] for cat in RubricCategory}

        for check in self.checks:
            result = self._run_check(check, output, expected_output)
            results.append(result)

            score = result.score if result.passed else 0.0
            category_scores[check.category].append(score * check.weight)

        passed = sum(1 for r in results if r.passed)
        total_weighted = sum(sum(scores) for scores in category_scores.values())
        max_weighted = sum(c.weight for c in self.checks)

        weighted_score = (total_weighted / max_weighted * 100) if max_weighted > 0 else 0.0

        final_category_scores = {}
        for cat, scores in category_scores.items():
            if scores:
                final_category_scores[cat] = sum(scores) / len(scores) * 100
            else:
                final_category_scores[cat] = 0.0

        return RubricScore(
            total_checks=len(results),
            passed_checks=passed,
            failed_checks=len(results) - passed,
            weighted_score=weighted_score,
            category_scores=final_category_scores,
            results=results,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _run_check(
        self, check: RubricCheck, output: str, expected_output: Optional[str]
    ) -> RubricResult:
        """Run a single rubric check."""
        try:
            if check.check_id == "json_valid":
                json.loads(output)
                return RubricResult(check.check_id, check.name, True, 1.0, "Valid JSON")
        except json.JSONDecodeError as e:
            return RubricResult(
                check.check_id,
                check.name,
                False,
                0.0,
                f"Invalid JSON: {str(e)}",
                {"error": str(e)},
            )

        if check.check_id == "identifier_format":
            pattern = r'"?[a-z][a-z0-9_]*:[a-z][a-z0-9_]*"?'
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                return RubricResult(check.check_id, check.name, True, 1.0, "Identifier format OK")
            else:
                return RubricResult(check.check_id, check.name, False, 0.0, "No identifiers found")

        if check.check_id == "format_version":
            if re.search(r'"format_version"\s*:\s*"[\d.]+"', output):
                return RubricResult(check.check_id, check.name, True, 1.0, "Format version found")
            return RubricResult(check.check_id, check.name, False, 0.0, "No format_version found")

        if check.check_id == "no_hallucination":
            known_terms = ["minecraft:", "format_version", "components", "events", "states"]
            found = any(term in output for term in known_terms)
            if found:
                return RubricResult(
                    check.check_id, check.name, True, 1.0, "No obvious hallucination"
                )
            return RubricResult(
                check.check_id, check.check_id, False, 0.0, "Possible hallucination detected"
            )

        return RubricResult(check.check_id, check.name, True, 0.5, "Check completed (generic)")

    def add_check(self, check: RubricCheck) -> None:
        self.checks.append(check)

    def get_checks(self) -> List[RubricCheck]:
        return self.checks.copy()
