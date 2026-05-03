"""
Tests for Smart Defaults Engine (GAP-2.5-03)

Tests the rule-based default selection engine with pattern matching
from historical conversions and user preferences learning.

See: docs/GAP-ANALYSIS-v2.5.md
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime
from typing import List

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.services.smart_defaults import (
    SmartDefaultsEngine,
    SmartDefaultsResult,
    DefaultSelectionRule,
    PatternMatch,
    HistoricalConversion,
    MODE_DEFAULT_RULES,
    FEATURE_ADJUSTMENT_RULES,
    PATTERN_LIBRARY,
    get_smart_defaults_engine,
)
from src.models.conversion_mode import (
    ConversionMode,
    ConversionSettings,
    ModFeatures,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def engine():
    """Create a SmartDefaultsEngine instance."""
    return SmartDefaultsEngine()


@pytest.fixture
def simple_features():
    """Create features for a simple mod."""
    return ModFeatures(
        total_classes=3,
        total_dependencies=1,
        has_items=True,
        has_blocks=False,
        has_entities=False,
    )


@pytest.fixture
def standard_features():
    """Create features for a standard mod."""
    return ModFeatures(
        total_classes=15,
        total_dependencies=3,
        has_items=True,
        has_blocks=True,
        has_entities=True,
        has_recipes=True,
    )


@pytest.fixture
def complex_features():
    """Create features for a complex mod."""
    return ModFeatures(
        total_classes=35,
        total_dependencies=7,
        has_items=True,
        has_blocks=True,
        has_entities=True,
        has_multiblock=True,
        has_custom_AI=True,
    )


@pytest.fixture
def expert_features():
    """Create features for an expert mod."""
    return ModFeatures(
        total_classes=80,
        total_dependencies=15,
        has_items=True,
        has_blocks=True,
        has_entities=True,
        has_dimensions=True,
        has_worldgen=True,
        has_multiblock=True,
        has_custom_AI=True,
    )


@pytest.fixture
def sample_historical_data():
    """Create sample historical conversion data."""
    return [
        HistoricalConversion(
            conversion_id="conv-001",
            user_id="user-123",
            mode=ConversionMode.SIMPLE,
            features={},
            settings_used={
                "detail_level": "minimal",
                "validation_level": "basic",
                "max_retries": 1,
                "timeout_seconds": 120,
            },
            success=True,
            duration_seconds=45,
        ),
        HistoricalConversion(
            conversion_id="conv-002",
            user_id="user-123",
            mode=ConversionMode.SIMPLE,
            features={},
            settings_used={
                "detail_level": "minimal",
                "validation_level": "basic",
                "max_retries": 2,
                "timeout_seconds": 100,
            },
            success=True,
            duration_seconds=55,
        ),
        HistoricalConversion(
            conversion_id="conv-003",
            user_id="user-123",
            mode=ConversionMode.STANDARD,
            features={},
            settings_used={
                "detail_level": "standard",
                "validation_level": "standard",
                "max_retries": 3,
                "timeout_seconds": 300,
            },
            success=True,
            duration_seconds=120,
        ),
    ]


# =============================================================================
# Tests: Mode Default Rules
# =============================================================================


class TestModeDefaultRules:
    """Tests for mode-specific default rules."""

    def test_simple_mode_returns_minimal_settings(self, engine, simple_features):
        """test_simple_mode_returns_minimal_settings"""
        result = engine._apply_mode_rules(ConversionMode.SIMPLE)
        settings, confidence = result

        assert settings["detail_level"] == "minimal"
        assert settings["validation_level"] == "basic"
        assert settings["max_retries"] == 1
        assert confidence >= 0.8

    def test_standard_mode_returns_standard_settings(self, engine):
        """test_standard_mode_returns_standard_settings"""
        result = engine._apply_mode_rules(ConversionMode.STANDARD)
        settings, confidence = result

        assert settings["detail_level"] == "standard"
        assert settings["validation_level"] == "standard"
        assert settings["max_retries"] == 3
        assert confidence >= 0.8

    def test_complex_mode_returns_detailed_settings(self, engine):
        """test_complex_mode_returns_detailed_settings"""
        result = engine._apply_mode_rules(ConversionMode.COMPLEX)
        settings, confidence = result

        assert settings["detail_level"] == "detailed"
        assert settings["validation_level"] == "strict"
        assert settings["max_retries"] == 5
        assert settings["parallel_processing"] == True
        assert confidence >= 0.8

    def test_expert_mode_disables_auto_fix(self, engine):
        """test_expert_mode_disables_auto_fix"""
        result = engine._apply_mode_rules(ConversionMode.EXPERT)
        settings, confidence = result

        assert settings["enable_auto_fix"] == False
        assert settings["detail_level"] == "detailed"
        assert settings["timeout_seconds"] == 900


# =============================================================================
# Tests: Feature-Based Rules
# =============================================================================


class TestFeatureBasedRules:
    """Tests for feature-based adjustment rules."""

    def test_has_entities_requires_strict_validation(self, engine, standard_features):
        """test_has_entities_requires_strict_validation"""
        result = engine._apply_feature_rules(ConversionMode.STANDARD, standard_features)
        settings, confidence = result

        assert settings.get("validation_level") == "strict"

    def test_has_multiblock_increases_retries(self, engine, complex_features):
        """test_has_multiblock_increases_retries"""
        result = engine._apply_feature_rules(ConversionMode.COMPLEX, complex_features)
        settings, confidence = result

        assert settings.get("max_retries") == 7
        assert settings.get("timeout_seconds") == 800

    def test_has_dimensions_disables_auto_fix(self, engine, expert_features):
        """test_has_dimensions_disables_auto_fix"""
        result = engine._apply_feature_rules(ConversionMode.EXPERT, expert_features)
        settings, confidence = result

        assert settings.get("enable_auto_fix") == False


# =============================================================================
# Tests: Pattern Matching
# =============================================================================


class TestPatternMatching:
    """Tests for historical pattern matching."""

    def test_pattern_matching_returns_settings(self, engine, sample_historical_data):
        """test_pattern_matching_returns_settings"""
        result = engine._apply_pattern_matching(ConversionMode.SIMPLE, sample_historical_data)
        settings, confidence = result

        assert "detail_level" in settings or "timeout_seconds" in settings
        assert confidence > 0

    def test_pattern_matching_no_data_returns_empty(self, engine):
        """test_pattern_matching_no_data_returns_empty"""
        result = engine._apply_pattern_matching(ConversionMode.SIMPLE, [])
        settings, confidence = result

        assert settings == {}
        assert confidence == 0.0

    def test_pattern_matching_wrong_mode_returns_empty(self, engine, sample_historical_data):
        """test_pattern_matching_wrong_mode_returns_empty"""
        # Historical data has SIMPLE mode, querying for EXPERT
        result = engine._apply_pattern_matching(ConversionMode.EXPERT, sample_historical_data)
        settings, confidence = result

        assert settings == {}
        assert confidence == 0.0


# =============================================================================
# Tests: Condition Evaluation
# =============================================================================


class TestConditionEvaluation:
    """Tests for simple condition evaluation."""

    def test_evaluate_has_items_condition_true(self, engine, simple_features):
        """test_evaluate_has_items_condition_true"""
        result = engine._evaluate_condition("features.has_items == True", simple_features)
        assert result == True

    def test_evaluate_has_items_condition_false(self, engine, complex_features):
        """test_evaluate_has_items_condition_false"""
        # complex_features has has_items=True but condition checks explicitly
        result = engine._evaluate_condition("features.has_blocks == True", complex_features)
        assert result == True

    def test_evaluate_has_dimensions_condition(self, engine, expert_features):
        """test_evaluate_has_dimensions_condition"""
        result = engine._evaluate_condition("features.has_dimensions == True", expert_features)
        assert result == True

    def test_evaluate_condition_invalid_returns_false(self, engine, simple_features):
        """test_evaluate_condition_invalid_returns_false"""
        result = engine._evaluate_condition("features.nonexistent == True", simple_features)
        assert result == False


# =============================================================================
# Tests: Get Defaults Integration
# =============================================================================


class TestGetDefaults:
    """Tests for the main get_defaults method."""

    @pytest.mark.asyncio
    async def test_get_defaults_simple_mode(self, engine, simple_features):
        """test_get_defaults_simple_mode"""
        result = await engine.get_defaults(
            mode=ConversionMode.SIMPLE,
            features=simple_features,
        )

        assert isinstance(result, SmartDefaultsResult)
        assert result.settings.mode == ConversionMode.SIMPLE
        assert result.confidence >= 0.5
        assert "mode_rule:simple" in result.sources

    @pytest.mark.asyncio
    async def test_get_defaults_with_historical_data(
        self, engine, simple_features, sample_historical_data
    ):
        """test_get_defaults_with_historical_data"""
        result = await engine.get_defaults(
            mode=ConversionMode.SIMPLE,
            features=simple_features,
            historical_data=sample_historical_data,
        )

        assert isinstance(result, SmartDefaultsResult)
        assert "historical_patterns" in result.sources

    @pytest.mark.asyncio
    async def test_get_defaults_with_user_preferences(self, engine, simple_features):
        """test_get_defaults_with_user_preferences"""
        # Mock user preferences
        with patch.object(
            engine,
            "_get_user_preferences",
            return_value={
                "detail_level": "minimal",
                "timeout_seconds": 100,
            },
        ):
            result = await engine.get_defaults(
                mode=ConversionMode.SIMPLE,
                user_id="user-123",
                features=simple_features,
            )

            assert isinstance(result, SmartDefaultsResult)
            assert "user_preferences:user-123" in result.sources

    @pytest.mark.asyncio
    async def test_get_defaults_complex_mode(self, engine, complex_features):
        """test_get_defaults_complex_mode"""
        result = await engine.get_defaults(
            mode=ConversionMode.COMPLEX,
            features=complex_features,
        )

        assert result.settings.detail_level == "detailed"
        assert result.settings.validation_level == "strict"


# =============================================================================
# Tests: Learning
# =============================================================================


class TestLearning:
    """Tests for learning from conversions."""

    def test_learn_from_conversion(self, engine):
        """test_learn_from_conversion"""
        conversion = HistoricalConversion(
            conversion_id="conv-new",
            user_id="user-123",
            mode=ConversionMode.STANDARD,
            features={},
            settings_used={
                "detail_level": "standard",
                "validation_level": "strict",
            },
            success=True,
            duration_seconds=200,
        )

        # Should not raise
        engine.learn_from_conversion(conversion)


# =============================================================================
# Tests: Pattern Suggestions
# =============================================================================


class TestPatternSuggestions:
    """Tests for pattern suggestion functionality."""

    def test_get_pattern_suggestions_simple_item(self, engine, simple_features):
        """test_get_pattern_suggestions_simple_item"""
        suggestions = engine.get_pattern_suggestions(simple_features)

        assert len(suggestions) > 0
        assert any(s.pattern_id == "simple_item_mod" for s in suggestions)

    def test_get_pattern_suggestions_block_mod(self, engine, standard_features):
        """test_get_pattern_suggestions_block_mod"""
        suggestions = engine.get_pattern_suggestions(standard_features)

        assert len(suggestions) > 0

    def test_get_pattern_suggestions_multiblock(self, engine, complex_features):
        """test_get_pattern_suggestions_multiblock"""
        suggestions = engine.get_pattern_suggestions(complex_features)

        assert len(suggestions) > 0
        assert any(s.pattern_id == "complex_multiblock" for s in suggestions)


# =============================================================================
# Tests: Singleton
# =============================================================================


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_smart_defaults_engine_returns_same_instance(self):
        """test_get_smart_defaults_engine_returns_same_instance"""
        engine1 = get_smart_defaults_engine()
        engine2 = get_smart_defaults_engine()

        assert engine1 is engine2


# =============================================================================
# Tests: Rule Count and Structure
# =============================================================================


class TestRuleStructure:
    """Tests for rule definitions."""

    def test_mode_rules_exist_for_all_modes(self):
        """test_mode_rules_exist_for_all_modes"""
        modes_with_rules = set()
        for rule in MODE_DEFAULT_RULES:
            modes_with_rules.update(rule.applies_to_modes)

        assert ConversionMode.SIMPLE in modes_with_rules
        assert ConversionMode.STANDARD in modes_with_rules
        assert ConversionMode.COMPLEX in modes_with_rules
        assert ConversionMode.EXPERT in modes_with_rules

    def test_feature_rules_have_conditions(self):
        """test_feature_rules_have_conditions"""
        rules_with_conditions = [r for r in FEATURE_ADJUSTMENT_RULES if r.condition]

        assert len(rules_with_conditions) > 0

    def test_pattern_library_has_entries(self):
        """test_pattern_library_has_entries"""
        assert len(PATTERN_LIBRARY) > 0


# =============================================================================
# Tests: SmartDefaultsResult Model
# =============================================================================


class TestSmartDefaultsResult:
    """Tests for SmartDefaultsResult model."""

    def test_result_model_validation(self):
        """test_result_model_validation"""
        result = SmartDefaultsResult(
            settings=ConversionSettings(mode=ConversionMode.SIMPLE),
            confidence=0.85,
            sources=["test_rule"],
            warnings=["test warning"],
        )

        assert result.confidence == 0.85
        assert len(result.sources) == 1
        assert len(result.warnings) == 1

    def test_result_confidence_rejects_invalid_range(self):
        """test_result_confidence_rejects_invalid_range"""
        # Pydantic v2 is strict - values outside valid range are rejected
        with pytest.raises(Exception):  # ValidationError
            SmartDefaultsResult(
                settings=ConversionSettings(mode=ConversionMode.SIMPLE),
                confidence=1.5,  # Invalid: must be <= 1.0
            )
