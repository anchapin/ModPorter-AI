"""
Output Integrity Validator

Validates output package integrity and completeness for generated Bedrock add-ons.
"""

import logging
import zipfile
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .manifest_validator import ManifestValidator
from .file_integrity_checker import FileIntegrityChecker

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of output integrity validation."""
    is_valid: bool
    package_path: str
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    file_count: int = 0
    total_size: int = 0
    manifest_valid: bool = False
    integrity_valid: bool = False


class OutputIntegrityConfig:
    """Configuration for output integrity validation."""
    
    def __init__(
        self,
        required_manifest_fields: Optional[List[str]] = None,
        max_package_size_mb: int = 500,
        allow_empty_packages: bool = False,
    ):
        self.required_manifest_fields = required_manifest_fields or [
            'header', 'modules', 'dependencies'
        ]
        self.max_package_size_mb = max_package_size_mb
        self.allow_empty_packages = allow_empty_packages


class OutputIntegrityValidator:
    """
    Validates output package integrity and completeness.
    
    Performs deep validation of .mcaddon packages to ensure all
    generated Bedrock output meets quality standards.
    """
    
    def __init__(self, config: Optional[OutputIntegrityConfig] = None):
        self.config = config or OutputIntegrityConfig()
        self.manifest_validator = ManifestValidator()
        self.file_integrity_checker = FileIntegrityChecker()
    
    async def validate_package(
        self, 
        package_path: str
    ) -> ValidationResult:
        """
        Validate entire .mcaddon package.
        
        Args:
            package_path: Path to the .mcaddon package
            
        Returns:
            ValidationResult with validation status and details
        """
        errors = []
        warnings = []
        
        # 1. Check package is valid zip
        if not zipfile.is_zipfile(package_path):
            return ValidationResult(
                is_valid=False,
                package_path=package_path,
                errors=[{
                    "type": "invalid_package",
                    "message": "Package is not a valid ZIP archive"
                }]
            )
        
        # 2. Get package size
        package_size = Path(package_path).stat().st_size
        if package_size > self.config.max_package_size_mb * 1024 * 1024:
            errors.append({
                "type": "size_exceeded",
                "message": f"Package size {package_size} exceeds maximum {self.config.max_package_size_mb}MB"
            })
        
        # 3. Validate manifest.json
        manifest_valid = False
        manifest_errors = []
        try:
            with zipfile.ZipFile(package_path, 'r') as zf:
                if 'manifest.json' in zf.namelist():
                    manifest_data = json.loads(zf.read('manifest.json').decode('utf-8'))
                    manifest_result = self.manifest_validator.validate(manifest_data)
                    manifest_valid = manifest_result.is_valid
                    manifest_errors = manifest_result.errors
                else:
                    manifest_errors.append({
                        "type": "missing_manifest",
                        "message": "manifest.json not found in package"
                    })
        except json.JSONDecodeError as e:
            manifest_errors.append({
                "type": "invalid_json",
                "message": f"manifest.json is not valid JSON: {e}"
            })
        except Exception as e:
            manifest_errors.append({
                "type": "read_error",
                "message": f"Failed to read manifest: {e}"
            })
        
        if manifest_errors:
            errors.extend(manifest_errors)
        
        # 4. Verify required files present and check integrity
        integrity_result = self.file_integrity_checker.check_integrity(package_path)
        integrity_valid = integrity_result.is_valid
        
        if integrity_result.errors:
            errors.extend(integrity_result.errors)
        if integrity_result.warnings:
            warnings.extend(integrity_result.warnings)
        
        # 5. Check for empty package
        if integrity_result.file_count == 0 and not self.config.allow_empty_packages:
            errors.append({
                "type": "empty_package",
                "message": "Package contains no files"
            })
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            package_path=package_path,
            errors=errors,
            warnings=warnings,
            file_count=integrity_result.file_count,
            total_size=package_size,
            manifest_valid=manifest_valid,
            integrity_valid=integrity_valid
        )


# Convenience function for quick validation
async def validate_output_package(package_path: str) -> ValidationResult:
    """
    Quick validation of an output package.
    
    Args:
        package_path: Path to the .mcaddon package
        
    Returns:
        ValidationResult
    """
    validator = OutputIntegrityValidator()
    return await validator.validate_package(package_path)
