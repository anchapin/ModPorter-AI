"""
Standalone validation test that doesn't import through agents/__init__.py
Tests for Issue #325: Validate and Fix Packaging Agent Structure
"""

import pytest
import json
import tempfile
import zipfile
from pathlib import Path
import uuid
import sys

# Import modules directly to avoid pydub import issue
sys.path.insert(0, str(Path(__file__).parent.parent))
import importlib.util

# Load packaging_validator directly
spec = importlib.util.spec_from_file_location(
    'packaging_validator',
    Path(__file__).parent.parent / 'agents' / 'packaging_validator.py'
)
validator_module = importlib.util.module_from_spec(spec)
sys.modules['packaging_validator'] = validator_module
spec.loader.exec_module(validator_module)

PackagingValidator = validator_module.PackagingValidator
ValidationSeverity = validator_module.ValidationSeverity


class TestBedrockFolderStructure:
    """Test correct Bedrock folder structure (behavior_packs/ and resource_packs/)."""

    def setup_method(self):
        self.validator = PackagingValidator()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
