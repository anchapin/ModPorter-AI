"""
Asset Converter Agent - Tools module.

Contains utility and analysis functions for asset conversion.
"""

import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def _is_power_of_2(n: int) -> bool:
    """Check if a number is a power of 2"""
    return n > 0 and (n & (n - 1)) == 0


def _assess_conversion_complexity(analysis: Dict) -> str:
    """Assess the overall conversion complexity"""
    total_issues = (
        len(analysis["textures"]["issues"])
        + len(analysis["models"]["issues"])
        + len(analysis["audio"]["issues"])
    )
    total_assets = (
        analysis["textures"]["count"] + analysis["models"]["count"] + analysis["audio"]["count"]
    )

    if total_assets == 0:
        return "none"

    issue_ratio = total_issues / total_assets if total_assets > 0 else 0

    if issue_ratio < 0.3:
        return "simple"
    elif issue_ratio < 0.7:
        return "moderate"
    else:
        return "complex"


@staticmethod
def analyze_assets_tool(asset_data: str) -> str:  # noqa: C901
    """Analyze assets for conversion."""
    from agents.asset_converter.base import AssetConverterAgent

    agent = AssetConverterAgent.get_instance()

    def _analyze_texture(texture_path: str, metadata: Dict) -> Dict:
        """Analyze a single texture for conversion needs"""
        width = metadata.get("width", 16)
        height = metadata.get("height", 16)
        channels = metadata.get("channels", "rgba")
        file_ext = Path(texture_path).suffix.lower()

        issues = []
        needs_conversion = False

        # Check resolution
        if (
            width > agent.texture_constraints["max_resolution"]
            or height > agent.texture_constraints["max_resolution"]
        ):
            issues.append(
                f"Resolution {width}x{height} exceeds maximum {agent.texture_constraints['max_resolution']}"
            )
            needs_conversion = True

        # Check if power of 2
        if agent.texture_constraints["must_be_power_of_2"]:
            if not _is_power_of_2(width) or not _is_power_of_2(height):
                issues.append(f"Resolution {width}x{height} is not power of 2")
                needs_conversion = True

        # Check format
        if file_ext != agent.texture_formats["output"]:
            needs_conversion = True

        # Check channels
        if channels not in agent.texture_constraints["supported_channels"]:
            issues.append(f"Unsupported channel format: {channels}")
            needs_conversion = True

        return {
            "path": texture_path,
            "needs_conversion": needs_conversion,
            "issues": issues,
            "current_format": file_ext,
            "target_format": agent.texture_formats["output"],
            "current_resolution": f"{width}x{height}",
            "recommended_resolution": agent._get_recommended_resolution(width, height),
        }

    def _analyze_model(model_path: str, metadata: Dict) -> Dict:
        """Analyze a single model for conversion needs"""
        vertex_count = metadata.get("vertices", 100)
        texture_count = metadata.get("textures", 1)
        bone_count = metadata.get("bones", 0)
        file_ext = Path(model_path).suffix.lower()

        issues = []
        needs_conversion = False

        # Check complexity
        if vertex_count > agent.model_constraints["max_vertices"]:
            issues.append(
                f"Vertex count {vertex_count} exceeds maximum {agent.model_constraints['max_vertices']}"
            )
            needs_conversion = True

        if texture_count > agent.model_constraints["max_textures"]:
            issues.append(
                f"Texture count {texture_count} exceeds maximum {agent.model_constraints['max_textures']}"
            )
            needs_conversion = True

        if bone_count > agent.model_constraints["supported_bones"]:
            issues.append(
                f"Bone count {bone_count} exceeds maximum {agent.model_constraints['supported_bones']}"
            )
            needs_conversion = True

        # Check format
        if file_ext != agent.model_formats["output"]:
            needs_conversion = True

        return {
            "path": model_path,
            "needs_conversion": needs_conversion,
            "issues": issues,
            "current_format": file_ext,
            "target_format": agent.model_formats["output"],
            "complexity": {
                "vertices": vertex_count,
                "textures": texture_count,
                "bones": bone_count,
            },
        }

    def _analyze_audio(audio_path: str, metadata: Dict) -> Dict:
        """Analyze a single audio file for conversion needs"""
        file_size_mb = metadata.get("file_size_mb", 1)
        sample_rate = metadata.get("sample_rate", 44100)
        duration = metadata.get("duration_seconds", 1)
        file_ext = Path(audio_path).suffix.lower()

        issues = []
        needs_conversion = False

        # Check file size
        if file_size_mb > agent.audio_constraints["max_file_size_mb"]:
            issues.append(
                f"File size {file_size_mb}MB exceeds maximum {agent.audio_constraints['max_file_size_mb']}MB"
            )
            needs_conversion = True

        # Check sample rate
        if sample_rate not in agent.audio_constraints["sample_rates"]:
            issues.append(
                f"Sample rate {sample_rate} not in supported rates {agent.audio_constraints['sample_rates']}"
            )
            needs_conversion = True

        # Check duration
        if duration > agent.audio_constraints["max_duration_seconds"]:
            issues.append(
                f"Duration {duration}s exceeds maximum {agent.audio_constraints['max_duration_seconds']}s"
            )
            needs_conversion = True

        # Check format
        if file_ext != agent.audio_formats["output"]:
            needs_conversion = True

        return {
            "path": audio_path,
            "needs_conversion": needs_conversion,
            "issues": issues,
            "current_format": file_ext,
            "target_format": agent.audio_formats["output"],
            "current_specs": {
                "file_size_mb": file_size_mb,
                "sample_rate": sample_rate,
                "duration": duration,
            },
        }

    try:
        data = json.loads(asset_data)
        if isinstance(data, list):
            asset_list = [{"path": p} for p in data]
        elif isinstance(data, dict):
            asset_list = data.get("asset_list", [])
        else:
            asset_list = [{"path": str(data)}]

        analysis_results = {
            "textures": {"count": 0, "conversions_needed": [], "issues": []},
            "models": {"count": 0, "conversions_needed": [], "issues": []},
            "audio": {"count": 0, "conversions_needed": [], "issues": []},
            "other": {"count": 0, "files": [], "issues": []},
        }

        for asset in asset_list:
            asset_path = asset.get("path", "")
            metadata = asset.get("metadata", {})
            file_ext = Path(asset_path).suffix.lower()

            if file_ext in agent.texture_formats["input"]:
                analysis_results["textures"]["count"] += 1
                texture_analysis = _analyze_texture(asset_path, metadata)
                if texture_analysis["needs_conversion"]:
                    analysis_results["textures"]["conversions_needed"].append(texture_analysis)
                if texture_analysis["issues"]:
                    analysis_results["textures"]["issues"].extend(texture_analysis["issues"])

            elif file_ext in agent.model_formats["input"]:
                analysis_results["models"]["count"] += 1
                model_analysis = _analyze_model(asset_path, metadata)
                if model_analysis["needs_conversion"]:
                    analysis_results["models"]["conversions_needed"].append(model_analysis)
                if model_analysis["issues"]:
                    analysis_results["models"]["issues"].extend(model_analysis["issues"])

            elif file_ext in agent.audio_formats["input"]:
                analysis_results["audio"]["count"] += 1
                audio_analysis = _analyze_audio(asset_path, metadata)
                if audio_analysis["needs_conversion"]:
                    analysis_results["audio"]["conversions_needed"].append(audio_analysis)
                if audio_analysis["issues"]:
                    analysis_results["audio"]["issues"].extend(audio_analysis["issues"])

            else:
                analysis_results["other"]["count"] += 1
                analysis_results["other"]["files"].append(asset_path)
                if file_ext not in [".txt", ".md", ".json"]:
                    analysis_results["other"]["issues"].append(f"Unknown asset type: {asset_path}")

        recommendations = []
        texture_count = analysis_results["textures"]["count"]
        model_count = analysis_results["models"]["count"]
        audio_count = analysis_results["audio"]["count"]

        if texture_count > 0:
            recommendations.append(
                f"Convert {texture_count} textures to PNG format with power-of-2 dimensions"
            )
        if model_count > 0:
            recommendations.append(f"Convert {model_count} models to Bedrock geometry format")
        if audio_count > 0:
            recommendations.append(f"Convert {audio_count} audio files to OGG format")

        total_issues = (
            len(analysis_results["textures"]["issues"])
            + len(analysis_results["models"]["issues"])
            + len(analysis_results["audio"]["issues"])
        )
        if total_issues > 0:
            recommendations.append(f"Address {total_issues} compatibility issues")

        response = {
            "success": True,
            "analysis_results": analysis_results,
            "recommendations": recommendations,
            "total_assets": len(asset_list),
            "conversion_complexity": _assess_conversion_complexity(analysis_results),
        }

        logger.info(f"Analyzed {len(asset_list)} assets")
        return json.dumps(response, indent=2)

    except Exception as e:
        logger.error(f"Unhandled error in analyze_assets: {e}", exc_info=True)
        return json.dumps(
            {"success": False, "error": f"Failed to analyze assets: {str(e)}"}, indent=2
        )


@staticmethod
def convert_textures_tool(texture_list: str) -> str:
    """Convert textures to Bedrock format."""
    from agents.asset_converter.base import AssetConverterAgent

    agent = AssetConverterAgent.get_instance()
    return agent.convert_textures(texture_list, "")


@staticmethod
def convert_models_tool(model_list: str) -> str:
    """Convert models to Bedrock format."""
    from agents.asset_converter.base import AssetConverterAgent

    agent = AssetConverterAgent.get_instance()
    return (
        agent.convert_models_tool(model_list)
        if hasattr(agent, "convert_models_tool")
        else str({"success": False, "error": "Model conversion not available"})
    )


@staticmethod
def convert_audio_tool(audio_list: str) -> str:
    """Convert audio files to Bedrock format."""
    from agents.asset_converter.base import AssetConverterAgent

    agent = AssetConverterAgent.get_instance()
    return (
        agent.convert_audio_tool(audio_list)
        if hasattr(agent, "convert_audio_tool")
        else str({"success": False, "error": "Audio conversion not available"})
    )


@staticmethod
def validate_bedrock_assets_tool(asset_paths: str) -> str:
    """Validate that assets meet Bedrock requirements."""
    from agents.asset_converter.base import AssetConverterAgent

    agent = AssetConverterAgent.get_instance()
    try:
        import json

        data = json.loads(asset_paths)
        paths = data if isinstance(data, list) else data.get("paths", [])
        results = []
        for path in paths:
            validation = agent.validate_texture(path) if path.endswith(".png") else {"valid": True}
            results.append({"path": path, "validation": validation})
        return json.dumps({"success": True, "results": results}, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@staticmethod
def extract_jar_textures_tool(jar_path: str, output_dir: str) -> str:
    """Extract textures from a Java mod JAR file."""
    from agents.asset_converter.base import AssetConverterAgent

    agent = AssetConverterAgent.get_instance()
    return json.dumps(agent.extract_textures_from_jar(jar_path, output_dir))


@staticmethod
def convert_java_texture_path_tool(java_path: str, bedrock_type: str = "blocks") -> str:
    """Convert a Java texture path to Bedrock format."""
    from agents.asset_converter.base import AssetConverterAgent

    agent = AssetConverterAgent.get_instance()
    return json.dumps(
        {"success": True, "bedrock_path": agent.convert_java_texture_path(java_path, bedrock_type)}
    )


@staticmethod
def validate_texture_tool(texture_path: str) -> str:
    """Validate a single texture for Bedrock compatibility."""
    from agents.asset_converter.base import AssetConverterAgent

    agent = AssetConverterAgent.get_instance()
    return json.dumps(agent.validate_texture(texture_path))


@staticmethod
def generate_fallback_texture_tool(output_path: str, usage: str = "block") -> str:
    """Generate a fallback texture for missing assets."""
    from agents.asset_converter.base import AssetConverterAgent

    agent = AssetConverterAgent.get_instance()
    return json.dumps(agent._generate_fallback_texture(usage))
