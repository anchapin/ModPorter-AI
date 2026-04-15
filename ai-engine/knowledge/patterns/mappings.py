"""
Pattern mappings between Java and Bedrock patterns.

Provides bidirectional mappings with confidence scores and conversion notes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class MappingConfidence(Enum):
    """Confidence levels for pattern mappings."""

    HIGH = "high"  # Direct, proven equivalent
    MEDIUM = "medium"  # Functional equivalent with minor differences
    LOW = "low"  # Conceptual equivalent, requires manual review
    EXPERIMENTAL = "experimental"  # Untested mapping


@dataclass
class PatternMapping:
    """
    Represents a mapping between Java and Bedrock patterns.

    Includes confidence score, conversion notes, and limitations.
    """

    java_pattern_id: str
    bedrock_pattern_id: str
    confidence: float  # 0.0-1.0
    notes: str = ""
    limitations: List[str] = field(default_factory=list)
    requires_manual_review: bool = False

    def __post_init__(self):
        """Validate mapping data."""
        if not self.java_pattern_id:
            raise ValueError("Java pattern ID cannot be empty")
        if not self.bedrock_pattern_id:
            raise ValueError("Bedrock pattern ID cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")

    def to_dict(self) -> Dict:
        """Convert mapping to dictionary."""
        return {
            "java_pattern_id": self.java_pattern_id,
            "bedrock_pattern_id": self.bedrock_pattern_id,
            "confidence": self.confidence,
            "notes": self.notes,
            "limitations": self.limitations,
            "requires_manual_review": self.requires_manual_review,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PatternMapping":
        """Create mapping from dictionary."""
        return cls(
            java_pattern_id=data["java_pattern_id"],
            bedrock_pattern_id=data["bedrock_pattern_id"],
            confidence=data["confidence"],
            notes=data.get("notes", ""),
            limitations=data.get("limitations", []),
            requires_manual_review=data.get("requires_manual_review", False),
        )


class PatternMappingRegistry:
    """
    Registry of Java→Bedrock pattern mappings.

    Pre-populated with 20+ mappings for common conversion scenarios.
    """

    def __init__(self):
        """Initialize registry with default mappings."""
        self.mappings: Dict[str, PatternMapping] = {}  # key: java_pattern_id
        self._initialize_mappings()

    def _initialize_mappings(self) -> None:
        """Initialize registry with default mappings."""
        # Item Mappings
        self._add_item_mappings()

        # Block Mappings
        self._add_block_mappings()

        # Entity Mappings
        self._add_entity_mappings()

        # Recipe Mappings
        self._add_recipe_mappings()

        # Event Mappings
        self._add_event_mappings()

        # Capability Mappings
        self._add_capability_mappings()

        # Tile Entity Mappings
        self._add_tile_entity_mappings()

        # Network Mappings
        self._add_network_mappings()

    def _add_item_mappings(self) -> None:
        """Add item-related mappings."""
        self.mappings["java_simple_item"] = PatternMapping(
            java_pattern_id="java_simple_item",
            bedrock_pattern_id="bedrock_simple_item",
            confidence=0.95,
            notes="Direct mapping: Java Item class → JSON item definition",
            limitations=[
                "Java class-based inheritance → JSON components",
                "Creative tabs require creative_category component",
            ],
            requires_manual_review=False,
        )

        self.mappings["java_item_properties"] = PatternMapping(
            java_pattern_id="java_item_properties",
            bedrock_pattern_id="bedrock_item_durability",
            confidence=0.90,
            notes="Item properties map to components",
            limitations=[
                "Durability system differs slightly",
                "Stack size is max_stack_size component",
            ],
            requires_manual_review=False,
        )

        self.mappings["java_food_item"] = PatternMapping(
            java_pattern_id="java_food_item",
            bedrock_pattern_id="bedrock_food_item",
            confidence=0.95,
            notes="Food items map directly to food component",
            limitations=[
                "Saturation calculation differs",
                "Always_edible flag may need manual adjustment",
            ],
            requires_manual_review=False,
        )

        self.mappings["java_ranged_weapon"] = PatternMapping(
            java_pattern_id="java_ranged_weapon",
            bedrock_pattern_id="bedrock_ranged_weapon",
            confidence=0.75,
            notes="Bow-like items use shooter component",
            limitations=[
                "Projectile spawning logic moves to Script API",
                "Custom projectile behavior requires entity definitions",
            ],
            requires_manual_review=True,
        )

    def _add_block_mappings(self) -> None:
        """Add block-related mappings."""
        self.mappings["java_simple_block"] = PatternMapping(
            java_pattern_id="java_simple_block",
            bedrock_pattern_id="bedrock_simple_block",
            confidence=0.90,
            notes="Basic block properties map to components",
            limitations=[
                "Material system differs (enum vs string)",
                "Sound types have different names",
            ],
            requires_manual_review=False,
        )

        self.mappings["java_block_properties"] = PatternMapping(
            java_pattern_id="java_block_properties",
            bedrock_pattern_id="bedrock_block_states",
            confidence=0.80,
            notes="Block states map to permutations",
            limitations=[
                "StateProperty → description.properties",
                "State logic moves to permutations with conditions",
            ],
            requires_manual_review=True,
        )

        self.mappings["java_rotatable_block"] = PatternMapping(
            java_pattern_id="java_rotatable_block",
            bedrock_pattern_id="bedrock_rotatable_block",
            confidence=0.70,
            notes="Horizontal rotation uses events and permutations",
            limitations=[
                "Placement logic moves to on_player_placed event",
                "Rotation requires geometry component",
            ],
            requires_manual_review=True,
        )

    def _add_entity_mappings(self) -> None:
        """Add entity-related mappings."""
        self.mappings["java_simple_entity"] = PatternMapping(
            java_pattern_id="java_simple_entity",
            bedrock_pattern_id="bedrock_simple_entity",
            confidence=0.85,
            notes="Basic entity structure maps to JSON + components",
            limitations=[
                "AI goals → behavior components",
                "Goal selector priority → component group ordering",
            ],
            requires_manual_review=True,
        )

        self.mappings["java_entity_attributes"] = PatternMapping(
            java_pattern_id="java_entity_attributes",
            bedrock_pattern_id="bedrock_entity_attributes",
            confidence=0.90,
            notes="Attributes map to components",
            limitations=[
                "Attribute system differs (double vs component)",
                "Custom attributes require component definitions",
            ],
            requires_manual_review=False,
        )

    def _add_recipe_mappings(self) -> None:
        """Add recipe-related mappings."""
        self.mappings["java_shaped_recipe"] = PatternMapping(
            java_pattern_id="java_shaped_recipe",
            bedrock_pattern_id="bedrock_shaped_recipe",
            confidence=0.95,
            notes="Shaped recipes map directly",
            limitations=[
                "Pattern characters must match key definitions",
                "Unlock conditions differ",
            ],
            requires_manual_review=False,
        )

        self.mappings["java_shapeless_recipe"] = PatternMapping(
            java_pattern_id="java_shapeless_recipe",
            bedrock_pattern_id="bedrock_shapeless_recipe",
            confidence=0.95,
            notes="Shapeless recipes map directly",
            limitations=[
                "Ingredient matching is exact",
            ],
            requires_manual_review=False,
        )

        self.mappings["java_smelting_recipe"] = PatternMapping(
            java_pattern_id="java_smelting_recipe",
            bedrock_pattern_id="bedrock_smelting_recipe",
            confidence=0.95,
            notes="Smelting recipes map directly",
            limitations=[
                "Cook time is in ticks (same)",
                "Experience is not used in Bedrock",
            ],
            requires_manual_review=False,
        )

    def _add_event_mappings(self) -> None:
        """Add event handler mappings."""
        self.mappings["java_player_interact"] = PatternMapping(
            java_pattern_id="java_player_interact",
            bedrock_pattern_id="bedrock_player_interact",
            confidence=0.75,
            notes="Event bus → Script API afterEvents",
            limitations=[
                "@SubscribeEvent → world.afterEvents.subscribe",
                "Event objects have different properties",
                "Client/server split requires careful handling",
            ],
            requires_manual_review=True,
        )

        self.mappings["java_block_break"] = PatternMapping(
            java_pattern_id="java_block_break",
            bedrock_pattern_id="bedrock_block_break",
            confidence=0.80,
            notes="Block events map to Script API",
            limitations=[
                "BlockBreakEvent → blockBreak afterEvent",
                "XP dropping requires entity spawning",
            ],
            requires_manual_review=True,
        )

        self.mappings["java_entity_join"] = PatternMapping(
            java_pattern_id="java_entity_join",
            bedrock_pattern_id="bedrock_entity_spawn",
            confidence=0.80,
            notes="Entity spawn events map to Script API",
            limitations=[
                "EntityJoinLevelEvent → entitySpawn afterEvent",
                "Entity modifications happen differently",
            ],
            requires_manual_review=True,
        )

    def _add_capability_mappings(self) -> None:
        """Add capability-related mappings."""
        self.mappings["java_item_handler"] = PatternMapping(
            java_pattern_id="java_item_handler",
            bedrock_pattern_id="bedrock_item_container",
            confidence=0.70,
            notes="IItemHandler → inventory component",
            limitations=[
                "Interface methods → component + Script API",
                "Slot extraction requires Script API",
                "Automation (hoppers, etc.) differs",
            ],
            requires_manual_review=True,
        )

        self.mappings["java_fluid_handler"] = PatternMapping(
            java_pattern_id="java_fluid_handler",
            bedrock_pattern_id="bedrock_fluid_container",
            confidence=0.60,
            notes="IFluidHandler → custom fluid system",
            limitations=[
                "No built-in fluid component",
                "Must implement using dynamic properties + Script API",
                "Fluid types are limited",
            ],
            requires_manual_review=True,
        )

    def _add_tile_entity_mappings(self) -> None:
        """Add tile entity-related mappings."""
        self.mappings["java_tile_entity"] = PatternMapping(
            java_pattern_id="java_tile_entity",
            bedrock_pattern_id="bedrock_block_entity",
            confidence=0.75,
            notes="TileEntity → dynamic properties",
            limitations=[
                "NBT data → dynamic properties",
                "Save/load logic → automatic with dynamic properties",
                "Data access requires Script API",
            ],
            requires_manual_review=True,
        )

        self.mappings["java_ticking_tile"] = PatternMapping(
            java_pattern_id="java_ticking_tile",
            bedrock_pattern_id="bedrock_ticking_block",
            confidence=0.65,
            notes="Ticking tile entity → system.runInterval",
            limitations=[
                "No built-in tick system for blocks",
                "Must use Script API interval",
                "Performance concerns with many ticking blocks",
            ],
            requires_manual_review=True,
        )

    def _add_network_mappings(self) -> None:
        """Add network-related mappings."""
        self.mappings["java_network_packet"] = PatternMapping(
            java_pattern_id="java_network_packet",
            bedrock_pattern_id="bedrock_network_packet",
            confidence=0.60,
            notes="Custom packets → dynamic properties + events",
            limitations=[
                "No direct packet system",
                "Communication via player dynamic properties",
                "Client-side scripts have limited access",
            ],
            requires_manual_review=True,
        )

    def add_mapping(self, mapping: PatternMapping) -> None:
        """
        Add a mapping to the registry.

        Args:
            mapping: Mapping to add

        Raises:
            ValueError: If java_pattern_id already exists
        """
        if mapping.java_pattern_id in self.mappings:
            raise ValueError(f"Mapping for {mapping.java_pattern_id} already exists")
        self.mappings[mapping.java_pattern_id] = mapping

    def get_bedrock_equivalent(self, java_pattern_id: str) -> Optional[PatternMapping]:
        """
        Get Bedrock equivalent for a Java pattern.

        Args:
            java_pattern_id: Java pattern identifier

        Returns:
            PatternMapping if found, None otherwise
        """
        return self.mappings.get(java_pattern_id)

    def get_all_mappings(self) -> List[PatternMapping]:
        """
        Get all registered mappings.

        Returns:
            List of all mappings
        """
        return list(self.mappings.values())

    def get_by_confidence(self, min_confidence: float) -> List[PatternMapping]:
        """
        Get mappings with confidence >= min_confidence.

        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            List of mappings meeting the threshold
        """
        return [
            mapping for mapping in self.mappings.values() if mapping.confidence >= min_confidence
        ]

    def get_manual_review_required(self) -> List[PatternMapping]:
        """
        Get mappings that require manual review.

        Returns:
            List of mappings requiring manual review
        """
        return [mapping for mapping in self.mappings.values() if mapping.requires_manual_review]

    def get_stats(self) -> Dict[str, int]:
        """
        Get registry statistics.

        Returns:
            Dictionary with total mappings and confidence breakdown
        """
        total = len(self.mappings)

        confidence_counts = {
            "high": len([m for m in self.mappings.values() if m.confidence >= 0.8]),
            "medium": len([m for m in self.mappings.values() if 0.5 <= m.confidence < 0.8]),
            "low": len([m for m in self.mappings.values() if m.confidence < 0.5]),
        }

        manual_review_count = len([m for m in self.mappings.values() if m.requires_manual_review])

        return {
            "total": total,
            "by_confidence": confidence_counts,
            "requires_manual_review": manual_review_count,
        }
