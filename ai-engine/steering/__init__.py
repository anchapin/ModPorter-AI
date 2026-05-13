"""
SAE-Based Feature Steering for Java Idioms Suppression

This module provides surgical steering of LLM activations to prevent
Java Edition idioms from appearing in Bedrock code generation.

Based on "Sieve: SAEs Beat Baselines on a Real-World Task" - Tilde Research, Dec 2024
"""

from .sae_feature_steering import (
    JavaIdiomClassifier,
    JavaIdiomFeatures,
    SAEFeatureSteerer,
    SteeringConfig,
    SteeringTarget,
    create_default_steering_config,
    create_demo_features,
)

__all__ = [
    "SAEFeatureSteerer",
    "JavaIdiomFeatures",
    "SteeringConfig",
    "SteeringTarget",
    "JavaIdiomClassifier",
    "create_default_steering_config",
    "create_demo_features",
]