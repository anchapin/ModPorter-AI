"""
Model inheritance resolution module.
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


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

    from agents.model_converter.blockstate import _resolve_parent_path

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
