"""Data models for QA Report Generator."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime


class IssueSeverity(Enum):
    """Severity levels for QA issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class IssueLocation:
    """Location information for an issue."""

    file: str
    line: int
    column: Optional[int] = None


@dataclass
class Issue:
    """Represents a single QA issue."""

    severity: IssueSeverity
    message: str
    location: Optional[IssueLocation] = None
    agent: Optional[str] = None
    code: Optional[str] = None


@dataclass
class AgentResult:
    """Result from a single QA agent."""

    agent_name: str
    score: float
    issues: List[Issue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityScore:
    """Quality score with weighted average calculation."""

    translator_score: float
    reviewer_score: float
    tester_score: float
    semantic_score: float
    weights: Dict[str, float] = None

    def __post_init__(self):
        if self.weights is None:
            self.weights = {"translator": 0.25, "reviewer": 0.25, "tester": 0.25, "semantic": 0.25}

    @property
    def overall(self) -> float:
        """Calculate weighted average of all agent scores."""
        return (
            self.translator_score * self.weights["translator"]
            + self.reviewer_score * self.weights["reviewer"]
            + self.tester_score * self.weights["tester"]
            + self.semantic_score * self.weights["semantic"]
        )


@dataclass
class RefinementImprovement:
    """Refinement improvement metrics."""

    initial_score: float
    final_score: float
    delta: float
    status: str
    iteration_count: int


@dataclass
class QAReport:
    """Aggregated QA report from all agents."""

    job_id: str
    timestamp: datetime
    agent_results: List[AgentResult] = field(default_factory=list)
    quality_score: float = 0.0
    refinement_improvement: Optional[RefinementImprovement] = None

    @property
    def total_issues(self) -> int:
        """Total number of issues across all agents."""
        return sum(len(r.issues) for r in self.agent_results)

    @property
    def issues_by_severity(self) -> Dict[IssueSeverity, List[Issue]]:
        """Group issues by severity level."""
        result: Dict[IssueSeverity, List[Issue]] = {s: [] for s in IssueSeverity}
        for agent_result in self.agent_results:
            for issue in agent_result.issues:
                result[issue.severity].append(issue)
        return result
