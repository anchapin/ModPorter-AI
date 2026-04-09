"""Markdown exporter for QA reports."""

from qa.report.models import QAReport, IssueSeverity
from qa.report.exporters.base import BaseExporter, ExportFormat


class MarkdownExporter(BaseExporter):
    """Exports QAReport to Markdown format."""

    @property
    def format(self) -> ExportFormat:
        return ExportFormat.MARKDOWN

    def export(self, report: QAReport, **options) -> str:
        """Export report as Markdown string."""
        lines = []

        # Header
        lines.append(f"# QA Report: {report.job_id}\n")
        lines.append(f"**Generated:** {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Quality Score
        score_emoji = self._score_emoji(report.quality_score)
        lines.append(f"## Quality Score {score_emoji}")
        lines.append(f"**{report.quality_score:.1f}%**\n")

        # Summary Table
        lines.append("## Agent Summary\n")
        lines.append("| Agent | Score | Issues |")
        lines.append("|-------|-------|--------|")
        for result in report.agent_results:
            lines.append(f"| {result.agent_name} | {result.score:.1f}% | {len(result.issues)} |")
        lines.append("")

        # Issues by Severity
        lines.append("## Issues\n")
        for severity in IssueSeverity:
            issues = report.issues_by_severity.get(severity, [])
            if issues:
                lines.append(f"### {severity.value.upper()} ({len(issues)})\n")
                for issue in issues:
                    file_loc = (
                        f"**{issue.location.file}:{issue.location.line}**"
                        if issue.location
                        else "**N/A**"
                    )
                    lines.append(f"- {file_loc}: {issue.message}")
                lines.append("")

        return "\n".join(lines)

    def _score_emoji(self, score: float) -> str:
        """Get emoji for score range."""
        if score >= 80:
            return "✅"
        elif score >= 60:
            return "⚠️"
        else:
            return "❌"
