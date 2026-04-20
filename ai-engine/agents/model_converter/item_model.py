"""
Item model special handling module.
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def _handle_item_model_special_cases(
    java_model: Dict,
    java_parent: str,
    texture_layers: Dict,
    all_bones: List[Dict],
    geo_description: Dict,
) -> Tuple[bool, List[str]]:
    """
    Handle special item model types like generated, builtin/entity, handheld.

    Args:
        java_model: The Java model JSON data
        java_parent: The parent model path
        texture_layers: The textures dict from the model
        all_bones: List of bones to append to
        geo_description: The geometry description dict to modify

    Returns:
        Tuple of (handled, warnings)
    """
    warnings = []
    processed = False

    if java_parent in ["item/generated", "item/builtin/entity", "item/handheld"]:
        processed = True
        if java_parent in ["item/generated", "item/builtin/entity"]:
            warnings.append(f"Handling as '{java_parent}'. Display transformations not applied.")
        elif java_parent == "item/handheld":
            warnings.append("Handling as 'item/handheld'. Display transformations not applied.")

        layer_count = 0
        for i in range(5):
            layer_texture_key = f"layer{i}"
            if layer_texture_key in texture_layers:
                z_offset = -0.05 - (0.1 * i)

                layer_bone = {
                    "name": layer_texture_key,
                    "pivot": [0.0, 0.0, 0.0],
                    "cubes": [
                        {
                            "origin": [-8.0, -8.0, z_offset],
                            "size": [16.0, 16.0, 0.1],
                            "uv": [0, 0],
                        }
                    ],
                }
                all_bones.append(layer_bone)
                layer_count += 1

        if layer_count == 0 and "particle" in texture_layers:
            warnings.append("No layer0/layer1 found, using 'particle' texture for a fallback quad.")
            particle_bone = {
                "name": "particle_quad",
                "pivot": [0.0, 0.0, 0.0],
                "cubes": [{"origin": [-8.0, -8.0, -0.05], "size": [16.0, 16.0, 0.1], "uv": [0, 0]}],
            }
            all_bones.append(particle_bone)
            layer_count = 1

        if layer_count > 0:
            geo_description["visible_bounds_width"] = 1.0
            geo_description["visible_bounds_height"] = 1.0
            geo_description["visible_bounds_offset"] = [0.0, 0.0, 0.0]
        else:
            warnings.append(
                f"Item model with parent '{java_parent}' defined no recognized texture layers."
            )
            geo_description["visible_bounds_width"] = 0.1
            geo_description["visible_bounds_height"] = 0.1
            geo_description["visible_bounds_offset"] = [0.0, 0.0, 0.0]

    return processed, warnings
