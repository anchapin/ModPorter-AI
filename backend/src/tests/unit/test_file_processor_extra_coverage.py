"""
Extra pytest tests for file_processor.py to push coverage from 79.1% to 80%+
Target: 90+ uncovered lines in file_processor.py
"""

import pytest
import io
import zipfile
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile

from file_processor import (
    FileProcessor,
    ValidationResult,
    ScanResult,
    ExtractionResult,
    DownloadResult,
)


class TestFileProcessorExtraValidation:
    """Extra tests for validate_upload error paths."""

    def test_validate_upload_size_exceeds_limit(self):
        """Test validation fails when file size exceeds limit."""
        processor = FileProcessor()

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "large.jar"
        mock_file.size = 600 * 1024 * 1024  # 600MB > 500MB limit
        mock_file.content_type = "application/java-archive"
        mock_file.file = io.BytesIO(b"PK\x03\x04")

        result = processor.validate_upload(mock_file)
        assert result.is_valid is False
        assert "exceeds" in result.message.lower()

    def test_validate_upload_invalid_magic_bytes(self):
        """Test validation fails with invalid magic bytes."""
        processor = FileProcessor()

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.jar"
        mock_file.size = 1000
        mock_file.content_type = "application/java-archive"
        mock_file.file = io.BytesIO(b"NOTAZIP")

        result = processor.validate_upload(mock_file)
        assert result.is_valid is False

    def test_validate_upload_read_error(self):
        """Test validation handles read errors gracefully."""
        processor = FileProcessor()

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.jar"
        mock_file.size = 1000
        mock_file.content_type = "application/java-archive"
        mock_file.file = MagicMock()
        mock_file.file.read = MagicMock(side_effect=IOError("Read failed"))

        result = processor.validate_upload(mock_file)
        assert result.is_valid is False
        assert "error" in result.message.lower()


class TestFileProcessorExtraDownloadValidation:
    """Extra tests for validate_downloaded_file error paths."""

    @pytest.mark.asyncio
    async def test_validate_downloaded_file_not_found(self):
        """Test downloaded file validation fails when file not found."""
        processor = FileProcessor()

        fake_path = Path("/nonexistent/file.jar")

        result = await processor.validate_downloaded_file(fake_path, "http://example.com/file.jar")
        assert result.is_valid is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_validate_downloaded_file_invalid_magic(self):
        """Test downloaded file validation fails with invalid magic bytes."""
        processor = FileProcessor()

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tmp:
            tmp.write(b"NOTAZIP")
            tmp_path = Path(tmp.name)

        try:
            result = await processor.validate_downloaded_file(
                tmp_path, "http://example.com/file.jar"
            )
            assert result.is_valid is False
            assert "magic bytes" in result.message.lower()
        finally:
            tmp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_validate_downloaded_file_unexpected_extension(self):
        """Test downloaded file with unexpected extension."""
        processor = FileProcessor()

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"PK\x03\x04")
            tmp_path = Path(tmp.name)

        try:
            result = await processor.validate_downloaded_file(
                tmp_path, "http://example.com/file.exe"
            )
            # Should still be valid since it has ZIP magic
            assert result.validated_file_type == "zip"
        finally:
            tmp_path.unlink(missing_ok=True)


class TestFileProcessorExtraMalwareScan:
    """Extra tests for scan_for_malware error paths."""

    @pytest.mark.asyncio
    async def test_scan_for_malware_path_traversal(self):
        """Test malware scan detects path traversal."""
        processor = FileProcessor()

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("../outside.txt", "malicious")
            tmp_path = Path(tmp.name)

        try:
            result = await processor.scan_for_malware(tmp_path, "zip")
            assert result.is_safe is False
            assert "path traversal" in result.message.lower()
        finally:
            tmp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_scan_for_malware_bad_zip(self):
        """Test malware scan handles corrupted zip."""
        processor = FileProcessor()

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(b"NOTAZIP")
            tmp_path = Path(tmp.name)

        try:
            result = await processor.scan_for_malware(tmp_path, "zip")
            assert result.is_safe is False
        finally:
            tmp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_scan_for_malware_absolute_path_traversal(self):
        """Test malware scan detects absolute path traversal."""
        processor = FileProcessor()

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("/etc/passwd", "malicious")
            tmp_path = Path(tmp.name)

        try:
            result = await processor.scan_for_malware(tmp_path, "zip")
            assert result.is_safe is False
            assert "path traversal" in result.message.lower()
        finally:
            tmp_path.unlink(missing_ok=True)


class TestFileProcessorExtraExtract:
    """Extra tests for extract_mod_files error paths."""

    @pytest.mark.asyncio
    async def test_extract_mod_files_unsupported_type(self):
        """Test extraction fails for unsupported file type."""
        processor = FileProcessor()

        result = await processor.extract_mod_files(Path("test.jar"), "job123", "exe")
        assert result.success is False
        assert "unsupported" in result.message.lower()

    @pytest.mark.asyncio
    async def test_extract_mod_files_bad_zip(self):
        """Test extraction handles corrupted zip."""
        processor = FileProcessor()

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(b"NOTAZIP")
            tmp_path = Path(tmp.name)

        try:
            result = await processor.extract_mod_files(tmp_path, "job123", "zip")
            assert result.success is False
            assert "corrupted" in result.message.lower()
        finally:
            tmp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_extract_mod_files_with_manifests(self):
        """Test extraction finds manifest files."""
        processor = FileProcessor()

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("fabric.mod.json", '{"id": "testmod"}')
                zf.writestr("test.txt", "content")
            tmp_path = Path(tmp.name)

        try:
            result = await processor.extract_mod_files(tmp_path, "job123", "zip")
            assert result.success is True
            assert result.found_manifest_type == "json"
            assert result.manifest_data is not None
        finally:
            tmp_path.unlink(missing_ok=True)


class TestFileProcessorExtraDownload:
    """Extra tests for download_from_url error paths."""

    @pytest.mark.asyncio
    async def test_download_from_url_timeout(self):
        """Test download handles timeout."""
        import httpx

        processor = FileProcessor()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            result = await processor.download_from_url("http://example.com/file.jar", "job_timeout")
            assert result.success is False
            assert "timeout" in result.message.lower()

    @pytest.mark.asyncio
    async def test_download_from_url_request_error(self):
        """Test download handles request errors."""
        import httpx

        processor = FileProcessor()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Network error")
            )

            result = await processor.download_from_url("http://example.com/file.jar", "job_reqerr")
            assert result.success is False

    @pytest.mark.asyncio
    async def test_download_from_url_too_many_redirects(self):
        """Test download handles too many redirects."""
        processor = FileProcessor()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 302
            mock_response.headers = {"Location": "http://example.com/next"}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await processor.download_from_url(
                "http://example.com/file.jar", "job_redirect"
            )
            assert result.success is False
            assert "redirect" in result.message.lower()

    @pytest.mark.asyncio
    async def test_download_from_url_unsafe_redirect(self):
        """Test download blocks unsafe URL redirects."""
        processor = FileProcessor()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 302
            mock_response.headers = {"Location": "http://169.254.169.254/"}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await processor.download_from_url("http://example.com/file.jar", "job_unsafe")
            assert result.success is False

    @pytest.mark.asyncio
    async def test_download_from_url_generic_exception(self):
        """Test download handles generic exceptions."""
        processor = FileProcessor()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Unknown error")
            )

            result = await processor.download_from_url("http://example.com/file.jar", "job_gen")
            assert result.success is False


class TestFileProcessorExtraCleanup:
    """Extra tests for cleanup_temp_files."""

    def test_cleanup_temp_files_not_exists(self):
        """Test cleanup handles non-existent directory."""
        processor = FileProcessor()

        result = processor.cleanup_temp_files("nonexistent_job")
        assert result is True

    def test_cleanup_temp_files_permission_error(self):
        """Test cleanup handles permission errors."""
        processor = FileProcessor()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("shutil.rmtree", side_effect=PermissionError("Access denied")):
                result = processor.cleanup_temp_files("job_perm")
                assert result is False

    def test_cleanup_temp_files_generic_error(self):
        """Test cleanup handles generic errors."""
        processor = FileProcessor()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("shutil.rmtree", side_effect=OSError("Unknown error")):
                result = processor.cleanup_temp_files("job_err")
                assert result is False


class TestFileProcessorSafeUrl:
    """Extra tests for _is_safe_url."""

    @pytest.mark.asyncio
    async def test_is_safe_url_invalid_scheme(self):
        """Test URL validation rejects invalid schemes."""
        processor = FileProcessor()

        result = await processor._is_safe_url("ftp://example.com/file.jar")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_safe_url_no_hostname(self):
        """Test URL validation rejects URLs without hostname."""
        processor = FileProcessor()

        result = await processor._is_safe_url("file:///path")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_safe_url_loopback(self):
        """Test URL validation rejects loopback addresses."""
        processor = FileProcessor()

        result = await processor._is_safe_url("http://127.0.0.1/file.jar")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_safe_url_private_ip(self):
        """Test URL validation rejects private IP addresses."""
        processor = FileProcessor()

        result = await processor._is_safe_url("http://192.168.1.1/file.jar")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_safe_url_localhost(self):
        """Test URL validation rejects localhost."""
        processor = FileProcessor()

        result = await processor._is_safe_url("http://localhost/file.jar")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_safe_url_unresolvable(self):
        """Test URL validation handles unresolvable hostnames."""
        processor = FileProcessor()

        import socket

        with patch("socket.getaddrinfo", side_effect=socket.gaierror("DNS error")):
            result = await processor._is_safe_url("http://nonexistent.invalid/file.jar")
            assert result is False

    @pytest.mark.asyncio
    async def test_is_safe_url_invalid_ip_parse(self):
        """Test URL validation handles invalid IP parsing."""
        processor = FileProcessor()

        with patch(
            "socket.getaddrinfo", return_value=[(None, None, None, None, ("invalid_ip", None))]
        ):
            result = await processor._is_safe_url("http://example.com/file.jar")
            assert result is False

    @pytest.mark.asyncio
    async def test_is_safe_url_link_local(self):
        """Test URL validation rejects link-local addresses."""
        processor = FileProcessor()

        result = await processor._is_safe_url("http://169.254.0.1/file.jar")
        assert result is False
