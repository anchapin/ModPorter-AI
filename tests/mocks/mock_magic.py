"""
Mock magic library for testing purposes.
This replaces the problematic python-magic library on Windows/Python 3.13.
"""

import os
from typing import Optional


class MockMagic:
    """Mock implementation of python-magic library."""

    def __init__(self, mime=False):
        self.mime = mime

    def from_buffer(self, _buffer: bytes) -> str:
        """Return mock MIME type or file description."""
        if self.mime:
            # Basic MIME type detection based on file signatures
            if _buffer.startswith(b'\x50\x4B\x03\x04'):
                return "application/zip"
            elif _buffer.startswith(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'):
                return "image/png"
            elif _buffer.startswith(b'\xFF\xD8\xFF'):
                return "image/jpeg"
            elif _buffer.startswith(b'PK'):
                return "application/java-archive"
            else:
                return "application/octet-stream"
        else:
            # Return basic description
            if _buffer.startswith(b'PK'):
                return "Java archive data"
            elif _buffer.startswith(b'\x89\x50\x4E\x47'):
                return "PNG image data"
            elif _buffer.startswith(b'\xFF\xD8\xFF'):
                return "JPEG image data"
            else:
                return "data"

    def from_file(self, filepath: str) -> str:
        """Return mock MIME type or file description for a file."""
        try:
            with open(filepath, 'rb') as f:
                buffer = f.read(1024)
            return self.from_buffer(buffer)
        except (IOError, OSError):
            return "cannot open"


def open(mime: bool = False) -> MockMagic:
    """Factory function to create a new MockMagic instance."""
    return MockMagic(mime=mime)


def detect_from_buffer(buffer: bytes, mime: bool = False) -> str:
    """Convenience function to detect content type from buffer."""
    magic = MockMagic(mime=mime)
    return magic.from_buffer(buffer)


def detect_from_filename(filepath: str, mime: bool = False) -> str:
    """Convenience function to detect content type from file."""
    magic = MockMagic(mime=mime)
    return magic.from_file(filepath)
