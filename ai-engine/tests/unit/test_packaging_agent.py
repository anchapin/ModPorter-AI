import pytest
import json
import uuid
import os
import zipfile
from pathlib import Path
import tempfile
import shutil

from src.agents.packaging_agent import PackagingAgent

@pytest.fixture
def packaging_agent():
    """Fixture to create a PackagingAgent instance."""
    return PackagingAgent()

@pytest.fixture
def temp_output_dir():
    """Fixture to create a temporary directory for test outputs."""
    temp_dir = tempfile.mkdtemp(prefix="modporter_test_")
    yield temp_dir
    # Teardown: remove the temporary directory and its contents
    shutil.rmtree(temp_dir)

class TestPackagingAgentManifests:
    """Tests for manifest generation."""

    

    def test_generate_manifests_tool_output_files(self, packaging_agent: PackagingAgent):
        manifest_data = {
            "mod_name": "My Full Addon",
            "mod_description": "Behavior and Resource Packs",
            "mod_version": [1, 0, 0],
            "pack_types": ["behavior_pack", "resource_pack"]
        }
        result_str = packaging_agent.generate_manifests(manifest_data)
        result = json.loads(result_str)


        assert "behavior_pack_manifest" in result
        assert "resource_pack_manifest" in result

        bp_content = result["behavior_pack_manifest"]
        rp_content = result["resource_pack_manifest"]

        assert bp_content["header"]["name"] == "My Full Addon Behavior Pack"
        assert bp_content["header"]["description"] == "Behavior and Resource Packs"
        assert uuid.UUID(bp_content["header"]["uuid"])
        assert bp_content["header"]["version"] == [1, 0, 0]
        assert bp_content["modules"][0]["type"] == "data"

        assert rp_content["header"]["name"] == "My Full Addon Resource Pack"
        assert rp_content["header"]["description"] == "Behavior and Resource Packs"
        assert uuid.UUID(rp_content["header"]["uuid"])
        assert rp_content["header"]["version"] == [1, 0, 0]
        assert rp_content["modules"][0]["type"] == "resources"

    def test_generate_manifests_tool_only_bp(self, packaging_agent: PackagingAgent):
        manifest_data = {
            "mod_name": "BP Only",
            "pack_types": ["behavior_pack"]
        }
        result_str = packaging_agent.generate_manifests(manifest_data)
        result = json.loads(result_str)


        assert "behavior_pack_manifest" in result
        assert "resource_pack_manifest" not in result

        bp_content = result["behavior_pack_manifest"]
        assert bp_content["header"]["name"] == "BP Only Behavior Pack"

    def test_generate_manifests_tool_only_rp(self, packaging_agent: PackagingAgent):
        manifest_data = {
            "mod_name": "RP Only",
            "pack_types": ["resource_pack"]
        }
        result_str = packaging_agent.generate_manifests(manifest_data)
        result = json.loads(result_str)


        assert "behavior_pack_manifest" not in result
        assert "resource_pack_manifest" in result

        rp_content = result["resource_pack_manifest"]
        assert rp_content["header"]["name"] == "RP Only Resource Pack"

    

# More test classes will follow for structure, packaging, validation etc.

class TestPackagingAgentStructure:
    """Tests for package structure creation."""

    

    def test_create_package_structure_tool_valid_input(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        structure_data = {
            "output_dir": temp_output_dir,
            "mod_name": "cool_addon"
        }
        result_str = packaging_agent.create_package_structure(structure_data)
        result = json.loads(result_str)


        assert "behavior_pack_path" in result
        assert "resource_pack_path" in result

        bp_path = Path(result["behavior_pack_path"])
        rp_path = Path(result["resource_pack_path"])

        assert bp_path.exists()
        assert bp_path.is_dir()
        assert rp_path.exists()
        assert rp_path.is_dir()

        # Check some expected subdirectories
        assert (bp_path / "entities").exists()
        assert (bp_path / "scripts").exists()
        assert (rp_path / "textures").exists()
        assert (rp_path / "models").exists()

    

class TestPackagingAgentMcAddon:
    """Tests for .mcaddon file building."""

    @pytest.fixture
    def sample_bp_dir(self, temp_output_dir: str) -> Path:
        bp_path = Path(temp_output_dir) / "sample_bp"
        bp_path.mkdir()
        (bp_path / "manifest.json").write_text(json.dumps({"format_version": 2, "header": {"uuid": str(uuid.uuid4()), "name":"bp", "version":[0,0,1]}, "modules":[{"type":"data", "uuid":str(uuid.uuid4()), "version":[0,0,1]}]}))
        (bp_path / "entities").mkdir()
        (bp_path / "entities" / "my_entity.json").write_text("{}")
        return bp_path

    @pytest.fixture
    def sample_rp_dir(self, temp_output_dir: str) -> Path:
        rp_path = Path(temp_output_dir) / "sample_rp"
        rp_path.mkdir()
        (rp_path / "manifest.json").write_text(json.dumps({"format_version": 2, "header": {"uuid": str(uuid.uuid4()), "name":"rp", "version":[0,0,1]}, "modules":[{"type":"resources", "uuid":str(uuid.uuid4()), "version":[0,0,1]}]}))
        (rp_path / "textures").mkdir()
        (rp_path / "textures" / "my_texture.png").write_text("dummy png content")
        return rp_path

    def test_build_mcaddon_file(self, packaging_agent: PackagingAgent, sample_bp_dir: Path, sample_rp_dir: Path, temp_output_dir: str):
        output_mcaddon_path = Path(temp_output_dir) / "test_addon.mcaddon"

        build_data = {
            "output_path": str(output_mcaddon_path),
            "behavior_pack_path": str(sample_bp_dir),
            "resource_pack_path": str(sample_rp_dir)
        }
        result_str = packaging_agent.build_mcaddon(build_data)
        result = json.loads(result_str)


        assert Path(result["output_path"]) == output_mcaddon_path
        assert output_mcaddon_path.exists()

        # Verify zip contents
        with zipfile.ZipFile(output_mcaddon_path, 'r') as zf:
            namelist = zf.namelist()
            # Check for correct top-level folder names and file paths within them
            assert "behaviors/manifest.json" in namelist # Manifest from BP
            assert "behaviors/entities/my_entity.json" in namelist
            assert "resources/manifest.json" in namelist # Manifest from RP
            assert "resources/textures/my_texture.png" in namelist
            assert len(namelist) == 4

    def test_build_mcaddon_tool_with_bp_and_rp(self, packaging_agent: PackagingAgent, sample_bp_dir: Path, sample_rp_dir: Path, temp_output_dir: str):
        output_path = Path(temp_output_dir) / "my_super_addon.mcaddon"
        build_data = {
            "output_path": str(output_path),
            "behavior_pack_path": str(sample_bp_dir),
            "resource_pack_path": str(sample_rp_dir)
        }
        result_str = packaging_agent.build_mcaddon(build_data)
        result = json.loads(result_str)


        assert Path(result["output_path"]) == output_path
        assert output_path.exists()

    


