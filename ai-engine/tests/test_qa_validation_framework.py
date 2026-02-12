"""
Tests for QA Validation Framework implementation
"""

import pytest
import json
import zipfile
import tempfile
import shutil
from pathlib import Path
from agents.qa_validator import QAValidatorAgent, VALIDATION_RULES


class TestValidationRules:
    """Test that validation rules are properly defined."""

    def test_manifest_rules_exist(self):
        """Test manifest validation rules."""
        assert "manifest" in VALIDATION_RULES
        rules = VALIDATION_RULES["manifest"]
        assert "format_version" in rules
        assert "required_fields" in rules
        assert "uuid" in rules["required_fields"]
        assert "name" in rules["required_fields"]
        assert "version" in rules["required_fields"]

    def test_block_rules_exist(self):
        """Test block validation rules."""
        assert "blocks" in VALIDATION_RULES
        rules = VALIDATION_RULES["blocks"]
        assert "required_fields" in rules
        assert "format_version" in rules["required_fields"]
        assert "minecraft:block" in rules["required_fields"]

    def test_texture_rules_exist(self):
        """Test texture validation rules."""
        assert "textures" in VALIDATION_RULES
        rules = VALIDATION_RULES["textures"]
        assert "format" in rules
        assert rules["format"] == "PNG"
        assert "dimensions" in rules
        assert rules["dimensions"] == "power_of_2"


class TestQAValidatorAgent:
    """Test QAValidatorAgent functionality."""

    def test_singleton_instance(self):
        """Test that QAValidatorAgent uses singleton pattern."""
        agent1 = QAValidatorAgent.get_instance()
        agent2 = QAValidatorAgent.get_instance()
        assert agent1 is agent2

    def test_validation_cache_exists(self):
        """Test that validation cache is initialized."""
        agent = QAValidatorAgent.get_instance()
        assert agent.validation_cache is not None

    def test_validation_categories_defined(self):
        """Test that validation categories are properly defined."""
        agent = QAValidatorAgent.get_instance()
        assert "structural" in agent.validation_categories
        assert "manifest" in agent.validation_categories
        assert "content" in agent.validation_categories
        assert "bedrock_compatibility" in agent.validation_categories


class TestValidationWithMockAddon:
    """Test validation with a mock .mcaddon file."""

    @pytest.fixture
    def mock_mcaddon_path(self):
        """Create a mock .mcaddon file for testing."""
        temp_dir = tempfile.mkdtemp()
        mcaddon_path = Path(temp_dir) / "test_addon.mcaddon"

        # Create a valid ZIP file with basic structure
        with zipfile.ZipFile(mcaddon_path, 'w') as zf:
            # Add behavior pack manifest
            manifest = {
                "format_version": 2,
                "header": {
                    "name": "Test Addon",
                    "description": "Test description",
                    "uuid": "12345678-1234-1234-1234-123456789abc",
                    "version": [1, 0, 0],
                    "min_engine_version": [1, 19, 0]
                },
                "modules": [
                    {
                        "type": "data",
                        "uuid": "87654321-4321-4321-4321-cba987654321",
                        "version": [1, 0, 0]
                    }
                ]
            }
            zf.writestr("behavior_packs/test_bp/manifest.json", json.dumps(manifest))

            # Add a block definition
            block = {
                "format_version": "1.20.10",
                "minecraft:block": {
                    "description": {
                        "identifier": "test:test_block"
                    },
                    "components": {
                        "minecraft:destroy_time": 3.0
                    }
                }
            }
            zf.writestr("behavior_packs/test_bp/blocks/test_block.json", json.dumps(block))

        yield str(mcaddon_path)

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_validate_mcaddon_basic(self, mock_mcaddon_path):
        """Test basic mcaddon validation."""
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mock_mcaddon_path)

        # Check structure
        assert "overall_score" in result
        assert "status" in result
        assert "validations" in result
        assert "recommendations" in result
        assert "stats" in result

        # Check validations
        validations = result["validations"]
        assert "structural" in validations
        assert "manifest" in validations
        assert "content" in validations
        assert "bedrock_compatibility" in validations

        # Each validation should have checks, passed, status
        for category, validation in validations.items():
            assert "checks" in validation
            assert "passed" in validation
            assert "status" in validation
            assert validation["checks"] >= validation["passed"]

    def test_validate_manifest_success(self, mock_mcaddon_path):
        """Test that valid manifest passes validation."""
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mock_mcaddon_path)

        manifest_validation = result["validations"]["manifest"]
        assert manifest_validation["passed"] > 0
        # Should have minimal errors for valid manifest
        assert len(manifest_validation.get("errors", [])) == 0

    def test_overall_score_range(self, mock_mcaddon_path):
        """Test that overall score is in valid range."""
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mock_mcaddon_path)

        assert 0 <= result["overall_score"] <= 100

    def test_status_is_valid(self, mock_mcaddon_path):
        """Test that status is one of valid values."""
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mock_mcaddon_path)

        assert result["status"] in ["pass", "partial", "fail", "unknown", "error"]

    def test_validation_cache_works(self, mock_mcaddon_path):
        """Test that validation caching works."""
        agent = QAValidatorAgent.get_instance()

        # First validation
        result1 = agent.validate_mcaddon(mock_mcaddon_path)

        # Second validation should use cache
        result2 = agent.validate_mcaddon(mock_mcaddon_path)

        # Results should be identical
        assert result1["overall_score"] == result2["overall_score"]

    def test_validate_conversion_quality_tool(self, mock_mcaddon_path):
        """Test validate_conversion_quality tool."""
        agent = QAValidatorAgent.get_instance()
        result_json = agent.validate_conversion_quality(
            json.dumps({"mcaddon_path": mock_mcaddon_path})
        )
        result = json.loads(result_json)

        assert "success" in result
        assert "overall_score" in result

    def test_validate_mcaddon_tool(self, mock_mcaddon_path):
        """Test validate_mcaddon tool."""
        result_json = QAValidatorAgent.validate_mcaddon_tool(mock_mcaddon_path)
        result = json.loads(result_json)

        assert "success" in result
        assert "overall_score" in result
        assert "validations" in result

    def test_generate_qa_report_tool(self, mock_mcaddon_path):
        """Test generate_qa_report tool."""
        result_json = QAValidatorAgent.generate_qa_report_tool(
            json.dumps({"mcaddon_path": mock_mcaddon_path})
        )
        result = json.loads(result_json)

        assert "success" in result
        assert "report_id" in result
        assert "overall_quality_score" in result


class TestInvalidAddons:
    """Test validation with invalid addon files."""

    def test_nonexistent_file(self):
        """Test validation with nonexistent file."""
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon("/nonexistent/file.mcaddon")

        assert result["status"] == "fail" or result["status"] == "error"
        assert len(result.get("issues", [])) > 0

    def test_invalid_zip_file(self, tmp_path):
        """Test validation with invalid ZIP file."""
        # Create a file that's not a valid ZIP
        invalid_file = tmp_path / "invalid.mcaddon"
        invalid_file.write_text("This is not a ZIP file")

        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(str(invalid_file))

        assert result["status"] == "fail" or result["status"] == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
