"""
Model extraction from JAR module.
"""

import json
import logging
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_models_from_jar(
    jar_path: str, output_dir: str, namespace: Optional[str] = None
) -> Dict:
    """
    Extract all block/item/entity models from a Java mod JAR file.

    Java models are at: assets/<namespace>/models/block/<name>.json
                       assets/<namespace>/models/item/<name>.json
                       assets/<namespace>/models/entity/<name>.json

    Args:
        jar_path: Path to the JAR file
        output_dir: Directory to extract models to
        namespace: Optional namespace to filter models

    Returns:
        Dict with extraction results including list of extracted models
    """
    extracted_models = []
    errors = []
    warnings = []

    try:
        jar_path_obj = Path(jar_path)
        if not jar_path_obj.exists():
            return {
                "success": False,
                "error": f"JAR file not found: {jar_path}",
                "extracted_models": [],
            }

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(jar_path, "r") as jar:
            file_list = jar.namelist()

            model_files = [
                f
                for f in file_list
                if f.startswith("assets/") and "/models/" in f and f.endswith(".json")
            ]

            if namespace:
                model_files = [f for f in model_files if f.startswith(f"assets/{namespace}/")]

            for model_file in model_files:
                try:
                    model_data = jar.read(model_file)
                    model_json = json.loads(model_data.decode("utf-8"))

                    parts = model_file.split("/")
                    if len(parts) >= 5:
                        model_namespace = parts[1]
                        model_type = parts[3]
                        model_name = Path(parts[-1]).stem
                    else:
                        continue

                    bedrock_type = "block" if model_type == "block" else model_type
                    bedrock_path = f"models/{bedrock_type}/{model_name}.json"

                    full_output_dir = output_path / Path(bedrock_path).parent
                    full_output_dir.mkdir(parents=True, exist_ok=True)

                    output_file = output_path / bedrock_path
                    with open(output_file, "w") as f:
                        json.dump(model_json, f, indent=2)

                    extracted_models.append(
                        {
                            "original_path": model_file,
                            "bedrock_path": bedrock_path,
                            "output_path": str(output_file),
                            "namespace": model_namespace,
                            "model_type": model_type,
                            "model_name": model_name,
                            "has_elements": "elements" in model_json,
                            "parent": model_json.get("parent"),
                            "success": True,
                        }
                    )

                except Exception as e:
                    errors.append(f"Failed to extract {model_file}: {str(e)}")

        blockstate_files = [
            f
            for f in file_list
            if f.startswith("assets/") and "/blockstates/" in f and f.endswith(".json")
        ]

        if namespace:
            blockstate_files = [f for f in blockstate_files if f.startswith(f"assets/{namespace}/")]

        blockstates_parsed = 0
        for blockstate_file in blockstate_files:
            try:
                blockstate_data = jar.read(blockstate_file)
                blockstate_json = json.loads(blockstate_data.decode("utf-8"))
                parts = blockstate_file.split("/")
                if len(parts) >= 4:
                    block_name = Path(parts[-1]).stem
                    blockstate_namespace = parts[1]
                    blockstate_output_dir = output_path / "blockstates" / blockstate_namespace
                    blockstate_output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = blockstate_output_dir / f"{block_name}.json"
                    with open(output_file, "w") as f:
                        json.dump(blockstate_json, f, indent=2)
                    blockstates_parsed += 1
            except Exception as e:
                warnings.append(f"Failed to extract blockstate {blockstate_file}: {str(e)}")

        return {
            "success": len(extracted_models) > 0,
            "extracted_models": extracted_models,
            "blockstates_extracted": blockstates_parsed,
            "errors": errors,
            "warnings": warnings,
            "count": len(extracted_models),
        }

    except zipfile.BadZipFile:
        return {
            "success": False,
            "error": f"Invalid JAR file: {jar_path}",
            "extracted_models": [],
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to extract models: {str(e)}",
            "extracted_models": [],
        }
