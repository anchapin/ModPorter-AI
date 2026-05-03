"""
Core texture conversion module.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

from PIL import Image

logger = logging.getLogger(__name__)


def _convert_single_texture(
    self, texture_path: str, metadata: Dict, usage: str, output_dir: Path = None
) -> Dict:
    """
    Convert a single texture file to Bedrock format with enhanced validation and optimization.
    If output_dir is provided, saves the converted texture to disk.
    """
    cache_key = f"{texture_path}_{usage}_{hash(str(metadata))}"

    if cache_key in agent._conversion_cache:
        logger.debug(f"Using cached result for texture conversion: {texture_path}")
        return agent._conversion_cache[cache_key]

    try:
        if not Path(texture_path).exists():
            logger.warning(f"Texture file not found: {texture_path}. Generating fallback texture.")
            img = agent._generate_fallback_texture(usage)
            original_dimensions = img.size
            is_valid_png = False
            optimizations_applied = ["Generated fallback texture"]
        else:
            try:
                img = Image.open(texture_path)
                original_dimensions = img.size

                is_valid_png = img.format == "PNG"

                img = img.convert("RGBA")
                optimizations_applied = ["Converted to RGBA"] if not is_valid_png else []
            except Exception as open_error:
                logger.warning(
                    f"Failed to open texture {texture_path}: {open_error}. Generating fallback texture."
                )
                img = agent._generate_fallback_texture(usage)
                original_dimensions = img.size
                is_valid_png = False
                optimizations_applied = ["Generated fallback texture due to open error"]

        width, height = img.size
        resized = False

        max_res = agent.texture_constraints.get("max_resolution", 1024)
        must_be_power_of_2 = agent.texture_constraints.get("must_be_power_of_2", True)

        new_width, new_height = width, height

        needs_pot_resize = must_be_power_of_2 and (
            not agent._is_power_of_2(width) or not agent._is_power_of_2(height)
        )

        if needs_pot_resize:
            new_width = agent._next_power_of_2(width)
            new_height = agent._next_power_of_2(height)
            resized = True

        if new_width > max_res or new_height > max_res:
            new_width = min(new_width, max_res)
            new_height = min(new_height, max_res)
            resized = True

        if resized and must_be_power_of_2:
            if not agent._is_power_of_2(new_width):
                new_width = agent._previous_power_of_2(new_width)
            if not agent._is_power_of_2(new_height):
                new_height = agent._previous_power_of_2(new_height)

        if resized and (new_width != width or new_height != height):
            img = img.resize((new_width, new_height), Image.LANCZOS)
            optimizations_applied.append(
                f"Resized from {original_dimensions} to {(new_width, new_height)}"
            )
        else:
            new_width, new_height = img.size
            resized = False

        if not is_valid_png or resized:
            optimizations_applied.append("Optimized PNG format")

        animation_data = None
        mcmeta_path = Path(str(texture_path) + ".mcmeta")
        if mcmeta_path.exists():
            try:
                with open(mcmeta_path, "r") as f:
                    mcmeta_content = json.load(f)
                if "animation" in mcmeta_content:
                    animation_data = mcmeta_content["animation"]
                    optimizations_applied.append("Parsed .mcmeta animation data")
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("Could not parse .mcmeta file for {}: {}".format(texture_path, e))

        base_name = Path(texture_path).stem if Path(texture_path).exists() else "fallback_texture"
        texture_path_obj = (
            Path(texture_path) if Path(texture_path).exists() else Path(f"fallback_{usage}.png")
        )

        if usage == "block" and "block" not in str(texture_path_obj).lower():
            if any(
                block_indicator in str(texture_path_obj).lower()
                for block_indicator in [
                    "block/",
                    "blocks/",
                    "/block/",
                    "/blocks/",
                    "_block",
                    "-block",
                ]
            ):
                usage = "block"
            elif any(
                item_indicator in str(texture_path_obj).lower()
                for item_indicator in ["item/", "items/", "/item/", "/items/", "_item", "-item"]
            ):
                usage = "item"
            elif any(
                entity_indicator in str(texture_path_obj).lower()
                for entity_indicator in [
                    "entity/",
                    "entities/",
                    "/entity/",
                    "/entities/",
                    "_entity",
                    "-entity",
                ]
            ):
                usage = "entity"
            elif "particle" in str(texture_path_obj).lower():
                usage = "particle"
            elif any(
                gui_indicator in str(texture_path_obj).lower()
                for gui_indicator in ["gui/", "ui/", "interface/", "menu/"]
            ):
                usage = "ui"

        if usage == "block":
            converted_path = f"textures/blocks/{base_name}.png"
        elif usage == "item":
            converted_path = f"textures/items/{base_name}.png"
        elif usage == "entity":
            converted_path = f"textures/entity/{base_name}.png"
        elif usage == "particle":
            converted_path = f"textures/particle/{base_name}.png"
        elif usage == "ui":
            converted_path = f"textures/ui/{base_name}.png"
        else:
            try:
                relative_path = texture_path_obj.relative_to(texture_path_obj.anchor).as_posix()
                for prefix in ["assets/minecraft/textures/", "textures/", "images/", "img/"]:
                    if relative_path.startswith(prefix):
                        relative_path = relative_path[len(prefix) :]
                        break
                if "." in relative_path:
                    relative_path = relative_path[: relative_path.rindex(".")]
                converted_path = f"textures/other/{relative_path}.png"
            except Exception:
                converted_path = f"textures/other/{base_name}.png"

        actual_output_path = None
        if output_dir is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            actual_output_path = output_dir / converted_path
            actual_output_path.parent.mkdir(parents=True, exist_ok=True)

            img.save(actual_output_path, "PNG", optimize=True)
            logger.info(f"Saved converted texture to {actual_output_path}")

        result = {
            "success": True,
            "original_path": str(texture_path),
            "converted_path": str(actual_output_path) if actual_output_path else converted_path,
            "relative_path": converted_path,
            "original_dimensions": original_dimensions,
            "converted_dimensions": (new_width, new_height),
            "format": "png",
            "resized": resized,
            "optimizations_applied": optimizations_applied,
            "bedrock_reference": f"{usage}_{base_name}",
            "animation_data": animation_data,
            "was_valid_png": is_valid_png,
            "was_fallback": not Path(texture_path).exists(),
        }

        agent._conversion_cache[cache_key] = result

        return result
    except Exception as e:
        logger.error(f"Texture conversion error for {texture_path}: {e}")
        error_result = {"success": False, "original_path": str(texture_path), "error": str(e)}
        agent._conversion_cache[cache_key] = error_result
        return error_result


def _generate_texture_pack_structure(agent, textures: List[Dict]) -> Dict:
    """Generate texture pack structure files with enhanced atlas handling"""
    manifest = {
        "format_version": 2,
        "header": {
            "name": "Converted Resource Pack",
            "description": "Assets converted from Java mod",
            "uuid": "f4aeb009-270e-4a11-8137-a916a1a3ea1e",
            "version": [1, 0, 0],
            "min_engine_version": [1, 16, 0],
        },
        "modules": [
            {
                "type": "resources",
                "uuid": "0d28590c-1797-4555-9a19-5ee98def104e",
                "version": [1, 0, 0],
            }
        ],
    }

    item_texture_data = {}
    terrain_texture_data = {}
    flipbook_entries = []

    texture_atlases = {}

    for t_data in textures:
        if not t_data.get("success"):
            continue

        bedrock_ref = t_data.get("bedrock_reference", Path(t_data["converted_path"]).stem)
        converted_path = t_data["converted_path"]
        texture_entry = {"textures": converted_path}

        base_name = Path(converted_path).stem
        if "_" in base_name:
            atlas_name = base_name.split("_")[0]
            if atlas_name not in texture_atlases:
                texture_atlases[atlas_name] = []
            texture_atlases[atlas_name].append({"reference": bedrock_ref, "path": converted_path})

        if bedrock_ref.startswith("item_") or "/items/" in converted_path:
            item_texture_data[bedrock_ref] = texture_entry
        elif bedrock_ref.startswith("block_") or "/blocks/" in converted_path:
            terrain_texture_data[bedrock_ref] = texture_entry
        elif bedrock_ref.startswith("entity_") or "/entity/" in converted_path:
            terrain_texture_data[bedrock_ref] = texture_entry
        else:
            terrain_texture_data[bedrock_ref] = texture_entry

        if t_data.get("animation_data"):
            anim_data = t_data["animation_data"]
            frames_list = anim_data.get("frames", [])

            if frames_list and all(isinstance(f, dict) for f in frames_list):
                try:
                    processed_frames = [
                        int(f["index"]) for f in frames_list if isinstance(f, dict) and "index" in f
                    ]
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
                "frames": processed_frames,
            }
            if "interpolate" in anim_data:
                entry["interpolate"] = anim_data["interpolate"]

            flipbook_entries.append(entry)

    result = {"pack_manifest.json": manifest}
    if item_texture_data:
        result["item_texture.json"] = {
            "resource_pack_name": "vanilla",
            "texture_data": item_texture_data,
        }
    if terrain_texture_data:
        result["terrain_texture.json"] = {
            "resource_pack_name": "vanilla",
            "texture_data": terrain_texture_data,
        }
    if flipbook_entries:
        result["flipbook_textures.json"] = flipbook_entries

    if texture_atlases:
        result["texture_atlases.json"] = texture_atlases

    return result


def convert_textures(agent, texture_list: str, output_path: str) -> str:
    """
    Convert textures to Bedrock-compatible format and save to disk.

    Args:
        texture_list: JSON string containing list of texture paths or structured data
        output_path: Output directory path

    Returns:
        JSON string with conversion results
    """
    try:
        if isinstance(texture_list, str):
            data = (
                json.loads(texture_list)
                if texture_list.startswith("[") or texture_list.startswith("{")
                else texture_list
            )
        else:
            data = texture_list

        if isinstance(data, list):
            textures = [{"path": path, "usage": "block"} for path in data]
        elif isinstance(data, dict):
            textures = data.get("textures", [])
        else:
            textures = [{"path": str(data), "usage": "block"}]

        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        result = {
            "converted_textures": [],
            "total_textures": len(textures),
            "successful_conversions": 0,
            "failed_conversions": 0,
            "errors": [],
        }

        for texture_data in textures:
            try:
                if isinstance(texture_data, str):
                    texture_path = texture_data
                    usage = "block"
                    metadata = {}
                else:
                    texture_path = texture_data.get("path", "")
                    usage = texture_data.get("usage", "block")
                    metadata = texture_data.get("metadata", {})

                conversion_result = agent._convert_single_texture(
                    texture_path, metadata, usage, output_path
                )

                if conversion_result.get("success"):
                    result["converted_textures"].append(
                        {
                            "original_path": texture_path,
                            "converted_path": conversion_result["converted_path"],
                            "relative_path": conversion_result["relative_path"],
                            "success": True,
                            "dimensions": conversion_result["converted_dimensions"],
                            "resized": conversion_result["resized"],
                            "optimizations": conversion_result["optimizations_applied"],
                        }
                    )
                    result["successful_conversions"] += 1
                else:
                    result["errors"].append(
                        f"Failed to convert {texture_path}: {conversion_result.get('error', 'Unknown error')}"
                    )
                    result["failed_conversions"] += 1
            except Exception as e:
                logger.error(f"Error converting texture {texture_data}: {e}")
                result["errors"].append(f"Failed to convert {texture_data}: {e}")
                result["failed_conversions"] += 1

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error converting textures: {e}")
        return json.dumps(
            {
                "converted_textures": [],
                "total_textures": 0,
                "successful_conversions": 0,
                "failed_conversions": 0,
                "errors": [str(e)],
            },
            indent=2,
        )


def convert_jar_textures_to_bedrock(
    self, jar_path: str, output_dir: str, namespace: str = None
) -> Dict:
    """
    Complete pipeline to extract textures from JAR and convert to Bedrock format.

    Args:
        jar_path: Path to the Java mod JAR file
        output_dir: Directory to save converted textures
        namespace: Optional namespace to filter textures

    Returns:
        Dict with conversion results
    """
    results = {
        "success": False,
        "extracted": [],
        "converted": [],
        "failed": [],
        "warnings": [],
        "errors": [],
    }

    try:
        extract_result = agent.extract_textures_from_jar(jar_path, output_dir, namespace)

        if not extract_result["success"]:
            results["errors"].append(
                f"Failed to extract textures: {extract_result.get('error', 'Unknown error')}"
            )
            return results

        results["extracted"] = extract_result["extracted_textures"]

        for texture_info in extract_result["extracted_textures"]:
            texture_path = texture_info["output_path"]

            try:
                validation = agent.validate_texture(texture_path)

                if not validation["valid"]:
                    results["failed"].append({"path": texture_path, "errors": validation["errors"]})
                    results["warnings"].extend(validation["warnings"])
                    continue

                conversion_result = agent._convert_single_texture(
                    texture_path,
                    {},
                    "block",
                    None,
                )

                if conversion_result.get("success"):
                    results["converted"].append(
                        {
                            "original": texture_info["original_path"],
                            "converted": texture_path,
                            "bedrock_path": texture_info["bedrock_path"],
                        }
                    )
                else:
                    fallback = agent._generate_fallback_texture("block")
                    fallback_path = Path(texture_path)
                    fallback.save(fallback_path, "PNG")

                    results["converted"].append(
                        {
                            "original": texture_info["original_path"],
                            "converted": texture_path,
                            "bedrock_path": texture_info["bedrock_path"],
                            "used_fallback": True,
                        }
                    )
                    results["warnings"].append(f"Used fallback texture for {texture_path}")

            except Exception as e:
                results["failed"].append({"path": texture_path, "errors": [str(e)]})

        results["success"] = len(results["converted"]) > 0

    except Exception as e:
        results["errors"].append(f"Conversion pipeline failed: {str(e)}")

    return results


def _get_recommended_resolution(agent, width: int, height: int) -> str:
    """Get recommended resolution for texture"""
    max_res = agent.texture_constraints["max_resolution"]

    target_width = min(max_res, agent._next_power_of_2(width))
    target_height = min(max_res, agent._next_power_of_2(height))

    return f"{target_width}x{target_height}"


def _generate_conversion_recommendations(agent, analysis: Dict) -> List[str]:
    """Generate conversion recommendations based on analysis"""
    recommendations = []

    texture_count = analysis["textures"]["count"]
    model_count = analysis["models"]["count"]
    audio_count = analysis["audio"]["count"]

    if texture_count > 0:
        recommendations.append(
            f"Convert {texture_count} textures to PNG format with power-of-2 dimensions"
        )

    if model_count > 0:
        recommendations.append(f"Convert {model_count} models to Bedrock geometry format")

    if audio_count > 0:
        recommendations.append(f"Convert {audio_count} audio files to OGG format")

    total_issues = (
        len(analysis["textures"]["issues"])
        + len(analysis["models"]["issues"])
        + len(analysis["audio"]["issues"])
    )

    if total_issues > 0:
        recommendations.append(f"Address {total_issues} compatibility issues")

    return recommendations


def _assess_conversion_complexity(agent, analysis: Dict) -> str:
    """Assess the complexity of the conversion task"""
    total_conversions = (
        len(analysis["textures"]["conversions_needed"])
        + len(analysis["models"]["conversions_needed"])
        + len(analysis["audio"]["conversions_needed"])
    )

    total_issues = (
        len(analysis["textures"]["issues"])
        + len(analysis["models"]["issues"])
        + len(analysis["audio"]["issues"])
    )

    if total_conversions == 0 and total_issues == 0:
        return "simple"
    elif total_conversions < 5 and total_issues < 3:
        return "moderate"
    else:
        return "complex"
