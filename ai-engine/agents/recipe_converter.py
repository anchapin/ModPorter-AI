"""
Recipe converter module - handles all recipe-related conversion logic.
This module is extracted from recipe_converter.py for better organization.

DEPRECATED: Use agents.recipe package instead.
This module is kept for backwards compatibility.
"""

import json
import logging
from typing import Dict, List

from crewai.tools import tool

from agents.recipe import (
    FORGE_TAG_MAPPINGS,
    JAVA_TO_BEDROCK_ITEM_MAP,
    CUSTOM_RECIPE_TYPES,
    RecipeConverterAgent,
)

logger = logging.getLogger(__name__)

__all__ = [
    "RecipeConverterAgent",
    "FORGE_TAG_MAPPINGS",
    "JAVA_TO_BEDROCK_ITEM_MAP",
    "CUSTOM_RECIPE_TYPES",
]