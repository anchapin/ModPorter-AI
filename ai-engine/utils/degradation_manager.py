"""
Degradation Manager

Manages graceful degradation of the conversion pipeline with fallback strategies
and multiple degradation levels.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable
import logging
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class DegradationLevel(Enum):
    """Degradation levels for conversion pipeline."""

    FULL = "full"
    REDUCED = "reduced"
    BASIC = "basic"
    EMERGENCY = "emergency"


@dataclass
class FallbackStrategy:
    """Defines a fallback strategy for a component."""

    name: str
    method: Callable
    conditions: list[str] = field(default_factory=list)
    priority: int = 0

    def __repr__(self) -> str:
        return f"FallbackStrategy(name={self.name}, priority={self.priority})"


@dataclass
class DegradationConfig:
    """Configuration for degradation behavior."""

    degradation_levels: dict[str, dict[str, Any]] = field(default_factory=dict)
    fallback_strategies: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    degradation_triggers: list[str] = field(default_factory=list)
    partial_output_minimum: float = 0.3

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> "DegradationConfig":
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls(
            degradation_levels=data.get("degradation_levels", {}),
            fallback_strategies=data.get("fallback_strategies", {}),
            degradation_triggers=data.get("degradation_triggers", []),
            partial_output_minimum=data.get("partial_output_minimum", 0.3),
        )


class DegradationManager:
    """
    Manages graceful degradation and fallback strategies for conversion pipeline.

    This class handles:
    - Multiple degradation levels (FULL, REDUCED, BASIC, EMERGENCY)
    - Fallback chain execution for failed components
    - Integration with timeout management from Phase 10-01
    """

    def __init__(self, config: DegradationConfig | str | Path | None = None):
        """
        Initialize the degradation manager.

        Args:
            config: DegradationConfig object or path to config YAML file.
        """
        if isinstance(config, (str, Path)):
            self.config = DegradationConfig.from_yaml(config)
        elif config is None:
            self.config = DegradationConfig()
        else:
            self.config = config

        self._current_level = DegradationLevel.FULL
        self._fallback_chains: dict[str, list[FallbackStrategy]] = {}
        self._fallback_methods: dict[str, list[Callable]] = {}
        self._initialize_default_chains()

    def _initialize_default_chains(self) -> None:
        """Initialize default fallback chains from config."""
        for component, strategies in self.config.fallback_strategies.items():
            chain = []
            for strategy_def in strategies:
                # Create a placeholder strategy - actual methods registered later
                chain.append(
                    FallbackStrategy(
                        name=strategy_def.get("name", component),
                        method=lambda: None,  # Placeholder
                        conditions=strategy_def.get("conditions", []),
                        priority=strategy_def.get("priority", 0),
                    )
                )
            self._fallback_chains[component] = chain

    def register_fallback(self, component: str, strategies: list[Callable]) -> None:
        """
        Register fallback chain for a component.

        Args:
            component: The component name.
            strategies: List of callable fallback methods in priority order.
        """
        self._fallback_methods[component] = strategies
        logger.info(
            f"Registered {len(strategies)} fallback strategies for component '{component}'"
        )

    def execute_with_fallback(
        self,
        component: str,
        primary_method: Callable,
        *args,
        **kwargs,
    ) -> tuple[Any, bool]:
        """
        Execute a method with fallback on failure.

        Args:
            component: The component name for fallback lookup.
            primary_method: The primary method to try first.
            *args: Positional arguments for the methods.
            **kwargs: Keyword arguments for the methods.

        Returns:
            Tuple of (result, used_fallback).
        """
        # Try primary method first
        try:
            result = primary_method(*args, **kwargs)
            logger.debug(f"Primary method succeeded for component '{component}'")
            return result, False
        except Exception as primary_error:
            logger.warning(
                f"Primary method failed for '{component}': {primary_error}"
            )

        # Try fallback methods
        fallbacks = self._fallback_methods.get(component, [])
        for i, fallback_method in enumerate(fallbacks):
            try:
                logger.info(
                    f"Attempting fallback {i + 1}/{len(fallbacks)} for '{component}'"
                )
                result = fallback_method(*args, **kwargs)
                logger.info(f"Fallback {i + 1} succeeded for component '{component}'")
                return result, True
            except Exception as fallback_error:
                logger.warning(
                    f"Fallback {i + 1} failed for '{component}': {fallback_error}"
                )
                continue

        # All methods failed
        logger.error(
            f"All methods failed for component '{component}', "
            f"escalating degradation"
        )
        self.escalate_degradation()
        return None, True

    def should_degrade(self, error: Exception) -> bool:
        """
        Determine if an error warrants degradation.

        Args:
            error: The exception that occurred.

        Returns:
            True if degradation should be triggered.
        """
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()

        for trigger in self.config.degradation_triggers:
            if trigger in error_type or trigger in error_message:
                logger.info(f"Degradation triggered by: {trigger}")
                return True

        # Also check for common timeout-related errors
        timeout_indicators = ["timeout", "deadline", "timed out"]
        if any(indicator in error_type or indicator in error_message for indicator in timeout_indicators):
            logger.info("Degradation triggered by timeout-related error")
            return True

        return False

    def escalate_degradation(self) -> None:
        """Move to the next higher degradation level."""
        levels = list(DegradationLevel)
        try:
            current_index = levels.index(self._current_level)
            if current_index < len(levels) - 1:
                self._current_level = levels[current_index + 1]
                logger.warning(
                    f"Degradation escalated to level: {self._current_level.value}"
                )
        except ValueError:
            logger.error(f"Invalid degradation level: {self._current_level}")

    def reduce_degradation(self) -> None:
        """Reduce degradation level (for recovery)."""
        levels = list(DegradationLevel)
        try:
            current_index = levels.index(self._current_level)
            if current_index > 0:
                self._current_level = levels[current_index - 1]
                logger.info(f"Degradation reduced to level: {self._current_level.value}")
        except ValueError:
            logger.error(f"Invalid degradation level: {self._current_level}")

    def get_current_level(self) -> DegradationLevel:
        """Get the current degradation level."""
        return self._current_level

    def set_level(self, level: DegradationLevel) -> None:
        """
        Set the degradation level directly.

        Args:
            level: The desired degradation level.
        """
        self._current_level = level
        logger.info(f"Degradation level set to: {level.value}")

    def get_validation_skip_list(self) -> list[str]:
        """
        Get list of validations to skip based on current degradation level.

        Returns:
            List of validation names to skip.
        """
        level_config = self.config.degradation_levels.get(
            self._current_level.value, {}
        )
        return level_config.get("skip_validations", [])

    def is_validation_required(self, validation_name: str) -> bool:
        """
        Check if a validation should be run based on degradation level.

        Args:
            validation_name: The name of the validation.

        Returns:
            True if validation should run.
        """
        skip_list = self.get_validation_skip_list()
        return validation_name not in skip_list

    def get_timeout_multiplier(self) -> float:
        """
        Get timeout multiplier based on degradation level.

        Higher degradation levels use longer timeouts to allow more processing time.

        Returns:
            Timeout multiplier (1.0 = normal).
        """
        multipliers = {
            DegradationLevel.FULL: 1.0,
            DegradationLevel.REDUCED: 1.25,
            DegradationLevel.BASIC: 1.5,
            DegradationLevel.EMERGENCY: 2.0,
        }
        return multipliers.get(self._current_level, 1.0)

    def get_status_report(self) -> dict[str, Any]:
        """
        Get current degradation status.

        Returns:
            Dictionary with status information.
        """
        return {
            "current_level": self._current_level.value,
            "validation_skip_list": self.get_validation_skip_list(),
            "timeout_multiplier": self.get_timeout_multiplier(),
            "registered_components": list(self._fallback_methods.keys()),
            "partial_output_minimum": self.config.partial_output_minimum,
        }

    def reset(self) -> None:
        """Reset degradation to full level."""
        self._current_level = DegradationLevel.FULL
        logger.info("Degradation manager reset to FULL level")


def get_degradation_manager(
    config_path: str | Path | None = None,
) -> DegradationManager:
    """
    Get a degradation manager instance.

    Args:
        config_path: Optional path to degradation config YAML.

    Returns:
        Configured DegradationManager instance.
    """
    if config_path is None:
        # Try default location
        default_path = Path(__file__).parent.parent / "config" / "degradation_config.yaml"
        if default_path.exists():
            config_path = default_path

    return DegradationManager(config_path)
