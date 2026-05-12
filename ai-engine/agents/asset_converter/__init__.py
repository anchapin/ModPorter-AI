"""
Asset converter package - handles texture, model, and audio asset conversion.
Extracted from asset_converter.py for better modularity.

Public API re-exports from submodules to maintain backwards compatibility.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Optional audio import (removed in Python 3.14)
try:
    from pydub import AudioSegment
    from pydub.exceptions import CouldntDecodeError

    HAS_AUDIO_SUPPORT = True
except ImportError:
    HAS_AUDIO_SUPPORT = False
    AudioSegment = None
    CouldntDecodeError = Exception

logger = logging.getLogger(__name__)

# Import from existing subpackages
from agents.texture_converter import (
    convert_textures as _convert_textures,
    detect_texture_atlas,
    extract_texture_atlas,
    parse_atlas_metadata,
    convert_atlas_to_bedrock,
    convert_java_texture_path,
    validate_texture as _validate_texture,
    validate_textures_batch,
    generate_fallback_for_jar,
    extract_textures_from_jar as _extract_textures_from_jar,
    extract_texture_atlas_from_jar,
    convert_jar_textures_to_bedrock,
    _generate_fallback_texture,
    _get_mod_ids_from_jar,
    _extract_textures_from_alt_locations,
    _map_java_texture_to_bedrock,
    _map_texture_type,
    _map_bedrock_texture_to_java,
    _map_bedrock_type_to_java,
    _get_recommended_resolution,
    _generate_conversion_recommendations,
    _assess_conversion_complexity,
    _convert_single_texture as _tc_convert_single_texture,
    _generate_texture_pack_structure as _tc_generate_texture_pack_structure,
)
from agents.model_converter import (
    _convert_single_model as _mc_convert_single_model,
    _analyze_model,
    _generate_model_structure,
    extract_models_from_jar,
    parse_blockstate,
    resolve_parent_model,
    get_model_elements_with_inheritance,
    convert_blockstate,
)
from agents.audio_converter import (
    _convert_single_audio as _ac_convert_single_audio,
    _analyze_audio,
    _generate_sound_structure,
)

__all__ = [
    # Main class
    "AssetConverterAgent",
    # Texture functions
    "convert_textures",
    "detect_texture_atlas",
    "extract_texture_atlas",
    "parse_atlas_metadata",
    "convert_atlas_to_bedrock",
    "convert_java_texture_path",
    "validate_texture",
    "validate_textures_batch",
    "generate_fallback_for_jar",
    "extract_textures_from_jar",
    "extract_texture_atlas_from_jar",
    "convert_jar_textures_to_bedrock",
    # Model functions
    "convert_models",
    "convert_blockstate",
    "parse_blockstate",
    # Audio functions
    "convert_audio",
    # Utility functions
    "is_power_of_2",
    "next_power_of_2",
    "previous_power_of_2",
    "analyze_assets",
    # Helper exports
    "HAS_AUDIO_SUPPORT",
]


# ============================================================================
# AssetConverterAgent
# ============================================================================


class AssetConverterAgent:
    """
    Asset Converter Agent responsible for converting visual and audio assets
    to Bedrock-compatible formats as specified in PRD Feature 2.
    """

    _instance = None

    def __init__(self):
        from models.smart_assumptions import SmartAssumptionEngine

        self.smart_assumption_engine = SmartAssumptionEngine()

        # Supported asset formats
        self.texture_formats = {
            "input": [".png", ".jpg", ".jpeg", ".tga", ".bmp"],
            "output": ".png",  # Bedrock uses PNG
        }

        self.model_formats = {
            "input": [".obj", ".fbx", ".json"],  # Java mod formats
            "output": ".geo.json",  # Bedrock geometry format
        }

        self.audio_formats = {
            "input": [".ogg", ".wav", ".mp3"],
            "output": ".ogg",  # Bedrock prefers OGG
        }

        # Bedrock asset constraints
        self.texture_constraints = {
            "max_resolution": 1024,  # Max texture size for performance
            "must_be_power_of_2": True,
            "supported_channels": ["rgb", "rgba"],
        }

        self.model_constraints = {
            "max_vertices": 3000,  # Bedrock model complexity limit
            "max_textures": 8,
            "supported_bones": 60,  # Max bones for animated models
        }

        self.audio_constraints = {
            "max_file_size_mb": 10,
            "sample_rates": [22050, 44100],
            "max_duration_seconds": 300,
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
            AssetConverterAgent.validate_bedrock_assets_tool,
            # New tools for Issue #650 - JAR Texture Extraction
            AssetConverterAgent.extract_jar_textures_tool,
            AssetConverterAgent.convert_java_texture_path_tool,
            AssetConverterAgent.validate_texture_tool,
            AssetConverterAgent.generate_fallback_texture_tool,
        ]

    # Delegate texture methods to texture_converter subpackage
    def _convert_single_texture(
        self, texture_path: str, metadata: Dict, usage: str, output_dir: Path = None
    ) -> Dict:
        return _tc_convert_single_texture(self, texture_path, metadata, usage, output_dir)

    def _generate_texture_pack_structure(self, textures: List[Dict]) -> Dict:
        return _tc_generate_texture_pack_structure(self, textures)

    def convert_textures(self, texture_list: str, output_path: str) -> str:
        return _convert_textures(self, texture_list, output_path)

    def detect_texture_atlas(self, texture_path: str) -> Dict:
        return detect_texture_atlas(self, texture_path)

    def extract_texture_atlas(
        self,
        atlas_path: str,
        output_dir: str,
        tile_size: int = 16,
        naming_pattern: str = "tile_{x}_{y}",
    ) -> Dict:
        return extract_texture_atlas(self, atlas_path, output_dir, tile_size, naming_pattern)

    def parse_atlas_metadata(self, mcmeta_path: str) -> Dict:
        return parse_atlas_metadata(self, mcmeta_path)

    def convert_atlas_to_bedrock(
        self, atlas_path: str, output_dir: str, texture_names: List[str] = None
    ) -> Dict:
        return convert_atlas_to_bedrock(self, atlas_path, output_dir, texture_names)

    def convert_java_texture_path(self, java_path: str, bedrock_type: str = "blocks") -> str:
        return convert_java_texture_path(self, java_path, bedrock_type)

    def validate_texture(self, texture_path: str) -> Dict:
        return _validate_texture(self, texture_path)

    def generate_fallback_for_jar(
        self, output_path: str, block_name: str, texture_type: str = "blocks"
    ) -> Dict:
        return generate_fallback_for_jar(self, output_path, block_name, texture_type)

    def _get_recommended_resolution(self, width: int, height: int) -> str:
        return _get_recommended_resolution(self, width, height)

    def _generate_conversion_recommendations(self, analysis: Dict) -> List[str]:
        return _generate_conversion_recommendations(self, analysis)

    def _assess_conversion_complexity(self, analysis: Dict) -> str:
        return _assess_conversion_complexity(self, analysis)

    def extract_textures_from_jar(
        self, jar_path: str, output_dir: str, texture_types: Optional[List[str]] = None
    ) -> Dict:
        return _extract_textures_from_jar(self, jar_path, output_dir, texture_types)

    def _map_java_texture_to_bedrock(self, java_path: str) -> str:
        return _map_java_texture_to_bedrock(self, java_path)

    def _map_texture_type(self, java_type: str) -> str:
        return _map_texture_type(self, java_type)

    def _map_bedrock_texture_to_java(self, bedrock_path: str, namespace: str) -> str:
        return _map_bedrock_texture_to_java(self, bedrock_path, namespace)

    def _map_bedrock_type_to_java(self, bedrock_type: str) -> str:
        return _map_bedrock_type_to_java(self, bedrock_type)

    def validate_textures_batch(self, texture_paths: List[str], metadata: Dict = None) -> Dict:
        return validate_textures_batch(self, texture_paths, metadata)

    def extract_texture_atlas_from_jar(
        self, jar_path: str, atlas_type: str, output_dir: str
    ) -> Dict:
        return extract_texture_atlas_from_jar(self, jar_path, atlas_type, output_dir)

    def convert_jar_textures_to_bedrock(
        self, jar_path: str, output_dir: str, namespace: str = None
    ) -> Dict:
        return convert_jar_textures_to_bedrock(self, jar_path, output_dir, namespace)

    def _generate_fallback_texture(self, usage: str = "block", size: tuple = (16, 16)):
        return _generate_fallback_texture(self, usage, size)

    def _get_mod_ids_from_jar(self, jar) -> List[str]:
        return _get_mod_ids_from_jar(self, jar)

    def _extract_textures_from_alt_locations(self, jar, output_path: Path):
        return _extract_textures_from_alt_locations(self, jar, output_path)

    # Delegate model methods to model_converter subpackage
    def _convert_single_model(self, model_path: str, metadata: Dict, entity_type: str) -> Dict:
        return _mc_convert_single_model(self, model_path, metadata, entity_type)

    def _analyze_model(self, model_path: str, metadata: Dict) -> Dict:
        return _analyze_model(self, model_path, metadata)

    def _generate_model_structure(self, models: List[Dict]) -> Dict:
        return _generate_model_structure(self, models)

    def _extract_models_from_jar(
        self, jar_path: str, output_dir: str, namespace: str = None
    ) -> Dict:
        return extract_models_from_jar(jar_path, output_dir, namespace)

    def _parse_blockstate(self, blockstate_data: Dict) -> Dict:
        return parse_blockstate(blockstate_data)

    def _resolve_parent_model(
        self, model_data: Dict, model_cache: Dict, namespace: str = None
    ) -> Tuple[List[Dict], List[str]]:
        return resolve_parent_model(model_data, model_cache, namespace)

    def _get_model_elements_with_inheritance(
        self, model_json: Dict, all_models: Dict, namespace: str = None
    ) -> Tuple[List[Dict], List[str]]:
        return get_model_elements_with_inheritance(model_json, all_models, namespace)

    def _convert_blockstate(
        self, blockstate_path: str, model_output_dir: str, all_models: Dict, namespace: str = None
    ) -> Dict:
        return convert_blockstate(self, blockstate_path, model_output_dir, all_models, namespace)

    # Delegate audio methods to audio_converter subpackage
    def _convert_single_audio(self, audio_path: str, metadata: Dict, audio_type: str) -> Dict:
        return _ac_convert_single_audio(self, audio_path, metadata, audio_type)

    def _analyze_audio(self, audio_path: str, metadata: Dict) -> Dict:
        return _analyze_audio(self, audio_path, metadata)

    def _generate_sound_structure(self, sounds: List[Dict]) -> Dict:
        return _generate_sound_structure(self, sounds)

    # Utility functions
    def _is_power_of_2(self, n: int) -> bool:
        return n > 0 and (n & (n - 1)) == 0

    def _next_power_of_2(self, n: int) -> int:
        power = 1
        while power < n:
            power *= 2
        return power

    def _previous_power_of_2(self, n: int) -> int:
        if n <= 0:
            return 1
        power = 1
        while (power * 2) <= n:
            power *= 2
        return power

    def clear_cache(self):
        """Clear the conversion cache"""
        self._conversion_cache.clear()
        logger.info("Cleared asset conversion cache")


# ============================================================================
# Standalone utility functions (not bound to class)
# ============================================================================


def is_power_of_2(n: int) -> bool:
    """Check if a number is a power of 2"""
    return n > 0 and (n & (n - 1)) == 0


def next_power_of_2(n: int) -> int:
    """Get the next power of 2 greater than or equal to n"""
    power = 1
    while power < n:
        power *= 2
    return power


def previous_power_of_2(n: int) -> int:
    """Get the previous power of 2 less than or equal to n"""
    if n <= 0:
        return 1
    power = 1
    while (power * 2) <= n:
        power *= 2
    return power


# Alias for convert_textures
def convert_models(model_list: str, output_path: str) -> str:
    """Convert models to Bedrock format"""
    agent = AssetConverterAgent.get_instance()
    return agent.convert_models_tool(model_list)


def convert_audio(audio_list: str, output_path: str) -> str:
    """Convert audio to Bedrock format"""
    agent = AssetConverterAgent.get_instance()
    return agent.convert_audio_tool(audio_list)


def analyze_assets_tool(asset_data: str) -> str:
    """Analyze assets for conversion."""
    return analyze_assets(asset_data)


def analyze_assets(asset_data: str) -> str:
    """Analyze assets for conversion."""
    # Analyze assets using agent's analysis capabilities
    try:
        data = json.loads(asset_data) if isinstance(asset_data, str) else asset_data
        asset_list = data if isinstance(data, list) else data.get("asset_list", [data])
    except Exception:
        asset_list = [{"path": str(asset_data)}]

    results = {
        "textures": {"count": 0, "conversions_needed": [], "issues": []},
        "models": {"count": 0, "conversions_needed": [], "issues": []},
        "audio": {"count": 0, "conversions_needed": [], "issues": []},
        "other": {"count": 0, "files": [], "issues": []},
    }

    for asset in asset_list:
        if isinstance(asset, str):
            path = asset
        else:
            path = asset.get("path", "") if isinstance(asset, dict) else str(asset)
        ext = Path(path).suffix.lower()

        if ext in [".png", ".jpg", ".jpeg", ".tga", ".bmp"]:
            results["textures"]["count"] += 1
            if ext != ".png":
                results["textures"]["conversions_needed"].append(
                    {"path": path, "needs_conversion": True}
                )
        elif ext in [".obj", ".fbx", ".json"]:
            results["models"]["count"] += 1
            if ext != ".geo.json":
                results["models"]["conversions_needed"].append(
                    {"path": path, "needs_conversion": True}
                )
        elif ext in [".ogg", ".wav", ".mp3"]:
            results["audio"]["count"] += 1
            if ext != ".ogg":
                results["audio"]["conversions_needed"].append(
                    {"path": path, "needs_conversion": True}
                )
        else:
            results["other"]["count"] += 1
            results["other"]["files"].append(path)

    return json.dumps(
        {"success": True, "analysis_results": results, "total_assets": len(asset_list)}
    )
