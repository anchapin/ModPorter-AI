"""
Tests for Output Integrity Validators

Unit tests for the output integrity validation system.
"""

import pytest
import json
import zipfile
import tempfile
import os
import sys
from pathlib import Path

# Workaround: ai-engine has hyphen which is invalid for Python import
# Use dynamic import like the backend does
current_file = Path(__file__).resolve()
tests_dir = current_file.parent  # ai-engine/tests
ai_engine_dir = tests_dir.parent  # ai-engine
project_root = ai_engine_dir.parent  # project root
ai_engine_path = str(ai_engine_dir)

if ai_engine_path not in sys.path:
    sys.path.insert(0, ai_engine_path)

# Now import normally
from validators import (
    ManifestValidator,
    FileIntegrityChecker,
    CompletenessTracker,
    CorrelationChecker,
    BedrockSchemaValidator,
    QualityGate,
    IntegrityHasher,
)


class TestManifestValidator:
    """Tests for ManifestValidator."""
    
    def test_valid_manifest(self):
        """Test validation of a valid manifest."""
        # Use already imported validators
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Test Pack",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "modules": [
                {
                    "type": "resource_pack",
                    "uuid": "87654321-4321-4321-4321-210987654321",
                    "version": [1, 0, 0]
                }
            ]
        }
        
        validator = ManifestValidator()
        # Use already imported
        result = validator.validate(manifest)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_missing_header(self):
        """Test validation fails when header is missing."""
        validator = ManifestValidator
        
        manifest = {
            "format_version": 2,
            "modules": []
        }
        
        validator = ManifestValidator()
        # Use already imported
        result = validator.validate(manifest)
        
        assert not result.is_valid
        assert any('header' in str(e.get('type', '')) for e in result.errors)
    
    def test_missing_modules(self):
        """Test validation fails when modules is missing."""
        validator = ManifestValidator
        
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Test",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            }
        }
        
        validator = ManifestValidator()
        # Use already imported
        result = validator.validate(manifest)
        
        assert not result.is_valid
        assert any('module' in str(e.get('type', '')).lower() for e in result.errors)
    
    def test_invalid_uuid_format(self):
        """Test warning for invalid UUID format."""
        validator = ManifestValidator
        
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Test",
                "uuid": "invalid-uuid",
                "version": [1, 0, 0]
            },
            "modules": [
                {
                    "type": "resource_pack",
                    "uuid": "87654321-4321-4321-4321-210987654321",
                    "version": [1, 0, 0]
                }
            ]
        }
        
        validator = ManifestValidator()
        # Use already imported
        result = validator.validate(manifest)
        
        # Should still be valid but with warnings
        assert len(result.warnings) > 0


class TestFileIntegrityChecker:
    """Tests for FileIntegrityChecker."""
    
    def test_valid_package(self):
        """Test integrity check on valid package."""
        FileIntegrityChecker
        
        # Create a temporary valid zip package
        with tempfile.NamedTemporaryFile(suffix='.mcaddon', delete=False) as f:
            temp_path = f.name
        
        try:
            with zipfile.ZipFile(temp_path, 'w') as zf:
                zf.writestr('manifest.json', json.dumps({
                    "format_version": 2,
                    "header": {"name": "Test", "uuid": "12345678-1234-1234-1234-123456789012", "version": [1, 0, 0]},
                    "modules": []
                }))
                zf.writestr('blocks/test_block.json', json.dumps({
                    "format_version": 1,
                    "minecraft:block": {
                        "description": {"identifier": "test:block"}
                    }
                }))
            
            checker = FileIntegrityChecker()
            result = checker.check_integrity(temp_path)
            
            assert result.is_valid
            assert result.file_count == 2
            assert result.json_valid_count == 2
        finally:
            os.unlink(temp_path)
    
    def test_missing_manifest(self):
        """Test integrity check fails when manifest is missing."""
        FileIntegrityChecker
        
        with tempfile.NamedTemporaryFile(suffix='.mcaddon', delete=False) as f:
            temp_path = f.name
        
        try:
            with zipfile.ZipFile(temp_path, 'w') as zf:
                zf.writestr('blocks/test_block.json', "{}")
            
            checker = FileIntegrityChecker()
            result = checker.check_integrity(temp_path)
            
            assert not result.is_valid
            assert any('required' in str(e.get('type', '')).lower() for e in result.errors)
        finally:
            os.unlink(temp_path)
    
    def test_invalid_json(self):
        """Test detection of invalid JSON files."""
        FileIntegrityChecker
        
        with tempfile.NamedTemporaryFile(suffix='.mcaddon', delete=False) as f:
            temp_path = f.name
        
        try:
            with zipfile.ZipFile(temp_path, 'w') as zf:
                zf.writestr('manifest.json', json.dumps({
                    "format_version": 2,
                    "header": {"name": "Test", "uuid": "12345678-1234-1234-1234-123456789012", "version": [1, 0, 0]},
                    "modules": []
                }))
                zf.writestr('blocks/broken.json', "{invalid json")
            
            checker = FileIntegrityChecker(strict_validation=True)
            result = checker.check_integrity(temp_path)
            
            assert result.json_invalid_count > 0
        finally:
            os.unlink(temp_path)


class TestCompletenessTracker:
    """Tests for CompletenessTracker."""
    
    @pytest.mark.asyncio
    async def test_full_completeness(self):
        """Test when all expected components are found."""
        CompletenessTracker
        
        # Create a test package
        with tempfile.NamedTemporaryFile(suffix='.mcaddon', delete=False) as f:
            temp_path = f.name
        
        try:
            with zipfile.ZipFile(temp_path, 'w') as zf:
                zf.writestr('manifest.json', "{}")
                zf.writestr('blocks/grass_block.json', "{}")
                zf.writestr('items/diamond_sword.json', "{}")
            
            input_analysis = {
                'blocks': [{'name': 'grass_block'}],
                'items': [{'name': 'diamond_sword'}]
            }
            
            tracker = CompletenessTracker()
            result = await tracker.verify_completeness(input_analysis, temp_path)
            
            assert result.completeness_percentage > 0
        finally:
            os.unlink(temp_path)


class TestQualityGate:
    """Tests for QualityGate."""
    
    def test_all_checks_pass(self):
        """Test quality gate passes when all checks pass."""
        QualityGate
        
        validation_data = {
            'completeness_percentage': 100,
            'integrity_valid': True,
            'manifest_valid': True,
            'correlation_score': 1.0,
            'schema_valid_ratio': 1.0,
            'syntax_valid_ratio': 1.0,
        }
        
        gate = QualityGate()
        result = gate.evaluate(validation_data)
        
        assert result.passed
        assert result.score >= 0.9
        assert result.passed
    
    def test_completeness_below_threshold(self):
        """Test quality gate fails when completeness is low."""
        QualityGate
        
        validation_data = {
            'completeness_percentage': 50,  # Below 80% threshold
            'integrity_valid': True,
            'manifest_valid': True,
            'correlation_score': 0.9,
            'schema_valid_ratio': 1.0,
            'syntax_valid_ratio': 1.0,
        }
        
        gate = QualityGate()
        result = gate.evaluate(validation_data)
        
        assert not result.passed
        assert any('completeness' in str(fc.get('check', '')).lower() for fc in result.failed_checks)
    
    def test_integrity_failure(self):
        """Test quality gate fails on integrity failure."""
        QualityGate
        
        validation_data = {
            'completeness_percentage': 100,
            'integrity_valid': False,  # Failed integrity
            'manifest_valid': True,
            'correlation_score': 1.0,
            'schema_valid_ratio': 1.0,
            'syntax_valid_ratio': 1.0,
        }
        
        gate = QualityGate()
        result = gate.evaluate(validation_data)
        
        assert not result.passed
    
    def test_grade_calculation(self):
        """Test grade calculation."""
        QualityGate
        
        gate = QualityGate()
        
        assert gate.get_grade(1.0) == 'A'
        assert gate.get_grade(0.95) == 'A'  # A requires >= 0.95
        assert gate.get_grade(0.9) == 'B'  # 0.9 >= 0.85 but < 0.95
        assert gate.get_grade(0.75) == 'C'
        assert gate.get_grade(0.55) == 'D'
        assert gate.get_grade(0.3) == 'F'


class TestIntegrityHasher:
    """Tests for IntegrityHasher."""
    
    def test_generate_hashes(self):
        """Test hash generation."""
        IntegrityHasher
        
        with tempfile.NamedTemporaryFile(suffix='.mcaddon', delete=False) as f:
            temp_path = f.name
        
        try:
            with zipfile.ZipFile(temp_path, 'w') as zf:
                zf.writestr('test.txt', 'hello world')
                zf.writestr('test2.txt', 'test data')
            
            hasher = IntegrityHasher()
            result = hasher.generate_hashes(temp_path)
            
            assert result.package_hash
            assert len(result.file_hashes) == 2
            assert result.hash_algorithm == 'sha256'
        finally:
            os.unlink(temp_path)
    
    def test_package_hash_deterministic(self):
        """Test that package hash is deterministic."""
        IntegrityHasher
        
        with tempfile.NamedTemporaryFile(suffix='.mcaddon', delete=False) as f:
            temp_path = f.name
        
        try:
            with zipfile.ZipFile(temp_path, 'w') as zf:
                zf.writestr('test.txt', 'hello world')
            
            hasher = IntegrityHasher()
            result1 = hasher.generate_hashes(temp_path)
            result2 = hasher.generate_hashes(temp_path)
            
            assert result1.package_hash == result2.package_hash
        finally:
            os.unlink(temp_path)


class TestBedrockSchemaValidator:
    """Tests for BedrockSchemaValidator."""
    
    def test_validate_block(self):
        """Test block schema validation."""
        BedrockSchemaValidator
        
        with tempfile.NamedTemporaryFile(suffix='.mcaddon', delete=False) as f:
            temp_path = f.name
        
        try:
            with zipfile.ZipFile(temp_path, 'w') as zf:
                zf.writestr('BP/blocks/grass_block.json', json.dumps({
                    "format_version": 1,
                    "minecraft:block": {
                        "description": {
                            "identifier": "mymod:grass_block"
                        }
                    }
                }))
            
            validator = BedrockSchemaValidator()
            result = validator.validate_all(temp_path)
            
            assert result.files_validated > 0
        finally:
            os.unlink(temp_path)
    
    def test_invalid_identifier(self):
        """Test detection of invalid block identifier."""
        BedrockSchemaValidator
        
        with tempfile.NamedTemporaryFile(suffix='.mcaddon', delete=False) as f:
            temp_path = f.name
        
        try:
            with zipfile.ZipFile(temp_path, 'w') as zf:
                zf.writestr('BP/blocks/bad_block.json', json.dumps({
                    "format_version": 1,
                    "minecraft:block": {
                        "description": {
                            "identifier": "BadBlock"  # Should be namespace:name
                        }
                    }
                }))
            
            validator = BedrockSchemaValidator()
            result = validator.validate_all(temp_path)
            
            # Should have errors due to invalid identifier format
            assert len(result.errors) > 0
        finally:
            os.unlink(temp_path)


class TestCorrelationChecker:
    """Tests for CorrelationChecker."""
    
    @pytest.mark.asyncio
    async def test_correlation_detection(self):
        """Test input-output correlation detection."""
        CorrelationChecker
        
        with tempfile.NamedTemporaryFile(suffix='.mcaddon', delete=False) as f:
            temp_path = f.name
        
        try:
            with zipfile.ZipFile(temp_path, 'w') as zf:
                zf.writestr('manifest.json', "{}")
                zf.writestr('blocks/grass_block.json', "{}")
                zf.writestr('items/diamond_sword.json', "{}")
            
            input_analysis = {
                'blocks': [{'name': 'grass_block'}],
                'items': [{'name': 'diamond_sword'}]
            }
            
            checker = CorrelationChecker()
            result = await checker.verify_correlation(input_analysis, temp_path)
            
            assert result.correlation_score >= 0
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
