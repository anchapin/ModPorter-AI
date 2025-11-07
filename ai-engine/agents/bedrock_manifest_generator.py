"""
Bedrock Manifest Generator for creating valid manifest.json files
Part of the Bedrock Add-on Generation System (Issue #6)
"""

import json
import uuid
import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import jsonschema

logger = logging.getLogger(__name__)


class PackType(Enum):
    BEHAVIOR = "behavior"
    RESOURCE = "resource"


@dataclass
class ModuleInfo:
    module_type: str
    uuid: str
    version: List[int]
    description: Optional[str] = None


@dataclass
class ManifestData:
    name: str
    description: str
    version: List[int]
    uuid: str
    min_engine_version: List[int]
    modules: List[ModuleInfo]
    capabilities: Optional[List[str]] = None
    dependencies: Optional[List[Dict[str, Any]]] = None


class BedrockManifestGenerator:
    """
    Generator for Bedrock add-on manifest.json files.
    Supports both behavior packs and resource packs with proper validation.
    """
    
    def __init__(self):
        self.format_version = 2
        self.default_min_engine = [1, 19, 0]
        
        # Bedrock manifest schema for validation
        self.manifest_schema = {
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
    
    def generate_manifests(self, mod_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate both behavior pack and resource pack manifests.
        
        Args:
            mod_data: Dictionary containing mod information
            
        Returns:
            Tuple of (behavior_pack_manifest, resource_pack_manifest)
        """
        logger.info(f"Generating manifests for mod: {mod_data.get('name', 'Unknown')}")
        
        # Extract mod information
        mod_name = mod_data.get('name', 'Converted Mod')
        mod_description = mod_data.get('description', 'Converted from Java mod')
        mod_version = self._parse_version(mod_data.get('version', '1.0.0'))
        
        # Generate unique UUIDs for each pack
        bp_uuid = str(uuid.uuid4())
        rp_uuid = str(uuid.uuid4())
        
        # Determine required capabilities based on mod features
        capabilities = self._determine_capabilities(mod_data)
        
        # Create behavior pack manifest
        bp_manifest = self._create_behavior_manifest(
            mod_name, mod_description, mod_version, bp_uuid, capabilities
        )
        
        # Create resource pack manifest  
        rp_manifest = self._create_resource_manifest(
            mod_name, mod_description, mod_version, rp_uuid, capabilities
        )
        
        # Create dependencies between packs
        bp_manifest = self._add_pack_dependencies(bp_manifest, rp_uuid, mod_version)
        rp_manifest = self._add_pack_dependencies(rp_manifest, bp_uuid, mod_version)
        
        # Validate manifests
        self._validate_manifest(bp_manifest, "behavior")
        self._validate_manifest(rp_manifest, "resource")
        
        logger.info("Successfully generated and validated manifests")
        return bp_manifest, rp_manifest
    
    def _create_behavior_manifest(self, name: str, description: str, version: List[int], 
                                pack_uuid: str, capabilities: List[str]) -> Dict[str, Any]:
        """Create behavior pack manifest."""
        modules = [
            {
                "type": "data",
                "uuid": str(uuid.uuid4()),
                "version": version
            }
        ]
        
        # Add script module if needed
        if any(cap in capabilities for cap in ["experimental_custom_ui", "script_eval"]):
            modules.append({
                "type": "javascript",
                "uuid": str(uuid.uuid4()),
                "version": version,
                "entry": "scripts/main.js"
            })
        
        manifest = {
            "format_version": self.format_version,
            "header": {
                "name": f"{name} BP",
                "description": f"{description} - Behavior Pack",
                "uuid": pack_uuid,
                "version": version,
                "min_engine_version": self.default_min_engine
            },
            "modules": modules
        }
        
        if capabilities:
            manifest["capabilities"] = capabilities
            
        return manifest
    
    def _create_resource_manifest(self, name: str, description: str, version: List[int],
                                pack_uuid: str, capabilities: List[str]) -> Dict[str, Any]:
        """Create resource pack manifest."""
        modules = [
            {
                "type": "resources",
                "uuid": str(uuid.uuid4()),
                "version": version
            }
        ]
        
        # Add client data module if needed for custom UI
        if "experimental_custom_ui" in capabilities:
            modules.append({
                "type": "client_data",
                "uuid": str(uuid.uuid4()),
                "version": version
            })
        
        manifest = {
            "format_version": self.format_version,
            "header": {
                "name": f"{name} RP",
                "description": f"{description} - Resource Pack",
                "uuid": pack_uuid,
                "version": version,
                "min_engine_version": self.default_min_engine
            },
            "modules": modules
        }
        
        if capabilities:
            manifest["capabilities"] = capabilities
            
        return manifest
    
    def _determine_capabilities(self, mod_data: Dict[str, Any]) -> List[str]:
        """Determine required Bedrock capabilities based on mod features."""
        capabilities = []
        features = mod_data.get('features', [])
        
        # Check for features that require specific capabilities
        if any(f.get('type') == 'custom_ui' for f in features):
            capabilities.append("experimental_custom_ui")
        
        if any(f.get('type') == 'scripting' for f in features):
            capabilities.append("script_eval")
        
        if any(f.get('type') == 'chemistry' for f in features):
            capabilities.append("chemistry")
        
        # Add experimental features if needed
        experimental_features = mod_data.get('experimental_features', [])
        if experimental_features:
            capabilities.extend(experimental_features)
        
        return list(set(capabilities))  # Remove duplicates
    
    def _parse_version(self, version_str: str) -> List[int]:
        """Parse version string into [major, minor, patch] format."""
        try:
            if isinstance(version_str, list):
                return version_str[:3] + [0] * (3 - len(version_str))
            
            # Handle semantic versioning
            version_parts = str(version_str).split('.')
            version_ints = []
            
            for part in version_parts[:3]:  # Take only first 3 parts
                # Extract numeric part (handle versions like "1.0.0-beta")
                numeric_part = ''.join(c for c in part if c.isdigit())
                version_ints.append(int(numeric_part) if numeric_part else 0)
            
            # Ensure we have exactly 3 parts
            while len(version_ints) < 3:
                version_ints.append(0)
                
            return version_ints
            
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse version '{version_str}', using [1, 0, 0]")
            return [1, 0, 0]
    
    def _add_pack_dependencies(self, manifest: Dict[str, Any], dep_uuid: str, 
                             dep_version: List[int]) -> Dict[str, Any]:
        """Add dependencies between behavior and resource packs."""
        dependencies = manifest.get("dependencies", [])
        dependencies.append({
            "uuid": dep_uuid,
            "version": dep_version
        })
        manifest["dependencies"] = dependencies
        return manifest
    
    def _validate_manifest(self, manifest: Dict[str, Any], pack_type: str) -> None:
        """Validate manifest against Bedrock schema."""
        try:
            jsonschema.validate(manifest, self.manifest_schema)
            logger.debug(f"Manifest validation passed for {pack_type} pack")
        except jsonschema.ValidationError as e:
            logger.error(f"Manifest validation failed for {pack_type} pack: {e.message}")
            raise ValueError(f"Invalid {pack_type} pack manifest: {e.message}")
    
    def write_manifests_to_disk(self, bp_manifest: Dict[str, Any], rp_manifest: Dict[str, Any],
                               bp_path: Path, rp_path: Path) -> Tuple[Path, Path]:
        """
        Write manifests to disk in the appropriate pack directories.
        
        Args:
            bp_manifest: Behavior pack manifest data
            rp_manifest: Resource pack manifest data
            bp_path: Path to behavior pack directory
            rp_path: Path to resource pack directory
            
        Returns:
            Tuple of (bp_manifest_path, rp_manifest_path)
        """
        # Ensure directories exist
        bp_path.mkdir(parents=True, exist_ok=True)
        rp_path.mkdir(parents=True, exist_ok=True)
        
        # Write behavior pack manifest
        bp_manifest_path = bp_path / "manifest.json"
        with open(bp_manifest_path, 'w', encoding='utf-8') as f:
            json.dump(bp_manifest, f, indent=2, ensure_ascii=False)
        
        # Write resource pack manifest
        rp_manifest_path = rp_path / "manifest.json"
        with open(rp_manifest_path, 'w', encoding='utf-8') as f:
            json.dump(rp_manifest, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Manifests written to {bp_manifest_path} and {rp_manifest_path}")
        return bp_manifest_path, rp_manifest_path
    
    def generate_single_manifest(self, pack_type: PackType, mod_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a single manifest for either behavior or resource pack.
        
        Args:
            pack_type: Type of pack to generate
            mod_data: Mod information
            
        Returns:
            Generated manifest dictionary
        """
        mod_name = mod_data.get('name', 'Converted Mod')
        mod_description = mod_data.get('description', 'Converted from Java mod')
        mod_version = self._parse_version(mod_data.get('version', '1.0.0'))
        pack_uuid = str(uuid.uuid4())
        capabilities = self._determine_capabilities(mod_data)
        
        if pack_type == PackType.BEHAVIOR:
            manifest = self._create_behavior_manifest(
                mod_name, mod_description, mod_version, pack_uuid, capabilities
            )
        else:
            manifest = self._create_resource_manifest(
                mod_name, mod_description, mod_version, pack_uuid, capabilities
            )
        
        self._validate_manifest(manifest, pack_type.value)
        return manifest