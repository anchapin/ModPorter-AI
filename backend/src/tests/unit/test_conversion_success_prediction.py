"""
Tests for conversion_success_prediction.py service.
Focus on covering the main prediction logic and ML model operations.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

# Import the service
from services.conversion_success_prediction import (
    ConversionSuccessPredictionService,
    PredictionType,
    ConversionFeatures,
    PredictionResult
)


class TestConversionFeatures:
    """Test the ConversionFeatures dataclass."""
    
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


class TestPredictionType:
    """Test the PredictionType enum."""
    
    def test_prediction_type_values(self):
        """Test all enum values are present."""
        assert PredictionType.OVERALL_SUCCESS.value == "overall_success"
        assert PredictionType.FEATURE_COMPLETENESS.value == "feature_completeness"
        assert PredictionType.PERFORMANCE_IMPACT.value == "performance_impact"
        assert PredictionType.COMPATIBILITY_SCORE.value == "compatibility_score"
        assert PredictionType.RISK_ASSESSMENT.value == "risk_assessment"
        assert PredictionType.CONVERSION_TIME.value == "conversion_time"
        assert PredictionType.RESOURCE_USAGE.value == "resource_usage"


class TestFeatureExtractor:
    """Test the FeatureExtractor class."""
    
    def test_extract_features_basic(self):
        """Test basic feature extraction."""
        extractor = FeatureExtractor()
        
        features = extractor.extract_features({
            "java_concept": "Entity",
            "bedrock_concept": "Entity Definition",
            "pattern_type": "entity_mapping",
            "minecraft_version": "1.20.1",
            "node_type": "concept",
            "platform": "java"
        })
        
        assert isinstance(features, np.ndarray)
        assert len(features) > 0
        
    def test_extract_features_with_empty_data(self):
        """Test feature extraction with empty data."""
        extractor = FeatureExtractor()
        
        with pytest.raises(ValueError):
            extractor.extract_features({})
            
    def test_extract_features_version_normalization(self):
        """Test version number normalization."""
        extractor = FeatureExtractor()
        
        # Test different version formats
        features_v1 = extractor.extract_features({
            "java_concept": "Entity",
            "bedrock_concept": "Entity Definition",
            "pattern_type": "entity_mapping",
            "minecraft_version": "1.20.1",
            "node_type": "concept",
            "platform": "java"
        })
        
        features_v2 = extractor.extract_features({
            "java_concept": "Entity",
            "bedrock_concept": "Entity Definition",
            "pattern_type": "entity_mapping",
            "minecraft_version": "1.20",
            "node_type": "concept",
            "platform": "java"
        })
        
        # Both should be valid feature arrays
        assert isinstance(features_v1, np.ndarray)
        assert isinstance(features_v2, np.ndarray)


class TestModelManager:
    """Test the ModelManager class."""
    
    def test_model_manager_initialization(self):
        """Test ModelManager initialization."""
        manager = ModelManager()
        
        assert manager.models == {}
        assert manager.scalers == {}
        assert manager.is_trained == {}
        
    def test_train_model_new(self):
        """Test training a new model."""
        manager = ModelManager()
        
        # Mock training data
        X = np.random.rand(100, 10)
        y = np.random.randint(0, 2, 100)
        
        manager.train_model(PredictionType.OVERALL_SUCCESS, X, y)
        
        assert PredictionType.OVERALL_SUCCESS in manager.models
        assert PredictionType.OVERALL_SUCCESS in manager.scalers
        assert manager.is_trained[PredictionType.OVERALL_SUCCESS] == True
        
    def test_train_model_existing(self):
        """Test retraining an existing model."""
        manager = ModelManager()
        
        # Train initial model
        X1 = np.random.rand(100, 10)
        y1 = np.random.randint(0, 2, 100)
        manager.train_model(PredictionType.OVERALL_SUCCESS, X1, y1)
        
        # Retrain with new data
        X2 = np.random.rand(100, 10)
        y2 = np.random.randint(0, 2, 100)
        manager.train_model(PredictionType.OVERALL_SUCCESS, X2, y2)
        
        # Model should still be trained
        assert manager.is_trained[PredictionType.OVERALL_SUCCESS] == True
        
    def test_predict_with_untrained_model(self):
        """Test prediction with untrained model."""
        manager = ModelManager()
        
        with pytest.raises(ValueError):
            manager.predict(PredictionType.OVERALL_SUCCESS, np.array([1, 2, 3]))
            
    def test_predict_success(self):
        """Test successful prediction."""
        manager = ModelManager()
        
        # Train model first
        X = np.random.rand(100, 10)
        y = np.random.randint(0, 2, 100)
        manager.train_model(PredictionType.OVERALL_SUCCESS, X, y)
        
        # Make prediction
        result = manager.predict(PredictionType.OVERALL_SUCCESS, X[0:1])
        
        assert isinstance(result, (float, int))
        assert 0 <= result <= 1 or 0 <= result <= 1  # Probability or class label


class TestConversionSuccessPredictor:
    """Test the main ConversionSuccessPredictor class."""
    
    @pytest.fixture
    def predictor(self):
        """Create a predictor instance with mocked dependencies."""
        with patch('services.conversion_success_prediction.KnowledgeNodeCRUD') as mock_crud:
            predictor = ConversionSuccessPredictor()
            predictor.node_crud = mock_crud
            return predictor
            
    def test_predictor_initialization(self, predictor):
        """Test predictor initialization."""
        assert predictor.model_manager is not None
        assert predictor.feature_extractor is not None
        assert predictor.node_crud is not None
        
    @pytest.mark.asyncio
    async def test_predict_overall_success(self, predictor):
        """Test predicting overall success."""
        # Mock database response
        mock_nodes = [
            MagicMock(id="1", properties={"concept": "Entity"}),
            MagicMock(id="2", properties={"concept": "Block"})
        ]
        predictor.node_crud.get_nodes_by_pattern.return_value = mock_nodes
        
        # Train model with mock data
        X = np.random.rand(50, 10)
        y = np.random.randint(0, 2, 50)
        predictor.model_manager.train_model(PredictionType.OVERALL_SUCCESS, X, y)
        
        result = await predictor.predict_overall_success(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            minecraft_version="1.20.1"
        )
        
        assert isinstance(result, float)
        assert 0 <= result <= 1
        
    @pytest.mark.asyncio
    async def test_predict_feature_completeness(self, predictor):
        """Test predicting feature completeness."""
        # Mock database response
        mock_nodes = [MagicMock(id="1", properties={"feature_count": 5})]
        predictor.node_crud.get_nodes_by_concept.return_value = mock_nodes
        
        # Train model
        X = np.random.rand(50, 10)
        y = np.random.rand(50)
        predictor.model_manager.train_model(PredictionType.FEATURE_COMPLETENESS, X, y)
        
        result = await predictor.predict_feature_completeness(
            java_concept="Entity",
            features=["movement", "rendering"]
        )
        
        assert isinstance(result, float)
        assert 0 <= result <= 1
        
    @pytest.mark.asyncio
    async def test_predict_performance_impact(self, predictor):
        """Test predicting performance impact."""
        # Train model
        X = np.random.rand(50, 10)
        y = np.random.rand(50)
        predictor.model_manager.train_model(PredictionType.PERFORMANCE_IMPACT, X, y)
        
        result = await predictor.predict_performance_impact(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            complexity_score=0.7
        )
        
        assert isinstance(result, float)
        assert 0 <= result <= 1
        
    @pytest.mark.asyncio
    async def test_predict_compatibility_score(self, predictor):
        """Test predicting compatibility score."""
        # Mock database response
        mock_patterns = [MagicMock(id="1", properties={"success_rate": 0.85})]
        predictor.node_crud.get_conversion_patterns.return_value = mock_patterns
        
        # Train model
        X = np.random.rand(50, 10)
        y = np.random.rand(50)
        predictor.model_manager.train_model(PredictionType.COMPATIBILITY_SCORE, X, y)
        
        result = await predictor.predict_compatibility_score(
            java_concept="Entity",
            target_version="1.20.1",
            source_version="1.19.4"
        )
        
        assert isinstance(result, float)
        assert 0 <= result <= 1
        
    @pytest.mark.asyncio
    async def test_predict_risk_assessment(self, predictor):
        """Test predicting risk assessment."""
        # Train model
        X = np.random.rand(50, 10)
        y = np.random.randint(0, 4, 50)  # Risk levels 0-3
        predictor.model_manager.train_model(PredictionType.RISK_ASSESSMENT, X, y)
        
        result = await predictor.predict_risk_assessment(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            complexity_score=0.8
        )
        
        assert isinstance(result, float)
        assert 0 <= result <= 3
        
    @pytest.mark.asyncio
    async def test_predict_conversion_time(self, predictor):
        """Test predicting conversion time."""
        # Train model
        X = np.random.rand(50, 10)
        y = np.random.rand(50) * 3600  # Time in seconds
        predictor.model_manager.train_model(PredictionType.CONVERSION_TIME, X, y)
        
        result = await predictor.predict_conversion_time(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            file_size=1000
        )
        
        assert isinstance(result, float)
        assert result >= 0
        
    @pytest.mark.asyncio
    async def test_predict_resource_usage(self, predictor):
        """Test predicting resource usage."""
        # Train model
        X = np.random.rand(50, 10)
        y = np.random.rand(50)
        predictor.model_manager.train_model(PredictionType.RESOURCE_USAGE, X, y)
        
        result = await predictor.predict_resource_usage(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            complexity_score=0.6
        )
        
        assert isinstance(result, float)
        assert 0 <= result <= 1
        
    @pytest.mark.asyncio
    async def test_batch_prediction(self, predictor):
        """Test batch prediction for multiple conversions."""
        # Mock database responses
        predictor.node_crud.get_nodes_by_pattern.return_value = []
        predictor.node_crud.get_nodes_by_concept.return_value = []
        predictor.node_crud.get_conversion_patterns.return_value = []
        
        # Train models
        X = np.random.rand(50, 10)
        
        y_classification = np.random.randint(0, 2, 50)
        predictor.model_manager.train_model(PredictionType.OVERALL_SUCCESS, X, y_classification)
        
        y_regression = np.random.rand(50)
        predictor.model_manager.train_model(PredictionType.FEATURE_COMPLETENESS, X, y_regression)
        
        conversions = [
            {
                "java_concept": "Entity",
                "bedrock_concept": "Entity Definition",
                "minecraft_version": "1.20.1"
            },
            {
                "java_concept": "Block",
                "bedrock_concept": "Block Definition",
                "minecraft_version": "1.20.1"
            }
        ]
        
        results = await predictor.batch_predict(conversions)
        
        assert len(results) == 2
        for result in results:
            assert isinstance(result, dict)
            assert "overall_success" in result
            assert "feature_completeness" in result
            assert "performance_impact" in result
            
    @pytest.mark.asyncio
    async def test_update_model_with_new_data(self, predictor):
        """Test updating models with new conversion data."""
        # Mock database responses
        mock_nodes = [MagicMock(id="1", properties={"concept": "Entity"})]
        predictor.node_crud.get_nodes_by_pattern.return_value = mock_nodes
        
        # Simulate new conversion data
        conversion_data = [
            {
                "java_concept": "Entity",
                "bedrock_concept": "Entity Definition",
                "success": True,
                "conversion_time": 300,
                "complexity_score": 0.5
            }
        ]
        
        await predictor.update_models(conversion_data)
        
        # Verify models were retrained
        assert predictor.model_manager.is_trained.get(PredictionType.OVERALL_SUCCESS, False)
