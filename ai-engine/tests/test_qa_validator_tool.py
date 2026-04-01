"""
Unit tests for the standalone QAValidator tool.
"""

import json
import os
import tempfile
from pathlib import Path
import pytest
from tools.qa_validator import QAValidator, ValidationStatus, validate_output


@pytest.fixture
def temp_addon_dir():
    """Create a temporary Bedrock addon directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create manifest.json
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Test Pack",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "modules": [
                {
                    "type": "resources",
                    "uuid": "87654321-4321-4321-4321-210987654321",
                    "version": [1, 0, 0]
                }
            ]
        }
        with open(tmp_path / "manifest.json", "w") as f:
            json.dump(manifest, f)
            
        # Create blocks directory and a block
        blocks_dir = tmp_path / "blocks"
        blocks_dir.mkdir()
        block_def = {
            "minecraft:block": {
                "description": {"identifier": "test:block"}
            }
        }
        with open(blocks_dir / "test_block.json", "w") as f:
            json.dump(block_def, f)
            
        # Create textures directory
        textures_dir = tmp_path / "textures"
        textures_dir.mkdir()
        # Create a dummy PNG (minimal 1x1)
        with open(textures_dir / "test.png", "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\x0d\n\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
            
        yield str(tmp_path)


def test_validator_all(temp_addon_dir):
    """Test full validation of a mock addon."""
    validator = QAValidator(temp_addon_dir)
    report = validator.validate_all("Test Pack")
    
    assert report.pack_name == "Test Pack"
    assert report.quality_score > 0
    assert report.failed_checks == 0
    
    # Check specific results
    results_dict = {r.check_name: r.status for r in report.results}
    assert results_dict["manifest_required_fields"] == ValidationStatus.PASS
    assert results_dict["header_uuid_format"] == ValidationStatus.PASS
    assert results_dict["blocks_exist"] == ValidationStatus.PASS


def test_validator_missing_manifest(temp_addon_dir):
    """Test validation with missing manifest."""
    os.remove(os.path.join(temp_addon_dir, "manifest.json"))
    report = validate_output(temp_addon_dir)
    
    assert report.failed_checks > 0
    results_dict = {r.check_name: r.status for r in report.results}
    assert results_dict["manifest_exists"] == ValidationStatus.FAIL


def test_validator_invalid_manifest_json(temp_addon_dir):
    """Test validation with invalid manifest JSON."""
    with open(os.path.join(temp_addon_dir, "manifest.json"), "w") as f:
        f.write("{invalid json")
    
    report = validate_output(temp_addon_dir)
    results_dict = {r.check_name: r.status for r in report.results}
    assert results_dict["manifest_valid_json"] == ValidationStatus.FAIL


def test_report_to_dict(temp_addon_dir):
    """Test converting report to dictionary."""
    report = validate_output(temp_addon_dir)
    report_dict = report.to_dict()
    
    assert report_dict["pack_name"] == "Bedrock Add-on"
    assert "quality_score" in report_dict
    assert isinstance(report_dict["results"], list)
