"""
Comprehensive working tests for conversion_success_prediction.py
Phase 3: Core Logic Completion
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os
import numpy as np
from datetime import datetime

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
            return ConversionSuccessPredictionService()

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = AsyncMock()
        return session

    @pytest.fixture
    def sample_features(self):
        """Create sample conversion features"""
        return ConversionFeatures(
            java_concept="Java Block",
            bedrock_concept="Bedrock Block",
            pattern_type="direct_mapping",
            minecraft_version="1.20.0",
            node_type="block",
            platform="java"
        )

    @pytest.fixture
    def sample_knowledge_node(self):
        """Create sample knowledge node"""
        return KnowledgeNode(
            id=1,
            node_type="block",
            name="test_block",
            description="Test block for conversion",
            metadata={"complexity": "medium"}
        )

    # Test initialization
    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert hasattr(service, 'models')
        assert hasattr(service, 'scalers')
        assert hasattr(service, 'feature_columns')

    # Test feature encoding
    def test_encode_pattern_type(self, service):
        """Test pattern type encoding"""
        result = service._encode_pattern_type("direct_mapping")
        assert isinstance(result, float)
        assert 0 <= result <= 1

    def test_encode_pattern_type_unknown(self, service):
        """Test encoding unknown pattern type"""
        result = service._encode_pattern_type("unknown_pattern")
        assert isinstance(result, float)
        assert result == 0.0  # Default value

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
            metadata=None
        )
        complexity = service._calculate_complexity(node)
        assert isinstance(complexity, float)
        assert complexity == 0.5  # Default complexity

    # Test cross-platform difficulty
    def test_calculate_cross_platform_difficulty(self, service):
        """Test cross-platform difficulty calculation"""
        difficulty = service._calculate_cross_platform_difficulty(
            java_concept="Java Block",
            bedrock_concept="Bedrock Block",
            platform="java"
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
    async def test_make_prediction(self, service, mock_db_session):
        """Test making predictions"""
        # Mock model and scaler
        service.models = {"overall_success": Mock()}
        service.scalers = {"overall_success": Mock()}
        service.models["overall_success"].predict.return_value = [0.8]
        service.scalers["overall_success"].transform.return_value = np.array([[1.0, 2.0, 3.0]])

        result = await service._make_prediction(
            features=[1.0, 2.0, 3.0],
            prediction_type=PredictionType.OVERALL_SUCCESS,
            db=mock_db_session
        )

        assert isinstance(result, PredictionResult)
        assert result.success_probability == 0.8
        assert result.confidence > 0

    # Test confidence calculation
    def test_calculate_prediction_confidence(self, service):
        """Test prediction confidence calculation"""
        # Test with consistent predictions
        confidence = service._calculate_prediction_confidence([0.8, 0.8, 0.8])
        assert confidence > 0.9

        # Test with varying predictions
        confidence = service._calculate_prediction_confidence([0.3, 0.8, 0.5])
        assert 0 <= confidence <= 1

    # Test risk factor identification
    def test_identify_risk_factors(self, service):
        """Test risk factor identification"""
        features = {
            'complexity': 0.9,
            'cross_platform_difficulty': 0.8,
            'pattern_rarity': 0.7
        }
        risks = service._identify_risk_factors(features)
        assert isinstance(risks, list)
        assert len(risks) > 0
        assert all(isinstance(risk, str) for risk in risks)

    # Test success factor identification
    def test_identify_success_factors(self, service):
        """Test success factor identification"""
        features = {
            'complexity': 0.2,
            'cross_platform_difficulty': 0.1,
            'pattern_commonality': 0.9
        }
        factors = service._identify_success_factors(features)
        assert isinstance(factors, list)
        assert len(factors) > 0
        assert all(isinstance(factor, str) for factor in factors)

    # Test conversion viability analysis
    @pytest.mark.asyncio
    async def test_analyze_conversion_viability(self, service, mock_db_session):
        """Test conversion viability analysis"""
        viability = await service._analyze_conversion_viability(
            features=[1.0, 2.0, 3.0],
            db=mock_db_session
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
        assert "proceed" in action.lower()

        # Medium viability
        action = service._get_recommended_action("medium")
        assert isinstance(action, str)
        assert "caution" in action.lower() or "review" in action.lower()

        # Low viability
        action = service._get_recommended_action("low")
        assert isinstance(action, str)
        assert "avoid" in action.lower() or "redesign" in action.lower()

    # Test model training
    @pytest.mark.asyncio
    async def test_train_models(self, service, mock_db_session):
        """Test model training"""
        # Mock training data collection
        with patch.object(service, '_collect_training_data') as mock_collect:
            mock_collect.return_value = [
                {
                    'features': [1.0, 2.0, 3.0],
                    'target_overall_success': 1,
                    'target_feature_completeness': 0.8,
                    'target_performance_impact': 0.7
                }
            ]

            # Mock model training
            with patch.object(service, '_train_model') as mock_train:
                mock_train.return_value = Mock()

                result = await service.train_models(db=mock_db_session)
                assert isinstance(result, dict)
                assert 'models_trained' in result
                assert 'training_samples' in result

    # Test conversion success prediction
    @pytest.mark.asyncio
    async def test_predict_conversion_success(self, service, mock_db_session, sample_features):
        """Test conversion success prediction"""
        # Mock the internal methods
        with patch.object(service, '_extract_conversion_features') as mock_extract, \
             patch.object(service, '_prepare_feature_vector') as mock_prepare, \
             patch.object(service, '_make_prediction') as mock_predict:

            mock_extract.return_value = sample_features
            mock_prepare.return_value = np.array([1.0, 2.0, 3.0])
            mock_predict.return_value = PredictionResult(
                success_probability=0.8,
                confidence=0.9,
                risk_factors=["low"],
                success_factors=["high"],
                recommendations=["proceed"]
            )

            result = await service.predict_conversion_success(
                java_concept="Java Block",
                bedrock_concept="Bedrock Block",
                pattern_type="direct_mapping",
                minecraft_version="1.20.0",
                node_type="block",
                platform="java",
                db=mock_db_session
            )

            assert isinstance(result, PredictionResult)
            assert result.success_probability == 0.8
            assert result.confidence == 0.9

    # Test batch prediction
    @pytest.mark.asyncio
    async def test_batch_predict_success(self, service, mock_db_session):
        """Test batch success prediction"""
        requests = [
            {
                'java_concept': 'Java Block 1',
                'bedrock_concept': 'Bedrock Block 1',
                'pattern_type': 'direct_mapping',
                'minecraft_version': '1.20.0',
                'node_type': 'block',
                'platform': 'java'
            },
            {
                'java_concept': 'Java Block 2',
                'bedrock_concept': 'Bedrock Block 2',
                'pattern_type': 'indirect_mapping',
                'minecraft_version': '1.20.0',
                'node_type': 'block',
                'platform': 'java'
            }
        ]

        # Mock the prediction method
        with patch.object(service, 'predict_conversion_success') as mock_predict:
            mock_predict.return_value = PredictionResult(
                success_probability=0.8,
                confidence=0.9,
                risk_factors=["low"],
                success_factors=["high"],
                recommendations=["proceed"]
            )

            results = await service.batch_predict_success(requests, db=mock_db_session)

            assert isinstance(results, list)
            assert len(results) == 2
            assert all(isinstance(result, PredictionResult) for result in results)
            assert mock_predict.call_count == 2

    # Test error handling
    @pytest.mark.asyncio
    async def test_predict_conversion_success_error(self, service, mock_db_session):
        """Test error handling in prediction"""
        # Mock exception in feature extraction
        with patch.object(service, '_extract_conversion_features') as mock_extract:
            mock_extract.side_effect = Exception("Feature extraction failed")

            with pytest.raises(Exception):
                await service.predict_conversion_success(
                    java_concept="Java Block",
                    bedrock_concept="Bedrock Block",
                    pattern_type="direct_mapping",
                    minecraft_version="1.20.0",
                    node_type="block",
                    platform="java",
                    db=mock_db_session
                )

    # Test model update with feedback
    @pytest.mark.asyncio
    async def test_update_models_with_feedback(self, service, mock_db_session):
        """Test updating models with feedback"""
        feedback_data = [
            {
                'java_concept': 'Java Block',
                'bedrock_concept': 'Bedrock Block',
                'actual_success': True,
                'predicted_probability': 0.8,
                'conversion_time': 120,
                'issues': ['minor_compatibility']
            }
        ]

        with patch.object(service, 'train_models') as mock_train:
            mock_train.return_value = {'models_trained': 5, 'training_samples': 100}

            result = await service.update_models_with_feedback(feedback_data, db=mock_db_session)

            assert isinstance(result, dict)
            assert 'models_updated' in result
            assert 'feedback_processed' in result
            assert mock_train.called


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
        """Test conversion features creation"""
        features = ConversionFeatures(
            java_concept="Java Block",
            bedrock_concept="Bedrock Block",
            pattern_type="direct_mapping",
            minecraft_version="1.20.0",
            node_type="block",
            platform="java"
        )

        assert features.java_concept == "Java Block"
        assert features.bedrock_concept == "Bedrock Block"
        assert features.pattern_type == "direct_mapping"
        assert features.minecraft_version == "1.20.0"
        assert features.node_type == "block"
        assert features.platform == "java"


class TestPredictionResult:
    """Test PredictionResult dataclass"""

    def test_prediction_result_creation(self):
        """Test prediction result creation"""
        result = PredictionResult(
            success_probability=0.8,
            confidence=0.9,
            risk_factors=["low_complexity"],
            success_factors=["common_pattern"],
            recommendations=["proceed_with_conversion"]
        )

        assert result.success_probability == 0.8
        assert result.confidence == 0.9
        assert result.risk_factors == ["low_complexity"]
        assert result.success_factors == ["common_pattern"]
        assert result.recommendations == ["proceed_with_conversion"]


if __name__ == "__main__":
    pytest.main([__file__])
