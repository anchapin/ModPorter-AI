"""
Asset Converter Agent for handling texture, model, and audio asset conversion
"""

from typing import Dict, List, Any, Optional, Tuple
from crewai_tools import tool
import logging
import json
import base64
from pathlib import Path
from ..models.smart_assumptions import (
    SmartAssumptionEngine, FeatureContext, ConversionPlanComponent
)

logger = logging.getLogger(__name__)


class AssetConverterAgent:
    """
    Asset Converter Agent responsible for converting visual and audio assets
    to Bedrock-compatible formats as specified in PRD Feature 2.
    """
    
    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        
        # Supported asset formats
        self.texture_formats = {
            'input': ['.png', '.jpg', '.jpeg', '.tga', '.bmp'],
            'output': '.png'  # Bedrock uses PNG
        }
        
        self.model_formats = {
            'input': ['.obj', '.fbx', '.json'],  # Java mod formats
            'output': '.geo.json'  # Bedrock geometry format
        }
        
        self.audio_formats = {
            'input': ['.ogg', '.wav', '.mp3'],
            'output': '.ogg'  # Bedrock prefers OGG
        }
        
        # Bedrock asset constraints
        self.texture_constraints = {
            'max_resolution': 1024,  # Max texture size for performance
            'must_be_power_of_2': True,
            'supported_channels': ['rgb', 'rgba']
        }
        
        self.model_constraints = {
            'max_vertices': 3000,  # Bedrock model complexity limit
            'max_textures': 8,
            'supported_bones': 60  # Max bones for animated models
        }
        
        self.audio_constraints = {
            'max_file_size_mb': 10,
            'sample_rates': [22050, 44100],
            'max_duration_seconds': 300
        }
    
    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            self.analyze_assets,
            self.convert_textures,
            self.convert_models,
            self.convert_audio,
            self.validate_bedrock_assets
        ]
    
    @tool("Analyze Assets")
    def analyze_assets(self, asset_data: str) -> str:
        """
        Analyze Java mod assets to determine conversion requirements.
        
        Args:
            asset_data: JSON string containing asset information:
                       asset_list (list of asset objects with path, type, metadata)
        
        Returns:
            JSON string with analysis results and conversion plan
        """
        try:
            data = json.loads(asset_data)
            asset_list = data.get('asset_list', [])
            
            analysis_results = {
                'textures': {'count': 0, 'conversions_needed': [], 'issues': []},
                'models': {'count': 0, 'conversions_needed': [], 'issues': []},
                'audio': {'count': 0, 'conversions_needed': [], 'issues': []},
                'other': {'count': 0, 'files': [], 'issues': []}
            }
            
            for asset in asset_list:
                asset_path = asset.get('path', '')
                asset_type = asset.get('type', 'unknown')
                metadata = asset.get('metadata', {})
                
                file_ext = Path(asset_path).suffix.lower()
                
                if file_ext in self.texture_formats['input']:
                    analysis_results['textures']['count'] += 1
                    texture_analysis = self._analyze_texture(asset_path, metadata)
                    if texture_analysis['needs_conversion']:
                        analysis_results['textures']['conversions_needed'].append(texture_analysis)
                    if texture_analysis['issues']:
                        analysis_results['textures']['issues'].extend(texture_analysis['issues'])
                
                elif file_ext in self.model_formats['input']:
                    analysis_results['models']['count'] += 1
                    model_analysis = self._analyze_model(asset_path, metadata)
                    if model_analysis['needs_conversion']:
                        analysis_results['models']['conversions_needed'].append(model_analysis)
                    if model_analysis['issues']:
                        analysis_results['models']['issues'].extend(model_analysis['issues'])
                
                elif file_ext in self.audio_formats['input']:
                    analysis_results['audio']['count'] += 1
                    audio_analysis = self._analyze_audio(asset_path, metadata)
                    if audio_analysis['needs_conversion']:
                        analysis_results['audio']['conversions_needed'].append(audio_analysis)
                    if audio_analysis['issues']:
                        analysis_results['audio']['issues'].extend(audio_analysis['issues'])
                
                else:
                    analysis_results['other']['count'] += 1
                    analysis_results['other']['files'].append(asset_path)
                    if file_ext not in ['.txt', '.md', '.json']:  # Skip known text files
                        analysis_results['other']['issues'].append(f"Unknown asset type: {asset_path}")
            
            # Generate conversion recommendations
            recommendations = self._generate_conversion_recommendations(analysis_results)
            
            response = {
                "success": True,
                "analysis_results": analysis_results,
                "recommendations": recommendations,
                "total_assets": len(asset_list),
                "conversion_complexity": self._assess_conversion_complexity(analysis_results)
            }
            
            logger.info(f"Analyzed {len(asset_list)} assets")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to analyze assets: {str(e)}"}
            logger.error(f"Asset analysis error: {e}")
            return json.dumps(error_response)
    
    @tool("Convert Textures")
    def convert_textures(self, texture_data: str) -> str:
        """
        Convert texture assets to Bedrock-compatible format.
        
        Args:
            texture_data: JSON string containing texture conversion requests
        
        Returns:
            JSON string with conversion results
        """
        try:
            data = json.loads(texture_data)
            textures = data.get('textures', [])
            
            conversion_results = []
            
            for texture in textures:
                texture_path = texture.get('path', '')
                metadata = texture.get('metadata', {})
                target_usage = texture.get('usage', 'block')  # block, item, entity, etc.
                
                result = self._convert_single_texture(texture_path, metadata, target_usage)
                conversion_results.append(result)
            
            successful_conversions = [r for r in conversion_results if r['success']]
            failed_conversions = [r for r in conversion_results if not r['success']]
            
            response = {
                "success": True,
                "conversion_results": conversion_results,
                "summary": {
                    "total_textures": len(textures),
                    "successful_conversions": len(successful_conversions),
                    "failed_conversions": len(failed_conversions)
                },
                "bedrock_texture_pack_structure": self._generate_texture_pack_structure(successful_conversions)
            }
            
            logger.info(f"Converted {len(successful_conversions)}/{len(textures)} textures")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to convert textures: {str(e)}"}
            logger.error(f"Texture conversion error: {e}")
            return json.dumps(error_response)
    
    @tool("Convert Models")
    def convert_models(self, model_data: str) -> str:
        """
        Convert 3D models to Bedrock geometry format.
        
        Args:
            model_data: JSON string containing model conversion requests
        
        Returns:
            JSON string with conversion results
        """
        try:
            data = json.loads(model_data)
            models = data.get('models', [])
            
            conversion_results = []
            
            for model in models:
                model_path = model.get('path', '')
                metadata = model.get('metadata', {})
                entity_type = model.get('entity_type', 'block')  # block, item, entity
                
                result = self._convert_single_model(model_path, metadata, entity_type)
                conversion_results.append(result)
            
            successful_conversions = [r for r in conversion_results if r['success']]
            failed_conversions = [r for r in conversion_results if not r['success']]
            
            response = {
                "success": True,
                "conversion_results": conversion_results,
                "summary": {
                    "total_models": len(models),
                    "successful_conversions": len(successful_conversions),
                    "failed_conversions": len(failed_conversions)
                },
                "bedrock_model_structure": self._generate_model_structure(successful_conversions)
            }
            
            logger.info(f"Converted {len(successful_conversions)}/{len(models)} models")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to convert models: {str(e)}"}
            logger.error(f"Model conversion error: {e}")
            return json.dumps(error_response)
    
    @tool("Convert Audio")
    def convert_audio(self, audio_data: str) -> str:
        """
        Convert audio assets to Bedrock-compatible format.
        
        Args:
            audio_data: JSON string containing audio conversion requests
        
        Returns:
            JSON string with conversion results
        """
        try:
            data = json.loads(audio_data)
            audio_files = data.get('audio_files', [])
            
            conversion_results = []
            
            for audio_file in audio_files:
                audio_path = audio_file.get('path', '')
                metadata = audio_file.get('metadata', {})
                audio_type = audio_file.get('type', 'sound')  # sound, music, voice
                
                result = self._convert_single_audio(audio_path, metadata, audio_type)
                conversion_results.append(result)
            
            successful_conversions = [r for r in conversion_results if r['success']]
            failed_conversions = [r for r in conversion_results if not r['success']]
            
            response = {
                "success": True,
                "conversion_results": conversion_results,
                "summary": {
                    "total_audio_files": len(audio_files),
                    "successful_conversions": len(successful_conversions),
                    "failed_conversions": len(failed_conversions)
                },
                "bedrock_sound_structure": self._generate_sound_structure(successful_conversions)
            }
            
            logger.info(f"Converted {len(successful_conversions)}/{len(audio_files)} audio files")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to convert audio: {str(e)}"}
            logger.error(f"Audio conversion error: {e}")
            return json.dumps(error_response)
    
    @tool("Validate Bedrock Assets")
    def validate_bedrock_assets(self, validation_data: str) -> str:
        """
        Validate converted assets for Bedrock compatibility.
        
        Args:
            validation_data: JSON string containing assets to validate
        
        Returns:
            JSON string with validation results
        """
        try:
            data = json.loads(validation_data)
            assets = data.get('assets', [])
            
            validation_results = {
                'valid_assets': [],
                'invalid_assets': [],
                'warnings': [],
                'optimization_suggestions': []
            }
            
            for asset in assets:
                asset_path = asset.get('path', '')
                asset_type = asset.get('type', 'unknown')
                metadata = asset.get('metadata', {})
                
                validation = self._validate_single_asset(asset_path, asset_type, metadata)
                
                if validation['is_valid']:
                    validation_results['valid_assets'].append(validation)
                else:
                    validation_results['invalid_assets'].append(validation)
                
                validation_results['warnings'].extend(validation.get('warnings', []))
                validation_results['optimization_suggestions'].extend(validation.get('optimizations', []))
            
            # Generate overall quality score
            total_assets = len(assets)
            valid_count = len(validation_results['valid_assets'])
            quality_score = (valid_count / total_assets * 100) if total_assets > 0 else 0
            
            response = {
                "success": True,
                "validation_results": validation_results,
                "quality_metrics": {
                    "total_assets": total_assets,
                    "valid_assets": valid_count,
                    "invalid_assets": len(validation_results['invalid_assets']),
                    "quality_score": round(quality_score, 2),
                    "warning_count": len(validation_results['warnings']),
                    "optimization_count": len(validation_results['optimization_suggestions'])
                }
            }
            
            logger.info(f"Validated {total_assets} assets with {quality_score:.1f}% quality score")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to validate assets: {str(e)}"}
            logger.error(f"Asset validation error: {e}")
            return json.dumps(error_response)
    
    # Helper methods
    
    def _analyze_texture(self, texture_path: str, metadata: Dict) -> Dict:
        """Analyze a single texture for conversion needs"""
        width = metadata.get('width', 16)
        height = metadata.get('height', 16)
        channels = metadata.get('channels', 'rgba')
        file_ext = Path(texture_path).suffix.lower()
        
        issues = []
        needs_conversion = False
        
        # Check resolution
        if width > self.texture_constraints['max_resolution'] or height > self.texture_constraints['max_resolution']:
            issues.append(f"Resolution {width}x{height} exceeds maximum {self.texture_constraints['max_resolution']}")
            needs_conversion = True
        
        # Check if power of 2
        if self.texture_constraints['must_be_power_of_2']:
            if not self._is_power_of_2(width) or not self._is_power_of_2(height):
                issues.append(f"Resolution {width}x{height} is not power of 2")
                needs_conversion = True
        
        # Check format
        if file_ext != self.texture_formats['output']:
            needs_conversion = True
        
        # Check channels
        if channels not in self.texture_constraints['supported_channels']:
            issues.append(f"Unsupported channel format: {channels}")
            needs_conversion = True
        
        return {
            'path': texture_path,
            'needs_conversion': needs_conversion,
            'issues': issues,
            'current_format': file_ext,
            'target_format': self.texture_formats['output'],
            'current_resolution': f"{width}x{height}",
            'recommended_resolution': self._get_recommended_resolution(width, height)
        }
    
    def _analyze_model(self, model_path: str, metadata: Dict) -> Dict:
        """Analyze a single model for conversion needs"""
        vertex_count = metadata.get('vertices', 100)
        texture_count = metadata.get('textures', 1)
        bone_count = metadata.get('bones', 0)
        file_ext = Path(model_path).suffix.lower()
        
        issues = []
        needs_conversion = False
        
        # Check complexity
        if vertex_count > self.model_constraints['max_vertices']:
            issues.append(f"Vertex count {vertex_count} exceeds maximum {self.model_constraints['max_vertices']}")
            needs_conversion = True
        
        if texture_count > self.model_constraints['max_textures']:
            issues.append(f"Texture count {texture_count} exceeds maximum {self.model_constraints['max_textures']}")
            needs_conversion = True
        
        if bone_count > self.model_constraints['supported_bones']:
            issues.append(f"Bone count {bone_count} exceeds maximum {self.model_constraints['supported_bones']}")
            needs_conversion = True
        
        # Check format
        if file_ext != self.model_formats['output']:
            needs_conversion = True
        
        return {
            'path': model_path,
            'needs_conversion': needs_conversion,
            'issues': issues,
            'current_format': file_ext,
            'target_format': self.model_formats['output'],
            'complexity': {
                'vertices': vertex_count,
                'textures': texture_count,
                'bones': bone_count
            }
        }
    
    def _analyze_audio(self, audio_path: str, metadata: Dict) -> Dict:
        """Analyze a single audio file for conversion needs"""
        file_size_mb = metadata.get('file_size_mb', 1)
        sample_rate = metadata.get('sample_rate', 44100)
        duration = metadata.get('duration_seconds', 1)
        file_ext = Path(audio_path).suffix.lower()
        
        issues = []
        needs_conversion = False
        
        # Check file size
        if file_size_mb > self.audio_constraints['max_file_size_mb']:
            issues.append(f"File size {file_size_mb}MB exceeds maximum {self.audio_constraints['max_file_size_mb']}MB")
            needs_conversion = True
        
        # Check sample rate
        if sample_rate not in self.audio_constraints['sample_rates']:
            issues.append(f"Sample rate {sample_rate} not in supported rates {self.audio_constraints['sample_rates']}")
            needs_conversion = True
        
        # Check duration
        if duration > self.audio_constraints['max_duration_seconds']:
            issues.append(f"Duration {duration}s exceeds maximum {self.audio_constraints['max_duration_seconds']}s")
            needs_conversion = True
        
        # Check format
        if file_ext != self.audio_formats['output']:
            needs_conversion = True
        
        return {
            'path': audio_path,
            'needs_conversion': needs_conversion,
            'issues': issues,
            'current_format': file_ext,
            'target_format': self.audio_formats['output'],
            'current_specs': {
                'file_size_mb': file_size_mb,
                'sample_rate': sample_rate,
                'duration': duration
            }
        }
    
    def _convert_single_texture(self, texture_path: str, metadata: Dict, usage: str) -> Dict:
        """Convert a single texture (placeholder implementation)"""
        # In a real implementation, this would use image processing libraries
        # like PIL/Pillow to actually convert the texture
        
        return {
            'success': True,
            'original_path': texture_path,
            'converted_path': f"textures/{usage}/{Path(texture_path).stem}.png",
            'bedrock_format': 'png',
            'optimizations_applied': [
                'Converted to PNG format',
                'Resized to power-of-2 dimensions',
                'Optimized for Bedrock rendering'
            ],
            'bedrock_reference': f"{usage}_{Path(texture_path).stem}"
        }
    
    def _convert_single_model(self, model_path: str, metadata: Dict, entity_type: str) -> Dict:
        """Convert a single model (placeholder implementation)"""
        # In a real implementation, this would convert OBJ/FBX to Bedrock geometry format
        
        return {
            'success': True,
            'original_path': model_path,
            'converted_path': f"models/{entity_type}/{Path(model_path).stem}.geo.json",
            'bedrock_format': 'geo.json',
            'optimizations_applied': [
                'Converted to Bedrock geometry format',
                'Optimized vertex count',
                'Generated bone mappings'
            ],
            'bedrock_identifier': f"geometry.{entity_type}.{Path(model_path).stem}"
        }
    
    def _convert_single_audio(self, audio_path: str, metadata: Dict, audio_type: str) -> Dict:
        """Convert a single audio file (placeholder implementation)"""
        # In a real implementation, this would use audio processing libraries
        # like pydub to convert audio formats
        
        return {
            'success': True,
            'original_path': audio_path,
            'converted_path': f"sounds/{audio_type}/{Path(audio_path).stem}.ogg",
            'bedrock_format': 'ogg',
            'optimizations_applied': [
                'Converted to OGG format',
                'Optimized sample rate',
                'Compressed for performance'
            ],
            'bedrock_sound_event': f"{audio_type}.{Path(audio_path).stem}"
        }
    
    def _validate_single_asset(self, asset_path: str, asset_type: str, metadata: Dict) -> Dict:
        """Validate a single asset for Bedrock compatibility"""
        is_valid = True
        warnings = []
        optimizations = []
        
        if asset_type == 'texture':
            width = metadata.get('width', 16)
            height = metadata.get('height', 16)
            
            if width != height:
                warnings.append("Non-square texture may cause rendering issues")
            
            if width > 64:
                optimizations.append("Consider using lower resolution for better performance")
        
        elif asset_type == 'model':
            vertex_count = metadata.get('vertices', 100)
            
            if vertex_count > 1000:
                optimizations.append("High vertex count may impact performance")
        
        elif asset_type == 'audio':
            duration = metadata.get('duration_seconds', 1)
            
            if duration > 30:
                optimizations.append("Long audio files may impact memory usage")
        
        return {
            'path': asset_path,
            'type': asset_type,
            'is_valid': is_valid,
            'warnings': warnings,
            'optimizations': optimizations
        }
    
    def _is_power_of_2(self, n: int) -> bool:
        """Check if a number is a power of 2"""
        return n > 0 and (n & (n - 1)) == 0
    
    def _get_recommended_resolution(self, width: int, height: int) -> str:
        """Get recommended resolution for texture"""
        # Find the nearest power of 2 that's within constraints
        max_res = self.texture_constraints['max_resolution']
        
        target_width = min(max_res, self._next_power_of_2(width))
        target_height = min(max_res, self._next_power_of_2(height))
        
        return f"{target_width}x{target_height}"
    
    def _next_power_of_2(self, n: int) -> int:
        """Get the next power of 2 greater than or equal to n"""
        power = 1
        while power < n:
            power *= 2
        return power
    
    def _generate_conversion_recommendations(self, analysis: Dict) -> List[str]:
        """Generate conversion recommendations based on analysis"""
        recommendations = []
        
        texture_count = analysis['textures']['count']
        model_count = analysis['models']['count']
        audio_count = analysis['audio']['count']
        
        if texture_count > 0:
            recommendations.append(f"Convert {texture_count} textures to PNG format with power-of-2 dimensions")
        
        if model_count > 0:
            recommendations.append(f"Convert {model_count} models to Bedrock geometry format")
        
        if audio_count > 0:
            recommendations.append(f"Convert {audio_count} audio files to OGG format")
        
        total_issues = (len(analysis['textures']['issues']) + 
                       len(analysis['models']['issues']) + 
                       len(analysis['audio']['issues']))
        
        if total_issues > 0:
            recommendations.append(f"Address {total_issues} compatibility issues")
        
        return recommendations
    
    def _assess_conversion_complexity(self, analysis: Dict) -> str:
        """Assess the complexity of the conversion task"""
        total_conversions = (len(analysis['textures']['conversions_needed']) +
                           len(analysis['models']['conversions_needed']) +
                           len(analysis['audio']['conversions_needed']))
        
        total_issues = (len(analysis['textures']['issues']) +
                       len(analysis['models']['issues']) +
                       len(analysis['audio']['issues']))
        
        if total_conversions == 0 and total_issues == 0:
            return "simple"
        elif total_conversions < 5 and total_issues < 3:
            return "moderate"
        else:
            return "complex"
    
    def _generate_texture_pack_structure(self, textures: List[Dict]) -> Dict:
        """Generate Bedrock texture pack structure"""
        return {
            "pack_manifest": {
                "format_version": 2,
                "header": {
                    "name": "Converted Texture Pack",
                    "description": "Converted from Java mod",
                    "uuid": "generated-uuid-here",
                    "version": [1, 0, 0],
                    "min_engine_version": [1, 16, 0]
                },
                "modules": [{
                    "type": "resources",
                    "uuid": "generated-module-uuid",
                    "version": [1, 0, 0]
                }]
            },
            "texture_list": [t['converted_path'] for t in textures]
        }
    
    def _generate_model_structure(self, models: List[Dict]) -> Dict:
        """Generate Bedrock model structure"""
        return {
            "geometry_files": [m['converted_path'] for m in models],
            "entity_definitions": [m['bedrock_identifier'] for m in models]
        }
    
    def _generate_sound_structure(self, sounds: List[Dict]) -> Dict:
        """Generate Bedrock sound structure"""
        return {
            "sound_definitions": {s['bedrock_sound_event']: {
                "sounds": [s['converted_path']] 
            } for s in sounds}
        }
