"""Base exporter classes for QA reports."""

from abc import ABC, abstractmethod
from enum import Enum
from qa.report.models import QAReport


class ExportFormat(Enum):
    """Supported export formats for QA reports."""

    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


class BaseExporter(ABC):
    """Abstract base class for all report exporters."""

    @property
    @abstractmethod
    def format(self) -> ExportFormat:
        """Export format identifier."""
        pass

    @abstractmethod
    def export(self, report: QAReport, **options) -> str:
        """Export report to string in target format."""
        pass

    def get_content_type(self) -> str:
        """Get HTTP content type for this format."""
        return {
            ExportFormat.JSON: "application/json",
            ExportFormat.HTML: "text/html",
            ExportFormat.MARKDOWN: "text/markdown",
        }[self.format]
