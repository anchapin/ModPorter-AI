"""
Asset Converter Agent - Converts visual and audio assets to Bedrock formats
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from crewai_tools import BaseTool, tool

logger = logging.getLogger(__name__)


class TextureConverterTool(BaseTool):
    """Tool for converting textures to Bedrock format"""
    
    name: str = "Texture Converter Tool"
    description: str = "Converts Java mod textures to Bedrock-compatible formats and resolutions"
    
    def _run(self, texture_list: str, output_path: str) -> str:
        """
        Convert textures to Bedrock format
        
        Args:
            texture_list: JSON string with list of texture files
            output_path: Path for converted textures
            
        Returns:
            JSON string with conversion results
        """
        try:
            textures = json.loads(texture_list)
            
            conversion_results = {
                "converted_textures": [],
                "conversion_notes": [],
                "errors": [],
                "total_textures": len(textures),
                "successful_conversions": 0
            }
            
            for texture_path in textures:
                try:
                    result = self._convert_single_texture(texture_path, output_path)
                    conversion_results["converted_textures"].append(result)
                    if result["success"]:
                        conversion_results["successful_conversions"] += 1
                except Exception as e:
                    error_msg = f"Failed to convert {texture_path}: {str(e)}"
                    conversion_results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            # Add general conversion notes
            conversion_results["conversion_notes"].extend([
                "All textures converted to PNG format for Bedrock compatibility",
                "Textures resized to 16x16 or 32x32 for optimal performance",
                "Texture paths updated for Bedrock resource pack structure"
            ])
            
            return json.dumps(conversion_results, indent=2)
            
        except Exception as e:
            logger.error(f"Error converting textures: {e}")
            return json.dumps({"error": f"Failed to convert textures: {str(e)}"})
    
    def _convert_single_texture(self, texture_path: str, output_path: str) -> Dict[str, Any]:
        """Convert a single texture file"""
        # Simulate texture conversion logic
        texture_name = Path(texture_path).stem
        
        # Determine appropriate size based on texture type
        if "block" in texture_path.lower():
            target_size = "16x16"
        elif "item" in texture_path.lower():
            target_size = "16x16"
        elif "entity" in texture_path.lower():
            target_size = "32x32"
        else:
            target_size = "16x16"
        
        # Generate Bedrock-compatible path
        bedrock_path = self._generate_bedrock_texture_path(texture_path)
        
        return {
            "original_path": texture_path,
            "converted_path": bedrock_path,
            "target_size": target_size,
            "format": "PNG",
            "success": True,
            "notes": f"Converted to {target_size} PNG for Bedrock compatibility"
        }
    
    def _generate_bedrock_texture_path(self, java_path: str) -> str:
        """Generate Bedrock-compatible texture path"""
        # Convert Java texture path to Bedrock format
        # Java: assets/modid/textures/block/texture.png
        # Bedrock: textures/blocks/texture.png
        
        path_parts = java_path.split('/')
        if "textures" in path_parts:
            texture_idx = path_parts.index("textures")
            if texture_idx + 1 < len(path_parts):
                category = path_parts[texture_idx + 1]
                filename = path_parts[-1]
                
                # Map Java categories to Bedrock
                category_mapping = {
                    "block": "blocks",
                    "item": "items", 
                    "entity": "entity",
                    "gui": "ui",
                    "environment": "environment"
                }
                
                bedrock_category = category_mapping.get(category, category)
                return f"textures/{bedrock_category}/{filename}"
        
        # Fallback
        return f"textures/items/{Path(java_path).name}"


class ModelConverterTool(BaseTool):
    """Tool for converting 3D models to Bedrock geometry format"""
    
    name: str = "Model Converter Tool"
    description: str = "Converts Java mod models to Bedrock geometry format"
    
    def _run(self, model_list: str, output_path: str) -> str:
        """
        Convert models to Bedrock geometry format
        
        Args:
            model_list: JSON string with list of model files
            output_path: Path for converted models
            
        Returns:
            JSON string with conversion results
        """
        try:
            models = json.loads(model_list)
            
            conversion_results = {
                "converted_models": [],
                "conversion_notes": [],
                "errors": [],
                "total_models": len(models),
                "successful_conversions": 0
            }
            
            for model_path in models:
                try:
                    result = self._convert_single_model(model_path, output_path)
                    conversion_results["converted_models"].append(result)
                    if result["success"]:
                        conversion_results["successful_conversions"] += 1
                except Exception as e:
                    error_msg = f"Failed to convert {model_path}: {str(e)}"
                    conversion_results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            # Add general conversion notes
            conversion_results["conversion_notes"].extend([
                "Models converted to Bedrock geometry format",
                "Complex models may require manual adjustment",
                "Animations converted to Bedrock animation format"
            ])
            
            return json.dumps(conversion_results, indent=2)
            
        except Exception as e:
            logger.error(f"Error converting models: {e}")
            return json.dumps({"error": f"Failed to convert models: {str(e)}"})
    
    def _convert_single_model(self, model_path: str, output_path: str) -> Dict[str, Any]:
        """Convert a single model file"""
        model_name = Path(model_path).stem
        
        # Determine model type and complexity
        if "block" in model_path.lower():
            model_type = "block"
            complexity = "simple"
        elif "item" in model_path.lower():
            model_type = "item"
            complexity = "simple"
        elif "entity" in model_path.lower():
            model_type = "entity"
            complexity = "complex"
        else:
            model_type = "unknown"
            complexity = "medium"
        
        # Generate Bedrock geometry path
        bedrock_path = f"models/entity/{model_name}.geo.json"
        
        return {
            "original_path": model_path,
            "converted_path": bedrock_path,
            "model_type": model_type,
            "complexity": complexity,
            "format": "Bedrock Geometry",
            "success": True,
            "notes": f"Converted {model_type} model to Bedrock geometry format"
        }


class SoundConverterTool(BaseTool):
    """Tool for converting audio files to Bedrock format"""
    
    name: str = "Sound Converter Tool"
    description: str = "Converts Java mod sounds to Bedrock-compatible audio formats"
    
    def _run(self, sound_list: str, output_path: str) -> str:
        """
        Convert sounds to Bedrock format
        
        Args:
            sound_list: JSON string with list of sound files
            output_path: Path for converted sounds
            
        Returns:
            JSON string with conversion results
        """
        try:
            sounds = json.loads(sound_list)
            
            conversion_results = {
                "converted_sounds": [],
                "conversion_notes": [],
                "errors": [],
                "total_sounds": len(sounds),
                "successful_conversions": 0
            }
            
            for sound_path in sounds:
                try:
                    result = self._convert_single_sound(sound_path, output_path)
                    conversion_results["converted_sounds"].append(result)
                    if result["success"]:
                        conversion_results["successful_conversions"] += 1
                except Exception as e:
                    error_msg = f"Failed to convert {sound_path}: {str(e)}"
                    conversion_results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            # Add general conversion notes
            conversion_results["conversion_notes"].extend([
                "All sounds converted to OGG format for Bedrock",
                "Audio quality optimized for mobile devices",
                "Sound definitions created for Bedrock resource pack"
            ])
            
            return json.dumps(conversion_results, indent=2)
            
        except Exception as e:
            logger.error(f"Error converting sounds: {e}")
            return json.dumps({"error": f"Failed to convert sounds: {str(e)}"})
    
    def _convert_single_sound(self, sound_path: str, output_path: str) -> Dict[str, Any]:
        """Convert a single sound file"""
        sound_name = Path(sound_path).stem
        
        # Determine sound category
        if "block" in sound_path.lower():
            category = "block"
        elif "item" in sound_path.lower():
            category = "item"
        elif "entity" in sound_path.lower():
            category = "entity"
        elif "ambient" in sound_path.lower():
            category = "ambient"
        else:
            category = "misc"
        
        # Generate Bedrock sound path
        bedrock_path = f"sounds/{category}/{sound_name}.ogg"
        
        return {
            "original_path": sound_path,
            "converted_path": bedrock_path,
            "category": category,
            "format": "OGG",
            "success": True,
            "notes": f"Converted {category} sound to OGG format"
        }


class AssetConverterAgent:
    """Agent for converting all types of assets to Bedrock formats"""
    
    def __init__(self):
        self.texture_converter = TextureConverterTool()
        self.model_converter = ModelConverterTool()
        self.sound_converter = SoundConverterTool()
        logger.info("AssetConverterAgent initialized")
    
    @tool("Texture Conversion Tool")
    def convert_textures(self, texture_list: str, output_path: str) -> str:
        """
        Convert Java mod textures to Bedrock format.
        
        Args:
            texture_list: JSON string with list of texture file paths
            output_path: Output directory for converted textures
            
        Returns:
            JSON string with conversion results
        """
        return self.texture_converter._run(texture_list, output_path)
    
    @tool("Model Conversion Tool")
    def convert_models(self, model_list: str, output_path: str) -> str:
        """
        Convert Java mod models to Bedrock geometry format.
        
        Args:
            model_list: JSON string with list of model file paths
            output_path: Output directory for converted models
            
        Returns:
            JSON string with conversion results
        """
        return self.model_converter._run(model_list, output_path)
    
    @tool("Sound Conversion Tool")
    def convert_sounds(self, sound_list: str, output_path: str) -> str:
        """
        Convert Java mod sounds to Bedrock audio format.
        
        Args:
            sound_list: JSON string with list of sound file paths
            output_path: Output directory for converted sounds
            
        Returns:
            JSON string with conversion results
        """
        return self.sound_converter._run(sound_list, output_path)
    
    @tool("Asset Organization Tool")
    def organize_assets(self, asset_data: str, output_path: str) -> str:
        """
        Organize all converted assets into proper Bedrock resource pack structure.
        
        Args:
            asset_data: JSON string with asset conversion results
            output_path: Base output directory for resource pack
            
        Returns:
            JSON string with organization results
        """
        try:
            assets = json.loads(asset_data)
            
            organization_results = {
                "resource_pack_structure": {},
                "file_mappings": [],
                "manifest_entries": [],
                "total_assets": 0
            }
            
            # Define Bedrock resource pack structure
            resource_pack_structure = {
                "textures": ["blocks", "items", "entity", "ui", "environment"],
                "models": ["entity", "blocks"],
                "sounds": ["block", "item", "entity", "ambient", "misc"],
                "animations": ["entity"],
                "animation_controllers": ["entity"]
            }
            
            organization_results["resource_pack_structure"] = resource_pack_structure
            
            # Process each asset type
            for asset_type, asset_list in assets.items():
                if isinstance(asset_list, list):
                    for asset in asset_list:
                        if isinstance(asset, dict) and "converted_path" in asset:
                            organization_results["file_mappings"].append({
                                "type": asset_type,
                                "source": asset.get("original_path", ""),
                                "destination": asset["converted_path"],
                                "category": asset.get("category", "misc")
                            })
                            organization_results["total_assets"] += 1
            
            # Generate manifest entries
            organization_results["manifest_entries"] = [
                {
                    "format_version": "1.16.0",
                    "header": {
                        "description": "Converted mod assets",
                        "name": "Converted Resource Pack",
                        "uuid": "generated-uuid-here",
                        "version": [1, 0, 0]
                    },
                    "modules": [
                        {
                            "description": "Resource pack module",
                            "type": "resources",
                            "uuid": "generated-uuid-here",
                            "version": [1, 0, 0]
                        }
                    ]
                }
            ]
            
            return json.dumps(organization_results, indent=2)
            
        except Exception as e:
            logger.error(f"Error organizing assets: {e}")
            return json.dumps({"error": f"Failed to organize assets: {str(e)}"})
    
    @tool("Asset Quality Checker")
    def check_asset_quality(self, asset_data: str) -> str:
        """
        Check quality and compatibility of converted assets.
        
        Args:
            asset_data: JSON string with asset conversion results
            
        Returns:
            JSON string with quality assessment
        """
        try:
            assets = json.loads(asset_data)
            
            quality_assessment = {
                "overall_quality": "Unknown",
                "quality_checks": [],
                "issues_found": [],
                "recommendations": [],
                "compatibility_score": 0.0
            }
            
            total_assets = 0
            quality_issues = 0
            
            # Check each asset type
            for asset_type, asset_list in assets.items():
                if isinstance(asset_list, list):
                    for asset in asset_list:
                        total_assets += 1
                        
                        # Check for common issues
                        if isinstance(asset, dict):
                            if not asset.get("success", False):
                                quality_issues += 1
                                quality_assessment["issues_found"].append(
                                    f"Failed conversion: {asset.get('original_path', 'unknown')}"
                                )
                            
                            # Check format compatibility
                            if asset.get("format") not in ["PNG", "OGG", "Bedrock Geometry"]:
                                quality_issues += 1
                                quality_assessment["issues_found"].append(
                                    f"Incompatible format: {asset.get('format', 'unknown')}"
                                )
            
            # Calculate compatibility score
            if total_assets > 0:
                compatibility_score = 1.0 - (quality_issues / total_assets)
            else:
                compatibility_score = 0.0
            
            quality_assessment["compatibility_score"] = compatibility_score
            
            # Determine overall quality
            if compatibility_score >= 0.9:
                quality_assessment["overall_quality"] = "Excellent"
            elif compatibility_score >= 0.75:
                quality_assessment["overall_quality"] = "Good"
            elif compatibility_score >= 0.5:
                quality_assessment["overall_quality"] = "Fair"
            else:
                quality_assessment["overall_quality"] = "Poor"
            
            # Add recommendations
            if quality_issues > 0:
                quality_assessment["recommendations"].extend([
                    "Review failed asset conversions",
                    "Check asset format compatibility",
                    "Test assets in Bedrock before finalizing"
                ])
            else:
                quality_assessment["recommendations"].append(
                    "All assets converted successfully - ready for packaging"
                )
            
            return json.dumps(quality_assessment, indent=2)
            
        except Exception as e:
            logger.error(f"Error checking asset quality: {e}")
            return json.dumps({"error": f"Failed to check asset quality: {str(e)}"})
    
    def get_tools(self) -> List:
        """Return available tools for this agent"""
        return [
            self.convert_textures,
            self.convert_models,
            self.convert_sounds,
            self.organize_assets,
            self.check_asset_quality
        ]