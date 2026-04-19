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


class ConfidenceLevel(Enum):
    """Confidence level classification for segments."""

    HIGH = "high"
    SOFT_FLAG = "soft_flag"
    HARD_FLAG = "hard_flag"

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score >= 0.80:
            return cls.HIGH
        elif score >= 0.60:
            return cls.SOFT_FLAG
        else:
            return cls.HARD_FLAG


@dataclass
class SegmentConfidence:
    """Confidence scoring for a single converted code block."""

    block_id: str
    confidence: float
    review_flag: bool
    confidence_reasons: List[str] = field(default_factory=list)
    candidate_count: int = 0
    agreement_score: float = 0.0
    assertion_pass_rate: float = 0.0

    def __post_init__(self):
        self.confidence = max(0.0, min(1.0, self.confidence))
        self.confidence_level = ConfidenceLevel.from_score(self.confidence)

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.80

    @property
    def is_soft_flag(self) -> bool:
        return 0.60 <= self.confidence < 0.80

    @property
    def is_hard_flag(self) -> bool:
        return self.confidence < 0.60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "converted_code": None,
            "confidence": round(self.confidence, 2),
            "review_flag": self.review_flag,
            "confidence_reasons": self.confidence_reasons,
            "confidence_level": self.confidence_level.value,
        }


@dataclass
class ConfidenceDistribution:
    """Distribution of confidence levels across all segments."""

    high_confidence_count: int = 0
    soft_flag_count: int = 0
    hard_flag_count: int = 0
    total_segments: int = 0

    @property
    def high_confidence_pct(self) -> float:
        if self.total_segments == 0:
            return 0.0
        return (self.high_confidence_count / self.total_segments) * 100

    @property
    def soft_flag_pct(self) -> float:
        if self.total_segments == 0:
            return 0.0
        return (self.soft_flag_count / self.total_segments) * 100

    @property
    def hard_flag_pct(self) -> float:
        if self.total_segments == 0:
            return 0.0
        return (self.hard_flag_count / self.total_segments) * 100

    def to_histogram(self) -> Dict[str, float]:
        return {
            "high_confidence": self.high_confidence_pct,
            "soft_flag": self.soft_flag_pct,
            "hard_flag": self.hard_flag_pct,
        }


@dataclass
class QAReport:
    """Aggregated QA report from all agents."""

    job_id: str
    timestamp: datetime
    agent_results: List[AgentResult] = field(default_factory=list)
    quality_score: float = 0.0
    refinement_improvement: Optional[RefinementImprovement] = None
    confidence_segments: List[SegmentConfidence] = field(default_factory=list)
    confidence_distribution: Optional[ConfidenceDistribution] = None

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

    def get_flagged_segments(self) -> List[SegmentConfidence]:
        """Get all segments that need review."""
        return [s for s in self.confidence_segments if s.review_flag]

    def get_hard_flagged_segments(self) -> List[SegmentConfidence]:
        """Get segments with hard flags (manual conversion required)."""
        return [s for s in self.confidence_segments if s.is_hard_flag]

    def get_soft_flagged_segments(self) -> List[SegmentConfidence]:
        """Get segments with soft flags (review recommended)."""
        return [s for s in self.confidence_segments if s.is_soft_flag]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary with confidence info."""
        result = {
            "job_id": self.job_id,
            "timestamp": self.timestamp.isoformat(),
            "quality_score": round(self.quality_score, 2),
            "total_issues": self.total_issues,
            "confidence_summary": {
                "total_segments": len(self.confidence_segments),
                "high_confidence": sum(1 for s in self.confidence_segments if s.is_high_confidence),
                "soft_flag": sum(1 for s in self.confidence_segments if s.is_soft_flag),
                "hard_flag": sum(1 for s in self.confidence_segments if s.is_hard_flag),
                "histogram": self.confidence_distribution.to_histogram()
                if self.confidence_distribution
                else {},
            },
            "segments": [s.to_dict() for s in self.confidence_segments],
            "flagged_segments": [s.block_id for s in self.get_flagged_segments()],
        }
        return result
