"""
Model converter module - handles all model-related conversion logic.
This module is extracted from asset_converter.py for better organization.
"""

import logging
import json
from pathlib import Path
from typing import Dict, List

# Import utilities
try:
    from . import converter_utils
except ImportError:
    import converter_utils

logger = logging.getLogger(__name__)

__all__ = ["convert_single_model", "analyze_model", "generate_model_structure"]


# ============================================================================
# _convert_single_model
# ============================================================================


def _convert_single_model(agent, model_path: str, metadata: Dict, entity_type: str) -> Dict:
    warnings = []
    try:
        model_p = Path(model_path)
        if not model_p.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        with open(model_p, "r") as f:
            java_model = json.load(f)

        # Basic Bedrock geo.json structure
        bedrock_identifier = f"geometry.{entity_type}.{model_p.stem}"
        # For texture_width/height, try to get from metadata if available, else default
        # This metadata would ideally be populated by texture analysis of related textures
        texture_width = metadata.get("texture_width", 16)
        texture_height = metadata.get("texture_height", 16)

        bedrock_geo = {
            "format_version": "1.12.0",
            "minecraft:geometry": [
                {
                    "description": {
                        "identifier": bedrock_identifier,
                        "texture_width": texture_width,
                        "texture_height": texture_height,
                        # Visible bounds can be roughly estimated later if needed
                        "visible_bounds_width": 2,
                        "visible_bounds_height": 2,
                        "visible_bounds_offset": [0, 0.5, 0],
                    },
                    "bones": [],
                }
            ],
        }

        # Ensure we are modifying the correct dictionary part
        geo_main_part = bedrock_geo["minecraft:geometry"][0]
        geo_description = geo_main_part["description"]
        all_bones = geo_main_part["bones"]

        java_parent = java_model.get("parent")
        java_elements = java_model.get("elements", [])
        processed_as_item_specific_type = False

        if entity_type == "item" and java_parent in [
            "item/generated",
            "item/builtin/entity",
            "item/handheld",
        ]:
            processed_as_item_specific_type = True
            if java_parent in ["item/generated", "item/builtin/entity"]:
                warnings.append(
                    f"Handling as '{java_parent}'. Display transformations not applied."
                )
            elif java_parent == "item/handheld":
                warnings.append("Handling as 'item/handheld'. Display transformations not applied.")

            texture_layers = java_model.get("textures", {})
            layer_count = 0
            for i in range(5):  # Check for layer0 up to layer4
                layer_texture_key = f"layer{i}"
                if layer_texture_key in texture_layers:
                    # In a more advanced system, here you would resolve texture_layers[layer_texture_key]
                    # to get specific texture dimensions for texture_width/height.
                    # For now, we use the global/default texture_width/height.

                    z_offset = -0.05 - (
                        0.1 * i
                    )  # Each layer slightly behind the previous, very thin

                    layer_bone = {
                        "name": layer_texture_key,
                        "pivot": [0.0, 0.0, 0.0],
                        "cubes": [
                            {
                                "origin": [-8.0, -8.0, z_offset],
                                "size": [16.0, 16.0, 0.1],  # Thin quad
                                "uv": [
                                    0,
                                    0,
                                ],  # Assumes 0,0 of the specified texture_width/height
                            }
                        ],
                    }
                    all_bones.append(layer_bone)
                    layer_count += 1

            if layer_count == 0 and "particle" in texture_layers:
                warnings.append(
                    "No layer0/layer1 found, using 'particle' texture for a fallback quad."
                )
                particle_bone = {
                    "name": "particle_quad",
                    "pivot": [0.0, 0.0, 0.0],
                    "cubes": [
                        {"origin": [-8.0, -8.0, -0.05], "size": [16.0, 16.0, 0.1], "uv": [0, 0]}
                    ],
                }
                all_bones.append(particle_bone)
                layer_count = 1

            if layer_count > 0:
                # Set appropriate visible bounds for a typical 16x16 item sprite
                # Model dimensions are -8 to +8, so width/height is 16 model units.
                # If 16 model units = 1 block unit for bounds purposes:
                geo_description["visible_bounds_width"] = 1.0
                geo_description["visible_bounds_height"] = 1.0
                # Centered quad from -8 to 8 in X/Y plane, so offset is 0,0,0 relative to model origin
                geo_description["visible_bounds_offset"] = [0.0, 0.0, 0.0]
            else:
                warnings.append(
                    f"Item model '{model_p.name}' with parent '{java_parent}' defined no recognized texture layers (layerN or particle). Generating empty model."
                )
                geo_description["visible_bounds_width"] = 0.1
                geo_description["visible_bounds_height"] = 0.1
                geo_description["visible_bounds_offset"] = [0.0, 0.0, 0.0]

        if not processed_as_item_specific_type and java_elements:
            # Standard element processing logic (from previous step)
            model_min_x, model_min_y, model_min_z = float("inf"), float("inf"), float("inf")
            model_max_x, model_max_y, model_max_z = float("-inf"), float("-inf"), float("-inf")

            for i, element in enumerate(java_elements):
                bone_name = f"element_{i}"
                bone_pivot = [0.0, 0.0, 0.0]
                bone_rotation = [0.0, 0.0, 0.0]

                if "rotation" in element:
                    rot = element["rotation"]
                    angle = rot.get("angle", 0.0)
                    axis = rot.get("axis", "y")
                    java_rot_origin = rot.get("origin", [8.0, 8.0, 8.0])
                    bone_pivot = [c - 8.0 for c in java_rot_origin]
                    if axis == "x":
                        bone_rotation[0] = angle
                    elif axis == "y":
                        bone_rotation[1] = -angle  # Often Y rotation is inverted
                    elif axis == "z":
                        bone_rotation[2] = angle
                    else:
                        warnings.append(f"Unsupported rotation axis '{axis}' in element {i}")
                    warnings.append(
                        f"Element {i} has rotation. Ensure pivot {bone_pivot} and rotation {bone_rotation} are correctly interpreted by Bedrock."
                    )

                from_coords = element.get("from", [0.0, 0.0, 0.0])
                to_coords = element.get("to", [16.0, 16.0, 16.0])
                cube_origin = [from_coords[0] - 8.0, from_coords[1] - 8.0, from_coords[2] - 8.0]
                cube_size = [
                    to_coords[0] - from_coords[0],
                    to_coords[1] - from_coords[1],
                    to_coords[2] - from_coords[2],
                ]

                model_min_x = min(model_min_x, cube_origin[0])
                model_min_y = min(model_min_y, cube_origin[1])
                model_min_z = min(model_min_z, cube_origin[2])
                model_max_x = max(model_max_x, cube_origin[0] + cube_size[0])
                model_max_y = max(model_max_y, cube_origin[1] + cube_size[1])
                model_max_z = max(model_max_z, cube_origin[2] + cube_size[2])

                cube_uv = [0, 0]
                element_faces = element.get("faces")
                if element_faces:
                    face_data = None
                    for face_name_priority in ["north", "up", "east", "south", "west", "down"]:
                        if face_name_priority in element_faces:
                            face_data = element_faces[face_name_priority]
                            break
                    if not face_data:
                        face_data = next(iter(element_faces.values()), None)
                    if face_data and "uv" in face_data:
                        cube_uv = [face_data["uv"][0], face_data["uv"][1]]
                        texture_variable = face_data.get("texture")
                        if texture_variable and not texture_variable.startswith("#"):
                            warnings.append(
                                f"Element {i} face uses direct texture path '{texture_variable}' - needs mapping."
                            )

                new_bone = {
                    "name": bone_name,
                    "pivot": bone_pivot,
                    "rotation": bone_rotation,
                    "cubes": [{"origin": cube_origin, "size": cube_size, "uv": cube_uv}],
                }
                all_bones.append(new_bone)

            if java_elements:  # Recalculate bounds if elements were processed
                v_bounds_w = model_max_x - model_min_x
                v_bounds_h = model_max_y - model_min_y
                v_bounds_d = model_max_z - model_min_z
                geo_description["visible_bounds_width"] = round(max(v_bounds_w, v_bounds_d), 4)
                geo_description["visible_bounds_height"] = round(v_bounds_h, 4)
                geo_description["visible_bounds_offset"] = [
                    round(model_min_x + v_bounds_w / 2.0, 4),
                    round(model_min_y + v_bounds_h / 2.0, 4),
                    round(model_min_z + v_bounds_d / 2.0, 4),
                ]
            else:  # No elements, but not handled as item/generated item type
                warnings.append(
                    "No elements found and not a recognized item parent type. Resulting model may be empty or unexpected."
                )
                geo_description["visible_bounds_width"] = 0.125
                geo_description["visible_bounds_height"] = 0.125
                geo_description["visible_bounds_offset"] = [0, 0.0625, 0]

        elif (
            not processed_as_item_specific_type and not java_elements
        ):  # No item-specific handling, no elements
            if java_parent:
                warnings.append(f"Model has unhandled parent '{java_parent}' and no local elements")
            else:
                warnings.append("Model has no elements and no parent")
            # Set default small bounds for an empty or placeholder model
            geo_description["visible_bounds_width"] = 0.1
            geo_description["visible_bounds_height"] = 0.1
            geo_description["visible_bounds_offset"] = [0, 0, 0]

        if java_model.get("display"):
            warnings.append("Java model 'display' transformations are not converted.")

        converted_filename = f"models/{entity_type}/{model_p.stem}.geo.json"

        return {
            "success": True,
            "original_path": str(model_path),
            "converted_path": converted_filename,
            "bedrock_format": "geo.json",
            "bedrock_identifier": bedrock_identifier,
            "warnings": warnings,
            "converted_model_json": bedrock_geo,
        }

    except FileNotFoundError as fnf_error:
        logger.error(f"Model conversion error for {model_path}: {fnf_error}")
        return {
            "success": False,
            "original_path": str(model_path),
            "error": str(fnf_error),
            "warnings": warnings,
        }
    except json.JSONDecodeError as json_error:
        logger.error(f"Model conversion JSON error for {model_path}: {json_error}")
        return {
            "success": False,
            "original_path": str(model_path),
            "error": f"Invalid JSON: {json_error}",
            "warnings": warnings,
        }
    except Exception as e:
        logger.error(f"Model conversion error for {model_path}: {e}", exc_info=True)
        return {
            "success": False,
            "original_path": str(model_path),
            "error": str(e),
            "warnings": warnings,
        }


# ============================================================================
# _analyze_model
# ============================================================================


def _analyze_model(agent, model_path: str, metadata: Dict) -> Dict:
    """Analyze a single model for conversion needs"""
    vertex_count = metadata.get("vertices", 100)
    texture_count = metadata.get("textures", 1)
    bone_count = metadata.get("bones", 0)
    file_ext = Path(model_path).suffix.lower()

    issues = []
    needs_conversion = False

    # Check complexity
    if vertex_count > agent.model_constraints["max_vertices"]:
        issues.append(
            f"Vertex count {vertex_count} exceeds maximum {agent.model_constraints['max_vertices']}"
        )
        needs_conversion = True

    if texture_count > agent.model_constraints["max_textures"]:
        issues.append(
            f"Texture count {texture_count} exceeds maximum {agent.model_constraints['max_textures']}"
        )
        needs_conversion = True

    if bone_count > agent.model_constraints["supported_bones"]:
        issues.append(
            f"Bone count {bone_count} exceeds maximum {agent.model_constraints['supported_bones']}"
        )
        needs_conversion = True

    # Check format
    if file_ext != agent.model_formats["output"]:
        needs_conversion = True

    return {
        "path": model_path,
        "needs_conversion": needs_conversion,
        "issues": issues,
        "current_format": file_ext,
        "target_format": agent.model_formats["output"],
        "complexity": {
            "vertices": vertex_count,
            "textures": texture_count,
            "bones": bone_count,
        },
    }


# ============================================================================
# _generate_model_structure
# ============================================================================


def _generate_model_structure(agent, models: List[Dict]) -> Dict:
    # Ensure only successful conversions are included
    valid_models = [m for m in models if m.get("success")]
    return {
        # These keys are illustrative; the actual output is a list of file contents/paths
        # For this structure, we just return the list of paths and identifiers as before.
        # A higher-level packaging agent would create the actual files.
        "geometry_files": [m["converted_path"] for m in valid_models if "converted_path" in m],
        "identifiers_used": [
            m["bedrock_identifier"] for m in valid_models if "bedrock_identifier" in m
        ],
    }
