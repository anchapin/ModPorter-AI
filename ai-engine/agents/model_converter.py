"""
Model converter module - handles all model-related conversion logic.
This module is extracted from asset_converter.py for better organization.
"""

import logging
import json
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

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


# ============================================================================
# _convert_single_model
# ============================================================================


def _convert_single_model(
    agent,
    model_path: str,
    metadata: Dict,
    entity_type: str,
    model_cache: Optional[Dict[str, Dict]] = None,
    namespace: Optional[str] = None,
) -> Dict:
    """
    Convert a Java block/item/entity model JSON to Bedrock geometry format.

    Args:
        agent: AssetConverterAgent instance
        model_path: Path to the model JSON file
        metadata: Optional metadata (texture_width, texture_height)
        entity_type: Type of model ("block", "item", "entity")
        model_cache: Optional cache of model path -> JSON data for parent resolution
        namespace: Optional namespace for resolving parent model paths

    Returns:
        Dict with conversion result
    """
    warnings = []
    try:
        model_p = Path(model_path)
        model_cache = model_cache or {}

        if model_p.exists():
            with open(model_p, "r") as f:
                java_model = json.load(f)
        elif model_path in model_cache:
            java_model = model_cache[model_path]
        else:
            raise FileNotFoundError(f"Model file not found: {model_path}")

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
    valid_models = [m for m in models if m.get("success")]
    return {
        "geometry_files": [m["converted_path"] for m in valid_models if "converted_path" in m],
        "identifiers_used": [
            m["bedrock_identifier"] for m in valid_models if "bedrock_identifier" in m
        ],
    }


# ============================================================================
# extract_models_from_jar
# ============================================================================


def extract_models_from_jar(
    jar_path: str, output_dir: str, namespace: Optional[str] = None
) -> Dict:
    """
    Extract all block/item/entity models from a Java mod JAR file.

    Java models are at: assets/<namespace>/models/block/<name>.json
                       assets/<namespace>/models/item/<name>.json
                       assets/<namespace>/models/entity/<name>.json

    Args:
        jar_path: Path to the JAR file
        output_dir: Directory to extract models to
        namespace: Optional namespace to filter models

    Returns:
        Dict with extraction results including list of extracted models
    """
    extracted_models = []
    errors = []
    warnings = []

    try:
        jar_path_obj = Path(jar_path)
        if not jar_path_obj.exists():
            return {
                "success": False,
                "error": f"JAR file not found: {jar_path}",
                "extracted_models": [],
            }

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(jar_path, "r") as jar:
            file_list = jar.namelist()

            model_files = [
                f
                for f in file_list
                if f.startswith("assets/") and "/models/" in f and f.endswith(".json")
            ]

            if namespace:
                model_files = [f for f in model_files if f.startswith(f"assets/{namespace}/")]

            for model_file in model_files:
                try:
                    model_data = jar.read(model_file)
                    model_json = json.loads(model_data.decode("utf-8"))

                    parts = model_file.split("/")
                    if len(parts) >= 5:
                        model_namespace = parts[1]
                        model_type = parts[3]
                        model_name = Path(parts[-1]).stem
                    else:
                        continue

                    bedrock_type = "block" if model_type == "block" else model_type
                    bedrock_path = f"models/{bedrock_type}/{model_name}.json"

                    full_output_dir = output_path / Path(bedrock_path).parent
                    full_output_dir.mkdir(parents=True, exist_ok=True)

                    output_file = output_path / bedrock_path
                    with open(output_file, "w") as f:
                        json.dump(model_json, f, indent=2)

                    extracted_models.append(
                        {
                            "original_path": model_file,
                            "bedrock_path": bedrock_path,
                            "output_path": str(output_file),
                            "namespace": model_namespace,
                            "model_type": model_type,
                            "model_name": model_name,
                            "has_elements": "elements" in model_json,
                            "parent": model_json.get("parent"),
                            "success": True,
                        }
                    )

                except Exception as e:
                    errors.append(f"Failed to extract {model_file}: {str(e)}")

        blockstate_files = [
            f
            for f in file_list
            if f.startswith("assets/") and "/blockstates/" in f and f.endswith(".json")
        ]

        if namespace:
            blockstate_files = [f for f in blockstate_files if f.startswith(f"assets/{namespace}/")]

        blockstates_parsed = 0
        for blockstate_file in blockstate_files:
            try:
                blockstate_data = jar.read(blockstate_file)
                blockstate_json = json.loads(blockstate_data.decode("utf-8"))
                parts = blockstate_file.split("/")
                if len(parts) >= 4:
                    block_name = Path(parts[-1]).stem
                    namespace = parts[1]
                    blockstate_output_dir = output_path / "blockstates" / namespace
                    blockstate_output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = blockstate_output_dir / f"{block_name}.json"
                    with open(output_file, "w") as f:
                        json.dump(blockstate_json, f, indent=2)
                    blockstates_parsed += 1
            except Exception as e:
                warnings.append(f"Failed to extract blockstate {blockstate_file}: {str(e)}")

        return {
            "success": len(extracted_models) > 0,
            "extracted_models": extracted_models,
            "blockstates_extracted": blockstates_parsed,
            "errors": errors,
            "warnings": warnings,
            "count": len(extracted_models),
        }

    except zipfile.BadZipFile:
        return {
            "success": False,
            "error": f"Invalid JAR file: {jar_path}",
            "extracted_models": [],
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to extract models: {str(e)}",
            "extracted_models": [],
        }


# ============================================================================
# parse_blockstate
# ============================================================================


def parse_blockstate(blockstate_data: Dict) -> Dict:
    """
    Parse a Java blockstate JSON and extract all model variants.

    Blockstates come in two formats:
    1. variants: { "variant_name": { "model": "modid:path/to/model", "y": 90, ... }, ... }
    2. multipart: [ { "when": { "condition": value }, "apply": { "model": "..." } }, ... ]

    Args:
        blockstate_data: Parsed blockstate JSON

    Returns:
        Dict with model variants and their properties
    """
    variants = blockstate_data.get("variants", {})
    multipart = blockstate_data.get("multipart", [])

    parsed_variants = []

    for variant_name, variant_props in variants.items():
        if isinstance(variant_props, dict):
            model_path = variant_props.get("model", "")
            y_rotation = variant_props.get("y", 0)
            x_rotation = variant_props.get("x", 0)
            uvlock = variant_props.get("uvlock", False)

            parsed_variants.append(
                {
                    "variant_key": variant_name,
                    "model": model_path,
                    "y_rotation": y_rotation,
                    "x_rotation": x_rotation,
                    "uvlock": uvlock,
                    "type": "variant",
                }
            )

    for part in multipart:
        when = part.get("when", {})
        apply_props = part.get("apply", {})

        model_path = apply_props.get("model", "")
        y_rotation = apply_props.get("y", 0)
        x_rotation = apply_props.get("x", 0)
        uvlock = apply_props.get("uvlock", False)

        parsed_variants.append(
            {
                "variant_key": json.dumps(when),
                "model": model_path,
                "y_rotation": y_rotation,
                "x_rotation": x_rotation,
                "uvlock": uvlock,
                "when_conditions": when,
                "type": "multipart",
            }
        )

    return {
        "has_variants": len(variants) > 0,
        "has_multipart": len(multipart) > 0,
        "variant_count": len(parsed_variants),
        "variants": parsed_variants,
    }


# ============================================================================
# resolve_parent_model
# ============================================================================


def resolve_parent_model(
    model_data: Dict,
    model_cache: Dict[str, Dict],
    namespace: Optional[str] = None,
    _visited: Optional[set] = None,
) -> Tuple[List[Dict], List[str]]:
    """
    Recursively resolve parent model inheritance to get final elements.

    Java block models can have a "parent" that references another model.
    The parent model defines the base geometry (elements) that the child
    inherits and can override.

    Common parents:
    - block/cube (full block with 6 faces)
    - block/cube_all (block using single texture for all faces)
    - block/cube_column (log-like block with end and side textures)
    - block/cube_bottom_top (block with bottom, top, and side textures)
    - block/cube_directional (block with front/back/left/right/top/bottom)
    - item/generated (flat item sprite)
    - item/handheld (held item with depth)

    For Bedrock conversion, we need the resolved elements to convert.

    Args:
        model_data: The Java model JSON data
        model_cache: Cache of already-loaded models {model_path: model_data}
        namespace: Optional namespace for resolving model paths
        _visited: Internal set to track visited models (for cycle detection)

    Returns:
        Tuple of (resolved_elements, resolution_warnings)
    """
    if _visited is None:
        _visited = set()

    warnings: List[str] = []

    if "elements" in model_data:
        return model_data["elements"], warnings

    parent = model_data.get("parent")
    if not parent:
        warnings.append("Model has no elements and no parent - cannot resolve geometry")
        return [], warnings

    resolved_parent = _resolve_parent_path(parent, namespace)

    if resolved_parent in _visited:
        warnings.append(f"Circular parent reference detected: '{parent}' -> '{resolved_parent}'")
        return [], warnings

    _visited.add(resolved_parent)

    if resolved_parent in model_cache:
        parent_data = model_cache[resolved_parent]
        parent_elements, parent_warnings = resolve_parent_model(
            parent_data, model_cache, namespace, _visited
        )
        warnings.extend(parent_warnings)

        if parent_elements:
            return parent_elements, warnings

    warnings.append(
        f"Could not resolve elements from parent '{parent}' (resolved: '{resolved_parent}')"
    )
    return [], warnings


def _resolve_parent_path(parent: str, namespace: Optional[str] = None) -> str:
    """
    Resolve a parent model path to a full model path.

    Java parent paths can be:
    - "minecraft:block/cube_all" (fully qualified)
    - "block/cube_all" (assumes minecraft namespace)
    - "modid:block/custom_model" (custom mod model)

    Args:
        parent: Parent path string
        namespace: Current model namespace

    Returns:
        Resolved parent path
    """
    if ":" in parent:
        parts = parent.split(":", 1)
        return f"assets/{parts[0]}/models/{parts[1]}"
    else:
        if namespace:
            return f"assets/{namespace}/models/{parent}"
        return f"assets/minecraft/models/{parent}"


# ============================================================================
# get_model_elements_with_inheritance
# ============================================================================


def get_model_elements_with_inheritance(
    model_json: Dict, all_models: Dict[str, Dict], namespace: Optional[str] = None
) -> Tuple[List[Dict], List[str]]:
    """
    Get elements from a model, resolving parent inheritance.

    This is the main entry point for getting a model's elements
    after resolving any parent inheritance chain.

    Args:
        model_json: The Java model JSON (direct from file)
        all_models: Dict mapping model paths to their JSON data
        namespace: Optional namespace

    Returns:
        Tuple of (elements_list, warnings_list)
    """
    return resolve_parent_model(model_json, all_models, namespace)


# ============================================================================
# convert_blockstate
# ============================================================================


def convert_blockstate(
    agent,
    blockstate_path: str,
    model_output_dir: str,
    all_models: Dict[str, Dict],
    namespace: Optional[str] = None,
) -> Dict:
    """
    Convert a Java blockstate and all its referenced models to Bedrock geometry.

    This is the high-level function that:
    1. Parses the blockstate to find model variants
    2. For each variant, resolves the model (including parent inheritance)
    3. Converts each resolved model to Bedrock geometry format

    Args:
        agent: AssetConverterAgent instance
        blockstate_path: Path to blockstate JSON file
        model_output_dir: Directory to output converted models
        all_models: Dict mapping model paths to their JSON data
        namespace: Optional namespace

    Returns:
        Dict with conversion results for all variants
    """
    results = {
        "blockstate_path": blockstate_path,
        "variants_converted": [],
        "variants_failed": [],
        "total_models_attempted": 0,
        "total_models_succeeded": 0,
        "warnings": [],
    }

    try:
        with open(blockstate_path, "r") as f:
            blockstate_data = json.load(f)

        parsed = parse_blockstate(blockstate_data)
        results["warnings"].append(f"Parsed blockstate with {parsed['variant_count']} variants")

        for variant in parsed["variants"]:
            results["total_models_attempted"] += 1
            model_path = variant["model"]

            if not model_path:
                results["variants_failed"].append(
                    {"variant": variant["variant_key"], "error": "No model specified"}
                )
                continue

            resolved_path = _resolve_parent_path(model_path, namespace)

            if resolved_path not in all_models:
                results["warnings"].append(f"Model not in cache: {model_path} -> {resolved_path}")
                results["variants_failed"].append(
                    {"variant": variant["variant_key"], "error": f"Model not found: {model_path}"}
                )
                continue

            model_json = all_models[resolved_path]
            elements, elem_warnings = get_model_elements_with_inheritance(
                model_json, all_models, namespace
            )
            results["warnings"].extend(elem_warnings)

            if not elements:
                results["warnings"].append(f"No elements resolved for model: {model_path}")
                results["variants_failed"].append(
                    {"variant": variant["variant_key"], "error": "No elements in resolved model"}
                )
                continue

            model_name = Path(blockstate_path).stem
            variant_suffix = variant["variant_key"].replace("=", "_").replace(",", "_")
            variant_model_name = f"{model_name}_{variant_suffix}"

            metadata = {
                "texture_width": model_json.get("textures", {}).get("width", 16),
                "texture_height": model_json.get("textures", {}).get("height", 16),
            }

            conversion_result = _convert_single_model(
                agent,
                resolved_path,
                metadata,
                "block",
            )

            if conversion_result.get("success"):
                conversion_result["variant_key"] = variant["variant_key"]
                conversion_result["variant_model_name"] = variant_model_name
                conversion_result["y_rotation"] = variant.get("y_rotation", 0)
                conversion_result["x_rotation"] = variant.get("x_rotation", 0)
                results["variants_converted"].append(conversion_result)
                results["total_models_succeeded"] += 1
            else:
                results["variants_failed"].append(
                    {
                        "variant": variant["variant_key"],
                        "error": conversion_result.get("error", "Unknown error"),
                    }
                )

    except Exception as e:
        results["error"] = str(e)
        logger.error(f"Error converting blockstate {blockstate_path}: {e}")

    return results
