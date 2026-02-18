
import pytest
import os
import io
import zipfile
import uuid
import datetime
from unittest.mock import MagicMock, patch
from services import addon_exporter
from models import addon_models as pydantic_addon_models

def test_create_mcaddon_zip_prevents_zip_slip(tmp_path):
    """
    Test that create_mcaddon_zip prevents Zip Slip vulnerability
    by sanitizing asset filenames.
    """
    # Setup mock data
    mock_addon_id = uuid.uuid4()
    mock_asset_base_path = str(tmp_path / "addon_assets")
    mock_addon_asset_dir = os.path.join(mock_asset_base_path, str(mock_addon_id))
    os.makedirs(mock_addon_asset_dir, exist_ok=True)

    # Create a dummy asset file on disk
    asset_path_on_disk = f"{uuid.uuid4()}_malicious.txt"
    full_asset_path = os.path.join(mock_addon_asset_dir, asset_path_on_disk)
    with open(full_asset_path, "w") as f:
        f.write("malicious content")

    # Malicious filename attempting traversal
    malicious_filename = "../../../../malicious.txt"

    mock_addon = pydantic_addon_models.AddonDetails(
        id=mock_addon_id,
        name="Malicious Addon",
        description="Testing Zip Slip",
        user_id="hacker",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        blocks=[],
        assets=[
            pydantic_addon_models.AddonAsset(
                id=uuid.uuid4(),
                addon_id=mock_addon_id,
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now(),
                type="texture_block", # Uses "textures/blocks" path
                path=asset_path_on_disk,
                original_filename=malicious_filename
            )
        ],
        recipes=[]
    )

    # Execute the vulnerable function
    zip_buffer = addon_exporter.create_mcaddon_zip(mock_addon, mock_asset_base_path)

    # Verify the vulnerability is prevented
    found_traversal = False
    found_sanitized = False
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        for name in zf.namelist():
            # Check if any file path contains traversal characters
            if "../" in name or "..\\" in name:
                found_traversal = True

            # Check if the sanitized version exists (malicious.txt inside textures/blocks)
            if "malicious.txt" in name and not ("../" in name):
                found_sanitized = True

    # After the fix, we expect NO traversal and YES sanitized file
    assert not found_traversal, "Vulnerability persisted: Traversal path found in zip"
    assert found_sanitized, "Sanitized file not found in zip"
