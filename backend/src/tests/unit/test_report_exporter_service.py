import pytest
import json
from unittest.mock import MagicMock
from datetime import datetime, timezone
from services.report_exporter import ReportExporter
from schemas.report_types import (
    InteractiveReport,
    ReportMetadata,
    SummaryReport,
    FeatureAnalysis,
    AssumptionsReport,
    DeveloperLog,
)


@pytest.fixture
def mock_report():
    metadata = ReportMetadata(
        report_id="rep-123", job_id="job-123", generation_timestamp=datetime.now(timezone.utc)
    )

    summary = SummaryReport(
        overall_success_rate=85.0,
        total_features=10,
        converted_features=8,
        partially_converted_features=1,
        failed_features=1,
        assumptions_applied_count=5,
        processing_time_seconds=12.5,
        conversion_quality_score=0.9,
    )

    feature_analysis = MagicMock(spec=FeatureAnalysis)
    feature_analysis.features = []
    feature_analysis.compatibility_mapping_summary = "Good"
    feature_analysis.visual_comparisons_overview = "None"
    feature_analysis.impact_assessment_summary = "Low"

    assumptions_report = MagicMock(spec=AssumptionsReport)
    assumptions_report.assumptions = []
    assumptions_report.total_assumptions_count = 0

    developer_log = MagicMock(spec=DeveloperLog)

    report = InteractiveReport(
        metadata=metadata,
        summary=summary,
        feature_analysis=feature_analysis,
        assumptions_report=assumptions_report,
        developer_log=developer_log,
    )

    # Mock to_dict because it's used in exporters
    report.to_dict = MagicMock(
        return_value={
            "metadata": {"job_id": "job-123", "version": "2.0.0"},
            "summary": {
                "overall_success_rate": 85.0,
                "total_features": 10,
                "converted_features": 8,
                "assumptions_applied_count": 5,
                "processing_time_seconds": 12.5,
                "conversion_quality_score": 0.9,
                "manual_work_estimate_hours": 2.5,
                "priority_order": "fabric,forge",
            },
            "feature_analysis": {
                "compatibility_mapping_summary": "Good",
                "impact_assessment_summary": "Low",
                "features": [],
            },
            "assumptions_report": {"total_assumptions_count": 0, "assumptions": []},
        }
    )

    return report


@pytest.fixture
def exporter():
    return ReportExporter()


def test_report_exporter_init(exporter):
    assert exporter.supported_formats == ["json", "html", "csv"]


def test_export_to_json(exporter, mock_report):
    result = exporter.export_to_json(mock_report)

    assert isinstance(result, str)
    decoded = json.loads(result)
    assert decoded["metadata"]["job_id"] == "job-123"


def test_export_to_html(exporter, mock_report):
    result = exporter.export_to_html(mock_report)

    assert isinstance(result, str)
    assert "<html" in result.lower()
    assert "job-123" in result
    assert "85.0%" in result
    assert "2.5h" in result


def test_export_to_csv(exporter, mock_report):
    result = exporter.export_to_csv(mock_report)

    assert isinstance(result, str)
    assert "Section,Metric,Value" in result
    assert "Summary,Overall Success Rate,85.0%" in result


def test_create_shareable_link(exporter):
    link = exporter.create_shareable_link("rep-123", "https://test.ai")
    assert link == "https://test.ai/reports/rep-123"


def test_generate_download_package(exporter, mock_report):
    package = exporter.generate_download_package(mock_report)

    assert "report.json" in package
    assert "report.html" in package
    assert "summary.csv" in package
    assert "metadata.json" in package


def test_escape_report_data(exporter):
    data = "<script>alert('xss')</script>"
    escaped = exporter._escape_report_data(data)
    assert "&lt;script&gt;" in escaped
