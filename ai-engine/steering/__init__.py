"""
SAE-Based Feature Steering for Java Idioms Suppression

This module provides surgical steering of LLM activations to prevent
Java Edition idioms from appearing in Bedrock code generation.

Based on "Sieve: SAEs Beat Baselines on a Real-World Task" - Tilde Research, Dec 2024
"""

from .evaluation import (
    EvaluationResult,
    IdiomCategory,
    IdiomPattern,
    JAVA_IDIOM_PATTERNS,
    SteeringEvaluator,
    evaluate_steering_effectiveness,
)
from .pipeline import (
    SteeringPipeline,
    SteeringPipelineConfig,
    configure_steering_pipeline,
    get_steering_pipeline,
    reset_steering_pipeline,
)
from .sae_feature_steering import (
    JavaIdiomClassifier,
    JavaIdiomFeatures,
    SAEFeatureSteerer,
    SteeringConfig,
    SteeringTarget,
    create_default_steering_config,
    create_demo_features,
)
from .steering_vectors import SteeringMode

__all__ = [
    # Existing exports
    "SAEFeatureSteerer",
    "JavaIdiomFeatures",
    "SteeringConfig",
    "SteeringTarget",
    "JavaIdiomClassifier",
    "create_default_steering_config",
    "create_demo_features",
    # SteeringPipeline facade (consumed by agents.logic_translator.steering_tools)
    "SteeringPipeline",
    "SteeringPipelineConfig",
    "get_steering_pipeline",
    "configure_steering_pipeline",
    "reset_steering_pipeline",
    # Evaluation API
    "SteeringEvaluator",
    "evaluate_steering_effectiveness",
    "EvaluationResult",
    "IdiomCategory",
    "IdiomPattern",
    "JAVA_IDIOM_PATTERNS",
    # Steering primitives
    "SteeringMode",
]
