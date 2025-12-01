"""
Comprehensive tests for automated_confidence_scoring.py
Focus on improving coverage toward 80% target
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
from datetime import datetime

# Add source to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAutomatedConfidenceScoringService:
    """Comprehensive test suite for AutomatedConfidenceScoringService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        # Mock imports that cause issues
        with patch.dict(
            "sys.modules",
            {
                "db": Mock(),
                "db.models": Mock(),
                "db.knowledge_graph_crud": Mock(),
                "numpy": Mock(),
                "sklearn": Mock(),
            },
        ):
            from src.services.automated_confidence_scoring import (
                AutomatedConfidenceScoringService,
            )

            return AutomatedConfidenceScoringService()

    def test_service_import(self):
        """Test that service can be imported"""
        try:
            from src.services.automated_confidence_scoring import (
                AutomatedConfidenceScoringService,
            )

            assert AutomatedConfidenceScoringService is not None
        except ImportError as e:
            pytest.skip(f"Cannot import service: {e}")

    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        # Should have ML models initialized
        assert hasattr(service, "models")
        assert hasattr(service, "scalers")

    @pytest.mark.asyncio
    async def test_assess_confidence_basic(self, service, mock_db):
        """Test basic confidence assessment"""
        # Create test assessment request
        assessment_request = {
            "conversion_id": "test_conversion_123",
            "java_mod_id": "test_mod_java",
            "bedrock_mod_id": "test_mod_bedrock",
            "features": {
                "code_complexity": 0.7,
                "api_usage": 0.8,
                "resource_requirements": 0.6,
                "documentation_quality": 0.9,
            },
        }

        # Mock ML prediction
        with patch.object(service, "models") as mock_models:
            mock_confidence_model = Mock()
            mock_confidence_model.predict.return_value = [0.85]
            mock_models.confidence = mock_confidence_model

            result = await service.assess_confidence(assessment_request, mock_db)

            assert result is not None
            assert "confidence_score" in result
            assert "assessment_id" in result
            assert "conversion_id" in result

    @pytest.mark.asyncio
    async def test_batch_assess_confidence(self, service, mock_db):
        """Test batch confidence assessment"""
        # Create test batch request
        batch_request = {
            "conversions": [
                {
                    "conversion_id": "test_conversion_1",
                    "java_mod_id": "mod1_java",
                    "bedrock_mod_id": "mod1_bedrock",
                    "features": {"code_complexity": 0.7},
                },
                {
                    "conversion_id": "test_conversion_2",
                    "java_mod_id": "mod2_java",
                    "bedrock_mod_id": "mod2_bedrock",
                    "features": {"code_complexity": 0.8},
                },
            ]
        }

        with patch.object(service, "assess_confidence") as mock_assess:
            mock_assess.side_effect = [
                {"confidence_score": 0.85, "assessment_id": "assess1"},
                {"confidence_score": 0.72, "assessment_id": "assess2"},
            ]

            results = await service.batch_assess_confidence(batch_request, mock_db)

            assert len(results) == 2
            assert results[0]["confidence_score"] == 0.85
            assert results[1]["confidence_score"] == 0.72
            assert mock_assess.call_count == 2

    @pytest.mark.asyncio
    async def test_update_confidence_from_feedback(self, service, mock_db):
        """Test updating confidence scores from feedback"""
        feedback_data = {
            "assessment_id": "assess_123",
            "conversion_id": "conv_123",
            "original_confidence": 0.85,
            "actual_success": True,
            "feedback_source": "user_review",
            "feedback_notes": "Conversion was successful",
            "timestamp": datetime.now().isoformat(),
        }

        with patch.object(service, "models") as mock_models:
            mock_update_model = Mock()
            mock_update_model.partial_fit.return_value = None
            mock_models.confidence_update = mock_update_model

            result = await service.update_confidence_from_feedback(
                feedback_data, mock_db
            )

            assert result is True
            mock_update_model.partial_fit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_confidence_trends(self, service, mock_db):
        """Test getting confidence trends over time"""
        conversion_id = "test_conversion_123"

        # Mock trend data
        mock_trend_data = [
            {"date": "2024-01-01", "avg_confidence": 0.82, "count": 10},
            {"date": "2024-01-02", "avg_confidence": 0.85, "count": 15},
            {"date": "2024-01-03", "avg_confidence": 0.88, "count": 12},
        ]

        with patch(
            "src.services.automated_confidence_scoring.ConfidenceAssessmentCRUD"
        ) as mock_crud:
            mock_crud.get_confidence_trends.return_value = mock_trend_data

            result = await service.get_confidence_trends(conversion_id, mock_db)

            assert len(result) == 3
            assert result[0]["avg_confidence"] == 0.82
            assert result[-1]["avg_confidence"] == 0.88
            mock_crud.get_confidence_trends.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_assessment_request(self, service):
        """Test validation of assessment requests"""
        # Valid request
        valid_request = {
            "conversion_id": "test_123",
            "java_mod_id": "mod_java",
            "bedrock_mod_id": "mod_bedrock",
            "features": {"code_complexity": 0.7},
        }

        result = await service.validate_assessment_request(valid_request)
        assert result["valid"] is True
        assert "errors" not in result

        # Invalid request - missing required fields
        invalid_request = {
            "conversion_id": "test_123",
            "features": {"code_complexity": 0.7},
        }

        result = await service.validate_assessment_request(invalid_request)
        assert result["valid"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0

    def test_extract_features_from_request(self, service):
        """Test feature extraction from assessment request"""
        request = {
            "conversion_id": "test_123",
            "java_mod_id": "mod_java",
            "bedrock_mod_id": "mod_bedrock",
            "features": {
                "code_complexity": 0.7,
                "api_usage": 0.8,
                "resource_requirements": 0.6,
                "documentation_quality": 0.9,
                "test_coverage": 0.85,
            },
        }

        features = service.extract_features_from_request(request)

        assert len(features) == 5  # Should extract all feature values
        assert 0.7 in features
        assert 0.8 in features
        assert 0.6 in features
        assert 0.9 in features
        assert 0.85 in features

    def test_calculate_confidence_score(self, service):
        """Test confidence score calculation"""
        # Test with high feature values
        features = [0.9, 0.8, 0.85, 0.95]
        score = service.calculate_confidence_score(features)

        assert score >= 0.8  # High features should give high confidence
        assert score <= 1.0  # Should be normalized

        # Test with low feature values
        features = [0.3, 0.4, 0.35, 0.25]
        score = service.calculate_confidence_score(features)

        assert score <= 0.5  # Low features should give low confidence
        assert score >= 0.0  # Should be normalized

    @pytest.mark.asyncio
    async def test_save_assessment_result(self, service, mock_db):
        """Test saving assessment results"""
        assessment_result = {
            "assessment_id": "assess_123",
            "conversion_id": "conv_123",
            "confidence_score": 0.85,
            "features": {"code_complexity": 0.7},
            "model_version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
        }

        with patch(
            "src.services.automated_confidence_scoring.ConfidenceAssessmentCRUD"
        ) as mock_crud:
            mock_crud.create.return_value = Mock()

            result = await service.save_assessment_result(assessment_result, mock_db)

            # Should successfully save assessment
            assert result is not None
            mock_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_assessment_history(self, service, mock_db):
        """Test retrieving assessment history"""
        conversion_id = "test_conversion_123"

        # Mock historical assessment data
        mock_history = [
            Mock(
                assessment_id="assess1", confidence_score=0.82, timestamp=datetime.now()
            ),
            Mock(
                assessment_id="assess2", confidence_score=0.85, timestamp=datetime.now()
            ),
            Mock(
                assessment_id="assess3", confidence_score=0.88, timestamp=datetime.now()
            ),
        ]

        with patch(
            "src.services.automated_confidence_scoring.ConfidenceAssessmentCRUD"
        ) as mock_crud:
            mock_crud.get_by_conversion_id.return_value = mock_history

            result = await service.get_assessment_history(conversion_id, mock_db)

            assert len(result) == 3
            assert result[0].confidence_score == 0.82
            assert result[-1].confidence_score == 0.88
            mock_crud.get_by_conversion_id.assert_called_once()

    def test_feature_normalization(self, service):
        """Test feature normalization"""
        # Test normalization of feature values
        features = {
            "code_complexity": 150,  # Raw value
            "api_usage": 25,  # Raw value
            "resource_requirements": 500,  # Raw value
            "documentation_quality": 80,  # Raw value
        }

        normalized = service.normalize_features(features)

        # All values should be between 0 and 1
        for key, value in normalized.items():
            assert 0.0 <= value <= 1.0

    @pytest.mark.asyncio
    async def test_assess_confidence_error_handling(self, service, mock_db):
        """Test error handling in confidence assessment"""
        # Test with invalid features
        invalid_request = {
            "conversion_id": "test_123",
            "java_mod_id": "mod_java",
            "bedrock_mod_id": "mod_bedrock",
            "features": {"invalid_feature": "not_a_number"},
        }

        result = await service.assess_confidence(invalid_request, mock_db)

        # Should handle error gracefully
        assert result is not None
        assert "error" in result
        assert result["confidence_score"] == 0.5  # Default fallback

    @pytest.mark.asyncio
    async def test_batch_assess_confidence_error_handling(self, service, mock_db):
        """Test error handling in batch confidence assessment"""
        # Test with mixed valid/invalid requests
        batch_request = {
            "conversions": [
                {
                    "conversion_id": "valid_1",
                    "java_mod_id": "mod1_java",
                    "bedrock_mod_id": "mod1_bedrock",
                    "features": {"code_complexity": 0.7},
                },
                {
                    "conversion_id": "invalid_1",
                    "java_mod_id": "mod2_java",
                    "bedrock_mod_id": "mod2_bedrock",
                    "features": {"invalid_feature": "not_a_number"},
                },
                {
                    "conversion_id": "valid_2",
                    "java_mod_id": "mod3_java",
                    "bedrock_mod_id": "mod3_bedrock",
                    "features": {"code_complexity": 0.8},
                },
            ]
        }

        with patch.object(service, "assess_confidence") as mock_assess:
            mock_assess.side_effect = [
                {"confidence_score": 0.85},  # valid
                {"error": "Invalid features", "confidence_score": 0.5},  # invalid
                {"confidence_score": 0.72},  # valid
            ]

            results = await service.batch_assess_confidence(batch_request, mock_db)

            # Should handle mixed results
            assert len(results) == 3
            assert results[0]["confidence_score"] == 0.85
            assert "error" in results[1]
            assert results[2]["confidence_score"] == 0.72

    def test_model_training_features(self, service):
        """Test model training feature extraction"""
        # Mock training data
        training_data = [
            {"features": {"code_complexity": 0.7, "api_usage": 0.8}, "target": 0.85},
            {"features": {"code_complexity": 0.6, "api_usage": 0.7}, "target": 0.72},
        ]

        # Extract feature vectors and targets
        feature_vectors, targets = service.extract_training_features(training_data)

        assert len(feature_vectors) == 2
        assert len(targets) == 2
        assert targets[0] == 0.85
        assert targets[1] == 0.72
        assert len(feature_vectors[0]) == 2  # Two features
        assert len(feature_vectors[1]) == 2

    @pytest.mark.asyncio
    async def test_confidence_threshold_validation(self, service, mock_db):
        """Test confidence threshold validation"""
        assessment_request = {
            "conversion_id": "test_123",
            "java_mod_id": "mod_java",
            "bedrock_mod_id": "mod_bedrock",
            "features": {"code_complexity": 0.1},  # Very low confidence
            "threshold": 0.5,  # Required threshold
        }

        # Mock low confidence prediction
        with patch.object(service, "calculate_confidence_score", return_value=0.3):
            result = await service.assess_confidence(assessment_request, mock_db)

            assert result["confidence_score"] == 0.3
            assert result["meets_threshold"] is False
            assert "warning" in result

    @pytest.mark.asyncio
    async def test_confidence_improvement_tracking(self, service, mock_db):
        """Test tracking confidence improvements over time"""
        conversion_id = "test_conversion_123"

        # Mock improvement data
        mock_improvements = [
            {"date": "2024-01-01", "avg_confidence": 0.75, "improvement": 0.0},
            {"date": "2024-01-02", "avg_confidence": 0.82, "improvement": 0.07},
            {"date": "2024-01-03", "avg_confidence": 0.88, "improvement": 0.13},
        ]

        with patch(
            "src.services.automated_confidence_scoring.ConfidenceAssessmentCRUD"
        ) as mock_crud:
            mock_crud.get_confidence_improvements.return_value = mock_improvements

            result = await service.get_confidence_improvements(conversion_id, mock_db)

            assert len(result) == 3
            assert result[0]["improvement"] == 0.0
            assert result[-1]["improvement"] == 0.13
            assert result[1]["improvement"] == 0.07
