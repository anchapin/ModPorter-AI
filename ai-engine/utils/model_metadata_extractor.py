"""
3D Model metadata extractor for Bedrock .json model files.

This module provides functionality to extract metadata from Bedrock Edition
model JSON files including geometry definitions, animation data, material
references, parent model references, and model type classification.
"""

import json
import os
import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Import MultiModalDocument schema
try:
    from schemas.multimodal_schema import MultiModalDocument, ContentType, ProcessingStatus
except ImportError:
    try:
        from ai_engine.schemas.multimodal_schema import (
            MultiModalDocument,
            ContentType,
            ProcessingStatus,
        )
    except ImportError:
        MultiModalDocument = None
        ContentType = None
        ProcessingStatus = None
        logger.warning("Could not import MultiModalDocument schema")


class ModelMetadataExtractor:
    """
    Extracts metadata from Bedrock Edition model JSON files.

    Supports:
    - Geometry definition extraction (cube count, bone count)
    - Animation data extraction (animation names, length, loops)
    - Material reference extraction
    - Parent model reference extraction (for variants)
    - Model type classification (entity, block, item, animated)
    """

    # Model type patterns in file path
    MODEL_TYPE_PATTERNS = {
        "entity": ["entity", "mob", "hostile", "passive", "animal", "npc"],
        "block": ["block", "cube", "block_model"],
        "item": ["item", "hand", "held"],
        "animated": ["animation", "animated", "controller"],
    }

    def __init__(self):
        """Initialize the model metadata extractor."""
        self.geometry_schemas = ["minecraft:geometry", "minecraft:geometry_template"]

    def extract(self, file_path: str) -> Optional[MultiModalDocument]:
        """
        Extract metadata from a Bedrock model JSON file.

        Args:
            file_path: Path to the model JSON file

        Returns:
            Dictionary containing extracted metadata, or None if extraction failed
        """
        if not os.path.exists(file_path):
            logger.error(f"Model file not found: {file_path}")
            return None

        try:
            with open(file_path, "r") as f:
                model_data = json.load(f)

            # Extract geometry information
            geometry_info = self._extract_geometry(model_data)

            # Extract animation information
            animation_info = self._extract_animations(model_data)

            # Extract material references
            material_refs = self._extract_materials(model_data)

            # Extract parent model references
            parent_refs = self._extract_parents(model_data)

            # Classify model type
            model_type = self._classify_model_type(file_path, model_data)

            # Build result dictionary (for metadata content)
            metadata_content = {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "geometry_count": geometry_info["geometry_count"],
                "cube_count": geometry_info["cube_count"],
                "bone_count": geometry_info["bone_count"],
                "texture_width": geometry_info["texture_width"],
                "texture_height": geometry_info["texture_height"],
                "animations": animation_info,
                "material_references": material_refs,
                "parent_references": parent_refs,
                "model_type": model_type,
            }

            # Return as MultiModalDocument if schema is available
            if MultiModalDocument and ContentType and ProcessingStatus:
                content_text = json.dumps(metadata_content)
                content_hash = str(uuid.uuid4())  # Simple hash for now

                return MultiModalDocument(
                    id=str(uuid.uuid4()),
                    content_hash=content_hash,
                    source_path=file_path,
                    content_type=ContentType.MULTIMODAL,
                    content_text=content_text,
                    content_metadata=metadata_content,
                    processing_status=ProcessingStatus.COMPLETED,
                    indexed_at=datetime.now(timezone.utc),
                )
            else:
                # Fallback to dict if schema not available
                return metadata_content

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in model file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to extract model metadata from {file_path}: {e}")
            return None

    def _extract_geometry(self, model_data: Dict) -> Dict[str, Any]:
        """
        Extract geometry definitions from model data.

        Args:
            model_data: Parsed JSON model data

        Returns:
            Dictionary with geometry information
        """
        geometry_count = 0
        cube_count = 0
        bone_count = 0
        texture_width = 64
        texture_height = 64

        # Find geometry entries
        for schema in self.geometry_schemas:
            if schema in model_data:
                geometries = model_data[schema]
                if isinstance(geometries, list):
                    geometry_count = len(geometries)
                    for geometry in geometries:
                        if isinstance(geometry, dict):
                            # Extract description
                            description = geometry.get("description", {})
                            if isinstance(description, dict):
                                texture_width = description.get("texture_width", texture_width)
                                texture_height = description.get("texture_height", texture_height)

                            # Count bones
                            bones = geometry.get("bones", [])
                            if isinstance(bones, list):
                                bone_count += len(bones)

                                # Count cubes in each bone
                                for bone in bones:
                                    if isinstance(bone, dict):
                                        cubes = bone.get("cubes", [])
                                        if isinstance(cubes, list):
                                            cube_count += len(cubes)

        return {
            "geometry_count": geometry_count,
            "cube_count": cube_count,
            "bone_count": bone_count,
            "texture_width": texture_width,
            "texture_height": texture_height,
        }

    def _extract_animations(self, model_data: Dict) -> List[Dict[str, Any]]:
        """
        Extract animation data from model data.

        Args:
            model_data: Parsed JSON model data

        Returns:
            List of animation information dictionaries
        """
        animations = []

        # Look for animation definitions
        animation_schemas = ["minecraft:animations", "animations"]

        for schema in animation_schemas:
            if schema in model_data:
                anim_data = model_data[schema]
                if isinstance(anim_data, dict):
                    for anim_name, anim_content in anim_data.items():
                        animation_entry = {
                            "name": anim_name,
                            "loop": anim_content.get("loop", False)
                            if isinstance(anim_content, dict)
                            else False,
                        }

                        # Extract animation length if available
                        if isinstance(anim_content, dict):
                            animation_entry["length"] = anim_content.get("length", 0.0)

                            # Look for timeline or animation bones
                            if "timeline" in anim_content:
                                animation_entry["has_timeline"] = True
                            if "bones" in anim_content:
                                animation_entry["bone_count"] = len(anim_content["bones"])

                        animations.append(animation_entry)
                elif isinstance(anim_data, list):
                    # Handle list format
                    for anim in anim_data:
                        if isinstance(anim, dict):
                            animations.append(
                                {
                                    "name": anim.get("name", "unknown"),
                                    "loop": anim.get("loop", False),
                                    "length": anim.get("length", 0.0),
                                }
                            )

        return animations

    def _extract_materials(self, model_data: Dict) -> List[str]:
        """
        Extract material references from model data.

        Args:
            model_data: Parsed JSON model data

        Returns:
            List of material names
        """
        materials = []

        # Look for material definitions in various locations
        # Check geometry materials
        for schema in self.geometry_schemas:
            if schema in model_data:
                geometries = model_data[schema]
                if isinstance(geometries, list):
                    for geometry in geometries:
                        if isinstance(geometry, dict):
                            # Check for materials in geometry
                            materials.extend(self._find_materials_in_dict(geometry))

        return list(set(materials))  # Remove duplicates

    def _find_materials_in_dict(self, data: Any) -> List[str]:
        """Recursively find material references in a dictionary."""
        materials = []

        if isinstance(data, dict):
            for key, value in data.items():
                # Look for material-related keys
                if key in ["material", "materials", "particle", "texture"]:
                    if isinstance(value, str):
                        materials.append(value)
                    elif isinstance(value, dict):
                        for v in value.values():
                            if isinstance(v, str):
                                materials.append(v)
                else:
                    # Recurse into nested structures
                    materials.extend(self._find_materials_in_dict(value))
        elif isinstance(data, list):
            for item in data:
                materials.extend(self._find_materials_in_dict(item))

        return materials

    def _extract_parents(self, model_data: Dict) -> List[str]:
        """
        Extract parent model references.

        Args:
            model_data: Parsed JSON model data

        Returns:
            List of parent model identifiers
        """
        parents = []

        # Look for parent reference in description or root
        description = model_data.get("description", {})

        if isinstance(description, dict):
            parent = description.get("parent")
            if parent:
                parents.append(parent)

            # Check for template reference
            template = description.get("template_reference")
            if template:
                parents.append(template)

        # Check for geometry templates
        geometry_templates = model_data.get("minecraft:geometry_template", [])
        if isinstance(geometry_templates, list):
            for template in geometry_templates:
                if isinstance(template, dict):
                    parent = template.get("parent")
                    if parent:
                        parents.append(parent)

        return list(set(parents))

    def _classify_model_type(self, file_path: str, model_data: Dict) -> Optional[str]:
        """
        Classify the model type based on path and content.

        Args:
            file_path: Path to the model file
            model_data: Parsed JSON model data

        Returns:
            Model type string (entity, block, item, animated) or None
        """
        path_lower = file_path.lower()

        # Check path patterns first
        for model_type, patterns in self.MODEL_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in path_lower:
                    return model_type

        # Check content for animated models
        if "minecraft:animations" in model_data or "animations" in model_data:
            return "animated"

        # Default to entity if uncertain
        return "entity"


def extract_model_metadata(file_path: str) -> Optional[MultiModalDocument]:
    """
    Convenience function to extract model metadata.

    Args:
        file_path: Path to the model JSON file

    Returns:
        MultiModalDocument instance containing extracted metadata, or None if extraction failed
    """
    extractor = ModelMetadataExtractor()
    return extractor.extract(file_path)
