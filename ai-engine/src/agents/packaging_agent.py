"""
Packaging Agent - Assembles converted components into .mcaddon packages
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from crewai_tools import BaseTool, tool
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class ManifestGeneratorTool(BaseTool):
    """Tool for generating Bedrock add-on manifest files"""
    
    name: str = "Manifest Generator Tool"
    description: str = "Generates valid manifest.json files for Bedrock add-ons"
    
    def _run(self, mod_info: str, pack_type: str = "both") -> str:
        """
        Generate manifest.json for Bedrock add-on
        
        Args:
            mod_info: JSON string with mod information
            pack_type: Type of pack (resource, behavior, both)
            
        Returns:
            JSON string with manifest data
        """
        try:
            info = json.loads(mod_info)
            
            manifest_data = {
                "format_version": "1.16.0",
                "header": {
                    "description": f"Converted from Java mod: {info.get('name', 'Unknown Mod')}",
                    "name": info.get('name', 'Converted Mod'),
                    "uuid": str(uuid.uuid4()),
                    "version": self._parse_version(info.get('version', '1.0.0')),
                    "min_engine_version": [1, 16, 0]
                },
                "modules": []
            }
            
            # Add resource pack module
            if pack_type in ["resource", "both"]:
                manifest_data["modules"].append({
                    "description": "Resource pack module",
                    "type": "resources",
                    "uuid": str(uuid.uuid4()),
                    "version": self._parse_version(info.get('version', '1.0.0'))
                })
            
            # Add behavior pack module
            if pack_type in ["behavior", "both"]:
                manifest_data["modules"].append({
                    "description": "Behavior pack module",
                    "type": "data",
                    "uuid": str(uuid.uuid4()),
                    "version": self._parse_version(info.get('version', '1.0.0'))
                })
            
            # Add dependencies if both packs are present
            if pack_type == "both" and len(manifest_data["modules"]) > 1:
                # Resource pack depends on behavior pack
                resource_module = next(m for m in manifest_data["modules"] if m["type"] == "resources")
                behavior_module = next(m for m in manifest_data["modules"] if m["type"] == "data")
                
                manifest_data["dependencies"] = [
                    {
                        "uuid": behavior_module["uuid"],
                        "version": behavior_module["version"]
                    }
                ]
            
            # Add metadata
            manifest_data["metadata"] = {
                "authors": ["ModPorter AI"],
                "license": "Converted from Java mod",
                "generated_with": "ModPorter AI Conversion Engine",
                "generation_date": datetime.now().isoformat(),
                "original_mod": {
                    "name": info.get('name', 'Unknown'),
                    "version": info.get('version', 'Unknown'),
                    "framework": info.get('framework', 'Unknown'),
                    "minecraft_version": info.get('minecraft_version', 'Unknown')
                }
            }
            
            return json.dumps(manifest_data, indent=2)
            
        except Exception as e:
            logger.error(f"Error generating manifest: {e}")
            return json.dumps({"error": f"Failed to generate manifest: {str(e)}"})
    
    def _parse_version(self, version_str: str) -> List[int]:
        """Parse version string to [major, minor, patch] format"""
        try:
            # Remove any non-numeric prefixes (like 'v')
            clean_version = version_str.lstrip('v')
            
            # Split by dots and convert to integers
            parts = clean_version.split('.')
            
            # Ensure we have at least 3 parts
            while len(parts) < 3:
                parts.append('0')
            
            # Convert to integers, default to 0 if conversion fails
            version_parts = []
            for part in parts[:3]:  # Only take first 3 parts
                try:
                    version_parts.append(int(part))
                except ValueError:
                    version_parts.append(0)
            
            return version_parts
            
        except Exception:
            return [1, 0, 0]  # Default version


class PackageAssemblerTool(BaseTool):
    """Tool for assembling all components into final package structure"""
    
    name: str = "Package Assembler Tool"
    description: str = "Assembles all converted components into proper Bedrock add-on structure"
    
    def _run(self, conversion_data: str, output_path: str) -> str:
        """
        Assemble package from conversion data
        
        Args:
            conversion_data: JSON string with all conversion results
            output_path: Base output directory for package
            
        Returns:
            JSON string with assembly results
        """
        try:
            data = json.loads(conversion_data)
            
            assembly_results = {
                "package_structure": {},
                "files_created": [],
                "manifest_files": [],
                "total_files": 0,
                "package_size": "Unknown",
                "errors": []
            }
            
            # Define standard Bedrock add-on structure
            package_structure = {
                "resource_pack": {
                    "root": ["manifest.json", "pack_icon.png"],
                    "textures": ["blocks", "items", "entity", "ui", "environment"],
                    "models": ["entity", "blocks"],
                    "sounds": ["block", "item", "entity", "ambient"],
                    "animations": ["entity"],
                    "animation_controllers": ["entity"],
                    "render_controllers": ["entity"],
                    "materials": ["entity"],
                    "ui": ["ui_defs.json"]
                },
                "behavior_pack": {
                    "root": ["manifest.json", "pack_icon.png"],
                    "blocks": [],
                    "items": [],
                    "entities": [],
                    "functions": [],
                    "loot_tables": [],
                    "recipes": [],
                    "spawn_rules": [],
                    "trading": [],
                    "scripts": ["client", "server"]
                }
            }
            
            assembly_results["package_structure"] = package_structure
            
            # Process converted assets
            self._process_assets(data, assembly_results)
            
            # Process converted features
            self._process_features(data, assembly_results)
            
            # Generate manifest files
            self._generate_manifests(data, assembly_results)
            
            # Generate installation instructions
            assembly_results["installation_instructions"] = self._generate_installation_instructions(data)
            
            return json.dumps(assembly_results, indent=2)
            
        except Exception as e:
            logger.error(f"Error assembling package: {e}")
            return json.dumps({"error": f"Failed to assemble package: {str(e)}"})
    
    def _process_assets(self, data: Dict, results: Dict):
        """Process converted assets into package structure"""
        if "asset_conversions" in data:
            assets = data["asset_conversions"]
            
            for asset_type, asset_list in assets.items():
                if isinstance(asset_list, list):
                    for asset in asset_list:
                        if isinstance(asset, dict) and "converted_path" in asset:
                            results["files_created"].append({
                                "type": "asset",
                                "category": asset_type,
                                "source": asset.get("original_path", ""),
                                "destination": asset["converted_path"],
                                "size": "Unknown"
                            })
                            results["total_files"] += 1
    
    def _process_features(self, data: Dict, results: Dict):
        """Process converted features into package structure"""
        if "feature_conversions" in data:
            features = data["feature_conversions"]
            
            for feature_type, feature_list in features.items():
                if isinstance(feature_list, list):
                    for feature in feature_list:
                        if isinstance(feature, dict):
                            results["files_created"].append({
                                "type": "feature",
                                "category": feature_type,
                                "name": feature.get("name", f"Unknown {feature_type}"),
                                "files": feature.get("generated_files", []),
                                "size": "Unknown"
                            })
                            results["total_files"] += len(feature.get("generated_files", []))
    
    def _generate_manifests(self, data: Dict, results: Dict):
        """Generate manifest files for the package"""
        mod_info = data.get("mod_info", {})
        
        # Generate resource pack manifest
        manifest_tool = ManifestGeneratorTool()
        resource_manifest = manifest_tool._run(json.dumps(mod_info), "resource")
        results["manifest_files"].append({
            "type": "resource_pack",
            "path": "resource_pack/manifest.json",
            "content": resource_manifest
        })
        
        # Generate behavior pack manifest
        behavior_manifest = manifest_tool._run(json.dumps(mod_info), "behavior")
        results["manifest_files"].append({
            "type": "behavior_pack",
            "path": "behavior_pack/manifest.json",
            "content": behavior_manifest
        })
        
        results["total_files"] += 2
    
    def _generate_installation_instructions(self, data: Dict) -> List[str]:
        """Generate installation instructions for the converted add-on"""
        instructions = [
            "Installation Instructions:",
            "1. Download the generated .mcaddon file",
            "2. Double-click the .mcaddon file to install",
            "3. Or manually place the resource pack and behavior pack in their respective folders:",
            "   - Resource Pack: %localappdata%\\Packages\\Microsoft.MinecraftUWP_8wekyb3d8bbwe\\LocalState\\games\\com.mojang\\resource_packs\\",
            "   - Behavior Pack: %localappdata%\\Packages\\Microsoft.MinecraftUWP_8wekyb3d8bbwe\\LocalState\\games\\com.mojang\\behavior_packs\\",
            "4. Create a new world and enable both packs in the world settings",
            "5. Join the world to experience the converted mod content"
        ]
        
        # Add specific instructions based on conversion results
        if data.get("smart_assumptions_applied"):
            instructions.extend([
                "",
                "Important Notes:",
                "- This mod uses smart assumptions to handle incompatible features",
                "- Some features may work differently than in the original Java mod",
                "- Check the conversion report for details on applied assumptions"
            ])
        
        return instructions


class PackageValidatorTool(BaseTool):
    """Tool for validating assembled packages"""
    
    name: str = "Package Validator Tool"
    description: str = "Validates assembled Bedrock add-on packages for correctness"
    
    def _run(self, package_data: str) -> str:
        """
        Validate assembled package
        
        Args:
            package_data: JSON string with package assembly results
            
        Returns:
            JSON string with validation results
        """
        try:
            package = json.loads(package_data)
            
            validation_results = {
                "valid": True,
                "validation_checks": [],
                "errors": [],
                "warnings": [],
                "recommendations": []
            }
            
            # Check for required manifest files
            self._validate_manifests(package, validation_results)
            
            # Check package structure
            self._validate_structure(package, validation_results)
            
            # Check file integrity
            self._validate_files(package, validation_results)
            
            # Overall validation status
            validation_results["valid"] = len(validation_results["errors"]) == 0
            
            return json.dumps(validation_results, indent=2)
            
        except Exception as e:
            logger.error(f"Error validating package: {e}")
            return json.dumps({"error": f"Failed to validate package: {str(e)}"})
    
    def _validate_manifests(self, package: Dict, results: Dict):
        """Validate manifest files"""
        manifest_files = package.get("manifest_files", [])
        
        if not manifest_files:
            results["errors"].append("No manifest files found")
            return
        
        required_types = ["resource_pack", "behavior_pack"]
        found_types = [m["type"] for m in manifest_files]
        
        for req_type in required_types:
            if req_type not in found_types:
                results["warnings"].append(f"Missing {req_type} manifest")
        
        # Validate manifest content
        for manifest in manifest_files:
            try:
                manifest_data = json.loads(manifest["content"])
                
                # Check required fields
                required_fields = ["format_version", "header", "modules"]
                for field in required_fields:
                    if field not in manifest_data:
                        results["errors"].append(f"Missing required field '{field}' in {manifest['type']} manifest")
                
                # Check header fields
                if "header" in manifest_data:
                    header_fields = ["name", "description", "uuid", "version"]
                    for field in header_fields:
                        if field not in manifest_data["header"]:
                            results["errors"].append(f"Missing header field '{field}' in {manifest['type']} manifest")
                
                results["validation_checks"].append(f"Manifest {manifest['type']}: Valid JSON structure")
                
            except json.JSONDecodeError:
                results["errors"].append(f"Invalid JSON in {manifest['type']} manifest")
    
    def _validate_structure(self, package: Dict, results: Dict):
        """Validate package structure"""
        structure = package.get("package_structure", {})
        
        if not structure:
            results["errors"].append("No package structure defined")
            return
        
        # Check for required pack types
        required_packs = ["resource_pack", "behavior_pack"]
        for pack_type in required_packs:
            if pack_type not in structure:
                results["warnings"].append(f"Missing {pack_type} structure")
        
        results["validation_checks"].append("Package structure: Defined")
    
    def _validate_files(self, package: Dict, results: Dict):
        """Validate file integrity"""
        files_created = package.get("files_created", [])
        
        if not files_created:
            results["warnings"].append("No files created in package")
            return
        
        # Check for duplicate files
        destinations = [f.get("destination", "") for f in files_created]
        duplicates = [dest for dest in destinations if destinations.count(dest) > 1]
        
        if duplicates:
            results["warnings"].append(f"Duplicate file destinations: {list(set(duplicates))}")
        
        # Check for missing critical files
        asset_files = [f for f in files_created if f.get("type") == "asset"]
        if not asset_files:
            results["warnings"].append("No asset files converted")
        
        results["validation_checks"].append(f"File validation: {len(files_created)} files processed")


class PackagingAgent:
    """Agent for packaging converted components into .mcaddon files"""
    
    def __init__(self):
        self.manifest_generator = ManifestGeneratorTool()
        self.package_assembler = PackageAssemblerTool()
        self.package_validator = PackageValidatorTool()
        logger.info("PackagingAgent initialized")
    
    @tool("Manifest Generation Tool")
    def generate_manifest(self, mod_info: str, pack_type: str = "both") -> str:
        """
        Generate manifest.json files for Bedrock add-on.
        
        Args:
            mod_info: JSON string with mod information
            pack_type: Type of pack (resource, behavior, both)
            
        Returns:
            JSON string with manifest data
        """
        return self.manifest_generator._run(mod_info, pack_type)
    
    @tool("Package Assembly Tool")
    def assemble_package(self, conversion_data: str, output_path: str) -> str:
        """
        Assemble all converted components into final package structure.
        
        Args:
            conversion_data: JSON string with all conversion results
            output_path: Base output directory for package
            
        Returns:
            JSON string with assembly results
        """
        return self.package_assembler._run(conversion_data, output_path)
    
    @tool("Package Validation Tool")
    def validate_package(self, package_data: str) -> str:
        """
        Validate assembled package for correctness and completeness.
        
        Args:
            package_data: JSON string with package assembly results
            
        Returns:
            JSON string with validation results
        """
        return self.package_validator._run(package_data)
    
    @tool("Installation Guide Generator")
    def generate_installation_guide(self, package_data: str, mod_info: str) -> str:
        """
        Generate comprehensive installation guide for converted add-on.
        
        Args:
            package_data: JSON string with package assembly results
            mod_info: JSON string with original mod information
            
        Returns:
            JSON string with installation guide
        """
        try:
            package = json.loads(package_data)
            mod_data = json.loads(mod_info)
            
            guide = {
                "title": f"Installation Guide for {mod_data.get('name', 'Converted Mod')}",
                "overview": f"This guide will help you install the converted Bedrock add-on version of {mod_data.get('name', 'your mod')}.",
                "requirements": [
                    "Minecraft Bedrock Edition",
                    "Version 1.16.0 or higher",
                    "Experimental features enabled (if using scripts)"
                ],
                "installation_steps": [
                    {
                        "step": 1,
                        "title": "Download the Add-on",
                        "description": "Download the generated .mcaddon file from the conversion results"
                    },
                    {
                        "step": 2,
                        "title": "Install the Add-on",
                        "description": "Double-click the .mcaddon file to automatically install both resource and behavior packs"
                    },
                    {
                        "step": 3,
                        "title": "Create New World",
                        "description": "Create a new world in Minecraft Bedrock Edition"
                    },
                    {
                        "step": 4,
                        "title": "Enable Add-on",
                        "description": "In world settings, enable both the resource pack and behavior pack"
                    },
                    {
                        "step": 5,
                        "title": "Join World",
                        "description": "Join the world to experience the converted mod content"
                    }
                ],
                "troubleshooting": [
                    {
                        "issue": "Add-on not appearing in world settings",
                        "solution": "Restart Minecraft and check that the add-on was installed correctly"
                    },
                    {
                        "issue": "Some features not working",
                        "solution": "Check that experimental features are enabled in world settings"
                    },
                    {
                        "issue": "Textures not loading",
                        "solution": "Ensure the resource pack is enabled and applied in world settings"
                    }
                ],
                "important_notes": [],
                "manual_installation": [
                    "If automatic installation fails, you can manually install:",
                    "1. Extract the .mcaddon file",
                    "2. Place resource pack in: %localappdata%\\Packages\\Microsoft.MinecraftUWP_8wekyb3d8bbwe\\LocalState\\games\\com.mojang\\resource_packs\\",
                    "3. Place behavior pack in: %localappdata%\\Packages\\Microsoft.MinecraftUWP_8wekyb3d8bbwe\\LocalState\\games\\com.mojang\\behavior_packs\\"
                ]
            }
            
            # Add smart assumption notes
            if package.get("smart_assumptions_applied"):
                guide["important_notes"].extend([
                    "This converted add-on uses smart assumptions to handle incompatible features",
                    "Some features may work differently than in the original Java mod",
                    "Check the conversion report for details on what was changed"
                ])
            
            return json.dumps(guide, indent=2)
            
        except Exception as e:
            logger.error(f"Error generating installation guide: {e}")
            return json.dumps({"error": f"Failed to generate installation guide: {str(e)}"})
    
    def get_tools(self) -> List:
        """Return available tools for this agent"""
        return [
            self.generate_manifest,
            self.assemble_package,
            self.validate_package,
            self.generate_installation_guide
        ]