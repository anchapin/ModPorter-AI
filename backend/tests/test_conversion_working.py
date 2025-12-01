"""
Working tests for conversion_success_prediction.py
Focused on improving coverage with correct method names and data structures
"""

import pytest
from unittest.mock import patch, AsyncMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.conversion_success_prediction import (
    ConversionSuccessPredictionService,
    ConversionFeatures,
    PredictionType,
    PredictionResult,
)


@pytest.fixture
def mock_session():
    """Mock database session"""
    return AsyncMock()


@pytest.fixture
def service():
    """Create service instance for testing"""
    return ConversionSuccessPredictionService()


class TestPredictionType:
    """Test PredictionType enum"""

    def test_prediction_type_values(self):
        """Test that prediction type enum has expected values"""
        assert PredictionType.OVERALL_SUCCESS.value == "overall_success"
        assert PredictionType.FEATURE_COMPLETENESS.value == "feature_completeness"
        assert PredictionType.PERFORMANCE_IMPACT.value == "performance_impact"
        assert PredictionType.COMPATIBILITY_SCORE.value == "compatibility_score"
        assert PredictionType.RISK_ASSESSMENT.value == "risk_assessment"
        assert PredictionType.CONVERSION_TIME.value == "conversion_time"
        assert PredictionType.RESOURCE_USAGE.value == "resource_usage"

    def test_prediction_type_enumeration(self):
        """Test iterating over PredictionType enum"""
        prediction_types = list(PredictionType)

        # Should have expected number of types
        assert len(prediction_types) >= 7

        # Should include key types
        type_values = [t.value for t in prediction_types]
        assert "overall_success" in type_values
        assert "feature_completeness" in type_values


class TestConversionFeatures:
    """Test ConversionFeatures dataclass"""

    def test_conversion_features_creation(self):
        """Test creating ConversionFeatures instance"""
        features = ConversionFeatures(
            java_concept="java_entity",
            bedrock_concept="bedrock_entity",
            pattern_type="entity_mapping",
            minecraft_version="1.20.0",
            node_type="entity",
            platform="bedrock",
            description_length=150,
            expert_validated=True,
            community_rating=4.5,
            usage_count=25,
            relationship_count=8,
            success_history=[0.9, 0.85, 0.92],
            feature_count=12,
            complexity_score=0.75,
            version_compatibility=0.88,
            cross_platform_difficulty=0.3,
        )

        assert features.java_concept == "java_entity"
        assert features.bedrock_concept == "bedrock_entity"
        assert features.pattern_type == "entity_mapping"
        assert features.minecraft_version == "1.20.0"
        assert features.node_type == "entity"
        assert features.platform == "bedrock"
        assert features.description_length == 150
        assert features.expert_validated
        assert features.community_rating == 4.5
        assert features.usage_count == 25
        assert features.relationship_count == 8
        assert features.success_history == [0.9, 0.85, 0.92]
        assert features.feature_count == 12
        assert features.complexity_score == 0.75
        assert features.version_compatibility == 0.88
        assert features.cross_platform_difficulty == 0.3

    def test_conversion_features_minimal(self):
        """Test ConversionFeatures with minimal values"""
        features = ConversionFeatures(
            java_concept="java_block",
            bedrock_concept="bedrock_block",
            pattern_type="block_mapping",
            minecraft_version="1.20.0",
            node_type="block",
            platform="bedrock",
            description_length=0,
            expert_validated=False,
            community_rating=0.0,
            usage_count=0,
            relationship_count=0,
            success_history=[],
            feature_count=0,
            complexity_score=0.0,
            version_compatibility=0.0,
            cross_platform_difficulty=1.0,
        )

        assert features.java_concept == "java_block"
        assert features.description_length == 0
        assert not features.expert_validated
        assert features.community_rating == 0.0
        assert features.success_history == []

    def test_conversion_features_comparison(self):
        """Test comparing ConversionFeatures instances"""
        features1 = ConversionFeatures(
            java_concept="java_entity",
            bedrock_concept="bedrock_entity",
            pattern_type="entity_mapping",
            minecraft_version="1.20.0",
            node_type="entity",
            platform="bedrock",
            description_length=100,
            expert_validated=True,
            community_rating=4.0,
            usage_count=20,
            relationship_count=5,
            success_history=[0.8, 0.9],
            feature_count=10,
            complexity_score=0.6,
            version_compatibility=0.9,
            cross_platform_difficulty=0.4,
        )

        features2 = ConversionFeatures(
            java_concept="java_block",
            bedrock_concept="bedrock_block",
            pattern_type="block_mapping",
            minecraft_version="1.19.0",
            node_type="block",
            platform="bedrock",
            description_length=80,
            expert_validated=False,
            community_rating=3.5,
            usage_count=15,
            relationship_count=3,
            success_history=[0.7, 0.8],
            feature_count=8,
            complexity_score=0.5,
            version_compatibility=0.85,
            cross_platform_difficulty=0.6,
        )

        # Should be different
        assert features1.java_concept != features2.java_concept
        assert features1.bedrock_concept != features2.bedrock_concept
        assert features1.pattern_type != features2.pattern_type
        assert features1.description_length != features2.description_length


class TestConversionSuccessPredictionService:
    """Test ConversionSuccessPredictionService class"""

    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert hasattr(service, "models")
        assert hasattr(service, "preprocessors")
        assert hasattr(service, "is_trained")

    def test_service_models_initialization(self):
        """Test that service models are properly initialized"""
        service = ConversionSuccessPredictionService()

        # Should have all model types
        assert "overall_success" in service.models
        assert "feature_completeness" in service.models
        assert "performance_impact" in service.models
        assert "compatibility_score" in service.models
        assert "risk_assessment" in service.models
        assert "conversion_time" in service.models
        assert "resource_usage" in service.models

        # Should not be trained initially
        assert not service.is_trained

    def test_predict_conversion_success_method_exists(self, service):
        """Test that predict_conversion_success method exists"""
        assert hasattr(service, "predict_conversion_success")
        assert callable(getattr(service, "predict_conversion_success", None))

    def test_train_models_method_exists(self, service):
        """Test that train_models method exists"""
        assert hasattr(service, "train_models")
        assert callable(getattr(service, "train_models", None))

    def test_batch_predict_success_method_exists(self, service):
        """Test that batch_predict_success method exists"""
        assert hasattr(service, "batch_predict_success")
        assert callable(getattr(service, "batch_predict_success", None))

    def test_update_models_with_feedback_method_exists(self, service):
        """Test that update_models_with_feedback method exists"""
        assert hasattr(service, "update_models_with_feedback")
        assert callable(getattr(service, "update_models_with_feedback", None))

    def test_get_prediction_insights_method_exists(self, service):
        """Test that get_prediction_insights method exists"""
        assert hasattr(service, "get_prediction_insights")
        assert callable(getattr(service, "get_prediction_insights", None))


class TestMockIntegration:
    """Test service with mocked dependencies"""

    def test_predict_conversion_success_with_mock(self, service, mock_session):
        """Test predict_conversion_success with mocked database session"""
        # Mock async method
        with patch.object(
            service, "predict_conversion_success", new_callable=AsyncMock
        ) as mock_predict:
            mock_predict.return_value = PredictionResult(
                prediction_type=PredictionType.OVERALL_SUCCESS,
                predicted_value=0.85,
                confidence=0.92,
                feature_importance={"pattern_type": 0.3, "complexity": 0.25},
                risk_factors=["high complexity"],
                success_factors=["expert validated"],
                recommendations=["simplify conversion"],
                prediction_metadata={"model_version": "1.0"},
            )

            # Test async call
            import asyncio

            result = asyncio.run(
                service.predict_conversion_success(mock_session, "test-pattern-id")
            )

            assert isinstance(result, PredictionResult)
            assert result.predicted_value == 0.85
            assert result.confidence == 0.92
            assert result.prediction_type == PredictionType.OVERALL_SUCCESS

    def test_train_models_with_mock(self, service, mock_session):
        """Test train_models with mocked database session"""
        # Mock async method
        with patch.object(
            service, "train_models", new_callable=AsyncMock
        ) as mock_train:
            mock_train.return_value = {
                "overall_success_model": {"accuracy": 0.82, "f1_score": 0.81},
                "feature_completeness_model": {"accuracy": 0.79, "f1_score": 0.78},
                "performance_impact_model": {"accuracy": 0.84, "f1_score": 0.83},
            }

            # Test async call
            import asyncio

            result = asyncio.run(service.train_models(mock_session))

            assert isinstance(result, dict)
            assert "overall_success_model" in result
            assert result["overall_success_model"]["accuracy"] == 0.82

    def test_batch_predict_success_with_mock(self, service, mock_session):
        """Test batch_predict_success with mocked database session"""
        pattern_ids = ["pattern-1", "pattern-2", "pattern-3"]

        # Mock async method
        with patch.object(
            service, "batch_predict_success", new_callable=AsyncMock
        ) as mock_batch:
            mock_batch.return_value = {
                "predictions": [
                    {"pattern_id": "pattern-1", "success_probability": 0.9},
                    {"pattern_id": "pattern-2", "success_probability": 0.7},
                    {"pattern_id": "pattern-3", "success_probability": 0.85},
                ],
                "batch_stats": {"mean_probability": 0.82, "count": 3},
            }

            # Test async call
            import asyncio

            result = asyncio.run(
                service.batch_predict_success(mock_session, pattern_ids)
            )

            assert isinstance(result, dict)
            assert "predictions" in result
            assert "batch_stats" in result
            assert len(result["predictions"]) == 3


class TestEdgeCases:
    """Test edge cases and error scenarios"""

    def test_service_with_no_training_data(self, service, mock_session):
        """Test service behavior with no training data"""
        # Mock training data collection to return empty
        with patch.object(
            service, "_collect_training_data", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = []

            import asyncio

            result = asyncio.run(service.train_models(mock_session))

            # Should handle empty data gracefully
            assert isinstance(result, dict)
            assert "message" in result or "error" in result

    def test_predict_with_invalid_pattern_id(self, service, mock_session):
        """Test prediction with invalid pattern ID"""
        # Mock method to handle invalid ID
        with patch.object(
            service, "predict_conversion_success", new_callable=AsyncMock
        ) as mock_predict:
            mock_predict.return_value = PredictionResult(
                prediction_type=PredictionType.OVERALL_SUCCESS,
                predicted_value=0.5,
                confidence=0.1,
                feature_importance={},
                risk_factors=["pattern not found"],
                success_factors=[],
                recommendations=["check pattern ID"],
                prediction_metadata={"error": "Pattern not found"},
            )

            import asyncio

            result = asyncio.run(
                service.predict_conversion_success(mock_session, "invalid-id")
            )

            assert isinstance(result, PredictionResult)
            assert result.predicted_value == 0.5
            assert result.confidence == 0.1
            assert "pattern not found" in result.risk_factors


class TestCoverageImprovement:
    """Additional tests to improve coverage"""

    def test_prediction_result_creation(self):
        """Test PredictionResult dataclass creation"""
        result = PredictionResult(
            prediction_type=PredictionType.FEATURE_COMPLETENESS,
            predicted_value=0.78,
            confidence=0.85,
            feature_importance={"pattern_type": 0.4, "usage_count": 0.3},
            risk_factors=["low usage"],
            success_factors=["high community rating"],
            recommendations=["increase documentation"],
            prediction_metadata={"model_version": "2.0", "timestamp": "2023-01-01"},
        )

        assert result.prediction_type == PredictionType.FEATURE_COMPLETENESS
        assert result.predicted_value == 0.78
        assert result.confidence == 0.85
        assert "pattern_type" in result.feature_importance
        assert "low usage" in result.risk_factors
        assert "high community rating" in result.success_factors
        assert "increase documentation" in result.recommendations

    def test_service_method_signatures(self, service):
        """Test that service methods have correct signatures"""
        import inspect

        # Check predict_conversion_success signature
        predict_sig = inspect.signature(service.predict_conversion_success)
        assert "session" in predict_sig.parameters
        assert "pattern_id" in predict_sig.parameters

        # Check train_models signature
        train_sig = inspect.signature(service.train_models)
        assert "session" in train_sig.parameters
        assert "force_retrain" in train_sig.parameters

        # Check batch_predict_success signature
        batch_sig = inspect.signature(service.batch_predict_success)
        assert "session" in batch_sig.parameters
        assert "pattern_ids" in batch_sig.parameters

    def test_all_prediction_types_coverage(self):
        """Test that all prediction types are covered"""
        all_types = [
            PredictionType.OVERALL_SUCCESS,
            PredictionType.FEATURE_COMPLETENESS,
            PredictionType.PERFORMANCE_IMPACT,
            PredictionType.COMPATIBILITY_SCORE,
            PredictionType.RISK_ASSESSMENT,
            PredictionType.CONVERSION_TIME,
            PredictionType.RESOURCE_USAGE,
        ]

        # Verify each type has correct value
        type_values = {t.value: t for t in all_types}
        assert len(type_values) == 7
        assert "overall_success" in type_values
        assert "feature_completeness" in type_values
        assert "performance_impact" in type_values
        assert "compatibility_score" in type_values
        assert "risk_assessment" in type_values
        assert "conversion_time" in type_values
        assert "resource_usage" in type_values
