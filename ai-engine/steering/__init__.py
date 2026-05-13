"""
SAE-Based Feature Steering for Java Idiom Suppression.

This module provides end-to-end SAE-based feature steering for the conversion
pipeline, integrating SAE feature extraction, steering vector computation,
and inference interception.

Usage:
    from steering import SteeringPipeline, SteeringMode

    # Initialize steering
    pipeline = SteeringPipeline()
    pipeline.enable_steering()

    # Generate with steering
    result = await pipeline.generate_with_steering(
        messages=[...],
        suppression_targets=["java_forge_suppress", "java_class_suppress"],
    )
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .sae import SAEClient, SAEConfig, SAEResult
from .java_idiom_detector import JavaIdiomHeuristics
from .steering_vectors import (
    FeatureSteeringEngine,
    SteeringConfig,
    SteeringMode,
    SteeringVector,
    SteeringVectorStore,
)
from .inference_interceptor import (
    HiddenStateInterceptor,
    InterceptorConfig,
    PromptSteeringEngine,
    InferenceBackend,
)
from .evaluation import (
    EvaluationResult,
    IdiomCategory,
    IdiomMetrics,
    IdiomPattern,
    SteeringEvaluator,
    evaluate_steering_effectiveness,
)

logger = logging.getLogger(__name__)


@dataclass
class SteeringPipelineConfig:
    """Configuration for the steering pipeline"""
    # SAE settings
    sae_enabled: bool = True
    sae_endpoint: Optional[str] = None
    sae_api_key: Optional[str] = None
    use_fallback_detector: bool = True

    # Steering settings
    steering_enabled: bool = True
    steering_scale: float = 2.0
    suppression_targets: List[str] = field(default_factory=lambda: [
        "java_forge_suppress",
        "java_class_suppress",
    ])

    # Inference backend
    inference_backend: InferenceBackend = InferenceBackend.OPENAI_COMPATIBLE
    inference_endpoint: Optional[str] = None

    # Feature detection
    detect_java_idioms: bool = True
    idiom_threshold: float = 0.1

    # Logging
    log_steering_events: bool = True


class SteeringPipeline:
    """
    End-to-end steering pipeline for Java idiom suppression.

    This pipeline:
    1. Takes Java code as input
    2. Runs it through SAE to detect Java idiom features
    3. Computes steering vectors from detected features
    4. Applies steering during LLM generation to suppress Java patterns

    Usage:
        pipeline = SteeringPipeline(config)
        steered_result = await pipeline.generate_with_steering(
            messages=[...],
            context={"java_code": java_snippet},
        )
    """

    def __init__(self, config: Optional[SteeringPipelineConfig] = None):
        self.config = config or SteeringPipelineConfig()
        self._initialize_components()
        self._stats = {
            "generations": 0,
            "steering_applications": 0,
            "idiom_detections": 0,
            "fallback_activations": 0,
        }

    def _initialize_components(self) -> None:
        """Initialize all steering components"""
        # SAE Client
        sae_config = SAEConfig(
            endpoint_url=self.config.sae_endpoint,
            api_key=self.config.sae_api_key,
        )
        self._sae_client = SAEClient(config=sae_config)

        # Java idiom detector (fallback)
        self._idiom_detector = JavaIdiomHeuristics()

        # Steering engine
        steering_config = SteeringConfig(
            steering_scale=self.config.steering_scale,
        )
        self._steering_engine = FeatureSteeringEngine(config=steering_config)

        # Vector store
        self._vector_store = SteeringVectorStore()

        # Inference interceptor
        interceptor_config = InterceptorConfig(
            backend=self.config.inference_backend,
            endpoint_url=self.config.inference_endpoint,
            steering_enabled=self.config.steering_enabled,
        )
        self._interceptor = HiddenStateInterceptor(config=interceptor_config)

        # Prompt steering fallback
        self._prompt_steering = PromptSteeringEngine()

        # State
        self._steering_enabled = True
        self._current_features: Dict[int, float] = {}

    def enable_steering(self) -> None:
        """Enable steering globally"""
        self._steering_enabled = True
        self._interceptor.set_steering_active(True)
        logger.info("Steering enabled")

    def disable_steering(self) -> None:
        """Disable steering globally"""
        self._steering_enabled = False
        self._interceptor.set_steering_active(False)
        logger.info("Steering disabled")

    async def detect_and_compute_steering(
        self,
        java_snippet: str,
        custom_features: Optional[Dict[int, float]] = None,
    ) -> SteeringVector:
        """
        Detect Java idioms and compute steering vector.

        Args:
            java_snippet: Java code to analyze
            custom_features: Optional pre-computed features to use

        Returns:
            Steering vector ready for application
        """
        self._stats["idiom_detections"] += 1

        if custom_features:
            features = custom_features
        elif self.config.sae_enabled:
            # Try SAE first
            try:
                sae_result = await self._sae_client.run_async(java_snippet)
                features = sae_result.get_feature_weights()
            except Exception as e:
                logger.warning(f"SAE detection failed, using fallback: {e}")
                features = self._idiom_detector.detect_features(java_snippet)
        else:
            # Use fallback detector
            features = self._idiom_detector.detect_features(java_snippet)

        self._current_features = features

        # Filter by threshold
        filtered = {k: v for k, v in features.items() if v >= self.config.idiom_threshold}

        # Compute steering vector
        steering = self._steering_engine.compute_steering_from_text(
            text=java_snippet,
            idiom_features=filtered,
            scale=self.config.steering_scale,
        )

        if self.config.log_steering_events:
            self._log_steering_event("compute", steering)

        return steering

    async def generate_with_steering(
        self,
        messages: List[Dict[str, str]],
        java_context: Optional[str] = None,
        steering_vector: Optional[SteeringVector] = None,
        **generation_kwargs,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate text with steering applied.

        Args:
            messages: Chat messages for generation
            java_context: Optional Java code context for feature detection
            steering_vector: Pre-computed steering vector (optional)
            **generation_kwargs: Generation parameters

        Returns:
            Tuple of (generated_text, metadata)
        """
        self._stats["generations"] += 1

        if not self._steering_enabled:
            return await self._generate_without_steering(messages, **generation_kwargs)

        # Detect idioms and compute steering if not provided
        if steering_vector is None and java_context:
            steering_vector = await self.detect_and_compute_steering(java_context)

        # Apply steering
        self._stats["steering_applications"] += 1

        if self.config.inference_backend == InferenceBackend.OPENAI_COMPATIBLE:
            # Use prompt steering fallback
            self._stats["fallback_activations"] += 1
            return await self._generate_with_prompt_steering(
                messages, steering_vector, **generation_kwargs
            )
        else:
            # Use hidden state steering
            return await self._interceptor.generate_with_steering(
                messages=messages,
                steering_vector=steering_vector.steering_direction
                if steering_vector else None,
                **generation_kwargs,
            )

    async def _generate_without_steering(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate without steering - direct inference call"""
        # Placeholder - would call actual inference
        return "", {"source": "no_steering"}

    async def _generate_with_prompt_steering(
        self,
        messages: List[Dict[str, str]],
        steering_vector: Optional[SteeringVector],
        **generation_kwargs,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate with prompt-based steering (fallback)"""
        if steering_vector is None:
            return await self._generate_without_steering(messages, **generation_kwargs)

        # Extract features from steering vector
        features = self._steering_vector_to_features(steering_vector)

        # Get suppression/encouragement lists
        suppress, encourage = self._prompt_steering.extract_steering_from_features(features)

        # Build steering prompt
        base_system = next(
            (m["content"] for m in messages if m.get("role") == "system"),
            "You are a Bedrock add-on code generator.",
        )

        modified_system = self._prompt_steering.build_steering_prompt(
            base_system, suppress, encourage
        )

        # Modify messages
        modified_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                modified_messages.append({
                    "role": "system",
                    "content": modified_system,
                })
            else:
                modified_messages.append(msg)

        if self.config.log_steering_events:
            logger.info(f"Prompt steering: suppress={suppress[:2]}, encourage={encourage[:2]}")

        # Generate
        result = await self._call_inference(modified_messages, **generation_kwargs)

        return result, {
            "source": "prompt_steering",
            "suppress": suppress,
            "encourage": encourage,
            "features": features,
        }

    def _steering_vector_to_features(self, vector: SteeringVector) -> Dict[int, float]:
        """Convert steering vector back to feature dict"""
        return {f: abs(w) for f, w in zip(vector.feature_ids, vector.weights)}

    async def _call_inference(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> str:
        """Call inference endpoint"""
        # Placeholder - would integrate with SelfHostedInferenceClient
        return ""

    def _log_steering_event(self, event_type: str, steering: SteeringVector) -> None:
        """Log a steering event"""
        if not self.config.log_steering_events:
            return

        logger.info(
            f"Steering event: {event_type} | "
            f"vector={steering.name} | "
            f"magnitude={steering.magnitude:.3f} | "
            f"features={len(steering.feature_ids)}"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return {
            **self._stats,
            "steering_active": self._steering_enabled,
            "current_features": self._current_features,
        }

    def get_suppression_targets(self) -> List[str]:
        """Get list of active suppression target names"""
        return self.config.suppression_targets

    def add_suppression_target(self, target: str) -> None:
        """Add a suppression target by name"""
        if target not in self.config.suppression_targets:
            self.config.suppression_targets.append(target)

    def get_steering_vector(self, name: str) -> Optional[SteeringVector]:
        """Get a pre-computed steering vector by name"""
        return self._vector_store.get(name)


# Singleton instance
_steering_pipeline: Optional[SteeringPipeline] = None


def get_steering_pipeline() -> SteeringPipeline:
    """Get singleton steering pipeline"""
    global _steering_pipeline
    if _steering_pipeline is None:
        _steering_pipeline = SteeringPipeline()
    return _steering_pipeline


def configure_steering_pipeline(config: SteeringPipelineConfig) -> SteeringPipeline:
    """Configure and return singleton steering pipeline"""
    global _steering_pipeline
    _steering_pipeline = SteeringPipeline(config=config)
    return _steering_pipeline
