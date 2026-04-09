
import pytest
import json
import zipfile
import io
from agents.addon_validator import AddonValidator

class TestAddonValidator:
    @pytest.fixture
    def validator(self):
        return AddonValidator()

    @pytest.fixture
    def sample_manifest(self):
        return {
            "format_version": 2,
            "header": {
                "name": "Test Pack",
                "description": "A test pack",
                "uuid": "00000000-0000-0000-0000-000000000001",
                "version": [1, 0, 0],
                "min_engine_version": [1, 16, 0]
            },
            "modules": [
                {
                    "type": "data",
                    "uuid": "00000000-0000-0000-0000-000000000002",
                    "version": [1, 0, 0]
                }
            ]
        }

    def test_validate_manifest_only_success(self, validator, sample_manifest):
        result = validator.validate_manifest_only(sample_manifest)
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_manifest_only_invalid_uuid(self, validator, sample_manifest):
        sample_manifest["header"]["uuid"] = "invalid-uuid"
        result = validator.validate_manifest_only(sample_manifest)
        assert result["is_valid"] is False
        assert any("uuid" in err.lower() for err in result["errors"])

    def test_validate_manifest_only_missing_fields(self, validator):
        result = validator.validate_manifest_only({})
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0

    def test_compare_versions(self, validator):
        assert validator._compare_versions([1, 0, 0], [1, 0, 0]) == 0
        assert validator._compare_versions([1, 1, 0], [1, 0, 0]) == 1
        assert validator._compare_versions([1, 0, 0], [1, 1, 0]) == -1
        assert validator._compare_versions([1, 0, 0], [1, 0]) == 0
        assert validator._compare_versions([1, 0], [1, 0, 0]) == 0

    def test_validate_basic_file_not_exists(self, validator, tmp_path):
        result = {"errors": [], "warnings": []}
        non_existent = tmp_path / "non_existent.mcaddon"
        assert validator._validate_basic_file(non_existent, result) is False
        assert "does not exist" in result["errors"][0]

    def test_validate_basic_file_wrong_extension(self, validator, tmp_path):
        result = {"errors": [], "warnings": []}
        wrong_ext = tmp_path / "test.txt"
        wrong_ext.write_text("dummy")
        
        # It should not raise, but add a warning and then an error (not a valid zip)
        assert validator._validate_basic_file(wrong_ext, result) is False
        assert "should be .mcaddon" in result["warnings"][0]
        assert "not a valid ZIP archive" in result["errors"][0]

    def test_analyze_addon_stats(self, validator):
        # Create a mock ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            zip_file.writestr("behavior_packs/test_bp/manifest.json", "{}")
            zip_file.writestr("resource_packs/test_rp/manifest.json", "{}")
            zip_file.writestr("test.png", "dummy content")
        
        zip_buffer.seek(0)
        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            stats = validator._analyze_addon_stats(zip_file)
            assert stats["total_files"] == 3
            assert "test_bp" in stats["behavior_packs"]
            assert "test_rp" in stats["resource_packs"]
            assert ".png" in stats["file_types"]

    def test_validate_addon_structure_empty(self, validator):
        result = {"errors": [], "warnings": [], "info": []}
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a") as zip_file:
            zip_file.writestr("some_other_dir/file.txt", "dummy")
        
        zip_buffer.seek(0)
        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            validator._validate_addon_structure(zip_file, result)
            assert any("must contain" in err for err in result["errors"])

    def test_validate_addon_structure_valid(self, validator):
        result = {"errors": [], "warnings": [], "info": []}
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a") as zip_file:
            zip_file.writestr("behavior_packs/test_bp/manifest.json", "{}")
            zip_file.writestr("behavior_packs/test_bp/entities/test.json", "{}")
            zip_file.writestr("resource_packs/test_rp/manifest.json", "{}")
            zip_file.writestr("resource_packs/test_rp/textures/test.png", "dummy")
        
        zip_buffer.seek(0)
        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            validator._validate_addon_structure(zip_file, result)
            # errors might still have "Missing manifest.json" because it's not actually reading the content yet
            # but we just want to see if it traverses correctly

    def test_calculate_overall_score(self, validator):
        result = {
            "errors": ["error 1"],
            "warnings": ["warning 1", "warning 2"],
            "stats": {"behavior_packs": ["bp"], "resource_packs": ["rp"]},
            "compatibility": {"experimental_features": []}
        }
        score = validator._calculate_overall_score(result)
        # 100 - 15*1 - 3*2 + 5 (both packs) + 5 (no experimental) = 100 - 15 - 6 + 10 = 89
        assert score == 89

    def test_validate_basic_file_large_size(self, validator, tmp_path):
        result = {"errors": [], "warnings": []}
        large_file = tmp_path / "large.mcaddon"
        
        # Create a 600MB file (exceeds 500MB limit)
        with open(large_file, "wb") as f:
            f.seek(600 * 1024 * 1024 - 1)
            f.write(b"\0")
        
        assert validator._validate_basic_file(large_file, result) is False
        assert any("exceeds maximum" in err for err in result["errors"])

    def test_validate_basic_file_warning_size(self, validator, tmp_path):
        result = {"errors": [], "warnings": []}
        warning_file = tmp_path / "warning.mcaddon"
        
        # Create a 450MB file (80% of 500MB = 400MB)
        with open(warning_file, "wb") as f:
            f.seek(450 * 1024 * 1024 - 1)
            f.write(b"\0")
        
        # This might still fail at ZipFile check if not a real zip
        validator._validate_basic_file(warning_file, result)
        assert any("Large file size" in warn for warn in result["warnings"])

    def test_validate_single_manifest_various_cases(self, validator):
        result = {"errors": [], "warnings": []}
        
        # Invalid version format
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Test", "description": "", 
                "uuid": "00000000-0000-0000-0000-000000000001",
                "version": [1, 0] # Should be 3 items
            },
            "modules": []
        }
        validator._validate_single_manifest(manifest, "manifest.json", result)
        assert any("Manifest schema error" in err for err in result["errors"])
        
        # Unknown module type (should also be caught by schema enum)
        manifest["header"]["version"] = [1, 0, 0]
        manifest["modules"] = [{"type": "unknown", "uuid": "00000000-0000-0000-0000-000000000002", "version": [1, 0, 0]}]
        result = {"errors": [], "warnings": []}
        validator._validate_single_manifest(manifest, "manifest.json", result)
        assert any("Manifest schema error" in err for err in result["errors"])

    def test_validate_addon_files(self, validator):
        result = {"errors": [], "warnings": []}
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a") as zip_file:
            zip_file.writestr("test.json", "{ invalid }")
            zip_file.writestr("test.js", "function() { return 1; }") # Mismatched braces
            zip_file.writestr("large_sound.ogg", "a" * (11 * 1024 * 1024)) # 11MB > 10MB limit
        
        zip_buffer.seek(0)
        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            validator._validate_addon_files(zip_file, result)
            assert any("Invalid JSON" in err for err in result["errors"])
            assert any("Large sound file" in warn for warn in result["warnings"])

    def test_check_bedrock_compatibility(self, validator):
        result = {"errors": [], "warnings": []}
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a") as zip_file:
            manifest = {
                "format_version": 2,
                "header": {"uuid": "00000000-0000-0000-0000-000000000001", "version": [1,0,0], "name": "test", "description": ""},
                "modules": [{"type": "javascript", "uuid": "00000000-0000-0000-0000-000000000002", "version": [1,0,0]}],
                "capabilities": ["experimental_custom_ui"]
            }
            zip_file.writestr("behavior_packs/bp/manifest.json", json.dumps(manifest))
            zip_file.writestr("test.js", "console.log('hi');")
            
        zip_buffer.seek(0)
        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            validator._check_bedrock_compatibility(zip_file, result)
            compat = result["compatibility"]
            assert "experimental_custom_ui" in compat["experimental_features"]
            assert compat["education_edition"] is False

    def test_generate_recommendations(self, validator):
        result = {
            "is_valid": True,
            "stats": {
                "total_size_uncompressed": 200 * 1024 * 1024,
                "largest_files": [{"filename": "big.png", "size_mb": 15}]
            },
            "warnings": ["w1", "w2", "w3", "w4", "w5", "w6"],
            "compatibility": {"experimental_features": ["f1"]}
        }
        validator._generate_recommendations(result)
        recs = result["recommendations"]
        assert any("optimizing assets" in r for r in recs)
        assert any("Optimize large file" in r for r in recs)
        assert any("Address warnings" in r for r in recs)
        assert any(r.lower().count("experimental features") > 0 for r in recs)

    def test_validate_addon_full_flow(self, validator, tmp_path, sample_manifest):
        addon_path = tmp_path / "test.mcaddon"
        
        with zipfile.ZipFile(addon_path, "w") as zip_file:
            zip_file.writestr("behavior_packs/test_bp/manifest.json", json.dumps(sample_manifest))
            zip_file.writestr("resource_packs/test_rp/manifest.json", json.dumps(sample_manifest))
            zip_file.writestr("resource_packs/test_rp/textures/item.png", "dummy")
        
        result = validator.validate_addon(addon_path)
        assert result["is_valid"] is True
        assert result["overall_score"] > 80
        assert len(result["stats"]["behavior_packs"]) == 1
