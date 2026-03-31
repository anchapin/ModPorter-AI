import pytest
import json
import uuid
import os
from pathlib import Path
from agents.bedrock_manifest_generator import BedrockManifestGenerator, PackType

class TestBedrockManifestGenerator:
    @pytest.fixture
    def generator(self):
        return BedrockManifestGenerator()

    def test_parse_version_valid(self, generator):
        assert generator._parse_version("1.2.3") == [1, 2, 3]
        assert generator._parse_version("1.0") == [1, 0, 0]
        assert generator._parse_version("2") == [2, 0, 0]
        assert generator._parse_version([1, 2, 3]) == [1, 2, 3]
        assert generator._parse_version([1, 2]) == [1, 2, 0]

    def test_parse_version_complex(self, generator):
        assert generator._parse_version("1.2.3-beta") == [1, 2, 3]
        assert generator._parse_version("v2.1.0") == [2, 1, 0]

    def test_parse_version_invalid(self, generator):
        assert generator._parse_version("invalid") == [0, 0, 0]
        # str(None) is "None", which results in [0, 0, 0]
        assert generator._parse_version(None) == [0, 0, 0]

    def test_determine_capabilities(self, generator):
        mod_data = {
            "features": [
                {"type": "custom_ui"},
                {"type": "scripting"}
            ],
            "experimental_features": ["chemistry"]
        }
        capabilities = generator._determine_capabilities(mod_data)
        assert "experimental_custom_ui" in capabilities
        assert "script_eval" in capabilities
        assert "chemistry" in capabilities

    def test_generate_manifests_basic(self, generator):
        mod_data = {
            "name": "Test Mod",
            "description": "A test mod",
            "version": "1.0.0"
        }
        bp, rp = generator.generate_manifests(mod_data)
        
        assert bp["header"]["name"] == "Test Mod BP"
        assert rp["header"]["name"] == "Test Mod RP"
        assert bp["header"]["version"] == [1, 0, 0]
        
        # Check dependencies
        assert bp["dependencies"][0]["uuid"] == rp["header"]["uuid"]
        assert rp["dependencies"][0]["uuid"] == bp["header"]["uuid"]
        
        # Check modules
        assert bp["modules"][0]["type"] == "data"
        assert rp["modules"][0]["type"] == "resources"

    def test_generate_manifests_with_capabilities(self, generator):
        mod_data = {
            "name": "Test Mod",
            "features": [{"type": "custom_ui"}]
        }
        bp, rp = generator.generate_manifests(mod_data)
        
        assert "experimental_custom_ui" in bp["capabilities"]
        assert "experimental_custom_ui" in rp["capabilities"]
        
        # Check modules for custom_ui
        assert any(m["type"] == "javascript" for m in bp["modules"])
        assert any(m["type"] == "client_data" for m in rp["modules"])

    def test_generate_single_manifest(self, generator):
        mod_data = {"name": "Single Pack"}
        bp = generator.generate_single_manifest(PackType.BEHAVIOR, mod_data)
        assert bp["header"]["name"] == "Single Pack BP"
        
        rp = generator.generate_single_manifest(PackType.RESOURCE, mod_data)
        assert rp["header"]["name"] == "Single Pack RP"

    def test_validate_manifest_invalid(self, generator):
        invalid_manifest = {
            "format_version": 2,
            "header": {
                "name": "Invalid",
                # missing uuid, version
            },
            "modules": []
        }
        with pytest.raises(ValueError, match="Invalid behavior pack manifest"):
            generator._validate_manifest(invalid_manifest, "behavior")

    def test_write_manifests_to_disk(self, generator, tmp_path):
        bp_manifest = {"test": "bp"}
        rp_manifest = {"test": "rp"}
        bp_dir = tmp_path / "bp"
        rp_dir = tmp_path / "rp"
        
        bp_file, rp_file = generator.write_manifests_to_disk(
            bp_manifest, rp_manifest, bp_dir, rp_dir
        )
        
        assert bp_file.exists()
        assert rp_file.exists()
        
        with open(bp_file, "r") as f:
            assert json.load(f) == bp_manifest
