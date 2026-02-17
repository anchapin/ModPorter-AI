"""
Unit tests for CurseForgeParser

Tests the CurseForgeManifestParser and CurseForgeParserAgent classes
for parsing CurseForge modpack manifests.

Issue: #496 - Implement CurseForge Modpack Manifest Parser (Phase 5a)
"""

import json
import pytest
import tempfile
from pathlib import Path

from ai_engine.agents.curseforge_parser import (
    CurseForgeManifestParser,
    CurseForgeParserAgent,
)


# Sample CurseForge manifest for testing
SAMPLE_CURSEFORGE_MANIFEST = {
    "manifestType": "minecraftModpack",
    "manifestVersion": 1,
    "name": "Test Modpack",
    "version": "1.0.0",
    "author": "TestAuthor",
    "description": "A test modpack",
    "minecraft": {
        "version": "1.20.1",
        "modLoaders": [
            {"id": "forge-47.0.0", "primary": True}
        ]
    },
    "overrides": "overrides",
    "files": [
        {
            "projectID": 123456,
            "fileID": 987654,
            "name": "TestMod",
            "version": "1.0.0",
            "filename": "testmod-1.0.0.jar",
            "path": "mods/testmod-1.0.0.jar",
            "required": True,
            "dependencies": [
                {
                    "projectID": 654321,
                    "fileID": 111111,
                    "dependencyType": "required"
                },
                {
                    "projectID": 111111,
                    "fileID": 222222,
                    "dependencyType": "optional"
                }
            ]
        },
        {
            "projectID": 654321,
            "fileID": 111111,
            "name": "DependencyMod",
            "version": "2.0.0",
            "filename": "depmob-2.0.0.jar",
            "path": "mods/depmod-2.0.0.jar",
            "required": True,
            "dependencies": []
        }
    ]
}


class TestCurseForgeManifestParser:
    """Tests for CurseForgeManifestParser class."""
    
    def test_parse_manifest_from_dict(self):
        """Test parsing manifest from dictionary."""
        parser = CurseForgeManifestParser()
        result = parser.parse_from_string(json.dumps(SAMPLE_CURSEFORGE_MANIFEST))
        
        assert result is not None
        assert result["metadata"]["name"] == "Test Modpack"
        assert result["metadata"]["version"] == "1.0.0"
        assert result["metadata"]["author"] == "TestAuthor"
        assert result["metadata"]["minecraft_version"] == "1.20.1"
        assert result["mod_count"] == 2
    
    def test_parse_manifest_from_file(self):
        """Test parsing manifest from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(SAMPLE_CURSEFORGE_MANIFEST, f)
            
            parser = CurseForgeManifestParser()
            result = parser.parse_manifest(manifest_path)
            
            assert result["metadata"]["name"] == "Test Modpack"
            assert result["mod_count"] == 2
    
    def test_extract_mods(self):
        """Test extracting mod information."""
        parser = CurseForgeManifestParser()
        parser.parse_from_string(json.dumps(SAMPLE_CURSEFORGE_MANIFEST))
        
        mods = parser.get_parsed_data()["mods"]
        assert len(mods) == 2
        
        # Check first mod
        assert mods[0]["project_id"] == 123456
        assert mods[0]["file_id"] == 987654
        assert mods[0]["name"] == "TestMod"
        assert mods[0]["version"] == "1.0.0"
        assert mods[0]["required"] is True
        assert len(mods[0]["dependencies"]) == 2
    
    def test_extract_dependencies(self):
        """Test extracting dependency information."""
        parser = CurseForgeManifestParser()
        parser.parse_from_string(json.dumps(SAMPLE_CURSEFORGE_MANIFEST))
        
        mod = parser.get_mod_by_project_id(123456)
        assert mod is not None
        assert len(mod["dependencies"]) == 2
        
        # Check first dependency
        deps = mod["dependencies"]
        assert deps[0]["project_id"] == 654321
        assert deps[1]["project_id"] == 111111
    
    def test_get_required_mods(self):
        """Test getting required mods."""
        parser = CurseForgeManifestParser()
        parser.parse_from_string(json.dumps(SAMPLE_CURSEFORGE_MANIFEST))
        
        required = parser.get_required_mods()
        assert len(required) == 2
    
    def test_validate_manifest_missing_manifestType(self):
        """Test validation fails for missing manifestType."""
        invalid_manifest = SAMPLE_CURSEFORGE_MANIFEST.copy()
        del invalid_manifest["manifestType"]
        
        parser = CurseForgeManifestParser()
        with pytest.raises(ValueError, match="Missing required field: manifestType"):
            parser.parse_from_string(json.dumps(invalid_manifest))
    
    def test_validate_manifest_wrong_type(self):
        """Test validation fails for wrong manifestType."""
        invalid_manifest = SAMPLE_CURSEFORGE_MANIFEST.copy()
        invalid_manifest["manifestType"] = "wrongType"
        
        parser = CurseForgeManifestParser()
        with pytest.raises(ValueError, match="Unsupported manifest type"):
            parser.parse_from_string(json.dumps(invalid_manifest))
    
    def test_validate_manifest_unsupported_version(self):
        """Test validation fails for unsupported version."""
        invalid_manifest = SAMPLE_CURSEFORGE_MANIFEST.copy()
        invalid_manifest["manifestVersion"] = 99
        
        parser = CurseForgeManifestParser()
        with pytest.raises(ValueError, match="Unsupported manifest version"):
            parser.parse_from_string(json.dumps(invalid_manifest))
    
    def test_validate_manifest_missing_files(self):
        """Test validation fails for missing files."""
        invalid_manifest = SAMPLE_CURSEFORGE_MANIFEST.copy()
        del invalid_manifest["files"]
        
        parser = CurseForgeManifestParser()
        with pytest.raises(ValueError, match="Missing required field: files"):
            parser.parse_from_string(json.dumps(invalid_manifest))
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        parser = CurseForgeManifestParser()
        with pytest.raises(ValueError, match="Invalid JSON"):
            parser.parse_from_string("not valid json")
    
    def test_is_server_modpack(self):
        """Test server modpack detection."""
        # Create manifest with server overrides
        manifest = SAMPLE_CURSEFORGE_MANIFEST.copy()
        manifest["overrides"] = "server"
        
        parser = CurseForgeManifestParser()
        parser.parse_from_string(json.dumps(manifest))
        
        assert parser._is_server_modpack() is True
        assert parser._is_client_modpack() is False
    
    def test_is_client_modpack(self):
        """Test client modpack detection."""
        manifest = SAMPLE_CURSEFORGE_MANIFEST.copy()
        manifest["overrides"] = "client"
        
        parser = CurseForgeManifestParser()
        parser.parse_from_string(json.dumps(manifest))
        
        assert parser._is_client_modpack() is True
        assert parser._is_server_modpack() is False


class TestCurseForgeParserAgent:
    """Tests for CurseForgeParserAgent class."""
    
    def test_agent_parse_modpack(self):
        """Test agent parsing a modpack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "testpack"
            pack_path.mkdir()
            
            manifest_path = pack_path / "manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(SAMPLE_CURSEFORGE_MANIFEST, f)
            
            agent = CurseForgeParserAgent()
            result = agent.parse_modpack(pack_path)
            
            assert result["metadata"]["name"] == "Test Modpack"
            assert result["mod_count"] == 2
    
    def test_agent_file_not_found(self):
        """Test agent handles missing manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "empty"
            pack_path.mkdir()
            
            agent = CurseForgeParserAgent()
            with pytest.raises(FileNotFoundError):
                agent.parse_modpack(pack_path)


class TestCurseForgeManifestV2:
    """Tests for CurseForge manifest version 2."""
    
    def test_parse_v2_manifest(self):
        """Test parsing manifest version 2."""
        manifest_v2 = SAMPLE_CURSEFORGE_MANIFEST.copy()
        manifest_v2["manifestVersion"] = 2
        
        parser = CurseForgeManifestParser()
        result = parser.parse_from_string(json.dumps(manifest_v2))
        
        assert result is not None
        assert result["metadata"]["manifest_version"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
