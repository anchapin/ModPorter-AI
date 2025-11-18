"""Tests for report_types.py module."""

import pytest
import json
from datetime import datetime
from typing import Dict, Any, List

from src.custom_types.report_types import (
    ConversionStatus,
    ImpactLevel,
    ReportMetadata,
    SummaryReport,
    FeatureAnalysisItem,
    FeatureAnalysis,
    AssumptionReportItem,
    AssumptionsReport,
    DeveloperLog,
    InteractiveReport,
    ModConversionStatus,
    SmartAssumption,
    FeatureConversionDetail,
    AssumptionDetail,
    LogEntry,
    create_report_metadata,
    calculate_quality_score
)


class TestConversionStatus:
    """Test ConversionStatus constants."""
    
    def test_success_constant(self):
        assert ConversionStatus.SUCCESS == "success"
    
    def test_partial_constant(self):
        assert ConversionStatus.PARTIAL == "partial"
    
    def test_failed_constant(self):
        assert ConversionStatus.FAILED == "failed"
    
    def test_processing_constant(self):
        assert ConversionStatus.PROCESSING == "processing"


class TestImpactLevel:
    """Test ImpactLevel constants."""
    
    def test_low_constant(self):
        assert ImpactLevel.LOW == "low"
    
    def test_medium_constant(self):
        assert ImpactLevel.MEDIUM == "medium"
    
    def test_high_constant(self):
        assert ImpactLevel.HIGH == "high"
    
    def test_critical_constant(self):
        assert ImpactLevel.CRITICAL == "critical"


class TestReportMetadata:
    """Test ReportMetadata dataclass."""
    
    def test_report_metadata_creation(self):
        metadata = ReportMetadata(
            report_id="test_report",
            job_id="test_job",
            generation_timestamp=datetime(2023, 1, 1, 12, 0, 0)
        )
        
        assert metadata.report_id == "test_report"
        assert metadata.job_id == "test_job"
        assert metadata.generation_timestamp == datetime(2023, 1, 1, 12, 0, 0)
        assert metadata.version == "2.0.0"
        assert metadata.report_type == "comprehensive"
    
    def test_report_metadata_with_custom_values(self):
        metadata = ReportMetadata(
            report_id="custom",
            job_id="job123",
            generation_timestamp=datetime.now(),
            version="3.0.0",
            report_type="custom_type"
        )
        
        assert metadata.version == "3.0.0"
        assert metadata.report_type == "custom_type"


class TestSummaryReport:
    """Test SummaryReport dataclass."""
    
    def test_summary_report_minimal(self):
        report = SummaryReport(
            overall_success_rate=85.5,
            total_features=10,
            converted_features=8,
            partially_converted_features=1,
            failed_features=1,
            assumptions_applied_count=3,
            processing_time_seconds=120.5
        )
        
        assert report.overall_success_rate == 85.5
        assert report.total_features == 10
        assert report.converted_features == 8
        assert report.partially_converted_features == 1
        assert report.failed_features == 1
        assert report.assumptions_applied_count == 3
        assert report.processing_time_seconds == 120.5
        assert report.download_url is None
        assert report.quick_statistics == {}
        assert report.recommended_actions == []
    
    def test_summary_report_with_optional_fields(self):
        report = SummaryReport(
            overall_success_rate=90.0,
            total_features=20,
            converted_features=18,
            partially_converted_features=2,
            failed_features=0,
            assumptions_applied_count=5,
            processing_time_seconds=180.0,
            download_url="http://example.com/download",
            quick_statistics={"key": "value"},
            total_files_processed=50,
            output_size_mb=25.5,
            conversion_quality_score=95.0,
            recommended_actions=["action1", "action2"]
        )
        
        assert report.download_url == "http://example.com/download"
        assert report.quick_statistics == {"key": "value"}
        assert report.total_files_processed == 50
        assert report.output_size_mb == 25.5
        assert report.conversion_quality_score == 95.0
        assert report.recommended_actions == ["action1", "action2"]


class TestFeatureAnalysisItem:
    """Test FeatureAnalysisItem dataclass."""
    
    def test_feature_analysis_item_creation(self):
        item = FeatureAnalysisItem(
            name="test_feature",
            original_type="java_block",
            converted_type="bedrock_block",
            status="converted",
            compatibility_score=95.0,
            assumptions_used=["assumption1", "assumption2"],
            impact_assessment="low"
        )
        
        assert item.name == "test_feature"
        assert item.original_type == "java_block"
        assert item.converted_type == "bedrock_block"
        assert item.status == "converted"
        assert item.compatibility_score == 95.0
        assert item.assumptions_used == ["assumption1", "assumption2"]
        assert item.impact_assessment == "low"
        assert item.visual_comparison is None
        assert item.technical_notes is None
    
    def test_feature_analysis_item_to_dict(self):
        item = FeatureAnalysisItem(
            name="feature",
            original_type="type1",
            converted_type="type2",
            status="status",
            compatibility_score=80.0,
            assumptions_used=["assumption"],
            impact_assessment="medium",
            visual_comparison={"before": "img1", "after": "img2"},
            technical_notes="notes"
        )
        
        result = item.to_dict()
        
        assert result["name"] == "feature"
        assert result["original_type"] == "type1"
        assert result["converted_type"] == "type2"
        assert result["status"] == "status"
        assert result["compatibility_score"] == 80.0
        assert result["assumptions_used"] == ["assumption"]
        assert result["impact_assessment"] == "medium"
        assert result["visual_comparison"] == {"before": "img1", "after": "img2"}
        assert result["technical_notes"] == "notes"


class TestFeatureAnalysis:
    """Test FeatureAnalysis dataclass."""
    
    def test_feature_analysis_creation(self):
        feature = FeatureAnalysisItem(
            name="test",
            original_type="type1",
            converted_type="type2",
            status="status",
            compatibility_score=90.0,
            assumptions_used=["assumption"],
            impact_assessment="low"
        )
        
        analysis = FeatureAnalysis(
            features=[feature],
            compatibility_mapping_summary="Good compatibility",
            impact_assessment_summary="Low impact"
        )
        
        assert len(analysis.features) == 1
        assert analysis.compatibility_mapping_summary == "Good compatibility"
        assert analysis.impact_assessment_summary == "Low impact"
        assert analysis.total_compatibility_score == 0.0
        assert analysis.feature_categories == {}
        assert analysis.conversion_patterns == []
    
    def test_feature_analysis_with_optional_fields(self):
        feature = FeatureAnalysisItem(
            name="test",
            original_type="type1",
            converted_type="type2",
            status="status",
            compatibility_score=90.0,
            assumptions_used=["assumption"],
            impact_assessment="low"
        )
        
        analysis = FeatureAnalysis(
            features=[feature],
            compatibility_mapping_summary="Summary",
            total_compatibility_score=85.0,
            feature_categories={"blocks": ["feature"]},
            conversion_patterns=["pattern1", "pattern2"]
        )
        
        assert analysis.total_compatibility_score == 85.0
        assert analysis.feature_categories == {"blocks": ["feature"]}
        assert analysis.conversion_patterns == ["pattern1", "pattern2"]


class TestAssumptionReportItem:
    """Test AssumptionReportItem dataclass."""
    
    def test_assumption_report_item_creation(self):
        item = AssumptionReportItem(
            original_feature="original",
            assumption_type="conversion",
            bedrock_equivalent="bedrock_feature",
            impact_level="medium",
            user_explanation="explanation",
            technical_details="details",
            confidence_score=85.0
        )
        
        assert item.original_feature == "original"
        assert item.assumption_type == "conversion"
        assert item.bedrock_equivalent == "bedrock_feature"
        assert item.impact_level == "medium"
        assert item.user_explanation == "explanation"
        assert item.technical_details == "details"
        assert item.confidence_score == 85.0
        assert item.alternatives_considered == []
    
    def test_assumption_report_item_to_dict(self):
        item = AssumptionReportItem(
            original_feature="feature",
            assumption_type="type",
            bedrock_equivalent="equivalent",
            impact_level="high",
            user_explanation="user_explanation",
            technical_details="technical_details",
            visual_example={"before": "img1", "after": "img2"},
            confidence_score=90.0,
            alternatives_considered=["alt1", "alt2"]
        )
        
        result = item.to_dict()
        
        assert result["original_feature"] == "feature"
        assert result["assumption_type"] == "type"
        assert result["bedrock_equivalent"] == "equivalent"
        assert result["impact_level"] == "high"
        assert result["user_explanation"] == "user_explanation"
        assert result["technical_details"] == "technical_details"
        assert result["visual_example"] == {"before": "img1", "after": "img2"}
        assert result["confidence_score"] == 90.0
        assert result["alternatives_considered"] == ["alt1", "alt2"]


class TestAssumptionsReport:
    """Test AssumptionsReport dataclass."""
    
    def test_assumptions_report_creation(self):
        item = AssumptionReportItem(
            original_feature="feature",
            assumption_type="type",
            bedrock_equivalent="equivalent",
            impact_level="low",
            user_explanation="explanation",
            technical_details="details"
        )
        
        report = AssumptionsReport(
            assumptions=[item]
        )
        
        assert len(report.assumptions) == 1
        assert report.total_assumptions_count == 1
        assert report.impact_distribution == {"low": 0, "medium": 0, "high": 0}
        assert report.category_breakdown == {}
    
    def test_assumptions_report_with_impact_distribution(self):
        item1 = AssumptionReportItem(
            original_feature="feature1",
            assumption_type="type1",
            bedrock_equivalent="equiv1",
            impact_level="low",
            user_explanation="exp1",
            technical_details="det1"
        )
        
        item2 = AssumptionReportItem(
            original_feature="feature2",
            assumption_type="type2",
            bedrock_equivalent="equiv2",
            impact_level="high",
            user_explanation="exp2",
            technical_details="det2"
        )
        
        report = AssumptionsReport(
            assumptions=[item1, item2],
            impact_distribution={"low": 1, "medium": 0, "high": 1}
        )
        
        assert report.total_assumptions_count == 2
        assert report.impact_distribution == {"low": 1, "medium": 0, "high": 1}


class TestDeveloperLog:
    """Test DeveloperLog dataclass."""
    
    def test_developer_log_creation(self):
        log = DeveloperLog(
            code_translation_details=[{"file": "test.java", "changes": ["change1"]}],
            api_mapping_issues=[{"issue": "mapping_issue"}],
            file_processing_log=[{"file": "test.txt", "status": "processed"}],
            performance_metrics={"time": 100, "memory": "50MB"},
            error_details=[{"error": "test_error"}]
        )
        
        assert len(log.code_translation_details) == 1
        assert len(log.api_mapping_issues) == 1
        assert len(log.file_processing_log) == 1
        assert log.performance_metrics == {"time": 100, "memory": "50MB"}
        assert len(log.error_details) == 1
        assert log.optimization_opportunities == []
        assert log.technical_debt_notes == []
        assert log.benchmark_comparisons == {}
    
    def test_developer_log_with_optional_fields(self):
        log = DeveloperLog(
            code_translation_details=[],
            api_mapping_issues=[],
            file_processing_log=[],
            performance_metrics={},
            error_details=[],
            optimization_opportunities=["opt1", "opt2"],
            technical_debt_notes=["debt1"],
            benchmark_comparisons={"test": 95.0}
        )
        
        assert log.optimization_opportunities == ["opt1", "opt2"]
        assert log.technical_debt_notes == ["debt1"]
        assert log.benchmark_comparisons == {"test": 95.0}


class TestInteractiveReport:
    """Test InteractiveReport dataclass."""
    
    def test_interactive_report_creation(self):
        metadata = ReportMetadata("report", "job", datetime.now())
        summary = SummaryReport(
            overall_success_rate=90.0,
            total_features=10,
            converted_features=9,
            partially_converted_features=1,
            failed_features=0,
            assumptions_applied_count=2,
            processing_time_seconds=100.0
        )
        
        feature = FeatureAnalysisItem(
            name="feature",
            original_type="type1",
            converted_type="type2",
            status="converted",
            compatibility_score=95.0,
            assumptions_used=[],
            impact_assessment="low"
        )
        
        feature_analysis = FeatureAnalysis(
            features=[feature],
            compatibility_mapping_summary="Summary"
        )
        
        assumption = AssumptionReportItem(
            original_feature="feature",
            assumption_type="type",
            bedrock_equivalent="equiv",
            impact_level="low",
            user_explanation="exp",
            technical_details="details"
        )
        
        assumptions_report = AssumptionsReport(
            assumptions=[assumption]
        )
        
        developer_log = DeveloperLog(
            code_translation_details=[],
            api_mapping_issues=[],
            file_processing_log=[],
            performance_metrics={},
            error_details=[]
        )
        
        report = InteractiveReport(
            metadata=metadata,
            summary=summary,
            feature_analysis=feature_analysis,
            assumptions_report=assumptions_report,
            developer_log=developer_log
        )
        
        assert report.metadata == metadata
        assert report.summary == summary
        assert report.feature_analysis == feature_analysis
        assert report.assumptions_report == assumptions_report
        assert report.developer_log == developer_log
        assert report.navigation_structure == {
            "sections": ["summary", "features", "assumptions", "developer"],
            "expandable": True,
            "search_enabled": True
        }
        assert report.export_formats == ["pdf", "json", "html"]
        assert report.user_actions == ["download", "share", "feedback", "expand_all"]
    
    def test_interactive_report_to_dict(self):
        metadata = ReportMetadata("report", "job", datetime(2023, 1, 1, 12, 0, 0))
        summary = SummaryReport(
            overall_success_rate=85.0,
            total_features=5,
            converted_features=4,
            partially_converted_features=1,
            failed_features=0,
            assumptions_applied_count=1,
            processing_time_seconds=50.0
        )
        
        feature = FeatureAnalysisItem(
            name="test_feature",
            original_type="java",
            converted_type="bedrock",
            status="converted",
            compatibility_score=90.0,
            assumptions_used=[],
            impact_assessment="low"
        )
        
        feature_analysis = FeatureAnalysis(
            features=[feature],
            compatibility_mapping_summary="Good"
        )
        
        assumption = AssumptionReportItem(
            original_feature="feature",
            assumption_type="type",
            bedrock_equivalent="equiv",
            impact_level="low",
            user_explanation="exp",
            technical_details="details"
        )
        
        assumptions_report = AssumptionsReport(
            assumptions=[assumption]
        )
        
        developer_log = DeveloperLog(
            code_translation_details=[],
            api_mapping_issues=[],
            file_processing_log=[],
            performance_metrics={},
            error_details=[]
        )
        
        report = InteractiveReport(
            metadata=metadata,
            summary=summary,
            feature_analysis=feature_analysis,
            assumptions_report=assumptions_report,
            developer_log=developer_log
        )
        
        result = report.to_dict()
        
        assert "metadata" in result
        assert "summary" in result
        assert "feature_analysis" in result
        assert "assumptions_report" in result
        assert "developer_log" in result
        assert result["metadata"]["report_id"] == "report"
        assert result["metadata"]["job_id"] == "job"
        assert result["summary"]["overall_success_rate"] == 85.0
    
    def test_interactive_report_to_json(self):
        metadata = ReportMetadata("report", "job", datetime.now())
        summary = SummaryReport(
            overall_success_rate=80.0,
            total_features=3,
            converted_features=2,
            partially_converted_features=1,
            failed_features=0,
            assumptions_applied_count=1,
            processing_time_seconds=30.0
        )
        
        feature = FeatureAnalysisItem(
            name="feature",
            original_type="type1",
            converted_type="type2",
            status="converted",
            compatibility_score=85.0,
            assumptions_used=[],
            impact_assessment="medium"
        )
        
        feature_analysis = FeatureAnalysis(
            features=[feature],
            compatibility_mapping_summary="Summary"
        )
        
        assumption = AssumptionReportItem(
            original_feature="feature",
            assumption_type="type",
            bedrock_equivalent="equiv",
            impact_level="medium",
            user_explanation="exp",
            technical_details="details"
        )
        
        assumptions_report = AssumptionsReport(
            assumptions=[assumption]
        )
        
        developer_log = DeveloperLog(
            code_translation_details=[],
            api_mapping_issues=[],
            file_processing_log=[],
            performance_metrics={},
            error_details=[]
        )
        
        report = InteractiveReport(
            metadata=metadata,
            summary=summary,
            feature_analysis=feature_analysis,
            assumptions_report=assumptions_report,
            developer_log=developer_log
        )
        
        json_str = report.to_json()
        parsed = json.loads(json_str)
        
        assert "metadata" in parsed
        assert "summary" in parsed
        assert parsed["metadata"]["report_id"] == "report"
        assert parsed["summary"]["overall_success_rate"] == 80.0


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_report_metadata_with_defaults(self):
        metadata = create_report_metadata("job123")
        
        assert metadata.job_id == "job123"
        assert metadata.version == "2.0.0"
        assert metadata.report_type == "comprehensive"
        assert metadata.report_id.startswith("report_job123_")
    
    def test_create_report_metadata_with_custom_id(self):
        metadata = create_report_metadata("job123", "custom_report_id")
        
        assert metadata.job_id == "job123"
        assert metadata.report_id == "custom_report_id"
    
    def test_calculate_quality_score_all_success(self):
        summary = SummaryReport(
            overall_success_rate=100.0,
            total_features=10,
            converted_features=10,
            partially_converted_features=0,
            failed_features=0,
            assumptions_applied_count=0,
            processing_time_seconds=0
        )
        
        score = calculate_quality_score(summary)
        assert score == 100.0
    
    def test_calculate_quality_score_mixed(self):
        summary = SummaryReport(
            overall_success_rate=0.0,
            total_features=10,
            converted_features=5,
            partially_converted_features=3,
            failed_features=2,
            assumptions_applied_count=0,
            processing_time_seconds=0
        )
        
        score = calculate_quality_score(summary)
        expected = ((5 * 1.0) + (3 * 0.6) + (2 * 0.0)) / 10 * 100
        assert score == round(expected, 1)
    
    def test_calculate_quality_score_zero_features(self):
        summary = SummaryReport(
            overall_success_rate=0.0,
            total_features=0,
            converted_features=0,
            partially_converted_features=0,
            failed_features=0,
            assumptions_applied_count=0,
            processing_time_seconds=0
        )
        
        score = calculate_quality_score(summary)
        assert score == 0.0


class TestLegacyTypes:
    """Test legacy type definitions."""
    
    def test_mod_conversion_status(self):
        status: ModConversionStatus = {
            "name": "test_mod",
            "version": "1.0.0",
            "status": "success",
            "warnings": ["warning1"],
            "errors": ["error1"]
        }
        
        assert status["name"] == "test_mod"
        assert status["version"] == "1.0.0"
        assert status["status"] == "success"
        assert status["warnings"] == ["warning1"]
        assert status["errors"] == ["error1"]
    
    def test_smart_assumption(self):
        assumption: SmartAssumption = {
            "originalFeature": "feature",
            "assumptionApplied": "assumption",
            "impact": "low",
            "description": "description",
            "userExplanation": "explanation",
            "visualExamples": ["img1", "img2"]
        }
        
        assert assumption["originalFeature"] == "feature"
        assert assumption["assumptionApplied"] == "assumption"
        assert assumption["impact"] == "low"
    
    def test_feature_conversion_detail(self):
        detail: FeatureConversionDetail = {
            "feature_name": "feature",
            "status": "converted",
            "compatibility_notes": "notes",
            "visual_comparison_before": "before.png",
            "visual_comparison_after": "after.png",
            "impact_of_assumption": "low"
        }
        
        assert detail["feature_name"] == "feature"
        assert detail["status"] == "converted"
    
    def test_assumption_detail(self):
        detail: AssumptionDetail = {
            "assumption_id": "assumption1",
            "feature_affected": "feature",
            "description": "description",
            "reasoning": "reasoning",
            "impact_level": "medium",
            "user_explanation": "explanation",
            "technical_notes": "notes"
        }
        
        assert detail["assumption_id"] == "assumption1"
        assert detail["feature_affected"] == "feature"
    
    def test_log_entry(self):
        entry: LogEntry = {
            "timestamp": "2023-01-01T12:00:00",
            "level": "INFO",
            "message": "Test message",
            "details": {"key": "value"}
        }
        
        assert entry["timestamp"] == "2023-01-01T12:00:00"
        assert entry["level"] == "INFO"
        assert entry["message"] == "Test message"
        assert entry["details"] == {"key": "value"}
