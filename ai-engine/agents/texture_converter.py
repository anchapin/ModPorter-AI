"""
Texture converter module - handles all texture-related conversion logic.
This module is extracted from asset_converter.py for better organization.

DEPRECATED: Use agents.texture_converter package instead.
This module is kept for backwards compatibility.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

logger = logging.getLogger(__name__)

from agents.texture_converter import (
    detect_texture_atlas,
    extract_texture_atlas,
    parse_atlas_metadata,
    convert_atlas_to_bedrock,
    convert_java_texture_path,
    validate_texture,
    validate_textures_batch,
    generate_fallback_texture,
    generate_fallback_for_jar,
    extract_textures_from_jar,
    extract_texture_atlas_from_jar,
    convert_jar_textures_to_bedrock,
)

from agents.texture_converter.atlas import extract_texture_atlas as _extract_texture_atlas
from agents.texture_converter.conversion import (
    _convert_single_texture,
    _generate_texture_pack_structure,
    convert_textures,
    _get_recommended_resolution,
    _generate_conversion_recommendations,
    _assess_conversion_complexity,
)
from agents.texture_converter.path_mapper import (
    _map_java_texture_to_bedrock,
    _map_texture_type,
    _map_bedrock_texture_to_java,
    _map_bedrock_type_to_java,
)
from agents.texture_converter.fallback import _generate_fallback_texture
from agents.texture_converter.jar_extractor import (
    _get_mod_ids_from_jar,
    _extract_textures_from_alt_locations,
)

__all__ = [
    "convert_single_texture",
    "detect_texture_atlas",
    "extract_texture_atlas",
    "parse_atlas_metadata",
    "convert_atlas_to_bedrock",
    "convert_java_texture_path",
    "validate_texture",
    "validate_textures_batch",
    "generate_fallback_texture",
    "generate_fallback_for_jar",
    "extract_textures_from_jar",
    "extract_texture_atlas_from_jar",
    "convert_jar_textures_to_bedrock",
    "_convert_single_texture",
    "_generate_texture_pack_structure",
    "_map_java_texture_to_bedrock",
    "_map_texture_type",
    "_map_bedrock_texture_to_java",
    "_map_bedrock_type_to_java",
    "_generate_fallback_texture",
    "_get_recommended_resolution",
    "_generate_conversion_recommendations",
    "_assess_conversion_complexity",
    "_get_mod_ids_from_jar",
    "_extract_textures_from_alt_locations",
]

convert_single_texture = _convert_single_texture
