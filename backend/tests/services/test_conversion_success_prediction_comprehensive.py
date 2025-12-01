"""
Comprehensive tests for conversion_success_prediction.py
Created to improve code coverage for key methods and functionality
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
import numpy as np
from datetime import datetime, timedelta, UTC

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.conversion_success_prediction import (
    ConversionSuccessPredictionService,
    ConversionFeatures,
    PredictionType,
    PredictionResult,
)


class TestConversionSuccessPredictionServiceComprehensive:
    """Comprehensive test suite for ConversionSuccessPredictionService"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        return ConversionSuccessPredictionService()

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock()

    @pytest.fixture
    def sample_features(self):
        """Sample conversion features for testing"""
        return ConversionFeatures(
            java_concept="CustomEntity",
            bedrock_concept="BedrockEntity",
            pattern_type="entity_conversion",
            minecraft_version="1.20.1",
            node_type="entity",
            platform="java",
            description_length=200,
            expert_validated=True,
            community_rating=4.5,
            usage_count=100,
            relationship_count=15,
            success_history=[0.8, 0.9, 0.85, 0.92, 0.88],
            feature_count=20,
            complexity_score=0.7,
            version_compatibility=0.95,
            cross_platform_difficulty=0.3,
        )

    @pytest.fixture
    def mock_knowledge_node(self):
        """Mock knowledge node"""
        mock_node = Mock()
        mock_node.id = "test_node_id"
        mock_node.name = "TestConcept"
        mock_node.node_type = "entity"
        mock_node.platform = "java"
        mock_node.description = "Test entity concept"
        mock_node.expert_validated = True
        mock_node.community_rating = 4.2
        mock_node.properties = '{"type": "entity", "behaviors": ["ai", "movement"]}'
        mock_node.minecraft_version = "1.20.1"
        return mock_node

    @pytest.fixture
    def mock_relationship(self):
        """Mock knowledge relationship"""
        mock_rel = Mock()
        mock_rel.id = "test_rel_id"
        mock_rel.target_node_name = "TargetConcept"
        mock_rel.confidence_score = 0.85
        mock_rel.expert_validated = True
        return mock_rel

    @pytest.fixture
    def mock_conversion_pattern(self):
        """Mock conversion pattern"""
        mock_pattern = Mock()
        mock_pattern.java_concept = "JavaConcept"
        mock_pattern.bedrock_concept = "BedrockConcept"
        mock_pattern.pattern_type = "entity_conversion"
        mock_pattern.minecraft_version = "latest"
        mock_pattern.success_rate = 0.85
        mock_pattern.expert_validated = True
        mock_pattern.usage_count = 50
        mock_pattern.confidence_score = 0.88
        mock_pattern.conversion_features = '{"complexity": "medium"}'
        mock_pattern.validation_results = '{"status": "validated"}'
        return mock_pattern

    # Test service initialization
    def test_service_initialization_models(self, service):
        """Test that all required models are initialized"""
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
            assert service.models[model_name] is not None

    def test_service_initialization_preprocessors(self, service):
        """Test that preprocessors are initialized"""
        assert "feature_scaler" in service.preprocessors
        assert "label_encoders" in service.preprocessors
        assert service.preprocessors["feature_scaler"] is not None

    # Test model training
    @pytest.mark.asyncio
    async def test_train_models_success(
        self, service, mock_conversion_pattern, mock_db
    ):
        """Test successful model training"""
        mock_patterns = [mock_conversion_pattern] * 150  # Minimum 100 samples

        with patch(
            "src.services.conversion_success_prediction.ConversionPatternCRUD"
        ) as mock_crud:
            mock_crud.get_by_version.return_value = mock_patterns

            with patch(
                "src.services.conversion_success_prediction.KnowledgeNodeCRUD"
            ) as mock_node_crud:
                mock_node_crud.get_by_type.return_value = []

                result = await service.train_models(mock_db)

                assert result["success"] is True
                assert "training_samples" in result
                assert "feature_count" in result
                assert service.is_trained is True

    @pytest.mark.asyncio
    async def test_train_models_insufficient_data(self, service, mock_db):
        """Test model training with insufficient data"""
        with patch.object(service, "_collect_training_data", return_value=[]):
            result = await service.train_models(mock_db)

            assert result["success"] is False
            assert "Insufficient training data" in result["error"]

    @pytest.mark.asyncio
    async def test_train_models_already_trained(self, service):
        """Test model training when already trained"""
        service.is_trained = True
        service.model_metrics = {"test": "metric"}

        result = await service.train_models(mock_db, force_retrain=False)

        assert result["success"] is True
        assert "Models already trained" in result["message"]

    @pytest.mark.asyncio
    async def test_train_models_force_retrain(self, service, mock_conversion_pattern):
        """Test force retraining of models"""
        service.is_trained = True
        mock_patterns = [mock_conversion_pattern] * 150

        with patch(
            "src.services.conversion_success_prediction.ConversionPatternCRUD"
        ) as mock_crud:
            mock_crud.get_by_version.return_value = mock_patterns

            with patch(
                "src.services.conversion_success_prediction.KnowledgeNodeCRUD"
            ) as mock_node_crud:
                mock_node_crud.get_by_type.return_value = []

                result = await service.train_models(mock_db, force_retrain=True)

                assert result["success"] is True

    # Test data collection methods
    @pytest.mark.asyncio
    async def test_collect_training_data(
        self, service, mock_conversion_pattern, mock_knowledge_node, mock_relationship
    ):
        """Test training data collection"""
        mock_patterns = [mock_conversion_pattern] * 10
        mock_nodes = [mock_knowledge_node] * 5
        mock_relationships = [mock_relationship] * 3

        with patch(
            "src.services.conversion_success_prediction.ConversionPatternCRUD"
        ) as mock_crud:
            mock_crud.get_by_version.return_value = mock_patterns

            with patch(
                "src.services.conversion_success_prediction.KnowledgeNodeCRUD"
            ) as mock_node_crud:
                mock_node_crud.get_by_type.return_value = mock_nodes

                with patch(
                    "src.services.conversion_success_prediction.KnowledgeRelationshipCRUD"
                ) as mock_rel_crud:
                    mock_rel_crud.get_by_source.return_value = mock_relationships

                    training_data = await service._collect_training_data(mock_db)

                    assert len(training_data) > 0
                    assert all("java_concept" in sample for sample in training_data)
                    assert all("bedrock_concept" in sample for sample in training_data)

    @pytest.mark.asyncio
    async def test_collect_training_data_exception(self, service):
        """Test training data collection with exception"""
        with patch(
            "src.services.conversion_success_prediction.ConversionPatternCRUD"
        ) as mock_crud:
            mock_crud.get_by_version.side_effect = Exception("Database error")

            training_data = await service._collect_training_data(mock_db)

            assert training_data == []

    @pytest.mark.asyncio
    async def test_prepare_training_data(self, service):
        """Test training data preparation"""
        mock_training_data = [
            {
                "expert_validated": True,
                "usage_count": 50,
                "confidence_score": 0.85,
                "features": {"test": "feature"},
                "pattern_type": "direct_conversion",
                "minecraft_version": "latest",
                "overall_success": 1,
                "feature_completeness": 0.9,
                "performance_impact": 0.8,
                "compatibility_score": 0.95,
                "risk_assessment": 0,
                "conversion_time": 1.5,
                "resource_usage": 0.6,
            }
        ] * 100

        features, targets = await service._prepare_training_data(mock_training_data)

        assert len(features) == 100
        assert len(targets) > 0
        assert "expert_validated" in features[0]
        assert "overall_success" in targets

    @pytest.mark.asyncio
    async def test_prepare_training_data_exception(self, service):
        """Test training data preparation with exception"""
        features, targets = await service._prepare_training_data([])

        assert features == []
        assert targets == {}

    # Test pattern type encoding
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

    # Test individual model training
    @pytest.mark.asyncio
    async def test_train_model_success(self, service):
        """Test successful individual model training"""
        features = [
            {
                "expert_validated": 1,
                "usage_count": 0.5,
                "confidence_score": 0.8,
                "feature_count": 5,
                "pattern_type_encoded": 1.0,
                "version_compatibility": 0.9,
            }
            for _ in range(100)
        ]
        targets = [1] * 50 + [0] * 50  # Classification targets

        result = await service._train_model(
            PredictionType.OVERALL_SUCCESS, features, targets
        )

        assert "training_samples" in result
        assert "test_samples" in result
        assert "metrics" in result
        assert result["training_samples"] == 80  # 80% of 100 for train set

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
        targets = []

        result = await service._train_model(
            PredictionType.OVERALL_SUCCESS, features, targets
        )

        assert "error" in result

    # Test feature extraction
    @pytest.mark.asyncio
    async def test_extract_conversion_features_with_node(
        self, service, mock_knowledge_node, mock_relationship
    ):
        """Test feature extraction with existing knowledge node"""
        with patch(
            "src.services.conversion_success_prediction.KnowledgeNodeCRUD"
        ) as mock_crud:
            mock_crud.search.return_value = [mock_knowledge_node]

            with patch(
                "src.services.conversion_success_prediction.KnowledgeRelationshipCRUD"
            ) as mock_rel_crud:
                mock_rel_crud.get_by_source.return_value = [mock_relationship]

                features = await service._extract_conversion_features(
                    "TestConcept",
                    "TargetConcept",
                    "entity_conversion",
                    "1.20.1",
                    mock_db,
                )

                assert features is not None
                assert features.java_concept == "TestConcept"
                assert features.bedrock_concept == "TargetConcept"
                assert features.expert_validated
                assert features.relationship_count == 1

    @pytest.mark.asyncio
    async def test_extract_conversion_features_no_node(self, service):
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
    async def test_extract_conversion_features_exception(self, service):
        """Test feature extraction with exception"""
        with patch(
            "src.services.conversion_success_prediction.KnowledgeNodeCRUD"
        ) as mock_crud:
            mock_crud.search.side_effect = Exception("Search error")

            features = await service._extract_conversion_features(
                "TestConcept", "TargetConcept", "entity_conversion", "1.20.1", mock_db
            )

            assert features is None

    # Test complexity calculation
    def test_calculate_complexity(self, service, mock_knowledge_node):
        """Test complexity score calculation"""
        complexity = service._calculate_complexity(mock_knowledge_node)

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

    # Test cross-platform difficulty calculation
    def test_calculate_cross_platform_difficulty(self, service, mock_knowledge_node):
        """Test cross-platform difficulty calculation"""
        difficulty = service._calculate_cross_platform_difficulty(
            mock_knowledge_node, "TargetConcept"
        )

        assert 0.0 <= difficulty <= 1.0
        assert isinstance(difficulty, float)

    def test_calculate_cross_platform_difficulty_exception(self, service):
        """Test cross-platform difficulty calculation with exception"""
        mock_node = Mock()
        mock_node.platform = "invalid"
        mock_node.node_type = None

        difficulty = service._calculate_cross_platform_difficulty(mock_node, None)

        assert difficulty == 0.5

    # Test feature vector preparation
    @pytest.mark.asyncio
    async def test_prepare_feature_vector(self, service, sample_features):
        """Test feature vector preparation"""
        # Mock the scaler
        service.preprocessors["feature_scaler"].fit = Mock(return_value=None)
        service.preprocessors["feature_scaler"].transform = Mock(
            return_value=np.array([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]])
        )

        feature_vector = await service._prepare_feature_vector(sample_features)

        assert len(feature_vector) == 10
        assert isinstance(feature_vector, np.ndarray)

    @pytest.mark.asyncio
    async def test_prepare_feature_vector_exception(self, service, sample_features):
        """Test feature vector preparation with exception"""
        service.preprocessors["feature_scaler"].transform.side_effect = Exception(
            "Transform error"
        )

        feature_vector = await service._prepare_feature_vector(sample_features)

        assert len(feature_vector) == 10
        assert np.all(feature_vector == 0)

    # Test main prediction methods
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
            assert "batch_analysis" in result

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
    async def test_update_models_with_feedback_success(self, service):
        """Test successful model update with feedback"""
        # Add mock prediction to history
        service.prediction_history = [
            {
                "conversion_id": "test_id",
                "predictions": {
                    "overall_success": {"predicted_value": 0.8, "confidence": 0.9},
                    "feature_completeness": {"predicted_value": 0.7, "confidence": 0.8},
                },
                "java_concept": "TestConcept",
                "bedrock_concept": "TargetConcept",
                "context_data": {"pattern_type": "entity_conversion"},
            }
        ]

        actual_result = {
            "overall_success": 1.0,
            "feature_completeness": 0.9,
            "risk_assessment": 0,
        }

        result = await service.update_models_with_feedback("test_id", actual_result)

        assert result["success"] is True
        assert "accuracy_scores" in result
        assert "model_improvements" in result

    @pytest.mark.asyncio
    async def test_get_prediction_insights_not_trained(self, service):
        """Test getting insights when models not trained"""
        service.is_trained = False

        result = await service.get_prediction_insights()

        assert result["success"] is False
        assert "ML models not trained" in result["error"]

    @pytest.mark.asyncio
    async def test_get_prediction_insights_success(self, service):
        """Test successful prediction insights - simplified test"""
        service.is_trained = True
        service.prediction_history = [
            {
                "timestamp": (datetime.now(UTC) - timedelta(days=10)).isoformat(),
                "predictions": {"overall_success": {"predicted_value": 0.8}},
            }
        ]

        # Mock the missing methods
        with patch.object(service, "_analyze_prediction_accuracy", return_value={}):
            with patch.object(
                service, "_analyze_feature_importance_trends", return_value={}
            ):
                with patch.object(
                    service, "_identify_prediction_patterns", return_value={}
                ):
                    result = await service.get_prediction_insights(days=30)

                    assert result["success"] is True
                    assert "total_predictions" in result

    # Test helper methods
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
        del mock_model.feature_importances_  # Ensure it doesn't have tree importance

        importance = service._get_feature_importance(
            mock_model, PredictionType.OVERALL_SUCCESS
        )

        assert isinstance(importance, dict)
        assert len(importance) <= 5

    def test_get_feature_importance_no_importance(self, service):
        """Test feature importance when model doesn't support it"""
        mock_model = Mock()
        del mock_model.feature_importances_
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
        del mock_model.predict_proba

        confidence = service._calculate_prediction_confidence(
            mock_model, np.array([1, 2, 3]), PredictionType.FEATURE_COMPLETENESS
        )

        assert confidence == 0.7

    def test_identify_risk_factors(self, service, sample_features):
        """Test risk factor identification"""
        risk_factors = service._identify_risk_factors(
            sample_features, PredictionType.OVERALL_SUCCESS, 0.3
        )

        assert isinstance(risk_factors, list)
        # Should identify some risk factors due to low prediction value
        assert any("Low predicted success" in factor for factor in risk_factors)

    def test_identify_success_factors(self, service, sample_features):
        """Test success factor identification"""
        success_factors = service._identify_success_factors(
            sample_features, PredictionType.OVERALL_SUCCESS, 0.9
        )

        assert isinstance(success_factors, list)
        # Should identify success factors due to high prediction value
        assert any("High predicted success" in factor for factor in success_factors)

    def test_generate_type_recommendations(self, service, sample_features):
        """Test recommendation generation for specific prediction types"""
        # Test overall success recommendations
        recommendations = service._generate_type_recommendations(
            PredictionType.OVERALL_SUCCESS, 0.9, sample_features
        )
        assert any("High success probability" in rec for rec in recommendations)

        # Test feature completeness recommendations
        recommendations = service._generate_type_recommendations(
            PredictionType.FEATURE_COMPLETENESS, 0.5, sample_features
        )
        assert any("feature gaps" in rec for rec in recommendations)

        # Test performance impact recommendations
        recommendations = service._generate_type_recommendations(
            PredictionType.PERFORMANCE_IMPACT, 0.9, sample_features
        )
        assert any("performance" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_analyze_conversion_viability(self, service):
        """Test conversion viability analysis"""
        # Create mock predictions
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

    def test_get_recommended_action(self, service):
        """Test recommended action generation"""
        assert "proceed" in service._get_recommended_action("high").lower()
        assert "caution" in service._get_recommended_action("medium").lower()
        assert "alternatives" in service._get_recommended_action("low").lower()
        assert "not recommended" in service._get_recommended_action("very_low").lower()

    @pytest.mark.asyncio
    async def test_generate_conversion_recommendations(self, service, sample_features):
        """Test comprehensive conversion recommendations"""
        predictions = {
            "overall_success": PredictionResult(
                PredictionType.OVERALL_SUCCESS, 0.8, 0.9, {}, [], [], [], {}
            )
        }
        viability_analysis = {"viability_level": "high", "viability_score": 0.85}

        recommendations = await service._generate_conversion_recommendations(
            sample_features, predictions, viability_analysis
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

    @pytest.mark.asyncio
    async def test_identify_issues_mitigations(self, service, sample_features):
        """Test issue and mitigation identification"""
        predictions = {
            "overall_success": PredictionResult(
                PredictionType.OVERALL_SUCCESS, 0.4, 0.7, {}, [], [], [], {}
            ),
            "risk_assessment": PredictionResult(
                PredictionType.RISK_ASSESSMENT, 0.8, 0.8, {}, [], [], [], {}
            ),
        }

        issues_mitigations = await service._identify_issues_mitigations(
            sample_features, predictions
        )

        assert "issues" in issues_mitigations
        assert "mitigations" in issues_mitigations
        assert isinstance(issues_mitigations["issues"], list)
        assert isinstance(issues_mitigations["mitigations"], list)

    @pytest.mark.asyncio
    async def test_store_prediction(self, service, sample_features):
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
        assert service.prediction_history[0]["bedrock_concept"] == "BedrockConcept"

    @pytest.mark.asyncio
    async def test_analyze_batch_predictions(self, service):
        """Test batch prediction analysis"""
        batch_results = {
            "conv1": {
                "prediction": {
                    "predictions": {
                        "overall_success": {"predicted_value": 0.8},
                        "risk_assessment": {"predicted_value": 0.2},
                        "feature_completeness": {"predicted_value": 0.9},
                    }
                }
            },
            "conv2": {
                "prediction": {
                    "predictions": {
                        "overall_success": {"predicted_value": 0.6},
                        "risk_assessment": {"predicted_value": 0.4},
                        "feature_completeness": {"predicted_value": 0.7},
                    }
                }
            },
        }

        analysis = await service._analyze_batch_predictions(batch_results)

        assert "total_conversions" in analysis
        assert "average_success_probability" in analysis
        assert analysis["total_conversions"] == 2
        assert 0.0 <= analysis["average_success_probability"] <= 1.0

    @pytest.mark.asyncio
    async def test_rank_conversions_by_success(self, service):
        """Test conversion ranking by success probability"""
        batch_results = {
            "conv1": {
                "input": {"java_concept": "Concept1"},
                "success_probability": 0.9,
            },
            "conv2": {
                "input": {"java_concept": "Concept2"},
                "success_probability": 0.7,
            },
            "conv3": {
                "input": {"java_concept": "Concept3"},
                "success_probability": 0.8,
            },
        }

        rankings = await service._rank_conversions_by_success(batch_results)

        assert len(rankings) == 3
        assert rankings[0]["success_probability"] == 0.9  # Highest first
        assert rankings[0]["rank"] == 1
        assert rankings[1]["rank"] == 2
        assert rankings[2]["rank"] == 3

    @pytest.mark.asyncio
    async def test_identify_batch_patterns(self, service):
        """Test batch pattern identification"""
        batch_results = {
            "conv1": {
                "input": {"pattern_type": "entity_conversion"},
                "success_probability": 0.9,
            },
            "conv2": {
                "input": {"pattern_type": "entity_conversion"},
                "success_probability": 0.8,
            },
            "conv3": {
                "input": {"pattern_type": "block_conversion"},
                "success_probability": 0.6,
            },
        }

        patterns = await service._identify_batch_patterns(batch_results)

        assert "pattern_type_distribution" in patterns
        assert "average_success_by_pattern" in patterns
        assert "most_common_pattern" in patterns
        assert "best_performing_pattern" in patterns
        assert patterns["most_common_pattern"] == "entity_conversion"

    @pytest.mark.asyncio
    async def test_update_model_metrics(self, service):
        """Test model metrics update"""
        service.model_metrics = {
            "overall_success": {"metrics": {"accuracy": 0.8}},
            "feature_completeness": {"metrics": {"mse": 0.1}},
        }

        accuracy_scores = {"overall_success": 0.9, "feature_completeness": 0.8}

        improvements = await service._update_model_metrics(accuracy_scores)

        assert isinstance(improvements, dict)
        assert "overall_success" in improvements
        assert "feature_completeness" in improvements

    @pytest.mark.asyncio
    async def test_create_training_example(self, service):
        """Test training example creation"""
        stored_prediction = {
            "java_concept": "JavaConcept",
            "bedrock_concept": "BedrockConcept",
            "context_data": {
                "pattern_type": "entity_conversion",
                "minecraft_version": "1.20.1",
            },
        }

        actual_result = {
            "overall_success": 1,
            "feature_completeness": 0.9,
            "performance_impact": 0.8,
        }

        feedback_data = {"user_rating": 5, "comments": "Good conversion"}

        training_example = await service._create_training_example(
            stored_prediction, actual_result, feedback_data
        )

        assert training_example is not None
        assert training_example["java_concept"] == "JavaConcept"
        assert training_example["bedrock_concept"] == "BedrockConcept"
        assert training_example["overall_success"] == 1
        assert training_example["feedback_data"] == feedback_data

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

        # Empty scores - the method actually defaults to the "low accuracy" path
        recommendation = asyncio.run(service._get_model_update_recommendation({}))
        assert "need improvement" in recommendation.lower()

    # Test edge cases and error handling
    @pytest.mark.asyncio
    async def test_predict_conversion_success_with_context(
        self, service, sample_features
    ):
        """Test prediction with additional context data"""
        service.is_trained = True

        with patch.object(
            service, "_extract_conversion_features", return_value=sample_features
        ):
            with patch.object(
                service,
                "_prepare_feature_vector",
                return_value=np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
            ):
                with patch.object(service, "_make_prediction") as mock_predict:
                    mock_predict.return_value = PredictionResult(
                        PredictionType.OVERALL_SUCCESS, 0.8, 0.9, {}, [], [], [], {}
                    )

                    context_data = {
                        "user_preferences": {"quality": "high"},
                        "deadline": "urgent",
                    }
                    result = await service.predict_conversion_success(
                        "TestConcept",
                        "TargetConcept",
                        "entity_conversion",
                        "1.20.1",
                        context_data,
                    )

                    assert result["success"] is True
                    assert result["java_concept"] == "TestConcept"
                    assert result["bedrock_concept"] == "TargetConcept"

    @pytest.mark.asyncio
    async def test_make_prediction_exception(self, service, sample_features):
        """Test prediction with exception"""
        feature_vector = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        prediction = await service._make_prediction(
            PredictionType.OVERALL_SUCCESS, feature_vector, sample_features
        )

        assert prediction.prediction_type == PredictionType.OVERALL_SUCCESS
        assert prediction.predicted_value == 0.5  # Default fallback value
        assert prediction.confidence == 0.0
        assert "Prediction error" in prediction.risk_factors[0]

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
