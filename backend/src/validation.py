from dataclasses import dataclass
from typing import Optional, IO
import magic  # type: ignore


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
        "application/x-jar",
        "application/octet-stream",  # For .mcaddon files and generic archives
    ]

    def validate_upload(self, file: IO[bytes], filename: str) -> ValidationResult:
        """
        Validate an uploaded file for size and MIME type constraints.

        This method performs comprehensive validation of uploaded files to ensure they
        meet security and functionality requirements for the mod conversion system.

        Parameters:
        -----------
        file : IO[bytes]
            The file object to validate. Must support seek(), tell(), and read() operations.
            The file pointer will be reset to the beginning after validation.
        filename : str
            The original filename of the uploaded file, used for error messaging.

        Returns:
        --------
        ValidationResult
            A dataclass containing:
            - is_valid (bool): True if file passes all validation checks
            - error_message (Optional[str]): Descriptive error message if validation fails

        Validation Steps:
        ----------------
        1. File Size Check: Ensures file does not exceed MAX_FILE_SIZE_BYTES (500MB)
        2. MIME Type Check: Uses python-magic to verify file is a valid ZIP or JAR archive
           - Reads first 2048 bytes for efficient MIME type detection
           - Validates against ALLOWED_MIME_TYPES list
           - Prevents malicious files with misleading extensions

        Note:
        -----
        The file pointer is automatically reset to the beginning after validation
        to ensure the file can be properly processed by subsequent operations.
        """
        # File Size Validation
        file.seek(0, 2)  # Move cursor to the end of the file
        file_size = file.tell()
        file.seek(0)  # Reset cursor to the beginning

        if file_size == 0:
            return ValidationResult(
                is_valid=False,
                error_message=f"File '{filename}' is empty and cannot be processed.",
            )

        if file_size > self.MAX_FILE_SIZE_BYTES:
            return ValidationResult(
                is_valid=False,
                error_message=f"File '{filename}' exceeds the maximum allowed size of {self.MAX_FILE_SIZE_MB}MB. File size: {file_size // (1024 * 1024)}MB",
            )

        # File Type Validation using python-magic
        # Read a chunk of the file for MIME type detection, not the whole file
        file_chunk = file.read(2048)  # Read the first 2048 bytes
        file.seek(0)  # Reset cursor to the beginning

        mime_type = magic.from_buffer(file_chunk, mime=True)

        if mime_type not in self.ALLOWED_MIME_TYPES:
            return ValidationResult(
                is_valid=False,
                error_message=f"File '{filename}' has an invalid file type: '{mime_type}'. Allowed types are ZIP and JAR archives.",
            )

        return ValidationResult(is_valid=True)
