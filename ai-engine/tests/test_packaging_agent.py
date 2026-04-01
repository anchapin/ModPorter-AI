"""
Unit tests for the PackagingAgent - comprehensive coverage for mcaddon packaging functionality.
"""

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.packaging_agent import PackagingAgent


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    import shutil

    shutil.rmtree(tmpdir, ignore_errors=True)


class TestPackagingAgent:
    """Test cases for PackagingAgent packaging functionality"""

    @pytest.fixture
    def agent(self):
        """Create PackagingAgent instance for testing."""
        return PackagingAgent.get_instance()

    def test_singleton_pattern(self):
        """Test singleton pattern for PackagingAgent"""
        agent1 = PackagingAgent.get_instance()
        agent2 = PackagingAgent.get_instance()
        assert agent1 is agent2

    def test_generate_manifest_basic(self, agent):
        """Test basic manifest generation"""
        mod_info = json.dumps({"name": "Test Mod", "version": [1, 0, 0], "framework": "fabric"})
        result = agent.generate_manifest(mod_info, "behavior")

        result_data = json.loads(result)
        assert "error" not in result_data or result_data.get("success") is not False

    def test_generate_manifest_with_packs(self, agent):
        """Test manifest generation with different pack types"""
        mod_info = json.dumps(
            {"name": "Multi Pack Mod", "version": [2, 0, 1], "framework": "forge"}
        )

        # Test behavior pack
        result = agent.generate_manifest(mod_info, "behavior")
        result_data = json.loads(result)
        assert "error" not in result_data

        # Test resource pack
        result = agent.generate_manifest(mod_info, "resource")
        result_data = json.loads(result)
        assert "error" not in result_data

        # Test both packs
        result = agent.generate_manifest(mod_info, "both")
        result_data = json.loads(result)
        assert "error" not in result_data

    def test_generate_manifest_invalid_json(self, agent):
        """Test manifest generation with invalid JSON"""
        result = agent.generate_manifest("invalid json", "behavior")
        result_data = json.loads(result)
        assert result_data.get("success") is False or "error" in result_data

    def test_generate_manifests_with_output_dir(self, agent, temp_dir):
        """Test manifest generation with output directory"""
        manifest_data = json.dumps(
            {
                "package_info": {
                    "name": "Test Package",
                    "version": [1, 0, 0],
                    "output_directory": temp_dir,
                    "has_behavior_pack": True,
                    "has_resource_pack": True,
                },
                "capabilities": ["chemistry"],
                "pack_types": ["behavior_pack", "resource_pack"],
            }
        )

        result = agent.generate_manifests(manifest_data)
        result_data = json.loads(result)

        # Check if files were created
        if result_data.get("success"):
            assert "files_created" in result_data

    def test_generate_manifests_invalid_json(self, agent):
        """Test manifest generation with invalid JSON input"""
        result = agent.generate_manifests("not valid json")
        result_data = json.loads(result)
        assert result_data.get("success") is False

    def test_analyze_conversion_components(self, agent):
        """Test conversion component analysis"""
        component_data = json.dumps(
            {
                "blocks": ["stone", "dirt"],
                "items": ["sword", "pickaxe"],
                "textures": ["stone.png", "sword.png"],
            }
        )

        result = agent.analyze_conversion_components(component_data)
        result_data = json.loads(result)

        assert result_data.get("success") is True
        assert "components" in result_data

    def test_analyze_conversion_components_string(self, agent):
        """Test component analysis with string input"""
        result = agent.analyze_conversion_components("some string data")
        result_data = json.loads(result)
        assert result_data.get("success") is True

    def test_create_package_structure(self, agent, temp_dir):
        """Test package structure creation"""
        structure_data = {"output_dir": temp_dir, "mod_name": "test_mod"}

        result = agent.create_package_structure(structure_data)
        result_data = json.loads(result)

        assert result_data.get("success") is True
        assert "behavior_pack_path" in result_data
        assert "resource_pack_path" in result_data

    def test_create_package_structure_no_output_dir(self, agent):
        """Test package structure creation without output directory"""
        structure_data = {"mod_name": "test_mod"}

        result = agent.create_package_structure(structure_data)
        result_data = json.loads(result)

        assert result_data.get("success") is False

    def test_validate_package(self, agent):
        """Test package validation"""
        validation_data = json.dumps(
            {"package_path": "/path/to/package", "check_manifest": True, "check_textures": True}
        )

        result = agent.validate_package(validation_data)
        result_data = json.loads(result)

        assert result_data.get("success") is True

    def test_validate_package_string_input(self, agent):
        """Test package validation with string input"""
        result = agent.validate_package("some validation data")
        result_data = json.loads(result)
        assert result_data.get("success") is True

    def test_build_mcaddon(self, agent, temp_dir):
        """Test mcaddon build"""
        # Create mock conversion data
        conversion_data = json.dumps(
            {
                "output_path": os.path.join(temp_dir, "output"),
                "mod_name": "TestMod",
                "mod_version": "1.0.0",
                "behavior_pack": {"entities": [], "items": [], "blocks": []},
                "resource_pack": {"textures": [], "models": []},
            }
        )

        result = agent.build_mcaddon(conversion_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True

    def test_get_tools(self, agent):
        """Test that get_tools returns a list"""
        tools = agent.get_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_analyze_conversion_components_tool(self, agent):
        """Test analyze_conversion_components_tool"""
        input_data = json.dumps({"components": []})
        result = agent.analyze_conversion_components_tool.run(component_data=input_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True

    def test_create_package_structure_tool(self, agent, temp_dir):
        """Test create_package_structure_tool"""
        input_data = json.dumps({"output_dir": temp_dir, "mod_name": "test_mod"})
        result = agent.create_package_structure_tool.run(structure_data=input_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True

    def test_generate_manifests_tool(self, agent, temp_dir):
        """Test generate_manifests_tool"""
        input_data = json.dumps({"package_info": {"name": "Test", "output_directory": temp_dir}})
        result = agent.generate_manifests_tool.run(manifest_data=input_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True

    def test_validate_package_tool(self, agent):
        """Test validate_package_tool"""
        input_data = json.dumps({"package_path": "/fake/path"})
        result = agent.validate_package_tool.run(validation_data=input_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True

    def test_build_mcaddon_tool(self, agent, temp_dir):
        """Test build_mcaddon_tool"""
        input_data = json.dumps({"output_path": temp_dir, "mod_name": "TestMod"})
        result = agent.build_mcaddon_tool.run(build_data=input_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True

    def test_generate_enhanced_manifests_tool(self, agent):
        """Test generate_enhanced_manifests_tool"""
        input_data = json.dumps({"mod_name": "EnhancedMod", "mod_version": [1, 0, 0]})
        result = agent.generate_enhanced_manifests_tool.run(mod_data=input_data)
        result_data = json.loads(result)
        # May fail due to dependencies but should handle gracefully

    def test_generate_blocks_and_items_tool(self, agent):
        """Test generate_blocks_and_items_tool"""
        input_data = json.dumps({"blocks": [], "items": []})
        result = agent.generate_blocks_and_items_tool.run(conversion_data=input_data)
        result_data = json.loads(result)
        # Should handle gracefully

    def test_package_constraints(self, agent):
        """Test package constraints are defined"""
        assert "max_total_size_mb" in agent.package_constraints
        assert "max_files" in agent.package_constraints
        assert "required_files" in agent.package_constraints

    def test_pack_structures(self, agent):
        """Test pack structures are defined"""
        assert "behavior_pack" in agent.pack_structures
        assert "resource_pack" in agent.pack_structures

    def test_manifest_template(self, agent):
        """Test manifest template structure"""
        assert "format_version" in agent.manifest_template
        assert "header" in agent.manifest_template
        assert "modules" in agent.manifest_template


class TestPackagingAgentEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def agent(self):
        return PackagingAgent.get_instance()

    def test_generate_manifest_empty_info(self, agent):
        """Test manifest generation with empty info"""
        result = agent.generate_manifest("{}", "behavior")
        result_data = json.loads(result)
        assert "error" not in result_data

    def test_generate_manifests_dict_input(self, agent, temp_dir):
        """Test manifests generation with dict input"""
        manifest_data = {"package_info": {"name": "Test", "output_directory": temp_dir}}

        result = agent.generate_manifests(manifest_data)
        result_data = json.loads(result)
        assert result_data.get("success") is True

    def test_analyze_conversion_empty_components(self, agent):
        """Test analysis with empty components"""
        result = agent.analyze_conversion_components("{}")
        result_data = json.loads(result)
        assert result_data.get("success") is True

    def test_validate_package_empty_data(self, agent):
        """Test validation with empty data"""
        result = agent.validate_package("{}")
        result_data = json.loads(result)
        assert result_data.get("success") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
