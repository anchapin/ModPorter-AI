"""
Unit tests for BedrockBuilderAgent MVP functionality.
Implements tests for Issue #168: Emit Bedrock JSON & copy texture in BedrockBuilderAgent
"""

import pytest
import tempfile
import zipfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

from agents.bedrock_builder import BedrockBuilderAgent


class TestBedrockBuilderMVP:
    """Test BedrockBuilderAgent MVP-specific functionality."""
    
    @pytest.fixture
    def builder(self):
        """Create BedrockBuilderAgent instance for testing."""
        return BedrockBuilderAgent()
    
    @pytest.fixture
    def test_jar_with_texture(self):
        """Create a test JAR with a real texture for testing."""
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as jar_file:
            with zipfile.ZipFile(jar_file.name, 'w') as zf:
                # Create a real 16x16 PNG texture using Pillow
                from PIL import Image
                import io
                
                # Create a simple 16x16 RGBA image
                img = Image.new('RGBA', (16, 16), (200, 100, 50, 255))  # Orange-ish color
                png_buffer = io.BytesIO()
                img.save(png_buffer, format='PNG')
                png_data = png_buffer.getvalue()
                
                # Add the real PNG texture to JAR
                zf.writestr('assets/simple_copper/textures/block/polished_copper.png', png_data)
                
            yield jar_file.name
            
        os.unlink(jar_file.name)
    
    @pytest.fixture
    def output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_build_block_addon_mvp_success(self, builder, test_jar_with_texture, output_dir):
        """Test successful MVP block addon creation."""
        registry_name = "simple_copper:polished_copper"
        texture_path = "assets/simple_copper/textures/block/polished_copper.png"
        
        result = builder.build_block_addon_mvp(
            registry_name=registry_name,
            texture_path=texture_path,
            jar_path=test_jar_with_texture,
            output_dir=output_dir
        )
        
        assert result["success"] is True
        assert result["addon_path"] is not None
        assert Path(result["addon_path"]).exists()
        assert len(result["bp_files"]) > 0
        assert len(result["rp_files"]) > 0
        assert len(result["errors"]) == 0
    
    def test_build_block_addon_mvp_registry_parsing(self, builder, test_jar_with_texture, output_dir):
        """Test registry name parsing."""
        # Test with namespace
        result = builder.build_block_addon_mvp(
            registry_name="test_mod:custom_block",
            texture_path="assets/simple_copper/textures/block/polished_copper.png",
            jar_path=test_jar_with_texture,
            output_dir=output_dir
        )
        
        assert result["success"] is True
        assert "test_mod_custom_block.mcaddon" in result["addon_path"]
        
        # Test without namespace (should default to modporter)
        result2 = builder.build_block_addon_mvp(
            registry_name="just_block_name",
            texture_path="assets/simple_copper/textures/block/polished_copper.png",
            jar_path=test_jar_with_texture,
            output_dir=output_dir
        )
        
        assert result2["success"] is True
        assert "modporter_just_block_name.mcaddon" in result2["addon_path"]
    
    def test_build_bp_mvp(self, builder, output_dir):
        """Test behavior pack creation."""
        bp_path = Path(output_dir) / "BP"
        bp_path.mkdir()
        
        files_created = builder._build_bp_mvp(
            bp_path=bp_path,
            namespace="test_mod",
            block_name="test_block",
            bp_uuid="test-uuid-bp"
        )
        
        assert len(files_created) >= 2  # manifest + block file
        
        # Check manifest exists
        manifest_file = bp_path / "manifest.json"
        assert manifest_file.exists()
        
        # Check manifest content
        manifest_data = json.loads(manifest_file.read_text())
        assert manifest_data["header"]["name"] == "ModPorter Test Block"
        assert manifest_data["header"]["uuid"] == "test-uuid-bp"
        
        # Check block file exists
        block_file = bp_path / "blocks" / "test_block.json"
        assert block_file.exists()
        
        # Check block content
        block_data = json.loads(block_file.read_text())
        assert block_data["minecraft:block"]["description"]["identifier"] == "test_mod:test_block"
    
    def test_build_rp_mvp(self, builder, test_jar_with_texture, output_dir):
        """Test resource pack creation."""
        rp_path = Path(output_dir) / "RP"
        rp_path.mkdir()
        
        files_created = builder._build_rp_mvp(
            rp_path=rp_path,
            namespace="simple_copper",
            block_name="polished_copper",
            rp_uuid="test-uuid-rp",
            texture_path="assets/simple_copper/textures/block/polished_copper.png",
            jar_path=test_jar_with_texture
        )
        
        assert len(files_created) >= 3  # manifest + block + texture
        
        # Check manifest exists
        manifest_file = rp_path / "manifest.json"
        assert manifest_file.exists()
        
        # Check manifest content
        manifest_data = json.loads(manifest_file.read_text())
        assert "Resources" in manifest_data["header"]["name"]
        assert manifest_data["header"]["uuid"] == "test-uuid-rp"
        
        # Check block file exists
        block_file = rp_path / "blocks" / "polished_copper.json"
        assert block_file.exists()
        
        # Check texture file exists
        texture_file = rp_path / "textures" / "blocks" / "polished_copper.png"
        assert texture_file.exists()
    
    def test_copy_texture_mvp(self, builder, test_jar_with_texture, output_dir):
        """Test texture copying and processing."""
        rp_path = Path(output_dir) / "RP"
        rp_path.mkdir()
        
        # Mock Pillow Image processing since we have fake PNG data
        with patch('agents.bedrock_builder.Image') as mock_image:
            mock_img = Mock()
            mock_img.size = (32, 32)
            mock_img.convert.return_value = mock_img
            mock_img.resize.return_value = mock_img
            mock_image.open.return_value.__enter__.return_value = mock_img
            
            files_created = builder._copy_texture_mvp(
                rp_path=rp_path,
                block_name="test_block",
                texture_path="assets/simple_copper/textures/block/polished_copper.png",
                jar_path=test_jar_with_texture
            )
            
            # Should have created texture file
            assert len(files_created) == 1
            
            # Check texture directory was created
            textures_dir = rp_path / "textures" / "blocks"
            assert textures_dir.exists()
            
            # Verify Image processing was called
            mock_img.convert.assert_called_with('RGBA')
            mock_img.resize.assert_called_with((16, 16), mock_image.Resampling.NEAREST)
    
    def test_copy_texture_missing_texture(self, builder, output_dir):
        """Test handling of missing texture in JAR."""
        # Create JAR without the expected texture
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as jar_file:
            with zipfile.ZipFile(jar_file.name, 'w') as zf:
                zf.writestr('some_other_file.txt', b'not a texture')
        
        try:
            rp_path = Path(output_dir) / "RP"
            rp_path.mkdir()
            
            # Should not raise an exception, but should log warning
            files_created = builder._copy_texture_mvp(
                rp_path=rp_path,
                block_name="test_block",
                texture_path="assets/missing/texture.png",
                jar_path=jar_file.name
            )
            
            # Should create no files when texture is missing
            assert len(files_created) == 0
            
        finally:
            os.unlink(jar_file.name)
    
    def test_package_addon_mvp(self, builder, output_dir):
        """Test addon packaging into .mcaddon file."""
        # Create temporary pack structure
        temp_path = Path(output_dir) / "temp"
        temp_path.mkdir()
        
        # Create some test files
        bp_path = temp_path / "BP"
        rp_path = temp_path / "RP"
        bp_path.mkdir()
        rp_path.mkdir()
        
        (bp_path / "manifest.json").write_text('{"test": "bp"}')
        (rp_path / "manifest.json").write_text('{"test": "rp"}')
        
        addon_path = Path(output_dir) / "test_addon.mcaddon"
        
        # Package the addon
        builder._package_addon_mvp(temp_path, addon_path)
        
        # Verify addon file was created
        assert addon_path.exists()
        assert addon_path.suffix == ".mcaddon"
        
        # Verify contents
        with zipfile.ZipFile(addon_path, 'r') as addon_zip:
            files = addon_zip.namelist()
            assert "BP/manifest.json" in files
            assert "RP/manifest.json" in files
    
    def test_invalid_jar_file(self, builder, output_dir):
        """Test handling of invalid JAR files."""
        # Create invalid JAR file
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as jar_file:
            jar_file.write(b'not a valid jar file')
            jar_file.flush()
            
            try:
                result = builder.build_block_addon_mvp(
                    registry_name="test:block",
                    texture_path="assets/test/texture.png",
                    jar_path=jar_file.name,
                    output_dir=output_dir
                )
                
                assert result["success"] is False
                assert len(result["errors"]) > 0
                assert "Build failed" in result["errors"][0]
                
            finally:
                os.unlink(jar_file.name)
    
    def test_nonexistent_jar_file(self, builder, output_dir):
        """Test handling of nonexistent JAR files."""
        result = builder.build_block_addon_mvp(
            registry_name="test:block",
            texture_path="assets/test/texture.png",
            jar_path="/nonexistent/path/to/file.jar",
            output_dir=output_dir
        )
        
        assert result["success"] is False
        assert len(result["errors"]) > 0
    
    @patch('agents.bedrock_builder.logger')
    def test_logging_behavior(self, mock_logger, builder, test_jar_with_texture, output_dir):
        """Test that appropriate logging occurs during build."""
        builder.build_block_addon_mvp(
            registry_name="simple_copper:polished_copper",
            texture_path="assets/simple_copper/textures/block/polished_copper.png",
            jar_path=test_jar_with_texture,
            output_dir=output_dir
        )
        
        # Verify info logs were called
        mock_logger.info.assert_called()
        
        # Check that specific log messages were made
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("MVP: Building block add-on" in msg for msg in info_calls)
        assert any("MVP: Successfully created" in msg for msg in info_calls)


if __name__ == '__main__':
    pytest.main([__file__])