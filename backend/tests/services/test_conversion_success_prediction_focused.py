"""
Focused tests for conversion_success_prediction.py to improve coverage
Tests the core functionality with proper mocking
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
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


class TestConversionSuccessPredictionFocused:
    """Focused test suite for ConversionSuccessPredictionService"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return ConversionSuccessPredictionService()

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock()

    def test_service_initialization(self, service):
        """Test service initialization and model setup"""
        assert not service.is_trained
        assert hasattr(service, "models")
        assert hasattr(service, "preprocessors")

        # Check all required models are initialized
        expected_models = [
            "overall_success",
            "feature_completeness",
            "performance_impact",
            "compatibility_score",
            "risk_assessment",
            "conversion_time",
            "resource_usage",
        ]
        for model_name in expected_models:
            assert model_name in service.models

    def test_encode_pattern_type(self, service):
        """Test pattern type encoding"""
        assert service._encode_pattern_type("direct_conversion") == 1.0
        assert service._encode_pattern_type("entity_conversion") == 0.8
        assert service._encode_pattern_type("block_conversion") == 0.7
        assert service._encode_pattern_type("item_conversion") == 0.6
        assert service._encode_pattern_type("behavior_conversion") == 0.5
        assert service._encode_pattern_type("command_conversion") == 0.4
        assert service._encode_pattern_type("unknown") == 0.3
        assert service._encode_pattern_type("invalid_pattern") == 0.3

    def test_calculate_complexity(self, service):
        """Test complexity score calculation"""
        mock_node = Mock()
        mock_node.properties = '{"type": "entity", "behaviors": ["ai"]}'
        mock_node.description = "Test entity with description"
        mock_node.node_type = "entity"

        complexity = service._calculate_complexity(mock_node)
        assert 0.0 <= complexity <= 1.0
        assert isinstance(complexity, float)

    def test_calculate_complexity_exception(self, service):
        """Test complexity calculation with exception"""
        mock_node = Mock()
        mock_node.properties = "invalid json"
        mock_node.description = "test"
        mock_node.node_type = "unknown"

        complexity = service._calculate_complexity(mock_node)
        assert isinstance(complexity, float)
        assert 0.0 <= complexity <= 1.0

    def test_calculate_cross_platform_difficulty(self, service):
        """Test cross-platform difficulty calculation"""
        mock_node = Mock()
        mock_node.platform = "java"
        mock_node.node_type = "entity"

        difficulty = service._calculate_cross_platform_difficulty(
            mock_node, "TargetConcept"
        )
        assert 0.0 <= difficulty <= 1.0
        assert isinstance(difficulty, float)

    def test_get_feature_importance_tree_model(self, service):
        """Test feature importance extraction for tree models"""
        mock_model = Mock()
        mock_model.feature_importances_ = np.array(
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )

        importance = service._get_feature_importance(
            mock_model, PredictionType.OVERALL_SUCCESS
        )
        assert isinstance(importance, dict)
        assert len(importance) == 10
        assert "expert_validated" in importance

    def test_get_feature_importance_linear_model(self, service):
        """Test feature importance extraction for linear models"""
        mock_model = Mock()
        mock_model.coef_ = np.array([0.1, -0.2, 0.3, -0.4, 0.5])
        # Remove tree model attribute
        if hasattr(mock_model, "feature_importances_"):
            del mock_model.feature_importances_

        importance = service._get_feature_importance(
            mock_model, PredictionType.OVERALL_SUCCESS
        )
        assert isinstance(importance, dict)
        assert len(importance) <= 5

    def test_get_feature_importance_no_importance(self, service):
        """Test feature importance when model doesn't support it"""
        mock_model = Mock()
        # Ensure it doesn't have any importance attributes
        if hasattr(mock_model, "feature_importances_"):
            del mock_model.feature_importances_
        if hasattr(mock_model, "coef_"):
            del mock_model.coef_

        importance = service._get_feature_importance(
            mock_model, PredictionType.OVERALL_SUCCESS
        )
        assert importance == {}

    def test_calculate_prediction_confidence_classification(self, service):
        """Test confidence calculation for classification models"""
        mock_model = Mock()
        mock_model.predict_proba.return_value = [[0.2, 0.8]]

        confidence = service._calculate_prediction_confidence(
            mock_model, np.array([1, 2, 3]), PredictionType.OVERALL_SUCCESS
        )
        assert confidence == 0.8

    def test_calculate_prediction_confidence_regression(self, service):
        """Test confidence calculation for regression models"""
        mock_model = Mock()
        # Remove predict_proba to simulate regression model
        if hasattr(mock_model, "predict_proba"):
            del mock_model.predict_proba

        confidence = service._calculate_prediction_confidence(
            mock_model, np.array([1, 2, 3]), PredictionType.FEATURE_COMPLETENESS
        )
        assert confidence == 0.7

    def test_identify_risk_factors(self, service):
        """Test risk factor identification"""
        features = ConversionFeatures(
            java_concept="Test",
            bedrock_concept="Target",
            pattern_type="unknown",
            minecraft_version="1.20.1",
            node_type="unknown",
            platform="java",
            description_length=10,
            expert_validated=False,
            community_rating=0.3,
            usage_count=1,
            relationship_count=0,
            success_history=[],
            feature_count=1,
            complexity_score=0.9,
            version_compatibility=0.5,
            cross_platform_difficulty=0.8,
        )

        risk_factors = service._identify_risk_factors(
            features, PredictionType.OVERALL_SUCCESS, 0.3
        )
        assert isinstance(risk_factors, list)
        assert len(risk_factors) > 0

    def test_identify_success_factors(self, service):
        """Test success factor identification"""
        features = ConversionFeatures(
            java_concept="Test",
            bedrock_concept="Target",
            pattern_type="direct_conversion",
            minecraft_version="latest",
            node_type="entity",
            platform="both",
            description_length=100,
            expert_validated=True,
            community_rating=4.8,
            usage_count=100,
            relationship_count=10,
            success_history=[0.9, 0.95],
            feature_count=15,
            complexity_score=0.3,
            version_compatibility=0.95,
            cross_platform_difficulty=0.2,
        )

        success_factors = service._identify_success_factors(
            features, PredictionType.OVERALL_SUCCESS, 0.9
        )
        assert isinstance(success_factors, list)
        assert len(success_factors) > 0

    def test_generate_type_recommendations(self, service):
        """Test recommendation generation for specific prediction types"""
        features = ConversionFeatures(
            java_concept="Test",
            bedrock_concept="Target",
            pattern_type="entity_conversion",
            minecraft_version="1.20.1",
            node_type="entity",
            platform="java",
            description_length=50,
            expert_validated=True,
            community_rating=4.0,
            usage_count=20,
            relationship_count=5,
            success_history=[0.8],
            feature_count=8,
            complexity_score=0.6,
            version_compatibility=0.8,
            cross_platform_difficulty=0.5,
        )

        # Test overall success recommendations
        recommendations = service._generate_type_recommendations(
            PredictionType.OVERALL_SUCCESS, 0.9, features
        )
        assert any("High success probability" in rec for rec in recommendations)

        # Test feature completeness recommendations
        recommendations = service._generate_type_recommendations(
            PredictionType.FEATURE_COMPLETENESS, 0.5, features
        )
        assert any("feature gaps" in rec for rec in recommendations)

    def test_get_recommended_action(self, service):
        """Test recommended action generation"""
        assert "proceed" in service._get_recommended_action("high").lower()
        assert "caution" in service._get_recommended_action("medium").lower()
        assert "alternatives" in service._get_recommended_action("low").lower()
        assert "not recommended" in service._get_recommended_action("very_low").lower()
        assert service._get_recommended_action("unknown") == "Unknown viability level"

    @pytest.mark.asyncio
    async def test_collect_training_data_exception(self, service, mock_db):
        """Test training data collection with exception"""
        with patch(
            "src.services.conversion_success_prediction.ConversionPatternCRUD"
        ) as mock_crud:
            mock_crud.get_by_version.side_effect = Exception("Database error")

            training_data = await service._collect_training_data(mock_db)
            assert training_data == []

    @pytest.mark.asyncio
    async def test_prepare_training_data_exception(self, service):
        """Test training data preparation with exception"""
        features, targets = await service._prepare_training_data([])
        assert features == []
        assert targets == {}

    @pytest.mark.asyncio
    async def test_train_model_insufficient_data(self, service):
        """Test model training with insufficient data"""
        features = [{"test": "data"}] * 5  # Less than minimum 10
        targets = [1] * 5

        result = await service._train_model(
            PredictionType.OVERALL_SUCCESS, features, targets
        )
        assert "error" in result
        assert "Insufficient data" in result["error"]

    @pytest.mark.asyncio
    async def test_train_model_exception(self, service):
        """Test model training with exception"""
        features = [{"invalid": "data"}] * 100
        targets = []  # Empty targets will cause an error

        result = await service._train_model(
            PredictionType.OVERALL_SUCCESS, features, targets
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_extract_conversion_features_no_node(self, service, mock_db):
        """Test feature extraction with no existing knowledge node"""
        with patch(
            "src.services.conversion_success_prediction.KnowledgeNodeCRUD"
        ) as mock_crud:
            mock_crud.search.return_value = []

            features = await service._extract_conversion_features(
                "UnknownConcept",
                "TargetConcept",
                "entity_conversion",
                "1.20.1",
                mock_db,
            )
            assert features is not None
            assert features.java_concept == "UnknownConcept"
            assert features.node_type == "unknown"
            assert not features.expert_validated

    @pytest.mark.asyncio
    async def test_extract_conversion_features_exception(self, service, mock_db):
        """Test feature extraction with exception"""
        with patch(
            "src.services.conversion_success_prediction.KnowledgeNodeCRUD"
        ) as mock_crud:
            mock_crud.search.side_effect = Exception("Search error")

            features = await service._extract_conversion_features(
                "TestConcept", "TargetConcept", "entity_conversion", "1.20.1", mock_db
            )
            assert features is None

    @pytest.mark.asyncio
    async def test_prepare_feature_vector(self, service):
        """Test feature vector preparation"""
        features = ConversionFeatures(
            java_concept="Test",
            bedrock_concept="Target",
            pattern_type="entity_conversion",
            minecraft_version="1.20.1",
            node_type="entity",
            platform="java",
            description_length=50,
            expert_validated=True,
            community_rating=4.0,
            usage_count=20,
            relationship_count=5,
            success_history=[0.8],
            feature_count=8,
            complexity_score=0.6,
            version_compatibility=0.8,
            cross_platform_difficulty=0.5,
        )

        # Mock the scaler to avoid fitting issues
        service.preprocessors["feature_scaler"].fit = Mock(return_value=None)
        service.preprocessors["feature_scaler"].transform = Mock(
            return_value=np.array([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]])
        )

        feature_vector = await service._prepare_feature_vector(features)
        assert len(feature_vector) == 10
        assert isinstance(feature_vector, np.ndarray)

    @pytest.mark.asyncio
    async def test_prepare_feature_vector_exception(self, service):
        """Test feature vector preparation with exception"""
        features = ConversionFeatures(
            java_concept="Test",
            bedrock_concept="Target",
            pattern_type="entity_conversion",
            minecraft_version="1.20.1",
            node_type="entity",
            platform="java",
            description_length=50,
            expert_validated=True,
            community_rating=4.0,
            usage_count=20,
            relationship_count=5,
            success_history=[0.8],
            feature_count=8,
            complexity_score=0.6,
            version_compatibility=0.8,
            cross_platform_difficulty=0.5,
        )

        service.preprocessors["feature_scaler"].transform.side_effect = Exception(
            "Transform error"
        )

        feature_vector = await service._prepare_feature_vector(features)
        assert len(feature_vector) == 10
        assert np.all(feature_vector == 0)

    @pytest.mark.asyncio
    async def test_predict_conversion_success_not_trained(self, service):
        """Test prediction when models not trained"""
        service.is_trained = False

        result = await service.predict_conversion_success("TestConcept")
        assert result["success"] is False
        assert "ML models not trained" in result["error"]

    @pytest.mark.asyncio
    async def test_predict_conversion_success_no_features(self, service):
        """Test prediction when feature extraction fails"""
        service.is_trained = True

        with patch.object(service, "_extract_conversion_features", return_value=None):
            result = await service.predict_conversion_success("TestConcept")
            assert result["success"] is False
            assert "Unable to extract conversion features" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_predict_success_not_trained(self, service):
        """Test batch prediction when models not trained"""
        service.is_trained = False
        conversions = [{"java_concept": "Test1"}, {"java_concept": "Test2"}]

        result = await service.batch_predict_success(conversions)
        assert result["success"] is False
        assert "ML models not trained" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_predict_success(self, service):
        """Test successful batch prediction"""
        service.is_trained = True
        conversions = [
            {"java_concept": "Test1", "bedrock_concept": "Target1"},
            {"java_concept": "Test2", "bedrock_concept": "Target2"},
        ]

        with patch.object(service, "predict_conversion_success") as mock_predict:
            mock_predict.return_value = {
                "success": True,
                "predictions": {"overall_success": {"predicted_value": 0.8}},
            }

            result = await service.batch_predict_success(conversions)
            assert result["success"] is True
            assert result["total_conversions"] == 2
            assert "batch_results" in result

    @pytest.mark.asyncio
    async def test_update_models_with_feedback_no_prediction(self, service):
        """Test model update with no stored prediction"""
        service.prediction_history = []

        result = await service.update_models_with_feedback(
            "test_id", {"overall_success": 1}
        )
        assert result["success"] is False
        assert "No stored prediction found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_prediction_insights_not_trained(self, service):
        """Test getting insights when models not trained"""
        service.is_trained = False

        result = await service.get_prediction_insights()
        assert result["success"] is False
        assert "ML models not trained" in result["error"]

    @pytest.mark.asyncio
    async def test_make_prediction_exception(self, service):
        """Test prediction with exception"""
        features = ConversionFeatures(
            java_concept="Test",
            bedrock_concept="Target",
            pattern_type="entity_conversion",
            minecraft_version="1.20.1",
            node_type="entity",
            platform="java",
            description_length=50,
            expert_validated=True,
            community_rating=4.0,
            usage_count=20,
            relationship_count=5,
            success_history=[0.8],
            feature_count=8,
            complexity_score=0.6,
            version_compatibility=0.8,
            cross_platform_difficulty=0.5,
        )

        feature_vector = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        prediction = await service._make_prediction(
            PredictionType.OVERALL_SUCCESS, feature_vector, features
        )
        assert prediction.prediction_type == PredictionType.OVERALL_SUCCESS
        assert prediction.predicted_value == 0.5  # Default fallback value
        assert prediction.confidence == 0.0

    @pytest.mark.asyncio
    async def test_analyze_conversion_viability(self, service):
        """Test conversion viability analysis"""
        predictions = {
            "overall_success": PredictionResult(
                PredictionType.OVERALL_SUCCESS, 0.8, 0.9, {}, [], [], [], {}
            ),
            "risk_assessment": PredictionResult(
                PredictionType.RISK_ASSESSMENT, 0.2, 0.8, {}, [], [], [], {}
            ),
            "feature_completeness": PredictionResult(
                PredictionType.FEATURE_COMPLETENESS, 0.85, 0.85, {}, [], [], [], {}
            ),
        }

        viability = await service._analyze_conversion_viability(
            "JavaConcept", "BedrockConcept", predictions
        )
        assert "viability_score" in viability
        assert "viability_level" in viability
        assert "recommended_action" in viability
        assert 0.0 <= viability["viability_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_store_prediction(self, service):
        """Test prediction storage"""
        predictions = {
            PredictionType.OVERALL_SUCCESS: PredictionResult(
                PredictionType.OVERALL_SUCCESS, 0.8, 0.9, {}, [], [], [], {}
            )
        }

        # Clear history and store one prediction
        service.prediction_history = []
        await service._store_prediction(
            "JavaConcept", "BedrockConcept", predictions, {"test": "context"}
        )
        assert len(service.prediction_history) == 1
        assert service.prediction_history[0]["java_concept"] == "JavaConcept"

    def test_get_model_update_recommendation(self, service):
        """Test model update recommendation generation"""
        import asyncio

        # High accuracy
        recommendation = asyncio.run(
            service._get_model_update_recommendation({"overall_success": 0.9})
        )
        assert "performing well" in recommendation.lower()

        # Medium accuracy
        recommendation = asyncio.run(
            service._get_model_update_recommendation({"overall_success": 0.7})
        )
        assert "moderately" in recommendation.lower()

        # Low accuracy
        recommendation = asyncio.run(
            service._get_model_update_recommendation({"overall_success": 0.4})
        )
        assert "need improvement" in recommendation.lower()

    # Test singleton instance
    def test_singleton_instance(self):
        """Test that singleton instance is created correctly"""
        from src.services.conversion_success_prediction import (
            conversion_success_prediction_service,
        )

        assert conversion_success_prediction_service is not None
        assert isinstance(
            conversion_success_prediction_service, ConversionSuccessPredictionService
        )
