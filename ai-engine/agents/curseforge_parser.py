"""
CurseForge Modpack Manifest Parser
Parses CurseForge modpack manifest files for modpack conversion support.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class CurseForgeManifestParser:
    """
    Parser for CurseForge modpack manifest files.
    
    Handles parsing of manifest.json files from CurseForge modpacks,
    extracting mod information, dependencies, and metadata.
    """
    
    # CurseForge manifest version constants
    SUPPORTED_VERSIONS = [1, 2]
    
    def __init__(self):
        self.manifest: Optional[Dict[str, Any]] = None
        self.mods: List[Dict[str, Any]] = []
        self.overrides: List[str] = []
        self.metadata: Dict[str, Any] = {}
    
    def parse_manifest(self, manifest_path: Path) -> Dict[str, Any]:
        """
        Parse a CurseForge manifest.json file.
        
        Args:
            manifest_path: Path to the manifest.json file
            
        Returns:
            Dictionary containing parsed manifest data
            
        Raises:
            FileNotFoundError: If manifest file doesn't exist
            ValueError: If manifest format is invalid
        """
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                self.manifest = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in manifest: {e}")
        
        # Validate manifest structure
        self._validate_manifest()
        
        # Extract data
        self._extract_metadata()
        self._extract_mods()
        self._extract_overrides()
        
        return self.get_parsed_data()
    
    def parse_from_string(self, manifest_content: str) -> Dict[str, Any]:
        """
        Parse a CurseForge manifest from a string.
        
        Args:
            manifest_content: JSON string content
            
        Returns:
            Dictionary containing parsed manifest data
        """
        try:
            self.manifest = json.loads(manifest_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in manifest content: {e}")
        
        self._validate_manifest()
        self._extract_metadata()
        self._extract_mods()
        self._extract_overrides()
        
        return self.get_parsed_data()
    
    def _validate_manifest(self) -> None:
        """Validate the manifest structure."""
        if not self.manifest:
            raise ValueError("Manifest is empty")
        
        # Check required fields
        if 'manifestType' not in self.manifest:
            raise ValueError("Missing required field: manifestType")
        
        if self.manifest.get('manifestType') != 'minecraftModpack':
            raise ValueError(f"Unsupported manifest type: {self.manifest.get('manifestType')}")
        
        # Check manifest version
        manifest_version = self.manifest.get('manifestVersion', 1)
        if manifest_version not in self.SUPPORTED_VERSIONS:
            raise ValueError(f"Unsupported manifest version: {manifest_version}")
        
        # Check for mods array
        if 'files' not in self.manifest:
            raise ValueError("Missing required field: files")
    
    def _extract_metadata(self) -> None:
        """Extract metadata from the manifest."""
        if not self.manifest:
            return
        
        self.metadata = {
            'name': self.manifest.get('name', 'Unnamed Modpack'),
            'version': self.manifest.get('version', '1.0.0'),
            'author': self.manifest.get('author', 'Unknown'),
            'description': self.manifest.get('description', ''),
            'manifest_version': self.manifest.get('manifestVersion', 1),
            'minecraft_version': self.manifest.get('minecraft', {}).get('version', ''),
            'modloader': self.manifest.get('minecraft', {}).get('modLoaders', []),
            'manifest_type': self.manifest.get('manifestType', ''),
        }
        
        # Extract overrides path
        overrides_path = self.manifest.get('overrides', '')
        if overrides_path:
            self.metadata['overrides_path'] = overrides_path
    
    def _extract_mods(self) -> None:
        """Extract mod information from the files array."""
        if not self.manifest:
            return
        
        self.mods = []
        files = self.manifest.get('files', [])
        
        for file_entry in files:
            mod_info = {
                'project_id': file_entry.get('projectID'),
                'file_id': file_entry.get('fileID'),
                'name': file_entry.get('name', ''),
                'version': file_entry.get('version', ''),
                'filename': file_entry.get('filename', ''),
                'path': file_entry.get('path', ''),
                'dependencies': self._extract_dependencies(file_entry),
                'required': file_entry.get('required', True),
            }
            self.mods.append(mod_info)
    
    def _extract_dependencies(self, file_entry: Dict[str, Any]) -> List[Dict[str, int]]:
        """Extract dependency information from a file entry."""
        dependencies = file_entry.get('dependencies', [])
        return [{'project_id': dep.get('projectID'), 'file_id': dep.get('fileID')} 
                for dep in dependencies if isinstance(dep, dict)]
    
    def _extract_overrides(self) -> None:
        """Extract overrides list from manifest."""
        if not self.manifest:
            return
        
        overrides_path = self.manifest.get('overrides', '')
        self.overrides = self.manifest.get('overrides', []) if isinstance(self.manifest.get('overrides'), list) else []
        
        if overrides_path:
            self.metadata['overrides_path'] = overrides_path
    
    def get_parsed_data(self) -> Dict[str, Any]:
        """
        Get the complete parsed data.
        
        Returns:
            Dictionary containing all parsed manifest data
        """
        return {
            'metadata': self.metadata,
            'mods': self.mods,
            'mod_count': len(self.mods),
            'overrides': self.overrides,
            'is_server_modpack': self._is_server_modpack(),
            'is_client_modpack': self._is_client_modpack(),
        }
    
    def _is_server_modpack(self) -> bool:
        """Check if this is a server modpack."""
        if not self.manifest:
            return False
        
        # Check for server overrides directory
        return 'server' in str(self.manifest.get('overrides', '')).lower()
    
    def _is_client_modpack(self) -> bool:
        """Check if this is a client modpack."""
        if not self.manifest:
            return False
        
        # Check for client overrides directory
        return 'client' in str(self.manifest.get('overrides', '')).lower()
    
    def get_mod_by_project_id(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get mod information by project ID."""
        for mod in self.mods:
            if mod.get('project_id') == project_id:
                return mod
        return None
    
    def get_mod_dependencies(self, project_id: int) -> List[Dict[str, Any]]:
        """Get all dependencies for a specific mod."""
        mod = self.get_mod_by_project_id(project_id)
        if mod:
            return mod.get('dependencies', [])
        return []
    
    def get_required_mods(self) -> List[Dict[str, Any]]:
        """Get all required mods."""
        return [mod for mod in self.mods if mod.get('required', True)]
    
    def get_optional_mods(self) -> List[Dict[str, Any]]:
        """Get all optional mods."""
        return [mod for mod in self.mods if not mod.get('required', True)]


class CurseForgeParserAgent:
    """
    CrewAI agent for parsing CurseForge modpack manifests.
    """
    
    def __init__(self):
        self.parser = CurseForgeManifestParser()
        self.tools = []
    
    def get_tools(self):
        """Get the tools for this agent."""
        return self.tools
    
    def parse_modpack(self, modpack_path: Path) -> Dict[str, Any]:
        """
        Parse a CurseForge modpack.
        
        Args:
            modpack_path: Path to the modpack directory or zip file
            
        Returns:
            Parsed modpack data
        """
        manifest_path = modpack_path / 'manifest.json'
        
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found in {modpack_path}")
        
        return self.parser.parse_manifest(manifest_path)
