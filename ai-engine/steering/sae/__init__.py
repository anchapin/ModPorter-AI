"""
SAE-Based Feature Steering for Bedrock Code Generation

Implements SAE (Sparse Autoencoder)-based feature steering to surgically suppress
Java Edition idioms in Bedrock code generation, following the approach from:
- Sieve: SAEs Beat Baselines on a Real-World Code Generation Task (Tilde Research, Dec 2024)
- https://blog.tilderesearch.com/blog/sieve

The core insight from Sieve:
- Train an SAE on the base model's activations
- Identify features corresponding to unwanted patterns (e.g., Java Forge API calls)
- Apply steering at inference time by zeroing/suppressing those feature directions

This is more surgical than:
- Prompt engineering (imprecise, affects all outputs)
- Steering vectors (collateral degradation on unrelated prompts)

Architecture:
1. SAE Training Pipeline: Train SAE on conversion samples to learn feature directions
2. Feature Identification: Automated search to find "Java idioms" vs "Bedrock idioms" features
3. Steering Engine: Apply conditional steering during inference (Sieve pipeline)
4. Integration: Hook into the conversion pipeline for seamless operation

Related Issues:
- #1375: Investigate SAE-based feature steering (this module)
- #1269: Reward model for idiomaticity (RM detects bad output)
- #1268: Constraint violation tracking (SAE prevents at generation time)
"""

from .core import (
    SAEDecoder,
    FeatureSteeringConfig,
    SteeringDirection,
    FeatureSearchResult,
    get_steering_engine,
)
from .identifiers import (
    JavaIdiomFeatureRegistry,
    BedrockIdiomFeatureRegistry,
    create_feature_registry,
)

__all__ = [
    "SAEDecoder",
    "FeatureSteeringConfig",
    "SteeringDirection",
    "FeatureSearchResult",
    "get_steering_engine",
    "JavaIdiomFeatureRegistry",
    "BedrockIdiomFeatureRegistry",
    "create_feature_registry",
]
