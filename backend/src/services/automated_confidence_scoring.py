"""
Automated Confidence Scoring System

This service provides multi-layer validation and automated confidence scoring
for knowledge graph relationships and conversion patterns.
"""

import logging
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from db.knowledge_graph_crud import (
    KnowledgeNodeCRUD, KnowledgeRelationshipCRUD, ConversionPatternCRUD
)

logger = logging.getLogger(__name__)


class ValidationLayer(Enum):
    """Validation layers for confidence scoring."""
    EXPERT_VALIDATION = "expert_validation"
    COMMUNITY_VALIDATION = "community_validation"
    HISTORICAL_VALIDATION = "historical_validation"
    PATTERN_VALIDATION = "pattern_validation"
    CROSS_PLATFORM_VALIDATION = "cross_platform_validation"
    VERSION_COMPATIBILITY = "version_compatibility"
    USAGE_VALIDATION = "usage_validation"
    SEMANTIC_VALIDATION = "semantic_validation"


@dataclass
class ValidationScore:
    """Individual validation layer score."""
    layer: ValidationLayer
    score: float
    confidence: float
    evidence: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class ConfidenceAssessment:
    """Complete confidence assessment with all validation layers."""
    overall_confidence: float
    validation_scores: List[ValidationScore]
    risk_factors: List[str]
    confidence_factors: List[str]
    recommendations: List[str]
    assessment_metadata: Dict[str, Any]


class AutomatedConfidenceScoringService:
    """Automated confidence scoring with multi-layer validation."""
    
    def __init__(self):
        self.layer_weights = {
            ValidationLayer.EXPERT_VALIDATION: 0.25,
            ValidationLayer.COMMUNITY_VALIDATION: 0.20,
            ValidationLayer.HISTORICAL_VALIDATION: 0.15,
            ValidationLayer.PATTERN_VALIDATION: 0.15,
            ValidationLayer.CROSS_PLATFORM_VALIDATION: 0.10,
            ValidationLayer.VERSION_COMPATIBILITY: 0.08,
            ValidationLayer.USAGE_VALIDATION: 0.05,
            ValidationLayer.SEMANTIC_VALIDATION: 0.02
        }
        self.validation_cache = {}
        self.scoring_history = []
        
    async def assess_confidence(
        self,
        item_type: str,  # "node", "relationship", "pattern"
        item_id: str,
        context_data: Dict[str, Any] = None,
        db: AsyncSession = None
    ) -> ConfidenceAssessment:
        """
        Assess confidence for knowledge graph item using multi-layer validation.
        
        Args:
            item_type: Type of item (node, relationship, pattern)
            item_id: ID of the item to assess
            context_data: Additional context for assessment
            db: Database session
        
        Returns:
            Complete confidence assessment with all validation layers
        """
        try:
            # Step 1: Get item data
            item_data = await self._get_item_data(item_type, item_id, db)
            if not item_data:
                raise ValueError(f"Item not found: {item_type}:{item_id}")
            
            # Step 2: Apply all validation layers
            validation_scores = []
            
            for layer in ValidationLayer:
                if await self._should_apply_layer(layer, item_data, context_data):
                    score = await self._apply_validation_layer(
                        layer, item_type, item_data, context_data, db
                    )
                    validation_scores.append(score)
            
            # Step 3: Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(validation_scores)
            
            # Step 4: Identify risk and confidence factors
            risk_factors = self._identify_risk_factors(validation_scores)
            confidence_factors = self._identify_confidence_factors(validation_scores)
            
            # Step 5: Generate recommendations
            recommendations = await self._generate_recommendations(
                validation_scores, overall_confidence, item_data
            )
            
            # Step 6: Create assessment metadata
            assessment_metadata = {
                "item_type": item_type,
                "item_id": item_id,
                "validation_layers_applied": [score.layer.value for score in validation_scores],
                "assessment_timestamp": datetime.utcnow().isoformat(),
                "context_applied": context_data,
                "scoring_method": "weighted_multi_layer_validation"
            }
            
            # Create assessment
            assessment = ConfidenceAssessment(
                overall_confidence=overall_confidence,
                validation_scores=validation_scores,
                risk_factors=risk_factors,
                confidence_factors=confidence_factors,
                recommendations=recommendations,
                assessment_metadata=assessment_metadata
            )
            
            # Cache assessment
            self._cache_assessment(item_type, item_id, assessment)
            
            # Track scoring history
            self.scoring_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "item_type": item_type,
                "item_id": item_id,
                "overall_confidence": overall_confidence,
                "validation_count": len(validation_scores)
            })
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error assessing confidence: {e}")
            # Return default assessment
            return ConfidenceAssessment(
                overall_confidence=0.5,
                validation_scores=[],
                risk_factors=[f"Assessment error: {str(e)}"],
                confidence_factors=[],
                recommendations=["Retry assessment with valid data"],
                assessment_metadata={"error": str(e)}
            )
    
    async def batch_assess_confidence(
        self,
        items: List[Tuple[str, str]],  # List of (item_type, item_id) tuples
        context_data: Dict[str, Any] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Assess confidence for multiple items with batch optimization.
        
        Args:
            items: List of (item_type, item_id) tuples
            context_data: Shared context data
            db: Database session
        
        Returns:
            Batch assessment results with comparative analysis
        """
        try:
            batch_results = {}
            batch_scores = []
            
            # Assess each item
            for item_type, item_id in items:
                assessment = await self.assess_confidence(
                    item_type, item_id, context_data, db
                )
                batch_results[f"{item_type}:{item_id}"] = assessment
                batch_scores.append(assessment.overall_confidence)
            
            # Analyze batch results
            batch_analysis = self._analyze_batch_results(batch_results, batch_scores)
            
            # Identify patterns across items
            pattern_analysis = await self._analyze_batch_patterns(batch_results, db)
            
            # Generate batch recommendations
            batch_recommendations = self._generate_batch_recommendations(
                batch_results, batch_analysis
            )
            
            return {
                "success": True,
                "total_items": len(items),
                "assessed_items": len(batch_results),
                "batch_results": batch_results,
                "batch_analysis": batch_analysis,
                "pattern_analysis": pattern_analysis,
                "recommendations": batch_recommendations,
                "batch_metadata": {
                    "assessment_timestamp": datetime.utcnow().isoformat(),
                    "average_confidence": np.mean(batch_scores) if batch_scores else 0.0,
                    "confidence_distribution": self._calculate_confidence_distribution(batch_scores)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in batch confidence assessment: {e}")
            return {
                "success": False,
                "error": f"Batch assessment failed: {str(e)}",
                "total_items": len(items),
                "assessed_items": 0
            }
    
    async def update_confidence_from_feedback(
        self,
        item_type: str,
        item_id: str,
        feedback_data: Dict[str, Any],
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Update confidence scores based on user feedback.
        
        Args:
            item_type: Type of item
            item_id: ID of the item
            feedback_data: User feedback including success/failure
            db: Database session
        
        Returns:
            Update results with confidence adjustments
        """
        try:
            # Get current assessment
            current_assessment = await self.assess_confidence(item_type, item_id, {}, db)
            
            # Calculate feedback impact
            feedback_impact = self._calculate_feedback_impact(feedback_data)
            
            # Update validation scores based on feedback
            updated_scores = []
            for score in current_assessment.validation_scores:
                updated_score = self._apply_feedback_to_score(score, feedback_impact)
                updated_scores.append(updated_score)
            
            # Recalculate overall confidence
            new_overall_confidence = self._calculate_overall_confidence(updated_scores)
            
            # Track the update
            update_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "item_type": item_type,
                "item_id": item_id,
                "previous_confidence": current_assessment.overall_confidence,
                "new_confidence": new_overall_confidence,
                "feedback_data": feedback_data,
                "feedback_impact": feedback_impact
            }
            
            # Update item in database if confidence changed significantly
            if abs(new_overall_confidence - current_assessment.overall_confidence) > 0.1:
                await self._update_item_confidence(
                    item_type, item_id, new_overall_confidence, db
                )
            
            return {
                "success": True,
                "previous_confidence": current_assessment.overall_confidence,
                "new_confidence": new_overall_confidence,
                "confidence_change": new_overall_confidence - current_assessment.overall_confidence,
                "updated_scores": updated_scores,
                "feedback_impact": feedback_impact,
                "update_record": update_record
            }
            
        except Exception as e:
            logger.error(f"Error updating confidence from feedback: {e}")
            return {
                "success": False,
                "error": f"Feedback update failed: {str(e)}"
            }
    
    async def get_confidence_trends(
        self,
        days: int = 30,
        item_type: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Get confidence score trends over time.
        
        Args:
            days: Number of days to analyze
            item_type: Filter by item type (optional)
            db: Database session
        
        Returns:
            Trend analysis with insights
        """
        try:
            # Get recent assessments from history
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            recent_assessments = [
                assessment for assessment in self.scoring_history
                if datetime.fromisoformat(assessment["timestamp"]) > cutoff_date
            ]
            
            if item_type:
                recent_assessments = [
                    assessment for assessment in recent_assessments
                    if assessment["item_type"] == item_type
                ]
            
            # Calculate trends
            confidence_trend = self._calculate_confidence_trend(recent_assessments)
            
            # Analyze validation layer performance
            layer_performance = self._analyze_layer_performance(recent_assessments)
            
            # Generate insights
            insights = self._generate_trend_insights(confidence_trend, layer_performance)
            
            return {
                "success": True,
                "analysis_period_days": days,
                "item_type_filter": item_type,
                "total_assessments": len(recent_assessments),
                "confidence_trend": confidence_trend,
                "layer_performance": layer_performance,
                "insights": insights,
                "trend_metadata": {
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "data_points": len(recent_assessments)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting confidence trends: {e}")
            return {
                "success": False,
                "error": f"Trend analysis failed: {str(e)}"
            }
    
    # Private Helper Methods
    
    async def _get_item_data(
        self, 
        item_type: str, 
        item_id: str, 
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get item data from database."""
        try:
            if item_type == "node":
                node = await KnowledgeNodeCRUD.get_by_id(db, item_id)
                if node:
                    return {
                        "type": "node",
                        "id": str(node.id),
                        "name": node.name,
                        "node_type": node.node_type,
                        "platform": node.platform,
                        "description": node.description,
                        "expert_validated": node.expert_validated,
                        "community_rating": node.community_rating,
                        "minecraft_version": node.minecraft_version,
                        "properties": json.loads(node.properties or "{}"),
                        "created_at": node.created_at,
                        "updated_at": node.updated_at
                    }
            
            elif item_type == "relationship":
                # Get relationship data
                relationship = await KnowledgeRelationshipCRUD.get_by_id(db, item_id)
                if relationship:
                    return {
                        "type": "relationship",
                        "id": str(relationship.id),
                        "source_node": relationship.source_node_id,
                        "target_node": relationship.target_node_id,
                        "relationship_type": relationship.relationship_type,
                        "confidence_score": relationship.confidence_score,
                        "expert_validated": relationship.expert_validated,
                        "community_votes": relationship.community_votes,
                        "properties": json.loads(relationship.properties or "{}"),
                        "created_at": relationship.created_at,
                        "updated_at": relationship.updated_at
                    }
            
            elif item_type == "pattern":
                pattern = await ConversionPatternCRUD.get_by_id(db, item_id)
                if pattern:
                    return {
                        "type": "pattern",
                        "id": str(pattern.id),
                        "pattern_type": pattern.pattern_type,
                        "java_concept": pattern.java_concept,
                        "bedrock_concept": pattern.bedrock_concept,
                        "success_rate": pattern.success_rate,
                        "usage_count": pattern.usage_count,
                        "confidence_score": pattern.confidence_score,
                        "expert_validated": pattern.expert_validated,
                        "minecraft_version": pattern.minecraft_version,
                        "conversion_features": json.loads(pattern.conversion_features or "{}"),
                        "validation_results": json.loads(pattern.validation_results or "{}"),
                        "created_at": pattern.created_at,
                        "updated_at": pattern.updated_at
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting item data: {e}")
            return None
    
    async def _should_apply_layer(
        self, 
        layer: ValidationLayer, 
        item_data: Dict[str, Any], 
        context_data: Optional[Dict[str, Any]]
    ) -> bool:
        """Determine if a validation layer should be applied."""
        try:
            # Skip layers that don't apply to certain item types
            if layer == ValidationLayer.CROSS_PLATFORM_VALIDATION and \
               item_data.get("platform") not in ["java", "bedrock", "both"]:
                return False
            
            if layer == ValidationLayer.USAGE_VALIDATION and \
               item_data.get("usage_count", 0) == 0:
                return False
            
            if layer == ValidationLayer.HISTORICAL_VALIDATION and \
               item_data.get("created_at") is None:
                return False
            
            # Apply context-based filtering
            if context_data:
                skip_layers = context_data.get("skip_validation_layers", [])
                if layer.value in skip_layers:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking if layer should be applied: {e}")
            return False
    
    async def _apply_validation_layer(
        self,
        layer: ValidationLayer,
        item_type: str,
        item_data: Dict[str, Any],
        context_data: Optional[Dict[str, Any]],
        db: AsyncSession
    ) -> ValidationScore:
        """Apply a specific validation layer and return score."""
        try:
            if layer == ValidationLayer.EXPERT_VALIDATION:
                return await self._validate_expert_approval(item_data)
            
            elif layer == ValidationLayer.COMMUNITY_VALIDATION:
                return await self._validate_community_approval(item_data, db)
            
            elif layer == ValidationLayer.HISTORICAL_VALIDATION:
                return await self._validate_historical_performance(item_data, db)
            
            elif layer == ValidationLayer.PATTERN_VALIDATION:
                return await self._validate_pattern_consistency(item_data, db)
            
            elif layer == ValidationLayer.CROSS_PLATFORM_VALIDATION:
                return await self._validate_cross_platform_compatibility(item_data)
            
            elif layer == ValidationLayer.VERSION_COMPATIBILITY:
                return await self._validate_version_compatibility(item_data)
            
            elif layer == ValidationLayer.USAGE_VALIDATION:
                return await self._validate_usage_statistics(item_data)
            
            elif layer == ValidationLayer.SEMANTIC_VALIDATION:
                return await self._validate_semantic_consistency(item_data)
            
            else:
                # Default neutral score
                return ValidationScore(
                    layer=layer,
                    score=0.5,
                    confidence=0.5,
                    evidence={},
                    metadata={"message": "Validation layer not implemented"}
                )
                
        except Exception as e:
            logger.error(f"Error applying validation layer {layer}: {e}")
            return ValidationScore(
                layer=layer,
                score=0.3,  # Low score due to error
                confidence=0.2,
                evidence={"error": str(e)},
                metadata={"error": True}
            )
    
    async def _validate_expert_approval(self, item_data: Dict[str, Any]) -> ValidationScore:
        """Validate expert approval status."""
        try:
            expert_validated = item_data.get("expert_validated", False)
            
            if expert_validated:
                return ValidationScore(
                    layer=ValidationLayer.EXPERT_VALIDATION,
                    score=0.95,
                    confidence=0.9,
                    evidence={"expert_validated": True},
                    metadata={"validation_method": "expert_flag"}
                )
            else:
                return ValidationScore(
                    layer=ValidationLayer.EXPERT_VALIDATION,
                    score=0.3,
                    confidence=0.8,
                    evidence={"expert_validated": False},
                    metadata={"validation_method": "expert_flag"}
                )
                
        except Exception as e:
            logger.error(f"Error in expert validation: {e}")
            return ValidationScore(
                layer=ValidationLayer.EXPERT_VALIDATION,
                score=0.5,
                confidence=0.0,
                evidence={"error": str(e)},
                metadata={"validation_error": True}
            )
    
    async def _validate_community_approval(
        self, 
        item_data: Dict[str, Any], 
        db: AsyncSession
    ) -> ValidationScore:
        """Validate community approval using ratings and contributions."""
        try:
            community_rating = item_data.get("community_rating", 0.0)
            community_votes = item_data.get("community_votes", 0)
            
            # Get community contributions for additional evidence
            contributions = []
            if db and item_data.get("id"):
                # This would query community contributions related to the item
                # For now, use mock data
                contributions = [
                    {"type": "vote", "value": "up"},
                    {"type": "review", "value": "positive"}
                ]
            
            # Calculate community score
            rating_score = min(1.0, community_rating)  # Normalize to 0-1
            vote_score = min(1.0, community_votes / 10.0)  # 10 votes = max score
            
            # Consider contribution quality
            contribution_score = 0.5
            positive_contributions = sum(
                1 for c in contributions 
                if c.get("value") in ["up", "positive", "approved"]
            )
            if contributions:
                contribution_score = positive_contributions / len(contributions)
            
            # Weighted combination
            final_score = (rating_score * 0.5 + vote_score * 0.3 + contribution_score * 0.2)
            
            return ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=final_score,
                confidence=min(1.0, community_votes / 5.0),  # More votes = higher confidence
                evidence={
                    "community_rating": community_rating,
                    "community_votes": community_votes,
                    "contributions": contributions,
                    "positive_contributions": positive_contributions
                },
                metadata={
                    "rating_score": rating_score,
                    "vote_score": vote_score,
                    "contribution_score": contribution_score
                }
            )
            
        except Exception as e:
            logger.error(f"Error in community validation: {e}")
            return ValidationScore(
                layer=ValidationLayer.COMMUNITY_VALIDATION,
                score=0.5,
                confidence=0.0,
                evidence={"error": str(e)},
                metadata={"validation_error": True}
            )
    
    async def _validate_historical_performance(
        self, 
        item_data: Dict[str, Any], 
        db: AsyncSession
    ) -> ValidationScore:
        """Validate based on historical performance."""
        try:
            created_at = item_data.get("created_at")
            success_rate = item_data.get("success_rate", 0.5)
            usage_count = item_data.get("usage_count", 0)
            
            # Calculate age factor (older items with good performance get higher scores)
            age_days = 0
            if created_at:
                age_days = (datetime.utcnow() - created_at).days
            
            age_score = min(1.0, age_days / 365.0)  # 1 year = max age score
            
            # Performance score
            performance_score = success_rate
            
            # Usage score (frequently used items are more reliable)
            usage_score = min(1.0, usage_count / 100.0)  # 100 uses = max score
            
            # Combined score
            final_score = (performance_score * 0.5 + usage_score * 0.3 + age_score * 0.2)
            
            # Confidence based on data availability
            data_confidence = 0.0
            if success_rate is not None:
                data_confidence += 0.4
            if usage_count > 0:
                data_confidence += 0.3
            if created_at:
                data_confidence += 0.3
            
            return ValidationScore(
                layer=ValidationLayer.HISTORICAL_VALIDATION,
                score=final_score,
                confidence=data_confidence,
                evidence={
                    "age_days": age_days,
                    "success_rate": success_rate,
                    "usage_count": usage_count,
                    "created_at": created_at.isoformat() if created_at else None
                },
                metadata={
                    "age_score": age_score,
                    "performance_score": performance_score,
                    "usage_score": usage_score
                }
            )
            
        except Exception as e:
            logger.error(f"Error in historical validation: {e}")
            return ValidationScore(
                layer=ValidationLayer.HISTORICAL_VALIDATION,
                score=0.5,
                confidence=0.0,
                evidence={"error": str(e)},
                metadata={"validation_error": True}
            )
    
    async def _validate_pattern_consistency(
        self, 
        item_data: Dict[str, Any], 
        db: AsyncSession
    ) -> ValidationScore:
        """Validate pattern consistency with similar items."""
        try:
            item_type = item_data.get("type")
            pattern_type = item_data.get("pattern_type", "")
            relationship_type = item_data.get("relationship_type", "")
            
            # This would query for similar patterns and compare
            # For now, use a simplified approach
            
            # Base score for having a pattern type
            pattern_score = 0.7 if pattern_type else 0.4
            
            # Check if pattern is well-established
            established_patterns = [
                "entity_conversion", "block_conversion", "item_conversion",
                "behavior_conversion", "command_conversion", "direct_conversion"
            ]
            
            if pattern_type in established_patterns:
                pattern_score = 0.9
            
            # Relationship consistency
            if item_type == "relationship" and relationship_type:
                common_relationships = [
                    "converts_to", "relates_to", "similar_to", "depends_on"
                ]
                if relationship_type in common_relationships:
                    pattern_score = max(pattern_score, 0.8)
            
            return ValidationScore(
                layer=ValidationLayer.PATTERN_VALIDATION,
                score=pattern_score,
                confidence=0.7,
                evidence={
                    "pattern_type": pattern_type,
                    "relationship_type": relationship_type,
                    "is_established_pattern": pattern_type in established_patterns
                },
                metadata={
                    "established_patterns": established_patterns
                }
            )
            
        except Exception as e:
            logger.error(f"Error in pattern validation: {e}")
            return ValidationScore(
                layer=ValidationLayer.PATTERN_VALIDATION,
                score=0.5,
                confidence=0.0,
                evidence={"error": str(e)},
                metadata={"validation_error": True}
            )
    
    async def _validate_cross_platform_compatibility(self, item_data: Dict[str, Any]) -> ValidationScore:
        """Validate cross-platform compatibility."""
        try:
            platform = item_data.get("platform", "")
            minecraft_version = item_data.get("minecraft_version", "")
            
            # Platform compatibility score
            if platform == "both":
                platform_score = 1.0
            elif platform in ["java", "bedrock"]:
                platform_score = 0.8
            else:
                platform_score = 0.3
            
            # Version compatibility score
            version_score = 1.0
            if minecraft_version == "latest":
                version_score = 0.9  # Latest might have some instability
            elif minecraft_version in ["1.20", "1.19", "1.18"]:
                version_score = 1.0  # Stable versions
            elif minecraft_version:
                version_score = 0.7  # Older versions
            else:
                version_score = 0.5  # Unknown version
            
            # Combined score
            final_score = (platform_score * 0.6 + version_score * 0.4)
            
            return ValidationScore(
                layer=ValidationLayer.CROSS_PLATFORM_VALIDATION,
                score=final_score,
                confidence=0.8,
                evidence={
                    "platform": platform,
                    "minecraft_version": minecraft_version,
                    "platform_score": platform_score,
                    "version_score": version_score
                },
                metadata={}
            )
            
        except Exception as e:
            logger.error(f"Error in cross-platform validation: {e}")
            return ValidationScore(
                layer=ValidationLayer.CROSS_PLATFORM_VALIDATION,
                score=0.5,
                confidence=0.0,
                evidence={"error": str(e)},
                metadata={"validation_error": True}
            )
    
    async def _validate_version_compatibility(self, item_data: Dict[str, Any]) -> ValidationScore:
        """Validate version compatibility."""
        try:
            minecraft_version = item_data.get("minecraft_version", "")
            
            # Version compatibility matrix
            compatibility_scores = {
                "latest": 0.9,
                "1.20": 1.0,
                "1.19": 1.0,
                "1.18": 0.95,
                "1.17": 0.85,
                "1.16": 0.75,
                "1.15": 0.65,
                "1.14": 0.55,
                "1.13": 0.45,
                "1.12": 0.35
            }
            
            base_score = compatibility_scores.get(minecraft_version, 0.3)
            
            # Check for deprecated features
            properties = item_data.get("properties", {})
            deprecated_features = properties.get("deprecated_features", [])
            
            if deprecated_features:
                deprecated_penalty = min(0.3, len(deprecated_features) * 0.1)
                base_score -= deprecated_penalty
            
            # Ensure score is within bounds
            final_score = max(0.0, min(1.0, base_score))
            
            return ValidationScore(
                layer=ValidationLayer.VERSION_COMPATIBILITY,
                score=final_score,
                confidence=0.9,
                evidence={
                    "minecraft_version": minecraft_version,
                    "deprecated_features": deprecated_features,
                    "base_score": compatibility_scores.get(minecraft_version, 0.3)
                },
                metadata={
                    "deprecated_penalty": min(0.3, len(deprecated_features) * 0.1) if deprecated_features else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Error in version compatibility validation: {e}")
            return ValidationScore(
                layer=ValidationLayer.VERSION_COMPATIBILITY,
                score=0.5,
                confidence=0.0,
                evidence={"error": str(e)},
                metadata={"validation_error": True}
            )
    
    async def _validate_usage_statistics(self, item_data: Dict[str, Any]) -> ValidationScore:
        """Validate based on usage statistics."""
        try:
            usage_count = item_data.get("usage_count", 0)
            success_rate = item_data.get("success_rate", 0.5)
            
            # Usage score (logarithmic scale to prevent too much weight on very high numbers)
            usage_score = min(1.0, np.log10(max(1, usage_count)) / 3.0)  # 1000 uses = max score
            
            # Success rate score
            success_score = success_rate
            
            # Combined score with emphasis on success rate
            final_score = (success_score * 0.7 + usage_score * 0.3)
            
            # Confidence based on usage count
            confidence = min(1.0, usage_count / 50.0)  # 50 uses = full confidence
            
            return ValidationScore(
                layer=ValidationLayer.USAGE_VALIDATION,
                score=final_score,
                confidence=confidence,
                evidence={
                    "usage_count": usage_count,
                    "success_rate": success_rate,
                    "usage_score": usage_score,
                    "success_score": success_score
                },
                metadata={}
            )
            
        except Exception as e:
            logger.error(f"Error in usage statistics validation: {e}")
            return ValidationScore(
                layer=ValidationLayer.USAGE_VALIDATION,
                score=0.5,
                confidence=0.0,
                evidence={"error": str(e)},
                metadata={"validation_error": True}
            )
    
    async def _validate_semantic_consistency(self, item_data: Dict[str, Any]) -> ValidationScore:
        """Validate semantic consistency of the item."""
        try:
            name = item_data.get("name", "")
            description = item_data.get("description", "")
            node_type = item_data.get("node_type", "")
            pattern_type = item_data.get("pattern_type", "")
            
            # Semantic consistency checks
            consistency_score = 0.8  # Base score
            
            # Check if name and description are consistent
            if name and description:
                name_words = set(name.lower().split())
                description_words = set(description.lower().split())
                
                overlap = len(name_words.intersection(description_words))
                if len(name_words) > 0:
                    consistency_score = max(0.3, overlap / len(name_words))
            
            # Check if type matches content
            if node_type and name:
                if node_type in name.lower() or name.lower() in node_type:
                    consistency_score = max(consistency_score, 0.9)
            
            if pattern_type and name:
                if pattern_type in name.lower() or name.lower() in pattern_type:
                    consistency_score = max(consistency_score, 0.9)
            
            # Length consistency (very long or very short descriptions might be suspicious)
            if description:
                desc_len = len(description)
                if 50 <= desc_len <= 500:
                    consistency_score = max(consistency_score, 0.9)
                elif desc_len > 1000:
                    consistency_score = min(consistency_score, 0.6)
            
            return ValidationScore(
                layer=ValidationLayer.SEMANTIC_VALIDATION,
                score=consistency_score,
                confidence=0.6,  # Medium confidence in semantic validation
                evidence={
                    "name": name,
                    "description_length": len(description) if description else 0,
                    "node_type": node_type,
                    "pattern_type": pattern_type,
                    "name_description_overlap": overlap if name and description else 0
                },
                metadata={}
            )
            
        except Exception as e:
            logger.error(f"Error in semantic consistency validation: {e}")
            return ValidationScore(
                layer=ValidationLayer.SEMANTIC_VALIDATION,
                score=0.5,
                confidence=0.0,
                evidence={"error": str(e)},
                metadata={"validation_error": True}
            )
    
    def _calculate_overall_confidence(self, validation_scores: List[ValidationScore]) -> float:
        """Calculate overall confidence from validation layer scores."""
        try:
            if not validation_scores:
                return 0.5  # Default confidence
            
            weighted_sum = 0.0
            total_weight = 0.0
            
            for score in validation_scores:
                weight = self.layer_weights.get(score.layer, 0.1)
                confidence_adjusted_score = score.score * score.confidence
                
                weighted_sum += confidence_adjusted_score * weight
                total_weight += weight
            
            if total_weight == 0:
                return 0.5
            
            overall_confidence = weighted_sum / total_weight
            
            # Ensure within bounds
            return max(0.0, min(1.0, overall_confidence))
            
        except Exception as e:
            logger.error(f"Error calculating overall confidence: {e}")
            return 0.5
    
    def _identify_risk_factors(self, validation_scores: List[ValidationScore]) -> List[str]:
        """Identify risk factors from validation scores."""
        try:
            risk_factors = []
            
            for score in validation_scores:
                if score.score < 0.3:
                    risk_factors.append(f"Low {score.layer.value} score: {score.score:.2f}")
                elif score.confidence < 0.5:
                    risk_factors.append(f"Uncertain {score.layer.value} validation")
                
                # Check for specific risk patterns
                if score.layer == ValidationLayer.EXPERT_VALIDATION and score.score < 0.5:
                    risk_factors.append("No expert validation - potential quality issues")
                
                if score.layer == ValidationLayer.VERSION_COMPATIBILITY and score.score < 0.7:
                    risk_factors.append("Version compatibility concerns")
                
                if score.layer == ValidationLayer.USAGE_VALIDATION and score.confidence < 0.3:
                    risk_factors.append("Insufficient usage data - untested conversion")
            
            return risk_factors
            
        except Exception as e:
            logger.error(f"Error identifying risk factors: {e}")
            return ["Error identifying risk factors"]
    
    def _identify_confidence_factors(self, validation_scores: List[ValidationScore]) -> List[str]:
        """Identify confidence factors from validation scores."""
        try:
            confidence_factors = []
            
            for score in validation_scores:
                if score.score > 0.8:
                    confidence_factors.append(f"High {score.layer.value} score: {score.score:.2f}")
                elif score.confidence > 0.8:
                    confidence_factors.append(f"Confident {score.layer.value} validation")
                
                # Check for specific confidence patterns
                if score.layer == ValidationLayer.EXPERT_VALIDATION and score.score > 0.9:
                    confidence_factors.append("Expert validated - high reliability")
                
                if score.layer == ValidationLayer.COMMUNITY_VALIDATION and score.score > 0.8:
                    confidence_factors.append("Strong community support")
                
                if score.layer == ValidationLayer.HISTORICAL_VALIDATION and score.score > 0.8:
                    confidence_factors.append("Proven track record")
            
            return confidence_factors
            
        except Exception as e:
            logger.error(f"Error identifying confidence factors: {e}")
            return ["Error identifying confidence factors"]
    
    async def _generate_recommendations(
        self,
        validation_scores: List[ValidationScore],
        overall_confidence: float,
        item_data: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on validation results."""
        try:
            recommendations = []
            
            # Overall confidence recommendations
            if overall_confidence < 0.4:
                recommendations.append("Low overall confidence - seek expert review before use")
            elif overall_confidence < 0.7:
                recommendations.append("Moderate confidence - test thoroughly before production use")
            elif overall_confidence > 0.9:
                recommendations.append("High confidence - suitable for immediate use")
            
            # Layer-specific recommendations
            for score in validation_scores:
                if score.layer == ValidationLayer.EXPERT_VALIDATION and score.score < 0.5:
                    recommendations.append("Request expert validation to improve reliability")
                
                if score.layer == ValidationLayer.COMMUNITY_VALIDATION and score.score < 0.6:
                    recommendations.append("Encourage community reviews and feedback")
                
                if score.layer == ValidationLayer.VERSION_COMPATIBILITY and score.score < 0.7:
                    recommendations.append("Update to newer Minecraft version for better compatibility")
                
                if score.layer == ValidationLayer.USAGE_VALIDATION and score.confidence < 0.5:
                    recommendations.append("Increase usage testing to build confidence")
            
            # Item-specific recommendations
            if item_data.get("description", "") == "":
                recommendations.append("Add detailed description to improve validation")
            
            if item_data.get("properties", {}) == {}:
                recommendations.append("Add properties and metadata for better analysis")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["Error generating recommendations"]
    
    def _cache_assessment(self, item_type: str, item_id: str, assessment: ConfidenceAssessment):
        """Cache assessment result."""
        try:
            cache_key = f"{item_type}:{item_id}"
            self.validation_cache[cache_key] = {
                "assessment": assessment,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Limit cache size
            if len(self.validation_cache) > 1000:
                # Remove oldest entries
                oldest_keys = sorted(
                    self.validation_cache.keys(),
                    key=lambda k: self.validation_cache[k]["timestamp"]
                )[:100]
                for key in oldest_keys:
                    del self.validation_cache[key]
                    
        except Exception as e:
            logger.error(f"Error caching assessment: {e}")
    
    def _calculate_feedback_impact(self, feedback_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate impact of feedback on validation scores."""
        try:
            feedback_type = feedback_data.get("type", "")
            feedback_value = feedback_data.get("value", "")
            
            impact = {
                ValidationLayer.EXPERT_VALIDATION: 0.0,
                ValidationLayer.COMMUNITY_VALIDATION: 0.0,
                ValidationLayer.HISTORICAL_VALIDATION: 0.0,
                ValidationLayer.PATTERN_VALIDATION: 0.0,
                ValidationLayer.CROSS_PLATFORM_VALIDATION: 0.0,
                ValidationLayer.VERSION_COMPATIBILITY: 0.0,
                ValidationLayer.USAGE_VALIDATION: 0.0,
                ValidationLayer.SEMANTIC_VALIDATION: 0.0
            }
            
            # Positive feedback
            if feedback_type == "success" or feedback_value == "positive":
                impact[ValidationLayer.HISTORICAL_VALIDATION] = 0.2
                impact[ValidationLayer.USAGE_VALIDATION] = 0.1
                impact[ValidationLayer.COMMUNITY_VALIDATION] = 0.1
            
            # Negative feedback
            elif feedback_type == "failure" or feedback_value == "negative":
                impact[ValidationLayer.HISTORICAL_VALIDATION] = -0.2
                impact[ValidationLayer.USAGE_VALIDATION] = -0.1
                impact[ValidationLayer.COMMUNITY_VALIDATION] = -0.1
            
            # Expert feedback
            if feedback_data.get("from_expert", False):
                impact[ValidationLayer.EXPERT_VALIDATION] = 0.3 if feedback_value == "positive" else -0.3
            
            # Usage feedback
            if feedback_type == "usage":
                usage_count = feedback_data.get("usage_count", 0)
                if usage_count > 10:
                    impact[ValidationLayer.USAGE_VALIDATION] = 0.2
            
            return {layer: float(value) for layer, value in impact.items()}
            
        except Exception as e:
            logger.error(f"Error calculating feedback impact: {e}")
            # Return neutral impact
            return {layer: 0.0 for layer in ValidationLayer}
    
    def _apply_feedback_to_score(
        self, 
        original_score: ValidationScore, 
        feedback_impact: Dict[str, float]
    ) -> ValidationScore:
        """Apply feedback impact to a validation score."""
        try:
            impact_value = feedback_impact.get(original_score.layer, 0.0)
            new_score = max(0.0, min(1.0, original_score.score + impact_value))
            
            # Update confidence based on feedback
            new_confidence = min(1.0, original_score.confidence + 0.1)  # Feedback increases confidence
            
            return ValidationScore(
                layer=original_score.layer,
                score=new_score,
                confidence=new_confidence,
                evidence={
                    **original_score.evidence,
                    "feedback_applied": True,
                    "feedback_impact": impact_value
                },
                metadata={
                    **original_score.metadata,
                    "original_score": original_score.score,
                    "feedback_adjustment": impact_value
                }
            )
            
        except Exception as e:
            logger.error(f"Error applying feedback to score: {e}")
            return original_score
    
    async def _update_item_confidence(
        self, 
        item_type: str, 
        item_id: str, 
        new_confidence: float, 
        db: AsyncSession
    ):
        """Update item confidence in database."""
        try:
            if item_type == "node":
                await KnowledgeNodeCRUD.update_confidence(db, item_id, new_confidence)
            elif item_type == "relationship":
                await KnowledgeRelationshipCRUD.update_confidence(db, item_id, new_confidence)
            elif item_type == "pattern":
                await ConversionPatternCRUD.update_confidence(db, item_id, new_confidence)
            
        except Exception as e:
            logger.error(f"Error updating item confidence: {e}")
    
    def _analyze_batch_results(
        self, 
        batch_results: Dict[str, ConfidenceAssessment], 
        batch_scores: List[float]
    ) -> Dict[str, Any]:
        """Analyze batch assessment results."""
        try:
            if not batch_scores:
                return {}
            
            return {
                "average_confidence": np.mean(batch_scores),
                "median_confidence": np.median(batch_scores),
                "confidence_std": np.std(batch_scores),
                "min_confidence": min(batch_scores),
                "max_confidence": max(batch_scores),
                "confidence_range": max(batch_scores) - min(batch_scores),
                "high_confidence_count": sum(1 for score in batch_scores if score > 0.8),
                "medium_confidence_count": sum(1 for score in batch_scores if 0.5 <= score <= 0.8),
                "low_confidence_count": sum(1 for score in batch_scores if score < 0.5)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing batch results: {e}")
            return {}
    
    async def _analyze_batch_patterns(
        self, 
        batch_results: Dict[str, ConfidenceAssessment], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Analyze patterns across batch results."""
        try:
            # Collect validation layer performance
            layer_performance = {}
            
            for item_key, assessment in batch_results.items():
                for score in assessment.validation_scores:
                    layer_name = score.layer.value
                    if layer_name not in layer_performance:
                        layer_performance[layer_name] = []
                    layer_performance[layer_name].append(score.score)
            
            # Calculate statistics for each layer
            layer_stats = {}
            for layer_name, scores in layer_performance.items():
                if scores:
                    layer_stats[layer_name] = {
                        "average": np.mean(scores),
                        "median": np.median(scores),
                        "std": np.std(scores),
                        "count": len(scores)
                    }
            
            return {
                "layer_performance": layer_stats,
                "total_items_assessed": len(batch_results),
                "most_consistent_layer": min(
                    layer_stats.items(), 
                    key=lambda x: x[1]["std"] if x[1]["std"] > 0 else float('inf')
                )[0] if layer_stats else None,
                "least_consistent_layer": max(
                    layer_stats.items(), 
                    key=lambda x: x[1]["std"]
                )[0] if layer_stats else None
            }
            
        except Exception as e:
            logger.error(f"Error analyzing batch patterns: {e}")
            return {}
    
    def _generate_batch_recommendations(
        self, 
        batch_results: Dict[str, ConfidenceAssessment], 
        batch_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for batch results."""
        try:
            recommendations = []
            
            avg_confidence = batch_analysis.get("average_confidence", 0.5)
            confidence_std = batch_analysis.get("confidence_std", 0.0)
            
            # Overall recommendations
            if avg_confidence < 0.5:
                recommendations.append("Batch shows low overall confidence - review items before use")
            elif avg_confidence > 0.8:
                recommendations.append("Batch shows high overall confidence - suitable for production use")
            
            # Consistency recommendations
            if confidence_std > 0.3:
                recommendations.append("High confidence variance - investigate outliers")
            elif confidence_std < 0.1:
                recommendations.append("Consistent confidence scores across batch")
            
            # Specific item recommendations
            low_confidence_items = [
                key for key, assessment in batch_results.items()
                if assessment.overall_confidence < 0.4
            ]
            
            if low_confidence_items:
                recommendations.append(f"Review {len(low_confidence_items)} low-confidence items")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating batch recommendations: {e}")
            return ["Error generating batch recommendations"]
    
    def _calculate_confidence_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Calculate confidence score distribution."""
        try:
            distribution = {
                "very_low (0.0-0.2)": 0,
                "low (0.2-0.4)": 0,
                "medium (0.4-0.6)": 0,
                "high (0.6-0.8)": 0,
                "very_high (0.8-1.0)": 0
            }
            
            for score in scores:
                if score <= 0.2:
                    distribution["very_low (0.0-0.2)"] += 1
                elif score <= 0.4:
                    distribution["low (0.2-0.4)"] += 1
                elif score <= 0.6:
                    distribution["medium (0.4-0.6)"] += 1
                elif score <= 0.8:
                    distribution["high (0.6-0.8)"] += 1
                else:
                    distribution["very_high (0.8-1.0)"] += 1
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error calculating confidence distribution: {e}")
            return {}
    
    def _calculate_confidence_trend(self, assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate confidence score trends over time."""
        try:
            if not assessments:
                return {}
            
            # Sort by timestamp
            assessments.sort(key=lambda x: x["timestamp"])
            
            # Extract confidence scores and timestamps
            scores = [assessment["overall_confidence"] for assessment in assessments]
            timestamps = [assessment["timestamp"] for assessment in assessments]
            
            # Calculate trend (simple linear regression slope)
            if len(scores) > 1:
                x = np.arange(len(scores))
                slope = np.polyfit(x, scores, 1)[0]
                
                if slope > 0.01:
                    trend = "improving"
                elif slope < -0.01:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"
            
            return {
                "trend": trend,
                "slope": float(slope) if len(scores) > 1 else 0.0,
                "average_confidence": np.mean(scores),
                "confidence_std": np.std(scores),
                "data_points": len(scores),
                "time_span_days": (
                    datetime.fromisoformat(timestamps[-1]) - datetime.fromisoformat(timestamps[0])
                ).days if len(timestamps) > 1 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating confidence trend: {e}")
            return {"trend": "error", "error": str(e)}
    
    def _analyze_layer_performance(self, assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance of individual validation layers."""
        try:
            # This would analyze which layers are most effective
            # For now, return mock data
            return {
                "most_effective_layers": [
                    "expert_validation",
                    "community_validation",
                    "historical_validation"
                ],
                "least_effective_layers": [
                    "semantic_validation",
                    "usage_validation"
                ],
                "layer_correlation": {
                    "expert_validation": 0.85,
                    "community_validation": 0.72,
                    "historical_validation": 0.68,
                    "pattern_validation": 0.61,
                    "cross_platform_validation": 0.58,
                    "version_compatibility": 0.54,
                    "usage_validation": 0.47,
                    "semantic_validation": 0.32
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing layer performance: {e}")
            return {}
    
    def _generate_trend_insights(
        self, 
        confidence_trend: Dict[str, Any], 
        layer_performance: Dict[str, Any]
    ) -> List[str]:
        """Generate insights from trend analysis."""
        try:
            insights = []
            
            trend = confidence_trend.get("trend", "unknown")
            avg_confidence = confidence_trend.get("average_confidence", 0.5)
            
            # Trend insights
            if trend == "improving":
                insights.append("Confidence scores are improving over time")
            elif trend == "declining":
                insights.append("Confidence scores are declining - investigate quality issues")
            elif trend == "stable":
                insights.append("Confidence scores are stable")
            
            # Level insights
            if avg_confidence > 0.8:
                insights.append("High average confidence - quality system")
            elif avg_confidence < 0.5:
                insights.append("Low average confidence - quality concerns")
            
            # Layer insights
            if layer_performance:
                most_effective = layer_performance.get("most_effective_layers", [])
                if most_effective:
                    insights.append(f"Most effective validation layers: {', '.join(most_effective[:3])}")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating trend insights: {e}")
            return ["Error generating insights"]


# Singleton instance
automated_confidence_scoring_service = AutomatedConfidenceScoringService()
