"""
Unit tests for JavaAnalyzerAgent MVP functionality.
Implements tests for Issue #167: Parse registry name & texture path in JavaAnalyzerAgent
"""

import pytest
import tempfile
import zipfile
import json
import os
from pathlib import Path

from java_analyzer_agent import JavaAnalyzerAgent


class TestJavaAnalyzerMVP:
    """Test JavaAnalyzerAgent MVP-specific functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create JavaAnalyzerAgent instance for testing."""
        return JavaAnalyzerAgent()

    @pytest.fixture
    def simple_jar_with_texture(self):
        """Create a simple test JAR with texture and metadata."""
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as jar_file:
            with zipfile.ZipFile(jar_file.name, 'w') as zf:
                # Add fabric.mod.json
                fabric_mod = {
                    "schemaVersion": 1,
                    "id": "simple_copper",
                    "version": "1.0.0",
                    "name": "Simple Copper Block"
                }
                zf.writestr('fabric.mod.json', json.dumps(fabric_mod))

                # Add a block texture
                zf.writestr('assets/simple_copper/textures/block/polished_copper.png', b'fake_png_data')

                # Add a block class
                zf.writestr('com/example/PolishedCopperBlock.class', b'fake_class_data')

            yield jar_file.name

        # Cleanup
        os.unlink(jar_file.name)

    @pytest.fixture
    def jar_with_java_source(self):
        """Create a JAR with Java source containing @Register annotation."""
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as jar_file:
            with zipfile.ZipFile(jar_file.name, 'w') as zf:
                # Add fabric.mod.json
                fabric_mod = {
                    "schemaVersion": 1,
                    "id": "copper_mod",
                    "version": "1.0.0"
                }
                zf.writestr('fabric.mod.json', json.dumps(fabric_mod))

                # Add Java source with @Register annotation
                java_source = '''
package com.example;

import net.minecraft.block.Block;

public class PolishedCopperBlock extends Block {
    @Register("polished_copper")
    public static final Block POLISHED_COPPER_BLOCK = new PolishedCopperBlock();

    public void register() {
        Registry.register("polished_copper", POLISHED_COPPER_BLOCK);
    }
}
'''
                zf.writestr('com/example/PolishedCopperBlock.java', java_source.encode('utf-8'))

                # Add texture
                zf.writestr('assets/copper_mod/textures/block/polished_copper.png', b'fake_png_data')

            yield jar_file.name

        os.unlink(jar_file.name)

    @pytest.fixture
    def jar_without_texture(self):
        """Create a JAR without texture files."""
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as jar_file:
            with zipfile.ZipFile(jar_file.name, 'w') as zf:
                # Add metadata only
                fabric_mod = {
                    "schemaVersion": 1,
                    "id": "no_texture_mod",
                    "version": "1.0.0"
                }
                zf.writestr('fabric.mod.json', json.dumps(fabric_mod))
                zf.writestr('com/example/SomeBlock.class', b'fake_class_data')

            yield jar_file.name

        os.unlink(jar_file.name)

    @pytest.fixture
    def jar_with_forge_metadata(self):
        """Create a JAR with Forge-style metadata."""
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as jar_file:
            with zipfile.ZipFile(jar_file.name, 'w') as zf:
                # Add mcmod.info
                mcmod_info = [
                    {
                        "modid": "copper_extras",
                        "name": "Copper Extras",
                        "version": "1.0.0"
                    }
                ]
                zf.writestr('mcmod.info', json.dumps(mcmod_info))

                # Add texture and class
                zf.writestr('assets/copper_extras/textures/block/copper_ingot_block.png', b'fake_png_data')
                zf.writestr('com/example/CopperIngotBlock.class', b'fake_class_data')

            yield jar_file.name

        os.unlink(jar_file.name)

    def test_analyze_jar_for_mvp_success(self, analyzer, simple_jar_with_texture):
        """Test successful MVP analysis with both registry name and texture."""
        result = analyzer.analyze_jar_for_mvp(simple_jar_with_texture)

        assert result["success"] is True
        assert result["registry_name"] == "simple_copper:polished_copper"
        assert result["texture_path"] == "assets/simple_copper/textures/block/polished_copper.png"
        assert len(result["errors"]) == 0

    def test_analyze_jar_with_java_source(self, analyzer, jar_with_java_source):
        """Test MVP analysis with Java source containing @Register annotation."""
        result = analyzer.analyze_jar_for_mvp(jar_with_java_source)

        assert result["success"] is True
        assert result["registry_name"] == "copper_mod:polished_copper"
        assert result["texture_path"] == "assets/copper_mod/textures/block/polished_copper.png"
        assert len(result["errors"]) == 0

    def test_analyze_jar_for_mvp_missing_texture(self, analyzer, jar_without_texture):
        """Test MVP analysis when texture is missing."""
        result = analyzer.analyze_jar_for_mvp(jar_without_texture)

        assert result["success"] is False
        assert result["registry_name"] is not None  # Should still extract mod ID
        assert result["texture_path"] is None
        assert "Could not find block texture in JAR" in result["errors"]

    def test_analyze_jar_for_mvp_forge_metadata(self, analyzer, jar_with_forge_metadata):
        """Test MVP analysis with Forge-style metadata."""
        result = analyzer.analyze_jar_for_mvp(jar_with_forge_metadata)

        assert result["success"] is True
        assert result["registry_name"] == "copper_extras:copper_ingot"
        assert result["texture_path"] == "assets/copper_extras/textures/block/copper_ingot_block.png"

    def test_analyze_jar_with_mods_toml(self, analyzer):
        """Test MVP analysis with mods.toml (Forge) metadata."""
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as jar_file:
            with zipfile.ZipFile(jar_file.name, 'w') as zf:
                # Add mods.toml with proper TOML structure
                mods_toml = '''
modLoader="javafml"
loaderVersion="[40,)"
license="MIT"

[[mods]]
modId="advanced_copper"
version="2.0.0"
displayName="Advanced Copper Mod"
authors="Test Author"
'''
                zf.writestr('META-INF/mods.toml', mods_toml.encode('utf-8'))

                # Add texture and class
                zf.writestr('assets/advanced_copper/textures/block/oxidized_copper_block.png', b'fake_png_data')
                zf.writestr('com/example/OxidizedCopperBlock.class', b'fake_class_data')

            try:
                result = analyzer.analyze_jar_for_mvp(jar_file.name)

                assert result["success"] is True
                assert result["registry_name"] == "advanced_copper:oxidized_copper"
                assert result["texture_path"] == "assets/advanced_copper/textures/block/oxidized_copper_block.png"
                assert len(result["errors"]) == 0
            finally:
                os.unlink(jar_file.name)

    def test_find_block_texture(self, analyzer):
        """Test texture finding logic."""
        file_list = [
            'META-INF/MANIFEST.MF',
            'assets/test_mod/textures/block/test_block.png',
            'assets/test_mod/textures/item/test_item.png',
            'com/example/TestBlock.class'
        ]

        texture_path = analyzer._find_block_texture(file_list)
        assert texture_path == 'assets/test_mod/textures/block/test_block.png'

    def test_find_block_texture_none_found(self, analyzer):
        """Test texture finding when no block textures exist."""
        file_list = [
            'META-INF/MANIFEST.MF',
            'assets/test_mod/textures/item/test_item.png',
            'com/example/TestBlock.class'
        ]

        texture_path = analyzer._find_block_texture(file_list)
        assert texture_path is None

    def test_extract_mod_id_from_metadata_fabric(self, analyzer):
        """Test mod ID extraction from Fabric metadata."""
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as jar_file:
            with zipfile.ZipFile(jar_file.name, 'w') as zf:
                fabric_mod = {"id": "test_fabric_mod", "version": "1.0.0"}
                zf.writestr('fabric.mod.json', json.dumps(fabric_mod))

            try:
                with zipfile.ZipFile(jar_file.name, 'r') as jar:
                    file_list = jar.namelist()
                    mod_id = analyzer._extract_mod_id_from_metadata(jar, file_list)
                    assert mod_id == "test_fabric_mod"
            finally:
                os.unlink(jar_file.name)

    def test_find_block_class_name(self, analyzer):
        """Test block class name extraction."""
        file_list = [
            'com/example/TestBlock.class',
            'com/example/TestItem.class',
            'com/example/AbstractBlock.class',  # Should be ignored
            'com/example/SimpleBlock.class'
        ]

        block_class = analyzer._find_block_class_name(file_list)
        # Should prefer shorter, simpler names
        assert block_class in ['TestBlock', 'SimpleBlock']

    def test_class_name_to_registry_name(self, analyzer):
        """Test class name to registry name conversion."""
        test_cases = [
            ('PolishedCopperBlock', 'polished_copper'),
            ('TestBlock', 'test'),
            ('SimpleStoneBlock', 'simple_stone'),
            ('CopperIngotBlock', 'copper_ingot'),
            ('BlockOfCopper', 'of_copper'),  # Edge case
        ]

        for class_name, expected in test_cases:
            result = analyzer._class_name_to_registry_name(class_name)
            assert result == expected, f"Expected {expected}, got {result} for {class_name}"

    def test_invalid_jar_file(self, analyzer):
        """Test handling of invalid JAR files."""
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as jar_file:
            jar_file.write(b'not a valid jar file')
            jar_file.flush()

            try:
                result = analyzer.analyze_jar_for_mvp(jar_file.name)
                assert result["success"] is False
                assert len(result["errors"]) > 0
                assert "JAR analysis failed" in result["errors"][0]
            finally:
                os.unlink(jar_file.name)

    def test_nonexistent_file(self, analyzer):
        """Test handling of nonexistent files."""
        result = analyzer.analyze_jar_for_mvp("/nonexistent/path/to/file.jar")
        assert result["success"] is False
        assert len(result["errors"]) > 0

    def test_fixture_jar_file(self, analyzer):
        """Test analysis of the fixture JAR file created for Issue #167."""
        # Use the fixture JAR created by simple_copper_block.py
        fixture_path = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "simple_copper_block.jar"

        if fixture_path.exists():
            result = analyzer.analyze_jar_for_mvp(str(fixture_path))

            assert result["success"] is True
            assert result["registry_name"] == "simple_copper:polished_copper"
            assert result["texture_path"] == "assets/simple_copper/textures/block/polished_copper.png"
            assert len(result["errors"]) == 0
        else:
            pytest.skip("Fixture JAR file not found - run tests/fixtures/simple_copper_block.py first")


if __name__ == '__main__':
    pytest.main([__file__])
