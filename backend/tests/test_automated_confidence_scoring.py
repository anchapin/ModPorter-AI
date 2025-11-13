"""
Comprehensive tests for automated_confidence_scoring.py
Enhanced with actual test logic for 80% coverage target
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.automated_confidence_scoring import (
    AutomatedConfidenceScoringService,
    ValidationLayer,
    ValidationScore,
    ConfidenceAssessment
)


class TestAutomatedConfidenceScoringService:
    """Test suite for AutomatedConfidenceScoringService"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        return AutomatedConfidenceScoringService()
    
    @pytest.fixture
    def mock_item_data(self):
        """Mock item data for testing"""
        return {
            "id": "test_id",
            "name": "Test Item",
            "description": "Test description",
            "expert_validated": True,
            "community_rating": 4.2,
            "usage_count": 50,
            "success_rate": 0.85,
            "properties": {"test": "data"}
        }
    
    @pytest.mark.asyncio
    async def test_assess_confidence_basic(self, service, mock_item_data):
        """Test basic confidence assessment"""
        with patch.object(service, '_get_item_data', return_value=mock_item_data):
            with patch.object(service, '_should_apply_layer', return_value=True):
                with patch.object(service, '_apply_validation_layer', return_value=ValidationScore(
                    layer=ValidationLayer.EXPERT_VALIDATION,
                    score=0.9,
                    confidence=0.8,
                    evidence={"expert_approved": True},
                    metadata={}
                )):
                    with patch.object(service, '_calculate_overall_confidence', return_value=0.85):
                        with patch.object(service, '_identify_risk_factors', return_value=[]):
                            with patch.object(service, '_identify_confidence_factors', return_value=[]):
                                with patch.object(service, '_generate_recommendations', return_value=[]):
                                    with patch.object(service, '_cache_assessment'):
                                        result = await service.assess_confidence("node", "test_id", {}, None)
                                        
                                        assert isinstance(result, ConfidenceAssessment)
                                        assert result.overall_confidence == 0.85
                                        assert len(result.validation_scores) >= 1
    
    @pytest.mark.asyncio
    async def test_assess_confidence_edge_cases(self, service):
        """Test edge cases for confidence assessment"""
        # Test with missing item
        with patch.object(service, '_get_item_data', return_value=None):
            with pytest.raises(ValueError, match="Item not found"):
                await service.assess_confidence("node", "nonexistent_id", {}, None)
        
        # Test with empty validation scores
        with patch.object(service, '_get_item_data', return_value={"id": "test"}):
            with patch.object(service, '_apply_validation_layers', return_value=[]):
                with patch.object(service, '_calculate_overall_confidence', return_value=0.0):
                    result = await service.assess_confidence("node", "test", {}, None)
                    assert result.overall_confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_assess_confidence_error_handling(self, service):
        """Test error handling in confidence assessment"""
        # Test with database error
        with patch.object(service, '_get_item_data', side_effect=Exception("Database error")):
            with pytest.raises(Exception, match="Database error"):
                await service.assess_confidence("node", "test_id", {}, None)
    
    @pytest.mark.asyncio
    async def test_batch_assess_confidence_basic(self, service, mock_item_data):
        """Test batch confidence assessment"""
        items = [
            {"item_type": "node", "item_id": "test1"},
            {"item_type": "relationship", "item_id": "test2"},
            {"item_type": "pattern", "item_id": "test3"}
        ]
        
        with patch.object(service, 'assess_confidence', return_value=ConfidenceAssessment(
            overall_confidence=0.8,
            validation_scores=[],
            risk_factors=[],
            confidence_factors=[],
            recommendations=[],
            assessment_metadata={}
        )):
            result = await service.batch_assess_confidence(items, None)
            
            assert result['success'] is True
            assert result['total_items'] == 3
            assert len(result['batch_results']) == 3
    
    @pytest.mark.asyncio
    async def test_batch_assess_confidence_edge_cases(self, service):
        """Test edge cases for batch assessment"""
        # Test with empty batch
        result = await service.batch_assess_confidence([], None)
        assert result['success'] is True
        assert result['total_items'] == 0
        assert len(result['batch_results']) == 0
        
        # Test with mixed valid/invalid items
        items = [
            {"item_type": "node", "item_id": "valid"},
            {"item_type": "invalid_type", "item_id": "invalid"}
        ]
        
        with patch.object(service, 'assess_confidence', side_effect=[ConfidenceAssessment(
            overall_confidence=0.8, validation_scores=[], risk_factors=[], confidence_factors=[], 
            recommendations=[], assessment_metadata={}
        ), ValueError("Invalid item type")]):
            result = await service.batch_assess_confidence(items, None)
            assert result['success'] is True
            assert result['successful_assessments'] == 1
            assert result['failed_assessments'] == 1
    
    @pytest.mark.asyncio
    async def test_batch_assess_confidence_error_handling(self, service):
        """Test error handling in batch assessment"""
        items = [{"item_type": "node", "item_id": "test"}]
        
        # Test with complete service failure
        with patch.object(service, 'assess_confidence', side_effect=Exception("Service unavailable")):
            result = await service.batch_assess_confidence(items, None)
            assert result['success'] is False
            assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_update_confidence_from_feedback_basic(self, service):
        """Test basic confidence update from feedback"""
        feedback_data = {
            "assessment_id": "test_assessment",
            "actual_outcome": "success",
            "confidence_rating": 0.9,
            "feedback_comments": "Excellent prediction"
        }
        
        with patch.object(service, '_find_assessment_record', return_value={"confidence": 0.8}):
            with patch.object(service, '_update_validation_weights', return_value=True):
                with patch.object(service, '_record_feedback', return_value=True):
                    result = await service.update_confidence_from_feedback(feedback_data, None)
                    
                    assert result['success'] is True
                    assert 'weight_adjustments' in result
                    assert 'new_confidence' in result
    
    @pytest.mark.asyncio
    async def test_update_confidence_from_feedback_edge_cases(self, service):
        """Test edge cases for confidence update"""
        # Test with missing assessment
        feedback_data = {"assessment_id": "nonexistent"}
        
        with patch.object(service, '_find_assessment_record', return_value=None):
            result = await service.update_confidence_from_feedback(feedback_data, None)
            assert result['success'] is False
            assert 'assessment not found' in result['error'].lower()
        
        # Test with invalid confidence rating
        feedback_data = {
            "assessment_id": "test",
            "confidence_rating": 1.5  # Invalid > 1.0
        }
        
        with patch.object(service, '_find_assessment_record', return_value={"confidence": 0.8}):
            result = await service.update_confidence_from_feedback(feedback_data, None)
            assert result['success'] is False
    
    @pytest.mark.asyncio
    async def test_update_confidence_from_feedback_error_handling(self, service):
        """Test error handling in confidence update"""
        feedback_data = {"assessment_id": "test"}
        
        with patch.object(service, '_find_assessment_record', side_effect=Exception("Database error")):
            result = await service.update_confidence_from_feedback(feedback_data, None)
            assert result['success'] is False
            assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_get_confidence_trends_basic(self, service):
        """Test basic confidence trends analysis"""
        with patch.object(service, '_get_historical_assessments', return_value=[
            {"timestamp": datetime.now() - timedelta(days=5), "confidence": 0.7},
            {"timestamp": datetime.now() - timedelta(days=3), "confidence": 0.8},
            {"timestamp": datetime.now() - timedelta(days=1), "confidence": 0.85}
        ]):
            with patch.object(service, '_analyze_trends', return_value={
                "trend": "improving",
                "rate": 0.075,
                "confidence_level": "high"
            }):
                result = await service.get_confidence_trends(days=7, item_type="node", db=None)
                
                assert result['success'] is True
                assert 'trend_analysis' in result
                assert result['trend_analysis']['trend'] == "improving"
    
    @pytest.mark.asyncio
    async def test_get_confidence_trends_edge_cases(self, service):
        """Test edge cases for confidence trends"""
        # Test with no data
        with patch.object(service, '_get_historical_assessments', return_value=[]):
            result = await service.get_confidence_trends(days=7, item_type=None, db=None)
            assert result['success'] is True
            assert result['trend_analysis']['trend'] == "insufficient_data"
        
        # Test with single data point
        single_data = [{"timestamp": datetime.now(), "confidence": 0.8}]
        with patch.object(service, '_get_historical_assessments', return_value=single_data):
            result = await service.get_confidence_trends(days=7, item_type=None, db=None)
            assert result['success'] is True
            assert result['trend_analysis']['trend'] == "insufficient_data"
    
    @pytest.mark.asyncio
    async def test_get_confidence_trends_error_handling(self, service):
        """Test error handling in confidence trends"""
        with patch.object(service, '_get_historical_assessments', side_effect=Exception("Database error")):
            result = await service.get_confidence_trends(days=7, item_type=None, db=None)
            assert result['success'] is False
            assert 'error' in result


class TestValidationLayer:
    """Test suite for ValidationLayer enum"""
    
    def test_validation_layer_values(self):
        """Test ValidationLayer enum values"""
        assert ValidationLayer.EXPERT_VALIDATION.value == "expert_validation"
        assert ValidationLayer.COMMUNITY_VALIDATION.value == "community_validation"
        assert ValidationLayer.HISTORICAL_VALIDATION.value == "historical_validation"
        assert ValidationLayer.PATTERN_VALIDATION.value == "pattern_validation"
        assert ValidationLayer.CROSS_PLATFORM_VALIDATION.value == "cross_platform_validation"
        assert ValidationLayer.VERSION_COMPATIBILITY.value == "version_compatibility"
        assert ValidationLayer.USAGE_VALIDATION.value == "usage_validation"
        assert ValidationLayer.SEMANTIC_VALIDATION.value == "semantic_validation"
    
    def test_validation_layer_uniqueness(self):
        """Test that all validation layers have unique values"""
        values = [layer.value for layer in ValidationLayer]
        assert len(values) == len(set(values))


class TestValidationScore:
    """Test suite for ValidationScore dataclass"""
    
    def test_validation_score_creation(self):
        """Test ValidationScore dataclass creation"""
        score = ValidationScore(
            layer=ValidationLayer.EXPERT_VALIDATION,
            score=0.85,
            confidence=0.9,
            evidence={"expert_approved": True},
            metadata={"assessment_version": "1.0"}
        )
        
        assert score.layer == ValidationLayer.EXPERT_VALIDATION
        assert score.score == 0.85
        assert score.confidence == 0.9
        assert score.evidence["expert_approved"] is True
        assert score.metadata["assessment_version"] == "1.0"


class TestConfidenceAssessment:
    """Test suite for ConfidenceAssessment dataclass"""
    
    def test_confidence_assessment_creation(self):
        """Test ConfidenceAssessment dataclass creation"""
        validation_score = ValidationScore(
            layer=ValidationLayer.EXPERT_VALIDATION,
            score=0.9,
            confidence=0.8,
            evidence={},
            metadata={}
        )
        
        assessment = ConfidenceAssessment(
            overall_confidence=0.85,
            validation_scores=[validation_score],
            risk_factors=["limited_usage"],
            confidence_factors=["expert_validated"],
            recommendations=["increase_usage_data"],
            assessment_metadata={"assessment_version": "1.0"}
        )
        
        assert assessment.overall_confidence == 0.85
        assert len(assessment.validation_scores) == 1
        assert assessment.risk_factors == ["limited_usage"]
        assert assessment.confidence_factors == ["expert_validated"]
        assert assessment.recommendations == ["increase_usage_data"]
        assert assessment.assessment_metadata["assessment_version"] == "1.0"
