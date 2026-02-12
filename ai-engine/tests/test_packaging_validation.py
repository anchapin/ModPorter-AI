"""
Comprehensive tests for packaging validation and structure (Issue #325)

Tests:
- Correct folder structure (behavior_packs/, resource_packs/)
- Manifest validation with JSON schemas
- UUID uniqueness and format
- Error handling and rollback
- .mcaddon internal structure
- Multiple blocks in single package
"""

import pytest
import json
import tempfile
import zipfile
from pathlib import Path
import uuid

from agents.packaging_validator import (
    PackagingValidator,
    ValidationResult,
    ValidationSeverity,
    ValidationIssue
)
from agents.packaging_agent import PackagingAgent
from agents.bedrock_manifest_generator import BedrockManifestGenerator


class TestBedrockFolderStructure:
    """Test correct Bedrock folder structure (behavior_packs/ and resource_packs/)."""

    def setup_method(self):
        self.validator = PackagingValidator()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        # Clean up temp files
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_test_mcaddon(
        self,
        output_path: Path,
        include_behavior: bool = True,
        include_resource: bool = True,
        use_plural: bool = True,
        include_blocks: bool = False
    ) -> None:
        """Helper to create test .mcaddon files."""
        pack_type = "behavior_packs" if use_plural else "behavior_pack"
        res_type = "resource_packs" if use_plural else "resource_pack"

        with zipfile.ZipFile(output_path, 'w') as zipf:
            if include_behavior:
                bp_uuid = str(uuid.uuid4())
                manifest = {
                    "format_version": 2,
                    "header": {
                        "name": "Test Behavior Pack",
                        "description": "Test pack for validation",
                        "uuid": bp_uuid,
                        "version": [1, 0, 0],
                        "min_engine_version": [1, 19, 0]
                    },
                    "modules": [{
                        "type": "data",
                        "uuid": str(uuid.uuid4()),
                        "version": [1, 0, 0]
                    }]
                }

                manifest_path = f"{pack_type}/test_bp/manifest.json"
                zipf.writestr(manifest_path, json.dumps(manifest))

                # Add blocks if requested
                if include_blocks:
                    block1 = {
                        "format_version": "1.20.0",
                        "minecraft:block": {
                            "description": {
                                "identifier": "testmod:copper_block"
                            },
                            "components": {
                                "minecraft:destroy_time": 2.0,
                                "minecraft:explosion_resistance": 3.0
                            }
                        }
                    }

                    block2 = {
                        "format_version": "1.20.0",
                        "minecraft:block": {
                            "description": {
                                "identifier": "testmod:tin_block"
                            },
                            "components": {
                                "minecraft:destroy_time": 2.5,
                                "minecraft:explosion_resistance": 3.5
                            }
                        }
                    }

                    zipf.writestr(f"{pack_type}/test_bp/blocks/copper_block.json", json.dumps(block1))
                    zipf.writestr(f"{pack_type}/test_bp/blocks/tin_block.json", json.dumps(block2))

            if include_resource:
                rp_uuid = str(uuid.uuid4())
                manifest = {
                    "format_version": 2,
                    "header": {
                        "name": "Test Resource Pack",
                        "description": "Test resource pack",
                        "uuid": rp_uuid,
                        "version": [1, 0, 0]
                    },
                    "modules": [{
                        "type": "resources",
                        "uuid": str(uuid.uuid4()),
                        "version": [1, 0, 0]
                    }]
                }

                manifest_path = f"{res_type}/test_rp/manifest.json"
                zipf.writestr(manifest_path, json.dumps(manifest))

    def test_correct_plural_folder_structure(self):
        """Test that behavior_packs/ and resource_packs/ (plural) are detected correctly."""
        mcaddon_path = self.temp_dir / "test.mcaddon"
        self.create_test_mcaddon(mcaddon_path, use_plural=True)

        result = self.validator.validate_mcaddon(mcaddon_path)

        assert result.is_valid
        assert len(result.file_structure['behavior_packs']) == 1
        assert len(result.file_structure['resource_packs']) == 1
        assert len(result.get_issues_by_severity(ValidationSeverity.ERROR)) == 0

    def test_incorrect_singular_folder_structure(self):
        """Test that behavior_pack/ and resource_pack/ (singular) are flagged as errors."""
        mcaddon_path = self.temp_dir / "test.mcaddon"
        self.create_test_mcaddon(mcaddon_path, use_plural=False)

        result = self.validator.validate_mcaddon(mcaddon_path)

        # Should have errors about incorrect structure
        errors = result.get_issues_by_severity(ValidationSeverity.ERROR)
        assert len(errors) > 0
        assert any("singular" in error.message.lower() for error in errors)

    def test_missing_behavior_packs(self):
        """Test validation when behavior_packs/ is missing."""
        mcaddon_path = self.temp_dir / "test.mcaddon"
        self.create_test_mcaddon(mcaddon_path, include_behavior=False)

        result = self.validator.validate_mcaddon(mcaddon_path)

        # Should still be valid if resource pack exists
        assert len(result.file_structure['behavior_packs']) == 0
        assert len(result.file_structure['resource_packs']) == 1

    def test_missing_all_packs(self):
        """Test validation when both pack types are missing."""
        mcaddon_path = self.temp_dir / "test_empty.mcaddon"

        with zipfile.ZipFile(mcaddon_path, 'w') as zipf:
            zipf.writestr("readme.txt", "Empty package")

        result = self.validator.validate_mcaddon(mcaddon_path)

        assert not result.is_valid
        assert any("behavior_packs" in issue.message.lower() or "resource_packs" in issue.message.lower()
                  for issue in result.issues)


class TestManifestValidation:
    """Test manifest.json validation with JSON schemas."""

    def setup_method(self):
        self.validator = PackagingValidator()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def create_mcaddon_with_manifest(self, manifest_data: dict) -> Path:
        """Helper to create .mcaddon with custom manifest."""
        mcaddon_path = self.temp_dir / "test.mcaddon"

        with zipfile.ZipFile(mcaddon_path, 'w') as zipf:
            zipf.writestr("behavior_packs/test_bp/manifest.json", json.dumps(manifest_data))

        return mcaddon_path

    def test_valid_manifest_passes_schema_validation(self):
        """Test that a valid manifest passes schema validation."""
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Valid Pack",
                "description": "A valid test pack",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0],
                "min_engine_version": [1, 19, 0]
            },
            "modules": [{
                "type": "data",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            }]
        }

        mcaddon_path = self.create_mcaddon_with_manifest(manifest)
        result = self.validator.validate_mcaddon(mcaddon_path)

        manifest_errors = [i for i in result.issues if i.category == "manifest" and
                          i.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]]
        assert len(manifest_errors) == 0

    def test_invalid_uuid_fails_validation(self):
        """Test that invalid UUID format is detected."""
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Invalid UUID Pack",
                "description": "Pack with bad UUID",
                "uuid": "not-a-valid-uuid",
                "version": [1, 0, 0]
            },
            "modules": [{
                "type": "data",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            }]
        }

        mcaddon_path = self.create_mcaddon_with_manifest(manifest)
        result = self.validator.validate_mcaddon(mcaddon_path)

        uuid_errors = [i for i in result.issues if "uuid" in i.message.lower()]
        assert len(uuid_errors) > 0

    def test_missing_required_fields_detected(self):
        """Test that missing required fields are detected."""
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Incomplete Pack"
                # Missing description, uuid, version
            },
            "modules": []  # Empty modules
        }

        mcaddon_path = self.create_mcaddon_with_manifest(manifest)
        result = self.validator.validate_mcaddon(mcaddon_path)

        # Should have errors about missing fields
        assert not result.is_valid
        critical_issues = result.get_issues_by_severity(ValidationSeverity.CRITICAL)
        assert len(critical_issues) > 0

    def test_duplicate_uuids_detected(self):
        """Test that duplicate UUIDs are detected."""
        test_uuid = str(uuid.uuid4())

        manifest = {
            "format_version": 2,
            "header": {
                "name": "Duplicate UUID Pack",
                "description": "Pack with duplicate UUIDs",
                "uuid": test_uuid,
                "version": [1, 0, 0]
            },
            "modules": [{
                "type": "data",
                "uuid": test_uuid,  # Same as header UUID
                "version": [1, 0, 0]
            }]
        }

        mcaddon_path = self.create_mcaddon_with_manifest(manifest)
        result = self.validator.validate_mcaddon(mcaddon_path)

        dup_errors = [i for i in result.issues if "duplicate" in i.message.lower()]
        assert len(dup_errors) > 0

    def test_version_format_validation(self):
        """Test that version format [major, minor, patch] is validated."""
        # Valid version
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Valid Version",
                "description": "Test",
                "uuid": str(uuid.uuid4()),
                "version": [2, 5, 1]
            },
            "modules": [{
                "type": "data",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            }]
        }

        mcaddon_path = self.create_mcaddon_with_manifest(manifest)
        result = self.validator.validate_mcaddon(mcaddon_path)

        # Should not have version errors
        version_errors = [i for i in result.issues if "version" in i.message.lower()]
        assert len(version_errors) == 0


class TestMultipleBlocksPackaging:
    """Test packaging multiple blocks in a single .mcaddon."""

    def setup_method(self):
        self.validator = PackagingValidator()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_multiple_blocks_in_single_package(self):
        """Test that multiple blocks can be packaged together."""
        mcaddon_path = self.temp_dir / "multi_block.mcaddon"

        blocks = {
            "copper_block": {
                "format_version": "1.20.0",
                "minecraft:block": {
                    "description": {"identifier": "testmod:copper_block"},
                    "components": {
                        "minecraft:destroy_time": 2.0,
                        "minecraft:explosion_resistance": 3.0
                    }
                }
            },
            "tin_block": {
                "format_version": "1.20.0",
                "minecraft:block": {
                    "description": {"identifier": "testmod:tin_block"},
                    "components": {
                        "minecraft:destroy_time": 2.5,
                        "minecraft:explosion_resistance": 3.5
                    }
                }
            },
            "lead_block": {
                "format_version": "1.20.0",
                "minecraft:block": {
                    "description": {"identifier": "testmod:lead_block"},
                    "components": {
                        "minecraft:destroy_time": 3.0,
                        "minecraft:explosion_resistance": 4.0
                    }
                }
            }
        }

        with zipfile.ZipFile(mcaddon_path, 'w') as zipf:
            # Add manifest
            bp_uuid = str(uuid.uuid4())
            manifest = {
                "format_version": 2,
                "header": {
                    "name": "Multi Block Pack",
                    "description": "Pack with multiple blocks",
                    "uuid": bp_uuid,
                    "version": [1, 0, 0]
                },
                "modules": [{
                    "type": "data",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                }]
            }
            zipf.writestr("behavior_packs/multi_bp/manifest.json", json.dumps(manifest))

            # Add all blocks
            for block_name, block_data in blocks.items():
                zipf.writestr(
                    f"behavior_packs/multi_bp/blocks/{block_name}.json",
                    json.dumps(block_data)
                )

        result = self.validator.validate_mcaddon(mcaddon_path)

        # Should be valid
        assert result.is_valid
        assert result.stats['total_files'] == 4  # 1 manifest + 3 blocks


class TestErrorHandlingAndRollback:
    """Test error handling and rollback mechanisms."""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_invalid_zip_file_handling(self):
        """Test handling of invalid ZIP files."""
        validator = PackagingValidator()

        # Create invalid ZIP file
        invalid_path = self.temp_dir / "invalid.mcaddon"
        with open(invalid_path, 'wb') as f:
            f.write(b"This is not a ZIP file")

        result = validator.validate_mcaddon(invalid_path)

        assert not result.is_valid
        critical_issues = result.get_issues_by_severity(ValidationSeverity.CRITICAL)
        assert len(critical_issues) > 0

    def test_malformed_json_handling(self):
        """Test handling of malformed JSON files."""
        validator = PackagingValidator()
        mcaddon_path = self.temp_dir / "malformed.mcaddon"

        with zipfile.ZipFile(mcaddon_path, 'w') as zipf:
            zipf.writestr("behavior_packs/test_bp/manifest.json", "{invalid json content")

        result = validator.validate_mcaddon(mcaddon_path)

        # Should detect JSON error
        json_errors = [i for i in result.issues if "json" in i.message.lower()]
        assert len(json_errors) > 0

    def test_clean_temp_files_detection(self):
        """Test detection of temporary/cleanup files."""
        validator = PackagingValidator()
        mcaddon_path = self.temp_dir / "with_temp.mcaddon"

        with zipfile.ZipFile(mcaddon_path, 'w') as zipf:
            # Add valid manifest
            manifest = {
                "format_version": 2,
                "header": {
                    "name": "Test",
                    "description": "Test",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                },
                "modules": [{
                    "type": "data",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                }]
            }
            zipf.writestr("behavior_packs/test_bp/manifest.json", json.dumps(manifest))

            # Add temporary files
            zipf.writestr("behavior_packs/test_bp/.DS_Store", "binary")
            zipf.writestr("behavior_packs/test_bp/temp~", "temp")

        result = validator.validate_mcaddon(mcaddon_path)

        # Should warn about temporary files
        cleanup_issues = [i for i in result.issues if i.category == "cleanup"]
        assert len(cleanup_issues) > 0


class TestPackagingAgentIntegration:
    """Test PackagingAgent with correct folder structure."""

    def setup_method(self):
        self.agent = PackagingAgent.get_instance()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_build_mcaddon_uses_correct_structure(self):
        """Test that build_mcaddon_mvp creates correct behavior_packs/ structure."""
        # Create temp directory with behavior_pack and resource_pack
        temp_input = self.temp_dir / "input"
        temp_input.mkdir()

        behavior_dir = temp_input / "behavior_pack"
        resource_dir = temp_input / "resource_pack"
        behavior_dir.mkdir()
        resource_dir.mkdir()

        # Create manifests
        bp_manifest = {
            "format_version": 2,
            "header": {
                "name": "Test BP",
                "description": "Test",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            },
            "modules": [{
                "type": "data",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            }]
        }

        with open(behavior_dir / "manifest.json", 'w') as f:
            json.dump(bp_manifest, f)

        rp_manifest = {
            "format_version": 2,
            "header": {
                "name": "Test RP",
                "description": "Test",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            },
            "modules": [{
                "type": "resources",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            }]
        }

        with open(resource_dir / "manifest.json", 'w') as f:
            json.dump(rp_manifest, f)

        # Build .mcaddon
        output_path = self.temp_dir / "output.mcaddon"
        result = self.agent.build_mcaddon_mvp(str(temp_input), str(output_path), "test_mod")

        assert result['success']

        # Validate the created file
        validator = PackagingValidator()
        validation_result = validator.validate_mcaddon(Path(output_path))

        # Check for correct structure
        assert validation_result.is_valid
        assert len(validation_result.file_structure['behavior_packs']) > 0
        assert len(validation_result.file_structure['resource_packs']) > 0

        # Verify no errors about singular form
        structure_errors = [i for i in validation_result.issues
                           if i.category == "structure" and "singular" in i.message.lower()]
        assert len(structure_errors) == 0


class TestValidationReporting:
    """Test validation report generation."""

    def setup_method(self):
        self.validator = PackagingValidator()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_report_generation(self):
        """Test that validation reports are generated correctly."""
        mcaddon_path = self.temp_dir / "test.mcaddon"

        # Create minimal valid package
        with zipfile.ZipFile(mcaddon_path, 'w') as zipf:
            manifest = {
                "format_version": 2,
                "header": {
                    "name": "Test Pack",
                    "description": "Test pack for reporting",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                },
                "modules": [{
                    "type": "data",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                }]
            }
            zipf.writestr("behavior_packs/test_bp/manifest.json", json.dumps(manifest))

        result = self.validator.validate_mcaddon(mcaddon_path)
        report = self.validator.generate_report(result)

        # Check report content
        assert "Overall Status:" in report
        assert "Score:" in report
        assert "Package Statistics:" in report
        assert "Compatibility:" in report

    def test_report_includes_all_issues(self):
        """Test that report includes all validation issues."""
        mcaddon_path = self.temp_dir / "test.mcaddon"

        # Create package with issues
        with zipfile.ZipFile(mcaddon_path, 'w') as zipf:
            # Invalid manifest (missing description)
            manifest = {
                "format_version": 2,
                "header": {
                    "name": "Bad Pack",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                },
                "modules": []
            }
            zipf.writestr("behavior_packs/test_bp/manifest.json", json.dumps(manifest))

        result = self.validator.validate_mcaddon(mcaddon_path)
        report = self.validator.generate_report(result)

        # Should mention the errors
        assert "ERROR" in report or "CRITICAL" in report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
