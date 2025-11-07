import json
import uuid
import io
import zipfile
from typing import Dict, Any, List

from models import addon_models as pydantic_addon_models # For type hinting with Pydantic models

# Constants for manifest versions, can be updated as needed
MIN_ENGINE_VERSION_RP = [1, 16, 0]
MIN_ENGINE_VERSION_BP = [1, 16, 0]
MANIFEST_VERSION = 2
PACK_VERSION = [1, 0, 0]


def generate_bp_manifest(
    addon_pydantic: pydantic_addon_models.AddonDetails,
    module_uuid: str,
    header_uuid: str
) -> Dict[str, Any]:
    """Generates the behavior pack manifest.json content."""
    return {
        "format_version": MANIFEST_VERSION,
        "header": {
            "name": f"{addon_pydantic.name} Behavior Pack",
            "description": addon_pydantic.description or f"Behavior pack for {addon_pydantic.name}",
            "uuid": header_uuid,
            "version": PACK_VERSION,
            "min_engine_version": MIN_ENGINE_VERSION_BP,
        },
        "modules": [
            {
                "type": "data",
                "uuid": module_uuid,
                "version": PACK_VERSION,
            }
        ],
        # Optional: Add dependencies if your addon relies on others, e.g., experimental features
        # "dependencies": [
        #     {
        #         "uuid": "b26a4d4c-af54-4ff2-b3f0-9550596aaf14", # Example: Experimental Gameplay
        #         "version": [0, 1, 0]
        #     }
        # ]
    }

def generate_rp_manifest(
    addon_pydantic: pydantic_addon_models.AddonDetails,
    module_uuid: str,
    header_uuid: str
) -> Dict[str, Any]:
    """Generates the resource pack manifest.json content."""
    return {
        "format_version": MANIFEST_VERSION,
        "header": {
            "name": f"{addon_pydantic.name} Resource Pack",
            "description": addon_pydantic.description or f"Resource pack for {addon_pydantic.name}",
            "uuid": header_uuid,
            "version": PACK_VERSION,
            "min_engine_version": MIN_ENGINE_VERSION_RP,
        },
        "modules": [
            {
                "type": "resources",
                "uuid": module_uuid,
                "version": PACK_VERSION,
            }
        ],
    }

# Placeholder for other generation functions to be added later
def generate_block_behavior_json(block_pydantic: pydantic_addon_models.AddonBlock) -> Dict[str, Any]:
    """
    Generates the JSON content for a single block's behavior file.
    Example: MyAddon BP/blocks/custom_test_block.json
    """
    # This is a simplified example. Real block behavior can be complex.
    # The identifier should be like "namespace:block_name"
    # Example: "custom:my_block"

    components = {}
    # Basic properties might go into "minecraft:block_description" or other components
    if block_pydantic.properties:
        # This is highly dependent on how properties are structured and map to Bedrock components
        # For example, if 'luminance' is a property:
        if "luminance" in block_pydantic.properties:
            components["minecraft:block_light_emission"] = block_pydantic.properties["luminance"]
        if "friction" in block_pydantic.properties:
            components["minecraft:friction"] = block_pydantic.properties["friction"]
        # Add more property mappings here

    # Add behavior data
    if block_pydantic.behavior and block_pydantic.behavior.data:
        # Behavior data might include components, events, etc.
        # This assumes behavior.data is already structured somewhat like Bedrock components
        for key, value in block_pydantic.behavior.data.items():
            components[key] = value

    # Default component if no other properties define one.
    # A block usually needs at least a description.
    # if not components: # Or ensure a base description component
    # components["minecraft:display_name"] = f"tile.{block_pydantic.identifier}.name" # For localization

    return {
        "format_version": "1.16.100", # Or a more current version
        "minecraft:block": {
            "description": {
                "identifier": block_pydantic.identifier,
                "is_experimental": False, # Adjust if necessary
                # "properties": {} # For block states/properties if any
            },
            "components": components,
            # "events": {} # For block events
        }
    }

def generate_rp_block_definitions_json(addon_blocks: List[pydantic_addon_models.AddonBlock]) -> Dict[str, Any]:
    """
    Generates the blocks.json for the resource pack.
    This defines client-side appearance, sound, textures.
    """
    # Example: MyAddon RP/blocks.json
    output = {
        "format_version": "1.16.100", # Use appropriate version
    }
    for block in addon_blocks:
        # Assuming block.identifier is like "namespace:block_name"
        # The key in blocks.json is the full identifier.
        block_definition = {
            # "sound": "stone", # Example, make this configurable
            # "textures": {
            #    "up": "my_block_top", # These are short names defined in terrain_texture.json
            #    "down": "my_block_bottom",
            #    "side": "my_block_side"
            # }
        }
        # This is highly dependent on how block appearance is stored in AddonBlock.properties
        # or related asset information.
        # For now, a very basic placeholder.
        # A common approach is to have a 'texture_set' property or link assets.
        if block.properties and "rp_sound" in block.properties:
            block_definition["sound"] = block.properties["rp_sound"]

        if block.properties and "rp_texture_name" in block.properties:
             # This implies terrain_texture.json would map this name to actual texture files
            block_definition["textures"] = block.properties["rp_texture_name"]
        elif block.properties and isinstance(block.properties.get("rp_textures"), dict):
            block_definition["textures"] = block.properties["rp_textures"]
        else:
            # Default to use identifier as texture name if not specified
            texture_name_from_id = block.identifier.split(":")[-1]
            block_definition["textures"] = texture_name_from_id


        output[block.identifier] = block_definition
    return output

def generate_terrain_texture_json(addon_assets: List[pydantic_addon_models.AddonAsset]) -> Dict[str, Any]:
    """
    Generates the terrain_texture.json file based on texture assets.
    """
    texture_data = {}
    for asset in addon_assets:
        if asset.type == "texture": # Assuming a way to identify block textures
            # asset.path is like "addon_id/asset_id_filename.png"
            # We need a short name for the texture, e.g., "my_block_texture"
            # And the actual path relative to RP/textures/ folder.
            # Example: asset.original_filename = "my_block.png"
            # asset.path might be "textures/blocks/my_block.png" (if stored with this intent)
            # or we derive from original_filename.

            texture_name = os.path.splitext(asset.original_filename)[0] if asset.original_filename else \
                           os.path.splitext(os.path.basename(asset.path))[0]

            # Path in terrain_texture.json is relative to the "textures" folder of the RP
            # e.g., "textures/blocks/my_custom_block_texture"
            # Our asset.path is "addon_id/asset_id_filename.png" relative to BASE_ASSET_PATH
            # For the ZIP, it should be "textures/blocks/original_filename.png" (example)
            # So, the value here should be the path used *inside* the RP.
            # Let's assume asset.original_filename is 'dirt.png', asset.type is 'texture_block'
            # and it should be placed in 'textures/blocks/dirt.png' in RP.
            # The terrain_texture.json entry would be: "dirt": {"textures": "textures/blocks/dirt"}

            # This logic needs to be robust based on how asset paths are decided for export.
            # For now, assume asset.path in DB is already the desired relative path within RP's textures folder
            # OR that asset.original_filename is enough to place it correctly.
            # Let's assume a simple structure: textures/{original_filename_without_ext}
            # And original_filename contains the intended subfolder e.g. "blocks/my_texture.png"

            # If asset.original_filename = "blocks/my_block.png", then texture_name = "my_block" (this is wrong)
            # The key in terrain_texture.json is the "short name" used in blocks.json
            # The value is the path to the texture file (without .png) relative to RP root.

            # Let's assume the key is the filename without extension:

            # Path in terrain_texture.json needs to be like "textures/blocks/my_block_texture"
            # if the file is textures/blocks/my_block_texture.png in RP
            # If original_filename is "my_block_texture.png" and it's a block texture,
            # it might go to "textures/blocks/my_block_texture.png"
            # The value for terrain_texture.json would be "textures/blocks/my_block_texture"

            # Simplification: use original_filename without extension as key,
            # and assume it's placed in 'textures/blocks/' or 'textures/items/'
            texture_folder = "blocks" # Default, can be based on asset.type or a property
            if "item" in asset.type: # very basic heuristic
                texture_folder = "items"

            # Path for terrain_texture.json value:
            internal_texture_path = f"textures/{texture_folder}/{texture_name}"

            texture_data[texture_name] = {
                "textures": internal_texture_path
            }

    return {
        "resource_pack_name": "vanilla", # Standard practice
        "texture_name": "atlas.terrain",
        "padding": 8,
        "num_mip_levels": 4,
        "texture_data": texture_data,
    }


def generate_recipe_json(recipe: pydantic_addon_models.AddonRecipe) -> Dict[str, Any]:
    """
    Generates the JSON for a single recipe file.
    Filename could be recipe_id.json or similar.
    """
    # Assumes recipe.data is already structured very close to Bedrock recipe format.
    # Example: recipe.data = {"format_version": "1.12.0", "minecraft:recipe_shaped": {...}}
    if not isinstance(recipe.data, dict):
        # Or raise error, or log and skip
        return {"error": "Recipe data is not a valid dictionary"}
    return recipe.data


import os
import datetime # For example usage in __main__

# --- End of imports ---

# Main ZIP creation function (to be completed)
def create_mcaddon_zip(
    addon_pydantic: pydantic_addon_models.AddonDetails,
    asset_base_path: str # e.g., "backend/addon_assets"
) -> io.BytesIO:
    """
    Orchestrates the creation of all necessary files and folders for the .mcaddon pack
    and creates the .mcaddon ZIP file in memory.
    """
    zip_buffer = io.BytesIO()

    # Sanitize addon name for folder names
    sanitized_addon_name = "".join(c if c.isalnum() else "_" for c in addon_pydantic.name)
    if not sanitized_addon_name:
        sanitized_addon_name = "MyAddon"

    bp_folder_name = f"{sanitized_addon_name} BP"
    rp_folder_name = f"{sanitized_addon_name} RP"

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Generate UUIDs for manifests
        bp_header_uuid = str(uuid.uuid4())
        bp_module_uuid = str(uuid.uuid4())
        rp_header_uuid = str(uuid.uuid4())
        rp_module_uuid = str(uuid.uuid4())

        # Behavior Pack (BP)
        bp_manifest_content = generate_bp_manifest(addon_pydantic, bp_module_uuid, bp_header_uuid)
        zf.writestr(f"{bp_folder_name}/manifest.json", json.dumps(bp_manifest_content, indent=2))

        for block in addon_pydantic.blocks:
            block_behavior_content = generate_block_behavior_json(block)
            # Filename from identifier: "custom:my_block" -> "my_block.json"
            behavior_filename = block.identifier.split(":")[-1] + ".json"
            zf.writestr(f"{bp_folder_name}/blocks/{behavior_filename}", json.dumps(block_behavior_content, indent=2))

        for recipe in addon_pydantic.recipes:
            recipe_content = generate_recipe_json(recipe)
            # Filename needs to be unique, e.g., based on recipe ID or a sanitized name from its description
            recipe_identifier = recipe.data.get("minecraft:recipe_shaped", {}).get("description", {}).get("identifier") or \
                                recipe.data.get("minecraft:recipe_shapeless", {}).get("description", {}).get("identifier") or \
                                str(recipe.id) # Fallback to recipe UUID
            recipe_filename = recipe_identifier.split(":")[-1] + ".json"
            zf.writestr(f"{bp_folder_name}/recipes/{recipe_filename}", json.dumps(recipe_content, indent=2))

        # Resource Pack (RP)
        rp_manifest_content = generate_rp_manifest(addon_pydantic, rp_module_uuid, rp_header_uuid)
        zf.writestr(f"{rp_folder_name}/manifest.json", json.dumps(rp_manifest_content, indent=2))

        if addon_pydantic.blocks: # Only create blocks.json if there are blocks
            rp_blocks_content = generate_rp_block_definitions_json(addon_pydantic.blocks)
            zf.writestr(f"{rp_folder_name}/blocks.json", json.dumps(rp_blocks_content, indent=2))

        # Asset handling
        texture_assets = [asset for asset in addon_pydantic.assets if asset.type.startswith("texture")]
        if texture_assets:
            terrain_texture_content = generate_terrain_texture_json(texture_assets)
            zf.writestr(f"{rp_folder_name}/textures/terrain_texture.json", json.dumps(terrain_texture_content, indent=2))
            # (Could also need item_texture.json, etc.)

            for asset in texture_assets:
                # asset.path in DB is like "{asset_id_uuid}_{file.filename}" relative to "{addon_id}" folder
                # Full disk path: backend/addon_assets/{addon_id}/{asset.path}
                asset_disk_path = os.path.join(asset_base_path, str(addon_pydantic.id), asset.path)

                # Determine path within ZIP for RP
                # Example: if original_filename is "my_block.png", place in "textures/blocks/my_block.png"
                # This requires asset.original_filename to be reliable.
                zip_texture_path_parts = []
                if "block" in asset.type: # e.g. asset.type == "texture_block"
                    zip_texture_path_parts = ["textures", "blocks"]
                elif "item" in asset.type: # e.g. asset.type == "texture_item"
                    zip_texture_path_parts = ["textures", "items"]
                else: # Default fallback
                    zip_texture_path_parts = ["textures", "misc"]

                if asset.original_filename:
                    zip_texture_path_parts.append(asset.original_filename)
                else: # Fallback if original_filename is somehow missing
                    zip_texture_path_parts.append(os.path.basename(asset.path))

                zip_path = os.path.join(rp_folder_name, *zip_texture_path_parts)

                if os.path.exists(asset_disk_path):
                    zf.write(asset_disk_path, zip_path)
                else:
                    # Log or handle missing asset file
                    print(f"Warning: Asset file not found on disk: {asset_disk_path}")

        # TODO: Handle other asset types like sounds, models in their respective folders.

    zip_buffer.seek(0)
    return zip_buffer


if __name__ == '__main__':
    # Example Usage (for testing the functions directly)
    mock_addon_id = uuid.uuid4()
    mock_block_id = uuid.uuid4()

    mock_addon = pydantic_addon_models.AddonDetails(
        id=mock_addon_id,
        name="My Test Addon",
        description="A cool addon for testing.",
        user_id="test_user",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        blocks=[
            pydantic_addon_models.AddonBlock(
                id=mock_block_id,
                addon_id=mock_addon_id,
                identifier="custom:magic_brick",
                properties={"luminance": 10, "friction": 0.8, "rp_texture_name": "magic_brick_tex"},
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now(),
                behavior=pydantic_addon_models.AddonBehavior(
                    id=uuid.uuid4(),
                    block_id=mock_block_id,
                    data={"minecraft:on_interact": {"event": "explode", "target": "self"}},
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now()
                )
            )
        ],
        assets=[
            pydantic_addon_models.AddonAsset(
                id=uuid.uuid4(), addon_id=mock_addon_id, created_at=datetime.datetime.now(), updated_at=datetime.datetime.now(),
                type="texture_block",
                path=f"{str(uuid.uuid4())}_magic_brick_tex.png", # Path as stored by CRUD: {asset_id}_{original_filename}
                original_filename="magic_brick_tex.png"
            )
        ],
        recipes=[] # Add mock recipe if needed for zip test
    )

    bp_manifest_uuid_module = str(uuid.uuid4())
    bp_manifest_uuid_header = str(uuid.uuid4())
    rp_manifest_uuid_module = str(uuid.uuid4())
    rp_manifest_uuid_header = str(uuid.uuid4())

    bp_manifest = generate_bp_manifest(mock_addon, bp_manifest_uuid_module, bp_manifest_uuid_header)
    rp_manifest = generate_rp_manifest(mock_addon, rp_manifest_uuid_module, rp_manifest_uuid_header)

    print("Behavior Pack Manifest:", json.dumps(bp_manifest, indent=2))
    print("\\nResource Pack Manifest:", json.dumps(rp_manifest, indent=2))

    mock_block_instance = mock_addon.blocks[0] # Get the block from the list
    block_behavior_content = generate_block_behavior_json(mock_block_instance)
    print("\\nBlock Behavior JSON (custom:magic_brick):", json.dumps(block_behavior_content, indent=2))

    rp_blocks_json = generate_rp_block_definitions_json(mock_addon.blocks)
    print("\\nRP blocks.json:", json.dumps(rp_blocks_json, indent=2))

    terrain_textures = generate_terrain_texture_json(mock_addon.assets)
    print("\\nterrain_texture.json:", json.dumps(terrain_textures, indent=2))

    # Test ZIP creation (requires mock asset file on disk)
    # Create a dummy asset file for testing create_mcaddon_zip
    mock_asset_base_path = "backend/addon_assets" # Matches crud.BASE_ASSET_PATH
    mock_addon_asset_dir = os.path.join(mock_asset_base_path, str(mock_addon.id))
    os.makedirs(mock_addon_asset_dir, exist_ok=True)

    mock_asset_on_disk_path = os.path.join(mock_addon_asset_dir, mock_addon.assets[0].path)
    with open(mock_asset_on_disk_path, "w") as f:
        f.write("dummy texture content")

    print(f"\\nAttempting to create ZIP for addon {mock_addon.id}...")
    print(f"Mock asset created at: {mock_asset_on_disk_path}")

    try:
        zip_bytes_io = create_mcaddon_zip(mock_addon, mock_asset_base_path)
        zip_filename = f"{mock_addon.name.replace(' ', '_')}.mcaddon"
        with open(zip_filename, "wb") as f:
            f.write(zip_bytes_io.getvalue())
        print(f"Successfully created {zip_filename}. Size: {len(zip_bytes_io.getvalue())} bytes.")

        # Clean up dummy file and dir
        os.remove(mock_asset_on_disk_path)
        if not os.listdir(mock_addon_asset_dir): # Check if dir is empty
             os.rmdir(mock_addon_asset_dir)
        if os.path.exists(zip_filename): # remove the created zip
            os.remove(zip_filename)

    except Exception as e:
        print(f"Error during ZIP creation test: {e}")
        import traceback
        traceback.print_exc()

