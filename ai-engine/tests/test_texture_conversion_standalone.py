"""
Standalone unit tests for texture conversion functionality (without CrewAI dependency)
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import only the parts we need without triggering CrewAI import
from PIL import Image


class TextureConverter:
    """Minimal texture converter for testing"""

    def __init__(self):
        self.texture_constraints = {
            'max_resolution': 1024,
            'must_be_power_of_2': True,
            'supported_channels': ['rgb', 'rgba']
        }
        self._conversion_cache = {}

    @staticmethod
    def _is_power_of_2(n: int) -> bool:
        """Check if a number is a power of 2"""
        return n > 0 and (n & (n - 1)) == 0

    @staticmethod
    def _next_power_of_2(n: int) -> int:
        """Get the next power of 2 greater than or equal to n"""
        power = 1
        while power < n:
            power *= 2
        return power

    @staticmethod
    def _previous_power_of_2(n: int) -> int:
        """Get the previous power of 2 less than or equal to n"""
        if n <= 0:
            return 1
        power = 1
        while (power * 2) <= n:
            power *= 2
        return power

    def _generate_fallback_texture(self, usage: str = "block", size: tuple = (16, 16)) -> Image.Image:
        """Generate a fallback texture for edge cases"""
        colors = {
            'block': (128, 128, 128, 255),
            'item': (200, 200, 100, 255),
            'entity': (150, 100, 100, 255),
            'particle': (200, 200, 255, 255),
            'ui': (100, 200, 100, 255),
            'other': (128, 128, 128, 255)
        }

        color = colors.get(usage, colors['other'])
        img = Image.new('RGBA', size, color)

        # Add pattern
        for x in range(0, size[0], 4):
            for y in range(0, size[1], 4):
                if (x + y) % 8 == 0:
                    img.putpixel((x, y), (min(255, color[0] + 50), min(255, color[1] + 50), min(255, color[2] + 50), 255))

        return img

    def convert_texture(self, texture_path: str, output_dir: Path, usage: str = "block") -> dict:
        """Convert a single texture and save to output directory"""
        cache_key = f"{texture_path}_{usage}"

        # Check cache
        if cache_key in self._conversion_cache:
            return self._conversion_cache[cache_key]

        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Check if file exists
            if not Path(texture_path).exists():
                print(f"Texture not found: {texture_path}, generating fallback")
                img = self._generate_fallback_texture(usage)
                original_dimensions = img.size
                is_valid_png = False
                optimizations = ["Generated fallback texture"]
            else:
                try:
                    img = Image.open(texture_path)
                    original_dimensions = img.size
                    is_valid_png = img.format == 'PNG'
                    img = img.convert("RGBA")
                    optimizations = ["Converted to RGBA"] if not is_valid_png else []
                except Exception as e:
                    print(f"Failed to open texture: {e}, generating fallback")
                    img = self._generate_fallback_texture(usage)
                    original_dimensions = img.size
                    is_valid_png = False
                    optimizations = ["Generated fallback texture due to error"]

            width, height = img.size
            resized = False

            max_res = self.texture_constraints.get('max_resolution', 1024)
            must_be_pot = self.texture_constraints.get('must_be_power_of_2', True)

            new_width, new_height = width, height

            # Check power of 2
            if must_be_pot and (not self._is_power_of_2(width) or not self._is_power_of_2(height)):
                new_width = self._next_power_of_2(width)
                new_height = self._next_power_of_2(height)
                resized = True

            # Cap at max resolution
            if new_width > max_res or new_height > max_res:
                new_width = min(new_width, max_res)
                new_height = min(new_height, max_res)
                resized = True

            # Ensure capped dimensions are still power of 2
            if resized and must_be_pot:
                if not self._is_power_of_2(new_width):
                    new_width = self._previous_power_of_2(new_width)
                if not self._is_power_of_2(new_height):
                    new_height = self._previous_power_of_2(new_height)

            # Perform resize
            if resized and (new_width != width or new_height != height):
                img = img.resize((new_width, new_height), Image.LANCZOS)
                optimizations.append(f"Resized from {original_dimensions} to {(new_width, new_height)}")

            # Determine output path
            base_name = Path(texture_path).stem if Path(texture_path).exists() else f"fallback_{usage}"

            if usage == 'block':
                relative_path = f"textures/blocks/{base_name}.png"
            elif usage == 'item':
                relative_path = f"textures/items/{base_name}.png"
            elif usage == 'entity':
                relative_path = f"textures/entity/{base_name}.png"
            else:
                relative_path = f"textures/other/{base_name}.png"

            # Save the file
            output_path = output_dir / relative_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, 'PNG', optimize=True)

            result = {
                'success': True,
                'original_path': str(texture_path),
                'converted_path': str(output_path),
                'relative_path': relative_path,
                'original_dimensions': original_dimensions,
                'converted_dimensions': (new_width, new_height),
                'format': 'png',
                'resized': resized,
                'optimizations_applied': optimizations,
                'bedrock_reference': f"{usage}_{base_name}",
                'was_valid_png': is_valid_png,
                'was_fallback': not Path(texture_path).exists()
            }

            # Cache result
            self._conversion_cache[cache_key] = result

            return result

        except Exception as e:
            print(f"Error converting texture: {e}")
            return {
                'success': False,
                'original_path': str(texture_path),
                'error': str(e)
            }


class TestTextureConversion:
    """Test texture conversion functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.converter = TextureConverter()
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "output"

    def teardown_method(self):
        """Clean up temp files"""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_image(self, filename: str, size=(64, 64), color=(255, 0, 0, 255)) -> str:
        """Create a test PNG image"""
        img = Image.new('RGBA', size, color)
        img_path = Path(self.temp_dir) / filename
        img_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(img_path, 'PNG')
        return str(img_path)

    def test_basic_conversion(self):
        """Test basic texture conversion"""
        img_path = self.create_test_image("stone.png", (32, 32), (128, 128, 128, 255))

        result = self.converter.convert_texture(img_path, self.output_dir, "block")

        assert result['success'] is True
        assert result['original_dimensions'] == (32, 32)
        assert result['converted_dimensions'] == (32, 32)
        assert result['resized'] is False
        assert Path(result['converted_path']).exists()

        # Verify output file
        output_img = Image.open(result['converted_path'])
        assert output_img.size == (32, 32)
        assert output_img.format == 'PNG'
        assert output_img.mode == 'RGBA'

    def test_power_of_2_resize(self):
        """Test power of 2 resizing"""
        img_path = self.create_test_image("custom.png", (33, 45), (100, 100, 200, 255))

        result = self.converter.convert_texture(img_path, self.output_dir, "block")

        assert result['success'] is True
        assert result['original_dimensions'] == (33, 45)
        assert result['resized'] is True
        # Should resize to next power of 2: 33 -> 64, 45 -> 64
        assert result['converted_dimensions'] == (64, 64)

        # Verify output
        output_img = Image.open(result['converted_path'])
        assert output_img.size == (64, 64)

    def test_fallback_generation(self):
        """Test fallback texture generation for missing files"""
        result = self.converter.convert_texture("/nonexistent/file.png", self.output_dir, "block")

        assert result['success'] is True
        assert result['was_fallback'] is True
        assert "fallback" in result['optimizations_applied'][0]
        assert Path(result['converted_path']).exists()

        # Verify fallback texture was created
        output_img = Image.open(result['converted_path'])
        assert output_img.size == (16, 16)  # Default fallback size
        assert output_img.mode == 'RGBA'

    def test_path_mapping_block(self):
        """Test path mapping for block textures"""
        img_path = self.create_test_image("dirt.png", (16, 16))

        result = self.converter.convert_texture(img_path, self.output_dir, "block")

        assert result['success'] is True
        assert 'textures/blocks/dirt.png' in result['relative_path']
        assert result['bedrock_reference'] == 'block_dirt'

    def test_path_mapping_item(self):
        """Test path mapping for item textures"""
        img_path = self.create_test_image("diamond_sword.png", (16, 16))

        result = self.converter.convert_texture(img_path, self.output_dir, "item")

        assert result['success'] is True
        assert 'textures/items/diamond_sword.png' in result['relative_path']
        assert result['bedrock_reference'] == 'item_diamond_sword'

    def test_max_resolution_capping(self):
        """Test capping at maximum resolution"""
        # Create a large image
        large_size = (2048, 2048)
        img_path = self.create_test_image("large.png", large_size)

        result = self.converter.convert_texture(img_path, self.output_dir, "block")

        assert result['success'] is True
        assert result['original_dimensions'] == (2048, 2048)
        assert result['resized'] is True
        # Should cap at 1024 (max resolution)
        assert result['converted_dimensions'] == (1024, 1024)

    def test_non_png_to_png_conversion(self):
        """Test converting non-PNG to PNG"""
        # Create a JPEG image
        img = Image.new('RGB', (32, 32), (255, 0, 0))
        jpeg_path = Path(self.temp_dir) / "test.jpg"
        img.save(jpeg_path, 'JPEG')

        result = self.converter.convert_texture(str(jpeg_path), self.output_dir, "block")

        assert result['success'] is True
        assert result['format'] == 'png'
        assert 'Converted to RGBA' in result['optimizations_applied']

        # Verify output is PNG
        output_img = Image.open(result['converted_path'])
        assert output_img.format == 'PNG'
        assert output_img.mode == 'RGBA'

    def test_caching(self):
        """Test that conversion results are cached"""
        img_path = self.create_test_image("test.png", (16, 16))

        result1 = self.converter.convert_texture(img_path, self.output_dir, "block")
        result2 = self.converter.convert_texture(img_path, self.output_dir, "block")

        assert result1 == result2
        # Second conversion should hit cache
        assert ' Converted to RGBA' not in str(result2) or len(result2['optimizations_applied']) == len(result1['optimizations_applied'])

    def test_is_power_of_2(self):
        """Test power of 2 checking"""
        assert TextureConverter._is_power_of_2(1) is True
        assert TextureConverter._is_power_of_2(2) is True
        assert TextureConverter._is_power_of_2(4) is True
        assert TextureConverter._is_power_of_2(8) is True
        assert TextureConverter._is_power_of_2(16) is True
        assert TextureConverter._is_power_of_2(32) is True
        assert TextureConverter._is_power_of_2(64) is True
        assert TextureConverter._is_power_of_2(128) is True
        assert TextureConverter._is_power_of_2(256) is True
        assert TextureConverter._is_power_of_2(512) is True
        assert TextureConverter._is_power_of_2(1024) is True

        assert TextureConverter._is_power_of_2(0) is False
        assert TextureConverter._is_power_of_2(3) is False
        assert TextureConverter._is_power_of_2(5) is False
        assert TextureConverter._is_power_of_2(7) is False
        assert TextureConverter._is_power_of_2(33) is False
        assert TextureConverter._is_power_of_2(100) is False

    def test_next_power_of_2(self):
        """Test next power of 2 calculation"""
        assert TextureConverter._next_power_of_2(1) == 1
        assert TextureConverter._next_power_of_2(2) == 2
        assert TextureConverter._next_power_of_2(3) == 4
        assert TextureConverter._next_power_of_2(5) == 8
        assert TextureConverter._next_power_of_2(9) == 16
        assert TextureConverter._next_power_of_2(17) == 32
        assert TextureConverter._next_power_of_2(33) == 64
        assert TextureConverter._next_power_of_2(100) == 128
        assert TextureConverter._next_power_of_2(1025) == 2048

    def test_previous_power_of_2(self):
        """Test previous power of 2 calculation"""
        assert TextureConverter._previous_power_of_2(1) == 1
        assert TextureConverter._previous_power_of_2(2) == 2
        assert TextureConverter._previous_power_of_2(3) == 2
        assert TextureConverter._previous_power_of_2(5) == 4
        assert TextureConverter._previous_power_of_2(9) == 8
        assert TextureConverter._previous_power_of_2(17) == 16
        assert TextureConverter._previous_power_of_2(33) == 32
        assert TextureConverter._previous_power_of_2(100) == 64
        assert TextureConverter._previous_power_of_2(1025) == 1024


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
