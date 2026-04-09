"""
Unit tests for GUI and Menu Conversion.

Tests the conversion of Java screens, GUI components, containers, and
inventory layouts to Bedrock's UI JSON, forms, and inventory definitions.
"""

import pytest
import sys
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from converters.gui_converter import (
    GUIConverter,
    ContainerConverter,
    GUIComponentType,
)
from knowledge.patterns.gui_patterns import (
    GUIPatternLibrary,
    GUICategory,
    GUIPattern,
    get_gui_pattern,
)


class TestGUIComponentConversion:
    """Test cases for GUI component conversion."""

    def test_gui_converter_initialization(self):
        """Test GUIConverter initializes correctly."""
        converter = GUIConverter()
        assert converter is not None
        assert len(converter.component_map) > 0

    def test_convert_button(self):
        """Test button conversion."""
        converter = GUIConverter()
        java_button = {"text": "Click Me", "width": 200, "height": 40}
        result = converter.convert_button(java_button)

        assert "button" in result
        assert result["button"]["text"] == "Click Me"
        assert result["button"]["width"] == 200

    def test_convert_text_field(self):
        """Test text field conversion."""
        converter = GUIConverter()
        java_textfield = {"placeholder": "Enter text", "max_length": 64}
        result = converter.convert_text_field(java_textfield, "my_input")

        assert "input" in result
        assert result["input"]["placeholder"] == "Enter text"
        assert result["input"]["max_length"] == 64

    def test_convert_inventory(self):
        """Test inventory conversion."""
        converter = GUIConverter()
        java_container = {"slot_count": 54, "rows": 6, "type": "large"}
        result = converter.convert_inventory(java_container)

        assert "inventory" in result
        assert result["inventory"]["slot_count"] == 54
        assert result["inventory"]["rows"] == 6

    def test_extract_gui_components(self):
        """Test extracting GUI components from Java list."""
        converter = GUIConverter()
        java_components = [
            {"type": "GuiButton", "name": "btn1"},
            {"type": "GuiTextField", "name": "tf1"},
        ]
        result = converter.extract_gui_components(java_components)

        assert len(result) == 2
        assert result[0].component_type == GUIComponentType.BUTTON
        assert result[1].component_type == GUIComponentType.TEXT_FIELD

    def test_map_layout_manager(self):
        """Test layout manager conversion."""
        converter = GUIConverter()
        java_layout = {"type": "grid", "columns": 9}
        result = converter.map_layout_manager(java_layout)

        assert result["type"] == "grid"
        assert result["columns"] == 9


class TestFormGeneration:
    """Test cases for form generation."""

    def test_create_custom_form(self):
        """Test custom form creation."""
        converter = GUIConverter()
        buttons = [
            {"text": "Option 1", "id": 1},
            {"text": "Option 2", "id": 2},
        ]
        result = converter.create_custom_form("Test Form", buttons)

        assert "form" in result
        assert result["form"]["title"] == "Test Form"
        assert len(result["form"]["buttons"]) == 2

    def test_create_modal_form(self):
        """Test modal form creation."""
        converter = GUIConverter()
        result = converter.create_modal_form("Confirm", "Are you sure?", "OK", "Cancel")

        assert "modal_form" in result
        assert result["modal_form"]["title"] == "Confirm"
        assert result["modal_form"]["button1"] == "OK"
        assert result["modal_form"]["button2"] == "Cancel"

    def test_create_message_form(self):
        """Test message form creation."""
        converter = GUIConverter()
        result = converter.create_message_form("Success!", "OK")

        assert "message_form" in result
        assert result["message_form"]["title"] == "Success!"
        assert result["message_form"]["button"] == "OK"

    def test_form_with_empty_buttons(self):
        """Test custom form with empty buttons list."""
        converter = GUIConverter()
        result = converter.create_custom_form("Empty Form", [])

        assert "form" in result
        assert len(result["form"]["buttons"]) == 0

    def test_form_with_many_buttons(self):
        """Test custom form with many buttons."""
        converter = GUIConverter()
        buttons = [{"text": f"Option {i}", "id": i} for i in range(10)]
        result = converter.create_custom_form("Many Options", buttons)

        assert len(result["form"]["buttons"]) == 10


class TestContainerConversion:
    """Test cases for container conversion."""

    def test_container_converter_initialization(self):
        """Test ContainerConverter initializes correctly."""
        converter = ContainerConverter()
        assert converter is not None

    def test_convert_chest(self):
        """Test chest conversion."""
        converter = ContainerConverter()
        result = converter.convert_chest("chest")

        assert "minecraft:block_entity" in result
        assert "minecraft:container" in result["minecraft:block_entity"]["components"]

    def test_convert_large_chest(self):
        """Test large chest conversion."""
        converter = ContainerConverter()
        result = converter.convert_chest("large_chest")

        assert "minecraft:block_entity" in result

    def test_convert_furnace(self):
        """Test furnace conversion."""
        converter = ContainerConverter()
        result = converter.convert_furnace("furnace")

        assert "minecraft:block_entity" in result
        assert "minecraft:furnace" in result["minecraft:block_entity"]["components"]

    def test_convert_hopper(self):
        """Test hopper conversion."""
        converter = ContainerConverter()
        result = converter.convert_hopper("hopper")

        assert "minecraft:block_entity" in result
        assert "minecraft:hopper" in result["minecraft:block_entity"]["components"]


class TestInventoryLayout:
    """Test cases for inventory layout generation."""

    def test_generate_slot_layout_27(self):
        """Test generating 27-slot layout."""
        converter = ContainerConverter()
        slots = converter.generate_slot_layout(27)

        assert len(slots) == 27
        assert slots[0]["slot"] == 0
        assert slots[26]["slot"] == 26

    def test_generate_slot_layout_54(self):
        """Test generating 54-slot layout."""
        converter = ContainerConverter()
        slots = converter.generate_slot_layout(54)

        assert len(slots) == 54

    def test_generate_slot_layout_9(self):
        """Test generating 9-slot layout."""
        converter = ContainerConverter()
        slots = converter.generate_slot_layout(9)

        assert len(slots) == 9
        # All should be in first row
        assert all(s["y"] == 0 for s in slots)

    def test_convert_item_handler(self):
        """Test item handler conversion."""
        converter = ContainerConverter()
        java_handler = {
            "slot_count": 27,
            "items": [
                {"slot": 0, "id": "minecraft:diamond", "count": 64},
                {"slot": 1, "id": "minecraft:iron_ingot", "count": 32},
            ],
        }
        result = converter.convert_item_handler(java_handler)

        assert result["size"] == 27
        assert len(result["items"]) == 2


class TestGUIPatternLibrary:
    """Test cases for GUIPatternLibrary."""

    def test_pattern_library_initialization(self):
        """Test pattern library loads with patterns."""
        lib = GUIPatternLibrary()
        assert len(lib.patterns) >= 25, "Should have at least 25 patterns"

    def test_pattern_search(self):
        """Test searching patterns by Java class."""
        lib = GUIPatternLibrary()
        results = lib.search_by_java("ContainerScreen")
        assert len(results) > 0

    def test_category_filtering(self):
        """Test filtering patterns by category."""
        lib = GUIPatternLibrary()
        screen_patterns = lib.get_by_category(GUICategory.SCREEN)
        assert len(screen_patterns) > 0
        assert all(p.category == GUICategory.SCREEN for p in screen_patterns)

    def test_screen_type_filtering(self):
        """Test filtering patterns by screen type."""
        lib = GUIPatternLibrary()
        inventory_patterns = lib.get_by_screen_type("inventory")
        assert len(inventory_patterns) > 0

    def test_add_pattern(self):
        """Test adding new patterns."""
        lib = GUIPatternLibrary()
        new_pattern = GUIPattern(
            java_component_class="test.custom",
            bedrock_control_type="custom",
            category=GUICategory.CUSTOM,
            conversion_notes="Custom test pattern",
        )
        lib.add_pattern(new_pattern)
        found = lib.get_pattern_by_java_class("test.custom")
        assert found is not None

    def test_stats(self):
        """Test getting library statistics."""
        lib = GUIPatternLibrary()
        stats = lib.get_stats()
        assert stats["total"] >= 25
        assert "by_category" in stats
        assert "screen" in stats["by_category"]


class TestIntegration:
    """Integration tests for GUI conversion."""

    def test_full_screen_conversion(self):
        """Test complete screen conversion."""
        converter = GUIConverter()
        java_screen = {
            "name": "test_screen",
            "type": "ContainerScreen",
            "components": [
                {"type": "GuiButton", "name": "btn1", "text": "Click"},
                {"type": "GuiTextField", "name": "tf1"},
            ],
        }
        result = converter.convert_screen(java_screen)
        assert result is not None

    def test_container_and_pattern_integration(self):
        """Test container conversion with pattern lookup."""
        # Get pattern from library
        pattern = get_gui_pattern("ContainerScreen")
        assert pattern is not None

        # Use container converter
        container_converter = ContainerConverter()
        result = container_converter.convert_chest("chest")
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
