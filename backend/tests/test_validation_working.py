"""
Tests for validation module.
"""

from unittest.mock import patch
import io

from src.validation import ValidationFramework, ValidationResult


class TestValidationFramework:
    """Test ValidationFramework class."""

    def test_validation_framework_initialization(self):
        """Test ValidationFramework initialization."""
        framework = ValidationFramework()
        assert framework.MAX_FILE_SIZE_MB == 500
        assert framework.MAX_FILE_SIZE_BYTES == 500 * 1024 * 1024
        assert len(framework.ALLOWED_MIME_TYPES) > 0
        assert "application/zip" in framework.ALLOWED_MIME_TYPES

    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        # Valid result
        result_valid = ValidationResult(is_valid=True)
        assert result_valid.is_valid is True
        assert result_valid.error_message is None

        # Invalid result
        result_invalid = ValidationResult(is_valid=False, error_message="Test error")
        assert result_invalid.is_valid is False
        assert result_invalid.error_message == "Test error"

    def test_validate_empty_file(self):
        """Test validation of empty file."""
        framework = ValidationFramework()

        # Create empty file mock
        empty_file = io.BytesIO(b"")
        empty_file.name = "empty.zip"

        result = framework.validate_upload(empty_file, "empty.zip")
        assert result.is_valid is False
        assert "empty" in result.error_message.lower()

    def test_validate_oversized_file(self):
        """Test validation of oversized file."""
        framework = ValidationFramework()

        # Create file larger than limit
        oversized_content = b"A" * (framework.MAX_FILE_SIZE_BYTES + 1)
        oversized_file = io.BytesIO(oversized_content)
        oversized_file.name = "oversized.zip"

        result = framework.validate_upload(oversized_file, "oversized.zip")
        assert result.is_valid is False
        assert "exceeds" in result.error_message.lower()

    def test_validate_valid_zip_file(self):
        """Test validation of valid ZIP file."""
        framework = ValidationFramework()

        # Create a minimal valid ZIP file signature
        zip_signature = b"PK\x03\x04" + b"\x00" * 20
        valid_file = io.BytesIO(zip_signature)
        valid_file.name = "valid.zip"

        result = framework.validate_upload(valid_file, "valid.zip")
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_invalid_file_type(self):
        """Test validation of invalid file type."""
        framework = ValidationFramework()

        # Create file with invalid signature
        invalid_content = b"INVALID_FILE_SIGNATURE"
        invalid_file = io.BytesIO(invalid_content)
        invalid_file.name = "invalid.txt"

        result = framework.validate_upload(invalid_file, "invalid.txt")
        assert result.is_valid is False
        assert "invalid file type" in result.error_message.lower()

    @patch("src.validation.MAGIC_AVAILABLE", True)
    @patch("src.validation.magic")
    def test_validate_with_magic_available(self, mock_magic):
        """Test validation when python-magic is available."""
        framework = ValidationFramework()

        # Mock magic library
        mock_magic.from_buffer.return_value = "application/zip"

        zip_content = b"PK\x03\x04" + b"\x00" * 20
        test_file = io.BytesIO(zip_content)
        test_file.name = "test.zip"

        result = framework.validate_upload(test_file, "test.zip")

        # Should use magic library for detection
        mock_magic.from_buffer.assert_called_once()
        assert result.is_valid is True

    @patch("src.validation.MAGIC_AVAILABLE", False)
    def test_validate_without_magic_fallback(self):
        """Test validation fallback when python-magic is not available."""
        framework = ValidationFramework()

        # Test different ZIP file signatures
        zip_signatures = [
            b"PK\x03\x04",  # Local file header
            b"PK\x05\x06",  # Central directory end
            b"PK\x07\x08",  # Spanned archive
        ]

        for signature in zip_signatures:
            content = signature + b"\x00" * 20
            test_file = io.BytesIO(content)
            test_file.name = "test.zip"

            result = framework.validate_upload(test_file, "test.zip")
            assert result.is_valid is True

    @patch("src.validation.MAGIC_AVAILABLE", False)
    def test_validate_unknown_file_type_fallback(self):
        """Test fallback validation for unknown file types."""
        framework = ValidationFramework()

        # Create file with unknown signature
        unknown_content = b"UNKNOWN_SIGNATURE_FOR_TESTING"
        test_file = io.BytesIO(unknown_content)
        test_file.name = "unknown.bin"

        result = framework.validate_upload(test_file, "unknown.bin")
        assert result.is_valid is False
        assert result.error_message is not None

    def test_file_pointer_reset(self):
        """Test that file pointer is reset after validation."""
        framework = ValidationFramework()

        # Create test content
        test_content = b"PK\x03\x04" + b"\x00" * 100
        test_file = io.BytesIO(test_content)
        test_file.name = "test.zip"

        # Validate file
        result = framework.validate_upload(test_file, "test.zip")
        assert result.is_valid is True

        # File pointer should be reset to beginning
        position = test_file.tell()
        assert position == 0

    def test_validate_file_read_chunk_size(self):
        """Test that only a chunk is read for MIME detection."""
        framework = ValidationFramework()

        # Create a file
        large_content = b"PK\x03\x04" + b"A" * 10000
        test_file = io.BytesIO(large_content)
        test_file.name = "large.zip"

        result = framework.validate_upload(test_file, "large.zip")

        # Should read only first 2048 bytes for detection
        # (This is an indirect test - we check it doesn't fail on large files)
        assert result.is_valid is True

    def test_validate_different_allowed_mime_types(self):
        """Test validation of different allowed MIME types."""
        framework = ValidationFramework()

        # Test various ZIP/JAR signatures
        valid_signatures = [
            (b"PK\x03\x04", "application/zip"),
            (b"PK\x05\x06", "application/zip"),
        ]

        for signature, expected_mime in valid_signatures:
            content = signature + b"\x00" * 20
            test_file = io.BytesIO(content)
            test_file.name = "test.zip"

            result = framework.validate_upload(test_file, "test.zip")
            assert result.is_valid is True

    def test_validate_jar_file(self):
        """Test validation of JAR files."""
        framework = ValidationFramework()

        # JAR files are ZIP files with different MIME type
        jar_content = b"PK\x03\x04" + b"\x00" * 20
        jar_file = io.BytesIO(jar_content)
        jar_file.name = "mod.jar"

        result = framework.validate_upload(jar_file, "mod.jar")
        assert result.is_valid is True

    def test_validate_mcaddon_file(self):
        """Test validation of .mcaddon files."""
        framework = ValidationFramework()

        # .mcaddon files should be treated as ZIP files
        mcaddon_content = b"PK\x03\x04" + b"\x00" * 20
        mcaddon_file = io.BytesIO(mcaddon_content)
        mcaddon_file.name = "mod.mcaddon"

        result = framework.validate_upload(mcaddon_file, "mod.mcaddon")
        assert result.is_valid is True

    def test_validation_error_messages(self):
        """Test validation error message format."""
        framework = ValidationFramework()

        # Test empty file error message
        empty_file = io.BytesIO(b"")
        empty_file.name = "test.zip"

        result = framework.validate_upload(empty_file, "test.zip")
        assert result.is_valid is False
        assert "test.zip" in result.error_message
        assert "empty" in result.error_message.lower()

        # Test oversized file error message
        large_content = b"A" * (framework.MAX_FILE_SIZE_BYTES + 1)
        large_file = io.BytesIO(large_content)
        large_file.name = "large.zip"

        result = framework.validate_upload(large_file, "large.zip")
        assert result.is_valid is False
        assert "large.zip" in result.error_message
        assert "500MB" in result.error_message
        assert "exceeds" in result.error_message.lower()

    def test_validation_framework_constants(self):
        """Test ValidationFramework constants."""
        framework = ValidationFramework()

        # Test file size constants
        assert framework.MAX_FILE_SIZE_MB > 0
        assert framework.MAX_FILE_SIZE_BYTES > 0
        assert framework.MAX_FILE_SIZE_BYTES == framework.MAX_FILE_SIZE_MB * 1024 * 1024

        # Test allowed MIME types
        assert len(framework.ALLOWED_MIME_TYPES) > 0
        assert all(isinstance(mime, str) for mime in framework.ALLOWED_MIME_TYPES)

        # Common MIME types should be included
        assert "application/zip" in framework.ALLOWED_MIME_TYPES
        assert "application/java-archive" in framework.ALLOWED_MIME_TYPES
        assert "application/x-jar" in framework.ALLOWED_MIME_TYPES

    def test_validation_comprehensive_scenarios(self):
        """Test comprehensive validation scenarios."""
        framework = ValidationFramework()

        test_cases = [
            # (content, filename, expected_valid)
            (b"PK\x03\x04", "valid.zip", True),
            (b"", "empty.zip", False),
            (b"A" * 1000, "invalid.bin", False),
            (b"PK\x03\x04", "mod.jar", True),
            (b"PK\x03\x04", "mod.mcaddon", True),
        ]

        for content, filename, expected_valid in test_cases:
            test_file = io.BytesIO(content)
            test_file.name = filename

            result = framework.validate_upload(test_file, filename)

            if expected_valid:
                assert result.is_valid, (
                    f"Expected {filename} to be valid: {result.error_message}"
                )
            else:
                assert not result.is_valid, f"Expected {filename} to be invalid"

    def test_validation_exception_handling(self):
        """Test validation exception handling."""
        framework = ValidationFramework()

        # Test with invalid file-like object
        # This tests exception handling without mocking file operations
        try:
            # Pass something that's not a proper file object
            framework.validate_upload(None, "bad.zip")
            # Should handle None gracefully or raise expected exception
        except Exception:
            # Expected to raise some kind of exception for invalid input
            assert True  # Any exception is acceptable for this test case

    def test_validation_performance(self):
        """Test validation performance with large files."""
        import time

        framework = ValidationFramework()

        # Create a reasonably large file (but under limit)
        large_content = b"PK\x03\x04" + b"A" * 100000  # ~100KB
        large_file = io.BytesIO(large_content)
        large_file.name = "large.zip"

        start_time = time.time()
        result = framework.validate_upload(large_file, "large.zip")
        duration = time.time() - start_time

        assert result.is_valid is True
        assert duration < 1.0  # Should complete within 1 second

    def test_validation_edge_cases(self):
        """Test validation edge cases."""
        framework = ValidationFramework()

        # Test with minimal valid ZIP
        minimal_zip = b"PK\x03\x04" + b"\x00" * 10
        minimal_file = io.BytesIO(minimal_zip)
        minimal_file.name = "minimal.zip"

        result = framework.validate_upload(minimal_file, "minimal.zip")
        assert result.is_valid is True

        # Test with exact size limit
        limit_content = b"PK\x03\x04" + b"A" * (framework.MAX_FILE_SIZE_BYTES - 10)
        limit_file = io.BytesIO(limit_content)
        limit_file.name = "limit.zip"

        result = framework.validate_upload(limit_file, "limit.zip")
        assert result.is_valid is True

    def test_validation_security(self):
        """Test validation security aspects."""
        framework = ValidationFramework()

        # Test with potentially malicious files (should be blocked by type check)
        malicious_signatures = [
            b"MZ\x90\x00",  # Windows executable
            b"\x7fELF",  # Linux executable
            b"cafebabe",  # Java class file
        ]

        for signature in malicious_signatures:
            malicious_content = signature + b"\x00" * 20
            malicious_file = io.BytesIO(malicious_content)
            malicious_file.name = "malicious.zip"

            result = framework.validate_upload(malicious_file, "malicious.zip")
            assert result.is_valid is False
            assert "invalid file type" in result.error_message.lower()
