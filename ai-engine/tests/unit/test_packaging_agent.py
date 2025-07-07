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

    def test_generate_behavior_manifest_basic(self, packaging_agent: PackagingAgent):
        package_info = {
            "name": "Test Behavior Pack",
            "description": "A test behavior pack.",
            "version": [1, 2, 3],
            "min_engine_version": [1, 19, 50]
        }
        manifest = packaging_agent._generate_behavior_manifest(package_info, [], [])

        assert manifest["format_version"] == 2
        assert manifest["header"]["name"] == "Test Behavior Pack"
        assert manifest["header"]["description"] == "A test behavior pack."
        assert uuid.UUID(manifest["header"]["uuid"]) # Valid UUID
        assert manifest["header"]["version"] == [1, 2, 3]
        assert manifest["header"]["min_engine_version"] == [1, 19, 50]
        assert len(manifest["modules"]) == 1
        assert manifest["modules"][0]["type"] == "data"
        assert uuid.UUID(manifest["modules"][0]["uuid"])
        assert manifest["modules"][0]["version"] == [1, 2, 3]

    def test_generate_resource_manifest_basic(self, packaging_agent: PackagingAgent):
        package_info = {
            "name": "Test Resource Pack",
            "description": "A test resource pack.",
            "version": [0, 1, 0],
        }
        manifest = packaging_agent._generate_resource_manifest(package_info, [])

        assert manifest["format_version"] == 2
        assert manifest["header"]["name"] == "Test Resource Pack"
        assert uuid.UUID(manifest["header"]["uuid"])
        assert manifest["header"]["version"] == [0, 1, 0]
        assert manifest["header"]["min_engine_version"] == [1, 20, 0] # Default
        assert len(manifest["modules"]) == 1
        assert manifest["modules"][0]["type"] == "resources"
        assert uuid.UUID(manifest["modules"][0]["uuid"])
        assert manifest["modules"][0]["version"] == [0, 1, 0]

    def test_generate_manifests_tool_output_files(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        manifest_data = {
            "package_info": {
                "name": "My Full Addon",
                "description": "Behavior and Resource Packs",
                "version": [1, 0, 0],
                "output_directory": temp_output_dir, # Specify output dir
                "has_behavior_pack": True,
                "has_resource_pack": True
            },
            "dependencies": [],
            "capabilities": ["scripting"]
        }
        result_str = packaging_agent.generate_manifests_tool(json.dumps(manifest_data))
        result = json.loads(result_str)

        assert result["success"] is True
        assert result["behavior_manifest_path"] is not None
        assert result["resource_manifest_path"] is not None

        bp_manifest_path = Path(result["behavior_manifest_path"])
        rp_manifest_path = Path(result["resource_manifest_path"])

        assert bp_manifest_path.exists()
        assert rp_manifest_path.exists()
        assert bp_manifest_path.parent.name == "behavior_pack"
        assert rp_manifest_path.parent.name == "resource_pack"
        assert bp_manifest_path.parent.parent == Path(temp_output_dir)
        assert rp_manifest_path.parent.parent == Path(temp_output_dir)

        with open(bp_manifest_path, 'r') as f:
            bp_content = json.load(f)
        with open(rp_manifest_path, 'r') as f:
            rp_content = json.load(f)

        assert bp_content["header"]["name"] == "My Full Addon" # Default name from package_info
        assert rp_content["header"]["name"] == "My Full Addon" # Default name from package_info
        assert len(bp_content["modules"]) == 2 # data and script
        assert any(module["type"] == "script" for module in bp_content["modules"])

    def test_generate_manifests_tool_only_bp(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        manifest_data = {
            "package_info": {
                "name": "BP Only",
                "output_directory": temp_output_dir,
                "has_behavior_pack": True,
                "has_resource_pack": False # Explicitly false
            }
        }
        result_str = packaging_agent.generate_manifests_tool(json.dumps(manifest_data))
        result = json.loads(result_str)

        assert result["success"] is True
        assert result["behavior_manifest_path"] is not None
        assert result["resource_manifest_path"] is None
        assert Path(result["behavior_manifest_path"]).exists()

    def test_generate_manifests_tool_only_rp(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        manifest_data = {
            "package_info": {
                "name": "RP Only",
                "output_directory": temp_output_dir,
                "has_behavior_pack": False, # Explicitly false
                "has_resource_pack": True
            }
        }
        result_str = packaging_agent.generate_manifests_tool(json.dumps(manifest_data))
        result = json.loads(result_str)

        assert result["success"] is True
        assert result["behavior_manifest_path"] is None
        assert result["resource_manifest_path"] is not None
        assert Path(result["resource_manifest_path"]).exists()

    def test_generate_manifests_with_dependencies_and_capabilities(self, packaging_agent: PackagingAgent):
        package_info = {
            "name": "Complex BP",
            "version": [1,0,0]
        }
        dependencies = [
            {"uuid": str(uuid.uuid4()), "version": [1,0,0]},
            {"module_id": "Minecraft", "version": [1,19,0]} # Example by module_id
        ]
        capabilities = ["scripting", "experimental_custom_ui"]

        manifest = packaging_agent._generate_behavior_manifest(package_info, dependencies, capabilities)

        assert "dependencies" in manifest
        assert len(manifest["dependencies"]) == 2
        assert manifest["dependencies"][0]["uuid"] is not None
        assert manifest["dependencies"][1]["module_id"] == "Minecraft"

        assert "capabilities" in manifest
        assert "scripting" in manifest["capabilities"]
        assert "experimental_custom_ui" in manifest["capabilities"]
        assert len(manifest["modules"]) == 2 # data and script (due to "scripting" capability)

    def test_manifest_uuids_are_unique(self, packaging_agent: PackagingAgent):
        # Test that multiple calls generate unique UUIDs where expected
        bp1_header_uuid = uuid.UUID(packaging_agent._generate_behavior_manifest({},[],[])["header"]["uuid"])
        bp1_module_uuid = uuid.UUID(packaging_agent._generate_behavior_manifest({},[],[])["modules"][0]["uuid"])

        bp2_header_uuid = uuid.UUID(packaging_agent._generate_behavior_manifest({},[],[])["header"]["uuid"])
        bp2_module_uuid = uuid.UUID(packaging_agent._generate_behavior_manifest({},[],[])["modules"][0]["uuid"])

        rp1_header_uuid = uuid.UUID(packaging_agent._generate_resource_manifest({},[])["header"]["uuid"])
        rp1_module_uuid = uuid.UUID(packaging_agent._generate_resource_manifest({},[])["modules"][0]["uuid"])

        assert bp1_header_uuid != bp2_header_uuid
        assert bp1_module_uuid != bp2_module_uuid
        assert bp1_header_uuid != rp1_header_uuid
        assert bp1_module_uuid != rp1_module_uuid

    def test_can_override_uuids_for_testing(self, packaging_agent: PackagingAgent):
        fixed_header_uuid = str(uuid.uuid4())
        fixed_module_uuid = str(uuid.uuid4())
        package_info = {
            "header_uuid": fixed_header_uuid, # For behavior pack header
            "module_uuid_behavior": fixed_module_uuid, # For behavior data module
        }
        manifest = packaging_agent._generate_behavior_manifest(package_info, [], [])
        assert manifest["header"]["uuid"] == fixed_header_uuid
        assert manifest["modules"][0]["uuid"] == fixed_module_uuid

        fixed_header_uuid_rp = str(uuid.uuid4())
        fixed_module_uuid_rp = str(uuid.uuid4())
        package_info_rp = {
            "header_uuid_resource": fixed_header_uuid_rp,
            "module_uuid_resource": fixed_module_uuid_rp
        }
        manifest_rp = packaging_agent._generate_resource_manifest(package_info_rp, [])
        assert manifest_rp["header"]["uuid"] == fixed_header_uuid_rp
        assert manifest_rp["modules"][0]["uuid"] == fixed_module_uuid_rp

# More test classes will follow for structure, packaging, validation etc.

class TestPackagingAgentStructure:
    """Tests for package structure creation."""

    def test_create_base_structure_behavior_pack(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        bp_path = Path(temp_output_dir) / "my_bp"
        result = packaging_agent._create_base_structure("behavior_pack", str(bp_path))

        assert result["package_type"] == "behavior_pack"
        assert Path(result["base_directory"]) == bp_path

        # Check that all defined directories in pack_structures for behavior_pack are created
        for dir_key in packaging_agent.pack_structures["behavior_pack"]:
            if dir_key.endswith('/'): # It's a directory
                expected_dir = bp_path / dir_key.rstrip('/')
                assert expected_dir.exists()
                assert expected_dir.is_dir()
                assert str(expected_dir) in result["created_directories"]

        # Check manifest.json and pack_icon.png are NOT created by _create_base_structure
        assert not (bp_path / "manifest.json").exists()
        assert not (bp_path / "pack_icon.png").exists()


    def test_create_base_structure_resource_pack(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        rp_path = Path(temp_output_dir) / "my_rp"
        result = packaging_agent._create_base_structure("resource_pack", str(rp_path))

        assert result["package_type"] == "resource_pack"
        assert Path(result["base_directory"]) == rp_path

        for dir_key in packaging_agent.pack_structures["resource_pack"]:
            if dir_key.endswith('/'):
                expected_dir = rp_path / dir_key.rstrip('/')
                assert expected_dir.exists()
                assert expected_dir.is_dir()

    def test_create_package_structure_tool_valid_input(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        target_pack_dir = Path(temp_output_dir) / "cool_addon_bp"
        structure_data = {
            "package_type": "behavior_pack",
            "components": [], # No actual components to place in this unit test for structure
            "target_directory": str(target_pack_dir)
        }
        result_str = packaging_agent.create_package_structure_tool(json.dumps(structure_data))
        result = json.loads(result_str)

        assert result["success"] is True
        assert result["package_type"] == "behavior_pack"
        assert Path(result["target_directory"]) == target_pack_dir
        assert target_pack_dir.exists()
        assert (target_pack_dir / "entities").exists() # Check a sample directory
        assert result["structure_validation"]["valid"] is True # Assuming _validate_pack_structure_directories works

    def test_get_target_directory_mapping(self, packaging_agent: PackagingAgent):
        # Behavior Pack
        assert packaging_agent._get_target_directory("entity_definition", "behavior_pack") == "entities"
        assert packaging_agent._get_target_directory("item_definition", "behavior_pack") == "items"
        assert packaging_agent._get_target_directory("block_definition", "behavior_pack") == "blocks"
        assert packaging_agent._get_target_directory("script", "behavior_pack") == "scripts"
        assert packaging_agent._get_target_directory("pack_icon", "behavior_pack") == "" # Root

        # Resource Pack
        assert packaging_agent._get_target_directory("texture_png", "resource_pack") == "textures"
        assert packaging_agent._get_target_directory("model_geo_json", "resource_pack") == "models"
        assert packaging_agent._get_target_directory("sound_ogg", "resource_pack") == "sounds"
        assert packaging_agent._get_target_directory("pack_icon", "resource_pack") == "" # Root

        # Invalid
        assert packaging_agent._get_target_directory("non_existent_type", "behavior_pack") is None
        assert packaging_agent._get_target_directory("texture_png", "invalid_pack_type") is None

    def test_organize_components_placeholder(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        # This test is more about checking the conceptual mapping than actual file ops
        # as _organize_components itself doesn't move files, just plans paths.
        bp_dir = Path(temp_output_dir) / "org_bp"
        packaging_agent._create_base_structure("behavior_pack", str(bp_dir)) # Ensure dir exists for path joining

        components = [
            {"type": "entity_definition", "path": "/dummy/source/creeper.json"},
            {"type": "script", "path": "/dummy/source/main.js"},
            {"type": "unknown_comp", "path": "/dummy/source/mystery.file"}
        ]
        result = packaging_agent._organize_components(components, "behavior_pack", str(bp_dir))

        assert len(result["placed_files"]) == 2
        assert len(result["failed_placements"]) == 1

        placed_targets = [Path(pf["target"]).name for pf in result["placed_files"]]
        assert "creeper.json" in placed_targets
        assert "main.js" in placed_targets

        assert Path(result["placed_files"][0]["target"]).parent.name == "entities" # creeper.json -> entities/
        assert Path(result["placed_files"][1]["target"]).parent.name == "scripts"  # main.js -> scripts/

        assert result["failed_placements"][0]["type"] == "unknown_comp"

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
        source_dirs = [str(sample_bp_dir), str(sample_rp_dir)]

        result = packaging_agent._build_mcaddon_file(source_dirs, str(output_mcaddon_path), {})

        assert result["success"] is True
        assert Path(result["output_path"]) == output_mcaddon_path
        assert output_mcaddon_path.exists()
        assert result["total_files"] == 4 # 2 manifests, 1 entity json, 1 texture png
        assert result["file_size_bytes"] > 0

        # Verify zip contents
        with zipfile.ZipFile(output_mcaddon_path, 'r') as zf:
            namelist = zf.namelist()
            # Check for correct top-level folder names and file paths within them
            assert "sample_bp/manifest.json" in namelist
            assert "sample_bp/entities/my_entity.json" in namelist
            assert "sample_rp/manifest.json" in namelist
            assert "sample_rp/textures/my_texture.png" in namelist
            assert len(namelist) == 4

    def test_build_mcaddon_tool_with_bp_and_rp(self, packaging_agent: PackagingAgent, sample_bp_dir: Path, sample_rp_dir: Path, temp_output_dir: str):
        output_path = Path(temp_output_dir) / "my_super_addon.mcaddon"
        build_data = {
            "source_directories": [str(sample_bp_dir), str(sample_rp_dir)],
            "output_path": str(output_path),
            "metadata": {"addon_name": "My Super Addon"}
        }
        result_str = packaging_agent.build_mcaddon_tool(json.dumps(build_data))
        result = json.loads(result_str)

        assert result["success"] is True
        assert Path(result["output_path"]) == output_path.resolve() # Check resolved path
        assert output_path.exists()
        assert result["post_validation"]["file_exists"] is True
        assert result["post_validation"]["is_valid_zip"] is True
        assert result["post_validation"]["contains_manifests"] is True # Checks for any manifest
        assert len(result["installation_instructions"]) > 0

    def test_build_mcaddon_tool_pre_validation_fails(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        non_existent_dir = Path(temp_output_dir) / "i_do_not_exist"
        output_path = Path(temp_output_dir) / "fail_addon.mcaddon"
        build_data = {
            "source_directories": [str(non_existent_dir)],
            "output_path": str(output_path)
        }
        result_str = packaging_agent.build_mcaddon_tool(json.dumps(build_data))
        result = json.loads(result_str)

        assert result["success"] is False
        assert "Pre-build validation failed" in result["error"]
        assert not output_path.exists()

    def test_pre_build_validation(self, packaging_agent: PackagingAgent, sample_bp_dir: Path, temp_output_dir: str):
        # Valid case
        assert packaging_agent._pre_build_validation([str(sample_bp_dir)])["valid"] is True

        # Missing manifest
        bp_no_manifest = Path(temp_output_dir) / "bp_no_manifest"
        bp_no_manifest.mkdir()
        validation_result = packaging_agent._pre_build_validation([str(bp_no_manifest)])
        assert validation_result["valid"] is False
        assert f"Missing manifest.json in {bp_no_manifest}" in validation_result["errors"]

        # Missing source directory
        non_existent_dir = Path(temp_output_dir) / "ghost_dir"
        validation_result_missing_dir = packaging_agent._pre_build_validation([str(non_existent_dir)])
        assert validation_result_missing_dir["valid"] is False
        assert f"Source directory does not exist: {non_existent_dir}" in validation_result_missing_dir["errors"]

    def test_post_build_validation(self, packaging_agent: PackagingAgent, sample_bp_dir:Path, temp_output_dir:str):
        # Create a valid dummy mcaddon for testing post_build_validation
        valid_mcaddon_path = Path(temp_output_dir) / "valid.mcaddon"
        with zipfile.ZipFile(valid_mcaddon_path, 'w') as zf:
            zf.writestr("sample_bp/manifest.json", "{}") # minimal manifest

        validation_result = packaging_agent._post_build_validation(str(valid_mcaddon_path))
        assert validation_result["file_exists"] is True
        assert validation_result["is_valid_zip"] is True
        assert validation_result["contains_manifests"] is True
        assert validation_result["file_size_ok"] is True # Assuming small file is okay

        # Test with a non-zip file
        not_a_zip_path = Path(temp_output_dir) / "not_a_zip.mcaddon"
        not_a_zip_path.write_text("This is not a zip file.")
        validation_result_bad_zip = packaging_agent._post_build_validation(str(not_a_zip_path))
        assert validation_result_bad_zip["is_valid_zip"] is False
        assert validation_result_bad_zip["contains_manifests"] is False

        # Test with a zip file missing manifests
        zip_no_manifest_path = Path(temp_output_dir) / "no_manifest.mcaddon"
        with zipfile.ZipFile(zip_no_manifest_path, 'w') as zf:
            zf.writestr("some_other_file.txt", "content")
        validation_result_no_manifest = packaging_agent._post_build_validation(str(zip_no_manifest_path))
        assert validation_result_no_manifest["is_valid_zip"] is True
        assert validation_result_no_manifest["contains_manifests"] is False

class TestPackagingAgentValidation:
    """Tests for package validation logic."""

    @pytest.fixture
    def valid_bp_manifest_content(self) -> dict:
        return {
            "format_version": 2,
            "header": {
                "name": "Valid BP",
                "description": "Test",
                "uuid": str(uuid.uuid4()),
                "version": [1,0,0],
                "min_engine_version": [1,20,0]
            },
            "modules": [
                {"type": "data", "uuid": str(uuid.uuid4()), "version": [1,0,0]}
            ]
        }

    @pytest.fixture
    def valid_rp_manifest_content(self) -> dict:
        return {
            "format_version": 2,
            "header": {
                "name": "Valid RP",
                "description": "Test",
                "uuid": str(uuid.uuid4()),
                "version": [1,0,0],
                "min_engine_version": [1,20,0]
            },
            "modules": [
                {"type": "resources", "uuid": str(uuid.uuid4()), "version": [1,0,0]}
            ]
        }

    def test_validate_manifest_file_valid(self, packaging_agent: PackagingAgent, temp_output_dir: str, valid_bp_manifest_content: dict):
        manifest_path = Path(temp_output_dir) / "manifest.json"
        manifest_path.write_text(json.dumps(valid_bp_manifest_content))

        result = packaging_agent._validate_manifest_file(str(manifest_path))
        assert result["valid"] is True
        assert not result["errors"]
        assert not result["warnings"]

    def test_validate_manifest_file_invalid_json(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        manifest_path = Path(temp_output_dir) / "manifest.json"
        manifest_path.write_text("this is not json")
        result = packaging_agent._validate_manifest_file(str(manifest_path))
        assert result["valid"] is False
        assert "Invalid JSON format" in result["errors"][0]

    def test_validate_manifest_file_missing_fields(self, packaging_agent: PackagingAgent, temp_output_dir: str, valid_bp_manifest_content: dict):
        invalid_content = valid_bp_manifest_content.copy()
        del invalid_content["header"]["uuid"] # Remove a required field
        manifest_path = Path(temp_output_dir) / "manifest.json"
        manifest_path.write_text(json.dumps(invalid_content))

        result = packaging_agent._validate_manifest_file(str(manifest_path))
        assert result["valid"] is False
        assert any("Missing 'uuid' in manifest header" in error for error in result["errors"])

    def test_validate_manifest_file_script_entry_missing(self, packaging_agent: PackagingAgent, temp_output_dir: str, valid_bp_manifest_content: dict):
        manifest_content = valid_bp_manifest_content.copy()
        script_module_uuid = str(uuid.uuid4())
        manifest_content["modules"].append({
            "type": "script",
            "language": "javascript",
            "uuid": script_module_uuid,
            "version": [0,0,1],
            "entry": "scripts/main.js" # This file won't exist
        })
        manifest_path = Path(temp_output_dir) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_content))

        # The manifest path itself is in temp_output_dir. We need a scripts folder inside a pack folder.
        # Let's assume the manifest is inside a pack folder for this test.
        pack_dir = Path(temp_output_dir) / "my_test_pack"
        pack_dir.mkdir(exist_ok=True)
        actual_manifest_path_in_pack = pack_dir / "manifest.json"
        actual_manifest_path_in_pack.write_text(json.dumps(manifest_content))

        # (pack_dir / "scripts").mkdir() # Don't create main.js to test error

        result = packaging_agent._validate_manifest_file(str(actual_manifest_path_in_pack))
        assert result["valid"] is False # Should be an error if script entry doesn't exist
        assert any("Script entry point 'scripts/main.js' defined in manifest module 1 does not exist" in error for error in result["errors"])


    def test_is_valid_uuid_util(self, packaging_agent: PackagingAgent):
        assert packaging_agent._is_valid_uuid(str(uuid.uuid4())) is True
        assert packaging_agent._is_valid_uuid("not-a-uuid") is False
        assert packaging_agent._is_valid_uuid(None) is False # type: ignore

    def test_validate_package_structure_valid(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        bp_path = Path(temp_output_dir) / "test_bp"
        bp_path.mkdir()
        (bp_path / "entities").mkdir() # A required dir
        (bp_path / "pack_icon.png").touch() # A required file

        result = packaging_agent._validate_package_structure(str(bp_path), "behavior_pack")
        assert result["valid"] is True # Currently only issues warnings
        assert not result["errors"]
        assert not result["warnings"] # No unexpected files, required icon exists
        assert not result["missing_required_files"]
        assert not result["unexpected_root_items"]

    def test_validate_package_structure_missing_icon(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        bp_path = Path(temp_output_dir) / "test_bp_no_icon"
        bp_path.mkdir()
        (bp_path / "entities").mkdir()
        # pack_icon.png is missing

        result = packaging_agent._validate_package_structure(str(bp_path), "behavior_pack")
        assert result["valid"] is True # Still true as it's a warning
        assert "Missing pack_icon.png" in result["warnings"][0]
        assert "pack_icon.png" in result["missing_required_files"]

    def test_validate_package_structure_unexpected_file(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        bp_path = Path(temp_output_dir) / "test_bp_extra"
        bp_path.mkdir()
        (bp_path / "entities").mkdir()
        (bp_path / "pack_icon.png").touch()
        (bp_path / "my_random_file.txt").write_text("hello")

        result = packaging_agent._validate_package_structure(str(bp_path), "behavior_pack")
        assert result["valid"] is True # Still true
        assert "Unexpected file or folder at pack root: my_random_file.txt" in result["warnings"][0]
        assert "my_random_file.txt" in result["unexpected_root_items"]

    def test_validate_package_size(self, packaging_agent: PackagingAgent, temp_output_dir: str):
        pack_path = Path(temp_output_dir) / "size_test_pack"
        pack_path.mkdir()
        (pack_path / "file1.txt").write_text("a" * 1024) # 1KB
        (pack_path / "file2.dat").write_text("b" * 2048) # 2KB

        result = packaging_agent._validate_package_size(str(pack_path))
        assert result["total_size_bytes"] == 1024 + 2048
        assert result["file_count"] == 2
        assert result["within_size_limit"] is True # Assuming default limit is much larger
        assert result["within_file_limit"] is True # Assuming default limit is much larger

    def test_validate_single_package_overall(self, packaging_agent: PackagingAgent, temp_output_dir: str, valid_bp_manifest_content: dict):
        # Setup a mostly valid behavior pack
        bp_package_path = Path(temp_output_dir) / "my_behavior_pack"
        bp_package_path.mkdir()
        (bp_package_path / "manifest.json").write_text(json.dumps(valid_bp_manifest_content))
        (bp_package_path / "entities").mkdir() # Expected dir
        (bp_package_path / "scripts").mkdir()  # Expected dir for scripts if manifest implies
        (bp_package_path / "pack_icon.png").touch()

        result = packaging_agent._validate_single_package(str(bp_package_path), {}) # requirements can be empty for this test

        assert result["path"] == str(bp_package_path)
        assert result["is_valid"] is True # Should be true if no critical errors
        assert not result["critical_errors"]
        # May have warnings if e.g. _validate_pack_structure_directories has other expectations not met
        # For this setup, it should be clean based on current validation logic.
        assert not result["warnings"]
        assert result["manifest_validation"]["valid"] is True
        assert result["structure_validation"]["valid"] is True # From _validate_pack_structure_directories
        assert result["size_validation"]["valid"] is True
        assert result["file_content_validation"]["passed"] is True

    def test_validate_single_package_with_forbidden_file(self, packaging_agent: PackagingAgent, temp_output_dir: str, valid_bp_manifest_content: dict):
        bp_package_path = Path(temp_output_dir) / "bad_bp"
        bp_package_path.mkdir()
        (bp_package_path / "manifest.json").write_text(json.dumps(valid_bp_manifest_content))
        (bp_package_path / "virus.exe").write_text("evil") # Forbidden file

        result = packaging_agent._validate_single_package(str(bp_package_path), {})
        assert result["is_valid"] is False
        assert any("Forbidden file type found: " in error for error in result["critical_errors"])
        assert result["file_content_validation"]["passed"] is False

    def test_validate_package_tool_overall(self, packaging_agent: PackagingAgent, temp_output_dir:str, valid_bp_manifest_content:dict, valid_rp_manifest_content:dict):
        # Setup BP
        bp_path = Path(temp_output_dir) / "sample_bp_for_tool"
        bp_path.mkdir()
        (bp_path / "manifest.json").write_text(json.dumps(valid_bp_manifest_content))
        (bp_path / "entities").mkdir()
        (bp_path / "pack_icon.png").touch()

        # Setup RP
        rp_path = Path(temp_output_dir) / "sample_rp_for_tool"
        rp_path.mkdir()
        (rp_path / "manifest.json").write_text(json.dumps(valid_rp_manifest_content))
        (rp_path / "textures").mkdir()
        (rp_path / "pack_icon.png").touch()

        validation_input = {
            "package_paths": [str(bp_path), str(rp_path)],
            "requirements": {} # E.g. specific Bedrock version, etc. Not deeply tested here.
        }
        result_str = packaging_agent.validate_package_tool(json.dumps(validation_input))
        result = json.loads(result_str)

        assert result["success"] is True
        val_results = result["validation_results"]
        assert val_results["overall_valid"] is True
        assert not val_results["critical_errors"]
        assert len(val_results["package_validations"]) == 2
        assert val_results["package_validations"][0]["is_valid"] is True
        assert val_results["package_validations"][1]["is_valid"] is True
        assert val_results["quality_score"] == 100.0 # Assuming no warnings from this setup
        assert val_results["bedrock_compatibility"] == "fully_compatible"


def main():
    # Helper to run pytest from script, useful for iterative dev
    pytest.main([__file__])

if __name__ == "__main__":
    main()
