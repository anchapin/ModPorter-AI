"""
Unit tests for report_models service.

Tests TypedDict definitions for report structures.
"""

import pytest
from services.report_models import (
    ModConversionStatus,
    SmartAssumption,
    SummaryReport,
    FeatureConversionDetail,
    FeatureAnalysis,
    AssumptionDetail,
    AssumptionsReport,
    LogEntry,
    DeveloperLog,
    InteractiveReport,
    FullConversionReport,
)


class TestModConversionStatus:
    def test_mod_conversion_status_type(self):
        """Test ModConversionStatus is a dict."""
        status: ModConversionStatus = {
            "job_id": "test-123",
            "status": "completed",
            "progress": 100,
        }
        assert status["job_id"] == "test-123"
        assert status["status"] == "completed"


class TestSmartAssumption:
    def test_smart_assumption_type(self):
        """Test SmartAssumption is a dict."""
        assumption: SmartAssumption = {
            "id": "asm-1",
            "type": "entity_behavior",
            "description": "Test assumption",
            "confidence": 0.9,
        }
        assert assumption["id"] == "asm-1"


class TestSummaryReport:
    def test_summary_report_type(self):
        """Test SummaryReport is a dict."""
        report: SummaryReport = {
            "total_features": 10,
            "converted_features": 8,
            "failed_features": 2,
            "success_rate": 80.0,
        }
        assert report["success_rate"] == 80.0


class TestFeatureConversionDetail:
    def test_feature_conversion_detail_type(self):
        """Test FeatureConversionDetail is a dict."""
        detail: FeatureConversionDetail = {
            "feature_id": "feat-1",
            "feature_name": "Test Feature",
            "status": "converted",
        }
        assert detail["status"] == "converted"


class TestFeatureAnalysis:
    def test_feature_analysis_type(self):
        """Test FeatureAnalysis is a dict."""
        analysis: FeatureAnalysis = {
            "feature_type": "block",
            "count": 5,
            "converted": 4,
            "failed": 1,
        }
        assert analysis["count"] == 5


class TestAssumptionDetail:
    def test_assumption_detail_type(self):
        """Test AssumptionDetail is a dict."""
        detail: AssumptionDetail = {
            "assumption_id": "asm-1",
            "description": "Test",
            "validated": True,
        }
        assert detail["validated"] is True


class TestAssumptionsReport:
    def test_assumptions_report_type(self):
        """Test AssumptionsReport is a dict."""
        report: AssumptionsReport = {
            "total": 5,
            "validated": 3,
            "failed": 2,
        }
        assert report["total"] == 5


class TestLogEntry:
    def test_log_entry_type(self):
        """Test LogEntry is a dict."""
        entry: LogEntry = {
            "timestamp": "2024-01-01T00:00:00Z",
            "level": "info",
            "message": "Test message",
        }
        assert entry["level"] == "info"


class TestDeveloperLog:
    def test_developer_log_type(self):
        """Test DeveloperLog is a dict."""
        log: DeveloperLog = {
            "log_level": "debug",
            "source": "converter",
            "message": "Debug info",
        }
        assert log["log_level"] == "debug"


class TestInteractiveReport:
    def test_interactive_report_type(self):
        """Test InteractiveReport is a dict."""
        report: InteractiveReport = {
            "job_id": "test-123",
            "summary": {"total_features": 10},
            "features": [],
        }
        assert "job_id" in report


class TestFullConversionReport:
    def test_full_conversion_report_type(self):
        """Test FullConversionReport is a dict."""
        report: FullConversionReport = {
            "job_id": "test-123",
            "status": "completed",
            "summary": {"total_features": 10},
            "features": [],
            "logs": [],
        }
        assert report["status"] == "completed"
