"""
Blockstate parsing and conversion module.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


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
            from agents.model_converter.inheritance import get_model_elements_with_inheritance

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

            from agents.model_converter.geometry import _convert_single_model

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
