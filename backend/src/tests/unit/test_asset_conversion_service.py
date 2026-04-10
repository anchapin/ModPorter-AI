import pytest
import httpx
from unittest.mock import MagicMock, patch, AsyncMock
from services.asset_conversion_service import AssetConversionService


class TestAssetConversionService:
    @pytest.fixture
    def service(self):
        return AssetConversionService()

    @pytest.fixture
    def mock_asset(self):
        asset = MagicMock()
        asset.id = "asset123"
        asset.asset_type = "texture"
        asset.original_path = "original.png"
        asset.original_filename = "original.png"
        return asset

    @pytest.mark.asyncio
    async def test_convert_asset_success(self, service, mock_asset):
        mock_session = AsyncMock()
        mock_session_context = MagicMock()
        mock_session_context.__aenter__.return_value = mock_session

        with (
            patch(
                "services.asset_conversion_service.AsyncSessionLocal",
                return_value=mock_session_context,
            ),
            patch("services.asset_conversion_service.crud", new_callable=MagicMock) as mock_crud,
            patch.object(
                service, "_call_ai_engine_convert_asset", new_callable=AsyncMock
            ) as mock_ai_call,
        ):
            mock_crud.get_asset = AsyncMock(return_value=mock_asset)
            mock_crud.update_asset_status = AsyncMock()
            mock_ai_call.return_value = {"success": True, "converted_path": "converted.png"}

            result = await service.convert_asset("asset123")

            assert result["success"] is True
            assert result["converted_path"] == "converted.png"
            mock_crud.update_asset_status.assert_any_call(mock_session, "asset123", "processing")
            mock_crud.update_asset_status.assert_any_call(
                mock_session, "asset123", "converted", converted_path="converted.png"
            )

    @pytest.mark.asyncio
    async def test_convert_asset_not_found(self, service):
        mock_session = AsyncMock()
        mock_session_context = MagicMock()
        mock_session_context.__aenter__.return_value = mock_session

        with (
            patch(
                "services.asset_conversion_service.AsyncSessionLocal",
                return_value=mock_session_context,
            ),
            patch("services.asset_conversion_service.crud", new_callable=MagicMock) as mock_crud,
        ):
            mock_crud.get_asset = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="Asset asset123 not found"):
                await service.convert_asset("asset123")

    @pytest.mark.asyncio
    async def test_convert_assets_for_conversion(self, service, mock_asset):
        mock_session = AsyncMock()
        mock_session_context = MagicMock()
        mock_session_context.__aenter__.return_value = mock_session

        with (
            patch(
                "services.asset_conversion_service.AsyncSessionLocal",
                return_value=mock_session_context,
            ),
            patch("services.asset_conversion_service.crud", new_callable=MagicMock) as mock_crud,
            patch.object(service, "convert_asset", new_callable=AsyncMock) as mock_convert,
        ):
            mock_crud.list_assets_for_conversion = AsyncMock(return_value=[mock_asset, mock_asset])
            mock_convert.return_value = {"success": True}

            result = await service.convert_assets_for_conversion("job123")

            assert result["success"] is True
            assert result["total_assets"] == 2
            assert result["converted_count"] == 2

    @pytest.mark.asyncio
    async def test_call_ai_engine_convert_asset_success(self, service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"converted_path": "ai_converted.png", "metadata": {}}

        with (
            patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
            patch("os.makedirs"),
        ):
            mock_post.return_value = mock_response

            result = await service._call_ai_engine_convert_asset(
                "a1", "texture", "in.png", "orig.png"
            )

            assert result["success"] is True
            assert result["converted_path"] == "ai_converted.png"

    @pytest.mark.asyncio
    async def test_fallback_texture_conversion(self, service):
        # Mock PIL.Image.open and shutil at global level since they're imported locally in the function
        mock_image = MagicMock()
        mock_image.save = MagicMock()

        import PIL.Image

        original_open = PIL.Image.open

        def mock_open(path):
            return mock_image

        mock_image_instance = MagicMock()
        mock_image_instance.__enter__ = MagicMock(return_value=mock_image)
        mock_image_instance.__aexit__ = MagicMock(return_value=None)
        mock_image_instance.save = MagicMock()

        PIL.Image.open = MagicMock(return_value=mock_image_instance)

        import shutil

        original_copy2 = shutil.copy2
        shutil.copy2 = MagicMock()

        try:
            result = await service._fallback_texture_conversion("in.png", "out.png")
            assert result["success"] is True
        finally:
            PIL.Image.open = original_open
            shutil.copy2 = original_copy2

    @pytest.mark.asyncio
    async def test_fallback_sound_conversion(self, service):
        with patch("shutil.copy2") as mock_copy:
            result = await service._fallback_sound_conversion("in.ogg", "out.ogg")
            assert result["success"] is True
            mock_copy.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
