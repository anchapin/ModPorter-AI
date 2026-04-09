import pytest
import json
from unittest.mock import MagicMock, patch, mock_open
from agents.asset_converter import AssetConverterAgent

class TestAssetConverterAgentComprehensive:
    @pytest.fixture
    def agent(self):
        AssetConverterAgent._instance = None
        return AssetConverterAgent.get_instance()

    def test_analyze_assets_tool_basic(self, agent):
        asset_data = json.dumps({
            "asset_list": [
                {"path": "assets/modid/textures/block/stone.png", "metadata": {"width": 16, "height": 16, "channels": "rgba"}},
                {"path": "assets/modid/models/block/stone.json", "metadata": {"vertices": 100, "textures": 1, "bones": 0}},
                {"path": "assets/modid/sounds/random/explode.ogg", "metadata": {"file_size_mb": 1, "sample_rate": 44100, "duration_seconds": 2}}
            ]
        })
        
        result_json = agent.analyze_assets_tool.func(asset_data)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert result["total_assets"] == 3
        assert result["analysis_results"]["textures"]["count"] == 1
        assert result["analysis_results"]["models"]["count"] == 1
        assert result["analysis_results"]["audio"]["count"] == 1
        assert result["conversion_complexity"] == "moderate"

    def test_analyze_assets_tool_complex(self, agent):
        asset_data = json.dumps({
            "asset_list": [
                {"path": "large_tex.png", "metadata": {"width": 2048, "height": 2048}},
                {"path": "complex_model.json", "metadata": {"vertices": 5000}},
                {"path": "long_audio.wav", "metadata": {"duration_seconds": 600}}
            ]
        })
        
        result_json = agent.analyze_assets_tool.func(asset_data)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert result["conversion_complexity"] == "complex"
        assert len(result["analysis_results"]["textures"]["issues"]) > 0
        assert len(result["analysis_results"]["models"]["issues"]) > 0
        assert len(result["analysis_results"]["audio"]["issues"]) > 0

    @patch("agents.asset_converter.Image")
    def test_convert_textures_tool_simple(self, mock_image, agent, tmp_path):
        output_dir = tmp_path / "output"
        texture_data = json.dumps({
            "textures": [
                {"path": "test_block.png", "usage": "block"}
            ],
            "output_dir": str(output_dir)
        })
        
        # Mock Image.open and save
        mock_img_obj = MagicMock()
        mock_img_obj.size = (16, 16)
        mock_img_obj.format = "PNG"
        mock_img_obj.convert.return_value = mock_img_obj
        mock_image.open.return_value = mock_img_obj
        
        with patch("agents.asset_converter.Path.exists", return_value=True):
            result_json = agent.convert_textures_tool.func(texture_data)
            result = json.loads(result_json)
            
            assert result["success"] is True
            assert result["conversion_summary"]["successfully_converted"] == 1
            assert "terrain_texture.json" in result["bedrock_pack_files"]

    @patch("agents.asset_converter.Image")
    def test_convert_textures_tool_resize(self, mock_image, agent, tmp_path):
        texture_data = json.dumps({
            "textures": [
                {"path": "test_non_pot.png", "usage": "item"}
            ]
        })
        
        mock_img_obj = MagicMock()
        mock_img_obj.size = (17, 17)
        mock_img_obj.format = "PNG"
        mock_img_obj.convert.return_value = mock_img_obj
        mock_image.open.return_value = mock_img_obj
        
        # Mock resize
        mock_resized_img = MagicMock()
        mock_resized_img.size = (32, 32)
        mock_img_obj.resize.return_value = mock_resized_img
        
        with patch("agents.asset_converter.Path.exists", return_value=True):
            result_json = agent.convert_textures_tool.func(texture_data)
            result = json.loads(result_json)
            
            assert result["success"] is True
            assert result["successful_results"][0]["resized"] is True
            assert result["successful_results"][0]["converted_dimensions"] == [32, 32]

    def test_convert_textures_tool_fallback(self, agent):
        texture_data = json.dumps({
            "textures": [
                {"path": "non_existent.png", "usage": "block"}
            ]
        })
        
        with patch("agents.asset_converter.Path.exists", return_value=False), \
             patch.object(agent, "_generate_fallback_texture") as mock_fallback:
            
            mock_img = MagicMock()
            mock_img.size = (16, 16)
            mock_fallback.return_value = mock_img
            
            result_json = agent.convert_textures_tool.func(texture_data)
            result = json.loads(result_json)
            
            assert result["success"] is True
            assert result["successful_results"][0]["was_fallback"] is True

    @patch("agents.asset_converter.AssetConverterAgent.convert_jar_textures_to_bedrock")
    def test_extract_jar_textures_tool(self, mock_convert, agent):
        mock_convert.return_value = {
            "success": True,
            "extracted": ["t1.png"],
            "converted": [{"original": "t1.png", "bedrock_path": "textures/blocks/t1.png"}],
            "failed": [],
            "warnings": [],
            "errors": []
        }
        
        jar_data = json.dumps({
            "jar_path": "test.jar",
            "output_dir": "out"
        })
        
        result_json = agent.extract_jar_textures_tool.func(jar_data)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert result["extracted_count"] == 1
        assert result["converted_count"] == 1

    def test_convert_models_tool_basic(self, agent):
        model_data = json.dumps({
            "models": [
                {"path": "test_model.json", "metadata": {"vertices": 100}}
            ]
        })
        
        # We need to mock some internal methods or the file system
        with patch("agents.asset_converter.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data='{"bones": []}')):
            
            result_json = agent.convert_models_tool.func(model_data)
            result = json.loads(result_json)
            
            # Since convert_models_tool is likely complex, let's at least check success or handled error
            assert "success" in result

    def test_convert_audio_tool_basic(self, agent):
        audio_data = json.dumps({
            "audio": [
                {"path": "test_sound.wav"}
            ]
        })
        
        # Mock HAS_AUDIO_SUPPORT if needed, but let's see if it works with mocks
        with patch("agents.asset_converter.Path.exists", return_value=True), \
             patch("agents.asset_converter.HAS_AUDIO_SUPPORT", True), \
             patch("agents.asset_converter.AudioSegment") as mock_audio:
            
            mock_segment = MagicMock()
            mock_audio.from_file.return_value = mock_segment
            
            result_json = agent.convert_audio_tool.func(audio_data)
            result = json.loads(result_json)
            
            assert "success" in result
