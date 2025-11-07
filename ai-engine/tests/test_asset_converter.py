"""
Unit tests for the AssetConverterAgent
"""
import json
import os
import sys
import tempfile

from PIL import Image

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.asset_converter import AssetConverterAgent


class TestAssetConverterAgent:
    """Test cases for AssetConverterAgent texture conversion functionality"""

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

    def test_texture_conversion_basic(self):
        """Test basic texture conversion functionality"""
        # Create a test image
        img_path = self.create_test_image("test_texture.png", (32, 32))
        
        # Convert the texture
        result = self.agent._convert_single_texture(
            img_path, 
            {"width": 32, "height": 32}, 
            "block"
        )
        
        # Verify the result
        assert result["success"] is True
        assert result["original_path"] == img_path
        assert result["converted_path"] == "textures/blocks/test_texture.png"
        assert result["format"] == "png"
        assert result["converted_dimensions"] == (32, 32)
        
    def test_texture_conversion_resize_power_of_2(self):
        """Test texture conversion with power-of-2 resizing"""
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
        
    def test_texture_conversion_with_animation(self):
        """Test texture conversion with animation data"""
        # Create a test image and mcmeta file
        img_path = self.create_test_image("test_animated_texture.png", (16, 16))
        self.create_test_mcmeta("test_animated_texture.png.mcmeta")
        
        # Convert the texture
        result = self.agent._convert_single_texture(
            img_path, 
            {"width": 16, "height": 16}, 
            "block"
        )
        
        # Verify the result includes animation data
        assert result["success"] is True
        assert result["animation_data"] is not None
        assert "frametime" in result["animation_data"]
        assert "frames" in result["animation_data"]
        
    def test_texture_conversion_invalid_file(self):
        """Test texture conversion with invalid file path"""
        # Try to convert a non-existent file
        result = self.agent._convert_single_texture(
            "/non/existent/file.png", 
            {"width": 16, "height": 16}, 
            "block"
        )
        
        # Verify the result now includes fallback generation
        assert result["success"] is True
        assert result["was_fallback"] is True
        assert "Generated fallback texture" in result["optimizations_applied"]
        
    def test_generate_texture_pack_structure(self):
        """Test generation of texture pack structure files"""
        # Create test conversion results
        conversion_results = [
            {
                'success': True,
                'original_path': '/path/to/stone.png',
                'converted_path': 'textures/blocks/stone.png',
                'format': 'png',
                'bedrock_reference': 'block_stone',
                'converted_dimensions': (16, 16)
            },
            {
                'success': True,
                'original_path': '/path/to/diamond_pickaxe.png',
                'converted_path': 'textures/items/diamond_pickaxe.png',
                'format': 'png',
                'bedrock_reference': 'item_diamond_pickaxe',
                'converted_dimensions': (16, 16)
            }
        ]
        
        # Generate texture pack structure
        structure = self.agent._generate_texture_pack_structure(conversion_results)
        
        # Verify the structure
        assert "pack_manifest.json" in structure
        assert "terrain_texture.json" in structure
        assert "item_texture.json" in structure
        assert structure["pack_manifest.json"]["format_version"] == 2
        assert "block_stone" in structure["terrain_texture.json"]["texture_data"]
        assert "item_diamond_pickaxe" in structure["item_texture.json"]["texture_data"]

    def test_is_power_of_2(self):
        """Test the power-of-2 checking function"""
        assert self.agent._is_power_of_2(1) is True
        assert self.agent._is_power_of_2(2) is True
        assert self.agent._is_power_of_2(4) is True
        assert self.agent._is_power_of_2(8) is True
        assert self.agent._is_power_of_2(16) is True
        assert self.agent._is_power_of_2(32) is True
        assert self.agent._is_power_of_2(3) is False
        assert self.agent._is_power_of_2(5) is False
        assert self.agent._is_power_of_2(0) is False
        assert self.agent._is_power_of_2(-1) is False

    def test_next_power_of_2(self):
        """Test the next power-of-2 function"""
        assert self.agent._next_power_of_2(1) == 1
        assert self.agent._next_power_of_2(2) == 2
        assert self.agent._next_power_of_2(3) == 4
        assert self.agent._next_power_of_2(5) == 8
        assert self.agent._next_power_of_2(9) == 16
        assert self.agent._next_power_of_2(17) == 32

    def test_previous_power_of_2(self):
        """Test the previous power-of-2 function"""
        assert self.agent._previous_power_of_2(1) == 1
        assert self.agent._previous_power_of_2(2) == 2
        assert self.agent._previous_power_of_2(3) == 2
        assert self.agent._previous_power_of_2(5) == 4
        assert self.agent._previous_power_of_2(9) == 8
        assert self.agent._previous_power_of_2(17) == 16

    def test_convert_textures_tool(self):
        """Test the convert_textures_tool function"""
        # Create test images
        img1_path = self.create_test_image("stone.png", (16, 16))
        img2_path = self.create_test_image("dirt.png", (32, 32))
        
        # Prepare texture data
        texture_data = json.dumps([
            img1_path,
            img2_path
        ])
        
        # Convert textures by calling the method directly
        agent = AssetConverterAgent.get_instance()
        result_json = agent.convert_textures(texture_data, self.temp_dir)
        result = json.loads(result_json)
        
        # Verify the result
        assert "converted_textures" in result
        assert result["total_textures"] == 2
        assert result["successful_conversions"] == 2
        assert result["failed_conversions"] == 0
        assert len(result["converted_textures"]) == 2
        assert len(result["errors"]) == 0

    def test_analyze_texture(self):
        """Test texture analysis functionality"""
        # Test a texture that needs conversion (non-power-of-2)
        result = self.agent._analyze_texture(
            "/fake/path/texture.png",
            {"width": 33, "height": 45, "channels": "rgb"}
        )
        
        assert result["needs_conversion"] is True
        assert "not power of 2" in result["issues"][0]
        
        # Test a texture that doesn't need conversion
        result = self.agent._analyze_texture(
            "/fake/path/texture.png",
            {"width": 32, "height": 32, "channels": "rgba"}
        )
        
        assert result["needs_conversion"] is False
        assert len(result["issues"]) == 0
        
    def test_generate_fallback_texture(self):
        """Test fallback texture generation"""
        # Test generating a fallback texture for a block
        fallback_img = self.agent._generate_fallback_texture("block", (16, 16))
        assert fallback_img.size == (16, 16)
        assert fallback_img.mode == "RGBA"
        
        # Test generating a fallback texture for an item
        fallback_img = self.agent._generate_fallback_texture("item", (32, 32))
        assert fallback_img.size == (32, 32)
        assert fallback_img.mode == "RGBA"
        
    def test_texture_conversion_with_fallback(self):
        """Test texture conversion with fallback generation for missing files"""
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
        
    def test_caching(self):
        """Test caching functionality"""
        # Create a test image
        img_path = self.create_test_image("test_texture.png", (32, 32))
        
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
        
    def test_enhanced_path_mapping(self):
        """Test enhanced asset path mapping"""
        # Test block texture path mapping
        img_path = self.create_test_image("stone.png", (16, 16))
        result = self.agent._convert_single_texture(
            img_path,
            {"width": 16, "height": 16}, 
            "block"
        )
        assert result["success"] is True
        assert result["converted_path"] == "textures/blocks/stone.png"
        
        # Test item texture path mapping
        img_path = self.create_test_image("diamond_sword.png", (16, 16))
        result = self.agent._convert_single_texture(
            img_path,
            {"width": 16, "height": 16}, 
            "item"
        )
        assert result["success"] is True
        assert result["converted_path"] == "textures/items/diamond_sword.png"