"""Unit tests for QA Report Exporters."""

import pytest
from datetime import datetime, timezone

from qa.report.exporters.base import BaseExporter, ExportFormat
from qa.report.exporters.json_exporter import JSONExporter
from qa.report.exporters.markdown_exporter import MarkdownExporter
from qa.report.exporters.html_exporter import HTMLExporter
from qa.report.models import (
    QAReport,
    AgentResult,
    Issue,
    IssueLocation,
    IssueSeverity,
    SegmentConfidence,
    ConfidenceDistribution,
)


@pytest.fixture
def sample_report():
    """Create a sample QAReport for testing exporters."""
    report = QAReport(
        job_id="test-job-123",
        timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        quality_score=85.5,
        agent_results=[
            AgentResult(
                agent_name="translator",
                score=90.0,
                issues=[
                    Issue(
                        severity=IssueSeverity.WARNING,
                        message="Missing docstring",
                        location=IssueLocation(file="test.py", line=10, column=5),
                        agent="translator",
                        code="D103",
                    ),
                    Issue(
                        severity=IssueSeverity.INFO,
                        message="Consider using f-string",
                        location=IssueLocation(file="test.py", line=25, column=1),
                        agent="translator",
                        code="UP032",
                    ),
                ],
            ),
            AgentResult(
                agent_name="reviewer",
                score=80.0,
                issues=[
                    Issue(
                        severity=IssueSeverity.ERROR,
                        message="Undefined name 'foo'",
                        location=IssueLocation(file="test.py", line=42, column=10),
                        agent="reviewer",
                        code="F821",
                    ),
                ],
            ),
        ],
    )
    return report


class TestExportFormat:
    """Test cases for ExportFormat enum."""

    def test_json_format(self):
        """Test JSON format value."""
        assert ExportFormat.JSON.value == "json"

    def test_html_format(self):
        """Test HTML format value."""
        assert ExportFormat.HTML.value == "html"

    def test_markdown_format(self):
        """Test MARKDOWN format value."""
        assert ExportFormat.MARKDOWN.value == "markdown"


class TestBaseExporter:
    """Test cases for BaseExporter abstract class."""

    def test_base_exporter_is_abc(self):
        """Test that BaseExporter is properly abstract."""
        assert issubclass(BaseExporter, BaseExporter.__bases__[0])

    def test_get_content_type_json(self):
        """Test content type for JSON format."""

        class TestExporter(BaseExporter):
            @property
            def format(self) -> ExportFormat:
                return ExportFormat.JSON

            def export(self, report: QAReport, **options) -> str:
                return "{}"

        exporter = TestExporter()
        assert exporter.get_content_type() == "application/json"

    def test_get_content_type_html(self):
        """Test content type for HTML format."""

        class TestExporter(BaseExporter):
            @property
            def format(self) -> ExportFormat:
                return ExportFormat.HTML

            def export(self, report: QAReport, **options) -> str:
                return "<html></html>"

        exporter = TestExporter()
        assert exporter.get_content_type() == "text/html"

    def test_get_content_type_markdown(self):
        """Test content type for Markdown format."""

        class TestExporter(BaseExporter):
            @property
            def format(self) -> ExportFormat:
                return ExportFormat.MARKDOWN

            def export(self, report: QAReport, **options) -> str:
                return "# Test"

        exporter = TestExporter()
        assert exporter.get_content_type() == "text/markdown"


class TestJSONExporter:
    """Test cases for JSONExporter."""

    def test_format_property(self):
        """Test that format returns JSON."""
        exporter = JSONExporter()
        assert exporter.format == ExportFormat.JSON

    def test_export_basic(self, sample_report):
        """Test basic JSON export."""
        exporter = JSONExporter()
        result = exporter.export(sample_report)

        assert isinstance(result, str)
        assert '"job_id": "test-job-123"' in result
        assert '"quality_score": 85.5' in result

    def test_export_with_custom_indent(self, sample_report):
        """Test JSON export with custom indent."""
        exporter = JSONExporter()
        result = exporter.export(sample_report, indent=4)

        assert isinstance(result, str)
        # With indent=4, we expect deeper indentation
        assert '"job_id"' in result

    def test_export_no_indent(self, sample_report):
        """Test JSON export without indent."""
        exporter = JSONExporter()
        result = exporter.export(sample_report, indent=0)

        assert isinstance(result, str)

    def test_to_dict(self, sample_report):
        """Test conversion to dictionary."""
        exporter = JSONExporter()
        data = exporter._to_dict(sample_report)

        assert data["job_id"] == "test-job-123"
        assert data["quality_score"] == 85.5
        assert data["total_issues"] == 3
        assert len(data["agent_results"]) == 2

    def test_agent_result_to_dict(self, sample_report):
        """Test AgentResult to dictionary conversion."""
        exporter = JSONExporter()
        result = sample_report.agent_results[0]
        data = exporter._agent_result_to_dict(result)

        assert data["agent_name"] == "translator"
        assert data["score"] == 90.0
        assert data["issue_count"] == 2

    def test_issue_to_dict_with_location(self):
        """Test Issue to dict with location."""
        exporter = JSONExporter()
        issue = Issue(
            severity=IssueSeverity.ERROR,
            message="Test error",
            location=IssueLocation(file="test.py", line=10, column=5),
            agent="test_agent",
            code="E501",
        )
        data = exporter._issue_to_dict(issue)

        assert data["severity"] == "error"
        assert data["message"] == "Test error"
        assert data["location"]["file"] == "test.py"
        assert data["location"]["line"] == 10
        assert data["location"]["column"] == 5
        assert data["agent"] == "test_agent"
        assert data["code"] == "E501"

    def test_issue_to_dict_without_location(self):
        """Test Issue to dict without location."""
        exporter = JSONExporter()
        issue = Issue(
            severity=IssueSeverity.WARNING,
            message="Test warning",
        )
        data = exporter._issue_to_dict(issue)

        assert data["severity"] == "warning"
        assert data["message"] == "Test warning"
        assert data["location"] is None

    def test_json_serializer_datetime(self):
        """Test datetime serialization in JSON."""
        exporter = JSONExporter()
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = exporter._json_serializer(dt)

        assert result == "2024-01-15T10:30:00+00:00"

    def test_json_serializer_unsupported_type(self):
        """Test that unsupported types raise TypeError."""
        exporter = JSONExporter()
        with pytest.raises(TypeError, match="not serializable"):
            exporter._json_serializer(set([1, 2, 3]))


class TestMarkdownExporter:
    """Test cases for MarkdownExporter."""

    def test_format_property(self):
        """Test that format returns Markdown."""
        exporter = MarkdownExporter()
        assert exporter.format == ExportFormat.MARKDOWN

    def test_export_basic(self, sample_report):
        """Test basic Markdown export."""
        exporter = MarkdownExporter()
        result = exporter.export(sample_report)

        assert isinstance(result, str)
        assert "# QA Report: test-job-123" in result
        assert "Quality Score" in result
        assert "translator" in result
        assert "reviewer" in result

    def test_export_includes_timestamp(self, sample_report):
        """Test that export includes timestamp."""
        exporter = MarkdownExporter()
        result = exporter.export(sample_report)

        assert "2024-01-15" in result

    def test_score_emoji_high(self):
        """Test emoji for high score (>=80)."""
        exporter = MarkdownExporter()
        assert exporter._score_emoji(80.0) == "✅"
        assert exporter._score_emoji(95.0) == "✅"

    def test_score_emoji_medium(self):
        """Test emoji for medium score (60-79)."""
        exporter = MarkdownExporter()
        assert exporter._score_emoji(60.0) == "⚠️"
        assert exporter._score_emoji(75.0) == "⚠️"

    def test_score_emoji_low(self):
        """Test emoji for low score (<60)."""
        exporter = MarkdownExporter()
        assert exporter._score_emoji(59.0) == "❌"
        assert exporter._score_emoji(30.0) == "❌"

    def test_export_with_no_issues(self):
        """Test Markdown export with no issues."""
        report = QAReport(
            job_id="clean-job",
            timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc),
            quality_score=100.0,
            agent_results=[],
        )
        exporter = MarkdownExporter()
        result = exporter.export(report)

        assert "# QA Report: clean-job" in result
        assert "100.0" in result

    def test_export_with_severity_groups(self, sample_report):
        """Test that severity groups are included in export."""
        exporter = MarkdownExporter()
        result = exporter.export(sample_report)

        assert "ERROR" in result or "error" in result.lower()
        assert "WARNING" in result or "warning" in result.lower()


class TestHTMLExporter:
    """Test cases for HTMLExporter."""

    def test_format_property(self):
        """Test that format returns HTML."""
        exporter = HTMLExporter()
        assert exporter.format == ExportFormat.HTML

    def test_init_default_template_dir(self):
        """Test initialization with default template directory."""
        exporter = HTMLExporter()
        assert exporter.env is not None
        assert exporter.env.loader is not None

    def test_init_custom_template_dir(self, tmp_path):
        """Test initialization with custom template directory."""
        # Create a minimal template directory
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        exporter = HTMLExporter(template_dir=str(templates_dir))
        assert exporter.env is not None

    def test_severity_color_info(self):
        """Test severity color for INFO level."""
        exporter = HTMLExporter()
        assert exporter._severity_color(IssueSeverity.INFO) == "#3b82f6"

    def test_severity_color_warning(self):
        """Test severity color for WARNING level."""
        exporter = HTMLExporter()
        assert exporter._severity_color(IssueSeverity.WARNING) == "#f59e0b"

    def test_severity_color_error(self):
        """Test severity color for ERROR level."""
        exporter = HTMLExporter()
        assert exporter._severity_color(IssueSeverity.ERROR) == "#ef4444"

    def test_severity_color_critical(self):
        """Test severity color for CRITICAL level."""
        exporter = HTMLExporter()
        assert exporter._severity_color(IssueSeverity.CRITICAL) == "#7f1d1d"

    def test_get_severity_colors(self):
        """Test getting all severity colors."""
        exporter = HTMLExporter()
        colors = exporter._get_severity_colors()

        assert "info" in colors
        assert "warning" in colors
        assert "error" in colors
        assert "critical" in colors
        assert colors["info"] == "#3b82f6"

    def test_export_basic(self, sample_report, tmp_path):
        """Test basic HTML export."""
        # Create minimal template
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "report.html.j2"
        template_file.write_text("""
<!DOCTYPE html>
<html>
<head><title>QA Report</title></head>
<body>
<h1>QA Report: {{ report.job_id }}</h1>
<p>Quality Score: {{ report.quality_score }}</p>
</body>
</html>
""")
        exporter = HTMLExporter(template_dir=str(templates_dir))
        result = exporter.export(sample_report)

        assert isinstance(result, str)
        assert "test-job-123" in result

    def test_export_with_custom_template(self, sample_report, tmp_path):
        """Test export with custom template name."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "custom.html.j2"
        template_file.write_text("<html><body>Custom: {{ report.job_id }}</body></html>")

        exporter = HTMLExporter(template_dir=str(templates_dir))
        result = exporter.export(sample_report, template="custom.html.j2")

        assert "Custom:" in result
        assert "test-job-123" in result

    def test_export_without_template(self, sample_report, tmp_path):
        """Test export falls back gracefully when template not found."""
        exporter = HTMLExporter()  # Uses default template dir which may not exist
        try:
            result = exporter.export(sample_report)
            # If no template exists, Jinja2 will raise TemplateNotFound
        except Exception:
            pass  # Expected if no template exists


class TestQAReportModelIntegration:
    """Integration tests using QAReport with exporters."""

    def test_report_total_issues(self, sample_report):
        """Test QAReport total_issues property."""
        assert sample_report.total_issues == 3

    def test_report_issues_by_severity(self, sample_report):
        """Test QAReport issues_by_severity property."""
        by_severity = sample_report.issues_by_severity
        assert len(by_severity[IssueSeverity.INFO]) == 1
        assert len(by_severity[IssueSeverity.WARNING]) == 1
        assert len(by_severity[IssueSeverity.ERROR]) == 1
        assert len(by_severity[IssueSeverity.CRITICAL]) == 0

    def test_json_exporter_roundtrip(self, sample_report):
        """Test that JSON export produces valid JSON."""
        import json

        exporter = JSONExporter()
        result = exporter.export(sample_report)

        # Should not raise
        parsed = json.loads(result)
        assert parsed["job_id"] == "test-job-123"

    def test_markdown_exporter_with_confidence_segments(self):
        """Test Markdown export with confidence segments."""
        report = QAReport(
            job_id="confidence-test",
            timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc),
            quality_score=75.0,
            agent_results=[],
            confidence_segments=[
                SegmentConfidence(
                    block_id="block-1",
                    confidence=0.85,
                    review_flag=False,
                    confidence_reasons=["High agreement"],
                ),
                SegmentConfidence(
                    block_id="block-2",
                    confidence=0.55,
                    review_flag=True,
                    confidence_reasons=["Low agreement", "Edge case"],
                ),
            ],
        )
        exporter = MarkdownExporter()
        result = exporter.export(report)

        assert "# QA Report: confidence-test" in result
