"""
CurseForge Modpack Manifest Parser

Parses CurseForge modpack manifest files (manifest.json) for modpack conversion support.
API Documentation: https://docs.curseforge.com/en/

Manifest Structure:
{
  "manifestType": "minecraftModpack",
  "manifestVersion": 1,
  "name": "Modpack Name",
  "version": "1.0.0",
  "author": "Author Name",
  "files": [
    {
      "projectID": 123456,
      "fileID": 789012,
      "required": true
    }
  ],
  "overrides": "overrides",
  "gameVersion": ["1.20.1", "1.20.2"]
}
"""

import json
import zipfile
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ModpackFile:
    """Represents a single mod file in a modpack."""
    project_id: int
    file_id: int
    required: bool = True
    source: str = "curseforge"  # or "modrinth"


@dataclass
class CurseForgeManifest:
    """Parsed CurseForge modpack manifest."""
    manifest_type: str
    manifest_version: int
    name: str
    version: str
    author: str
    files: List[ModpackFile] = field(default_factory=list)
    overrides: Optional[str] = None
    game_versions: List[str] = field(default_factory=list)
    original_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def mod_count(self) -> int:
        """Get the total number of mods in the modpack."""
        return len(self.files)
    
    @property
    def required_mod_count(self) -> int:
        """Get the number of required mods."""
        return sum(1 for f in self.files if f.required)


@dataclass
class ParsedModpack:
    """Complete parsed modpack information."""
    manifest: CurseForgeManifest
    is_client_side: bool = True
    is_server_side: bool = True
    game_version: Optional[str] = None
    
    def get_mod_ids(self) -> List[int]:
        """Get list of project IDs."""
        return [f.project_id for f in self.manifest.files]
    
    def get_required_mod_ids(self) -> List[int]:
        """Get list of required project IDs."""
        return [f.project_id for f in self.manifest.files if f.required]


class CurseForgeModpackParser:
    """Parser for CurseForge modpack manifest files."""
    
    SUPPORTED_MANIFEST_VERSIONS = [1]
    SUPPORTED_MANIFEST_TYPES = ["minecraftModpack"]
    
    def __init__(self):
        self.logger = logger
    
    def parse_from_file(self, file_path: Path) -> ParsedModpack:
        """
        Parse a CurseForge modpack manifest from a file.
        
        Args:
            file_path: Path to the manifest.json file or a .zip/.cfmodpack file
            
        Returns:
            ParsedModpack object with parsed manifest data
            
        Raises:
            ValueError: If the manifest is invalid or unsupported
            FileNotFoundError: If the file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check if it's a zip file (packwiz, curseforge pack)
        if file_path.suffix.lower() in ['.zip', '.cfmodpack', '.mrpack']:
            return self._parse_from_zip(file_path)
        
        # Otherwise, assume it's a direct manifest.json
        return self._parse_from_manifest(file_path)
    
    def _parse_from_manifest(self, manifest_path: Path) -> ParsedModpack:
        """Parse a direct manifest.json file."""
        self.logger.info(f"Parsing manifest from: {manifest_path}")
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in manifest: {e}")
        
        return self._parse_manifest_data(data)
    
    def _parse_from_zip(self, zip_path: Path) -> ParsedModpack:
        """Parse a modpack from a ZIP archive."""
        self.logger.info(f"Parsing modpack from ZIP: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Look for manifest.json in various possible locations
            manifest_locations = [
                'manifest.json',
                'manifest.json',  # In root
                'pack/manifest.json',
                'minecraft/manifest.json',
            ]
            
            manifest_data = None
            for location in manifest_locations:
                try:
                    with zf.open(location) as f:
                        manifest_data = json.load(f)
                    self.logger.info(f"Found manifest at: {location}")
                    break
                except KeyError:
                    continue
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid JSON at {location}: {e}")
                    continue
            
            if manifest_data is None:
                # Try to find any manifest.json
                for name in zf.namelist():
                    if name.endswith('manifest.json'):
                        try:
                            with zf.open(name) as f:
                                manifest_data = json.load(f)
                            self.logger.info(f"Found manifest at: {name}")
                            break
                        except (KeyError, json.JSONDecodeError):
                            continue
                
            if manifest_data is None:
                raise ValueError(f"No manifest.json found in {zip_path}")
        
        return self._parse_manifest_data(manifest_data)
    
    def _parse_manifest_data(self, data: Dict[str, Any]) -> ParsedModpack:
        """Parse manifest data dictionary into structured objects."""
        
        # Validate manifest type
        manifest_type = data.get('manifestType', '')
        if manifest_type not in self.SUPPORTED_MANIFEST_TYPES:
            raise ValueError(
                f"Unsupported manifest type: {manifest_type}. "
                f"Supported types: {self.SUPPORTED_MANIFEST_TYPES}"
            )
        
        # Validate manifest version
        manifest_version = data.get('manifestVersion', 0)
        if manifest_version not in self.SUPPORTED_MANIFEST_VERSIONS:
            raise ValueError(
                f"Unsupported manifest version: {manifest_version}. "
                f"Supported versions: {self.SUPPORTED_MANIFEST_VERSIONS}"
            )
        
        # Extract basic info
        name = data.get('name', 'Unnamed Modpack')
        version = data.get('version', '1.0.0')
        author = data.get('author', 'Unknown')
        overrides = data.get('overrides')
        
        # Parse game versions
        game_versions = data.get('gameVersion', [])
        if isinstance(game_versions, str):
            game_versions = [game_versions]
        
        # Parse files
        files = []
        for file_entry in data.get('files', []):
            mod_file = ModpackFile(
                project_id=file_entry.get('projectID', 0),
                file_id=file_entry.get('fileID', 0),
                required=file_entry.get('required', True),
                source='curseforge'
            )
            if mod_file.project_id > 0:
                files.append(mod_file)
        
        # Create manifest object
        manifest = CurseForgeManifest(
            manifest_type=manifest_type,
            manifest_version=manifest_version,
            name=name,
            version=version,
            author=author,
            files=files,
            overrides=overrides,
            game_versions=game_versions,
            original_data=data
        )
        
        # Determine if client or server modpack
        # CurseForge packs are typically client-side by default
        is_client_side = True
        is_server_side = True
        
        # Check for server-specific indicators
        if 'server' in name.lower() or 'server' in str(data.get('description', '')).lower():
            is_client_side = False
        
        # Get primary game version
        game_version = game_versions[0] if game_versions else None
        
        self.logger.info(
            f"Parsed modpack '{name}' v{version}: "
            f"{len(files)} mods, {manifest.required_mod_count} required"
        )
        
        return ParsedModpack(
            manifest=manifest,
            is_client_side=is_client_side,
            is_server_side=is_server_side,
            game_version=game_version
        )
    
    def parse_from_url(self, url: str) -> Dict[str, Any]:
        """
        Parse a CurseForge modpack URL to extract information.
        
        Args:
            url: CurseForge modpack URL
            
        Returns:
            Dictionary with parsed URL information
        """
        import re
        
        # Pattern for CurseForge modpack URLs
        patterns = [
            r'curseforge\.com/minecraft/modpacks/([^/?]+)',
            r'curseforge\.com/minecraft/mc-mods/([^/?]+)',  # Single mod
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                slug = match.group(1)
                return {
                    "platform": "curseforge",
                    "type": "modpack" if "modpacks" in pattern else "mod",
                    "slug": slug,
                    "url": f"https://www.curseforge.com/{'minecraft/modpacks' if 'modpacks' in pattern else 'minecraft/mc-mods'}/{slug}",
                }
        
        return {"platform": "unknown", "url": url}
    
    def get_dependency_tree(
        self, 
        modpack: ParsedModpack, 
        include_optional: bool = False
    ) -> Dict[int, List[int]]:
        """
        Get dependency tree for mods in the modpack.
        
        Note: CurseForge manifest doesn't include transitive dependencies.
        This would require additional API calls to get full dependency info.
        
        Args:
            modpack: The parsed modpack
            include_optional: Whether to include optional dependencies
            
        Returns:
            Dictionary mapping project IDs to their dependency project IDs
        """
        # For now, return just direct dependencies
        # Full dependency resolution would require CurseForge API calls
        dependencies: Dict[int, List[int]] = {}
        
        for mod_file in modpack.manifest.files:
            if mod_file.required or include_optional:
                # Placeholder - actual dependencies would come from API
                dependencies[mod_file.project_id] = []
        
        return dependencies


class ModrinthModpackParser:
    """Parser for Modrinth modpack format (.mrpack)."""
    
    def __init__(self):
        self.logger = logger
    
    def parse_from_file(self, file_path: Path) -> ParsedModpack:
        """
        Parse a Modrinth modpack manifest.
        
        Args:
            file_path: Path to the .mrpack file
            
        Returns:
            ParsedModpack object
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.suffix.lower() != '.mrpack':
            raise ValueError(f"Expected .mrpack file, got: {file_path.suffix}")
        
        return self._parse_mrpack(file_path)
    
    def _parse_mrpack(self, mrpack_path: Path) -> ParsedModpack:
        """Parse a Modrinth modpack (.mrpack is a ZIP file)."""
        self.logger.info(f"Parsing Modrinth modpack from: {mrpack_path}")
        
        with zipfile.ZipFile(mrpack_path, 'r') as zf:
            # Look for modrinth.index.json
            try:
                with zf.open('modrinth.index.json') as f:
                    data = json.load(f)
            except KeyError:
                raise ValueError("Invalid .mrpack: missing modrinth.index.json")
        
        # Parse the Modrinth index format
        name = data.get('name', 'Unnamed Modpack')
        version = data.get('version', '1.0.0')
        
        # Modrinth uses a single gameVersion (string), not a list
        game_version_str = data.get('gameVersion', '')
        game_versions = [game_version_str] if game_version_str else []
        
        # Parse files
        files = []
        for file_entry in data.get('files', []):
            # Modrinth uses hashes and paths instead of IDs
            project_id = file_entry.get('projectID', 0)
            file_id = file_entry.get('fileID', 0)
            
            mod_file = ModpackFile(
                project_id=project_id,
                file_id=file_id,
                required=file_entry.get('env', {}).get('required', True),
                source='modrinth'
            )
            if project_id:
                files.append(mod_file)
        
        manifest = CurseForgeManifest(
            manifest_type="modrinthModpack",
            manifest_version=1,
            name=name,
            version=version,
            author=data.get('author', 'Unknown'),
            files=files,
            overrides=data.get('overrides'),
            game_versions=game_versions,
            original_data=data
        )
        
        return ParsedModpack(
            manifest=manifest,
            is_client_side=True,
            is_server_side=True,
            game_version=game_version_str if game_version_str else None
        )


# Singleton instances
curseforge_parser = CurseForgeModpackParser()
modrinth_parser = ModrinthModpackParser()


def parse_modpack(file_path: Path) -> ParsedModpack:
    """
    Convenience function to parse any supported modpack format.
    
    Args:
        file_path: Path to the modpack file
        
    Returns:
        ParsedModpack object
    """
    suffix = file_path.suffix.lower()
    
    if suffix == '.mrpack':
        return modrinth_parser.parse_from_file(file_path)
    else:
        # Default to CurseForge format
        return curseforge_parser.parse_from_file(file_path)
