"""
Bedrock Schema Validator

Deep validation of Bedrock JSON files against schemas.
"""

import logging
import zipfile
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)


@dataclass
class SchemaValidationResult:
    """Result of schema validation."""
    is_valid: bool
    files_validated: int = 0
    files_with_errors: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    validation_details: Dict[str, Any] = field(default_factory=dict)


class BedrockSchemaValidator:
    """
    Deep validation of Bedrock JSON files.
    
    Validates Bedrock add-on JSON files against known schemas
    and checks semantic correctness.
    """
    
    SCHEMAS = {
        'blocks': {
            'root_key': 'minecraft:block',
            'required': ['description'],
            'description_fields': ['identifier'],
        },
        'items': {
            'root_key': 'minecraft:item',
            'required': ['description'],
            'description_fields': ['identifier'],
        },
        'recipes': {
            'root_key': 'minecraft:recipe',
            'required': ['description'],
            'description_fields': ['identifier'],
        },
        'loot_tables': {
            'root_key': 'pools',
            'required': [],
        },
        'entity': {
            'root_key': 'minecraft:entity',
            'required': ['description', 'components'],
            'description_fields': ['identifier', 'runtime_identifier'],
        },
        'biomes': {
            'root_key': 'minecraft:biome',
            'required': ['description'],
            'description_fields': ['identifier'],
        },
        'manifest': {
            'root_key': None,
            'required': ['format_version', 'header', 'modules'],
        },
    }
    
    # Known Bedrock component types
    VALID_COMPONENTS = {
        'minecraft:block',
        'minecraft:item',
        'minecraft:entity',
        'minecraft:biome',
        'minecraft:recipe',
        'minecraft:loot_table',
        'minecraft:tag',
    }
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
    
    def validate_all(self, package_path: str) -> SchemaValidationResult:
        """
        Validate all Bedrock JSON files against schemas.
        
        Args:
            package_path: Path to the .mcaddon package
            
        Returns:
            SchemaValidationResult with validation status
        """
        errors = []
        warnings = []
        files_validated = 0
        files_with_errors = 0
        
        if not zipfile.is_zipfile(package_path):
            return SchemaValidationResult(
                is_valid=False,
                errors=[{
                    "type": "invalid_package",
                    "message": "Package is not a valid ZIP archive"
                }]
            )
        
        try:
            with zipfile.ZipFile(package_path, 'r') as zf:
                for file_path in zf.namelist():
                    if file_path.endswith('/'):
                        continue
                    
                    if not file_path.endswith(('.json', '.jsonc')):
                        continue
                    
                    # Determine schema type from path
                    schema_type = self._determine_schema_type(file_path)
                    
                    if schema_type:
                        files_validated += 1
                        file_errors, file_warnings = self._validate_file(
                            zf, file_path, schema_type
                        )
                        
                        if file_errors:
                            files_with_errors += 1
                            for error in file_errors:
                                error['file'] = file_path
                            errors.extend(file_errors)
                        
                        if file_warnings:
                            for warning in file_warnings:
                                warning['file'] = file_path
                            warnings.extend(file_warnings)
        
        except Exception as e:
            errors.append({
                "type": "validation_error",
                "message": f"Failed to validate package: {e}"
            })
        
        is_valid = len(errors) == 0
        
        return SchemaValidationResult(
            is_valid=is_valid,
            files_validated=files_validated,
            files_with_errors=files_with_errors,
            errors=errors,
            warnings=warnings,
            validation_details={
                'total_files': files_validated,
                'valid_files': files_validated - files_with_errors
            }
        )
    
    def _determine_schema_type(self, file_path: str) -> Optional[str]:
        """Determine which schema type to use based on file path."""
        path_lower = file_path.lower().replace('\\', '/')
        
        # Check path patterns
        if '/blocks/' in path_lower or path_lower.endswith('blocks.json'):
            return 'blocks'
        elif '/items/' in path_lower or path_lower.endswith('items.json'):
            return 'items'
        elif '/recipes/' in path_lower or 'recipe' in path_lower:
            return 'recipes'
        elif '/loot_tables/' in path_lower or '/loot_table/' in path_lower:
            return 'loot_tables'
        elif '/entities/' in path_lower or '/entity/' in path_lower:
            return 'entity'
        elif '/biomes/' in path_lower or '/biome/' in path_lower:
            return 'biomes'
        elif path_lower.endswith('manifest.json'):
            return 'manifest'
        
        return None
    
    def _validate_file(
        self,
        zf: zipfile.ZipFile,
        file_path: str,
        schema_type: str
    ) -> tuple:
        """Validate a single file against its schema."""
        errors = []
        warnings = []
        
        try:
            data = zf.read(file_path)
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                text = data.decode('latin-1')
            
            # Handle JSONC
            if file_path.endswith('.jsonc'):
                text = self._strip_comments(text)
            
            json_data = json.loads(text)
        except json.JSONDecodeError as e:
            errors.append({
                "type": "invalid_json",
                "message": f"Invalid JSON: {e}"
            })
            return errors, warnings
        except Exception as e:
            errors.append({
                "type": "read_error",
                "message": f"Failed to read file: {e}"
            })
            return errors, warnings
        
        schema = self.SCHEMAS.get(schema_type)
        if not schema:
            return errors, warnings
        
        # Validate based on schema type
        if schema_type == 'blocks':
            errors.extend(self._validate_block(json_data, file_path))
        elif schema_type == 'items':
            errors.extend(self._validate_item(json_data, file_path))
        elif schema_type == 'entity':
            errors.extend(self._validate_entity(json_data, file_path))
        elif schema_type == 'recipes':
            errors.extend(self._validate_recipe(json_data, file_path))
        elif schema_type == 'loot_tables':
            errors.extend(self._validate_loot_table(json_data, file_path))
        elif schema_type == 'manifest':
            errors.extend(self._validate_manifest_schema(json_data, file_path))
        
        return errors, warnings
    
    def _validate_block(self, data: Dict, file_path: str) -> List[Dict]:
        """Validate block definition."""
        errors = []
        
        # Check for minecraft:block key
        if 'minecraft:block' not in data:
            errors.append({
                "type": "missing_root_key",
                "expected": "minecraft:block",
                "message": "Block definition missing 'minecraft:block' root key"
            })
            return errors
        
        block = data.get('minecraft:block', {})
        
        # Check description
        if 'description' not in block:
            errors.append({
                "type": "missing_description",
                "message": "Block missing 'description' field"
            })
        else:
            desc = block['description']
            if 'identifier' not in desc:
                errors.append({
                    "type": "missing_identifier",
                    "message": "Block description missing 'identifier'"
                })
            elif not self._is_valid_identifier(desc['identifier']):
                errors.append({
                    "type": "invalid_identifier",
                    "identifier": desc['identifier'],
                    "message": f"Invalid block identifier: {desc['identifier']}"
                })
        
        return errors
    
    def _validate_item(self, data: Dict, file_path: str) -> List[Dict]:
        """Validate item definition."""
        errors = []
        
        if 'minecraft:item' not in data:
            errors.append({
                "type": "missing_root_key",
                "expected": "minecraft:item",
                "message": "Item definition missing 'minecraft:item' root key"
            })
            return errors
        
        item = data.get('minecraft:item', {})
        
        if 'description' not in item:
            errors.append({
                "type": "missing_description",
                "message": "Item missing 'description' field"
            })
        else:
            desc = item['description']
            if 'identifier' not in desc:
                errors.append({
                    "type": "missing_identifier",
                    "message": "Item description missing 'identifier'"
                })
            elif not self._is_valid_identifier(desc['identifier']):
                errors.append({
                    "type": "invalid_identifier",
                    "identifier": desc['identifier'],
                    "message": f"Invalid item identifier: {desc['identifier']}"
                })
        
        return errors
    
    def _validate_entity(self, data: Dict, file_path: str) -> List[Dict]:
        """Validate entity definition."""
        errors = []
        
        if 'minecraft:entity' not in data:
            errors.append({
                "type": "missing_root_key",
                "expected": "minecraft:entity",
                "message": "Entity definition missing 'minecraft:entity' root key"
            })
            return errors
        
        entity = data.get('minecraft:entity', {})
        
        # Check description
        if 'description' not in entity:
            errors.append({
                "type": "missing_description",
                "message": "Entity missing 'description' field"
            })
        else:
            desc = entity['description']
            if 'identifier' not in desc:
                errors.append({
                    "type": "missing_identifier",
                    "message": "Entity description missing 'identifier'"
                })
            elif not self._is_valid_identifier(desc['identifier']):
                errors.append({
                    "type": "invalid_identifier",
                    "identifier": desc['identifier'],
                    "message": f"Invalid entity identifier: {desc['identifier']}"
                })
        
        # Check components (at least one required)
        if 'components' not in entity and 'component_groups' not in entity:
            warnings = [{
                "type": "no_components",
                "message": "Entity has no components or component_groups"
            }]
        
        return errors
    
    def _validate_recipe(self, data: Dict, file_path: str) -> List[Dict]:
        """Validate recipe definition."""
        errors = []
        
        if 'minecraft:recipe' not in data:
            # Try alternative root keys
            found = False
            for key in data.keys():
                if 'recipe' in key.lower():
                    found = True
                    break
            
            if not found:
                errors.append({
                    "type": "missing_root_key",
                    "expected": "minecraft:recipe",
                    "message": "Recipe definition missing recipe root key"
                })
        
        return errors
    
    def _validate_loot_table(self, data: Dict, file_path: str) -> List[Dict]:
        """Validate loot table definition."""
        errors = []
        
        # Loot tables should have 'pools' array
        if 'pools' not in data:
            errors.append({
                "type": "missing_pools",
                "message": "Loot table missing 'pools' array"
            })
        elif not isinstance(data['pools'], list):
            errors.append({
                "type": "invalid_pools",
                "message": "'pools' must be an array"
            })
        
        return errors
    
    def _validate_manifest_schema(self, data: Dict, file_path: str) -> List[Dict]:
        """Validate manifest.json schema."""
        errors = []
        
        # Check format_version
        if 'format_version' not in data:
            errors.append({
                "type": "missing_format_version",
                "message": "manifest.json missing 'format_version'"
            })
        
        # Check header
        if 'header' not in data:
            errors.append({
                "type": "missing_header",
                "message": "manifest.json missing 'header'"
            })
        
        # Check modules
        if 'modules' not in data:
            errors.append({
                "type": "missing_modules",
                "message": "manifest.json missing 'modules'"
            })
        
        return errors
    
    def _is_valid_identifier(self, identifier: str) -> bool:
        """Check if identifier follows Bedrock naming convention."""
        if not identifier:
            return False
        
        # Format: namespace:name
        pattern = r'^[a-z_][a-z0-9_]*:[a-z_][a-z0-9_]*$'
        return bool(re.match(pattern, identifier, re.IGNORECASE))
    
    def _strip_comments(self, text: str) -> str:
        """Strip JSONC comments."""
        # Remove single-line comments
        text = ''.join(
            line.split('//')[0] for line in text.split('\n')
        )
        # Remove multi-line comments
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        return text
