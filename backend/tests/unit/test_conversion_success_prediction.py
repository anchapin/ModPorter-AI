"""
Comprehensive tests for Conversion Success Prediction Service
Tests ML models, feature engineering, and prediction pipelines
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.conversion_success_prediction import (
    ConversionSuccessPredictionService,
    PredictionType,
    ConversionFeatures,
    PredictionResult
)


class TestConversionSuccessPredictionService:
    """Test suite for ConversionSuccessPredictionService"""

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return ConversionSuccessPredictionService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.fixture
    def sample_features(self):
        """Create sample conversion features for testing"""
        return ConversionFeatures(
            java_concept="java_block",
            bedrock_concept="bedrock_block",
            pattern_type="direct_mapping",
            minecraft_version="1.20.0",
            node_type="block",
            platform="java_edition",
            description_length=150,
            expert_validated=True,
            community_rating=4.5,
            usage_count=1250,
            relationship_count=8,
            success_history=[0.8, 0.9, 0.85, 0.95],
            feature_count=5,
            complexity_score=3.2,
            version_compatibility=0.9,
            cross_platform_difficulty=2.1
        )

    @pytest.fixture
    def sample_training_data(self):
        """Create sample training data for model testing"""
        return [
            {
                "java_concept": "java_block",
                "bedrock_concept": "bedrock_block",
                "pattern_type": "direct_mapping",
                "minecraft_version": "1.20.0",
                "node_type": "block",
                "platform": "java_edition",
                "description_length": 150,
                "expert_validated": True,
                "community_rating": 4.5,
                "usage_count": 1250,
                "relationship_count": 8,
                "success_history": [0.8, 0.9, 0.85],
                "feature_count": 5,
                "complexity_score": 3.2,
                "version_compatibility": 0.9,
                "cross_platform_difficulty": 2.1,
                "overall_success": 1,
                "feature_completeness": 0.85,
                "performance_impact": 0.3,
                "compatibility_score": 0.92,
                "risk_assessment": 0,
                "conversion_time": 45.5,
                "resource_usage": 0.4
            },
            {
                "java_concept": "java_entity",
                "bedrock_concept": "bedrock_entity",
                "pattern_type": "complex_transformation",
                "minecraft_version": "1.19.4",
                "node_type": "entity",
                "platform": "java_edition",
                "description_length": 280,
                "expert_validated": False,
                "community_rating": 3.2,
                "usage_count": 450,
                "relationship_count": 15,
                "success_history": [0.4, 0.5, 0.3],
                "feature_count": 12,
                "complexity_score": 7.8,
                "version_compatibility": 0.6,
                "cross_platform_difficulty": 8.2,
                "overall_success": 0,
                "feature_completeness": 0.45,
                "performance_impact": 0.7,
                "compatibility_score": 0.58,
                "risk_assessment": 1,
                "conversion_time": 120.3,
                "resource_usage": 0.85
            }
        ]

    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service.db is None
        assert not service.is_trained
        assert len(service.models) == 7
        assert "feature_scaler" in service.preprocessors
        assert service.feature_names == []
        assert service.training_data == []
        assert service.prediction_history == []

    def test_prediction_type_enum(self):
        """Test PredictionType enum values"""
        assert PredictionType.OVERALL_SUCCESS.value == "overall_success"
        assert PredictionType.FEATURE_COMPLETENESS.value == "feature_completeness"
        assert PredictionType.PERFORMANCE_IMPACT.value == "performance_impact"
        assert PredictionType.COMPATIBILITY_SCORE.value == "compatibility_score"
        assert PredictionType.RISK_ASSESSMENT.value == "risk_assessment"
        assert PredictionType.CONVERSION_TIME.value == "conversion_time"
        assert PredictionType.RESOURCE_USAGE.value == "resource_usage"

    def test_conversion_features_dataclass(self, sample_features):
        """Test ConversionFeatures dataclass"""
        assert sample_features.java_concept == "java_block"
        assert sample_features.bedrock_concept == "bedrock_block"
        assert sample_features.expert_validated is True
        assert sample_features.community_rating == 4.5
        assert len(sample_features.success_history) == 4

    def test_prediction_result_dataclass(self):
        """Test PredictionResult dataclass"""
        result = PredictionResult(
            prediction_type=PredictionType.OVERALL_SUCCESS,
            predicted_value=0.85,
            confidence=0.92,
            feature_importance={"complexity_score": 0.3, "expert_validated": 0.25},
            risk_factors=["high_complexity"],
            success_factors=["expert_validated", "high_usage"],
            recommendations=["increase_testing", "add_validation"],
            prediction_metadata={"model_version": "1.0", "timestamp": "2024-01-01"}
        )

        assert result.prediction_type == PredictionType.OVERALL_SUCCESS
        assert result.predicted_value == 0.85
        assert result.confidence == 0.92
        assert len(result.feature_importance) == 2
        assert len(result.risk_factors) == 1
        assert len(result.success_factors) == 2
        assert len(result.recommendations) == 2

    @pytest.mark.asyncio
    async def test_train_models_insufficient_data(self, service, mock_db):
        """Test model training with insufficient training data"""
        with patch.object(service, '_collect_training_data', return_value=[]):
            result = await service.train_models(mock_db)

            assert result["success"] is False
            assert "Insufficient training data" in result["error"]
            assert result["available_samples"] == 0

    @pytest.mark.asyncio
    async def test_train_models_already_trained(self, service, mock_db, sample_training_data):
        """Test model training when models are already trained"""
        service.is_trained = True
        service.model_metrics = {"accuracy": 0.85}

        with patch.object(service, '_collect_training_data', return_value=sample_training_data):
            result = await service.train_models(mock_db, force_retrain=False)

            assert result["success"] is True
            assert "Models already trained" in result["message"]
            assert result["metrics"]["accuracy"] == 0.85

    @pytest.mark.asyncio
    async def test_train_models_force_retrain(self, service, mock_db, sample_training_data):
        """Test forced model retraining"""
        service.is_trained = True
        service.model_metrics = {"old_accuracy": 0.75}

        with patch.object(service, '_collect_training_data', return_value=sample_training_data), \
             patch.object(service, '_prepare_training_data') as mock_prepare, \
             patch.object(service, '_train_model', return_value={"accuracy": 0.88}) as mock_train:

            # Mock the prepare training data to return proper features and targets
            features = [
                {
                    "description_length": 150,
                    "expert_validated": 1,
                    "community_rating": 4.5,
                    "usage_count": 1250,
                    "relationship_count": 8,
                    "feature_count": 5,
                    "complexity_score": 3.2,
                    "version_compatibility": 0.9,
                    "cross_platform_difficulty": 2.1
                }
            ]
            targets = {
                "overall_success": np.array([1, 0]),
                "feature_completeness": np.array([0.85, 0.45])
            }
            mock_prepare.return_value = (features, targets)

            result = await service.train_models(mock_db, force_retrain=True)

            assert result["success"] is True
            assert service.is_trained is True
            assert len(service.feature_names) > 0
            mock_train.assert_called()

    @pytest.mark.asyncio
    async def test_predict_conversion_success_not_trained(self, service, sample_features):
        """Test prediction when models are not trained"""
        service.is_trained = False

        with pytest.raises(Exception, match="Models must be trained before making predictions"):
            await service.predict_conversion_success(
                conversion_features=sample_features,
                prediction_types=[PredictionType.OVERALL_SUCCESS]
            )

    @pytest.mark.asyncio
    async def test_predict_conversion_success_trained(self, service, mock_db, sample_features, sample_training_data):
        """Test successful conversion prediction"""
        # Train the service first
        with patch.object(service, '_collect_training_data', return_value=sample_training_data), \
             patch.object(service, '_prepare_training_data') as mock_prepare:

            # Mock training data preparation
            features = [
                {
                    "description_length": 150,
                    "expert_validated": 1,
                    "community_rating": 4.5,
                    "usage_count": 1250,
                    "relationship_count": 8,
                    "feature_count": 5,
                    "complexity_score": 3.2,
                    "version_compatibility": 0.9,
                    "cross_platform_difficulty": 2.1
                },
                {
                    "description_length": 280,
                    "expert_validated": 0,
                    "community_rating": 3.2,
                    "usage_count": 450,
                    "relationship_count": 15,
                    "feature_count": 12,
                    "complexity_score": 7.8,
                    "version_compatibility": 0.6,
                    "cross_platform_difficulty": 8.2
                }
            ]
            targets = {
                "overall_success": np.array([1, 0]),
                "feature_completeness": np.array([0.85, 0.45])
            }
            mock_prepare.return_value = (features, targets)

            # Train models
            train_result = await service.train_models(mock_db, force_retrain=True)
            assert train_result["success"] is True

        # Test prediction
        results = await service.predict_conversion_success(
            conversion_features=sample_features,
            prediction_types=[PredictionType.OVERALL_SUCCESS]
        )

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, PredictionResult)
        assert result.prediction_type == PredictionType.OVERALL_SUCCESS
        assert 0 <= result.predicted_value <= 1
        assert 0 <= result.confidence <= 1
        assert isinstance(result.feature_importance, dict)
        assert isinstance(result.risk_factors, list)
        assert isinstance(result.success_factors, list)
        assert isinstance(result.recommendations, list)

    @pytest.mark.asyncio
    async def test_predict_multiple_types(self, service, mock_db, sample_features, sample_training_data):
        """Test predicting multiple prediction types simultaneously"""
        # Train the service first
        with patch.object(service, '_collect_training_data', return_value=sample_training_data), \
             patch.object(service, '_prepare_training_data') as mock_prepare:

            features = [
                {
                    "description_length": 150,
                    "expert_validated": 1,
                    "community_rating": 4.5,
                    "usage_count": 1250,
                    "relationship_count": 8,
                    "feature_count": 5,
                    "complexity_score": 3.2,
                    "version_compatibility": 0.9,
                    "cross_platform_difficulty": 2.1
                }
            ]
            targets = {
                "overall_success": np.array([1]),
                "feature_completeness": np.array([0.85]),
                "performance_impact": np.array([0.3])
            }
            mock_prepare.return_value = (features, targets)

            train_result = await service.train_models(mock_db, force_retrain=True)
            assert train_result["success"] is True

        # Test multiple predictions
        results = await service.predict_conversion_success(
            conversion_features=sample_features,
            prediction_types=[
                PredictionType.OVERALL_SUCCESS,
                PredictionType.FEATURE_COMPLETENESS,
                PredictionType.PERFORMANCE_IMPACT
            ]
        )

        assert len(results) == 3
        prediction_types = [r.prediction_type for r in results]
        assert PredictionType.OVERALL_SUCCESS in prediction_types
        assert PredictionType.FEATURE_COMPLETENESS in prediction_types
        assert PredictionType.PERFORMANCE_IMPACT in prediction_types

    def test_feature_engineering(self, service, sample_features):
        """Test feature engineering from ConversionFeatures to model input"""
        # Test converting features to dictionary
        feature_dict = service._features_to_dict(sample_features)

        assert isinstance(feature_dict, dict)
        assert feature_dict["java_concept"] == "java_block"
        assert feature_dict["bedrock_concept"] == "bedrock_block"
        assert feature_dict["description_length"] == 150
        assert feature_dict["expert_validated"] == 1  # Converted boolean to int
        assert feature_dict["community_rating"] == 4.5
        assert feature_dict["usage_count"] == 1250

    def test_feature_preprocessing(self, service):
        """Test feature preprocessing and scaling"""
        # Create sample features
        features = [
            {
                "description_length": 150,
                "expert_validated": 1,
                "community_rating": 4.5,
                "usage_count": 1250,
                "complexity_score": 3.2,
                "version_compatibility": 0.9
            },
            {
                "description_length": 280,
                "expert_validated": 0,
                "community_rating": 3.2,
                "usage_count": 450,
                "complexity_score": 7.8,
                "version_compatibility": 0.6
            }
        ]

        # Test preprocessing
        processed_features = service._preprocess_features(features)

        assert isinstance(processed_features, np.ndarray)
        assert processed_features.shape == (2, 6)  # 2 samples, 6 features
        assert np.allclose(processed_features.mean(axis=0), 0, atol=1e-10)  # Mean centered

    def test_model_evaluation_metrics(self, service):
        """Test model evaluation metrics calculation"""
        y_true = np.array([1, 0, 1, 1, 0])
        y_pred = np.array([1, 0, 1, 0, 0])
        y_scores = np.array([0.9, 0.1, 0.8, 0.4, 0.2])

        metrics = service._calculate_model_metrics(y_true, y_pred, y_scores, is_classification=True)

        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1_score"] <= 1

    def test_model_evaluation_regression(self, service):
        """Test regression model evaluation metrics"""
        y_true = np.array([0.85, 0.45, 0.92, 0.38])
        y_pred = np.array([0.82, 0.48, 0.90, 0.40])

        metrics = service._calculate_model_metrics(y_true, y_pred, None, is_classification=False)

        assert "mse" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert "r2_score" in metrics
        assert metrics["mse"] >= 0
        assert metrics["rmse"] >= 0
        assert metrics["mae"] >= 0
        assert -1 <= metrics["r2_score"] <= 1

    def test_prediction_confidence_calculation(self, service):
        """Test prediction confidence calculation"""
        # Test high confidence prediction
        confidence_high = service._calculate_prediction_confidence(
            predicted_value=0.85,
            model_uncertainty=0.05,
            feature_quality=0.9
        )
        assert confidence_high > 0.8

        # Test low confidence prediction
        confidence_low = service._calculate_prediction_confidence(
            predicted_value=0.55,
            model_uncertainty=0.25,
            feature_quality=0.6
        )
        assert confidence_low < 0.7

    def test_risk_factor_identification(self, service, sample_features):
        """Test risk factor identification from features"""
        # High complexity features should trigger risk factors
        sample_features.complexity_score = 9.5
        sample_features.expert_validated = False
        sample_features.community_rating = 2.1

        risk_factors = service._identify_risk_factors(sample_features)

        assert "high_complexity" in risk_factors
        assert "not_expert_validated" in risk_factors
        assert "low_community_rating" in risk_factors

    def test_success_factor_identification(self, service, sample_features):
        """Test success factor identification from features"""
        # High quality features should trigger success factors
        sample_features.expert_validated = True
        sample_features.community_rating = 4.8
        sample_features.usage_count = 5000
        sample_features.version_compatibility = 0.95

        success_factors = service._identify_success_factors(sample_features)

        assert "expert_validated" in success_factors
        assert "high_community_rating" in success_factors
        assert "high_usage_count" in success_factors
        assert "excellent_version_compatibility" in success_factors

    def test_recommendation_generation(self, service, sample_features):
        """Test recommendation generation based on features and prediction"""
        # Mock prediction results
        risk_factors = ["high_complexity", "not_expert_validated"]
        success_factors = ["high_usage_count"]
        predicted_value = 0.65  # Medium success probability

        recommendations = service._generate_recommendations(
            features=sample_features,
            risk_factors=risk_factors,
            success_factors=success_factors,
            predicted_value=predicted_value
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # Should recommend addressing risk factors
        assert any("expert" in rec.lower() for rec in recommendations)
        # Should recommend leveraging success factors
        assert any("usage" in rec.lower() or "community" in rec.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_batch_prediction(self, service, mock_db, sample_training_data):
        """Test batch prediction for multiple conversion features"""
        # Train the service first
        with patch.object(service, '_collect_training_data', return_value=sample_training_data), \
             patch.object(service, '_prepare_training_data') as mock_prepare:

            features = [
                {
                    "description_length": 150,
                    "expert_validated": 1,
                    "community_rating": 4.5,
                    "usage_count": 1250,
                    "relationship_count": 8,
                    "feature_count": 5,
                    "complexity_score": 3.2,
                    "version_compatibility": 0.9,
                    "cross_platform_difficulty": 2.1
                }
            ]
            targets = {"overall_success": np.array([1])}
            mock_prepare.return_value = (features, targets)

            train_result = await service.train_models(mock_db, force_retrain=True)
            assert train_result["success"] is True

        # Create multiple features for batch prediction
        features_batch = [
            sample_features,
            ConversionFeatures(
                java_concept="java_entity",
                bedrock_concept="bedrock_entity",
                pattern_type="complex_transformation",
                minecraft_version="1.19.4",
                node_type="entity",
                platform="java_edition",
                description_length=280,
                expert_validated=False,
                community_rating=3.2,
                usage_count=450,
                relationship_count=15,
                success_history=[0.4, 0.5],
                feature_count=12,
                complexity_score=7.8,
                version_compatibility=0.6,
                cross_platform_difficulty=8.2
            )
        ]

        # Test batch prediction
        batch_results = await service.batch_predict_conversion_success(
            features_list=features_batch,
            prediction_types=[PredictionType.OVERALL_SUCCESS]
        )

        assert len(batch_results) == 2
        assert all(isinstance(results, list) for results in batch_results)
        assert all(len(results) == 1 for results in batch_results)

    def test_model_persistence(self, service):
        """Test model saving and loading"""
        # Mock model training
        service.is_trained = True
        service.model_metrics = {"accuracy": 0.85}
        service.feature_names = ["description_length", "expert_validated", "community_rating"]

        # Test model serialization
        model_data = service._serialize_models()

        assert "models" in model_data
        assert "preprocessors" in model_data
        assert "metadata" in model_data
        assert model_data["metadata"]["is_trained"] is True
        assert model_data["metadata"]["feature_count"] == 3

    def test_error_handling_invalid_features(self, service):
        """Test error handling for invalid features"""
        invalid_features = None

        with pytest.raises(ValueError, match="Invalid conversion features provided"):
            service._validate_features(invalid_features)

    def test_error_handling_invalid_prediction_types(self, service, sample_features):
        """Test error handling for invalid prediction types"""
        service.is_trained = True

        with pytest.raises(ValueError, match="Invalid prediction types provided"):
            # Using async function with sync test for demonstration
            import asyncio
            asyncio.run(service.predict_conversion_success(
                conversion_features=sample_features,
                prediction_types=[]  # Empty list should raise error
            ))

    def test_edge_case_minimal_features(self, service):
        """Test handling of minimal feature sets"""
        minimal_features = ConversionFeatures(
            java_concept="test",
            bedrock_concept="test",
            pattern_type="direct",
            minecraft_version="1.20.0",
            node_type="test",
            platform="java",
            description_length=10,
            expert_validated=False,
            community_rating=0.0,
            usage_count=0,
            relationship_count=0,
            success_history=[],
            feature_count=1,
            complexity_score=0.0,
            version_compatibility=0.0,
            cross_platform_difficulty=0.0
        )

        feature_dict = service._features_to_dict(minimal_features)
        assert feature_dict["description_length"] == 10
        assert feature_dict["expert_validated"] == 0
        assert feature_dict["community_rating"] == 0.0

    def test_edge_case_maximal_features(self, service):
        """Test handling of maximal feature values"""
        maximal_features = ConversionFeatures(
            java_concept="complex_java_system",
            bedrock_concept="complex_bedrock_system",
            pattern_type="complex_transformation",
            minecraft_version="1.20.0",
            node_type="complex_system",
            platform="java_edition",
            description_length=10000,
            expert_validated=True,
            community_rating=5.0,
            usage_count=1000000,
            relationship_count=1000,
            success_history=[0.9] * 100,
            feature_count=500,
            complexity_score=10.0,
            version_compatibility=1.0,
            cross_platform_difficulty=10.0
        )

        feature_dict = service._features_to_dict(maximal_features)
        assert feature_dict["description_length"] == 10000
        assert feature_dict["expert_validated"] == 1
        assert feature_dict["community_rating"] == 5.0
        assert feature_dict["usage_count"] == 1000000