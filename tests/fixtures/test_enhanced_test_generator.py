"""Unit tests for enhanced_test_generator module."""

import sys
import tempfile
import zipfile
from pathlib import Path

import pytest
import json

# Add fixtures directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_test_generator import (
    EnhancedTestModGenerator,
    create_curated_test_suite,
)


class TestEnhancedTestModGenerator:
    """Test suite for EnhancedTestModGenerator class."""

    def test_generator_initialization_with_default_dir(self):
        """Test that generator initializes with default directory."""
        generator = EnhancedTestModGenerator()
        
        assert generator.output_dir is not None
        assert generator.created_mods == []

    def test_generator_initialization_with_custom_dir(self):
        """Test that generator initializes with custom directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            assert str(generator.output_dir) == tmpdir
            assert generator.created_mods == []

    def test_generator_creates_output_directory(self):
        """Test that generator creates output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "test_mods" / "nested"
            
            generator = EnhancedTestModGenerator(str(output_dir))
            
            assert output_dir.exists()

    def test_create_entity_mod_passive(self):
        """Test creation of passive entity mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_entity_mod("passive")
            
            assert jar_path.exists()
            assert jar_path.suffix == ".jar"
            assert "passive" in str(jar_path)

    def test_create_entity_mod_hostile(self):
        """Test creation of hostile entity mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_entity_mod("hostile")
            
            assert jar_path.exists()
            assert jar_path.suffix == ".jar"
            assert "hostile" in str(jar_path)

    def test_create_entity_mod_custom_ai(self):
        """Test creation of custom AI entity mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_entity_mod("custom_ai")
            
            assert jar_path.exists()
            assert jar_path.suffix == ".jar"

    def test_create_entity_mod_contains_fabric_mod_json(self):
        """Test that entity mod contains fabric.mod.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_entity_mod("passive")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                assert 'fabric.mod.json' in zf.namelist()

    def test_create_entity_mod_contains_texture(self):
        """Test that entity mod contains texture file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_entity_mod("passive")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                texture_files = [f for f in zf.namelist() if f.endswith('.png')]
                assert len(texture_files) > 0

    def test_create_entity_mod_contains_java_code(self):
        """Test that entity mod contains Java source files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_entity_mod("passive")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                java_files = [f for f in zf.namelist() if f.endswith('.java')]
                assert len(java_files) > 0

    def test_create_gui_mod_inventory(self):
        """Test creation of inventory GUI mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_gui_mod("inventory")
            
            assert jar_path.exists()
            assert jar_path.suffix == ".jar"

    def test_create_gui_mod_config(self):
        """Test creation of config GUI mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_gui_mod("config")
            
            assert jar_path.exists()
            assert jar_path.suffix == ".jar"

    def test_create_gui_mod_hud(self):
        """Test creation of HUD GUI mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_gui_mod("hud")
            
            assert jar_path.exists()
            assert jar_path.suffix == ".jar"

    def test_create_gui_mod_contains_java_code(self):
        """Test that GUI mod contains Java source files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_gui_mod("inventory")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                java_files = [f for f in zf.namelist() if f.endswith('.java')]
                assert len(java_files) > 0

    def test_create_complex_logic_mod_machinery(self):
        """Test creation of machinery logic mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_complex_logic_mod("machinery")
            
            assert jar_path.exists()
            assert jar_path.suffix == ".jar"

    def test_create_complex_logic_mod_multiblock(self):
        """Test creation of multiblock logic mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_complex_logic_mod("multiblock")
            
            assert jar_path.exists()
            assert jar_path.suffix == ".jar"

    def test_create_complex_logic_mod_automation(self):
        """Test creation of automation logic mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_complex_logic_mod("automation")
            
            assert jar_path.exists()
            assert jar_path.suffix == ".jar"

    def test_create_complex_logic_mod_contains_java_code(self):
        """Test that complex logic mod contains Java source files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_complex_logic_mod("machinery")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                java_files = [f for f in zf.namelist() if f.endswith('.java')]
                assert len(java_files) > 0

    def test_created_mods_are_tracked(self):
        """Test that created mods are tracked in created_mods list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar1 = generator.create_entity_mod("passive")
            jar2 = generator.create_gui_mod("inventory")
            
            assert len(generator.created_mods) == 2
            assert jar1 in generator.created_mods
            assert jar2 in generator.created_mods

    def test_create_all_test_mods(self):
        """Test creating all test mod categories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            all_mods = generator.create_all_test_mods()
            
            # Should create 9 mods (3 entity types + 3 GUI types + 3 logic types)
            assert len(all_mods) == 9
            # All should exist
            assert all(m.exists() for m in all_mods)

    def test_entity_mod_fabric_mod_json_structure(self):
        """Test that entity mod fabric.mod.json has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_entity_mod("passive")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                fabric_mod_content = zf.read('fabric.mod.json').decode('utf-8')
                fabric_mod = json.loads(fabric_mod_content)
                
                assert 'schemaVersion' in fabric_mod
                assert 'id' in fabric_mod
                assert 'version' in fabric_mod
                assert 'name' in fabric_mod
                assert 'description' in fabric_mod

    def test_gui_mod_fabric_mod_json_environment_client(self):
        """Test that GUI mod fabric.mod.json has client environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_gui_mod("inventory")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                fabric_mod_content = zf.read('fabric.mod.json').decode('utf-8')
                fabric_mod = json.loads(fabric_mod_content)
                
                assert fabric_mod.get('environment') == 'client'

    def test_complex_logic_mod_contains_json_files(self):
        """Test that complex logic mod contains JSON configuration files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_complex_logic_mod("machinery")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                json_files = [f for f in zf.namelist() if f.endswith('.json')]
                # Should have at least fabric.mod.json
                assert len(json_files) > 0

    def test_entity_mod_contains_loot_table(self):
        """Test that entity mod contains loot table JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_entity_mod("passive")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                loot_table_files = [f for f in zf.namelist() if 'loot_tables' in f]
                assert len(loot_table_files) > 0

    def test_generator_cleanup(self):
        """Test that cleanup method removes created mods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar1 = generator.create_entity_mod("passive")
            jar2 = generator.create_gui_mod("inventory")
            
            assert jar1.exists()
            assert jar2.exists()
            
            generator.cleanup()
            
            assert not jar1.exists()
            assert not jar2.exists()
            assert len(generator.created_mods) == 0

    def test_create_curated_test_suite_returns_dict(self):
        """Test that create_curated_test_suite returns correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_suite = create_curated_test_suite(tmpdir)
            
            assert isinstance(test_suite, dict)
            assert 'entities' in test_suite
            assert 'gui_mods' in test_suite
            assert 'complex_logic' in test_suite

    def test_create_curated_test_suite_creates_all_categories(self):
        """Test that curated test suite creates all mod categories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_suite = create_curated_test_suite(tmpdir)
            
            # Should create 3 entities, 3 GUIs, 3 logic mods
            total_mods = sum(len(mods) for mods in test_suite.values())
            assert total_mods == 9

    def test_gui_mod_contains_texture(self):
        """Test that GUI mod contains texture file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_gui_mod("inventory")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                texture_files = [f for f in zf.namelist() if f.endswith('.png')]
                assert len(texture_files) > 0

    def test_entity_mod_contains_entity_model_json(self):
        """Test that entity mod contains entity model JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_entity_mod("passive")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                model_files = [f for f in zf.namelist() if 'models/entity' in f]
                assert len(model_files) > 0

    def test_create_jar_is_valid_zip(self):
        """Test that created JAR files are valid ZIP archives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            jar_path = generator.create_entity_mod("passive")
            
            # Should be able to open as ZIP without errors
            with zipfile.ZipFile(jar_path, 'r') as zf:
                assert len(zf.namelist()) > 0

    def test_multiple_mods_in_separate_directories(self):
        """Test that different mod types are created in separate directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = EnhancedTestModGenerator(tmpdir)
            
            entity_jar = generator.create_entity_mod("passive")
            gui_jar = generator.create_gui_mod("inventory")
            logic_jar = generator.create_complex_logic_mod("machinery")
            
            # Different directory structure
            assert "entities" in str(entity_jar)
            assert "gui_mods" in str(gui_jar)
            assert "complex_logic" in str(logic_jar)
