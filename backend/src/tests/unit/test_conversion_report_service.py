"""
Unit tests for conversion_report service.
"""

import pytest
from unittest.mock import MagicMock, patch
from services.conversion_report import (
    ConversionReport,
    ConversionReportGenerator,
    get_report_generator,
)


class TestConversionReport:
    def test_conversion_report_init(self):
        """Test ConversionReport can be initialized."""
        report = ConversionReport(job_id="test-123", java_code="// java code")
        assert report.job_id == "test-123"
        assert report.java_code == "// java code"
        assert report.status == "pending"

    def test_conversion_report_has_attributes(self):
        """Test ConversionReport has expected attributes."""
        report = ConversionReport(job_id="test", java_code="code")
        assert hasattr(report, 'bedrock_code')
        assert hasattr(report, 'start_time')
        assert hasattr(report, 'stages')
        assert hasattr(report, 'assumptions')
        assert hasattr(report, 'issues')
        assert hasattr(report, 'metrics')

    def test_conversion_report_add_stage(self):
        """Test ConversionReport can add stages."""
        report = ConversionReport(job_id="test", java_code="code")
        report.add_stage("parsing", "completed", 100.0)
        assert len(report.stages) == 1
        assert report.stages[0]["name"] == "parsing"


class TestConversionReportGenerator:
    @patch('services.conversion_report.Path.mkdir')
    def test_conversion_report_generator_init(self, mock_mkdir):
        """Test ConversionReportGenerator can be initialized."""
        with patch('pathlib.Path.mkdir'):
            generator = ConversionReportGenerator()
            assert generator is not None


class TestModuleFunctions:
    @patch('services.conversion_report.Path.mkdir')
    def test_get_report_generator(self, mock_mkdir):
        """Test get_report_generator function."""
        with patch('pathlib.Path.mkdir'):
            generator = get_report_generator()
            assert generator is not None
            assert isinstance(generator, ConversionReportGenerator)
