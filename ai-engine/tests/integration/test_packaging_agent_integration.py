import pytest
import json
import uuid
import os
import zipfile
from pathlib import Path
import tempfile
import shutil

from src.agents.packaging_agent import PackagingAgent

@pytest.fixture(scope="class")
def packaging_agent_instance():
    """Class-scoped fixture for PackagingAgent instance."""
    return PackagingAgent()

@pytest.fixture
def integration_temp_dir():
    """Fixture to create a temporary directory for integration test outputs."""
    temp_dir = tempfile.mkdtemp(prefix="modporter_int_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


class TestPackagingAgentIntegration:
    """Integration tests for the PackagingAgent."""

    def test_full_packaging_workflow_bp_only(self, packaging_agent_instance: PackagingAgent, integration_temp_dir: Path):
        """
        Tests the full workflow:
        1. Generate manifest for a behavior pack.
        2. Create structure for the behavior pack.
        3. Build .mcaddon file.
        4. Validate the created .mcaddon.
        """
        agent = packaging_agent_instance
        addon_name = "MyIntegratedBPAddon"

        # --- Step 1: Generate Manifest ---
        # We'll create files in a temporary "source" behavior pack directory
        bp_source_path = integration_temp_dir / "bp_source"
        # The generate_manifests_tool will create bp_source_path / "behavior_pack" / "manifest.json"

        manifest_data_bp = {
            "package_info": {
                "name": addon_name,
                "description": "Integrated Behavior Pack Test",
                "version": [1, 1, 0],
                "output_directory": str(bp_source_path), # Tool creates subdirs like "behavior_pack" here
                "has_behavior_pack": True,
                "has_resource_pack": False
            },
            "capabilities": ["scripting"]
        }
        manifest_result_str = agent.generate_manifests_tool(json.dumps(manifest_data_bp))
        manifest_result = json.loads(manifest_result_str)

        assert manifest_result["success"] is True
        assert manifest_result["behavior_manifest_path"] is not None
        bp_manifest_file = Path(manifest_result["behavior_manifest_path"])
        assert bp_manifest_file.exists()

        # The actual pack directory that generate_manifests_tool created
        actual_bp_pack_dir = bp_manifest_file.parent
        assert actual_bp_pack_dir.name == "behavior_pack"
        assert actual_bp_pack_dir.parent == bp_source_path

        # --- Step 2: Create Structure (and add some dummy files) ---
        # The manifest generation already created the basic "behavior_pack" dir.
        # We'll use create_package_structure_tool to ensure it can work with an existing dir
        # and to conceptually "place" components (though it doesn't move files).

        # Create dummy script file referenced in manifest
        scripts_dir = actual_bp_pack_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        (scripts_dir / "main.js").write_text("console.log('hello from script');")

        # Add a dummy entity file
        entities_dir = actual_bp_pack_dir / "entities"
        entities_dir.mkdir(exist_ok=True) # Should have been made by _create_base_structure if called by create_package_structure_tool
        (entities_dir / "my_mob.json").write_text('{"format_version":"1.20.0", "minecraft:entity":{}}')

        # (Optional: Call create_package_structure_tool if we want to test its direct output,
        # but for packaging, we just need the files in the right place)
        # For this test, we manually ensured files are in actual_bp_pack_dir

        # --- Step 3: Build .mcaddon ---
        mcaddon_output_path = integration_temp_dir / f"{addon_name}.mcaddon"
        build_data = {
            "source_directories": [str(actual_bp_pack_dir)], # Pass the actual pack dir, not its parent
            "output_path": str(mcaddon_output_path),
            "metadata": {"addon_name": addon_name}
        }
        build_result_str = agent.build_mcaddon_tool(json.dumps(build_data))
        build_result = json.loads(build_result_str)

        assert build_result["success"] is True
        assert Path(build_result["output_path"]) == mcaddon_output_path.resolve()
        assert mcaddon_output_path.exists()

        # Verify zip contents
        with zipfile.ZipFile(mcaddon_output_path, 'r') as zf:
            namelist = zf.namelist()
            # The path inside the zip should be relative to actual_bp_pack_dir's name
            assert f"{actual_bp_pack_dir.name}/manifest.json" in namelist
            assert f"{actual_bp_pack_dir.name}/scripts/main.js" in namelist
            assert f"{actual_bp_pack_dir.name}/entities/my_mob.json" in namelist
            assert len(namelist) == 3

        # --- Step 4: Validate the created .mcaddon (conceptually) ---
        # The validate_package_tool expects paths to extracted packs, not the .mcaddon itself.
        # For this integration test, we'll rely on the post_build_validation from build_mcaddon_tool.
        assert build_result["post_validation"]["is_valid_zip"] is True
        assert build_result["post_validation"]["contains_manifests"] is True


    def test_full_packaging_workflow_bp_and_rp(self, packaging_agent_instance: PackagingAgent, integration_temp_dir: Path):
        agent = packaging_agent_instance
        addon_name = "MyIntegratedFullAddon"

        # --- Step 1: Generate Manifests ---
        source_packs_parent_dir = integration_temp_dir / "full_addon_source"
        # generate_manifests_tool will create:
        # source_packs_parent_dir / "behavior_pack" / "manifest.json"
        # source_packs_parent_dir / "resource_pack" / "manifest.json"

        manifest_data = {
            "package_info": {
                "name": addon_name,
                "description": "Integrated Full Addon Test",
                "version": [1,0,0],
                "output_directory": str(source_packs_parent_dir),
                "has_behavior_pack": True,
                "has_resource_pack": True
            }
        }
        manifest_result_str = agent.generate_manifests_tool(json.dumps(manifest_data))
        manifest_result = json.loads(manifest_result_str)

        assert manifest_result["success"] is True
        bp_manifest_file = Path(manifest_result["behavior_manifest_path"])
        rp_manifest_file = Path(manifest_result["resource_manifest_path"])
        assert bp_manifest_file.exists()
        assert rp_manifest_file.exists()

        actual_bp_pack_dir = bp_manifest_file.parent
        actual_rp_pack_dir = rp_manifest_file.parent

        assert actual_bp_pack_dir.name == "behavior_pack"
        assert actual_rp_pack_dir.name == "resource_pack"

        # --- Step 2: Add dummy files to packs ---
        (actual_bp_pack_dir / "items").mkdir(exist_ok=True)
        (actual_bp_pack_dir / "items" / "custom_sword.json").write_text("{}")
        (actual_rp_pack_dir / "textures").mkdir(exist_ok=True)
        (actual_rp_pack_dir / "textures" / "items").mkdir(exist_ok=True)
        (actual_rp_pack_dir / "textures" / "items" / "custom_sword.png").write_text("png_data")
        (actual_rp_pack_dir / "pack_icon.png").write_text("icon_data") # Add pack icon to RP

        # --- Step 3: Build .mcaddon ---
        mcaddon_output_path = integration_temp_dir / f"{addon_name}.mcaddon"
        build_data = {
            "source_directories": [str(actual_bp_pack_dir), str(actual_rp_pack_dir)],
            "output_path": str(mcaddon_output_path),
            "metadata": {"addon_name": addon_name}
        }
        build_result_str = agent.build_mcaddon_tool(json.dumps(build_data))
        build_result = json.loads(build_result_str)

        assert build_result["success"] is True
        assert mcaddon_output_path.exists()

        with zipfile.ZipFile(mcaddon_output_path, 'r') as zf:
            namelist = zf.namelist()
            assert f"{actual_bp_pack_dir.name}/manifest.json" in namelist
            assert f"{actual_bp_pack_dir.name}/items/custom_sword.json" in namelist
            assert f"{actual_rp_pack_dir.name}/manifest.json" in namelist
            assert f"{actual_rp_pack_dir.name}/textures/items/custom_sword.png" in namelist
            assert f"{actual_rp_pack_dir.name}/pack_icon.png" in namelist
            assert len(namelist) == 5

        # --- Step 4: Validate (using build_mcaddon_tool's post_validation) ---
        assert build_result["post_validation"]["is_valid_zip"] is True
        assert build_result["post_validation"]["contains_manifests"] is True

        # --- Step 5: Use validate_package_tool (requires extracting first) ---
        # Create a temporary directory to extract the mcaddon contents
        extracted_addon_dir = integration_temp_dir / "extracted_addon"
        extracted_addon_dir.mkdir()
        with zipfile.ZipFile(mcaddon_output_path, 'r') as zf:
            zf.extractall(extracted_addon_dir)

        # Paths to the extracted behavior and resource packs
        extracted_bp_path = extracted_addon_dir / actual_bp_pack_dir.name
        extracted_rp_path = extracted_addon_dir / actual_rp_pack_dir.name
        assert extracted_bp_path.exists()
        assert extracted_rp_path.exists()

        validation_input = {
            "package_paths": [str(extracted_bp_path), str(extracted_rp_path)],
            "requirements": {}
        }
        validation_tool_result_str = agent.validate_package_tool(json.dumps(validation_input))
        validation_tool_result = json.loads(validation_tool_result_str)

        assert validation_tool_result["success"] is True
        val_results = validation_tool_result["validation_results"]
        assert val_results["overall_valid"] is True
        assert not val_results["critical_errors"] # Should be no critical errors for this setup
        assert len(val_results["package_validations"]) == 2
        assert val_results["package_validations"][0]["is_valid"] is True # BP
        assert val_results["package_validations"][1]["is_valid"] is True # RP
        # Quality score might not be 100 if there are warnings (e.g. missing optional dirs)
        # but it should be high for this basic valid structure.
        assert val_results["quality_score"] > 70
        assert val_results["bedrock_compatibility"] in ["fully_compatible", "mostly_compatible"]


def main():
    pytest.main([__file__, "-s", "-v"])

if __name__ == "__main__":
    main()
