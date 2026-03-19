"""
Partial Conversion Engine

Tracks successful and failed conversion components, generates partial output
when full conversion is not possible.
"""

from dataclasses import dataclass, field
from typing import Any
import json
import logging

logger = logging.getLogger(__name__)


# Component types that can be partially converted
COMPONENT_TYPES = [
    "manifest",
    "items",
    "blocks",
    "entities",
    "recipes",
    "scripts",
    "textures",
    "sounds",
]


@dataclass
class PartialConversionResult:
    """Result of a partial conversion operation."""

    components_converted: list[str] = field(default_factory=list)
    components_failed: list[str] = field(default_factory=list)
    partial_output: dict[str, Any] = field(default_factory=dict)
    completeness_percentage: float = 0.0
    warnings: list[str] = field(default_factory=list)
    error_details: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "components_converted": self.components_converted,
            "components_failed": self.components_failed,
            "partial_output": self.partial_output,
            "completeness_percentage": self.completeness_percentage,
            "warnings": self.warnings,
            "error_details": self.error_details,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def is_success(self) -> bool:
        """Check if conversion was fully successful."""
        return len(self.components_failed) == 0

    def has_partial_output(self) -> bool:
        """Check if partial output is available."""
        return len(self.components_converted) > 0


class PartialConverter:
    """
    Tracks partial conversion progress and generates partial output.

    This class manages the tracking of which components have been
    successfully converted and which have failed, enabling the system
    to produce usable output even when full conversion is not possible.
    """

    def __init__(self, component_types: list[str] | None = None):
        """
        Initialize the partial converter.

        Args:
            component_types: List of component types to track.
                           Defaults to standard COMPONENT_TYPES.
        """
        self.component_types = component_types or COMPONENT_TYPES.copy()
        self._converted: dict[str, Any] = {}
        self._failed: dict[str, str] = {}
        self._warnings: list[str] = []
        self._started = False

    def start_conversion(self) -> None:
        """Initialize tracking for conversion components."""
        self._converted = {}
        self._failed = {}
        self._warnings = []
        self._started = True
        logger.info(
            f"Partial conversion tracking started for components: {self.component_types}"
        )

    def mark_component_success(self, component: str, output: Any) -> None:
        """
        Record a successful component conversion.

        Args:
            component: The component type that was successfully converted.
            output: The converted output for this component.
        """
        if not self._started:
            self.start_conversion()

        if component in self.component_types:
            self._converted[component] = output
            if component in self._failed:
                del self._failed[component]
            logger.info(f"Component '{component}' marked as successfully converted")
        else:
            self._warnings.append(f"Unknown component type: {component}")

    def mark_component_failure(self, component: str, error: str) -> None:
        """
        Record a failed component conversion.

        Args:
            component: The component type that failed to convert.
            error: The error message or reason for failure.
        """
        if not self._started:
            self.start_conversion()

        if component in self.component_types:
            self._failed[component] = error
            if component in self._converted:
                del self._converted[component]
            logger.warning(f"Component '{component}' marked as failed: {error}")
        else:
            self._warnings.append(f"Unknown component type: {component}")

    def get_converted_components(self) -> list[str]:
        """Get list of successfully converted components."""
        return list(self._converted.keys())

    def get_failed_components(self) -> list[str]:
        """Get list of failed components."""
        return list(self._failed.keys())

    def generate_partial_output(self) -> PartialConversionResult:
        """
        Generate partial output from successfully converted components.

        Returns:
            PartialConversionResult containing all tracked information.
        """
        if not self._started:
            return PartialConversionResult(
                warnings=["Conversion not started"]
            )

        # Calculate completeness percentage
        total = len(self.component_types)
        converted_count = len(self._converted)
        completeness = (converted_count / total * 100) if total > 0 else 0.0

        # Build partial output
        partial_output = {
            "manifest": self._converted.get("manifest", {}),
            "items": self._converted.get("items", []),
            "blocks": self._converted.get("blocks", []),
            "entities": self._converted.get("entities", []),
            "recipes": self._converted.get("recipes", []),
            "scripts": self._converted.get("scripts", []),
            "textures": self._converted.get("textures", []),
            "sounds": self._converted.get("sounds", []),
        }

        # Add warnings for missing components
        for component in self.component_types:
            if component not in self._converted and component not in self._failed:
                self._warnings.append(f"Component '{component}' was not processed")

        result = PartialConversionResult(
            components_converted=list(self._converted.keys()),
            components_failed=list(self._failed.keys()),
            partial_output=partial_output,
            completeness_percentage=completeness,
            warnings=self._warnings.copy(),
            error_details=self._failed.copy(),
        )

        logger.info(
            f"Partial output generated: {completeness:.1f}% complete "
            f"({converted_count}/{total} components)"
        )

        return result

    def get_completeness_report(self) -> dict[str, Any]:
        """
        Get detailed completeness report.

        Returns:
            Dictionary with detailed completeness information.
        """
        if not self._started:
            return {"status": "not_started", "completeness": 0.0}

        total = len(self.component_types)
        converted_count = len(self._converted)
        failed_count = len(self._failed)
        processed_count = converted_count + failed_count

        return {
            "status": "complete" if failed_count == 0 else "partial",
            "completeness_percentage": (converted_count / total * 100) if total > 0 else 0.0,
            "total_components": total,
            "converted_count": converted_count,
            "failed_count": failed_count,
            "unprocessed_count": total - processed_count,
            "converted_components": list(self._converted.keys()),
            "failed_components": list(self._failed.keys()),
            "warnings": self._warnings.copy(),
        }

    def is_complete_enough(self, minimum_percentage: float = 30.0) -> bool:
        """
        Check if partial output meets minimum threshold.

        Args:
            minimum_percentage: Minimum required completeness percentage.

        Returns:
            True if partial output meets threshold.
        """
        total = len(self.component_types)
        converted_count = len(self._converted)
        completeness = (converted_count / total * 100) if total > 0 else 0.0
        return completeness >= minimum_percentage

    def reset(self) -> None:
        """Reset all tracked conversion state."""
        self._converted = {}
        self._failed = {}
        self._warnings = []
        self._started = False
        logger.info("Partial conversion tracking reset")
