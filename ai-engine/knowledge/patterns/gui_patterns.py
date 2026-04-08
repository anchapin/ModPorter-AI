"""
GUI Pattern Library for RAG-based GUI conversion.

Provides pattern matching and retrieval for Java to Bedrock GUI conversion
including screens, containers, controls, and component mappings.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class GUICategory(Enum):
    """GUI pattern categories."""

    SCREEN = "screen"
    CONTAINER = "container"
    CONTROL = "control"
    LAYOUT = "layout"
    EVENT = "event"
    CUSTOM = "custom"


@dataclass
class GUIPattern:
    """
    Represents a single GUI conversion pattern.

    Contains Java GUI class reference and corresponding Bedrock control
    type with conversion notes and metadata.
    """

    java_component_class: str
    bedrock_control_type: str
    category: GUICategory
    conversion_notes: str
    screen_type: str = "generic"  # Which screen type this applies to
    rarity: int = 1  # 1-100, how common

    def to_dict(self) -> Dict:
        """Convert pattern to dictionary."""
        return {
            "java_component_class": self.java_component_class,
            "bedrock_control_type": self.bedrock_control_type,
            "category": self.category.value,
            "conversion_notes": self.conversion_notes,
            "screen_type": self.screen_type,
            "rarity": self.rarity,
        }


class GUIPatternLibrary:
    """
    Library of GUI conversion patterns.

    Provides storage, retrieval, and search functionality for
    Java→Bedrock GUI pattern conversion.
    """

    def __init__(self):
        """Initialize pattern library with default patterns."""
        self.patterns: List[GUIPattern] = []
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default GUI patterns (25+ patterns)."""

        # Screen patterns (5 patterns)
        screen_patterns = [
            GUIPattern(
                java_component_class="Screen",
                bedrock_control_type="screen",
                category=GUICategory.SCREEN,
                conversion_notes="Base Java Screen maps to generic Bedrock screen",
                screen_type="generic",
                rarity=50,
            ),
            GUIPattern(
                java_component_class="ContainerScreen",
                bedrock_control_type="screen",
                category=GUICategory.SCREEN,
                conversion_notes="Java ContainerScreen maps to Bedrock inventory screen",
                screen_type="inventory",
                rarity=80,
            ),
            GUIPattern(
                java_component_class="InventoryScreen",
                bedrock_control_type="screen",
                category=GUICategory.SCREEN,
                conversion_notes="Java InventoryScreen maps to Bedrock player inventory",
                screen_type="inventory",
                rarity=90,
            ),
            GUIPattern(
                java_component_class="CraftingScreen",
                bedrock_control_type="screen",
                category=GUICategory.SCREEN,
                conversion_notes="Java CraftingScreen maps to Bedrock crafting UI",
                screen_type="crafting",
                rarity=70,
            ),
            GUIPattern(
                java_component_class="MainMenuScreen",
                bedrock_control_type="screen",
                category=GUICategory.SCREEN,
                conversion_notes="Java MainMenuScreen maps to Bedrock main menu",
                screen_type="menu",
                rarity=95,
            ),
            GUIPattern(
                java_component_class="ChatScreen",
                bedrock_control_type="screen",
                category=GUICategory.SCREEN,
                conversion_notes="Java ChatScreen maps to Bedrock chat UI",
                screen_type="chat",
                rarity=85,
            ),
            GUIPattern(
                java_component_class="OptionsScreen",
                bedrock_control_type="screen",
                category=GUICategory.SCREEN,
                conversion_notes="Java OptionsScreen maps to Bedrock settings UI",
                screen_type="options",
                rarity=75,
            ),
        ]

        # Container patterns (10 patterns)
        container_patterns = [
            GUIPattern(
                java_component_class="ChestContainer",
                bedrock_control_type="inventory",
                category=GUICategory.CONTAINER,
                conversion_notes="Java ChestContainer maps to Bedrock chest inventory",
                screen_type="inventory",
                rarity=80,
            ),
            GUIPattern(
                java_component_class="LargeChestContainer",
                bedrock_control_type="inventory",
                category=GUICategory.CONTAINER,
                conversion_notes="Java LargeChestContainer maps to Bedrock large chest",
                screen_type="inventory",
                rarity=60,
            ),
            GUIPattern(
                java_component_class="FurnaceContainer",
                bedrock_control_type="furnace",
                category=GUICategory.CONTAINER,
                conversion_notes="Java FurnaceContainer maps to Bedrock furnace UI",
                screen_type="furnace",
                rarity=70,
            ),
            GUIPattern(
                java_component_class="HopperContainer",
                bedrock_control_type="hopper",
                category=GUICategory.CONTAINER,
                conversion_notes="Java HopperContainer maps to Bedrock hopper inventory",
                screen_type="inventory",
                rarity=50,
            ),
            GUIPattern(
                java_component_class="DispenserContainer",
                bedrock_control_type="inventory",
                category=GUICategory.CONTAINER,
                conversion_notes="Java DispenserContainer maps to Bedrock dispenser",
                screen_type="inventory",
                rarity=45,
            ),
            GUIPattern(
                java_component_class="EnchantmentContainer",
                bedrock_control_type="enchantment",
                category=GUICategory.CONTAINER,
                conversion_notes="Java EnchantmentContainer maps to Bedrock enchantment UI",
                screen_type="enchantment",
                rarity=55,
            ),
            GUIPattern(
                java_component_class="AnvilContainer",
                bedrock_control_type="anvil",
                category=GUICategory.CONTAINER,
                conversion_notes="Java AnvilContainer maps to Bedrock anvil UI",
                screen_type="anvil",
                rarity=50,
            ),
            GUIPattern(
                java_component_class="BeaconContainer",
                bedrock_control_type="beacon",
                category=GUICategory.CONTAINER,
                conversion_notes="Java BeaconContainer maps to Bedrock beacon UI",
                screen_type="beacon",
                rarity=40,
            ),
            GUIPattern(
                java_component_class="BrewingStandContainer",
                bedrock_control_type="brewing_stand",
                category=GUICategory.CONTAINER,
                conversion_notes="Java BrewingStandContainer maps to Bedrock brewing UI",
                screen_type="brewing",
                rarity=45,
            ),
            GUIPattern(
                java_component_class="MerchantContainer",
                bedrock_control_type="merchant",
                category=GUICategory.CONTAINER,
                conversion_notes="Java MerchantContainer maps to Bedrock villager trading UI",
                screen_type="merchant",
                rarity=60,
            ),
        ]

        # Control patterns (15 patterns)
        control_patterns = [
            GUIPattern(
                java_component_class="GuiButton",
                bedrock_control_type="button",
                category=GUICategory.CONTROL,
                conversion_notes="Java GuiButton maps to Bedrock button control",
                screen_type="generic",
                rarity=90,
            ),
            GUIPattern(
                java_component_class="Button",
                bedrock_control_type="button",
                category=GUICategory.CONTROL,
                conversion_notes="Java Button maps to Bedrock button control",
                screen_type="generic",
                rarity=90,
            ),
            GUIPattern(
                java_component_class="GuiTextField",
                bedrock_control_type="input",
                category=GUICategory.CONTROL,
                conversion_notes="Java GuiTextField maps to Bedrock input control",
                screen_type="generic",
                rarity=70,
            ),
            GUIPattern(
                java_component_class="TextField",
                bedrock_control_type="input",
                category=GUICategory.CONTROL,
                conversion_notes="Java TextField maps to Bedrock input control",
                screen_type="generic",
                rarity=70,
            ),
            GUIPattern(
                java_component_class="GuiTextFieldWidget",
                bedrock_control_type="input",
                category=GUICategory.CONTROL,
                conversion_notes="Java GuiTextFieldWidget maps to Bedrock input control",
                screen_type="generic",
                rarity=65,
            ),
            GUIPattern(
                java_component_class="GuiLabel",
                bedrock_control_type="label",
                category=GUICategory.CONTROL,
                conversion_notes="Java GuiLabel maps to Bedrock label control",
                screen_type="generic",
                rarity=80,
            ),
            GUIPattern(
                java_component_class="Label",
                bedrock_control_type="label",
                category=GUICategory.CONTROL,
                conversion_notes="Java Label maps to Bedrock label control",
                screen_type="generic",
                rarity=80,
            ),
            GUIPattern(
                java_component_class="GuiImage",
                bedrock_control_type="image",
                category=GUICategory.CONTROL,
                conversion_notes="Java GuiImage maps to Bedrock image control",
                screen_type="generic",
                rarity=60,
            ),
            GUIPattern(
                java_component_class="GuiSlider",
                bedrock_control_type="slider",
                category=GUICategory.CONTROL,
                conversion_notes="Java GuiSlider maps to Bedrock slider control",
                screen_type="generic",
                rarity=55,
            ),
            GUIPattern(
                java_component_class="SliderWidget",
                bedrock_control_type="slider",
                category=GUICategory.CONTROL,
                conversion_notes="Java SliderWidget maps to Bedrock slider control",
                screen_type="generic",
                rarity=55,
            ),
            GUIPattern(
                java_component_class="GuiCheckbox",
                bedrock_control_type="checkbox",
                category=GUICategory.CONTROL,
                conversion_notes="Java GuiCheckbox maps to Bedrock checkbox control",
                screen_type="generic",
                rarity=50,
            ),
            GUIPattern(
                java_component_class="CheckboxWidget",
                bedrock_control_type="checkbox",
                category=GUICategory.CONTROL,
                conversion_notes="Java CheckboxWidget maps to Bedrock checkbox control",
                screen_type="generic",
                rarity=50,
            ),
            GUIPattern(
                java_component_class="GuiDropdown",
                bedrock_control_type="dropdown",
                category=GUICategory.CONTROL,
                conversion_notes="Java GuiDropdown maps to Bedrock dropdown control",
                screen_type="generic",
                rarity=45,
            ),
            GUIPattern(
                java_component_class="ScrollContainer",
                bedrock_control_type="scroll",
                category=GUICategory.CONTROL,
                conversion_notes="Java ScrollContainer maps to Bedrock scroll view",
                screen_type="generic",
                rarity=40,
            ),
            GUIPattern(
                java_component_class="ScrollPane",
                bedrock_control_type="scroll",
                category=GUICategory.CONTROL,
                conversion_notes="Java ScrollPane maps to Bedrock scroll view",
                screen_type="generic",
                rarity=40,
            ),
        ]

        # Add all patterns
        self.patterns.extend(screen_patterns)
        self.patterns.extend(container_patterns)
        self.patterns.extend(control_patterns)

    def search_by_java(self, java_class: str) -> List[GUIPattern]:
        """
        Search patterns by Java component class.

        Args:
            java_class: Java component class to search for

        Returns:
            List of matching GUIPattern objects
        """
        results = []
        java_class_lower = java_class.lower()

        for pattern in self.patterns:
            # Check for partial match
            if java_class_lower in pattern.java_component_class.lower():
                results.append(pattern)
            # Check for exact match
            elif java_class_lower == pattern.java_component_class.lower():
                # Prioritize exact matches
                results.insert(0, results.pop(results.index(pattern)))

        return results

    def get_by_category(self, category: GUICategory) -> List[GUIPattern]:
        """
        Get all patterns in a category.

        Args:
            category: GUICategory to filter by

        Returns:
            List of patterns in the category
        """
        return [p for p in self.patterns if p.category == category]

    def get_by_screen_type(self, screen_type: str) -> List[GUIPattern]:
        """
        Get all patterns for a specific screen type.

        Args:
            screen_type: Screen type to filter by

        Returns:
            List of patterns for the screen type
        """
        return [p for p in self.patterns if p.screen_type == screen_type]

    def add_pattern(self, pattern: GUIPattern) -> None:
        """
        Add a new pattern to the library.

        Args:
            pattern: GUIPattern to add
        """
        # Check for duplicate
        for existing in self.patterns:
            if existing.java_component_class == pattern.java_component_class:
                # Update existing
                existing.bedrock_control_type = pattern.bedrock_control_type
                existing.conversion_notes = pattern.conversion_notes
                return
        self.patterns.append(pattern)

    def get_pattern_by_java_class(self, java_class: str) -> Optional[GUIPattern]:
        """
        Get exact pattern by Java component class.

        Args:
            java_class: Java component class

        Returns:
            GUIPattern if found, None otherwise
        """
        for pattern in self.patterns:
            if pattern.java_component_class.lower() == java_class.lower():
                return pattern
        return None

    def get_stats(self) -> Dict[str, int]:
        """
        Get library statistics.

        Returns:
            Dictionary with pattern counts
        """
        stats = {
            "total": len(self.patterns),
            "by_category": {},
            "by_screen_type": {},
        }

        # Count by category
        for pattern in self.patterns:
            cat = pattern.category.value
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

            st = pattern.screen_type
            stats["by_screen_type"][st] = stats["by_screen_type"].get(st, 0) + 1

        return stats


# Global pattern instance for easy import
GUI_PATTERNS = GUIPatternLibrary()


def get_gui_pattern(java_class: str) -> Optional[GUIPattern]:
    """
    Get a GUI pattern by Java class.

    Args:
        java_class: Java component class

    Returns:
        GUIPattern if found, None otherwise
    """
    return GUI_PATTERNS.get_pattern_by_java_class(java_class)


def search_gui_patterns(query: str) -> List[GUIPattern]:
    """
    Search GUI patterns by Java class.

    Args:
        query: Search query

    Returns:
        List of matching patterns
    """
    return GUI_PATTERNS.search_by_java(query)


def get_patterns_by_category(category: GUICategory) -> List[GUIPattern]:
    """
    Get all patterns in a category.

    Args:
        category: Category to filter by

    Returns:
        List of patterns
    """
    return GUI_PATTERNS.get_by_category(category)


def get_patterns_by_screen_type(screen_type: str) -> List[GUIPattern]:
    """
    Get all patterns for a screen type.

    Args:
        screen_type: Screen type to filter by

    Returns:
        List of patterns
    """
    return GUI_PATTERNS.get_by_screen_type(screen_type)


def get_gui_stats() -> Dict[str, int]:
    """
    Get GUI pattern library statistics.

    Returns:
        Statistics dictionary
    """
    return GUI_PATTERNS.get_stats()
