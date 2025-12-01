import os
import json
import uuid
from typing import List, Dict, Optional, Any

from models import addon_models as pydantic_addon_models

# Placeholder for actual user ID retrieval logic
DEFAULT_USER_ID = "conversion_system_user"


def parse_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Safely parses a JSON file."""
    if not os.path.exists(file_path):
        # print(f"Warning: JSON file not found: {file_path}")
        return None
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # print(f"Warning: Could not decode JSON from {file_path}")
        return None


def find_pack_folder(
    pack_root_path: str, pack_type_suffix: str = "BP"
) -> Optional[str]:
    """Finds a behavior or resource pack folder by common naming conventions."""
    for item in os.listdir(pack_root_path):
        item_path = os.path.join(pack_root_path, item)
        if os.path.isdir(item_path) and item.endswith(pack_type_suffix):
            manifest_path = os.path.join(item_path, "manifest.json")
            if os.path.exists(manifest_path):
                return item_path
    # Fallback: check if root itself is the pack folder (e.g. if only one pack type provided)
    if os.path.exists(os.path.join(pack_root_path, "manifest.json")):
        # crude check, might need more specific manifest parsing to confirm type
        return pack_root_path
    return None


def transform_pack_to_addon_data(
    pack_root_path: str,  # Path to the directory containing RP and BP folders
    addon_name_fallback: str,
    addon_id_override: uuid.UUID,  # The ID for the addon (job_id)
    user_id: Optional[str] = None,
) -> tuple[pydantic_addon_models.AddonDataUpload, List[Dict[str, str]]]:
    """
    Parses a converted addon pack directory (containing RP & BP)
    and transforms its content into an AddonDataUpload Pydantic model.
    Assets are conceptually copied during this process to their final destination.
    """
    actual_user_id = user_id or DEFAULT_USER_ID

    bp_path = find_pack_folder(pack_root_path, "BP")
    rp_path = find_pack_folder(pack_root_path, "RP")

    addon_description = "Converted addon."
    addon_name = addon_name_fallback

    # Extract name and description from BP manifest if possible
    if bp_path:
        bp_manifest = parse_json_file(os.path.join(bp_path, "manifest.json"))
        if bp_manifest and isinstance(bp_manifest.get("header"), dict):
            addon_name = (
                bp_manifest["header"]
                .get("name", addon_name)
                .replace(" Behavior Pack", "")
                .replace(" BP", "")
            )
            addon_description = bp_manifest["header"].get(
                "description", addon_description
            )
    elif rp_path:  # Or from RP manifest
        rp_manifest = parse_json_file(os.path.join(rp_path, "manifest.json"))
        if rp_manifest and isinstance(rp_manifest.get("header"), dict):
            addon_name = (
                rp_manifest["header"]
                .get("name", addon_name)
                .replace(" Resource Pack", "")
                .replace(" RP", "")
            )
            addon_description = rp_manifest["header"].get(
                "description", addon_description
            )

    blocks: List[pydantic_addon_models.AddonBlockCreate] = []
    # assets list (old) removed here
    recipes: List[pydantic_addon_models.AddonRecipeCreate] = []
    identified_assets_info: List[Dict[str, str]] = []  # New list for asset details

    # 1. Parse Behavior Pack (Blocks, Recipes)
    if bp_path:
        # Parse Blocks from BP
        bp_blocks_path = os.path.join(bp_path, "blocks")
        if os.path.isdir(bp_blocks_path):
            for block_file_name in os.listdir(bp_blocks_path):
                if block_file_name.endswith(".json"):
                    block_json_path = os.path.join(bp_blocks_path, block_file_name)
                    block_data_bp = parse_json_file(block_json_path)
                    if block_data_bp and isinstance(
                        block_data_bp.get("minecraft:block"), dict
                    ):
                        description = block_data_bp["minecraft:block"].get(
                            "description", {}
                        )
                        identifier = description.get("identifier")
                        if not identifier:
                            continue  # Skip block if no identifier

                        # For AddonBlock.properties, we might store non-component description fields
                        # or specific custom properties derived from the Bedrock JSON.
                        # For AddonBehavior.data, we store the components.
                        properties_for_db = {}  # Example: could store 'is_experimental'
                        if description.get("is_experimental"):
                            properties_for_db["is_experimental"] = True

                        # Simplistic: store all components as behavior data
                        behavior_data_for_db = block_data_bp["minecraft:block"].get(
                            "components", {}
                        )

                        block_create = pydantic_addon_models.AddonBlockCreate(
                            identifier=identifier,
                            properties=properties_for_db,
                            behavior=pydantic_addon_models.AddonBehaviorCreate(
                                data=behavior_data_for_db
                            )
                            if behavior_data_for_db
                            else None,
                        )
                        blocks.append(block_create)

        # Parse Recipes from BP
        bp_recipes_path = os.path.join(bp_path, "recipes")
        if os.path.isdir(bp_recipes_path):
            for recipe_file_name in os.listdir(bp_recipes_path):
                if recipe_file_name.endswith(".json"):
                    recipe_json_path = os.path.join(bp_recipes_path, recipe_file_name)
                    recipe_data = parse_json_file(recipe_json_path)
                    if recipe_data:
                        recipes.append(
                            pydantic_addon_models.AddonRecipeCreate(data=recipe_data)
                        )

    # 2. Parse Resource Pack (Assets, client-side block definitions)
    if rp_path:
        # Identify and process assets (e.g., textures)
        # This is where asset files would be copied to permanent storage
        # and AddonAssetCreate objects would be prepared.

        # Example for textures:
        rp_textures_path = os.path.join(rp_path, "textures")
        if os.path.isdir(rp_textures_path):
            for root, _, files in os.walk(rp_textures_path):
                for file_name in files:
                    if file_name.lower().endswith((".png", ".jpg", ".jpeg", ".tga")):
                        asset_file_source_path = os.path.join(root, file_name)

                        # Determine asset type and path for DB
                        # Path stored in AddonAssetCreate should be relative to the *final* asset storage
                        # For this transformation, we assume they are copied to `backend/addon_assets/{addon_id_override}/`
                        # The path for AddonAssetCreate will be like "{asset_uuid}_{original_filename}"

                        original_filename_for_db = file_name
                        asset_type_for_db = "texture"  # Default, can be refined

                        # Determine subfolder (e.g., "blocks", "items") for semantic path
                        relative_to_textures_dir = os.path.relpath(
                            asset_file_source_path, rp_textures_path
                        )
                        # e.g. blocks/my_texture.png -> type "texture_block"
                        if "block" in relative_to_textures_dir.lower():
                            asset_type_for_db = "texture_block"
                        elif "item" in relative_to_textures_dir.lower():
                            asset_type_for_db = "texture_item"

                        # This is a placeholder for the actual asset registration
                        # In a real scenario, the file from asset_file_source_path would be copied to
                        # a path like `backend/addon_assets/{addon_id_override}/{new_asset_uuid}_{original_filename_for_db}`
                        # and that new relative path (e.g. `{new_asset_uuid}_{original_filename_for_db}`)
                        # would be stored in AddonAssetCreate.path.
                        # For now, we'll use the relative path within the RP for placeholder.

                        # This path is conceptual for AddonDataUpload, final path set by create_addon_asset
                        # conceptual_path_in_rp = os.path.join("textures", relative_to_textures_dir).replace("\\\\", "/")

                        # Asset information to be returned for later processing
                        identified_assets_info.append(
                            {
                                "type": asset_type_for_db,
                                "original_filename": original_filename_for_db,
                                "source_tmp_path": asset_file_source_path,  # Full path to the asset in the temp pack
                            }
                        )

        # Client-side block definitions (blocks.json) could be processed here if needed.

    # Construct the AddonDataUpload Pydantic model with an empty assets list
    addon_data_upload = pydantic_addon_models.AddonDataUpload(
        name=addon_name,
        description=addon_description,
        user_id=actual_user_id,
        blocks=blocks,
        assets=[],  # Assets are handled separately now
        recipes=recipes,
    )

    return addon_data_upload, identified_assets_info  # Return both objects


# Note: Asset file copying logic is explicitly NOT in this parser.
# The parser identifies assets and their source paths.
# The calling function (e.g., in main.py or crud.py) will handle the actual
# file copy operation when iterating through AddonDataUpload.assets
# and creating AddonAsset records using crud.create_addon_asset.
# This means AddonAssetCreate.path in AddonDataUpload is more of a "source_path_within_pack".
# This will need careful handling in the integration step.
#
# Re-evaluation: For AddonDataUpload, the `assets` list expects `AddonAssetCreate`.
# `AddonAssetCreate` has `path` which, for `crud.update_addon_details` (if it were to handle assets directly this way),
# would mean "final relative path in permanent storage".
# This parser should probably return a structure that includes the *source path* of the asset from the temp pack
# and the intended *type* and *original_filename*.
# The actual creation of `AddonAsset` DB records and file copying to permanent storage should be done
# by iterating this prepared data and calling `crud.create_addon_asset` for each asset.
#
# For now, the `assets` list in `AddonDataUpload` will contain conceptual paths.
# The integration in `main.py` will need to be smart about this.
