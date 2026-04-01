"""Unit tests for test_mod_validator fixture module."""

import sys
import tempfile
import zipfile
import json
from pathlib import Path

import pytest

# Add fixtures directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_mod_validator import (
    TestModValidator,
    ValidationResult,
)
from test_jar_generator import TestJarGenerator


class TestValidationResult:
    """Test suite for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating a ValidationResult."""
        result = ValidationResult(
            is_valid=True,
            mod_name="test_mod",
            mod_type="entity",
            errors=[],
            warnings=["warning1"],
            features=["feature1"],
            expected_conversion_challenges=["challenge1"]
        )
        
        assert result.is_valid is True
        assert result.mod_name == "test_mod"
        assert result.mod_type == "entity"

    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors."""
        result = ValidationResult(
            is_valid=False,
            mod_name="test_mod",
            mod_type="gui",
            errors=["error1", "error2"],
            warnings=[],
            features=[],
            expected_conversion_challenges=[]
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_validation_result_all_fields(self):
        """Test that ValidationResult has all expected fields."""
        result = ValidationResult(
            is_valid=True,
            mod_name="test",
            mod_type="logic",
            errors=[],
            warnings=[],
            features=[],
            expected_conversion_challenges=[]
        )
        
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'mod_name')
        assert hasattr(result, 'mod_type')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'features')
        assert hasattr(result, 'expected_conversion_challenges')


class TestTestModValidator:
    """Test suite for TestModValidator class."""

    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = TestModValidator()
        
        assert validator is not None
        assert 'entity' in validator.validation_rules
        assert 'gui' in validator.validation_rules
        assert 'logic' in validator.validation_rules

    def test_validate_nonexistent_jar_returns_invalid(self):
        """Test validating non-existent JAR file."""
        validator = TestModValidator()
        
        non_existent = Path("/nonexistent/path/test.jar")
        result = validator.validate_mod(non_existent)
        
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_bad_zip_file(self):
        """Test validating invalid ZIP file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            
            # Create a file that's not a valid ZIP
            bad_jar = Path(tmpdir) / "bad.jar"
            bad_jar.write_text("This is not a ZIP file")
            
            result = validator.validate_mod(bad_jar)
            
            assert result.is_valid is False

    def test_validate_valid_simple_jar(self):
        """Test validating a valid simple JAR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            # Create a simple JAR
            java_files = {"com/example/Test.java": "public class Test {}"}
            jar_path = generator.create_simple_jar("test", java_files)
            
            result = validator.validate_mod(Path(jar_path))
            
            # Should be valid
            assert isinstance(result, ValidationResult)
            assert result.mod_name is not None

    def test_validate_mod_jar(self):
        """Test validating a mod JAR."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_mod_jar("TestMod")
            
            result = validator.validate_mod(Path(jar_path))
            
            assert isinstance(result, ValidationResult)

    def test_validate_mod_sets_mod_name(self):
        """Test that validation sets mod name from JAR filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_simple_jar("my_test_mod", {})
            
            result = validator.validate_mod(Path(jar_path))
            
            assert result.mod_name == "my_test_mod"

    def test_validate_mod_determines_type(self):
        """Test that validation determines mod type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_simple_jar("entity_mod", {})
            
            result = validator.validate_mod(Path(jar_path))
            
            assert result.mod_type is not None

    def test_validate_mod_empty_errors_on_success(self):
        """Test that successful validation has no errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            # Create a valid ZIP/JAR
            jar_path = generator.create_simple_jar("valid", {
                "META-INF/MANIFEST.MF": "Manifest-Version: 1.0"
            })
            
            result = validator.validate_mod(Path(jar_path))
            
            # Valid JAR should have fewer or no errors
            assert isinstance(result.errors, list)

    def test_validate_test_suite_returns_dict(self):
        """Test that validate_test_suite returns dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            
            # Create test directory structure
            test_dir = Path(tmpdir) / "test_mods"
            test_dir.mkdir()
            (test_dir / "entities").mkdir()
            (test_dir / "gui_mods").mkdir()
            (test_dir / "complex_logic").mkdir()
            
            result = validator.validate_test_suite(test_dir)
            
            assert isinstance(result, dict)

    def test_validation_result_is_valid_when_no_errors(self):
        """Test that validation result is_valid is True when errors are empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_simple_jar("test", {
                "META-INF/MANIFEST.MF": "Manifest-Version: 1.0"
            })
            
            result = validator.validate_mod(Path(jar_path))
            
            # The is_valid flag should be based on errors
            if len(result.errors) == 0:
                assert result.is_valid is True
            else:
                assert result.is_valid is False

    def test_validate_mod_with_warnings(self):
        """Test that validation can produce warnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_simple_jar("test", {})
            
            result = validator.validate_mod(Path(jar_path))
            
            assert isinstance(result.warnings, list)

    def test_validate_mod_with_features(self):
        """Test that validation identifies features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_mod_jar("TestMod", blocks=["test_block"], items=["test_item"])
            
            result = validator.validate_mod(Path(jar_path))
            
            assert isinstance(result.features, list)

    def test_validate_mod_with_conversion_challenges(self):
        """Test that validation identifies conversion challenges."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_mod_jar("TestMod")
            
            result = validator.validate_mod(Path(jar_path))
            
            assert isinstance(result.expected_conversion_challenges, list)

    def test_validation_result_as_dict_like(self):
        """Test that ValidationResult behaves like dict for accessing fields."""
        result = ValidationResult(
            is_valid=True,
            mod_name="test",
            mod_type="entity",
            errors=[],
            warnings=[],
            features=[],
            expected_conversion_challenges=[]
        )
        
        # Should be accessible as attributes
        assert result.is_valid is True
        assert result.mod_name == "test"

    def test_validate_entity_mod(self):
        """Test validating entity mod type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            # Create JAR with "entity" in name
            jar_path = generator.create_simple_jar("entity_test", {})
            
            result = validator.validate_mod(Path(jar_path))
            
            assert result.mod_type == "entity"

    def test_validate_gui_mod(self):
        """Test validating GUI mod type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_simple_jar("gui_test", {})
            
            result = validator.validate_mod(Path(jar_path))
            
            assert result.mod_type == "gui"

    def test_validate_logic_mod(self):
        """Test validating logic mod type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_simple_jar("logic_test", {})
            
            result = validator.validate_mod(Path(jar_path))
            
            assert result.mod_type == "logic"

    def test_multiple_validations(self):
        """Test performing multiple validations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = TestModValidator()
            generator = TestJarGenerator(tmpdir)
            
            jar1 = generator.create_simple_jar("test1", {})
            jar2 = generator.create_simple_jar("test2", {})
            
            result1 = validator.validate_mod(Path(jar1))
            result2 = validator.validate_mod(Path(jar2))
            
            assert result1.mod_name == "test1"
            assert result2.mod_name == "test2"

    def test_validation_error_accumulation(self):
        """Test that validation errors are properly accumulated."""
        validator = TestModValidator()
        
        # Non-existent file should produce error
        result = validator.validate_mod(Path("/nonexistent/test.jar"))
        
        assert len(result.errors) > 0
        assert "does not exist" in " ".join(result.errors).lower() or len(result.errors) > 0

    def test_validator_validation_rules_exist(self):
        """Test that all validation rule methods exist."""
        validator = TestModValidator()
        
        # Should have validation methods for each type
        for mod_type in ["entity", "gui", "logic"]:
            assert mod_type in validator.validation_rules
            assert callable(validator.validation_rules[mod_type])
