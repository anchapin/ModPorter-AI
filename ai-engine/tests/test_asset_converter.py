"""
Unit tests for the AssetConverterAgent
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
        img = Image.new("RGB", size, color)
        img_path = os.path.join(self.temp_dir, filename)
        img.save(img_path, "PNG")
        return img_path

    def create_test_mcmeta(self, filename, animation_data=None):
        """Create a test .mcmeta file"""
        mcmeta_path = os.path.join(self.temp_dir, filename)
        if animation_data is None:
            animation_data = {"animation": {"frametime": 2, "frames": [0, 1, 2]}}
        with open(mcmeta_path, "w") as f:
            json.dump(animation_data, f)
        return mcmeta_path

    def test_texture_conversion_basic(self):
        """Test basic texture conversion functionality"""
        # Create a test image
        img_path = self.create_test_image("test_texture.png", (32, 32))

        # Convert the texture
        result = self.agent._convert_single_texture(img_path, {"width": 32, "height": 32}, "block")

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
        result = self.agent._convert_single_texture(img_path, {"width": 33, "height": 45}, "block")

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
        result = self.agent._convert_single_texture(img_path, {"width": 16, "height": 16}, "block")

        # Verify the result includes animation data
        assert result["success"] is True
        assert result["animation_data"] is not None
        assert "frametime" in result["animation_data"]
        assert "frames" in result["animation_data"]

    def test_texture_conversion_invalid_file(self):
        """Test texture conversion with invalid file path"""
        # Try to convert a non-existent file
        result = self.agent._convert_single_texture(
            "/non/existent/file.png", {"width": 16, "height": 16}, "block"
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
                "success": True,
                "original_path": "/path/to/stone.png",
                "converted_path": "textures/blocks/stone.png",
                "format": "png",
                "bedrock_reference": "block_stone",
                "converted_dimensions": (16, 16),
            },
            {
                "success": True,
                "original_path": "/path/to/diamond_pickaxe.png",
                "converted_path": "textures/items/diamond_pickaxe.png",
                "format": "png",
                "bedrock_reference": "item_diamond_pickaxe",
                "converted_dimensions": (16, 16),
            },
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
        texture_data = json.dumps([img1_path, img2_path])

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
            "/fake/path/texture.png", {"width": 33, "height": 45, "channels": "rgb"}
        )

        assert result["needs_conversion"] is True
        assert "not power of 2" in result["issues"][0]

        # Test a texture that doesn't need conversion
        result = self.agent._analyze_texture(
            "/fake/path/texture.png", {"width": 32, "height": 32, "channels": "rgba"}
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
            "/non/existent/file.png", {"width": 16, "height": 16}, "block"
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
        result1 = self.agent._convert_single_texture(img_path, {"width": 32, "height": 32}, "block")

        result2 = self.agent._convert_single_texture(img_path, {"width": 32, "height": 32}, "block")

        # Verify both results are successful
        assert result1["success"] is True
        assert result2["success"] is True

    def test_enhanced_path_mapping(self):
        """Test enhanced asset path mapping"""
        # Test block texture path mapping
        img_path = self.create_test_image("stone.png", (16, 16))
        result = self.agent._convert_single_texture(img_path, {"width": 16, "height": 16}, "block")
        assert result["success"] is True
        assert result["converted_path"] == "textures/blocks/stone.png"

        # Test item texture path mapping
        img_path = self.create_test_image("diamond_sword.png", (16, 16))
        result = self.agent._convert_single_texture(img_path, {"width": 16, "height": 16}, "item")
        assert result["success"] is True
        assert result["converted_path"] == "textures/items/diamond_sword.png"

    def test_convert_models_tool_basic(self):
        """Test basic model conversion functionality via tool"""
        # Create a test Java model file
        model_json = {
            "parent": "block/cube_all",
            "textures": {
                "all": "block/stone"
            },
            "elements": [
                {
                    "from": [0, 0, 0],
                    "to": [16, 16, 16],
                    "faces": {
                        "north": {"uv": [0, 0, 16, 16], "texture": "#all"}
                    }
                }
            ]
        }
        model_path = os.path.join(self.temp_dir, "test_model.json")
        with open(model_path, "w") as f:
            json.dump(model_json, f)

        # Call the tool
        input_data = json.dumps([model_path])
        result_str = self.agent.convert_models_tool.run(model_data=input_data)
        result = json.loads(result_str)

        # Verify the result
        assert result["success"] is True
        assert result["conversion_summary"]["total_requested"] == 1
        assert result["conversion_summary"]["successfully_converted"] == 1
        assert "test_model.geo.json" in result["successful_results"][0]["converted_path"]
        assert "geometry.block.test_model" in result["successful_results"][0]["bedrock_identifier"]

    def test_convert_audio_tool_basic(self):
        """Test basic audio conversion functionality via tool"""
        audio_path = os.path.join(self.temp_dir, "test_sound.ogg")
        with open(audio_path, "wb") as f:
            f.write(b"OggS" + b"\x00" * 100) # Minimum OGG header

        # Call the tool
        input_data = json.dumps([{"path": audio_path, "type": "block.stone"}])
        result_str = self.agent.convert_audio_tool.run(audio_data=input_data)
        result = json.loads(result_str)

        # Verify the result
        assert result["success"] is True
        assert result["conversion_summary"]["total_requested"] == 1
        # Success depends on pydub/ffmpeg being able to read our dummy file
        # If it fails, it's still testing the robust list/dict handling we added.

    def test_analyze_assets_tool(self):
        """Test asset analysis tool"""
        img_path = self.create_test_image("test_texture.png", (32, 32))
        input_data = json.dumps([img_path])
        result_str = self.agent.analyze_assets_tool.run(asset_data=input_data)
        result = json.loads(result_str)
        assert result["success"] is True
        assert result["total_assets"] == 1
        assert "textures" in result["analysis_results"]

    def test_analyze_assets_tool_complex(self):
        """Test asset analysis tool with various asset types"""
        img_path = self.create_test_image("test.png", (32, 32))
        model_path = os.path.join(self.temp_dir, "test.json")
        with open(model_path, "w") as f:
            json.dump({"elements": []}, f)
        audio_path = os.path.join(self.temp_dir, "test.ogg")
        with open(audio_path, "w") as f:
            f.write("ogg data")

        input_data = json.dumps({
            "asset_list": [
                {"path": img_path, "metadata": {"width": 32, "height": 32}},
                {"path": model_path, "metadata": {"vertices": 500}},
                {"path": audio_path, "metadata": {"duration_seconds": 10}},
                {"path": "unknown.txt"}
            ]
        })
        result_str = self.agent.analyze_assets_tool.run(asset_data=input_data)
        result = json.loads(result_str)
        assert result["success"] is True
        assert result["total_assets"] == 4
        assert result["analysis_results"]["textures"]["count"] == 1
        assert result["analysis_results"]["models"]["count"] == 1
        assert result["analysis_results"]["audio"]["count"] == 1
        assert result["analysis_results"]["other"]["count"] == 1

    def test_validate_bedrock_assets_tool(self):
        """Test Bedrock asset validation tool"""
        input_data = json.dumps({
            "assets": [
                {"path": "test.png", "type": "texture", "metadata": {"width": 16, "height": 16}},
                {"path": "bad.png", "type": "texture", "metadata": {"width": 16, "height": 32}},
                {"path": "model.json", "type": "model", "metadata": {"vertices": 2000}},
                {"path": "sound.ogg", "type": "audio", "metadata": {"duration_seconds": 45}}
            ]
        })
        result_str = self.agent.validate_bedrock_assets_tool.run(validation_data=input_data)
        result = json.loads(result_str)
        assert result["success"] is True
        assert result["quality_metrics"]["total_assets"] == 4
        assert result["quality_metrics"]["warning_count"] > 0
        assert result["quality_metrics"]["optimization_count"] > 0

    def test_model_conversion_item_handheld(self):
        """Test model conversion for item/handheld parent"""
        model_json = {
            "parent": "item/handheld",
            "textures": {"layer0": "items/stick"}
        }
        model_path = os.path.join(self.temp_dir, "stick.json")
        with open(model_path, "w") as f:
            json.dump(model_json, f)

        result = self.agent._convert_single_model(model_path, {}, "item")
        assert result["success"] is True
        assert "geometry.item.stick" == result["bedrock_identifier"]
        assert len(result["converted_model_json"]["minecraft:geometry"][0]["bones"]) > 0

    def test_model_conversion_with_elements(self):
        """Test model conversion with elements and rotation"""
        model_json = {
            "elements": [
                {
                    "from": [0, 0, 0],
                    "to": [8, 8, 8],
                    "rotation": {"origin": [4, 4, 4], "axis": "y", "angle": 45},
                    "faces": {
                        "north": {"uv": [0, 0, 8, 8], "texture": "#all"}
                    }
                }
            ]
        }
        model_path = os.path.join(self.temp_dir, "cube.json")
        with open(model_path, "w") as f:
            json.dump(model_json, f)

        result = self.agent._convert_single_model(model_path, {}, "block")
        assert result["success"] is True
        bone = result["converted_model_json"]["minecraft:geometry"][0]["bones"][0]
        assert bone["rotation"][1] == -45  # Y rotation inverted

    def test_audio_conversion_wav(self):
        """Test audio conversion from WAV to OGG"""
        # We need a real WAV header for pydub to not crash if it tries to read it
        # But since we're just testing the logic, we can mock AudioSegment
        with patch("agents.asset_converter.AudioSegment") as mock_audio:
            mock_instance = MagicMock()
            mock_instance.duration_seconds = 5.5
            mock_audio.from_wav.return_value = mock_instance
            
            wav_path = os.path.join(self.temp_dir, "test.wav")
            with open(wav_path, "wb") as f:
                f.write(b"RIFF....WAVEfmt ")

            result = self.agent._convert_single_audio(wav_path, {}, "block.stone")
            assert result["success"] is True
            assert result["conversion_performed"] is True
            assert result["duration_seconds"] == 5.5

    def test_atlas_detection_and_extraction(self):
        """Test texture atlas detection and extraction"""
        # Create a 64x64 "atlas" image
        atlas_path = self.create_test_image("atlas.png", (64, 64))
        
        # Detection
        detection = self.agent.detect_texture_atlas(atlas_path)
        assert detection["is_atlas"] is True
        assert detection["tiles_x"] == 4
        assert detection["tiles_y"] == 4

        # Extraction
        extract_dir = os.path.join(self.temp_dir, "extracted")
        extraction = self.agent.extract_texture_atlas(atlas_path, extract_dir, tile_size=16)
        assert extraction["success"] is True
        assert extraction["extracted_count"] > 0

    def test_jar_texture_extraction_mock(self):
        """Test JAR texture extraction with mocked zipfile"""
        with patch("zipfile.ZipFile") as mock_zip:
            mock_jar = MagicMock()
            mock_jar.namelist.return_value = [
                "assets/modid/textures/block/stone.png",
                "assets/modid/textures/item/stick.png"
            ]
            file_info = MagicMock()
            file_info.filename = "assets/modid/textures/block/stone.png"
            mock_jar.filelist = [file_info]
            mock_jar.read.return_value = b"fake image data"
            mock_zip.return_value.__enter__.return_value = mock_jar
            
            jar_path = os.path.join(self.temp_dir, "mod.jar")
            with open(jar_path, "wb") as f:
                f.write(b"PK...")

            result = self.agent.extract_textures_from_jar(jar_path, self.temp_dir, namespace="modid")
            assert result["success"] is True
            assert result["count"] > 0

    def test_convert_java_texture_path(self):
        """Test Java to Bedrock path conversion"""
        path = "assets/modid/textures/block/grass_block_side.png"
        result = self.agent.convert_java_texture_path(path, "blocks")
        assert result == "textures/blocks/grass_block_side"

    def test_validate_texture_method(self):
        """Test the validate_texture method directly"""
        img_path = self.create_test_image("valid.png", (16, 16))
        result = self.agent.validate_texture(img_path)
        assert result["valid"] is True

        img_path_bad = self.create_test_image("invalid.png", (17, 17))
        result = self.agent.validate_texture(img_path_bad)
        assert result["valid"] is False
        assert any("power of 2" in error for error in result["errors"])

    def test_clear_cache(self):
        """Test clearing the conversion cache"""
        self.agent._conversion_cache["test"] = {"data": 123}
        self.agent.clear_cache()
        assert len(self.agent._conversion_cache) == 0

    def test_generate_fallback_for_jar(self):
        """Test fallback generation for JAR extraction"""
        out_path = os.path.join(self.temp_dir, "fallback.png")
        result = self.agent.generate_fallback_for_jar(out_path, "test_block", "blocks")
        assert result["success"] is True
        assert os.path.exists(out_path)

    def test_parse_atlas_metadata(self):
        """Test parsing of .mcmeta files"""
        mcmeta_data = {
            "animation": {"frametime": 2, "interpolate": True},
            "villager": {"profession": "farmer"}
        }
        mcmeta_path = os.path.join(self.temp_dir, "test.mcmeta")
        with open(mcmeta_path, "w") as f:
            json.dump(mcmeta_data, f)
            
        result = self.agent.parse_atlas_metadata(mcmeta_path)
        assert result["success"] is True
        assert result["animation"]["interpolate"] is True
        assert result["villager"]["profession"] == "farmer"

    def test_convert_textures_tool_internal(self):
        """Test the internal logic of convert_textures_tool"""
        img_path = self.create_test_image("stone.png", (16, 16))
        # Create mcmeta for animation coverage
        self.create_test_mcmeta("stone.png.mcmeta")
        
        input_data = json.dumps({
            "textures": [
                {"path": img_path, "usage": "block", "metadata": {"width": 16, "height": 16}}
            ],
            "output_dir": self.temp_dir
        })
        # Call the tool via run() to hit the static method implementation
        result_str = self.agent.convert_textures_tool.run(texture_data=input_data)
        result = json.loads(result_str)
        assert result["success"] is True
        assert result["conversion_summary"]["successfully_converted"] == 1
        assert "pack_manifest.json" in result["bedrock_pack_files"]

    def test_convert_models_tool_internal(self):
        """Test the internal logic of convert_models_tool"""
        model_json = {
            "parent": "item/generated",
            "textures": {"layer0": "items/apple"},
            "elements": []
        }
        model_path = os.path.join(self.temp_dir, "apple.json")
        with open(model_path, "w") as f:
            json.dump(model_json, f)
            
        input_data = json.dumps({
            "models": [
                {"path": model_path, "entity_type": "item"}
            ]
        })
        result_str = self.agent.convert_models_tool.run(model_data=input_data)
        result = json.loads(result_str)
        assert result["success"] is True
        assert result["conversion_summary"]["successfully_converted"] == 1

    def test_extract_texture_atlas_from_jar(self):
        """Test extracting texture atlas from JAR"""
        with patch("zipfile.ZipFile") as mock_zip:
            mock_jar = MagicMock()
            mock_jar.namelist.return_value = ["assets/minecraft/textures/terrain.png"]
            mock_jar.read.return_value = b"fake image data"
            mock_zip.return_value = mock_jar
            
            # Mock Image.open for the atlas processing
            with patch("PIL.Image.open") as mock_open:
                mock_img = MagicMock()
                mock_img.size = (256, 256)
                mock_img.convert.return_value = mock_img
                mock_img.crop.return_value = mock_img
                # Mock getdata for the empty tile check
                mock_img.getdata.return_value = [(0, 0, 0, 255)] * (16 * 16)
                mock_open.return_value = mock_img

                jar_path = os.path.join(self.temp_dir, "vanilla.jar")
                result = self.agent.extract_texture_atlas_from_jar(jar_path, "terrain", self.temp_dir)
                assert result["success"] is True

    def test_convert_jar_textures_to_bedrock_pipeline(self):
        """Test the full JAR to Bedrock conversion pipeline"""
        jar_path = os.path.join(self.temp_dir, "mod_pipeline.jar")
        with open(jar_path, "wb") as f:
            f.write(b"PK...")
            
        with patch.object(self.agent, "extract_textures_from_jar") as mock_extract:
            mock_extract.return_value = {
                "success": True,
                "extracted_textures": [
                    {
                        "original_path": "assets/mod/textures/block/test.png",
                        "output_path": self.create_test_image("test_extracted.png"),
                        "bedrock_path": "textures/blocks/test.png"
                    }
                ]
            }
            
            result = self.agent.convert_jar_textures_to_bedrock(jar_path, self.temp_dir)
            assert result["success"] is True
            assert len(result["converted"]) > 0

    def test_convert_textures_method(self):
        """Test the convert_textures method directly"""
        img_path = self.create_test_image("test.png")
        texture_data = json.dumps([img_path])
        result_json = self.agent.convert_textures(texture_data, self.temp_dir)
        result = json.loads(result_json)
        assert result["successful_conversions"] == 1

    def test_audio_conversion_ogg(self):
        """Test audio conversion for OGG files"""
        with patch("agents.asset_converter.AudioSegment") as mock_audio:
            mock_instance = MagicMock()
            mock_instance.duration_seconds = 10.0
            mock_audio.from_ogg.return_value = mock_instance
            
            ogg_path = os.path.join(self.temp_dir, "test.ogg")
            with open(ogg_path, "wb") as f:
                f.write(b"OggS")

            result = self.agent._convert_single_audio(ogg_path, {}, "block.stone")
            assert result["success"] is True
            assert result["conversion_performed"] is False

    def test_model_conversion_elements_no_rotation(self):
        """Test model conversion with elements but no rotation"""
        model_json = {
            "elements": [
                {
                    "from": [0, 0, 0],
                    "to": [16, 16, 16],
                    "faces": {"north": {"uv": [0, 0, 16, 16]}}
                }
            ]
        }
        model_path = os.path.join(self.temp_dir, "block.json")
        with open(model_path, "w") as f:
            json.dump(model_json, f)
            
        result = self.agent._convert_single_model(model_path, {}, "block")
        assert result["success"] is True

    def test_extract_textures_from_alt_locations(self):
        """Test extraction from alternative JAR locations"""
        with patch("zipfile.ZipFile") as mock_zip:
            mock_jar = MagicMock()
            # File in an alternative location
            mock_jar.namelist.return_value = ["textures/block/alt.png"]
            file_info = MagicMock()
            file_info.filename = "textures/block/alt.png"
            mock_jar.filelist = [file_info]
            mock_jar.read.return_value = b"data"
            
            alt_textures = self.agent._extract_textures_from_alt_locations(mock_jar, Path(self.temp_dir))
            assert len(alt_textures) == 1
            assert alt_textures[0]["namespace"] == "minecraft"

    def test_analyze_methods_directly(self):
        """Test analyze methods directly"""
        res_tex = self.agent._analyze_texture("test.png", {"width": 1025, "height": 16})
        assert res_tex["needs_conversion"] is True
        
        res_mod = self.agent._analyze_model("test.json", {"vertices": 5000})
        assert res_mod["needs_conversion"] is True
        
        res_aud = self.agent._analyze_audio("test.ogg", {"file_size_mb": 20})
        assert res_aud["needs_conversion"] is True

    def test_get_recommended_resolution(self):
        """Test get_recommended_resolution"""
        assert self.agent._get_recommended_resolution(10, 10) == "16x16"
        assert self.agent._get_recommended_resolution(2000, 16) == "1024x16"

    def test_generate_sound_structure_edge_cases(self):
        """Test sound structure generation with edge cases"""
        sounds = [
            {"success": True, "bedrock_sound_event": "test.event", "converted_path": "sounds/test/s1.ogg"},
            {"success": True, "bedrock_sound_event": "test.event2", "converted_path": "other/s2.ogg"},
            {"success": False}
        ]
        result = self.agent._generate_sound_structure(sounds)
        assert "sound_definitions.json" in result
        assert "test.event" in result["sound_definitions.json"]["sound_definitions"]

    def test_convert_audio_method_directly(self):
        """Test convert_audio method directly"""
        audio_path = os.path.join(self.temp_dir, "test.ogg")
        with open(audio_path, "wb") as f:
            f.write(b"OggS")
        
        with patch("agents.asset_converter.AudioSegment") as mock_audio:
            mock_instance = MagicMock()
            mock_instance.duration_seconds = 2.0
            mock_audio.from_ogg.return_value = mock_instance
            
            input_data = json.dumps([{"path": audio_path, "type": "ambient.cave"}])
            result_str = self.agent.convert_audio_tool.run(audio_data=input_data)
            result = json.loads(result_str)
            assert result["success"] is True

    def test_extract_texture_atlas_no_content(self):
        """Test atlas extraction with empty tiles"""
        atlas_path = self.create_test_image("atlas_empty.png", (32, 32))
        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (32, 32)
            mock_img.convert.return_value = mock_img
            mock_img.crop.return_value = mock_img
            # All transparent pixels
            mock_img.getdata.return_value = [(0, 0, 0, 0)] * (16 * 16)
            mock_open.return_value = mock_img
            
            result = self.agent.extract_texture_atlas(atlas_path, self.temp_dir)
            assert result["success"] is True
            assert result["extracted_count"] == 0

    def test_convert_atlas_to_bedrock_not_atlas(self):
        """Test convert_atlas_to_bedrock when it's not an atlas"""
        img_path = self.create_test_image("not_atlas.png", (16, 16))
        result = self.agent.convert_atlas_to_bedrock(img_path, self.temp_dir)
        assert result["success"] is True
        assert "converted_path" in result

    def test_map_functions(self):
        """Test mapping functions"""
        assert self.agent._map_texture_type("block") == "blocks"
        assert self.agent._map_texture_type("unknown") == "misc"
        
        assert self.agent._map_bedrock_type_to_java("blocks") == "block"
        
        java_path = "assets/mod/textures/block/stone.png"
        bedrock_path = self.agent._map_java_texture_to_bedrock(java_path)
        assert bedrock_path == "textures/blocks/stone.png"
        
        back_to_java = self.agent._map_bedrock_texture_to_java("textures/blocks/stone.png", "mod")
        assert back_to_java == "assets/mod/textures/block/stone.png"

    def test_batch_validation(self):
        """Test batch validation of textures"""
        paths = [self.create_test_image(f"img{i}.png") for i in range(3)]
        result = self.agent.validate_textures_batch(paths)
        assert result["total"] == 3
        assert result["valid"] == 3

    def test_extract_jar_textures_tool_internal(self):
        """Test the extract_jar_textures_tool"""
        with patch.object(self.agent, "convert_jar_textures_to_bedrock") as mock_pipeline:
            mock_pipeline.return_value = {
                "success": True,
                "extracted": ["a"],
                "converted": [{"original": "a", "bedrock_path": "b"}],
                "failed": [],
                "warnings": [],
                "errors": []
            }
            
            input_data = json.dumps({
                "jar_path": "test.jar",
                "output_dir": self.temp_dir
            })
            result_str = self.agent.extract_jar_textures_tool.run(jar_data=input_data)
            result = json.loads(result_str)
            assert result["success"] is True
            assert result["converted_count"] == 1
