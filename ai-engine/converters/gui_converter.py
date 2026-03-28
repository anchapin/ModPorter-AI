"""
GUI Converter for converting Java GUI, menus, and screens to Bedrock format.

Converts Java screen classes, GUI components, containers, and inventory layouts
to Bedrock's UI JSON files, custom forms, and inventory definitions.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class GUIComponentType(Enum):
    """Bedrock GUI component types."""

    BUTTON = "button"
    TEXT_FIELD = "input"
    LABEL = "label"
    IMAGE = "image"
    SLIDER = "slider"
    CHECKBOX = "checkbox"
    DROPDOWN = "dropdown"
    INVENTORY = "inventory"
    SCROLL = "scroll"
    PANEL = "panel"
    CUSTOM = "custom"


class ScreenType(Enum):
    """Java screen types."""

    SCREEN = "screen"
    CONTAINER_SCREEN = "container_screen"
    INVENTORY_SCREEN = "inventory_screen"
    CRAFTING_SCREEN = "crafting_screen"
    CHAT_SCREEN = "chat_screen"
    OPTIONS_SCREEN = "options_screen"
    MENU = "menu"
    CUSTOM = "custom"


class ContainerType(Enum):
    """Java container types."""

    CHEST = "chest"
    LARGE_CHEST = "large_chest"
    FURNACE = "furnace"
    HOPPER = "hopper"
    DISPENSER = "dispenser"
    ENCHANTMENT = "enchantment"
    ANVIL = "anvil"
    BEACON = "beacon"
    BREWING_STAND = "brewing_stand"
    CUSTOM = "custom"


@dataclass
class GUIButton:
    """Represents a GUI button."""

    text: str
    width: int = 200
    height: int = 40
    enabled: bool = True
    visible: bool = True


@dataclass
class GUITextField:
    """Represents a GUI text field."""

    placeholder: str = ""
    max_length: int = 32
    width: int = 200
    height: int = 30


@dataclass
class GUIComponent:
    """Represents a GUI component."""

    component_type: GUIComponentType
    name: str
    x: int = 0
    y: int = 0
    width: int = 100
    height: int = 100
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreenDefinition:
    """Represents a screen definition."""

    name: str
    screen_type: ScreenType
    components: List[GUIComponent] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InventorySlot:
    """Represents an inventory slot."""

    index: int
    x: int
    y: int
    width: int = 18
    height: int = 18


class GUIConverter:
    """
    Converter for Java GUI screens and components to Bedrock format.

    Handles screen conversion, component mapping, event handlers, and
    form generation for Bedrock UI.
    """

    def __init__(self):
        # Base UI file template
        self.ui_template = {"format_version": "1.19.0"}

        # Java to Bedrock component type mapping
        self.component_map = {
            "GuiButton": GUIComponentType.BUTTON,
            "Button": GUIComponentType.BUTTON,
            "GuiTextField": GUIComponentType.TEXT_FIELD,
            "TextField": GUIComponentType.TEXT_FIELD,
            "TextFieldWidget": GUIComponentType.TEXT_FIELD,
            "GuiLabel": GUIComponentType.LABEL,
            "Label": GUIComponentType.LABEL,
            "GuiImage": GUIComponentType.IMAGE,
            "Image": GUIComponentType.IMAGE,
            "GuiSlider": GUIComponentType.SLIDER,
            "Slider": GUIComponentType.SLIDER,
            "SliderWidget": GUIComponentType.SLIDER,
            "GuiCheckbox": GUIComponentType.CHECKBOX,
            "Checkbox": GUIComponentType.CHECKBOX,
            "CheckboxWidget": GUIComponentType.CHECKBOX,
            "GuiDropdown": GUIComponentType.DROPDOWN,
            "Dropdown": GUIComponentType.DROPDOWN,
            "DropdownWidget": GUIComponentType.DROPDOWN,
            "ContainerScreen": GUIComponentType.INVENTORY,
            "InventoryScreen": GUIComponentType.INVENTORY,
            "ScrollContainer": GUIComponentType.SCROLL,
            "ScrollPane": GUIComponentType.SCROLL,
        }

        # Java screen type mapping
        self.screen_type_map = {
            "Screen": ScreenType.SCREEN,
            "ContainerScreen": ScreenType.CONTAINER_SCREEN,
            "InventoryScreen": ScreenType.INVENTORY_SCREEN,
            "CraftingScreen": ScreenType.CRAFTING_SCREEN,
            "ChatScreen": ScreenType.CHAT_SCREEN,
            "OptionsScreen": ScreenType.OPTIONS_SCREEN,
            "MainMenuScreen": ScreenType.MENU,
            "GuiModMenu": ScreenType.MENU,
        }

        # Default button styles
        self.button_styles = {
            "default": {
                "background": "button_background",
                "text_color": "white",
                "hover_color": "#E0E0E0",
            },
            "primary": {
                "background": "button_primary_background",
                "text_color": "white",
                "hover_color": "#4A90D9",
            },
            "danger": {
                "background": "button_danger_background",
                "text_color": "white",
                "hover_color": "#D94A4A",
            },
        }

    def convert_screen(self, java_screen: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Java screen definition to Bedrock UI JSON.

        Args:
            java_screen: Java screen dictionary

        Returns:
            Bedrock UI screen definition
        """
        screen_name = java_screen.get("name", "custom_screen")
        screen_type = self._get_screen_type(java_screen.get("type", "Screen"))

        # Extract GUI components
        components = self.extract_gui_components(java_screen.get("components", []))

        # Build screen definition
        screen_def = ScreenDefinition(
            name=screen_name,
            screen_type=screen_type,
            components=components,
            properties=java_screen.get("properties", {}),
        )

        return self._build_screen_json(screen_def)

    def convert_button(self, java_button: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Java button to Bedrock button control.

        Args:
            java_button: Java button dictionary

        Returns:
            Bedrock button control definition
        """
        button = GUIButton(
            text=java_button.get("text", "Button"),
            width=java_button.get("width", 200),
            height=java_button.get("height", 40),
            enabled=java_button.get("enabled", True),
            visible=java_button.get("visible", True),
        )

        button_type = java_button.get("button_type", "default")
        style = self.button_styles.get(button_type, self.button_styles["default"])

        return {
            "button": {
                "text": button.text,
                "width": button.width,
                "height": button.height,
                "enabled": button.enabled,
                "visible": button.visible,
                "style": style,
            }
        }

    def convert_text_field(
        self, java_textfield: Dict[str, Any], name: str = "text_field"
    ) -> Dict[str, Any]:
        """
        Convert a Java text field to Bedrock input control.

        Args:
            java_textfield: Java text field dictionary
            name: Control name

        Returns:
            Bedrock input control definition
        """
        textfield = GUITextField(
            placeholder=java_textfield.get("placeholder", ""),
            max_length=java_textfield.get("max_length", 32),
            width=java_textfield.get("width", 200),
            height=java_textfield.get("height", 30),
        )

        return {
            "input": {
                "name": name,
                "placeholder": textfield.placeholder,
                "max_length": textfield.max_length,
                "width": textfield.width,
                "height": textfield.height,
            }
        }

    def convert_inventory(self, java_container: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Java container/inventory to Bedrock inventory definition.

        Args:
            java_container: Java container dictionary

        Returns:
            Bedrock inventory definition
        """
        slot_count = java_container.get("slot_count", 27)
        rows = java_container.get("rows", 3)

        return {
            "inventory": {
                "slot_count": slot_count,
                "rows": rows,
                "container_type": java_container.get("type", "generic"),
            }
        }

    def extract_gui_components(self, java_components: List[Dict]) -> List[GUIComponent]:
        """
        Extract GUI components from Java component list.

        Args:
            java_components: List of Java component dictionaries

        Returns:
            List of GUIComponent objects
        """
        components = []

        for comp in java_components:
            comp_type_str = comp.get("type", "unknown")
            component_type = self.component_map.get(comp_type_str, GUIComponentType.CUSTOM)

            component = GUIComponent(
                component_type=component_type,
                name=comp.get("name", f"component_{len(components)}"),
                x=comp.get("x", 0),
                y=comp.get("y", 0),
                width=comp.get("width", 100),
                height=comp.get("height", 100),
                properties=comp.get("properties", {}),
            )
            components.append(component)

        return components

    def map_layout_manager(self, java_layout: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java layout manager to Bedrock layout JSON.

        Args:
            java_layout: Java layout dictionary

        Returns:
            Bedrock layout definition
        """
        layout_type = java_layout.get("type", "absolute")

        if layout_type == "grid":
            return {
                "type": "grid",
                "columns": java_layout.get("columns", 9),
                "spacing": java_layout.get("spacing", 2),
            }
        elif layout_type == "vertical":
            return {
                "type": "vertical",
                "spacing": java_layout.get("spacing", 4),
                "alignment": java_layout.get("alignment", "center"),
            }
        elif layout_type == "horizontal":
            return {
                "type": "horizontal",
                "spacing": java_layout.get("spacing", 4),
                "alignment": java_layout.get("alignment", "center"),
            }
        else:
            return {"type": "absolute"}

    def convert_event_handlers(self, java_screen: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """
        Convert Java event handlers to Bedrock button actions.

        Args:
            java_screen: Java screen dictionary

        Returns:
            Dictionary of event handler mappings
        """
        handlers = {}

        # Map common Java events to Bedrock actions
        event_map = {
            "on_click": "click",
            "on_press": "click",
            "on_release": "release",
            "on_hover": "hover",
            "on_changed": "change",
            "on_focus_lost": "blur",
        }

        java_handlers = java_screen.get("event_handlers", {})

        for java_event, bedrock_action in event_map.items():
            if java_event in java_handlers:
                handlers[bedrock_action] = java_handlers[java_event]

        return handlers

    def create_custom_form(self, title: str, buttons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a Bedrock custom form JSON.

        Args:
            title: Form title
            buttons: List of button definitions

        Returns:
            Custom form JSON
        """
        form_buttons = []

        for i, button in enumerate(buttons):
            form_buttons.append(
                {
                    "text": button.get("text", f"Button {i + 1}"),
                    "id": button.get("id", i),
                }
            )

        return {
            "form": {
                "title": title,
                "buttons": form_buttons,
            }
        }

    def create_modal_form(
        self, title: str, content: str, button1_text: str, button2_text: str
    ) -> Dict[str, Any]:
        """
        Create a Bedrock modal form JSON.

        Args:
            title: Form title
            content: Modal content text
            button1_text: First button text (e.g., "OK")
            button2_text: Second button text (e.g., "Cancel")

        Returns:
            Modal form JSON
        """
        return {
            "modal_form": {
                "title": title,
                "content": content,
                "button1": button1_text,
                "button2": button2_text,
            }
        }

    def create_message_form(self, title: str, button_text: str = "OK") -> Dict[str, Any]:
        """
        Create a Bedrock message form JSON.

        Args:
            title: Form title
            button_text: Button text

        Returns:
            Message form JSON
        """
        return {
            "message_form": {
                "title": title,
                "button": button_text,
            }
        }

    def _get_screen_type(self, java_type: str) -> ScreenType:
        """Map Java screen type to ScreenType enum."""
        return self.screen_type_map.get(java_type, ScreenType.CUSTOM)

    def _build_screen_json(self, screen_def: ScreenDefinition) -> Dict[str, Any]:
        """Build the full screen JSON definition."""
        controls = {}

        for component in screen_def.components:
            control_name = component.name
            control_def = self._build_control(component)
            controls[control_name] = control_def

        return {
            "format_version": "1.19.0",
            "ui_defs": [
                {
                    "screen": {
                        "namespace": "gui",
                        "name": screen_def.name,
                        "screen_type": screen_def.screen_type.value,
                        "controls": controls,
                        "properties": screen_def.properties,
                    }
                }
            ],
        }

    def _build_control(self, component: GUIComponent) -> Dict[str, Any]:
        """Build a single control definition."""
        base_control = {
            "type": component.component_type.value,
            "x": component.x,
            "y": component.y,
            "width": component.width,
            "height": component.height,
        }

        # Add component-specific properties
        if component.component_type == GUIComponentType.BUTTON:
            base_control.update(
                {
                    "text": component.properties.get("text", "Button"),
                    "enabled": component.properties.get("enabled", True),
                    "visible": component.properties.get("visible", True),
                }
            )
        elif component.component_type == GUIComponentType.TEXT_FIELD:
            base_control.update(
                {
                    "placeholder": component.properties.get("placeholder", ""),
                    "max_length": component.properties.get("max_length", 32),
                }
            )
        elif component.component_type == GUIComponentType.LABEL:
            base_control.update(
                {
                    "text": component.properties.get("text", "Label"),
                    "color": component.properties.get("color", "white"),
                }
            )
        elif component.component_type == GUIComponentType.IMAGE:
            base_control.update(
                {
                    "texture": component.properties.get("texture", ""),
                    "tiled": component.properties.get("tiled", False),
                }
            )

        # Add any additional properties
        for key, value in component.properties.items():
            if key not in base_control:
                base_control[key] = value

        return base_control


class ContainerConverter:
    """
    Converter for Java containers and tile entities to Bedrock format.

    Handles chest, furnace, hopper, and other container conversions
    to Bedrock block entities and inventory definitions.
    """

    def __init__(self):
        # Container type mappings
        self.container_type_map = {
            "chest": ContainerType.CHEST,
            "large_chest": ContainerType.LARGE_CHEST,
            "big_chest": ContainerType.LARGE_CHEST,
            "double_chest": ContainerType.LARGE_CHEST,
            "furnace": ContainerType.FURNACE,
            "blast_furnace": ContainerType.FURNACE,
            "smoker": ContainerType.FURNACE,
            "hopper": ContainerType.HOPPER,
            "dispenser": ContainerType.DISPENSER,
            "dropper": ContainerType.DISPENSER,
            "enchantment_table": ContainerType.ENCHANTMENT,
            "anvil": ContainerType.ANVIL,
            "beacon": ContainerType.BEACON,
            "brewing_stand": ContainerType.BREWING_STAND,
        }

        # Slot layouts for containers
        self.slot_layouts = {
            ContainerType.CHEST: {"rows": 3, "columns": 9, "total": 27},
            ContainerType.LARGE_CHEST: {"rows": 6, "columns": 9, "total": 54},
            ContainerType.FURNACE: {"rows": 1, "columns": 3, "total": 3},
            ContainerType.HOPPER: {"rows": 1, "columns": 5, "total": 5},
            ContainerType.DISPENSER: {"rows": 1, "columns": 9, "total": 9},
            ContainerType.ENCHANTMENT: {"rows": 1, "columns": 1, "total": 1},
            ContainerType.ANVIL: {"rows": 1, "columns": 3, "total": 3},
            ContainerType.BEACON: {"rows": 1, "columns": 1, "total": 1},
            ContainerType.BREWING_STAND: {"rows": 1, "columns": 5, "total": 5},
        }

    def convert_chest(self, java_chest: str) -> Dict[str, Any]:
        """
        Convert a Java chest to Bedrock chest block entity.

        Args:
            java_chest: Java chest type (e.g., "chest", "large_chest")

        Returns:
            Bedrock chest block entity definition
        """
        chest_type = self._get_container_type(java_chest, ContainerType.CHEST)
        is_large = chest_type == ContainerType.LARGE_CHEST

        return {
            "format_version": "1.19.0",
            "minecraft:block_entity": {
                "description": {
                    "identifier": f"minecraft:chest{'|large' if is_large else ''}",
                },
                "components": {
                    "minecraft:container": self._get_container_components(chest_type, is_large),
                },
            },
        }

    def convert_furnace(self, java_furnace: str) -> Dict[str, Any]:
        """
        Convert a Java furnace to Bedrock furnace definition.

        Args:
            java_furnace: Java furnace type

        Returns:
            Bedrock furnace block entity definition
        """
        furnace_type = self._get_container_type(java_furnace, ContainerType.FURNACE)
        slot_layout = self.slot_layouts[ContainerType.FURNACE]

        return {
            "format_version": "1.19.0",
            "minecraft:block_entity": {
                "description": {
                    "identifier": "minecraft:furnace",
                },
                "components": {
                    "minecraft:furnace": {
                        "input_slots": slot_layout["total"] - 1,
                        "fuel_slots": 1,
                        "output_slots": 1,
                    },
                    "minecraft:container": {
                        "size": slot_layout["total"],
                        "slot_list": self.generate_slot_layout(slot_layout["total"]),
                    },
                },
            },
        }

    def convert_hopper(self, java_hopper: str) -> Dict[str, Any]:
        """
        Convert a Java hopper to Bedrock hopper definition.

        Args:
            java_hopper: Java hopper type

        Returns:
            Bedrock hopper block entity definition
        """
        hopper_type = self._get_container_type(java_hopper, ContainerType.HOPPER)
        slot_layout = self.slot_layouts[ContainerType.HOPPER]

        return {
            "format_version": "1.19.0",
            "minecraft:block_entity": {
                "description": {
                    "identifier": "minecraft:hopper",
                },
                "components": {
                    "minecraft:hopper": {
                        "transfer_cooldown": 8,
                        "pull_delay": 8,
                    },
                    "minecraft:container": {
                        "size": slot_layout["total"],
                        "slot_list": self.generate_slot_layout(slot_layout["total"]),
                    },
                },
            },
        }

    def generate_slot_layout(self, slot_count: int) -> List[Dict[str, Any]]:
        """
        Generate slot layout for inventory grid.

        Args:
            slot_count: Total number of slots

        Returns:
            List of slot definitions with x, y coordinates
        """
        slots = []
        columns = 9
        slot_width = 18
        slot_height = 18
        spacing = 2
        start_x = 0
        start_y = 0

        for i in range(slot_count):
            row = i // columns
            col = i % columns

            slots.append(
                {
                    "slot": i,
                    "x": start_x + col * (slot_width + spacing),
                    "y": start_y + row * (slot_height + spacing),
                    "width": slot_width,
                    "height": slot_height,
                }
            )

        return slots

    def convert_item_handler(self, java_item_handler: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java item handler to Bedrock item stack definitions.

        Args:
            java_item_handler: Java item handler dictionary

        Returns:
            Bedrock item stack definitions
        """
        items = java_item_handler.get("items", [])
        slot_count = java_item_handler.get("slot_count", 27)

        result = {
            "size": slot_count,
            "items": [],
        }

        for item in items:
            result["items"].append(
                {
                    "slot": item.get("slot", 0),
                    "item": item.get("id", "minecraft:air"),
                    "count": item.get("count", 1),
                    "data": item.get("damage", 0),
                }
            )

        return result

    def convert_on_open(self, java_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java onOpen event to Bedrock on_open event.

        Args:
            java_event: Java event dictionary

        Returns:
            Bedrock event definition
        """
        return {
            "on_open": {
                "sound": java_event.get("sound", "random.chestopen"),
                "particle": java_event.get("particle", ""),
                "condition": java_event.get("condition", ""),
            }
        }

    def convert_on_close(self, java_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java onClose event to Bedrock on_close event.

        Args:
            java_event: Java event dictionary

        Returns:
            Bedrock event definition
        """
        return {
            "on_close": {
                "sound": java_event.get("sound", "random.chestclosed"),
                "particle": java_event.get("particle", ""),
                "condition": java_event.get("condition", ""),
            }
        }

    def _get_container_type(self, java_type: str, default: ContainerType) -> ContainerType:
        """Map Java container type to ContainerType enum."""
        return self.container_type_map.get(java_type.lower(), default)

    def _get_container_components(
        self, container_type: ContainerType, is_large: bool = False
    ) -> Dict[str, Any]:
        """Get container components for a container type."""
        slot_layout = self.slot_layouts.get(container_type, {"rows": 3, "columns": 9, "total": 27})

        components = {
            "size": slot_layout["total"],
            "slot_list": self.generate_slot_layout(slot_layout["total"]),
        }

        if is_large:
            components["type"] = "large"

        return components
