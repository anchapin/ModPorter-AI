"""
SteeringPipeline facade for SAE-based feature steering.

Provides a stable, lightweight orchestration layer that the LogicTranslator
agent's LangChain tools (``agents.logic_translator.steering_tools``) consume.

Historically the agent code imported ``SteeringPipeline``,
``SteeringPipelineConfig``, ``get_steering_pipeline``, and
``configure_steering_pipeline`` from the top-level ``steering`` package, but
those names had no implementation -- only the lower-level ``SievePipeline``
existed. Importing ``agents.logic_translator`` therefore raised ``ImportError``
at collection time and required the ``--admin`` escape hatch to merge PRs.

This module restores the missing API. It is intentionally a thin facade: the
pipeline holds configuration plus a small in-memory stats dict, and delegates
heavy lifting (when wired in) to the existing :mod:`steering.sae` machinery.
The shape of the API matches what ``steering_tools.py`` calls:

    * ``SteeringPipelineConfig(...)`` with the kwargs used by the configure tool.
    * ``pipeline._steering_enabled``         -- read by ``get_steering_enabled``.
    * ``pipeline.enable_steering()`` /
      ``pipeline.disable_steering()``        -- toggle steering on/off.
    * ``pipeline.get_stats()``               -- returns a dict for the stats tool.
    * ``configure_steering_pipeline(cfg)``   -- replaces the global pipeline.
    * ``get_steering_pipeline()``            -- returns / lazily creates it.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SteeringPipelineConfig:
    """Configuration for the high-level SteeringPipeline facade.

    Attributes mirror the JSON config accepted by ``configure_steering_tool``
    so that callers can pass kwargs through unchanged.
    """

    sae_endpoint: Optional[str] = None
    sae_api_key: Optional[str] = None
    steering_scale: float = 2.0
    suppression_targets: List[str] = field(
        default_factory=lambda: ["java_forge_suppress", "java_class_suppress"]
    )
    inference_backend: str = "openai_compatible"
    inference_endpoint: Optional[str] = None


class SteeringPipeline:
    """Thin orchestration layer over :mod:`steering.sae`.

    Tracks whether steering is enabled, exposes simple counters, and stores
    the :class:`SteeringPipelineConfig` used to create it. Heavier integration
    (loading SAE weights, calling the inference backend) is intentionally
    deferred -- it lives in the lower-level ``SievePipeline`` / ``SAEClient``
    classes and can be wired in incrementally without breaking imports.
    """

    def __init__(self, config: Optional[SteeringPipelineConfig] = None) -> None:
        self.config: SteeringPipelineConfig = config or SteeringPipelineConfig()
        # Public-by-convention; ``steering_tools`` reads it directly.
        self._steering_enabled: bool = False
        self._stats: Dict[str, Any] = {
            "generations": 0,
            "steering_applications": 0,
            "features_tracked": [],
        }

    def enable_steering(self) -> None:
        """Globally enable steering for subsequent generations."""
        self._steering_enabled = True
        logger.info("SteeringPipeline: steering ENABLED")

    def disable_steering(self) -> None:
        """Globally disable steering for subsequent generations."""
        self._steering_enabled = False
        logger.info("SteeringPipeline: steering DISABLED")

    def is_enabled(self) -> bool:
        """Return whether steering is currently enabled."""
        return self._steering_enabled

    def record_generation(self, steering_applied: bool = False) -> None:
        """Record that a generation occurred (used by integrations)."""
        self._stats["generations"] += 1
        if steering_applied:
            self._stats["steering_applications"] += 1

    def record_features(self, feature_ids: List[int]) -> None:
        """Record the SAE feature ids that were touched."""
        self._stats["features_tracked"].extend(feature_ids)

    def get_stats(self) -> Dict[str, Any]:
        """Return a copy of pipeline statistics for the stats tool."""
        return {
            "steering_enabled": self._steering_enabled,
            "generations": self._stats["generations"],
            "steering_applications": self._stats["steering_applications"],
            "features_tracked": list(self._stats["features_tracked"]),
            "config": {
                "steering_scale": self.config.steering_scale,
                "suppression_targets": list(self.config.suppression_targets),
                "inference_backend": self.config.inference_backend,
            },
        }

    def reset_stats(self) -> None:
        """Reset all counters; primarily used by tests."""
        self._stats = {
            "generations": 0,
            "steering_applications": 0,
            "features_tracked": [],
        }


# ---------------------------------------------------------------------------
# Global singleton accessors used by ``steering_tools``.
# ---------------------------------------------------------------------------

_pipeline_lock = threading.Lock()
_global_pipeline: Optional[SteeringPipeline] = None


def get_steering_pipeline() -> SteeringPipeline:
    """Return the process-wide :class:`SteeringPipeline`, creating one lazily."""
    global _global_pipeline
    with _pipeline_lock:
        if _global_pipeline is None:
            _global_pipeline = SteeringPipeline()
        return _global_pipeline


def configure_steering_pipeline(
    config: Optional[SteeringPipelineConfig] = None,
) -> SteeringPipeline:
    """Replace the global pipeline with one built from ``config``.

    Returns the new pipeline so callers can continue to chain
    ``enable_steering()`` etc. on the result.
    """
    global _global_pipeline
    with _pipeline_lock:
        _global_pipeline = SteeringPipeline(config=config)
        return _global_pipeline


def reset_steering_pipeline() -> None:
    """Drop the global pipeline (used by tests for isolation)."""
    global _global_pipeline
    with _pipeline_lock:
        _global_pipeline = None


__all__ = [
    "SteeringPipeline",
    "SteeringPipelineConfig",
    "get_steering_pipeline",
    "configure_steering_pipeline",
    "reset_steering_pipeline",
]
