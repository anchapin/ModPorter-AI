import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import uuid
from datetime import datetime
from io import BytesIO

from src.api.behavior_export import export_behavior_pack, download_exported_pack, preview_export, get_export_formats, ExportRequest

# Mock data
CONVERSION_ID = str(uuid.uuid4())
PACK_CONTENT = b"pack_content"

class MockBehaviorFile:
    def __init__(self, file_path, file_type, content):
        self.file_path = file_path
        self.file_type = file_type
        self.content = content
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

def create_mock_db_session(files_to_return=None):
    """Creates a mock DB session that handles the .execute().scalars().all() chain."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = files_to_return or []
    mock_result.scalars.return_value = mock_scalars

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result
    return mock_session

@pytest.mark.asyncio
@patch("src.api.behavior_export.CacheService")
@patch("src.api.behavior_export.addon_exporter.create_mcaddon_zip")
@patch("src.api.behavior_export.crud.get_behavior_files_by_conversion", new_callable=AsyncMock)
@patch("src.api.behavior_export.crud.get_job", new_callable=AsyncMock)
async def test_export_behavior_pack_direct_call(
    mock_get_job, mock_get_files, mock_create_zip, MockCacheService
):
    """Test the export_behavior_pack function with proper mocking."""
    # Setup mocks
    mock_job = MagicMock()
    mock_job.status = "completed"
    mock_job.name = "Test Addon" # Add name attribute for fallback
    mock_job.description = "A test addon" # Add description attribute for fallback
    mock_get_job.return_value = mock_job
    mock_files = [MockBehaviorFile("path1", "type1", "content1")]
    mock_get_files.return_value = mock_files

    zip_buffer = BytesIO(PACK_CONTENT)
    zip_buffer.seek(0)
    mock_create_zip.return_value = zip_buffer

    mock_cache_instance = MockCacheService.return_value
    mock_cache_instance.set_export_data = AsyncMock()

    mock_db_session = create_mock_db_session(files_to_return=mock_files)

    # Prepare request and call function
    request = ExportRequest(conversion_id=CONVERSION_ID, export_format="mcaddon")
    response = await export_behavior_pack(request, db=mock_db_session)

    # Assertions
    assert response.conversion_id == CONVERSION_ID
    assert response.export_format == "mcaddon"
    mock_cache_instance.set_export_data.assert_called_once()

@pytest.mark.asyncio
@patch("src.api.behavior_export.CacheService")
@patch("src.api.behavior_export.crud.get_job", new_callable=AsyncMock)
async def test_download_exported_pack_direct_call(mock_get_job, MockCacheService):
    """Test the download_exported_pack function."""
    # Setup mocks
    mock_cache_instance = MockCacheService.return_value
    mock_cache_instance.get_export_data.return_value = AsyncMock(return_value=PACK_CONTENT)()
    mock_get_job.return_value = MagicMock(status="completed")
    mock_db_session = create_mock_db_session()

    # Call function
    response = await download_exported_pack(conversion_id=CONVERSION_ID, db=mock_db_session)

    # Assertions
    assert response.status_code == 200
    # To read the content from a StreamingResponse, you need to iterate over its body
    content = [chunk async for chunk in response.body_iterator]
    assert b"".join(content) == PACK_CONTENT


@pytest.mark.asyncio
async def test_get_export_formats_direct_call():
    """Test the get_export_formats function."""
    response = await get_export_formats()
    assert isinstance(response, list)
    assert "mcaddon" in [fmt["format"] for fmt in response]

@pytest.mark.asyncio
@patch("src.api.behavior_export.crud.get_behavior_files_by_conversion", new_callable=AsyncMock)
@patch("src.api.behavior_export.crud.get_job", new_callable=AsyncMock)
async def test_preview_export_direct_call(mock_get_job, mock_get_files):
    """Test the preview_export function."""
    # Setup mocks
    mock_get_job.return_value = MagicMock(status="completed")
    mock_files = [
        MockBehaviorFile("path1", "type1", '{"_template_info": {"template_name": "t1"}}')
    ]
    mock_get_files.return_value = mock_files
    mock_db_session = create_mock_db_session(files_to_return=mock_files)

    # Call function
    response = await preview_export(conversion_id=CONVERSION_ID, db=mock_db_session)

    # Assertions
    assert response["conversion_id"] == CONVERSION_ID
    assert response["analysis"]["total_files"] == 1
