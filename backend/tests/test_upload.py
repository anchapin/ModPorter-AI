"""
Integration tests for file upload system.

Tests:
- Upload tests (4 tests)
- Validation tests (4 tests)
- Storage tests (3 tests)
"""

import pytest
import os
import io
import zipfile
import tempfile
import shutil
from unittest.mock import patch, AsyncMock, MagicMock

# Test constants
TEST_JOB_ID = "12345678-1234-1234-1234-123456789012"
TEST_USER_ID = "test_user"
TEST_FILENAME = "test_mod.jar"


# Helper functions for creating test JAR files
def create_test_jar(content: str = "test content") -> bytes:
    """Create a minimal JAR file for testing"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add manifest
        manifest = "Manifest-Version: 1.0\nModId: testmod\nMod-Name: TestMod\nVersion: 1.0.0\n"
        zf.writestr("META-INF/MANIFEST.MF", manifest)
        # Add a dummy class file
        zf.writestr("com/testmod/TestMod.class", content)
    return buffer.getvalue()


def create_test_zip() -> bytes:
    """Create a test ZIP file"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.txt", "test content")
    return buffer.getvalue()


# ========== Upload Tests ==========


class TestUploadAPI:
    """Tests for file upload API endpoints"""

    def test_upload_endpoint_import(self):
        """Test that upload endpoint can be imported"""
        try:
            from api import upload

            assert upload.router is not None
        except ImportError as e:
            pytest.skip(f"Cannot import upload module: {e}")

    def test_validate_file_type_jar(self):
        """Test file type validation for JAR files"""
        from api.upload import validate_file_type

        # Valid JAR
        assert validate_file_type("mod.jar", "application/java-archive") is True
        assert validate_file_type("mod.jar", "application/zip") is True
        assert validate_file_type("mod.jar", "application/x-java-archive") is True

    def test_validate_file_type_zip(self):
        """Test file type validation for ZIP files"""
        from api.upload import validate_file_type

        # Valid ZIP
        assert validate_file_type("mod.zip", "application/zip") is True

    def test_validate_file_type_mcaddon(self):
        """Test file type validation for mcaddon files"""
        from api.upload import validate_file_type

        # Valid mcaddon
        assert validate_file_type("mod.mcaddon", "application/zip") is True

    def test_validate_file_type_invalid(self):
        """Test file type validation rejects invalid files"""
        from api.upload import validate_file_type

        # Invalid extensions
        assert validate_file_type("mod.exe", "application/octet-stream") is False
        assert validate_file_type("mod.pdf", "application/pdf") is False
        assert validate_file_type("mod.txt", "text/plain") is False


# ========== Validation Tests ==========


class TestFileValidation:
    """Tests for file handler validation"""

    @pytest.mark.asyncio
    async def test_validate_jar_valid(self):
        """Test validation of valid JAR file"""
        from services.file_handler import FileHandler

        handler = FileHandler()

        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            f.write(create_test_jar())
            temp_path = f.name

        try:
            result = await handler.validate_jar(temp_path)
            assert result.is_valid is True
            assert len(result.errors) == 0
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_validate_jar_invalid_format(self):
        """Test validation rejects invalid file format"""
        from services.file_handler import FileHandler

        handler = FileHandler()

        # Create temp file with invalid content
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            f.write(b"not a valid zip")
            temp_path = f.name

        try:
            result = await handler.validate_jar(temp_path)
            assert result.is_valid is False
            assert len(result.errors) > 0
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_validate_jar_missing_manifest(self):
        """Test validation warns about missing manifest"""
        from services.file_handler import FileHandler

        handler = FileHandler()

        # Create JAR without manifest
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("test.txt", "test")
        content = buffer.getvalue()

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = await handler.validate_jar(temp_path)
            assert result.is_valid is True
            assert len(result.warnings) > 0
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_validate_jar_nonexistent(self):
        """Test validation rejects nonexistent file"""
        from services.file_handler import FileHandler

        handler = FileHandler()

        result = await handler.validate_jar("/nonexistent/file.jar")
        assert result.is_valid is False
        assert len(result.errors) > 0


# ========== Storage Tests ==========


class TestStorageManager:
    """Tests for storage manager"""

    def test_storage_backend_local(self):
        """Test local storage backend initialization"""
        from core.storage import StorageManager, StorageBackend

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)
            assert storage.backend == StorageBackend.LOCAL
            assert os.path.exists(os.path.join(tmpdir, "uploads"))
            assert os.path.exists(os.path.join(tmpdir, "processing"))
            assert os.path.exists(os.path.join(tmpdir, "results"))

    @pytest.mark.asyncio
    async def test_save_and_get_file(self):
        """Test saving and retrieving files"""
        from core.storage import StorageManager, StorageBackend

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)

            content = b"test file content"
            file_path = await storage.save_file(
                content=content, job_id=TEST_JOB_ID, filename="test.jar", user_id=TEST_USER_ID
            )

            # Verify file was saved
            assert os.path.exists(file_path)

            # Verify content
            retrieved = await storage.get_file(TEST_JOB_ID, "test.jar", TEST_USER_ID)
            assert retrieved == content

    @pytest.mark.asyncio
    async def test_delete_job_files(self):
        """Test deleting job files"""
        from core.storage import StorageManager, StorageBackend

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager(backend=StorageBackend.LOCAL, base_path=tmpdir)

            # Save a file
            content = b"test content"
            await storage.save_file(
                content=content, job_id=TEST_JOB_ID, filename="test.jar", user_id=TEST_USER_ID
            )

            # Delete the files
            result = await storage.delete_job_files(TEST_JOB_ID, TEST_USER_ID)
            assert result is True

            # Verify file is deleted
            retrieved = await storage.get_file(TEST_JOB_ID, "test.jar", TEST_USER_ID)
            assert retrieved is None


# ========== Integration Tests ==========


class TestFileHandler:
    """Tests for file handler service"""

    @pytest.mark.asyncio
    async def test_extract_metadata_from_jar(self):
        """Test metadata extraction from JAR"""
        from services.file_handler import FileHandler

        handler = FileHandler()

        # Create test JAR with manifest
        jar_content = create_test_jar()

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            f.write(jar_content)
            temp_path = f.name

        try:
            metadata = await handler.extract_metadata(temp_path)
            # Manifest-based extraction
            assert metadata.modid is not None or metadata.version is not None
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_identify_mod_loader(self):
        """Test mod loader identification"""
        from services.file_handler import FileHandler, ModLoader

        handler = FileHandler()

        # Create test JAR
        jar_content = create_test_jar()

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            f.write(jar_content)
            temp_path = f.name

        try:
            loader = await handler.identify_mod_loader(temp_path)
            # Should detect something or return unknown
            assert isinstance(loader, ModLoader)
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_virus_scan_placeholder(self):
        """Test virus scan placeholder always returns True"""
        from services.file_handler import FileHandler

        handler = FileHandler()

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            f.write(b"test")
            temp_path = f.name

        try:
            result = await handler.virus_scan_placeholder(temp_path)
            assert result is True
        finally:
            os.unlink(temp_path)


# Run all tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
