import pytest
import pytest_asyncio
import uuid
import zipfile
import io
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from db import crud
from api.behavior_export import export_behavior_pack, ExportRequest

@pytest_asyncio.fixture
async def sample_conversion_job(db_session: AsyncSession):
    """Create a sample conversion job for testing."""
    job = await crud.create_job(
        db_session,
        file_id=str(uuid.uuid4()),
        original_filename="test_mod.jar",
        target_version="1.20.0",
        options={}
    )
    yield job
    # Cleanup is handled by transaction rollback in db_session fixture

@pytest.mark.asyncio
class TestBehaviorFilesSecurity:
    """Test security aspects of behavior files."""

    async def test_create_behavior_file_path_traversal(self, db_session: AsyncSession, sample_conversion_job):
        """Test that creating a behavior file with path traversal fails."""
        malicious_paths = [
            "../evil.json",
            "../../etc/passwd",
            "folder/../evil.json",
            "/absolute/path.json",
            "\\absolute\\windows\\path.json"
        ]

        for path in malicious_paths:
            with pytest.raises(ValueError, match="Invalid file path"):
                await crud.create_behavior_file(
                    db_session,
                    conversion_id=str(sample_conversion_job.id),
                    file_path=path,
                    file_type="script",
                    content="{}"
                )

    async def test_create_behavior_file_valid_paths(self, db_session: AsyncSession, sample_conversion_job):
        """Test that creating a behavior file with valid paths succeeds."""
        valid_paths = [
            "valid.json",
            "folder/valid.json",
            "folder/subfolder/valid.json",
            "file-with-dashes.json",
            "file_with_underscores.json"
        ]

        for path in valid_paths:
            file = await crud.create_behavior_file(
                db_session,
                conversion_id=str(sample_conversion_job.id),
                file_path=path,
                file_type="script",
                content="{}"
            )
            assert file.file_path == path

    async def test_export_zip_sanitization(self, db_session: AsyncSession, sample_conversion_job, mocker):
        """Test that zip export sanitizes paths."""

        # Mock behavior file object
        MockBehaviorFile = type('BehaviorFile', (), {})
        malicious_file = MockBehaviorFile()
        malicious_file.file_path = "../../evil.sh"
        malicious_file.content = "echo pwned"
        malicious_file.file_type = "script"
        malicious_file.created_at = datetime.now()
        malicious_file.updated_at = datetime.now()

        # Mock dependencies using AsyncMock because these functions are awaited
        from unittest.mock import AsyncMock

        mocker.patch('db.crud.get_behavior_files_by_conversion', side_effect=AsyncMock(return_value=[malicious_file]))
        mocker.patch('db.crud.get_job', side_effect=AsyncMock(return_value=sample_conversion_job))
        mocker.patch('db.crud.get_addon_details', side_effect=AsyncMock(return_value=None), create=True)

        # Mock CacheService.set_export_data
        mock_set = mocker.patch('services.cache.CacheService.set_export_data', side_effect=AsyncMock(return_value=True))

        # Execute export
        request = ExportRequest(
            conversion_id=str(sample_conversion_job.id),
            export_format="zip",
            include_templates=False
        )

        await export_behavior_pack(request, db_session)

        # Verify zip content passed to cache
        assert mock_set.called
        zip_content = mock_set.call_args[0][1]

        # Verify zip content
        with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zf:
            names = zf.namelist()
            # The path "../../evil.sh" should be sanitized to "evil.sh"
            assert "evil.sh" in names
            assert "../../evil.sh" not in names
            print(f"Sanitized paths in zip: {names}")
