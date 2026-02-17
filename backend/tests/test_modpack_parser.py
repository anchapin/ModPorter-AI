"""
Unit tests for CurseForge Modpack Manifest Parser
"""

import json
import tempfile
import zipfile
from pathlib import Path
import pytest

from src.services.modpack_parser import (
    CurseForgeModpackParser,
    ModrinthModpackParser,
    parse_modpack,
    ModpackFile,
    CurseForgeManifest,
    ParsedModpack,
)


class TestCurseForgeManifestParser:
    """Tests for CurseForge modpack manifest parsing."""
    
    @pytest.fixture
    def parser(self):
        return CurseForgeModpackParser()
    
    @pytest.fixture
    def sample_manifest_data(self):
        return {
            "manifestType": "minecraftModpack",
            "manifestVersion": 1,
            "name": "Test Modpack",
            "version": "1.0.0",
            "author": "Test Author",
            "files": [
                {"projectID": 123456, "fileID": 789012, "required": True},
                {"projectID": 234567, "fileID": 890123, "required": True},
                {"projectID": 345678, "fileID": 901234, "required": False},
            ],
            "overrides": "overrides",
            "gameVersion": ["1.20.1", "1.20.2"]
        }
    
    def test_parse_manifest_json(self, parser, sample_manifest_data):
        """Test parsing a direct manifest.json file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_manifest_data, f)
            manifest_path = Path(f.name)
        
        try:
            result = parser.parse_from_file(manifest_path)
            
            assert isinstance(result, ParsedModpack)
            assert result.manifest.name == "Test Modpack"
            assert result.manifest.version == "1.0.0"
            assert result.manifest.author == "Test Author"
            assert result.manifest.mod_count == 3
            assert result.manifest.required_mod_count == 2
            assert result.game_version == "1.20.1"
            assert result.is_client_side == True
        finally:
            manifest_path.unlink()
    
    def test_parse_from_zip(self, parser, sample_manifest_data):
        """Test parsing a modpack from a ZIP archive."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
            zip_path = Path(f.name)
        
        try:
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr('manifest.json', json.dumps(sample_manifest_data))
            
            result = parser.parse_from_file(zip_path)
            
            assert isinstance(result, ParsedModpack)
            assert result.manifest.name == "Test Modpack"
            assert result.manifest.mod_count == 3
        finally:
            zip_path.unlink()
    
    def test_invalid_manifest_type(self, parser):
        """Test that invalid manifest type raises ValueError."""
        invalid_data = {
            "manifestType": "invalidType",
            "manifestVersion": 1,
            "name": "Test",
            "version": "1.0.0",
            "author": "Test",
            "files": []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_data, f)
            manifest_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Unsupported manifest type"):
                parser.parse_from_file(manifest_path)
        finally:
            manifest_path.unlink()
    
    def test_invalid_manifest_version(self, parser):
        """Test that invalid manifest version raises ValueError."""
        invalid_data = {
            "manifestType": "minecraftModpack",
            "manifestVersion": 999,
            "name": "Test",
            "version": "1.0.0",
            "author": "Test",
            "files": []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_data, f)
            manifest_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Unsupported manifest version"):
                parser.parse_from_file(manifest_path)
        finally:
            manifest_path.unlink()
    
    def test_server_modpack_detection(self, parser):
        """Test that server modpacks are correctly identified."""
        server_data = {
            "manifestType": "minecraftModpack",
            "manifestVersion": 1,
            "name": "Server Modpack",
            "version": "1.0.0",
            "author": "Test",
            "files": [
                {"projectID": 123456, "fileID": 789012, "required": True},
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(server_data, f)
            manifest_path = Path(f.name)
        
        try:
            result = parser.parse_from_file(manifest_path)
            # Server in name should indicate it's server-side
            assert result.is_client_side == False
        finally:
            manifest_path.unlink()
    
    def test_parse_url(self, parser):
        """Test parsing CurseForge URLs."""
        url = "https://www.curseforge.com/minecraft/modpacks/fabric-example"
        
        result = parser.parse_from_url(url)
        
        assert result["platform"] == "curseforge"
        assert result["type"] == "modpack"
        assert result["slug"] == "fabric-example"
    
    def test_parse_single_mod_url(self, parser):
        """Test parsing single mod URLs."""
        url = "https://curseforge.com/minecraft/mc-mods/fabric-api"
        
        result = parser.parse_from_url(url)
        
        assert result["platform"] == "curseforge"
        assert result["type"] == "mod"
        assert result["slug"] == "fabric-api"


class TestModrinthParser:
    """Tests for Modrinth modpack parsing."""
    
    @pytest.fixture
    def parser(self):
        return ModrinthModpackParser()
    
    @pytest.fixture
    def sample_mrpack_data(self):
        return {
            "formatVersion": 1,
            "name": "Test Modrinth Pack",
            "version": "1.0.0",
            "author": "Test Author",
            "gameVersion": "1.20.1",
            "files": [
                {"projectID": "abc123", "fileID": "def456", "path": "mods/test.jar"},
                {"projectID": "xyz789", "fileID": "uvw012", "path": "mods/another.jar"},
            ]
        }
    
    def test_parse_mrpack(self, parser, sample_mrpack_data):
        """Test parsing a Modrinth .mrpack file."""
        with tempfile.NamedTemporaryFile(suffix='.mrpack', delete=False) as f:
            zip_path = Path(f.name)
        
        try:
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr('modrinth.index.json', json.dumps(sample_mrpack_data))
            
            result = parser.parse_from_file(zip_path)
            
            assert isinstance(result, ParsedModpack)
            assert result.manifest.name == "Test Modrinth Pack"
            assert result.manifest.version == "1.0.0"
            assert result.game_version == "1.20.1"
        finally:
            zip_path.unlink()
    
    def test_invalid_mrpack(self, parser):
        """Test that invalid .mrpack raises ValueError."""
        with tempfile.NamedTemporaryFile(suffix='.mrpack', delete=False) as f:
            zip_path = Path(f.name)
        
        try:
            with zipfile.ZipFile(zip_path, 'w') as zf:
                # Don't include modrinth.index.json
                zf.writestr('other.txt', 'test')
            
            with pytest.raises(ValueError, match="missing modrinth.index.json"):
                parser.parse_from_file(zip_path)
        finally:
            zip_path.unlink()


class TestConvenienceFunction:
    """Tests for the parse_modpack convenience function."""
    
    def test_parse_curseforge_pack(self):
        """Test parse_modpack with CurseForge format."""
        manifest_data = {
            "manifestType": "minecraftModpack",
            "manifestVersion": 1,
            "name": "Test Pack",
            "version": "1.0.0",
            "author": "Test",
            "files": [{"projectID": 1, "fileID": 1, "required": True}]
        }
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
            zip_path = Path(f.name)
        
        try:
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr('manifest.json', json.dumps(manifest_data))
            
            result = parse_modpack(zip_path)
            
            assert result.manifest.name == "Test Pack"
        finally:
            zip_path.unlink()
    
    def test_parse_modrinth_pack(self):
        """Test parse_modpack with Modrinth format."""
        mrpack_data = {
            "formatVersion": 1,
            "name": "Test Pack",
            "version": "1.0.0",
            "author": "Test",
            "gameVersion": "1.20.1",
            "files": []
        }
        
        with tempfile.NamedTemporaryFile(suffix='.mrpack', delete=False) as f:
            mrpack_path = Path(f.name)
        
        try:
            with zipfile.ZipFile(mrpack_path, 'w') as zf:
                zf.writestr('modrinth.index.json', json.dumps(mrpack_data))
            
            result = parse_modpack(mrpack_path)
            
            assert result.manifest.name == "Test Pack"
        finally:
            mrpack_path.unlink()


class TestDataClasses:
    """Tests for dataclasses."""
    
    def test_modpack_file(self):
        """Test ModpackFile dataclass."""
        mf = ModpackFile(project_id=123, file_id=456, required=True, source="curseforge")
        
        assert mf.project_id == 123
        assert mf.file_id == 456
        assert mf.required == True
        assert mf.source == "curseforge"
    
    def test_curseforge_manifest_properties(self):
        """Test CurseForgeManifest computed properties."""
        manifest = CurseForgeManifest(
            manifest_type="minecraftModpack",
            manifest_version=1,
            name="Test",
            version="1.0.0",
            author="Test",
            files=[
                ModpackFile(project_id=1, file_id=1, required=True),
                ModpackFile(project_id=2, file_id=2, required=False),
            ]
        )
        
        assert manifest.mod_count == 2
        assert manifest.required_mod_count == 1
    
    def test_parsed_modpack_methods(self):
        """Test ParsedModpack helper methods."""
        manifest = CurseForgeManifest(
            manifest_type="minecraftModpack",
            manifest_version=1,
            name="Test",
            version="1.0.0",
            author="Test",
            files=[
                ModpackFile(project_id=1, file_id=1, required=True),
                ModpackFile(project_id=2, file_id=2, required=False),
                ModpackFile(project_id=3, file_id=3, required=True),
            ]
        )
        
        modpack = ParsedModpack(manifest=manifest, game_version="1.20.1")
        
        assert modpack.get_mod_ids() == [1, 2, 3]
        assert modpack.get_required_mod_ids() == [1, 3]
