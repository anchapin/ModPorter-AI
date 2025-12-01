"""
Asset Conversion Service - Handles integration with AI Engine for asset conversion
"""

import os
import asyncio
import httpx
import logging
from typing import Dict, Any

from src.db import crud
from src.db.base import AsyncSessionLocal

logger = logging.getLogger(__name__)

# AI Engine settings
AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://localhost:8001")
CONVERSION_ASSETS_DIR = os.getenv("ASSETS_STORAGE_DIR", "conversion_assets")


class AssetConversionService:
    """Service for handling asset conversion through the AI Engine"""

    def __init__(self):
        self.ai_engine_url = AI_ENGINE_URL

    async def convert_asset(self, asset_id: str) -> Dict[str, Any]:
        """
        Convert a single asset using the AI Engine.

        Args:
            asset_id: ID of the asset to convert

        Returns:
            Dictionary with conversion result information
        """
        async with AsyncSessionLocal() as session:
            # Get asset details
            asset = await crud.get_asset(session, asset_id)
            if not asset:
                raise ValueError(f"Asset {asset_id} not found")

            # Update status to processing
            await crud.update_asset_status(session, asset_id, "processing")

            try:
                # Call AI Engine for asset conversion
                conversion_result = await self._call_ai_engine_convert_asset(
                    asset_id=asset_id,
                    asset_type=asset.asset_type,
                    input_path=asset.original_path,
                    original_filename=asset.original_filename,
                )

                if conversion_result.get("success"):
                    # Update asset with converted path
                    converted_path = conversion_result.get("converted_path")
                    await crud.update_asset_status(
                        session, asset_id, "converted", converted_path=converted_path
                    )

                    logger.info(f"Asset {asset_id} converted successfully")
                    return {
                        "success": True,
                        "asset_id": asset_id,
                        "converted_path": converted_path,
                        "message": "Asset converted successfully",
                    }
                else:
                    # Update asset with error
                    error_message = conversion_result.get("error", "Conversion failed")
                    await crud.update_asset_status(
                        session, asset_id, "failed", error_message=error_message
                    )

                    logger.error(f"Asset {asset_id} conversion failed: {error_message}")
                    return {
                        "success": False,
                        "asset_id": asset_id,
                        "error": error_message,
                    }

            except Exception as e:
                # Update asset with error
                error_message = f"Conversion error: {str(e)}"
                await crud.update_asset_status(
                    session, asset_id, "failed", error_message=error_message
                )

                logger.error(f"Asset {asset_id} conversion error: {e}")
                return {"success": False, "asset_id": asset_id, "error": error_message}

    async def convert_assets_for_conversion(self, conversion_id: str) -> Dict[str, Any]:
        """
        Convert all assets associated with a conversion job.

        Args:
            conversion_id: ID of the conversion job

        Returns:
            Dictionary with batch conversion results
        """
        async with AsyncSessionLocal() as session:
            # Get all assets for the conversion
            assets = await crud.list_assets_for_conversion(
                session,
                conversion_id,
                status="pending",  # Only convert pending assets
            )

            if not assets:
                return {
                    "success": True,
                    "conversion_id": conversion_id,
                    "message": "No pending assets to convert",
                    "converted_count": 0,
                    "failed_count": 0,
                }

            results = []
            converted_count = 0
            failed_count = 0

            # Process assets in parallel (with limited concurrency)
            semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent conversions

            async def convert_single_asset(asset):
                async with semaphore:
                    result = await self.convert_asset(str(asset.id))
                    return result

            # Execute conversions
            tasks = [convert_single_asset(asset) for asset in assets]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    failed_count += 1
                    logger.error(f"Asset conversion exception: {result}")
                elif result.get("success"):
                    converted_count += 1
                else:
                    failed_count += 1

            logger.info(
                f"Conversion {conversion_id}: {converted_count} assets converted, {failed_count} failed"
            )

            return {
                "success": True,
                "conversion_id": conversion_id,
                "total_assets": len(assets),
                "converted_count": converted_count,
                "failed_count": failed_count,
                "results": [r for r in results if not isinstance(r, Exception)],
            }

    async def _call_ai_engine_convert_asset(
        self, asset_id: str, asset_type: str, input_path: str, original_filename: str
    ) -> Dict[str, Any]:
        """
        Call the AI Engine to convert a specific asset.

        Args:
            asset_id: ID of the asset
            asset_type: Type of asset (texture, model, sound, etc.)
            input_path: Path to the original asset file
            original_filename: Original filename of the asset

        Returns:
            Dictionary with conversion result
        """
        try:
            # Generate output path
            output_filename = f"{asset_id}_converted_{original_filename}"
            output_path = os.path.join(
                CONVERSION_ASSETS_DIR, "converted", output_filename
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Prepare request for AI Engine
            request_data = {
                "asset_id": asset_id,
                "asset_type": asset_type,
                "input_path": input_path,
                "output_path": output_path,
                "original_filename": original_filename,
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                # Check if AI Engine is available
                try:
                    health_response = await client.get(
                        f"{self.ai_engine_url}/api/v1/health"
                    )
                    if health_response.status_code != 200:
                        return await self._fallback_conversion(
                            asset_type, input_path, output_path
                        )
                except Exception:
                    return await self._fallback_conversion(
                        asset_type, input_path, output_path
                    )

                # Call AI Engine asset conversion endpoint
                response = await client.post(
                    f"{self.ai_engine_url}/api/v1/convert/asset", json=request_data
                )

                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "converted_path": result.get("converted_path", output_path),
                        "metadata": result.get("metadata", {}),
                    }
                else:
                    error_msg = (
                        f"AI Engine returned {response.status_code}: {response.text}"
                    )
                    logger.error(f"AI Engine error for asset {asset_id}: {error_msg}")
                    return await self._fallback_conversion(
                        asset_type, input_path, output_path
                    )

        except Exception as e:
            logger.error(f"Error calling AI Engine for asset {asset_id}: {e}")
            return await self._fallback_conversion(asset_type, input_path, output_path)

    async def _fallback_conversion(
        self, asset_type: str, input_path: str, output_path: str
    ) -> Dict[str, Any]:
        """
        Fallback conversion method when AI Engine is not available.

        Args:
            asset_type: Type of asset
            input_path: Input file path
            output_path: Output file path

        Returns:
            Dictionary with conversion result
        """
        try:
            if asset_type == "texture":
                return await self._fallback_texture_conversion(input_path, output_path)
            elif asset_type == "sound":
                return await self._fallback_sound_conversion(input_path, output_path)
            elif asset_type == "model":
                return await self._fallback_model_conversion(input_path, output_path)
            else:
                # For unknown types, just copy the file
                return await self._fallback_copy_conversion(input_path, output_path)

        except Exception as e:
            logger.error(f"Fallback conversion error: {e}")
            return {"success": False, "error": f"Fallback conversion failed: {str(e)}"}

    async def _fallback_texture_conversion(
        self, input_path: str, output_path: str
    ) -> Dict[str, Any]:
        """Simple texture conversion fallback"""
        try:
            # For now, just copy PNG files or convert to PNG
            import shutil
            from PIL import Image

            # If already PNG, just copy
            if input_path.lower().endswith(".png"):
                shutil.copy2(input_path, output_path)
            else:
                # Convert to PNG
                with Image.open(input_path) as img:
                    # Ensure output has .png extension
                    if not output_path.lower().endswith(".png"):
                        output_path = os.path.splitext(output_path)[0] + ".png"
                    img.save(output_path, "PNG")

            return {
                "success": True,
                "converted_path": output_path,
                "metadata": {"conversion_type": "fallback_texture"},
            }
        except Exception as e:
            return {"success": False, "error": f"Texture conversion failed: {str(e)}"}

    async def _fallback_sound_conversion(
        self, input_path: str, output_path: str
    ) -> Dict[str, Any]:
        """Simple sound conversion fallback"""
        try:
            import shutil

            # For now, just copy the file
            shutil.copy2(input_path, output_path)

            return {
                "success": True,
                "converted_path": output_path,
                "metadata": {"conversion_type": "fallback_sound"},
            }
        except Exception as e:
            return {"success": False, "error": f"Sound conversion failed: {str(e)}"}

    async def _fallback_model_conversion(
        self, input_path: str, output_path: str
    ) -> Dict[str, Any]:
        """Simple model conversion fallback"""
        try:
            import shutil

            # For now, just copy the file
            shutil.copy2(input_path, output_path)

            return {
                "success": True,
                "converted_path": output_path,
                "metadata": {"conversion_type": "fallback_model"},
            }
        except Exception as e:
            return {"success": False, "error": f"Model conversion failed: {str(e)}"}

    async def _fallback_copy_conversion(
        self, input_path: str, output_path: str
    ) -> Dict[str, Any]:
        """Simple copy fallback for unknown asset types"""
        try:
            import shutil

            shutil.copy2(input_path, output_path)

            return {
                "success": True,
                "converted_path": output_path,
                "metadata": {"conversion_type": "fallback_copy"},
            }
        except Exception as e:
            return {"success": False, "error": f"Copy conversion failed: {str(e)}"}


# Global service instance
asset_conversion_service = AssetConversionService()
