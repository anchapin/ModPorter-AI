"""
Tests for Report Generator (Phase 12-05)
"""

import pytest
import sys
import os
import json

# Add ai-engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))

from report_generator import (
    ReportGenerator,
    ReportBuilder,
    ReportFormat,
    EnhancedConversionReport,
    ConversionMetadata,
    FileMetrics,
    QualityMetrics,
    RecommendationItem,
    ConversionResult,
    create_sample_report,
)


class TestConversionMetadata:
    """Tests for ConversionMetadata."""

    def test_create_metadata(self):
        """Test creating conversion metadata."""
        meta = ConversionMetadata(
            conversion_id="test-123",
            mod_name="TestMod",
            complexity="complex"
        )
        
        assert meta.conversion_id == "test-123"
        assert meta.mod_name == "TestMod"
        assert meta.complexity == "complex"


class TestFileMetrics:
    """Tests for FileMetrics."""

    def test_create_file_metrics(self):
        """Test creating file metrics."""
        metrics = FileMetrics(
            total_files=10,
            converted_files=8,
            failed_files=2,
            total_functions=50,
            converted_functions=45
        )
        
        assert metrics.total_files == 10
        assert metrics.converted_files == 8


class TestQualityMetrics:
    """Tests for QualityMetrics."""

    def test_create_quality_metrics(self):
        """Test creating quality metrics."""
        metrics = QualityMetrics(
            overall_score=85.5,
            quality_level="good",
            syntax_score=100.0,
            semantic_score=82.0,
            behavior_score=78.0,
            completeness_score=90.0,
            critical_issues=1,
            major_issues=2,
            minor_issues=3
        )
        
        assert metrics.overall_score == 85.5
        assert metrics.quality_level == "good"


class TestEnhancedConversionReport:
    """Tests for EnhancedConversionReport."""

    def test_create_report(self):
        """Test creating a report."""
        report = EnhancedConversionReport(
            result=ConversionResult.SUCCESS.value,
            metadata=ConversionMetadata("test", "TestMod", "standard"),
            file_metrics=FileMetrics(total_files=5, converted_files=5),
            quality_metrics=QualityMetrics(overall_score=95.0, quality_level="excellent")
        )
        
        assert report.result == "success"
        assert report.metadata.mod_name == "TestMod"

    def test_to_dict(self):
        """Test converting report to dictionary."""
        report = EnhancedConversionReport(
            result=ConversionResult.SUCCESS.value,
            metadata=ConversionMetadata("test", "TestMod", "simple"),
            file_metrics=FileMetrics(total_files=3, converted_files=2),
            quality_metrics=QualityMetrics(overall_score=80.0, quality_level="good")
        )
        
        d = report.to_dict()
        
        assert d["result"] == "success"
        assert d["metadata"]["mod_name"] == "TestMod"
        assert d["file_metrics"]["total_files"] == 3


class TestReportBuilder:
    """Tests for ReportBuilder fluent API."""

    def test_builder_basic(self):
        """Test basic report building."""
        report = (ReportBuilder()
            .with_metadata("conv-1", "MyMod", "standard")
            .with_result(ConversionResult.SUCCESS.value)
            .build())
        
        assert report.metadata.conversion_id == "conv-1"
        assert report.result == "success"

    def test_builder_with_file_metrics(self):
        """Test adding file metrics."""
        report = (ReportBuilder()
            .with_metadata("conv-1", "MyMod")
            .with_result(ConversionResult.SUCCESS.value)
            .with_file_metrics(total=10, converted=8, failed=2)
            .build())
        
        assert report.file_metrics.total_files == 10
        assert report.file_metrics.converted_files == 8
        assert report.file_metrics.failed_files == 2

    def test_builder_with_quality_metrics(self):
        """Test adding quality metrics."""
        report = (ReportBuilder()
            .with_metadata("conv-1", "MyMod")
            .with_result(ConversionResult.SUCCESS.value)
            .with_quality_metrics(overall=85.5, level="good")
            .build())
        
        assert report.quality_metrics.overall_score == 85.5
        assert report.quality_metrics.quality_level == "good"

    def test_builder_with_issues(self):
        """Test adding issues."""
        report = (ReportBuilder()
            .with_metadata("conv-1", "MyMod")
            .with_result(ConversionResult.SUCCESS.value)
            .with_issue("syntax", "critical", "Missing bracket")
            .with_issue("behavior", "major", "Event not mapped")
            .build())
        
        assert len(report.issues) == 2
        assert report.issues[0]["severity"] == "critical"

    def test_builder_with_recommendations(self):
        """Test adding recommendations."""
        report = (ReportBuilder()
            .with_metadata("conv-1", "MyMod")
            .with_result(ConversionResult.SUCCESS.value)
            .with_recommendation(1, "Fix Issues", "Fix the critical issues", "High", "Medium")
            .build())
        
        assert len(report.recommendations) == 1
        assert report.recommendations[0].priority == 1


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_generate_json(self):
        """Test JSON generation."""
        report = create_sample_report()
        generator = ReportGenerator()
        
        json_output = generator.generate_json(report)
        
        # Should be valid JSON
        data = json.loads(json_output)
        assert "result" in data
        assert "quality_metrics" in data

    def test_generate_html(self):
        """Test HTML generation."""
        report = create_sample_report()
        generator = ReportGenerator()
        
        html_output = generator.generate_html(report)
        
        assert "<!DOCTYPE html>" in html_output
        assert "Conversion Report" in html_output
        assert "<div class=\"card\">" in html_output

    def test_generate_markdown(self):
        """Test Markdown generation."""
        report = create_sample_report()
        generator = ReportGenerator()
        
        md_output = generator.generate_markdown(report)
        
        assert "Conversion Report" in md_output
        assert "##" in md_output  # Section headers exist
        assert "Overall Score" in md_output

    def test_generate_with_format(self):
        """Test generate with format parameter."""
        report = create_sample_report()
        generator = ReportGenerator()
        
        json_out = generator.generate(report, "json")
        html_out = generator.generate(report, "html")
        md_out = generator.generate(report, "markdown")
        
        assert "{" in json_out
        assert "<!DOCTYPE html>" in html_out
        assert "Conversion Report" in md_out


class TestConversionResult:
    """Tests for ConversionResult enum."""

    def test_values(self):
        """Test enum values."""
        assert ConversionResult.SUCCESS.value == "success"
        assert ConversionResult.PARTIAL_SUCCESS.value == "partial_success"
        assert ConversionResult.FAILED.value == "failed"


class TestReportFormat:
    """Tests for ReportFormat enum."""

    def test_values(self):
        """Test enum values."""
        assert ReportFormat.JSON.value == "json"
        assert ReportFormat.HTML.value == "html"
        assert ReportFormat.MARKDOWN.value == "markdown"


class TestCreateSampleReport:
    """Tests for create_sample_report function."""

    def test_create_sample(self):
        """Test creating sample report."""
        report = create_sample_report()
        
        assert report.metadata is not None
        assert report.file_metrics is not None
        assert report.quality_metrics is not None
        assert len(report.issues) > 0
        assert len(report.recommendations) > 0


class TestReportContent:
    """Tests for report content in different formats."""

    def test_json_contains_all_fields(self):
        """Test JSON output contains all expected fields."""
        report = create_sample_report()
        generator = ReportGenerator()
        
        json_output = generator.generate_json(report)
        data = json.loads(json_output)
        
        assert "report_version" in data
        assert "generated_at" in data
        assert "metadata" in data
        assert "result" in data
        assert "file_metrics" in data
        assert "quality_metrics" in data
        assert "issues" in data
        assert "recommendations" in data

    def test_html_contains_scores(self):
        """Test HTML output contains score displays."""
        report = create_sample_report()
        generator = ReportGenerator()
        
        html_output = generator.generate_html(report)
        
        assert "Quality Scores" in html_output
        assert "File Metrics" in html_output

    def test_markdown_contains_sections(self):
        """Test Markdown output contains all sections."""
        report = create_sample_report()
        generator = ReportGenerator()
        
        md_output = generator.generate_markdown(report)
        
        assert "Summary" in md_output
        assert "File Metrics" in md_output
        assert "Quality Scores" in md_output


class TestReportBuilderChaining:
    """Tests for builder method chaining."""

    def test_full_chain(self):
        """Test building complete report with all features."""
        report = (ReportBuilder()
            .with_metadata("conv-999", "FullTestMod", "complex")
            .with_result(ConversionResult.PARTIAL_SUCCESS.value)
            .with_file_metrics(
                total=20, converted=15, failed=3, skipped=2,
                total_funcs=100, converted_funcs=80, failed_funcs=20
            )
            .with_quality_metrics(
                overall=72.5, level="good",
                syntax=95, semantic=70, behavior=65, completeness=75,
                critical=1, major=3, minor=5
            )
            .with_issue("syntax", "critical", "Parse error in file.js")
            .with_issue("behavior", "major", "Missing event handler")
            .with_recommendation(1, "Fix Critical", "Fix the parse error", "High", "Low")
            .with_assumption("Java 11 compatibility")
            .with_warning("Uses deprecated API")
            .with_duration(180.5)
            .build())
        
        assert report.metadata.conversion_id == "conv-999"
        assert report.result == "partial_success"
        assert report.file_metrics.total_files == 20
        assert report.quality_metrics.overall_score == 72.5
        assert len(report.issues) == 2
        assert len(report.recommendations) == 1
        assert len(report.assumptions) == 1
        assert len(report.warnings) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
