"""
Bedrock Builder Agent for generating Bedrock add-on files from Java mod analysis.
Enhanced for MVP functionality as specified in Issue #168.
"""

import os
import zipfile
import json
import tempfile
import uuid
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from PIL import Image
import logging
from jinja2 import Environment, FileSystemLoader, Template
from crewai.tools import tool

from src.models.smart_assumptions import SmartAssumptionEngine

logger = logging.getLogger(__name__)


class BedrockBuilderAgent:
    """
    Bedrock Builder Agent responsible for generating Bedrock add-on files
    from Java mod analysis results as specified in PRD Feature 2.
    """
    
    _instance = None
    
    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        
        # Initialize Jinja2 environment for templates
        templates_dir = Path(__file__).parent.parent / 'templates' / 'bedrock'
        self.jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))
        
        # Bedrock file structure templates
        self.bp_structure = {
            'manifest.json': self._create_bp_manifest,
            'blocks/': self._create_bp_blocks
        }
        
        self.rp_structure = {
            'manifest.json': self._create_rp_manifest,
            'blocks/': self._create_rp_blocks,
            'textures/blocks/': self._copy_textures
        }
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance of BedrockBuilderAgent"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            BedrockBuilderAgent.build_bedrock_structure_tool,
            BedrockBuilderAgent.generate_block_definitions_tool,
            BedrockBuilderAgent.convert_assets_tool,
            BedrockBuilderAgent.package_addon_tool
        ]
    
    def build_block_addon_mvp(self, registry_name: str, texture_path: str, jar_path: str, output_dir: str) -> Dict[str, Any]:
        """
        MVP-focused method to build Bedrock add-on from JavaAnalyzerAgent output.
        Implements requirements for Issue #168.
        
        Args:
            registry_name: Block registry name (e.g., "simple_copper:polished_copper")
            texture_path: Path to texture in JAR (e.g., "assets/mod/textures/block/texture.png")
            jar_path: Path to source JAR file
            output_dir: Output directory for .mcaddon file
            
        Returns:
            Dict with success status, file paths, and any errors
        """
        logger.info(f"MVP: Building block add-on for {registry_name}")
        
        result = {
            "success": False,
            "addon_path": None,
            "bp_files": [],
            "rp_files": [],
            "errors": []
        }
        
        try:
            # Parse registry name
            if ':' in registry_name:
                namespace, block_name = registry_name.split(':', 1)
            else:
                namespace = 'modporter'
                block_name = registry_name
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create BP and RP directories
                bp_path = temp_path / "BP"
                rp_path = temp_path / "RP"
                bp_path.mkdir()
                rp_path.mkdir()
                
                # Generate UUIDs for manifests
                bp_uuid = str(uuid.uuid4())
                rp_uuid = str(uuid.uuid4())
                
                # Build behavior pack
                bp_files = self._build_bp_mvp(bp_path, namespace, block_name, bp_uuid)
                result["bp_files"] = bp_files
                
                # Build resource pack with texture
                rp_files = self._build_rp_mvp(rp_path, namespace, block_name, rp_uuid, texture_path, jar_path)
                result["rp_files"] = rp_files
                
                # Package into .mcaddon
                addon_name = f"{namespace}_{block_name}"
                addon_path = Path(output_dir) / f"{addon_name}.mcaddon"
                addon_path.parent.mkdir(parents=True, exist_ok=True)
                
                self._package_addon_mvp(temp_path, addon_path)
                
                result["success"] = True
                result["addon_path"] = str(addon_path)
                
                logger.info(f"MVP: Successfully created {addon_path}")
                
        except Exception as e:
            logger.error(f"MVP build failed: {e}")
            result["errors"].append(f"Build failed: {str(e)}")
        
        return result
    
    def _build_bp_mvp(self, bp_path: Path, namespace: str, block_name: str, bp_uuid: str) -> List[str]:
        """Build behavior pack for MVP."""
        files_created = []
        
        # Create manifest.json
        manifest_data = {
            "pack_name": f"ModPorter {block_name.replace('_', ' ').title()}",
            "pack_description": f"Behavior pack for {block_name} block",
            "pack_uuid": bp_uuid,
            "module_uuid": str(uuid.uuid4()),
            "module_type": "data"
        }
        
        manifest_template = self.jinja_env.get_template('manifest.json')
        manifest_content = manifest_template.render(**manifest_data)
        
        manifest_file = bp_path / "manifest.json"
        manifest_file.write_text(manifest_content)
        files_created.append(str(manifest_file))
        
        # Create blocks directory and block JSON
        blocks_dir = bp_path / "blocks"
        blocks_dir.mkdir(exist_ok=True)
        
        block_data = {
            "namespace": namespace,
            "block_name": block_name,
            "texture_name": block_name
        }
        
        block_template = self.jinja_env.get_template('block_bp.json')
        block_content = block_template.render(**block_data)
        
        block_file = blocks_dir / f"{block_name}.json"
        block_file.write_text(block_content)
        files_created.append(str(block_file))
        
        return files_created
    
    def _build_rp_mvp(self, rp_path: Path, namespace: str, block_name: str, rp_uuid: str, 
                      texture_path: str, jar_path: str) -> List[str]:
        """Build resource pack for MVP."""
        files_created = []
        
        # Create manifest.json
        manifest_data = {
            "pack_name": f"ModPorter {block_name.replace('_', ' ').title()} Resources",
            "pack_description": f"Resource pack for {block_name} block",
            "pack_uuid": rp_uuid,
            "module_uuid": str(uuid.uuid4()),
            "module_type": "resources"
        }
        
        manifest_template = self.jinja_env.get_template('manifest.json')
        manifest_content = manifest_template.render(**manifest_data)
        
        manifest_file = rp_path / "manifest.json"
        manifest_file.write_text(manifest_content)
        files_created.append(str(manifest_file))
        
        # Create blocks directory and block JSON
        blocks_dir = rp_path / "blocks"
        blocks_dir.mkdir(exist_ok=True)
        
        block_data = {
            "namespace": namespace,
            "block_name": block_name,
            "texture_name": block_name
        }
        
        block_template = self.jinja_env.get_template('block_rp.json')
        block_content = block_template.render(**block_data)
        
        block_file = blocks_dir / f"{block_name}.json"
        block_file.write_text(block_content)
        files_created.append(str(block_file))
        
        # Copy and process texture
        texture_files = self._copy_texture_mvp(rp_path, block_name, texture_path, jar_path)
        files_created.extend(texture_files)
        
        return files_created
    
    def _copy_texture_mvp(self, rp_path: Path, block_name: str, texture_path: str, jar_path: str) -> List[str]:
        """Copy and resize texture from JAR to resource pack."""
        files_created = []
        
        try:
            # Create textures directory
            textures_dir = rp_path / "textures" / "blocks"
            textures_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract texture from JAR
            with zipfile.ZipFile(jar_path, 'r') as jar:
                if texture_path in jar.namelist():
                    # Read texture data
                    texture_data = jar.read(texture_path)
                    
                    # Process with Pillow
                    with tempfile.NamedTemporaryFile() as temp_file:
                        temp_file.write(texture_data)
                        temp_file.flush()
                        
                        # Open and resize to 16x16 (Bedrock standard)
                        with Image.open(temp_file.name) as img:
                            # Convert to RGBA for consistency
                            img = img.convert('RGBA')
                            
                            # Resize to 16x16 if needed
                            if img.size != (16, 16):
                                img = img.resize((16, 16), Image.Resampling.NEAREST)
                                logger.info(f"Resized texture from {img.size} to 16x16")
                            
                            # Save to resource pack
                            output_path = textures_dir / f"{block_name}.png"
                            img.save(output_path, 'PNG')
                            files_created.append(str(output_path))
                            
                            logger.info(f"Texture copied: {texture_path} -> {output_path}")
                else:
                    logger.warning(f"Texture not found in JAR: {texture_path}")
                    
        except Exception as e:
            logger.error(f"Error copying texture: {e}")
            raise
        
        return files_created
    
    def _package_addon_mvp(self, temp_path: Path, addon_path: Path) -> None:
        """Package BP and RP into .mcaddon file."""
        try:
            # Create zip file with .mcaddon extension
            with zipfile.ZipFile(addon_path, 'w', zipfile.ZIP_DEFLATED) as addon_zip:
                # Add all files from temp directory
                for root, dirs, files in os.walk(temp_path):
                    for file in files:
                        file_path = Path(root) / file
                        # Calculate relative path from temp_path
                        rel_path = file_path.relative_to(temp_path)
                        addon_zip.write(file_path, rel_path)
                        
            logger.info(f"Packaged add-on: {addon_path} ({addon_path.stat().st_size} bytes)")
            
        except Exception as e:
            logger.error(f"Error packaging add-on: {e}")
            raise

    # Legacy methods for compatibility with existing code
    def _create_bp_manifest(self, analysis_data):
        """Legacy method for compatibility."""
        return {}
    
    def _create_bp_blocks(self, analysis_data):
        """Legacy method for compatibility."""
        return {}
    
    def _create_rp_manifest(self, analysis_data):
        """Legacy method for compatibility."""
        return {}
    
    def _create_rp_blocks(self, analysis_data):
        """Legacy method for compatibility."""
        return {}
    
    def _copy_textures(self, analysis_data):
        """Legacy method for compatibility."""
        return []

    @tool
    @staticmethod
    def build_bedrock_structure_tool(structure_data: str) -> str:
        """Build basic Bedrock addon structure."""
        # Implementation placeholder
        return json.dumps({"success": True, "message": "Structure created"})

    @tool
    @staticmethod
    def generate_block_definitions_tool(block_data: str) -> str:
        """Generate Bedrock block definition files."""
        # Implementation placeholder
        return json.dumps({"success": True, "message": "Block definitions generated"})

    @tool
    @staticmethod
    def convert_assets_tool(asset_data: str) -> str:
        """Convert assets to Bedrock format."""
        # Implementation placeholder
        return json.dumps({"success": True, "message": "Assets converted"})

    @tool
    @staticmethod
    def package_addon_tool(package_data: str) -> str:
        """Package addon into .mcaddon file."""
        # Implementation placeholder
        return json.dumps({"success": True, "message": "Addon packaged"})
>>>>>>> main
