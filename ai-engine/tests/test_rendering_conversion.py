"""
Unit tests for Rendering/Entity Conversion.

Tests the conversion of Java entity rendering systems, models, textures,
and animations to Bedrock's render controller .json, geometry definitions,
and animation controllers.
"""

import pytest
import sys
import json
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from converters.rendering_converter import (
    RenderingConverter,
    AnimationConverter,
    RenderControllerDefinition,
    GeometryDefinition,
    TextureMapping,
    AnimationDefinition,
    AnimationControllerDefinition,
    RenderControllerType,
    ModelType,
    TextureType,
    convert_render_controller,
    convert_geometry,
    convert_texture,
    convert_animation,
    convert_animation_controller,
    generate_render_controller_file,
    generate_geometry_file,
    generate_animation_file,
    generate_animation_controller_file,
)
from knowledge.patterns.rendering_patterns import (
    RenderingPatternLibrary,
    RenderingPatternCategory,
    RenderingPattern,
    get_rendering_pattern,
    search_rendering_patterns,
    get_rendering_stats,
)


class TestRenderControllerConversion:
    """Test cases for render controller conversion."""

    def test_rendering_converter_initialization(self):
        """Test RenderingConverter initializes correctly."""
        converter = RenderingConverter()
        assert converter is not None
        assert len(converter.model_map) > 0
        assert len(converter.texture_map) > 0

    def test_render_controller_enum(self):
        """Test RenderControllerType enum values."""
        assert RenderControllerType.ENTITY.value == "entity"
        assert RenderControllerType.BLOCK.value == "block"
        assert RenderControllerType.ITEM.value == "item"
        assert RenderControllerType.CUSTOM.value == "custom"

    def test_convert_render_controller_basic(self):
        """Test basic render controller conversion."""
        converter = RenderingConverter()
        java_renderer = {
            "entityId": "zombie",
            "modelClass": "biped",
            "texture": "textures/entity/zombie",
        }
        controller = converter.convert_render_controller(java_renderer)
        assert controller.identifier == "controller.render.zombie"
        assert controller.controller_type == RenderControllerType.ENTITY

    def test_convert_render_controller_mod_entity(self):
        """Test render controller conversion for mod entity."""
        converter = RenderingConverter()
        java_renderer = {
            "entityId": "mymod:custom_mob",
            "modelClass": "quadruped",
            "texture": "textures/entity/mymod/custom_mob",
        }
        controller = converter.convert_render_controller(java_renderer)
        assert "custom_mob" in controller.identifier

    def test_generate_render_controller_json(self):
        """Test render controller JSON generation."""
        converter = RenderingConverter()
        controller = RenderControllerDefinition(
            identifier="controller.render.test",
            controller_type=RenderControllerType.ENTITY,
            geometry_id="geometry.biped",
            texture_id="textures/entity/test",
        )
        json_output = converter.generate_render_controller_json(controller)
        assert "format_version" in json_output
        assert "render_controller" in json_output


class TestAnimationConversion:
    """Test cases for animation conversion."""

    def test_animation_converter_initialization(self):
        """Test AnimationConverter initializes correctly."""
        converter = AnimationConverter()
        assert converter is not None

    def test_convert_animation_basic(self):
        """Test basic animation conversion."""
        converter = AnimationConverter()
        java_animation = {
            "animationId": "idle",
            "type": "controller",
            "length": 1.5,
            "loops": True,
        }
        animation = converter.convert_animation(java_animation)
        assert animation.identifier == "animation.idle"
        assert animation.length == 1.5
        assert animation.loops is True

    def test_convert_keyframe(self):
        """Test keyframe conversion."""
        converter = AnimationConverter()
        java_keyframe = {
            "time": 0.5,
            "rotation": [0, 45, 0],
            "position": [0, 1, 0],
            "scale": [1, 1, 1],
        }
        keyframe = converter.convert_keyframe(java_keyframe)
        assert keyframe["time"] == 0.5
        assert keyframe["rotation"] == [0, 45, 0]

    def test_convert_bone_animation(self):
        """Test bone animation conversion."""
        converter = AnimationConverter()
        frames = [
            {"time": 0.0, "rotation": [0, 0, 0]},
            {"time": 0.5, "rotation": [0, 45, 0]},
        ]
        bone_anim = converter.convert_bone_animation("arm", frames)
        assert len(bone_anim) == 2
        assert bone_anim[0]["time"] == 0.0

    def test_animation_controller_conversion(self):
        """Test animation controller conversion."""
        converter = AnimationConverter()
        java_controller = {
            "controllerId": "mob",
            "initialState": "idle",
            "states": {
                "idle": {
                    "animations": ["idle"],
                    "transitions": [{"to": "walk", "condition": "speed > 0"}],
                },
            },
        }
        controller = converter.convert_animation_controller(java_controller)
        assert controller.identifier == "animation_controller.mob"
        assert controller.initial_state == "idle"


class TestModelConversion:
    """Test cases for model conversion."""

    def test_model_type_enum(self):
        """Test ModelType enum values."""
        assert ModelType.BIPED.value == "biped"
        assert ModelType.QUADRUPED.value == "quadruped"
        assert ModelType.ARMORSMITH.value == "armorsmith"

    def test_convert_model_type(self):
        """Test model type conversion."""
        converter = RenderingConverter()
        assert converter.convert_model_type("biped") == ModelType.BIPED
        assert converter.convert_model_type("quadruped") == ModelType.QUADRUPED

    def test_convert_geometry_basic(self):
        """Test basic geometry conversion."""
        converter = RenderingConverter()
        java_model = {
            "modelId": "custom_zombie",
            "modelClass": "biped",
            "textureWidth": 64,
            "textureHeight": 64,
            "bones": [],
        }
        geometry = converter.convert_geometry(java_model)
        assert geometry.identifier == "geometry.custom_zombie"
        assert geometry.model_type == ModelType.BIPED

    def test_convert_geometry_with_bones(self):
        """Test geometry conversion with bone structure."""
        converter = RenderingConverter()
        java_model = {
            "modelId": "test_model",
            "modelClass": "biped",
            "bones": [
                {"name": "head", "pivot": [0, 24, 0]},
                {"name": "body", "pivot": [0, 12, 0]},
            ],
        }
        geometry = converter.convert_geometry(java_model)
        assert len(geometry.bones) == 2
        assert geometry.bones[0]["name"] == "head"


class TestTextureConversion:
    """Test cases for texture conversion."""

    def test_texture_type_enum(self):
        """Test TextureType enum values."""
        assert TextureType.COLOR.value == "color"
        assert TextureType.EMISSIVE.value == "emissive"
        assert TextureType.ARMOR.value == "armor"

    def test_convert_texture_mapping(self):
        """Test texture mapping conversion."""
        converter = RenderingConverter()
        java_texture = {
            "textureId": "zombie",
            "path": "textures/entity/zombie",
            "type": "color",
        }
        texture = converter.convert_texture_mapping(java_texture)
        assert texture.texture_id == "zombie"
        assert texture.texture_type == TextureType.COLOR

    def test_convert_texture_animated(self):
        """Test animated texture conversion."""
        converter = RenderingConverter()
        java_texture = {
            "textureId": "lava",
            "path": "textures/entity/lava",
            "type": "color",
            "animated": True,
            "frames": 32,
        }
        texture = converter.convert_texture_mapping(java_texture)
        assert texture.is_animated is True
        assert texture.animation_frames == 32


class TestRenderingPatterns:
    """Test cases for rendering patterns."""

    def test_pattern_library_initialization(self):
        """Test RenderingPatternLibrary initializes correctly."""
        lib = RenderingPatternLibrary()
        assert lib is not None
        assert len(lib.patterns) >= 20

    def test_search_by_java_model(self):
        """Test pattern search for model classes."""
        lib = RenderingPatternLibrary()
        patterns = lib.search_by_java("BipedModel")
        assert len(patterns) > 0
        assert patterns[0].java_rendering_class == "BipedModel"

    def test_search_by_java_animation(self):
        """Test pattern search for animation classes."""
        lib = RenderingPatternLibrary()
        patterns = lib.search_by_java("WalkAnimation")
        assert len(patterns) > 0

    def test_get_by_category(self):
        """Test pattern retrieval by category."""
        lib = RenderingPatternLibrary()
        model_patterns = lib.get_by_category(RenderingPatternCategory.MODEL)
        assert len(model_patterns) >= 6

    def test_pattern_stats(self):
        """Test pattern library statistics."""
        lib = RenderingPatternLibrary()
        stats = lib.get_stats()
        assert stats["total"] >= 20
        assert "model" in stats["by_category"]


class TestIntegration:
    """Integration tests for rendering conversion pipeline."""

    def test_full_render_controller_pipeline(self):
        """Test complete render controller conversion pipeline."""
        java_renderer = {
            "entityId": "custom_zombie",
            "modelClass": "biped",
            "texture": "textures/entity/custom_zombie",
            "textureType": "color",
        }
        json_output = generate_render_controller_file(java_renderer)
        assert "format_version" in json_output
        assert "render_controller" in json_output

    def test_full_animation_pipeline(self):
        """Test complete animation conversion pipeline."""
        java_animation = {
            "animationId": "walk",
            "type": "controller",
            "length": 1.0,
            "loops": True,
            "bones": {
                "left_leg": [
                    {"time": 0.0, "rotation": [-15, 0, 0]},
                    {"time": 0.5, "rotation": [15, 0, 0]},
                ]
            },
        }
        json_output = generate_animation_file(java_animation)
        assert "format_version" in json_output
        assert "animations" in json_output

    def test_model_to_geometry_pipeline(self):
        """Test model to geometry file generation."""
        java_model = {
            "modelId": "test_entity",
            "modelClass": "biped",
            "textureWidth": 64,
            "textureHeight": 64,
            "bones": [{"name": "root", "pivot": [0, 0, 0]}],
        }
        json_output = generate_geometry_file(java_model)
        assert "format_version" in json_output
        assert "minecraft:geometry" in json_output

    def test_pattern_lookup_in_conversion(self):
        """Test pattern lookup is used in conversion."""
        converter = RenderingConverter()
        pattern = get_rendering_pattern("BipedModel")
        assert pattern is not None
        assert "biped" in pattern.bedrock_render_id

    def test_animation_controller_pipeline(self):
        """Test animation controller file generation."""
        java_controller = {
            "controllerId": "mob_ai",
            "initialState": "idle",
            "states": {
                "idle": {
                    "animations": ["idle"],
                    "transitions": [{"to": "walk", "condition": "moving"}],
                },
                "walk": {
                    "animations": ["walk"],
                    "transitions": [{"to": "idle", "condition": "!moving"}],
                },
            },
        }
        json_output = generate_animation_controller_file(java_controller)
        assert "format_version" in json_output
        assert "animation_controllers" in json_output


class TestConvenienceFunctions:
    """Test convenience functions for rendering conversion."""

    def test_convert_render_controller_function(self):
        """Test convert_render_controller convenience function."""
        java_renderer = {"entityId": "test", "modelClass": "biped"}
        result = convert_render_controller(java_renderer)
        assert isinstance(result, RenderControllerDefinition)

    def test_convert_geometry_function(self):
        """Test convert_geometry convenience function."""
        java_model = {"modelId": "test", "modelClass": "biped"}
        result = convert_geometry(java_model)
        assert isinstance(result, GeometryDefinition)

    def test_convert_texture_function(self):
        """Test convert_texture convenience function."""
        java_texture = {"textureId": "test", "type": "color"}
        result = convert_texture(java_texture)
        assert isinstance(result, TextureMapping)

    def test_convert_animation_function(self):
        """Test convert_animation convenience function."""
        java_animation = {"animationId": "test"}
        result = convert_animation(java_animation)
        assert isinstance(result, AnimationDefinition)

    def test_convert_animation_controller_function(self):
        """Test convert_animation_controller convenience function."""
        java_controller = {"controllerId": "test"}
        result = convert_animation_controller(java_controller)
        assert isinstance(result, AnimationControllerDefinition)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
