"""
Model converter package - handles all model-related conversion logic.
Modularized from model_converter.py for better organization.

Public API re-exports from submodules to maintain backwards compatibility.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from agents.model_converter.geometry import (
    _convert_single_model,
    _analyze_model,
    _generate_model_structure,
)
from agents.model_converter.blockstate import (
    parse_blockstate,
    convert_blockstate,
)
from agents.model_converter.item_model import (
    _handle_item_model_special_cases,
)
from agents.model_converter.inheritance import (
    resolve_parent_model,
    get_model_elements_with_inheritance,
    _resolve_parent_path,
)
from agents.model_converter.jar_extractor import (
    extract_models_from_jar,
)

__all__ = [
    "convert_single_model",
    "analyze_model",
    "generate_model_structure",
    "extract_models_from_jar",
    "parse_blockstate",
    "resolve_parent_model",
    "convert_blockstate",
    "get_model_elements_with_inheritance",
]

convert_single_model = _convert_single_model
analyze_model = _analyze_model
generate_model_structure = _generate_model_structure
