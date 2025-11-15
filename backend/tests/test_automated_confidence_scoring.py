"""
Fixed tests for automated_confidence_scoring.py

This test module provides comprehensive coverage of automated confidence scoring
service functionality, focusing on core validation methods and business logic.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.automated_confidence_scoring import (
    AutomatedConfidenceScoringService,
    ValidationLayer,
    ValidationScore,
    ConfidenceAssessment
)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def confidence_service():
    """Create a confidence scoring service instance with mocked dependencies."""
    with patch('src.services.automated_confidence_scoring.logger'):
        service = AutomatedConfidenceScoringService()
        return service


class TestAutomatedConfidenceScoringService:
    """Test cases for AutomatedConfidenceScoringService class."""

    class TestInitialization:
        """Test cases for service initialization."""

        def test_init(self, confidence_service):
            """Test service initialization."""
            # Verify layer weights
            assert confidence_service.layer_weights[ValidationLayer.EXPERT_VALIDATION] == 0.25
            assert confidence_service.layer_weights[ValidationLayer.COMMUNITY_VALIDATION] == 0.20
            assert confidence_service.layer_weights[ValidationLayer.HISTORICAL_VALIDATION] == 0.15
            assert confidence_service.layer_weights[ValidationLayer.PATTERN_VALIDATION] == 0.15
            assert confidence_service.layer_weights[ValidationLayer.CROSS_PLATFORM_VALIDATION] == 0.10
            assert confidence_service.layer_weights[ValidationLayer.VERSION_COMPATIBILITY] == 0.05
            assert confidence_service.layer_weights[ValidationLayer.USAGE_VALIDATION] == 0.05
            assert confidence_service.layer_weights[ValidationLayer.SEMANTIC_VALIDATION] == 0.05

            # Verify cache and history are initialized
            assert hasattr(confidence_service, 'validation_cache')
            assert hasattr(confidence_service, 'scoring_history')
            assert hasattr(confidence_service, 'feedback_history')

    class TestConfidenceAssessment:
        """Test cases for confidence assessment methods."""

        @pytest.mark.asyncio
        async def test_assess_confidence(self, confidence_service, mock_db_session):
            """Test confidence assessment for a knowledge graph node."""
            # Mock the helper methods
            confidence_service._get_item_data = AsyncMock(return_value={
                "platform": "java",
                "usage_count": 50,
                "created_at": datetime.utcnow() - timedelta(days=30)
            })

            # Mock validation layer methods
            confidence_service._validate_expert_approval = AsyncMock(
                return_value=ValidationScore(
                    layer=ValidationLayer.EXPERT_VALIDATION,
                    score=0.8,
                    confidence=0.9,
                    evidence={"expert_review": True},
                    metadata={"validation_method": "expert_check"}
                )
            )
            confidence_service._validate_community_approval = AsyncMock(
                return_value=ValidationScore(
                    layer=ValidationLayer.COMMUNITY_VALIDATION,
                    score=0.7,
                    confidence=0.8,
                    evidence={"community_votes": 10},
                    metadata={"validation_method": "community_check"}
                )
            )
            confidence_service._validate_historical_performance = AsyncMock(
                return_value=ValidationScore(
                    layer=ValidationLayer.HISTORICAL_VALIDATION,
                    score=0.6,
                    confidence=0.7,
                    evidence={"usage_history": "positive"},
                    metadata={"validation_method": "historical_check"}
                )
            )
            confidence_service._validate_pattern_consistency = AsyncMock(
                return_value=ValidationScore(
                    layer=ValidationLayer.PATTERN_VALIDATION,
                    score=0.75,
                    confidence=0.8,
                    evidence={"pattern_match": True},
                    metadata={"validation_method": "pattern_check"}
                )
            )
            confidence_service._validate_cross_platform_compatibility = AsyncMock(
                return_value=ValidationScore(
                    layer=ValidationLayer.CROSS_PLATFORM_VALIDATION,
                    score=0.8,
                    confidence=0.9,
                    evidence={"platform": "both"},
                    metadata={"validation_method": "platform_check"}
                )
            )
            confidence_service._validate_version_compatibility = AsyncMock(
                return_value=ValidationScore(
                    layer=ValidationLayer.VERSION_COMPATIBILITY,
                    score=0.85,
                    confidence=0.9,
                    evidence={"minecraft_version": "latest"},
                    metadata={"validation_method": "version_check"}
                )
            )
            confidence_service._validate_usage_statistics = AsyncMock(
                return_value=ValidationScore(
                    layer=ValidationLayer.USAGE_VALIDATION,
                    score=0.7,
                    confidence=0.8,
                    evidence={"usage_count": 50},
                    metadata={"validation_method": "usage_stats"}
                )
            )
            confidence_service._validate_semantic_consistency = AsyncMock(
                return_value=ValidationScore(
                    layer=ValidationLayer.SEMANTIC_VALIDATION,
                    score=0.75,
                    confidence=0.85,
                    evidence={"description_match": True},
                    metadata={"validation_method": "semantic_check"}
                )
            )

            # Mock the recommendation generation
            confidence_service._generate_recommendations = AsyncMock(return_value=[
                "Test recommendation 1",
                "Test recommendation 2"
            ])

            # Call the method
            assessment = await confidence_service.assess_confidence(
                item_type="node",
                item_id="test_item_id",
                context_data={"test": True},
                db=mock_db_session
            )

            # Verify the result
            assert isinstance(assessment, ConfidenceAssessment)
            assert 0 <= assessment.overall_confidence <= 1
            assert len(assessment.validation_scores) == 8  # All validation layers
            assert len(assessment.risk_factors) >= 0
            assert len(assessment.confidence_factors) >= 0
            assert len(assessment.recommendations) == 2
            assert assessment.assessment_metadata["item_type"] == "node"
            assert assessment.assessment_metadata["item_id"] == "test_item_id"

            # Verify that assessment was cached
            assert "node:test_item_id" in confidence_service.validation_cache

            # Verify that assessment was tracked in history
            assert len(confidence_service.scoring_history) == 1
            assert confidence_service.scoring_history[0]["item_type"] == "node"
            assert confidence_service.scoring_history[0]["item_id"] == "test_item_id"

        @pytest.mark.asyncio
        async def test_assess_confidence_item_not_found(self, confidence_service, mock_db_session):
            """Test confidence assessment when item is not found."""
            # Mock the helper method to return None
            confidence_service._get_item_data = AsyncMock(return_value=None)

            # Call the method and verify default assessment is returned
            assessment = await confidence_service.assess_confidence(
                item_type="node",
                item_id="nonexistent_item",
                db=mock_db_session
            )

            # Verify default assessment
            assert isinstance(assessment, ConfidenceAssessment)
            assert assessment.overall_confidence == 0.5
            assert len(assessment.validation_scores) == 0
            assert "Item not found" in assessment.risk_factors[0]
            assert assessment.recommendations == ["Retry assessment with valid data"]

    class TestHelperMethods:
        """Test cases for helper methods."""

        def test_calculate_overall_confidence(self, confidence_service):
            """Test calculation of overall confidence from validation scores."""
            # Create validation scores with different weights
            validation_scores = [
                ValidationScore(
                    layer=ValidationLayer.EXPERT_VALIDATION,  # weight: 0.25
                    score=0.8,
                    confidence=0.9,
                    evidence={"expert_review": True},
                    metadata={}
                ),
                ValidationScore(
                    layer=ValidationLayer.COMMUNITY_VALIDATION,  # weight: 0.20
                    score=0.6,
                    confidence=0.7,
                    evidence={"community_votes": 10},
                    metadata={}
                ),
                ValidationScore(
                    layer=ValidationLayer.HISTORICAL_VALIDATION,  # weight: 0.15
                    score=0.7,
                    confidence=0.8,
                    evidence={"usage_count": 50},
                    metadata={}
                )
            ]

            # Calculate expected overall confidence
            # (0.8*0.9*0.25 + 0.6*0.7*0.2 + 0.7*0.8*0.15) / (0.25 + 0.2 + 0.15)
            # = (0.18 + 0.084 + 0.084) / 0.6 = 0.348 / 0.6 = 0.58
            expected_confidence = (0.8 * 0.9 * 0.25 + 0.6 * 0.7 * 0.2 + 0.7 * 0.8 * 0.15) / (0.25 + 0.2 + 0.15)

            # Call the method
            overall_confidence = confidence_service._calculate_overall_confidence(validation_scores)

            # Verify the result
            assert abs(overall_confidence - expected_confidence) < 0.01

        def test_identify_risk_factors(self, confidence_service):
            """Test identification of risk factors from validation scores."""
            # Create validation scores with low confidence
            validation_scores = [
                ValidationScore(
                    layer=ValidationLayer.EXPERT_VALIDATION,
                    score=0.3,  # Low score
                    confidence=0.8,
                    evidence={"expert_review": False},
                    metadata={}
                ),
                ValidationScore(
                    layer=ValidationLayer.VERSION_COMPATIBILITY,
                    score=0.2,  # Low score
                    confidence=0.9,
                    evidence={"version_mismatch": True},
                    metadata={}
                )
            ]

            # Call the method
            risk_factors = confidence_service._identify_risk_factors(validation_scores)

            # Verify risk factors are identified
            assert len(risk_factors) >= 2  # At least one for each low score
            assert any("expert" in factor.lower() for factor in risk_factors)
            assert any("version" in factor.lower() for factor in risk_factors)

        def test_identify_confidence_factors(self, confidence_service):
            """Test identification of confidence factors from validation scores."""
            # Create validation scores with high confidence
            validation_scores = [
                ValidationScore(
                    layer=ValidationLayer.EXPERT_VALIDATION,
                    score=0.9,  # High score
                    confidence=0.8,
                    evidence={"expert_review": True},
                    metadata={}
                ),
                ValidationScore(
                    layer=ValidationLayer.COMMUNITY_VALIDATION,
                    score=0.8,  # High score
                    confidence=0.9,
                    evidence={"community_votes": 100},
                    metadata={}
                )
            ]

            # Call the method
            confidence_factors = confidence_service._identify_confidence_factors(validation_scores)

            # Verify confidence factors are identified
            assert len(confidence_factors) >= 2  # At least one for each high score
            assert any("expert" in factor.lower() for factor in confidence_factors)
            assert any("community" in factor.lower() for factor in confidence_factors)

        def test_calculate_confidence_distribution(self, confidence_service):
            """Test calculation of confidence distribution."""
            # Create a list of confidence scores
            confidence_scores = [0.2, 0.3, 0.5, 0.7, 0.8, 0.9]

            # Call the method
            distribution = confidence_service._calculate_confidence_distribution(confidence_scores)

            # Verify distribution
            assert "very_low (0.0-0.2)" in distribution
            assert "low (0.2-0.4)" in distribution
            assert "medium (0.4-0.6)" in distribution
            assert "high (0.6-0.8)" in distribution
            assert "very_high (0.8-1.0)" in distribution
            assert distribution["very_low (0.0-0.2)"] == 1/6  # 0.2 is very low (0.0-0.2)
            assert distribution["low (0.2-0.4)"] == 1/6     # 0.3 is low (0.2-0.4)
            assert distribution["medium (0.4-0.6)"] == 1/6   # 0.5 is medium (0.4-0.6)
            assert distribution["high (0.6-0.8)"] == 1/6     # 0.7 is high (0.6-0.8)
            assert distribution["very_high (0.8-1.0)"] == 2/6 # 0.8 and 0.9 are very high (0.8-1.0)

        def test_cache_assessment(self, confidence_service):
            """Test caching of assessments."""
            # Create a test assessment
            assessment = ConfidenceAssessment(
                overall_confidence=0.8,
                validation_scores=[],
                risk_factors=[],
                confidence_factors=[],
                recommendations=[],
                assessment_metadata={}
            )

            # Call the method
            confidence_service._cache_assessment("node", "test_item", assessment)

            # Verify the assessment was cached
            assert "node:test_item" in confidence_service.validation_cache
            # The assessment is wrapped in a dict with timestamp
            assert "assessment" in confidence_service.validation_cache["node:test_item"]
            assert confidence_service.validation_cache["node:test_item"]["assessment"] == assessment

        def test_calculate_feedback_impact(self, confidence_service):
            """Test calculation of feedback impact."""
            # Test positive feedback
            positive_feedback = {"success": True, "user_rating": 5}
            positive_impact = confidence_service._calculate_feedback_impact(positive_feedback)

            # Verify positive impact on historical validation
            assert positive_impact[ValidationLayer.HISTORICAL_VALIDATION] > 0
            assert positive_impact[ValidationLayer.USAGE_VALIDATION] > 0

            # Test negative feedback
            negative_feedback = {"success": False, "user_rating": 1}
            negative_impact = confidence_service._calculate_feedback_impact(negative_feedback)

            # Verify negative impact on historical validation
            assert negative_impact[ValidationLayer.HISTORICAL_VALIDATION] < 0
            assert negative_impact[ValidationLayer.USAGE_VALIDATION] < 0

            # Test expert feedback
            expert_positive_feedback = {"from_expert": True, "value": "positive"}
            expert_impact = confidence_service._calculate_feedback_impact(expert_positive_feedback)
            assert expert_impact[ValidationLayer.EXPERT_VALIDATION] > 0

            expert_negative_feedback = {"from_expert": True, "value": "negative"}
            expert_negative_impact = confidence_service._calculate_feedback_impact(expert_negative_feedback)
            assert expert_negative_impact[ValidationLayer.EXPERT_VALIDATION] < 0

        def test_apply_feedback_to_score(self, confidence_service):
            """Test applying feedback impact to a validation score."""
            # Create a test score
            original_score = ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.7,
                confidence=0.8,
                evidence={"expert_review": True},
                metadata={}
            )

            # Test positive feedback impact
            positive_impact = {ValidationLayer.EXPERT_VALIDATION: 0.2}
            updated_score = confidence_service._apply_feedback_to_score(original_score, positive_impact)

            # Verify the score was increased
            assert updated_score.score > original_score.score
            assert updated_score.confidence > original_score.confidence
            assert "feedback_adjustment" in updated_score.metadata
            assert updated_score.metadata["feedback_adjustment"] == 0.2

            # Test negative feedback impact
            negative_impact = {ValidationLayer.EXPERT_VALIDATION: -0.3}
            updated_score_negative = confidence_service._apply_feedback_to_score(original_score, negative_impact)

            # Verify the score was decreased but not below 0
            assert 0 <= updated_score_negative.score <= original_score.score
            assert "feedback_adjustment" in updated_score_negative.metadata
            assert updated_score_negative.metadata["feedback_adjustment"] == -0.3

        @pytest.mark.asyncio
        async def test_should_apply_layer(self, confidence_service):
            """Test determination of whether a validation layer should be applied."""
            # Test valid item data
            item_data = {
                "platform": "java",
                "usage_count": 10,
                "created_at": datetime.utcnow() - timedelta(days=30)
            }

            # All layers should be applied for valid data
            for layer in ValidationLayer:
                should_apply = await confidence_service._should_apply_layer(
                        layer, item_data, {}
                    )
                assert should_apply is True

            # Test with invalid platform
            invalid_platform_data = {
                "platform": "invalid",
                "usage_count": 10,
                "created_at": datetime.utcnow() - timedelta(days=30)
            }

            should_apply = await confidence_service._should_apply_layer(
                ValidationLayer.CROSS_PLATFORM_VALIDATION, invalid_platform_data, {}
            )
            assert should_apply is False

            # Test with no usage
            no_usage_data = {
                "platform": "java",
                "usage_count": 0,
                "created_at": datetime.utcnow() - timedelta(days=30)
            }

            should_apply = await confidence_service._should_apply_layer(
                ValidationLayer.USAGE_VALIDATION, no_usage_data, {}
            )
            assert should_apply is False

            # Test with no creation date
            no_date_data = {
                "platform": "java",
                "usage_count": 10,
                "created_at": None
            }

            should_apply = await confidence_service._should_apply_layer(
                ValidationLayer.HISTORICAL_VALIDATION, no_date_data, {}
            )
            assert should_apply is False

            # Test with skipped validation layers in context
            context_data = {"skip_validation_layers": [ValidationLayer.EXPERT_VALIDATION.value]}

            should_apply = await confidence_service._should_apply_layer(
                ValidationLayer.EXPERT_VALIDATION, item_data, context_data
            )
            assert should_apply is False

    class TestValidationLayers:
        """Test cases for individual validation layers."""

        @pytest.mark.asyncio
        async def test_validate_expert_approval(self, confidence_service):
            """Test expert validation layer."""
            # Test with expert validation
            expert_validated_data = {"expert_validated": True}
            score = await confidence_service._validate_expert_approval(expert_validated_data)

            assert score.layer == ValidationLayer.EXPERT_VALIDATION
            assert score.score > 0.7
            assert score.confidence > 0.8
            assert score.evidence["expert_validated"] is True

            # Test without expert validation
            non_expert_data = {"expert_validated": False}
            score = await confidence_service._validate_expert_approval(non_expert_data)

            assert score.layer == ValidationLayer.EXPERT_VALIDATION
            assert score.score < 0.5
            assert score.evidence["expert_validated"] is False

        @pytest.mark.asyncio
        async def test_validate_cross_platform_compatibility(self, confidence_service):
            """Test cross-platform validation layer."""
            # Test with both platforms
            both_platform_data = {"platform": "both", "minecraft_version": "latest"}
            score = await confidence_service._validate_cross_platform_compatibility(both_platform_data)

            assert score.layer == ValidationLayer.CROSS_PLATFORM_VALIDATION
            assert score.score > 0.8
            assert score.evidence["platform"] == "both"
            assert score.evidence["minecraft_version"] == "latest"

            # Test with java only
            java_platform_data = {"platform": "java", "minecraft_version": "1.18.2"}
            score = await confidence_service._validate_cross_platform_compatibility(java_platform_data)

            assert score.layer == ValidationLayer.CROSS_PLATFORM_VALIDATION
            assert 0.6 < score.score < 0.8
            assert score.evidence["platform"] == "java"
            assert score.evidence["minecraft_version"] == "1.18.2"

            # Test with invalid platform
            invalid_platform_data = {"platform": "invalid", "minecraft_version": "1.18.2"}
            score = await confidence_service._validate_cross_platform_compatibility(invalid_platform_data)

            assert score.layer == ValidationLayer.CROSS_PLATFORM_VALIDATION
            assert score.score < 0.5

        @pytest.mark.asyncio
        async def test_validate_version_compatibility(self, confidence_service):
            """Test version compatibility validation layer."""
            # Test with latest version
            latest_version_data = {"minecraft_version": "latest", "properties": {}}
            score = await confidence_service._validate_version_compatibility(latest_version_data)

            assert score.layer == ValidationLayer.VERSION_COMPATIBILITY
            assert score.score > 0.8
            assert score.evidence["minecraft_version"] == "latest"

            # Test with 1.18 version
            version_data = {"minecraft_version": "1.18.2", "properties": {}}
            score = await confidence_service._validate_version_compatibility(version_data)

            assert score.layer == ValidationLayer.VERSION_COMPATIBILITY
            assert 0.6 < score.score < 0.8
            assert score.evidence["minecraft_version"] == "1.18.2"

            # Test with deprecated features
            deprecated_data = {
                "minecraft_version": "1.18.2",
                "properties": {"deprecated_features": ["feature1", "feature2"]}
            }
            score = await confidence_service._validate_version_compatibility(deprecated_data)

            assert score.layer == ValidationLayer.VERSION_COMPATIBILITY
            assert score.score < 0.6  # Should be penalized for deprecated features
            assert "deprecated_penalty" in score.evidence

        @pytest.mark.asyncio
        async def test_validate_usage_statistics(self, confidence_service):
            """Test usage statistics validation layer."""
            # Test with high usage and success rate
            high_usage_data = {"usage_count": 1000, "success_rate": 0.9}
            score = await confidence_service._validate_usage_statistics(high_usage_data)

            assert score.layer == ValidationLayer.USAGE_VALIDATION
            assert score.score > 0.7
            assert score.confidence > 0.9
            assert score.evidence["usage_count"] == 1000
            assert score.evidence["success_rate"] == 0.9

            # Test with low usage and success rate
            low_usage_data = {"usage_count": 5, "success_rate": 0.4}
            score = await confidence_service._validate_usage_statistics(low_usage_data)

            assert score.layer == ValidationLayer.USAGE_VALIDATION
            assert score.score < 0.6
            assert score.confidence < 0.3

        @pytest.mark.asyncio
        async def test_validate_semantic_consistency(self, confidence_service):
            """Test semantic consistency validation layer."""
            # Test with good semantic consistency
            good_semantic_data = {
                "name": "Test Item",
                "description": "This is a test item for testing purposes",
                "tags": ["test", "item"]
            }
            score = await confidence_service._validate_semantic_consistency(good_semantic_data)

            assert score.layer == ValidationLayer.SEMANTIC_VALIDATION
            assert score.score > 0.7
            assert score.confidence > 0.8

            # Test with poor semantic consistency
            poor_semantic_data = {
                "name": "Item",
                "description": "",
                "tags": []
            }
            score = await confidence_service._validate_semantic_consistency(poor_semantic_data)

            assert score.layer == ValidationLayer.SEMANTIC_VALIDATION
            assert score.score < 0.5
            assert score.confidence < 0.7

    class TestBatchOperations:
        """Test cases for batch operations."""

        @pytest.mark.asyncio
        async def test_batch_assess_confidence(self, confidence_service, mock_db_session):
            """Test batch confidence assessment for multiple items."""
            # Mock the assess_confidence method
            mock_assessments = [
                ConfidenceAssessment(
                    overall_confidence=0.8,
                    validation_scores=[
                        ValidationScore(
                            layer=ValidationLayer.EXPERT_VALIDATION,
                            score=0.8,
                            confidence=0.9,
                            evidence={"expert_review": True},
                            metadata={}
                        )
                    ],
                    risk_factors=[],
                    confidence_factors=[],
                    recommendations=[],
                    assessment_metadata={}
                ),
                ConfidenceAssessment(
                    overall_confidence=0.7,
                    validation_scores=[
                        ValidationScore(
                            layer=ValidationLayer.COMMUNITY_VALIDATION,
                            score=0.7,
                            confidence=0.8,
                            evidence={"community_votes": 10},
                            metadata={}
                        )
                    ],
                    risk_factors=[],
                    confidence_factors=[],
                    recommendations=[],
                    assessment_metadata={}
                )
            ]

            # Mock methods
            confidence_service.assess_confidence = AsyncMock(side_effect=mock_assessments)
            confidence_service._analyze_batch_patterns = AsyncMock(return_value={"patterns": []})
            confidence_service._generate_batch_recommendations = MagicMock(return_value=["Batch recommendation"])

            # Call the method
            result = await confidence_service.batch_assess_confidence(
                items=[("node", "item1"), ("node", "item2")],
                context_data={"batch": True},
                db=mock_db_session
            )

            # Verify the result
            assert result["success"] is True
            assert result["total_items"] == 2
            assert result["assessed_items"] == 2
            assert "node:item1" in result["batch_results"]
            assert "node:item2" in result["batch_results"]
            assert "batch_metadata" in result
            assert "recommendations" in result
            assert "pattern_analysis" in result

            # Verify batch metadata
            assert "assessment_timestamp" in result["batch_metadata"]
            assert "confidence_distribution" in result["batch_metadata"]

    class TestFeedbackUpdate:
        """Test cases for feedback-based confidence updates."""

        @pytest.mark.asyncio
        async def test_update_confidence_from_feedback(self, confidence_service, mock_db_session):
            """Test updating confidence based on user feedback."""
            # Mock current assessment
            mock_current_assessment = ConfidenceAssessment(
                overall_confidence=0.7,
                validation_scores=[
                    ValidationScore(
                        layer=ValidationLayer.EXPERT_VALIDATION,
                        score=0.7,
                        confidence=0.8,
                        evidence={"expert_review": True},
                        metadata={}
                    )
                ],
                risk_factors=[],
                confidence_factors=[],
                recommendations=[],
                assessment_metadata={}
            )

            # Mock methods
            confidence_service.assess_confidence = AsyncMock(return_value=mock_current_assessment)
            confidence_service._calculate_feedback_impact = MagicMock(return_value={
                ValidationLayer.EXPERT_VALIDATION: 0.2
            })
            confidence_service._apply_feedback_to_score = MagicMock(
                return_value=mock_current_assessment.validation_scores[0]
            )
            confidence_service._update_item_confidence = AsyncMock()

            # Call the method
            feedback_data = {"success": True, "user_rating": 5}
            result = await confidence_service.update_confidence_from_feedback(
                item_type="node",
                item_id="test_item",
                feedback_data=feedback_data,
                db=mock_db_session
            )

            # Verify the result
            assert result["success"] is True
            assert result["previous_confidence"] == 0.7
            assert "new_confidence" in result
            assert "confidence_change" in result
            assert "update_record" in result

            # Verify update record
            assert result["update_record"]["item_type"] == "node"
            assert result["update_record"]["item_id"] == "test_item"
            assert result["update_record"]["previous_confidence"] == 0.7

            # Verify that update_item_confidence was called
            confidence_service._update_item_confidence.assert_called()

        @pytest.mark.asyncio
        async def test_update_confidence_invalid_item(self, confidence_service, mock_db_session):
            """Test updating confidence for a non-existent item."""
            # Mock assess_confidence to return None (item not found)
            confidence_service.assess_confidence = AsyncMock(return_value=None)

            # Call the method
            feedback_data = {"success": True, "user_rating": 5}
            result = await confidence_service.update_confidence_from_feedback(
                item_type="node",
                item_id="nonexistent_item",
                feedback_data=feedback_data,
                db=mock_db_session
            )

            # Verify the result
            assert result["success"] is False
            assert "Item not found" in result["error"]

    # Additional comprehensive tests for better coverage

    async def test_batch_assess_confidence(self, confidence_service, mock_db_session):
        """Test batch confidence assessment for multiple items."""
        batch_items = [
            {"item_type": "node", "item_id": "node_1"},
            {"item_type": "node", "item_id": "node_2"},
            {"item_type": "relationship", "item_id": "rel_1"},
            {"item_type": "pattern", "item_id": "pattern_1"}
        ]

        # Mock individual assessments
        with patch.object(confidence_service, 'assess_confidence') as mock_assess:
            mock_assess.side_effect = [
                ConfidenceAssessment(
                    overall_confidence=0.85,
                    validation_scores={},
                    risk_factors=[],
                    confidence_factors=[]
                ),
                ConfidenceAssessment(
                    overall_confidence=0.72,
                    validation_scores={},
                    risk_factors=["low_usage"],
                    confidence_factors=["expert_validated"]
                ),
                ConfidenceAssessment(
                    overall_confidence=0.65,
                    validation_scores={},
                    risk_factors=["complex_mapping"],
                    confidence_factors=["pattern_consistency"]
                ),
                None  # Not found
            ]

            results = await confidence_service.batch_assess_confidence(
                batch_items, mock_db_session
            )

            assert len(results) == 4
            assert results[0]["overall_confidence"] == 0.85
            assert results[1]["overall_confidence"] == 0.72
            assert results[2]["overall_confidence"] == 0.65
            assert results[3]["success"] is False
            assert mock_assess.call_count == 4

    async def test_get_confidence_trends(self, confidence_service, mock_db_session):
        """Test getting confidence trends over time."""
        with patch.object(confidence_service, '_collect_historical_data') as mock_collect:
            mock_collect.return_value = [
                {"date": "2024-01-01", "avg_confidence": 0.75, "item_count": 120},
                {"date": "2024-01-02", "avg_confidence": 0.78, "item_count": 135},
                {"date": "2024-01-03", "avg_confidence": 0.82, "item_count": 142},
                {"date": "2024-01-04", "avg_confidence": 0.80, "item_count": 138}
            ]

            trends = await confidence_service.get_confidence_trends(
                item_type="node",
                days_back=30,
                db=mock_db_session
            )

            assert "trend_data" in trends
            assert "summary" in trends
            assert "insights" in trends
            assert len(trends["trend_data"]) == 4
            assert trends["summary"]["average_confidence"] == 0.7875
            assert "trend_direction" in trends["summary"]

    async def test_validate_community_approval(self, confidence_service):
        """Test community validation layer."""
        # High community approval
        high_community_data = {
            "community_rating": 4.7,
            "user_reviews": 125,
            "positive_reviews": 118,
            "usage_count": 2500,
            "reported_issues": 2
        }

        score = await confidence_service._validate_community_approval(high_community_data)

        assert score.layer == ValidationLayer.COMMUNITY_VALIDATION
        assert score.score >= 0.8  # High approval
        assert len(score.reasons) >= 1
        assert len(score.factors) >= 2

        # Low community approval
        low_community_data = {
            "community_rating": 2.3,
            "user_reviews": 45,
            "positive_reviews": 12,
            "usage_count": 150,
            "reported_issues": 15
        }

        low_score = await confidence_service._validate_community_approval(low_community_data)

        assert low_score.score <= 0.5  # Low approval
        assert len(low_score.reasons) >= 1
        assert any("low rating" in reason.lower() for reason in low_score.reasons)

    async def test_validate_historical_performance(self, confidence_service):
        """Test historical performance validation."""
        # Strong historical performance
        strong_history_data = {
            "success_rate": 0.92,
            "total_conversions": 156,
            "failed_conversions": 12,
            "avg_implementation_time": 35.5,
            "avg_complexity": 3.2
        }

        score = await confidence_service._validate_historical_performance(strong_history_data)

        assert score.layer == ValidationLayer.HISTORICAL_VALIDATION
        assert score.score >= 0.8
        assert len(score.factors) >= 2

        # Poor historical performance
        poor_history_data = {
            "success_rate": 0.45,
            "total_conversions": 31,
            "failed_conversions": 17,
            "avg_implementation_time": 125.8,
            "avg_complexity": 8.7
        }

        poor_score = await confidence_service._validate_historical_performance(poor_history_data)

        assert poor_score.score <= 0.6
        assert len(poor_score.reasons) >= 1
        assert any("success rate" in reason.lower() for reason in poor_score.reasons)

    async def test_validate_pattern_consistency(self, confidence_service):
        """Test pattern consistency validation."""
        # Consistent pattern
        consistent_data = {
            "pattern_type": "direct_mapping",
            "similarity_score": 0.88,
            "matching_features": 12,
            "total_features": 14,
            "pattern_frequency": 0.65,
            "related_patterns": ["simple_mapping", "block_conversion"]
        }

        score = await confidence_service._validate_pattern_consistency(consistent_data)

        assert score.layer == ValidationLayer.PATTERN_VALIDATION
        assert score.score >= 0.7
        assert len(score.factors) >= 2

        # Inconsistent pattern
        inconsistent_data = {
            "pattern_type": "complex_transformation",
            "similarity_score": 0.34,
            "matching_features": 3,
            "total_features": 10,
            "pattern_frequency": 0.08,
            "related_patterns": []
        }

        inconsistent_score = await confidence_service._validate_pattern_consistency(inconsistent_data)

        assert inconsistent_score.score <= 0.5
        assert len(inconsistent_score.reasons) >= 1

    async def test_validate_cross_platform_compatibility(self, confidence_service):
        """Test cross-platform compatibility validation."""
        # Good cross-platform compatibility
        compatible_data = {
            "java_version": "1.20.0",
            "bedrock_version": "1.20.0",
            "platform_differences": ["minor_syntax"],
            "compatibility_score": 0.91,
            "tested_platforms": ["java", "bedrock"],
            "compatibility_issues": []
        }

        score = await confidence_service._validate_cross_platform_compatibility(compatible_data)

        assert score.layer == ValidationLayer.CROSS_PLATFORM_VALIDATION
        assert score.score >= 0.8
        assert len(score.factors) >= 2

        # Poor cross-platform compatibility
        incompatible_data = {
            "java_version": "1.18.0",
            "bedrock_version": "1.20.0",
            "platform_differences": ["major_api_changes", "removed_features"],
            "compatibility_score": 0.23,
            "tested_platforms": ["java"],
            "compatibility_issues": ["feature_gap", "api_mismatch"]
        }

        incompatible_score = await confidence_service._validate_cross_platform_compatibility(incompatible_data)

        assert incompatible_score.score <= 0.4
        assert len(incompatible_score.reasons) >= 2

    async def test_validate_version_compatibility(self, confidence_service):
        """Test version compatibility validation."""
        # Good version compatibility
        compatible_version_data = {
            "minecraft_version": "1.20.0",
            "version_range": ["1.19.0", "1.20.5"],
            "deprecated_features": [],
            "breaking_changes": [],
            "version_stability": 0.95
        }

        score = await confidence_service._validate_version_compatibility(compatible_version_data)

        assert score.layer == ValidationLayer.VERSION_COMPATIBILITY
        assert score.score >= 0.9
        assert len(score.factors) >= 2

        # Poor version compatibility
        incompatible_version_data = {
            "minecraft_version": "1.16.5",
            "version_range": ["1.20.0", "1.21.0"],
            "deprecated_features": ["old_api"],
            "breaking_changes": ["entity_changes", "block_changes"],
            "version_stability": 0.45
        }

        incompatible_score = await confidence_service._validate_version_compatibility(incompatible_version_data)

        assert incompatible_score.score <= 0.5
        assert len(incompatible_score.reasons) >= 2

    async def test_validate_usage_statistics(self, confidence_service):
        """Test usage statistics validation."""
        # High usage statistics
        high_usage_data = {
            "usage_count": 8500,
            "unique_users": 1200,
            "successful_implementations": 7950,
            "failed_implementations": 550,
            "avg_user_rating": 4.6,
            "usage_trend": "increasing"
        }

        score = await confidence_service._validate_usage_statistics(high_usage_data)

        assert score.layer == ValidationLayer.USAGE_STATISTICS
        assert score.score >= 0.8
        assert len(score.factors) >= 3

        # Low usage statistics
        low_usage_data = {
            "usage_count": 45,
            "unique_users": 12,
            "successful_implementations": 28,
            "failed_implementations": 17,
            "avg_user_rating": 2.8,
            "usage_trend": "decreasing"
        }

        low_score = await confidence_service._validate_usage_statistics(low_usage_data)

        assert low_score.score <= 0.5
        assert len(low_score.reasons) >= 2

    async def test_validate_semantic_consistency(self, confidence_service):
        """Test semantic consistency validation."""
        # High semantic consistency
        consistent_semantic_data = {
            "concept_similarity": 0.89,
            "description_match": 0.92,
            "feature_overlap": 0.87,
            "behavioral_similarity": 0.85,
            "semantic_drift": 0.05,
            "concept_alignment": 0.94
        }

        score = await confidence_service._validate_semantic_consistency(consistent_semantic_data)

        assert score.layer == ValidationLayer.SEMANTIC_CONSISTENCY
        assert score.score >= 0.85
        assert len(score.factors) >= 3

        # Low semantic consistency
        inconsistent_semantic_data = {
            "concept_similarity": 0.31,
            "description_match": 0.28,
            "feature_overlap": 0.45,
            "behavioral_similarity": 0.22,
            "semantic_drift": 0.78,
            "concept_alignment": 0.35
        }

        inconsistent_score = await confidence_service._validate_semantic_consistency(inconsistent_semantic_data)

        assert inconsistent_score.score <= 0.4
        assert len(inconsistent_score.reasons) >= 2

    def test_calculate_overall_confidence_comprehensive(self, confidence_service):
        """Test comprehensive overall confidence calculation."""
        # All high-confidence validations
        high_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.9,
                reasons=["expert_approved"],
                factors=["expert_reputation", "thorough_review"]
            ),
            ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=0.85,
                reasons=["high_community_rating"],
                factors=["user_reviews", "usage_stats"]
            ),
            ValidationScore(
                layer=ValidationLayer.HISTORICAL_VALIDATION,
                score=0.88,
                reasons=["strong_success_rate"],
                factors=["historical_performance"]
            )
        ]

        overall = confidence_service._calculate_overall_confidence(high_scores)
        assert overall >= 0.8

        # Mixed confidence scores
        mixed_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.95,
                reasons=["expert_approved"],
                factors=["expert_reputation"]
            ),
            ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=0.45,
                reasons=["low_community_rating"],
                factors=["poor_reviews"]
            ),
            ValidationScore(
                layer=ValidationLayer.HISTORICAL_VALIDATION,
                score=0.72,
                reasons=["moderate_success_rate"],
                factors=["historical_data"]
            )
        ]

        mixed_overall = confidence_service._calculate_overall_confidence(mixed_scores)
        assert 0.6 <= mixed_overall <= 0.8  # Should be balanced

    def test_identify_risk_factors_comprehensive(self, confidence_service):
        """Test comprehensive risk factor identification."""
        # Multiple low scores
        risk_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.3,
                reasons=["no_expert_approval", "questionable_methodology"],
                factors=[]
            ),
            ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=0.25,
                reasons=["very_low_rating", "many_complaints"],
                factors=[]
            ),
            ValidationScore(
                layer=ValidationLayer.HISTORICAL_VALIDATION,
                score=0.82,
                reasons=["good_historical_performance"],
                factors=[]
            )
        ]

        risk_factors = confidence_service._identify_risk_factors(risk_scores)

        assert len(risk_factors) >= 3
        assert "no_expert_approval" in risk_factors
        assert "very_low_rating" in risk_factors
        assert any("low confidence" in factor for factor in risk_factors)

    def test_identify_confidence_factors_comprehensive(self, confidence_service):
        """Test comprehensive confidence factor identification."""
        # Multiple high scores
        confidence_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.95,
                reasons=[],
                factors=["expert_approved", "thorough_review", "reliable_source"]
            ),
            ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=0.88,
                reasons=[],
                factors=["high_usage", "positive_reviews", "community_trust"]
            ),
            ValidationScore(
                layer=ValidationLayer.PATTERN_VALIDATION,
                score=0.91,
                reasons=[],
                factors=["strong_pattern_match", "consistent_structure"]
            )
        ]

        confidence_factors = confidence_service._identify_confidence_factors(confidence_scores)

        assert len(confidence_factors) >= 6
        assert "expert_approved" in confidence_factors
        assert "high_usage" in confidence_factors
        assert "strong_pattern_match" in confidence_factors

    async def test_generate_recommendations_comprehensive(self, confidence_service):
        """Test comprehensive recommendation generation."""
        low_confidence_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.3,
                reasons=["no_expert_review"],
                factors=[]
            ),
            ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=0.45,
                reasons=["low_community_rating"],
                factors=[]
            ),
            ValidationScore(
                layer=ValidationLayer.HISTORICAL_VALIDATION,
                score=0.22,
                reasons=["poor_success_rate"],
                factors=[]
            )
        ]

        recommendations = await confidence_service._generate_recommendations(
            low_confidence_scores, overall_confidence=0.32
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) >= 3
        assert all("category" in rec for rec in recommendations)
        assert all("priority" in rec for rec in recommendations)
        assert all("action" in rec for rec in recommendations)

        # Should recommend expert review
        expert_recs = [r for r in recommendations if "expert" in r["action"].lower()]
        assert len(expert_recs) >= 1

        # Should recommend community engagement
        community_recs = [r for r in recommendations if "community" in r["action"].lower()]
        assert len(community_recs) >= 1

    def test_edge_case_no_validation_scores(self, confidence_service):
        """Test handling of empty validation scores."""
        empty_scores = []

        overall_confidence = confidence_service._calculate_overall_confidence(empty_scores)
        assert overall_confidence == 0.0

        risk_factors = confidence_service._identify_risk_factors(empty_scores)
        assert risk_factors == []

        confidence_factors = confidence_service._identify_confidence_factors(empty_scores)
        assert confidence_factors == []

    def test_edge_case_extreme_values(self, confidence_service):
        """Test handling of extreme confidence values."""
        # Perfect scores
        perfect_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=1.0,
                reasons=["perfect_validation"],
                factors=["ideal_conditions"]
            )
        ]

        perfect_overall = confidence_service._calculate_overall_confidence(perfect_scores)
        assert perfect_overall == 1.0

        # Zero scores
        zero_scores = [
            ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.0,
                reasons=["complete_failure"],
                factors=["critical_issues"]
            )
        ]

        zero_overall = confidence_service._calculate_overall_confidence(zero_scores)
        assert zero_overall == 0.0

    async def test_performance_large_batch_assessment(self, confidence_service, mock_db_session):
        """Test performance with large batch assessments."""
        # Create large batch
        large_batch = [
            {"item_type": "node", "item_id": f"node_{i}"}
            for i in range(200)
        ]

        # Mock individual assessments
        with patch.object(confidence_service, 'assess_confidence') as mock_assess:
            mock_assess.return_value = ConfidenceAssessment(
                overall_confidence=0.75,
                validation_scores={},
                risk_factors=[],
                confidence_factors=[]
            )

            import time
            start_time = time.time()

            results = await confidence_service.batch_assess_confidence(
                large_batch, mock_db_session
            )

            processing_time = time.time() - start_time

            assert len(results) == 200
            assert processing_time < 10.0  # Should complete within 10 seconds
            assert mock_assess.call_count == 200

    def test_validation_layer_weights_sum(self, confidence_service):
        """Test that validation layer weights sum to 1.0."""
        total_weight = sum(confidence_service.layer_weights.values())
        assert abs(total_weight - 1.0) < 0.01  # Allow small floating point error

    def test_confidence_assessment_dataclass(self):
        """Test ConfidenceAssessment dataclass functionality."""
        assessment = ConfidenceAssessment(
            overall_confidence=0.85,
            validation_scores={
                ValidationLayer.EXPERT_VALIDATION: ValidationScore(
                    layer=ValidationLayer.EXPERT_VALIDATION,
                    score=0.9,
                    reasons=["expert_approved"],
                    factors=["thorough_review"]
                )
            },
            risk_factors=["low_community_rating"],
            confidence_factors=["expert_validation"]
        )

        assert assessment.overall_confidence == 0.85
        assert len(assessment.validation_scores) == 1
        assert len(assessment.risk_factors) == 1
        assert len(assessment.confidence_factors) == 1
