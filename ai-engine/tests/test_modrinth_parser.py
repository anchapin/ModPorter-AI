"""
Unit tests for ModrinthParser

Tests the ModrinthPackParser and ModrinthParserAgent classes
for parsing Modrinth pack format files.

Issue: #497 - Implement Modrinth Pack Format Support (Phase 5b)
"""

import json
import pytest
import tempfile
from pathlib import Path

from agents.modrinth_parser import (
    ModrinthPackParser,
    ModrinthParserAgent,
)


# Sample Modrinth index for testing
SAMPLE_MODRINTH_INDEX = {
    "format_version": 1,
    "pack": {
        "name": "Test Modpack",
        "version": "1.0.0",
        "description": "A test modpack"
    },
    "author": {
        "name": "TestAuthor"
    },
    "dependencies": {
        "minecraft": "1.20.1",
        "fabric-loader": "0.15.0",
        "fabric-api": "0.90.0"
    },
    "files": [
        {
            "path": "mods/testmod.jar",
            "hashes": {
                "sha1": "abc123",
                "sha512": "def456"
            },
            "env": {
                "client": "required",
                "server": "optional"
            },
            "downloads": ["https://cdn.modrinth.com/mod1.jar"],
            "fileSize": 12345
        },
        {
            "path": "mods/depmod.jar",
            "hashes": {
                "sha1": "ghi789"
            },
            "env": {
                "client": "optional",
                "server": "required"
            },
            "downloads": ["https://cdn.modrinth.com/mod2.jar"],
            "fileSize": 67890
        },
        {
            "path": "config/settings.json",
            "hashes": {
                "sha1": "jkl012"
            },
            "env": {
                "client": "optional",
                "server": "optional"
            }
        }
    ]
}


class TestModrinthPackParser:
    """Tests for ModrinthPackParser class."""
    
    def test_parse_index_from_dict(self):
        """Test parsing index from dictionary."""
        parser = ModrinthPackParser()
        result = parser.parse_from_string(json.dumps(SAMPLE_MODRINTH_INDEX))
        
        assert result is not None
        assert result["metadata"]["name"] == "Test Modpack"
        assert result["metadata"]["version"] == "1.0.0"
        assert result["metadata"]["author"] == "TestAuthor"
        assert result["file_count"] == 3
    
    def test_parse_index_from_file(self):
        """Test parsing index from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "modrinth.index.json"
            with open(index_path, 'w') as f:
                json.dump(SAMPLE_MODRINTH_INDEX, f)
            
            parser = ModrinthPackParser()
            result = parser.parse_index(index_path)
            
            assert result["metadata"]["name"] == "Test Modpack"
            assert result["file_count"] == 3
    
    def test_extract_files(self):
        """Test extracting file information."""
        parser = ModrinthPackParser()
        parser.parse_from_string(json.dumps(SAMPLE_MODRINTH_INDEX))
        
        files = parser.get_parsed_data()["files"]
        assert len(files) == 3
        
        # Check first file
        assert files[0]["path"] == "mods/testmod.jar"
        assert "sha1" in files[0]["hashes"]
        assert files[0]["env"]["client"] == "required"
        assert files[0]["env"]["server"] == "optional"
    
    def test_extract_dependencies(self):
        """Test extracting dependencies."""
        parser = ModrinthPackParser()
        parser.parse_from_string(json.dumps(SAMPLE_MODRINTH_INDEX))
        
        deps = parser.get_dependency_versions()
        assert "minecraft" in deps
        assert deps["minecraft"] == "1.20.1"
        assert "fabric-loader" in deps
    
    def test_get_client_files(self):
        """Test getting client-specific files."""
        parser = ModrinthPackParser()
        parser.parse_from_string(json.dumps(SAMPLE_MODRINTH_INDEX))
        
        client_files = parser.get_client_files()
        # Only files with client=required
        assert len(client_files) == 1
        assert client_files[0]["path"] == "mods/testmod.jar"
    
    def test_get_server_files(self):
        """Test getting server-specific files."""
        parser = ModrinthPackParser()
        parser.parse_from_string(json.dumps(SAMPLE_MODRINTH_INDEX))
        
        server_files = parser.get_server_files()
        # Only files with server=required
        assert len(server_files) == 1
        assert server_files[0]["path"] == "mods/depmod.jar"
    
    def test_has_client_files(self):
        """Test checking for client files."""
        parser = ModrinthPackParser()
        parser.parse_from_string(json.dumps(SAMPLE_MODRINTH_INDEX))
        
        assert parser._has_client_files() is True
        assert parser._has_server_files() is True
    
    def test_get_files_by_pattern(self):
        """Test getting files by path pattern."""
        parser = ModrinthPackParser()
        parser.parse_from_string(json.dumps(SAMPLE_MODRINTH_INDEX))
        
        mod_files = parser.get_files_by_pattern(r"^mods/")
        assert len(mod_files) == 2
        
        config_files = parser.get_files_by_pattern(r"^config/")
        assert len(config_files) == 1
    
    def test_validate_index_missing_format_version(self):
        """Test validation fails for missing format_version."""
        invalid_index = SAMPLE_MODRINTH_INDEX.copy()
        del invalid_index["format_version"]
        
        parser = ModrinthPackParser()
        with pytest.raises(ValueError, match="Missing required field: format_version"):
            parser.parse_from_string(json.dumps(invalid_index))
    
    def test_validate_index_unsupported_version(self):
        """Test validation fails for unsupported version."""
        invalid_index = SAMPLE_MODRINTH_INDEX.copy()
        invalid_index["format_version"] = 99
        
        parser = ModrinthPackParser()
        with pytest.raises(ValueError, match="Unsupported format version"):
            parser.parse_from_string(json.dumps(invalid_index))
    
    def test_validate_index_missing_pack(self):
        """Test validation fails for missing pack info."""
        invalid_index = SAMPLE_MODRINTH_INDEX.copy()
        del invalid_index["pack"]
        
        parser = ModrinthPackParser()
        with pytest.raises(ValueError, match="Missing required field: pack"):
            parser.parse_from_string(json.dumps(invalid_index))
    
    def test_validate_index_missing_files(self):
        """Test validation fails for missing files."""
        invalid_index = SAMPLE_MODRINTH_INDEX.copy()
        del invalid_index["files"]
        
        parser = ModrinthPackParser()
        with pytest.raises(ValueError, match="Missing required field: files"):
            parser.parse_from_string(json.dumps(invalid_index))
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        parser = ModrinthPackParser()
        with pytest.raises(ValueError, match="Invalid JSON"):
            parser.parse_from_string("not valid json")
    
    def test_determine_pack_type(self):
        """Test pack type determination."""
        parser = ModrinthPackParser()
        
        # Test modpack
        assert parser._determine_pack_type("My Modpack") == "modpack"
        
        # Test datapack
        assert parser._determine_pack_type("My Datapack") == "datapack"
        
        # Test resourcepack
        assert parser._determine_pack_type("My Resource Pack") == "resourcepack"


class TestModrinthParserAgent:
    """Tests for ModrinthParserAgent class."""
    
    def test_agent_parse_modpack(self):
        """Test agent parsing a modpack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "testpack"
            pack_path.mkdir()
            
            index_path = pack_path / "modrinth.index.json"
            with open(index_path, 'w') as f:
                json.dump(SAMPLE_MODRINTH_INDEX, f)
            
            agent = ModrinthParserAgent()
            result = agent.parse_modpack(pack_path)
            
            assert result["metadata"]["name"] == "Test Modpack"
            assert result["file_count"] == 3
    
    def test_agent_file_not_found(self):
        """Test agent handles missing index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "empty"
            pack_path.mkdir()
            
            agent = ModrinthParserAgent()
            with pytest.raises(FileNotFoundError):
                agent.parse_modpack(pack_path)


class TestModrinthIndexV2:
    """Tests for Modrinth index format version 2."""
    
    def test_parse_v2_index(self):
        """Test parsing index version 2."""
        index_v2 = SAMPLE_MODRINTH_INDEX.copy()
        index_v2["format_version"] = 2
        
        parser = ModrinthPackParser()
        result = parser.parse_from_string(json.dumps(index_v2))
        
        assert result is not None
        assert result["metadata"]["format_version"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
