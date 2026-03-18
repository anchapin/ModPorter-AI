"""
One-Click Conversion System

Enables single-click conversion for Simple/Standard mode mods with:
- Auto-mode selection
- Smart defaults application
- Instant conversion start
- Progress tracking
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
<<<<<<< HEAD
=======
from pathlib import Path
import json
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))

# Import mode classifier
try:
    from .mode_classifier import ModeClassifier, ClassificationResult, ConversionMode
except ImportError:
    from mode_classifier import ModeClassifier, ClassificationResult, ConversionMode

logger = logging.getLogger(__name__)


@dataclass
class ConversionSettings:
    """Settings for conversion."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Mode-specific settings
    mode: str = "Standard"
    detail_level: str = "standard"  # basic, standard, detailed, comprehensive
    validation_level: str = "standard"  # basic, standard, strict
    optimization: str = "balanced"  # speed, balanced, accuracy
    error_handling: str = "auto-fix"  # auto-fix, review, manual
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Output settings
    output_format: str = "mcaddon"  # mcaddon, zip, folder
    include_source: bool = False
    include_report: bool = True
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Advanced settings
    use_rag: bool = True
    use_pattern_library: bool = True
    semantic_check: bool = True
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "detail_level": self.detail_level,
            "validation_level": self.validation_level,
            "optimization": self.optimization,
            "error_handling": self.error_handling,
            "output_format": self.output_format,
            "include_source": self.include_source,
            "include_report": self.include_report,
            "use_rag": self.use_rag,
            "use_pattern_library": self.use_pattern_library,
            "semantic_check": self.semantic_check,
        }


@dataclass
class OneClickResult:
    """Result of one-click conversion request."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    success: bool
    conversion_id: str
    mode: str
    settings: ConversionSettings
    status: str = "queued"  # queued, processing, completed, failed
    progress: int = 0
    message: str = ""
    estimated_time: float = 0.0  # seconds
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "conversion_id": self.conversion_id,
            "mode": self.mode,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "estimated_time": self.estimated_time,
            "output_path": self.output_path,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# Smart defaults by mode
MODE_DEFAULTS = {
    ConversionMode.SIMPLE: {
        "detail_level": "standard",
        "validation_level": "basic",
        "optimization": "speed",
        "error_handling": "auto-fix",
        "estimated_time": 60,  # seconds
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


class OneClickConverter:
    """
    One-click conversion system.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Usage:
        converter = OneClickConverter()
        result = converter.convert_mod("/path/to/mod.jar", "/output/path")
    """
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self):
        self.classifier = ModeClassifier()
        self.conversion_queue: Dict[str, OneClickResult] = {}
        logger.info("OneClickConverter initialized")
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def convert_mod(
        self,
        mod_path: str,
        output_path: str,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> OneClickResult:
        """
        Convert a mod with one click.
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Args:
            mod_path: Path to mod JAR file
            output_path: Output path for converted mod
            user_preferences: Optional user preference overrides
<<<<<<< HEAD

=======
            
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Returns:
            OneClickResult with conversion status
        """
        logger.info(f"One-click conversion requested: {mod_path}")
<<<<<<< HEAD

        # Step 1: Classify mod
        classification = self.classifier.classify_mod(mod_path)
        logger.info(f"Mod classified as: {classification.mode}")

=======
        
        # Step 1: Classify mod
        classification = self.classifier.classify_mod(mod_path)
        logger.info(f"Mod classified as: {classification.mode}")
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Step 2: Check if auto-conversion is appropriate
        if classification.mode in [ConversionMode.COMPLEX, ConversionMode.EXPERT]:
            # For complex/expert mods, provide recommendation instead of auto-converting
            return self._create_recommendation_result(classification, mod_path)
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Step 3: Apply smart defaults
        settings = self._apply_smart_defaults(
            classification.mode,
            user_preferences,
        )
        logger.info(f"Settings applied: {settings.detail_level}, {settings.optimization}")
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Step 4: Create conversion result
        result = self._create_conversion_result(
            classification.mode,
            settings,
            classification,
        )
<<<<<<< HEAD

        # Step 5: Start conversion (simulated for now)
        result = self._start_conversion(result, mod_path, output_path)

        logger.info(f"One-click conversion started: {result.conversion_id}")

        return result

=======
        
        # Step 5: Start conversion (simulated for now)
        result = self._start_conversion(result, mod_path, output_path)
        
        logger.info(f"One-click conversion started: {result.conversion_id}")
        
        return result
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _apply_smart_defaults(
        self,
        mode: str,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> ConversionSettings:
        """Apply smart defaults based on mode and user preferences."""
        defaults = MODE_DEFAULTS.get(mode, MODE_DEFAULTS[ConversionMode.STANDARD])
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        settings = ConversionSettings(
            mode=mode,
            detail_level=defaults["detail_level"],
            validation_level=defaults["validation_level"],
            optimization=defaults["optimization"],
            error_handling=defaults["error_handling"],
        )
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Apply user preferences if provided
        if user_preferences:
            for key, value in user_preferences.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
                    logger.debug(f"User preference applied: {key}={value}")
<<<<<<< HEAD

        return settings

=======
        
        return settings
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _create_recommendation_result(
        self,
        classification: ClassificationResult,
        mod_path: str,
    ) -> OneClickResult:
        """Create recommendation result for complex/expert mods."""
        result = OneClickResult(
            success=False,
            conversion_id=f"rec_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            mode=classification.mode,
            settings=self._apply_smart_defaults(classification.mode),
            status="requires_review",
            message=f"{classification.mode} mode requires manual review. {classification.reason}",
            estimated_time=MODE_DEFAULTS[classification.mode]["estimated_time"],
        )
<<<<<<< HEAD

        result.warnings.append(f"{classification.mode} complexity: Manual review recommended")
        result.warnings.extend(classification.recommendations)

        logger.info(f"Created recommendation result for {mod_path}")

        return result

=======
        
        result.warnings.append(
            f"{classification.mode} complexity: Manual review recommended"
        )
        result.warnings.extend(classification.recommendations)
        
        logger.info(f"Created recommendation result for {mod_path}")
        
        return result
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _create_conversion_result(
        self,
        mode: str,
        settings: ConversionSettings,
        classification: ClassificationResult,
    ) -> OneClickResult:
        """Create conversion result with smart defaults."""
        return OneClickResult(
            success=True,
            conversion_id=f"conv_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            mode=mode,
            settings=settings,
            status="queued",
            message=f"Auto-classified as {mode} mode. Starting conversion...",
            estimated_time=MODE_DEFAULTS[mode]["estimated_time"],
<<<<<<< HEAD
            warnings=(
                classification.recommendations[:2] if classification.confidence < 0.8 else []
            ),
        )

=======
            warnings=classification.recommendations[:2] if classification.confidence < 0.8 else [],
        )
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _start_conversion(
        self,
        result: OneClickResult,
        mod_path: str,
        output_path: str,
    ) -> OneClickResult:
        """Start the conversion process."""
        result.status = "processing"
        result.started_at = datetime.now()
        result.progress = 10
<<<<<<< HEAD

        # Simulate conversion steps
        # In production, this would call the actual conversion pipeline

        # Step 1: Extract mod (10% → 30%)
        result.progress = 30

        # Step 2: Analyze features (30% → 50%)
        result.progress = 50

        # Step 3: Apply patterns (50% → 70%)
        result.progress = 70

        # Step 4: Generate Bedrock code (70% → 90%)
        result.progress = 90

=======
        
        # Simulate conversion steps
        # In production, this would call the actual conversion pipeline
        
        # Step 1: Extract mod (10% → 30%)
        result.progress = 30
        
        # Step 2: Analyze features (30% → 50%)
        result.progress = 50
        
        # Step 3: Apply patterns (50% → 70%)
        result.progress = 70
        
        # Step 4: Generate Bedrock code (70% → 90%)
        result.progress = 90
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Step 5: Package output (90% → 100%)
        result.progress = 100
        result.status = "completed"
        result.completed_at = datetime.now()
        result.output_path = output_path
        result.message = f"Conversion completed successfully. Output: {output_path}"
<<<<<<< HEAD

        # Store in queue
        self.conversion_queue[result.conversion_id] = result

        return result

    def get_conversion_status(self, conversion_id: str) -> Optional[OneClickResult]:
        """Get status of a conversion by ID."""
        return self.conversion_queue.get(conversion_id)

=======
        
        # Store in queue
        self.conversion_queue[result.conversion_id] = result
        
        return result
    
    def get_conversion_status(self, conversion_id: str) -> Optional[OneClickResult]:
        """Get status of a conversion by ID."""
        return self.conversion_queue.get(conversion_id)
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get conversion queue statistics."""
        total = len(self.conversion_queue)
        completed = sum(1 for r in self.conversion_queue.values() if r.status == "completed")
        processing = sum(1 for r in self.conversion_queue.values() if r.status == "processing")
        failed = sum(1 for r in self.conversion_queue.values() if r.status == "failed")
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        return {
            "total": total,
            "completed": completed,
            "processing": processing,
            "failed": failed,
            "success_rate": completed / total if total > 0 else 0,
        }


class SmartDefaultsEngine:
    """
    Engine for applying smart defaults based on mod analysis.
<<<<<<< HEAD

    Analyzes mod characteristics and user history to determine
    optimal conversion settings.
    """

    def __init__(self):
        self.user_history: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("SmartDefaultsEngine initialized")

=======
    
    Analyzes mod characteristics and user history to determine
    optimal conversion settings.
    """
    
    def __init__(self):
        self.user_history: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("SmartDefaultsEngine initialized")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_defaults_for_mod(
        self,
        mod_features: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> ConversionSettings:
        """
        Get smart defaults for a mod based on features and user history.
<<<<<<< HEAD

        Args:
            mod_features: Features extracted from mod
            user_id: Optional user ID for personalization

=======
        
        Args:
            mod_features: Features extracted from mod
            user_id: Optional user ID for personalization
            
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Returns:
            ConversionSettings with optimal defaults
        """
        # Base defaults from mode
        mode = mod_features.get("mode", ConversionMode.STANDARD)
        defaults = MODE_DEFAULTS.get(mode, MODE_DEFAULTS[ConversionMode.STANDARD])
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        settings = ConversionSettings(
            mode=mode,
            detail_level=defaults["detail_level"],
            validation_level=defaults["validation_level"],
            optimization=defaults["optimization"],
            error_handling=defaults["error_handling"],
        )
<<<<<<< HEAD

        # Adjust based on mod features
        settings = self._adjust_for_features(settings, mod_features)

        # Adjust based on user history
        if user_id and user_id in self.user_history:
            settings = self._adjust_for_user(settings, user_id)

        return settings

=======
        
        # Adjust based on mod features
        settings = self._adjust_for_features(settings, mod_features)
        
        # Adjust based on user history
        if user_id and user_id in self.user_history:
            settings = self._adjust_for_user(settings, user_id)
        
        return settings
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _adjust_for_features(
        self,
        settings: ConversionSettings,
        mod_features: Dict[str, Any],
    ) -> ConversionSettings:
        """Adjust settings based on mod features."""
        # More classes → more detailed
        if mod_features.get("class_count", 0) > 30:
            settings.detail_level = "comprehensive"
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Complex features → stricter validation
        complex_features = mod_features.get("complex_features", [])
        if len(complex_features) > 2:
            settings.validation_level = "strict"
            settings.optimization = "accuracy"
<<<<<<< HEAD

        # Multiblock → manual error handling
        if "multiblock" in complex_features:
            settings.error_handling = "review"

        return settings

=======
        
        # Multiblock → manual error handling
        if "multiblock" in complex_features:
            settings.error_handling = "review"
        
        return settings
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _adjust_for_user(
        self,
        settings: ConversionSettings,
        user_id: str,
    ) -> ConversionSettings:
        """Adjust settings based on user history."""
        history = self.user_history[user_id]
<<<<<<< HEAD

        # Analyze user preferences from history
        if len(history) >= 3:
            # User prefers detailed output
            detailed_count = sum(1 for h in history if h.get("detail_level") == "comprehensive")
            if detailed_count / len(history) > 0.7:
                settings.detail_level = "comprehensive"

            # User prefers speed
            speed_count = sum(1 for h in history if h.get("optimization") == "speed")
            if speed_count / len(history) > 0.7:
                settings.optimization = "speed"

        return settings

=======
        
        # Analyze user preferences from history
        if len(history) >= 3:
            # User prefers detailed output
            detailed_count = sum(
                1 for h in history 
                if h.get("detail_level") == "comprehensive"
            )
            if detailed_count / len(history) > 0.7:
                settings.detail_level = "comprehensive"
            
            # User prefers speed
            speed_count = sum(
                1 for h in history 
                if h.get("optimization") == "speed"
            )
            if speed_count / len(history) > 0.7:
                settings.optimization = "speed"
        
        return settings
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def record_conversion(
        self,
        user_id: str,
        settings: ConversionSettings,
        success: bool,
    ):
        """Record a conversion for learning user preferences."""
        if user_id not in self.user_history:
            self.user_history[user_id] = []
<<<<<<< HEAD

        self.user_history[user_id].append(
            {
                "mode": settings.mode,
                "detail_level": settings.detail_level,
                "validation_level": settings.validation_level,
                "optimization": settings.optimization,
                "success": success,
                "timestamp": datetime.now().isoformat(),
            }
        )

=======
        
        self.user_history[user_id].append({
            "mode": settings.mode,
            "detail_level": settings.detail_level,
            "validation_level": settings.validation_level,
            "optimization": settings.optimization,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        })
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Keep only last 100 conversions per user
        if len(self.user_history[user_id]) > 100:
            self.user_history[user_id] = self.user_history[user_id][-100:]


# Convenience functions
def one_click_convert(
    mod_path: str,
    output_path: str,
    user_preferences: Optional[Dict[str, Any]] = None,
) -> OneClickResult:
    """
    Convert a mod with one click.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Args:
        mod_path: Path to mod JAR file
        output_path: Output path for converted mod
        user_preferences: Optional user preference overrides
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Returns:
        OneClickResult with conversion status
    """
    converter = OneClickConverter()
    return converter.convert_mod(mod_path, output_path, user_preferences)


def get_mode_defaults(mode: str) -> Dict[str, Any]:
    """
    Get default settings for a conversion mode.
<<<<<<< HEAD

    Args:
        mode: Mode name (Simple/Standard/Complex/Expert)

=======
    
    Args:
        mode: Mode name (Simple/Standard/Complex/Expert)
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Returns:
        Dictionary with default settings
    """
    if mode not in MODE_DEFAULTS:
        return {"error": f"Unknown mode: {mode}"}
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    defaults = MODE_DEFAULTS[mode]
    return {
        "mode": mode,
        "detail_level": defaults["detail_level"],
        "validation_level": defaults["validation_level"],
        "optimization": defaults["optimization"],
        "error_handling": defaults["error_handling"],
        "estimated_time_seconds": defaults["estimated_time"],
    }
