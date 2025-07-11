from pathlib import Path
from PIL import Image
from src.agents.asset_converter import AssetConverterAgent
# Assuming conftest.py is in the same directory or a parent directory configured for pytest

# Helper function to get image dimensions directly for tests that might not open the image via agent
def get_image_dimensions(file_path: str) -> tuple[int, int]:
    with Image.open(file_path) as img:
        return img.size

def test_is_power_of_2(agent: AssetConverterAgent):
    assert agent._is_power_of_2(16)
    assert not agent._is_power_of_2(15)
    assert agent._is_power_of_2(1)
    assert not agent._is_power_of_2(0)
    assert not agent._is_power_of_2(-2)

def test_next_power_of_2(agent: AssetConverterAgent):
    assert agent._next_power_of_2(15) == 16
    assert agent._next_power_of_2(16) == 16
    assert agent._next_power_of_2(17) == 32
    assert agent._next_power_of_2(1) == 1

def test_previous_power_of_2(agent: AssetConverterAgent):
    assert agent._previous_power_of_2(17) == 16
    assert agent._previous_power_of_2(16) == 16
    assert agent._previous_power_of_2(31) == 16
    assert agent._previous_power_of_2(1) == 1
    assert agent._previous_power_of_2(0) == 1 # As per current implementation

def test_convert_single_texture_valid_png_no_resize(agent: AssetConverterAgent, dummy_16x16_png: str):
    result = agent._convert_single_texture(dummy_16x16_png, {}, "block")
    assert result["success"]
    assert result["original_path"] == dummy_16x16_png
    assert Path(result["converted_path"]).name == "dummy_16x16.png"
    assert "textures/blocks/" in result["converted_path"]
    assert result["original_dimensions"] == (16, 16)
    assert result["converted_dimensions"] == (16, 16)
    assert not result["resized"]
    assert "Converted to RGBA" in result["optimizations_applied"]
    assert result["bedrock_reference"] == "block_dummy_16x16"

def test_convert_single_texture_valid_png_resize_needed(agent: AssetConverterAgent, dummy_17x17_png: str):
    # Default behavior is must_be_power_of_2 = True
    original_dims = get_image_dimensions(dummy_17x17_png) # Should be (17,17)
    result = agent._convert_single_texture(dummy_17x17_png, {}, "block")

    assert result["success"]
    assert result["original_dimensions"] == original_dims
    assert result["resized"]
    # For 17x17, next_power_of_2 should be 32x32
    assert result["converted_dimensions"] == (32, 32)
    assert f"Resized from {original_dims} to {(32,32)}" in result["optimizations_applied"]

def test_convert_single_texture_exceeds_max_resolution(agent: AssetConverterAgent, dummy_2048x2048_png: str):
    # Temporarily modify agent's constraints for this test
    original_constraints = agent.texture_constraints.copy()
    agent.texture_constraints['max_resolution'] = 128
    agent.texture_constraints['must_be_power_of_2'] = True # Ensure PoT is also applied

    # The dummy_2048x2048_png is actually 256x256 from the fixture
    original_dims = get_image_dimensions(dummy_2048x2048_png) # (256,256)

    result = agent._convert_single_texture(dummy_2048x2048_png, {}, "block")
    agent.texture_constraints = original_constraints # Restore constraints

    assert result["success"]
    assert result["original_dimensions"] == original_dims # (256,256)
    assert result["resized"]
    # It was 256x256. _next_power_of_2(256) is 256.
    # Then capped at max_res 128.
    # Then _previous_power_of_2(128) is 128.
    assert result["converted_dimensions"] == (128, 128)
    assert f"Resized from {original_dims} to {(128,128)}" in result["optimizations_applied"]


def test_convert_single_texture_animated_mcmeta(agent: AssetConverterAgent, dummy_animated_png_with_mcmeta: str):
    result = agent._convert_single_texture(dummy_animated_png_with_mcmeta, {}, "block")
    assert result["success"]
    assert result["animation_data"] is not None
    assert result["animation_data"]["frametime"] == 5
    assert result["animation_data"]["frames"] == [0, 1, 2]
    assert "Parsed .mcmeta animation data" in result["optimizations_applied"]

def test_convert_single_texture_file_not_found(agent: AssetConverterAgent):
    result = agent._convert_single_texture("non_existent_path.png", {}, "block")
    assert not result["success"]
    assert "error" in result
    assert "Texture file not found" in result["error"]

def test_generate_texture_pack_structure(agent: AssetConverterAgent):
    textures_data = [
        {
            'success': True, 'original_path': 'path/to/stone.png',
            'converted_path': 'textures/blocks/stone.png',
            'bedrock_reference': 'block_stone', 'animation_data': None,
            'original_dimensions': (16,16), 'converted_dimensions': (16,16), 'format': 'png', 'resized': False,
            'optimizations_applied': ['Converted to RGBA']
        },
        {
            'success': True, 'original_path': 'path/to/animated_lava.png',
            'converted_path': 'textures/blocks/animated_lava.png',
            'bedrock_reference': 'block_animated_lava',
            'animation_data': {"frametime": 2, "frames": [0,1,2,3], "interpolate": True},
            'original_dimensions': (16,64), 'converted_dimensions': (16,64), 'format': 'png', 'resized': False,
            'optimizations_applied': ['Converted to RGBA', 'Parsed .mcmeta animation data']
        },
        {
            'success': True, 'original_path': 'path/to/apple.png',
            'converted_path': 'textures/items/apple.png',
            'bedrock_reference': 'item_apple', 'animation_data': None,
            'original_dimensions': (16,16), 'converted_dimensions': (16,16), 'format': 'png', 'resized': False,
            'optimizations_applied': ['Converted to RGBA']
        },
        {'success': False, 'original_path': 'path/to/bad.png', 'error': 'some error'}
    ]

    structure = agent._generate_texture_pack_structure(textures_data)

    assert "pack_manifest.json" in structure
    assert "terrain_texture.json" in structure
    assert "item_texture.json" in structure
    assert "flipbook_textures.json" in structure

    manifest = structure["pack_manifest.json"]
    assert manifest["format_version"] == 2

    terrain_textures = structure["terrain_texture.json"]["texture_data"]
    assert "block_stone" in terrain_textures
    assert terrain_textures["block_stone"]["textures"] == "textures/blocks/stone.png"
    assert "block_animated_lava" in terrain_textures

    item_textures = structure["item_texture.json"]["texture_data"]
    assert "item_apple" in item_textures
    assert item_textures["item_apple"]["textures"] == "textures/items/apple.png"

    flipbooks = structure["flipbook_textures.json"]
    assert len(flipbooks) == 1
    lava_flipbook = flipbooks[0]
    assert lava_flipbook["flipbook_texture"] == "textures/blocks/animated_lava.png"
    assert lava_flipbook["atlas_tile"] == "animated_lava"
    assert lava_flipbook["ticks_per_frame"] == 2
    assert lava_flipbook["frames"] == [0,1,2,3]
    assert lava_flipbook["interpolate"]
