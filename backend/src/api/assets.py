"""
Assets API endpoints for conversion asset management.
"""

import uuid
import os
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from db.base import get_db
from db import crud
from services.asset_conversion_service import asset_conversion_service

# Configure logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

# File storage configuration
ASSETS_STORAGE_DIR = os.getenv("ASSETS_STORAGE_DIR", "conversion_assets")
MAX_ASSET_SIZE = 50 * 1024 * 1024  # 50 MB


class AssetResponse(BaseModel):
    id: str
    conversion_id: str
    asset_type: str
    original_path: str
    converted_path: Optional[str] = None
    status: str
    asset_metadata: Optional[Dict[str, Any]] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    original_filename: str
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class AssetUploadRequest(BaseModel):
    asset_type: str
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        schema_extra = {
            "example": {
                "asset_type": "texture",
                "metadata": {
                    "category": "blocks",
                    "resolution": "16x16"
                }
            }
        }


class AssetStatusUpdate(BaseModel):
    status: str
    converted_path: Optional[str] = None
    error_message: Optional[str] = None


def _asset_to_response(asset) -> AssetResponse:
    """Convert database Asset model to API response."""
    return AssetResponse(
        id=str(asset.id),
        conversion_id=str(asset.conversion_id),
        asset_type=asset.asset_type,
        original_path=asset.original_path,
        converted_path=asset.converted_path,
        status=asset.status,
        asset_metadata=asset.asset_metadata,
        file_size=asset.file_size,
        mime_type=asset.mime_type,
        original_filename=asset.original_filename,
        error_message=asset.error_message,
        created_at=asset.created_at.isoformat(),
        updated_at=asset.updated_at.isoformat()
    )


@router.get("/conversions/{conversion_id}/assets", response_model=List[AssetResponse], tags=["assets"])
async def list_conversion_assets(
    conversion_id: str = Path(..., description="ID of the conversion job"),
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    List all assets for a given conversion job.

    - **conversion_id**: ID of the conversion job
    - **asset_type**: Filter by asset type (e.g., 'texture', 'model', 'sound')
    - **status**: Filter by status (e.g., 'pending', 'processing', 'converted', 'failed')
    - **skip**: Number of assets to skip (for pagination)
    - **limit**: Maximum number of assets to return
    """
    try:
        assets = await crud.list_assets_for_conversion(
            db,
            conversion_id=conversion_id,
            asset_type=asset_type,
            status=status,
            skip=skip,
            limit=limit
        )
        return [_asset_to_response(asset) for asset in assets]
    except Exception as e:
        logger.error(f"Error listing assets for conversion {conversion_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve assets")


@router.post("/conversions/{conversion_id}/assets", response_model=AssetResponse, tags=["assets"])
async def upload_asset(
    conversion_id: str = Path(..., description="ID of the conversion job"),
    asset_type: str = Form(..., description="Type of asset (e.g., 'texture', 'model', 'sound')"),
    file: UploadFile = File(..., description="Asset file to upload"),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a new asset for a conversion job.

    - **conversion_id**: ID of the conversion job
    - **asset_type**: Type of asset being uploaded
    - **file**: The asset file to upload
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Create storage directory if it doesn't exist
    os.makedirs(ASSETS_STORAGE_DIR, exist_ok=True)

    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1].lower()
    stored_filename = f"{file_id}{file_ext}"
    file_path = os.path.join(ASSETS_STORAGE_DIR, stored_filename)

    # Save the uploaded file
    try:
        file_size = 0
        with open(file_path, "wb") as buffer:
            for chunk in file.file:
                chunk_size = len(chunk)
                file_size += chunk_size
                if file_size > MAX_ASSET_SIZE:
                    os.remove(file_path)  # Clean up partial file
                    raise HTTPException(
                        status_code=413,
                        detail=f"File size exceeds the limit of {MAX_ASSET_SIZE // (1024 * 1024)}MB"
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving asset file: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Could not save file")
    finally:
        file.file.close()

    # Create database record
    try:
        asset = await crud.create_asset(
            db,
            conversion_id=conversion_id,
            asset_type=asset_type,
            original_path=file_path,
            original_filename=file.filename,
            file_size=file_size,
            mime_type=file.content_type
        )
        return _asset_to_response(asset)
    except ValueError as e:
        # Clean up uploaded file if database creation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Clean up uploaded file if database creation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Error creating asset record: {e}")
        raise HTTPException(status_code=500, detail="Failed to create asset record")


@router.get("/assets/{asset_id}", response_model=AssetResponse, tags=["assets"])
async def get_asset(
    asset_id: str = Path(..., description="ID of the asset"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific asset.

    - **asset_id**: ID of the asset to retrieve
    """
    asset = await crud.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return _asset_to_response(asset)


@router.put("/assets/{asset_id}/status", response_model=AssetResponse, tags=["assets"])
async def update_asset_status(
    status_update: AssetStatusUpdate,
    asset_id: str = Path(..., description="ID of the asset"),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the conversion status of an asset.

    - **asset_id**: ID of the asset to update
    - **status**: New status ('pending', 'processing', 'converted', 'failed')
    - **converted_path**: Path to converted file (if status is 'converted')
    - **error_message**: Error message (if status is 'failed')
    """
    asset = await crud.update_asset_status(
        db,
        asset_id=asset_id,
        status=status_update.status,
        converted_path=status_update.converted_path,
        error_message=status_update.error_message
    )

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return _asset_to_response(asset)


@router.put("/assets/{asset_id}/metadata", response_model=AssetResponse, tags=["assets"])
async def update_asset_metadata(
    metadata: Dict[str, Any],
    asset_id: str = Path(..., description="ID of the asset"),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the metadata of an asset.

    - **asset_id**: ID of the asset to update
    - **metadata**: New metadata dictionary
    """
    asset = await crud.update_asset_metadata(db, asset_id=asset_id, metadata=metadata)

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return _asset_to_response(asset)


@router.delete("/assets/{asset_id}", tags=["assets"])
async def delete_asset(
    asset_id: str = Path(..., description="ID of the asset"),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an asset and its associated file.

    - **asset_id**: ID of the asset to delete
    """
    # Get asset info before deletion
    asset = await crud.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Delete the database record
    deleted_info = await crud.delete_asset(db, asset_id)
    if not deleted_info:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Clean up the physical file
    if asset.original_path and os.path.exists(asset.original_path):
        try:
            os.remove(asset.original_path)
            logger.info(f"Deleted asset file: {asset.original_path}")
        except Exception as e:
            logger.warning(f"Could not delete asset file {asset.original_path}: {e}")

    if asset.converted_path and os.path.exists(asset.converted_path):
        try:
            os.remove(asset.converted_path)
            logger.info(f"Deleted converted asset file: {asset.converted_path}")
        except Exception as e:
            logger.warning(f"Could not delete converted asset file {asset.converted_path}: {e}")

    return {"message": f"Asset {asset_id} deleted successfully"}


# Asset conversion trigger endpoint (for AI engine integration)
@router.post("/assets/{asset_id}/convert", response_model=AssetResponse, tags=["assets"])
async def trigger_asset_conversion(
    asset_id: str = Path(..., description="ID of the asset to convert"),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger conversion for a specific asset.

    This endpoint initiates AI-powered conversion for a specific asset,
    integrating with the AI engine for intelligent asset transformation.

    - **asset_id**: ID of the asset to convert
    """
    # Verify asset exists
    asset = await crud.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.status == "converted":
        # Return already converted asset
        return _asset_to_response(asset)

    try:
        # Trigger conversion through the service
        result = await asset_conversion_service.convert_asset(asset_id)

        if result.get("success"):
            # Get updated asset
            updated_asset = await crud.get_asset(db, asset_id)
            logger.info(f"Asset {asset_id} conversion triggered successfully")
            return _asset_to_response(updated_asset)
        else:
            error_msg = result.get("error", "Conversion failed")
            logger.error(f"Asset {asset_id} conversion failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Conversion failed: {error_msg}")

    except Exception as e:
        logger.error(f"Error triggering asset conversion: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger asset conversion")


# Batch conversion endpoint for conversion jobs
@router.post("/conversions/{conversion_id}/assets/convert-all", tags=["assets"])
async def convert_all_conversion_assets(
    conversion_id: str = Path(..., description="ID of the conversion job"),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger conversion for all pending assets in a conversion job.

    This endpoint processes all pending assets for a conversion job through
    the AI engine, providing batch asset conversion capabilities.

    - **conversion_id**: ID of the conversion job
    """
    try:
        # Trigger batch conversion through the service
        result = await asset_conversion_service.convert_assets_for_conversion(conversion_id)

        return {
            "message": "Asset conversion batch completed",
            "conversion_id": conversion_id,
            "total_assets": result.get("total_assets", 0),
            "converted_count": result.get("converted_count", 0),
            "failed_count": result.get("failed_count", 0),
            "success": result.get("success", False)
        }

    except Exception as e:
        logger.error(f"Error in batch asset conversion: {e}")
        raise HTTPException(status_code=500, detail="Failed to convert assets")
