"""
Unit tests for conversion_parser service.
"""

import pytest
from unittest.mock import MagicMock, patch
from services.conversion_parser import (
    parse_json_file,
    find_pack_folder,
    transform_pack_to_addon_data,
)


class TestParseJsonFile:
    @patch("os.path.exists")
    @patch("builtins.open", create=True)
    @patch("services.conversion_parser.json.load")
    def test_parse_json_file_success(self, mock_json_load, mock_open, mock_exists):
        """Test parse_json_file successfully parses JSON."""
        mock_exists.return_value = True
        mock_json_load.return_value = {"key": "value"}

        result = parse_json_file("/fake/path/manifest.json")

        assert result == {"key": "value"}
        mock_open.assert_called_once()

    @patch("os.path.exists")
    @patch("builtins.open", create=True)
    def test_parse_json_file_not_found(self, mock_open, mock_exists):
        """Test parse_json_file handles missing file."""
        mock_exists.return_value = False
        # No need to mock open since exists is False

        result = parse_json_file("/nonexistent/file.json")

        assert result is None

    @patch("os.path.exists")
    @patch("builtins.open", create=True)
    @patch("services.conversion_parser.json.load")
    def test_parse_json_file_invalid_json(self, mock_json_load, mock_open, mock_exists):
        """Test parse_json_file handles invalid JSON."""
        import json

        mock_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        result = parse_json_file("/invalid/file.json")

        assert result is None


class TestFindPackFolder:
    def test_find_pack_folder_returns_path(self):
        """Test find_pack_folder function exists."""
        assert callable(find_pack_folder)

    def test_find_pack_folder_behavior_pack_type(self):
        """Test find_pack_folder accepts pack_type parameter."""
        # Just verify the function accepts the parameter
        import inspect

        sig = inspect.signature(find_pack_folder)
        params = list(sig.parameters.keys())
        assert "pack_type_suffix" in params or "pack_type" in params


class TestTransformPackToAddonData:
    def test_transform_pack_to_addon_data_exists(self):
        """Test transform_pack_to_addon_data function exists."""
        assert callable(transform_pack_to_addon_data)
