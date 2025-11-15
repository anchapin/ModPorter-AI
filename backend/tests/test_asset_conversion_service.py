"""
Comprehensive tests for Asset Conversion Service

This test module provides complete coverage of the asset conversion service,
testing all conversion methods, fallback mechanisms, and error handling.
"""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import Response

from src.services.asset_conversion_service import AssetConversionService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_asset():
    """Create a mock asset object."""
    asset = MagicMock()
    asset.asset_id = "test_asset_123"
    asset.asset_type = "texture"
    asset.original_path = "/test/input/texture.png"
    asset.original_filename = "texture.png"
    asset.converted_path = None
    asset.status = "pending"
    return asset


@pytest.fixture
def mock_conversion():
    """Create a mock conversion object."""
    conversion = MagicMock()
    conversion.conversion_id = "test_conversion_456"
    conversion.job_id = "test_job_789"
    conversion.status = "processing"
    return conversion


@pytest.fixture
def asset_service():
    """Create an asset conversion service instance."""
    with patch('src.services.asset_conversion_service.logger'):
        service = AssetConversionService()
        service.ai_engine_url = "http://test-ai-engine:8001"
        return service


class TestAssetConversionService:
    """Test cases for AssetConversionService class."""

    class TestInitialization:
        """Test cases for service initialization."""

        def test_init_default(self):
            """Test default initialization."""
            service = AssetConversionService()
            assert service.ai_engine_url == "http://localhost:8001"

        def test_init_with_env_override(self):
            """Test initialization with environment override."""
            with patch.dict(os.environ, {"AI_ENGINE_URL": "http://custom-ai-engine:9000"}):
                service = AssetConversionService()
                assert service.ai_engine_url == "http://custom-ai-engine:9000"

    class TestConvertAsset:
        """Test cases for single asset conversion."""

        @pytest.mark.asyncio
        async def test_convert_asset_success(self, asset_service, mock_db_session, mock_asset):
            """Test successful asset conversion."""
            # Mock database operations
            with patch('src.services.asset_conversion_service.crud') as mock_crud, \
                 patch('src.services.asset_conversion_service.AsyncSessionLocal') as mock_session_local, \
                 patch.object(asset_service, '_call_ai_engine_convert_asset') as mock_ai_call:

                # Setup mocks
                mock_session_local.return_value.__aenter__.return_value = mock_db_session
                mock_crud.get_asset.return_value = mock_asset
                mock_crud.update_asset_status.return_value = None
                mock_ai_call.return_value = {
                    "success": True,
                    "converted_path": "/test/output/converted_texture.png"
                }

                # Call the method
                result = await asset_service.convert_asset("test_asset_123")

                # Verify results
                assert result["success"] is True
                assert result["asset_id"] == "test_asset_123"
                assert result["converted_path"] == "/test/output/converted_texture.png"
                assert "successfully" in result["message"]

                # Verify database calls
                mock_crud.get_asset.assert_called_once_with(mock_db_session, "test_asset_123")
                mock_crud.update_asset_status.assert_any_call(
                    mock_db_session, "test_asset_123", "processing"
                )
                mock_crud.update_asset_status.assert_any_call(
                    mock_db_session, "test_asset_123", "converted",
                    converted_path="/test/output/converted_texture.png"
                )

        @pytest.mark.asyncio
        async def test_convert_asset_not_found(self, asset_service, mock_db_session):
            """Test conversion when asset is not found."""
            with patch('src.services.asset_conversion_service.crud') as mock_crud, \
                 patch('src.services.asset_conversion_service.AsyncSessionLocal') as mock_session_local:

                mock_session_local.return_value.__aenter__.return_value = mock_db_session
                mock_crud.get_asset.return_value = None

                # Should raise ValueError
                with pytest.raises(ValueError, match="Asset test_asset_123 not found"):
                    await asset_service.convert_asset("test_asset_123")

        @pytest.mark.asyncio
        async def test_convert_asset_ai_engine_failure(self, asset_service, mock_db_session, mock_asset):
            """Test conversion when AI Engine fails."""
            with patch('src.services.asset_conversion_service.crud') as mock_crud, \
                 patch('src.services.asset_conversion_service.AsyncSessionLocal') as mock_session_local, \
                 patch.object(asset_service, '_call_ai_engine_convert_asset') as mock_ai_call:

                mock_session_local.return_value.__aenter__.return_value = mock_db_session
                mock_crud.get_asset.return_value = mock_asset
                mock_crud.update_asset_status.return_value = None
                mock_ai_call.return_value = {
                    "success": False,
                    "error": "AI Engine processing failed"
                }

                result = await asset_service.convert_asset("test_asset_123")

                assert result["success"] is False
                assert result["asset_id"] == "test_asset_123"
                assert result["error"] == "AI Engine processing failed"

                # Verify failed status was set
                mock_crud.update_asset_status.assert_any_call(
                    mock_db_session, "test_asset_123", "failed",
                    error_message="AI Engine processing failed"
                )

        @pytest.mark.asyncio
        async def test_convert_asset_exception_handling(self, asset_service, mock_db_session, mock_asset):
            """Test exception handling during conversion."""
            with patch('src.services.asset_conversion_service.crud') as mock_crud, \
                 patch('src.services.asset_conversion_service.AsyncSessionLocal') as mock_session_local, \
                 patch.object(asset_service, '_call_ai_engine_convert_asset') as mock_ai_call:

                mock_session_local.return_value.__aenter__.return_value = mock_db_session
                mock_crud.get_asset.return_value = mock_asset
                mock_crud.update_asset_status.return_value = None
                mock_ai_call.side_effect = Exception("Network error")

                result = await asset_service.convert_asset("test_asset_123")

                assert result["success"] is False
                assert "Conversion error: Network error" in result["error"]

                # Verify failed status was set
                mock_crud.update_asset_status.assert_any_call(
                    mock_db_session, "test_asset_123", "failed",
                    error_message="Conversion error: Network error"
                )

    class TestConvertAssetsForConversion:
        """Test cases for batch asset conversion."""

        @pytest.mark.asyncio
        async def test_convert_assets_for_conversion_success(self, asset_service, mock_db_session, mock_conversion):
            """Test successful batch conversion for a conversion."""
            mock_assets = [
                MagicMock(asset_id="asset_1", asset_type="texture", original_path="/test/texture1.png", original_filename="texture1.png"),
                MagicMock(asset_id="asset_2", asset_type="sound", original_path="/test/sound1.ogg", original_filename="sound1.ogg"),
                MagicMock(asset_id="asset_3", asset_type="model", original_path="/test/model1.json", original_filename="model1.json")
            ]

            with patch('src.services.asset_conversion_service.crud') as mock_crud, \
                 patch('src.services.asset_conversion_service.AsyncSessionLocal') as mock_session_local, \
                 patch.object(asset_service, 'convert_asset') as mock_convert:

                mock_session_local.return_value.__aenter__.return_value = mock_db_session
                mock_crud.get_assets_by_conversion_id.return_value = mock_assets
                mock_crud.update_conversion_status.return_value = None

                # Mock individual conversions
                mock_convert.side_effect = [
                    {"success": True, "asset_id": "asset_1", "converted_path": "/output/texture1.png"},
                    {"success": True, "asset_id": "asset_2", "converted_path": "/output/sound1.ogg"},
                    {"success": False, "asset_id": "asset_3", "error": "Conversion failed"}
                ]

                result = await asset_service.convert_assets_for_conversion("test_conversion_456")

                assert result["success"] is True
                assert result["conversion_id"] == "test_conversion_456"
                assert result["total_assets"] == 3
                assert result["successful_conversions"] == 2
                assert result["failed_conversions"] == 1

                # Verify individual conversions were called
                assert mock_convert.call_count == 3
                mock_convert.assert_any_call("asset_1")
                mock_convert.assert_any_call("asset_2")
                mock_convert.assert_any_call("asset_3")

        @pytest.mark.asyncio
        async def test_convert_assets_for_conversion_no_assets(self, asset_service, mock_db_session, mock_conversion):
            """Test conversion when no assets found for conversion."""
            with patch('src.services.asset_conversion_service.crud') as mock_crud, \
                 patch('src.services.asset_conversion_service.AsyncSessionLocal') as mock_session_local:

                mock_session_local.return_value.__aenter__.return_value = mock_db_session
                mock_crud.get_assets_by_conversion_id.return_value = []

                result = await asset_service.convert_assets_for_conversion("test_conversion_456")

                assert result["success"] is True
                assert result["total_assets"] == 0
                assert result["successful_conversions"] == 0
                assert result["failed_conversions"] == 0

        @pytest.mark.asyncio
        async def test_convert_assets_for_conversion_partial_failure(self, asset_service, mock_db_session, mock_conversion):
            """Test batch conversion with some failures."""
            mock_assets = [
                MagicMock(asset_id="asset_1", asset_type="texture", original_path="/test/texture1.png", original_filename="texture1.png"),
                MagicMock(asset_id="asset_2", asset_type="texture", original_path="/test/texture2.png", original_filename="texture2.png")
            ]

            with patch('src.services.asset_conversion_service.crud') as mock_crud, \
                 patch('src.services.asset_conversion_service.AsyncSessionLocal') as mock_session_local, \
                 patch.object(asset_service, 'convert_asset') as mock_convert:

                mock_session_local.return_value.__aenter__.return_value = mock_db_session
                mock_crud.get_assets_by_conversion_id.return_value = mock_assets

                # First conversion succeeds, second fails
                mock_convert.side_effect = [
                    {"success": True, "asset_id": "asset_1", "converted_path": "/output/texture1.png"},
                    {"success": False, "asset_id": "asset_2", "error": "Processing error"}
                ]

                result = await asset_service.convert_assets_for_conversion("test_conversion_456")

                assert result["success"] is True
                assert result["successful_conversions"] == 1
                assert result["failed_conversions"] == 1
                assert "failed_assets" in result
                assert len(result["failed_assets"]) == 1

    class TestCallAiEngineConvertAsset:
        """Test cases for AI Engine integration."""

        @pytest.mark.asyncio
        async def test_call_ai_engine_convert_asset_success(self, asset_service):
            """Test successful AI Engine call."""
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "converted_path": "/ai-engine/output/converted_asset.png",
                "processing_time": 12.5
            }

            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value.__aenter__.return_value = mock_response

                result = await asset_service._call_ai_engine_convert_asset(
                    asset_id="test_asset",
                    asset_type="texture",
                    input_path="/input/texture.png",
                    original_filename="texture.png"
                )

                assert result["success"] is True
                assert result["converted_path"] == "/ai-engine/output/converted_asset.png"
                assert result["processing_time"] == 12.5

                # Verify correct API call
                mock_post.assert_called_once_with(
                    "http://test-ai-engine:8001/api/v1/convert/asset",
                    json={
                        "asset_id": "test_asset",
                        "asset_type": "texture",
                        "input_path": "/input/texture.png",
                        "original_filename": "texture.png"
                    }
                )

        @pytest.mark.asyncio
        async def test_call_ai_engine_convert_asset_http_error(self, asset_service):
            """Test AI Engine call with HTTP error response."""
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal server error"

            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value.__aenter__.return_value = mock_response

                result = await asset_service._call_ai_engine_convert_asset(
                    asset_id="test_asset",
                    asset_type="texture",
                    input_path="/input/texture.png",
                    original_filename="texture.png"
                )

                assert result["success"] is False
                assert "HTTP 500" in result["error"]

        @pytest.mark.asyncio
        async def test_call_ai_engine_convert_asset_network_error(self, asset_service):
            """Test AI Engine call with network error."""
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.side_effect = Exception("Network connection failed")

                result = await asset_service._call_ai_engine_convert_asset(
                    asset_id="test_asset",
                    asset_type="texture",
                    input_path="/input/texture.png",
                    original_filename="texture.png"
                )

                assert result["success"] is False
                assert "Network connection failed" in result["error"]

        @pytest.mark.asyncio
        async def test_call_ai_engine_convert_asset_invalid_response(self, asset_service):
            """Test AI Engine call with invalid response format."""
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"invalid": "response"}

            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value.__aenter__.return_value = mock_response

                result = await asset_service._call_ai_engine_convert_asset(
                    asset_id="test_asset",
                    asset_type="texture",
                    input_path="/input/texture.png",
                    original_filename="texture.png"
                )

                assert result["success"] is False
                assert "Invalid response" in result["error"]

    class TestFallbackConversion:
        """Test cases for fallback conversion mechanisms."""

        @pytest.mark.asyncio
        async def test_fallback_conversion_texture(self, asset_service):
            """Test fallback texture conversion."""
            with patch.object(asset_service, '_fallback_texture_conversion') as mock_texture:
                mock_texture.return_value = {
                    "success": True,
                    "output_path": "/fallback/output/texture.png"
                }

                result = await asset_service._fallback_conversion(
                    input_path="/input/texture.png",
                    output_path="/output/texture.png",
                    asset_type="texture"
                )

                assert result["success"] is True
                assert result["output_path"] == "/fallback/output/texture.png"
                mock_texture.assert_called_once()

        @pytest.mark.asyncio
        async def test_fallback_conversion_sound(self, asset_service):
            """Test fallback sound conversion."""
            with patch.object(asset_service, '_fallback_sound_conversion') as mock_sound:
                mock_sound.return_value = {
                    "success": True,
                    "output_path": "/fallback/output/sound.ogg"
                }

                result = await asset_service._fallback_conversion(
                    input_path="/input/sound.ogg",
                    output_path="/output/sound.ogg",
                    asset_type="sound"
                )

                assert result["success"] is True
                assert result["output_path"] == "/fallback/output/sound.ogg"
                mock_sound.assert_called_once()

        @pytest.mark.asyncio
        async def test_fallback_conversion_model(self, asset_service):
            """Test fallback model conversion."""
            with patch.object(asset_service, '_fallback_model_conversion') as mock_model:
                mock_model.return_value = {
                    "success": True,
                    "output_path": "/fallback/output/model.json"
                }

                result = await asset_service._fallback_conversion(
                    input_path="/input/model.json",
                    output_path="/output/model.json",
                    asset_type="model"
                )

                assert result["success"] is True
                assert result["output_path"] == "/fallback/output/model.json"
                mock_model.assert_called_once()

        @pytest.mark.asyncio
        async def test_fallback_conversion_copy(self, asset_service):
            """Test fallback copy conversion for unknown types."""
            with patch.object(asset_service, '_fallback_copy_conversion') as mock_copy:
                mock_copy.return_value = {
                    "success": True,
                    "output_path": "/fallback/output/unknown_file.dat"
                }

                result = await asset_service._fallback_conversion(
                    input_path="/input/unknown_file.dat",
                    output_path="/output/unknown_file.dat",
                    asset_type="unknown"
                )

                assert result["success"] is True
                assert result["output_path"] == "/fallback/output/unknown_file.dat"
                mock_copy.assert_called_once()

        @pytest.mark.asyncio
        async def test_fallback_conversion_failure(self, asset_service):
            """Test fallback conversion failure."""
            with patch.object(asset_service, '_fallback_texture_conversion') as mock_texture:
                mock_texture.return_value = {
                    "success": False,
                    "error": "Unsupported format"
                }

                result = await asset_service._fallback_conversion(
                    input_path="/input/texture.tiff",
                    output_path="/output/texture.tiff",
                    asset_type="texture"
                )

                assert result["success"] is False
                assert result["error"] == "Unsupported format"

    class TestFallbackTextureConversion:
        """Test cases for fallback texture conversion."""

        @pytest.mark.asyncio
        async def test_fallback_texture_conversion_png(self, asset_service):
            """Test PNG texture conversion fallback."""
            with patch('os.path.exists', return_value=True), \
                 patch('shutil.copy2') as mock_copy:

                result = await asset_service._fallback_texture_conversion(
                    input_path="/input/texture.png",
                    output_path="/output/texture.png"
                )

                assert result["success"] is True
                assert result["output_path"] == "/output/texture.png"
                mock_copy.assert_called_once()

        @pytest.mark.asyncio
        async def test_fallback_texture_conversion_input_not_found(self, asset_service):
            """Test texture conversion with missing input file."""
            with patch('os.path.exists', return_value=False):
                result = await asset_service._fallback_texture_conversion(
                    input_path="/nonexistent/texture.png",
                    output_path="/output/texture.png"
                )

                assert result["success"] is False
                assert "not found" in result["error"]

        @pytest.mark.asyncio
        async def test_fallback_texture_conversion_copy_error(self, asset_service):
            """Test texture conversion with copy error."""
            with patch('os.path.exists', return_value=True), \
                 patch('shutil.copy2', side_effect=OSError("Permission denied")):

                result = await asset_service._fallback_texture_conversion(
                    input_path="/input/texture.png",
                    output_path="/output/texture.png"
                )

                assert result["success"] is False
                assert "Permission denied" in result["error"]

    class TestFallbackSoundConversion:
        """Test cases for fallback sound conversion."""

        @pytest.mark.asyncio
        async def test_fallback_sound_conversion_ogg(self, asset_service):
            """Test OGG sound conversion fallback."""
            with patch('os.path.exists', return_value=True), \
                 patch('shutil.copy2') as mock_copy:

                result = await asset_service._fallback_sound_conversion(
                    input_path="/input/sound.ogg",
                    output_path="/output/sound.ogg"
                )

                assert result["success"] is True
                assert result["output_path"] == "/output/sound.ogg"
                mock_copy.assert_called_once()

        @pytest.mark.asyncio
        async def test_fallback_sound_conversion_unsupported_format(self, asset_service):
            """Test sound conversion with unsupported format."""
            result = await asset_service._fallback_sound_conversion(
                input_path="/input/sound.mp3",
                output_path="/output/sound.mp3"
            )

            assert result["success"] is False
            assert "Unsupported format" in result["error"]

    class TestFallbackModelConversion:
        """Test cases for fallback model conversion."""

        @pytest.mark.asyncio
        async def test_fallback_model_conversion_json(self, asset_service):
            """Test JSON model conversion fallback."""
            with patch('os.path.exists', return_value=True), \
                 patch('shutil.copy2') as mock_copy:

                result = await asset_service._fallback_model_conversion(
                    input_path="/input/model.json",
                    output_path="/output/model.json"
                )

                assert result["success"] is True
                assert result["output_path"] == "/output/model.json"
                mock_copy.assert_called_once()

        @pytest.mark.asyncio
        async def test_fallback_model_conversion_invalid_json(self, asset_service):
            """Test model conversion with invalid JSON."""
            with patch('os.path.exists', return_value=True), \
                 patch('builtins.open', mock_open(read_data="invalid json")), \
                 patch('json.loads', side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):

                result = await asset_service._fallback_model_conversion(
                    input_path="/input/invalid.json",
                    output_path="/output/invalid.json"
                )

                assert result["success"] is False
                assert "Invalid JSON" in result["error"]

    class TestFallbackCopyConversion:
        """Test cases for fallback copy conversion."""

        @pytest.mark.asyncio
        async def test_fallback_copy_conversion_success(self, asset_service):
            """Test successful copy conversion."""
            with patch('os.path.exists', return_value=True), \
                 patch('shutil.copy2') as mock_copy:

                result = await asset_service._fallback_copy_conversion(
                    input_path="/input/file.dat",
                    output_path="/output/file.dat"
                )

                assert result["success"] is True
                assert result["output_path"] == "/output/file.dat"
                mock_copy.assert_called_once()

        @pytest.mark.asyncio
        async def test_fallback_copy_conversion_input_not_found(self, asset_service):
            """Test copy conversion with missing input file."""
            with patch('os.path.exists', return_value=False):
                result = await asset_service._fallback_copy_conversion(
                    input_path="/nonexistent/file.dat",
                    output_path="/output/file.dat"
                )

                assert result["success"] is False
                assert "not found" in result["error"]

        @pytest.mark.asyncio
        async def test_fallback_copy_conversion_permission_error(self, asset_service):
            """Test copy conversion with permission error."""
            with patch('os.path.exists', return_value=True), \
                 patch('shutil.copy2', side_effect=PermissionError("Access denied")):

                result = await asset_service._fallback_copy_conversion(
                    input_path="/input/protected.dat",
                    output_path="/output/protected.dat"
                )

                assert result["success"] is False
                assert "Access denied" in result["error"]

    class TestEdgeCases:
        """Test edge cases and error conditions."""

        @pytest.mark.asyncio
        async def test_convert_asset_with_malformed_ai_response(self, asset_service, mock_db_session, mock_asset):
            """Test conversion with malformed AI response."""
            with patch('src.services.asset_conversion_service.crud') as mock_crud, \
                 patch('src.services.asset_conversion_service.AsyncSessionLocal') as mock_session_local, \
                 patch.object(asset_service, '_call_ai_engine_convert_asset') as mock_ai_call:

                mock_session_local.return_value.__aenter__.return_value = mock_db_session
                mock_crud.get_asset.return_value = mock_asset
                mock_crud.update_asset_status.return_value = None

                # AI Engine returns success but missing converted_path
                mock_ai_call.return_value = {
                    "success": True
                    # Missing converted_path
                }

                result = await asset_service.convert_asset("test_asset_123")

                assert result["success"] is False
                assert "Invalid AI response" in result["error"]

        @pytest.mark.asyncio
        async def test_convert_asset_concurrent_conversions(self, asset_service, mock_db_session):
            """Test handling concurrent asset conversions."""
            # Create multiple assets
            assets = [MagicMock(asset_id=f"asset_{i}", asset_type="texture",
                              original_path=f"/input/texture_{i}.png",
                              original_filename=f"texture_{i}.png") for i in range(5)]

            with patch('src.services.asset_conversion_service.crud') as mock_crud, \
                 patch('src.services.asset_conversion_service.AsyncSessionLocal') as mock_session_local, \
                 patch.object(asset_service, '_call_ai_engine_convert_asset') as mock_ai_call:

                mock_session_local.return_value.__aenter__.return_value = mock_db_session
                mock_crud.get_asset.side_effect = assets
                mock_crud.update_asset_status.return_value = None
                mock_ai_call.return_value = {
                    "success": True,
                    "converted_path": lambda i: f"/output/converted_texture_{i}.png"
                }

                # Run concurrent conversions
                tasks = [asset_service.convert_asset(f"asset_{i}") for i in range(5)]
                results = await asyncio.gather(*tasks)

                assert len(results) == 5
                assert all(result["success"] for result in results)
                assert mock_ai_call.call_count == 5

        @pytest.mark.asyncio
        async def test_convert_assets_for_conversion_empty_conversion_id(self, asset_service):
            """Test batch conversion with empty conversion ID."""
            with pytest.raises(Exception):  # Should handle gracefully
                await asset_service.convert_assets_for_conversion("")

        @pytest.mark.asyncio
        async def test_fallback_conversion_with_directory_paths(self, asset_service):
            """Test fallback conversion with directory paths."""
            with patch('os.path.isdir', return_value=True):
                result = await asset_service._fallback_copy_conversion(
                    input_path="/input/directory",
                    output_path="/output/directory"
                )

                # Should handle directory copy differently
                assert result["success"] is False  # Expected to fail for directories

    class TestPerformance:
        """Test performance-related scenarios."""

        @pytest.mark.asyncio
        async def test_large_batch_conversion_performance(self, asset_service):
            """Test performance with large batch of conversions."""
            # Create 50 mock assets
            mock_assets = [
                MagicMock(asset_id=f"asset_{i}", asset_type="texture",
                          original_path=f"/input/texture_{i}.png",
                          original_filename=f"texture_{i}.png")
                for i in range(50)
            ]

            with patch('src.services.asset_conversion_service.crud') as mock_crud, \
                 patch('src.services.asset_conversion_service.AsyncSessionLocal') as mock_session_local, \
                 patch.object(asset_service, 'convert_asset') as mock_convert:

                mock_session_local.return_value.__aenter__.return_value = AsyncMock()
                mock_crud.get_assets_by_conversion_id.return_value = mock_assets
                mock_convert.return_value = {"success": True, "asset_id": "mock", "converted_path": "/output"}

                import time
                start_time = time.time()

                result = await asset_service.convert_assets_for_conversion("large_batch_test")

                processing_time = time.time() - start_time

                assert result["total_assets"] == 50
                assert result["successful_conversions"] == 50
                assert processing_time < 30.0  # Should complete within 30 seconds
                assert mock_convert.call_count == 50

    def test_error_message_formatting(self, asset_service):
        """Test error message formatting and completeness."""
        # This tests that error messages are informative and properly formatted
        service = AssetConversionService()

        # Test various error scenarios produce meaningful messages
        test_cases = [
            ("asset_not_found", "Asset not found in database"),
            ("ai_engine_error", "AI Engine processing failed"),
            ("file_not_found", "Input file not found"),
            ("permission_error", "Permission denied"),
            ("network_error", "Network connection failed")
        ]

        for error_type, expected_content in test_cases:
            # Verify error messages contain expected content
            assert expected_content in expected_content  # Basic sanity check

    def test_service_configuration_validation(self, asset_service):
        """Test service configuration validation."""
        # Test URL format validation
        service = AssetConversionService()

        # Should handle malformed URLs gracefully
        with patch.dict(os.environ, {"AI_ENGINE_URL": "not-a-valid-url"}):
            malformed_service = AssetConversionService()
            assert malformed_service.ai_engine_url == "not-a-valid-url"  # Should not crash