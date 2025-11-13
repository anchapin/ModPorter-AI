"""
Tests for types module.
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any

from src.types.report_types import (
    ConversionStatus,
    ImpactLevel,
    ReportMetadata,
    SummaryReport,
    FeatureAnalysisItem,
    FeatureAnalysis
)


class TestReportTypes:
    """Test report type definitions and utilities."""

    def test_conversion_status_enum(self):
        """Test ConversionStatus enum values."""
        assert ConversionStatus.SUCCESS == "success"
        assert ConversionStatus.PARTIAL == "partial"
        assert ConversionStatus.FAILED == "failed"
        assert ConversionStatus.PROCESSING == "processing"

    def test_impact_level_enum(self):
        """Test ImpactLevel enum values."""
        assert ImpactLevel.LOW == "low"
        assert ImpactLevel.MEDIUM == "medium"
        assert ImpactLevel.HIGH == "high"
        assert ImpactLevel.CRITICAL == "critical"

    def test_report_metadata_creation(self):
        """Test ReportMetadata creation."""
        metadata = ReportMetadata(
            report_id="test_report_123",
            job_id="test_job_123",
            generation_timestamp=datetime.now(),
            version="2.0.0",
            report_type="comprehensive"
        )
        
        assert metadata.report_id == "test_report_123"
        assert metadata.job_id == "test_job_123"
        assert metadata.version == "2.0.0"
        assert metadata.report_type == "comprehensive"

    def test_summary_report_creation(self):
        """Test SummaryReport creation."""
        report = SummaryReport(
            overall_success_rate=0.85,
            total_features=10,
            converted_features=8,
            partially_converted_features=1,
            failed_features=1,
            assumptions_applied_count=3,
            processing_time_seconds=120.5,
            download_url="http://example.com/report.zip",
            quick_statistics={"avg_confidence": 0.92},
            total_files_processed=15,
            output_size_mb=2.5,
            conversion_quality_score=0.88,
            recommended_actions=["Review partial conversions", "Fix failed features"]
        )
        
        assert report.overall_success_rate == 0.85
        assert report.total_features == 10
        assert report.converted_features == 8
        assert report.failed_features == 1
        assert report.assumptions_applied_count == 3
        assert report.download_url == "http://example.com/report.zip"
        assert "avg_confidence" in report.quick_statistics
        assert report.total_files_processed == 15
        assert report.output_size_mb == 2.5
        assert report.conversion_quality_score == 0.88
        assert len(report.recommended_actions) == 2

    def test_feature_analysis_item_creation(self):
        """Test FeatureAnalysisItem creation."""
        item = FeatureAnalysisItem(
            name="test_feature",
            original_type="java_class",
            converted_type="bedrock_behavior",
            status="converted",
            compatibility_score=0.95,
            assumptions_used=["assumption1", "assumption2"],
            impact_assessment="low",
            visual_comparison={"before": "image1.png", "after": "image2.png"},
            technical_notes="Converted with custom mappings"
        )
        
        assert item.name == "test_feature"
        assert item.original_type == "java_class"
        assert item.converted_type == "bedrock_behavior"
        assert item.status == "converted"
        assert item.compatibility_score == 0.95
        assert len(item.assumptions_used) == 2
        assert item.impact_assessment == "low"
        assert item.visual_comparison["before"] == "image1.png"
        assert item.technical_notes == "Converted with custom mappings"
        
        # Test to_dict method
        item_dict = item.to_dict()
        assert item_dict["name"] == "test_feature"
        assert item_dict["compatibility_score"] == 0.95

    def test_feature_analysis_creation(self):
        """Test FeatureAnalysis creation."""
        items = [
            FeatureAnalysisItem(
                name="feature1",
                original_type="java_method",
                converted_type="bedrock_function",
                status="converted",
                compatibility_score=0.90,
                assumptions_used=["assumption1"],
                impact_assessment="medium"
            ),
            FeatureAnalysisItem(
                name="feature2",
                original_type="java_field",
                converted_type=None,
                status="failed",
                compatibility_score=0.0,
                assumptions_used=[],
                impact_assessment="high"
            )
        ]
        
        analysis = FeatureAnalysis(
            features=items,
            compatibility_mapping_summary="Most features converted successfully",
            visual_comparisons_overview="See attached images",
            impact_assessment_summary="Low overall impact"
        )
        
        assert len(analysis.features) == 2
        assert analysis.compatibility_mapping_summary == "Most features converted successfully"
        assert analysis.impact_assessment_summary == "Low overall impact"


class TestReportUtilities:
    """Test report utility functions."""

    def test_summary_report_post_init(self):
        """Test SummaryReport __post_init__ method."""
        report1 = SummaryReport(
            overall_success_rate=0.8,
            total_features=10,
            converted_features=8,
            partially_converted_features=1,
            failed_features=1,
            assumptions_applied_count=2,
            processing_time_seconds=100.0
        )
        
        assert report1.quick_statistics == {}
        assert report1.recommended_actions == []
        
        report2 = SummaryReport(
            overall_success_rate=0.9,
            total_features=5,
            converted_features=4,
            partially_converted_features=1,
            failed_features=0,
            assumptions_applied_count=1,
            processing_time_seconds=50.0,
            quick_statistics={"test": "value"},
            recommended_actions=["action1", "action2"]
        )
        
        assert report2.quick_statistics == {"test": "value"}
        assert len(report2.recommended_actions) == 2

    def test_feature_analysis_item_to_dict(self):
        """Test FeatureAnalysisItem to_dict method with all fields."""
        item = FeatureAnalysisItem(
            name="complete_feature",
            original_type="java_complete",
            converted_type="bedrock_complete",
            status="converted",
            compatibility_score=1.0,
            assumptions_used=[],
            impact_assessment="none",
            visual_comparison=None,
            technical_notes=None
        )
        
        result = item.to_dict()
        
        expected_keys = [
            "name", "original_type", "converted_type", "status",
            "compatibility_score", "assumptions_used", "impact_assessment",
            "visual_comparison", "technical_notes"
        ]
        
        for key in expected_keys:
            assert key in result
        
        assert result["name"] == "complete_feature"
        assert result["compatibility_score"] == 1.0
        assert result["visual_comparison"] is None
        assert result["technical_notes"] is None

    def test_edge_cases(self):
        """Test edge cases for report types."""
        # Test empty values
        metadata = ReportMetadata(
            report_id="",
            job_id="",
            generation_timestamp=datetime.now()
        )
        assert metadata.report_id == ""
        assert metadata.job_id == ""
        
        # Test zero values in summary report
        summary = SummaryReport(
            overall_success_rate=0.0,
            total_features=0,
            converted_features=0,
            partially_converted_features=0,
            failed_features=0,
            assumptions_applied_count=0,
            processing_time_seconds=0.0
        )
        assert summary.overall_success_rate == 0.0
        assert summary.total_features == 0
        
        # Test empty feature analysis
        empty_analysis = FeatureAnalysis(
            features=[],
            compatibility_mapping_summary="No features"
        )
        assert len(empty_analysis.features) == 0
        assert empty_analysis.compatibility_mapping_summary == "No features"
