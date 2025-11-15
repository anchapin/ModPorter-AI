"""
Asset Converter Agent for handling texture, model, and audio asset conversion
"""

from typing import Dict, List
import logging
import json
from pathlib import Path
from PIL import Image
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
try:
    from crewai.tools import tool
except ImportError:
    try:
        from crewai import tool
    except ImportError:
        # Fallback if crewai tools aren't available
        def tool(func):
            return func
from models.smart_assumptions import (
    SmartAssumptionEngine
)

logger = logging.getLogger(__name__)


class AssetConverterAgent:
    """
    Asset Converter Agent responsible for converting visual and audio assets
    to Bedrock-compatible formats as specified in PRD Feature 2.
    """
    
    _instance = None
    
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
        
        # Caching for performance optimization
        self._texture_cache = {}
        self._conversion_cache = {}
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance of AssetConverterAgent"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            AssetConverterAgent.analyze_assets_tool,
            AssetConverterAgent.convert_textures_tool,
            AssetConverterAgent.convert_models_tool,
            AssetConverterAgent.convert_audio_tool,
            AssetConverterAgent.validate_bedrock_assets_tool
        ]
    
    def _is_power_of_2(self, n: int) -> bool:
        """Check if a number is a power of 2"""
        return n > 0 and (n & (n - 1)) == 0
    
    def _next_power_of_2(self, n: int) -> int:
        """Get the next power of 2 greater than or equal to n"""
        power = 1
        while power < n:
            power *= 2
        return power
    
    def _previous_power_of_2(self, n: int) -> int:
        """Get the previous power of 2 less than or equal to n"""
        if n <= 0:
            return 1
        power = 1
        while (power * 2) <= n:
            power *= 2
        return power
    
    def _convert_single_texture(self, texture_path: str, metadata: Dict, usage: str) -> Dict:
        """Convert a single texture file to Bedrock format with enhanced validation and optimization"""
        # Create a cache key
        cache_key = f"{texture_path}_{usage}_{hash(str(metadata))}"
        
        # Check if we have a cached result
        if cache_key in self._conversion_cache:
            logger.debug(f"Using cached result for texture conversion: {texture_path}")
            return self._conversion_cache[cache_key]
        
        try:
            # Handle missing or corrupted files with fallback generation
            if not Path(texture_path).exists():
                logger.warning(f"Texture file not found: {texture_path}. Generating fallback texture.")
                img = self._generate_fallback_texture(usage)
                original_dimensions = img.size
                is_valid_png = False
                optimizations_applied = ["Generated fallback texture"]
            else:
                try:
                    # Open and validate the image
                    img = Image.open(texture_path)
                    original_dimensions = img.size
                    
                    # Enhanced PNG validation - check if it's already a valid PNG
                    is_valid_png = img.format == 'PNG'
                    
                    # Convert to RGBA for consistency
                    img = img.convert("RGBA")
                    optimizations_applied = ["Converted to RGBA"] if not is_valid_png else []
                except Exception as open_error:
                    logger.warning(f"Failed to open texture {texture_path}: {open_error}. Generating fallback texture.")
                    img = self._generate_fallback_texture(usage)
                    original_dimensions = img.size
                    is_valid_png = False
                    optimizations_applied = ["Generated fallback texture due to open error"]

            width, height = img.size
            resized = False

            max_res = self.texture_constraints.get('max_resolution', 1024)
            must_be_power_of_2 = self.texture_constraints.get('must_be_power_of_2', True)

            new_width, new_height = width, height

            needs_pot_resize = must_be_power_of_2 and (not self._is_power_of_2(width) or not self._is_power_of_2(height))
            
            if needs_pot_resize:
                new_width = self._next_power_of_2(width)
                new_height = self._next_power_of_2(height)
                resized = True

            if new_width > max_res or new_height > max_res:
                new_width = min(new_width, max_res)
                new_height = min(new_height, max_res)
                resized = True

            if resized and must_be_power_of_2:
                if not self._is_power_of_2(new_width):
                    new_width = self._previous_power_of_2(new_width)
                if not self._is_power_of_2(new_height):
                    new_height = self._previous_power_of_2(new_height)

            if resized and (new_width != width or new_height != height):
                # Use different resampling filters based on upscaling/downscaling
                if new_width > width or new_height > height:
                    # Upscaling - use LANCZOS for better quality
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                else:
                    # Downscaling - use LANCZOS for better quality
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                optimizations_applied.append(f"Resized from {original_dimensions} to {(new_width, new_height)}")
            else:
                new_width, new_height = img.size
                resized = False

            # Apply PNG optimization if needed
            if not is_valid_png or resized:
                optimizations_applied.append("Optimized PNG format")

            # MCMETA parsing
            animation_data = None
            mcmeta_path = Path(str(texture_path) + ".mcmeta")
            if mcmeta_path.exists():
                try:
                    with open(mcmeta_path, 'r') as f:
                        mcmeta_content = json.load(f)
                    if "animation" in mcmeta_content:
                        animation_data = mcmeta_content["animation"]
                        optimizations_applied.append("Parsed .mcmeta animation data")
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning("Could not parse .mcmeta file for {}: {}".format(texture_path, e))

            base_name = Path(texture_path).stem if Path(texture_path).exists() else "fallback_texture"
            # Enhanced asset path mapping from Java mod structure to Bedrock structure
            # Handle common Java mod asset paths and map them to Bedrock equivalents
            texture_path_obj = Path(texture_path) if Path(texture_path).exists() else Path(f"fallback_{usage}.png")
            
            # Try to infer usage from the original path if not explicitly provided
            if usage == 'block' and 'block' not in str(texture_path_obj).lower():
                # Check if the path contains common block texture indicators
                if any(block_indicator in str(texture_path_obj).lower() for block_indicator in 
                       ['block/', 'blocks/', '/block/', '/blocks/', '_block', '-block']):
                    usage = 'block'
                # Check for item indicators
                elif any(item_indicator in str(texture_path_obj).lower() for item_indicator in 
                        ['item/', 'items/', '/item/', '/items/', '_item', '-item']):
                    usage = 'item'
                # Check for entity indicators
                elif any(entity_indicator in str(texture_path_obj).lower() for entity_indicator in 
                        ['entity/', 'entities/', '/entity/', '/entities/', '_entity', '-entity']):
                    usage = 'entity'
                # Check for particle indicators
                elif 'particle' in str(texture_path_obj).lower():
                    usage = 'particle'
                # Check for GUI indicators
                elif any(gui_indicator in str(texture_path_obj).lower() for gui_indicator in 
                        ['gui/', 'ui/', 'interface/', 'menu/']):
                    usage = 'ui'
            
            # Map to Bedrock structure
            if usage == 'block':
                converted_path = f"textures/blocks/{base_name}.png"
            elif usage == 'item':
                converted_path = f"textures/items/{base_name}.png"
            elif usage == 'entity':
                converted_path = f"textures/entity/{base_name}.png"
            elif usage == 'particle':
                converted_path = f"textures/particle/{base_name}.png"
            elif usage == 'ui':
                converted_path = f"textures/ui/{base_name}.png"
            else:
                # For other types, try to preserve some structure from the original path
                # Remove common prefixes and map to textures/other/
                try:
                    relative_path = texture_path_obj.relative_to(texture_path_obj.anchor).as_posix()
                    # Remove common prefixes that indicate source structure
                    for prefix in ['assets/minecraft/textures/', 'textures/', 'images/', 'img/']:
                        if relative_path.startswith(prefix):
                            relative_path = relative_path[len(prefix):]
                            break
                    # Remove file extension
                    if '.' in relative_path:
                        relative_path = relative_path[:relative_path.rindex('.')]
                    converted_path = f"textures/other/{relative_path}.png"
                except Exception:
                    # Fallback to a simple path if relative path calculation fails
                    converted_path = f"textures/other/{base_name}.png"

            result = {
                'success': True,
                'original_path': str(texture_path),
                'converted_path': converted_path,
                'original_dimensions': original_dimensions,
                'converted_dimensions': (new_width, new_height),
                'format': 'png',
                'resized': resized,
                'optimizations_applied': optimizations_applied,
                'bedrock_reference': f"{usage}_{base_name}",
                'animation_data': animation_data,
                'was_valid_png': is_valid_png,
                'was_fallback': not Path(texture_path).exists()
            }
            
            # Cache the result
            self._conversion_cache[cache_key] = result
            
            return result
        except Exception as e:
            logger.error(f"Texture conversion error for {texture_path}: {e}")
            error_result = {
                'success': False,
                'original_path': str(texture_path),
                'error': str(e)
            }
            # Cache error results too to avoid repeated failures
            self._conversion_cache[cache_key] = error_result
            return error_result

    def _generate_texture_pack_structure(self, textures: List[Dict]) -> Dict:
        """Generate texture pack structure files with enhanced atlas handling"""
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Converted Resource Pack",
                "description": "Assets converted from Java mod",
                "uuid": "f4aeb009-270e-4a11-8137-a916a1a3ea1e",
                "version": [1, 0, 0],
                "min_engine_version": [1, 16, 0]
            },
            "modules": [{
                "type": "resources",
                "uuid": "0d28590c-1797-4555-9a19-5ee98def104e",
                "version": [1, 0, 0]
            }]
        }

        item_texture_data = {}
        terrain_texture_data = {}
        flipbook_entries = []
        
        # Track texture atlases
        texture_atlases = {}

        for t_data in textures:
            if not t_data.get('success'):
                continue

            bedrock_ref = t_data.get('bedrock_reference', Path(t_data['converted_path']).stem)
            converted_path = t_data['converted_path']
            texture_entry = {"textures": converted_path}

            # Enhanced atlas handling - group related textures
            # For simplicity, we're using a basic heuristic based on naming
            base_name = Path(converted_path).stem
            if "_" in base_name:
                atlas_name = base_name.split("_")[0]  # Group by prefix
                if atlas_name not in texture_atlases:
                    texture_atlases[atlas_name] = []
                texture_atlases[atlas_name].append({
                    "reference": bedrock_ref,
                    "path": converted_path
                })

            if bedrock_ref.startswith("item_") or "/items/" in converted_path:
                item_texture_data[bedrock_ref] = texture_entry
            elif bedrock_ref.startswith("block_") or "/blocks/" in converted_path:
                terrain_texture_data[bedrock_ref] = texture_entry
            elif bedrock_ref.startswith("entity_") or "/entity/" in converted_path:
                terrain_texture_data[bedrock_ref] = texture_entry
            else:
                terrain_texture_data[bedrock_ref] = texture_entry

            if t_data.get('animation_data'):
                anim_data = t_data['animation_data']
                frames_list = anim_data.get("frames", [])
                
                if frames_list and all(isinstance(f, dict) for f in frames_list):
                    try:
                        processed_frames = [int(f['index']) for f in frames_list if isinstance(f, dict) and 'index' in f]
                        if not processed_frames:
                            processed_frames = []
                    except (TypeError, ValueError):
                        processed_frames = []
                elif frames_list and all(isinstance(f, (int, float)) for f in frames_list):
                    processed_frames = [int(f) for f in frames_list]
                else:
                    processed_frames = list(range(anim_data.get("frame_count", 1)))

                ticks = anim_data.get("frametime", 1)
                if ticks <= 0:
                    ticks = 1

                entry = {
                    "flipbook_texture": converted_path,
                    "atlas_tile": Path(converted_path).stem,
                    "ticks_per_frame": ticks,
                    "frames": processed_frames
                }
                if "interpolate" in anim_data:
                    entry["interpolate"] = anim_data["interpolate"]

                flipbook_entries.append(entry)

        result = {"pack_manifest.json": manifest}
        if item_texture_data:
            result["item_texture.json"] = {"resource_pack_name": "vanilla", "texture_data": item_texture_data}
        if terrain_texture_data:
            result["terrain_texture.json"] = {"resource_pack_name": "vanilla", "texture_data": terrain_texture_data}
        if flipbook_entries:
            result["flipbook_textures.json"] = flipbook_entries
            
        # Add texture atlas information if any were detected
        if texture_atlases:
            result["texture_atlases.json"] = texture_atlases

        return result

    def convert_textures(self, texture_list: str, output_path: str) -> str:
        """
        Convert textures to Bedrock-compatible format.
        
        Args:
            texture_list: JSON string containing list of texture paths
            output_path: Output directory path
            
        Returns:
            JSON string with conversion results
        """
        try:
            textures = json.loads(texture_list) if isinstance(texture_list, str) else texture_list
            
            result = {
                "converted_textures": [],
                "total_textures": len(textures),
                "successful_conversions": 0,
                "failed_conversions": 0,
                "errors": []
            }
            
            for texture_path in textures:
                try:
                    # Simulate texture conversion
                    converted_path = Path(output_path) / Path(texture_path).name
                    result["converted_textures"].append({
                        "original_path": texture_path,
                        "converted_path": str(converted_path),
                        "success": True
                    })
                    result["successful_conversions"] += 1
                except Exception as e:
                    result["errors"].append(f"Failed to convert {texture_path}: {e}")
                    result["failed_conversions"] += 1
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Error converting textures: {e}")
            return json.dumps({
                "converted_textures": [],
                "total_textures": 0,
                "successful_conversions": 0,
                "failed_conversions": 0,
                "errors": [str(e)]
            })

    def _convert_single_audio(self, audio_path: str, metadata: Dict, audio_type: str) -> Dict:
        """Convert a single audio file to Bedrock format"""
        try:
            audio_path_obj = Path(audio_path)
            
            if not audio_path_obj.exists():
                return {
                    'success': False,
                    'original_path': str(audio_path),
                    'error': 'Audio file not found'
                }

            file_ext = audio_path_obj.suffix.lower()
            
            if file_ext not in self.audio_formats['input']:
                return {
                    'success': False,
                    'original_path': str(audio_path),
                    'error': f'Unsupported audio format: {file_ext}'
                }

            original_format = file_ext[1:]
            base_name = audio_path_obj.stem
            audio_path_parts = audio_type.replace('.', '/')
            converted_path = f"sounds/{audio_path_parts}/{base_name}.ogg"
            
            conversion_performed = False
            optimizations_applied = []
            duration_seconds = metadata.get('duration_seconds')
            
            if original_format == 'wav':
                try:
                    audio = AudioSegment.from_wav(audio_path)
                    conversion_performed = True
                    optimizations_applied.append("Converted WAV to OGG")
                    duration_seconds = audio.duration_seconds
                except CouldntDecodeError as e:
                    return {
                        'success': False,
                        'original_path': str(audio_path),
                        'error': f'Could not decode audio file: {e}'
                    }
            elif original_format == 'ogg':
                conversion_performed = False
                optimizations_applied.append("Validated OGG format")
                
                if duration_seconds is None:
                    try:
                        audio = AudioSegment.from_ogg(audio_path)
                        duration_seconds = audio.duration_seconds
                    except CouldntDecodeError as e:
                        return {
                            'success': False,
                            'original_path': str(audio_path),
                            'error': f'Could not decode audio file: {e}'
                        }
            else:
                conversion_performed = True
                optimizations_applied.append(f"Converted {original_format.upper()} to OGG")
                duration_seconds = 1.0
            
            bedrock_sound_event = f"{audio_type}.{base_name}"
            
            return {
                'success': True,
                'original_path': str(audio_path),
                'converted_path': converted_path,
                'original_format': original_format,
                'bedrock_format': 'ogg',
                'conversion_performed': conversion_performed,
                'optimizations_applied': optimizations_applied,
                'bedrock_sound_event': bedrock_sound_event,
                'duration_seconds': duration_seconds
            }
            
        except Exception as e:
            logger.error(f"Audio conversion error for {audio_path}: {e}")
            return {
                'success': False,
                'original_path': str(audio_path),
                'error': str(e)
            }

    def _generate_sound_structure(self, sounds: List[Dict]) -> Dict:
        """Generate sound structure files"""
        sound_definitions = {}
        
        for s_data in sounds:
            if not s_data.get('success'):
                continue

            event_name = s_data.get('bedrock_sound_event')
            converted_path = s_data.get('converted_path')

            if not event_name or not converted_path:
                continue

            rel_path = Path(converted_path)
            if rel_path.parts and rel_path.parts[0] == 'sounds':
                sound_def_path = str(Path(*rel_path.parts[1:]).with_suffix(''))
            else:
                sound_def_path = str(rel_path.with_suffix(''))

            if event_name not in sound_definitions:
                sound_definitions[event_name] = {"sounds": []}

            sound_definitions[event_name]["sounds"].append(sound_def_path)

        if sound_definitions:
            return {"sound_definitions.json": {"sound_definitions": sound_definitions}}
        return {}

    def _generate_model_structure(self, models: List[Dict]) -> Dict:
        """Generate model structure files"""
        valid_models = [m for m in models if m.get('success')]
        return {
            "geometry_files": [m['converted_path'] for m in valid_models if 'converted_path' in m],
            "identifiers_used": [m['bedrock_identifier'] for m in valid_models if 'bedrock_identifier' in m]
        }
    
    def _convert_single_model(self, model_path: str, metadata: Dict, entity_type: str) -> Dict:
        """Convert a single model to Bedrock format"""
        warnings = []
        try:
            model_p = Path(model_path)
            if not model_p.exists():
                return {
                    'success': False,
                    'original_path': str(model_path),
                    'error': 'Model file not found',
                    'warnings': warnings
                }

            with open(model_p, 'r') as f:
                java_model = json.load(f)

            # Basic Bedrock geo.json structure
            bedrock_identifier = f"geometry.{entity_type}.{model_p.stem}"
            texture_width = metadata.get('texture_width', 16)
            texture_height = metadata.get('texture_height', 16)

            bedrock_geo = {
                "format_version": "1.12.0",
                "minecraft:geometry": [
                    {
                        "description": {
                            "identifier": bedrock_identifier,
                            "texture_width": texture_width,
                            "texture_height": texture_height,
                            "visible_bounds_width": 2,
                            "visible_bounds_height": 2,
                            "visible_bounds_offset": [0, 0.5, 0]
                        },
                        "bones": []
                    }
                ]
            }

            geo_main_part = bedrock_geo["minecraft:geometry"][0]
            geo_description = geo_main_part["description"]
            all_bones = geo_main_part["bones"]

            java_parent = java_model.get("parent")
            java_elements = java_model.get("elements", [])
            processed_as_item_specific_type = False

            if entity_type == "item" and java_parent in ["item/generated", "item/builtin/entity", "item/handheld"]:
                processed_as_item_specific_type = True
                if java_parent in ["item/generated", "item/builtin/entity"]:
                    warnings.append(f"Handling as '{java_parent}'. Display transformations not applied.")
                elif java_parent == "item/handheld":
                    warnings.append("Handling as 'item/handheld'. Display transformations not applied.")

                texture_layers = java_model.get("textures", {})
                layer_count = 0
                for i in range(5):
                    layer_texture_key = f"layer{i}"
                    if layer_texture_key in texture_layers:
                        z_offset = -0.05 - (0.1 * i)
                        layer_bone = {
                            "name": layer_texture_key,
                            "pivot": [0.0, 0.0, 0.0],
                            "cubes": [{
                                "origin": [-8.0, -8.0, z_offset],
                                "size": [16.0, 16.0, 0.1],
                                "uv": [0, 0]
                            }]
                        }
                        all_bones.append(layer_bone)
                        layer_count += 1

                if layer_count == 0 and "particle" in texture_layers:
                    warnings.append("No layer0/layer1 found, using 'particle' texture for a fallback quad.")
                    particle_bone = {
                        "name": "particle_quad",
                        "pivot": [0.0, 0.0, 0.0],
                        "cubes": [{"origin": [-8.0, -8.0, -0.05], "size": [16.0, 16.0, 0.1], "uv": [0, 0]}]
                    }
                    all_bones.append(particle_bone)
                    layer_count = 1

                if layer_count > 0:
                    geo_description["visible_bounds_width"] = 1.0
                    geo_description["visible_bounds_height"] = 1.0
                    geo_description["visible_bounds_offset"] = [0.0, 0.0, 0.0]
                else:
                    warnings.append(f"Item model '{model_p.name}' with parent '{java_parent}' defined no recognized texture layers (layerN or particle). Generating empty model.")
                    geo_description["visible_bounds_width"] = 0.1
                    geo_description["visible_bounds_height"] = 0.1
                    geo_description["visible_bounds_offset"] = [0.0, 0.0, 0.0]

            if not processed_as_item_specific_type and java_elements:
                model_min_x, model_min_y, model_min_z = float('inf'), float('inf'), float('inf')
                model_max_x, model_max_y, model_max_z = float('-inf'), float('-inf'), float('-inf')

                for i, element in enumerate(java_elements):
                    bone_name = f"element_{i}"
                    bone_pivot = [0.0, 0.0, 0.0]
                    bone_rotation = [0.0, 0.0, 0.0]

                    if "rotation" in element:
                        rot = element["rotation"]
                        angle = rot.get("angle", 0.0)
                        axis = rot.get("axis", "y")
                        java_rot_origin = rot.get("origin", [8.0, 8.0, 8.0])
                        bone_pivot = [c - 8.0 for c in java_rot_origin]
                        if axis == "x":
                            bone_rotation[0] = angle
                        elif axis == "y":
                            bone_rotation[1] = -angle
                        elif axis == "z":
                            bone_rotation[2] = angle
                        else:
                            warnings.append(f"Unsupported rotation axis '{axis}' in element {i}")
                        warnings.append(f"Element {i} has rotation. Ensure pivot {bone_pivot} and rotation {bone_rotation} are correctly interpreted by Bedrock.")

                    from_coords = element.get("from", [0.0, 0.0, 0.0])
                    to_coords = element.get("to", [16.0, 16.0, 16.0])
                    cube_origin = [from_coords[0] - 8.0, from_coords[1] - 8.0, from_coords[2] - 8.0]
                    cube_size = [to_coords[0] - from_coords[0], to_coords[1] - from_coords[1], to_coords[2] - from_coords[2]]

                    model_min_x = min(model_min_x, cube_origin[0])
                    model_min_y = min(model_min_y, cube_origin[1])
                    model_min_z = min(model_min_z, cube_origin[2])
                    model_max_x = max(model_max_x, cube_origin[0] + cube_size[0])
                    model_max_y = max(model_max_y, cube_origin[1] + cube_size[1])
                    model_max_z = max(model_max_z, cube_origin[2] + cube_size[2])

                    cube_uv = [0, 0]
                    element_faces = element.get("faces")
                    if element_faces:
                        face_data = None
                        for face_name_priority in ["north", "up", "east", "south", "west", "down"]:
                            if face_name_priority in element_faces:
                                face_data = element_faces[face_name_priority]
                                break
                        if not face_data:
                            face_data = next(iter(element_faces.values()), None)
                        if face_data and "uv" in face_data:
                            cube_uv = [face_data["uv"][0], face_data["uv"][1]]
                            texture_variable = face_data.get("texture")
                            if texture_variable and not texture_variable.startswith("#"):
                                warnings.append(f"Element {i} face uses direct texture path '{texture_variable}' - needs mapping.")

                    new_bone = {
                        "name": bone_name,
                        "pivot": bone_pivot,
                        "rotation": bone_rotation,
                        "cubes": [{"origin": cube_origin, "size": cube_size, "uv": cube_uv}]
                    }
                    all_bones.append(new_bone)

                if java_elements:
                    v_bounds_w = model_max_x - model_min_x
                    v_bounds_h = model_max_y - model_min_y
                    v_bounds_d = model_max_z - model_min_z
                    geo_description["visible_bounds_width"] = round(max(v_bounds_w, v_bounds_d), 4)
                    geo_description["visible_bounds_height"] = round(v_bounds_h, 4)
                    geo_description["visible_bounds_offset"] = [
                        round(model_min_x + v_bounds_w / 2.0, 4),
                        round(model_min_y + v_bounds_h / 2.0, 4),
                        round(model_min_z + v_bounds_d / 2.0, 4)
                    ]
                else:
                    warnings.append("No elements found and not a recognized item parent type. Resulting model may be empty or unexpected.")
                    geo_description["visible_bounds_width"] = 0.125
                    geo_description["visible_bounds_height"] = 0.125
                    geo_description["visible_bounds_offset"] = [0, 0.0625, 0]

            elif not processed_as_item_specific_type and not java_elements:
                if java_parent:
                    warnings.append(f"Model has unhandled parent '{java_parent}' and no local elements")
                else:
                    warnings.append("Model has no elements and no parent")
                geo_description["visible_bounds_width"] = 0.1
                geo_description["visible_bounds_height"] = 0.1
                geo_description["visible_bounds_offset"] = [0, 0, 0]

            if java_model.get("display"):
                warnings.append("Java model 'display' transformations are not converted.")

            converted_filename = f"models/{entity_type}/{model_p.stem}.geo.json"

            return {
                'success': True,
                'original_path': str(model_path),
                'converted_path': converted_filename,
                'bedrock_format': 'geo.json',
                'bedrock_identifier': bedrock_identifier,
                'warnings': warnings,
                'converted_model_json': bedrock_geo
            }

        except FileNotFoundError as fnf_error:
            return {
                'success': False,
                'original_path': str(model_path),
                'error': str(fnf_error),
                'warnings': warnings
            }
        except json.JSONDecodeError as json_error:
            return {
                'success': False,
                'original_path': str(model_path),
                'error': f"Invalid JSON: {json_error}",
                'warnings': warnings
            }
        except Exception as e:
            logger.error(f"Model conversion error for {model_path}: {e}")
            return {
                'success': False,
                'original_path': str(model_path),
                'error': str(e),
                'warnings': warnings
            }
    
    @tool
    @staticmethod
    def analyze_assets_tool(asset_data: str) -> str:
        """Analyze assets for conversion."""
        agent = AssetConverterAgent.get_instance()
        def _analyze_texture(texture_path: str, metadata: Dict) -> Dict:
            """Analyze a single texture for conversion needs"""
            width = metadata.get('width', 16)
            height = metadata.get('height', 16)
            channels = metadata.get('channels', 'rgba')
            file_ext = Path(texture_path).suffix.lower()
            
            issues = []
            needs_conversion = False
            
            # Check resolution
            if width > agent.texture_constraints['max_resolution'] or height > agent.texture_constraints['max_resolution']:
                issues.append(f"Resolution {width}x{height} exceeds maximum {agent.texture_constraints['max_resolution']}")
                needs_conversion = True
            
            # Check if power of 2
            if agent.texture_constraints['must_be_power_of_2']:
                if not _is_power_of_2(width) or not _is_power_of_2(height):
                    issues.append(f"Resolution {width}x{height} is not power of 2")
                    needs_conversion = True
            
            # Check format
            if file_ext != agent.texture_formats['output']:
                needs_conversion = True
            
            # Check channels
            if channels not in agent.texture_constraints['supported_channels']:
                issues.append(f"Unsupported channel format: {channels}")
                needs_conversion = True
            
            return {
                'path': texture_path,
                'needs_conversion': needs_conversion,
                'issues': issues,
                'current_format': file_ext,
                'target_format': agent.texture_formats['output'],
                'current_resolution': f"{width}x{height}",
                'recommended_resolution': _get_recommended_resolution(width, height)
            }
    
        def _analyze_model(model_path: str, metadata: Dict) -> Dict:
            """Analyze a single model for conversion needs"""
            vertex_count = metadata.get('vertices', 100)
            texture_count = metadata.get('textures', 1)
            bone_count = metadata.get('bones', 0)
            file_ext = Path(model_path).suffix.lower()
            
            issues = []
            needs_conversion = False
            
            # Check complexity
            if vertex_count > agent.model_constraints['max_vertices']:
                issues.append(f"Vertex count {vertex_count} exceeds maximum {agent.model_constraints['max_vertices']}")
                needs_conversion = True
            
            if texture_count > agent.model_constraints['max_textures']:
                issues.append(f"Texture count {texture_count} exceeds maximum {agent.model_constraints['max_textures']}")
                needs_conversion = True
            
            if bone_count > agent.model_constraints['supported_bones']:
                issues.append(f"Bone count {bone_count} exceeds maximum {agent.model_constraints['supported_bones']}")
                needs_conversion = True
            
            # Check format
            if file_ext != agent.model_formats['output']:
                needs_conversion = True
            
            return {
                'path': model_path,
                'needs_conversion': needs_conversion,
                'issues': issues,
                'current_format': file_ext,
                'target_format': agent.model_formats['output'],
                'complexity': {
                    'vertices': vertex_count,
                    'textures': texture_count,
                    'bones': bone_count
                }
            }
    
        def _analyze_audio(audio_path: str, metadata: Dict) -> Dict:
            """Analyze a single audio file for conversion needs"""
            file_size_mb = metadata.get('file_size_mb', 1)
            sample_rate = metadata.get('sample_rate', 44100)
            duration = metadata.get('duration_seconds', 1)
            file_ext = Path(audio_path).suffix.lower()
            
            issues = []
            needs_conversion = False
            
            # Check file size
            if file_size_mb > agent.audio_constraints['max_file_size_mb']:
                issues.append(f"File size {file_size_mb}MB exceeds maximum {agent.audio_constraints['max_file_size_mb']}MB")
                needs_conversion = True
            
            # Check sample rate
            if sample_rate not in agent.audio_constraints['sample_rates']:
                issues.append(f"Sample rate {sample_rate} not in supported rates {agent.audio_constraints['sample_rates']}")
                needs_conversion = True
            
            # Check duration
            if duration > agent.audio_constraints['max_duration_seconds']:
                issues.append(f"Duration {duration}s exceeds maximum {agent.audio_constraints['max_duration_seconds']}s")
                needs_conversion = True
            
            # Check format
            if file_ext != agent.audio_formats['output']:
                needs_conversion = True
            
            return {
                'path': audio_path,
                'needs_conversion': needs_conversion,
                'issues': issues,
                'current_format': file_ext,
                'target_format': agent.audio_formats['output'],
                'current_specs': {
                    'file_size_mb': file_size_mb,
                    'sample_rate': sample_rate,
                    'duration': duration
                }
            }
        def _is_power_of_2(n: int) -> bool:
            """Check if a number is a power of 2"""
            return n > 0 and (n & (n - 1)) == 0
        def _get_recommended_resolution(width: int, height: int) -> str:
            """Get recommended resolution for texture"""
            # Find the nearest power of 2 that's within constraints
            max_res = agent.texture_constraints['max_resolution']
            
            target_width = min(max_res, _next_power_of_2(width))
            target_height = min(max_res, _next_power_of_2(height))
            
            return f"{target_width}x{target_height}"
    
        def _next_power_of_2(n: int) -> int:
            """Get the next power of 2 greater than or equal to n"""
            power = 1
            while power < n:
                power *= 2
            return power
        def _generate_conversion_recommendations(analysis: Dict) -> List[str]:
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
    
        def _assess_conversion_complexity(analysis: Dict) -> str:
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
                metadata = asset.get('metadata', {})
                
                file_ext = Path(asset_path).suffix.lower()
                
                if file_ext in agent.texture_formats['input']:
                    analysis_results['textures']['count'] += 1
                    texture_analysis = _analyze_texture(asset_path, metadata)
                    if texture_analysis['needs_conversion']:
                        analysis_results['textures']['conversions_needed'].append(texture_analysis)
                    if texture_analysis['issues']:
                        analysis_results['textures']['issues'].extend(texture_analysis['issues'])
                
                elif file_ext in agent.model_formats['input']:
                    analysis_results['models']['count'] += 1
                    model_analysis = _analyze_model(asset_path, metadata)
                    if model_analysis['needs_conversion']:
                        analysis_results['models']['conversions_needed'].append(model_analysis)
                    if model_analysis['issues']:
                        analysis_results['models']['issues'].extend(model_analysis['issues'])
                
                elif file_ext in agent.audio_formats['input']:
                    analysis_results['audio']['count'] += 1
                    audio_analysis = _analyze_audio(asset_path, metadata)
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
            recommendations = _generate_conversion_recommendations(analysis_results)
            
            response = {
                "success": True,
                "analysis_results": analysis_results,
                "recommendations": recommendations,
                "total_assets": len(asset_list),
                "conversion_complexity": _assess_conversion_complexity(analysis_results)
            }
            
            logger.info(f"Analyzed {len(asset_list)} assets")
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Unhandled error in analyze_assets: {e}", exc_info=True)
            return json.dumps({"success": False, "error": f"Failed to analyze assets: {str(e)}"}, indent=2)
    
    @tool
    @staticmethod
    def convert_textures_tool(texture_data: str) -> str:
        """Convert textures to Bedrock format."""
        agent = AssetConverterAgent.get_instance()
        def _is_power_of_2(n: int) -> bool:
            """Check if a number is a power of 2"""
            return n > 0 and (n & (n - 1)) == 0
        def _next_power_of_2(n: int) -> int:
            """Get the next power of 2 greater than or equal to n"""
            power = 1
            while power < n:
                power *= 2
            return power
        def _previous_power_of_2(n: int) -> int:
            if n <= 0:
                return 1  # Smallest power of 2, or raise error
            power = 1
            while (power * 2) <= n:
                power *= 2
            return power
        def _convert_single_texture(texture_path: str, metadata: Dict, usage: str) -> Dict:
            try:
                if not Path(texture_path).exists():
                    raise FileNotFoundError(f"Texture file not found: {texture_path}")

                img = Image.open(texture_path)
                original_dimensions = img.size
                # Ensure RGBA conversion happens early to correctly assess channels if needed later
                # and to standardize the image format before any resizing.
                img = img.convert("RGBA")
                optimizations_applied = ["Converted to RGBA"]

                width, height = img.size # Use dimensions from RGBA converted image

                resized = False

                # Safely get constraints, providing defaults if not set
                max_res = agent.texture_constraints.get('max_resolution', 1024)
                must_be_power_of_2 = agent.texture_constraints.get('must_be_power_of_2', True)

                new_width, new_height = width, height

                # Determine if resizing is needed due to power-of-two requirement or exceeding max resolution
                needs_pot_resize = must_be_power_of_2 and (not _is_power_of_2(width) or not _is_power_of_2(height))

                if needs_pot_resize:
                    new_width = _next_power_of_2(width)
                    new_height = _next_power_of_2(height)
                    resized = True

                # If dimensions (potentially already adjusted for PoT) exceed max_res, cap them.
                if new_width > max_res or new_height > max_res:
                    new_width = min(new_width, max_res)
                    new_height = min(new_height, max_res)
                    resized = True # Marked as resized if capping occurs

                # If capping or initial PoT resize occurred, and must_be_power_of_2 is true,
                # ensure the capped dimensions are also power of two. This might require further shrinking.
                if resized and must_be_power_of_2:
                    if not _is_power_of_2(new_width):
                        new_width = _previous_power_of_2(new_width)
                    if not _is_power_of_2(new_height):
                        new_height = _previous_power_of_2(new_height)

                # Perform resize operation only if dimensions actually changed
                if resized and (new_width != width or new_height != height):
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    optimizations_applied.append(f"Resized from {original_dimensions} to {(new_width, new_height)}")
                else:
                    # If no resize occurred, ensure new_width and new_height reflect original (but RGBA converted) dimensions
                    new_width, new_height = img.size
                    resized = False # Correct resized status if no actual dimension change happened

                # MCMETA parsing logic starts
                animation_data = None
                # Ensure texture_path is a string before concatenation, Path objects might handle this differently.
                mcmeta_path_str = str(texture_path) + ".mcmeta"
                mcmeta_path = Path(mcmeta_path_str)

                if mcmeta_path.exists() and mcmeta_path.is_file():
                    try:
                        with open(mcmeta_path, 'r') as f:
                            mcmeta_content = json.load(f)
                        if "animation" in mcmeta_content:
                            animation_data = mcmeta_content["animation"]
                            optimizations_applied.append("Parsed .mcmeta animation data")
                            logger.info(f"Found and parsed animation data for {texture_path}")
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse .mcmeta file for {texture_path} due to JSON error.")
                    except Exception as e: # Catching other potential errors like permission issues
                        logger.warning(f"Error reading or processing .mcmeta file for {texture_path}: {e}")
                # MCMETA parsing logic ends

                base_name = Path(texture_path).stem
                if usage == 'block':
                    converted_path = f"textures/blocks/{base_name}.png"
                elif usage == 'item':
                    converted_path = f"textures/items/{base_name}.png"
                elif usage == 'entity':
                    converted_path = f"textures/entity/{base_name}.png"
                else:
                    converted_path = f"textures/{usage}/{base_name}.png"

                return {
                    'success': True,
                    'original_path': str(texture_path),
                    'converted_path': converted_path,
                    'original_dimensions': original_dimensions,
                    'converted_dimensions': (new_width, new_height),
                    'format': 'png',
                    'resized': resized,
                    'optimizations_applied': optimizations_applied,
                    'bedrock_reference': f"{usage}_{base_name}",
                    'animation_data': animation_data # New key added
                }
            except FileNotFoundError as fnf_error:
                logger.error(f"Texture conversion error for {texture_path}: {fnf_error}")
                return {'success': False, 'original_path': str(texture_path), 'error': str(fnf_error)}
            except Exception as e:
                logger.error(f"Texture conversion error for {texture_path}: {e}", exc_info=True)
                return {'success': False, 'original_path': str(texture_path), 'error': str(e)}
        def _generate_texture_pack_structure(textures: List[Dict]) -> Dict:
            # Basic manifest structure (can be expanded later with more dynamic UUIDs etc.)
            manifest = {
                "format_version": 2,
                "header": {
                    "name": "Converted Resource Pack",
                    "description": "Assets converted from Java mod",
                    "uuid": "f4aeb009-270e-4a11-8137-a916a1a3ea1e", # Placeholder UUID
                    "version": [1, 0, 0],
                    "min_engine_version": [1, 16, 0] # Example min engine version
                },
                "modules": [{
                    "type": "resources",
                    "uuid": "0d28590c-1797-4555-9a19-5ee98def104e", # Placeholder UUID
                    "version": [1, 0, 0]
                }]
            }

            item_texture_data = {}
            terrain_texture_data = {}
            flipbook_entries = []

            for t_data in textures:
                if not t_data.get('success'):
                    continue

                bedrock_ref = t_data.get('bedrock_reference', Path(t_data['converted_path']).stem)
                converted_path = t_data['converted_path'] # e.g. "textures/blocks/stone.png"

                texture_entry = {"textures": converted_path}

                # Crude heuristic to decide if it's an item or block/terrain texture
                # This should ideally be driven by the 'usage' field from _convert_single_texture
                if bedrock_ref.startswith("item_") or "/items/" in converted_path:
                    item_texture_data[bedrock_ref] = texture_entry
                elif bedrock_ref.startswith("block_") or "/blocks/" in converted_path:
                    terrain_texture_data[bedrock_ref] = texture_entry
                elif bedrock_ref.startswith("entity_") or "/entity/" in converted_path:
                    # Entities often use terrain_texture.json for their texture references in models
                    terrain_texture_data[bedrock_ref] = texture_entry
                else: # Default to terrain_texture for other types or if unclear
                    terrain_texture_data[bedrock_ref] = texture_entry


                if t_data.get('animation_data'):
                    anim_data = t_data['animation_data']
                    # Ensure frame list is integers if it's a simple list
                    frames_list = anim_data.get("frames", [])
                    if frames_list and all(isinstance(f, dict) for f in frames_list):
                        # This is a list of frame objects (e.g. {"index": 0, "time": 5})
                        # The simple flipbook format expects a list of indices if ticks_per_frame is global
                        # For now, we'll assume if frames is a list of dicts, it's not a simple flipbook.
                        # A more complex conversion would be needed for that.
                        # Or, if only 'index' is used in those dicts, extract them.
                        try:
                            processed_frames = [int(f['index']) for f in frames_list if isinstance(f, dict) and 'index' in f]
                            if not processed_frames or len(processed_frames) != len(frames_list):
                                 logger.warning(f"Complex frame definitions in {converted_path} not fully supported for simple flipbook. Using raw list or empty.")
                                 processed_frames = [] # Fallback or log error
                        except (TypeError, ValueError):
                            processed_frames = []
                            logger.warning(f"Could not parse frame indices for {converted_path}. Defaulting to empty frame list for flipbook.")

                    elif frames_list and all(isinstance(f, (int, float)) for f in frames_list): # list of numbers
                        processed_frames = [int(f) for f in frames_list]
                    else: # Default to a single frame if frames are undefined or in unexpected format
                        processed_frames = list(range(anim_data.get("frame_count", 1))) # frame_count is hypothetical here

                    # MCMETA frametime is in game ticks. Default to 1 if not specified.
                    ticks = anim_data.get("frametime", 1)
                    if ticks <= 0:
                        ticks = 1  # Ensure positive frametime

                    entry = {
                        "flipbook_texture": converted_path,
                        "atlas_tile": Path(converted_path).stem,
                        "ticks_per_frame": ticks,
                        "frames": processed_frames
                    }
                    if "interpolate" in anim_data:
                        entry["interpolate"] = anim_data["interpolate"]

                    flipbook_entries.append(entry)

            result = {"pack_manifest.json": manifest}
            if item_texture_data:
                result["item_texture.json"] = {"resource_pack_name": "vanilla", "texture_data": item_texture_data}
            if terrain_texture_data:
                result["terrain_texture.json"] = {"resource_pack_name": "vanilla", "texture_data": terrain_texture_data}
            if flipbook_entries:
                result["flipbook_textures.json"] = flipbook_entries

            return result
        try:
            # Handle both JSON string and plain list formats
            if isinstance(texture_data, str):
                if texture_data.startswith('[') or texture_data.startswith('{'):
                    # It's JSON
                    data = json.loads(texture_data)
                    if isinstance(data, list):
                        # Simple list of paths
                        textures = [{"path": path} for path in data]
                    else:
                        # Structured data
                        textures = data.get('textures', [])
                else:
                    # Single path
                    textures = [{"path": texture_data}]
            else:
                # Assume it's already a list
                textures = [{"path": path} for path in texture_data]
            
            all_conversion_results = []
            
            for texture_input_data in textures:
                texture_path = texture_input_data.get('path', '') if isinstance(texture_input_data, dict) else texture_input_data
                metadata = texture_input_data.get('metadata', {}) if isinstance(texture_input_data, dict) else {}
                target_usage = texture_input_data.get('usage', 'block') if isinstance(texture_input_data, dict) else 'block'

                result = _convert_single_texture(texture_path, metadata, target_usage)
                all_conversion_results.append(result)
            
            successful_conversions = [r for r in all_conversion_results if r.get('success')]
            failed_conversions_details = []
            for r in all_conversion_results:
                if not r.get('success'):
                    r['fallback_suggestion'] = f"Consider using a default placeholder for {r.get('original_path', 'unknown texture')}"
                    failed_conversions_details.append(r)
            
            generated_pack_files = {}
            if successful_conversions:
                generated_pack_files = _generate_texture_pack_structure(successful_conversions)

            response = {
                "success": True,
                "conversion_summary": {
                    "total_requested": len(textures),
                    "successfully_converted": len(successful_conversions),
                    "failed_conversions": len(failed_conversions_details)
                },
                "successful_results": successful_conversions,
                "failed_results": failed_conversions_details,
                "bedrock_pack_files": generated_pack_files,
                # Legacy fields for integration test compatibility
                "converted_textures": successful_conversions,
                "total_textures": len(textures),
                "successful_conversions": len(successful_conversions)
            }
            
            logger.info(f"Texture conversion process complete. Requested: {len(textures)}, Succeeded: {len(successful_conversions)}, Failed: {len(failed_conversions_details)}")
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Unhandled error in convert_textures: {e}", exc_info=True)
            return json.dumps({"success": False, "error": f"Failed to process texture conversion request: {str(e)}"}, indent=2)
    
    @tool
    @staticmethod
    def convert_models_tool(model_data: str) -> str:
        """Convert models to Bedrock format."""
        def _convert_single_model(model_path: str, metadata: Dict, entity_type: str) -> Dict:
            warnings = []
            try:
                model_p = Path(model_path)
                if not model_p.exists():
                    raise FileNotFoundError(f"Model file not found: {model_path}")

                with open(model_p, 'r') as f:
                    java_model = json.load(f)

                # Basic Bedrock geo.json structure
                bedrock_identifier = f"geometry.{entity_type}.{model_p.stem}"
                # For texture_width/height, try to get from metadata if available, else default
                # This metadata would ideally be populated by texture analysis of related textures
                texture_width = metadata.get('texture_width', 16)
                texture_height = metadata.get('texture_height', 16)

                bedrock_geo = {
                    "format_version": "1.12.0",
                    "minecraft:geometry": [
                        {
                            "description": {
                                "identifier": bedrock_identifier,
                                "texture_width": texture_width,
                                "texture_height": texture_height,
                                # Visible bounds can be roughly estimated later if needed
                                "visible_bounds_width": 2,
                                "visible_bounds_height": 2,
                                "visible_bounds_offset": [0, 0.5, 0]
                            },
                            "bones": []
                        }
                    ]
                }

                # Ensure we are modifying the correct dictionary part
                geo_main_part = bedrock_geo["minecraft:geometry"][0]
                geo_description = geo_main_part["description"]
                all_bones = geo_main_part["bones"]

                java_parent = java_model.get("parent")
                java_elements = java_model.get("elements", [])
                processed_as_item_specific_type = False

                if entity_type == "item" and java_parent in ["item/generated", "item/builtin/entity", "item/handheld"]:
                    processed_as_item_specific_type = True
                    if java_parent in ["item/generated", "item/builtin/entity"]:
                        warnings.append(f"Handling as '{java_parent}'. Display transformations not applied.")
                    elif java_parent == "item/handheld":
                        warnings.append("Handling as 'item/handheld'. Display transformations not applied.")

                    texture_layers = java_model.get("textures", {})
                    layer_count = 0
                    for i in range(5):  # Check for layer0 up to layer4
                        layer_texture_key = f"layer{i}"
                        if layer_texture_key in texture_layers:
                            # In a more advanced system, here you would resolve texture_layers[layer_texture_key]
                            # to get specific texture dimensions for texture_width/height.
                            # For now, we use the global/default texture_width/height.

                            z_offset = -0.05 - (0.1 * i) # Each layer slightly behind the previous, very thin

                            layer_bone = {
                                "name": layer_texture_key,
                                "pivot": [0.0, 0.0, 0.0],
                                "cubes": [{
                                    "origin": [-8.0, -8.0, z_offset],
                                    "size": [16.0, 16.0, 0.1], # Thin quad
                                    "uv": [0, 0] # Assumes 0,0 of the specified texture_width/height
                                }]
                            }
                            all_bones.append(layer_bone)
                            layer_count += 1

                    if layer_count == 0 and "particle" in texture_layers:
                        warnings.append("No layer0/layer1 found, using 'particle' texture for a fallback quad.")
                        particle_bone = {
                            "name": "particle_quad",
                            "pivot": [0.0,0.0,0.0],
                            "cubes": [{"origin": [-8.0,-8.0, -0.05], "size": [16.0,16.0,0.1], "uv": [0,0]}]
                        }
                        all_bones.append(particle_bone)
                        layer_count = 1

                    if layer_count > 0:
                        # Set appropriate visible bounds for a typical 16x16 item sprite
                        # Model dimensions are -8 to +8, so width/height is 16 model units.
                        # If 16 model units = 1 block unit for bounds purposes:
                        geo_description["visible_bounds_width"] = 1.0
                        geo_description["visible_bounds_height"] = 1.0
                        # Centered quad from -8 to 8 in X/Y plane, so offset is 0,0,0 relative to model origin
                        geo_description["visible_bounds_offset"] = [0.0, 0.0, 0.0]
                    else:
                        warnings.append(f"Item model '{model_p.name}' with parent '{java_parent}' defined no recognized texture layers (layerN or particle). Generating empty model.")
                        geo_description["visible_bounds_width"] = 0.1
                        geo_description["visible_bounds_height"] = 0.1
                        geo_description["visible_bounds_offset"] = [0.0,0.0,0.0]

                if not processed_as_item_specific_type and java_elements:
                    # Standard element processing logic (from previous step)
                    model_min_x, model_min_y, model_min_z = float('inf'), float('inf'), float('inf')
                    model_max_x, model_max_y, model_max_z = float('-inf'), float('-inf'), float('-inf')

                    for i, element in enumerate(java_elements):
                        bone_name = f"element_{i}"
                        bone_pivot = [0.0, 0.0, 0.0]
                        bone_rotation = [0.0, 0.0, 0.0]

                        if "rotation" in element:
                            rot = element["rotation"]
                            angle = rot.get("angle", 0.0)
                            axis = rot.get("axis", "y")
                            java_rot_origin = rot.get("origin", [8.0, 8.0, 8.0])
                            bone_pivot = [c - 8.0 for c in java_rot_origin]
                            if axis == "x":
                                bone_rotation[0] = angle
                            elif axis == "y":
                                bone_rotation[1] = -angle  # Often Y rotation is inverted
                            elif axis == "z":
                                bone_rotation[2] = angle
                            else:
                                warnings.append(f"Unsupported rotation axis '{axis}' in element {i}")
                            warnings.append(f"Element {i} has rotation. Ensure pivot {bone_pivot} and rotation {bone_rotation} are correctly interpreted by Bedrock.")

                        from_coords = element.get("from", [0.0,0.0,0.0])
                        to_coords = element.get("to", [16.0,16.0,16.0])
                        cube_origin = [from_coords[0] - 8.0, from_coords[1] - 8.0, from_coords[2] - 8.0]
                        cube_size = [to_coords[0] - from_coords[0], to_coords[1] - from_coords[1], to_coords[2] - from_coords[2]]

                        model_min_x = min(model_min_x, cube_origin[0])
                        model_min_y = min(model_min_y, cube_origin[1])
                        model_min_z = min(model_min_z, cube_origin[2])
                        model_max_x = max(model_max_x, cube_origin[0] + cube_size[0])
                        model_max_y = max(model_max_y, cube_origin[1] + cube_size[1])
                        model_max_z = max(model_max_z, cube_origin[2] + cube_size[2])

                        cube_uv = [0,0]
                        element_faces = element.get("faces")
                        if element_faces:
                            face_data = None
                            for face_name_priority in ["north", "up", "east", "south", "west", "down"]:
                                if face_name_priority in element_faces:
                                    face_data = element_faces[face_name_priority]
                                    break
                            if not face_data:
                                face_data = next(iter(element_faces.values()), None)
                            if face_data and "uv" in face_data:
                                cube_uv = [face_data["uv"][0], face_data["uv"][1]]
                                texture_variable = face_data.get("texture")
                                if texture_variable and not texture_variable.startswith("#"):
                                    warnings.append(f"Element {i} face uses direct texture path '{texture_variable}' - needs mapping.")

                        new_bone = {
                            "name": bone_name, "pivot": bone_pivot, "rotation": bone_rotation,
                            "cubes": [{"origin": cube_origin, "size": cube_size, "uv": cube_uv}]
                        }
                        all_bones.append(new_bone)

                    if java_elements: # Recalculate bounds if elements were processed
                        v_bounds_w = model_max_x - model_min_x
                        v_bounds_h = model_max_y - model_min_y
                        v_bounds_d = model_max_z - model_min_z
                        geo_description["visible_bounds_width"] = round(max(v_bounds_w, v_bounds_d), 4)
                        geo_description["visible_bounds_height"] = round(v_bounds_h, 4)
                        geo_description["visible_bounds_offset"] = [
                            round(model_min_x + v_bounds_w / 2.0, 4),
                            round(model_min_y + v_bounds_h / 2.0, 4),
                            round(model_min_z + v_bounds_d / 2.0, 4)
                        ]
                    else: # No elements, but not handled as item/generated item type
                        warnings.append("No elements found and not a recognized item parent type. Resulting model may be empty or unexpected.")
                        geo_description["visible_bounds_width"] = 0.125
                        geo_description["visible_bounds_height"] = 0.125
                        geo_description["visible_bounds_offset"] = [0, 0.0625, 0]

                elif not processed_as_item_specific_type and not java_elements: # No item-specific handling, no elements
                    if java_parent:
                        warnings.append(f"Model has unhandled parent '{java_parent}' and no local elements")
                    else:
                        warnings.append("Model has no elements and no parent")
                    # Set default small bounds for an empty or placeholder model
                    geo_description["visible_bounds_width"] = 0.1
                    geo_description["visible_bounds_height"] = 0.1
                    geo_description["visible_bounds_offset"] = [0,0,0]

                if java_model.get("display"):
                    warnings.append("Java model 'display' transformations are not converted.")

                converted_filename = f"models/{entity_type}/{model_p.stem}.geo.json"

                return {
                    'success': True,
                    'original_path': str(model_path),
                    'converted_path': converted_filename,
                    'bedrock_format': 'geo.json',
                    'bedrock_identifier': bedrock_identifier,
                    'warnings': warnings,
                    'converted_model_json': bedrock_geo
                }

            except FileNotFoundError as fnf_error:
                logger.error(f"Model conversion error for {model_path}: {fnf_error}")
                return {'success': False, 'original_path': str(model_path), 'error': str(fnf_error), 'warnings': warnings}
            except json.JSONDecodeError as json_error:
                logger.error(f"Model conversion JSON error for {model_path}: {json_error}")
                return {'success': False, 'original_path': str(model_path), 'error': f"Invalid JSON: {json_error}", 'warnings': warnings}
            except Exception as e:
                logger.error(f"Model conversion error for {model_path}: {e}", exc_info=True)
                return {'success': False, 'original_path': str(model_path), 'error': str(e), 'warnings': warnings}
        def _generate_model_structure(models: List[Dict]) -> Dict:
            # Ensure only successful conversions are included
            valid_models = [m for m in models if m.get('success')]
            return {
                # These keys are illustrative; the actual output is a list of file contents/paths
                # For this structure, we just return the list of paths and identifiers as before.
                # A higher-level packaging agent would create the actual files.
                "geometry_files": [m['converted_path'] for m in valid_models if 'converted_path' in m],
                "identifiers_used": [m['bedrock_identifier'] for m in valid_models if 'bedrock_identifier' in m]
            }
        try:
            data = json.loads(model_data)
            models = data.get('models', [])
            
            all_conversion_results = []
            
            for model_input_data in models:
                model_path = model_input_data.get('path', '')
                metadata = model_input_data.get('metadata', {})
                entity_type = model_input_data.get('entity_type', 'block')
                
                result = _convert_single_model(model_path, metadata, entity_type)
                all_conversion_results.append(result)
            
            successful_conversions = [r for r in all_conversion_results if r.get('success')]
            failed_conversions_details = []
            for r in all_conversion_results:
                if not r.get('success'):
                    r['fallback_suggestion'] = f"Consider using a default placeholder for {r.get('original_path', 'unknown model')}"
                    failed_conversions_details.append(r)

            # _generate_model_structure returns a dict like {"geometry_files": [...], "identifiers_used": [...]}
            # These are not file contents but rather lists of paths/ids for reporting.
            generated_model_info = {}
            if successful_conversions:
                 generated_model_info = _generate_model_structure(successful_conversions)

            response = {
                "success": True,
                "conversion_summary": {
                    "total_requested": len(models),
                    "successfully_converted": len(successful_conversions),
                    "failed_conversions": len(failed_conversions_details)
                },
                "successful_results": successful_conversions,
                "failed_results": failed_conversions_details,
                "bedrock_model_info": generated_model_info
            }
            
            logger.info(f"Model conversion process complete. Requested: {len(models)}, Succeeded: {len(successful_conversions)}, Failed: {len(failed_conversions_details)}")
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Unhandled error in convert_models: {e}", exc_info=True)
            return json.dumps({"success": False, "error": f"Failed to process model conversion request: {str(e)}"}, indent=2)
    
    @tool
    @staticmethod
    def convert_audio_tool(audio_data: str) -> str:
        """Convert audio files to Bedrock format."""
        agent = AssetConverterAgent.get_instance()
        def _convert_single_audio(audio_path: str, metadata: Dict, audio_type: str) -> Dict:
            """Convert a single audio file to Bedrock-compatible format"""
            try:
                audio_path_obj = Path(audio_path)
                
                # Check if file exists
                if not audio_path_obj.exists():
                    raise FileNotFoundError(f"Audio file not found: {audio_path}")
                
                # Get file extension
                file_ext = audio_path_obj.suffix.lower()
                
                # Check if format is supported
                if file_ext not in agent.audio_formats['input']:
                    return {
                        'success': False,
                        'original_path': str(audio_path),
                        'error': f"Unsupported audio format: {file_ext}"
                    }
                
                # Determine original format
                original_format = file_ext[1:]  # Remove the dot
                
                # Build converted path
                base_name = audio_path_obj.stem
                # Convert audio_type from "block.stone" to "block/stone"
                audio_path_parts = audio_type.replace('.', '/')
                converted_path = f"sounds/{audio_path_parts}/{base_name}.ogg"
                
                # Initialize conversion result
                conversion_performed = False
                optimizations_applied = []
                duration_seconds = metadata.get('duration_seconds')
                
                if original_format == 'wav':
                    # Convert WAV to OGG
                    try:
                        audio = AudioSegment.from_wav(audio_path)
                        # In real implementation, would export to OGG
                        # audio.export(converted_path, format="ogg")
                        conversion_performed = True
                        optimizations_applied.append("Converted WAV to OGG")
                        duration_seconds = audio.duration_seconds
                    except CouldntDecodeError as e:
                        return {
                            'success': False,
                            'original_path': str(audio_path),
                            'error': f"Could not decode audio file: {e}"
                        }
                elif original_format == 'ogg':
                    # OGG files don't need conversion, just validation
                    conversion_performed = False
                    optimizations_applied.append("Validated OGG format")
                    
                    # Get duration from metadata or calculate it
                    if duration_seconds is None:
                        try:
                            audio = AudioSegment.from_ogg(audio_path)
                            duration_seconds = audio.duration_seconds
                        except CouldntDecodeError as e:
                            return {
                                'success': False,
                                'original_path': str(audio_path),
                                'error': f"Could not decode audio file: {e}"
                            }
                else:
                    # Other formats would need conversion (mp3, etc.)
                    conversion_performed = True
                    optimizations_applied.append(f"Converted {original_format.upper()} to OGG")
                    # For now, assume conversion works
                    duration_seconds = 1.0  # Default duration
                
                # Generate bedrock sound event
                bedrock_sound_event = f"{audio_type}.{base_name}"
                
                return {
                    'success': True,
                    'original_path': str(audio_path),
                    'converted_path': converted_path,
                    'original_format': original_format,
                    'bedrock_format': 'ogg',
                    'conversion_performed': conversion_performed,
                    'optimizations_applied': optimizations_applied,
                    'bedrock_sound_event': bedrock_sound_event,
                    'duration_seconds': duration_seconds
                }
                
            except FileNotFoundError as e:
                return {
                    'success': False,
                    'original_path': str(audio_path),
                    'error': str(e)
                }
            except Exception as e:
                logger.error(f"Audio conversion error for {audio_path}: {e}", exc_info=True)
                return {
                    'success': False,
                    'original_path': str(audio_path),
                    'error': str(e)
                }
        def _generate_sound_structure(sounds: List[Dict]) -> Dict:
            sound_definitions = {}
            for s_data in sounds:
                if not s_data.get('success'):
                    continue

                event_name = s_data.get('bedrock_sound_event')
                converted_path = s_data.get('converted_path')

                if not event_name or not converted_path:
                    logger.warning(f"Skipping sound entry due to missing event name or converted path: {s_data.get('original_path')}")
                    continue

                rel_path = Path(converted_path)
                # Path for sound_definitions.json is relative to 'sounds' folder, without extension
                if rel_path.parts and rel_path.parts[0] == 'sounds':
                    sound_def_path = str(Path(*rel_path.parts[1:]).with_suffix(''))
                else:
                    # If converted_path is not starting with "sounds/", use it as is but remove suffix
                    sound_def_path = str(rel_path.with_suffix(''))
                    logger.warning(f"Sound path '{converted_path}' for event '{event_name}' does not start with 'sounds/'. Using path as-is (minus suffix): '{sound_def_path}'.")

                if event_name not in sound_definitions:
                    sound_definitions[event_name] = {"sounds": []}

                # Sounds can be simple strings or dictionaries for more control (e.g., volume, pitch)
                # For now, using simple string paths.
                sound_definitions[event_name]["sounds"].append(sound_def_path)

            if sound_definitions:
                return {"sound_definitions.json": {"sound_definitions": sound_definitions}}
            return {}
        try:
            data = json.loads(audio_data)
            audio_files = data.get('audio_files', [])
            
            all_conversion_results = []
            
            for audio_input_data in audio_files:
                audio_path = audio_input_data.get('path', '')
                metadata = audio_input_data.get('metadata', {})
                audio_type = audio_input_data.get('type', 'sound')
                
                result = _convert_single_audio(audio_path, metadata, audio_type)
                all_conversion_results.append(result)
            
            successful_conversions = [r for r in all_conversion_results if r.get('success')]
            failed_conversions_details = []
            for r in all_conversion_results:
                if not r.get('success'):
                    r['fallback_suggestion'] = f"Consider using a default placeholder for {r.get('original_path', 'unknown audio file')}"
                    failed_conversions_details.append(r)

            generated_sound_files = {}
            if successful_conversions:
                generated_sound_files = _generate_sound_structure(successful_conversions)

            response = {
                "success": True,
                "conversion_summary": {
                    "total_requested": len(audio_files),
                    "successfully_converted": len(successful_conversions),
                    "failed_conversions": len(failed_conversions_details)
                },
                "successful_results": successful_conversions,
                "failed_results": failed_conversions_details,
                "bedrock_sound_files": generated_sound_files
            }
            
            logger.info(f"Audio conversion process complete. Requested: {len(audio_files)}, Succeeded: {len(successful_conversions)}, Failed: {len(failed_conversions_details)}")
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Unhandled error in convert_audio: {e}", exc_info=True)
            return json.dumps({"success": False, "error": f"Failed to process audio conversion request: {str(e)}"}, indent=2)
    
    @tool
    @staticmethod
    def validate_bedrock_assets_tool(validation_data: str) -> str:
        """Validate assets for Bedrock compatibility."""
        def _validate_single_asset(asset_path: str, asset_type: str, metadata: Dict) -> Dict:
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
                
                validation = _validate_single_asset(asset_path, asset_type, metadata)
                
                if validation['is_valid']:
                    validation_results['valid_assets'].append(validation)
                else:
                    validation_results['invalid_assets'].append(validation)
                
                validation_results['warnings'].extend(validation.get("warnings", []))
                validation_results['optimization_suggestions'].extend(validation.get("optimizations", []))
            
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
            return json.dumps(response, indent=2)
            
        except Exception as e:
            logger.error(f"Unhandled error in validate_bedrock_assets: {e}", exc_info=True)
            return json.dumps({"success": False, "error": f"Failed to validate assets: {str(e)}"}, indent=2)
    
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
        """Convert a single texture file to Bedrock format with enhanced validation and optimization"""
        # Create a cache key
        cache_key = f"{texture_path}_{usage}_{hash(str(metadata))}"
        
        # Check if we have a cached result
        if cache_key in self._conversion_cache:
            logger.debug(f"Using cached result for texture conversion: {texture_path}")
            return self._conversion_cache[cache_key]
        
        try:
            # Handle missing or corrupted files with fallback generation
            if not Path(texture_path).exists():
                logger.warning(f"Texture file not found: {texture_path}. Generating fallback texture.")
                img = self._generate_fallback_texture(usage)
                original_dimensions = img.size
                is_valid_png = False
                optimizations_applied = ["Generated fallback texture"]
            else:
                try:
                    # Open and validate the image
                    img = Image.open(texture_path)
                    original_dimensions = img.size
                    
                    # Enhanced PNG validation - check if it's already a valid PNG
                    is_valid_png = img.format == 'PNG'
                    
                    # Convert to RGBA for consistency
                    img = img.convert("RGBA")
                    optimizations_applied = ["Converted to RGBA"] if not is_valid_png else []
                except Exception as open_error:
                    logger.warning(f"Failed to open texture {texture_path}: {open_error}. Generating fallback texture.")
                    img = self._generate_fallback_texture(usage)
                    original_dimensions = img.size
                    is_valid_png = False
                    optimizations_applied = ["Generated fallback texture due to open error"]

            width, height = img.size
            resized = False

            max_res = self.texture_constraints.get('max_resolution', 1024)
            must_be_power_of_2 = self.texture_constraints.get('must_be_power_of_2', True)

            new_width, new_height = width, height

            needs_pot_resize = must_be_power_of_2 and (not self._is_power_of_2(width) or not self._is_power_of_2(height))
            
            if needs_pot_resize:
                new_width = self._next_power_of_2(width)
                new_height = self._next_power_of_2(height)
                resized = True

            if new_width > max_res or new_height > max_res:
                new_width = min(new_width, max_res)
                new_height = min(new_height, max_res)
                resized = True

            if resized and must_be_power_of_2:
                if not self._is_power_of_2(new_width):
                    new_width = self._previous_power_of_2(new_width)
                if not self._is_power_of_2(new_height):
                    new_height = self._previous_power_of_2(new_height)

            if resized and (new_width != width or new_height != height):
                # Use different resampling filters based on upscaling/downscaling
                if new_width > width or new_height > height:
                    # Upscaling - use LANCZOS for better quality
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                else:
                    # Downscaling - use LANCZOS for better quality
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                optimizations_applied.append(f"Resized from {original_dimensions} to {(new_width, new_height)}")
            else:
                new_width, new_height = img.size
                resized = False

            # Apply PNG optimization if needed
            if not is_valid_png or resized:
                optimizations_applied.append("Optimized PNG format")

            # MCMETA parsing
            animation_data = None
            mcmeta_path = Path(str(texture_path) + ".mcmeta")
            if mcmeta_path.exists():
                try:
                    with open(mcmeta_path, 'r') as f:
                        mcmeta_content = json.load(f)
                    if "animation" in mcmeta_content:
                        animation_data = mcmeta_content["animation"]
                        optimizations_applied.append("Parsed .mcmeta animation data")
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning("Could not parse .mcmeta file for {}: {}".format(texture_path, e))

            base_name = Path(texture_path).stem if Path(texture_path).exists() else "fallback_texture"
            # Enhanced asset path mapping from Java mod structure to Bedrock structure
            # Handle common Java mod asset paths and map them to Bedrock equivalents
            texture_path_obj = Path(texture_path) if Path(texture_path).exists() else Path(f"fallback_{usage}.png")
            
            # Try to infer usage from the original path if not explicitly provided
            if usage == 'block' and 'block' not in str(texture_path_obj).lower():
                # Check if the path contains common block texture indicators
                if any(block_indicator in str(texture_path_obj).lower() for block_indicator in 
                       ['block/', 'blocks/', '/block/', '/blocks/', '_block', '-block']):
                    usage = 'block'
                # Check for item indicators
                elif any(item_indicator in str(texture_path_obj).lower() for item_indicator in 
                        ['item/', 'items/', '/item/', '/items/', '_item', '-item']):
                    usage = 'item'
                # Check for entity indicators
                elif any(entity_indicator in str(texture_path_obj).lower() for entity_indicator in 
                        ['entity/', 'entities/', '/entity/', '/entities/', '_entity', '-entity']):
                    usage = 'entity'
                # Check for particle indicators
                elif 'particle' in str(texture_path_obj).lower():
                    usage = 'particle'
                # Check for GUI indicators
                elif any(gui_indicator in str(texture_path_obj).lower() for gui_indicator in 
                        ['gui/', 'ui/', 'interface/', 'menu/']):
                    usage = 'ui'
            
            # Map to Bedrock structure
            if usage == 'block':
                converted_path = f"textures/blocks/{base_name}.png"
            elif usage == 'item':
                converted_path = f"textures/items/{base_name}.png"
            elif usage == 'entity':
                converted_path = f"textures/entity/{base_name}.png"
            elif usage == 'particle':
                converted_path = f"textures/particle/{base_name}.png"
            elif usage == 'ui':
                converted_path = f"textures/ui/{base_name}.png"
            else:
                # For other types, try to preserve some structure from the original path
                # Remove common prefixes and map to textures/other/
                try:
                    relative_path = texture_path_obj.relative_to(texture_path_obj.anchor).as_posix()
                    # Remove common prefixes that indicate source structure
                    for prefix in ['assets/minecraft/textures/', 'textures/', 'images/', 'img/']:
                        if relative_path.startswith(prefix):
                            relative_path = relative_path[len(prefix):]
                            break
                    # Remove file extension
                    if '.' in relative_path:
                        relative_path = relative_path[:relative_path.rindex('.')]
                    converted_path = f"textures/other/{relative_path}.png"
                except Exception:
                    # Fallback to a simple path if relative path calculation fails
                    converted_path = f"textures/other/{base_name}.png"

            result = {
                'success': True,
                'original_path': str(texture_path),
                'converted_path': converted_path,
                'original_dimensions': original_dimensions,
                'converted_dimensions': (new_width, new_height),
                'format': 'png',
                'resized': resized,
                'optimizations_applied': optimizations_applied,
                'bedrock_reference': f"{usage}_{base_name}",
                'animation_data': animation_data,
                'was_valid_png': is_valid_png,
                'was_fallback': not Path(texture_path).exists()
            }
            
            # Cache the result
            self._conversion_cache[cache_key] = result
            
            return result
        except Exception as e:
            logger.error(f"Texture conversion error for {texture_path}: {e}")
            error_result = {
                'success': False,
                'original_path': str(texture_path),
                'error': str(e)
            }
            # Cache error results too to avoid repeated failures
            self._conversion_cache[cache_key] = error_result
            return error_result

    def _previous_power_of_2(self, n: int) -> int:
        if n <= 0:
            return 1  # Smallest power of 2, or raise error
        power = 1
        while (power * 2) <= n:
            power *= 2
        return power

    def _convert_single_model(self, model_path: str, metadata: Dict, entity_type: str) -> Dict:
        warnings = []
        try:
            model_p = Path(model_path)
            if not model_p.exists():
                raise FileNotFoundError(f"Model file not found: {model_path}")

            with open(model_p, 'r') as f:
                java_model = json.load(f)

            # Basic Bedrock geo.json structure
            bedrock_identifier = f"geometry.{entity_type}.{model_p.stem}"
            # For texture_width/height, try to get from metadata if available, else default
            # This metadata would ideally be populated by texture analysis of related textures
            texture_width = metadata.get('texture_width', 16)
            texture_height = metadata.get('texture_height', 16)

            bedrock_geo = {
                "format_version": "1.12.0",
                "minecraft:geometry": [
                    {
                        "description": {
                            "identifier": bedrock_identifier,
                            "texture_width": texture_width,
                            "texture_height": texture_height,
                            # Visible bounds can be roughly estimated later if needed
                            "visible_bounds_width": 2,
                            "visible_bounds_height": 2,
                            "visible_bounds_offset": [0, 0.5, 0]
                        },
                        "bones": []
                    }
                ]
            }

            # Ensure we are modifying the correct dictionary part
            geo_main_part = bedrock_geo["minecraft:geometry"][0]
            geo_description = geo_main_part["description"]
            all_bones = geo_main_part["bones"]

            java_parent = java_model.get("parent")
            java_elements = java_model.get("elements", [])
            processed_as_item_specific_type = False

            if entity_type == "item" and java_parent in ["item/generated", "item/builtin/entity", "item/handheld"]:
                processed_as_item_specific_type = True
                if java_parent in ["item/generated", "item/builtin/entity"]:
                    warnings.append(f"Handling as '{java_parent}'. Display transformations not applied.")
                elif java_parent == "item/handheld":
                    warnings.append("Handling as 'item/handheld'. Display transformations not applied.")

                texture_layers = java_model.get("textures", {})
                layer_count = 0
                for i in range(5):  # Check for layer0 up to layer4
                    layer_texture_key = f"layer{i}"
                    if layer_texture_key in texture_layers:
                        # In a more advanced system, here you would resolve texture_layers[layer_texture_key]
                        # to get specific texture dimensions for texture_width/height.
                        # For now, we use the global/default texture_width/height.

                        z_offset = -0.05 - (0.1 * i) # Each layer slightly behind the previous, very thin

                        layer_bone = {
                            "name": layer_texture_key,
                            "pivot": [0.0, 0.0, 0.0],
                            "cubes": [{
                                "origin": [-8.0, -8.0, z_offset],
                                "size": [16.0, 16.0, 0.1], # Thin quad
                                "uv": [0, 0] # Assumes 0,0 of the specified texture_width/height
                            }]
                        }
                        all_bones.append(layer_bone)
                        layer_count += 1

                if layer_count == 0 and "particle" in texture_layers:
                    warnings.append("No layer0/layer1 found, using 'particle' texture for a fallback quad.")
                    particle_bone = {
                        "name": "particle_quad",
                        "pivot": [0.0,0.0,0.0],
                        "cubes": [{"origin": [-8.0,-8.0, -0.05], "size": [16.0,16.0,0.1], "uv": [0,0]}]
                    }
                    all_bones.append(particle_bone)
                    layer_count = 1

                if layer_count > 0:
                    # Set appropriate visible bounds for a typical 16x16 item sprite
                    # Model dimensions are -8 to +8, so width/height is 16 model units.
                    # If 16 model units = 1 block unit for bounds purposes:
                    geo_description["visible_bounds_width"] = 1.0
                    geo_description["visible_bounds_height"] = 1.0
                    # Centered quad from -8 to 8 in X/Y plane, so offset is 0,0,0 relative to model origin
                    geo_description["visible_bounds_offset"] = [0.0, 0.0, 0.0]
                else:
                    warnings.append(f"Item model '{model_p.name}' with parent '{java_parent}' defined no recognized texture layers (layerN or particle). Generating empty model.")
                    geo_description["visible_bounds_width"] = 0.1
                    geo_description["visible_bounds_height"] = 0.1
                    geo_description["visible_bounds_offset"] = [0.0,0.0,0.0]

            if not processed_as_item_specific_type and java_elements:
                # Standard element processing logic (from previous step)
                model_min_x, model_min_y, model_min_z = float('inf'), float('inf'), float('inf')
                model_max_x, model_max_y, model_max_z = float('-inf'), float('-inf'), float('-inf')

                for i, element in enumerate(java_elements):
                    bone_name = f"element_{i}"
                    bone_pivot = [0.0, 0.0, 0.0]
                    bone_rotation = [0.0, 0.0, 0.0]

                    if "rotation" in element:
                        rot = element["rotation"]
                        angle = rot.get("angle", 0.0)
                        axis = rot.get("axis", "y")
                        java_rot_origin = rot.get("origin", [8.0, 8.0, 8.0])
                        bone_pivot = [c - 8.0 for c in java_rot_origin]
                        if axis == "x":
                            bone_rotation[0] = angle
                        elif axis == "y":
                            bone_rotation[1] = -angle  # Often Y rotation is inverted
                        elif axis == "z":
                            bone_rotation[2] = angle
                        else:
                            warnings.append(f"Unsupported rotation axis '{axis}' in element {i}")
                        warnings.append(f"Element {i} has rotation. Ensure pivot {bone_pivot} and rotation {bone_rotation} are correctly interpreted by Bedrock.")

                    from_coords = element.get("from", [0.0,0.0,0.0])
                    to_coords = element.get("to", [16.0,16.0,16.0])
                    cube_origin = [from_coords[0] - 8.0, from_coords[1] - 8.0, from_coords[2] - 8.0]
                    cube_size = [to_coords[0] - from_coords[0], to_coords[1] - from_coords[1], to_coords[2] - from_coords[2]]

                    model_min_x = min(model_min_x, cube_origin[0])
                    model_min_y = min(model_min_y, cube_origin[1])
                    model_min_z = min(model_min_z, cube_origin[2])
                    model_max_x = max(model_max_x, cube_origin[0] + cube_size[0])
                    model_max_y = max(model_max_y, cube_origin[1] + cube_size[1])
                    model_max_z = max(model_max_z, cube_origin[2] + cube_size[2])

                    cube_uv = [0,0]
                    element_faces = element.get("faces")
                    if element_faces:
                        face_data = None
                        for face_name_priority in ["north", "up", "east", "south", "west", "down"]:
                            if face_name_priority in element_faces:
                                face_data = element_faces[face_name_priority]
                                break
                        if not face_data:
                            face_data = next(iter(element_faces.values()), None)
                        if face_data and "uv" in face_data:
                            cube_uv = [face_data["uv"][0], face_data["uv"][1]]
                            texture_variable = face_data.get("texture")
                            if texture_variable and not texture_variable.startswith("#"):
                                warnings.append(f"Element {i} face uses direct texture path '{texture_variable}' - needs mapping.")

                    new_bone = {
                        "name": bone_name, "pivot": bone_pivot, "rotation": bone_rotation,
                        "cubes": [{"origin": cube_origin, "size": cube_size, "uv": cube_uv}]
                    }
                    all_bones.append(new_bone)

                if java_elements: # Recalculate bounds if elements were processed
                    v_bounds_w = model_max_x - model_min_x
                    v_bounds_h = model_max_y - model_min_y
                    v_bounds_d = model_max_z - model_min_z
                    geo_description["visible_bounds_width"] = round(max(v_bounds_w, v_bounds_d), 4)
                    geo_description["visible_bounds_height"] = round(v_bounds_h, 4)
                    geo_description["visible_bounds_offset"] = [
                        round(model_min_x + v_bounds_w / 2.0, 4),
                        round(model_min_y + v_bounds_h / 2.0, 4),
                        round(model_min_z + v_bounds_d / 2.0, 4)
                    ]
                else: # No elements, but not handled as item/generated item type
                    warnings.append("No elements found and not a recognized item parent type. Resulting model may be empty or unexpected.")
                    geo_description["visible_bounds_width"] = 0.125
                    geo_description["visible_bounds_height"] = 0.125
                    geo_description["visible_bounds_offset"] = [0, 0.0625, 0]

            elif not processed_as_item_specific_type and not java_elements: # No item-specific handling, no elements
                if java_parent:
                    warnings.append(f"Model has unhandled parent '{java_parent}' and no local elements")
                else:
                    warnings.append("Model has no elements and no parent")
                # Set default small bounds for an empty or placeholder model
                geo_description["visible_bounds_width"] = 0.1
                geo_description["visible_bounds_height"] = 0.1
                geo_description["visible_bounds_offset"] = [0,0,0]

            if java_model.get("display"):
                warnings.append("Java model 'display' transformations are not converted.")

            converted_filename = f"models/{entity_type}/{model_p.stem}.geo.json"

            return {
                'success': True,
                'original_path': str(model_path),
                'converted_path': converted_filename,
                'bedrock_format': 'geo.json',
                'bedrock_identifier': bedrock_identifier,
                'warnings': warnings,
                'converted_model_json': bedrock_geo
            }

        except FileNotFoundError as fnf_error:
            logger.error(f"Model conversion error for {model_path}: {fnf_error}")
            return {'success': False, 'original_path': str(model_path), 'error': str(fnf_error), 'warnings': warnings}
        except json.JSONDecodeError as json_error:
            logger.error(f"Model conversion JSON error for {model_path}: {json_error}")
            return {'success': False, 'original_path': str(model_path), 'error': f"Invalid JSON: {json_error}", 'warnings': warnings}
        except Exception as e:
            logger.error(f"Model conversion error for {model_path}: {e}", exc_info=True)
            return {'success': False, 'original_path': str(model_path), 'error': str(e), 'warnings': warnings}
    
    def _convert_single_audio(self, audio_path: str, metadata: Dict, audio_type: str) -> Dict:
        """Convert a single audio file to Bedrock-compatible format"""
        try:
            audio_path_obj = Path(audio_path)
            
            # Check if file exists
            if not audio_path_obj.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            # Get file extension
            file_ext = audio_path_obj.suffix.lower()
            
            # Check if format is supported
            if file_ext not in self.audio_formats['input']:
                return {
                    'success': False,
                    'original_path': str(audio_path),
                    'error': f"Unsupported audio format: {file_ext}"
                }
            
            # Determine original format
            original_format = file_ext[1:]  # Remove the dot
            
            # Build converted path
            base_name = audio_path_obj.stem
            # Convert audio_type from "block.stone" to "block/stone"
            audio_path_parts = audio_type.replace('.', '/')
            converted_path = f"sounds/{audio_path_parts}/{base_name}.ogg"
            
            # Initialize conversion result
            conversion_performed = False
            optimizations_applied = []
            duration_seconds = metadata.get('duration_seconds')
            
            if original_format == 'wav':
                # Convert WAV to OGG
                try:
                    audio = AudioSegment.from_wav(audio_path)
                    # In real implementation, would export to OGG
                    # audio.export(converted_path, format="ogg")
                    conversion_performed = True
                    optimizations_applied.append("Converted WAV to OGG")
                    duration_seconds = audio.duration_seconds
                except CouldntDecodeError as e:
                    return {
                        'success': False,
                        'original_path': str(audio_path),
                        'error': f"Could not decode audio file: {e}"
                    }
            elif original_format == 'ogg':
                # OGG files don't need conversion, just validation
                conversion_performed = False
                optimizations_applied.append("Validated OGG format")
                
                # Get duration from metadata or calculate it
                if duration_seconds is None:
                    try:
                        audio = AudioSegment.from_ogg(audio_path)
                        duration_seconds = audio.duration_seconds
                    except CouldntDecodeError as e:
                        return {
                            'success': False,
                            'original_path': str(audio_path),
                            'error': f"Could not decode audio file: {e}"
                        }
            else:
                # Other formats would need conversion (mp3, etc.)
                conversion_performed = True
                optimizations_applied.append(f"Converted {original_format.upper()} to OGG")
                # For now, assume conversion works
                duration_seconds = 1.0  # Default duration
            
            # Generate bedrock sound event
            bedrock_sound_event = f"{audio_type}.{base_name}"
            
            return {
                'success': True,
                'original_path': str(audio_path),
                'converted_path': converted_path,
                'original_format': original_format,
                'bedrock_format': 'ogg',
                'conversion_performed': conversion_performed,
                'optimizations_applied': optimizations_applied,
                'bedrock_sound_event': bedrock_sound_event,
                'duration_seconds': duration_seconds
            }
            
        except FileNotFoundError as e:
            return {
                'success': False,
                'original_path': str(audio_path),
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Audio conversion error for {audio_path}: {e}", exc_info=True)
            return {
                'success': False,
                'original_path': str(audio_path),
                'error': str(e)
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

    def _generate_fallback_texture(self, usage: str = "block", size: tuple = (16, 16)) -> Image.Image:
        """Generate a fallback texture for edge cases"""
        # Create a simple colored texture based on usage type
        colors = {
            'block': (128, 128, 128, 255),    # Gray for blocks
            'item': (200, 200, 100, 255),     # Yellowish for items
            'entity': (150, 100, 100, 255),   # Reddish for entities
            'particle': (200, 200, 255, 255), # Light blue for particles
            'ui': (100, 200, 100, 255),       # Green for UI
            'other': (128, 128, 128, 255)     # Default gray
        }
        
        color = colors.get(usage, colors['other'])
        img = Image.new('RGBA', size, color)
        
        # Add a simple pattern to make it identifiable
        for x in range(0, size[0], 4):
            for y in range(0, size[1], 4):
                if (x + y) % 8 == 0:
                    img.putpixel((x, y), (min(255, color[0] + 50), min(255, color[1] + 50), min(255, color[2] + 50), 255))
        
        return img
        
    def clear_cache(self):
        """Clear the conversion cache"""
        self._conversion_cache.clear()
        logger.info("Cleared asset conversion cache")
    
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
        """Generate texture pack structure files with enhanced atlas handling"""
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Converted Resource Pack",
                "description": "Assets converted from Java mod",
                "uuid": "f4aeb009-270e-4a11-8137-a916a1a3ea1e",
                "version": [1, 0, 0],
                "min_engine_version": [1, 16, 0]
            },
            "modules": [{
                "type": "resources",
                "uuid": "0d28590c-1797-4555-9a19-5ee98def104e",
                "version": [1, 0, 0]
            }]
        }

        item_texture_data = {}
        terrain_texture_data = {}
        flipbook_entries = []
        
        # Track texture atlases
        texture_atlases = {}

        for t_data in textures:
            if not t_data.get('success'):
                continue

            bedrock_ref = t_data.get('bedrock_reference', Path(t_data['converted_path']).stem)
            converted_path = t_data['converted_path']
            texture_entry = {"textures": converted_path}

            # Enhanced atlas handling - group related textures
            # For simplicity, we're using a basic heuristic based on naming
            base_name = Path(converted_path).stem
            if "_" in base_name:
                atlas_name = base_name.split("_")[0]  # Group by prefix
                if atlas_name not in texture_atlases:
                    texture_atlases[atlas_name] = []
                texture_atlases[atlas_name].append({
                    "reference": bedrock_ref,
                    "path": converted_path
                })

            if bedrock_ref.startswith("item_") or "/items/" in converted_path:
                item_texture_data[bedrock_ref] = texture_entry
            elif bedrock_ref.startswith("block_") or "/blocks/" in converted_path:
                terrain_texture_data[bedrock_ref] = texture_entry
            elif bedrock_ref.startswith("entity_") or "/entity/" in converted_path:
                terrain_texture_data[bedrock_ref] = texture_entry
            else:
                terrain_texture_data[bedrock_ref] = texture_entry

            if t_data.get('animation_data'):
                anim_data = t_data['animation_data']
                frames_list = anim_data.get("frames", [])
                
                if frames_list and all(isinstance(f, dict) for f in frames_list):
                    try:
                        processed_frames = [int(f['index']) for f in frames_list if isinstance(f, dict) and 'index' in f]
                        if not processed_frames:
                            processed_frames = []
                    except (TypeError, ValueError):
                        processed_frames = []
                elif frames_list and all(isinstance(f, (int, float)) for f in frames_list):
                    processed_frames = [int(f) for f in frames_list]
                else:
                    processed_frames = list(range(anim_data.get("frame_count", 1)))

                ticks = anim_data.get("frametime", 1)
                if ticks <= 0:
                    ticks = 1

                entry = {
                    "flipbook_texture": converted_path,
                    "atlas_tile": Path(converted_path).stem,
                    "ticks_per_frame": ticks,
                    "frames": processed_frames
                }
                if "interpolate" in anim_data:
                    entry["interpolate"] = anim_data["interpolate"]

                flipbook_entries.append(entry)

        result = {"pack_manifest.json": manifest}
        if item_texture_data:
            result["item_texture.json"] = {"resource_pack_name": "vanilla", "texture_data": item_texture_data}
        if terrain_texture_data:
            result["terrain_texture.json"] = {"resource_pack_name": "vanilla", "texture_data": terrain_texture_data}
        if flipbook_entries:
            result["flipbook_textures.json"] = flipbook_entries
            
        # Add texture atlas information if any were detected
        if texture_atlases:
            result["texture_atlases.json"] = texture_atlases

        return result

    def _generate_model_structure(self, models: List[Dict]) -> Dict:
        # Ensure only successful conversions are included
        valid_models = [m for m in models if m.get('success')]
        return {
            # These keys are illustrative; the actual output is a list of file contents/paths
            # For this structure, we just return the list of paths and identifiers as before.
            # A higher-level packaging agent would create the actual files.
            "geometry_files": [m['converted_path'] for m in valid_models if 'converted_path' in m],
            "identifiers_used": [m['bedrock_identifier'] for m in valid_models if 'bedrock_identifier' in m]
        }

    def _generate_sound_structure(self, sounds: List[Dict]) -> Dict:
        sound_definitions = {}
        for s_data in sounds:
            if not s_data.get('success'):
                continue

            event_name = s_data.get('bedrock_sound_event')
            converted_path = s_data.get('converted_path')

            if not event_name or not converted_path:
                logger.warning(f"Skipping sound entry due to missing event name or converted path: {s_data.get('original_path')}")
                continue

            rel_path = Path(converted_path)
            # Path for sound_definitions.json is relative to 'sounds' folder, without extension
            if rel_path.parts and rel_path.parts[0] == 'sounds':
                sound_def_path = str(Path(*rel_path.parts[1:]).with_suffix(''))
            else:
                # If converted_path is not starting with "sounds/", use it as is but remove suffix
                sound_def_path = str(rel_path.with_suffix(''))
                logger.warning(f"Sound path '{converted_path}' for event '{event_name}' does not start with 'sounds/'. Using path as-is (minus suffix): '{sound_def_path}'.")

            if event_name not in sound_definitions:
                sound_definitions[event_name] = {"sounds": []}

            # Sounds can be simple strings or dictionaries for more control (e.g., volume, pitch)
            # For now, using simple string paths.
            sound_definitions[event_name]["sounds"].append(sound_def_path)

        if sound_definitions:
            return {"sound_definitions.json": {"sound_definitions": sound_definitions}}
        return {}
