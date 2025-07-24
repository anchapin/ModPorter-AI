"""
Test to validate that the simple_copper_block.jar fixture is properly structured
and can be used for testing the ModPorter AI pipeline.

This test ensures Issue #174 requirements are met:
- Simple test mod .jar file exists
- Has proper structure for conversion testing  
- Expected conversion output is documented
"""

import json
import zipfile
from pathlib import Path
import pytest

# Import the fixture creation utilities
from simple_copper_block import get_expected_analysis_result, get_expected_bedrock_block


def test_simple_copper_block_jar_exists():
    """Test that the JAR fixture file exists."""
    fixtures_dir = Path(__file__).parent
    jar_path = fixtures_dir / "simple_copper_block.jar"
    
    assert jar_path.exists(), f"JAR fixture not found at {jar_path}"
    assert jar_path.stat().st_size > 0, "JAR file is empty"


def test_jar_has_required_structure():
    """Test that the JAR contains all required files for testing."""
    fixtures_dir = Path(__file__).parent
    jar_path = fixtures_dir / "simple_copper_block.jar"
    
    with zipfile.ZipFile(jar_path, 'r') as zf:
        files = zf.namelist()
        
        # Check for required files
        required_files = [
            'fabric.mod.json',
            'assets/simple_copper/textures/block/polished_copper.png',
            'com/example/simple_copper/PolishedCopperBlock.class',
            'com/example/simple_copper/PolishedCopperBlock.java',
            'META-INF/MANIFEST.MF'
        ]
        
        for required_file in required_files:
            assert required_file in files, f"Missing required file: {required_file}"


def test_fabric_mod_json_structure():
    """Test that fabric.mod.json has the expected structure."""
    fixtures_dir = Path(__file__).parent
    jar_path = fixtures_dir / "simple_copper_block.jar"
    
    with zipfile.ZipFile(jar_path, 'r') as zf:
        fabric_mod_content = zf.read('fabric.mod.json').decode('utf-8')
        fabric_mod = json.loads(fabric_mod_content)
        
        # Verify key fields
        assert fabric_mod['id'] == 'simple_copper', "Incorrect mod ID"
        assert fabric_mod['version'] == '1.0.0', "Incorrect version"
        assert fabric_mod['name'] == 'Simple Copper Block', "Incorrect mod name"
        


def test_texture_file_present():
    """Test that the block texture file is present and accessible."""
    fixtures_dir = Path(__file__).parent
    jar_path = fixtures_dir / "simple_copper_block.jar"
    
    with zipfile.ZipFile(jar_path, 'r') as zf:
        texture_path = 'assets/simple_copper/textures/block/polished_copper.png'
        
        # Check file exists in JAR
        assert texture_path in zf.namelist(), f"Texture file {texture_path} not found"
        
        # Check file has content
        texture_data = zf.read(texture_path)
        assert len(texture_data) > 0, "Texture file is empty"
        assert texture_data.startswith(b'\x89PNG'), "Texture file is not a valid PNG"


def test_expected_analysis_result():
    """Test that the expected analysis result is properly defined."""
    expected = get_expected_analysis_result()
    
    assert isinstance(expected, dict), "Expected result should be a dictionary"
    assert expected['success'] is True, "Expected analysis should be successful"
    assert expected['registry_name'] == 'simple_copper:polished_copper', "Incorrect expected registry name"
    assert expected['texture_path'] == 'assets/simple_copper/textures/block/polished_copper.png', "Incorrect expected texture path"
    assert isinstance(expected['errors'], list), "Errors should be a list"


def test_expected_bedrock_block():
    """Test that the expected Bedrock block definition is properly structured."""
    expected = get_expected_bedrock_block()
    
    assert isinstance(expected, dict), "Expected block should be a dictionary"
    assert 'format_version' in expected, "Missing format_version"
    assert 'minecraft:block' in expected, "Missing minecraft:block"
    
    block_def = expected['minecraft:block']
    assert 'description' in block_def, "Missing block description"
    assert 'components' in block_def, "Missing block components"
    
    description = block_def['description']
    assert description['identifier'] == 'simple_copper:polished_copper', "Incorrect block identifier"


def test_jar_can_be_opened_multiple_times():
    """Test that the JAR can be opened and read multiple times without corruption."""
    fixtures_dir = Path(__file__).parent
    jar_path = fixtures_dir / "simple_copper_block.jar"
    
    # Open the JAR multiple times to ensure it's not corrupted
    for i in range(3):
        with zipfile.ZipFile(jar_path, 'r') as zf:
            files = zf.namelist()
            assert len(files) >= 5, f"JAR should contain at least 5 files, found {len(files)}"
            
            # Read a file to ensure data integrity
            fabric_content = zf.read('fabric.mod.json')
            fabric_data = json.loads(fabric_content.decode('utf-8'))
            assert fabric_data['id'] == 'simple_copper', "Data corruption detected"


def test_readme_documentation_exists():
    """Test that README documentation for fixtures exists."""
    fixtures_dir = Path(__file__).parent
    readme_path = fixtures_dir / "README.md"
    
    assert readme_path.exists(), "README.md documentation not found"
    
    # Check that README contains key information
    readme_content = readme_path.read_text()
    assert "simple_copper_block.jar" in readme_content, "README should document the JAR fixture"
    assert "Expected Conversion Output" in readme_content, "README should document expected outputs"
    assert "registry_name" in readme_content, "README should document registry name extraction"


if __name__ == "__main__":
    # Run basic validation when executed directly
    print("Validating simple_copper_block.jar fixture...")
    
    test_simple_copper_block_jar_exists()
    print("✓ JAR file exists")
    
    test_jar_has_required_structure()
    print("✓ JAR has required structure")
    
    test_fabric_mod_json_structure()
    print("✓ fabric.mod.json is valid")
    
    test_texture_file_present()
    print("✓ Texture file is present and valid")
    
    test_expected_analysis_result()
    print("✓ Expected analysis result is valid")
    
    test_expected_bedrock_block()
    print("✓ Expected Bedrock block definition is valid")
    
    test_jar_can_be_opened_multiple_times()
    print("✓ JAR integrity is maintained")
    
    test_readme_documentation_exists()
    print("✓ README documentation exists")
    
    print("\n🎉 All fixture validation tests passed!")
    print("The simple_copper_block.jar fixture is ready for use in testing.")