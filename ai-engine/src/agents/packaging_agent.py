"""
Packaging Agent for assembling converted components into .mcaddon packages
"""

from typing import Dict, List, Any, Optional, Union

import logging
import json
import zipfile
import tempfile
import os
from pathlib import Path
from datetime import datetime
import uuid
from langchain.tools import tool
from ..models.smart_assumptions import (
    SmartAssumptionEngine, FeatureContext, ConversionPlanComponent
)

logger = logging.getLogger(__name__)


class PackagingAgent:
    """
    Packaging Agent responsible for assembling converted components into
    .mcaddon packages as specified in PRD Feature 2.
    """
    
    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        
        # Bedrock package structure templates
        self.manifest_template = {
            "format_version": 2,
            "header": {
                "name": "",
                "description": "",
                "uuid": "",
                "version": [1, 0, 0],
                "min_engine_version": [1, 19, 0]
            },
            "modules": []
        }
        
        # Required directories for different pack types
        self.pack_structures = {
            "behavior_pack": {
                "manifest.json": "manifest",
                "pack_icon.png": "icon",
                "scripts/": "scripts",
                "entities/": "entities", 
                "items/": "items",
                "blocks/": "blocks",
                "functions/": "functions",
                "loot_tables/": "loot_tables",
                "recipes/": "recipes",
                "spawn_rules/": "spawn_rules",
                "trading/": "trading"
            },
            "resource_pack": {
                "manifest.json": "manifest",
                "pack_icon.png": "icon",
                "textures/": "textures",
                "models/": "models",
                "sounds/": "sounds",
                "animations/": "animations",
                "animation_controllers/": "animation_controllers",
                "attachables/": "attachables",
                "entity/": "entity_textures",
                "font/": "fonts",
                "particles/": "particles"
            }
        }
        
        # File size and validation constraints
        self.package_constraints = {
            "max_total_size_mb": 500,  # Maximum package size
            "max_files": 1000,  # Maximum number of files
            "required_files": ["manifest.json"],
            "forbidden_extensions": [".exe", ".dll", ".bat", ".sh"],
            "max_manifest_size_kb": 10
        }
    
    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            self.analyze_conversion_components_tool,
            self.create_package_structure_tool,
            self.generate_manifests_tool,
            self.validate_package_tool,
            self.build_mcaddon_tool
        ]
    
    @tool
    def analyze_conversion_components_tool(self, component_data: str) -> str:
        """Analyze conversion components for packaging."""
        return self.analyze_conversion_components(component_data)
    
    @tool
    def create_package_structure_tool(self, structure_data: str) -> str:
        """Create package structure for Bedrock addon."""
        return self.create_package_structure(structure_data)
    
    @tool
    def generate_manifests_tool(self, manifest_data: str) -> str:
        """Generate manifest files for the addon."""
        return self.generate_manifests(manifest_data)
    
    @tool
    def validate_package_tool(self, validation_data: str) -> str:
        """Validate the package structure."""
        return self.validate_package(validation_data)
    
    @tool
    def build_mcaddon_tool(self, build_data: str) -> str:
        """Build the final mcaddon package."""
        return self.build_mcaddon(build_data)
    
    
    def analyze_conversion_components(self, components_data: str) -> str:
        """
        Analyze converted components to determine packaging strategy.
        
        Args:
            components_data: JSON string containing conversion results:
                           behavior_pack_components, resource_pack_components, metadata
        
        Returns:
            JSON string with packaging analysis and recommendations
        """
        try:
            data = json.loads(components_data)
            
            behavior_components = data.get('behavior_pack_components', [])
            resource_components = data.get('resource_pack_components', [])
            metadata = data.get('metadata', {})
            
            analysis = {
                'behavior_pack': self._analyze_pack_components(behavior_components, 'behavior_pack'),
                'resource_pack': self._analyze_pack_components(resource_components, 'resource_pack'),
                'package_strategy': {},
                'compatibility_requirements': {},
                'size_estimates': {}
            }
            
            # Determine packaging strategy
            strategy = self._determine_packaging_strategy(analysis, metadata)
            analysis['package_strategy'] = strategy
            
            # Analyze compatibility requirements
            compatibility = self._analyze_compatibility_requirements(behavior_components, resource_components)
            analysis['compatibility_requirements'] = compatibility
            
            # Estimate package sizes
            sizes = self._estimate_package_sizes(behavior_components, resource_components)
            analysis['size_estimates'] = sizes
            
            response = {
                "success": True,
                "analysis": analysis,
                "recommendations": self._generate_packaging_recommendations(analysis),
                "estimated_completion_time": self._estimate_packaging_time(analysis)
            }
            
            logger.info(f"Analyzed components for packaging: {len(behavior_components)} behavior, {len(resource_components)} resource")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to analyze components: {str(e)}"}
            logger.error(f"Component analysis error: {e}")
            return json.dumps(error_response)
    
    
    def create_package_structure(self, structure_data: str) -> str:
        """
        Create the directory structure for Bedrock packages.
        
        Args:
            structure_data: JSON string containing package configuration:
                          package_type, components, target_directory
        
        Returns:
            JSON string with created structure details
        """
        try:
            data = json.loads(structure_data)
            
            package_type = data.get('package_type', 'behavior_pack')  # or 'resource_pack'
            components = data.get('components', [])
            target_dir = data.get('target_directory', 'temp_package')
            
            # Create base directory structure
            structure = self._create_base_structure(package_type, target_dir)
            
            # Organize components into appropriate directories
            organized_components = self._organize_components(components, package_type, target_dir)
            
            # Validate structure
            validation = self._validate_structure(target_dir, package_type)
            
            response = {
                "success": True,
                "package_type": package_type,
                "target_directory": target_dir,
                "created_structure": structure,
                "organized_components": organized_components,
                "validation": validation
            }
            
            logger.info(f"Created {package_type} structure in {target_dir}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to create structure: {str(e)}"}
            logger.error(f"Structure creation error: {e}")
            return json.dumps(error_response)
    
    
    def generate_manifests(self, manifest_data: str) -> str:
        """
        Generate manifest.json files for Bedrock packages.
        
        Args:
            manifest_data: JSON string containing manifest configuration:
                         package_info, dependencies, capabilities
        
        Returns:
            JSON string with generated manifest details
        """
        try:
            data = json.loads(manifest_data)
            
            package_info = data.get('package_info', {})
            dependencies = data.get('dependencies', [])
            capabilities = data.get('capabilities', [])
            
            # Generate behavior pack manifest
            behavior_manifest = None
            if package_info.get('has_behavior_pack', False):
                behavior_manifest = self._generate_behavior_manifest(package_info, dependencies, capabilities)
            
            # Generate resource pack manifest
            resource_manifest = None
            if package_info.get('has_resource_pack', False):
                resource_manifest = self._generate_resource_manifest(package_info, dependencies)
            
            response = {
                "success": True,
                "behavior_manifest": behavior_manifest,
                "resource_manifest": resource_manifest,
                "manifest_validation": self._validate_manifests(behavior_manifest, resource_manifest)
            }
            
            logger.info("Generated package manifests")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to generate manifests: {str(e)}"}
            logger.error(f"Manifest generation error: {e}")
            return json.dumps(error_response)
    
    
    def validate_package(self, validation_data: str) -> str:
        """
        Validate a complete Bedrock package for compliance and quality.
        
        Args:
            validation_data: JSON string containing package paths and requirements
        
        Returns:
            JSON string with comprehensive validation results
        """
        try:
            data = json.loads(validation_data)
            
            package_paths = data.get('package_paths', [])
            requirements = data.get('requirements', {})
            
            validation_results = {
                'overall_valid': True,
                'package_validations': [],
                'critical_errors': [],
                'warnings': [],
                'quality_score': 0,
                'bedrock_compatibility': 'unknown'
            }
            
            for package_path in package_paths:
                package_validation = self._validate_single_package(package_path, requirements)
                validation_results['package_validations'].append(package_validation)
                
                if not package_validation['is_valid']:
                    validation_results['overall_valid'] = False
                
                validation_results['critical_errors'].extend(package_validation.get('critical_errors', []))
                validation_results['warnings'].extend(package_validation.get('warnings', []))
            
            # Calculate overall quality score
            quality_score = self._calculate_quality_score(validation_results)
            validation_results['quality_score'] = quality_score
            
            # Determine Bedrock compatibility
            compatibility = self._determine_bedrock_compatibility(validation_results)
            validation_results['bedrock_compatibility'] = compatibility
            
            response = {
                "success": True,
                "validation_results": validation_results,
                "recommendations": self._generate_validation_recommendations(validation_results)
            }
            
            logger.info(f"Validated {len(package_paths)} packages with quality score {quality_score}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to validate package: {str(e)}"}
            logger.error(f"Package validation error: {e}")
            return json.dumps(error_response)
    
    
    def build_mcaddon(self, build_data: str) -> str:
        """
        Build the final .mcaddon package from prepared components.
        
        Args:
            build_data: JSON string containing build configuration:
                       source_directories, output_path, metadata
        
        Returns:
            JSON string with build results and package information
        """
        try:
            data = json.loads(build_data)
            
            source_dirs = data.get('source_directories', [])
            output_path = data.get('output_path', 'output.mcaddon')
            metadata = data.get('metadata', {})
            
            # Pre-build validation
            pre_validation = self._pre_build_validation(source_dirs)
            if not pre_validation['valid']:
                return json.dumps({
                    "success": False,
                    "error": "Pre-build validation failed",
                    "validation_errors": pre_validation['errors']
                })
            
            # Build the .mcaddon file
            build_result = self._build_mcaddon_file(source_dirs, output_path, metadata)
            
            # Post-build validation
            post_validation = self._post_build_validation(output_path)
            
            response = {
                "success": build_result['success'],
                "output_path": output_path,
                "build_details": build_result,
                "post_validation": post_validation,
                "installation_instructions": self._generate_installation_instructions(output_path, metadata)
            }
            
            if build_result['success']:
                logger.info(f"Successfully built .mcaddon package: {output_path}")
            else:
                logger.error(f"Failed to build .mcaddon package: {build_result.get('error', 'Unknown error')}")
            
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to build mcaddon: {str(e)}"}
            logger.error(f"McAddon build error: {e}")
            return json.dumps(error_response)
    
    # Helper methods
    
    def _analyze_pack_components(self, components: List[Dict], pack_type: str) -> Dict:
        """Analyze components for a specific pack type"""
        analysis = {
            'total_components': len(components),
            'component_types': {},
            'size_estimate_mb': 0,
            'complexity': 'low',
            'special_requirements': []
        }
        
        for component in components:
            comp_type = component.get('type', 'unknown')
            analysis['component_types'][comp_type] = analysis['component_types'].get(comp_type, 0) + 1
            
            # Estimate size
            size_mb = component.get('estimated_size_mb', 0.1)
            analysis['size_estimate_mb'] += size_mb
            
            # Check for special requirements
            if component.get('requires_experimental', False):
                analysis['special_requirements'].append('experimental_features')
            
            if component.get('requires_scripting', False):
                analysis['special_requirements'].append('scripting_api')
        
        # Determine complexity
        if analysis['total_components'] > 50 or analysis['size_estimate_mb'] > 50:
            analysis['complexity'] = 'high'
        elif analysis['total_components'] > 20 or analysis['size_estimate_mb'] > 20:
            analysis['complexity'] = 'medium'
        
        return analysis
    
    def _determine_packaging_strategy(self, analysis: Dict, metadata: Dict) -> Dict:
        """Determine the best packaging strategy"""
        strategy = {
            'type': 'single_mcaddon',  # single_mcaddon, separate_packs, modular
            'reasoning': [],
            'pack_linking': False,
            'compression_level': 'standard'
        }
        
        behavior_size = analysis['behavior_pack']['size_estimate_mb']
        resource_size = analysis['resource_pack']['size_estimate_mb']
        total_size = behavior_size + resource_size
        
        # Determine if packs should be linked
        if behavior_size > 0 and resource_size > 0:
            strategy['pack_linking'] = True
            strategy['reasoning'].append("Both behavior and resource packs present - linking required")
        
        # Determine compression strategy
        if total_size > 100:
            strategy['compression_level'] = 'high'
            strategy['reasoning'].append("Large package size - using high compression")
        
        # Check if modular approach is needed
        if total_size > self.package_constraints['max_total_size_mb']:
            strategy['type'] = 'modular'
            strategy['reasoning'].append("Package too large - splitting into modules")
        
        return strategy
    
    def _analyze_compatibility_requirements(self, behavior_components: List[Dict], resource_components: List[Dict]) -> Dict:
        """Analyze compatibility requirements"""
        requirements = {
            'min_engine_version': [1, 19, 0],
            'experimental_features': [],
            'script_modules': [],
            'dependencies': []
        }
        
        all_components = behavior_components + resource_components
        
        for component in all_components:
            # Check engine version requirements
            min_version = component.get('min_engine_version', [1, 19, 0])
            if self._version_greater_than(min_version, requirements['min_engine_version']):
                requirements['min_engine_version'] = min_version
            
            # Check experimental features
            if component.get('requires_experimental'):
                exp_features = component.get('experimental_features', [])
                for feature in exp_features:
                    if feature not in requirements['experimental_features']:
                        requirements['experimental_features'].append(feature)
            
            # Check script modules
            if component.get('requires_scripting'):
                script_modules = component.get('script_modules', ['@minecraft/server'])
                for module in script_modules:
                    if module not in requirements['script_modules']:
                        requirements['script_modules'].append(module)
        
        return requirements
    
    def _estimate_package_sizes(self, behavior_components: List[Dict], resource_components: List[Dict]) -> Dict:
        """Estimate package sizes"""
        behavior_size = sum(comp.get('estimated_size_mb', 0.1) for comp in behavior_components)
        resource_size = sum(comp.get('estimated_size_mb', 0.1) for comp in resource_components)
        
        # Add overhead for manifests, structure, compression
        overhead = 0.5  # MB
        
        return {
            'behavior_pack_mb': round(behavior_size + overhead, 2),
            'resource_pack_mb': round(resource_size + overhead, 2),
            'total_uncompressed_mb': round(behavior_size + resource_size + (overhead * 2), 2),
            'estimated_compressed_mb': round((behavior_size + resource_size + (overhead * 2)) * 0.7, 2)  # ~30% compression
        }
    
    def _create_base_structure(self, package_type: str, target_dir: str) -> Dict:
        """Create base directory structure"""
        structure = self.pack_structures.get(package_type, {})
        created_dirs = []
        
        # Create target directory
        os.makedirs(target_dir, exist_ok=True)
        
        # Create subdirectories
        for path, description in structure.items():
            if path.endswith('/'):  # It's a directory
                dir_path = os.path.join(target_dir, path.rstrip('/'))
                os.makedirs(dir_path, exist_ok=True)
                created_dirs.append(dir_path)
        
        return {
            'package_type': package_type,
            'base_directory': target_dir,
            'created_directories': created_dirs,
            'structure_template': structure
        }
    
    def _organize_components(self, components: List[Dict], package_type: str, target_dir: str) -> Dict:
        """Organize components into appropriate directories"""
        organized = {
            'placed_files': [],
            'failed_placements': [],
            'directory_mapping': {}
        }
        
        for component in components:
            comp_type = component.get('type', 'unknown')
            source_path = component.get('path', '')
            
            # Determine target directory based on component type
            target_subdir = self._get_target_directory(comp_type, package_type)
            
            if target_subdir:
                target_path = os.path.join(target_dir, target_subdir, os.path.basename(source_path))
                organized['placed_files'].append({
                    'source': source_path,
                    'target': target_path,
                    'type': comp_type
                })
                organized['directory_mapping'][comp_type] = target_subdir
            else:
                organized['failed_placements'].append({
                    'source': source_path,
                    'type': comp_type,
                    'reason': f"No target directory mapping for {comp_type}"
                })
        
        return organized
    
    def _get_target_directory(self, component_type: str, package_type: str) -> Optional[str]:
        """Get target directory for a component type"""
        mappings = {
            'behavior_pack': {
                'entity': 'entities',
                'item': 'items',
                'block': 'blocks',
                'script': 'scripts',
                'function': 'functions',
                'loot_table': 'loot_tables',
                'recipe': 'recipes'
            },
            'resource_pack': {
                'texture': 'textures',
                'model': 'models',
                'sound': 'sounds',
                'animation': 'animations',
                'particle': 'particles'
            }
        }
        
        return mappings.get(package_type, {}).get(component_type)
    
    def _generate_behavior_manifest(self, package_info: Dict, dependencies: List[Dict], capabilities: List[str]) -> Dict:
        """Generate behavior pack manifest"""
        manifest = self.manifest_template.copy()
        
        manifest['header']['name'] = package_info.get('name', 'Converted Behavior Pack')
        manifest['header']['description'] = package_info.get('description', 'Converted from Java mod')
        manifest['header']['uuid'] = str(uuid.uuid4())
        manifest['header']['version'] = package_info.get('version', [1, 0, 0])
        
        # Add behavior pack module
        behavior_module = {
            "type": "data",
            "uuid": str(uuid.uuid4()),
            "version": package_info.get('version', [1, 0, 0])
        }
        manifest['modules'].append(behavior_module)
        
        # Add script module if needed
        if 'scripting' in capabilities:
            script_module = {
                "type": "script",
                "language": "javascript",
                "uuid": str(uuid.uuid4()),
                "version": package_info.get('version', [1, 0, 0]),
                "entry": "scripts/main.js"
            }
            manifest['modules'].append(script_module)
        
        # Add dependencies
        if dependencies:
            manifest['dependencies'] = dependencies
        
        # Add capabilities
        if capabilities:
            manifest['capabilities'] = capabilities
        
        return manifest
    
    def _generate_resource_manifest(self, package_info: Dict, dependencies: List[Dict]) -> Dict:
        """Generate resource pack manifest"""
        manifest = self.manifest_template.copy()
        
        manifest['header']['name'] = package_info.get('name', 'Converted Resource Pack')
        manifest['header']['description'] = package_info.get('description', 'Converted from Java mod')
        manifest['header']['uuid'] = str(uuid.uuid4())
        manifest['header']['version'] = package_info.get('version', [1, 0, 0])
        
        # Add resource pack module
        resource_module = {
            "type": "resources",
            "uuid": str(uuid.uuid4()),
            "version": package_info.get('version', [1, 0, 0])
        }
        manifest['modules'].append(resource_module)
        
        # Add dependencies
        if dependencies:
            manifest['dependencies'] = dependencies
        
        return manifest
    
    def _validate_single_package(self, package_path: str, requirements: Dict) -> Dict:
        """Validate a single package"""
        validation = {
            'path': package_path,
            'is_valid': True,
            'critical_errors': [],
            'warnings': [],
            'manifest_validation': {},
            'structure_validation': {},
            'size_validation': {}
        }
        
        # Check if manifest exists and is valid
        manifest_path = os.path.join(package_path, 'manifest.json')
        if os.path.exists(manifest_path):
            validation['manifest_validation'] = self._validate_manifest_file(manifest_path)
            if not validation['manifest_validation']['valid']:
                validation['is_valid'] = False
                validation['critical_errors'].extend(validation['manifest_validation']['errors'])
        else:
            validation['is_valid'] = False
            validation['critical_errors'].append("Missing manifest.json file")
        
        # Validate structure
        validation['structure_validation'] = self._validate_package_structure(package_path)
        
        # Validate size constraints
        validation['size_validation'] = self._validate_package_size(package_path)
        if not validation['size_validation']['within_limits']:
            validation['warnings'].append(f"Package size exceeds recommended limits")
        
        return validation
    
    def _build_mcaddon_file(self, source_dirs: List[str], output_path: str, metadata: Dict) -> Dict:
        """Build the actual .mcaddon file"""
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as mcaddon:
                total_files = 0
                
                for source_dir in source_dirs:
                    if not os.path.exists(source_dir):
                        continue
                    
                    # Get the pack name for the directory structure
                    pack_name = os.path.basename(source_dir.rstrip('/'))
                    
                    # Add all files from the source directory
                    for root, dirs, files in os.walk(source_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Calculate relative path from source_dir
                            rel_path = os.path.relpath(file_path, source_dir)
                            # Add to zip with pack name prefix
                            archive_path = os.path.join(pack_name, rel_path).replace('\\', '/')
                            mcaddon.write(file_path, archive_path)
                            total_files += 1
            
            # Get file size
            file_size = os.path.getsize(output_path)
            
            return {
                'success': True,
                'output_path': output_path,
                'total_files': total_files,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to create .mcaddon file: {str(e)}"
            }
    
    def _pre_build_validation(self, source_dirs: List[str]) -> Dict:
        """Validate before building"""
        validation = {'valid': True, 'errors': []}
        
        for source_dir in source_dirs:
            if not os.path.exists(source_dir):
                validation['valid'] = False
                validation['errors'].append(f"Source directory does not exist: {source_dir}")
            
            manifest_path = os.path.join(source_dir, 'manifest.json')
            if not os.path.exists(manifest_path):
                validation['valid'] = False
                validation['errors'].append(f"Missing manifest.json in {source_dir}")
        
        return validation
    
    def _post_build_validation(self, output_path: str) -> Dict:
        """Validate after building"""
        validation = {
            'file_exists': os.path.exists(output_path),
            'is_valid_zip': False,
            'contains_manifests': False,
            'file_size_ok': False
        }
        
        if validation['file_exists']:
            try:
                with zipfile.ZipFile(output_path, 'r') as mcaddon:
                    # Check if it's a valid zip
                    validation['is_valid_zip'] = True
                    
                    # Check for manifests
                    file_list = mcaddon.namelist()
                    manifests = [f for f in file_list if f.endswith('manifest.json')]
                    validation['contains_manifests'] = len(manifests) > 0
                    
                    # Check file size
                    file_size = os.path.getsize(output_path)
                    max_size = self.package_constraints['max_total_size_mb'] * 1024 * 1024
                    validation['file_size_ok'] = file_size <= max_size
                    
            except zipfile.BadZipFile:
                validation['is_valid_zip'] = False
        
        return validation
    
    def _generate_installation_instructions(self, output_path: str, metadata: Dict) -> List[str]:
        """Generate installation instructions for the user"""
        instructions = [
            f"Your converted add-on has been packaged as: {os.path.basename(output_path)}",
            "",
            "Installation Instructions:",
            "1. Locate the .mcaddon file on your device",
            "2. Double-click the file (or tap on mobile) to import",
            "3. Minecraft will automatically open and import the add-on",
            "4. Create a new world or edit an existing world",
            "5. In world settings, activate the behavior pack and resource pack",
            "6. Enable any required experimental features if prompted",
            "",
            "Troubleshooting:",
            "- Ensure you have the latest version of Minecraft Bedrock",
            "- Check that experimental features are enabled if required",
            "- Restart Minecraft if the add-on doesn't appear immediately"
        ]
        
        # Add specific requirements if any
        if metadata.get('requires_experimental'):
            instructions.extend([
                "",
                "⚠️  This add-on requires experimental features:",
                "- Enable 'Beta APIs' in world settings",
                "- Enable any other experimental toggles as prompted"
            ])
        
        return instructions
    
    # Additional helper methods for validation and analysis
    
    def _version_greater_than(self, version1: List[int], version2: List[int]) -> bool:
        """Check if version1 is greater than version2"""
        for i in range(min(len(version1), len(version2))):
            if version1[i] > version2[i]:
                return True
            elif version1[i] < version2[i]:
                return False
        return len(version1) > len(version2)
    
    def _validate_manifests(self, behavior_manifest: Optional[Dict], resource_manifest: Optional[Dict]) -> Dict:
        """Validate generated manifests"""
        validation = {'valid': True, 'errors': []}
        
        for manifest, name in [(behavior_manifest, 'behavior'), (resource_manifest, 'resource')]:
            if manifest:
                if not manifest.get('header', {}).get('uuid'):
                    validation['valid'] = False
                    validation['errors'].append(f"{name} manifest missing UUID")
                
                if not manifest.get('modules'):
                    validation['valid'] = False
                    validation['errors'].append(f"{name} manifest missing modules")
        
        return validation
    
    def _validate_manifest_file(self, manifest_path: str) -> Dict:
        """Validate a manifest.json file"""
        validation = {'valid': True, 'errors': []}
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Check required fields
            if not manifest.get('format_version'):
                validation['errors'].append("Missing format_version")
            
            header = manifest.get('header', {})
            if not header.get('uuid'):
                validation['errors'].append("Missing header UUID")
            
            if not manifest.get('modules'):
                validation['errors'].append("Missing modules")
            
            if validation['errors']:
                validation['valid'] = False
                
        except json.JSONDecodeError:
            validation['valid'] = False
            validation['errors'].append("Invalid JSON format")
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"Error reading manifest: {str(e)}")
        
        return validation
    
    def _validate_package_structure(self, package_path: str) -> Dict:
        """Validate package directory structure"""
        validation = {'valid': True, 'missing_dirs': [], 'extra_files': []}
        
        # This is a simplified validation - real implementation would be more thorough
        required_files = ['manifest.json']
        
        for required_file in required_files:
            file_path = os.path.join(package_path, required_file)
            if not os.path.exists(file_path):
                validation['valid'] = False
                validation['missing_dirs'].append(required_file)
        
        return validation
    
    def _validate_package_size(self, package_path: str) -> Dict:
        """Validate package size constraints"""
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(package_path):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
                file_count += 1
        
        max_size = self.package_constraints['max_total_size_mb'] * 1024 * 1024
        max_files = self.package_constraints['max_files']
        
        return {
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'file_count': file_count,
            'within_size_limit': total_size <= max_size,
            'within_file_limit': file_count <= max_files,
            'within_limits': total_size <= max_size and file_count <= max_files
        }
    
    def _calculate_quality_score(self, validation_results: Dict) -> float:
        """Calculate overall quality score (0-100)"""
        base_score = 100.0
        
        # Deduct for critical errors
        critical_errors = len(validation_results.get('critical_errors', []))
        base_score -= critical_errors * 20  # -20 points per critical error
        
        # Deduct for warnings
        warnings = len(validation_results.get('warnings', []))
        base_score -= warnings * 5  # -5 points per warning
        
        # Deduct if not overall valid
        if not validation_results.get('overall_valid', True):
            base_score -= 25  # -25 points for invalid package
        
        return max(0.0, min(100.0, base_score))
    
    def _determine_bedrock_compatibility(self, validation_results: Dict) -> str:
        """Determine Bedrock compatibility level"""
        if not validation_results.get('overall_valid', False):
            return 'incompatible'
        
        critical_errors = len(validation_results.get('critical_errors', []))
        warnings = len(validation_results.get('warnings', []))
        
        if critical_errors == 0 and warnings == 0:
            return 'fully_compatible'
        elif critical_errors == 0 and warnings <= 3:
            return 'mostly_compatible'
        elif critical_errors <= 2:
            return 'partially_compatible'
        else:
            return 'limited_compatibility'
    
    def _generate_packaging_recommendations(self, analysis: Dict) -> List[str]:
        """Generate packaging recommendations"""
        recommendations = []
        
        strategy = analysis.get('package_strategy', {})
        if strategy.get('type') == 'modular':
            recommendations.append("Consider splitting into multiple smaller add-ons for better performance")
        
        size_estimates = analysis.get('size_estimates', {})
        total_size = size_estimates.get('total_uncompressed_mb', 0)
        if total_size > 100:
            recommendations.append("Large package size detected - consider optimizing assets")
        
        compatibility = analysis.get('compatibility_requirements', {})
        if compatibility.get('experimental_features'):
            recommendations.append("Package requires experimental features - document for users")
        
        return recommendations
    
    def _generate_validation_recommendations(self, validation_results: Dict) -> List[str]:
        """Generate validation-based recommendations"""
        recommendations = []
        
        if validation_results.get('critical_errors'):
            recommendations.append("Fix critical errors before distribution")
        
        quality_score = validation_results.get('quality_score', 0)
        if quality_score < 80:
            recommendations.append("Improve package quality before release")
        
        compatibility = validation_results.get('bedrock_compatibility', 'unknown')
        if compatibility in ['limited_compatibility', 'partially_compatible']:
            recommendations.append("Address compatibility issues for better user experience")
        
        return recommendations
    
    def _estimate_packaging_time(self, analysis: Dict) -> str:
        """Estimate time needed for packaging"""
        total_components = (analysis['behavior_pack']['total_components'] + 
                          analysis['resource_pack']['total_components'])
        
        if total_components < 10:
            return "< 1 minute"
        elif total_components < 50:
            return "1-5 minutes"
        else:
            return "5-15 minutes"
