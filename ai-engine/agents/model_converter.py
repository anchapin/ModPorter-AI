"""
Model converter module - handles all model-related conversion logic.
This module is extracted from asset_converter.py for better organization.

DEPRECATED: Use agents.model_converter package instead.
This module is kept for backwards compatibility.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from agents.model_converter import (
    parse_blockstate,
    resolve_parent_model,
    get_model_elements_with_inheritance,
    convert_blockstate,
    extract_models_from_jar,
)

from agents.model_converter.geometry import (
    _convert_single_model,
    _analyze_model,
    _generate_model_structure,
)
from agents.model_converter.blockstate import _resolve_parent_path
from agents.model_converter.inheritance import _resolve_parent_path as resolve_path

__all__ = [
    "convert_single_model",
    "analyze_model",
    "generate_model_structure",
    "extract_models_from_jar",
    "parse_blockstate",
    "resolve_parent_model",
    "convert_blockstate",
    "get_model_elements_with_inheritance",
    "_convert_single_model",
    "_analyze_model",
    "_generate_model_structure",
    "_resolve_parent_path",
]

convert_single_model = _convert_single_model
analyze_model = _analyze_model
generate_model_structure = _generate_model_structure
