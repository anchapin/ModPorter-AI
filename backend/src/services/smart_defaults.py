"""
Smart Defaults Engine for v2.5 Milestone

Implements rule-based default selection with pattern matching from historical
conversions and a user preferences learning system.

See: docs/GAP-ANALYSIS-v2.5.md

Pattern: Learning from History
Input: ConversionMode, user_id, historical_data
Output: ConversionSettings with all recommended defaults
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from src.models.conversion_mode import (
    ConversionMode,
    ConversionSettings,
    ModFeatures,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class DefaultSelectionRule(BaseModel):
    """A rule for selecting default settings based on mode and features."""

    name: str
    priority: int = 0  # Higher priority rules are evaluated first
    applies_to_modes: List[ConversionMode]
    condition: Optional[str] = None  # Simple condition expression
    settings_adjustments: Dict[str, Any] = Field(default_factory=dict)


class PatternMatch(BaseModel):
    """Result of matching against historical patterns."""

    pattern_id: str
    pattern_name: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    matched_settings: Dict[str, Any]
    usage_count: int = 0
    success_rate: float = 0.0


class HistoricalConversion(BaseModel):
    """Historical conversion record for pattern learning."""

    conversion_id: str
    user_id: str
    mode: ConversionMode
    features: Dict[str, Any]
    settings_used: Dict[str, Any]
    success: bool
    duration_seconds: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SmartDefaultsResult(BaseModel):
    """Result from smart defaults engine."""

    settings: ConversionSettings
    confidence: float = Field(ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)  # Which rules/patterns contributed
    warnings: List[str] = Field(default_factory=list)


# =============================================================================
# Default Selection Rules (Mode-specific)
# =============================================================================

MODE_DEFAULT_RULES: List[DefaultSelectionRule] = [
    # SIMPLE mode - minimal processing
    DefaultSelectionRule(
        name="simple_minimal_processing",
        priority=10,
        applies_to_modes=[ConversionMode.SIMPLE],
        settings_adjustments={
            "detail_level": "minimal",
            "validation_level": "basic",
            "max_retries": 1,
            "timeout_seconds": 120,
            "parallel_processing": False,
            "quality_threshold": 0.9,
        },
    ),
    # STANDARD mode - balanced processing
    DefaultSelectionRule(
        name="standard_balanced",
        priority=10,
        applies_to_modes=[ConversionMode.STANDARD],
        settings_adjustments={
            "detail_level": "standard",
            "validation_level": "standard",
            "max_retries": 3,
            "timeout_seconds": 300,
            "parallel_processing": True,
            "quality_threshold": 0.8,
        },
    ),
    # COMPLEX mode - detailed processing
    DefaultSelectionRule(
        name="complex_detailed",
        priority=10,
        applies_to_modes=[ConversionMode.COMPLEX],
        settings_adjustments={
            "detail_level": "detailed",
            "validation_level": "strict",
            "max_retries": 5,
            "timeout_seconds": 600,
            "parallel_processing": True,
            "quality_threshold": 0.7,
        },
    ),
    # EXPERT mode - manual review required
    DefaultSelectionRule(
        name="expert_manual_review",
        priority=10,
        applies_to_modes=[ConversionMode.EXPERT],
        settings_adjustments={
            "detail_level": "detailed",
            "validation_level": "strict",
            "enable_auto_fix": False,  # Manual review required
            "max_retries": 3,
            "timeout_seconds": 900,
            "parallel_processing": True,
            "quality_threshold": 0.6,
        },
    ),
]

# Feature-based adjustment rules
FEATURE_ADJUSTMENT_RULES: List[DefaultSelectionRule] = [
    DefaultSelectionRule(
        name="has_items_increase_timeout",
        priority=5,
        applies_to_modes=[ConversionMode.SIMPLE, ConversionMode.STANDARD],
        condition="features.has_items == True",
        settings_adjustments={
            "timeout_seconds": 180,  # Add 60s for item processing
        },
    ),
    DefaultSelectionRule(
        name="has_blocks_increase_timeout",
        priority=5,
        applies_to_modes=[ConversionMode.SIMPLE, ConversionMode.STANDARD],
        condition="features.has_blocks == True",
        settings_adjustments={
            "timeout_seconds": 240,  # Add 60s for block processing
        },
    ),
    DefaultSelectionRule(
        name="has_entities_requires_strict_validation",
        priority=8,
        applies_to_modes=[ConversionMode.STANDARD, ConversionMode.COMPLEX],
        condition="features.has_entities == True",
        settings_adjustments={
            "validation_level": "strict",
            "timeout_seconds": 400,
        },
    ),
    DefaultSelectionRule(
        name="has_multiblock_increase_retries",
        priority=7,
        applies_to_modes=[ConversionMode.COMPLEX, ConversionMode.EXPERT],
        condition="features.has_multiblock == True",
        settings_adjustments={
            "max_retries": 7,
            "timeout_seconds": 800,
        },
    ),
    DefaultSelectionRule(
        name="has_dimensions_expert_mode",
        priority=9,
        applies_to_modes=[ConversionMode.COMPLEX, ConversionMode.EXPERT],
        condition="features.has_dimensions == True",
        settings_adjustments={
            "enable_auto_fix": False,
            "timeout_seconds": 1200,
        },
    ),
]


# =============================================================================
# Pattern Library (Simulated Historical Data)
# =============================================================================

PATTERN_LIBRARY: Dict[str, PatternMatch] = {
    "simple_item_mod": PatternMatch(
        pattern_id="simple_item_mod",
        pattern_name="Simple Item Mod",
        similarity_score=0.95,
        matched_settings={
            "detail_level": "minimal",
            "validation_level": "basic",
            "max_retries": 1,
            "timeout_seconds": 120,
        },
        usage_count=150,
        success_rate=0.98,
    ),
    "standard_block_mod": PatternMatch(
        pattern_id="standard_block_mod",
        pattern_name="Standard Block Mod",
        similarity_score=0.90,
        matched_settings={
            "detail_level": "standard",
            "validation_level": "standard",
            "max_retries": 3,
            "timeout_seconds": 300,
        },
        usage_count=200,
        success_rate=0.95,
    ),
    "complex_multiblock": PatternMatch(
        pattern_id="complex_multiblock",
        pattern_name="Complex Multiblock Mod",
        similarity_score=0.85,
        matched_settings={
            "detail_level": "detailed",
            "validation_level": "strict",
            "max_retries": 5,
            "timeout_seconds": 600,
        },
        usage_count=50,
        success_rate=0.85,
    ),
}


# =============================================================================
# Smart Defaults Engine
# =============================================================================


class SmartDefaultsEngine:
    """
    Rule-based default selection engine with pattern matching and learning.

    Implements the Learning from History pattern:
    - Rule-based: IF mode=SIMPLE THEN detail_level=minimal
    - Pattern-based: Match similar successful conversions
    - Learning: Updates user preferences from conversion history
    """

    def __init__(self):
        self.mode_rules = MODE_DEFAULT_RULES
        self.feature_rules = FEATURE_ADJUSTMENT_RULES
        self.pattern_library = PATTERN_LIBRARY

    async def get_defaults(
        self,
        mode: ConversionMode,
        user_id: Optional[str] = None,
        historical_data: Optional[List[HistoricalConversion]] = None,
        features: Optional[ModFeatures] = None,
    ) -> SmartDefaultsResult:
        """
        Get recommended defaults for a conversion.

        Args:
            mode: The conversion mode (SIMPLE, STANDARD, COMPLEX, EXPERT)
            user_id: Optional user ID for personalized defaults
            historical_data: Optional list of historical conversions for pattern matching
            features: Optional extracted mod features for feature-based adjustments

        Returns:
            SmartDefaultsResult with settings, confidence, and sources
        """
        logger.info(f"Computing smart defaults for mode={mode}, user_id={user_id}")

        sources = []
        settings_dict: Dict[str, Any] = {}
        confidence_factors: List[float] = []

        # Step 1: Apply mode-specific rules (highest priority)
        mode_settings, mode_confidence = self._apply_mode_rules(mode)
        settings_dict.update(mode_settings)
        confidence_factors.append(mode_confidence)
        sources.append(f"mode_rule:{mode.value}")

        # Step 2: Apply feature-based adjustments
        if features:
            feature_settings, feature_confidence = self._apply_feature_rules(mode, features)
            settings_dict.update(feature_settings)
            confidence_factors.append(feature_confidence)
            sources.append("feature_rules")

        # Step 3: Apply pattern matching from historical data
        if historical_data:
            pattern_settings, pattern_confidence = self._apply_pattern_matching(
                mode, historical_data
            )
            if pattern_settings:
                settings_dict.update(pattern_settings)
                confidence_factors.append(pattern_confidence)
                sources.append("historical_patterns")

        # Step 4: Apply user preferences if available
        if user_id:
            prefs = self._get_user_preferences(user_id)
            if prefs:
                user_settings, user_confidence = self._apply_user_preferences(mode, prefs)
                settings_dict.update(user_settings)
                confidence_factors.append(user_confidence)
                sources.append(f"user_preferences:{user_id}")

        # Calculate overall confidence
        overall_confidence = (
            sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
        )

        # Build final settings
        final_settings = ConversionSettings(
            mode=mode,
            detail_level=settings_dict.get("detail_level", "standard"),
            validation_level=settings_dict.get("validation_level", "standard"),
            enable_auto_fix=settings_dict.get("enable_auto_fix", True),
            enable_ai_assistance=settings_dict.get("enable_ai_assistance", True),
            max_retries=settings_dict.get("max_retries", 3),
            timeout_seconds=settings_dict.get("timeout_seconds", 300),
            parallel_processing=settings_dict.get("parallel_processing", False),
            quality_threshold=settings_dict.get("quality_threshold", 0.8),
        )

        return SmartDefaultsResult(
            settings=final_settings,
            confidence=min(overall_confidence, 1.0),
            sources=sources,
        )

    def _apply_mode_rules(self, mode: ConversionMode) -> tuple[Dict[str, Any], float]:
        """Apply mode-specific rules to get base settings."""
        settings = {}

        # Find highest priority rule for this mode
        matching_rules = [r for r in self.mode_rules if mode in r.applies_to_modes]
        matching_rules.sort(key=lambda r: r.priority, reverse=True)

        if matching_rules:
            rule = matching_rules[0]
            settings = rule.settings_adjustments.copy()
            confidence = 0.8 + (rule.priority / 100)  # Base 0.8 + priority bonus
            return settings, min(confidence, 1.0)

        # Default fallback
        return {"detail_level": "standard", "validation_level": "standard"}, 0.5

    def _apply_feature_rules(
        self, mode: ConversionMode, features: ModFeatures
    ) -> tuple[Dict[str, Any], float]:
        """Apply feature-based adjustment rules."""
        settings = {}
        matched_rules = 0

        for rule in self.feature_rules:
            if mode not in rule.applies_to_modes:
                continue

            # Evaluate simple condition if present
            if rule.condition:
                if not self._evaluate_condition(rule.condition, features):
                    continue

            settings.update(rule.settings_adjustments)
            matched_rules += 1

        # Confidence based on how many rules matched
        confidence = 0.6 + (matched_rules * 0.05) if matched_rules > 0 else 0.5
        return settings, min(confidence, 0.9)

    def _apply_pattern_matching(
        self,
        mode: ConversionMode,
        historical_data: List[HistoricalConversion],
    ) -> tuple[Dict[str, Any], float]:
        """Apply pattern matching from historical conversions."""
        if not historical_data:
            return {}, 0.0

        # Find similar successful conversions
        similar_conversions = [c for c in historical_data if c.mode == mode and c.success]

        if not similar_conversions:
            return {}, 0.0

        # Aggregate settings from similar conversions
        settings_aggregate: Dict[str, Any] = {}
        for conv in similar_conversions[:10]:  # Use last 10 similar conversions
            for key, value in conv.settings_used.items():
                if key not in settings_aggregate:
                    settings_aggregate[key] = []
                settings_aggregate[key].append(value)

        # Average the settings
        averaged_settings = {}
        for key, values in settings_aggregate.items():
            if values:
                if isinstance(values[0], int):
                    # Integer fields: use int average
                    averaged_settings[key] = int(sum(values) / len(values))
                elif isinstance(values[0], float):
                    averaged_settings[key] = sum(values) / len(values)
                else:
                    averaged_settings[key] = values[0]  # Use most common

        # Calculate confidence based on sample size and success rate
        avg_success_rate = sum(c.success for c in similar_conversions) / len(similar_conversions)
        confidence = min(0.7 + (len(similar_conversions) * 0.02), 0.9) * avg_success_rate

        return averaged_settings, confidence

    def _get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user preferences (placeholder for Redis enhancement)."""
        # In production, this would fetch from Redis or database
        # For now, returns None (will be enhanced with user_preferences.py)
        return None

    def _apply_user_preferences(
        self,
        mode: ConversionMode,
        preferences: Dict[str, Any],
    ) -> tuple[Dict[str, Any], float]:
        """Apply user-specific preferences."""
        # Filter preferences to only valid settings fields
        valid_fields = {
            "detail_level",
            "validation_level",
            "enable_auto_fix",
            "enable_ai_assistance",
            "max_retries",
            "timeout_seconds",
            "parallel_processing",
            "quality_threshold",
        }

        filtered_prefs = {k: v for k, v in preferences.items() if k in valid_fields}

        return filtered_prefs, 0.85  # User preferences have high confidence

    def _evaluate_condition(self, condition: str, features: ModFeatures) -> bool:
        """Evaluate a simple condition expression against features."""
        try:
            # Simple condition parser for common patterns
            # e.g., "features.has_items == True"
            if "features.has_items" in condition:
                return features.has_items
            elif "features.has_blocks" in condition:
                return features.has_blocks
            elif "features.has_entities" in condition:
                return features.has_entities
            elif "features.has_multiblock" in condition:
                return features.has_multiblock
            elif "features.has_dimensions" in condition:
                return features.has_dimensions
            return False
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return False

    def learn_from_conversion(
        self,
        conversion: HistoricalConversion,
    ) -> None:
        """
        Learn from a completed conversion to improve future defaults.

        This updates the pattern library based on successful conversions.
        In production, this would persist to Redis or a database.
        """
        logger.info(f"Learning from conversion {conversion.conversion_id}")

        # Create a new pattern from the conversion
        new_pattern = PatternMatch(
            pattern_id=f"learned_{conversion.conversion_id}",
            pattern_name=f"Learned Pattern {conversion.mode.value}",
            similarity_score=0.8,
            matched_settings=conversion.settings_used,
            usage_count=1,
            success_rate=1.0 if conversion.success else 0.0,
        )

        # In production, this would be persisted
        # For now, we just log the learning
        logger.debug(f"Learned new pattern: {new_pattern.pattern_id}")

    def get_pattern_suggestions(
        self,
        features: ModFeatures,
    ) -> List[PatternMatch]:
        """
        Get pattern suggestions based on mod features.

        Returns patterns from the library that match the given features.
        """
        suggestions = []

        # Priority-based matching: most specific first
        if features.has_multiblock:
            suggestions.append(self.pattern_library.get("complex_multiblock"))
        elif features.has_entities or features.has_blocks:
            suggestions.append(self.pattern_library.get("standard_block_mod"))
        elif features.has_items:
            suggestions.append(self.pattern_library.get("simple_item_mod"))

        return [s for s in suggestions if s is not None]


# =============================================================================
# Singleton Instance
# =============================================================================

_smart_defaults_engine: Optional[SmartDefaultsEngine] = None


def get_smart_defaults_engine() -> SmartDefaultsEngine:
    """Get singleton SmartDefaultsEngine instance."""
    global _smart_defaults_engine
    if _smart_defaults_engine is None:
        _smart_defaults_engine = SmartDefaultsEngine()
    return _smart_defaults_engine
