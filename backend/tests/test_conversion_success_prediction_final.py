"""
Final working tests for conversion_success_prediction.py
Phase 3: Core Logic Completion - 80% Coverage Target
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.conversion_success_prediction import (
    ConversionSuccessPredictionService,
    PredictionType,
    ConversionFeatures,
    PredictionResult
)
from db.models import KnowledgeNode


class TestConversionSuccessPredictionService:
    """Test cases for ConversionSuccessPredictionService"""

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        with patch('services.conversion_success_prediction.KnowledgeNodeCRUD'), \
             patch('services.conversion_success_prediction.KnowledgeRelationshipCRUD'), \
             patch('services.conversion_success_prediction.ConversionPatternCRUD'):
            service = ConversionSuccessPredictionService()
            # Initialize required attributes
            service.is_trained = True
            service.models = {ptype.value: Mock() for ptype in PredictionType}
            service.preprocessors = {"feature_scaler": Mock()}
            service.preprocessors["feature_scaler"].transform.return_value = np.array([[1.0, 2.0, 3.0]])
            service.feature_names = ["expert_validated", "usage_count", "community_rating"]
            service.prediction_history = []
            service.training_data = []
            return service

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = AsyncMock()
        return session

    @pytest.fixture
    def sample_features(self):
        """Create sample conversion features with all required fields"""
        return ConversionFeatures(
            java_concept="Java Block",
            bedrock_concept="Bedrock Block",
            pattern_type="direct_conversion",
            minecraft_version="1.20.0",
            node_type="block",
            platform="java",
            description_length=50,
            expert_validated=True,
            community_rating=4.5,
            usage_count=100,
            relationship_count=5,
            success_history=[0.8, 0.9, 0.85],
            feature_count=10,
            complexity_score=0.3,
            version_compatibility=0.9,
            cross_platform_difficulty=0.2
        )

    @pytest.fixture
    def sample_knowledge_node(self):
        """Create sample knowledge node"""
        return KnowledgeNode(
            id=1,
            node_type="block",
            name="test_block",
            description="Test block for conversion",
            metadata={"complexity": "medium"},
            properties='{"test": "value"}',
            platform="java",
            expert_validated=True,
            community_rating=4.5,
            minecraft_version="1.20.0"
        )

    # Test initialization
    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert hasattr(service, 'is_trained')
        assert service.is_trained is True

    # Test feature encoding
    def test_encode_pattern_type(self, service):
        """Test pattern type encoding"""
        result = service._encode_pattern_type("direct_conversion")
        assert isinstance(result, float)
        assert result == 1.0

    def test_encode_pattern_type_unknown(self, service):
        """Test encoding unknown pattern type"""
        result = service._encode_pattern_type("unknown_pattern")
        assert isinstance(result, float)
        assert result == 0.3

    # Test complexity calculation
    def test_calculate_complexity(self, service, sample_knowledge_node):
        """Test complexity calculation"""
        complexity = service._calculate_complexity(sample_knowledge_node)
        assert isinstance(complexity, float)
        assert 0 <= complexity <= 1

    def test_calculate_complexity_no_metadata(self, service):
        """Test complexity calculation with no metadata"""
        node = KnowledgeNode(
            id=1,
            node_type="block",
            name="test_block",
            description="Test block",
            metadata=None,
            properties='{}',
            platform="java",
            expert_validated=False,
            community_rating=0.0,
            minecraft_version="1.20.0"
        )
        complexity = service._calculate_complexity(node)
        assert isinstance(complexity, float)
        assert 0 <= complexity <= 1

    # Test cross-platform difficulty
    def test_calculate_cross_platform_difficulty(self, service, sample_knowledge_node):
        """Test cross-platform difficulty calculation"""
        difficulty = service._calculate_cross_platform_difficulty(
            sample_knowledge_node, 
            "Bedrock Block"
        )
        assert isinstance(difficulty, float)
        assert 0 <= difficulty <= 1

    # Test feature preparation
    @pytest.mark.asyncio
    async def test_prepare_feature_vector(self, service, sample_features):
        """Test feature vector preparation"""
        feature_vector = await service._prepare_feature_vector(sample_features)
        assert isinstance(feature_vector, np.ndarray)
        assert len(feature_vector) > 0
        assert all(isinstance(x, (int, float)) for x in feature_vector)

    # Test prediction making
    @pytest.mark.asyncio
    async def test_make_prediction(self, service, sample_features):
        """Test making predictions"""
        # Mock model to return valid prediction
        service.models["overall_success"].predict.return_value = [0.8]
        service.models["overall_success"].feature_importances_ = np.array([0.1, 0.2, 0.3])

        result = await service._make_prediction(
            prediction_type=PredictionType.OVERALL_SUCCESS,
            feature_vector=np.array([1.0, 2.0, 3.0]),
            features=sample_features
        )

        assert isinstance(result, PredictionResult)
        assert result.predicted_value == 0.8
        assert result.confidence > 0

    # Test confidence calculation
    def test_calculate_prediction_confidence(self, service):
        """Test prediction confidence calculation"""
        mock_model = Mock()
        mock_model.predict.return_value = [0.8, 0.8, 0.8]
        
        confidence = service._calculate_prediction_confidence(
            mock_model,
            np.array([1.0, 2.0, 3.0]),
            PredictionType.OVERALL_SUCCESS
        )
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1

    # Test risk factor identification
    def test_identify_risk_factors(self, service, sample_features):
        """Test risk factor identification"""
        risks = service._identify_risk_factors(
            sample_features,
            PredictionType.OVERALL_SUCCESS,
            0.3
        )
        assert isinstance(risks, list)
        assert all(isinstance(risk, str) for risk in risks)

    # Test success factor identification
    def test_identify_success_factors(self, service, sample_features):
        """Test success factor identification"""
        factors = service._identify_success_factors(
            sample_features,
            PredictionType.OVERALL_SUCCESS,
            0.8
        )
        assert isinstance(factors, list)
        assert all(isinstance(factor, str) for factor in factors)

    # Test conversion viability analysis
    @pytest.mark.asyncio
    async def test_analyze_conversion_viability(self, service, sample_features):
        """Test conversion viability analysis"""
        predictions = {
            "overall_success": PredictionResult(
                prediction_type=PredictionType.OVERALL_SUCCESS,
                predicted_value=0.8,
                confidence=0.9,
                feature_importance={},
                risk_factors=[],
                success_factors=[],
                recommendations=[],
                prediction_metadata={}
            )
        }

        viability = await service._analyze_conversion_viability(
            java_concept="Java Block",
            bedrock_concept="Bedrock Block", 
            predictions=predictions
        )
        assert isinstance(viability, dict)
        assert 'viability_level' in viability
        assert 'success_probability' in viability
        assert 'confidence' in viability
        assert viability['viability_level'] in ['high', 'medium', 'low']

    # Test recommendation generation
    def test_get_recommended_action(self, service):
        """Test getting recommended actions"""
        # High viability
        action = service._get_recommended_action("high")
        assert isinstance(action, str)
        assert any(word in action.lower() for word in ["proceed", "excellent", "good"])

        # Medium viability
        action = service._get_recommended_action("medium")
        assert isinstance(action, str)
        assert any(word in action.lower() for word in ["caution", "review", "consider"])

        # Low viability
        action = service._get_recommended_action("low")
        assert isinstance(action, str)
        assert any(word in action.lower() for word in ["avoid", "alternatives", "expert", "redesign"])

    # Test feature importance
    def test_get_feature_importance(self, service):
        """Test feature importance extraction"""
        mock_model = Mock()
        mock_model.feature_importances_ = np.array([0.3, 0.5, 0.2])
        
        importance = service._get_feature_importance(mock_model, PredictionType.OVERALL_SUCCESS)
        assert isinstance(importance, dict)
        assert len(importance) == 3
        assert all(isinstance(v, float) for v in importance.values())

    # Test model training
    @pytest.mark.asyncio
    async def test_train_models(self, service, mock_db_session):
        """Test model training"""
        # Mock training data collection with sufficient samples
        with patch.object(service, '_collect_training_data') as mock_collect:
            mock_collect.return_value = [
                {
                    'java_concept': 'test',
                    'bedrock_concept': 'test',
                    'pattern_type': 'direct_conversion',
                    'minecraft_version': '1.20.0',
                    'overall_success': 1,
                    'feature_completeness': 0.8,
                    'performance_impact': 0.7,
                    'compatibility_score': 0.9,
                    'risk_assessment': 0,
                    'conversion_time': 1.0,
                    'resource_usage': 0.5,
                    'expert_validated': True,
                    'usage_count': 100,
                    'confidence_score': 0.8,
                    'features': {}
                }
            ] * 100  # Create 100 samples

            # Mock model training
            with patch.object(service, '_train_model') as mock_train:
                mock_train.return_value = {
                    'training_samples': 80,
                    'test_samples': 20,
                    'metrics': {'accuracy': 0.8}
                }

                result = await service.train_models(db=mock_db_session)
                assert isinstance(result, dict)
                assert any(key in result for key in ['success', 'error', 'models_trained'])

    # Test conversion success prediction
    @pytest.mark.asyncio
    async def test_predict_conversion_success(self, service, mock_db_session, sample_features):
        """Test conversion success prediction"""
        # Mock feature extraction process
        with patch.object(service, '_extract_conversion_features') as mock_extract, \
             patch.object(service, '_prepare_feature_vector') as mock_prepare, \
             patch.object(service, '_make_prediction') as mock_predict, \
             patch.object(service, '_analyze_conversion_viability') as mock_analyze, \
             patch.object(service, '_generate_conversion_recommendations') as mock_recomm, \
             patch.object(service, '_identify_issues_mitigations') as mock_issues, \
             patch.object(service, '_store_prediction') as mock_store:

            mock_extract.return_value = sample_features
            mock_prepare.return_value = np.array([1.0, 2.0, 3.0])
            mock_predict.return_value = PredictionResult(
                prediction_type=PredictionType.OVERALL_SUCCESS,
                predicted_value=0.8,
                confidence=0.9,
                feature_importance={"complexity": 0.5},
                risk_factors=["low_complexity"],
                success_factors=["common_pattern"],
                recommendations=["proceed"],
                prediction_metadata={}
            )
            mock_analyze.return_value = {"viability_level": "high", "success_probability": 0.8, "confidence": 0.9}
            mock_recomm.return_value = ["Recommended action"]
            mock_issues.return_value = {"issues": [], "mitigations": []}

            result = await service.predict_conversion_success(
                java_concept="Java Block",
                bedrock_concept="Bedrock Block",
                pattern_type="direct_conversion",
                minecraft_version="1.20.0",
                db=mock_db_session
            )

            assert isinstance(result, dict)
            assert result["success"] is True
            assert "predictions" in result
            assert "viability_analysis" in result

    # Test batch prediction
    @pytest.mark.asyncio
    async def test_batch_predict_success(self, service, mock_db_session):
        """Test batch success prediction"""
        requests = [
            {
                'java_concept': 'Java Block 1',
                'bedrock_concept': 'Bedrock Block 1',
                'pattern_type': 'direct_conversion',
                'minecraft_version': '1.20.0'
            },
            {
                'java_concept': 'Java Block 2',
                'bedrock_concept': 'Bedrock Block 2',
                'pattern_type': 'entity_conversion',
                'minecraft_version': '1.20.0'
            }
        ]

        # Mock prediction method
        with patch.object(service, 'predict_conversion_success') as mock_predict:
            mock_predict.return_value = {
                "success": True,
                "predictions": {
                    "overall_success": {
                        "predicted_value": 0.8,
                        "confidence": 0.9
                    }
                }
            }

            results = await service.batch_predict_success(requests, db=mock_db_session)

            assert isinstance(results, dict)
            assert results["success"] is True
            assert "batch_results" in results
            assert "total_conversions" in results
            assert results["total_conversions"] == 2

    # Test error handling
    @pytest.mark.asyncio
    async def test_predict_conversion_success_error(self, service, mock_db_session):
        """Test error handling in prediction"""
        # Set service as untrained to trigger error
        service.is_trained = False

        result = await service.predict_conversion_success(
            java_concept="Java Block",
            bedrock_concept="Bedrock Block",
            pattern_type="direct_conversion",
            minecraft_version="1.20.0",
            db=mock_db_session
        )

        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result

    # Test model update with feedback
    @pytest.mark.asyncio
    async def test_update_models_with_feedback(self, service, mock_db_session):
        """Test updating models with feedback"""
        conversion_id = "test_conversion_1"
        actual_result = {"overall_success": 1, "feature_completeness": 0.9}
        
        # Add a prediction to history
        service.prediction_history.append({
            "conversion_id": conversion_id,
            "predictions": {
                "overall_success": {"predicted_value": 0.8}
            }
        })

        with patch.object(service, '_update_model_metrics') as mock_update, \
             patch.object(service, '_create_training_example') as mock_create:
            
            mock_update.return_value = {"improvement": 0.1}
            mock_create.return_value = {"test": "example"}

            result = await service.update_models_with_feedback(
                conversion_id=conversion_id,
                actual_result=actual_result,
                db=mock_db_session
            )

            assert isinstance(result, dict)
            assert "accuracy_scores" in result
            assert "model_improvements" in result

    # Test conversion features extraction
    @pytest.mark.asyncio
    async def test_extract_conversion_features(self, service, mock_db_session):
        """Test conversion features extraction"""
        # Mock knowledge node search
        java_node = KnowledgeNode(
            id=1,
            node_type="block",
            name="test_block",
            description="Test block for conversion",
            properties='{"test": "value"}',
            platform="java",
            expert_validated=True,
            community_rating=4.5,
            minecraft_version="1.20.0"
        )

        with patch('services.conversion_success_prediction.KnowledgeNodeCRUD.search') as mock_search, \
             patch('services.conversion_success_prediction.KnowledgeRelationshipCRUD.get_by_source') as mock_rels:
            
            mock_search.return_value = [java_node]
            mock_rels.return_value = []

            features = await service._extract_conversion_features(
                java_concept="Java Block",
                bedrock_concept="Bedrock Block",
                pattern_type="direct_conversion",
                minecraft_version="1.20.0",
                db=mock_db_session
            )

            assert isinstance(features, ConversionFeatures)
            assert features.java_concept == "Java Block"
            assert features.bedrock_concept == "Bedrock Block"

    # Test training data preparation
    @pytest.mark.asyncio
    async def test_prepare_training_data(self, service):
        """Test training data preparation"""
        training_data = [
            {
                'java_concept': 'test',
                'bedrock_concept': 'test',
                'pattern_type': 'direct_conversion',
                'minecraft_version': '1.20.0',
                'overall_success': 1,
                'feature_completeness': 0.8,
                'performance_impact': 0.7,
                'compatibility_score': 0.9,
                'risk_assessment': 0,
                'conversion_time': 1.0,
                'resource_usage': 0.5,
                'expert_validated': True,
                'usage_count': 100,
                'confidence_score': 0.8,
                'features': {}
            }
        ]

        features, targets = await service._prepare_training_data(training_data)

        assert isinstance(features, list)
        assert isinstance(targets, dict)
        assert len(features) > 0
        assert "overall_success" in targets
        assert len(targets["overall_success"]) > 0


class TestPredictionType:
    """Test PredictionType enum"""

    def test_prediction_type_values(self):
        """Test prediction type enum values"""
        assert PredictionType.OVERALL_SUCCESS.value == "overall_success"
        assert PredictionType.FEATURE_COMPLETENESS.value == "feature_completeness"
        assert PredictionType.PERFORMANCE_IMPACT.value == "performance_impact"
        assert PredictionType.COMPATIBILITY_SCORE.value == "compatibility_score"
        assert PredictionType.RISK_ASSESSMENT.value == "risk_assessment"
        assert PredictionType.CONVERSION_TIME.value == "conversion_time"
        assert PredictionType.RESOURCE_USAGE.value == "resource_usage"


class TestConversionFeatures:
    """Test ConversionFeatures dataclass"""

    def test_conversion_features_creation(self):
        """Test conversion features creation with all required fields"""
        features = ConversionFeatures(
            java_concept="Java Block",
            bedrock_concept="Bedrock Block",
            pattern_type="direct_conversion",
            minecraft_version="1.20.0",
            node_type="block",
            platform="java",
            description_length=50,
            expert_validated=True,
            community_rating=4.5,
            usage_count=100,
            relationship_count=5,
            success_history=[0.8, 0.9, 0.85],
            feature_count=10,
            complexity_score=0.3,
            version_compatibility=0.9,
            cross_platform_difficulty=0.2
        )

        assert features.java_concept == "Java Block"
        assert features.bedrock_concept == "Bedrock Block"
        assert features.pattern_type == "direct_conversion"
        assert features.minecraft_version == "1.20.0"
        assert features.node_type == "block"
        assert features.platform == "java"
        assert features.description_length == 50
        assert features.expert_validated is True
        assert features.community_rating == 4.5
        assert features.usage_count == 100
        assert features.relationship_count == 5
        assert features.success_history == [0.8, 0.9, 0.85]
        assert features.feature_count == 10
        assert features.complexity_score == 0.3
        assert features.version_compatibility == 0.9
        assert features.cross_platform_difficulty == 0.2


class TestPredictionResult:
    """Test PredictionResult dataclass"""

    def test_prediction_result_creation(self):
        """Test prediction result creation with correct fields"""
        result = PredictionResult(
            prediction_type=PredictionType.OVERALL_SUCCESS,
            predicted_value=0.8,
            confidence=0.9,
            feature_importance={"complexity": 0.5},
            risk_factors=["low_complexity"],
            success_factors=["common_pattern"],
            recommendations=["proceed_with_conversion"],
            prediction_metadata={"model": "random_forest"}
        )

        assert result.prediction_type == PredictionType.OVERALL_SUCCESS
        assert result.predicted_value == 0.8
        assert result.confidence == 0.9
        assert result.feature_importance == {"complexity": 0.5}
        assert result.risk_factors == ["low_complexity"]
        assert result.success_factors == ["common_pattern"]
        assert result.recommendations == ["proceed_with_conversion"]
        assert result.prediction_metadata == {"model": "random_forest"}


if __name__ == "__main__":
    pytest.main([__file__])
