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
from .fix_ci import CIFixer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def convert_mod(jar_path: str, output_dir: str = None) -> Dict[str, Any]:
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

        # Step 1: Analyze the JAR file (block-only MVP analysis)
        logger.info("Step 1: Analyzing Java mod...")
        java_analyzer = JavaAnalyzerAgent()
        analysis_result = java_analyzer.analyze_jar_for_mvp(str(jar_file))

        if not analysis_result.get("success", False):
            raise RuntimeError(f"Analysis failed: {analysis_result.get('error', 'Unknown error')}")

        registry_name = analysis_result.get("registry_name", "unknown_block")
        texture_path = analysis_result.get("texture_path")

        # Step 1b: Run full AST analysis to detect entities and other features
        logger.info("Step 1b: Running full AST analysis for entity detection...")
        ast_result = java_analyzer.analyze_jar_with_ast(str(jar_file))
        entities_found = []
        entity_textures = []
        entity_models = []

        if ast_result.get("success", False):
            features = ast_result.get("features", {})
            entities_found = features.get("entities", [])
            assets = ast_result.get("assets", {})
            # Collect entity-related textures and models
            entity_textures = [
                t for t in assets.get("textures", []) if "/textures/entity/" in t
            ]
            entity_models = [
                m for m in assets.get("models", [])
                if "/models/entity/" in m or "/entity/" in m
            ]

            if entities_found:
                logger.info(
                    f"Found {len(entities_found)} entities: "
                    f"{[e.get('name', 'unknown') for e in entities_found]}"
                )
            else:
                logger.info("No entities detected in mod")

        has_blocks = registry_name != "unknown_block" or (
            ast_result.get("success", False)
            and ast_result.get("features", {}).get("blocks", [])
        )
        has_entities = len(entities_found) > 0

        if not has_blocks and not has_entities:
            raise RuntimeError(
                "Analysis found no blocks or entities to convert. "
                "The mod may use unsupported features."
            )

        logger.info(f"Found block: {registry_name}")
        if texture_path:
            logger.info(f"Found texture: {texture_path}")

        # Step 2: Build Bedrock add-on
        logger.info("Step 2: Building Bedrock add-on...")

        with tempfile.TemporaryDirectory() as temp_dir:
            bedrock_builder = BedrockBuilderAgent()

            # Build block add-on if blocks were found
            if has_blocks and registry_name != "unknown_block":
                build_result = bedrock_builder.build_block_addon_mvp(
                    registry_name=registry_name,
                    texture_path=texture_path,
                    jar_path=str(jar_file),
                    output_dir=temp_dir,
                )

                if not build_result.get("success", False):
                    raise RuntimeError(
                        f"Bedrock block build failed: "
                        f"{build_result.get('error', 'Unknown error')}"
                    )
            else:
                # Ensure pack directories exist even without blocks
                bp_path = Path(temp_dir) / "behavior_pack"
                rp_path = Path(temp_dir) / "resource_pack"
                bp_path.mkdir(parents=True, exist_ok=True)
                rp_path.mkdir(parents=True, exist_ok=True)

                # Create minimal manifests for entity-only mods
                bedrock_builder.build_entity_addon_mvp(
                    entities=entities_found,
                    jar_path=str(jar_file),
                    output_dir=temp_dir,
                )

            # Step 2b: Convert entities if found
            if has_entities:
                logger.info(f"Step 2b: Converting {len(entities_found)} entities...")
                entity_converter = EntityConverter()

                # Enrich entity data with texture/model info from AST analysis
                for entity in entities_found:
                    entity_name = entity.get("name", "").lower()
                    entity["textures"] = [
                        t for t in entity_textures if entity_name in t.lower()
                    ]
                    entity["models"] = [
                        m for m in entity_models if entity_name in m.lower()
                    ]

                # Convert entities to Bedrock format
                bedrock_entities = entity_converter.convert_entities(entities_found)

                if bedrock_entities:
                    # Write entity definitions to the pack directories
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

                    # Extract entity textures from JAR to resource pack
                    _extract_entity_assets(
                        jar_path=str(jar_file),
                        entity_textures=entity_textures,
                        entity_models=entity_models,
                        rp_path=rp_path,
                    )

            # Step 3: Package as .mcaddon
            logger.info("Step 3: Creating .mcaddon package...")
            packaging_agent = PackagingAgent()

            # Generate output filename
            mod_name = registry_name.replace(":", "_")  # Replace namespace separator
            if has_entities and not has_blocks:
                # For entity-only mods, use the first entity name
                first_entity = entities_found[0]
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
            "validation": package_result["validation"],
            "entities_converted": len(entities_found) if has_entities else 0,
        }

        logger.info("✅ Conversion complete!")
        logger.info(f"📦 Output: {result['output_file']}")
        logger.info(f"📏 Size: {result['file_size']:,} bytes")
        if has_entities:
            logger.info(
                f"🐾 Entities converted: {result['entities_converted']}"
            )

        return result

    except Exception as e:
        logger.error(f"❌ Conversion failed: {e}")
        return {"success": False, "error": str(e)}


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
