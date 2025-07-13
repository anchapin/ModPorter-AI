"""
Bedrock Builder Agent for creating Bedrock add-on structures from Java mods
"""

import json
import uuid
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
from PIL import Image
import zipfile


class BedrockBuilderAgent:
    """Agent for building Bedrock add-ons from Java mod components."""
    
    def __init__(self):
        """Initialize the Bedrock Builder Agent."""
        pass
    
    def build_block_addon_mvp(self, registry_name: str, texture_path: str, jar_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Build a Bedrock add-on for a single block (MVP version).
        
        Args:
            registry_name: The block's registry name (e.g., "mymod:copper_block")
            texture_path: Path to the texture file within the JAR
            jar_path: Path to the source JAR file
            output_dir: Directory to create the add-on structure
            
        Returns:
            Dict with success status and build information
        """
        try:
            output_path = Path(output_dir)
            
            # Create behavior pack structure
            bp_dir = output_path / "behavior_pack"
            bp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create resource pack structure
            rp_dir = output_path / "resource_pack"
            rp_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract namespace and block name
            if ":" in registry_name:
                namespace, block_name = registry_name.split(":", 1)
            else:
                namespace = "minecraft"
                block_name = registry_name
            
            # Create behavior pack manifest
            bp_manifest = {
                "format_version": 2,
                "header": {
                    "name": f"{namespace.title()} Behavior Pack",
                    "description": f"Behavior pack for {block_name}",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0],
                    "min_engine_version": [1, 19, 0]
                },
                "modules": [{
                    "type": "data",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                }]
            }
            
            # Create resource pack manifest
            rp_manifest = {
                "format_version": 2,
                "header": {
                    "name": f"{namespace.title()} Resource Pack",
                    "description": f"Resource pack for {block_name}",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0],
                    "min_engine_version": [1, 19, 0]
                },
                "modules": [{
                    "type": "resources",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                }]
            }
            
            # Write manifests
            with open(bp_dir / "manifest.json", "w") as f:
                json.dump(bp_manifest, f, indent=2)
            
            with open(rp_dir / "manifest.json", "w") as f:
                json.dump(rp_manifest, f, indent=2)
            
            # Create block definition (behavior pack)
            blocks_dir = bp_dir / "blocks"
            blocks_dir.mkdir(exist_ok=True)
            
            block_definition = {
                "format_version": "1.20.10",
                "minecraft:block": {
                    "description": {
                        "identifier": registry_name,
                        "menu_category": {
                            "category": "construction"
                        }
                    },
                    "components": {
                        "minecraft:material_instances": {
                            "*": {
                                "texture": block_name
                            }
                        }
                    }
                }
            }
            
            with open(blocks_dir / f"{block_name}.json", "w") as f:
                json.dump(block_definition, f, indent=2)
            
            # Extract and process texture
            if texture_path:
                self._extract_and_process_texture(jar_path, texture_path, rp_dir, block_name)
            
            return {
                "success": True,
                "output_dir": str(output_path),
                "behavior_pack_dir": str(bp_dir),
                "resource_pack_dir": str(rp_dir),
                "registry_name": registry_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_and_process_texture(self, jar_path: str, texture_path: str, rp_dir: Path, block_name: str):
        """Extract texture from JAR and process it for Bedrock."""
        try:
            # Create textures directory
            textures_dir = rp_dir / "textures" / "blocks"
            textures_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract texture from JAR
            with zipfile.ZipFile(jar_path, 'r') as jar:
                if texture_path in jar.namelist():
                    # Extract to temporary file
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        temp_file.write(jar.read(texture_path))
                        temp_texture_path = temp_file.name
                    
                    try:
                        # Process with PIL to ensure correct format and size
                        with Image.open(temp_texture_path) as img:
                            # Ensure 16x16 size for Bedrock compatibility
                            if img.size != (16, 16):
                                img = img.resize((16, 16), Image.Resampling.NEAREST)
                            
                            # Convert to RGBA if not already
                            if img.mode != 'RGBA':
                                img = img.convert('RGBA')
                            
                            # Save to resource pack
                            output_texture_path = textures_dir / f"{block_name}.png"
                            img.save(output_texture_path, 'PNG')
                    
                    finally:
                        # Clean up temp file
                        os.unlink(temp_texture_path)
                        
        except Exception as e:
            # If texture processing fails, create a default texture
            self._create_default_texture(rp_dir, block_name)
    
    def _create_default_texture(self, rp_dir: Path, block_name: str):
        """Create a default 16x16 texture."""
        textures_dir = rp_dir / "textures" / "blocks"
        textures_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a simple magenta texture as placeholder
        img = Image.new('RGBA', (16, 16), (255, 0, 255, 255))
        output_texture_path = textures_dir / f"{block_name}.png"
        img.save(output_texture_path, 'PNG')