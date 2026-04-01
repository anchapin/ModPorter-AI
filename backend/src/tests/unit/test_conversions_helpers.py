"""
Tests for conversions.py helper functions.

This module provides test coverage for:
- sanitize_filename function
- validate_path_safe function
- validate_file_type function
"""

import pytest
from pathlib import Path
import tempfile
import os

from api.conversions import (
    sanitize_filename,
    validate_path_safe,
    validate_file_type,
)


class TestSanitizeFilename:
    """Test cases for sanitize_filename function."""

    def test_simple_filename(self):
        """Test sanitizing a simple filename."""
        result = sanitize_filename("test.jar")
        assert result == "test.jar"

    def test_filename_with_path(self):
        """Test removing path components from filename."""
        result = sanitize_filename("/path/to/test.jar")
        assert result == "test.jar"

    def test_filename_with_backslash_path(self):
        """Test removing backslash path components."""
        result = sanitize_filename("C:\\Users\\test.jar")
        # Backslashes are removed, so this becomes CUserstest.jar
        assert result == "CUserstest.jar"

    def test_path_traversal_attempt(self):
        """Test blocking path traversal attempts."""
        result = sanitize_filename("../test.jar")
        assert ".." not in result

    def test_url_encoded_path_traversal(self):
        """Test blocking URL-encoded path traversal."""
        result = sanitize_filename("%2e%2e/test.jar")
        assert "%2e%2e" not in result
        assert result == "test.jar"

    def test_empty_filename(self):
        """Test handling empty filename."""
        result = sanitize_filename("")
        assert result == "uploaded_file"

    def test_only_special_characters(self):
        """Test filename with only special characters."""
        result = sanitize_filename("###@@@")
        assert result == "uploaded_file"

    def test_filename_starting_with_dot(self):
        """Test handling filename starting with period."""
        result = sanitize_filename(".hidden")
        assert result.startswith("file")

    def test_dangerous_characters_removed(self):
        """Test removing dangerous characters."""
        result = sanitize_filename("test<script>.jar")
        assert "<" not in result
        assert ">" not in result

    def test_preserves_safe_extensions(self):
        """Test preserving safe file extensions."""
        result = sanitize_filename("my_mod.jar")
        assert result == "my_mod.jar"

    def test_underscore_hyphen_preserved(self):
        """Test preserving underscores and hyphens."""
        result = sanitize_filename("my_test-mod.jar")
        assert result == "my_test-mod.jar"


class TestValidatePathSafe:
    """Test cases for validate_path_safe function."""

    def test_safe_path_inside_base(self):
        """Test path inside base directory is valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            result = validate_path_safe("subdir/file.txt", base)
            assert result is True

    def test_path_outside_base(self):
        """Test path outside base directory is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            result = validate_path_safe("../secret.txt", base)
            assert result is False

    def test_absolute_path_outside_base(self):
        """Test absolute path outside base is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            result = validate_path_safe("/etc/passwd", base)
            assert result is False

    def test_path_with_dot_outside_base(self):
        """Test path with dots outside base is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            result = validate_path_safe("subdir/../../secret.txt", base)
            assert result is False


class TestValidateFileType:
    """Test cases for validate_file_type function."""

    def test_valid_jar_file(self):
        """Test valid JAR file is accepted."""
        is_valid, error = validate_file_type("mod.jar")
        assert is_valid is True
        assert error == ""

    def test_valid_zip_file(self):
        """Test valid ZIP file is accepted."""
        is_valid, error = validate_file_type("archive.zip")
        assert is_valid is True
        assert error == ""

    def test_case_insensitive_extension(self):
        """Test extension check is case-insensitive."""
        is_valid, error = validate_file_type("mod.JAR")
        assert is_valid is True

    def test_invalid_exe_extension(self):
        """Test EXE file is rejected."""
        is_valid, error = validate_file_type("malware.exe")
        assert is_valid is False
        assert "not supported" in error.lower()

    def test_invalid_txt_extension(self):
        """Test TXT file is rejected."""
        is_valid, error = validate_file_type("readme.txt")
        assert is_valid is False

    def test_invalid_py_extension(self):
        """Test Python file is rejected."""
        is_valid, error = validate_file_type("script.py")
        assert is_valid is False