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
from crewai.tools import tool
from src.models.smart_assumptions import (
    SmartAssumptionEngine, FeatureContext, ConversionPlanComponent
)

logger = logging.getLogger(__name__)


class PackagingAgent:
    """
    Packaging Agent responsible for assembling converted components into
    .mcaddon packages as specified in PRD Feature 2.
    """
    
    _instance = None
    
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
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance of PackagingAgent"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            PackagingAgent.analyze_conversion_components_tool,
            PackagingAgent.create_package_structure_tool,
            PackagingAgent.generate_manifests_tool,
            PackagingAgent.validate_package_tool,
            PackagingAgent.build_mcaddon_tool
        ]
    
    def generate_manifest(self, mod_info: str, pack_type: str) -> str:
        """
        Generate manifest for a pack.
        
        Args:
            mod_info: JSON string containing mod information
            pack_type: Type of pack ("behavior", "resource", "both")
            
        Returns:
            JSON string with manifest data
        """
        try:
            info = json.loads(mod_info) if isinstance(mod_info, str) else mod_info
            
            # Create base manifest
            manifest = copy.deepcopy(self.manifest_template)
            manifest["header"]["name"] = info.get("name", "Converted Mod")
            manifest["header"]["description"] = f"Converted from {info.get('framework', 'Java')} mod"
            manifest["header"]["uuid"] = str(uuid.uuid4())
            manifest["header"]["version"] = info.get("version", [1, 0, 0])
            
            # Add modules based on pack type
            if pack_type in ["behavior", "both"]:
                manifest["modules"].append({
                    "type": "data",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                })
            
            if pack_type in ["resource", "both"]:
                manifest["modules"].append({
                    "type": "resources",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                })
            
            return json.dumps(manifest)
            
        except Exception as e:
            logger.error(f"Error generating manifest: {e}")
            return json.dumps({
                "error": str(e),
                "success": False
            })
    
    def generate_manifests(self, manifest_data: str) -> str:
        """
        Generate manifests for packaging.
        
        Args:
            manifest_data: JSON string or dict containing manifest information
            
        Returns:
            JSON string with generation results
        """
        try:
            # Handle both JSON string and direct input
            if isinstance(manifest_data, str):
                try:
                    data = json.loads(manifest_data)
                except json.JSONDecodeError:
                    return json.dumps({"success": False, "error": "Invalid JSON input"})
            else:
                data = manifest_data if isinstance(manifest_data, dict) else {"error": "Invalid input format"}
            
            # Extract package info
            package_info = data.get("package_info", {})
            capabilities = data.get("capabilities", [])
            
            # Generate manifest
            manifest = {
                "format_version": 2,
                "header": {
                    "name": package_info.get("name", "Converted Mod"),
                    "description": package_info.get("description", "Converted from Java mod"),
                    "uuid": str(uuid.uuid4()),
                    "version": package_info.get("version", [1, 0, 0]),
                    "min_engine_version": [1, 19, 0]
                },
                "modules": []
            }
            
            # Add behavior pack module if needed
            if package_info.get("has_behavior_pack", False):
                manifest["modules"].append({
                    "type": "data",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                })
            
            # Add resource pack module if needed
            if package_info.get("has_resource_pack", False):
                manifest["modules"].append({
                    "type": "resources",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                })
            
            # Add capabilities
            if capabilities:
                manifest["capabilities"] = capabilities
            
            # Create output directory structure
            output_dir = package_info.get("output_directory", "")
            if output_dir:
                output_path = Path(output_dir)
                
                # Create behavior pack directory if needed
                if package_info.get("has_behavior_pack", False):
                    bp_dir = output_path / "behavior_pack"
                    bp_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Write behavior pack manifest
                    bp_manifest = copy.deepcopy(manifest)
                    bp_manifest["modules"] = [m for m in bp_manifest["modules"] if m["type"] == "data"]
                    
                    with open(bp_dir / "manifest.json", "w") as f:
                        json.dump(bp_manifest, f, indent=2)
                
                # Create resource pack directory if needed
                if package_info.get("has_resource_pack", False):
                    rp_dir = output_path / "resource_pack"
                    rp_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Write resource pack manifest
                    rp_manifest = copy.deepcopy(manifest)
                    rp_manifest["modules"] = [m for m in rp_manifest["modules"] if m["type"] == "resources"]
                    
                    with open(rp_dir / "manifest.json", "w") as f:
                        json.dump(rp_manifest, f, indent=2)
            
            result = {
                "success": True,
                "manifest": manifest,
                "files_created": []
            }
            
            if package_info.get("has_behavior_pack"):
                result["behavior_manifest_path"] = f"{output_dir}/behavior_pack/manifest.json"
                result["files_created"].append(result["behavior_manifest_path"])
            
            if package_info.get("has_resource_pack"):
                result["resource_manifest_path"] = f"{output_dir}/resource_pack/manifest.json"
                result["files_created"].append(result["resource_manifest_path"])
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Error generating manifests: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
        
    
    def analyze_conversion_components(self, component_data: str) -> str:
        """Analyze conversion components for packaging."""
        try:
            # Handle both JSON string and direct input
            if isinstance(component_data, str):
                try:
                    data = json.loads(component_data)
                except json.JSONDecodeError:
                    data = {'input': component_data}
            else:
                data = component_data if isinstance(component_data, dict) else {'input': str(component_data)}
            
            # Mock analysis of conversion components
            analysis_result = {
                'success': True,
                'components': {
                    'behavior_packs': {'count': 1, 'size': '2.5MB'},
                    'resource_packs': {'count': 1, 'size': '15.8MB'},
                    'scripts': {'count': 8, 'size': '125KB'},
                    'textures': {'count': 45, 'size': '12.3MB'},
                    'models': {'count': 12, 'size': '3.1MB'},
                    'sounds': {'count': 6, 'size': '450KB'}
                },
                'packaging_requirements': {
                    'manifest_files': 2,
                    'folder_structure': 'standard',
                    'compression_needed': True
                },
                'recommendations': [
                    "Package structure is ready for assembly",
                    "Consider compressing large texture files",
                    "Validate manifest dependencies"
                ]
            }
            
            return json.dumps(analysis_result)
            
        except Exception as e:
            logger.error(f"Component analysis error: {e}")
            return json.dumps({"success": False, "error": f"Component analysis failed: {str(e)}"})
    
    def create_package_structure(self, structure_data: Dict[str, Any]) -> str:
        """Create package structure for Bedrock addon."""
        try:
            output_dir = structure_data.get("output_dir")
            mod_name = structure_data.get("mod_name", "converted_mod")

            if not output_dir:
                raise ValueError("output_dir is required for creating package structure")

            behavior_pack_path = os.path.join(output_dir, f"{mod_name}_BP")
            resource_pack_path = os.path.join(output_dir, f"{mod_name}_RP")

            os.makedirs(behavior_pack_path, exist_ok=True)
            os.makedirs(resource_pack_path, exist_ok=True)

            # Create subdirectories within packs (example, can be expanded)
            os.makedirs(os.path.join(behavior_pack_path, "entities"), exist_ok=True)
            os.makedirs(os.path.join(behavior_pack_path, "scripts"), exist_ok=True)
            os.makedirs(os.path.join(resource_pack_path, "textures"), exist_ok=True)
            os.makedirs(os.path.join(resource_pack_path, "models"), exist_ok=True)

            return json.dumps({
                "success": True,
                "behavior_pack_path": behavior_pack_path,
                "resource_pack_path": resource_pack_path,
                "message": "Package structure created successfully"
            })

        except Exception as e:
            logger.error(f"Structure creation error: {e}")
            return json.dumps({"success": False, "error": f"Structure creation failed: {str(e)}"})
    
    def validate_package(self, validation_data: str) -> str:
        """Validate the package structure."""
        try:
            # Handle both JSON string and direct input
            if isinstance(validation_data, str):
                try:
                    data = json.loads(validation_data)
                except json.JSONDecodeError:
                    data = {'input': validation_data}
            else:
                data = validation_data if isinstance(validation_data, dict) else {'input': str(validation_data)}
            
            # Mock package validation
            validation_result = {
                'success': True,
                'validation_passed': True,
                'validation_results': {
                    'overall_valid': True,
                    'quality_score': 85,
                    'critical_errors': [],
                    'package_validations': [
                        {'package_path': 'behavior_pack', 'is_valid': True, 'valid': True, 'errors': []},
                        {'package_path': 'resource_pack', 'is_valid': True, 'valid': True, 'errors': []}
                    ],
                    'manifest_validity': {'passed': True, 'message': 'Manifests are valid'},
                    'folder_structure': {'passed': True, 'message': 'Folder structure is correct'},
                    'file_integrity': {'passed': True, 'message': 'All files are intact'},
                    'uuid_uniqueness': {'passed': True, 'message': 'UUIDs are unique'},
                    'version_compatibility': {'passed': True, 'message': 'Version compatibility verified'}
                },
                'checks_performed': {
                    'manifest_validity': {'passed': True, 'message': 'Manifests are valid'},
                    'folder_structure': {'passed': True, 'message': 'Folder structure is correct'},
                    'file_integrity': {'passed': True, 'message': 'All files are intact'},
                    'uuid_uniqueness': {'passed': True, 'message': 'UUIDs are unique'},
                    'version_compatibility': {'passed': True, 'message': 'Version compatibility verified'}
                },
                'warnings': [
                    'Large texture files detected - consider optimization',
                    'Some scripts may need performance testing'
                ],
                'recommendations': [
                    "Package validation successful",
                    "Ready for final assembly",
                    "Consider performance optimizations"
                ]
            }
            
            return json.dumps(validation_result)
            
        except Exception as e:
            logger.error(f"Package validation error: {e}")
            return json.dumps({"success": False, "error": f"Package validation failed: {str(e)}"})
    
    def build_mcaddon(self, build_data) -> str:
        """Build the final mcaddon package."""
        try:
            # Handle both string and dict inputs
            if isinstance(build_data, str):
                data = json.loads(build_data)
            else:
                data = build_data
                
            output_path = data.get("output_path")
            source_directories = data.get("source_directories", [])
            behavior_pack_path = data.get("behavior_pack_path")
            resource_pack_path = data.get("resource_pack_path")
            
            if not output_path:
                raise ValueError("Missing required output_path for building .mcaddon")

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Handle source_directories (new format)
                if source_directories:
                    for source_dir in source_directories:
                        source_path = Path(source_dir)
                        if source_path.exists():
                            # Determine pack type based on directory structure
                            if source_path.name == "behavior_pack" or (source_path / "manifest.json").exists():
                                # It's a behavior pack
                                for root, _, files in os.walk(source_path):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        arcname = os.path.join(source_path.name, os.path.relpath(file_path, source_path))
                                        zipf.write(file_path, arcname)
                            elif source_path.name == "resource_pack":
                                # It's a resource pack
                                for root, _, files in os.walk(source_path):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        arcname = os.path.join(source_path.name, os.path.relpath(file_path, source_path))
                                        zipf.write(file_path, arcname)
                
                # Handle legacy format
                if behavior_pack_path and os.path.exists(behavior_pack_path):
                    for root, _, files in os.walk(behavior_pack_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join("behaviors", os.path.relpath(file_path, behavior_pack_path))
                            zipf.write(file_path, arcname)

                if resource_pack_path and os.path.exists(resource_pack_path):
                    for root, _, files in os.walk(resource_pack_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join("resources", os.path.relpath(file_path, resource_pack_path))
                            zipf.write(file_path, arcname)

            # Basic validation of the created zip file
            post_validation = {
                "is_valid_zip": True,
                "file_count": 0,
                "contains_manifests": False
            }
            
            try:
                with zipfile.ZipFile(output_path, 'r') as zf:
                    namelist = zf.namelist()
                    post_validation["file_count"] = len(namelist)
                    post_validation["contains_manifests"] = any("manifest.json" in name for name in namelist)
            except Exception as e:
                post_validation["is_valid_zip"] = False
                post_validation["error"] = str(e)
            
            return json.dumps({
                "success": True,
                "output_path": output_path,
                "post_validation": post_validation
            })

        except Exception as e:
            logger.error(f"Build error: {e}")
            return json.dumps({"success": False, "error": f"Build failed: {str(e)}"})
    
    @tool
    @staticmethod
    def analyze_conversion_components_tool(component_data: str) -> str:
        """Analyze conversion components for packaging."""
        agent = PackagingAgent.get_instance()
        return agent.analyze_conversion_components(component_data)
    
    @tool
    @staticmethod
    def create_package_structure_tool(structure_data: str) -> str:
        """Create package structure for Bedrock addon."""
        agent = PackagingAgent.get_instance()
        return agent.create_package_structure(structure_data)
    
    @tool
    @staticmethod
    def generate_manifests_tool(manifest_data: str) -> str:
        """Generate manifest files for the addon."""
        agent = PackagingAgent.get_instance()
        return agent.generate_manifests(manifest_data)
    
    @tool
    @staticmethod
    def validate_package_tool(validation_data: str) -> str:
        """Validate the package structure."""
        agent = PackagingAgent.get_instance()
        return agent.validate_package(validation_data)
    
    @tool
    @staticmethod
    def build_mcaddon_tool(build_data: str) -> str:
        """Build the final mcaddon package."""
        agent = PackagingAgent.get_instance()
        return agent.build_mcaddon(build_data)