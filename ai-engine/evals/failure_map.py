"""
Failure-to-Fix Location Mapping

Maps failure modes from eval runs to specific fix locations in the codebase.
This enables the hill-climb loop to automatically determine where to apply fixes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class FixLocation(Enum):
    """Where to apply a fix."""

    BLOCK_MAPPINGS = "block_mappings/"
    ENTITIES = "entities/"
    EVENT_TRANSFORMS = "event_transforms/"
    ITEM_REGISTRY = "item_registry/"
    LOGIC_TRANSLATION = "logic_translation/"
    PROMPTS = "prompts/"
    TOOL_SELECTION = "tool_selection/"
    VALIDATION = "validation/"
    UNKNOWN = "unknown"


@dataclass
class FixAction:
    """A recommended fix action."""

    location: FixLocation
    description: str
    confidence: float
    example_fix: Optional[str] = None
    priority: int = 1


@dataclass
class FailureMapping:
    """Mapping from failure mode to fix actions."""

    failure_mode: str
    possible_locations: List[FixLocation]
    likely_symptoms: List[str]
    fix_recommendations: List[FixAction]


class FailureMapper:
    """Maps eval failures to fix locations."""

    def __init__(self):
        self.mappings = self._build_default_mappings()

    def _build_default_mappings(self) -> Dict[str, FailureMapping]:
        return {
            "missing_block_mapping": FailureMapping(
                failure_mode="MISSING_BLOCK_MAPPING",
                possible_locations=[FixLocation.BLOCK_MAPPINGS],
                likely_symptoms=[
                    "Block identifier not found",
                    "Missing texture reference",
                    "Unknown block type",
                ],
                fix_recommendations=[
                    FixAction(
                        location=FixLocation.BLOCK_MAPPINGS,
                        description="Add missing block mapping to block_mappings/ directory",
                        confidence=0.9,
                        example_fix="Add mapping for custom block to block_mappings/custom_blocks.yaml",
                    )
                ],
            ),
            "incorrect_event_translation": FailureMapping(
                failure_mode="INCORRECT_EVENT_TRANSLATION",
                possible_locations=[FixLocation.EVENT_TRANSFORMS, FixLocation.LOGIC_TRANSLATION],
                likely_symptoms=[
                    "Event not triggering",
                    "Wrong event parameters",
                    "Missing event handler",
                ],
                fix_recommendations=[
                    FixAction(
                        location=FixLocation.EVENT_TRANSFORMS,
                        description="Fix event translation rules in event_transforms/",
                        confidence=0.8,
                        example_fix="Update event mapping in event_transforms/trigger_mapping.yaml",
                    )
                ],
            ),
            "wrong_item_translation": FailureMapping(
                failure_mode="WRONG_ITEM_TRANSLATION",
                possible_locations=[FixLocation.ITEM_REGISTRY],
                likely_symptoms=[
                    "Item not appearing in game",
                    "Wrong item ID",
                    "Missing item properties",
                ],
                fix_recommendations=[
                    FixAction(
                        location=FixLocation.ITEM_REGISTRY,
                        description="Fix item mapping in item_registry/",
                        confidence=0.85,
                        example_fix="Update item definition in item_registry/items.yaml",
                    )
                ],
            ),
            "logic_mistranslation": FailureMapping(
                failure_mode="LOGIC_MISTRANSLATION",
                possible_locations=[FixLocation.LOGIC_TRANSLATION],
                likely_symptoms=[
                    "Behavior not matching Java",
                    "Logic condition wrong",
                    "Missing conditional",
                ],
                fix_recommendations=[
                    FixAction(
                        location=FixLocation.LOGIC_TRANSLATION,
                        description="Fix logic translation rules in logic_translation/",
                        confidence=0.75,
                        example_fix="Update logic rule in logic_translation/conditionals.yaml",
                    )
                ],
            ),
            "prompt_hallucination": FailureMapping(
                failure_mode="PROMPT_HALLUCINATION",
                possible_locations=[FixLocation.PROMPTS],
                likely_symptoms=[
                    "Non-existent Minecraft references",
                    "Wrong API usage",
                    "Fabricated properties",
                ],
                fix_recommendations=[
                    FixAction(
                        location=FixLocation.PROMPTS,
                        description="Improve system prompt to reduce hallucination",
                        confidence=0.7,
                        example_fix="Add explicit constraint to prompts/system.txt to avoid fabricated references",
                    )
                ],
            ),
            "wrong_tool_selection": FailureMapping(
                failure_mode="WRONG_TOOL_SELECTION",
                possible_locations=[FixLocation.TOOL_SELECTION],
                likely_symptoms=[
                    "Wrong converter used",
                    "Suboptimal conversion path",
                    "Incorrect agent selected",
                ],
                fix_recommendations=[
                    FixAction(
                        location=FixLocation.TOOL_SELECTION,
                        description="Fix tool selection logic for this case type",
                        confidence=0.8,
                        example_fix="Update tool selection in agents/tool_selector.py",
                    )
                ],
            ),
            "unexpected_input": FailureMapping(
                failure_mode="UNEXPECTED_INPUT",
                possible_locations=[FixLocation.VALIDATION],
                likely_symptoms=[
                    "Parse error",
                    "Crash on malformed input",
                    "Missing validation feedback",
                ],
                fix_recommendations=[
                    FixAction(
                        location=FixLocation.VALIDATION,
                        description="Improve input validation to handle edge cases",
                        confidence=0.85,
                        example_fix="Add validation in agents/java_analyzer for malformed code",
                    )
                ],
            ),
            "validation_error": FailureMapping(
                failure_mode="VALIDATION_ERROR",
                possible_locations=[FixLocation.VALIDATION],
                likely_symptoms=[
                    "Output doesn't match Bedrock spec",
                    "Missing required fields",
                    "Wrong JSON structure",
                ],
                fix_recommendations=[
                    FixAction(
                        location=FixLocation.VALIDATION,
                        description="Improve validation rules for Bedrock output",
                        confidence=0.9,
                        example_fix="Update validation in tools/qa_validator.py",
                    )
                ],
            ),
        }

    def map_failure(
        self, failure_mode: str, context: Optional[Dict[str, Any]] = None
    ) -> FailureMapping:
        """Map a failure mode to its likely fix location."""
        mapping = self.mappings.get(failure_mode)
        if mapping:
            return mapping
        return FailureMapping(
            failure_mode=failure_mode,
            possible_locations=[FixLocation.UNKNOWN],
            likely_symptoms=["Unknown error"],
            fix_recommendations=[
                FixAction(
                    location=FixLocation.UNKNOWN,
                    description="Manual investigation required",
                    confidence=0.0,
                )
            ],
        )

    def get_fix_priority(self, failure_mode: str) -> int:
        """Get the priority of fixing a specific failure mode."""
        mapping = self.mappings.get(failure_mode)
        if mapping and mapping.fix_recommendations:
            return mapping.fix_recommendations[0].priority
        return 10

    def suggest_fixes(
        self, failure_mode: str, context: Optional[Dict[str, Any]] = None
    ) -> List[FixAction]:
        """Suggest specific fix actions for a failure mode."""
        mapping = self.map_failure(failure_mode, context)
        return sorted(mapping.fix_recommendations, key=lambda x: x.confidence, reverse=True)