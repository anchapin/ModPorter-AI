"""
Asset converter package - handles texture, model, and audio asset conversion.
Extracted from asset_converter.py for better modularity.

Public API re-exports from submodules to maintain backwards compatibility.
"""

import json
import logging
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

# Optional audio import (removed in Python 3.14)
try:
    from pydub import AudioSegment
    from pydub.exceptions import CouldntDecodeError

    HAS_AUDIO_SUPPORT = True
except ImportError:
    HAS_AUDIO_SUPPORT = False
    AudioSegment = None
    CouldntDecodeError = Exception

# PIL Image for texture processing
try:
    from PIL import Image as _PILImage

    Image = _PILImage
except ImportError:
    Image = None
    _PILImage = None

logger = logging.getLogger(__name__)

# Import from existing subpackages
from agents.texture_converter import (
    convert_textures as _convert_textures,
    convert_textures as convert_textures,  # re-export for backward compat
    detect_texture_atlas,
    extract_texture_atlas,
    parse_atlas_metadata,
    convert_atlas_to_bedrock,
    convert_java_texture_path,
    validate_texture as _validate_texture,
    validate_texture,
    validate_textures_batch,
    generate_fallback_for_jar,
    extract_textures_from_jar as _extract_textures_from_jar,
    extract_textures_from_jar,
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


# ============================================================================
# Tool function wrapper to provide .run() interface for backward compat
# ============================================================================


class ToolFunction:
    """Wrapper to make standalone functions compatible with CrewAI tool interface (.run())"""

    def __init__(self, func):
        self._func = func

    @property
    def func(self):
        """Access the wrapped function directly (for tests using .func())."""
        return self._func

    def run(self, **kwargs):
        """Call the wrapped function with flattened kwargs."""
        # Handle the case where a single keyword arg wraps the data
        if len(kwargs) == 1:
            key = list(kwargs.keys())[0]
            if key in (
                "asset_data",
                "texture_data",
                "model_data",
                "audio_data",
                "jar_path",
                "atlas_path",
                "model_data",
                "audio_list",
                "jar_data",
                "path_data",
                "texture_data",
                "validation_data",
            ):
                return self._func(kwargs[key])
        return self._func(**kwargs)


# ============================================================================
# Standalone tool functions (formerly @staticmethod methods with @tool decorator)
# ============================================================================


def _assess_conversion_complexity(analysis: Dict) -> str:
    """Assess the overall conversion complexity"""
    total_issues = (
        len(analysis.get("textures", {}).get("issues", []))
        + len(analysis.get("models", {}).get("issues", []))
        + len(analysis.get("audio", {}).get("issues", []))
    )
    total_assets = (
        analysis.get("textures", {}).get("count", 0)
        + analysis.get("models", {}).get("count", 0)
        + analysis.get("audio", {}).get("count", 0)
    )

    if total_assets == 0:
        return "none"

    issue_ratio = total_issues / total_assets if total_assets > 0 else 0

    if total_issues == 0 and total_assets >= 3:
        return "moderate"
    if issue_ratio < 0.3:
        return "simple"
    elif issue_ratio <= 0.65:
        return "moderate"
    else:
        return "complex"


def analyze_assets_tool_func(asset_data: str) -> str:
    """Analyze assets for conversion."""
    AssetConverterAgent.get_instance()

    try:
        data = json.loads(asset_data) if isinstance(asset_data, str) else asset_data
        # Handle nested array format from tests: [["path", {metadata}], ...]
        if isinstance(data, list) and all(isinstance(d, list) for d in data):
            asset_list = [{"path": d[0], "metadata": d[1] if len(d) > 1 else {}} for d in data]
        elif isinstance(data, list):
            asset_list = data
        else:
            asset_list = data.get("asset_list", [data])
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"success": False, "error": "Invalid input format"})

    analysis_results = {
        "textures": {"count": 0, "needs_conversion": 0, "issues": [], "conversions_needed": []},
        "models": {"count": 0, "issues": [], "conversions_needed": []},
        "audio": {"count": 0, "issues": [], "conversions_needed": []},
        "other": {"count": 0},
    }

    agent = AssetConverterAgent.get_instance()

    for asset in asset_list:
        path = (
            asset
            if isinstance(asset, str)
            else (asset.get("path", "") if isinstance(asset, dict) else "")
        )
        metadata = asset.get("metadata", {}) if isinstance(asset, dict) else {}

        file_ext = Path(path).suffix.lower()

        if file_ext in [".png", ".jpg", ".jpeg", ".tga", ".bmp"]:
            analysis_results["textures"]["count"] += 1
            width = metadata.get("width", 16)
            height = metadata.get("height", 16)
            if not (width > 0 and (width & (width - 1)) == 0) or not (
                height > 0 and (height & (height - 1)) == 0
            ):
                analysis_results["textures"]["needs_conversion"] += 1
                analysis_results["textures"]["issues"].append(
                    f"Resolution {width}x{height} is not power of 2"
                )
            if width > 1024 or height > 1024:
                analysis_results["textures"]["issues"].append(
                    f"Resolution {width}x{height} exceeds maximum 1024"
                )
        elif file_ext in [".obj", ".fbx", ".json"]:
            analysis_results["models"]["count"] += 1
            vertices = metadata.get("vertices", 0)
            if vertices > 3000:
                analysis_results["models"]["issues"].append(
                    f"Vertex count {vertices} exceeds maximum 3000"
                )
        elif file_ext in [".ogg", ".wav", ".mp3"]:
            analysis_results["audio"]["count"] += 1
            duration = metadata.get("duration_seconds", 0)
            if duration > 300:
                analysis_results["audio"]["issues"].append(
                    f"Duration {duration}s exceeds maximum 300s"
                )
        else:
            analysis_results["other"]["count"] += 1

    total_assets = sum(analysis_results[k]["count"] for k in analysis_results)

    return json.dumps(
        {
            "success": True,
            "total_assets": total_assets,
            "analysis_results": analysis_results,
            "conversion_complexity": _assess_conversion_complexity(analysis_results),
        }
    )


def convert_textures_tool_func(texture_data: str) -> str:
    """Convert textures to Bedrock format."""
    agent = AssetConverterAgent.get_instance()

    try:
        data = json.loads(texture_data) if isinstance(texture_data, str) else texture_data
        texture_list = data if isinstance(data, list) else data.get("textures", data.get("texture_list", []))
        output_dir = (
            data.get("output_path", "/tmp/texture_output")
            if isinstance(data, dict)
            else "/tmp/texture_output"
        )
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"success": False, "error": "Invalid input format"})

    if not texture_list:
        return json.dumps({"success": False, "error": "No textures provided"})

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    conversion_results = []
    errors = []

    successful_results = []
    for texture_info in texture_list:
        texture_path = (
            texture_info if isinstance(texture_info, str) else texture_info.get("path", "")
        )
        if not texture_path:
            continue

        try:
            result = agent._convert_single_texture(texture_path, {}, "texture", output_path)
            if result.get("success"):
                conversion_results.append(result)
                successful_results.append({
                    "resized": result.get("resized", False),
                    "was_fallback": result.get("was_fallback", False),
                    "converted_dimensions": list(result.get("converted_dimensions", [])),
                    "original_path": result.get("original_path", texture_path),
                    "converted_path": result.get("converted_path", ""),
                })
        except Exception as e:
            errors.append({"texture": texture_path, "error": str(e)})

    bedrock_pack_files = {}
    if conversion_results:
        pack_structure = agent._generate_texture_pack_structure(conversion_results)
        bedrock_pack_files = pack_structure

    return json.dumps(
        {
            "success": True,
            "conversion_summary": {
                "successfully_converted": len(conversion_results),
            },
            "successful_results": successful_results,
            "bedrock_pack_files": bedrock_pack_files,
            "converted_textures": [r.get("converted_path", "") for r in conversion_results],
            "total_textures": len(texture_list),
            "failed_conversions": len(errors),
            "errors": errors,
        }
    )


def convert_models_tool_func(model_data: str) -> str:
    """Convert models to Bedrock format."""
    agent = AssetConverterAgent.get_instance()

    try:
        data = json.loads(model_data) if isinstance(model_data, str) else model_data
        model_list = data if isinstance(data, list) else data.get("models", data.get("model_list", []))
        output_dir = (
            data.get("output_path", "/tmp/model_output")
            if isinstance(data, dict)
            else "/tmp/model_output"
        )
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"success": False, "error": "Invalid input format"})

    if not model_list:
        return json.dumps({"success": False, "error": "No models provided"})

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    successful_results = []
    errors = []

    for model_info in model_list:
        model_path = model_info if isinstance(model_info, str) else model_info.get("path", "")
        if not model_path:
            continue

        entity_type = "entity"
        if isinstance(model_info, dict) and "entity_type" in model_info:
            entity_type = model_info["entity_type"]
        else:
            try:
                with open(model_path, "r") as f:
                    model_data = json.load(f)
                parent = model_data.get("parent", "")
                if parent.startswith("block/"):
                    entity_type = "block"
                elif parent.startswith("item/"):
                    entity_type = "item"
            except Exception:
                pass

        try:
            result = agent._convert_single_model(model_path, {}, entity_type)
            if result.get("success"):
                successful_results.append({
                    "converted_path": result.get("converted_path", ""),
                    "bedrock_identifier": result.get("bedrock_identifier", ""),
                    "original_path": model_path,
                })
        except Exception as e:
            errors.append({"model": model_path, "error": str(e)})

    return json.dumps(
        {
            "success": True,
            "conversion_summary": {
                "total_requested": len(model_list),
                "successfully_converted": len(successful_results),
            },
            "successful_results": successful_results,
            "failed_conversions": len(errors),
            "errors": errors,
        }
    )


def convert_audio_tool_func(audio_data: str) -> str:
    """Convert audio to Bedrock format."""
    if not HAS_AUDIO_SUPPORT:
        return json.dumps(
            {"success": False, "error": "Audio support not available (pydub not installed)"}
        )

    agent = AssetConverterAgent.get_instance()

    try:
        data = json.loads(audio_data) if isinstance(audio_data, str) else audio_data
        audio_list = data if isinstance(data, list) else data.get("audio_list", [])
        output_dir = (
            data.get("output_path", "/tmp/audio_output")
            if isinstance(data, dict)
            else "/tmp/audio_output"
        )
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"success": False, "error": "Invalid input format"})

    if not audio_list:
        return json.dumps({"success": False, "error": "No audio files provided"})

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    converted = []
    errors = []

    for audio_info in audio_list:
        audio_path = audio_info if isinstance(audio_info, str) else audio_info.get("path", "")
        if not audio_path:
            continue

        try:
            result = agent._convert_single_audio(audio_path, {}, "ambient")
            if result.get("success"):
                converted.append(audio_path)
        except Exception as e:
            errors.append({"audio": audio_path, "error": str(e)})

    return json.dumps(
        {
            "success": True,
            "conversion_summary": {
                "total_requested": len(audio_list),
                "successfully_converted": len(converted),
            },
            "converted_audio": converted,
            "failed_conversions": len(errors),
            "errors": errors,
        }
    )


def validate_bedrock_assets_tool_func(assets_data: str) -> str:
    """Validate Bedrock assets."""
    agent = AssetConverterAgent.get_instance()

    try:
        data = json.loads(assets_data) if isinstance(assets_data, str) else assets_data
        assets = data.get("assets", []) if isinstance(data, dict) else data
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"success": False, "error": "Invalid input format"})

    results = []
    warning_count = 0
    optimization_count = 0
    for asset in assets:
        path = asset if isinstance(asset, str) else asset.get("path", "")
        asset_type = asset.get("type", "unknown") if isinstance(asset, dict) else "unknown"
        metadata = asset.get("metadata", {}) if isinstance(asset, dict) else {}

        validation = {"path": path, "valid": True, "issues": [], "warnings": []}

        file_ext = Path(path).suffix.lower()
        if asset_type == "texture" or file_ext in [".png", ".jpg", ".jpeg", ".tga", ".bmp"]:
            result = agent.validate_texture(path, metadata if metadata else None)
            if not result.get("valid", False):
                validation["valid"] = False
                validation["issues"].extend(result.get("errors", []))
            validation["warnings"] = result.get("warnings", [])
            if validation["warnings"]:
                warning_count += 1
            if result.get("properties", {}).get("format") != "PNG":
                optimization_count += 1

        results.append(validation)

    return json.dumps({
        "success": True,
        "results": results,
        "quality_metrics": {
            "total_assets": len(assets),
            "warning_count": warning_count,
            "optimization_count": optimization_count,
        }
    })


def extract_jar_textures_tool_func(jar_data: str) -> str:
    """Extract textures from JAR file."""
    agent = AssetConverterAgent.get_instance()

    try:
        data = json.loads(jar_data) if isinstance(jar_data, str) else jar_data
        jar_path = data.get("jar_path", "") if isinstance(data, dict) else ""
        output_dir = (
            data.get("output_dir", "/tmp/jar_textures")
            if isinstance(data, dict)
            else "/tmp/jar_textures"
        )
        namespace = data.get("namespace", None)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"success": False, "error": "Invalid input format"})

    if not jar_path:
        return json.dumps({"success": False, "error": "No JAR path provided"})

    try:
        result = agent.convert_jar_textures_to_bedrock(jar_path, output_dir, namespace)
        result["extracted_count"] = len(result.get("extracted", []))
        result["converted_count"] = len(result.get("converted", []))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def convert_java_texture_path_tool_func(path_data: str) -> str:
    """Convert Java texture path to Bedrock."""
    agent = AssetConverterAgent.get_instance()

    try:
        data = json.loads(path_data) if isinstance(path_data, str) else path_data
        java_path = data.get("path", "") if isinstance(data, dict) else ""
        bedrock_type = data.get("type", "blocks") if isinstance(data, dict) else "blocks"
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"success": False, "error": "Invalid input format"})

    if not java_path:
        return json.dumps({"success": False, "error": "No path provided"})

    result = agent.convert_java_texture_path(java_path, bedrock_type)
    return json.dumps({"success": True, "bedrock_path": result})


def validate_texture_tool_func(texture_path: str) -> str:
    """Validate a texture for Bedrock compatibility."""
    agent = AssetConverterAgent.get_instance()

    if not texture_path:
        return json.dumps({"success": False, "error": "No texture path provided"})

    result = agent.validate_texture(texture_path)
    return json.dumps({"success": True, "result": result})


def generate_fallback_texture_tool_func(texture_data: str) -> str:
    """Generate fallback texture for missing assets."""
    agent = AssetConverterAgent.get_instance()

    try:
        data = json.loads(texture_data) if isinstance(texture_data, str) else texture_data
        output_path = data.get("output_path", "") if isinstance(data, dict) else ""
        block_name = data.get("block_name", "unknown") if isinstance(data, dict) else "unknown"
        texture_type = data.get("type", "blocks") if isinstance(data, dict) else "blocks"
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"success": False, "error": "Invalid input format"})

    if not output_path:
        return json.dumps({"success": False, "error": "No output path provided"})

    result = agent.generate_fallback_for_jar(output_path, block_name, texture_type)
    return json.dumps({"success": True, "result": result})


# Create tool wrappers (formerly @tool decorated static methods)
analyze_assets_tool = ToolFunction(analyze_assets_tool_func)
convert_textures_tool = ToolFunction(convert_textures_tool_func)
convert_models_tool = ToolFunction(convert_models_tool_func)
convert_audio_tool = ToolFunction(convert_audio_tool_func)
validate_bedrock_assets_tool = ToolFunction(validate_bedrock_assets_tool_func)
extract_jar_textures_tool = ToolFunction(extract_jar_textures_tool_func)
convert_java_texture_path_tool = ToolFunction(convert_java_texture_path_tool_func)
validate_texture_tool = ToolFunction(validate_texture_tool_func)
generate_fallback_texture_tool = ToolFunction(generate_fallback_texture_tool_func)


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
    "zipfile",
    # Tool wrappers (for CrewAI compatibility with .run() interface)
    "analyze_assets_tool",
    "convert_textures_tool",
    "convert_models_tool",
    "convert_audio_tool",
    "validate_bedrock_assets_tool",
    "extract_jar_textures_tool",
    "convert_java_texture_path_tool",
    "validate_texture_tool",
    "generate_fallback_texture_tool",
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

    # Inherit tool references from module-level ToolFunction wrappers
    # This enables both: agent.analyze_assets_tool.run() AND analyze_assets_tool.run()
    analyze_assets_tool = globals().get("analyze_assets_tool")
    convert_textures_tool = globals().get("convert_textures_tool")
    convert_models_tool = globals().get("convert_models_tool")
    convert_audio_tool = globals().get("convert_audio_tool")
    validate_bedrock_assets_tool = globals().get("validate_bedrock_assets_tool")
    extract_jar_textures_tool = globals().get("extract_jar_textures_tool")
    convert_java_texture_path_tool = globals().get("convert_java_texture_path_tool")
    validate_texture_tool = globals().get("validate_texture_tool")
    generate_fallback_texture_tool = globals().get("generate_fallback_texture_tool")

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

    def _analyze_texture(self, texture_path: str, metadata: Dict) -> Dict:
        """Analyze a single texture for conversion needs."""
        width = metadata.get("width", 16)
        height = metadata.get("height", 16)
        channels = metadata.get("channels", "rgba")
        file_ext = Path(texture_path).suffix.lower()

        issues = []
        needs_conversion = False

        # Check resolution
        if (
            width > self.texture_constraints["max_resolution"]
            or height > self.texture_constraints["max_resolution"]
        ):
            issues.append(
                f"Resolution {width}x{height} exceeds maximum {self.texture_constraints['max_resolution']}"
            )
            needs_conversion = True

        # Check if power of 2
        if self.texture_constraints["must_be_power_of_2"]:
            if not self._is_power_of_2(width) or not self._is_power_of_2(height):
                issues.append(f"Resolution {width}x{height} is not power of 2")
                needs_conversion = True

        # Check format
        if file_ext != self.texture_formats["output"]:
            needs_conversion = True

        # Check channels
        if channels not in self.texture_constraints["supported_channels"]:
            issues.append(f"Unsupported channel format: {channels}")
            needs_conversion = True

        return {
            "path": texture_path,
            "needs_conversion": needs_conversion,
            "issues": issues,
            "current_format": file_ext,
            "target_format": self.texture_formats["output"],
            "current_resolution": f"{width}x{height}",
            "recommended_resolution": self._get_recommended_resolution(width, height),
        }

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

    def validate_texture(self, texture_path: str, metadata: Dict = None) -> Dict:
        return _validate_texture(self, texture_path, metadata)

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
        self, jar_path: str, output_dir: str, namespace: str = None
    ) -> Dict:
        return _extract_textures_from_jar(self, jar_path, output_dir, namespace)

    def _map_java_texture_to_bedrock(self, java_path: str) -> str:
        return _map_java_texture_to_bedrock(self, java_path)

    def _map_texture_type(self, java_type: str) -> str:
        return _map_texture_type(self, java_type)

    def _map_bedrock_texture_to_java(self, bedrock_path: str, namespace: str) -> str:
        return _map_bedrock_texture_to_java(self, bedrock_path, namespace)

    def _map_bedrock_type_to_java(self, bedrock_type: str) -> str:
        return _map_bedrock_type_to_java(self, bedrock_type)

    def validate_textures_batch(self, texture_paths: List[str], metadata: Dict = None) -> Dict:
        from agents.texture_converter.validation import validate_textures_batch as _validate_textures_batch
        return _validate_textures_batch(self, texture_paths, metadata)

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


def analyze_assets(asset_data: str) -> str:
    """Analyze assets for conversion."""
    return analyze_assets_tool_func(asset_data)
