"""
Comprehensive tests for Result Storage Service.

Tests the services/result_storage.py module covering:
- ResultStorage class initialization
- store_result: storing bedrock code and metadata
- get_result: retrieving result by ID
- download_result: getting file path for download
- cleanup_expired_results: removing old results from DB and filesystem
- get_storage_stats: reporting storage statistics
- get_result_storage: singleton factory function
"""

import os
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open, call


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dirs(tmp_path):
    """Return (temp_dir, output_dir) paths that actually exist."""
    temp_dir = tmp_path / "uploads"
    output_dir = tmp_path / "outputs"
    temp_dir.mkdir()
    output_dir.mkdir()
    return temp_dir, output_dir


@pytest.fixture
def storage(tmp_dirs):
    """Create a ResultStorage instance backed by real temporary directories."""
    temp_dir, output_dir = tmp_dirs
    with (
        patch("services.result_storage.TEMP_UPLOADS_DIR", temp_dir),
        patch("services.result_storage.CONVERSION_OUTPUTS_DIR", output_dir),
    ):
        from services.result_storage import ResultStorage

        return ResultStorage()


@pytest.fixture
def mock_db():
    """Async mock for SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# TestResultStorageInit
# ---------------------------------------------------------------------------


class TestResultStorageInit:
    """Tests for ResultStorage.__init__."""

    def test_init_creates_directories(self, tmp_path):
        """Directories are created on initialization if they don't exist."""
        temp_dir = tmp_path / "new_uploads"
        output_dir = tmp_path / "new_outputs"

        with (
            patch("services.result_storage.TEMP_UPLOADS_DIR", temp_dir),
            patch("services.result_storage.CONVERSION_OUTPUTS_DIR", output_dir),
        ):
            from services.result_storage import ResultStorage

            rs = ResultStorage()

        assert temp_dir.exists()
        assert output_dir.exists()
        assert rs.temp_dir == temp_dir
        assert rs.output_dir == output_dir

    def test_init_existing_directories(self, tmp_dirs):
        """Initialization succeeds when directories already exist."""
        temp_dir, output_dir = tmp_dirs
        with (
            patch("services.result_storage.TEMP_UPLOADS_DIR", temp_dir),
            patch("services.result_storage.CONVERSION_OUTPUTS_DIR", output_dir),
        ):
            from services.result_storage import ResultStorage

            rs = ResultStorage()

        assert rs.temp_dir == temp_dir
        assert rs.output_dir == output_dir

    def test_constants(self):
        """Module-level constants are defined with expected values."""
        from services.result_storage import (
            RESULT_EXPIRY_DAYS,
            TEMP_UPLOADS_DIR,
            CONVERSION_OUTPUTS_DIR,
        )

        assert RESULT_EXPIRY_DAYS == 30
        assert isinstance(TEMP_UPLOADS_DIR, Path)
        assert isinstance(CONVERSION_OUTPUTS_DIR, Path)


# ---------------------------------------------------------------------------
# TestStoreResult
# ---------------------------------------------------------------------------


class TestStoreResult:
    """Tests for ResultStorage.store_result."""

    @pytest.mark.asyncio
    async def test_store_result_creates_file_and_db_record(self, storage, mock_db, tmp_dirs):
        """store_result writes the .mcaddon file and creates a DB record."""
        _, output_dir = tmp_dirs

        mock_job = MagicMock()
        mock_job.status = "queued"
        mock_db.get = AsyncMock(return_value=mock_job)

        result_id = await storage.store_result(
            job_id="job-111",
            user_id="user-222",
            bedrock_code="// Bedrock addon code",
            result_metadata={"version": "1.20"},
            db=mock_db,
        )

        assert result_id is not None
        assert isinstance(result_id, str)

        # File should have been written
        output_file = output_dir / f"{result_id}.mcaddon"
        assert output_file.exists()
        assert output_file.read_text() == "// Bedrock addon code"

        # DB operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        assert mock_job.status == "completed"

    @pytest.mark.asyncio
    async def test_store_result_no_matching_job(self, storage, mock_db):
        """store_result works even when job is not found in DB (no status update)."""
        mock_db.get = AsyncMock(return_value=None)

        result_id = await storage.store_result(
            job_id="ghost-job",
            user_id=None,
            bedrock_code="code",
            result_metadata={},
            db=mock_db,
        )

        assert result_id is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_store_result_with_none_user_id(self, storage, mock_db):
        """store_result accepts user_id=None."""
        mock_db.get = AsyncMock(return_value=None)

        result_id = await storage.store_result(
            job_id="job-abc",
            user_id=None,
            bedrock_code="",
            result_metadata={},
            db=mock_db,
        )

        assert result_id is not None

    @pytest.mark.asyncio
    async def test_store_result_returns_uuid_string(self, storage, mock_db):
        """store_result returns a valid UUID string."""
        mock_db.get = AsyncMock(return_value=None)

        result_id = await storage.store_result(
            job_id="job-uuid",
            user_id="u1",
            bedrock_code="// code",
            result_metadata={},
            db=mock_db,
        )

        # Should be parseable as UUID
        parsed = uuid.UUID(result_id)
        assert str(parsed) == result_id

    @pytest.mark.asyncio
    async def test_store_result_db_record_has_correct_data(self, storage, mock_db):
        """The ConversionResult added to DB has expected output_data fields."""
        from db.models import ConversionResult

        mock_db.get = AsyncMock(return_value=None)
        added_obj = None

        def capture_add(obj):
            nonlocal added_obj
            added_obj = obj

        mock_db.add = MagicMock(side_effect=capture_add)

        result_id = await storage.store_result(
            job_id="job-data",
            user_id="user1",
            bedrock_code="my bedrock code",
            result_metadata={"key": "value"},
            db=mock_db,
        )

        assert added_obj is not None
        assert added_obj.job_id == "job-data"
        assert added_obj.output_data["metadata"] == {"key": "value"}
        assert added_obj.output_data["code_length"] == len("my bedrock code")
        assert ".mcaddon" in added_obj.output_data["output_file"]


# ---------------------------------------------------------------------------
# TestGetResult
# ---------------------------------------------------------------------------


class TestGetResult:
    """Tests for ResultStorage.get_result."""

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, storage, mock_db):
        """Returns None when result_id does not exist in DB."""
        mock_db.get = AsyncMock(return_value=None)

        result = await storage.get_result("nonexistent-id", mock_db)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_result_with_existing_file(self, storage, mock_db, tmp_dirs):
        """Returns result dict including bedrock code read from file."""
        _, output_dir = tmp_dirs
        result_id = str(uuid.uuid4())
        output_file = output_dir / f"{result_id}.mcaddon"
        output_file.write_text("// bedrock addon code")

        mock_result = MagicMock()
        mock_result.job_id = "job-999"
        mock_result.output_data = {
            "metadata": {"mod_version": "2.0"},
            "output_file": str(output_file),
        }
        mock_result.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        mock_db.get = AsyncMock(return_value=mock_result)

        data = await storage.get_result(result_id, mock_db)

        assert data is not None
        assert data["result_id"] == result_id
        assert data["job_id"] == "job-999"
        assert data["bedrock_code"] == "// bedrock addon code"
        assert data["metadata"] == {"mod_version": "2.0"}
        assert data["created_at"] is not None

    @pytest.mark.asyncio
    async def test_get_result_file_missing(self, storage, mock_db, tmp_dirs):
        """Returns empty bedrock_code when output file does not exist on disk."""
        _, output_dir = tmp_dirs
        result_id = str(uuid.uuid4())

        mock_result = MagicMock()
        mock_result.job_id = "job-888"
        mock_result.output_data = {
            "metadata": {},
            "output_file": str(output_dir / "nonexistent.mcaddon"),
        }
        mock_result.created_at = None
        mock_db.get = AsyncMock(return_value=mock_result)

        data = await storage.get_result(result_id, mock_db)

        assert data is not None
        assert data["bedrock_code"] == ""
        assert data["created_at"] is None

    @pytest.mark.asyncio
    async def test_get_result_no_output_file_key(self, storage, mock_db):
        """Returns empty bedrock_code when output_data has no output_file key."""
        result_id = str(uuid.uuid4())

        mock_result = MagicMock()
        mock_result.job_id = "job-777"
        mock_result.output_data = {"metadata": {}}
        mock_result.created_at = None
        mock_db.get = AsyncMock(return_value=mock_result)

        data = await storage.get_result(result_id, mock_db)

        assert data is not None
        assert data["bedrock_code"] == ""

    @pytest.mark.asyncio
    async def test_get_result_created_at_isoformat(self, storage, mock_db, tmp_dirs):
        """created_at field is formatted as ISO string."""
        _, output_dir = tmp_dirs
        result_id = str(uuid.uuid4())
        output_file = output_dir / f"{result_id}.mcaddon"
        output_file.write_text("x")

        ts = datetime(2024, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        mock_result = MagicMock()
        mock_result.job_id = "job-iso"
        mock_result.output_data = {"output_file": str(output_file), "metadata": {}}
        mock_result.created_at = ts
        mock_db.get = AsyncMock(return_value=mock_result)

        data = await storage.get_result(result_id, mock_db)

        assert data["created_at"] == ts.isoformat()


# ---------------------------------------------------------------------------
# TestDownloadResult
# ---------------------------------------------------------------------------


class TestDownloadResult:
    """Tests for ResultStorage.download_result."""

    @pytest.mark.asyncio
    async def test_download_result_file_exists(self, storage, tmp_dirs):
        """Returns file path string when .mcaddon file is present."""
        _, output_dir = tmp_dirs
        result_id = str(uuid.uuid4())
        output_file = output_dir / f"{result_id}.mcaddon"
        output_file.write_text("addon data")

        path = await storage.download_result(result_id)

        assert path == str(output_file)

    @pytest.mark.asyncio
    async def test_download_result_file_missing(self, storage):
        """Returns None when .mcaddon file does not exist."""
        path = await storage.download_result("ghost-result-id")
        assert path is None

    @pytest.mark.asyncio
    async def test_download_result_returns_string(self, storage, tmp_dirs):
        """Return type is str, not Path."""
        _, output_dir = tmp_dirs
        result_id = str(uuid.uuid4())
        (output_dir / f"{result_id}.mcaddon").write_text("data")

        path = await storage.download_result(result_id)

        assert isinstance(path, str)


# ---------------------------------------------------------------------------
# TestCleanupExpiredResults
# ---------------------------------------------------------------------------


class TestCleanupExpiredResults:
    """Tests for ResultStorage.cleanup_expired_results."""

    @pytest.mark.asyncio
    async def test_cleanup_no_expired_results(self, storage, mock_db):
        """Returns 0 when there are no expired results."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with patch("services.result_storage.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, tzinfo=timezone.utc)

            count = await storage.cleanup_expired_results(mock_db)

        assert count == 0
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cleanup_deletes_files_and_records(self, storage, mock_db, tmp_dirs):
        """Deletes files from disk and DB records for expired results."""
        _, output_dir = tmp_dirs

        # Create a file that simulates an expired result
        file_path = output_dir / "expired.mcaddon"
        file_path.write_text("old data")

        mock_result = MagicMock()
        mock_result.output_data = {"output_file": str(file_path)}

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_result]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with patch("services.result_storage.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, tzinfo=timezone.utc)

            count = await storage.cleanup_expired_results(mock_db)

        assert count == 1
        assert not file_path.exists()
        mock_db.delete.assert_called_once_with(mock_result)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cleanup_file_already_removed(self, storage, mock_db):
        """Handles case where the file was already removed before cleanup."""
        mock_result = MagicMock()
        mock_result.output_data = {"output_file": "/nonexistent/path/old.mcaddon"}

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_result]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with patch("services.result_storage.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, tzinfo=timezone.utc)

            count = await storage.cleanup_expired_results(mock_db)

        # Should still delete the DB record even if file doesn't exist
        assert count == 1
        mock_db.delete.assert_awaited_once_with(mock_result)

    @pytest.mark.asyncio
    async def test_cleanup_result_with_no_output_file_key(self, storage, mock_db):
        """Handles expired result with missing output_file key in output_data."""
        mock_result = MagicMock()
        mock_result.output_data = {"metadata": {}}  # no 'output_file' key

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_result]
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with patch("services.result_storage.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, tzinfo=timezone.utc)

            count = await storage.cleanup_expired_results(mock_db)

        assert count == 1
        mock_db.delete.assert_awaited_once_with(mock_result)

    @pytest.mark.asyncio
    async def test_cleanup_multiple_expired_results(self, storage, mock_db, tmp_dirs):
        """Deletes multiple expired files and DB records in one call."""
        _, output_dir = tmp_dirs

        files = []
        mock_results = []
        for i in range(3):
            f = output_dir / f"expired_{i}.mcaddon"
            f.write_text(f"data_{i}")
            files.append(f)
            mr = MagicMock()
            mr.output_data = {"output_file": str(f)}
            mock_results.append(mr)

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_results
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with patch("services.result_storage.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, tzinfo=timezone.utc)

            count = await storage.cleanup_expired_results(mock_db)

        assert count == 3
        for f in files:
            assert not f.exists()
        assert mock_db.delete.call_count == 3
        mock_db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# TestGetStorageStats
# ---------------------------------------------------------------------------


class TestGetStorageStats:
    """Tests for ResultStorage.get_storage_stats."""

    def test_stats_empty_output_dir(self, storage):
        """Returns zeroed stats when no .mcaddon files exist."""
        stats = storage.get_storage_stats()

        assert stats["total_results"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["total_size_mb"] == 0.0
        assert "output_directory" in stats
        assert stats["expiry_days"] == 30

    def test_stats_with_files(self, storage, tmp_dirs):
        """Returns correct counts and sizes when .mcaddon files are present."""
        _, output_dir = tmp_dirs

        (output_dir / "a.mcaddon").write_bytes(b"x" * 1024)
        (output_dir / "b.mcaddon").write_bytes(b"y" * 2048)

        stats = storage.get_storage_stats()

        assert stats["total_results"] == 2
        assert stats["total_size_bytes"] == 3072
        assert abs(stats["total_size_mb"] - 3072 / (1024 * 1024)) < 1e-9

    def test_stats_ignores_non_mcaddon_files(self, storage, tmp_dirs):
        """Only .mcaddon files are counted, other files are ignored."""
        _, output_dir = tmp_dirs

        (output_dir / "file.txt").write_text("ignored")
        (output_dir / "file.zip").write_text("also ignored")
        (output_dir / "valid.mcaddon").write_text("counted")

        stats = storage.get_storage_stats()

        assert stats["total_results"] == 1

    def test_stats_output_directory_path(self, storage, tmp_dirs):
        """output_directory field matches the configured output dir."""
        _, output_dir = tmp_dirs

        stats = storage.get_storage_stats()

        assert stats["output_directory"] == str(output_dir)

    def test_stats_expiry_days(self, storage):
        """expiry_days field equals RESULT_EXPIRY_DAYS constant."""
        from services.result_storage import RESULT_EXPIRY_DAYS

        stats = storage.get_storage_stats()

        assert stats["expiry_days"] == RESULT_EXPIRY_DAYS


# ---------------------------------------------------------------------------
# TestGetResultStorageSingleton
# ---------------------------------------------------------------------------


class TestGetResultStorageSingleton:
    """Tests for get_result_storage factory function."""

    def test_get_result_storage_returns_instance(self, tmp_path):
        """get_result_storage returns a ResultStorage instance."""
        import services.result_storage as rs_mod

        # Reset singleton so we get a fresh call
        original = rs_mod._result_storage
        rs_mod._result_storage = None
        try:
            temp_dir = tmp_path / "temp"
            output_dir = tmp_path / "output"
            temp_dir.mkdir()
            output_dir.mkdir()

            with (
                patch.object(rs_mod, "TEMP_UPLOADS_DIR", temp_dir),
                patch.object(rs_mod, "CONVERSION_OUTPUTS_DIR", output_dir),
            ):
                instance = rs_mod.get_result_storage()
            assert isinstance(instance, rs_mod.ResultStorage)
        finally:
            rs_mod._result_storage = original

    def test_get_result_storage_is_singleton(self, tmp_path):
        """get_result_storage returns the same instance on repeated calls."""
        import services.result_storage as rs_mod

        original = rs_mod._result_storage
        rs_mod._result_storage = None
        try:
            temp_dir = tmp_path / "temp"
            output_dir = tmp_path / "output"
            temp_dir.mkdir()
            output_dir.mkdir()

            with (
                patch.object(rs_mod, "TEMP_UPLOADS_DIR", temp_dir),
                patch.object(rs_mod, "CONVERSION_OUTPUTS_DIR", output_dir),
            ):
                inst1 = rs_mod.get_result_storage()
                inst2 = rs_mod.get_result_storage()
            assert inst1 is inst2
        finally:
            rs_mod._result_storage = original

    def test_get_result_storage_reuses_existing(self):
        """get_result_storage does not create a new instance when one exists."""
        import services.result_storage as rs_mod

        fake_instance = MagicMock()
        original = rs_mod._result_storage
        rs_mod._result_storage = fake_instance
        try:
            result = rs_mod.get_result_storage()
            assert result is fake_instance
        finally:
            rs_mod._result_storage = original


# ---------------------------------------------------------------------------
# TestResultStorageEdgeCases
# ---------------------------------------------------------------------------


class TestResultStorageEdgeCases:
    """Edge-case tests for ResultStorage."""

    @pytest.mark.asyncio
    async def test_store_result_empty_bedrock_code(self, storage, mock_db):
        """store_result handles empty bedrock_code string."""
        mock_db.get = AsyncMock(return_value=None)

        result_id = await storage.store_result(
            job_id="j1",
            user_id="u1",
            bedrock_code="",
            result_metadata={},
            db=mock_db,
        )

        assert result_id is not None
        added_arg = mock_db.add.call_args[0][0]
        assert added_arg.output_data["code_length"] == 0

    @pytest.mark.asyncio
    async def test_store_result_large_bedrock_code(self, storage, mock_db):
        """store_result handles large bedrock_code strings."""
        mock_db.get = AsyncMock(return_value=None)
        large_code = "x" * 100_000

        result_id = await storage.store_result(
            job_id="j2",
            user_id="u2",
            bedrock_code=large_code,
            result_metadata={},
            db=mock_db,
        )

        assert result_id is not None
        added_arg = mock_db.add.call_args[0][0]
        assert added_arg.output_data["code_length"] == 100_000

    @pytest.mark.asyncio
    async def test_get_result_empty_metadata(self, storage, mock_db, tmp_dirs):
        """get_result returns empty dict for metadata when missing from output_data."""
        _, output_dir = tmp_dirs
        result_id = str(uuid.uuid4())
        output_file = output_dir / f"{result_id}.mcaddon"
        output_file.write_text("")

        mock_result = MagicMock()
        mock_result.job_id = "j-meta"
        mock_result.output_data = {"output_file": str(output_file)}  # no 'metadata' key
        mock_result.created_at = None
        mock_db.get = AsyncMock(return_value=mock_result)

        data = await storage.get_result(result_id, mock_db)

        assert data["metadata"] == {}

    def test_stats_single_large_file(self, storage, tmp_dirs):
        """get_storage_stats correctly computes MB for a large file."""
        _, output_dir = tmp_dirs
        size_bytes = 5 * 1024 * 1024  # 5 MB
        (output_dir / "big.mcaddon").write_bytes(b"z" * size_bytes)

        stats = storage.get_storage_stats()

        assert stats["total_results"] == 1
        assert stats["total_size_bytes"] == size_bytes
        assert abs(stats["total_size_mb"] - 5.0) < 1e-6
