"""
Conversion Mode Models for v2.5 Milestone

Defines the 4 conversion modes (Simple/Standard/Complex/Expert) and
classification models for automatic mode detection.

See: docs/GAP-ANALYSIS-v2.5.md
"""

from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class ConversionMode(str, Enum):
    """4 conversion modes based on mod complexity."""

    SIMPLE = "simple"
    """1-5 classes, 0-2 dependencies, no complex features. 99% automation."""

    STANDARD = "standard"
    """5-20 classes, 2-5 dependencies, entities/recipes. 95% automation."""

    COMPLEX = "complex"
    """20-50 classes, 5-10 dependencies, multiblock/machines. 85% automation."""

    EXPERT = "expert"
    """50+ classes, 10+ dependencies, dimensions/worldgen. 70% automation."""


class ModeClassificationRule(BaseModel):
    """A rule for classifying a mod into a conversion mode."""

    mode: ConversionMode
    min_classes: int = 1
    max_classes: int = 999
    min_dependencies: int = 0
    max_dependencies: int = 999
    has_complex_features: bool = False
    confidence_boost: float = 0.0


class ComplexFeature(BaseModel):
    """Represents a detected complex feature in a mod."""

    feature_type: str
    description: str
    impact: str  # "blocking", "warning", "info"
    workaround_available: bool = False
    workaround_description: Optional[str] = None


class ModFeatures(BaseModel):
    """Extracted features from a mod used for classification."""

    total_classes: int = 0
    total_dependencies: int = 0
    has_items: bool = False
    has_blocks: bool = False
    has_entities: bool = False
    has_recipes: bool = False
    has_GUI: bool = False  # noqa: N815
    has_network_packets: bool = False
    has_ASM: bool = False  # noqa: N815
    has_dimensions: bool = False
    has_worldgen: bool = False
    has_biomes: bool = False
    has_multiblock: bool = False
    has_custom_AI: bool = False  # noqa: N815
    has_custom_rendering: bool = False
    has_custom_models: bool = False
    has_sounds: bool = False
    has_resources: bool = False

    complex_features: List[ComplexFeature] = Field(default_factory=list)

    mod_loader: Optional[str] = None  # "forge", "fabric", "neoforge"
    target_version: Optional[str] = None


class ClassificationConfidence(BaseModel):
    """Confidence score for a mode classification."""

    mode: ConversionMode
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ModeClassificationResult(BaseModel):
    """Result of mode classification with confidence scoring."""

    mode: ConversionMode
    confidence: float = Field(ge=0.0, le=1.0)
    features: ModFeatures
    alternative_modes: List[ClassificationConfidence] = Field(default_factory=list)
    convertible_percentage: float = Field(ge=0.0, le=100.0)
    estimated_time_seconds: int = 0
    automation_level: int = Field(ge=0, le=100)  # percentage

    model_config = ConfigDict(from_attributes=True)


class ModeClassificationRequest(BaseModel):
    """Request to classify a mod's conversion mode."""

    file_path: Optional[str] = None  # Path to uploaded mod file
    file_content: Optional[bytes] = None  # Raw file content
    features: Optional[ModFeatures] = None  # Pre-extracted features
    user_id: Optional[str] = None


class ModeClassificationResponse(BaseModel):
    """Response with mode classification result."""

    classification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mode: ConversionMode
    confidence: float
    features: ModFeatures
    alternative_modes: List[ClassificationConfidence] = []
    convertible_percentage: float
    estimated_time_seconds: int
    automation_level: int
    recommended_settings: "ConversionSettings"
    warnings: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversionSettings(BaseModel):
    """Recommended settings for a conversion based on mode."""

    mode: ConversionMode
    detail_level: str = "standard"  # "minimal", "standard", "detailed"
    validation_level: str = "standard"  # "basic", "standard", "strict"
    enable_auto_fix: bool = True
    enable_ai_assistance: bool = True
    max_retries: int = 3
    timeout_seconds: int = 600
    parallel_processing: bool = False
    quality_threshold: float = 0.8


class ModeSpecificPipelineConfig(BaseModel):
    """Configuration for mode-specific conversion pipeline."""

    mode: ConversionMode
    pipeline_name: str
    steps: List[str]
    estimated_success_rate: float
    requires_human_review: bool = False
    special_requirements: List[str] = []


# Default classification rules in priority order
DEFAULT_CLASSIFICATION_RULES: List[ModeClassificationRule] = [
    # Expert mode first (most specific)
    ModeClassificationRule(
        mode=ConversionMode.EXPERT,
        min_classes=50,
        min_dependencies=10,
        has_complex_features=True,
        confidence_boost=0.2,
    ),
    # Expert mode (class/dependency based)
    ModeClassificationRule(
        mode=ConversionMode.EXPERT, min_classes=50, min_dependencies=10, confidence_boost=0.1
    ),
    # Complex mode
    ModeClassificationRule(
        mode=ConversionMode.COMPLEX,
        min_classes=20,
        min_dependencies=5,
        has_complex_features=True,
        confidence_boost=0.2,
    ),
    ModeClassificationRule(
        mode=ConversionMode.COMPLEX, min_classes=20, min_dependencies=5, confidence_boost=0.1
    ),
    # Standard mode
    ModeClassificationRule(
        mode=ConversionMode.STANDARD, min_classes=5, min_dependencies=2, confidence_boost=0.1
    ),
    # Simple mode (default)
    ModeClassificationRule(mode=ConversionMode.SIMPLE, min_classes=1, confidence_boost=0.0),
]


# Mode-specific pipeline configurations
MODE_PIPELINES: Dict[ConversionMode, ModeSpecificPipelineConfig] = {
    ConversionMode.SIMPLE: ModeSpecificPipelineConfig(
        mode=ConversionMode.SIMPLE,
        pipeline_name="simple-pipeline",
        steps=["parse", "extract", "translate", "validate", "export"],
        estimated_success_rate=0.99,
        requires_human_review=False,
    ),
    ConversionMode.STANDARD: ModeSpecificPipelineConfig(
        mode=ConversionMode.STANDARD,
        pipeline_name="standard-pipeline",
        steps=["parse", "extract", "translate", "qa-review", "validate", "export"],
        estimated_success_rate=0.95,
        requires_human_review=False,
    ),
    ConversionMode.COMPLEX: ModeSpecificPipelineConfig(
        mode=ConversionMode.COMPLEX,
        pipeline_name="complex-pipeline",
        steps=[
            "parse",
            "extract",
            "translate",
            "qa-review",
            "semantic-check",
            "validate",
            "export",
        ],
        estimated_success_rate=0.85,
        requires_human_review=True,
        special_requirements=["additional_qa", "extended_validation"],
    ),
    ConversionMode.EXPERT: ModeSpecificPipelineConfig(
        mode=ConversionMode.EXPERT,
        pipeline_name="expert-pipeline",
        steps=[
            "parse",
            "extract",
            "translate",
            "qa-review",
            "semantic-check",
            "expert-review",
            "validate",
            "export",
        ],
        estimated_success_rate=0.70,
        requires_human_review=True,
        special_requirements=["expert_qa", "manual_inspection", "extended_validation"],
    ),
}
