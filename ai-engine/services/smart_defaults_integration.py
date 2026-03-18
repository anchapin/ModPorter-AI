"""
Smart Defaults Integration Module

Integrates ModeClassifier with SmartDefaultsEngine for seamless
one-click conversion with intelligent settings inference.
"""

import logging
from typing import Optional, Dict, Any

from mode_classifier import ModeClassifier, ModFeatures, ConversionMode
from smart_defaults_engine import (
    SmartDefaultsEngine,
    ConversionContext,
    SmartDefaultsResult,
)

logger = logging.getLogger(__name__)


class SmartDefaultsIntegration:
    """
    Unified interface for smart defaults with mode classification.
    
    Provides end-to-end conversion settings inference by:
    1. Classifying mod into conversion mode
    2. Extracting features for context
    3. Applying smart defaults from all sources
    """
    
    def __init__(self):
        self.classifier = ModeClassifier()
        self.smart_defaults = SmartDefaultsEngine()
        logger.info("SmartDefaultsIntegration initialized")
    
    def get_conversion_settings(
        self,
        mod_path: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get optimal conversion settings for a mod.
        
        Args:
            mod_path: Path to mod JAR or directory
            user_id: Optional user ID for personalization
            
        Returns:
            Dictionary with conversion settings
        """
        logger.info(f"Getting conversion settings for: {mod_path}")
        
        # Step 1: Classify mod
        classification = self.classifier.classify_mod(mod_path)
        logger.info(f"Mode: {classification.mode}, Confidence: {classification.confidence:.0%}")
        
        # Step 2: Build conversion context
        context = self._build_context(classification)
        
        # Step 3: Get mod features for pattern matching
        mod_features = None
        if classification.features:
            mod_features = classification.features.to_dict()
        
        # Step 4: Get smart defaults
        smart_result = self.smart_defaults.get_defaults(
            context=context,
            mod_features=mod_features,
            user_id=user_id,
        )
        
        # Step 5: Combine with mode defaults
        final_settings = self._combine_with_mode_defaults(
            classification.mode,
            smart_result,
        )
        
        logger.info(f"Final settings: {final_settings}")
        
        return {
            "mode": classification.mode,
            "mode_confidence": classification.confidence,
            "settings": final_settings,
            "defaults_confidence": smart_result.confidence,
            "defaults_source": smart_result.source,
            "reasoning": smart_result.reasoning,
        }
    
    def _build_context(
        self,
        classification,
    ) -> ConversionContext:
        """Build conversion context from classification result."""
        
        # Determine mod size
        features = classification.features
        if features:
            if features.class_count < 10:
                mod_size = "small"
            elif features.class_count < 50:
                mod_size = "medium"
            elif features.class_count < 100:
                mod_size = "large"
            else:
                mod_size = "very_large"
            
            # Determine mod type from features
            if features.has_multiblock or features.has_machines:
                mod_type = "tech"
            elif features.has_dimension or features.has_biome:
                mod_type = "magic"
            elif features.has_entities:
                mod_type = "adventure"
            else:
                mod_type = "utility"
        else:
            mod_size = "medium"
            mod_type = "unknown"
        
        context = ConversionContext(
            mod_size=mod_size,
            mod_complexity=classification.features.complexity_score if features else 0.5,
            mod_type=mod_type,
            has_dependencies=features.dependency_count > 0 if features else False,
            dependency_count=features.dependency_count if features else 0,
            has_entities=features.has_entities if features else False,
            has_multiblock=features.has_multiblock if features else False,
            has_machines=features.has_machines if features else False,
            has_dimensions=features.has_dimension if features else False,
            has_custom_ai=features.has_custom_ai if features else False,
        )
        
        return context
    
    def _combine_with_mode_defaults(
        self,
        mode: str,
        smart_result: SmartDefaultsResult,
    ) -> Dict[str, Any]:
        """Combine smart defaults with mode-specific defaults."""
        
        # Mode-specific defaults
        mode_defaults = {
            ConversionMode.SIMPLE: {
                "detail_level": "standard",
                "validation_level": "basic",
                "optimization": "speed",
                "error_handling": "auto-fix",
                "estimated_time": 60,
            },
            ConversionMode.STANDARD: {
                "detail_level": "detailed",
                "validation_level": "standard",
                "optimization": "balanced",
                "error_handling": "auto-fix",
                "estimated_time": 120,
            },
            ConversionMode.COMPLEX: {
                "detail_level": "comprehensive",
                "validation_level": "strict",
                "optimization": "accuracy",
                "error_handling": "review",
                "estimated_time": 300,
            },
            ConversionMode.EXPERT: {
                "detail_level": "comprehensive",
                "validation_level": "strict",
                "optimization": "accuracy",
                "error_handling": "manual",
                "estimated_time": 600,
            },
        }
        
        # Start with mode defaults
        defaults = mode_defaults.get(mode, mode_defaults[ConversionMode.STANDARD]).copy()
        
        # Override with smart defaults
        defaults.update(smart_result.settings)
        
        # Add mode info
        defaults["mode"] = mode
        
        return defaults


# Convenience function
def get_optimal_settings(
    mod_path: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get optimal conversion settings for a mod.
    
    Args:
        mod_path: Path to mod JAR or directory
        user_id: Optional user ID for personalization
        
    Returns:
        Dictionary with conversion settings
    """
    integration = SmartDefaultsIntegration()
    return integration.get_conversion_settings(mod_path, user_id)
