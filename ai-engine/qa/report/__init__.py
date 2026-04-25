"""QA Report Generator - aggregates results from all QA agents."""

from qa.report.aggregator import ResultAggregator, convert_agent_output
from qa.report.conformal_scorer import (
    CandidateGenerator,
    CandidateResult,
    ConformalScorer,
    create_candidate_result,
)
from qa.report.models import (
    AgentResult,
    ConfidenceDistribution,
    ConfidenceLevel,
    Issue,
    IssueLocation,
    IssueSeverity,
    QAReport,
    QualityScore,
    SegmentConfidence,
)
from qa.report.scorer import WeightedScorer

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
