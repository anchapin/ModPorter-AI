"""
Smart Defaults Engine - Enhanced Version

Advanced smart defaults system with:
- Settings inference from mod analysis
- Pattern-based defaults from successful conversions
- User preference learning
- Context-aware configuration
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ConversionContext:
    """Context for smart defaults inference."""

    # Mod characteristics
    mod_size: str = "medium"  # small, medium, large, very_large
    mod_complexity: float = 0.5  # 0.0 to 1.0
    mod_type: str = "unknown"  # tech, magic, adventure, utility, etc.
    has_dependencies: bool = False
    dependency_count: int = 0

    # Feature flags
    has_entities: bool = False
    has_multiblock: bool = False
    has_machines: bool = False
    has_dimensions: bool = False
    has_custom_ai: bool = False

    # User context
    user_experience: str = "intermediate"  # beginner, intermediate, expert
    conversion_purpose: str = "personal"  # personal, community, production

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mod_size": self.mod_size,
            "mod_complexity": self.mod_complexity,
            "mod_type": self.mod_type,
            "has_dependencies": self.has_dependencies,
            "dependency_count": self.dependency_count,
            "has_entities": self.has_entities,
            "has_multiblock": self.has_multiblock,
            "has_machines": self.has_machines,
            "has_dimensions": self.has_dimensions,
            "has_custom_ai": self.has_custom_ai,
            "user_experience": self.user_experience,
            "conversion_purpose": self.conversion_purpose,
        }


@dataclass
class SmartDefaultsResult:
    """Result of smart defaults inference."""

    settings: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    reasoning: List[str] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    source: str = "inference"  # inference, pattern, user_history, hybrid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "settings": self.settings,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
            "source": self.source,
        }


class SettingsInferenceEngine:
    """
    Infers optimal conversion settings from mod analysis.

    Uses rule-based and ML-based approaches to determine
    the best settings for each conversion.
    """

    def __init__(self):
        # Inference rules
        self.rules = self._initialize_rules()
        logger.info("SettingsInferenceEngine initialized")

    def _initialize_rules(self) -> List[Dict[str, Any]]:
        """Initialize inference rules."""
        return [
            # Size-based rules
            {
                "name": "large_mod_comprehensive",
                "condition": lambda ctx: ctx.mod_size == "large"
                or ctx.mod_size == "very_large",
                "action": {"detail_level": "comprehensive"},
                "reason": "Large mods require comprehensive detail",
            },
            {
                "name": "small_mod_fast",
                "condition": lambda ctx: ctx.mod_size == "small",
                "action": {"optimization": "speed"},
                "reason": "Small mods optimized for speed",
            },
            # Complexity-based rules
            {
                "name": "high_complexity_accuracy",
                "condition": lambda ctx: ctx.mod_complexity > 0.7,
                "action": {"optimization": "accuracy", "validation_level": "strict"},
                "reason": "High complexity requires accuracy over speed",
            },
            # Feature-based rules
            {
                "name": "multiblock_review",
                "condition": lambda ctx: ctx.has_multiblock,
                "action": {"error_handling": "review"},
                "reason": "Multiblock structures need manual review",
            },
            {
                "name": "custom_ai_detailed",
                "condition": lambda ctx: ctx.has_custom_ai,
                "action": {"detail_level": "comprehensive"},
                "reason": "Custom AI requires detailed conversion",
            },
            {
                "name": "dimensions_strict",
                "condition": lambda ctx: ctx.has_dimensions,
                "action": {"validation_level": "strict"},
                "reason": "Dimensions require strict validation",
            },
            # User experience rules
            {
                "name": "beginner_auto_fix",
                "condition": lambda ctx: ctx.user_experience == "beginner",
                "action": {"error_handling": "auto-fix"},
                "reason": "Beginners prefer automatic fixes",
            },
            {
                "name": "expert_manual",
                "condition": lambda ctx: ctx.user_experience == "expert",
                "action": {"error_handling": "manual", "include_source": True},
                "reason": "Experts prefer manual control",
            },
            # Purpose-based rules
            {
                "name": "production_strict",
                "condition": lambda ctx: ctx.conversion_purpose == "production",
                "action": {"validation_level": "strict", "include_report": True},
                "reason": "Production use requires strict validation",
            },
        ]

    def infer_settings(self, context: ConversionContext) -> SmartDefaultsResult:
        """
        Infer optimal settings from context.

        Args:
            context: Conversion context

        Returns:
            SmartDefaultsResult with inferred settings
        """
        settings = {}
        reasoning = []
        confidence = 1.0

        # Apply rules
        for rule in self.rules:
            if rule["condition"](context):
                settings.update(rule["action"])
                reasoning.append(rule["reason"])

        # Calculate confidence based on how many rules matched
        match_count = len(reasoning)
        if match_count == 0:
            confidence = 0.5  # Low confidence if no rules matched
        elif match_count < 3:
            confidence = 0.8
        else:
            confidence = 0.95

        # Generate alternatives
        alternatives = self._generate_alternatives(settings, context)

        return SmartDefaultsResult(
            settings=settings,
            confidence=confidence,
            reasoning=reasoning,
            alternatives=alternatives,
            source="inference",
        )

    def _generate_alternatives(
        self,
        base_settings: Dict[str, Any],
        context: ConversionContext,
    ) -> List[Dict[str, Any]]:
        """Generate alternative setting configurations."""
        alternatives = []

        # Speed-focused alternative
        if context.mod_complexity < 0.5:
            alternatives.append(
                {
                    "name": "Speed Focused",
                    "settings": {**base_settings, "optimization": "speed"},
                    "tradeoff": "Faster conversion, may miss edge cases",
                }
            )

        # Quality-focused alternative
        alternatives.append(
            {
                "name": "Quality Focused",
                "settings": {
                    **base_settings,
                    "optimization": "accuracy",
                    "validation_level": "strict",
                },
                "tradeoff": "Higher quality, slower conversion",
            }
        )

        return alternatives


class PatternBasedDefaults:
    """
    Learns defaults from successful conversion patterns.

    Analyzes historical conversion data to identify
    patterns that lead to successful conversions.
    """

    def __init__(self):
        self.conversion_history: List[Dict[str, Any]] = []
        self.pattern_cache: Dict[str, Dict[str, Any]] = {}
        logger.info("PatternBasedDefaults initialized")

    def record_conversion(
        self,
        mod_features: Dict[str, Any],
        settings_used: Dict[str, Any],
        success: bool,
        quality_score: float,
    ):
        """Record a conversion for pattern learning."""
        self.conversion_history.append(
            {
                "mod_features": mod_features,
                "settings_used": settings_used,
                "success": success,
                "quality_score": quality_score,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Update pattern cache
        self._update_patterns(mod_features, settings_used, success, quality_score)

        # Keep only last 1000 conversions
        if len(self.conversion_history) > 1000:
            self.conversion_history = self.conversion_history[-1000:]

    def _update_patterns(
        self,
        mod_features: Dict[str, Any],
        settings: Dict[str, Any],
        success: bool,
        quality_score: float,
    ):
        """Update pattern cache based on conversion result."""
        # Create pattern key from mod features
        pattern_key = self._create_pattern_key(mod_features)

        if pattern_key not in self.pattern_cache:
            self.pattern_cache[pattern_key] = {
                "successful_settings": [],
                "failed_settings": [],
                "avg_quality": 0.0,
                "count": 0,
            }

        cache = self.pattern_cache[pattern_key]
        cache["count"] += 1

        if success and quality_score >= 0.8:
            cache["successful_settings"].append(settings)
        else:
            cache["failed_settings"].append(settings)

        # Update average quality
        total_quality = cache["avg_quality"] * (cache["count"] - 1) + quality_score
        cache["avg_quality"] = total_quality / cache["count"]

    def _create_pattern_key(self, mod_features: Dict[str, Any]) -> str:
        """Create pattern key from mod features."""
        # Simplified pattern key based on key features
        features = []

        if mod_features.get("class_count", 0) > 50:
            features.append("large")
        elif mod_features.get("class_count", 0) > 20:
            features.append("medium")
        else:
            features.append("small")

        if mod_features.get("has_multiblock", False):
            features.append("multiblock")
        if mod_features.get("has_entities", False):
            features.append("entities")
        if mod_features.get("has_dimensions", False):
            features.append("dimensions")

        return "_".join(features) or "default"

    def get_defaults_for_pattern(
        self,
        mod_features: Dict[str, Any],
    ) -> SmartDefaultsResult:
        """Get defaults based on similar successful conversions."""
        pattern_key = self._create_pattern_key(mod_features)

        if pattern_key not in self.pattern_cache:
            return SmartDefaultsResult(
                settings={},
                confidence=0.0,
                reasoning=["No similar conversions found"],
                source="pattern",
            )

        cache = self.pattern_cache[pattern_key]

        if not cache["successful_settings"]:
            return SmartDefaultsResult(
                settings={},
                confidence=0.0,
                reasoning=["No successful conversions for this pattern"],
                source="pattern",
            )

        # Find most common successful settings
        settings = self._find_common_settings(cache["successful_settings"])

        reasoning = [
            f"Based on {len(cache['successful_settings'])} successful conversions",
            f"Pattern: {pattern_key}",
            f"Average quality: {cache['avg_quality']:.0%}",
        ]

        return SmartDefaultsResult(
            settings=settings,
            confidence=min(0.95, 0.5 + len(cache["successful_settings"]) * 0.1),
            reasoning=reasoning,
            source="pattern",
        )

    def _find_common_settings(
        self,
        successful_settings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Find most common settings from successful conversions."""
        if not successful_settings:
            return {}

        # Count setting values
        counts = defaultdict(lambda: defaultdict(int))

        for settings in successful_settings:
            for key, value in settings.items():
                counts[key][str(value)] += 1

        # Find most common value for each setting
        result = {}
        for key, value_counts in counts.items():
            most_common = max(value_counts.items(), key=lambda x: x[1])[0]
            # Convert back to original type
            if most_common == "True":
                result[key] = True
            elif most_common == "False":
                result[key] = False
            elif most_common.isdigit():
                result[key] = int(most_common)
            else:
                result[key] = most_common

        return result


class UserPreferenceLearner:
    """
    Learns user preferences from conversion history.

    Personalizes defaults based on individual user's
    past choices and feedback.
    """

    def __init__(self):
        self.user_profiles: Dict[str, Dict[str, Any]] = {}
        logger.info("UserPreferenceLearner initialized")

    def record_user_choice(
        self,
        user_id: str,
        suggested_settings: Dict[str, Any],
        actual_settings: Dict[str, Any],
        feedback: Optional[str] = None,
    ):
        """Record user's choice compared to suggestions."""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                "preferences": {},
                "overrides": [],
                "feedback_history": [],
                "conversion_count": 0,
            }

        profile = self.user_profiles[user_id]
        profile["conversion_count"] += 1

        # Track overrides
        for key in actual_settings:
            if (
                key in suggested_settings
                and actual_settings[key] != suggested_settings[key]
            ):
                profile["overrides"].append(
                    {
                        "setting": key,
                        "suggested": suggested_settings[key],
                        "actual": actual_settings[key],
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # Track feedback
        if feedback:
            profile["feedback_history"].append(
                {
                    "feedback": feedback,
                    "settings": actual_settings,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Update preferences
        self._update_preferences(user_id)

    def _update_preferences(self, user_id: str):
        """Update user preferences based on history."""
        profile = self.user_profiles[user_id]

        if len(profile["overrides"]) < 3:
            return  # Not enough data

        # Analyze override patterns
        setting_overrides = defaultdict(lambda: defaultdict(int))

        for override in profile["overrides"][-50:]:  # Last 50 overrides
            setting_overrides[override["setting"]][str(override["actual"])] += 1

        # Identify consistent preferences
        for setting, value_counts in setting_overrides.items():
            most_common, count = max(value_counts.items(), key=lambda x: x[1])

            if count >= 3:  # Consistent preference
                profile["preferences"][setting] = most_common

    def get_personalized_defaults(
        self,
        user_id: str,
        base_settings: Dict[str, Any],
    ) -> SmartDefaultsResult:
        """Get personalized defaults for a user."""
        if user_id not in self.user_profiles:
            return SmartDefaultsResult(
                settings=base_settings,
                confidence=1.0,
                reasoning=["Using base defaults (new user)"],
                source="user_history",
            )

        profile = self.user_profiles[user_id]
        settings = base_settings.copy()
        reasoning = []

        # Apply learned preferences
        for setting, value in profile["preferences"].items():
            if setting in settings:
                old_value = settings[setting]
                settings[setting] = value
                reasoning.append(
                    f"User prefers {setting}={value} (overrode {old_value})"
                )

        confidence = 0.7 if profile["conversion_count"] < 10 else 0.9

        return SmartDefaultsResult(
            settings=settings,
            confidence=confidence,
            reasoning=reasoning,
            source="user_history",
        )


class SmartDefaultsEngine:
    """
    Main smart defaults engine combining all approaches.

    Combines:
    - Settings inference from context
    - Pattern-based defaults from history
    - User preference learning
    """

    def __init__(self):
        self.inference_engine = SettingsInferenceEngine()
        self.pattern_defaults = PatternBasedDefaults()
        self.user_learner = UserPreferenceLearner()
        logger.info("SmartDefaultsEngine initialized")

    def get_defaults(
        self,
        context: ConversionContext,
        mod_features: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> SmartDefaultsResult:
        """
        Get smart defaults combining all approaches.

        Args:
            context: Conversion context
            mod_features: Optional mod features for pattern matching
            user_id: Optional user ID for personalization

        Returns:
            SmartDefaultsResult with combined defaults
        """
        results = []

        # 1. Get inference-based defaults
        inference_result = self.inference_engine.infer_settings(context)
        results.append(("inference", inference_result, 0.4))  # 40% weight

        # 2. Get pattern-based defaults (if mod features provided)
        if mod_features:
            pattern_result = self.pattern_defaults.get_defaults_for_pattern(
                mod_features
            )
            if pattern_result.confidence > 0:
                results.append(("pattern", pattern_result, 0.3))  # 30% weight

        # 3. Get user-personalized defaults (if user ID provided)
        if user_id:
            base_settings = inference_result.settings
            user_result = self.user_learner.get_personalized_defaults(
                user_id, base_settings
            )
            if user_result.reasoning:  # Has learned preferences
                results.append(("user", user_result, 0.3))  # 30% weight

        # Combine results
        combined = self._combine_results(results)

        logger.info(
            f"Smart defaults: {len(results)} sources, confidence {combined.confidence:.0%}"
        )

        return combined

    def _combine_results(
        self,
        results: List[Tuple[str, SmartDefaultsResult, float]],
    ) -> SmartDefaultsResult:
        """Combine results from multiple sources."""
        if not results:
            return SmartDefaultsResult(
                settings={},
                confidence=0.0,
                reasoning=["No defaults available"],
                source="none",
            )

        if len(results) == 1:
            return results[0][1]

        # Combine settings with weights
        combined_settings = {}
        combined_reasoning = []
        total_weight = sum(r[2] for r in results)

        for source, result, weight in results:
            for key, value in result.settings.items():
                if key not in combined_settings:
                    combined_settings[key] = value

            combined_reasoning.extend([f"[{source}] {r}" for r in result.reasoning])

        # Calculate combined confidence
        weighted_confidence = (
            sum(r[1].confidence * r[2] for r in results) / total_weight
        )

        return SmartDefaultsResult(
            settings=combined_settings,
            confidence=weighted_confidence,
            reasoning=combined_reasoning,
            alternatives=results[0][1].alternatives,  # Use first source's alternatives
            source="hybrid",
        )

    def record_conversion_outcome(
        self,
        mod_features: Dict[str, Any],
        settings_used: Dict[str, Any],
        success: bool,
        quality_score: float,
        user_id: Optional[str] = None,
        user_feedback: Optional[str] = None,
    ):
        """Record conversion outcome for learning."""
        # Update pattern learning
        self.pattern_defaults.record_conversion(
            mod_features, settings_used, success, quality_score
        )

        # Update user preference learning
        if user_id:
            self.user_learner.record_user_choice(
                user_id,
                settings_used,  # This would be the suggested settings
                settings_used,  # This would be actual settings
                user_feedback,
            )


# Convenience functions
def get_smart_defaults(
    mod_features: Dict[str, Any],
    user_id: Optional[str] = None,
) -> SmartDefaultsResult:
    """
    Get smart defaults for a mod.

    Args:
        mod_features: Features extracted from mod
        user_id: Optional user ID for personalization

    Returns:
        SmartDefaultsResult with recommended settings
    """
    engine = SmartDefaultsEngine()

    # Create context from features
    context = _features_to_context(mod_features)

    return engine.get_defaults(context, mod_features, user_id)


def _features_to_context(features: Dict[str, Any]) -> ConversionContext:
    """Convert mod features to conversion context."""
    class_count = features.get("class_count", 0)

    if class_count < 10:
        mod_size = "small"
    elif class_count < 30:
        mod_size = "medium"
    elif class_count < 100:
        mod_size = "large"
    else:
        mod_size = "very_large"

    return ConversionContext(
        mod_size=mod_size,
        mod_complexity=features.get("complexity_score", 0.5),
        has_entities=features.get("has_entities", False),
        has_multiblock=features.get("has_multiblock", False),
        has_machines=features.get("has_machines", False),
        has_dimensions=features.get("has_dimensions", False),
        has_custom_ai=features.get("has_custom_ai", False),
        has_dependencies=features.get("dependency_count", 0) > 0,
        dependency_count=features.get("dependency_count", 0),
    )
