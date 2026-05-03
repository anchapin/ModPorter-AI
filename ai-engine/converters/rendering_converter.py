"""
Rendering Converter for converting Java entity rendering systems to Bedrock format.

Converts Java EntityRenderer, model classes, textures, and animation definitions
to Bedrock's render controller .json, geometry definitions, and animation controllers.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RenderControllerType(Enum):
    """Bedrock render controller types."""

    ENTITY = "entity"
    BLOCK = "block"
    ITEM = "item"
    ARMOR = "armor"
    CUSTOM = "custom"


class ModelType(Enum):
    """Bedrock model types."""

    BIPED = "biped"
    QUADRUPED = "quadruped"
    ARMORSMITH = "armorsmith"
    ITEM_DISPLAY = "item_display"
    CUSTOM = "custom"


class TextureType(Enum):
    """Bedrock texture types."""

    COLOR = "color"
    EMISSIVE = "emissive"
    ARMOR = "armor"
    NORMAL = "normal"
    CUSTOM = "custom"


# Java to Bedrock model mapping
JAVA_TO_BEDROCK_MODEL = {
    "biped": "biped",
    "quadruped": "quadruped",
    "armorsmith": "armorsmith",
    "item_display": "item_display",
    "zombie": "biped",
    "skeleton": "biped",
    "pig": "quadruped",
    "cow": "quadruped",
    "horse": "quadruped",
    "slime": "custom",
    "enderdragon": "custom",
    "witherskull": "custom",
}

# Java to Bedrock texture mapping
JAVA_TO_BEDROCK_TEXTURE = {
    "color": "color",
    "emissive": "emissive",
    "armor": "armor",
    "normal": "normal",
    "leather": "color",
    "chainmail": "armor",
    "iron": "color",
    "gold": "color",
    "diamond": "color",
    "netherite": "color",
}


@dataclass
class RenderControllerDefinition:
    """Represents a Bedrock render controller."""

    identifier: str
    controller_type: RenderControllerType
    geometry_id: str
    texture_id: str
    materials: List[Dict[str, Any]] = field(default_factory=list)
    shaders: List[str] = field(default_factory=list)


@dataclass
class GeometryDefinition:
    """Represents a Bedrock geometry definition."""

    identifier: str
    model_type: ModelType
    bones: List[Dict[str, Any]] = field(default_factory=list)
    texture_dimensions: Dict[str, int] = field(default_factory=lambda: {"width": 64, "height": 64})
    parent_geometry: Optional[str] = None


@dataclass
class TextureMapping:
    """Represents a Bedrock texture mapping."""

    texture_id: str
    path: str
    texture_type: TextureType
    is_animated: bool = False
    animation_frames: int = 1


@dataclass
class AnimationDefinition:
    """Represents a Bedrock animation."""

    identifier: str
    animation_type: str
    length: float = 1.0
    loops: bool = True
    bone_animations: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)


@dataclass
class AnimationControllerDefinition:
    """Represents a Bedrock animation controller."""

    identifier: str
    initial_state: str
    states: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class RenderingConverter:
    """
    Converter for Java entity rendering to Bedrock format.

    Handles render controller conversion, geometry definitions, texture mappings,
    and animation controller generation for Bedrock's entity rendering system.
    """

    def __init__(self):
        """Initialize the RenderingConverter."""
        self.model_map = JAVA_TO_BEDROCK_MODEL.copy()
        self.texture_map = JAVA_TO_BEDROCK_TEXTURE.copy()
        self.animation_converter = AnimationConverter()

    def convert_render_controller(
        self, java_renderer: Dict[str, Any]
    ) -> RenderControllerDefinition:
        """
        Convert Java EntityRenderer to Bedrock render controller.

        Args:
            java_renderer: Java renderer dictionary containing model/texture info

        Returns:
            RenderControllerDefinition object
        """
        entity_id = java_renderer.get("entityId", "custom_entity")
        model_class = java_renderer.get("modelClass", "biped")
        texture_resource = java_renderer.get("texture", "textures/entity/custom")

        # Convert model type
        bedrock_model = self.convert_model_type(model_class)

        # Convert texture
        texture_type = self.convert_texture_type(java_renderer.get("textureType", "color"))

        # Generate render controller
        controller = RenderControllerDefinition(
            identifier=f"controller.render.{entity_id}",
            controller_type=RenderControllerType.ENTITY,
            geometry_id=f"geometry.{bedrock_model}",
            texture_id=texture_resource,
            materials=self._generate_materials(bedrock_model),
            shaders=self._generate_shaders(bedrock_model),
        )

        return controller

    def convert_geometry(self, java_model: Dict[str, Any]) -> GeometryDefinition:
        """
        Convert Java model to Bedrock geometry definition.

        Args:
            java_model: Java model dictionary

        Returns:
            GeometryDefinition object
        """
        model_id = java_model.get("modelId", "custom_model")
        model_class = java_model.get("modelClass", "biped")
        bones = java_model.get("bones", [])
        texture_width = java_model.get("textureWidth", 64)
        texture_height = java_model.get("textureHeight", 64)

        # Convert model type
        bedrock_model = self.convert_model_type(model_class)

        # Convert bone structure
        converted_bones = self.map_bone_structure(bones)

        geometry = GeometryDefinition(
            identifier=f"geometry.{model_id}",
            model_type=bedrock_model,
            bones=converted_bones,
            texture_dimensions={"width": texture_width, "height": texture_height},
            parent_geometry=java_model.get("parentModel"),
        )

        return geometry

    def convert_texture_mapping(self, java_texture: Dict[str, Any]) -> TextureMapping:
        """
        Convert Java texture mapping to Bedrock format.

        Args:
            java_texture: Java texture dictionary

        Returns:
            TextureMapping object
        """
        texture_id = java_texture.get("textureId", "custom_texture")
        path = java_texture.get("path", "textures/entity/custom")
        texture_type_str = java_texture.get("type", "color")

        # Convert texture type
        bedrock_texture_type = self.convert_texture_type(texture_type_str)

        return TextureMapping(
            texture_id=texture_id,
            path=path,
            texture_type=bedrock_texture_type,
            is_animated=java_texture.get("animated", False),
            animation_frames=java_texture.get("frames", 1),
        )

    def convert_model_type(self, java_model: str) -> ModelType:
        """
        Convert Java model class to Bedrock model type.

        Args:
            java_model: Java model class name

        Returns:
            Bedrock ModelType enum
        """
        model_lower = java_model.lower()
        if ":" in model_lower:
            model_lower = model_lower.split(":", 1)[1]

        model_key = self.model_map.get(model_lower, "custom")
        try:
            return ModelType(model_key)
        except ValueError:
            return ModelType.CUSTOM

    def convert_texture_type(self, java_texture: str) -> TextureType:
        """
        Convert Java texture type to Bedrock texture type.

        Args:
            java_texture: Java texture type

        Returns:
            Bedrock TextureType enum
        """
        texture_lower = java_texture.lower()
        if ":" in texture_lower:
            texture_lower = texture_lower.split(":", 1)[1]

        texture_key = self.texture_map.get(texture_lower, "custom")
        try:
            return TextureType(texture_key)
        except ValueError:
            return TextureType.CUSTOM

    def convert_geometry_definition(self, geometry: GeometryDefinition) -> Dict[str, Any]:
        """
        Convert GeometryDefinition to Bedrock geometry JSON.

        Args:
            geometry: GeometryDefinition object

        Returns:
            Bedrock geometry JSON structure
        """
        geometry_json = {
            "format_version": "1.16.0",
            "minecraft:geometry": {
                "description": {
                    "identifier": geometry.identifier,
                    "texture_width": geometry.texture_dimensions["width"],
                    "texture_height": geometry.texture_dimensions["height"],
                },
                "bones": geometry.bones,
            },
        }

        if geometry.parent_geometry:
            geometry_json["minecraft:geometry"]["description"]["parent"] = geometry.parent_geometry

        return geometry_json

    def map_bone_structure(self, java_bones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert Java bone structure to Bedrock bone hierarchy.

        Args:
            java_bones: List of Java bone dictionaries

        Returns:
            List of Bedrock bone definitions
        """
        bedrock_bones = []

        for bone in java_bones:
            bedrock_bone = {
                "name": bone.get("name", "bone"),
                "pivot": bone.get("pivot", [0, 0, 0]),
                "rotation": bone.get("rotation", [0, 0, 0]),
            }

            # Add cube definitions
            if "cubes" in bone:
                bedrock_bone["cubes"] = []
                for cube in bone["cubes"]:
                    cube_def = {
                        "origin": cube.get("origin", [0, 0, 0]),
                        "size": cube.get("size", [1, 1, 1]),
                        "uv": cube.get("uv", [0, 0]),
                    }
                    bedrock_bone["cubes"].append(cube_def)

            # Add child bones
            if "children" in bone:
                bedrock_bone["children"] = bone["children"]

            bedrock_bones.append(bedrock_bone)

        return bedrock_bones

    def convert_model_properties(self, java_properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java model properties to Bedrock model settings.

        Args:
            java_properties: Java model properties

        Returns:
            Bedrock model settings
        """
        return {
            "scale": java_properties.get("scale", 1.0),
            "shadow": java_properties.get("shadow", True),
            "leg_rotation_speed": java_properties.get("legRotationSpeed", 1.0),
            "rideable": java_properties.get("rideable", False),
            "carried_items": java_properties.get("carriedItems", False),
        }

    def generate_render_controller_json(
        self, controller: RenderControllerDefinition
    ) -> Dict[str, Any]:
        """
        Generate Bedrock render controller JSON file.

        Args:
            controller: RenderControllerDefinition object

        Returns:
            Bedrock render controller JSON
        """
        render_controller = {
            "format_version": "1.16.0",
            "render_controller": {
                "controller": controller.identifier,
                "textures": [controller.texture_id],
                "materials": controller.materials,
                "shaders": controller.shaders,
            },
        }

        return render_controller

    def _generate_materials(self, model_type: str) -> List[Dict[str, Any]]:
        """Generate default materials for a model type."""
        base_materials = [
            {"texture": "color", "fragment_shader": "entity"},
            {"texture": "emissive", "fragment_shader": "emissive"},
        ]

        if model_type == "armorsmith":
            base_materials.append({"texture": "armor", "fragment_shader": "armor"})
        elif model_type == "quadruped":
            base_materials[0]["fragment_shader"] = "horse"

        return base_materials

    def _generate_shaders(self, model_type: str) -> List[str]:
        """Generate default shaders for a model type."""
        shaders = ["vertex", "fragment"]

        if model_type == "custom":
            shaders.append("skinning")

        return shaders


class AnimationConverter:
    """
    Converter for Java entity animations to Bedrock format.

    Handles animation keyframes, bone animations, animation controllers,
    and particle effects in rendering.
    """

    def __init__(self):
        """Initialize the AnimationConverter."""
        self.animation_clips = {}

    def convert_animation(self, java_animation: Dict[str, Any]) -> AnimationDefinition:
        """
        Convert Java animation to Bedrock animation definition.

        Args:
            java_animation: Java animation dictionary

        Returns:
            AnimationDefinition object
        """
        anim_id = java_animation.get("animationId", "custom_animation")
        anim_type = java_animation.get("type", "controller")
        length = java_animation.get("length", 1.0)
        loops = java_animation.get("loops", True)

        # Convert bone animations
        bone_animations = {}
        if "bones" in java_animation:
            for bone_name, frames in java_animation["bones"].items():
                bone_animations[bone_name] = self.convert_bone_animation(bone_name, frames)

        return AnimationDefinition(
            identifier=f"animation.{anim_id}",
            animation_type=anim_type,
            length=length,
            loops=loops,
            bone_animations=bone_animations,
        )

    def convert_keyframe(self, java_keyframe: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java keyframe to Bedrock keyframe data.

        Args:
            java_keyframe: Java keyframe dictionary

        Returns:
            Bedrock keyframe data
        """
        return {
            "time": java_keyframe.get("time", 0.0),
            "rotation": java_keyframe.get("rotation", [0, 0, 0]),
            "position": java_keyframe.get("position", [0, 0, 0]),
            "scale": java_keyframe.get("scale", [1, 1, 1]),
        }

    def convert_bone_animation(
        self, bone: str, frames: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert bone animation frames to Bedrock format.

        Args:
            bone: Bone name
            frames: List of animation frames

        Returns:
            List of converted keyframes
        """
        converted_frames = []
        for frame in frames:
            converted_frame = self.convert_keyframe(frame)
            converted_frames.append(converted_frame)

        return converted_frames

    def convert_animation_blend(self, java_blend: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert animation blend settings.

        Args:
            java_blend: Java blend settings

        Returns:
            Bedrock blend settings
        """
        return {
            "blend_transition": java_blend.get("transition", 0.0),
            "blend_mode": java_blend.get("mode", "linear"),
            "ease_in": java_blend.get("easeIn", False),
            "ease_out": java_blend.get("easeOut", False),
        }

    def convert_animation_controller(
        self, java_controller: Dict[str, Any]
    ) -> AnimationControllerDefinition:
        """
        Convert Java animation controller to Bedrock format.

        Args:
            java_controller: Java animation controller dictionary

        Returns:
            AnimationControllerDefinition object
        """
        controller_id = java_controller.get("controllerId", "custom_controller")
        initial = java_controller.get("initialState", "idle")

        # Convert state machine
        states = self.convert_state_machine(java_controller.get("states", {}))

        return AnimationControllerDefinition(
            identifier=f"animation_controller.{controller_id}",
            initial_state=initial,
            states=states,
        )

    def convert_state_machine(self, states: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Convert animation state machine.

        Args:
            states: State definitions

        Returns:
            Converted states dictionary
        """
        converted_states = {}

        for state_name, state_data in states.items():
            converted_state = {
                "animations": state_data.get("animations", []),
                "transitions": self.map_animation_states(state_data.get("transitions", [])),
            }
            converted_states[state_name] = converted_state

        return converted_states

    def map_animation_states(self, transitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Map animation state transitions.

        Args:
            transitions: List of transition definitions

        Returns:
            List of converted transitions
        """
        converted_transitions = []

        for transition in transitions:
            converted_transition = {
                "state": transition.get("to", "idle"),
                "condition": transition.get("condition", ""),
                "transition_time": transition.get("transitionTime", 0.0),
            }
            converted_transitions.append(converted_transition)

        return converted_transitions

    def map_animation_clips(self, java_clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Map Java animation clips to Bedrock animation clips.

        Args:
            java_clips: List of Java animation clips

        Returns:
            List of Bedrock animation clips
        """
        clips = []

        for clip in java_clips:
            clip_def = {
                "name": clip.get("name", "clip"),
                "animation": clip.get("animation", ""),
                "loop": clip.get("loop", True),
                "weight": clip.get("weight", 1.0),
            }
            clips.append(clip_def)

        return clips

    def attach_particle_to_model(self, particle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attach particle effect to model.

        Args:
            particle_data: Particle effect data

        Returns:
            Model particle attachment definition
        """
        return {
            "particle": particle_data.get("particle", ""),
            "bone": particle_data.get("bone", ""),
            "offset": particle_data.get("offset", [0, 0, 0]),
            "frequency": particle_data.get("frequency", 1.0),
            "follow_entity": particle_data.get("followEntity", True),
        }

    def generate_animation_json(self, animation: AnimationDefinition) -> Dict[str, Any]:
        """
        Generate Bedrock animation JSON file.

        Args:
            animation: AnimationDefinition object

        Returns:
            Bedrock animation JSON structure
        """
        animation_json = {
            "format_version": "1.16.0",
            "animations": {
                animation.identifier: {
                    "loop": animation.loops,
                    "animation_length": animation.length,
                }
            },
        }

        # Add bone animations
        if animation.bone_animations:
            bone_anim_entry = {}
            for bone_name, frames in animation.bone_animations.items():
                bone_anim_entry[bone_name] = {"keyframes": frames}
            animation_json["animations"][animation.identifier]["bone_scripts"] = bone_anim_entry

        return animation_json

    def generate_animation_controller_json(
        self, controller: AnimationControllerDefinition
    ) -> Dict[str, Any]:
        """
        Generate Bedrock animation controller JSON file.

        Args:
            controller: AnimationControllerDefinition object

        Returns:
            Bedrock animation controller JSON structure
        """
        controller_json = {
            "format_version": "1.16.0",
            "animation_controllers": {
                controller.identifier: {
                    "initial_state": controller.initial_state,
                    "states": controller.states,
                }
            },
        }

        return controller_json


# Convenience functions
def convert_render_controller(java_renderer: Dict[str, Any]) -> RenderControllerDefinition:
    """Convert Java render controller to Bedrock render controller definition."""
    converter = RenderingConverter()
    return converter.convert_render_controller(java_renderer)


def convert_geometry(java_model: Dict[str, Any]) -> GeometryDefinition:
    """Convert Java model to Bedrock geometry definition."""
    converter = RenderingConverter()
    return converter.convert_geometry(java_model)


def convert_texture(java_texture: Dict[str, Any]) -> TextureMapping:
    """Convert Java texture to Bedrock texture mapping."""
    converter = RenderingConverter()
    return converter.convert_texture_mapping(java_texture)


def convert_animation(java_animation: Dict[str, Any]) -> AnimationDefinition:
    """Convert Java animation to Bedrock animation definition."""
    converter = AnimationConverter()
    return converter.convert_animation(java_animation)


def convert_animation_controller(java_controller: Dict[str, Any]) -> AnimationControllerDefinition:
    """Convert Java animation controller to Bedrock animation controller definition."""
    converter = AnimationConverter()
    return converter.convert_animation_controller(java_controller)


def generate_render_controller_file(java_renderer: Dict[str, Any]) -> Dict[str, Any]:
    """Generate complete Bedrock render controller JSON file."""
    converter = RenderingConverter()
    controller = converter.convert_render_controller(java_renderer)
    return converter.generate_render_controller_json(controller)


def generate_geometry_file(java_model: Dict[str, Any]) -> Dict[str, Any]:
    """Generate complete Bedrock geometry JSON file."""
    converter = RenderingConverter()
    geometry = converter.convert_geometry(java_model)
    return converter.convert_geometry_definition(geometry)


def generate_animation_file(java_animation: Dict[str, Any]) -> Dict[str, Any]:
    """Generate complete Bedrock animation JSON file."""
    converter = AnimationConverter()
    animation = converter.convert_animation(java_animation)
    return converter.generate_animation_json(animation)


def generate_animation_controller_file(java_controller: Dict[str, Any]) -> Dict[str, Any]:
    """Generate complete Bedrock animation controller JSON file."""
    converter = AnimationConverter()
    controller = converter.convert_animation_controller(java_controller)
    return converter.generate_animation_controller_json(controller)
