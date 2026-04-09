"""
Comprehensive unit tests for conversion_parser service to improve test coverage.
"""

import os
import json
import uuid
import pytest
from unittest.mock import MagicMock, patch, mock_open
from services.conversion_parser import (
    parse_json_file,
    find_pack_folder,
    transform_pack_to_addon_data,
    DEFAULT_USER_ID,
)


class TestParseJsonFile:
    @patch("os.path.exists")
    def test_parse_json_file_success(self, mock_exists):
        """Test parse_json_file successfully parses valid JSON."""
        mock_exists.return_value = True
        data = {"key": "value"}
        with patch("builtins.open", mock_open(read_data=json.dumps(data))):
            result = parse_json_file("/fake/path.json")
            assert result == data

    @patch("os.path.exists")
    def test_parse_json_file_not_found(self, mock_exists):
        """Test parse_json_file returns None for missing file."""
        mock_exists.return_value = False
        result = parse_json_file("/nonexistent/path.json")
        assert result is None

    @patch("os.path.exists")
    def test_parse_json_file_invalid_json(self, mock_exists):
        """Test parse_json_file returns None for invalid JSON."""
        mock_exists.return_value = True
        with patch("builtins.open", mock_open(read_data="invalid json")):
            result = parse_json_file("/invalid/path.json")
            assert result is None


class TestFindPackFolder:
    @patch("os.listdir")
    @patch("os.path.isdir")
    @patch("os.path.exists")
    def test_find_pack_folder_success(self, mock_exists, mock_isdir, mock_listdir):
        """Test find_pack_folder finds a pack folder by suffix."""
        mock_listdir.return_value = ["my_pack_BP", "other_folder"]
        mock_isdir.side_effect = lambda p: p.endswith("my_pack_BP")
        # For manifest.json existence check
        mock_exists.side_effect = lambda p: p.endswith("manifest.json")

        result = find_pack_folder("/root", "BP")
        assert result == "/root/my_pack_BP"

    @patch("os.listdir")
    @patch("os.path.exists")
    def test_find_pack_folder_fallback_to_root(self, mock_exists, mock_listdir):
        """Test find_pack_folder falls back to root if manifest.json exists there."""
        mock_listdir.return_value = ["some_file.txt"]
        # manifest.json exists in root but not in any subfolder
        mock_exists.side_effect = lambda p: p == "/root/manifest.json"

        result = find_pack_folder("/root", "BP")
        assert result == "/root"

    @patch("os.listdir")
    @patch("os.path.exists")
    def test_find_pack_folder_not_found(self, mock_exists, mock_listdir):
        """Test find_pack_folder returns None if no pack folder or manifest in root."""
        mock_listdir.return_value = ["some_file.txt"]
        mock_exists.return_value = False

        result = find_pack_folder("/root", "BP")
        assert result is None


class TestTransformPackToAddonData:
    @pytest.fixture
    def mock_uuid(self):
        return uuid.uuid4()

    @patch("services.conversion_parser.find_pack_folder")
    @patch("services.conversion_parser.parse_json_file")
    @patch("os.path.isdir")
    @patch("os.listdir")
    @patch("os.walk")
    def test_transform_success_full(
        self, mock_walk, mock_listdir, mock_isdir, mock_parse_json, mock_find_folder, mock_uuid
    ):
        """Test transform_pack_to_addon_data with both BP and RP."""
        # Setup find_pack_folder
        mock_find_folder.side_effect = lambda root, suffix: f"{root}/{suffix}"

        # Mock manifest files
        bp_manifest = {"header": {"name": "My Cool BP", "description": "Awesome description"}}
        rp_manifest = {"header": {"name": "My Cool RP", "description": "RP description"}}

        def parse_json_side_effect(path):
            if "BP/manifest.json" in path:
                return bp_manifest
            if "RP/manifest.json" in path:
                return rp_manifest
            if "blocks/custom_block.json" in path:
                return {
                    "minecraft:block": {
                        "description": {"identifier": "custom:block", "is_experimental": True},
                        "components": {"minecraft:luminance": 15},
                    }
                }
            if "recipes/my_recipe.json" in path:
                return {"minecraft:recipe_shaped": {"description": {"identifier": "custom:recipe"}}}
            return None

        mock_parse_json.side_effect = parse_json_side_effect

        # Mock BP directory structure for blocks and recipes
        mock_isdir.side_effect = lambda p: (
            p.endswith("BP/blocks") or p.endswith("BP/recipes") or p.endswith("RP/textures")
        )
        mock_listdir.side_effect = lambda p: (
            ["custom_block.json"]
            if p.endswith("blocks")
            else (["my_recipe.json"] if p.endswith("recipes") else [])
        )

        # Mock RP walk for textures
        mock_walk.return_value = [
            ("/root/RP/textures/blocks", [], ["texture1.png"]),
            ("/root/RP/textures/items", [], ["item1.jpg"]),
        ]

        addon_id = mock_uuid
        addon_data, assets_info = transform_pack_to_addon_data("/root", "Fallback", addon_id)

        assert addon_data.name == "My Cool"  # ".replace(' BP', '')"
        assert addon_data.description == "Awesome description"
        assert len(addon_data.blocks) == 1
        assert addon_data.blocks[0].identifier == "custom:block"
        assert addon_data.blocks[0].properties["is_experimental"] is True
        assert addon_data.blocks[0].behavior.data["minecraft:luminance"] == 15
        assert len(addon_data.recipes) == 1

        assert len(assets_info) == 2
        assert any(
            a["type"] == "texture_block" and a["original_filename"] == "texture1.png"
            for a in assets_info
        )
        assert any(
            a["type"] == "texture_item" and a["original_filename"] == "item1.jpg"
            for a in assets_info
        )

    @patch("services.conversion_parser.find_pack_folder")
    @patch("services.conversion_parser.parse_json_file")
    def test_transform_rp_only(self, mock_parse_json, mock_find_folder, mock_uuid):
        """Test transform_pack_to_addon_data when only RP is found."""
        mock_find_folder.side_effect = lambda root, suffix: (
            f"{root}/{suffix}" if suffix == "RP" else None
        )

        rp_manifest = {
            "header": {"name": "My Pack Resource Pack", "description": "RP only description"}
        }
        mock_parse_json.return_value = rp_manifest

        with patch("os.path.isdir", return_value=False):  # No subfolders in RP for this test
            addon_data, _ = transform_pack_to_addon_data("/root", "Fallback", mock_uuid)

            assert addon_data.name == "My Pack"  # ".replace(' Resource Pack', '')"
            assert addon_data.description == "RP only description"

    @patch("services.conversion_parser.find_pack_folder")
    def test_transform_nothing_found(self, mock_find_folder, mock_uuid):
        """Test transform_pack_to_addon_data when no BP or RP found."""
        mock_find_folder.return_value = None

        addon_data, assets_info = transform_pack_to_addon_data(
            "/root", "Fallback", mock_uuid, user_id="test_user"
        )

        assert addon_data.name == "Fallback"
        assert addon_data.description == "Converted addon."
        assert addon_data.user_id == "test_user"
        assert len(addon_data.blocks) == 0
        assert len(addon_data.recipes) == 0
        assert len(assets_info) == 0

    @patch("services.conversion_parser.find_pack_folder")
    @patch("services.conversion_parser.parse_json_file")
    @patch("os.path.isdir")
    @patch("os.listdir")
    def test_transform_block_missing_identifier(
        self, mock_listdir, mock_isdir, mock_parse_json, mock_find_folder, mock_uuid
    ):
        """Test transform skip block if it missing identifier."""
        mock_find_folder.side_effect = lambda root, suffix: (
            f"{root}/{suffix}" if suffix == "BP" else None
        )
        mock_parse_json.side_effect = [
            {"header": {"name": "Test"}},  # BP manifest
            {"minecraft:block": {"components": {}}},  # Block without identifier
        ]
        mock_isdir.return_value = True
        mock_listdir.side_effect = lambda p: ["bad_block.json"] if p.endswith("blocks") else []

        addon_data, _ = transform_pack_to_addon_data("/root", "Fallback", mock_uuid)
        assert len(addon_data.blocks) == 0

    @patch("services.conversion_parser.find_pack_folder")
    @patch("services.conversion_parser.parse_json_file")
    @patch("os.path.isdir")
    @patch("os.listdir")
    def test_transform_block_missing_minecraft_block(
        self, mock_listdir, mock_isdir, mock_parse_json, mock_find_folder, mock_uuid
    ):
        """Test transform skip block if it missing 'minecraft:block' key."""
        mock_find_folder.side_effect = lambda root, suffix: (
            f"{root}/{suffix}" if suffix == "BP" else None
        )
        mock_parse_json.side_effect = [
            {"header": {"name": "Test"}},  # BP manifest
            {"bad_key": {}},  # Not a block file
        ]
        mock_isdir.return_value = True
        mock_listdir.side_effect = lambda p: ["not_a_block.json"] if p.endswith("blocks") else []

        addon_data, _ = transform_pack_to_addon_data("/root", "Fallback", mock_uuid)
        assert len(addon_data.blocks) == 0
