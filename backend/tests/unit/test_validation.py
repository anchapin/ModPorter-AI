import unittest
from io import BytesIO
from unittest.mock import patch

# Adjust the import path based on your project structure
from src.validation import ValidationFramework

class TestValidationFramework(unittest.TestCase):

    def setUp(self):
        self.framework = ValidationFramework()

    def test_validate_upload_valid_file(self):
        # Create a dummy ZIP file content (just needs the right magic bytes for python-magic)
        # A real ZIP file starts with 'PK'
        zip_content = b"PK\x03\x04" + b"\0" * (1024 * 1024 - 4)  # 1MB
        mock_file = BytesIO(zip_content)
        filename = "valid_archive.zip"

        # Mock magic.from_buffer to return a valid MIME type
        with patch("magic.from_buffer", return_value="application/zip") as mock_magic:
            result = self.framework.validate_upload(mock_file, filename)
            mock_magic.assert_called_once()
            self.assertTrue(result.is_valid)
            self.assertIsNone(result.error_message)

    def test_validate_upload_oversized_file(self):
        # Create a file larger than MAX_FILE_SIZE_BYTES (500MB)
        # We don't need actual content, just a file-like object that reports a large size
        oversized_content = b"a" * (self.framework.MAX_FILE_SIZE_BYTES + 1)
        mock_file = BytesIO(oversized_content)
        filename = "oversized_archive.zip"

        # No need to mock magic here as size check comes first
        result = self.framework.validate_upload(mock_file, filename)

        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.error_message)
        self.assertIn("exceeds the maximum allowed size", result.error_message)
        self.assertIn(str(self.framework.MAX_FILE_SIZE_MB) + "MB", result.error_message)

    def test_validate_upload_invalid_file_type_text(self):
        txt_content = b"This is a text file, not a zip."
        mock_file = BytesIO(txt_content)
        filename = "invalid_type.txt"

        with patch("magic.from_buffer", return_value="text/plain") as mock_magic:
            result = self.framework.validate_upload(mock_file, filename)
            mock_magic.assert_called_once()
            self.assertFalse(result.is_valid)
            self.assertIsNotNone(result.error_message)
            self.assertIn("invalid file type: 'text/plain'", result.error_message)

    def test_validate_upload_misleading_extension_is_actually_zip(self):
        # File is named .txt but is actually a zip
        zip_content = b"PK\x03\x04" + b"\0" * (1024 - 4)  # 1KB
        mock_file = BytesIO(zip_content)
        filename = "actually_a_zip.txt"

        with patch("magic.from_buffer", return_value="application/zip") as mock_magic:
            result = self.framework.validate_upload(mock_file, filename)
            mock_magic.assert_called_once()
            self.assertTrue(result.is_valid)
            self.assertIsNone(result.error_message)

    def test_validate_upload_java_archive_jar(self):
        # JAR files are also ZIP files, often detected as application/java-archive or application/zip
        jar_content = b"PK\x03\x04" + b"\0" * (2 * 1024 * 1024 - 4)  # 2MB
        mock_file = BytesIO(jar_content)
        filename = "valid_mod.jar"

        with patch(
            "magic.from_buffer", return_value="application/java-archive"
        ) as mock_magic:
            result = self.framework.validate_upload(mock_file, filename)
            mock_magic.assert_called_once()
            self.assertTrue(result.is_valid)
            self.assertIsNone(result.error_message)

    def test_validate_upload_alternative_jar_mime_type(self):
        # Some systems might detect JAR as application/x-jar
        jar_content = b"PK\x03\x04" + b"\0" * (1024 - 4)  # 1KB
        mock_file = BytesIO(jar_content)
        filename = "another_mod.jar"

        with patch("magic.from_buffer", return_value="application/x-jar") as mock_magic:
            result = self.framework.validate_upload(mock_file, filename)
            mock_magic.assert_called_once()
            self.assertTrue(result.is_valid)
            self.assertIsNone(result.error_message)

    def test_validate_upload_empty_file(self):
        empty_content = b""
        mock_file = BytesIO(empty_content)
        filename = "empty_file.zip"

        # Empty files should be rejected before MIME type checking
        result = self.framework.validate_upload(mock_file, filename)
        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.error_message)
        self.assertIn("is empty and cannot be processed", result.error_message)


if __name__ == "__main__":
    unittest.main()
