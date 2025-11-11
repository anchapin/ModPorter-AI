"""
Tests for automated_confidence_scoring.py service.
Focus on covering the confidence scoring and validation logic.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

# Import the service
from services.automated_confidence_scoring import (
    AutomatedConfidenceScorer,
    ValidationLayer,
    ValidationScore,
    ConfidenceAssessment,
    SemanticValidator,
    PatternValidator,
    HistoricalValidator,
    ExpertValidator,
    CommunityValidator
)


class TestValidationLayer:
    """Test the ValidationLayer enum."""
    
    def test_validation_layer_values(self):
        """Test all enum values are present."""
        assert ValidationLayer.EXPERT_VALIDATION.value == "expert_validation"
        assert ValidationLayer.COMMUNITY_VALIDATION.value == "community_validation"
        assert ValidationLayer.HISTORICAL_VALIDATION.value == "historical_validation"
        assert ValidationLayer.PATTERN_VALIDATION.value == "pattern_validation"
        assert ValidationLayer.CROSS_PLATFORM_VALIDATION.value == "cross_platform_validation"
        assert ValidationLayer.VERSION_COMPATIBILITY.value == "version_compatibility"
        assert ValidationLayer.USAGE_VALIDATION.value == "usage_validation"
        assert ValidationLayer.SEMANTIC_VALIDATION.value == "semantic_validation"


class TestValidationScore:
    """Test the ValidationScore dataclass."""
    
    def test_validation_score_creation(self):
        """Test creating ValidationScore instance."""
        score = ValidationScore(
            layer=ValidationLayer.EXPERT_VALIDATION,
            score=0.85,
            confidence=0.9,
            evidence={"source": "expert_1"},
            metadata={"validation_date": "2024-01-01"}
        )
        
        assert score.layer == ValidationLayer.EXPERT_VALIDATION
        assert score.score == 0.85
        assert score.confidence == 0.9
        assert score.evidence["source"] == "expert_1"
        assert score.metadata["validation_date"] == "2024-01-01"


class TestConfidenceAssessment:
    """Test the ConfidenceAssessment dataclass."""
    
    def test_confidence_assessment_creation(self):
        """Test creating ConfidenceAssessment instance."""
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
            )
        ]
        
        assessment = ConfidenceAssessment(
            overall_confidence=0.87,
            validation_scores=validation_scores
        )
        
        assert assessment.overall_confidence == 0.87
        assert len(assessment.validation_scores) == 2
        assert assessment.validation_scores[0].layer == ValidationLayer.EXPERT_VALIDATION


class TestSemanticValidator:
    """Test the SemanticValidator class."""
    
    def test_semantic_validator_initialization(self):
        """Test SemanticValidator initialization."""
        validator = SemanticValidator()
        assert validator.similarity_threshold == 0.7
        assert validator.confidence_weights is not None
        
    def test_validate_semantic_similarity_high(self):
        """Test validation with high semantic similarity."""
        validator = SemanticValidator()
        
        result = validator.validate_semantic_similarity(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            context="Game object with behavior"
        )
        
        assert result.score >= 0.7
        assert 0 <= result.confidence <= 1
        assert "similarity_score" in result.evidence
        
    def test_validate_semantic_similarity_low(self):
        """Test validation with low semantic similarity."""
        validator = SemanticValidator()
        
        result = validator.validate_semantic_similarity(
            java_concept="Entity",
            bedrock_concept="Block State",
            context="Completely different concept"
        )
        
        assert result.score < 0.7
        assert 0 <= result.confidence <= 1
        
    def test_validate_concept_mapping_valid(self):
        """Test validation of valid concept mapping."""
        validator = SemanticValidator()
        
        result = validator.validate_concept_mapping(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            pattern_type="entity_mapping"
        )
        
        assert result.score >= 0.5
        assert 0 <= result.confidence <= 1
        assert "pattern_match" in result.evidence
        
    def test_validate_concept_mapping_invalid(self):
        """Test validation of invalid concept mapping."""
        validator = SemanticValidator()
        
        result = validator.validate_concept_mapping(
            java_concept="Entity",
            bedrock_concept="Biome",
            pattern_type="invalid_mapping"
        )
        
        assert result.score < 0.5
        assert 0 <= result.confidence <= 1


class TestPatternValidator:
    """Test the PatternValidator class."""
    
    def test_pattern_validator_initialization(self):
        """Test PatternValidator initialization."""
        validator = PatternValidator()
        assert validator.known_patterns is not None
        assert validator.pattern_confidence is not None
        
    def test_validate_pattern_recognition_valid(self):
        """Test validation with recognized pattern."""
        validator = PatternValidator()
        
        result = validator.validate_pattern_recognition(
            java_pattern="entity_class_structure",
            bedrock_pattern="entity_definition",
            pattern_type="entity_mapping"
        )
        
        assert result.score >= 0.6
        assert 0 <= result.confidence <= 1
        assert "pattern_type" in result.evidence
        
    def test_validate_pattern_recognition_invalid(self):
        """Test validation with unrecognized pattern."""
        validator = PatternValidator()
        
        result = validator.validate_pattern_recognition(
            java_pattern="unknown_pattern",
            bedrock_pattern="another_unknown",
            pattern_type="invalid_type"
        )
        
        assert result.score < 0.5
        assert 0 <= result.confidence <= 1
        
    def test_validate_structure_consistency(self):
        """Test validation of structure consistency."""
        validator = PatternValidator()
        
        java_structure = {
            "class": "Entity",
            "extends": "LivingEntity",
            "methods": ["update", "render"]
        }
        
        bedrock_structure = {
            "type": "entity",
            "components": ["minecraft:movement", "minecraft:behavior"],
            "events": ["minecraft:entity_spawned"]
        }
        
        result = validator.validate_structure_consistency(
            java_structure=java_structure,
            bedrock_structure=bedrock_structure
        )
        
        assert 0 <= result.score <= 1
        assert 0 <= result.confidence <= 1
        assert "structure_match" in result.evidence


class TestHistoricalValidator:
    """Test the HistoricalValidator class."""
    
    def test_historical_validator_initialization(self):
        """Test HistoricalValidator initialization."""
        validator = HistoricalValidator()
        assert validator.success_history is not None
        assert validator.time_decay_factor > 0
        
    def test_validate_historical_success(self):
        """Test validation with successful history."""
        validator = HistoricalValidator()
        
        # Mock successful conversions
        validator.success_history["entity_mapping"] = {
            "total_conversions": 100,
            "successful_conversions": 85,
            "average_confidence": 0.82
        }
        
        result = validator.validate_historical_success(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            pattern_type="entity_mapping"
        )
        
        assert result.score >= 0.7
        assert 0 <= result.confidence <= 1
        assert "success_rate" in result.evidence
        
    def test_validate_historical_failure(self):
        """Test validation with poor history."""
        validator = HistoricalValidator()
        
        # Mock failed conversions
        validator.success_history["entity_mapping"] = {
            "total_conversions": 100,
            "successful_conversions": 20,
            "average_confidence": 0.3
        }
        
        result = validator.validate_historical_success(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            pattern_type="entity_mapping"
        )
        
        assert result.score < 0.5
        assert 0 <= result.confidence <= 1
        
    def test_validate_trend_analysis(self):
        """Test trend analysis validation."""
        validator = HistoricalValidator()
        
        # Mock trend data
        recent_data = [
            {"date": datetime.now() - timedelta(days=5), "success": True},
            {"date": datetime.now() - timedelta(days=3), "success": True},
            {"date": datetime.now() - timedelta(days=1), "success": True}
        ]
        
        validator.success_history["entity_mapping"] = {
            "recent_conversions": recent_data,
            "success_rate": 0.8
        }
        
        result = validator.validate_trend_analysis(
            java_concept="Entity",
            pattern_type="entity_mapping"
        )
        
        assert 0 <= result.score <= 1
        assert 0 <= result.confidence <= 1
        assert "trend_direction" in result.evidence


class TestExpertValidator:
    """Test the ExpertValidator class."""
    
    def test_expert_validator_initialization(self):
        """Test ExpertValidator initialization."""
        validator = ExpertValidator()
        assert validator.expert_ratings is not None
        assert validator.expert_weights is not None
        
    def test_validate_expert_consensus_high(self):
        """Test validation with high expert consensus."""
        validator = ExpertValidator()
        
        # Mock high consensus
        validator.expert_ratings["entity_mapping"] = {
            "expert_1": {"rating": 0.9, "confidence": 0.95},
            "expert_2": {"rating": 0.85, "confidence": 0.9},
            "expert_3": {"rating": 0.88, "confidence": 0.92}
        }
        
        result = validator.validate_expert_consensus(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            pattern_type="entity_mapping"
        )
        
        assert result.score >= 0.8
        assert 0 <= result.confidence <= 1
        assert "consensus_level" in result.evidence
        
    def test_validate_expert_consensus_low(self):
        """Test validation with low expert consensus."""
        validator = ExpertValidator()
        
        # Mock low consensus
        validator.expert_ratings["entity_mapping"] = {
            "expert_1": {"rating": 0.9, "confidence": 0.95},
            "expert_2": {"rating": 0.3, "confidence": 0.8},
            "expert_3": {"rating": 0.4, "confidence": 0.7}
        }
        
        result = validator.validate_expert_consensus(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            pattern_type="entity_mapping"
        )
        
        assert result.score < 0.6
        assert 0 <= result.confidence <= 1
        assert "consensus_level" in result.evidence
        
    def test_validate_expertise_level(self):
        """Test validation based on expertise level."""
        validator = ExpertValidator()
        
        # Mock expertise levels
        validator.expert_weights = {
            "entity_expert": 1.0,
            "block_expert": 0.8,
            "general_expert": 0.5
        }
        
        result = validator.validate_expertise_level(
            java_concept="Entity",
            pattern_type="entity_mapping",
            expert_type="entity_expert"
        )
        
        assert result.score >= 0.5
        assert 0 <= result.confidence <= 1
        assert "expertise_weight" in result.evidence


class TestCommunityValidator:
    """Test the CommunityValidator class."""
    
    def test_community_validator_initialization(self):
        """Test CommunityValidator initialization."""
        validator = CommunityValidator()
        assert validator.community_ratings is not None
        assert validator.min_ratings_threshold > 0
        
    def test_validate_community_ratings_high(self):
        """Test validation with high community ratings."""
        validator = CommunityValidator()
        
        # Mock high community ratings
        validator.community_ratings["entity_mapping"] = {
            "total_ratings": 150,
            "average_rating": 4.2,
            "recent_ratings": [4, 5, 4, 5, 4]
        }
        
        result = validator.validate_community_ratings(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            pattern_type="entity_mapping"
        )
        
        assert result.score >= 0.7
        assert 0 <= result.confidence <= 1
        assert "community_score" in result.evidence
        
    def test_validate_community_ratings_low(self):
        """Test validation with low community ratings."""
        validator = CommunityValidator()
        
        # Mock low community ratings
        validator.community_ratings["entity_mapping"] = {
            "total_ratings": 50,
            "average_rating": 2.1,
            "recent_ratings": [2, 2, 3, 1, 2]
        }
        
        result = validator.validate_community_ratings(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            pattern_type="entity_mapping"
        )
        
        assert result.score < 0.5
        assert 0 <= result.confidence <= 1
        
    def test_validate_usage_frequency(self):
        """Test validation based on usage frequency."""
        validator = CommunityValidator()
        
        # Mock usage data
        validator.community_ratings["entity_mapping"] = {
            "usage_count": 500,
            "unique_users": 120,
            "success_uses": 425
        }
        
        result = validator.validate_usage_frequency(
            java_concept="Entity",
            pattern_type="entity_mapping"
        )
        
        assert 0 <= result.score <= 1
        assert 0 <= result.confidence <= 1
        assert "usage_stats" in result.evidence


class TestAutomatedConfidenceScorer:
    """Test the main AutomatedConfidenceScorer class."""
    
    @pytest.fixture
    def scorer(self):
        """Create a scorer instance."""
        return AutomatedConfidenceScorer()
        
    def test_scorer_initialization(self, scorer):
        """Test scorer initialization."""
        assert scorer.semantic_validator is not None
        assert scorer.pattern_validator is not None
        assert scorer.historical_validator is not None
        assert scorer.expert_validator is not None
        assert scorer.community_validator is not None
        
    def test_calculate_overall_confidence(self, scorer):
        """Test overall confidence calculation."""
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
                layer=ValidationLayer.SEMANTIC_VALIDATION,
                score=0.85,
                confidence=0.9,
                evidence={},
                metadata={}
            )
        ]
        
        overall = scorer.calculate_overall_confidence(validation_scores)
        
        assert 0 <= overall <= 1
        # Should be weighted average
        expected_approx = (0.9*0.95 + 0.8*0.85 + 0.85*0.9) / 3
        assert abs(overall - expected_approx) < 0.1
        
    @pytest.mark.asyncio
    async def test_score_conversion_full_validation(self, scorer):
        """Test full conversion scoring with all validations."""
        result = await scorer.score_conversion(
            java_concept="Entity",
            bedrock_concept="Entity Definition",
            pattern_type="entity_mapping",
            minecraft_version="1.20.1"
        )
        
        assert isinstance(result, ConfidenceAssessment)
        assert 0 <= result.overall_confidence <= 1
        assert len(result.validation_scores) > 0
        
        # Check all validation layers are present
        layer_types = [vs.layer for vs in result.validation_scores]
        assert ValidationLayer.SEMANTIC_VALIDATION in layer_types
        assert ValidationLayer.PATTERN_VALIDATION in layer_types
        
    @pytest.mark.asyncio
    async def test_score_conversion_minimal_validation(self, scorer):
        """Test conversion scoring with minimal data."""
        result = await scorer.score_conversion(
            java_concept="Entity",
            bedrock_concept="Entity Definition"
        )
        
        assert isinstance(result, ConfidenceAssessment)
        assert 0 <= result.overall_confidence <= 1
        assert len(result.validation_scores) > 0
        
    @pytest.mark.asyncio
    async def test_batch_score_conversions(self, scorer):
        """Test batch scoring of multiple conversions."""
        conversions = [
            {
                "java_concept": "Entity",
                "bedrock_concept": "Entity Definition",
                "pattern_type": "entity_mapping"
            },
            {
                "java_concept": "Block",
                "bedrock_concept": "Block Definition",
                "pattern_type": "block_mapping"
            }
        ]
        
        results = await scorer.batch_score_conversions(conversions)
        
        assert len(results) == 2
        for result in results:
            assert isinstance(result, ConfidenceAssessment)
            assert 0 <= result.overall_confidence <= 1
            
    def test_update_confidence_with_feedback(self, scorer):
        """Test updating confidence scores with feedback."""
        # Initial assessment
        validation_scores = [
            ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=0.7,
                confidence=0.8,
                evidence={},
                metadata={}
            )
        ]
        
        # Update with positive feedback
        feedback = {
            "success": True,
            "actual_confidence": 0.9,
            "validation_layers": ["community_validation"]
        }
        
        updated_scores = scorer.update_confidence_with_feedback(
            validation_scores, feedback
        )
        
        # Scores should be adjusted based on feedback
        assert len(updated_scores) > 0
        
    def test_get_confidence_breakdown(self, scorer):
        """Test getting detailed confidence breakdown."""
        validation_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.9,
                confidence=0.95,
                evidence={"source": "expert_1"},
                metadata={"date": "2024-01-01"}
            ),
            ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=0.8,
                confidence=0.85,
                evidence={"ratings_count": 100},
                metadata={"last_updated": "2024-01-02"}
            )
        ]
        
        breakdown = scorer.get_confidence_breakdown(validation_scores)
        
        assert "overall_confidence" in breakdown
        assert "validation_layers" in breakdown
        assert "layer_details" in breakdown
        assert len(breakdown["validation_layers"]) == 2
