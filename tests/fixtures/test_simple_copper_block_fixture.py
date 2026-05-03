"""Unit tests for simple_copper_block fixture module."""

import sys
import tempfile
import zipfile
import json
from pathlib import Path

import pytest

# Add fixtures directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from simple_copper_block import (
    create_simple_copper_block_jar,
    get_expected_analysis_result,
    get_expected_bedrock_block,
)


class TestSimpleCopperBlockFixture:
    """Test suite for simple_copper_block fixture module."""

    def test_create_simple_copper_block_jar_creates_file(self):
        """Test that create_simple_copper_block_jar creates a JAR file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Need to mock the fixtures directory
            import simple_copper_block
            original_file = simple_copper_block.__file__
            
            # Create JAR in temp directory
            jar_path = Path(tmpdir) / "simple_copper_block.jar"
            
            # Call the function to ensure it works
            result_path = create_simple_copper_block_jar()
            
            # Check that a JAR was created
            assert result_path.exists()
            assert result_path.suffix == ".jar"

    def test_jar_contains_fabric_mod_json(self):
        """Test that JAR contains fabric.mod.json."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            assert 'fabric.mod.json' in zf.namelist()

    def test_fabric_mod_json_has_correct_id(self):
        """Test that fabric.mod.json has correct mod ID."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            fabric_mod_content = zf.read('fabric.mod.json').decode('utf-8')
            fabric_mod = json.loads(fabric_mod_content)
            
            assert fabric_mod['id'] == 'simple_copper'

    def test_fabric_mod_json_has_correct_version(self):
        """Test that fabric.mod.json has correct version."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            fabric_mod_content = zf.read('fabric.mod.json').decode('utf-8')
            fabric_mod = json.loads(fabric_mod_content)
            
            assert fabric_mod['version'] == '1.0.0'

    def test_fabric_mod_json_has_required_fields(self):
        """Test that fabric.mod.json has all required fields."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            fabric_mod_content = zf.read('fabric.mod.json').decode('utf-8')
            fabric_mod = json.loads(fabric_mod_content)
            
            required_fields = ['schemaVersion', 'id', 'version', 'name', 'description', 'authors', 'license']
            for field in required_fields:
                assert field in fabric_mod

    def test_jar_contains_texture_file(self):
        """Test that JAR contains block texture file."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            texture_files = [f for f in zf.namelist() if f.endswith('.png')]
            assert len(texture_files) > 0
            assert any('polished_copper' in f for f in texture_files)

    def test_jar_contains_manifest(self):
        """Test that JAR contains META-INF/MANIFEST.MF."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            assert 'META-INF/MANIFEST.MF' in zf.namelist()

    def test_jar_contains_java_source_files(self):
        """Test that JAR contains Java source files."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            java_files = [f for f in zf.namelist() if f.endswith('.java')]
            assert len(java_files) > 0

    def test_jar_contains_java_class_files(self):
        """Test that JAR contains Java class files."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            class_files = [f for f in zf.namelist() if f.endswith('.class')]
            assert len(class_files) > 0

    def test_jar_contains_mixins_json(self):
        """Test that JAR contains mixins configuration."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            assert 'simple_copper.mixins.json' in zf.namelist()

    def test_jar_contains_pack_mcmeta(self):
        """Test that JAR contains pack.mcmeta."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            assert 'pack.mcmeta' in zf.namelist()

    def test_texture_file_is_valid_png(self):
        """Test that texture file is valid PNG format."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            texture_files = [f for f in zf.namelist() if 'polished_copper.png' in f and not f.endswith('.mcmeta')]
            assert len(texture_files) > 0
            
            for texture_file in texture_files:
                png_data = zf.read(texture_file)
                # PNG signature or PIL-generated image
                assert png_data[:4] == b'\x89PNG' or b'PNG' in png_data[:20]

    def test_jar_contains_texture_mcmeta(self):
        """Test that texture has associated .mcmeta file."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            mcmeta_files = [f for f in zf.namelist() if f.endswith('.mcmeta')]
            assert len(mcmeta_files) > 0

    def test_pack_mcmeta_has_correct_format(self):
        """Test that pack.mcmeta has correct format."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            pack_mcmeta_content = zf.read('pack.mcmeta').decode('utf-8')
            pack_mcmeta = json.loads(pack_mcmeta_content)
            
            assert 'pack' in pack_mcmeta
            assert 'pack_format' in pack_mcmeta['pack']
            assert 'description' in pack_mcmeta['pack']

    def test_jar_is_valid_zip(self):
        """Test that JAR is a valid ZIP file."""
        result_path = create_simple_copper_block_jar()
        
        # Should be able to open without errors
        with zipfile.ZipFile(result_path, 'r') as zf:
            files = zf.namelist()
            assert len(files) > 0

    def test_jar_file_size_reasonable(self):
        """Test that JAR file has reasonable size."""
        result_path = create_simple_copper_block_jar()
        
        file_size = result_path.stat().st_size
        # Should be at least 1KB but not huge
        assert 1024 < file_size < 10 * 1024 * 1024  # Between 1KB and 10MB

    def test_get_expected_analysis_result_returns_dict(self):
        """Test that get_expected_analysis_result returns dictionary."""
        result = get_expected_analysis_result()
        
        assert isinstance(result, dict)

    def test_get_expected_analysis_result_has_required_fields(self):
        """Test that expected analysis result has required fields."""
        result = get_expected_analysis_result()
        
        assert 'success' in result
        assert 'registry_name' in result
        assert 'texture_path' in result
        assert 'errors' in result

    def test_get_expected_analysis_result_success_true(self):
        """Test that expected analysis result indicates success."""
        result = get_expected_analysis_result()
        
        assert result['success'] is True

    def test_get_expected_analysis_result_registry_name(self):
        """Test that expected registry name is correct."""
        result = get_expected_analysis_result()
        
        assert result['registry_name'] == 'simple_copper:polished_copper'

    def test_get_expected_analysis_result_texture_path(self):
        """Test that expected texture path is correct."""
        result = get_expected_analysis_result()
        
        assert 'polished_copper.png' in result['texture_path']
        assert 'simple_copper' in result['texture_path']

    def test_get_expected_bedrock_block_returns_dict(self):
        """Test that get_expected_bedrock_block returns dictionary."""
        result = get_expected_bedrock_block()
        
        assert isinstance(result, dict)

    def test_get_expected_bedrock_block_has_format_version(self):
        """Test that bedrock block has format version."""
        result = get_expected_bedrock_block()
        
        assert 'format_version' in result

    def test_get_expected_bedrock_block_has_minecraft_block(self):
        """Test that bedrock block has minecraft:block key."""
        result = get_expected_bedrock_block()
        
        assert 'minecraft:block' in result

    def test_get_expected_bedrock_block_identifier(self):
        """Test that bedrock block has correct identifier."""
        result = get_expected_bedrock_block()
        
        block = result['minecraft:block']
        assert 'description' in block
        assert 'identifier' in block['description']
        assert block['description']['identifier'] == 'simple_copper:polished_copper'

    def test_get_expected_bedrock_block_components(self):
        """Test that bedrock block has components."""
        result = get_expected_bedrock_block()
        
        block = result['minecraft:block']
        assert 'components' in block

    def test_get_expected_bedrock_block_destroy_time(self):
        """Test that bedrock block has destroy time."""
        result = get_expected_bedrock_block()
        
        block = result['minecraft:block']
        components = block['components']
        assert 'minecraft:destroy_time' in components
        assert components['minecraft:destroy_time'] == 3.0

    def test_get_expected_bedrock_block_explosion_resistance(self):
        """Test that bedrock block has explosion resistance."""
        result = get_expected_bedrock_block()
        
        block = result['minecraft:block']
        components = block['components']
        assert 'minecraft:explosion_resistance' in components
        assert components['minecraft:explosion_resistance'] == 6.0

    def test_get_expected_bedrock_block_material_instances(self):
        """Test that bedrock block has material instances."""
        result = get_expected_bedrock_block()
        
        block = result['minecraft:block']
        components = block['components']
        assert 'minecraft:material_instances' in components

    def test_jar_contains_item_texture(self):
        """Test that JAR contains item texture."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            item_textures = [f for f in zf.namelist() if 'items/' in f or 'item/' in f]
            assert len(item_textures) > 0

    def test_java_source_contains_block_class(self):
        """Test that Java source contains block class definition."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            java_files = [f for f in zf.namelist() if f.endswith('.java')]
            
            has_block_class = False
            for java_file in java_files:
                content = zf.read(java_file).decode('utf-8')
                if 'class' in content and ('Block' in content or 'block' in content):
                    has_block_class = True
                    break
            
            assert has_block_class

    def test_fabric_mod_entrypoints_defined(self):
        """Test that fabric.mod.json has entrypoints."""
        result_path = create_simple_copper_block_jar()
        
        with zipfile.ZipFile(result_path, 'r') as zf:
            fabric_mod_content = zf.read('fabric.mod.json').decode('utf-8')
            fabric_mod = json.loads(fabric_mod_content)
            
            assert 'entrypoints' in fabric_mod
            assert 'main' in fabric_mod['entrypoints']

    def test_fixture_reproducible(self):
        """Test that fixture can be created multiple times without error."""
        paths = []
        for _ in range(3):
            path = create_simple_copper_block_jar()
            assert path.exists()
            paths.append(path)
        
        # All should be valid JARs
        for path in paths:
            with zipfile.ZipFile(path, 'r') as zf:
                assert len(zf.namelist()) > 0
