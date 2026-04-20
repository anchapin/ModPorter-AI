"""
Bedrock template data for block, item, entity, and recipe generation.

Loads templates from ai-engine/data/bedrock_block_templates.json.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

try:
    import tree_sitter_java as ts_java
    from tree_sitter import Language, Parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    ts_java = None
    Parser = None


def _get_data_path() -> Path:
    current_dir = Path(__file__).parent
    return current_dir.parent.parent / "data" / "bedrock_block_templates.json"


def load_templates() -> Dict[str, Any]:
    """Load all templates from the JSON data file."""
    data_path = _get_data_path()
    with open(data_path, "r") as f:
        return json.load(f)


TEMPLATE_DATA = load_templates()

BEDROCK_BLOCK_TEMPLATES = TEMPLATE_DATA["block_templates"]
BEDROCK_ITEM_TEMPLATES = TEMPLATE_DATA["item_templates"]
BEDROCK_ENTITY_TEMPLATES = TEMPLATE_DATA["entity_templates"]
BEDROCK_RECIPE_TEMPLATES = TEMPLATE_DATA["recipe_templates"]
JAVA_TO_BEDROCK_ITEM_PROPERTIES = TEMPLATE_DATA["java_to_bedrock_item_properties"]
JAVA_ITEM_METHOD_MAPPINGS = TEMPLATE_DATA["java_item_method_mappings"]
JAVA_TO_BEDROCK_ENTITY_PROPERTIES = TEMPLATE_DATA["java_to_bedrock_entity_properties"]


class BedrockTemplateLoader:
    """Loads and provides access to Bedrock template data."""

    def __init__(self):
        self._templates = TEMPLATE_DATA
        self._ts_parser = None

    @property
    def block_templates(self) -> Dict[str, Any]:
        return self._templates["block_templates"]

    @property
    def item_templates(self) -> Dict[str, Any]:
        return self._templates["item_templates"]

    @property
    def entity_templates(self) -> Dict[str, Any]:
        return self._templates["entity_templates"]

    @property
    def recipe_templates(self) -> Dict[str, Any]:
        return self._templates["recipe_templates"]

    @property
    def java_to_bedrock_item_properties(self) -> Dict[str, Any]:
        return self._templates["java_to_bedrock_item_properties"]

    @property
    def java_item_method_mappings(self) -> Dict[str, str]:
        return self._templates["java_item_method_mappings"]

    @property
    def java_to_bedrock_entity_properties(self) -> Dict[str, Any]:
        return self._templates["java_to_bedrock_entity_properties"]

    def get_block_template(self, template_type: str) -> Dict[str, Any]:
        """Get a block template by type."""
        return self.block_templates.get(template_type, self.block_templates["basic"])

    def get_item_template(self, template_type: str) -> Dict[str, Any]:
        """Get an item template by type."""
        return self.item_templates.get(template_type, self.item_templates["basic"])

    def get_entity_template(self, template_type: str) -> Dict[str, Any]:
        """Get an entity template by type."""
        return self.entity_templates.get(template_type, self.entity_templates.get("hostile_mob"))

    def get_recipe_template(self, template_type: str) -> Dict[str, Any]:
        """Get a recipe template by type."""
        return self.recipe_templates.get(template_type, self.recipe_templates.get("shaped"))


__all__ = [
    "BEDROCK_BLOCK_TEMPLATES",
    "BEDROCK_ITEM_TEMPLATES",
    "BEDROCK_ENTITY_TEMPLATES",
    "BEDROCK_RECIPE_TEMPLATES",
    "JAVA_TO_BEDROCK_ITEM_PROPERTIES",
    "JAVA_ITEM_METHOD_MAPPINGS",
    "JAVA_TO_BEDROCK_ENTITY_PROPERTIES",
    "TEMPLATE_DATA",
    "BedrockTemplateLoader",
    "TREE_SITTER_AVAILABLE",
]
