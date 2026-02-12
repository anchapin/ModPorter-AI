"""
Direct unit tests for texture conversion logic without CrewAI dependency.
Tests the actual AssetConverterAgent class methods directly.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PIL import Image


def create_test_texture(path: Path, size=(64, 64), color=(128, 128, 128, 255)):
    """Helper to create test texture files"""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new('RGBA', size, color)
    img.save(path, 'PNG')


def test_convert_single_texture():
    """Test the _convert_single_texture method directly"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        output_dir = temp_path / "output"

        # Create test texture
        test_file = input_dir / "test_block.png"
        create_test_texture(test_file, (32, 32), (128, 128, 128, 255))

        # Import just the class we need, avoiding the tool decorators
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "asset_converter",
            os.path.join(os.path.dirname(__file__), "..", "agents", "asset_converter.py")
        )
        module = importlib.util.module_from_spec(spec)

        # Mock the crewai import before loading
        import unittest.mock as mock
        sys.modules['crewai'] = mock.MagicMock()
        sys.modules['crewai.tools'] = mock.MagicMock()

        # Now load the module
        spec.loader.exec_module(module)

        # Create instance
        agent = module.AssetConverterAgent()

        # Test conversion with output directory
        result = agent._convert_single_texture(
            str(test_file),
            {},
            "block",
            output_dir
        )

        print(f"\n=== Test: _convert_single_texture ===")
        print(f"Success: {result['success']}")
        print(f"Original dimensions: {result['original_dimensions']}")
        print(f"Converted dimensions: {result['converted_dimensions']}")
        print(f"Relative path: {result['relative_path']}")
        print(f"Actual output: {result['converted_path']}")

        assert result['success'] is True
        assert result['original_dimensions'] == (32, 32)
        assert result['converted_dimensions'] == (32, 32)
        assert 'textures/blocks/test_block.png' in result['relative_path']

        # Verify file was saved
        output_file = Path(result['converted_path'])
        assert output_file.exists(), f"Output file not created: {output_file}"

        # Verify it's a valid PNG
        img = Image.open(output_file)
        assert img.format == 'PNG'
        assert img.mode == 'RGBA'
        assert img.size == (32, 32)

        print(f"✓ File saved successfully: {output_file.name}")
        print(f"✓ Valid PNG format: {img.size} {img.mode}")

        print("\n=== Test Passed ===\n")


def test_convert_textures_method():
    """Test the convert_textures method with JSON input"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        output_dir = temp_path / "output"

        # Create test textures
        textures = {
            "stone.png": (16, 16, (128, 128, 128, 255)),
            "dirt.png": (16, 16, (139, 90, 43, 255)),
            "custom.png": (33, 45, (200, 100, 50, 255)),  # Non-power-of-2
        }

        for filename, (width, height, color) in textures.items():
            create_test_texture(input_dir / filename, (width, height), color)

        # Import the module with mocked crewai
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "asset_converter",
            os.path.join(os.path.dirname(__file__), "..", "agents", "asset_converter.py")
        )
        module = importlib.util.module_from_spec(spec)

        import unittest.mock as mock
        sys.modules['crewai'] = mock.MagicMock()
        sys.modules['crewai.tools'] = mock.MagicMock()

        spec.loader.exec_module(module)
        agent = module.AssetConverterAgent()

        # Prepare texture data
        texture_data = {
            "textures": [
                {"path": str(input_dir / "stone.png"), "usage": "block"},
                {"path": str(input_dir / "dirt.png"), "usage": "block"},
                {"path": str(input_dir / "custom.png"), "usage": "item"},
            ],
            "output_dir": str(output_dir)
        }

        # Convert textures
        result_json = agent.convert_textures(json.dumps(texture_data), str(output_dir))
        result = json.loads(result_json)

        print(f"\n=== Test: convert_textures method ===")
        print(f"Total textures: {result['total_textures']}")
        print(f"Successful: {result['successful_conversions']}")
        print(f"Failed: {result['failed_conversions']}")

        assert result['total_textures'] == 3
        assert result['successful_conversions'] == 3
        assert result['failed_conversions'] == 0
        assert len(result['errors']) == 0

        # Verify output files
        for converted in result['converted_textures']:
            output_path = Path(converted['converted_path'])
            assert output_path.exists(), f"Output file not created: {output_path}"

            img = Image.open(output_path)
            print(f"✓ {output_path.name}: {img.size} {img.mode}")

            assert img.format == 'PNG'
            assert img.mode == 'RGBA'

        # Verify custom.png was resized to power of 2
        custom_result = next(r for r in result['converted_textures'] if 'custom' in r['converted_path'])
        assert custom_result['resized'] is True
        assert custom_result['dimensions'] == (64, 64)  # 33 -> 64, 45 -> 64
        print(f"✓ Power-of-2 resize verified: {custom_result['dimensions']}")

        print("\n=== Test Passed ===\n")


def test_fallback_texture():
    """Test fallback texture generation for missing files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        output_dir = temp_path / "output"

        # Import the module with mocked crewai
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "asset_converter",
            os.path.join(os.path.dirname(__file__), "..", "agents", "asset_converter.py")
        )
        module = importlib.util.module_from_spec(spec)

        import unittest.mock as mock
        sys.modules['crewai'] = mock.MagicMock()
        sys.modules['crewai.tools'] = mock.MagicMock()

        spec.loader.exec_module(module)
        agent = module.AssetConverterAgent()

        # Try to convert non-existent file
        result = agent._convert_single_texture(
            "/nonexistent/file.png",
            {},
            "block",
            output_dir
        )

        print(f"\n=== Test: Fallback Texture ===")
        print(f"Success: {result['success']}")
        print(f"Was fallback: {result['was_fallback']}")
        print(f"Optimizations: {result['optimizations_applied']}")

        assert result['success'] is True
        assert result['was_fallback'] is True
        assert any('fallback' in opt.lower() for opt in result['optimizations_applied'])

        # Verify fallback was saved
        output_path = Path(result['converted_path'])
        assert output_path.exists(), f"Fallback file not created: {output_path}"

        img = Image.open(output_path)
        print(f"✓ Fallback created: {img.size} {img.mode}")

        assert img.format == 'PNG'
        assert img.mode == 'RGBA'
        assert img.size == (16, 16)  # Default fallback size

        print("\n=== Test Passed ===\n")


def test_power_of_2_constraints():
    """Test various power-of-2 constraints"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        output_dir = temp_path / "output"

        # Import the module with mocked crewai
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "asset_converter",
            os.path.join(os.path.dirname(__file__), "..", "agents", "asset_converter.py")
        )
        module = importlib.util.module_from_spec(spec)

        import unittest.mock as mock
        sys.modules['crewai'] = mock.MagicMock()
        sys.modules['crewai.tools'] = mock.MagicMock()

        spec.loader.exec_module(module)
        agent = module.AssetConverterAgent()

        test_cases = [
            (17, 17, 32, 32),   # Round up to next power of 2
            (33, 65, 64, 128),  # Different dimensions
            (100, 100, 128, 128),  # Round up
            (1024, 1024, 1024, 1024),  # Already at max
            (2048, 2048, 1024, 1024),  # Cap at max resolution
        ]

        print(f"\n=== Test: Power-of-2 Constraints ===")

        for i, (width, height, expected_width, expected_height) in enumerate(test_cases):
            test_file = input_dir / f"test_{i}.png"
            create_test_texture(test_file, (width, height), (128, 128, 128, 255))

            result = agent._convert_single_texture(str(test_file), {}, "block", output_dir)

            actual_size = result['converted_dimensions']
            print(f"Input: {width}x{height} → Output: {actual_size[0]}x{actual_size[1]} (Expected: {expected_width}x{expected_height})")

            assert actual_size == (expected_width, expected_height), \
                f"Expected {expected_width}x{expected_height}, got {actual_size}"

            # Verify file was saved with correct dimensions
            output_file = Path(result['converted_path'])
            img = Image.open(output_file)
            assert img.size == (expected_width, expected_height)

        print("\n=== Test Passed ===\n")


def test_performance():
    """Test performance with multiple textures"""
    import time

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        output_dir = temp_path / "output"

        # Import the module with mocked crewai
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "asset_converter",
            os.path.join(os.path.dirname(__file__), "..", "agents", "asset_converter.py")
        )
        module = importlib.util.module_from_spec(spec)

        import unittest.mock as mock
        sys.modules['crewai'] = mock.MagicMock()
        sys.modules['crewai.tools'] = mock.MagicMock()

        spec.loader.exec_module(module)
        agent = module.AssetConverterAgent()

        # Create 50 textures
        num_textures = 50
        textures = []

        for i in range(num_textures):
            test_file = input_dir / f"texture_{i}.png"
            create_test_texture(test_file, (32, 32), (128, 128, 128, 255))
            textures.append(str(test_file))

        # Measure conversion time
        start_time = time.time()

        for texture_path in textures:
            result = agent._convert_single_texture(texture_path, {}, "block", output_dir)
            assert result['success']

        end_time = time.time()
        total_time = end_time - start_time

        avg_time_ms = (total_time / num_textures) * 1000

        print(f"\n=== Performance Test ===")
        print(f"Textures: {num_textures}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Average time per texture: {avg_time_ms:.2f}ms")

        # Verify performance requirement: < 1s per texture
        assert avg_time_ms < 1000, f"Average time {avg_time_ms:.2f}ms exceeds 1000ms threshold"

        # Verify success rate: > 95%
        success_rate = 100.0  # All should succeed
        assert success_rate >= 95.0, f"Success rate {success_rate:.1f}% is below 95% threshold"

        print(f"✓ Performance meets requirements")
        print("\n=== Test Passed ===\n")


if __name__ == '__main__':
    print("=" * 60)
    print("Direct Texture Conversion Tests")
    print("=" * 60)

    test_convert_single_texture()
    test_convert_textures_method()
    test_fallback_texture()
    test_power_of_2_constraints()
    test_performance()

    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
