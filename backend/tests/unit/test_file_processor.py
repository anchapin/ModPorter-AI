import pytest
import httpx
import shutil
import logging
from pathlib import Path
from unittest import mock  # For mock.patch

from src.file_processor import FileProcessor

# Configure basic logging for tests if needed, or mock it out
# logging.basicConfig(level=logging.DEBUG) # Could be noisy
logger = logging.getLogger(__name__)


@pytest.fixture
def file_processor():
    """Pytest fixture to provide a FileProcessor instance."""
    return FileProcessor()


@pytest.fixture
def mock_job_id():
    """Pytest fixture for a consistent job_id."""
    return "test_job_123"


@pytest.fixture
def temp_job_dirs(mock_job_id):
    """Creates temporary directories for a job and cleans them up afterwards."""
    base_tmp_dir = Path("/tmp/conversions_test")
    job_upload_dir = base_tmp_dir / mock_job_id / "uploaded"
    job_extracted_dir = base_tmp_dir / mock_job_id / "extracted"

    # Create dirs
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    job_extracted_dir.mkdir(parents=True, exist_ok=True)

    yield {
        "base": base_tmp_dir,
        "upload": job_upload_dir,
        "extracted": job_extracted_dir,
    }

    # Teardown: Remove the entire base temporary directory
    if base_tmp_dir.exists():
        shutil.rmtree(base_tmp_dir)


class TestFileProcessor:
    @pytest.mark.asyncio
    @mock.patch("src.file_processor.httpx.AsyncClient")
    async def test_download_from_url_success_content_disposition(
        self, MockAsyncClient, file_processor, mock_job_id, temp_job_dirs
    ):
        mock_response = mock.AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Disposition": 'attachment; filename="example.zip"'
        }
        mock_response.url = httpx.URL("http://example.com/download/example.zip")

        # Simulate async iteration for content
        async def mock_aiter_bytes():
            yield b"file"
            yield b" content"

        mock_response.aiter_bytes = mock_aiter_bytes

        mock_get = mock.AsyncMock(return_value=mock_response)
        MockAsyncClient.return_value.__aenter__.return_value.get = (
            mock_get  # For async context manager
        )

        url = (
            "http://example.com/download.zip"  # URL passed to function can be different
        )

        # The temp_job_dirs fixture already creates the directory
        result = await file_processor.download_from_url(url, mock_job_id)

        # Assertions
        # FileProcessor creates its own directory structure at /tmp/conversions/{job_id}/uploaded/
        actual_download_dir = Path(f"/tmp/conversions/{mock_job_id}/uploaded/")
        assert actual_download_dir.exists()

        expected_file_path = actual_download_dir / "example.zip"
        assert result.success is True
        assert result.file_path == expected_file_path
        assert result.file_name == "example.zip"
        assert expected_file_path.read_bytes() == b"file content"

        MockAsyncClient.return_value.__aenter__.return_value.get.assert_called_once_with(
            url, follow_redirects=True, timeout=30.0
        )

    @pytest.mark.asyncio
    @mock.patch("src.file_processor.httpx.AsyncClient")
    async def test_download_from_url_success_url_path_filename(
        self, MockAsyncClient, file_processor, mock_job_id, temp_job_dirs
    ):
        mock_response = mock.AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/zip"
        }  # No Content-Disposition
        mock_response.url = httpx.URL(
            "http://example.com/another_example.jar"
        )  # Filename from URL path

        async def mock_aiter_bytes():
            yield b"jar content"

        mock_response.aiter_bytes = mock_aiter_bytes
        MockAsyncClient.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        url = "http://example.com/another_example.jar"
        result = await file_processor.download_from_url(url, mock_job_id)

        # FileProcessor creates its own directory structure at /tmp/conversions/{job_id}/uploaded/
        actual_download_dir = Path(f"/tmp/conversions/{mock_job_id}/uploaded/")
        expected_file_path = actual_download_dir / "another_example.jar"
        assert result.success is True
        assert result.file_path == expected_file_path
        assert result.file_name == "another_example.jar"
        assert expected_file_path.read_bytes() == b"jar content"

    @pytest.mark.asyncio
    @mock.patch("src.file_processor.httpx.AsyncClient")
    async def test_download_from_url_success_content_type_extension(
        self, MockAsyncClient, file_processor, mock_job_id, temp_job_dirs
    ):
        mock_response = mock.AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        # No Content-Disposition, and URL path might not have extension
        mock_response.headers = {"Content-Type": "application/java-archive"}
        mock_response.url = httpx.URL("http://example.com/some_file_no_ext")

        async def mock_aiter_bytes():
            yield b"java archive"

        mock_response.aiter_bytes = mock_aiter_bytes
        MockAsyncClient.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        url = "http://example.com/some_file_no_ext"
        result = await file_processor.download_from_url(url, mock_job_id)

        # FileProcessor creates its own directory structure at /tmp/conversions/{job_id}/uploaded/
        actual_download_dir = Path(f"/tmp/conversions/{mock_job_id}/uploaded/")
        # Filename is 'some_file_no_ext' (no extension added since content-type doesn't match)
        expected_file_path = actual_download_dir / "some_file_no_ext"
        assert result.success is True
        assert result.file_path == expected_file_path
        assert result.file_name == "some_file_no_ext"
        assert expected_file_path.read_bytes() == b"java archive"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "status_code, error_type_expected",
        [(404, "HTTP error 404"), (500, "HTTP error 500"), (403, "HTTP error 403")],
    )
    @mock.patch("src.file_processor.httpx.AsyncClient")
    async def test_download_from_url_http_errors(
        self,
        MockAsyncClient,
        file_processor,
        mock_job_id,
        status_code,
        error_type_expected,
        temp_job_dirs,
    ):
        mock_response = mock.AsyncMock(spec=httpx.Response)
        mock_response.status_code = status_code
        mock_response.text = f"Server error details for {status_code}"
        mock_response.request = httpx.Request(
            "GET", "http://example.com/error_url"
        )  # Needed for raise_for_status

        # Configure raise_for_status to raise HTTPStatusError
        mock_response.raise_for_status = mock.Mock(
            side_effect=httpx.HTTPStatusError(
                message=f"Error response {status_code}",
                request=mock_response.request,
                response=mock_response,
            )
        )

        MockAsyncClient.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        url = "http://example.com/error_url"
        result = await file_processor.download_from_url(url, mock_job_id)

        assert result.success is False
        assert result.file_path is None
        assert (
            f"http error {status_code}" in result.message.lower()
        )  # Check if "HTTP error XYZ" is in the message

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exception_type, error_message_expected_part",
        [
            (httpx.TimeoutException, "Timeout while downloading"),
            (
                httpx.RequestError,
                "Request error while downloading",
            ),  # Generic network error
            (
                IOError,
                "IO error saving downloaded file",
            ),  # Simulate an issue during file write
        ],
    )
    @mock.patch("src.file_processor.httpx.AsyncClient")
    async def test_download_from_url_network_io_exceptions(
        self,
        MockAsyncClient,
        file_processor,
        mock_job_id,
        exception_type,
        error_message_expected_part,
        temp_job_dirs,
    ):
        if exception_type == IOError:
            # For IOError, the client.get call succeeds, but writing the file fails
            mock_response = mock.AsyncMock(spec=httpx.Response)
            mock_response.status_code = 200
            mock_response.headers = {
                "Content-Disposition": 'attachment; filename="io_error_test.zip"'
            }
            mock_response.url = httpx.URL("http://example.com/io_error_test.zip")

            async def mock_aiter_bytes_io():
                yield b"data"

            mock_response.aiter_bytes = mock_aiter_bytes_io
            MockAsyncClient.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            # Patch open to raise IOError when writing
            with mock.patch("builtins.open", mock.mock_open()) as mock_file_open:
                mock_file_open.side_effect = IOError("Simulated disk full error")
                result = await file_processor.download_from_url(
                    "http://example.com/io_error_test.zip", mock_job_id
                )
        else:
            # For httpx exceptions, the client.get call itself fails
            MockAsyncClient.return_value.__aenter__.return_value.get.side_effect = (
                exception_type("Simulated network/timeout error")
            )
            result = await file_processor.download_from_url(
                "http://example.com/network_error_url", mock_job_id
            )

        assert result.success is False
        assert result.file_path is None
        assert error_message_expected_part.lower() in result.message.lower()

    @pytest.mark.asyncio
    @mock.patch("src.file_processor.httpx.AsyncClient")
    async def test_download_from_url_empty_file(
        self, MockAsyncClient, file_processor, mock_job_id, temp_job_dirs
    ):
        mock_response = mock.AsyncMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Disposition": 'attachment; filename="empty.zip"'
        }
        mock_response.url = httpx.URL("http://example.com/empty.zip")

        async def mock_aiter_bytes_empty():
            if False:  # Ensure it's an async generator but yields nothing
                yield

        mock_response.aiter_bytes = mock_aiter_bytes_empty
        MockAsyncClient.return_value.__aenter__.return_value.get.return_value = (
            mock_response
        )

        url = "http://example.com/empty.zip"
        with mock.patch("src.file_processor.logger.warning") as mock_logger_warning:
            result = await file_processor.download_from_url(url, mock_job_id)

            # FileProcessor creates its own directory structure at /tmp/conversions/{job_id}/uploaded/
            actual_download_dir = Path(f"/tmp/conversions/{mock_job_id}/uploaded/")
            expected_file_path = actual_download_dir / "empty.zip"

            assert result.success is True  # Download itself technically succeeded
            assert result.file_path == expected_file_path
            assert result.file_name == "empty.zip"
            assert expected_file_path.exists()
            assert expected_file_path.stat().st_size == 0
            mock_logger_warning.assert_any_call(
                f"Downloaded file {expected_file_path} is empty for URL: {url}, job_id: {mock_job_id}"
            )

    # --- Tests for validate_downloaded_file ---
    @pytest.mark.asyncio
    async def test_validate_downloaded_file_valid(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        # Create a valid mock zip file (just needs magic number and to exist)
        # FileProcessor.ZIP_MAGIC_NUMBER is b"PK\x03\x04"
        valid_file_path = temp_job_dirs["upload"] / "valid.zip"
        with open(valid_file_path, "wb") as f:
            f.write(FileProcessor.ZIP_MAGIC_NUMBER + b"restofzipcontent")

        result = await file_processor.validate_downloaded_file(
            valid_file_path, "http://example.com/valid.zip"
        )
        assert result.is_valid is True
        assert result.message == "Downloaded file validation successful."
        assert result.sanitized_filename == "valid.zip"
        assert result.validated_file_type == "zip"

    @pytest.mark.asyncio
    async def test_validate_downloaded_file_valid_jar_extension(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        valid_file_path = temp_job_dirs["upload"] / "valid.jar"  # Ends with .jar
        with open(valid_file_path, "wb") as f:
            f.write(FileProcessor.ZIP_MAGIC_NUMBER + b"jarcontent")

        result = await file_processor.validate_downloaded_file(
            valid_file_path, "http://example.com/valid.jar"
        )
        assert result.is_valid is True
        assert result.validated_file_type == "jar"  # Should be determined as jar

    @pytest.mark.asyncio
    async def test_validate_downloaded_file_oversized(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        oversized_file_path = temp_job_dirs["upload"] / "oversized.zip"
        with open(oversized_file_path, "wb") as f:
            f.write(FileProcessor.ZIP_MAGIC_NUMBER)  # Magic number is fine
            # Create a file larger than MAX_FILE_SIZE (default 500MB)
            # We don't need to write 500MB, just mock stat().st_size

        with mock.patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = file_processor.MAX_FILE_SIZE + 1
            result = await file_processor.validate_downloaded_file(
                oversized_file_path, "http://example.com/oversized.zip"
            )

        assert result.is_valid is False
        assert "exceeds maximum allowed size" in result.message
        assert result.sanitized_filename == "oversized.zip"

    @pytest.mark.asyncio
    async def test_validate_downloaded_file_empty(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        empty_file_path = temp_job_dirs["upload"] / "empty.zip"
        empty_file_path.touch()  # Create an empty file

        result = await file_processor.validate_downloaded_file(
            empty_file_path, "http://example.com/empty.zip"
        )

        assert result.is_valid is False
        assert "is empty" in result.message
        assert result.sanitized_filename == "empty.zip"

    @pytest.mark.asyncio
    async def test_validate_downloaded_file_invalid_magic_number(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        invalid_file_path = temp_job_dirs["upload"] / "invalid.zip"
        with open(invalid_file_path, "wb") as f:
            f.write(b"NOTPK\x03\x04" + b"restofcontent")  # Incorrect magic number

        result = await file_processor.validate_downloaded_file(
            invalid_file_path, "http://example.com/invalid.zip"
        )

        assert result.is_valid is False
        assert "Magic bytes do not match ZIP/JAR" in result.message
        assert result.sanitized_filename == "invalid.zip"

    @pytest.mark.asyncio
    async def test_validate_downloaded_file_not_found(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        non_existent_file_path = temp_job_dirs["upload"] / "notfound.zip"
        # Do not create the file

        result = await file_processor.validate_downloaded_file(
            non_existent_file_path, "http://example.com/notfound.zip"
        )

        assert result.is_valid is False
        assert "not found at path" in result.message
        assert result.sanitized_filename == "notfound.zip"

    # --- Tests for cleanup_temp_files ---
    def test_cleanup_temp_files_success(self, file_processor, mock_job_id):
        # Create a dummy job directory and a file within it
        job_dir_path = Path(f"/tmp/conversions/{mock_job_id}")
        job_dir_path.mkdir(parents=True, exist_ok=True)
        (job_dir_path / "some_file.txt").write_text("dummy content")

        assert job_dir_path.exists()

        with mock.patch("src.file_processor.shutil.rmtree") as mock_rmtree:
            result = file_processor.cleanup_temp_files(mock_job_id)

            assert result is True
            mock_rmtree.assert_called_once_with(job_dir_path)
            # In a real test without mocking rmtree, we'd assert job_dir_path.exists() is False
            # Since we mock it, we trust the call was made. If you want to test actual deletion,
            # then don't mock rmtree for this specific test case, but be careful with /tmp.
            # For this unit test, mocking is appropriate.

        # Manual cleanup if mock_rmtree was used, as the actual rmtree was patched.
        if job_dir_path.exists():
            shutil.rmtree(job_dir_path)

    def test_cleanup_temp_files_dir_not_exist(self, file_processor, mock_job_id):
        job_dir_path = Path(f"/tmp/conversions/{mock_job_id}")
        # Ensure directory does not exist (it shouldn't from previous tests if cleanup is good)
        if job_dir_path.exists():
            shutil.rmtree(job_dir_path)

        with mock.patch("src.file_processor.shutil.rmtree") as mock_rmtree:
            with mock.patch.object(
                logging.getLogger("src.file_processor"), "info"
            ) as mock_logger_info:
                result = file_processor.cleanup_temp_files(mock_job_id)

                assert result is True
                mock_rmtree.assert_not_called()
                mock_logger_info.assert_any_call(
                    f"Temporary directory {job_dir_path} not found for job_id: {mock_job_id}. No cleanup needed."
                )

    @mock.patch(
        "src.file_processor.shutil.rmtree",
        side_effect=PermissionError("Test permission error"),
    )
    @mock.patch.object(logging.getLogger("src.file_processor"), "error")
    def test_cleanup_temp_files_permission_error(
        self, mock_logger_error, mock_rmtree, file_processor, mock_job_id
    ):
        job_dir_path = Path(f"/tmp/conversions/{mock_job_id}")
        job_dir_path.mkdir(
            parents=True, exist_ok=True
        )  # Directory needs to exist for rmtree to be called
        (job_dir_path / "another_file.txt").write_text("content")

        result = file_processor.cleanup_temp_files(mock_job_id)

        assert result is False
        mock_rmtree.assert_called_once_with(job_dir_path)
        mock_logger_error.assert_called_once_with(
            f"Permission error while trying to delete {job_dir_path} for job_id: {mock_job_id}. Manual cleanup may be required.",
            exc_info=True,
        )
        # Manual cleanup - use subprocess since rmtree is mocked
        try:
            import subprocess

            if job_dir_path.exists():
                subprocess.run(["rm", "-rf", str(job_dir_path)], check=True)
        except Exception:
            pass  # If cleanup fails, that's okay for the test

    @mock.patch(
        "src.file_processor.shutil.rmtree", side_effect=Exception("Test generic error")
    )
    @mock.patch.object(logging.getLogger("src.file_processor"), "error")
    def test_cleanup_temp_files_generic_error(
        self, mock_logger_error, mock_rmtree, file_processor, mock_job_id
    ):
        job_dir_path = Path(f"/tmp/conversions/{mock_job_id}")
        job_dir_path.mkdir(parents=True, exist_ok=True)
        (job_dir_path / "generic_error_file.txt").write_text("content")

        result = file_processor.cleanup_temp_files(mock_job_id)

        assert result is False
        mock_rmtree.assert_called_once_with(job_dir_path)
        mock_logger_error.assert_called_once_with(
            f"An unexpected error occurred while deleting {job_dir_path} for job_id: {mock_job_id}: Test generic error",
            exc_info=True,
        )
        # Manual cleanup - use subprocess since rmtree is mocked
        try:
            import subprocess

            if job_dir_path.exists():
                subprocess.run(["rm", "-rf", str(job_dir_path)], check=True)
        except Exception:
            pass  # If cleanup fails, that's okay for the test

    # --- (Optional) Tests for validate_upload ---
    # These are more complex due to UploadFile interaction, might skip if focusing on the new/modified logic first

    # --- Tests for scan_for_malware ---

    @pytest.mark.asyncio
    async def test_scan_for_malware_safe_zip(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        """Test malware scan on a safe ZIP file."""
        import zipfile

        # Create a safe ZIP file
        safe_zip_path = temp_job_dirs["upload"] / "safe.zip"
        with zipfile.ZipFile(safe_zip_path, "w") as zip_file:
            zip_file.writestr("normal_file.txt", "This is normal content")
            zip_file.writestr("subdir/another_file.java", "public class Test {}")

        result = await file_processor.scan_for_malware(safe_zip_path, "zip")

        assert result.is_safe is True
        assert "passed implemented security checks" in result.message

    @pytest.mark.asyncio
    async def test_scan_for_malware_path_traversal_dotdot(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        """Test malware scan detects path traversal with .. sequences."""
        import zipfile

        # Create a ZIP with path traversal attempt
        malicious_zip_path = temp_job_dirs["upload"] / "malicious_dotdot.zip"
        with zipfile.ZipFile(malicious_zip_path, "w") as zip_file:
            zip_file.writestr("../../../etc/passwd", "root:x:0:0:root:/root:/bin/bash")
            zip_file.writestr("normal_file.txt", "Normal content")

        result = await file_processor.scan_for_malware(malicious_zip_path, "zip")

        assert result.is_safe is False
        assert "path traversal" in result.message.lower()
        assert "details" in result.model_dump()
        assert "../../../etc/passwd" in result.details["filename"]

    @pytest.mark.asyncio
    async def test_scan_for_malware_path_traversal_absolute(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        """Test malware scan detects absolute path traversal."""
        import zipfile

        # Create a ZIP with absolute path
        malicious_zip_path = temp_job_dirs["upload"] / "malicious_absolute.zip"
        with zipfile.ZipFile(malicious_zip_path, "w") as zip_file:
            zip_file.writestr("/etc/shadow", "root:$6$...")
            zip_file.writestr("normal_file.txt", "Normal content")

        result = await file_processor.scan_for_malware(malicious_zip_path, "zip")

        assert result.is_safe is False
        assert "path traversal" in result.message.lower()
        assert "/etc/shadow" in result.details["filename"]

    @pytest.mark.asyncio
    async def test_scan_for_malware_zip_bomb_compression_ratio(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        """Test malware scan detects ZIP bomb via high compression ratio."""
        import zipfile
        from unittest import mock

        # Create a ZIP file and mock its info to simulate a ZIP bomb
        zip_bomb_path = temp_job_dirs["upload"] / "zip_bomb.zip"
        with zipfile.ZipFile(zip_bomb_path, "w") as zip_file:
            zip_file.writestr("bomb.txt", "A" * 1000)  # Small content for real file

        # Mock the ZipFile.infolist to return a member with extreme compression ratio
        mock_member = mock.Mock()
        mock_member.filename = "bomb.txt"
        mock_member.file_size = 2 * 1024 * 1024 * 1024  # 2GB uncompressed
        mock_member.compress_size = 1024  # 1KB compressed (ratio > 100)

        with mock.patch("zipfile.ZipFile") as mock_zipfile:
            mock_zipfile.return_value.__enter__.return_value.infolist.return_value = [
                mock_member
            ]

            result = await file_processor.scan_for_malware(zip_bomb_path, "zip")

        assert result.is_safe is False
        assert "zip bomb" in result.message.lower()
        assert "extreme compression ratio" in result.message
        assert result.details["filename"] == "bomb.txt"
        assert result.details["ratio"] > 100

    @pytest.mark.asyncio
    async def test_scan_for_malware_excessive_files(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        """Test malware scan detects ZIP bomb via excessive file count."""
        import zipfile
        from unittest import mock

        zip_bomb_path = temp_job_dirs["upload"] / "file_bomb.zip"
        with zipfile.ZipFile(zip_bomb_path, "w") as zip_file:
            zip_file.writestr("test.txt", "test")

        # Mock to return excessive number of files
        mock_members = []
        for i in range(100001):  # Exceeds MAX_TOTAL_FILES (100000)
            mock_member = mock.Mock()
            mock_member.filename = f"file_{i}.txt"
            mock_member.file_size = 100
            mock_member.compress_size = 50
            mock_members.append(mock_member)

        with mock.patch("zipfile.ZipFile") as mock_zipfile:
            mock_zipfile.return_value.__enter__.return_value.infolist.return_value = (
                mock_members
            )

            result = await file_processor.scan_for_malware(zip_bomb_path, "zip")

        assert result.is_safe is False
        assert "zip bomb" in result.message.lower()
        assert "excessive number of files" in result.message
        assert result.details["num_files"] == 100001

    @pytest.mark.asyncio
    async def test_scan_for_malware_corrupted_archive(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        """Test malware scan handles corrupted ZIP files."""
        # Create a file that looks like ZIP but is corrupted
        corrupted_zip_path = temp_job_dirs["upload"] / "corrupted.zip"
        with open(corrupted_zip_path, "wb") as f:
            f.write(b"PK\x03\x04" + b"corrupted data that is not a valid zip")

        result = await file_processor.scan_for_malware(corrupted_zip_path, "zip")

        assert result.is_safe is False
        assert "invalid or corrupted" in result.message.lower()

    @pytest.mark.asyncio
    async def test_scan_for_malware_unsupported_file_type(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        """Test malware scan with unsupported file type."""
        # Create a dummy file
        text_file_path = temp_job_dirs["upload"] / "test.txt"
        text_file_path.write_text("This is just text")

        # scan_for_malware should handle non-archive types gracefully
        result = await file_processor.scan_for_malware(text_file_path, "txt")

        # Should pass basic checks since it's not an archive
        assert result.is_safe is True
        assert "passed implemented security checks" in result.message

    @pytest.mark.asyncio
    async def test_scan_for_malware_jar_file(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        """Test malware scan on JAR file (which is a ZIP)."""
        import zipfile

        # Create a safe JAR file
        safe_jar_path = temp_job_dirs["upload"] / "safe.jar"
        with zipfile.ZipFile(safe_jar_path, "w") as zip_file:
            zip_file.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            zip_file.writestr(
                "com/example/Main.class", b"\xCA\xFE\xBA\xBE"
            )  # Mock class file

        result = await file_processor.scan_for_malware(safe_jar_path, "jar")

        assert result.is_safe is True
        assert "passed implemented security checks" in result.message

    @pytest.mark.asyncio
    async def test_scan_for_malware_exception_handling(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        """Test malware scan handles unexpected exceptions."""
        zip_path = temp_job_dirs["upload"] / "test.zip"

        # Mock zipfile.ZipFile to raise an unexpected exception
        with mock.patch("zipfile.ZipFile", side_effect=Exception("Unexpected error")):
            result = await file_processor.scan_for_malware(zip_path, "zip")

        assert result.is_safe is False
        assert "error during archive scanning" in result.message.lower()
        assert "Unexpected error" in result.message

    @pytest.mark.asyncio
    async def test_scan_for_malware_edge_case_zero_compression(
        self, file_processor, temp_job_dirs, mock_job_id
    ):
        """Test malware scan handles zero compression size edge case."""
        import zipfile
        from unittest import mock

        zip_path = temp_job_dirs["upload"] / "zero_compression.zip"
        with zipfile.ZipFile(zip_path, "w") as zip_file:
            zip_file.writestr("test.txt", "test")

        # Mock member with zero compress_size to test division by zero protection
        mock_member = mock.Mock()
        mock_member.filename = "test.txt"
        mock_member.file_size = 1000
        mock_member.compress_size = 0  # This could cause division by zero

        with mock.patch("zipfile.ZipFile") as mock_zipfile:
            mock_zipfile.return_value.__enter__.return_value.infolist.return_value = [
                mock_member
            ]

            result = await file_processor.scan_for_malware(zip_path, "zip")

        # Should handle gracefully and not crash
        assert result.is_safe is True  # Should pass since division by zero is protected

    # --- (Optional) Tests for extract_mod_files ---
    # Similar to scan_for_malware, needs mock archives
    pass  # Placeholder for test methods


# Example of how to run: pytest backend/tests/unit/test_file_processor.py
# Remember to create __init__.py in directories if Python complains about imports.
# For these tests, assuming src.file_processor is importable from the test execution path.
# This might require setting PYTHONPATH environment variable or specific pytest configurations.
# e.g. export PYTHONPATH=$PYTHONPATH:./
# or in pytest.ini:
# [pytest]
# pythonpath = .
# (Assuming tests are run from the root of the repository)


# Basic test to ensure fixture and class setup is okay
def test_file_processor_instantiation(file_processor):
    assert isinstance(file_processor, FileProcessor)


def test_temp_job_dirs_fixture(temp_job_dirs):
    assert temp_job_dirs["base"].exists()
    assert temp_job_dirs["upload"].exists()
    assert temp_job_dirs["extracted"].exists()
    assert "test_job_123" in str(temp_job_dirs["upload"])  # from mock_job_id
    # Cleanup will be handled by the fixture's yield
