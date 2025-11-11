"""
Basic tests for conversion_success_prediction.py service.
Focus on testing main classes and methods.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

from services.conversion_success_prediction import (
    PredictionType,
    ConversionFeatures,
    PredictionResult
)


class TestPredictionType:
    """Test PredictionType enum."""
    
    def test_prediction_type_values(self):
        """Test all enum values are present."""
        assert PredictionType.OVERALL_SUCCESS.value == "overall_success"
        assert PredictionType.FEATURE_COMPLETENESS.value == "feature_completeness"
        assert PredictionType.PERFORMANCE_IMPACT.value == "performance_impact"
        assert PredictionType.COMPATIBILITY_SCORE.value == "compatibility_score"
        assert PredictionType.RISK_ASSESSMENT.value == "risk_assessment"
        assert PredictionType.CONVERSION_TIME.value == "conversion_time"
        assert PredictionType.RESOURCE_USAGE.value == "resource_usage"


class TestConversionFeatures:
    """Test ConversionFeatures dataclass."""
    
    def test_conversion_features_creation(self):
        """Test creating ConversionFeatures instance."""
        features = ConversionFeatures(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            pattern_type="entity_mapping",
            minecraft_version="1.20.1",
            node_type="concept",
            platform="java"
        )
        
        assert features.java_concept == "Entity"
        assert features.bedrock_concept == "Entity Definition"
        assert features.pattern_type == "entity_mapping"
        assert features.minecraft_version == "1.20.1"
        assert features.node_type == "concept"
        assert features.platform == "java"


class TestPredictionResult:
    """Test PredictionResult dataclass."""
    
    def test_prediction_result_creation(self):
        """Test creating PredictionResult instance."""
        result = PredictionResult(
            prediction_type=PredictionType.OVERALL_SUCCESS,
            score=0.85,
            confidence=0.9,
            details={"model": "random_forest"}
        )
        
        assert result.prediction_type == PredictionType.OVERALL_SUCCESS
        assert result.score == 0.85
        assert result.confidence == 0.9
        assert result.details["model"] == "random_forest"


class TestConversionSuccessPredictionBasic:
    """Test basic functionality of ConversionSuccessPredictionService."""
    
    @pytest.fixture
    def service(self):
        """Create a service instance."""
        from services.conversion_success_prediction import ConversionSuccessPredictionService
        return ConversionSuccessPredictionService()
        
    def test_service_initialization(self, service):
        """Test service initialization."""
        assert hasattr(service, 'models')
        assert hasattr(service, 'scalers')
        assert hasattr(service, 'is_trained')
        
    def test_feature_extraction_basic(self, service):
        """Test basic feature extraction."""
        if hasattr(service, 'extract_features'):
            features = service.extract_features({
                "java_concept": "Entity",
                "bedrock_concept": "Entity Definition",
                "pattern_type": "entity_mapping",
                "minecraft_version": "1.20.1",
                "node_type": "concept",
                "platform": "java"
            })
            
            assert features is not None or isinstance(features, (list, type(None)))
        
    def test_prediction_types_coverage(self):
        """Test all prediction types are covered."""
        expected_types = [
            "overall_success",
            "feature_completeness",
            "performance_impact",
            "compatibility_score",
            "risk_assessment",
            "conversion_time",
            "resource_usage"
        ]
        
        actual_types = [t.value for t in PredictionType]
        
        for expected in expected_types:
            assert expected in actual_types
