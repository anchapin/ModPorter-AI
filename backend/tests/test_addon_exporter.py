import uuid
import zipfile
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock

import pytest

from src.models import addon_models
from src.services import addon_exporter


@pytest.fixture
def mock_addon_details():
    addon_id = uuid.uuid4()
    return addon_models.AddonDetails(
        id=addon_id,
        name="Test Addon",
        description="A test addon.",
        user_id="test-user",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        blocks=[
            addon_models.AddonBlock(
                id=uuid.uuid4(),
                addon_id=addon_id,
                identifier="test:my_block",
                properties={"luminance": 8, "rp_texture_name": "my_block_tex"},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                behavior=None,
            )
        ],
        assets=[
            addon_models.AddonAsset(
                id=uuid.uuid4(),
                addon_id=addon_id,
                type="texture_block",
                path="test_asset.png",
                original_filename="my_block_tex.png",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ],
        recipes=[
            addon_models.AddonRecipe(
                id=uuid.uuid4(),
                addon_id=addon_id,
                data={
                    "format_version": "1.12.0",
                    "minecraft:recipe_shaped": {
                        "description": {"identifier": "test:my_recipe"}
                    },
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ],
    )


def test_generate_bp_manifest(mock_addon_details):
    module_uuid = str(uuid.uuid4())
    header_uuid = str(uuid.uuid4())
    manifest = addon_exporter.generate_bp_manifest(
        mock_addon_details, module_uuid, header_uuid
    )

    assert manifest["format_version"] == 2
    assert manifest["header"]["name"] == "Test Addon Behavior Pack"
    assert manifest["header"]["uuid"] == header_uuid
    assert manifest["modules"][0]["uuid"] == module_uuid


def test_generate_rp_manifest(mock_addon_details):
    module_uuid = str(uuid.uuid4())
    header_uuid = str(uuid.uuid4())
    manifest = addon_exporter.generate_rp_manifest(
        mock_addon_details, module_uuid, header_uuid
    )

    assert manifest["format_version"] == 2
    assert manifest["header"]["name"] == "Test Addon Resource Pack"
    assert manifest["header"]["uuid"] == header_uuid
    assert manifest["modules"][0]["uuid"] == module_uuid


def test_generate_block_behavior_json(mock_addon_details):
    block = mock_addon_details.blocks[0]
    behavior_json = addon_exporter.generate_block_behavior_json(block)

    assert (
        behavior_json["minecraft:block"]["description"]["identifier"] == "test:my_block"
    )
    assert (
        behavior_json["minecraft:block"]["components"]["minecraft:block_light_emission"]
        == 8
    )


def test_generate_rp_block_definitions_json(mock_addon_details):
    blocks_json = addon_exporter.generate_rp_block_definitions_json(
        mock_addon_details.blocks
    )
    assert "test:my_block" in blocks_json
    assert blocks_json["test:my_block"]["textures"] == "my_block_tex"


def test_generate_terrain_texture_json(mock_addon_details):
    terrain_texture_json = addon_exporter.generate_terrain_texture_json(
        mock_addon_details.assets
    )
    assert "my_block_tex" in terrain_texture_json["texture_data"]
    assert (
        terrain_texture_json["texture_data"]["my_block_tex"]["textures"]
        == "textures/blocks/my_block_tex"
    )


def test_generate_recipe_json(mock_addon_details):
    recipe = mock_addon_details.recipes[0]
    recipe_json = addon_exporter.generate_recipe_json(recipe)
    assert recipe_json["format_version"] == "1.12.0"


def test_create_mcaddon_zip(mock_addon_details, monkeypatch):
    # Mock os.path.exists to always return True
    monkeypatch.setattr("os.path.exists", lambda path: True)
    # Mock open to avoid real file I/O
    monkeypatch.setattr("builtins.open", MagicMock())

    zip_buffer = addon_exporter.create_mcaddon_zip(
        mock_addon_details, "/fake/base/path"
    )

    assert isinstance(zip_buffer, BytesIO)
    zip_buffer.seek(0)
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        zip_files = zf.namelist()
        assert "Test_Addon_BP/manifest.json" in zip_files
        assert "Test_Addon_RP/manifest.json" in zip_files
        assert "Test_Addon_BP/blocks/my_block.json" in zip_files
        assert "Test_Addon_RP/blocks.json" in zip_files
        assert "Test_Addon_RP/textures/terrain_texture.json" in zip_files
        assert "Test_Addon_BP/recipes/my_recipe.json" in zip_files
