"""Tests for validation.py module."""

import pytest
import io
from unittest.mock import patch, MagicMock

from src.validation import ValidationFramework, ValidationResult


class TestValidationFramework:
    """Test cases for ValidationFramework class."""

    @pytest.fixture
    def framework(self):
        """Create a ValidationFramework instance."""
        return ValidationFramework()

    @pytest.fixture
    def valid_zip_file(self):
        """Create a valid ZIP file-like object."""
        # Create a mock ZIP file with PK header
        zip_content = b"PK\x03\x04" + b"\x00" * 100  # ZIP file signature + padding
        return io.BytesIO(zip_content)

    @pytest.fixture
    def large_file(self):
        """Create a file that exceeds size limit."""
        # Create a file larger than MAX_FILE_SIZE_BYTES
        large_content = b"\x00" * (ValidationFramework.MAX_FILE_SIZE_BYTES + 1)
        return io.BytesIO(large_content)

    @pytest.fixture
    def empty_file(self):
        """Create an empty file."""
        return io.BytesIO(b"")

    @pytest.fixture
    def invalid_file(self):
        """Create an invalid file (not a ZIP/JAR)."""
        # Random bytes that don't match ZIP signature
        return io.BytesIO(b"Hello, World! This is not a ZIP file.")

    def test_validation_framework_initialization(self, framework):
        """Test that ValidationFramework initializes with correct constants."""
        assert framework.MAX_FILE_SIZE_MB == 500
        assert framework.MAX_FILE_SIZE_BYTES == 500 * 1024 * 1024
        assert len(framework.ALLOWED_MIME_TYPES) > 0
        assert "application/zip" in framework.ALLOWED_MIME_TYPES
        assert "application/java-archive" in framework.ALLOWED_MIME_TYPES

    def test_validate_upload_success_with_magic(self, framework, valid_zip_file):
        """Test successful validation when python-magic is available."""
        with patch('src.validation.MAGIC_AVAILABLE', True), \
             patch('src.validation.magic') as mock_magic:
            
            mock_magic.from_buffer.return_value = "application/zip"
            
            result = framework.validate_upload(valid_zip_file, "test.zip")
            
            assert result.is_valid is True
            assert result.error_message is None
            mock_magic.from_buffer.assert_called_once()

    def test_validate_upload_success_without_magic(self, framework, valid_zip_file):
        """Test successful validation when python-magic is not available."""
        with patch('src.validation.MAGIC_AVAILABLE', False):
            result = framework.validate_upload(valid_zip_file, "test.jar")
            
            assert result.is_valid is True
            assert result.error_message is None

    def test_validate_upload_empty_file(self, framework, empty_file):
        """Test validation of empty file."""
        result = framework.validate_upload(empty_file, "empty.zip")
        
        assert result.is_valid is False
        assert "is empty" in result.error_message
        assert "empty.zip" in result.error_message

    def test_validate_upload_file_too_large(self, framework, large_file):
        """Test validation of file that exceeds size limit."""
        result = framework.validate_upload(large_file, "large.zip")
        
        assert result.is_valid is False
        assert "exceeds the maximum allowed size" in result.error_message
        assert "500MB" in result.error_message

    def test_validate_upload_invalid_mime_type_with_magic(self, framework, invalid_file):
        """Test validation of file with invalid MIME type."""
        with patch('src.validation.MAGIC_AVAILABLE', True), \
             patch('src.validation.magic') as mock_magic:
            
            mock_magic.from_buffer.return_value = "text/plain"
            
            result = framework.validate_upload(invalid_file, "invalid.txt")
            
            assert result.is_valid is False
            assert "Invalid file type" in result.error_message
            assert "text/plain" in result.error_message

    def test_validate_upload_invalid_mime_type_without_magic(self, framework, invalid_file):
        """Test validation of invalid file without python-magic."""
        with patch('src.validation.MAGIC_AVAILABLE', False):
            result = framework.validate_upload(invalid_file, "invalid.txt")
            
            assert result.is_valid is False
            assert "Invalid file type" in result.error_message

    def test_validate_upload_file_position_reset(self, framework, valid_zip_file):
        """Test that file position is reset after validation."""
        # Write some data and move position
        valid_zip_file.write(b"PK\x03\x04")
        valid_zip_file.seek(10)
        
        result = framework.validate_upload(valid_zip_file, "test.zip")
        
        # File should be back at position 0
        assert valid_zip_file.tell() == 0
        assert result.is_valid is True

    def test_validate_upload_different_zip_signatures(self, framework):
        """Test validation with different ZIP file signatures."""
        # Test PK\x03\x04 signature
        zip1 = io.BytesIO(b"PK\x03\x04")
        with patch('src.validation.MAGIC_AVAILABLE', False):
            result1 = framework.validate_upload(zip1, "test1.zip")
            assert result1.is_valid is True
        
        # Test PK\x05\x06 signature (empty archive)
        zip2 = io.BytesIO(b"PK\x05\x06")
        with patch('src.validation.MAGIC_AVAILABLE', False):
            result2 = framework.validate_upload(zip2, "test2.zip")
            assert result2.is_valid is True
        
        # Test PK\x07\x08 signature (spanned archive)
        zip3 = io.BytesIO(b"PK\x07\x08")
        with patch('src.validation.MAGIC_AVAILABLE', False):
            result3 = framework.validate_upload(zip3, "test3.zip")
            assert result3.is_valid is True

    def test_validate_upload_allowed_mime_types(self, framework, valid_zip_file):
        """Test validation with different allowed MIME types."""
        allowed_types = [
            "application/zip",
            "application/java-archive",
            "application/x-jar",
            "application/octet-stream",
            "application/x-zip-compressed",
            "application/x-zip",
            "multipart/x-zip"
        ]
        
        with patch('src.validation.MAGIC_AVAILABLE', True), \
             patch('src.validation.magic') as mock_magic:
            
            for mime_type in allowed_types:
                mock_magic.from_buffer.return_value = mime_type
                result = framework.validate_upload(valid_zip_file, f"test.{mime_type.split('/')[-1]}")
                assert result.is_valid is True, f"Failed for MIME type: {mime_type}"

    def test_validate_upload_disallowed_mime_type(self, framework, valid_zip_file):
        """Test validation with disallowed MIME types."""
        disallowed_types = [
            "text/plain",
            "image/png",
            "application/pdf",
            "video/mp4",
            "application/json"
        ]
        
        with patch('src.validation.MAGIC_AVAILABLE', True), \
             patch('src.validation.magic') as mock_magic:
            
            for mime_type in disallowed_types:
                mock_magic.from_buffer.return_value = mime_type
                result = framework.validate_upload(valid_zip_file, f"test.{mime_type.split('/')[-1]}")
                assert result.is_valid is False, f"Should have failed for MIME type: {mime_type}"
                assert "Invalid file type" in result.error_message

    def test_validate_read_file_chunk(self, framework, valid_zip_file):
        """Test that only a chunk of file is read for MIME detection."""
        with patch('src.validation.MAGIC_AVAILABLE', True), \
             patch('src.validation.magic') as mock_magic:
            
            mock_magic.from_buffer.return_value = "application/zip"
            
            # Add large amount of data to file
            valid_zip_file.write(b"PK\x03\x04" + b"\x00" * 10000)
            valid_zip_file.seek(0)
            
            framework.validate_upload(valid_zip_file, "test.zip")
            
            # Check that from_buffer was called (it reads from buffer)
            mock_magic.from_buffer.assert_called_once()
            # The argument should be the first 2048 bytes
            call_args = mock_magic.from_buffer.call_args[0]
            assert len(call_args[0]) <= 2048

    def test_validation_result_dataclass(self):
        """Test ValidationResult dataclass."""
        # Test with error
        result1 = ValidationResult(is_valid=False, error_message="Test error")
        assert result1.is_valid is False
        assert result1.error_message == "Test error"
        
        # Test without error
        result2 = ValidationResult(is_valid=True)
        assert result2.is_valid is True
        assert result2.error_message is None

    def test_validate_file_name_in_error_message(self, framework, empty_file):
        """Test that filename appears in error messages."""
        filename = "my_mod_file.zip"
        result = framework.validate_upload(empty_file, filename)
        
        assert result.is_valid is False
        assert filename in result.error_message

    def test_validate_file_size_mb_conversion(self, framework, large_file):
        """Test that file size is correctly converted to MB in error message."""
        # Create file 600MB
        mb_600 = 600 * 1024 * 1024
        large_600mb = io.BytesIO(b"\x00" * mb_600)
        
        result = framework.validate_upload(large_600mb, "huge.zip")
        
        assert result.is_valid is False
        assert "600MB" in result.error_message  # Should show actual file size in MB
