"""
Integration tests for the texture conversion pipeline with file saving
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image


def create_test_texture(path: Path, size=(64, 64), color=(128, 128, 128, 255)):
    """Helper to create test texture files"""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", size, color)
    img.save(path, "PNG")


def test_full_texture_conversion_pipeline():
    """
    Test the complete texture conversion pipeline from input to output files.
    This simulates what would happen when converting a Java mod to Bedrock.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create input directory structure
        input_dir = temp_path / "input"
        output_dir = temp_path / "output"

        # Create sample textures mimicking a Java mod structure
        textures = {
            "stone.png": (32, 32, (128, 128, 128, 255)),
            "dirt.png": (16, 16, (139, 90, 43, 255)),
            "grass_block_top.png": (16, 16, (100, 180, 60, 255)),
            "diamond_sword.png": (16, 16, (100, 220, 255, 255)),
            "custom_block.png": (33, 45, (200, 100, 50, 255)),  # Non-power-of-2
        }

        for filename, (width, height, color) in textures.items():
            create_test_texture(input_dir / filename, (width, height), color)

        # Import the agent
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from agents.asset_converter import AssetConverterAgent

        agent = AssetConverterAgent.get_instance()

        # Prepare texture data for conversion
        texture_data = {
            "textures": [
                {"path": str(input_dir / "stone.png"), "usage": "block"},
                {"path": str(input_dir / "dirt.png"), "usage": "block"},
                {"path": str(input_dir / "grass_block_top.png"), "usage": "block"},
                {"path": str(input_dir / "diamond_sword.png"), "usage": "item"},
                {"path": str(input_dir / "custom_block.png"), "usage": "block"},
            ],
            "output_dir": str(output_dir),
        }

        # Convert textures
        result_json = agent.convert_textures(json.dumps(texture_data), str(output_dir))
        result = json.loads(result_json)

        # Verify results

        assert result["total_textures"] == 5, f"Expected 5 textures, got {result['total_textures']}"
        assert result["successful_conversions"] == 5, (
            f"Expected 5 successful conversions, got {result['successful_conversions']}"
        )
        assert result["failed_conversions"] == 0, (
            f"Expected 0 failures, got {result['failed_conversions']}"
        )

        # Verify output files exist
        for converted in result["converted_textures"]:
            output_path = Path(converted["converted_path"])
            assert output_path.exists(), f"Output file not created: {output_path}"

            # Verify the file is a valid PNG
            img = Image.open(output_path)
            assert img.format == "PNG", f"Output file is not PNG: {output_path}"
            assert img.mode == "RGBA", f"Output file is not RGBA: {output_path}"

            # Verify dimensions
            dimensions = converted["dimensions"]
            assert list(img.size) == dimensions, (
                f"Dimension mismatch for {output_path}: expected {dimensions}, got {img.size}"
            )

        # Verify Bedrock directory structure
        expected_structure = [
            output_dir / "textures" / "blocks" / "stone.png",
            output_dir / "textures" / "blocks" / "dirt.png",
            output_dir / "textures" / "blocks" / "grass_block_top.png",
            output_dir / "textures" / "blocks" / "custom_block.png",
            output_dir / "textures" / "items" / "diamond_sword.png",
        ]

        for expected_file in expected_structure:
            assert expected_file.exists(), f"Expected file not found: {expected_file}"

        # Verify power-of-2 resizing was applied to custom_block.png
        custom_block_result = next(
            r for r in result["converted_textures"] if "custom_block" in r["converted_path"]
        )
        assert custom_block_result["resized"] is True, "custom_block.png should have been resized"
        assert tuple(custom_block_result["dimensions"]) == (64, 64), (
            f"Expected (64, 64), got {custom_block_result['dimensions']}"
        )


def test_fallback_texture_generation():
    """Test that fallback textures are generated for missing files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        output_dir = temp_path / "output"

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from agents.asset_converter import AssetConverterAgent

        agent = AssetConverterAgent.get_instance()

        # Try to convert a non-existent file
        texture_data = {
            "textures": [
                {"path": "/nonexistent/texture.png", "usage": "block"},
            ],
            "output_dir": str(output_dir),
        }

        result_json = agent.convert_textures(json.dumps(texture_data), str(output_dir))
        result = json.loads(result_json)

        assert result["successful_conversions"] == 1, "Fallback should be generated successfully"

        # Verify fallback file was created
        fallback_file = next(r for r in result["converted_textures"] if r["success"])
        output_path = Path(fallback_file["converted_path"])

        assert output_path.exists(), f"Fallback file not created: {output_path}"

        # Verify it's a valid PNG
        img = Image.open(output_path)
        assert img.format == "PNG"
        assert img.mode == "RGBA"


def test_texture_atlas_detection():
    """Test texture atlas detection for simple mods"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        output_dir = temp_path / "output"

        # Create a set of related textures that would form an atlas
        textures = [
            "oak_log.png",
            "oak_log_top.png",
            "oak_leaves.png",
        ]

        for texture in textures:
            create_test_texture(input_dir / texture, (16, 16), (100, 80, 40, 255))

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from agents.asset_converter import AssetConverterAgent

        agent = AssetConverterAgent.get_instance()

        texture_data = {
            "textures": [{"path": str(input_dir / t), "usage": "block"} for t in textures],
            "output_dir": str(output_dir),
        }

        result_json = agent.convert_textures(json.dumps(texture_data), str(output_dir))
        result = json.loads(result_json)

        # All conversions should succeed
        assert result["successful_conversions"] == 3

        # Verify all files exist
        for converted in result["converted_textures"]:
            assert Path(converted["converted_path"]).exists()


def test_performance_benchmark():
    """Benchmark texture conversion performance"""
    import time

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        output_dir = temp_path / "output"

        # Create 100 textures of varying sizes
        num_textures = 100
        textures = []

        for i in range(num_textures):
            size = (
                (16, 16)
                if i % 4 == 0
                else (32, 32)
                if i % 4 == 1
                else (64, 64)
                if i % 4 == 2
                else (128, 128)
            )
            filename = f"texture_{i}.png"
            create_test_texture(input_dir / filename, size, (128, 128, 128, 255))
            textures.append({"path": str(input_dir / filename), "usage": "block"})

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from agents.asset_converter import AssetConverterAgent

        agent = AssetConverterAgent.get_instance()

        texture_data = {"textures": textures, "output_dir": str(output_dir)}

        # Measure conversion time
        start_time = time.time()
        result_json = agent.convert_textures(json.dumps(texture_data), str(output_dir))
        end_time = time.time()

        result = json.loads(result_json)
        total_time = end_time - start_time

        # Verify success rate
        success_rate = result["successful_conversions"] / num_textures

        assert result["successful_conversions"] == num_textures
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} is below 95% threshold"

        # Verify performance meets requirements (<1s per texture)
        avg_time_ms = (total_time / num_textures) * 1000
        assert avg_time_ms < 1000, f"Average time {avg_time_ms:.2f}ms exceeds 1000ms threshold"


if __name__ == "__main__":
    test_full_texture_conversion_pipeline()
    test_fallback_texture_generation()
    test_texture_atlas_detection()
    test_performance_benchmark()
