"""
Tests for Conversion Metrics Service (Phase 12-03)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from dataclasses import asdict

import sys
import os

# Add ai-engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Add services directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))

from conversion_metrics import (
    MetricsCollector,
    SuccessRateCalculator,
    ConversionStatus,
    ComplexityLevel,
    ErrorCategory,
    ConversionMetrics,
    AggregatedMetrics,
    create_metrics_report,
)


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_init_creates_database(self):
        """Test that initialization creates in-memory database."""
        collector = MetricsCollector()
        
        # Check that tables exist
        cursor = collector.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'conversion_metrics' in tables
        collector.close()

    def test_init_with_db_path(self):
        """Test initialization with custom database path."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            collector = MetricsCollector(db_path=db_path)
            assert os.path.exists(db_path)
            collector.close()
        finally:
            os.unlink(db_path)

    def test_start_conversion_creates_record(self):
        """Test that start_conversion creates a database record."""
        collector = MetricsCollector()
        
        metrics = collector.start_conversion(
            conversion_id="test-123",
            mod_name="TestMod",
            complexity="standard"
        )
        
        assert metrics.conversion_id == "test-123"
        assert metrics.mod_name == "TestMod"
        assert metrics.complexity == "standard"
        assert metrics.status == ConversionStatus.IN_PROGRESS.value
        
        collector.close()

    def test_complete_conversion_updates_record(self):
        """Test that complete_conversion updates the record."""
        collector = MetricsCollector()
        
        # Start a conversion
        collector.start_conversion(
            conversion_id="test-456",
            mod_name="AnotherMod",
            complexity="simple"
        )
        
        # Complete it
        collector.complete_conversion(
            conversion_id="test-456",
            status=ConversionStatus.COMPLETE_SUCCESS.value,
            semantic_score=0.95,
            file_count=10,
            functions_converted=5
        )
        
        # Verify the update
        cursor = collector.conn.execute(
            "SELECT status, semantic_score, file_count, functions_converted "
            "FROM conversion_metrics WHERE conversion_id = ?",
            ("test-456",)
        )
        row = cursor.fetchone()
        
        assert row[0] == ConversionStatus.COMPLETE_SUCCESS.value
        assert row[1] == 0.95
        assert row[2] == 10
        assert row[3] == 5
        
        collector.close()

    def test_complete_conversion_with_error(self):
        """Test completing a conversion with error information."""
        collector = MetricsCollector()
        
        collector.start_conversion(
            conversion_id="test-error",
            mod_name="ErrorMod",
            complexity="complex"
        )
        
        collector.complete_conversion(
            conversion_id="test-error",
            status=ConversionStatus.FAILED.value,
            error_category=ErrorCategory.PERMANENT.value,
            error_message="Parse error in source file",
            functions_failed=3
        )
        
        cursor = collector.conn.execute(
            "SELECT status, error_category, error_message, functions_failed "
            "FROM conversion_metrics WHERE conversion_id = ?",
            ("test-error",)
        )
        row = cursor.fetchone()
        
        assert row[0] == ConversionStatus.FAILED.value
        assert row[1] == ErrorCategory.PERMANENT.value
        assert row[2] == "Parse error in source file"
        assert row[3] == 3
        
        collector.close()

    def test_get_aggregated_metrics_empty(self):
        """Test aggregated metrics with no data."""
        collector = MetricsCollector()
        
        agg = collector.get_aggregated_metrics()
        
        assert agg.total_conversions == 0
        assert agg.success_rate == 0.0
        
        collector.close()

    def test_get_aggregated_metrics_with_data(self):
        """Test aggregated metrics with conversion data."""
        collector = MetricsCollector()
        
        # Add multiple conversions with different outcomes
        collector.start_conversion("c1", "mod1", "simple")
        collector.complete_conversion("c1", ConversionStatus.COMPLETE_SUCCESS.value, 0.95)
        
        collector.start_conversion("c2", "mod2", "standard")
        collector.complete_conversion("c2", ConversionStatus.PARTIAL_SUCCESS.value, 0.75)
        
        collector.start_conversion("c3", "mod3", "complex")
        collector.complete_conversion("c3", ConversionStatus.FAILED.value, 0.30, error_category="permanent")
        
        collector.start_conversion("c4", "mod4", "simple")
        collector.complete_conversion("c4", ConversionStatus.COMPLETE_SUCCESS.value, 0.90)
        
        agg = collector.get_aggregated_metrics()
        
        assert agg.total_conversions == 4
        assert agg.successful == 2
        assert agg.partial_success == 1
        assert agg.failed == 1
        assert agg.success_rate == 50.0  # 2/4 = 50%
        assert agg.partial_rate == 25.0  # 1/4 = 25%
        assert agg.failure_rate == 25.0  # 1/4 = 25%
        
        collector.close()

    def test_get_aggregated_metrics_by_complexity(self):
        """Test aggregated metrics grouped by complexity."""
        collector = MetricsCollector()
        
        # Simple: 2 successful, 1 failed
        collector.start_conversion("s1", "smod1", "simple")
        collector.complete_conversion("s1", ConversionStatus.COMPLETE_SUCCESS.value)
        collector.start_conversion("s2", "smod2", "simple")
        collector.complete_conversion("s2", ConversionStatus.COMPLETE_SUCCESS.value)
        collector.start_conversion("s3", "smod3", "simple")
        collector.complete_conversion("s3", ConversionStatus.FAILED.value)
        
        # Standard: 1 successful, 1 partial
        collector.start_conversion("st1", "stmod1", "standard")
        collector.complete_conversion("st1", ConversionStatus.COMPLETE_SUCCESS.value)
        collector.start_conversion("st2", "stmod2", "standard")
        collector.complete_conversion("st2", ConversionStatus.PARTIAL_SUCCESS.value)
        
        agg = collector.get_aggregated_metrics()
        
        assert 'simple' in agg.by_complexity
        assert agg.by_complexity['simple']['total'] == 3
        assert agg.by_complexity['simple']['successful'] == 2
        assert agg.by_complexity['simple']['rate'] == pytest.approx(66.67, rel=0.1)
        
        assert 'standard' in agg.by_complexity
        assert agg.by_complexity['standard']['total'] == 2
        assert agg.by_complexity['standard']['rate'] == 50.0
        
        collector.close()

    def test_get_recent_metrics(self):
        """Test getting metrics for recent time period."""
        collector = MetricsCollector()
        
        # Add a conversion
        collector.start_conversion("recent-1", "mod1", "simple")
        collector.complete_conversion("recent-1", ConversionStatus.COMPLETE_SUCCESS.value)
        
        # Get metrics for last 7 days
        recent = collector.get_recent_metrics(days=7)
        
        assert len(recent) > 0
        
        collector.close()

    def test_get_top_errors(self):
        """Test getting most common error messages."""
        collector = MetricsCollector()
        
        # Add conversions with errors
        collector.start_conversion("e1", "mod1", "complex")
        collector.complete_conversion("e1", ConversionStatus.FAILED.value, 
                                    error_message="NullPointerException")
        
        collector.start_conversion("e2", "mod2", "complex")
        collector.complete_conversion("e2", ConversionStatus.FAILED.value,
                                    error_message="NullPointerException")
        
        collector.start_conversion("e3", "mod3", "expert")
        collector.complete_conversion("e3", ConversionStatus.FAILED.value,
                                    error_message="OutOfMemoryError")
        
        top_errors = collector.get_top_errors(limit=5)
        
        assert len(top_errors) == 2
        assert top_errors[0] == ("NullPointerException", 2)
        assert top_errors[1] == ("OutOfMemoryError", 1)
        
        collector.close()


class TestSuccessRateCalculator:
    """Tests for SuccessRateCalculator class."""

    def test_calculate_overall_rate(self):
        """Test overall success rate calculation."""
        collector = MetricsCollector()
        
        collector.start_conversion("c1", "m1", "simple")
        collector.complete_conversion("c1", ConversionStatus.COMPLETE_SUCCESS.value)
        
        collector.start_conversion("c2", "m2", "simple")
        collector.complete_conversion("c2", ConversionStatus.FAILED.value)
        
        collector.start_conversion("c3", "m3", "simple")
        collector.complete_conversion("c3", ConversionStatus.COMPLETE_SUCCESS.value)
        
        calculator = SuccessRateCalculator(collector)
        rate = calculator.calculate_overall_rate()
        
        assert rate == pytest.approx(66.67, rel=0.1)
        
        collector.close()

    def test_calculate_by_complexity(self):
        """Test success rate calculation by complexity."""
        collector = MetricsCollector()
        
        collector.start_conversion("c1", "m1", "simple")
        collector.complete_conversion("c1", ConversionStatus.COMPLETE_SUCCESS.value)
        
        collector.start_conversion("c2", "m2", "simple")
        collector.complete_conversion("c2", ConversionStatus.FAILED.value)
        
        collector.start_conversion("c3", "m3", "complex")
        collector.complete_conversion("c3", ConversionStatus.COMPLETE_SUCCESS.value)
        
        calculator = SuccessRateCalculator(collector)
        by_complexity = calculator.calculate_by_complexity()
        
        assert by_complexity['simple'] == pytest.approx(50.0, rel=0.1)
        assert by_complexity['complex'] == pytest.approx(100.0, rel=0.1)
        
        collector.close()

    def test_calculate_weighted_score(self):
        """Test weighted success score calculation."""
        collector = MetricsCollector()
        
        # Simple: 2/2 = 100%
        collector.start_conversion("s1", "m1", "simple")
        collector.complete_conversion("s1", ConversionStatus.COMPLETE_SUCCESS.value)
        collector.start_conversion("s2", "m2", "simple")
        collector.complete_conversion("s2", ConversionStatus.COMPLETE_SUCCESS.value)
        
        # Complex: 1/2 = 50%
        collector.start_conversion("c1", "m3", "complex")
        collector.complete_conversion("c1", ConversionStatus.COMPLETE_SUCCESS.value)
        collector.start_conversion("c2", "m4", "complex")
        collector.complete_conversion("c2", ConversionStatus.FAILED.value)
        
        calculator = SuccessRateCalculator(collector)
        weighted = calculator.calculate_weighted_score()
        
        # Expected: (100% * 1.0 + 50% * 0.7) / (1.0 + 0.7) = (100 + 35) / 1.7 = 79.4%
        expected = (100.0 * 1.0 + 50.0 * 0.7) / 1.7
        assert weighted == pytest.approx(expected, rel=0.1)
        
        collector.close()

    def test_get_summary(self):
        """Test getting complete metrics summary."""
        collector = MetricsCollector()
        
        collector.start_conversion("c1", "mod1", "simple")
        collector.complete_conversion("c1", ConversionStatus.COMPLETE_SUCCESS.value, 
                                    semantic_score=0.95)
        
        collector.start_conversion("c2", "mod2", "standard")
        collector.complete_conversion("c2", ConversionStatus.PARTIAL_SUCCESS.value,
                                    semantic_score=0.75)
        
        calculator = SuccessRateCalculator(collector)
        summary = calculator.get_summary()
        
        assert 'total_conversions' in summary
        assert 'success_rate' in summary
        assert 'by_complexity' in summary
        assert 'weighted_score' in summary
        assert summary['total_conversions'] == 2
        
        collector.close()


class TestConversionMetrics:
    """Tests for ConversionMetrics dataclass."""

    def test_create_metrics(self):
        """Test creating a ConversionMetrics object."""
        metrics = ConversionMetrics(
            conversion_id="test-1",
            mod_name="TestMod",
            complexity="standard",
            status=ConversionStatus.IN_PROGRESS.value,
            start_time=datetime.now()
        )
        
        assert metrics.conversion_id == "test-1"
        assert metrics.status == ConversionStatus.IN_PROGRESS.value

    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = ConversionMetrics(
            conversion_id="test-2",
            mod_name="TestMod2",
            complexity="complex",
            status=ConversionStatus.COMPLETE_SUCCESS.value,
            start_time=datetime.now(),
            semantic_score=0.88
        )
        
        d = asdict(metrics)
        
        assert d['conversion_id'] == "test-2"
        assert d['semantic_score'] == 0.88


class TestAggregatedMetrics:
    """Tests for AggregatedMetrics dataclass."""

    def test_create_aggregated_metrics(self):
        """Test creating AggregatedMetrics with defaults."""
        agg = AggregatedMetrics()
        
        assert agg.total_conversions == 0
        assert agg.success_rate == 0.0
        assert agg.by_complexity == {}
        assert agg.by_error_category == {}

    def test_aggregated_metrics_with_data(self):
        """Test AggregatedMetrics with data."""
        agg = AggregatedMetrics(
            total_conversions=10,
            successful=7,
            partial_success=2,
            failed=1,
            success_rate=70.0,
            by_complexity={'simple': {'total': 5, 'successful': 4, 'rate': 80.0}},
            by_error_category={'transient': 2, 'permanent': 1}
        )
        
        assert agg.total_conversions == 10
        assert agg.successful == 7
        assert agg.by_complexity['simple']['rate'] == 80.0
        assert agg.by_error_category['transient'] == 2


class TestCreateMetricsReport:
    """Tests for create_metrics_report function."""

    def test_create_report_empty(self):
        """Test creating report with no data."""
        collector = MetricsCollector()
        
        report = create_metrics_report(collector)
        
        assert "CONVERSION METRICS REPORT" in report
        assert "Total Conversions: 0" in report
        
        collector.close()

    def test_create_report_with_data(self):
        """Test creating report with conversion data."""
        collector = MetricsCollector()
        
        collector.start_conversion("c1", "mod1", "simple")
        collector.complete_conversion("c1", ConversionStatus.COMPLETE_SUCCESS.value,
                                    semantic_score=0.95)
        
        collector.start_conversion("c2", "mod2", "complex")
        collector.complete_conversion("c2", ConversionStatus.FAILED.value,
                                    error_category="permanent")
        
        report = create_metrics_report(collector)
        
        assert "CONVERSION METRICS REPORT" in report
        assert "Total Conversions: 2" in report
        
        collector.close()


class TestEnumValues:
    """Tests for enum values."""

    def test_conversion_status_values(self):
        """Test ConversionStatus enum has correct values."""
        assert ConversionStatus.COMPLETE_SUCCESS.value == "complete_success"
        assert ConversionStatus.PARTIAL_SUCCESS.value == "partial_success"
        assert ConversionStatus.FAILED.value == "failed"
        assert ConversionStatus.IN_PROGRESS.value == "in_progress"

    def test_complexity_level_values(self):
        """Test ComplexityLevel enum has correct values."""
        assert ComplexityLevel.SIMPLE.value == "simple"
        assert ComplexityLevel.STANDARD.value == "standard"
        assert ComplexityLevel.COMPLEX.value == "complex"
        assert ComplexityLevel.EXPERT.value == "expert"

    def test_error_category_values(self):
        """Test ErrorCategory enum has correct values."""
        assert ErrorCategory.TRANSIENT.value == "transient"
        assert ErrorCategory.PERMANENT.value == "permanent"
        assert ErrorCategory.RESOURCE.value == "resource"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.NONE.value == "none"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
