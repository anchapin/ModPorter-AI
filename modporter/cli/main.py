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
from agents.entity_converter import EntityConverter
from agents.packaging_agent import PackagingAgent
from .fix_ci import CIFixer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def convert_mod(jar_path: str, output_dir: str = None) -> Dict[str, Any]:
    """
    Convert a Java mod JAR to Bedrock .mcaddon format.

    Supports block mods, entity mods, and mixed mods containing both.

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

        # Step 1: Run full AST analysis to detect all feature types
        logger.info("Step 1: Analyzing Java mod (full analysis)...")
        java_analyzer = JavaAnalyzerAgent()
        full_analysis = java_analyzer.analyze_jar_with_ast(str(jar_file))

        if not full_analysis.get("success", False):
            raise RuntimeError(f"Analysis failed: {full_analysis.get('errors', ['Unknown error'])}")

        features = full_analysis.get("features", {})
        mod_info = full_analysis.get("mod_info", {})
        mod_name = mod_info.get("name", "unknown_mod")

        has_blocks = bool(features.get("blocks"))
        has_entities = bool(features.get("entities"))

        if not has_blocks and not has_entities:
            # Fallback to MVP block analysis for backward compatibility
            logger.info("No blocks or entities detected via AST, falling back to MVP block analysis...")
            mvp_result = java_analyzer.analyze_jar_for_mvp(str(jar_file))
            if mvp_result.get("success", False):
                has_blocks = True
                features["_mvp_block"] = mvp_result
            else:
                raise RuntimeError(
                    "Could not detect any convertible features (blocks or entities) in the mod."
                )

        logger.info(
            f"Detected features — blocks: {len(features.get('blocks', []))}, "
            f"entities: {len(features.get('entities', []))}"
        )

        # Step 2: Build Bedrock add-on
        logger.info("Step 2: Building Bedrock add-on...")

        with tempfile.TemporaryDirectory() as temp_dir:
            bedrock_builder = BedrockBuilderAgent()
            build_success = False
            registry_name = mod_name

            # --- Handle blocks ---
            if has_blocks:
                if "_mvp_block" in features:
                    # Use MVP path for fallback block conversion
                    mvp = features["_mvp_block"]
                    registry_name = mvp.get("registry_name", "unknown_block")
                    texture_path = mvp.get("texture_path")
                else:
                    # Use first detected block from AST analysis
                    block = features["blocks"][0]
                    block_name = block.get("registry_name", block.get("name", "unknown_block"))
                    registry_name = f"{mod_name}:{block_name}"
                    # Find block texture from assets
                    texture_path = None
                    for tex in full_analysis.get("assets", {}).get("textures", []):
                        if "/textures/block/" in tex:
                            texture_path = tex
                            break

                logger.info(f"Building block: {registry_name}")
                build_result = bedrock_builder.build_block_addon_mvp(
                    registry_name=registry_name,
                    texture_path=texture_path,
                    jar_path=str(jar_file),
                    output_dir=temp_dir,
                )

                if not build_result.get("success", False):
                    raise RuntimeError(
                        f"Block build failed: {build_result.get('errors', ['Unknown error'])}"
                    )
                build_success = True

            # --- Handle entities ---
            if has_entities:
                logger.info(f"Converting {len(features['entities'])} entities...")
                entity_converter = EntityConverter()

                # Enrich entity data with namespace from mod_info
                enriched_entities = []
                for entity in features["entities"]:
                    enriched = dict(entity)
                    if "namespace" not in enriched:
                        enriched["namespace"] = mod_name
                    if "id" not in enriched:
                        enriched["id"] = enriched.get(
                            "registry_name", enriched.get("name", "unknown_entity")
                        )

                    # Classify entity type from Java superclass/methods
                    methods = enriched.get("methods", [])
                    method_str = " ".join(methods).lower()
                    if any(
                        kw in method_str
                        for kw in ["attack", "melee", "ranged", "target", "explode"]
                    ):
                        enriched["category"] = "hostile"
                    else:
                        enriched["category"] = "passive"

                    enriched_entities.append(enriched)

                # Convert entities to Bedrock format
                bedrock_entities = entity_converter.convert_entities(enriched_entities)

                if bedrock_entities:
                    # Ensure pack directories exist
                    bp_path = Path(temp_dir) / "behavior_pack"
                    rp_path = Path(temp_dir) / "resource_pack"
                    bp_path.mkdir(parents=True, exist_ok=True)
                    rp_path.mkdir(parents=True, exist_ok=True)

                    # If no block was built, we need manifests for entity-only mods
                    if not has_blocks:
                        import uuid as _uuid
                        import os

                        if os.getenv("TESTING") or os.getenv("PYTEST_CURRENT_TEST"):
                            bp_uuid = "12345678-1234-1234-1234-123456789abc"
                            rp_uuid = "87654321-4321-4321-4321-abcdef123456"
                            bp_mod_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
                            rp_mod_uuid = "ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj"
                        else:
                            bp_uuid = str(_uuid.uuid4())
                            rp_uuid = str(_uuid.uuid4())
                            bp_mod_uuid = str(_uuid.uuid4())
                            rp_mod_uuid = str(_uuid.uuid4())

                        entity_name = enriched_entities[0].get("id", mod_name)
                        display_name = entity_name.replace("_", " ").title()

                        bp_manifest = {
                            "format_version": 2,
                            "header": {
                                "name": f"ModPorter {display_name}",
                                "description": f"Behavior pack for {display_name} entity",
                                "uuid": bp_uuid,
                                "version": [1, 0, 0],
                                "min_engine_version": [1, 19, 0],
                            },
                            "modules": [
                                {
                                    "type": "data",
                                    "uuid": bp_mod_uuid,
                                    "version": [1, 0, 0],
                                }
                            ],
                        }
                        rp_manifest = {
                            "format_version": 2,
                            "header": {
                                "name": f"ModPorter {display_name} Resources",
                                "description": f"Resource pack for {display_name} entity",
                                "uuid": rp_uuid,
                                "version": [1, 0, 0],
                                "min_engine_version": [1, 19, 0],
                            },
                            "modules": [
                                {
                                    "type": "resources",
                                    "uuid": rp_mod_uuid,
                                    "version": [1, 0, 0],
                                }
                            ],
                        }

                        import json

                        (bp_path / "manifest.json").write_text(
                            json.dumps(bp_manifest, indent=2)
                        )
                        (rp_path / "manifest.json").write_text(
                            json.dumps(rp_manifest, indent=2)
                        )

                    # Write entity definitions to disk
                    entity_converter.write_entities_to_disk(
                        bedrock_entities, bp_path, rp_path
                    )

                    # Copy entity textures from JAR
                    _copy_entity_assets(
                        jar_path=str(jar_file),
                        assets=full_analysis.get("assets", {}),
                        rp_path=rp_path,
                    )

                    registry_name = f"{mod_name}:{enriched_entities[0].get('id', 'entity')}"
                    build_success = True
                    logger.info(f"Entity conversion complete: {len(bedrock_entities)} definitions written")

            if not build_success:
                raise RuntimeError("No features were successfully converted.")

            # Step 3: Package as .mcaddon
            logger.info("Step 3: Creating .mcaddon package...")
            packaging_agent = PackagingAgent()

            safe_name = registry_name.replace(":", "_")
            output_path = output_dir / f"{safe_name}.mcaddon"

            package_result = packaging_agent.build_mcaddon_mvp(
                temp_dir=temp_dir, output_path=str(output_path), mod_name=safe_name
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
            "validation": package_result["validation"],
            "converted_features": {
                "blocks": len(features.get("blocks", [])),
                "entities": len(features.get("entities", [])),
            },
        }

        logger.info("✅ Conversion complete!")
        logger.info(f"📦 Output: {result['output_file']}")
        logger.info(f"📏 Size: {result['file_size']:,} bytes")

        return result

    except Exception as e:
        logger.error(f"❌ Conversion failed: {e}")
        return {"success": False, "error": str(e)}



def _copy_entity_assets(jar_path: str, assets: Dict[str, Any], rp_path: Path) -> None:
    """Copy entity textures and models from JAR to resource pack."""
    import zipfile

    textures = assets.get("textures", [])
    models = assets.get("models", [])

    with zipfile.ZipFile(jar_path, "r") as jar:
        # Copy entity textures
        for tex_path in textures:
            if "/textures/entity/" in tex_path or "/textures/" in tex_path:
                try:
                    tex_data = jar.read(tex_path)
                    # Map to Bedrock resource pack structure
                    tex_filename = Path(tex_path).name
                    dest_dir = rp_path / "textures" / "entity"
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_file = dest_dir / tex_filename
                    dest_file.write_bytes(tex_data)
                    logger.info(f"Copied entity texture: {tex_path} -> {dest_file}")
                except Exception as e:
                    logger.warning(f"Failed to copy texture {tex_path}: {e}")

        # Copy entity models
        for model_path in models:
            if "/models/entity/" in model_path or "/models/" in model_path:
                try:
                    model_data = jar.read(model_path)
                    model_filename = Path(model_path).name
                    dest_dir = rp_path / "models" / "entity"
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_file = dest_dir / model_filename
                    dest_file.write_bytes(model_data)
                    logger.info(f"Copied entity model: {model_path} -> {dest_file}")
                except Exception as e:
                    logger.warning(f"Failed to copy model {model_path}: {e}")



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
