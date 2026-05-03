"""HTML exporter for QA reports."""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from qa.report.exporters.base import BaseExporter, ExportFormat
from qa.report.models import IssueSeverity, QAReport


class HTMLExporter(BaseExporter):
    """Exports QAReport to HTML format with Jinja2 templates."""

    def __init__(self, template_dir: Optional[str] = None):
        if template_dir is None:
            # Default to qa/templates relative to ai-engine/src
            template_dir = Path(__file__).parent.parent.parent / "templates"

        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Register custom filter for severity color
        self.env.filters["severity_color"] = self._severity_color

    @property
    def format(self) -> ExportFormat:
        return ExportFormat.HTML

    def export(self, report: QAReport, **options) -> str:
        """Export report as HTML string."""
        template_name = options.get("template", "report.html.j2")
        template = self.env.get_template(template_name)

        return template.render(report=report, severity_colors=self._get_severity_colors())

    def _severity_color(self, severity: IssueSeverity) -> str:
        """Get color for severity level."""
        return {
            IssueSeverity.INFO: "#3b82f6",  # blue
            IssueSeverity.WARNING: "#f59e0b",  # yellow
            IssueSeverity.ERROR: "#ef4444",  # red
            IssueSeverity.CRITICAL: "#7f1d1d",  # dark red
        }[severity]

    def _get_severity_colors(self) -> dict:
        """Get all severity colors."""
        return {s.value: self._severity_color(s) for s in IssueSeverity}
