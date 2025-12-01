"""
Simplified tests for comprehensive_report_generator.py service
Focus on basic functionality to increase coverage from 0%
"""

import pytest
import json
import sys
import os

# Set up path imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module under test
from src.services.comprehensive_report_generator import ConversionReportGenerator


class TestConversionReportGeneratorSimple:
    """Simplified test suite for ConversionReportGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create a ConversionReportGenerator instance for testing."""
        return ConversionReportGenerator()

    @pytest.fixture
    def mock_conversion_result(self):
        """Sample conversion result data."""
        return {
            "total_features": 100,
            "converted_features": 85,
            "partially_converted_features": 10,
            "failed_features": 5,
            "assumptions_applied_count": 3,
            "processing_time_seconds": 45.2,
            "download_url": "https://example.com/download/converted-addon.mcpack",
            "quick_statistics": {
                "blocks_converted": 50,
                "entities_converted": 25,
                "items_converted": 10,
            },
            "total_files_processed": 25,
            "output_size_mb": 2.5,
        }

    def test_initialization(self, generator):
        """Test ConversionReportGenerator initialization."""
        assert generator.version == "2.0.0"
        assert hasattr(generator, "start_time")
        assert isinstance(generator.start_time, float)

    def test_generate_summary_report_basic(self, generator, mock_conversion_result):
        """Test basic summary report generation."""
        result = generator.generate_summary_report(mock_conversion_result)

        # Check that result has expected attributes
        assert hasattr(result, "overall_success_rate")
        assert hasattr(result, "total_features")
        assert hasattr(result, "converted_features")
        assert hasattr(result, "partially_converted_features")
        assert hasattr(result, "failed_features")
        assert hasattr(result, "assumptions_applied_count")
        assert hasattr(result, "processing_time_seconds")
        assert hasattr(result, "download_url")
        assert hasattr(result, "total_files_processed")
        assert hasattr(result, "output_size_mb")

        # Check that values are reasonable
        assert 0 <= result.overall_success_rate <= 100
        assert result.total_features >= 0
        assert result.converted_features >= 0
        assert result.partially_converted_features >= 0
        assert result.failed_features >= 0
        assert result.assumptions_applied_count >= 0
        assert result.processing_time_seconds >= 0
        assert result.total_files_processed >= 0
        assert result.output_size_mb >= 0

    def test_generate_summary_report_empty_result(self, generator):
        """Test summary report generation with empty conversion result."""
        empty_result = {}

        result = generator.generate_summary_report(empty_result)

        # Check default values
        assert result.overall_success_rate == 0.0
        assert result.total_features == 0
        assert result.converted_features == 0
        assert result.partially_converted_features == 0
        assert result.failed_features == 0
        assert result.assumptions_applied_count == 0
        assert result.processing_time_seconds == 0.0
        assert result.download_url is None
        assert result.total_files_processed == 0
        assert result.output_size_mb == 0.0

    def test_generate_feature_analysis_basic(self, generator):
        """Test basic feature analysis generation."""
        # Create mock features data
        features_data = [
            {
                "feature_name": "grass_block",
                "original_type": "block",
                "converted_type": "block",
                "status": "converted",
                "compatibility": 0.9,
                "notes": "Direct mapping available",
            },
            {
                "feature_name": "zombie_entity",
                "original_type": "entity",
                "converted_type": "entity",
                "status": "partially_converted",
                "compatibility": 0.7,
                "notes": "AI behavior differences",
            },
            {
                "feature_name": "custom_item",
                "original_type": "item",
                "converted_type": None,
                "status": "failed",
                "compatibility": 0.0,
                "notes": "No equivalent in Bedrock",
            },
        ]

        result = generator.generate_feature_analysis(features_data)

        # Check that result has expected attributes
        assert hasattr(result, "features")
        assert hasattr(result, "compatibility_mapping_summary")

        # Check feature items
        feature_items = result.features
        assert len(feature_items) == 3

        # Check first feature (fully converted)
        grass_block = feature_items[0]
        assert grass_block.name == "grass_block"
        assert grass_block.original_type == "block"
        assert grass_block.converted_type == "block"
        assert grass_block.status == "converted"
        assert hasattr(grass_block, "compatibility_score")

    def test_generate_feature_analysis_empty_list(self, generator):
        """Test feature analysis with empty features list."""
        empty_features = []

        result = generator.generate_feature_analysis(empty_features)

        # Check that result has expected attributes
        assert hasattr(result, "features")
        assert hasattr(result, "compatibility_mapping_summary")

        # Check default values
        assert len(result.features) == 0

    def test_calculate_compatibility_score_converted(self, generator):
        """Test compatibility score calculation for converted feature."""
        feature_data = {"status": "converted", "compatibility": 0.9}

        score = generator._calculate_compatibility_score(feature_data)

        assert score == 0.9

    def test_calculate_compatibility_score_partially_converted(self, generator):
        """Test compatibility score calculation for partially converted feature."""
        feature_data = {"status": "partially_converted", "compatibility": 0.7}

        score = generator._calculate_compatibility_score(feature_data)

        assert score == 0.7

    def test_calculate_compatibility_score_failed(self, generator):
        """Test compatibility score calculation for failed feature."""
        feature_data = {"status": "failed", "compatibility": 0.0}

        score = generator._calculate_compatibility_score(feature_data)

        assert score == 0.0

    def test_calculate_compatibility_score_missing_data(self, generator):
        """Test compatibility score calculation with missing data."""
        feature_data = {}

        score = generator._calculate_compatibility_score(feature_data)

        assert score == 0.0

    def test_export_report_json_success(self, generator, mock_conversion_result):
        """Test successful JSON export of report."""
        # Create mock features data
        features_data = [
            {
                "feature_name": "grass_block",
                "original_type": "block",
                "converted_type": "block",
                "status": "converted",
                "compatibility": 0.9,
            }
        ]

        # Generate feature analysis first
        feature_analysis = generator.generate_feature_analysis(features_data)

        # Export to JSON
        json_result = generator.export_report(feature_analysis, "json")

        # Parse JSON to verify structure
        parsed = json.loads(json_result)

        # Check that it's valid JSON
        assert isinstance(parsed, dict)

    def test_export_report_csv_features(self, generator):
        """Test successful CSV export of features."""
        # Create mock features data
        features_data = [
            {
                "feature_name": "grass_block",
                "original_type": "block",
                "converted_type": "block",
                "status": "converted",
                "compatibility": 0.9,
            },
            {
                "feature_name": "zombie_entity",
                "original_type": "entity",
                "converted_type": "entity",
                "status": "partially_converted",
                "compatibility": 0.7,
            },
        ]

        # Generate feature analysis first
        feature_analysis = generator.generate_feature_analysis(features_data)

        # Export to CSV
        csv_result = generator.export_feature_analysis_csv(feature_analysis)

        # Check CSV structure
        lines = csv_result.strip().split("\n")
        assert len(lines) >= 2  # Header + at least one feature

        # Check header
        header = lines[0]
        assert "name" in header
        assert "original_type" in header
        assert "converted_type" in header
        assert "status" in header
        assert "compatibility_score" in header
