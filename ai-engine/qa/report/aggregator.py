"""Result aggregation for QA reports."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from qa.report.models import (
    Issue,
    IssueSeverity,
    IssueLocation,
    AgentResult,
    QAReport,
    SegmentConfidence,
    ConfidenceDistribution,
)
from qa.report.scorer import WeightedScorer


def parse_issue(issue_dict: Dict[str, Any], agent_name: str) -> Issue:
    """Parse issue dict from agent output into Issue object."""
    severity_str = issue_dict.get("severity", "info").lower()
    severity = (
        IssueSeverity(severity_str)
        if severity_str in [s.value for s in IssueSeverity]
        else IssueSeverity.INFO
    )

    location = None
    if "location" in issue_dict:
        loc = issue_dict["location"]
        location = IssueLocation(
            file=loc.get("file", ""), line=loc.get("line", 0), column=loc.get("column")
        )

    return Issue(
        severity=severity,
        message=issue_dict.get("message", ""),
        location=location,
        agent=agent_name,
        code=issue_dict.get("code"),
    )


def convert_agent_output(agent_name: str, output: Dict[str, Any]) -> AgentResult:
    """Convert raw agent output dict to AgentResult."""
    issues = [parse_issue(i, agent_name) for i in output.get("issues", [])]

    return AgentResult(
        agent_name=agent_name, score=output.get("score", 0.0), issues=issues, metadata=output
    )


class ResultAggregator:
    """Aggregates agent outputs into QAReport."""

    def __init__(self, scorer: WeightedScorer = None):
        self.scorer = scorer or WeightedScorer()

    def aggregate(self, job_id: str, agent_outputs: Dict[str, Dict[str, Any]]) -> QAReport:
        """Aggregate agent outputs into QAReport."""
        agent_results: List[AgentResult] = []
        for agent_name, output in agent_outputs.items():
            agent_results.append(convert_agent_output(agent_name, output))

        quality_score = self.scorer.calculate(agent_results)

        return QAReport(
            job_id=job_id,
            timestamp=datetime.now(),
            agent_results=agent_results,
            quality_score=quality_score.overall,
        )

    def aggregate_partial(self, job_id: str, agent_outputs: Dict[str, Dict[str, Any]]) -> QAReport:
        """Aggregate with graceful handling of missing agents."""
        agent_results: List[AgentResult] = []

        for agent_name, output in agent_outputs.items():
            agent_results.append(convert_agent_output(agent_name, output))

        if not agent_results:
            return QAReport(job_id=job_id, timestamp=datetime.now())

        quality_score = self.scorer.calculate(agent_results)

        return QAReport(
            job_id=job_id,
            timestamp=datetime.now(),
            agent_results=agent_results,
            quality_score=quality_score.overall,
        )

    def aggregate_with_confidence(
        self,
        job_id: str,
        agent_outputs: Dict[str, Dict[str, Any]],
        confidence_segments: List[SegmentConfidence],
        confidence_distribution: ConfidenceDistribution,
    ) -> QAReport:
        """Aggregate agent outputs with confidence scoring."""
        agent_results: List[AgentResult] = []
        for agent_name, output in agent_outputs.items():
            agent_results.append(convert_agent_output(agent_name, output))

        quality_score = self.scorer.calculate(agent_results)

        return QAReport(
            job_id=job_id,
            timestamp=datetime.now(),
            agent_results=agent_results,
            quality_score=quality_score.overall,
            confidence_segments=confidence_segments,
            confidence_distribution=confidence_distribution,
        )
