"""
Add-on Validator for validating Bedrock add-on packages and structure
Part of the Bedrock Add-on Generation System (Issue #6)
"""

import json
import logging
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import jsonschema
import uuid

logger = logging.getLogger(__name__)


class ValidationLevel:
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AddonValidator:
    """
    Comprehensive validator for Bedrock add-on packages.
    Validates manifest files, file structure, asset formats, and compatibility.
    """
    
    def __init__(self):
        # Bedrock manifest schemas
        self.manifest_schema = self._load_manifest_schema()
        
        # Valid Bedrock components and their schemas
        self.valid_components = self._load_component_schemas()
        
        # File format validation
        self.valid_formats = {
            'textures': ['.png'],
            'models': ['.geo.json', '.json'],
            'sounds': ['.ogg', '.wav'],
            'animations': ['.json'],
            'scripts': ['.js']
        }
        
        # Size constraints
        self.size_limits = {
            'texture_max_size': 1024,  # pixels
            'model_max_vertices': 3000,
            'sound_max_size_mb': 10,
            'script_max_size_kb': 500,
            'total_addon_max_mb': 500
        }
        
        # Bedrock version compatibility
        self.min_supported_version = [1, 16, 0]
        self.latest_stable_version = [1, 20, 0]
    
    def validate_addon(self, addon_path: Path) -> Dict[str, Any]:
        """
        Comprehensive validation of a .mcaddon file.
        
        Args:
            addon_path: Path to the .mcaddon file
            
        Returns:
            Validation results with detailed feedback
        """
        logger.info(f"Starting comprehensive validation of {addon_path}")
        
        validation_result = {
            'is_valid': True,
            'overall_score': 100,
            'validation_time': None,
            'errors': [],
            'warnings': [],
            'info': [],
            'stats': {},
            'compatibility': {},
            'recommendations': []
        }
        
        try:
            # Basic file validation
            if not self._validate_basic_file(addon_path, validation_result):
                return validation_result
            
            # Extract and analyze contents
            with zipfile.ZipFile(addon_path, 'r') as zipf:
                validation_result['stats'] = self._analyze_addon_stats(zipf)
                
                # Validate structure
                self._validate_addon_structure(zipf, validation_result)
                
                # Validate manifests
                self._validate_manifests(zipf, validation_result)
                
                # Validate individual files
                self._validate_addon_files(zipf, validation_result)
                
                # Check compatibility
                self._check_bedrock_compatibility(zipf, validation_result)
                
                # Generate recommendations
                self._generate_recommendations(validation_result)
            
            # Calculate final score
            validation_result['overall_score'] = self._calculate_overall_score(
                validation_result
            )
            validation_result['is_valid'] = len(validation_result['errors']) == 0
            
            logger.info(
                f"Validation completed. Score: {validation_result['overall_score']}/100"
            )
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            validation_result['is_valid'] = False
            validation_result['overall_score'] = 0
            validation_result['errors'].append(f"Validation failed: {str(e)}")
        
        return validation_result
    
    def _validate_basic_file(
        self, 
        addon_path: Path, 
        result: Dict[str, Any]
    ) -> bool:
        """Validate basic file properties."""
        # Check if file exists
        if not addon_path.exists():
            result['errors'].append(f"File does not exist: {addon_path}")
            return False
        
        # Check file extension
        if addon_path.suffix.lower() != '.mcaddon':
            result['warnings'].append("File extension should be .mcaddon")
        
        # Check file size
        file_size_mb = addon_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.size_limits['total_addon_max_mb']:
            result['errors'].append(
                f"File size ({file_size_mb:.1f}MB) exceeds maximum "
                f"({self.size_limits['total_addon_max_mb']}MB)"
            )
            return False
        elif file_size_mb > self.size_limits['total_addon_max_mb'] * 0.8:
            result['warnings'].append(
                f"Large file size ({file_size_mb:.1f}MB). "
                "Consider optimizing assets for better performance."
            )
        
        # Validate ZIP file
        try:
            with zipfile.ZipFile(addon_path, 'r') as zipf:
                zipf.testzip()
        except zipfile.BadZipFile:
            result['errors'].append("File is not a valid ZIP archive")
            return False
        except Exception as e:
            result['errors'].append(f"Error reading ZIP file: {e}")
            return False
        
        return True
    
    def _analyze_addon_stats(self, zipf: zipfile.ZipFile) -> Dict[str, Any]:
        """Analyze basic statistics of the add-on."""
        stats = {
            'total_files': len(zipf.namelist()),
            'total_size_compressed': sum(
                info.compress_size for info in zipf.infolist()
            ),
            'total_size_uncompressed': sum(
                info.file_size for info in zipf.infolist()
            ),
            'behavior_packs': set(),
            'resource_packs': set(),
            'file_types': {},
            'largest_files': []
        }
        
        # Analyze file types and pack structure
        for info in zipf.infolist():
            if not info.is_dir():
                # Track file types
                ext = Path(info.filename).suffix.lower()
                stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1
                
                # Identify packs
                if info.filename.startswith('behavior_packs/'):
                    parts = info.filename.split('/')
                    if len(parts) > 1:
                        stats['behavior_packs'].add(parts[1])
                elif info.filename.startswith('resource_packs/'):
                    parts = info.filename.split('/')
                    if len(parts) > 1:
                        stats['resource_packs'].add(parts[1])
                
                # Track large files
                if info.file_size > 1024 * 1024:  # > 1MB
                    stats['largest_files'].append({
                        'filename': info.filename,
                        'size_mb': info.file_size / (1024 * 1024)
                    })
        
        # Convert sets to lists for JSON serialization
        stats['behavior_packs'] = list(stats['behavior_packs'])
        stats['resource_packs'] = list(stats['resource_packs'])
        
        # Sort largest files
        stats['largest_files'].sort(key=lambda x: x['size_mb'], reverse=True)
        stats['largest_files'] = stats['largest_files'][:10]  # Top 10
        
        return stats
    
    def _validate_addon_structure(
        self, 
        zipf: zipfile.ZipFile, 
        result: Dict[str, Any]
    ):
        """Validate the add-on directory structure."""
        namelist = zipf.namelist()
        
        # Check for required top-level directories
        has_behavior_packs = any(
            name.startswith('behavior_packs/') for name in namelist
        )
        has_resource_packs = any(
            name.startswith('resource_packs/') for name in namelist
        )
        
        if not has_behavior_packs and not has_resource_packs:
            result['errors'].append(
                "Add-on must contain at least one behavior_packs/ or "
                "resource_packs/ directory"
            )
            return
        
        # Validate pack directory structure
        if has_behavior_packs:
            self._validate_pack_structure(namelist, 'behavior_packs', result)
        
        if has_resource_packs:
            self._validate_pack_structure(namelist, 'resource_packs', result)
        
        # Check for common structural issues
        self._check_common_structure_issues(namelist, result)
    
    def _validate_pack_structure(
        self, 
        namelist: List[str], 
        pack_type: str, 
        result: Dict[str, Any]
    ):
        """Validate structure of individual pack type."""
        pack_files = [
            name for name in namelist 
            if name.startswith(f'{pack_type}/')
        ]
        
        # Find all pack directories
        pack_dirs = set()
        for name in pack_files:
            parts = name.split('/')
            if len(parts) > 1:
                pack_dirs.add(parts[1])
        
        # Validate each pack
        for pack_dir in pack_dirs:
            pack_prefix = f'{pack_type}/{pack_dir}/'
            pack_specific_files = [
                name for name in namelist 
                if name.startswith(pack_prefix)
            ]
            
            # Check for manifest.json
            manifest_path = f'{pack_prefix}manifest.json'
            if manifest_path not in namelist:
                result['errors'].append(
                    f"Missing manifest.json in {pack_type}/{pack_dir}"
                )
                continue
            
            # Validate pack-specific structure
            if pack_type == 'behavior_packs':
                self._validate_behavior_pack_structure(
                    pack_specific_files, pack_dir, result
                )
            elif pack_type == 'resource_packs':
                self._validate_resource_pack_structure(
                    pack_specific_files, pack_dir, result
                )
    
    def _validate_behavior_pack_structure(
        self, 
        files: List[str], 
        pack_name: str, 
        result: Dict[str, Any]
    ):
        """Validate behavior pack specific structure."""
        allowed_dirs = [
            'animations', 'animation_controllers', 'blocks', 'entities',
            'functions', 'items', 'loot_tables', 'recipes', 'scripts',
            'spawn_rules', 'texts', 'trading'
        ]
        
        for file_path in files:
            if '/' in file_path:
                parts = file_path.split('/')
                if len(parts) > 2:  # behavior_packs/pack_name/directory/...
                    dir_name = parts[2]
                    if dir_name not in allowed_dirs and not file_path.endswith('.json'):
                        result['warnings'].append(
                            f"Unexpected directory '{dir_name}' in "
                            f"behavior pack '{pack_name}'"
                        )
    
    def _validate_resource_pack_structure(
        self, 
        files: List[str], 
        pack_name: str, 
        result: Dict[str, Any]
    ):
        """Validate resource pack specific structure."""
        allowed_dirs = [
            'animations', 'animation_controllers', 'attachables', 'blocks',
            'entity', 'fogs', 'font', 'models', 'particles', 'sounds',
            'textures', 'texts', 'ui'
        ]
        
        for file_path in files:
            if '/' in file_path:
                parts = file_path.split('/')
                if len(parts) > 2:  # resource_packs/pack_name/directory/...
                    dir_name = parts[2]
                    if dir_name not in allowed_dirs and not file_path.endswith('.json'):
                        result['warnings'].append(
                            f"Unexpected directory '{dir_name}' in "
                            f"resource pack '{pack_name}'"
                        )
    
    def _check_common_structure_issues(
        self, 
        namelist: List[str], 
        result: Dict[str, Any]
    ):
        """Check for common structural issues."""
        # Check for files in root directory
        root_files = [
            name for name in namelist 
            if '/' not in name.strip('/')
        ]
        if root_files:
            result['warnings'].append(
                f"Files found in root directory: {', '.join(root_files[:3])}"
                + ("..." if len(root_files) > 3 else "")
            )
        
        # Check for incorrect pack directory names
        incorrect_names = [
            name for name in namelist 
            if name.startswith(('behavior_pack/', 'resource_pack/'))  # Singular form
        ]
        if incorrect_names:
            result['errors'].append(
                "Found directories with incorrect names. Use "
                "'behavior_packs' and 'resource_packs' (plural)"
            )
        
        # Check for empty directories
        dirs = set()
        for name in namelist:
            if name.endswith('/'):
                dirs.add(name)
        
        files_dirs = set()
        for name in namelist:
            if not name.endswith('/'):
                files_dirs.add('/'.join(name.split('/')[:-1]) + '/')
        
        empty_dirs = dirs - files_dirs
        if empty_dirs:
            result['info'].append(
                f"Found {len(empty_dirs)} empty directories "
                f"that could be removed"
            )
    
    def _validate_manifests(
        self, 
        zipf: zipfile.ZipFile, 
        result: Dict[str, Any]
    ):
        """Validate all manifest.json files in the add-on."""
        manifest_files = [
            name for name in zipf.namelist() 
            if name.endswith('manifest.json')
        ]
        
        if not manifest_files:
            result['errors'].append("No manifest.json files found")
            return
        
        for manifest_path in manifest_files:
            try:
                with zipf.open(manifest_path) as f:
                    manifest_data = json.load(f)
                
                self._validate_single_manifest(
                    manifest_data, manifest_path, result
                )
                
            except json.JSONDecodeError as e:
                result['errors'].append(
                    f"Invalid JSON in {manifest_path}: {e}"
                )
            except Exception as e:
                result['errors'].append(f"Error reading {manifest_path}: {e}")
    
    def _validate_single_manifest(
        self, 
        manifest: Dict[str, Any], 
        path: str, 
        result: Dict[str, Any]
    ):
        """Validate a single manifest file."""
        # Schema validation
        try:
            jsonschema.validate(manifest, self.manifest_schema)
        except jsonschema.ValidationError as e:
            result['errors'].append(
                f"Manifest schema error in {path}: {e.message}"
            )
            return
        
        # UUID validation
        header = manifest.get('header', {})
        uuid_str = header.get('uuid', '')
        
        try:
            uuid.UUID(uuid_str)
        except ValueError:
            result['errors'].append(f"Invalid UUID in {path}: {uuid_str}")
        
        # Version validation
        version = header.get('version', [])
        if not isinstance(version, list) or len(version) != 3:
            result['errors'].append(f"Invalid version format in {path}")
        elif not all(isinstance(v, int) and v >= 0 for v in version):
            result['errors'].append(f"Version numbers must be non-negative integers in {path}")
        
        # Engine version compatibility
        min_engine = header.get('min_engine_version', [])
        if min_engine:
            if self._compare_versions(min_engine, self.latest_stable_version) > 0:
                result['warnings'].append(
                    f"Manifest {path} requires engine version {min_engine} "
                    f"which is newer than latest stable {self.latest_stable_version}"
                )
        
        # Module validation
        modules = manifest.get('modules', [])
        if not modules:
            result['errors'].append(f"No modules defined in {path}")
        
        for i, module in enumerate(modules):
            module_type = module.get('type', '')
            if module_type not in ['data', 'resources', 'client_data', 'javascript']:
                result['warnings'].append(
                    f"Unknown module type '{module_type}' in {path}, module {i}"
                )
            
            # Check module UUID
            module_uuid = module.get('uuid', '')
            try:
                uuid.UUID(module_uuid)
            except ValueError:
                result['errors'].append(f"Invalid module UUID in {path}, module {i}: {module_uuid}")
        
        # Capability validation
        capabilities = manifest.get('capabilities', [])
        known_capabilities = [
            'chemistry', 'experimental_custom_ui', 'script_eval'
        ]
        
        for capability in capabilities:
            if capability not in known_capabilities:
                result['warnings'].append(
                    f"Unknown capability '{capability}' in {path}"
                )
    
    def _validate_addon_files(self, zipf: zipfile.ZipFile, result: Dict[str, Any]):
        """Validate individual files within the add-on."""
        for info in zipf.infolist():
            if info.is_dir():
                continue
            
            file_path = info.filename
            file_size = info.file_size
            
            # Validate based on file type
            if file_path.endswith('.json'):
                self._validate_json_file(zipf, file_path, result)
            elif file_path.endswith('.png'):
                self._validate_texture_file(zipf, file_path, file_size, result)
            elif file_path.endswith(('.ogg', '.wav')):
                self._validate_sound_file(file_path, file_size, result)
            elif file_path.endswith('.js'):
                self._validate_script_file(zipf, file_path, file_size, result)
    
    def _validate_json_file(self, zipf: zipfile.ZipFile, file_path: str, result: Dict[str, Any]):
        """Validate JSON files for syntax and structure."""
        try:
            with zipf.open(file_path) as f:
                json.load(f)
        except json.JSONDecodeError as e:
            result['errors'].append(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            result['warnings'].append(f"Could not validate JSON file {file_path}: {e}")
    
    def _validate_texture_file(self, zipf: zipfile.ZipFile, file_path: str, file_size: int, result: Dict[str, Any]):
        """Validate texture files."""
        # Check file size
        if file_size > 5 * 1024 * 1024:  # 5MB
            result['warnings'].append(f"Large texture file: {file_path} ({file_size / 1024 / 1024:.1f}MB)")
        
        # For now, we can't easily validate image dimensions without extracting
        # In a more complete implementation, we could extract and check with PIL
    
    def _validate_sound_file(self, file_path: str, file_size: int, result: Dict[str, Any]):
        """Validate sound files."""
        max_size = self.size_limits['sound_max_size_mb'] * 1024 * 1024
        if file_size > max_size:
            result['warnings'].append(
                f"Large sound file: {file_path} "
                f"({file_size / 1024 / 1024:.1f}MB > {self.size_limits['sound_max_size_mb']}MB)"
            )
    
    def _validate_script_file(self, zipf: zipfile.ZipFile, file_path: str, file_size: int, result: Dict[str, Any]):
        """Validate JavaScript files."""
        max_size = self.size_limits['script_max_size_kb'] * 1024
        if file_size > max_size:
            result['warnings'].append(
                f"Large script file: {file_path} "
                f"({file_size / 1024:.1f}KB > {self.size_limits['script_max_size_kb']}KB)"
            )
        
        # Basic syntax validation
        try:
            with zipf.open(file_path) as f:
                content = f.read().decode('utf-8', errors='ignore')
                # Very basic JavaScript syntax check
                if content.count('{') != content.count('}'):
                    result['warnings'].append(f"Potential syntax error in {file_path}: mismatched braces")
        except Exception as e:
            result['warnings'].append(f"Could not validate script file {file_path}: {e}")
    
    def _check_bedrock_compatibility(self, zipf: zipfile.ZipFile, result: Dict[str, Any]):
        """Check compatibility with different Bedrock versions."""
        compatibility = {
            'bedrock_edition': True,
            'education_edition': True,
            'min_version_detected': self.min_supported_version,
            'experimental_features': [],
            'compatibility_issues': []
        }
        
        # Check for experimental features
        manifest_files = [name for name in zipf.namelist() if name.endswith('manifest.json')]
        
        for manifest_path in manifest_files:
            try:
                with zipf.open(manifest_path) as f:
                    manifest = json.load(f)
                
                capabilities = manifest.get('capabilities', [])
                for cap in capabilities:
                    if 'experimental' in cap:
                        compatibility['experimental_features'].append(cap)
                
                # Check engine version requirements
                min_engine = manifest.get('header', {}).get('min_engine_version', [])
                if min_engine and self._compare_versions(min_engine, compatibility['min_version_detected']) > 0:
                    compatibility['min_version_detected'] = min_engine
                
            except Exception:
                continue
        
        # Check for Education Edition compatibility
        script_files = [name for name in zipf.namelist() if name.endswith('.js')]
        if script_files:
            compatibility['education_edition'] = False
            compatibility['compatibility_issues'].append(
                "JavaScript files may not be supported in Education Edition"
            )
        
        if compatibility['experimental_features']:
            compatibility['compatibility_issues'].append(
                f"Uses experimental features: {', '.join(compatibility['experimental_features'])}"
            )
        
        result['compatibility'] = compatibility
    
    def _generate_recommendations(self, result: Dict[str, Any]):
        """Generate actionable recommendations based on validation results."""
        recommendations = []
        stats = result.get('stats', {})
        
        # Size optimization recommendations
        if stats.get('total_size_uncompressed', 0) > 100 * 1024 * 1024:  # 100MB
            recommendations.append("Consider optimizing assets to reduce file size")
        
        if stats.get('largest_files'):
            largest = stats['largest_files'][0]
            if largest['size_mb'] > 10:
                recommendations.append(
                    f"Optimize large file: {largest['filename']} ({largest['size_mb']:.1f}MB)"
                )
        
        # Structure recommendations
        if len(result.get('warnings', [])) > 5:
            recommendations.append("Review and address structural warnings")
        
        # Compatibility recommendations
        compatibility = result.get('compatibility', {})
        if compatibility.get('experimental_features'):
            recommendations.append(
                "Consider alternatives to experimental features for better compatibility"
            )
        
        if not result.get('is_valid'):
            recommendations.append("Fix all validation errors before distribution")
        elif result.get('overall_score', 0) < 80:
            recommendations.append("Address warnings to improve add-on quality")
        
        result['recommendations'] = recommendations
    
    def _calculate_overall_score(self, result: Dict[str, Any]) -> int:
        """Calculate overall quality score."""
        score = 100
        
        # Deduct points for errors and warnings
        errors = len(result.get('errors', []))
        warnings = len(result.get('warnings', []))
        
        score -= errors * 15  # 15 points per error
        score -= warnings * 3  # 3 points per warning
        
        # Bonus points for good practices
        stats = result.get('stats', {})
        if stats.get('behavior_packs') and stats.get('resource_packs'):
            score += 5  # Complete add-on with both packs
        
        compatibility = result.get('compatibility', {})
        if not compatibility.get('experimental_features'):
            score += 5  # No experimental features
        
        return max(0, min(100, score))
    
    def _compare_versions(self, v1: List[int], v2: List[int]) -> int:
        """Compare two version arrays. Returns -1, 0, or 1."""
        for i in range(max(len(v1), len(v2))):
            a = v1[i] if i < len(v1) else 0
            b = v2[i] if i < len(v2) else 0
            if a < b:
                return -1
            elif a > b:
                return 1
        return 0
    
    def _load_manifest_schema(self) -> Dict[str, Any]:
        """Load Bedrock manifest JSON schema."""
        return {
            "type": "object",
            "required": ["format_version", "header", "modules"],
            "properties": {
                "format_version": {"type": "integer", "minimum": 1, "maximum": 2},
                "header": {
                    "type": "object",
                    "required": ["name", "description", "uuid", "version"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1, "maxLength": 256},
                        "description": {"type": "string", "maxLength": 512},
                        "uuid": {"type": "string", "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"},
                        "version": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 0},
                            "minItems": 3,
                            "maxItems": 3
                        },
                        "min_engine_version": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 0},
                            "minItems": 3,
                            "maxItems": 3
                        }
                    }
                },
                "modules": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["type", "uuid", "version"],
                        "properties": {
                            "type": {"type": "string", "enum": ["data", "resources", "client_data", "javascript"]},
                            "uuid": {"type": "string", "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"},
                            "version": {
                                "type": "array",
                                "items": {"type": "integer", "minimum": 0},
                                "minItems": 3,
                                "maxItems": 3
                            }
                        }
                    }
                },
                "capabilities": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "dependencies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["uuid", "version"],
                        "properties": {
                            "uuid": {"type": "string"},
                            "version": {"type": "array"}
                        }
                    }
                }
            }
        }
    
    def _load_component_schemas(self) -> Dict[str, Any]:
        """Load schemas for Bedrock components."""
        # This would contain schemas for various Bedrock components
        # For now, return empty dict - could be expanded in future
        return {}
    
    def validate_manifest_only(self, manifest_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate only a manifest.json structure.
        
        Args:
            manifest_data: Manifest dictionary
            
        Returns:
            Validation results
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        self._validate_single_manifest(manifest_data, "manifest.json", result)
        
        # Set is_valid based on whether there are errors
        result['is_valid'] = len(result['errors']) == 0
        
        return result