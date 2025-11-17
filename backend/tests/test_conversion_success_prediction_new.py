"""
Comprehensive tests for conversion_success_prediction.py service
Focused on ML-based conversion success prediction for 80% coverage target
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.conversion_success_prediction import (
    ConversionSuccessPredictionService, PredictionType, ConversionFeatures, PredictionResult
)
from db.knowledge_graph_crud import KnowledgeNodeCRUD, KnowledgeRelationshipCRUD, ConversionPatternCRUD
from db.models import KnowledgeNode
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    """Mock database session"""
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def service():
    """Create service instance with mocked dependencies"""
    return ConversionSuccessPredictionService()

@pytest.fixture
def sample_features():
    """Sample conversion features for testing"""
    return ConversionFeatures(
        java_concept="Block",
        bedrock_concept="block_component", 
        pattern_type="direct_mapping",
        minecraft_version="1.20.0",
        node_type="entity",
        platform="java_edition",
        description_length=50,
        expert_validated=True,
        community_rating=4.2,
        usage_count=15,
        relationship_count=8,
        success_history=[0.9, 0.85, 0.95],
        feature_count=5,
        complexity_score=0.3,
        version_compatibility=0.8,
        cross_platform_difficulty=0.4
    )

@pytest.fixture
def sample_knowledge_nodes():
    """Sample knowledge nodes for training data"""
    return [
        KnowledgeNode(
            id="node1",
            name="Block",
            node_type="java_concept",
            platform="java",
            minecraft_version="1.20.0",
            properties={"type": "solid", "light_level": 0}
        ),
        KnowledgeNode(
            id="node2",
            name="block_component",
            node_type="bedrock_concept",
            platform="bedrock",
            minecraft_version="1.20.0",
            properties={"component_type": "minecraft:block", "light_emission": 0.0}
        )
    ]


class TestPredictionType:
    """Test PredictionType enum"""
    
    def test_prediction_type_values(self):
        """Test all prediction type enum values"""
        assert PredictionType.OVERALL_SUCCESS.value == "overall_success"
        assert PredictionType.FEATURE_COMPLETENESS.value == "feature_completeness"
        assert PredictionType.PERFORMANCE_IMPACT.value == "performance_impact"
        assert PredictionType.COMPATIBILITY_SCORE.value == "compatibility_score"
        assert PredictionType.RISK_ASSESSMENT.value == "risk_assessment"
        assert PredictionType.CONVERSION_TIME.value == "conversion_time"
        assert PredictionType.RESOURCE_USAGE.value == "resource_usage"


class TestConversionFeatures:
    """Test ConversionFeatures dataclass"""
    
    def test_conversion_features_creation(self, sample_features):
        """Test conversion features creation"""
        assert sample_features.java_concept == "Block"
        assert sample_features.bedrock_concept == "block_component"
        assert sample_features.pattern_type == "direct_mapping"
        assert sample_features.minecraft_version == "1.20.0"
        assert sample_features.node_type == "entity"
        assert sample_features.platform == "java_edition"
    
    def test_conversion_features_equality(self, sample_features):
        """Test conversion features equality"""
        same_features = ConversionFeatures(
            java_concept="Block",
            bedrock_concept="block_component",
            pattern_type="direct_mapping", 
            minecraft_version="1.20.0",
            node_type="entity",
            platform="java_edition"
        )
        assert sample_features == same_features
    
    def test_conversion_features_inequality(self, sample_features):
        """Test conversion features inequality"""
        different_features = ConversionFeatures(
            java_concept="Entity",  # Different concept
            bedrock_concept="block_component",
            pattern_type="direct_mapping",
            minecraft_version="1.20.0", 
            node_type="entity",
            platform="java_edition"
        )
        assert sample_features != different_features


class TestPredictionResult:
    """Test PredictionResult dataclass"""
    
    def test_prediction_result_creation(self):
        """Test prediction result creation"""
        result = PredictionResult(
            prediction_type=PredictionType.OVERALL_SUCCESS,
            predicted_value=1.0,
            confidence=0.85,
            feature_importance={"pattern_type": 0.3, "platform": 0.2, "version": 0.5},
            risk_factors=["complex_conversion"],
            success_factors=["direct_mapping"],
            recommendations=["test_thoroughly"],
            prediction_metadata={"model_version": "1.0.0", "features_used": ["pattern_type", "platform", "version"]}
        )
        
        assert result.prediction_type == PredictionType.OVERALL_SUCCESS
        assert result.predicted_value == 1.0
        assert result.confidence == 0.85
        assert "pattern_type" in result.feature_importance
        assert "complex_conversion" in result.risk_factors
        assert "direct_mapping" in result.success_factors
        assert "test_thoroughly" in result.recommendations
        assert result.prediction_metadata["model_version"] == "1.0.0"
    
    def test_prediction_result_with_metadata(self):
        """Test prediction result with metadata"""
        metadata = {"training_samples": 1000, "accuracy": 0.92}
        result = PredictionResult(
            prediction_type=PredictionType.COMPATIBILITY_SCORE,
            predicted_value=0.65,
            confidence=0.78,
            feature_importance={"concept_similarity": 1.0},
            risk_factors=[],
            success_factors=["high_similarity"],
            recommendations=["proceed_with_conversion"],
            prediction_metadata=metadata
        )
        
        assert result.prediction_metadata == metadata
        assert "training_samples" in result.prediction_metadata


class TestConversionSuccessPredictionService:
    """Test main service class"""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initialization"""
        assert service.is_trained is False
        assert service.models is not None
        assert service.preprocessors is not None
        assert len(service.models) == 7  # All prediction types
    
    @pytest.mark.asyncio
    async def test_train_models_success(self, service, sample_knowledge_nodes, mock_db):
        """Test successful model training"""
        # Mock CRUD operations
        with patch('src.services.conversion_success_prediction.KnowledgeNodeCRUD') as mock_crud:
            mock_crud.return_value.get_nodes_by_platform.return_value = sample_knowledge_nodes
            
            # Mock pattern CRUD
            with patch('src.services.conversion_success_prediction.ConversionPatternCRUD') as mock_pattern_crud:
                mock_pattern_crud.return_value.get_all_patterns.return_value = []
                
                result = await service.train_models(db=mock_db, force_retrain=True)
                
                assert result["success"] is True
                assert "metrics" in result
                assert service.is_trained is True
    
    @pytest.mark.asyncio
    async def test_train_models_with_insufficient_data(self, service):
        """Test model training with insufficient data"""
        with patch.object(service.knowledge_crud, 'get_nodes_by_platform') as mock_get_nodes:
            mock_get_nodes.return_value = []  # No training data
            
            result = await service.train_models(
                prediction_types=[PredictionType.OVERALL_SUCCESS],
                training_data_limit=100
            )
            
            assert result["success"] is True  # Still succeeds but with warning
            assert "warning" in result
    
    @pytest.mark.asyncio
    async def test_predict_conversion_success(self, service, sample_features):
        """Test conversion success prediction"""
        # Setup mock model
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1.0])
        mock_model.predict_proba.return_value = np.array([0.2, 0.8])
        
        with patch.object(service, '_get_model') as mock_get_model:
            mock_get_model.return_value = mock_model
            
            result = await service.predict_conversion_success(
                features=sample_features,
                prediction_type=PredictionType.OVERALL_SUCCESS
            )
            
            assert isinstance(result, PredictionResult)
            assert result.prediction_type == PredictionType.OVERALL_SUCCESS
            assert 0 <= result.confidence <= 1
            assert isinstance(result.value, (int, float))
    
    @pytest.mark.asyncio
    async def test_predict_conversion_success_no_model(self, service, sample_features):
        """Test prediction when no model is available"""
        with patch.object(service, '_get_model') as mock_get_model:
            mock_get_model.return_value = None
            
            with pytest.raises(ValueError, match="No trained model available"):
                await service.predict_conversion_success(
                    features=sample_features,
                    prediction_type=PredictionType.OVERALL_SUCCESS
                )
    
    @pytest.mark.asyncio
    async def test_batch_predict_success(self, service):
        """Test batch prediction for multiple features"""
        features_list = [
            ConversionFeatures("Block", "block_component", "direct", "1.20.0", "entity", "java"),
            ConversionFeatures("Entity", "entity_component", "complex", "1.19.0", "entity", "java"),
            ConversionFeatures("Item", "item_component", "direct", "1.20.0", "item", "java")
        ]
        
        # Mock model
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1.0, 0.8, 0.9])
        mock_model.predict_proba.return_value = np.array([[0.2, 0.8], [0.3, 0.7], [0.1, 0.9]])
        
        with patch.object(service, '_get_model') as mock_get_model:
            mock_get_model.return_value = mock_model
            
            results = await service.batch_predict_success(
                features_list=features_list,
                prediction_type=PredictionType.OVERALL_SUCCESS
            )
            
            assert len(results) == 3
            for result in results:
                assert isinstance(result, PredictionResult)
                assert result.prediction_type == PredictionType.OVERALL_SUCCESS
    
    @pytest.mark.asyncio
    async def test_update_models_with_feedback(self, service, sample_features):
        """Test updating models with feedback"""
        feedback_data = [
            {
                "features": sample_features,
                "actual_outcome": 1.0,
                "predicted_outcome": 0.8,
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        # Mock model
        mock_model = Mock()
        
        with patch.object(service, '_get_model') as mock_get_model:
            mock_get_model.return_value = mock_model
            
            result = await service.update_models_with_feedback(
                feedback_data=feedback_data,
                prediction_type=PredictionType.OVERALL_SUCCESS
            )
            
            assert result["success"] is True
            assert "feedback_processed" in result
            assert result["feedback_processed"] == len(feedback_data)
    
    @pytest.mark.asyncio
    async def test_get_prediction_insights(self, service, sample_features):
        """Test getting detailed prediction insights"""
        # Mock model and scaler
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1.0])
        mock_model.predict_proba.return_value = np.array([0.2, 0.8])
        mock_model.feature_importances_ = np.array([0.3, 0.2, 0.5])
        
        mock_scaler = Mock()
        mock_scaler.transform.return_value = np.array([[1.0, 2.0, 3.0]])
        
        with patch.object(service, '_get_model') as mock_get_model, \
             patch.object(service, '_get_scaler') as mock_get_scaler:
            mock_get_model.return_value = mock_model
            mock_get_scaler.return_value = mock_scaler
            
            insights = await service.get_prediction_insights(
                features=sample_features,
                prediction_type=PredictionType.OVERALL_SUCCESS
            )
            
            assert "prediction" in insights
            assert "feature_importance" in insights
            assert "confidence_factors" in insights
            assert "recommendations" in insights


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_invalid_features_handling(self, service):
        """Test handling of invalid features"""
        invalid_features = ConversionFeatures(
            java_concept="",  # Empty concept
            bedrock_concept="block_component",
            pattern_type="direct_mapping",
            minecraft_version="invalid_version",  # Invalid version
            node_type="entity",
            platform="invalid_platform"  # Invalid platform
        )
        
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.5])
        mock_model.predict_proba.return_value = np.array([0.5, 0.5])
        
        with patch.object(service, '_get_model') as mock_get_model:
            mock_get_model.return_value = mock_model
            
            result = await service.predict_conversion_success(
                features=invalid_features,
                prediction_type=PredictionType.OVERALL_SUCCESS
            )
            
            # Should still return a result but with lower confidence
            assert isinstance(result, PredictionResult)
            assert result.confidence < 0.8  # Lower confidence for invalid data
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, service):
        """Test handling of database errors"""
        with patch.object(service.knowledge_crud, 'get_nodes_by_platform') as mock_get_nodes:
            mock_get_nodes.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception):
                await service.train_models(
                    prediction_types=[PredictionType.OVERALL_SUCCESS],
                    training_data_limit=100
                )
    
    def test_feature_vector_creation(self, service):
        """Test conversion of features to numerical vector"""
        features = ConversionFeatures(
            java_concept="Block",
            bedrock_concept="block_component", 
            pattern_type="direct_mapping",
            minecraft_version="1.20.0",
            node_type="entity",
            platform="java_edition"
        )
        
        vector = service._features_to_vector(features)
        
        assert isinstance(vector, np.ndarray)
        assert len(vector) > 0
        assert all(isinstance(x, (int, float)) for x in vector)


class TestPerformance:
    """Test performance-related aspects"""
    
    @pytest.mark.asyncio
    async def test_batch_prediction_performance(self, service):
        """Test batch prediction performance with large dataset"""
        import time
        
        # Create large feature list
        features_list = [
            ConversionFeatures(
                f"Concept{i}", f"BedrockConcept{i}", 
                "direct", "1.20.0", "entity", "java"
            )
            for i in range(100)  # 100 features
        ]
        
        mock_model = Mock()
        mock_model.predict.return_value = np.ones(100)
        mock_model.predict_proba.return_value = np.column_stack([
            np.zeros(100), np.ones(100)
        ])
        
        with patch.object(service, '_get_model') as mock_get_model:
            mock_get_model.return_value = mock_model
            
            start_time = time.time()
            results = await service.batch_predict_success(
                features_list=features_list,
                prediction_type=PredictionType.OVERALL_SUCCESS
            )
            end_time = time.time()
            
            # Performance assertions
            assert len(results) == 100
            assert (end_time - start_time) < 5.0  # Should complete within 5 seconds
    
    @pytest.mark.asyncio
    async def test_concurrent_predictions(self, service):
        """Test concurrent prediction requests"""
        import asyncio
        
        features = ConversionFeatures(
            "Block", "block_component", "direct", 
            "1.20.0", "entity", "java"
        )
        
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1.0])
        mock_model.predict_proba.return_value = np.array([0.2, 0.8])
        
        with patch.object(service, '_get_model') as mock_get_model:
            mock_get_model.return_value = mock_model
            
            # Run multiple predictions concurrently
            tasks = [
                service.predict_conversion_success(
                    features=features,
                    prediction_type=PredictionType.OVERALL_SUCCESS
                )
                for _ in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            assert len(results) == 10
            for result in results:
                assert isinstance(result, PredictionResult)
                assert result.prediction_type == PredictionType.OVERALL_SUCCESS
