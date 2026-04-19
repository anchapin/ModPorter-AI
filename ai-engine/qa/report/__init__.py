"""QA Report Generator - aggregates results from all QA agents."""

from qa.report.models import (
    QAReport,
    QualityScore,
    Issue,
    IssueSeverity,
    IssueLocation,
    AgentResult,
    SegmentConfidence,
    ConfidenceDistribution,
    ConfidenceLevel,
)
from qa.report.scorer import WeightedScorer
from qa.report.aggregator import ResultAggregator, convert_agent_output
from qa.report.conformal_scorer import (
    ConformalScorer,
    CandidateResult,
    create_candidate_result,
    CandidateGenerator,
)

__all__ = [
    "QAReport",
    "QualityScore",
    "Issue",
    "IssueSeverity",
    "IssueLocation",
    "AgentResult",
    "WeightedScorer",
    "ResultAggregator",
    "convert_agent_output",
    "SegmentConfidence",
    "ConfidenceDistribution",
    "ConfidenceLevel",
    "ConformalScorer",
    "CandidateResult",
    "create_candidate_result",
    "CandidateGenerator",
]
