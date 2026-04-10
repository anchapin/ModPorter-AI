"""
Standalone unit tests for model conversion functionality (without CrewAI dependency)
"""

import os
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents import model_converter


class MockAgent:
    """Mock agent for testing"""

    def __init__(self):
        self.model_constraints = {
            "max_vertices": 3000,
            "max_textures": 8,
            "supported_bones": 60,
        }
        self.model_formats = {
            "input": [".obj", ".fbx", ".json"],
            "output": ".geo.json",
        }


def test_parse_blockstate_variants():
    """Test parsing blockstate with variants format"""
    blockstate = {
        "variants": {
            "facing=north,powered=false": {"model": "mod:block/machine_off"},
            "facing=north,powered=true": {"model": "mod:block/machine_on", "y": 90},
            "facing=east,powered=false": {"model": "mod:block/machine_off", "y": 90},
            "facing=east,powered=true": {"model": "mod:block/machine_on", "y": 180},
        }
    }

    result = model_converter.parse_blockstate(blockstate)

    assert result["has_variants"] == True
    assert result["has_multipart"] == False
    assert result["variant_count"] == 4
    assert len(result["variants"]) == 4

    assert result["variants"][0]["model"] == "mod:block/machine_off"
    assert result["variants"][0]["y_rotation"] == 0
    assert result["variants"][1]["model"] == "mod:block/machine_on"
    assert result["variants"][1]["y_rotation"] == 90

    print("✓ test_parse_blockstate_variants passed")


def test_parse_blockstate_multipart():
    """Test parsing blockstate with multipart format"""
    blockstate = {
        "multipart": [
            {"when": {"powered": False}, "apply": {"model": "mod:block/lever_off"}},
            {"when": {"powered": True}, "apply": {"model": "mod:block/lever_on", "y": 180}},
        ]
    }

    result = model_converter.parse_blockstate(blockstate)

    assert result["has_variants"] == False
    assert result["has_multipart"] == True
    assert result["variant_count"] == 2

    print("✓ test_parse_blockstate_multipart passed")


def test_resolve_parent_model_direct_elements():
    """Test resolving a model that has direct elements"""
    model = {
        "parent": "block/cube_all",
        "elements": [
            {
                "name": "cube",
                "from": [0, 0, 0],
                "to": [16, 16, 16],
                "faces": {"north": {"uv": [0, 0, 16, 16], "texture": "#all"}},
            }
        ],
    }

    model_cache = {
        "assets/mod/models/block/cube_all": {
            "elements": [
                {
                    "name": "base_cube",
                    "from": [0, 0, 0],
                    "to": [16, 16, 16],
                    "faces": {"north": {"uv": [0, 0, 16, 16], "texture": "#all"}},
                }
            ]
        }
    }

    elements, warnings = model_converter.resolve_parent_model(model, model_cache, "mod")

    assert len(elements) == 1
    assert elements[0]["name"] == "cube"

    print("✓ test_resolve_parent_model_direct_elements passed")


def test_resolve_parent_model_inheritance():
    """Test resolving a model that inherits from parent"""
    parent_model = {
        "elements": [
            {
                "name": "parent_cube",
                "from": [0, 0, 0],
                "to": [16, 16, 16],
                "faces": {"north": {"uv": [0, 0, 16, 16], "texture": "#all"}},
            }
        ],
    }

    child_model = {
        "parent": "mod:block/parent_model",
        "textures": {"all": "mod:block/test"},
    }

    model_cache = {
        "assets/mod/models/block/parent_model": parent_model,
        "assets/mod/models/block/child_model": child_model,
    }

    elements, warnings = model_converter.resolve_parent_model(child_model, model_cache, "mod")

    assert len(elements) == 1
    assert elements[0]["name"] == "parent_cube"

    print("✓ test_resolve_parent_model_inheritance passed")


def test_resolve_parent_model_no_parent():
    """Test resolving a model with no parent and no elements"""
    model = {
        "textures": {"all": "mod:block/test"},
    }

    model_cache = {}

    elements, warnings = model_converter.resolve_parent_model(model, model_cache)

    assert len(elements) == 0
    assert len(warnings) > 0

    print("✓ test_resolve_parent_model_no_parent passed")


def test_convert_single_model_with_elements():
    """Test converting a model with direct elements"""
    agent = MockAgent()

    model_data = {
        "parent": "block/cube_all",
        "elements": [
            {
                "name": "test_cube",
                "from": [0, 0, 0],
                "to": [16, 16, 16],
                "faces": {
                    "north": {"uv": [0, 0, 16, 16], "texture": "#all"},
                    "up": {"uv": [0, 0, 16, 16], "texture": "#all"},
                    "east": {"uv": [0, 0, 16, 16], "texture": "#all"},
                    "south": {"uv": [0, 0, 16, 16], "texture": "#all"},
                    "west": {"uv": [0, 0, 16, 16], "texture": "#all"},
                    "down": {"uv": [0, 0, 16, 16], "texture": "#all"},
                },
            }
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(model_data, f)
        temp_path = f.name

    try:
        result = model_converter._convert_single_model(agent, temp_path, {}, "block")

        assert result["success"] == True
        assert "converted_model_json" in result
        assert len(result["converted_model_json"]["minecraft:geometry"][0]["bones"]) == 1

        print("✓ test_convert_single_model_with_elements passed")
    finally:
        os.unlink(temp_path)


def test_convert_single_model_item_generated():
    """Test converting an item model with layer textures"""
    agent = MockAgent()

    model_data = {
        "parent": "item/generated",
        "textures": {"layer0": "mod:item/test_item"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(model_data, f)
        temp_path = f.name

    try:
        result = model_converter._convert_single_model(agent, temp_path, {}, "item")

        assert result["success"] == True
        assert len(result["warnings"]) > 0
        assert "layer0" in result["warnings"][0] or "Handling" in result["warnings"][0]

        print("✓ test_convert_single_model_item_generated passed")
    finally:
        os.unlink(temp_path)


def test_resolve_parent_path():
    """Test resolving parent model paths"""
    assert (
        model_converter._resolve_parent_path("minecraft:block/cube_all")
        == "assets/minecraft/models/block/cube_all"
    )

    assert (
        model_converter._resolve_parent_path("mod:block/custom", "other_namespace")
        == "assets/mod/models/block/custom"
    )

    assert (
        model_converter._resolve_parent_path("block/cube", "mymod")
        == "assets/mymod/models/block/cube"
    )

    assert (
        model_converter._resolve_parent_path("block/cube") == "assets/minecraft/models/block/cube"
    )

    print("✓ test_resolve_parent_path passed")


if __name__ == "__main__":
    test_parse_blockstate_variants()
    test_parse_blockstate_multipart()
    test_resolve_parent_model_direct_elements()
    test_resolve_parent_model_inheritance()
    test_resolve_parent_model_no_parent()
    test_convert_single_model_with_elements()
    test_convert_single_model_item_generated()
    test_resolve_parent_path()

    print("\n✅ All model conversion tests passed!")
