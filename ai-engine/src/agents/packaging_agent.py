"""
Packaging Agent for assembling converted components into .mcaddon packages
"""

from typing import Dict, List, Any, Optional, Union

import logging
import json
import zipfile
import tempfile
import os
import copy
from pathlib import Path
from datetime import datetime
import uuid
from langchain.tools import tool
from src.models.smart_assumptions import (
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
                "required": {
                    "manifest.json": "manifest"
                },
                "optional": {
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
                }
            },
            "resource_pack": {
                "required": {
                    "manifest.json": "manifest"
                },
                "optional": {
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
            base_structure_details = self._create_base_structure(package_type, target_dir)
            
            # Organize components into appropriate directories
            # This assumes 'components' is a list of file paths or objects with 'path' and 'type'
            # For now, we'll focus on creating the structure. File placement will be enhanced later.
            organized_components_details = self._organize_components(components, package_type, target_dir)
            
            # Validate created structure (basic validation for now)
            structure_validation_results = self._validate_pack_structure_directories(target_dir, package_type)
            
            response = {
                "success": True,
                "package_type": package_type,
                "target_directory": target_dir,
                "base_structure_created": base_structure_details,
                "components_organization_attempted": organized_components_details,
                "structure_validation": structure_validation_results
            }
            
            logger.info(f"Created {package_type} structure in {target_dir}. Validation: {structure_validation_results}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to create structure: {str(e)}"}
            logger.error(f"Structure creation error: {e}", exc_info=True)
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
            behavior_manifest_content = None
            if package_info.get('has_behavior_pack', True): # Default to true if not specified
                behavior_manifest_content = self._generate_behavior_manifest(package_info, dependencies, capabilities)
            
            # Generate resource pack manifest
            resource_manifest_content = None
            if package_info.get('has_resource_pack', True): # Default to true if not specified
                resource_manifest_content = self._generate_resource_manifest(package_info, dependencies)
            
            # Determine output directory - use a temporary one if not provided
            output_dir_base = package_info.get('output_directory', tempfile.mkdtemp(prefix="modporter_manifests_"))

            bp_manifest_path = None
            rp_manifest_path = None

            if behavior_manifest_content:
                bp_dir = Path(output_dir_base) / "behavior_pack"
                bp_dir.mkdir(parents=True, exist_ok=True)
                bp_manifest_path = bp_dir / "manifest.json"
                with open(bp_manifest_path, 'w') as f:
                    json.dump(behavior_manifest_content, f, indent=2)
                logger.info(f"Behavior pack manifest generated at: {bp_manifest_path}")

            if resource_manifest_content:
                rp_dir = Path(output_dir_base) / "resource_pack"
                rp_dir.mkdir(parents=True, exist_ok=True)
                rp_manifest_path = rp_dir / "manifest.json"
                with open(rp_manifest_path, 'w') as f:
                    json.dump(resource_manifest_content, f, indent=2)
                logger.info(f"Resource pack manifest generated at: {rp_manifest_path}")

            response = {
                "success": True,
                "behavior_manifest_path": str(bp_manifest_path) if bp_manifest_path else None,
                "resource_manifest_path": str(rp_manifest_path) if rp_manifest_path else None,
                "behavior_manifest_content": behavior_manifest_content,
                "resource_manifest_content": resource_manifest_content,
                "manifest_validation": self._validate_manifests(behavior_manifest_content, resource_manifest_content)
            }
            
            logger.info("Generated package manifests")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to generate manifests: {str(e)}"}
            logger.error(f"Manifest generation error: {e}", exc_info=True)
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
                logger.error(f"Pre-build validation failed: {pre_validation['errors']}")
                return json.dumps({
                    "success": False,
                    "error": "Pre-build validation failed",
                    "validation_errors": pre_validation['errors']
                })
            
            # Ensure output_path directory exists
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # Build the .mcaddon file
            build_result = self._build_mcaddon_file(source_dirs, output_path, metadata)
            
            # Post-build validation
            post_validation = self._post_build_validation(output_path)
            
            response = {
                "success": build_result['success'],
                "output_path": str(Path(output_path).resolve()) if build_result['success'] else None,
                "build_details": build_result,
                "post_validation": post_validation,
                "installation_instructions": self._generate_installation_instructions(output_path, metadata) if build_result['success'] else []
            }
            
            if build_result['success']:
                logger.info(f"Successfully built .mcaddon package: {output_path}")
            else:
                logger.error(f"Failed to build .mcaddon package: {build_result.get('error', 'Unknown error')}")
            
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to build mcaddon: {str(e)}"}
            logger.error(f"McAddon build error: {e}", exc_info=True)
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
        structure_template = self.pack_structures.get(package_type, {})
        created_dirs = []
        
        # Create target directory
        os.makedirs(target_dir, exist_ok=True)
        
        # Create subdirectories from both required and optional sections
        all_dirs = {}
        all_dirs.update(structure_template.get('required', {}))
        all_dirs.update(structure_template.get('optional', {}))
        
        for path, description in all_dirs.items():
            if path.endswith('/'):  # It's a directory
                dir_path = os.path.join(target_dir, path.rstrip('/'))
                os.makedirs(dir_path, exist_ok=True)
                created_dirs.append(dir_path)
        
        return {
            'package_type': package_type,
            'base_directory': target_dir,
            'created_directories': created_dirs,
            'structure_template': structure_template
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
        """Get target directory for a component type based on self.pack_structures."""
        pack_specific_structure = self.pack_structures.get(package_type)
        if not pack_specific_structure:
            logger.warning(f"No structure definition found for package_type: {package_type}")
            return None

        # Find the directory key associated with this component type
        # This requires a reverse mapping or a more structured component_type to directory mapping
        # For now, we'll assume component_type directly matches a key in pack_structures (e.g., "entities", "textures")
        # or we have a predefined mapping.

        # Simplified: if component_type is 'entities', it maps to 'entities/'
        # This needs to be more robust.
        # Example: component_type 'block_definition' -> 'blocks/'
        # component_type 'texture_png' -> 'textures/'

        # Let's refine the mapping logic.
        # Assuming component_type is something like 'block', 'item', 'texture', 'model'
        # And pack_structures keys are like 'blocks/', 'items/', 'textures/', 'models/'

        # A more direct mapping from internal component types to directory keys:
        type_to_dir_key_map = {
            'behavior_pack': {
                'entity_definition': 'entities/',
                'item_definition': 'items/',
                'block_definition': 'blocks/',
                'script': 'scripts/', # Assuming script files are directly placed here
                'function_mcfunction': 'functions/',
                'loot_table_json': 'loot_tables/',
                'recipe_json': 'recipes/',
                'spawn_rule_json': 'spawn_rules/',
                'trading_json': 'trading/',
                'pack_icon': 'pack_icon.png' # Special case for file
            },
            'resource_pack': {
                'texture_png': 'textures/',
                'model_geo_json': 'models/', # or just 'models/' if geo.json is implied
                'sound_ogg': 'sounds/', # or 'sounds/'
                'animation_json': 'animations/',
                'animation_controller_json': 'animation_controllers/',
                'attachable_json': 'attachables/',
                'entity_texture_json': 'entity/', # Bedrock entity texture definitions
                'font_ttf_otf': 'font/',
                'particle_json': 'particles/',
                'pack_icon': 'pack_icon.png' # Special case for file
            }
        }

        package_map = type_to_dir_key_map.get(package_type)
        if not package_map:
            logger.warning(f"No component type to directory map for package_type: {package_type}")
            return None

        dir_key_or_filename = package_map.get(component_type)
        if not dir_key_or_filename:
            logger.warning(f"No directory key found for component_type '{component_type}' in package_type '{package_type}'")
            return None

        # If it's a filename like pack_icon.png, the target subdir is the root of the pack.
        if not dir_key_or_filename.endswith('/'):
            return "" # Place in root of the pack

        return dir_key_or_filename.rstrip('/')


    def _validate_pack_structure_directories(self, base_path: str, package_type: str) -> Dict:
        """
        Validates if the essential directories for a given package_type exist.
        Args:
            base_path: The root directory of the pack (e.g., temp_package/behavior_pack).
            package_type: 'behavior_pack' or 'resource_pack'.
        Returns:
            A dictionary with validation status and list of missing/found directories.
        """
        validation_results = {
            "valid": True,
            "message": "All essential directories found.",
            "checked_path": base_path,
            "package_type": package_type,
            "required_directories_found": [],
            "required_directories_missing": []
        }
        
        pack_structure_template = self.pack_structures.get(package_type)
        if not pack_structure_template:
            validation_results["valid"] = False
            validation_results["message"] = f"No structure template found for package type: {package_type}"
            return validation_results

        # Only check required directories for validation
        required_structure = pack_structure_template.get('required', {})
        essential_dirs = [dir_key.rstrip('/') for dir_key in required_structure if dir_key.endswith('/')]

        if not os.path.exists(base_path):
            validation_results["valid"] = False
            validation_results["message"] = f"Base path does not exist: {base_path}"
            # All essential dirs will be missing if base path is gone
            validation_results["required_directories_missing"] = essential_dirs
            return validation_results

        for dir_name in essential_dirs:
            dir_to_check = Path(base_path) / dir_name
            if dir_to_check.exists() and dir_to_check.is_dir():
                validation_results["required_directories_found"].append(dir_name)
            else:
                validation_results["valid"] = False
                validation_results["required_directories_missing"].append(dir_name)

        if not validation_results["valid"]:
            validation_results["message"] = f"Missing essential directories: {validation_results['required_directories_missing']}"

        return validation_results

    def _generate_behavior_manifest(self, package_info: Dict, dependencies: List[Dict], capabilities: List[str]) -> Dict:
        """Generate behavior pack manifest"""
        manifest = copy.deepcopy(self.manifest_template)
        
        manifest['header']['name'] = package_info.get('name', 'My Converted Behavior Pack')
        manifest['header']['description'] = package_info.get('description', 'A behavior pack converted from a Java mod by ModPorter AI')
        manifest['header']['uuid'] = package_info.get('header_uuid', str(uuid.uuid4())) # Allow overriding for testing
        manifest['header']['version'] = package_info.get('version', [0, 0, 1])
        manifest['header']['min_engine_version'] = package_info.get('min_engine_version', [1, 20, 0]) # Updated default
        
        # Add behavior pack module
        behavior_module_uuid = package_info.get('module_uuid_behavior', str(uuid.uuid4()))
        behavior_module = {
            "description": "Behavior pack module",
            "type": "data",
            "uuid": behavior_module_uuid,
            "version": package_info.get('version', [0, 0, 1])
        }
        manifest['modules'].append(behavior_module)
        
        # Add script module if needed
        if 'scripting' in capabilities or package_info.get('enable_scripting', False):
            script_module_uuid = package_info.get('module_uuid_script', str(uuid.uuid4()))
            script_module_entry = package_info.get('script_entry', 'scripts/main.js')
            script_module = {
                "description": "Scripting module",
                "type": "script",
                "language": "javascript",
                "uuid": script_module_uuid,
                "version": package_info.get('script_version', [0, 0, 1]), # Allow different script version
                "entry": script_module_entry
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
        manifest = copy.deepcopy(self.manifest_template)
        
        manifest['header']['name'] = package_info.get('name', 'My Converted Resource Pack')
        manifest['header']['description'] = package_info.get('description', 'A resource pack converted from a Java mod by ModPorter AI')
        manifest['header']['uuid'] = package_info.get('header_uuid_resource', str(uuid.uuid4())) # Allow overriding for testing
        manifest['header']['version'] = package_info.get('version', [0, 0, 1])
        manifest['header']['min_engine_version'] = package_info.get('min_engine_version', [1, 20, 0]) # Updated default
        
        # Add resource pack module
        resource_module_uuid = package_info.get('module_uuid_resource', str(uuid.uuid4()))
        resource_module = {
            "description": "Resource pack module",
            "type": "resources",
            "uuid": resource_module_uuid,
            "version": package_info.get('version', [0, 0, 1])
        }
        manifest['modules'].append(resource_module)
        
        # Add dependencies
        # Example: if resource pack depends on behavior pack for custom blocks/items
        # This might be automatically added if a behavior pack is also generated
        # and they share a common 'mod_id' or similar identifier.
        # For now, explicit dependencies passed in `dependencies` are handled.
        if dependencies:
            manifest['dependencies'] = dependencies
        
        return manifest
    
    def _validate_single_package(self, package_path: str, requirements: Dict) -> Dict:
        """Validate a single package"""
        validation = {
            'path': package_path,
            'is_valid': True, # Overall validity of this specific pack
            'critical_errors': [], # Errors that make the pack unusable
            'warnings': [], # Issues that might not break but are problematic
            'info': [], # General information or suggestions
            'manifest_validation': {'valid': False, 'errors': [], 'details': {}},
            'structure_validation': {'valid': False, 'missing': [], 'unexpected': []},
            'size_validation': {'valid': True, 'details': {}},
            'file_content_validation': {'passed': True, 'issues': []} # New category
        }

        pack_type_guess = self._detect_pack_type_from_manifest(package_path)
        
        # 1. Manifest Validation
        manifest_path = Path(package_path) / 'manifest.json'
        if manifest_path.exists():
            validation['manifest_validation'] = self._validate_manifest_file(str(manifest_path))
            if not validation['manifest_validation']['valid']:
                validation['is_valid'] = False
                validation['critical_errors'].extend(validation['manifest_validation']['errors'])
        else:
            validation['is_valid'] = False
            validation['critical_errors'].append(f"Missing manifest.json in {package_path}")
            validation['manifest_validation']['errors'].append("Missing manifest.json")

        # 2. Structure Validation (Essential Directories)
        # Using the previously created _validate_pack_structure_directories
        # This needs the pack_type, which we infer or should get from context
        structure_val_results = self._validate_pack_structure_directories(package_path, pack_type_guess)
        validation['structure_validation']['valid'] = structure_val_results['valid']
        if not structure_val_results['valid']:
            # For single pack validation, missing directories might be warnings or errors depending on strictness
            # For now, let's treat them as warnings if manifest is okay, errors otherwise.
            if validation['is_valid']: # If manifest was okay, these are warnings
                 validation['warnings'].extend([f"Missing directory: {d}" for d in structure_val_results['required_directories_missing']])
            else: # If manifest also bad, these contribute to critical errors
                 validation['critical_errors'].extend([f"Missing directory: {d}" for d in structure_val_results['required_directories_missing']])
            validation['structure_validation']['missing'] = structure_val_results['required_directories_missing']

        # 3. Size Validation
        size_val_results = self._validate_package_size(package_path)
        validation['size_validation']['details'] = size_val_results
        if not size_val_results['within_size_limit']:
            validation['warnings'].append(f"Package total size ({size_val_results['total_size_mb']}MB) exceeds limit ({self.package_constraints['max_total_size_mb']}MB)")
            # This could be a critical error if significantly over
        if not size_val_results['within_file_limit']:
            validation['warnings'].append(f"Package file count ({size_val_results['file_count']}) exceeds limit ({self.package_constraints['max_files']})")

        # 4. Forbidden File Types / Basic Content Sanity
        forbidden_files_found = []
        for root, _, files in os.walk(package_path):
            for file_name in files:
                file_ext = Path(file_name).suffix.lower()
                if file_ext in self.package_constraints['forbidden_extensions']:
                    forbidden_files_found.append(os.path.join(root, file_name))

        if forbidden_files_found:
            validation['is_valid'] = False # Forbidden files are critical
            validation['critical_errors'].extend([f"Forbidden file type found: {f}" for f in forbidden_files_found])
            validation['file_content_validation']['passed'] = False
            validation['file_content_validation']['issues'].extend([f"Forbidden file type: {f}" for f in forbidden_files_found])

        # Update overall validity based on critical errors
        if validation['critical_errors']:
            validation['is_valid'] = False

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
                'error': f"Failed to create .mcaddon file: {str(e)}",
                'exception_type': type(e).__name__
            }
        except zipfile.BadZipFile as bze:
            logger.error(f"Bad .mcaddon zip file during build: {output_path}, error: {bze}", exc_info=True)
            return {
                'success': False,
                'error': f"Generated .mcaddon file is invalid/corrupt: {str(bze)}",
                'exception_type': type(bze).__name__
            }
        except OSError as ose: # Catch broader I/O errors
            logger.error(f"OS error during .mcaddon build for {output_path}: {ose}", exc_info=True)
            return {
                'success': False,
                'error': f"OS error during .mcaddon file creation: {str(ose)}",
                'exception_type': type(ose).__name__
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
    
    def generate_manifest(self, mod_info: str, pack_type: str = "both") -> str:
        """
        Generate manifest(s) for Bedrock addon packages.
        
        Args:
            mod_info: JSON string containing mod information
            pack_type: Type of pack ("resource", "behavior", "both")
        
        Returns:
            JSON string with generated manifest(s)
        """
        try:
            # Create manifest data structure that matches existing implementation
            manifest_data = {
                "mod_info": json.loads(mod_info),
                "pack_type": pack_type,
                "generation_options": {
                    "include_icons": True,
                    "include_dependencies": True
                }
            }
            
            # Use existing manifest generation method
            result_json = self.generate_manifests(json.dumps(manifest_data))
            result = json.loads(result_json)
            
            # For integration tests, return a direct manifest structure
            if result.get("success"):
                # Extract the actual manifest content or create a basic one
                mod_data = json.loads(mod_info)
                manifest = {
                    "format_version": 2,
                    "header": {
                        "description": mod_data.get("name", "Converted Mod"),
                        "name": mod_data.get("name", "Converted Mod"),
                        "uuid": str(uuid.uuid4()),
                        "version": [int(x) for x in mod_data.get("version", "1.0.0").split(".")]
                    },
                    "modules": []
                }
                
                # Add modules based on pack type
                if pack_type in ["resource", "both"]:
                    manifest["modules"].append({
                        "description": "Resource Pack Module",
                        "type": "resources", 
                        "uuid": str(uuid.uuid4()),
                        "version": [int(x) for x in mod_data.get("version", "1.0.0").split(".")]
                    })
                    
                if pack_type in ["behavior", "both"]:
                    manifest["modules"].append({
                        "description": "Behavior Pack Module",
                        "type": "data",
                        "uuid": str(uuid.uuid4()),
                        "version": [int(x) for x in mod_data.get("version", "1.0.0").split(".")]
                    })
                
                return json.dumps(manifest, indent=2)
            else:
                return result_json
            
        except Exception as e:
            logger.error(f"Error in generate_manifest: {str(e)}")
            return json.dumps({
                "success": False,
                "format_version": 2,
                "header": {},
                "modules": [],
                "error": str(e)
            })

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
        """Validate a manifest.json file for structure and required fields."""
        validation = {'valid': True, 'errors': [], 'warnings': [], 'details': {}}
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            validation['details']['content'] = manifest # Store parsed manifest for further inspection if needed

            # 1. Check format_version (must be 2 for most modern packs)
            format_version = manifest.get('format_version')
            if format_version != 2:
                validation['errors'].append(f"Invalid or missing 'format_version'. Expected 2, got {format_version}.")
            
            # 2. Check header section
            header = manifest.get('header')
            if not isinstance(header, dict):
                validation['errors'].append("Missing or invalid 'header' section.")
            else:
                for field in ['name', 'description', 'uuid', 'version', 'min_engine_version']:
                    if not header.get(field):
                        validation['errors'].append(f"Missing '{field}' in manifest header.")
                if not self._is_valid_uuid(header.get('uuid')):
                    validation['errors'].append(f"Invalid UUID format in header: {header.get('uuid')}.")
                if not isinstance(header.get('version'), list) or len(header.get('version')) != 3:
                    validation['warnings'].append(f"Header 'version' should be an array of 3 numbers (e.g., [1, 0, 0]). Found: {header.get('version')}")
                if not isinstance(header.get('min_engine_version'), list) or len(header.get('min_engine_version')) != 3:
                     validation['warnings'].append(f"Header 'min_engine_version' should be an array of 3 numbers. Found: {header.get('min_engine_version')}")


            # 3. Check modules section
            modules = manifest.get('modules')
            if not isinstance(modules, list) or not modules:
                validation['errors'].append("Missing or empty 'modules' section. At least one module is required.")
            else:
                for i, module in enumerate(modules):
                    if not isinstance(module, dict):
                        validation['errors'].append(f"Module at index {i} is not a valid object.")
                        continue
                    for field in ['type', 'uuid', 'version']:
                        if not module.get(field):
                            validation['errors'].append(f"Missing '{field}' in module at index {i}.")
                    if not self._is_valid_uuid(module.get('uuid')):
                        validation['errors'].append(f"Invalid UUID format in module at index {i}: {module.get('uuid')}.")
                    if not isinstance(module.get('version'), list) or len(module.get('version')) != 3:
                         validation['warnings'].append(f"Module 'version' at index {i} should be an array of 3 numbers. Found: {module.get('version')}")

                    # Check for script module entry point if type is script
                    if module.get('type') == 'script':
                        entry_point = module.get('entry')
                        if not entry_point or not isinstance(entry_point, str):
                             validation['errors'].append(f"Script module at index {i} missing or invalid 'entry' point.")
                        else:
                            # Check if entry script actually exists (relative to manifest_path's parent)
                            script_file_path = Path(manifest_path).parent / entry_point
                            if not script_file_path.is_file():
                                validation['errors'].append(f"Script entry point '{entry_point}' defined in manifest module {i} does not exist at {script_file_path}.")


            # 4. Check dependencies section (if present)
            dependencies = manifest.get('dependencies')
            if dependencies is not None: # It's an optional field
                if not isinstance(dependencies, list):
                    validation['errors'].append("'dependencies' section, if present, must be a list.")
                else:
                    for i, dep in enumerate(dependencies):
                        if not isinstance(dep, dict):
                            validation['errors'].append(f"Dependency at index {i} is not a valid object.")
                            continue
                        # Common dependency fields: uuid or module_id, version
                        if not dep.get('uuid') and not dep.get('module_id'): # Bedrock often uses 'uuid' for pack dependencies
                            validation['errors'].append(f"Dependency at index {i} missing 'uuid' or 'module_id'.")
                        if dep.get('uuid') and not self._is_valid_uuid(dep.get('uuid')):
                             validation['errors'].append(f"Invalid UUID in dependency at index {i}: {dep.get('uuid')}")
                        if not isinstance(dep.get('version'), list) or len(dep.get('version')) != 3 :
                            validation['warnings'].append(f"Dependency 'version' at index {i} should be an array of 3 numbers. Found: {dep.get('version')}")
            
            # Max size check
            manifest_size_kb = Path(manifest_path).stat().st_size / 1024
            if manifest_size_kb > self.package_constraints['max_manifest_size_kb']:
                validation['warnings'].append(f"Manifest size ({manifest_size_kb:.2f}KB) exceeds recommended limit ({self.package_constraints['max_manifest_size_kb']}KB).")


            if validation['errors']:
                validation['valid'] = False
                
        except json.JSONDecodeError as e:
            validation['valid'] = False
            validation['errors'].append(f"Invalid JSON format in manifest: {str(e)}")
        except FileNotFoundError:
            validation['valid'] = False
            validation['errors'].append("Manifest file not found (should not happen if called by _validate_single_package).")
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"Error reading or parsing manifest: {str(e)}")
        
        return validation
    
    def _is_valid_uuid(self, uuid_string: Optional[str]) -> bool:
        """Helper to validate UUID format."""
        if not uuid_string:
            return False
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False

    def _validate_package_structure(self, package_path: str, pack_type: str) -> Dict:
        """
        Validate overall package structure beyond just directory existence.
        Checks for unexpected files/folders at the root, specific required files like pack_icon.png.
        Args:
            package_path: Path to the root of the behavior or resource pack.
            pack_type: 'behavior_pack' or 'resource_pack'.
        Returns:
            Dict with validation results.
        """
        validation = {'valid': True, 'errors': [], 'warnings': [], 'missing_required_files': [], 'unexpected_root_items': []}

        root_items = [item.name for item in Path(package_path).iterdir()]
        
        # Get all defined structure keys from both required and optional sections
        pack_template = self.pack_structures.get(pack_type, {})
        all_structure_items = {}
        all_structure_items.update(pack_template.get('required', {}))
        all_structure_items.update(pack_template.get('optional', {}))
        defined_structure_keys = [key.rstrip('/') for key in all_structure_items.keys()]

        # Check for unexpected items at the root
        for item_name in root_items:
            if item_name not in defined_structure_keys and item_name != 'manifest.json': # manifest.json is expected
                # Allow common non-essential files like README.md, LICENSE, etc.
                if item_name.lower() not in ['readme.md', 'license', 'changelog.md', '.ds_store', 'pack_icon.png']: # pack_icon is checked separately
                    validation['warnings'].append(f"Unexpected file or folder at pack root: {item_name}")
                    validation['unexpected_root_items'].append(item_name)

        # Check for pack_icon.png (conditionally required, but good practice)
        pack_icon_path = Path(package_path) / 'pack_icon.png'
        # Check if pack_icon.png is defined in either required or optional sections
        pack_template = self.pack_structures.get(pack_type, {})
        has_pack_icon_defined = ('pack_icon.png' in pack_template.get('required', {}) or 
                                'pack_icon.png' in pack_template.get('optional', {}))
        
        if has_pack_icon_defined:
            if not pack_icon_path.is_file():
                validation['warnings'].append("Missing pack_icon.png at the root of the pack.")
                validation['missing_required_files'].append('pack_icon.png')
            else:
                # Optional: basic validation of pack_icon.png (e.g., is it a valid PNG, dimensions)
                pass
        
        # Further checks can be added here, e.g., ensuring only valid subfolders exist
        # or that specific files are in correct locations if a full file map is available.

        if validation['errors']: # Currently only populating warnings, but if errors are added
            validation['valid'] = False

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
    
    def _detect_pack_type_from_manifest(self, package_path: str) -> str:
        """
        Detect pack type by analyzing the manifest.json content instead of relying on directory name.
        
        Args:
            package_path: Path to the pack directory
            
        Returns:
            'behavior_pack' or 'resource_pack', defaults to 'behavior_pack' if cannot determine
        """
        try:
            manifest_path = Path(package_path) / 'manifest.json'
            if not manifest_path.exists():
                # No manifest - fall back to directory name heuristic
                return "behavior_pack" if "behavior" in Path(package_path).name.lower() else "resource_pack"
            
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            # Check modules to determine pack type
            modules = manifest.get('modules', [])
            for module in modules:
                module_type = module.get('type', '')
                if module_type == 'resources':
                    return "resource_pack"
                elif module_type in ['data', 'script']:
                    return "behavior_pack"
            
            # If no clear indication from modules, fall back to directory name
            return "behavior_pack" if "behavior" in Path(package_path).name.lower() else "resource_pack"
            
        except (json.JSONDecodeError, IOError, KeyError) as e:
            logger.warning(f"Could not detect pack type from manifest in {package_path}: {e}")
            # Fall back to directory name heuristic
            return "behavior_pack" if "behavior" in Path(package_path).name.lower() else "resource_pack"
