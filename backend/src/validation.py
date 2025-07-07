from dataclasses import dataclass
from typing import Optional, IO
import magic # type: ignore

@dataclass
class ValidationResult:
    is_valid: bool
    error_message: Optional[str] = None

class ValidationFramework:
    MAX_FILE_SIZE_MB = 500
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    ALLOWED_MIME_TYPES = [
        "application/zip",
        "application/java-archive",
        "application/x-jar"
    ]

    def validate_upload(self, file: IO[bytes], filename: str) -> ValidationResult:
        # File Size Validation
        file.seek(0, 2) # Move cursor to the end of the file
        file_size = file.tell()
        file.seek(0) # Reset cursor to the beginning

        if file_size > self.MAX_FILE_SIZE_BYTES:
            return ValidationResult(
                is_valid=False,
                error_message=f"File '{filename}' exceeds the maximum allowed size of {self.MAX_FILE_SIZE_MB}MB. File size: {file_size // (1024 * 1024)}MB"
            )

        # File Type Validation using python-magic
        # Read a chunk of the file for MIME type detection, not the whole file
        file_chunk = file.read(2048) # Read the first 2048 bytes
        file.seek(0) # Reset cursor to the beginning

        mime_type = magic.from_buffer(file_chunk, mime=True)

        if mime_type not in self.ALLOWED_MIME_TYPES:
            return ValidationResult(
                is_valid=False,
                error_message=f"File '{filename}' has an invalid file type: '{mime_type}'. Allowed types are ZIP and JAR archives."
            )

        return ValidationResult(is_valid=True)
