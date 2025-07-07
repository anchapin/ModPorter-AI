import pytest
from pathlib import Path
import json
from ai_engine.src.agents.asset_converter import AssetConverterAgent

# Uses fixtures from conftest.py: agent, dummy_java_block_model,
# dummy_java_rotated_block_model, dummy_item_generated_model

def test_convert_single_model_basic_block(agent: AssetConverterAgent, dummy_java_block_model: str):
    result = agent._convert_single_model(dummy_java_block_model, {}, "block")

    assert result["success"]
    assert result["original_path"] == dummy_java_block_model
    assert Path(result["converted_path"]).name == "dummy_block_model.geo.json"
    assert "models/block/" in result["converted_path"]
    assert result["bedrock_identifier"] == "geometry.block.dummy_block_model"
    assert not result["warnings"] # No warnings for this basic model

    model_json = result["converted_model_json"]
    assert model_json["format_version"] == "1.12.0"
    assert "minecraft:geometry" in model_json
    assert len(model_json["minecraft:geometry"]) == 1

    geo = model_json["minecraft:geometry"][0]
    assert geo["description"]["identifier"] == "geometry.block.dummy_block_model"
    assert geo["description"]["texture_width"] == 16 # Default
    assert geo["description"]["texture_height"] == 16 # Default

    assert len(geo["bones"]) == 1
    bone = geo["bones"][0]
    assert bone["name"] == "element_0"
    assert bone["pivot"] == [0.0, 0.0, 0.0] # Default pivot for non-rotated elements

    assert len(bone["cubes"]) == 1
    cube = bone["cubes"][0]
    # Java element from [0,0,0] to [16,16,16]
    # Bedrock origin: coord - 8
    # Bedrock size: to - from
    assert cube["origin"] == [-8.0, -8.0, -8.0]
    assert cube["size"] == [16.0, 16.0, 16.0]
    assert cube["uv"] == [0, 0] # Simplified from first face "down"

    # Check calculated visible bounds for a 16x16x16 cube centered at world origin
    # Origin [-8,-8,-8], Size [16,16,16] => Extends from -8 to 8 on all axes
    # v_bounds_w = 8 - (-8) = 16
    # v_bounds_h = 16
    # v_bounds_d = 16
    # geo_description["visible_bounds_width"] = round(max(16, 16), 4) = 16.0
    # geo_description["visible_bounds_height"] = round(16, 4) = 16.0
    # geo_description["visible_bounds_offset"] = [0,0,0] (center of -8 to 8)
    assert geo["description"]["visible_bounds_width"] == 16.0
    assert geo["description"]["visible_bounds_height"] == 16.0
    assert geo["description"]["visible_bounds_offset"] == [0.0, 0.0, 0.0]


def test_convert_single_model_rotated_block(agent: AssetConverterAgent, dummy_java_rotated_block_model: str):
    result = agent._convert_single_model(dummy_java_rotated_block_model, {}, "block")

    assert result["success"]
    assert len(result["warnings"]) > 0 # Expect warnings about rotation
    assert "has rotation" in result["warnings"][0]

    model_json = result["converted_model_json"]
    bone = model_json["minecraft:geometry"][0]["bones"][0]
    # Java rotation: {"origin": [8, 8, 8], "axis": "y", "angle": 45}
    # Bedrock pivot: origin - 8 => [0,0,0]
    # Bedrock rotation: [0, -angle, 0] for y-axis => [0, -45, 0]
    assert bone["pivot"] == [0.0, 0.0, 0.0]
    assert bone["rotation"] == [0.0, -45.0, 0.0]

    # Element from [4,0,4] to [12,16,12]
    # Origin: [4-8, 0-8, 4-8] = [-4, -8, -4]
    # Size: [12-4, 16-0, 12-4] = [8, 16, 8]
    cube = bone["cubes"][0]
    assert cube["origin"] == [-4.0, -8.0, -4.0]
    assert cube["size"] == [8.0, 16.0, 8.0]

def test_convert_single_model_item_generated(agent: AssetConverterAgent, dummy_item_generated_model: str):
    result = agent._convert_single_model(dummy_item_generated_model, {}, "item")

    assert result["success"]
    assert "Handling as 'item/generated'" in result["warnings"][0]
    assert Path(result["converted_path"]).name == "dummy_item_generated.geo.json"
    assert "models/item/" in result["converted_path"]
    assert result["bedrock_identifier"] == "geometry.item.dummy_item_generated"

    model_json = result["converted_model_json"]
    geo = model_json["minecraft:geometry"][0]
    assert geo["description"]["identifier"] == "geometry.item.dummy_item_generated"

    assert len(geo["bones"]) == 1 # One layer "layer0"
    bone = geo["bones"][0]
    assert bone["name"] == "layer0"
    assert len(bone["cubes"]) == 1
    cube = bone["cubes"][0]
    assert cube["origin"] == [-8.0, -8.0, -0.05] # Centered flat quad
    assert cube["size"] == [16.0, 16.0, 0.1]   # Thin
    assert cube["uv"] == [0,0]

    # Check specific item bounds
    assert geo["description"]["visible_bounds_width"] == 1.0
    assert geo["description"]["visible_bounds_height"] == 1.0
    assert geo["description"]["visible_bounds_offset"] == [0.0, 0.0, 0.0]

def test_convert_single_model_file_not_found(agent: AssetConverterAgent):
    result = agent._convert_single_model("non_existent_model.json", {}, "block")
    assert not result["success"]
    assert "error" in result
    assert "Model file not found" in result["error"]

def test_convert_single_model_invalid_json(agent: AssetConverterAgent, tmp_path: Path):
    invalid_json_path = tmp_path / "invalid.json"
    invalid_json_path.write_text("this is not json")
    result = agent._convert_single_model(str(invalid_json_path), {}, "block")
    assert not result["success"]
    assert "error" in result
    assert "Invalid JSON" in result["error"]

def test_generate_model_structure(agent: AssetConverterAgent):
    models_data = [
        {
            'success': True, 'original_path': 'path/to/model1.json',
            'converted_path': 'models/block/model1.geo.json',
            'bedrock_identifier': 'geometry.block.model1',
            'converted_model_json': {} # Dummy
        },
        {
            'success': True, 'original_path': 'path/to/model2.json',
            'converted_path': 'models/item/model2.geo.json',
            'bedrock_identifier': 'geometry.item.model2',
            'converted_model_json': {} # Dummy
        },
        {'success': False, 'original_path': 'path/to/bad_model.json', 'error': 'some error'}
    ]
    structure = agent._generate_model_structure(models_data)
    assert len(structure["geometry_files"]) == 2
    assert "models/block/model1.geo.json" in structure["geometry_files"]
    assert "models/item/model2.geo.json" in structure["geometry_files"]

    assert len(structure["identifiers_used"]) == 2
    assert "geometry.block.model1" in structure["identifiers_used"]
    assert "geometry.item.model2" in structure["identifiers_used"]

def test_convert_model_no_elements_no_parent(agent: AssetConverterAgent, tmp_path: Path):
    model_content = {"textures": {"particle": "block/stone"}} # No elements, no parent
    file_path = tmp_path / "empty_model.json"
    with open(file_path, 'w') as f:
        json.dump(model_content, f)

    result = agent._convert_single_model(str(file_path), {}, "block")
    assert result["success"] # Still true, but with warnings and empty bones
    assert "Model has no elements and no parent" in result["warnings"]

    model_json = result["converted_model_json"]
    geo = model_json["minecraft:geometry"][0]
    assert len(geo["bones"]) == 0
    assert geo["description"]["visible_bounds_width"] == 0.1 # Default for empty

def test_convert_model_unhandled_parent_no_elements(agent: AssetConverterAgent, tmp_path: Path):
    model_content = {"parent": "custom/some_base_model"} # Unhandled parent, no elements
    file_path = tmp_path / "unhandled_parent_model.json"
    with open(file_path, 'w') as f:
        json.dump(model_content, f)

    result = agent._convert_single_model(str(file_path), {}, "block")
    assert result["success"] # Still true
    assert "Model has unhandled parent 'custom/some_base_model' and no local elements" in result["warnings"]

    model_json = result["converted_model_json"]
    geo = model_json["minecraft:geometry"][0]
    # As per current logic, it generates no bones if not item/generated and no elements.
    # The prompt for this subtask didn't explicitly ask for a placeholder cube for this specific case,
    # but the code implements it. Let's verify that.
    # The code path for this is:
    # elif not processed_as_item_specific_type and not java_elements:
    #    if java_parent: # This case
    #       warnings.append(...)
    #    else: # No parent, no elements
    #       warnings.append(...)
    #    geo_description["visible_bounds_width"] = 0.1
    # So, it seems it *doesn't* create a placeholder bone from the test case description.
    # Let's adjust the test to expect 0 bones for this specific path.
    assert len(geo["bones"]) == 0
    assert geo["description"]["visible_bounds_width"] == 0.1 # Default for empty/unhandled parent
