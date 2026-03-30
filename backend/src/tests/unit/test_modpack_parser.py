import pytest
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from services.modpack_parser import CurseForgeModpackParser, ModpackFile, CurseForgeManifest

@pytest.fixture
def parser():
    return CurseForgeModpackParser()

def test_parse_manifest_data_valid(parser):
    data = {
        "manifestType": "minecraftModpack",
        "manifestVersion": 1,
        "name": "Test Pack",
        "version": "1.0.0",
        "author": "Author",
        "files": [
            {"projectID": 1234, "fileID": 5678, "required": True}
        ],
        "gameVersion": "1.20.1"
    }
    result = parser._parse_manifest_data(data)
    assert result.manifest.name == "Test Pack"
    assert len(result.manifest.files) == 1
    assert result.manifest.files[0].project_id == 1234
    assert result.game_version == "1.20.1"

def test_parse_manifest_data_invalid_type(parser):
    data = {
        "manifestType": "invalidType",
        "manifestVersion": 1
    }
    with pytest.raises(ValueError, match="Unsupported manifest type"):
        parser._parse_manifest_data(data)

def test_parse_from_manifest(parser):
    data = {
        "manifestType": "minecraftModpack",
        "manifestVersion": 1,
        "name": "Test Pack"
    }
    m = mock_open(read_data=json.dumps(data))
    with patch("builtins.open", m):
        result = parser._parse_from_manifest(Path("manifest.json"))
        assert result.manifest.name == "Test Pack"

def test_parse_from_url_modpack(parser):
    url = "https://www.curseforge.com/minecraft/modpacks/test-pack"
    result = parser.parse_from_url(url)
    assert result["platform"] == "curseforge"
    assert result["type"] == "modpack"
    assert result["slug"] == "test-pack"

def test_parse_from_url_mod(parser):
    url = "https://www.curseforge.com/minecraft/mc-mods/test-mod"
    result = parser.parse_from_url(url)
    assert result["platform"] == "curseforge"
    assert result["type"] == "mod"
    assert result["slug"] == "test-mod"

def test_curseforge_manifest_properties():
    files = [
        ModpackFile(project_id=1, file_id=10, required=True),
        ModpackFile(project_id=2, file_id=20, required=False)
    ]
    manifest = CurseForgeManifest(
        manifest_type="test", manifest_version=1, name="Test", version="1", author="A",
        files=files
    )
    assert manifest.mod_count == 2
    assert manifest.required_mod_count == 1
