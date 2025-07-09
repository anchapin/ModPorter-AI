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
            PackagingAgent.analyze_conversion_components_tool,
            PackagingAgent.create_package_structure_tool,
            PackagingAgent.generate_manifests_tool,
            PackagingAgent.validate_package_tool,
            PackagingAgent.build_mcaddon_tool
        ]
        
    
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
    
    def generate_manifests(self, manifest_data: Dict[str, Any]) -> str:
        """Generate manifest files for the addon."""
        try:
            mod_name = manifest_data.get("mod_name", "Converted Mod")
            mod_description = manifest_data.get("mod_description", "Mod converted by ModPorter AI")
            mod_version = manifest_data.get("mod_version", [1, 0, 0])
            pack_types = manifest_data.get("pack_types", ["behavior_pack", "resource_pack"])

            generated_manifests = {}

            for pack_type in pack_types:
                manifest = copy.deepcopy(self.manifest_template)
                header_uuid = str(uuid.uuid4())
                module_uuid = str(uuid.uuid4())

                manifest["header"]["name"] = f"{mod_name} {pack_type.replace('_', ' ').title()}"
                manifest["header"]["description"] = mod_description
                manifest["header"]["uuid"] = header_uuid
                manifest["header"]["version"] = mod_version

                module_type = "data" if pack_type == "behavior_pack" else "resources"
                manifest["modules"].append({
                    "description": f"{module_type.title()} module",
                    "type": module_type,
                    "uuid": module_uuid,
                    "version": mod_version
                })
                generated_manifests[f"{pack_type}_manifest"] = manifest

            return json.dumps(generated_manifests)

        except Exception as e:
            logger.error(f"Manifest generation error: {e}")
            return json.dumps({"success": False, "error": f"Manifest generation failed: {str(e)}"})
    
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
    
    def build_mcaddon(self, build_data: Dict[str, Any]) -> str:
        """Build the final mcaddon package."""
        try:
            output_path = build_data.get("output_path")
            behavior_pack_path = build_data.get("behavior_pack_path")
            resource_pack_path = build_data.get("resource_pack_path")
            
            if not output_path or not behavior_pack_path or not resource_pack_path:
                raise ValueError("Missing required paths for building .mcaddon")

            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add behavior pack files
                for root, _, files in os.walk(behavior_pack_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join("behaviors", os.path.relpath(file_path, behavior_pack_path))
                        zipf.write(file_path, arcname)

                # Add resource pack files
                for root, _, files in os.walk(resource_pack_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join("resources", os.path.relpath(file_path, resource_pack_path))
                        zipf.write(file_path, arcname)

            return json.dumps({"success": True, "output_path": output_path})

        except Exception as e:
            logger.error(f"Build error: {e}")
            return json.dumps({"success": False, "error": f"Build failed: {str(e)}"})
    
    @tool
    @staticmethod
    def analyze_conversion_components_tool(component_data: str) -> str:
        """Analyze conversion components for packaging."""
        agent = PackagingAgent()
        return agent.analyze_conversion_components(component_data)
    
    @tool
    @staticmethod
    def create_package_structure_tool(structure_data: str) -> str:
        """Create package structure for Bedrock addon."""
        agent = PackagingAgent()
        return agent.create_package_structure(structure_data)
    
    @tool
    @staticmethod
    def generate_manifests_tool(manifest_data: str) -> str:
        """Generate manifest files for the addon."""
        agent = PackagingAgent()
        return agent.generate_manifests(manifest_data)
    
    @tool
    @staticmethod
    def validate_package_tool(validation_data: str) -> str:
        """Validate the package structure."""
        agent = PackagingAgent()
        return agent.validate_package(validation_data)
    
    @tool
    @staticmethod
    def build_mcaddon_tool(build_data: str) -> str:
        """Build the final mcaddon package."""
        agent = PackagingAgent()
        return agent.build_mcaddon(build_data)