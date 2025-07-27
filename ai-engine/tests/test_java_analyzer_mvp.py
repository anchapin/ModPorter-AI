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
from unittest.mock import Mock, patch

from agents.java_analyzer import JavaAnalyzerAgent


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
    
    @patch('agents.java_analyzer.logger')
    def test_logging_behavior(self, mock_logger, analyzer, simple_jar_with_texture):
        """Test that appropriate logging occurs during analysis."""
        analyzer.analyze_jar_for_mvp(simple_jar_with_texture)
        
        # Verify info logs were called
        mock_logger.info.assert_called()
        
        # Check that specific log messages were made
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("MVP analysis of JAR" in msg for msg in info_calls)
        assert any("Found texture" in msg for msg in info_calls)
        assert any("Found registry name" in msg for msg in info_calls)


if __name__ == '__main__':
    pytest.main([__file__])