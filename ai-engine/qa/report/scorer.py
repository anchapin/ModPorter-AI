"""Weighted quality score calculation."""

from dataclasses import dataclass
from typing import Dict, List
from qa.report.models import AgentResult, QualityScore


@dataclass
class WeightedScorer:
    """Calculates weighted quality scores from agent results."""

    weights: Dict[str, float] = None

    def __post_init__(self):
        if self.weights is None:
            self.weights = {"translator": 0.25, "reviewer": 0.25, "tester": 0.25, "semantic": 0.25}

    def calculate(self, agent_results: List[AgentResult]) -> QualityScore:
        """Calculate weighted quality score from agent results."""
        scores = {r.agent_name: r.score for r in agent_results}

        return QualityScore(
            translator_score=scores.get("translator", 0.0),
            reviewer_score=scores.get("reviewer", 0.0),
            tester_score=scores.get("tester", 0.0),
            semantic_score=scores.get("semantic", 0.0),
            weights=self.weights,
        )

    def set_weights(self, weights: Dict[str, float]):
        """Update weight distribution."""
        total = sum(weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        self.weights = weights
