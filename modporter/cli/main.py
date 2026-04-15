#!/usr/bin/env python3
"""
ModPorter AI CLI - Command-line interface for converting Java mods to Bedrock
"""

import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any


def add_ai_engine_to_path():
    """Setup sys.path to import ai-engine modules (addresses review comment)."""
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent
    ai_engine_path = project_root / "ai-engine"

    if str(ai_engine_path) not in sys.path:
        sys.path.insert(0, str(ai_engine_path))

    return ai_engine_path


# Setup imports
add_ai_engine_to_path()

from agents.java_analyzer import JavaAnalyzerAgent
from agents.bedrock_builder import BedrockBuilderAgent
from agents.packaging_agent import PackagingAgent
from agents.entity_converter import EntityConverter
from agents.block_item_generator import BlockItemGenerator
from .fix_ci import CIFixer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def convert_mod(jar_path: str, output_dir: str = None) -> Dict[str, Any]:  # noqa: C901
    """
    Convert a Java mod JAR to Bedrock .mcaddon format.

    Supports both block and entity mods. The pipeline:
    1. Runs block-only MVP analysis (analyze_jar_for_mvp)
    2. Runs full AST analysis (analyze_jar_with_ast) to detect entities
    3. Builds block add-on if blocks found
    4. Converts entities via EntityConverter if entities found
    5. Packages everything into .mcaddon

    Args:
        jar_path: Path to the Java mod JAR file
        output_dir: Optional output directory (defaults to same directory as JAR)

    Returns:
        Dict with conversion results
    """
    try:
        # Validate input
        jar_file = Path(jar_path)
        if not jar_file.exists():
            raise FileNotFoundError(f"JAR file not found: {jar_path}")

        if not jar_file.suffix.lower() == ".jar":
            raise ValueError(f"File must be a .jar file: {jar_path}")

        # Set output directory
        if output_dir is None:
            output_dir = jar_file.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Converting {jar_file.name} to Bedrock add-on...")

        java_analyzer = JavaAnalyzerAgent()

        ast_analysis_result = java_analyzer.analyze_jar_with_ast(str(jar_file))

        if not ast_analysis_result.get("success", False):
            logger.warning("AST analysis failed, falling back to MVP analysis...")
            analysis_result = java_analyzer.analyze_jar_for_mvp(str(jar_file))
            if not analysis_result.get("success", False):
                raise RuntimeError(
                    f"Analysis failed: {analysis_result.get('error', 'Unknown error')}"
                )
            registry_name = analysis_result.get("registry_name", "unknown_block")
            texture_path = analysis_result.get("texture_path")
            entities = []
            blocks = []
            features = {}
            entity_textures = []
            entity_models = []
            assets = {}
        else:
            features = ast_analysis_result.get("features", {})
            entities = features.get("entities", [])
            blocks = features.get("blocks", [])
            mod_info = ast_analysis_result.get("mod_info", {})
            mod_id = mod_info.get("name", "unknown")

            logger.info(f"AST analysis found: {len(blocks)} blocks, {len(entities)} entities")

            if blocks:
                block_registry_name = blocks[0].get("registry_name", "unknown:block")
                if ":" not in block_registry_name or block_registry_name.startswith("unknown:"):
                    registry_name = f"{mod_id}:{block_registry_name}"
                else:
                    registry_name = block_registry_name
            else:
                registry_name = "unknown:block"

            assets = ast_analysis_result.get("assets", {})
            texture_path = None
            if "block_textures" in assets and assets["block_textures"]:
                texture_path = assets["block_textures"][0]

            entity_textures = [t for t in assets.get("textures", []) if "/textures/entity/" in t]
            entity_models = [
                m for m in assets.get("models", []) if "/models/entity/" in m or "/entity/" in m
            ]

        has_blocks = len(blocks) > 0 or registry_name != "unknown_block"
        has_entities = len(entities) > 0

        if not has_blocks and not has_entities:
            raise RuntimeError(
                "Analysis found no blocks or entities to convert. "
                "The mod may use unsupported features."
            )

        logger.info(f"Primary entity: {registry_name}")
        if texture_path:
            logger.info(f"Found texture: {texture_path}")

        # Step 2: Build Bedrock add-on with entity support
        logger.info("Step 2: Building Bedrock add-on...")

        with tempfile.TemporaryDirectory() as temp_dir:
            bedrock_builder = BedrockBuilderAgent()

            # Build block add-on if blocks were found
            if not has_blocks:
                bp_path = Path(temp_dir) / "behavior_pack"
                rp_path = Path(temp_dir) / "resource_pack"
                bp_path.mkdir(parents=True, exist_ok=True)
                rp_path.mkdir(parents=True, exist_ok=True)
                bedrock_builder.build_entity_addon_mvp(
                    entities=entities,
                    jar_path=str(jar_file),
                    output_dir=temp_dir,
                )
            elif registry_name != "unknown_block":
                build_result = bedrock_builder.build_block_addon_mvp(
                    registry_name=registry_name,
                    texture_path=texture_path,
                    jar_path=str(jar_file),
                    output_dir=temp_dir,
                )

            if has_entities:
                logger.info(f"Step 2b: Converting {len(entities)} entities...")
                entity_converter = EntityConverter()

                for entity in entities:
                    entity_name = entity.get("name", "").lower()
                    entity["textures"] = [t for t in entity_textures if entity_name in t.lower()]
                    entity["models"] = [m for m in entity_models if entity_name in m.lower()]

                bedrock_entities = entity_converter.convert_entities(entities)

                if bedrock_entities:
                    bp_path = Path(temp_dir) / "behavior_pack"
                    rp_path = Path(temp_dir) / "resource_pack"
                    bp_path.mkdir(parents=True, exist_ok=True)
                    rp_path.mkdir(parents=True, exist_ok=True)

                    written = entity_converter.write_entities_to_disk(
                        bedrock_entities, bp_path, rp_path
                    )
                    logger.info(
                        f"Wrote {len(written.get('entities', []))} entity definitions, "
                        f"{len(written.get('behaviors', []))} behaviors, "
                        f"{len(written.get('animations', []))} animations"
                    )

                    _extract_entity_assets(
                        jar_path=str(jar_file),
                        entity_textures=entity_textures,
                        entity_models=entity_models,
                        rp_path=rp_path,
                    )

            # Step 2c: Extract and convert block/item models from JAR
            block_models = [
                m for m in assets.get("models", []) if "/models/block/" in m or "/models/item/" in m
            ]
            if block_models:
                logger.info(f"Step 2c: Converting {len(block_models)} block/item models...")
                _extract_and_convert_models(
                    jar_path=str(jar_file),
                    model_paths=block_models,
                    entity_type="block",
                    bp_path=Path(temp_dir) / "behavior_pack",
                    rp_path=Path(temp_dir) / "resource_pack",
                )

            # Step 2d: Extract and convert recipes from JAR data pack
            java_recipes = _extract_recipes_from_jar(str(jar_file))
            if java_recipes:
                logger.info(f"Step 2d: Generating {len(java_recipes)} Bedrock recipes...")
                block_item_gen = BlockItemGenerator()
                bedrock_recipes = block_item_gen.generate_recipes(java_recipes)
                if bedrock_recipes:
                    import json

                    recipes_bp_path = Path(temp_dir) / "behavior_pack" / "recipes"
                    recipes_bp_path.mkdir(parents=True, exist_ok=True)
                    for recipe_id, recipe_data in bedrock_recipes.items():
                        recipe_file = recipes_bp_path / f"{recipe_id}.json"
                        recipe_file.write_text(json.dumps(recipe_data, indent=2))
                    logger.info(f"Wrote {len(bedrock_recipes)} recipe files")

            # Step 3: Package as .mcaddon
            logger.info("Step 3: Creating .mcaddon package...")
            packaging_agent = PackagingAgent()

            # Generate output filename
            mod_name = registry_name.replace(":", "_")  # Replace namespace separator
            if has_entities and not has_blocks:
                first_entity = entities[0]
                mod_name = first_entity.get(
                    "registry_name",
                    first_entity.get("name", "entity_mod").lower(),
                )
            output_path = output_dir / f"{mod_name}.mcaddon"

            package_result = packaging_agent.build_mcaddon_mvp(
                temp_dir=temp_dir, output_path=str(output_path), mod_name=mod_name
            )

            if not package_result.get("success", False):
                raise RuntimeError(
                    f"Packaging failed: {package_result.get('error', 'Unknown error')}"
                )

        # Success!
        result = {
            "success": True,
            "input_file": str(jar_file),
            "output_file": package_result["output_path"],
            "file_size": package_result["file_size"],
            "registry_name": registry_name,
            "entities_detected": len(entities),
            "blocks_detected": len(features.get("blocks", [])),
            "validation": package_result["validation"],
            "entities_converted": len(entities) if has_entities else 0,
        }

        logger.info("✅ Conversion complete!")
        logger.info(f"📦 Output: {result['output_file']}")
        logger.info(f"📏 Size: {result['file_size']:,} bytes")
        logger.info(
            f"🔍 Detected: {result['blocks_detected']} blocks, {result['entities_detected']} entities"
        )
        if has_entities:
            logger.info(f"🐾 Entities converted: {result['entities_converted']}")

        return result

    except Exception as e:
        logger.error(f"❌ Conversion failed: {e}")
        return {"success": False, "error": str(e)}


def _extract_and_convert_models(
    jar_path: str,
    model_paths: list,
    entity_type: str,
    bp_path: Path,
    rp_path: Path,
) -> None:
    """
    Extract models from JAR and convert them to Bedrock geo.json format.

    Args:
        jar_path: Path to the source JAR file
        model_paths: List of model paths to extract and convert
        entity_type: Type of model (block, item, etc.)
        bp_path: Behavior pack path
        rp_path: Resource pack path
    """
    import zipfile
    import json

    try:
        models_dir = rp_path / "models" / entity_type
        models_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(jar_path, "r") as jar:
            for model_path in model_paths:
                try:
                    model_data = jar.read(model_path)
                    java_model = json.loads(model_data.decode("utf-8"))

                    bedrock_geo = _convert_java_model_to_bedrock(
                        java_model, entity_type, Path(model_path).stem
                    )
                    output_file = models_dir / (Path(model_path).stem + ".geo.json")
                    output_file.write_text(json.dumps(bedrock_geo, indent=2))
                    logger.info(f"Converted model: {output_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to convert model {model_path}: {e}")

    except Exception as e:
        logger.warning(f"Model extraction failed: {e}")


def _convert_java_model_to_bedrock(java_model: dict, entity_type: str, model_stem: str) -> dict:
    """
    Convert a Java JSON model to Bedrock geo.json format.

    Args:
        java_model: Parsed Java model JSON
        entity_type: Type of entity (block, item)
        model_stem: Stem of the model filename

    Returns:
        Bedrock geo.json structure
    """
    bedrock_identifier = f"geometry.{entity_type}.{model_stem}"
    java_parent = java_model.get("parent")
    java_elements = java_model.get("elements", [])

    bones = []
    model_min_x, model_min_y, model_min_z = float("inf"), float("inf"), float("inf")
    model_max_x, model_max_y, model_max_z = float("-inf"), float("-inf"), float("-inf")

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

        from_coords = element.get("from", [0.0, 0.0, 0.0])
        to_coords = element.get("to", [16.0, 16.0, 16.0])
        cube_origin = [from_coords[0] - 8.0, from_coords[1] - 8.0, from_coords[2] - 8.0]
        cube_size = [
            to_coords[0] - from_coords[0],
            to_coords[1] - from_coords[1],
            to_coords[2] - from_coords[2],
        ]

        model_min_x = min(model_min_x, cube_origin[0])
        model_min_y = min(model_min_y, cube_origin[1])
        model_min_z = min(model_min_z, cube_origin[2])
        model_max_x = max(model_max_x, cube_origin[0] + cube_size[0])
        model_max_y = max(model_max_y, cube_origin[1] + cube_size[1])
        model_max_z = max(model_max_z, cube_origin[2] + cube_size[2])

        cube_uv = [0, 0]
        element_faces = element.get("faces")
        if element_faces:
            face_data = next(iter(element_faces.values()), None)
            if face_data and "uv" in face_data:
                cube_uv = [face_data["uv"][0], face_data["uv"][1]]

        bones.append(
            {
                "name": bone_name,
                "pivot": bone_pivot,
                "rotation": bone_rotation,
                "cubes": [{"origin": cube_origin, "size": cube_size, "uv": cube_uv}],
            }
        )

    if java_elements:
        v_bounds_w = model_max_x - model_min_x
        v_bounds_h = model_max_y - model_min_y
        v_bounds_d = model_max_z - model_min_z
        visible_bounds_width = round(max(v_bounds_w, v_bounds_d), 4)
        visible_bounds_height = round(v_bounds_h, 4)
        visible_bounds_offset = [
            round(model_min_x + v_bounds_w / 2.0, 4),
            round(model_min_y + v_bounds_h / 2.0, 4),
            round(model_min_z + v_bounds_d / 2.0, 4),
        ]
    else:
        visible_bounds_width = 0.1
        visible_bounds_height = 0.1
        visible_bounds_offset = [0, 0.0625, 0]

    return {
        "format_version": "1.12.0",
        "minecraft:geometry": [
            {
                "description": {
                    "identifier": bedrock_identifier,
                    "texture_width": 16,
                    "texture_height": 16,
                    "visible_bounds_width": visible_bounds_width,
                    "visible_bounds_height": visible_bounds_height,
                    "visible_bounds_offset": visible_bounds_offset,
                },
                "bones": bones,
            }
        ],
    }


def _extract_recipes_from_jar(jar_path: str) -> list:
    """
    Extract recipes from JAR's data pack directory.

    Args:
        jar_path: Path to the source JAR file

    Returns:
        List of recipe dictionaries
    """
    import zipfile
    import json

    recipes = []
    recipe_types_found = {}
    try:
        with zipfile.ZipFile(jar_path, "r") as jar:
            for file_name in jar.namelist():
                # Skip advancement files - they are not actual recipes
                # Advancement files are in data/<mod>/advancement/recipes/
                # Actual recipes are in data/<mod>/recipe/ (singular) or data/<mod>/recipes/ (plural)
                if "/advancement/" in file_name:
                    continue

                if file_name.startswith("data/") and file_name.endswith(".json"):
                    # Match both /recipe/ (NeoForge 1.21+ singular) and /recipes/ (vanilla plural)
                    if "/recipe/" in file_name or "/recipes/" in file_name:
                        try:
                            recipe_data = json.loads(jar.read(file_name).decode("utf-8"))
                            recipe_id = file_name.split("/")[-1].replace(".json", "")

                            # Track recipe types for debugging
                            recipe_type = recipe_data.get("type", "MISSING_TYPE")
                            recipe_types_found.setdefault(recipe_type, []).append(recipe_id)

                            if recipe_type == "MISSING_TYPE":
                                logger.warning(
                                    f"Recipe {recipe_id} in {file_name} has no 'type' field. Keys: {list(recipe_data.keys())}"
                                )

                            recipe_data["id"] = recipe_id
                            recipes.append(recipe_data)
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.debug(f"Skipping recipe file {file_name}: {e}")
                            continue
    except Exception as e:
        logger.warning(f"Recipe extraction failed: {e}")

    if recipes:
        logger.info(
            f"Extracted {len(recipes)} recipes from JAR. Types found: {list(recipe_types_found.keys())}"
        )
        for rt, ids in recipe_types_found.items():
            logger.debug(f"  Type '{rt}': {len(ids)} recipes, e.g., {ids[:3]}")

    return recipes


def _extract_entity_assets(
    jar_path: str,
    entity_textures: list,
    entity_models: list,
    rp_path: Path,
) -> None:
    """
    Extract entity textures and models from the source JAR into the resource pack.

    Args:
        jar_path: Path to the source JAR file
        entity_textures: List of texture paths found in the JAR
        entity_models: List of model paths found in the JAR
        rp_path: Resource pack output directory
    """
    import zipfile

    try:
        with zipfile.ZipFile(jar_path, "r") as jar:
            # Extract entity textures
            textures_dir = rp_path / "textures" / "entity"
            textures_dir.mkdir(parents=True, exist_ok=True)

            for tex_path in entity_textures:
                try:
                    tex_data = jar.read(tex_path)
                    tex_filename = Path(tex_path).name
                    output_tex = textures_dir / tex_filename
                    output_tex.write_bytes(tex_data)
                    logger.info(f"Extracted entity texture: {tex_filename}")
                except KeyError:
                    logger.warning(f"Texture not found in JAR: {tex_path}")

            # Extract entity models
            models_dir = rp_path / "models" / "entity"
            models_dir.mkdir(parents=True, exist_ok=True)

            for model_path in entity_models:
                try:
                    model_data = jar.read(model_path)
                    model_filename = Path(model_path).name
                    output_model = models_dir / model_filename
                    output_model.write_bytes(model_data)
                    logger.info(f"Extracted entity model: {model_filename}")
                except KeyError:
                    logger.warning(f"Model not found in JAR: {model_path}")

    except Exception as e:
        logger.warning(f"Failed to extract entity assets: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ModPorter AI - Convert Java Minecraft mods to Bedrock add-ons",
        prog="python -m modporter.cli",
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Convert command (default)
    convert_parser = subparsers.add_parser("convert", help="Convert a Java mod to Bedrock add-on")
    convert_parser.add_argument("jar_file", help="Path to the Java mod JAR file to convert")
    convert_parser.add_argument(
        "-o",
        "--output",
        help="Output directory (defaults to same directory as JAR file)",
        default=None,
    )

    # Fix CI command
    fix_ci_parser = subparsers.add_parser("fix-ci", help="Fix failing CI checks for current PR")
    fix_ci_parser.add_argument(
        "--repo-path", default=".", help="Path to the repository (default: current directory)"
    )

    # Global arguments
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    parser.add_argument("--version", action="version", version="ModPorter AI v0.1.0 (MVP)")

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle commands
    if args.command == "convert" or args.command is None:
        # Default to convert if no command specified
        jar_file = getattr(args, "jar_file", None)
        if not jar_file:
            parser.error("jar_file is required for convert command")

        result = convert_mod(jar_file, getattr(args, "output", None))

        # Exit with appropriate code
        if result["success"]:
            sys.exit(0)
        else:
            sys.exit(1)

    elif args.command == "fix-ci":
        fixer = CIFixer(getattr(args, "repo_path", "."))
        success = fixer.fix_failing_ci()

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    else:
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
