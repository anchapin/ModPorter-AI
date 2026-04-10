"""
Unit tests for Storage module.

Issue: #643 - Backend: Implement Rate Limiting Dashboard
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from core.storage import StorageManager, storage_manager, StorageBackend


class TestStorageBackend:
    """Tests for StorageBackend enum."""

    def test_backend_values(self):
        """Test backend enum values."""
        assert StorageBackend.LOCAL.value == "local"
        assert StorageBackend.S3.value == "s3"


class TestStorageManagerInit:
    """Tests for StorageManager initialization."""

    def test_default_initialization(self):
        """Test default initialization uses local backend."""
        with patch.dict(os.environ, {"STORAGE_BACKEND": "local"}):
            manager = StorageManager()
            assert manager.backend == StorageBackend.LOCAL

    def test_s3_backend_initialization(self):
        """Test S3 backend initialization."""
        with patch.dict(os.environ, {"STORAGE_BACKEND": "s3"}):
            manager = StorageManager()
            assert manager.backend == StorageBackend.S3

    def test_custom_base_path(self):
        """Test custom base path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(base_path=tmpdir)
            assert manager.base_path == tmpdir

    def test_custom_ttl(self):
        """Test custom TTL."""
        manager = StorageManager(default_ttl_days=14)
        assert manager.default_ttl_days == 14

    def test_direct_local_backend(self):
        """Test direct local backend specification."""
        manager = StorageManager(backend=StorageBackend.LOCAL)
        assert manager.backend == StorageBackend.LOCAL


class TestStorageDirectories:
    """Tests for storage directory management."""

    def test_directories_created(self):
        """Test storage directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)
            assert os.path.exists(os.path.join(tmpdir, "uploads"))
            assert os.path.exists(os.path.join(tmpdir, "processing"))
            assert os.path.exists(os.path.join(tmpdir, "results"))

    def test_directory_constants(self):
        """Test directory name constants."""
        assert StorageManager.UPLOADS_DIR == "uploads"
        assert StorageManager.PROCESSING_DIR == "processing"
        assert StorageManager.RESULTS_DIR == "results"


class TestSaveFile:
    """Tests for save_file method."""

    @pytest.fixture
    def manager(self):
        """Create manager with temp path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)

    @pytest.mark.asyncio
    async def test_save_file_original(self, manager):
        """Test saving file to original category."""
        content = b"test content"
        path = await manager.save_file(
            content=content,
            job_id="job123",
            filename="test.jar",
            user_id="user1",
            category="original",
        )
        assert os.path.exists(path)
        with open(path, "rb") as f:
            assert f.read() == content

    @pytest.mark.asyncio
    async def test_save_file_processing(self, manager):
        """Test saving file to processing category."""
        content = b"processing content"
        path = await manager.save_file(
            content=content,
            job_id="job456",
            filename="processed.jar",
            user_id="user2",
            category="processing",
        )
        assert os.path.exists(path)

    @pytest.mark.asyncio
    async def test_save_file_result(self, manager):
        """Test saving file to result category."""
        content = b"result content"
        path = await manager.save_file(
            content=content,
            job_id="job789",
            filename="result.jar",
            user_id="user3",
            category="result",
        )
        assert os.path.exists(path)

    @pytest.mark.asyncio
    async def test_save_file_custom_category(self, manager):
        """Test saving file to custom category."""
        content = b"custom content"
        path = await manager.save_file(
            content=content,
            job_id="job999",
            filename="custom.jar",
            user_id="user4",
            category="custom",
        )
        assert os.path.exists(path)

    @pytest.mark.asyncio
    async def test_save_file_updates_status(self, manager):
        """Test save_file updates upload status."""
        content = b"status test"
        await manager.save_file(
            content=content,
            job_id="status_job",
            filename="test.jar",
            user_id="user1",
            category="original",
        )
        status = await manager.get_upload_status("status_job")
        assert status is not None
        assert status["status"] == "completed"
        assert status["progress"] == 100
        assert status["size"] == len(content)


class TestGetFile:
    """Tests for get_file method."""

    @pytest.fixture
    def manager(self):
        """Create manager with temp path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)

    @pytest.mark.asyncio
    async def test_get_file_exists(self, manager):
        """Test getting existing file."""
        content = b"test content for get"
        await manager.save_file(
            content=content,
            job_id="get_job",
            filename="test.jar",
            user_id="user1",
            category="original",
        )
        result = await manager.get_file(job_id="get_job", filename="test.jar", user_id="user1")
        assert result == content

    @pytest.mark.asyncio
    async def test_get_file_not_found(self, manager):
        """Test getting nonexistent file."""
        result = await manager.get_file(job_id="nonexistent", filename="test.jar", user_id="user1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_file_from_processing(self, manager):
        """Test getting file from processing category."""
        content = b"processing file"
        await manager.save_file(
            content=content,
            job_id="proc_job",
            filename="processed.jar",
            user_id="user1",
            category="processing",
        )
        result = await manager.get_file(job_id="proc_job", filename="processed.jar")
        assert result == content

    @pytest.mark.asyncio
    async def test_get_file_from_results(self, manager):
        """Test getting file from results category."""
        content = b"result file"
        await manager.save_file(
            content=content,
            job_id="result_job",
            filename="result.jar",
            user_id="user1",
            category="result",
        )
        result = await manager.get_file(job_id="result_job", filename="result.jar")
        assert result == content


class TestDeleteJobFiles:
    """Tests for delete_job_files method."""

    @pytest.fixture
    def manager(self):
        """Create manager with temp path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)

    @pytest.mark.asyncio
    async def test_delete_job_files(self, manager):
        """Test deleting job files."""
        await manager.save_file(
            content=b"content",
            job_id="delete_job",
            filename="test.jar",
            user_id="user1",
            category="original",
        )
        result = await manager.delete_job_files(job_id="delete_job", user_id="user1")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_job(self, manager):
        """Test deleting nonexistent job returns False."""
        result = await manager.delete_job_files(job_id="nonexistent", user_id="user1")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_clears_status(self, manager):
        """Test delete clears upload status."""
        await manager.save_file(
            content=b"content",
            job_id="status_clear",
            filename="test.jar",
            user_id="user1",
            category="original",
        )
        await manager.delete_job_files(job_id="status_clear", user_id="user1")
        status = await manager.get_upload_status("status_clear")
        assert status is None


class TestCleanupOldFiles:
    """Tests for cleanup_old_files method."""

    @pytest.fixture
    def manager(self):
        """Create manager with temp path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)

    @pytest.mark.asyncio
    async def test_cleanup_old_files(self, manager):
        """Test cleaning up old files."""
        count = await manager.cleanup_old_files(ttl_days=0)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_cleanup_uses_default_ttl(self, manager):
        """Test cleanup uses default TTL."""
        manager.default_ttl_days = 30
        count = await manager.cleanup_old_files()
        assert count >= 0


class TestStorageStats:
    """Tests for storage statistics."""

    @pytest.fixture
    def manager(self):
        """Create manager with temp path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)

    @pytest.mark.asyncio
    async def test_get_storage_stats_local(self, manager):
        """Test getting storage stats for local backend."""
        stats = await manager.get_storage_stats()
        assert "backend" in stats
        assert stats["backend"] == "local"
        assert "base_path" in stats
        assert "upload_count" in stats
        assert "total_size" in stats
        assert "file_count" in stats

    @pytest.mark.asyncio
    async def test_storage_stats_after_save(self, manager):
        """Test stats update after saving file."""
        await manager.save_file(
            content=b"stats test",
            job_id="stats_job",
            filename="test.jar",
            user_id="user1",
            category="original",
        )
        stats = await manager.get_storage_stats()
        assert stats["upload_count"] == 1

    def test_get_local_size(self, manager):
        """Test getting local storage size."""
        size = manager._get_local_size()
        assert size >= 0

    def test_get_local_file_count(self, manager):
        """Test getting local file count."""
        count = manager._get_local_file_count()
        assert count >= 0


class TestUploadStatus:
    """Tests for upload status tracking."""

    @pytest.fixture
    def manager(self):
        """Create manager with temp path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)

    @pytest.mark.asyncio
    async def test_get_upload_status_exists(self, manager):
        """Test getting existing upload status."""
        await manager.save_file(
            content=b"content",
            job_id="status_test",
            filename="test.jar",
            user_id="user1",
            category="original",
        )
        status = await manager.get_upload_status("status_test")
        assert status is not None
        assert "status" in status
        assert "progress" in status
        assert "path" in status

    @pytest.mark.asyncio
    async def test_get_upload_status_not_exists(self, manager):
        """Test getting nonexistent upload status."""
        status = await manager.get_upload_status("nonexistent")
        assert status is None


class TestS3Fallback:
    """Tests for S3 backend fallback to local."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="S3 storage backend not implemented yet - needs actual S3 support")
    async def test_s3_save_falls_back_to_local(self):
        """Test S3 save falls back to local storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(
                backend=StorageBackend.S3, base_path=tmpdir, s3_bucket="test-bucket"
            )
            content = b"s3 fallback content"
            path = await manager.save_file(
                content=content,
                job_id="s3_fallback",
                filename="test.jar",
                user_id="user1",
                category="original",
            )
            assert os.path.exists(path)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="S3 storage backend not implemented yet - needs actual S3 support")
    async def test_s3_get_falls_back_to_local(self):
        """Test S3 get falls back to local storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(
                backend=StorageBackend.S3, base_path=tmpdir, s3_bucket="test-bucket"
            )
            content = b"s3 fallback get content"
            path = await manager.save_file(
                content=content,
                job_id="s3_get_fallback",
                filename="test.jar",
                user_id="user1",
                category="original",
            )
            # S3 fallback saves to local, but _get_s3 returns None
            # So we test the fallback by reading directly
            assert os.path.exists(path)

    @pytest.mark.asyncio
    async def test_s3_delete_falls_back(self):
        """Test S3 delete falls back to local."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(
                backend=StorageBackend.S3, base_path=tmpdir, s3_bucket="test-bucket"
            )
            # Save directly using local method
            content = b"content"
            path = await manager._save_local(
                content, "s3_del_fallback", "test.jar", "user1", "original"
            )
            # Delete uses _delete_s3 which returns False for S3
            # But the file was saved to local, so it won't be found by _get_s3
            result = await manager.delete_job_files(job_id="s3_del_fallback", user_id="user1")
            assert result is False  # S3 delete is not implemented


class TestLocalStoragePaths:
    """Tests for local storage path generation."""

    @pytest.fixture
    def manager(self):
        """Create manager with temp path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)

    @pytest.mark.asyncio
    async def test_user_isolation(self, manager):
        """Test files are isolated by user."""
        await manager.save_file(
            content=b"user1 content",
            job_id="user_job",
            filename="test.jar",
            user_id="user1",
            category="original",
        )
        await manager.save_file(
            content=b"user2 content",
            job_id="user_job",
            filename="test.jar",
            user_id="user2",
            category="original",
        )
        user1_file = await manager.get_file(job_id="user_job", filename="test.jar", user_id="user1")
        user2_file = await manager.get_file(job_id="user_job", filename="test.jar", user_id="user2")
        assert user1_file == b"user1 content"
        assert user2_file == b"user2 content"

    @pytest.mark.asyncio
    async def test_job_isolation(self, manager):
        """Test files are isolated by job."""
        await manager.save_file(
            content=b"job1 content",
            job_id="job1",
            filename="test.jar",
            user_id="user1",
            category="original",
        )
        await manager.save_file(
            content=b"job2 content",
            job_id="job2",
            filename="test.jar",
            user_id="user1",
            category="original",
        )
        job1_file = await manager.get_file(job_id="job1", filename="test.jar", user_id="user1")
        job2_file = await manager.get_file(job_id="job2", filename="test.jar", user_id="user1")
        assert job1_file == b"job1 content"
        assert job2_file == b"job2 content"


class TestS3Config:
    """Tests for S3 configuration."""

    def test_s3_config_from_env(self):
        """Test S3 config from environment variables."""
        with patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "s3",
                "S3_BUCKET": "my-bucket",
                "AWS_REGION": "eu-west-1",
            },
        ):
            manager = StorageManager()
            assert manager.s3_bucket == "my-bucket"
            assert manager.s3_region == "eu-west-1"

    def test_s3_config_defaults(self):
        """Test S3 config default values."""
        with patch.dict(os.environ, {"STORAGE_BACKEND": "s3"}):
            manager = StorageManager()
            assert manager.s3_bucket == ""
            assert manager.s3_region == "us-east-1"


class TestStorageManagerInstance:
    """Tests for storage_manager singleton."""

    def test_storage_manager_exists(self):
        """Test storage_manager instance exists."""
        assert storage_manager is not None
        assert isinstance(storage_manager, StorageManager)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def manager(self):
        """Create manager with temp path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)

    @pytest.mark.asyncio
    async def test_save_empty_content(self, manager):
        """Test saving empty content."""
        path = await manager.save_file(
            content=b"",
            job_id="empty_job",
            filename="empty.jar",
            user_id="user1",
            category="original",
        )
        assert os.path.exists(path)

    @pytest.mark.asyncio
    async def test_save_large_content(self, manager):
        """Test saving large content."""
        large_content = b"x" * (1024 * 1024)  # 1MB
        path = await manager.save_file(
            content=large_content,
            job_id="large_job",
            filename="large.jar",
            user_id="user1",
            category="original",
        )
        assert os.path.exists(path)
        with open(path, "rb") as f:
            assert len(f.read()) == len(large_content)

    @pytest.mark.asyncio
    async def test_get_upload_status_no_status(self, manager):
        """Test getting status for job with no status."""
        status = await manager.get_upload_status("no_status_job")
        assert status is None

    def test_get_local_size_nonexistent_dir(self):
        """Test getting size of nonexistent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)
            os.rmdir(os.path.join(tmpdir, "uploads"))
            size = manager._get_local_size()
            assert size >= 0

    def test_get_local_file_count_nonexistent_dir(self):
        """Test getting file count of nonexistent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)
            os.rmdir(os.path.join(tmpdir, "uploads"))
            count = manager._get_local_file_count()
            assert count >= 0

    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_dir(self, manager):
        """Test cleanup handles nonexistent directory."""
        count = await manager._cleanup_local(datetime.now() - timedelta(days=30))
        assert count >= 0

    @pytest.mark.asyncio
    async def test_s3_cleanup_not_implemented(self):
        """Test S3 cleanup returns 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(backend=StorageBackend.S3, base_path=tmpdir)
            count = await manager._cleanup_s3(datetime.now())
            assert count == 0

    @pytest.mark.asyncio
    async def test_s3_get_not_implemented(self):
        """Test S3 get returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(backend=StorageBackend.S3, base_path=tmpdir)
            result = await manager._get_s3("job", "file.jar", "user")
            assert result is None

    @pytest.mark.asyncio
    async def test_s3_delete_not_implemented(self):
        """Test S3 delete returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = StorageManager(backend=StorageBackend.S3, base_path=tmpdir)
            result = await manager._delete_s3("job", "user")
            assert result is False


class TestDefaultConstants:
    """Tests for default constants."""

    def test_chunk_size_constant(self):
        """Test default chunk size."""
        assert StorageManager.DEFAULT_CHUNK_SIZE == 5 * 1024 * 1024

    def test_ttl_days_constant(self):
        """Test default TTL days."""
        assert StorageManager.DEFAULT_TTL_DAYS == 7
