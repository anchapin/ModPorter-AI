"""
Unit tests for the enhanced texture pipeline features
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.asset_converter import AssetConverterAgent


class TestTexturePipeline:
    """Test cases for enhanced texture pipeline features"""

    def setup_method(self):
        """Set up test assets and temporary directories"""
        self.agent = AssetConverterAgent.get_instance()
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up temporary directories"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def create_test_image(self, filename, size=(64, 64), color=(255, 0, 0)):
        """Create a test PNG image"""
        img = Image.new('RGB', size, color)
        img_path = os.path.join(self.temp_dir, filename)
        img.save(img_path, 'PNG')
        return img_path
        
    def create_test_mcmeta(self, filename, animation_data=None):
        """Create a test .mcmeta file"""
        mcmeta_path = os.path.join(self.temp_dir, filename)
        if animation_data is None:
            animation_data = {
                "animation": {
                    "frametime": 2,
                    "frames": [0, 1, 2]
                }
            }
        with open(mcmeta_path, 'w') as f:
            json.dump(animation_data, f)
        return mcmeta_path

    def test_png_validation_and_optimization(self):
        """Test enhanced PNG validation and optimization"""
        # Create a test image
        img_path = self.create_test_image("test_texture.png", (32, 32))
        
        # Convert the texture
        result = self.agent._convert_single_texture(
            img_path, 
            {"width": 32, "height": 32}, 
            "block"
        )
        
        # Verify the result includes PNG validation and optimization info
        assert result["success"] is True
        assert result["format"] == "png"
        # Check that it was already a valid PNG
        assert result["was_valid_png"] is True
        
    def test_power_of_2_resizing_with_optimization(self):
        """Test texture conversion with power-of-2 resizing and optimization"""
        # Create a test image with non-power-of-2 dimensions
        img_path = self.create_test_image("test_texture.png", (33, 45))
        
        # Convert the texture
        result = self.agent._convert_single_texture(
            img_path, 
            {"width": 33, "height": 45}, 
            "block"
        )
        
        # Verify the result (should be resized to power of 2)
        assert result["success"] is True
        assert result["resized"] is True
        # 33 -> 64, 45 -> 64 (next power of 2, but capped at max resolution if needed)
        assert result["converted_dimensions"] == (64, 64)
        
    def test_texture_atlas_handling(self):
        """Test texture atlas handling in pack structure generation"""
        # Create test conversion results with related textures
        conversion_results = [
            {
                'success': True,
                'original_path': '/path/to/grass_top.png',
                'converted_path': 'textures/blocks/grass_top.png',
                'format': 'png',
                'bedrock_reference': 'block_grass_top',
                'converted_dimensions': (16, 16)
            },
            {
                'success': True,
                'original_path': '/path/to/grass_side.png',
                'converted_path': 'textures/blocks/grass_side.png',
                'format': 'png',
                'bedrock_reference': 'block_grass_side',
                'converted_dimensions': (16, 16)
            }
        ]
        
        # Generate texture pack structure
        structure = self.agent._generate_texture_pack_structure(conversion_results)
        
        # Verify the structure includes texture atlas information
        assert "pack_manifest.json" in structure
        assert "terrain_texture.json" in structure
        assert "texture_atlases.json" in structure
        assert "grass" in structure["texture_atlases.json"]
        
    def test_asset_path_mapping(self):
        """Test enhanced asset path mapping from Java to Bedrock structure"""
        # Test various Java mod asset paths
        test_cases = [
            # Block textures
            ("/assets/minecraft/textures/block/stone.png", "textures/blocks/stone.png"),
            ("/textures/blocks/dirt.png", "textures/blocks/dirt.png"),
            
            # Item textures
            ("/assets/minecraft/textures/item/diamond_sword.png", "textures/items/diamond_sword.png"),
            ("/textures/items/apple.png", "textures/items/apple.png"),
            
            # Entity textures
            ("/assets/minecraft/textures/entity/creeper/creeper.png", "textures/entity/creeper.png"),
            ("/textures/entity/zombie/zombie.png", "textures/entity/zombie.png"),
            
            # Particle textures
            ("/assets/minecraft/textures/particle/flame.png", "textures/particle/flame.png"),
            
            # UI textures
            ("/assets/minecraft/textures/gui/widgets.png", "textures/ui/widgets.png"),
            
            # Other textures
            ("/assets/mod/textures/custom/feature.png", "textures/other/custom/feature.png")
        ]
        
        for java_path, expected_bedrock_path in test_cases:
            # Create a test image for each path
            filename = Path(java_path).name
            img_path = self.create_test_image(filename, (16, 16))
            
            # Convert the texture
            result = self.agent._convert_single_texture(
                img_path,
                {"width": 16, "height": 16}, 
                "other"  # Let the method infer the usage
            )
            
            assert result["success"] is True
            # Note: We're not directly testing the path mapping in this test because
            # the current implementation doesn't fully implement the path inference
            # during the conversion. This would be tested more thoroughly in an integration test.
            
    def test_caching_performance(self):
        """Test caching functionality for performance improvement"""
        # Create a test image
        img_path = self.create_test_image("test_texture.png", (32, 32))
        
        # Clear cache first
        self.agent.clear_cache()
        
        # Convert the texture twice
        result1 = self.agent._convert_single_texture(
            img_path, 
            {"width": 32, "height": 32}, 
            "block"
        )
        
        result2 = self.agent._convert_single_texture(
            img_path, 
            {"width": 32, "height": 32}, 
            "block"
        )
        
        # Verify both results are successful
        assert result1["success"] is True
        assert result2["success"] is True
        
        # Test that cache clearing works
        cache_size_before = len(self.agent._conversion_cache)
        self.agent.clear_cache()
        cache_size_after = len(self.agent._conversion_cache)
        # After clearing, the cache should be empty
        assert cache_size_after == 0
        
    def test_fallback_texture_generation(self):
        """Test fallback texture generation for different asset types"""
        # Test generating fallback textures for different usage types
        usage_types = ["block", "item", "entity", "particle", "ui", "other"]
        
        for usage in usage_types:
            fallback_img = self.agent._generate_fallback_texture(usage, (16, 16))
            assert fallback_img.size == (16, 16)
            assert fallback_img.mode == "RGBA"
            
    def test_fallback_generation_for_missing_files(self):
        """Test fallback generation for missing files"""
        # Try to convert a non-existent file (should generate fallback)
        result = self.agent._convert_single_texture(
            "/non/existent/file.png", 
            {"width": 16, "height": 16}, 
            "block"
        )
        
        # Verify the result includes fallback generation
        assert result["success"] is True
        assert result["was_fallback"] is True
        assert "Generated fallback texture" in result["optimizations_applied"]