"""
Comprehensive tests for conversion_success_prediction.py
Enhanced with actual test logic for 80% coverage target
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.conversion_success_prediction import (
    ConversionSuccessPredictionService,
    ConversionFeatures,
    PredictionType,
    PredictionResult,
)


class TestConversionSuccessPredictionService:
    """Test suite for ConversionSuccessPredictionService"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return ConversionSuccessPredictionService()

    @pytest.fixture
    def sample_features(self):
        """Sample conversion features for testing"""
        return ConversionFeatures(
            java_concept="BiomeDecorator",
            bedrock_concept="BiomeFeature",
            pattern_type="structural_transformation",
            minecraft_version="1.20.1",
            node_type="decoration",
            platform="java",
            description_length=150,
            expert_validated=True,
            community_rating=4.2,
            usage_count=25,
            relationship_count=8,
            success_history=[0.8, 0.9, 0.85, 0.88],
            feature_count=12,
            complexity_score=0.65,
            version_compatibility=0.92,
            cross_platform_difficulty=0.4,
        )

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initialization and model setup"""
        assert not service.is_trained
        assert hasattr(service, "models")
        assert hasattr(service, "preprocessors")

    @pytest.mark.asyncio
    async def test_train_models_basic(self, service, sample_features):
        """Test basic model training functionality"""
        # Mock historical data with 100+ samples as required
        mock_historical_data = [
            {
                "java_concept": "TestConcept",
                "bedrock_concept": "TestBedrock",
                "pattern_type": "direct_conversion",
                "minecraft_version": "latest",
                "overall_success": 1,
                "feature_completeness": 0.85,
                "performance_impact": 0.8,
                "compatibility_score": 0.9,
                "risk_assessment": 0,
                "conversion_time": 1.0,
                "resource_usage": 0.5,
                "expert_validated": True,
                "usage_count": 10,
                "confidence_score": 0.85,
                "features": {"test": "feature"},
                "metadata": {},
            }
        ] * 100  # Create 100 samples as required

        with patch.object(
            service, "_collect_training_data", return_value=mock_historical_data
        ):
            with patch.object(
                service,
                "_prepare_training_data",
                return_value=(
                    [
                        {
                            "expert_validated": 1,
                            "usage_count": 0.1,
                            "confidence_score": 0.85,
                            "feature_count": 1,
                            "pattern_type_encoded": 1.0,
                            "version_compatibility": 0.9,
                        }
                    ]
                    * 100,
                    {
                        "overall_success": [1] * 100,
                        "feature_completeness": [0.85] * 100,
                        "performance_impact": [0.8] * 100,
                        "compatibility_score": [0.9] * 100,
                        "risk_assessment": [0] * 100,
                        "conversion_time": [1.0] * 100,
                        "resource_usage": [0.5] * 100,
                    },
                ),
            ):
                result = await service.train_models(None)  # Need db parameter

                assert result["success"] is True
                assert "training_samples" in result

    @pytest.mark.asyncio
    async def test_train_models_insufficient_data(self, service):
        """Test model training with insufficient data"""
        mock_historical_data = []  # Empty data

        with patch.object(
            service, "_collect_training_data", return_value=mock_historical_data
        ):
            result = await service.train_models(None)  # Need db parameter

            assert result["success"] is False
            assert "Insufficient training data" in result["error"]

    @pytest.mark.asyncio
    async def test_predict_conversion_success_basic(self, service, sample_features):
        """Test basic prediction functionality"""
        # Setup trained model
        service.is_trained = True

        with patch.object(
            service, "_extract_conversion_features", return_value=sample_features
        ):
            with patch.object(
                service,
                "_prepare_feature_vector",
                return_value=np.array([1, 0, 1, 0, 1, 0]),
            ):
                with patch.object(
                    service,
                    "_make_prediction",
                    return_value=PredictionResult(
                        prediction_type=PredictionType.OVERALL_SUCCESS,
                        predicted_value=0.82,
                        confidence=0.82,
                        feature_importance={},
                        risk_factors=[],
                        success_factors=[],
                        recommendations=[],
                        prediction_metadata={},
                    ),
                ):
                    with patch.object(
                        service, "_analyze_conversion_viability", return_value={}
                    ):
                        with patch.object(
                            service,
                            "_generate_conversion_recommendations",
                            return_value=[],
                        ):
                            with patch.object(
                                service, "_identify_issues_mitigations", return_value={}
                            ):
                                with patch.object(service, "_store_prediction"):
                                    result = await service.predict_conversion_success(
                                        "TestConcept",
                                        "TestBedrock",
                                        "test_pattern",
                                        "latest",
                                        {},
                                        None,
                                    )

                                    assert result["success"] is True
                                    assert "predictions" in result

    @pytest.mark.asyncio
    async def test_predict_conversion_success_no_model(self, service, sample_features):
        """Test prediction when model is not trained"""
        # Ensure model is not trained
        service.is_trained = False

        result = await service.predict_conversion_success(
            "TestConcept", "TestBedrock", "test_pattern", "latest", {}, None
        )

        assert result["success"] is False
        assert "not trained" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_predict_success_basic(self, service, sample_features):
        """Test batch prediction functionality"""
        # Setup trained model
        service.is_trained = True

        conversions = [
            {"java_concept": "Concept1", "bedrock_concept": "Bedrock1"},
            {"java_concept": "Concept2", "bedrock_concept": "Bedrock2"},
            {"java_concept": "Concept3", "bedrock_concept": "Bedrock3"},
        ]

        with patch.object(
            service,
            "predict_conversion_success",
            return_value={
                "success": True,
                "predictions": {"overall_success": {"predicted_value": 0.82}},
            },
        ):
            result = await service.batch_predict_success(conversions, None)

            assert result["success"] is True
            assert result["total_conversions"] == 3
            assert "batch_results" in result
            assert len(result["batch_results"]) == 3

    def test_encode_pattern_type_basic(self, service):
        """Test pattern type encoding"""
        # Test known pattern types
        encoded = service._encode_pattern_type("direct_conversion")
        assert isinstance(encoded, float)

        encoded2 = service._encode_pattern_type("entity_conversion")
        assert isinstance(encoded2, float)

        # Should return different values for different patterns
        assert encoded != encoded2

    def test_encode_pattern_type_unknown(self, service):
        """Test encoding unknown pattern type"""
        encoded = service._encode_pattern_type("unknown_pattern")
        assert isinstance(encoded, float)
        # Should handle gracefully without error

    def test_calculate_complexity_basic(self, service):
        """Test complexity calculation"""
        mock_node = Mock()
        mock_node.description = "Test node with medium complexity"
        mock_node.relationship_count = 5
        mock_node.feature_count = 8

        complexity = service._calculate_complexity(mock_node)
        assert isinstance(complexity, float)
        assert 0.0 <= complexity <= 1.0  # Should be normalized

    def test_calculate_cross_platform_difficulty_basic(self, service):
        """Test cross-platform difficulty calculation"""
        # Create mock node
        mock_node = Mock()
        mock_node.platform = "java"
        mock_node.node_type = "entity"

        difficulty_java = service._calculate_cross_platform_difficulty(
            mock_node, "bedrock_concept"
        )

        assert isinstance(difficulty_java, float)
        assert 0.0 <= difficulty_java <= 1.0

    def test_get_feature_importance_basic(self, service):
        """Test feature importance calculation"""
        mock_model = Mock()
        mock_model.feature_importances_ = np.array([0.25, 0.20, 0.15, 0.15, 0.15, 0.10])

        importance = service._get_feature_importance(
            mock_model, PredictionType.OVERALL_SUCCESS
        )
        assert isinstance(importance, dict)
        assert len(importance) > 0

    def test_calculate_prediction_confidence_basic(self, service):
        """Test prediction confidence calculation"""
        mock_model = Mock()
        mock_model.predict_proba = Mock(return_value=np.array([[0.2, 0.8]]))

        confidence = service._calculate_prediction_confidence(
            mock_model, np.array([1, 0, 1, 0]), PredictionType.OVERALL_SUCCESS
        )
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_identify_risk_factors_basic(self, service, sample_features):
        """Test risk factor identification"""
        risks = service._identify_risk_factors(
            sample_features, PredictionType.OVERALL_SUCCESS, 0.5
        )
        assert isinstance(risks, list)
        # Should return some risk factors even for good features

    def test_identify_success_factors_basic(self, service, sample_features):
        """Test success factor identification"""
        factors = service._identify_success_factors(
            sample_features, PredictionType.OVERALL_SUCCESS, 0.8
        )
        assert isinstance(factors, list)
        # Should return some success factors

    def test_generate_type_recommendations_basic(self, service, sample_features):
        """Test type recommendations generation"""
        recommendations = service._generate_type_recommendations(
            PredictionType.OVERALL_SUCCESS, 0.7, sample_features
        )
        assert isinstance(recommendations, list)


class TestConversionFeatures:
    """Test suite for ConversionFeatures dataclass"""

    def test_conversion_features_creation(self):
        """Test ConversionFeatures dataclass creation"""
        features = ConversionFeatures(
            java_concept="BlockEntity",
            bedrock_concept="BlockComponent",
            pattern_type="entity_transformation",
            minecraft_version="1.19.4",
            node_type="entity",
            platform="java",
            description_length=120,
            expert_validated=False,
            community_rating=3.8,
            usage_count=15,
            relationship_count=5,
            success_history=[0.7, 0.8, 0.75],
            feature_count=8,
            complexity_score=0.55,
            version_compatibility=0.88,
            cross_platform_difficulty=0.3,
        )

        assert features.java_concept == "BlockEntity"
        assert features.bedrock_concept == "BlockComponent"
        assert features.pattern_type == "entity_transformation"
        assert features.minecraft_version == "1.19.4"
        assert features.node_type == "entity"
        assert features.platform == "java"
        assert features.description_length == 120
        assert not features.expert_validated
        assert features.community_rating == 3.8
        assert features.success_history == [0.7, 0.8, 0.75]

    def test_conversion_features_equality(self):
        """Test ConversionFeatures equality comparison"""
        features1 = ConversionFeatures(
            java_concept="BlockEntity",
            bedrock_concept="BlockComponent",
            pattern_type="entity_transformation",
            minecraft_version="1.19.4",
            node_type="entity",
            platform="java",
            description_length=120,
            expert_validated=False,
            community_rating=3.8,
            usage_count=15,
            relationship_count=5,
            success_history=[0.7, 0.8, 0.75],
            feature_count=8,
            complexity_score=0.55,
            version_compatibility=0.88,
            cross_platform_difficulty=0.3,
        )

        features2 = ConversionFeatures(
            java_concept="BlockEntity",
            bedrock_concept="BlockComponent",
            pattern_type="entity_transformation",
            minecraft_version="1.19.4",
            node_type="entity",
            platform="java",
            description_length=120,
            expert_validated=False,
            community_rating=3.8,
            usage_count=15,
            relationship_count=5,
            success_history=[0.7, 0.8, 0.75],
            feature_count=8,
            complexity_score=0.55,
            version_compatibility=0.88,
            cross_platform_difficulty=0.3,
        )

        assert features1 == features2


class TestPredictionType:
    """Test suite for PredictionType enum"""

    def test_prediction_type_values(self):
        """Test PredictionType enum values"""
        assert PredictionType.OVERALL_SUCCESS.value == "overall_success"
        assert PredictionType.FEATURE_COMPLETENESS.value == "feature_completeness"
        assert PredictionType.PERFORMANCE_IMPACT.value == "performance_impact"
        assert PredictionType.COMPATIBILITY_SCORE.value == "compatibility_score"
        assert PredictionType.RISK_ASSESSMENT.value == "risk_assessment"
        assert PredictionType.CONVERSION_TIME.value == "conversion_time"
        assert PredictionType.RESOURCE_USAGE.value == "resource_usage"

    def test_prediction_type_uniqueness(self):
        """Test that all prediction types have unique values"""
        values = [ptype.value for ptype in PredictionType]
        assert len(values) == len(set(values))


class TestPredictionResult:
    """Test suite for PredictionResult dataclass"""

    def test_prediction_result_creation(self):
        """Test PredictionResult dataclass creation"""
        result = PredictionResult(
            prediction_type=PredictionType.OVERALL_SUCCESS,
            predicted_value=0.85,
            confidence=0.82,
            feature_importance={"java_concept": 0.3, "bedrock_concept": 0.25},
            risk_factors=["complex_structure"],
            success_factors=["similar_patterns"],
            recommendations=["test_thoroughly"],
            prediction_metadata={"model_version": "1.0"},
        )

        assert result.prediction_type == PredictionType.OVERALL_SUCCESS
        assert result.predicted_value == 0.85
        assert result.confidence == 0.82
        assert len(result.feature_importance) == 2
        assert "complex_structure" in result.risk_factors
        assert "similar_patterns" in result.success_factors
        assert "test_thoroughly" in result.recommendations
        assert result.prediction_metadata["model_version"] == "1.0"
