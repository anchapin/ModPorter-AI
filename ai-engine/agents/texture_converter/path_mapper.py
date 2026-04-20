"""
Java to Bedrock texture path mapping module.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def convert_java_texture_path(agent, java_path: str, bedrock_type: str = "blocks") -> str:
    """
    Convert Java texture path to Bedrock texture path.

    Args:
        java_path: Java texture path (e.g., 'assets/modid/textures/block/grass_block_side.png')
        bedrock_type: Target Bedrock texture type ('blocks', 'items', 'entity')

    Returns:
        Bedrock texture path (e.g., 'textures/blocks/grass_block_side')
    """
    parts = java_path.replace("\\", "/").split("/")

    try:
        textures_idx = parts.index("textures")
    except ValueError:
        textures_idx = -1

    if textures_idx >= 0:
        relative_parts = parts[textures_idx + 1 :]
    else:
        relative_parts = [p for p in parts if p.endswith(".png")]
        if relative_parts:
            relative_parts = [relative_parts[0]]
        else:
            relative_parts = []

    if relative_parts:
        filename = relative_parts[-1]
        if filename.endswith(".png"):
            filename = filename[:-4]
    else:
        filename = "unknown"

    bedrock_path = f"textures/{bedrock_type}/{filename}"

    logger.debug(f"Converted Java path '{java_path}' to Bedrock path '{bedrock_path}'")
    return bedrock_path


def _map_java_texture_to_bedrock(agent, java_path: str) -> str:
    """
    Map a Java mod texture path to Bedrock resource pack texture path.

    Java: assets/<namespace>/textures/<type>/<name>.png
    Bedrock: textures/<type>/<name>.png

    Args:
        java_path: Java mod texture path

    Returns:
        Bedrock texture path
    """
    parts = java_path.split("/")

    if len(parts) >= 5 and parts[0] == "assets" and parts[2] == "textures":
        texture_type = parts[3]
        texture_name = parts[4]

        bedrock_type = agent._map_texture_type(texture_type)

        return f"textures/{bedrock_type}/{texture_name}"

    return f"textures/{Path(java_path).name}"


def _map_texture_type(agent, java_type: str) -> str:
    """
    Map Java texture type to Bedrock texture type.

    Args:
        java_type: Java texture type (block, item, entity, etc.)

    Returns:
        Bedrock texture type
    """
    type_mapping = {
        "block": "blocks",
        "item": "items",
        "entity": "entity",
        "blockentity": "entity",
        "particle": "particle",
        "armor": "armor",
        "misc": "misc",
        "environment": "environment",
        "gui": "gui",
        "painting": "painting",
    }

    return type_mapping.get(java_type.lower(), "misc")


def _map_bedrock_texture_to_java(agent, bedrock_path: str, namespace: str) -> str:
    """
    Map a Bedrock texture path back to Java mod texture path.

    Bedrock: textures/blocks/name.png
    Java: assets/<namespace>/textures/block/name.png

    Args:
        bedrock_path: Bedrock texture path
        namespace: Java mod namespace

    Returns:
        Java texture path
    """
    parts = bedrock_path.split("/")

    if len(parts) >= 3 and parts[0] == "textures":
        bedrock_type = parts[1]
        texture_name = parts[2]

        java_type = agent._map_bedrock_type_to_java(bedrock_type)

        return f"assets/{namespace}/textures/{java_type}/{texture_name}"

    return f"assets/{namespace}/textures/misc/{bedrock_path}"


def _map_bedrock_type_to_java(agent, bedrock_type: str) -> str:
    """
    Map Bedrock texture type to Java texture type.

    Args:
        bedrock_type: Bedrock texture type (blocks, items, entity, etc.)

    Returns:
        Java texture type
    """
    type_mapping = {
        "blocks": "block",
        "items": "item",
        "entity": "entity",
        "particle": "particle",
        "armor": "armor",
        "misc": "misc",
        "environment": "environment",
        "gui": "gui",
    }

    return type_mapping.get(bedrock_type.lower(), "misc")
