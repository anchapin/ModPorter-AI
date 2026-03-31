import pytest
import json
import zipfile
import io
from pathlib import Path
from unittest.mock import MagicMock, patch
from services.modpack_parser import ModrinthModpackParser, ParsedModpack

@pytest.fixture
def parser():
    return ModrinthModpackParser()

@pytest.fixture
def mock_mrpack_path(tmp_path):
    mrpack_path = tmp_path / "test.mrpack"
    
    # Create a mock .mrpack file (ZIP)
    with zipfile.ZipFile(mrpack_path, "w") as zf:
        index_data = {
            "name": "Test Modrinth Pack",
            "version": "1.0.0",
            "game": "minecraft",
            "gameVersion": "1.20.1",
            "author": "Test Author",
            "files": [
                {
                    "path": "mods/test-mod.jar",
                    "hashes": {"sha1": "abc"},
                    "env": {"client": "required", "server": "required"},
                    "projectID": 123,
                    "fileID": 456
                }
            ]
        }
        zf.writestr("modrinth.index.json", json.dumps(index_data))
    
    return mrpack_path

def test_modrinth_parser_init(parser):
    assert parser is not None

def test_parse_from_file_not_found(parser):
    with pytest.raises(FileNotFoundError):
        parser.parse_from_file(Path("nonexistent.mrpack"))

def test_parse_from_file_invalid_extension(parser, tmp_path):
    invalid_file = tmp_path / "test.zip"
    invalid_file.write_text("not a zip")
    with pytest.raises(ValueError, match="Expected .mrpack file"):
        parser.parse_from_file(invalid_file)

def test_parse_mrpack_valid(parser, mock_mrpack_path):
    result = parser.parse_from_file(mock_mrpack_path)
    
    assert isinstance(result, ParsedModpack)
    assert result.manifest.name == "Test Modrinth Pack"
    assert result.manifest.version == "1.0.0"
    assert result.manifest.author == "Test Author"
    assert len(result.manifest.files) == 1
    assert result.manifest.files[0].project_id == 123
    assert result.manifest.files[0].file_id == 456
    assert result.manifest.files[0].source == "modrinth"
    assert result.game_version == "1.20.1"

def test_parse_mrpack_missing_index(parser, tmp_path):
    invalid_mrpack = tmp_path / "invalid.mrpack"
    with zipfile.ZipFile(invalid_mrpack, "w") as zf:
        zf.writestr("other.json", "{}")
    
    with pytest.raises(ValueError, match="missing modrinth.index.json"):
        parser.parse_from_file(invalid_mrpack)

def test_parse_mrpack_no_files(parser, tmp_path):
    mrpack_path = tmp_path / "empty.mrpack"
    with zipfile.ZipFile(mrpack_path, "w") as zf:
        index_data = {
            "name": "Empty Pack",
            "version": "1.0.0",
            "files": []
        }
        zf.writestr("modrinth.index.json", json.dumps(index_data))
    
    result = parser.parse_from_file(mrpack_path)
    assert len(result.manifest.files) == 0

def test_parse_modpack_convenience_function(mock_mrpack_path):
    from services.modpack_parser import parse_modpack
    
    result = parse_modpack(mock_mrpack_path)
    assert result.manifest.name == "Test Modrinth Pack"
    assert result.manifest.manifest_type == "modrinthModpack"
