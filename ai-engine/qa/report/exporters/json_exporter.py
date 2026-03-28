"""JSON exporter for QA reports."""

import json
from datetime import datetime
from typing import Dict, Any
from qa.report.models import QAReport, Issue, IssueSeverity, AgentResult
from qa.report.exporters.base import BaseExporter, ExportFormat


class JSONExporter(BaseExporter):
    """Exports QAReport to JSON format."""

    @property
    def format(self) -> ExportFormat:
        return ExportFormat.JSON

    def export(self, report: QAReport, **options) -> str:
        """Export report as JSON string."""
        indent = options.get("indent", 2)

        data = self._to_dict(report)

        return json.dumps(data, indent=indent, default=self._json_serializer)

    def _to_dict(self, report: QAReport) -> Dict[str, Any]:
        """Convert QAReport to dictionary."""
        return {
            "job_id": report.job_id,
            "timestamp": report.timestamp.isoformat(),
            "quality_score": report.quality_score,
            "total_issues": report.total_issues,
            "agent_results": [self._agent_result_to_dict(ar) for ar in report.agent_results],
            "issues_by_severity": {
                severity.value: len(issues)
                for severity, issues in report.issues_by_severity.items()
            },
        }

    def _agent_result_to_dict(self, result: AgentResult) -> Dict[str, Any]:
        """Convert AgentResult to dictionary."""
        return {
            "agent_name": result.agent_name,
            "score": result.score,
            "issue_count": len(result.issues),
            "issues": [self._issue_to_dict(i) for i in result.issues],
        }

    def _issue_to_dict(self, issue: Issue) -> Dict[str, Any]:
        """Convert Issue to dictionary."""
        return {
            "severity": issue.severity.value,
            "message": issue.message,
            "location": {
                "file": issue.location.file,
                "line": issue.location.line,
                "column": issue.location.column,
            }
            if issue.location
            else None,
            "agent": issue.agent,
            "code": issue.code,
        }

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for datetime."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
