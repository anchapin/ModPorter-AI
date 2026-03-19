"""
Manifest Validator

Validates Bedrock manifest.json files in generated packages.
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)


@dataclass
class ManifestValidationResult:
    """Result of manifest validation."""
    is_valid: bool
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    manifest_data: Dict[str, Any] = field(default_factory=dict)


class ManifestValidator:
    """
    Validates Bedrock manifest.json files.
    
    Ensures manifest files conform to Bedrock add-on specifications.
    """
    
    REQUIRED_FIELDS = ['header', 'modules']
    REQUIRED_HEADER_FIELDS = ['name', 'uuid', 'version']
    REQUIRED_MODULE_FIELDS = ['type', 'uuid']
    
    # UUID pattern (standard format)
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    )
    
    # Version array pattern (3 integers)
    VERSION_PATTERN = re.compile(r'^\d+\.\d+\.\d+$')
    
    VALID_MODULE_TYPES = [
        'skin_pack',
        'resource_pack',
        'data',
        'world_template',
    ]
    
    def validate(self, manifest: Dict[str, Any]) -> ManifestValidationResult:
        """
        Validate manifest structure and content.
        
        Args:
            manifest: Parsed manifest.json data
            
        Returns:
            ManifestValidationResult with validation status
        """
        errors = []
        warnings = []
        
        # Check root level required fields
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in manifest:
                errors.append({
                    "type": "missing_field",
                    "field": field_name,
                    "message": f"Required field '{field_name}' not found in manifest"
                })
        
        # Validate header
        if 'header' in manifest:
            header_errors, header_warnings = self._validate_header(manifest['header'])
            errors.extend(header_errors)
            warnings.extend(header_warnings)
        else:
            errors.append({
                "type": "missing_header",
                "message": "Header section is required"
            })
        
        # Validate modules
        if 'modules' in manifest:
            modules_errors, modules_warnings = self._validate_modules(manifest['modules'])
            errors.extend(modules_errors)
            warnings.extend(modules_warnings)
        else:
            errors.append({
                "type": "missing_modules",
                "message": "At least one module is required"
            })
        
        # Validate dependencies (optional but warn if malformed)
        if 'dependencies' in manifest:
            deps_errors, deps_warnings = self._validate_dependencies(manifest['dependencies'])
            errors.extend(deps_errors)
            warnings.extend(deps_warnings)
        
        is_valid = len(errors) == 0
        
        return ManifestValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            manifest_data=manifest
        )
    
    def _validate_header(self, header: Dict[str, Any]) -> tuple:
        """Validate header section."""
        errors = []
        warnings = []
        
        # Check required header fields
        for field_name in self.REQUIRED_HEADER_FIELDS:
            if field_name not in header:
                errors.append({
                    "type": "missing_header_field",
                    "field": field_name,
                    "message": f"Required header field '{field_name}' not found"
                })
        
        # Validate name
        if 'name' in header:
            name = header['name']
            if not isinstance(name, str):
                errors.append({
                    "type": "invalid_header_field",
                    "field": "name",
                    "message": "Header 'name' must be a string"
                })
            elif len(name) == 0:
                errors.append({
                    "type": "invalid_header_field",
                    "field": "name",
                    "message": "Header 'name' cannot be empty"
                })
        
        # Validate UUID
        if 'uuid' in header:
            uuid = header['uuid']
            if not isinstance(uuid, str):
                errors.append({
                    "type": "invalid_header_field",
                    "field": "uuid",
                    "message": "Header 'uuid' must be a string"
                })
            elif not self.UUID_PATTERN.match(uuid):
                warnings.append({
                    "type": "invalid_uuid_format",
                    "field": "uuid",
                    "message": "UUID should be in format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                })
        
        # Validate version
        if 'version' in header:
            version = header['version']
            if isinstance(version, str):
                if not self.VERSION_PATTERN.match(version):
                    warnings.append({
                        "type": "version_format_warning",
                        "message": "Version should be in format: X.Y.Z (e.g., 1.0.0)"
                    })
            elif isinstance(version, list):
                if len(version) != 3:
                    errors.append({
                        "type": "invalid_version",
                        "message": "Version array must have exactly 3 elements [major, minor, patch]"
                    })
                elif not all(isinstance(v, int) for v in version):
                    errors.append({
                        "type": "invalid_version",
                        "message": "Version array elements must be integers"
                    })
            else:
                errors.append({
                    "type": "invalid_version",
                    "message": "Version must be a string or array of 3 integers"
                })
        
        # Validate description (optional)
        if 'description' in header:
            if not isinstance(header['description'], str):
                warnings.append({
                    "type": "optional_field_type",
                    "field": "description",
                    "message": "Description should be a string"
                })
        
        return errors, warnings
    
    def _validate_modules(self, modules: Any) -> tuple:
        """Validate modules section."""
        errors = []
        warnings = []
        
        if not isinstance(modules, list):
            errors.append({
                "type": "invalid_modules",
                "message": "Modules must be an array"
            })
            return errors, warnings
        
        if len(modules) == 0:
            errors.append({
                "type": "empty_modules",
                "message": "At least one module is required"
            })
            return errors, warnings
        
        for idx, module in enumerate(modules):
            if not isinstance(module, dict):
                errors.append({
                    "type": "invalid_module",
                    "index": idx,
                    "message": f"Module {idx} must be an object"
                })
                continue
            
            # Check required module fields
            for field_name in self.REQUIRED_MODULE_FIELDS:
                if field_name not in module:
                    errors.append({
                        "type": "missing_module_field",
                        "index": idx,
                        "field": field_name,
                        "message": f"Module {idx} missing required field '{field_name}'"
                    })
            
            # Validate module type
            if 'type' in module:
                module_type = module['type']
                if module_type not in self.VALID_MODULE_TYPES:
                    warnings.append({
                        "type": "unknown_module_type",
                        "index": idx,
                        "module_type": module_type,
                        "message": f"Module type '{module_type}' may not be recognized. Valid types: {', '.join(self.VALID_MODULE_TYPES)}"
                    })
            
            # Validate module UUID
            if 'uuid' in module:
                uuid = module['uuid']
                if not isinstance(uuid, str):
                    errors.append({
                        "type": "invalid_module_uuid",
                        "index": idx,
                        "message": "Module UUID must be a string"
                    })
                elif not self.UUID_PATTERN.match(uuid):
                    warnings.append({
                        "type": "invalid_module_uuid_format",
                        "index": idx,
                        "message": "Module UUID should be in standard UUID format"
                    })
        
        return errors, warnings
    
    def _validate_dependencies(self, dependencies: Any) -> tuple:
        """Validate dependencies section."""
        errors = []
        warnings = []
        
        if not isinstance(dependencies, list):
            errors.append({
                "type": "invalid_dependencies",
                "message": "Dependencies must be an array"
            })
            return errors, warnings
        
        for idx, dep in enumerate(dependencies):
            if not isinstance(dep, dict):
                errors.append({
                    "type": "invalid_dependency",
                    "index": idx,
                    "message": f"Dependency {idx} must be an object"
                })
                continue
            
            if 'uuid' not in dep:
                errors.append({
                    "type": "missing_dependency_uuid",
                    "index": idx,
                    "message": f"Dependency {idx} missing required field 'uuid'"
                })
            elif not self.UUID_PATTERN.match(dep.get('uuid', '')):
                warnings.append({
                    "type": "invalid_dependency_uuid",
                    "index": idx,
                    "message": "Dependency UUID should be in standard UUID format"
                })
        
        return errors, warnings
