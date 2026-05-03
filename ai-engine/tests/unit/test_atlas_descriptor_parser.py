"""
Unit tests for the atlas descriptor parser module.
Tests parsing of Minecraft atlas JSON descriptors for sprite sheet unpacking.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from utils.atlas_descriptor_parser import (
    AtlasSpriteInfo,
    parse_atlas_descriptor,
    find_atlas_descriptors_in_jar,
    extract_sprites_from_atlas,
    find_atlas_textures_in_jar,
    is_likely_atlas_texture,
)


class TestAtlasDescriptorParser:
    """Test cases for atlas descriptor parsing"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directories"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_atlas_sprite_info_creation(self):
        """Test AtlasSpriteInfo object creation"""
        sprite = AtlasSpriteInfo(
            name="test_sprite",
            x=16,
            y=32,
            width=16,
            height=16,
            atlas_path="textures/gui/atlas.png",
            original_name="modid:textures/gui/test_sprite.png",
        )

        assert sprite.name == "test_sprite"
        assert sprite.x == 16
        assert sprite.y == 32
        assert sprite.width == 16
        assert sprite.height == 16
        assert sprite.atlas_path == "textures/gui/atlas.png"
        assert sprite.original_name == "modid:textures/gui/test_sprite.png"

    def test_atlas_sprite_info_to_dict(self):
        """Test AtlasSpriteInfo.to_dict() method"""
        sprite = AtlasSpriteInfo(
            name="widget_button",
            x=0,
            y=0,
            width=200,
            height=20,
            atlas_path="gui/widgets.png",
        )

        sprite_dict = sprite.to_dict()
        assert sprite_dict["name"] == "widget_button"
        assert sprite_dict["x"] == 0
        assert sprite_dict["y"] == 0
        assert sprite_dict["width"] == 200
        assert sprite_dict["height"] == 20

    def test_parse_minecraft_format_single(self):
        """Test parsing Minecraft format with single source"""
        descriptor_data = {
            "sources": [
                {
                    "type": "single",
                    "resourceLocation": "modid:textures/gui/widgets.png",
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(descriptor_data, f)
            desc_path = f.name

        try:
            sprites = parse_atlas_descriptor(desc_path, "textures/gui/widgets.png")
            assert len(sprites) == 1
            # Sprite name is derived from the resource path stem
            assert "widgets" in sprites
        finally:
            os.unlink(desc_path)

    def test_parse_minecraft_format_horizontal(self):
        """Test parsing Minecraft format with horizontal strip"""
        descriptor_data = {
            "sources": [
                {
                    "type": "horizontal",
                    "resourceLocation": "modid:textures/gui/buttons.png",
                    "width": 200,
                    "height": 20,
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(descriptor_data, f)
            desc_path = f.name

        try:
            sprites = parse_atlas_descriptor(desc_path, "textures/gui/buttons.png")
            # Horizontal creates sprite per index
            assert len(sprites) == 1
            # Sprite name is derived from resource path stem + index
            assert "buttons_0" in sprites
        finally:
            os.unlink(desc_path)

    def test_parse_minecraft_format_horizontal(self):
        """Test parsing Minecraft format with horizontal strip"""
        descriptor_data = {
            "sources": [
                {
                    "type": "horizontal",
                    "resourceLocation": "modid:textures/gui/buttons.png",
                    "width": 200,
                    "height": 20,
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(descriptor_data, f)
            desc_path = f.name

        try:
            sprites = parse_atlas_descriptor(desc_path, "textures/gui/buttons.png")
            # Horizontal creates sprite per index
            assert len(sprites) == 1
            # Sprite name is derived from resource path stem + index
            assert "buttons_0" in sprites
        finally:
            os.unlink(desc_path)

    def test_parse_sprites_format(self):
        """Test parsing sprites array format"""
        descriptor_data = {
            "sprites": [
                {
                    "name": "slot_empty",
                    "x": 0,
                    "y": 0,
                    "width": 16,
                    "height": 16,
                },
                {
                    "name": "slot_highlighted",
                    "x": 16,
                    "y": 0,
                    "width": 16,
                    "height": 16,
                },
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(descriptor_data, f)
            desc_path = f.name

        try:
            sprites = parse_atlas_descriptor(desc_path, "textures/gui/slots.png")
            assert len(sprites) == 2
            assert "slot_empty" in sprites
            assert "slot_highlighted" in sprites
            assert sprites["slot_empty"].x == 0
            assert sprites["slot_highlighted"].x == 16
        finally:
            os.unlink(desc_path)

    def test_parse_regions_format(self):
        """Test parsing regions array format"""
        descriptor_data = {
            "regions": [
                {
                    "name": "jei_item_slot",
                    "x": 0,
                    "y": 0,
                    "width": 16,
                    "height": 16,
                },
                {
                    "name": "jei_arrow",
                    "x": 16,
                    "y": 0,
                    "width": 16,
                    "height": 16,
                },
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(descriptor_data, f)
            desc_path = f.name

        try:
            sprites = parse_atlas_descriptor(desc_path, "textures/gui/jei_atlas.png")
            assert len(sprites) == 2
            assert "jei_item_slot" in sprites
            assert "jei_arrow" in sprites
        finally:
            os.unlink(desc_path)

    def test_parse_direct_dict_format(self):
        """Test parsing direct dictionary format"""
        descriptor_data = {
            "widget_slot": {
                "x": 0,
                "y": 0,
                "width": 18,
                "height": 18,
            },
            "widget_energy_bar": {
                "x": 18,
                "y": 0,
                "width": 18,
                "height": 4,
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(descriptor_data, f)
            desc_path = f.name

        try:
            sprites = parse_atlas_descriptor(desc_path, "textures/gui/energy.png")
            assert len(sprites) == 2
            assert "widget_slot" in sprites
            assert sprites["widget_slot"].width == 18
        finally:
            os.unlink(desc_path)

    def test_parse_invalid_json(self):
        """Test handling of invalid JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {")
            desc_path = f.name

        try:
            sprites = parse_atlas_descriptor(desc_path, "textures/gui/atlas.png")
            assert len(sprites) == 0  # Should fail gracefully
        finally:
            os.unlink(desc_path)

    def test_parse_empty_descriptor(self):
        """Test handling of empty descriptor"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({}, f)
            desc_path = f.name

        try:
            sprites = parse_atlas_descriptor(desc_path, "textures/gui/atlas.png")
            assert len(sprites) == 0
        finally:
            os.unlink(desc_path)


class TestFindAtlasDescriptorsInJar:
    """Test cases for finding atlas descriptors in JAR files"""

    def test_find_descriptor_same_name_json(self):
        """Test finding descriptor with same name + .json"""
        mock_jar = MagicMock()
        mock_jar.namelist.return_value = [
            "assets/jei/textures/gui/widgets.png",
            "assets/jei/textures/gui/widgets.json",
        ]

        descriptors = find_atlas_descriptors_in_jar(mock_jar, "jei", "gui")
        assert "assets/jei/textures/gui/widgets.png" in descriptors
        assert (
            descriptors["assets/jei/textures/gui/widgets.png"]
            == "assets/jei/textures/gui/widgets.json"
        )

    def test_find_descriptor_in_atlases_subdir(self):
        """Test finding descriptor in atlases subdirectory"""
        mock_jar = MagicMock()
        mock_jar.namelist.return_value = [
            "assets/jei/textures/gui/widgets.png",
            "assets/jei/textures/gui/atlases/widgets.json",
        ]

        descriptors = find_atlas_descriptors_in_jar(mock_jar, "jei", "gui")
        assert "assets/jei/textures/gui/widgets.png" in descriptors

    def test_find_no_descriptor(self):
        """Test when no descriptor exists"""
        mock_jar = MagicMock()
        mock_jar.namelist.return_value = [
            "assets/jei/textures/gui/widgets.png",
        ]

        descriptors = find_atlas_descriptors_in_jar(mock_jar, "jei", "gui")
        assert len(descriptors) == 0

    def test_find_multiple_descriptors(self):
        """Test finding multiple descriptors"""
        mock_jar = MagicMock()
        mock_jar.namelist.return_value = [
            "assets/jei/textures/gui/widgets.png",
            "assets/jei/textures/gui/widgets.json",
            "assets/jei/textures/gui/buttons.png",
            "assets/jei/textures/gui/buttons.json",
        ]

        descriptors = find_atlas_descriptors_in_jar(mock_jar, "jei", "gui")
        assert len(descriptors) == 2


class TestExtractSpritesFromAtlas:
    """Test cases for extracting sprites from atlas images"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directories"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_atlas_image(self, filename, size=(256, 256), color=(255, 0, 0)):
        """Create a test PNG atlas image"""
        from PIL import Image

        img = Image.new("RGBA", size, color)
        img_path = os.path.join(self.temp_dir, filename)
        img.save(img_path, "PNG")
        return img_path

    def test_extract_single_sprite(self):
        """Test extracting a single sprite from atlas"""
        atlas_path = self.create_test_atlas_image("atlas.png", (64, 64))

        sprites = {
            "test_sprite": AtlasSpriteInfo(
                name="test_sprite",
                x=0,
                y=0,
                width=16,
                height=16,
                atlas_path=atlas_path,
            )
        }

        extracted = extract_sprites_from_atlas(
            atlas_path, sprites, self.temp_dir, naming_pattern="sprite_{name}"
        )

        assert len(extracted) == 1
        assert extracted[0]["name"] == "test_sprite"
        assert extracted[0]["width"] == 16
        assert extracted[0]["height"] == 16

    def test_extract_multiple_sprites(self):
        """Test extracting multiple sprites"""
        atlas_path = self.create_test_atlas_image("atlas.png", (64, 64))

        sprites = {
            "sprite_0": AtlasSpriteInfo(
                name="sprite_0", x=0, y=0, width=16, height=16, atlas_path=atlas_path
            ),
            "sprite_1": AtlasSpriteInfo(
                name="sprite_1", x=16, y=0, width=16, height=16, atlas_path=atlas_path
            ),
            "sprite_2": AtlasSpriteInfo(
                name="sprite_2", x=32, y=0, width=16, height=16, atlas_path=atlas_path
            ),
        }

        extracted = extract_sprites_from_atlas(
            atlas_path, sprites, self.temp_dir, naming_pattern="sprite_{name}"
        )

        assert len(extracted) == 3

    def test_extract_sprite_out_of_bounds(self):
        """Test handling of sprite with out-of-bounds coordinates"""
        atlas_path = self.create_test_atlas_image("small_atlas.png", (32, 32))

        sprites = {
            "big_sprite": AtlasSpriteInfo(
                name="big_sprite",
                x=0,
                y=0,
                width=64,  # Larger than atlas
                height=64,
                atlas_path=atlas_path,
            )
        }

        extracted = extract_sprites_from_atlas(
            atlas_path, sprites, self.temp_dir, naming_pattern="sprite_{name}"
        )

        # Should skip sprite that doesn't fit
        assert len(extracted) == 0

    def test_extract_nonexistent_atlas(self):
        """Test handling of nonexistent atlas file"""
        sprites = {
            "test": AtlasSpriteInfo(
                name="test",
                x=0,
                y=0,
                width=16,
                height=16,
                atlas_path="/nonexistent/atlas.png",
            )
        }

        extracted = extract_sprites_from_atlas("/nonexistent/atlas.png", sprites, self.temp_dir)

        assert len(extracted) == 0


class TestIsLikelyAtlasTexture:
    """Test cases for atlas detection heuristic"""

    def test_is_atlas_large_square(self):
        """Test detection of large square texture as atlas"""
        mock_jar = MagicMock()
        mock_jar.read.return_value = self._create_minimal_png(256, 256)

        result = is_likely_atlas_texture(mock_jar, "textures/gui/atlas.png")
        assert result is True

    def test_is_not_atlas_small(self):
        """Test that small textures are not detected as atlases"""
        mock_jar = MagicMock()
        mock_jar.read.return_value = self._create_minimal_png(16, 16)

        result = is_likely_atlas_texture(mock_jar, "textures/block/cobblestone.png")
        assert result is False

    def test_is_atlas_common_size(self):
        """Test detection of common atlas sizes"""
        for size in [128, 256, 512, 1024]:
            mock_jar = MagicMock()
            mock_jar.read.return_value = self._create_minimal_png(size, size)

            result = is_likely_atlas_texture(mock_jar, f"textures/gui/atlas_{size}.png")
            assert result is True, f"Failed for size {size}"

    def _create_minimal_png(self, width, height):
        """Create minimal PNG image data"""
        from PIL import Image
        import io

        img = Image.new("RGBA", (width, height), (255, 0, 0, 255))
        buffer = io.BytesIO()
        img.save(buffer, "PNG")
        return buffer.getvalue()


class TestFindAtlasTexturesInJar:
    """Test cases for finding atlas textures in JAR"""

    def test_find_atlases_empty_jar(self):
        """Test handling of empty JAR"""
        mock_jar = MagicMock()
        mock_jar.namelist.return_value = []

        atlases = find_atlas_textures_in_jar(mock_jar)
        assert len(atlases) == 0

    def test_find_atlases_with_regular_textures(self):
        """Test filtering of regular textures vs atlases"""
        # Create mock JAR with namelist containing both small and large textures
        mock_jar = MagicMock()
        mock_jar.namelist.return_value = [
            "assets/mod/textures/block/stone.png",  # Small - should be filtered
            "assets/mod/textures/gui/atlas.png",  # Large - potential atlas
        ]

        def read_side_effect(path):
            if "atlas.png" in path:
                return self._create_minimal_png(256, 256)
            return self._create_minimal_png(16, 16)

        mock_jar.read.side_effect = read_side_effect

        atlases = find_atlas_textures_in_jar(mock_jar, "mod")

        # Should find the atlas but not the stone texture
        assert len(atlases) == 1
        assert atlases[0]["texture_path"] == "assets/mod/textures/gui/atlas.png"

    def _create_minimal_png(self, width, height):
        """Create minimal PNG image data"""
        from PIL import Image
        import io

        img = Image.new("RGBA", (width, height), (255, 0, 0, 255))
        buffer = io.BytesIO()
        img.save(buffer, "PNG")
        return buffer.getvalue()


class TestAtlasParserIntegration:
    """Integration tests for atlas parsing pipeline"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directories"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_extraction_pipeline(self):
        """Test full atlas to sprite extraction pipeline"""
        from PIL import Image

        # Create test atlas image
        atlas_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        # Draw some colored squares
        for x in range(16):
            for y in range(16):
                atlas_img.putpixel((x, y), (255, 0, 0, 255))  # Red square
        for x in range(16, 32):
            for y in range(16):
                atlas_img.putpixel((x, y), (0, 255, 0, 255))  # Green square

        atlas_path = os.path.join(self.temp_dir, "test_atlas.png")
        atlas_img.save(atlas_path, "PNG")

        # Create descriptor
        descriptor = {
            "sprites": [
                {"name": "red_square", "x": 0, "y": 0, "width": 16, "height": 16},
                {"name": "green_square", "x": 16, "y": 0, "width": 16, "height": 16},
            ]
        }
        desc_path = os.path.join(self.temp_dir, "test_atlas.json")
        with open(desc_path, "w") as f:
            json.dump(descriptor, f)

        # Parse and extract
        sprites = parse_atlas_descriptor(desc_path, atlas_path)
        extracted = extract_sprites_from_atlas(
            atlas_path, sprites, self.temp_dir, naming_pattern="extracted_{name}"
        )

        assert len(extracted) == 2

        # Verify extracted files exist
        for sprite in extracted:
            assert os.path.exists(sprite["path"])

    def test_graceful_fallback_no_descriptor(self):
        """Test graceful handling when no descriptor is found"""
        from PIL import Image

        # Create atlas without descriptor
        atlas_img = Image.new("RGBA", (256, 256), (255, 0, 0, 255))
        atlas_path = os.path.join(self.temp_dir, "no_descriptor_atlas.png")
        atlas_img.save(atlas_path, "PNG")

        # Empty descriptor path
        sprites = parse_atlas_descriptor("/fake/path.json", atlas_path)
        assert len(sprites) == 0


# Run tests when executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
