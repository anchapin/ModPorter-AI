import pytest
import json
from unittest.mock import MagicMock, patch, mock_open
from agents.asset_converter import AssetConverterAgent

class TestAssetConverterAgent:
    @pytest.fixture
    def agent(self):
        AssetConverterAgent._instance = None
        return AssetConverterAgent.get_instance()

    def test_is_power_of_2(self, agent):
        assert agent._is_power_of_2(1) is True
        assert agent._is_power_of_2(2) is True
        assert agent._is_power_of_2(16) is True
        assert agent._is_power_of_2(1024) is True
        assert agent._is_power_of_2(0) is False
        assert agent._is_power_of_2(3) is False
        assert agent._is_power_of_2(100) is False

    def test_next_power_of_2(self, agent):
        assert agent._next_power_of_2(1) == 1
        assert agent._next_power_of_2(3) == 4
        assert agent._next_power_of_2(15) == 16
        assert agent._next_power_of_2(100) == 128

    def test_convert_java_texture_path(self, agent):
        java_path = "assets/modid/textures/block/grass.png"
        bedrock_path = agent.convert_java_texture_path(java_path, "blocks")
        assert bedrock_path == "textures/blocks/grass"
        
        java_path = "some/random/path/textures/item/sword.png"
        bedrock_path = agent.convert_java_texture_path(java_path, "items")
        assert bedrock_path == "textures/items/sword"

    def test_map_texture_type(self, agent):
        assert agent._map_texture_type("block") == "blocks"
        assert agent._map_texture_type("item") == "items"
        assert agent._map_texture_type("unknown") == "misc"

    @patch("agents.asset_converter.Image")
    def test_validate_texture(self, mock_image, agent):
        # Mock Path.exists
        with patch("agents.asset_converter.Path.exists", return_value=True), \
             patch("agents.asset_converter.Path.stat") as mock_stat:
            
            mock_stat.return_value.st_size = 1024
            mock_img_obj = MagicMock()
            mock_img_obj.size = (16, 16)
            mock_img_obj.format = "PNG"
            mock_img_obj.mode = "RGBA"
            mock_image.open.return_value.__enter__.return_value = mock_img_obj
            
            result = agent.validate_texture("test.png")
            assert result["valid"] is True
            assert result["properties"]["width"] == 16

    @patch("agents.asset_converter.Image")
    def test_validate_texture_invalid(self, mock_image, agent):
        with patch("agents.asset_converter.Path.exists", return_value=True), \
             patch("agents.asset_converter.Path.stat") as mock_stat:
            
            mock_stat.return_value.st_size = 1024
            mock_img_obj = MagicMock()
            mock_img_obj.size = (17, 17) # Not power of 2
            mock_img_obj.format = "JPG"
            mock_img_obj.mode = "CMYK" # Unsupported
            mock_image.open.return_value.__enter__.return_value = mock_img_obj
            
            result = agent.validate_texture("test.png")
            assert result["valid"] is False
            assert len(result["errors"]) > 0

    def test_generate_fallback_texture(self, agent):
        with patch("agents.asset_converter.Image.new") as mock_new:
            mock_img = MagicMock()
            mock_new.return_value = mock_img
            
            img = agent._generate_fallback_texture("block")
            assert img == mock_img
            mock_new.assert_called_with("RGBA", (16, 16), (128, 128, 128, 255))

    @patch("agents.asset_converter.zipfile.ZipFile")
    def test_extract_textures_from_jar(self, mock_zip, agent, tmp_path):
        mock_jar = MagicMock()
        mock_zip.return_value.__enter__.return_value = mock_jar
        
        # Mock file list in JAR
        mock_jar.namelist.return_value = [
            "assets/modid/textures/block/stone.png",
            "assets/modid/textures/item/iron_ingot.png",
            "not_a_texture.txt"
        ]
        
        mock_jar.read.return_value = b"fake_png_data"
        
        with patch("agents.asset_converter.Path.exists", return_value=True), \
             patch("builtins.open", mock_open()):
            result = agent.extract_textures_from_jar("fake.jar", str(tmp_path))
            
            assert result["success"] is True
            assert result["count"] == 2

    def test_detect_texture_atlas(self, agent):
        with patch("agents.asset_converter.Path.exists", return_value=True), \
             patch("agents.asset_converter.Image.open") as mock_open_img:
            
            mock_img = MagicMock()
            mock_img.size = (256, 256)
            mock_open_img.return_value = mock_img
            
            result = agent.detect_texture_atlas("atlas.png")
            assert result["is_atlas"] is True
            assert result["atlas_type"] == "grid"
            assert result["total_tiles"] == 256 # (256/16) * (256/16) = 16 * 16 = 256

    def test_parse_atlas_metadata(self, agent):
        mcmeta_content = json.dumps({
            "animation": {
                "frametime": 2,
                "interpolate": True
            }
        })
        
        with patch("agents.asset_converter.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=mcmeta_content)):
            
            result = agent.parse_atlas_metadata("test.png.mcmeta")
            assert result["success"] is True
            assert result["animation"]["frametime"] == 2
            assert result["animation"]["interpolate"] is True

    def test_convert_java_texture_path_variants(self, agent):
        # Case with backslashes
        java_path = "assets\\modid\\textures\\block\\test.png"
        assert agent.convert_java_texture_path(java_path) == "textures/blocks/test"
        
        # Case without textures/ in path
        java_path = "assets/modid/test.png"
        assert agent.convert_java_texture_path(java_path) == "textures/blocks/test"
        
        # Unknown case
        assert agent.convert_java_texture_path("nothing") == "textures/blocks/unknown"

    def test_generate_fallback_for_jar(self, agent, tmp_path):
        output_file = tmp_path / "fallback.png"
        result = agent.generate_fallback_for_jar(str(output_file), "test_block", "blocks")
        
        assert result["success"] is True
        assert output_file.exists()
        assert result["generated"] is True

    def test_validate_textures_batch(self, agent):
        with patch.object(agent, "validate_texture") as mock_validate:
            mock_validate.return_value = {"valid": True, "warnings": []}
            result = agent.validate_textures_batch(["t1.png", "t2.png"])
            assert result["total"] == 2
            assert result["valid"] == 2

    def test_clear_cache(self, agent):
        agent._conversion_cache["test"] = "data"
        agent.clear_cache()
        assert len(agent._conversion_cache) == 0
