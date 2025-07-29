"""
File Packager for creating .mcaddon packages from Bedrock add-on components
Part of the Bedrock Add-on Generation System (Issue #6)
"""

import os
import zipfile
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import tempfile
import magic

logger = logging.getLogger(__name__)


class FilePackager:
    """
    Packager for creating .mcaddon files from behavior and resource pack directories.
    Handles proper folder structure, compression, and validation.
    """
    
    def __init__(self):
        # Bedrock add-on file structure requirements
        self.required_structure = {
            'behavior_packs': {
                'required_files': ['manifest.json'],
                'allowed_dirs': [
                    'animations', 'animation_controllers', 'blocks', 'entities', 
                    'functions', 'items', 'loot_tables', 'recipes', 'scripts',
                    'spawn_rules', 'trading', 'texts'
                ]
            },
            'resource_packs': {
                'required_files': ['manifest.json'],
                'allowed_dirs': [
                    'animations', 'animation_controllers', 'attachables', 'blocks',
                    'entity', 'fogs', 'font', 'models', 'particles', 'sounds',
                    'textures', 'texts', 'ui'
                ]
            }
        }
        
        # File size and validation constraints
        self.constraints = {
            'max_total_size_mb': 500,
            'max_files': 2000,
            'forbidden_extensions': ['.exe', '.dll', '.bat', '.sh', '.com', '.scr'],
            'max_individual_file_mb': 50
        }
        
        # Initialize magic for file type detection
        try:
            self.magic = magic.Magic(mime=True)
        except Exception as e:
            logger.warning(f"Could not initialize python-magic: {e}")
            self.magic = None
    
    def package_addon(self, addon_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create .mcaddon package from addon data.
        
        Args:
            addon_data: Dictionary containing pack paths and metadata
            
        Returns:
            Dictionary with packaging results
        """
        logger.info("Starting .mcaddon package creation")
        
        result = {
            'success': False,
            'output_path': None,
            'file_size': 0,
            'validation_results': {},
            'errors': []
        }
        
        try:
            # Extract required parameters
            output_path = Path(addon_data['output_path'])
            behavior_pack_path = addon_data.get('behavior_pack_path')
            resource_pack_path = addon_data.get('resource_pack_path')
            source_directories = addon_data.get('source_directories', [])
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create temporary working directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Copy and organize pack directories
                pack_info = self._organize_pack_structure(
                    temp_path, behavior_pack_path, resource_pack_path, source_directories
                )
                
                # Validate pack structure
                validation_results = self._validate_pack_structure(temp_path)
                result['validation_results'] = validation_results
                
                if not validation_results['is_valid']:
                    result['errors'].extend(validation_results['errors'])
                    return result
                
                # Create .mcaddon file
                self._create_mcaddon_file(temp_path, output_path)
                
                # Get final file info
                result['output_path'] = str(output_path)
                result['file_size'] = output_path.stat().st_size
                result['pack_info'] = pack_info
                result['success'] = True
                
                logger.info(f"Successfully created .mcaddon: {output_path} ({result['file_size']} bytes)")
                
        except Exception as e:
            logger.error(f"Failed to package addon: {e}")
            result['errors'].append(str(e))
        
        return result
    
    def _organize_pack_structure(self, temp_path: Path, behavior_pack_path: Optional[str],
                               resource_pack_path: Optional[str], 
                               source_directories: List[str]) -> Dict[str, Any]:
        """Organize pack directories into proper Bedrock structure."""
        pack_info = {
            'behavior_packs': [],
            'resource_packs': [],
            'total_files': 0
        }
        
        # Create behavior_packs and resource_packs directories
        bp_root = temp_path / "behavior_packs"
        rp_root = temp_path / "resource_packs"
        bp_root.mkdir(exist_ok=True)
        rp_root.mkdir(exist_ok=True)
        
        # Handle source directories (preferred method)
        if source_directories:
            for source_dir in source_directories:
                source_path = Path(source_dir)
                if not source_path.exists():
                    logger.warning(f"Source directory does not exist: {source_dir}")
                    continue
                
                # Determine pack type from directory structure
                if self._is_behavior_pack(source_path):
                    pack_name = self._get_pack_name(source_path, "bp")
                    dest_path = bp_root / pack_name
                    self._copy_pack_contents(source_path, dest_path)
                    pack_info['behavior_packs'].append(pack_name)
                    
                elif self._is_resource_pack(source_path):
                    pack_name = self._get_pack_name(source_path, "rp")
                    dest_path = rp_root / pack_name
                    self._copy_pack_contents(source_path, dest_path)
                    pack_info['resource_packs'].append(pack_name)
                    
                else:
                    logger.warning(f"Could not determine pack type for: {source_dir}")
        
        # Handle legacy format (individual pack paths)
        if behavior_pack_path and Path(behavior_pack_path).exists():
            bp_source = Path(behavior_pack_path)
            pack_name = self._get_pack_name(bp_source, "bp")
            dest_path = bp_root / pack_name
            self._copy_pack_contents(bp_source, dest_path)
            pack_info['behavior_packs'].append(pack_name)
        
        if resource_pack_path and Path(resource_pack_path).exists():
            rp_source = Path(resource_pack_path)
            pack_name = self._get_pack_name(rp_source, "rp")
            dest_path = rp_root / pack_name
            self._copy_pack_contents(rp_source, dest_path)
            pack_info['resource_packs'].append(pack_name)
        
        # Count total files
        pack_info['total_files'] = sum(1 for _ in temp_path.rglob('*') if _.is_file())
        
        return pack_info
    
    def _is_behavior_pack(self, pack_path: Path) -> bool:
        """Determine if directory is a behavior pack."""
        manifest_path = pack_path / "manifest.json"
        if not manifest_path.exists():
            return False
        
        try:
            import json
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # Check for data module type
            for module in manifest.get('modules', []):
                if module.get('type') in ['data', 'javascript']:
                    return True
        except Exception as e:
            logger.warning(f"Could not parse manifest in {pack_path}: {e}")
        
        # Fallback: check for typical BP directories
        bp_dirs = ['entities', 'functions', 'loot_tables', 'recipes', 'scripts']
        return any((pack_path / dir_name).exists() for dir_name in bp_dirs)
    
    def _is_resource_pack(self, pack_path: Path) -> bool:
        """Determine if directory is a resource pack."""
        manifest_path = pack_path / "manifest.json"
        if not manifest_path.exists():
            return False
        
        try:
            import json
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # Check for resources module type
            for module in manifest.get('modules', []):
                if module.get('type') in ['resources', 'client_data']:
                    return True
        except Exception as e:
            logger.warning(f"Could not parse manifest in {pack_path}: {e}")
        
        # Fallback: check for typical RP directories
        rp_dirs = ['textures', 'models', 'sounds', 'animations']
        return any((pack_path / dir_name).exists() for dir_name in rp_dirs)
    
    def _get_pack_name(self, pack_path: Path, pack_type: str) -> str:
        """Get pack name from manifest or directory name."""
        manifest_path = pack_path / "manifest.json"
        
        try:
            import json
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            name = manifest.get('header', {}).get('name', '')
            if name:
                # Sanitize name for file system
                safe_name = ''.join(c for c in name if c.isalnum() or c in ' -_').strip()
                return safe_name.replace(' ', '_')
        except Exception:
            pass
        
        # Fallback to directory name
        dir_name = pack_path.name
        if dir_name in ['behavior_pack', 'resource_pack']:
            return f"converted_mod_{pack_type}"
        
        return dir_name
    
    def _copy_pack_contents(self, source_path: Path, dest_path: Path):
        """Copy pack contents with validation."""
        dest_path.mkdir(parents=True, exist_ok=True)
        
        for item in source_path.rglob('*'):
            if item.is_file():
                # Check file constraints
                if not self._validate_file(item):
                    logger.warning(f"Skipping invalid file: {item}")
                    continue
                
                # Calculate relative path and copy
                rel_path = item.relative_to(source_path)
                dest_file = dest_path / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(item, dest_file)
    
    def _validate_file(self, file_path: Path) -> bool:
        """Validate individual file against constraints."""
        # Check file extension
        if file_path.suffix.lower() in self.constraints['forbidden_extensions']:
            logger.warning(f"Forbidden file extension: {file_path}")
            return False
        
        # Check file size
        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.constraints['max_individual_file_mb']:
                logger.warning(f"File too large ({file_size_mb:.1f}MB): {file_path}")
                return False
        except OSError:
            logger.warning(f"Could not check file size: {file_path}")
            return False
        
        # Check MIME type if available
        if self.magic:
            try:
                mime_type = self.magic.from_file(str(file_path))
                if 'executable' in mime_type.lower():
                    logger.warning(f"Executable file detected: {file_path}")
                    return False
            except Exception:
                pass  # Continue if MIME detection fails
        
        return True
    
    def _validate_pack_structure(self, temp_path: Path) -> Dict[str, Any]:
        """Validate the organized pack structure."""
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'stats': {
                'total_files': 0,
                'total_size_mb': 0,
                'behavior_packs': 0,
                'resource_packs': 0
            }
        }
        
        # Check for required top-level directories
        bp_dir = temp_path / "behavior_packs"
        rp_dir = temp_path / "resource_packs"
        
        if not bp_dir.exists() and not rp_dir.exists():
            validation['errors'].append("No behavior_packs or resource_packs directories found")
            validation['is_valid'] = False
            return validation
        
        # Validate behavior packs
        if bp_dir.exists():
            for pack_dir in bp_dir.iterdir():
                if pack_dir.is_dir():
                    validation['stats']['behavior_packs'] += 1
                    pack_validation = self._validate_individual_pack(pack_dir, 'behavior')
                    if not pack_validation['is_valid']:
                        validation['errors'].extend(pack_validation['errors'])
                        validation['is_valid'] = False
                    validation['warnings'].extend(pack_validation['warnings'])
        
        # Validate resource packs
        if rp_dir.exists():
            for pack_dir in rp_dir.iterdir():
                if pack_dir.is_dir():
                    validation['stats']['resource_packs'] += 1
                    pack_validation = self._validate_individual_pack(pack_dir, 'resource')
                    if not pack_validation['is_valid']:
                        validation['errors'].extend(pack_validation['errors'])
                        validation['is_valid'] = False
                    validation['warnings'].extend(pack_validation['warnings'])
        
        # Calculate overall stats
        validation['stats']['total_files'] = sum(1 for _ in temp_path.rglob('*') if _.is_file())
        validation['stats']['total_size_mb'] = sum(
            f.stat().st_size for f in temp_path.rglob('*') if f.is_file()
        ) / (1024 * 1024)
        
        # Check size constraints
        if validation['stats']['total_size_mb'] > self.constraints['max_total_size_mb']:
            validation['errors'].append(
                f"Total size ({validation['stats']['total_size_mb']:.1f}MB) exceeds limit "
                f"({self.constraints['max_total_size_mb']}MB)"
            )
            validation['is_valid'] = False
        
        if validation['stats']['total_files'] > self.constraints['max_files']:
            validation['errors'].append(
                f"Total files ({validation['stats']['total_files']}) exceeds limit "
                f"({self.constraints['max_files']})"
            )
            validation['is_valid'] = False
        
        return validation
    
    def _validate_individual_pack(self, pack_dir: Path, pack_type: str) -> Dict[str, Any]:
        """Validate an individual pack directory."""
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check for required manifest.json
        manifest_path = pack_dir / "manifest.json"
        if not manifest_path.exists():
            validation['errors'].append(f"Missing manifest.json in {pack_dir.name}")
            validation['is_valid'] = False
            return validation
        
        # Validate manifest content
        try:
            import json
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # Check required fields
            required_fields = ['format_version', 'header', 'modules']
            for field in required_fields:
                if field not in manifest:
                    validation['errors'].append(f"Missing {field} in manifest of {pack_dir.name}")
                    validation['is_valid'] = False
            
            # Check header fields
            if 'header' in manifest:
                header_fields = ['name', 'description', 'uuid', 'version']
                for field in header_fields:
                    if field not in manifest['header']:
                        validation['errors'].append(
                            f"Missing header.{field} in manifest of {pack_dir.name}"
                        )
                        validation['is_valid'] = False
            
        except json.JSONDecodeError as e:
            validation['errors'].append(f"Invalid JSON in manifest of {pack_dir.name}: {e}")
            validation['is_valid'] = False
        except Exception as e:
            validation['errors'].append(f"Error reading manifest of {pack_dir.name}: {e}")
            validation['is_valid'] = False
        
        # Check directory structure
        pack_config = self.required_structure.get(f'{pack_type}_packs', {})
        allowed_dirs = pack_config.get('allowed_dirs', [])
        
        for item in pack_dir.iterdir():
            if item.is_dir() and item.name not in allowed_dirs:
                validation['warnings'].append(
                    f"Unexpected directory '{item.name}' in {pack_type} pack {pack_dir.name}"
                )
        
        return validation
    
    def _create_mcaddon_file(self, temp_path: Path, output_path: Path):
        """Create the final .mcaddon ZIP file."""
        logger.info(f"Creating .mcaddon file: {output_path}")
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_path)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Successfully created .mcaddon file with {len(zipf.namelist())} files")
    
    def validate_mcaddon_file(self, mcaddon_path: Path) -> Dict[str, Any]:
        """
        Validate an existing .mcaddon file.
        
        Args:
            mcaddon_path: Path to .mcaddon file
            
        Returns:
            Validation results
        """
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'stats': {
                'file_count': 0,
                'compressed_size': 0,
                'uncompressed_size': 0,
                'behavior_packs': [],
                'resource_packs': []
            }
        }
        
        try:
            with zipfile.ZipFile(mcaddon_path, 'r') as zipf:
                # Basic ZIP validation
                try:
                    zipf.testzip()
                except Exception as e:
                    validation['errors'].append(f"Corrupted ZIP file: {e}")
                    validation['is_valid'] = False
                    return validation
                
                # Analyze contents
                namelist = zipf.namelist()
                validation['stats']['file_count'] = len(namelist)
                validation['stats']['compressed_size'] = mcaddon_path.stat().st_size
                
                # Check structure
                has_bp = any(name.startswith('behavior_packs/') for name in namelist)
                has_rp = any(name.startswith('resource_packs/') for name in namelist)
                
                if not has_bp and not has_rp:
                    validation['errors'].append("No behavior_packs or resource_packs found")
                    validation['is_valid'] = False
                
                # Find pack directories
                bp_packs = set()
                rp_packs = set()
                
                for name in namelist:
                    if name.startswith('behavior_packs/'):
                        parts = name.split('/')
                        if len(parts) > 1:
                            bp_packs.add(parts[1])
                    elif name.startswith('resource_packs/'):
                        parts = name.split('/')
                        if len(parts) > 1:
                            rp_packs.add(parts[1])
                
                validation['stats']['behavior_packs'] = list(bp_packs)
                validation['stats']['resource_packs'] = list(rp_packs)
                
                # Check for manifests
                manifest_count = sum(1 for name in namelist if name.endswith('manifest.json'))
                expected_manifests = len(bp_packs) + len(rp_packs)
                
                if manifest_count != expected_manifests:
                    validation['warnings'].append(
                        f"Expected {expected_manifests} manifests, found {manifest_count}"
                    )
                
        except zipfile.BadZipFile:
            validation['errors'].append("File is not a valid ZIP archive")
            validation['is_valid'] = False
        except Exception as e:
            validation['errors'].append(f"Error validating file: {e}")
            validation['is_valid'] = False
        
        return validation