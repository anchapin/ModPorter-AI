"""
Comprehensive working tests for automated_confidence_scoring.py
Phase 3: Core Logic Completion - 80% Coverage Target
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.automated_confidence_scoring import (
    AutomatedConfidenceScoringService,
    ValidationLayer,
    ValidationScore,
    ConfidenceAssessment
)


class TestAutomatedConfidenceScoringService:
    """Test cases for AutomatedConfidenceScoringService"""

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        with patch('services.automated_confidence_scoring.KnowledgeNodeCRUD'), \
             patch('services.automated_confidence_scoring.KnowledgeRelationshipCRUD'), \
             patch('services.automated_confidence_scoring.ConversionPatternCRUD'):
            service = AutomatedConfidenceScoringService()
            # Initialize required attributes
            service.confidence_cache = {}
            service.validation_history = []
            service.feedback_history = []
            return service

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = AsyncMock()
        return session

    @pytest.fixture
    def sample_item_data(self):
        """Create sample item data for validation"""
        return {
            "id": "test_item_1",
            "type": "knowledge_relationship",
            "java_concept": "Java Block",
            "bedrock_concept": "Bedrock Block",
            "pattern_type": "direct_conversion",
            "minecraft_version": "1.20.0",
            "expert_validated": True,
            "community_rating": 4.5,
            "usage_count": 100,
            "success_rate": 0.85,
            "historical_accuracy": 0.9,
            "cross_platform_compatible": True,
            "version_compatibility": 0.9,
            "semantic_similarity": 0.8,
            "properties": {"test": "value"},
            "metadata": {"source": "expert_curated"}
        }

    # Test initialization
    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert hasattr(service, 'confidence_cache')
        assert hasattr(service, 'validation_history')
        assert hasattr(service, 'feedback_history')

    # Test confidence assessment
    @pytest.mark.asyncio
    async def test_assess_confidence(self, service, mock_db_session, sample_item_data):
        """Test confidence assessment"""
        # Mock validation methods
        with patch.object(service, '_get_item_data') as mock_get_data, \
             patch.object(service, '_should_apply_layer') as mock_should_apply, \
             patch.object(service, '_apply_validation_layer') as mock_validate, \
             patch.object(service, '_calculate_overall_confidence') as mock_calc, \
             patch.object(service, '_cache_assessment') as mock_cache:

            mock_get_data.return_value = sample_item_data
            mock_should_apply.return_value = True
            mock_validate.return_value = ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.9,
                confidence=0.95,
                evidence={"expert_approved": True},
                metadata={"validator": "expert_1"}
            )
            mock_calc.return_value = 0.85
            mock_cache.return_value = None

            result = await service.assess_confidence(
                item_type="knowledge_relationship",
                item_id="test_item_1",
                db=mock_db_session
            )

            assert isinstance(result, ConfidenceAssessment)
            assert result.overall_confidence == 0.85
            assert len(result.validation_scores) > 0

    # Test batch confidence assessment
    @pytest.mark.asyncio
    async def test_batch_assess_confidence(self, service, mock_db_session):
        """Test batch confidence assessment"""
        items = [
            {"type": "knowledge_relationship", "id": "item_1"},
            {"type": "conversion_pattern", "id": "item_2"},
            {"type": "knowledge_node", "id": "item_3"}
        ]

        # Mock individual assessment
        with patch.object(service, 'assess_confidence') as mock_assess:
            mock_assess.return_value = ConfidenceAssessment(
                overall_confidence=0.8,
                validation_scores=[
                    ValidationScore(
                        layer=ValidationLayer.EXPERT_VALIDATION,
                        score=0.9,
                        confidence=0.95,
                        evidence={},
                        metadata={}
                    )
                ]
            )

            result = await service.batch_assess_confidence(items, db=mock_db_session)

            assert isinstance(result, dict)
            assert "batch_results" in result
            assert "total_items" in result
            assert result["total_items"] == 3
            assert mock_assess.call_count == 3

    # Test confidence update from feedback
    @pytest.mark.asyncio
    async def test_update_confidence_from_feedback(self, service, mock_db_session):
        """Test confidence update from feedback"""
        feedback_data = {
            "item_type": "knowledge_relationship",
            "item_id": "test_item_1",
            "actual_outcome": "success",
            "confidence_score": 0.8,
            "feedback_type": "performance",
            "details": {"conversion_completed": True, "accuracy": 0.9}
        }

        # Mock update methods
        with patch.object(service, '_calculate_feedback_impact') as mock_impact, \
             patch.object(service, '_apply_feedback_to_score') as mock_apply, \
             patch.object(service, '_update_item_confidence') as mock_update, \
             patch.object(service, '_get_item_data') as mock_get_data:

            mock_impact.return_value = {"expert_validation": 0.1, "community_validation": -0.05}
            mock_apply.return_value = 0.85
            mock_update.return_value = {"success": True, "new_confidence": 0.85}
            mock_get_data.return_value = {"current_confidence": 0.8}

            result = await service.update_confidence_from_feedback(
                feedback_data, db=mock_db_session
            )

            assert isinstance(result, dict)
            assert "item_type" in result
            assert "item_id" in result
            assert "feedback_impact" in result
            assert "updated_confidence" in result

    # Test confidence trends
    @pytest.mark.asyncio
    async def test_get_confidence_trends(self, service, mock_db_session):
        """Test confidence trends analysis"""
        # Mock trend analysis
        with patch.object(service, '_analyze_layer_performance') as mock_analyze:
            mock_analyze.return_value = {
                "expert_validation": {"trend": "stable", "avg_confidence": 0.9},
                "community_validation": {"trend": "increasing", "avg_confidence": 0.8}
            }

            result = await service.get_confidence_trends(
                days=30,
                layer=ValidationLayer.EXPERT_VALIDATION,
                db=mock_db_session
            )

            assert isinstance(result, dict)
            assert "trends" in result
            assert "analysis_period" in result
            assert result["analysis_period"] == 30

    # Test item data retrieval
    @pytest.mark.asyncio
    async def test_get_item_data(self, service, mock_db_session):
        """Test item data retrieval"""
        # Mock CRUD operations
        with patch('services.automated_confidence_scoring.KnowledgeNodeCRUD.get_by_id') as mock_node, \
             patch('services.automated_confidence_scoring.KnowledgeRelationshipCRUD.get_by_id') as mock_rel, \
             patch('services.automated_confidence_scoring.ConversionPatternCRUD.get_by_id') as mock_pattern:

            mock_node.return_value = Mock(
                id="node_1",
                name="test_node",
                expert_validated=True,
                community_rating=4.5,
                usage_count=100
            )
            mock_rel.return_value = Mock(
                id="rel_1",
                confidence_score=0.8,
                expert_validated=True
            )
            mock_pattern.return_value = Mock(
                id="pattern_1",
                success_rate=0.85,
                expert_validated=True
            )

            # Test different item types
            node_data = await service._get_item_data("knowledge_node", "node_1", mock_db_session)
            assert isinstance(node_data, dict)
            assert "id" in node_data
            assert node_data["id"] == "node_1"

            rel_data = await service._get_item_data("knowledge_relationship", "rel_1", mock_db_session)
            assert isinstance(rel_data, dict)
            assert rel_data["id"] == "rel_1"

            pattern_data = await service._get_item_data("conversion_pattern", "pattern_1", mock_db_session)
            assert isinstance(pattern_data, dict)
            assert pattern_data["id"] == "pattern_1"

    # Test validation layer application
    @pytest.mark.asyncio
    async def test_should_apply_layer(self, service, sample_item_data):
        """Test validation layer application criteria"""
        # Test expert validation layer
        should_apply = await service._should_apply_layer(
            ValidationLayer.EXPERT_VALIDATION, 
            sample_item_data
        )
        assert isinstance(should_apply, bool)

        # Test layer with insufficient data
        incomplete_data = {"id": "test", "type": "test"}
        should_apply = await service._should_apply_layer(
            ValidationLayer.COMMUNITY_VALIDATION,
            incomplete_data
        )
        assert isinstance(should_apply, bool)

    # Test expert validation
    @pytest.mark.asyncio
    async def test_validate_expert_approval(self, service, sample_item_data):
        """Test expert validation scoring"""
        result = await service._validate_expert_approval(sample_item_data)

        assert isinstance(result, ValidationScore)
        assert result.layer == ValidationLayer.EXPERT_VALIDATION
        assert isinstance(result.score, float)
        assert 0 <= result.score <= 1
        assert isinstance(result.confidence, float)
        assert 0 <= result.confidence <= 1

    # Test community validation
    @pytest.mark.asyncio
    async def test_validate_community_approval(self, service, sample_item_data):
        """Test community validation scoring"""
        result = await service._validate_community_approval(sample_item_data)

        assert isinstance(result, ValidationScore)
        assert result.layer == ValidationLayer.COMMUNITY_VALIDATION
        assert isinstance(result.score, float)
        assert 0 <= result.score <= 1
        assert isinstance(result.confidence, float)
        assert 0 <= result.confidence <= 1

    # Test historical validation
    @pytest.mark.asyncio
    async def test_validate_historical_performance(self, service, sample_item_data):
        """Test historical performance validation"""
        result = await service._validate_historical_performance(sample_item_data)

        assert isinstance(result, ValidationScore)
        assert result.layer == ValidationLayer.HISTORICAL_VALIDATION
        assert isinstance(result.score, float)
        assert 0 <= result.score <= 1
        assert isinstance(result.confidence, float)
        assert 0 <= result.confidence <= 1

    # Test pattern validation
    @pytest.mark.asyncio
    async def test_validate_pattern_consistency(self, service, sample_item_data):
        """Test pattern consistency validation"""
        result = await service._validate_pattern_consistency(sample_item_data)

        assert isinstance(result, ValidationScore)
        assert result.layer == ValidationLayer.PATTERN_VALIDATION
        assert isinstance(result.score, float)
        assert 0 <= result.score <= 1
        assert isinstance(result.confidence, float)
        assert 0 <= result.confidence <= 1

    # Test cross-platform validation
    @pytest.mark.asyncio
    async def test_validate_cross_platform_compatibility(self, service, sample_item_data):
        """Test cross-platform compatibility validation"""
        result = await service._validate_cross_platform_compatibility(sample_item_data)

        assert isinstance(result, ValidationScore)
        assert result.layer == ValidationLayer.CROSS_PLATFORM_VALIDATION
        assert isinstance(result.score, float)
        assert 0 <= result.score <= 1
        assert isinstance(result.confidence, float)
        assert 0 <= result.confidence <= 1

    # Test version compatibility validation
    @pytest.mark.asyncio
    async def test_validate_version_compatibility(self, service, sample_item_data):
        """Test version compatibility validation"""
        result = await service._validate_version_compatibility(sample_item_data)

        assert isinstance(result, ValidationScore)
        assert result.layer == ValidationLayer.VERSION_COMPATIBILITY
        assert isinstance(result.score, float)
        assert 0 <= result.score <= 1
        assert isinstance(result.confidence, float)
        assert 0 <= result.confidence <= 1

    # Test usage validation
    @pytest.mark.asyncio
    async def test_validate_usage_statistics(self, service, sample_item_data):
        """Test usage statistics validation"""
        result = await service._validate_usage_statistics(sample_item_data)

        assert isinstance(result, ValidationScore)
        assert result.layer == ValidationLayer.USAGE_VALIDATION
        assert isinstance(result.score, float)
        assert 0 <= result.score <= 1
        assert isinstance(result.confidence, float)
        assert 0 <= result.confidence <= 1

    # Test semantic validation
    @pytest.mark.asyncio
    async def test_validate_semantic_consistency(self, service, sample_item_data):
        """Test semantic consistency validation"""
        result = await service._validate_semantic_consistency(sample_item_data)

        assert isinstance(result, ValidationScore)
        assert result.layer == ValidationLayer.SEMANTIC_VALIDATION
        assert isinstance(result.score, float)
        assert 0 <= result.score <= 1
        assert isinstance(result.confidence, float)
        assert 0 <= result.confidence <= 1

    # Test overall confidence calculation
    def test_calculate_overall_confidence(self, service):
        """Test overall confidence calculation"""
        validation_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.9,
                confidence=0.95,
                evidence={},
                metadata={}
            ),
            ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=0.8,
                confidence=0.85,
                evidence={},
                metadata={}
            ),
            ValidationScore(
                layer=ValidationLayer.HISTORICAL_VALIDATION,
                score=0.85,
                confidence=0.9,
                evidence={},
                metadata={}
            )
        ]

        overall = service._calculate_overall_confidence(validation_scores)

        assert isinstance(overall, float)
        assert 0 <= overall <= 1
        # Should be weighted by confidence
        assert overall > 0.8  # With high scores, should be high

    # Test risk factor identification
    def test_identify_risk_factors(self, service):
        """Test risk factor identification"""
        validation_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.3,  # Low score
                confidence=0.9,
                evidence={},
                metadata={}
            ),
            ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=0.2,  # Very low score
                confidence=0.8,
                evidence={},
                metadata={}
            ),
            ValidationScore(
                layer=ValidationLayer.HISTORICAL_VALIDATION,
                score=0.8,  # High score
                confidence=0.9,
                evidence={},
                metadata={}
            )
        ]

        risks = service._identify_risk_factors(validation_scores)

        assert isinstance(risks, list)
        assert len(risks) > 0
        assert all(isinstance(risk, str) for risk in risks)

    # Test confidence factor identification
    def test_identify_confidence_factors(self, service):
        """Test confidence factor identification"""
        validation_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.9,  # High score
                confidence=0.95,
                evidence={},
                metadata={}
            ),
            ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=0.8,  # High score
                confidence=0.85,
                evidence={},
                metadata={}
            ),
            ValidationScore(
                layer=ValidationLayer.HISTORICAL_VALIDATION,
                score=0.85,  # High score
                confidence=0.9,
                evidence={},
                metadata={}
            )
        ]

        factors = service._identify_confidence_factors(validation_scores)

        assert isinstance(factors, list)
        assert len(factors) > 0
        assert all(isinstance(factor, str) for factor in factors)

    # Test feedback impact calculation
    def test_calculate_feedback_impact(self, service):
        """Test feedback impact calculation"""
        feedback_data = {
            "actual_outcome": "success",
            "predicted_confidence": 0.8,
            "performance_metrics": {"accuracy": 0.9, "conversion_time": 120}
        }

        impact = service._calculate_feedback_impact(feedback_data)

        assert isinstance(impact, dict)
        # Should contain impacts for different validation layers
        for layer in ValidationLayer:
            assert layer.value in impact
            assert isinstance(impact[layer.value], float)

    # Test feedback score application
    def test_apply_feedback_to_score(self, service):
        """Test feedback score application"""
        current_score = 0.8
        feedback_impact = {
            "expert_validation": 0.1,  # Increase
            "community_validation": -0.05  # Decrease
        }
        layer_confidence = {
            "expert_validation": 0.9,
            "community_validation": 0.8
        }

        new_score = service._apply_feedback_to_score(
            current_score, feedback_impact, layer_confidence
        )

        assert isinstance(new_score, float)
        assert 0 <= new_score <= 1
        # Should reflect the weighted impact
        assert new_score > current_score  # Net positive impact

    # Test batch result analysis
    def test_analyze_batch_results(self, service):
        """Test batch result analysis"""
        batch_results = {
            "item_1": {"confidence": 0.9, "validation_layers": ["expert", "community"]},
            "item_2": {"confidence": 0.7, "validation_layers": ["expert", "community"]},
            "item_3": {"confidence": 0.8, "validation_layers": ["expert", "community"]},
            "item_4": {"confidence": 0.6, "validation_layers": ["expert", "community"]},
            "item_5": {"confidence": 0.85, "validation_layers": ["expert", "community"]}
        }

        analysis = service._analyze_batch_results(batch_results)

        assert isinstance(analysis, dict)
        assert "average_confidence" in analysis
        assert "confidence_distribution" in analysis
        assert "high_confidence_count" in analysis
        assert "low_confidence_count" in analysis

    # Test batch pattern analysis
    @pytest.mark.asyncio
    async def test_analyze_batch_patterns(self, service):
        """Test batch pattern analysis"""
        batch_results = {
            "item_1": {"item_type": "knowledge_relationship", "confidence": 0.9},
            "item_2": {"item_type": "knowledge_relationship", "confidence": 0.7},
            "item_3": {"item_type": "conversion_pattern", "confidence": 0.8},
            "item_4": {"item_type": "conversion_pattern", "confidence": 0.85},
            "item_5": {"item_type": "knowledge_node", "confidence": 0.6}
        }

        patterns = await service._analyze_batch_patterns(batch_results)

        assert isinstance(patterns, dict)
        assert "type_distribution" in patterns
        assert "average_confidence_by_type" in patterns
        assert "most_common_type" in patterns

    # Test confidence distribution calculation
    def test_calculate_confidence_distribution(self, service):
        """Test confidence distribution calculation"""
        scores = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]

        distribution = service._calculate_confidence_distribution(scores)

        assert isinstance(distribution, dict)
        assert "high" in distribution  # > 0.8
        assert "medium" in distribution  # 0.5-0.8
        assert "low" in distribution  # < 0.5
        assert distribution["high"] == 1  # Only 0.9
        assert distribution["medium"] == 4  # 0.8, 0.7, 0.6, 0.5
        assert distribution["low"] == 4  # 0.4, 0.3, 0.2, 0.1

    # Test confidence trend calculation
    def test_calculate_confidence_trend(self, service):
        """Test confidence trend calculation"""
        assessments = [
            {"timestamp": "2024-01-01", "confidence": 0.7},
            {"timestamp": "2024-01-02", "confidence": 0.75},
            {"timestamp": "2024-01-03", "confidence": 0.8},
            {"timestamp": "2024-01-04", "confidence": 0.85},
            {"timestamp": "2024-01-05", "confidence": 0.9}
        ]

        trend = service._calculate_confidence_trend(assessments)

        assert isinstance(trend, dict)
        assert "direction" in trend
        assert "slope" in trend
        assert "change_percentage" in trend
        assert trend["direction"] == "increasing"
        assert trend["slope"] > 0

    # Test caching
    def test_cache_assessment(self, service):
        """Test assessment caching"""
        assessment = ConfidenceAssessment(
            overall_confidence=0.85,
            validation_scores=[
                ValidationScore(
                    layer=ValidationLayer.EXPERT_VALIDATION,
                    score=0.9,
                    confidence=0.95,
                    evidence={},
                    metadata={}
                )
            ]
        )

        # Test caching
        service._cache_assessment("knowledge_relationship", "item_1", assessment)

        assert "knowledge_relationship" in service.confidence_cache
        assert "item_1" in service.confidence_cache["knowledge_relationship"]
        cached = service.confidence_cache["knowledge_relationship"]["item_1"]
        assert cached.overall_confidence == 0.85

    # Test error handling
    @pytest.mark.asyncio
    async def test_assess_confidence_error(self, service, mock_db_session):
        """Test error handling in confidence assessment"""
        # Mock data retrieval failure
        with patch.object(service, '_get_item_data') as mock_get_data:
            mock_get_data.side_effect = Exception("Data retrieval failed")

            with pytest.raises(Exception):
                await service.assess_confidence(
                    item_type="knowledge_relationship",
                    item_id="non_existent",
                    db=mock_db_session
                )


class TestValidationLayer:
    """Test ValidationLayer enum"""

    def test_validation_layer_values(self):
        """Test validation layer enum values"""
        assert ValidationLayer.EXPERT_VALIDATION.value == "expert_validation"
        assert ValidationLayer.COMMUNITY_VALIDATION.value == "community_validation"
        assert ValidationLayer.HISTORICAL_VALIDATION.value == "historical_validation"
        assert ValidationLayer.PATTERN_VALIDATION.value == "pattern_validation"
        assert ValidationLayer.CROSS_PLATFORM_VALIDATION.value == "cross_platform_validation"
        assert ValidationLayer.VERSION_COMPATIBILITY.value == "version_compatibility"
        assert ValidationLayer.USAGE_VALIDATION.value == "usage_validation"
        assert ValidationLayer.SEMANTIC_VALIDATION.value == "semantic_validation"


class TestValidationScore:
    """Test ValidationScore dataclass"""

    def test_validation_score_creation(self):
        """Test validation score creation"""
        score = ValidationScore(
            layer=ValidationLayer.EXPERT_VALIDATION,
            score=0.9,
            confidence=0.95,
            evidence={"expert_approved": True},
            metadata={"validator": "expert_1"}
        )

        assert score.layer == ValidationLayer.EXPERT_VALIDATION
        assert score.score == 0.9
        assert score.confidence == 0.95
        assert score.evidence == {"expert_approved": True}
        assert score.metadata == {"validator": "expert_1"}


class TestConfidenceAssessment:
    """Test ConfidenceAssessment dataclass"""

    def test_confidence_assessment_creation(self):
        """Test confidence assessment creation"""
        validation_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.9,
                confidence=0.95,
                evidence={},
                metadata={}
            )
        ]

        assessment = ConfidenceAssessment(
            overall_confidence=0.85,
            validation_scores=validation_scores
        )

        assert assessment.overall_confidence == 0.85
        assert len(assessment.validation_scores) == 1
        assert assessment.validation_scores[0].layer == ValidationLayer.EXPERT_VALIDATION


if __name__ == "__main__":
    pytest.main([__file__])
