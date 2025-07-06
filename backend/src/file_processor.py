import logging
import os
import re
import shutil
import zipfile
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Dict

import httpx
from fastapi import UploadFile
from pydantic import BaseModel

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Note: For enhanced security, file processing operations (especially extraction and handling of potentially untrusted files)
# should ideally be executed within isolated, ephemeral containers (e.g., Docker) to limit potential impact from malicious files.


# --- Pydantic Models ---
class ValidationResult(BaseModel):
    is_valid: bool
    message: str
    sanitized_filename: Optional[str] = None
    validated_file_type: Optional[str] = None  # e.g., "jar", "zip"


class ScanResult(BaseModel):
    is_safe: bool
    message: str
    details: Optional[Dict] = None


class ExtractionResult(BaseModel):
    success: bool
    message: str
    extracted_files_count: int = 0
    manifest_data: Optional[Dict] = None
    found_manifest_type: Optional[str] = None


class DownloadResult(BaseModel):
    success: bool
    message: str
    file_path: Optional[Path] = None
    file_name: Optional[str] = None  # Sanitized filename
    # determined_file_type: Optional[str] = None # Could be added later if we can determine it


class FileProcessor:
    """
    A class to handle file processing tasks such as validation, malware scanning,
    extraction, downloading, and cleanup.
    """

    ALLOWED_MIME_TYPES: Dict[str, str] = {
        "application/java-archive": "jar",
        "application/zip": "zip",
        "application/x-zip-compressed": "zip",
    }
    # ZIP and JAR (which is a zip) magic number
    ZIP_MAGIC_NUMBER: bytes = b"PK\x03\x04"
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitizes a filename by removing potentially harmful characters.
        Allows alphanumerics, dots, hyphens, and underscores. Replaces others with an underscore.
        """
        if not filename:
            return "default_filename"
        # Get only the filename component
        base_filename = Path(filename).name
        # Replace invalid characters with an underscore
        sanitized = re.sub(r"[^\w.\-_]", "_", base_filename)
        # Prevent names that are just dots or start with a dot (like .bashrc) if not desired
        if sanitized.startswith("."):
            sanitized = "_" + sanitized[1:]
        if not sanitized:  # If filename became empty after sanitization
            return "default_sanitized_filename"
        return sanitized

    def validate_upload(self, file: UploadFile) -> ValidationResult:
        """
        Validates the uploaded file based on MIME type, magic numbers, size, and filename.
        """
        logger.info(f"Starting validation for uploaded file: {file.filename}")

        # 1. Sanitize filename first
        sanitized_filename = self._sanitize_filename(file.filename)
        logger.info(f"Sanitized filename: {sanitized_filename}")

        # 2. Check file size
        if file.size > self.MAX_FILE_SIZE:
            msg = f"File size {file.size} exceeds maximum allowed size of {self.MAX_FILE_SIZE} bytes."
            logger.warning(msg)
            return ValidationResult(
                is_valid=False, message=msg, sanitized_filename=sanitized_filename
            )
        logger.info(f"File size {file.size} is within limits.")

        # 3. Check file type using magic numbers and content type
        try:
            # Read the first few bytes for magic number checking
            file.file.seek(0)  # Ensure we are at the beginning of the file
            magic_bytes = file.file.read(4)
            file.file.seek(0)  # Reset cursor for other operations if needed

            determined_file_type = None
            if magic_bytes == self.ZIP_MAGIC_NUMBER:
                # It could be a ZIP or a JAR. We can use the content_type to hint.
                # If content_type is java-archive, we prefer 'jar'.
                if file.content_type == "application/java-archive":
                    determined_file_type = "jar"
                else:  # Otherwise, treat as 'zip'. This covers general zip and x-zip-compressed.
                    determined_file_type = "zip"
                logger.info(
                    f"Magic bytes match ZIP/JAR for uploaded file. Content-type: {file.content_type}. Determined type: {determined_file_type}"
                )
            else:
                msg = f"Invalid file type for uploaded file {sanitized_filename}: Magic bytes do not match ZIP/JAR."
                logger.warning(msg)
                return ValidationResult(
                    is_valid=False, message=msg, sanitized_filename=sanitized_filename
                )

            if determined_file_type not in self.ALLOWED_MIME_TYPES.values():
                msg = f"Determined file type '{determined_file_type}' for uploaded file {sanitized_filename} is not in allowed types."
                logger.warning(msg)
                return ValidationResult(
                    is_valid=False, message=msg, sanitized_filename=sanitized_filename
                )

            logger.info(
                f"Uploaded file {sanitized_filename} validated successfully as type: {determined_file_type}."
            )
            return ValidationResult(
                is_valid=True,
                message="File validation successful.",
                sanitized_filename=sanitized_filename,
                validated_file_type=determined_file_type,
            )

        except Exception as e:
            msg = f"An error occurred during file validation for {sanitized_filename}: {e}"
            logger.error(msg)
            return ValidationResult(
                is_valid=False, message=msg, sanitized_filename=sanitized_filename
            )

    async def validate_downloaded_file(
        self, file_path: Path, original_url: str
    ) -> ValidationResult:
        """
        Validates a downloaded file based on its path, size, and magic numbers.
        The original_url is used for logging context.
        """
        sanitized_filename = file_path.name  # Already sanitized by download_from_url
        logger.info(
            f"Starting validation for downloaded file: {sanitized_filename} from URL: {original_url}"
        )

        # 1. Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                msg = f"Downloaded file {sanitized_filename} size {file_size} exceeds maximum allowed size of {self.MAX_FILE_SIZE} bytes."
                logger.warning(msg)
                return ValidationResult(
                    is_valid=False, message=msg, sanitized_filename=sanitized_filename
                )
            if file_size == 0:
                msg = f"Downloaded file {sanitized_filename} is empty."
                logger.warning(msg)
                return ValidationResult(
                    is_valid=False, message=msg, sanitized_filename=sanitized_filename
                )
            logger.info(
                f"Downloaded file {sanitized_filename} size {file_size} is within limits."
            )
        except FileNotFoundError:
            msg = f"Downloaded file {sanitized_filename} not found at path {file_path} for validation."
            logger.error(msg)
            return ValidationResult(
                is_valid=False, message=msg, sanitized_filename=sanitized_filename
            )
        except Exception as e:
            msg = f"Error accessing file {sanitized_filename} for size validation: {e}"
            logger.error(msg, exc_info=True)
            return ValidationResult(
                is_valid=False, message=msg, sanitized_filename=sanitized_filename
            )

        # 2. Check file type using magic numbers
        try:
            with open(file_path, "rb") as f:
                magic_bytes = f.read(4)

            determined_file_type = None
            file_extension = file_path.suffix.lower()  # e.g. '.jar', '.zip'

            if magic_bytes == self.ZIP_MAGIC_NUMBER:
                # If magic bytes match ZIP, decide if it's 'jar' or 'zip' based on extension.
                # This is a common heuristic.
                if file_extension == ".jar":
                    determined_file_type = "jar"
                elif file_extension == ".zip":
                    determined_file_type = "zip"
                else:
                    # Magic bytes are ZIP, but extension is something else or missing.
                    # Default to 'zip' as the container type. Could also be an error/warning.
                    logger.warning(
                        f"File {sanitized_filename} has ZIP magic numbers but unexpected extension '{file_extension}'. Treating as 'zip'."
                    )
                    determined_file_type = "zip"
                logger.info(
                    f"Magic bytes match ZIP/JAR for downloaded file {sanitized_filename}. Extension: {file_extension}. Determined type: {determined_file_type}"
                )
            else:
                msg = f"Invalid file type for downloaded file {sanitized_filename}: Magic bytes do not match ZIP/JAR."
                logger.warning(msg)
                return ValidationResult(
                    is_valid=False, message=msg, sanitized_filename=sanitized_filename
                )

            # Check if the determined type is one we generally allow (jar or zip)
            if determined_file_type not in self.ALLOWED_MIME_TYPES.values():
                # This case might be redundant if we only determine 'jar' or 'zip' above for PKZIP files
                msg = f"Determined file type '{determined_file_type}' for {sanitized_filename} is not one of the allowed archive types (jar, zip)."
                logger.warning(msg)
                return ValidationResult(
                    is_valid=False, message=msg, sanitized_filename=sanitized_filename
                )

            logger.info(
                f"Downloaded file {sanitized_filename} validated successfully as type: {determined_file_type}."
            )
            return ValidationResult(
                is_valid=True,
                message="Downloaded file validation successful.",
                sanitized_filename=sanitized_filename,
                validated_file_type=determined_file_type,
            )
        except Exception as e:
            msg = f"An error occurred during downloaded file validation for {sanitized_filename}: {e}"
            logger.error(msg, exc_info=True)
            return ValidationResult(
                is_valid=False, message=msg, sanitized_filename=sanitized_filename
            )

    async def scan_for_malware(self, file_path: Path, file_type: str) -> ScanResult:
        """
        Scans the specified file for malware, including ZIP bomb and path traversal checks.
        """
        logger.info(f"Starting malware scan for file: {file_path} (type: {file_type})")

        # Define limits for ZIP bomb detection
        MAX_COMPRESSION_RATIO = 100
        MAX_UNCOMPRESSED_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 1GB
        MAX_TOTAL_FILES = 100000
        # Hypothetical target directory for path traversal check
        # In a real scenario, this would be the actual job-specific temp extraction dir.
        HYPOTHETICAL_TARGET_EXTRACTION_DIR = Path("/tmp/safe_extraction_zone")

        if file_type in ["zip", "jar"]:
            try:
                with zipfile.ZipFile(file_path, "r") as archive:
                    num_files = 0
                    total_uncompressed_size = 0

                    for member in archive.infolist():
                        num_files += 1
                        total_uncompressed_size += member.file_size

                        # 1. Path Traversal Check
                        if "../" in member.filename or member.filename.startswith("/"):
                            msg = f"Potential path traversal detected in archive member: {member.filename}"
                            logger.warning(msg)
                            return ScanResult(
                                is_safe=False,
                                message=msg,
                                details={"filename": member.filename},
                            )

                        # Ensure resolved path stays within the hypothetical target directory
                        # This is a conceptual check; actual extraction needs careful handling.
                        abs_member_path = Path(
                            os.path.abspath(
                                os.path.join(
                                    HYPOTHETICAL_TARGET_EXTRACTION_DIR, member.filename
                                )
                            )
                        )
                        if not str(abs_member_path).startswith(
                            str(os.path.abspath(HYPOTHETICAL_TARGET_EXTRACTION_DIR))
                        ):
                            msg = f"Potential path traversal (resolved path escapes target) in: {member.filename}"
                            logger.warning(msg)
                            return ScanResult(
                                is_safe=False,
                                message=msg,
                                details={"filename": member.filename},
                            )

                        # 2. ZIP Bomb - Individual file check (highly compressed large file)
                        if (
                            member.file_size > 0 and member.compress_size > 0
                        ):  # Avoid division by zero
                            ratio = member.file_size / member.compress_size
                            if (
                                ratio > MAX_COMPRESSION_RATIO
                                and member.file_size > MAX_UNCOMPRESSED_FILE_SIZE
                            ):
                                msg = (
                                    f"Potential ZIP bomb: File {member.filename} has extreme compression ratio ({ratio:.2f}) "
                                    f"and large uncompressed size ({member.file_size} bytes)."
                                )
                                logger.warning(msg)
                                return ScanResult(
                                    is_safe=False,
                                    message=msg,
                                    details={
                                        "filename": member.filename,
                                        "ratio": ratio,
                                        "size": member.file_size,
                                    },
                                )

                    # 3. ZIP Bomb - Excessive number of files check
                    if num_files > MAX_TOTAL_FILES:
                        msg = f"Potential ZIP bomb: Archive contains excessive number of files ({num_files})."
                        logger.warning(msg)
                        return ScanResult(
                            is_safe=False, message=msg, details={"num_files": num_files}
                        )

                    logger.info(
                        f"Archive {file_path} passed ZIP bomb and path traversal checks. Total files: {num_files}, Total uncompressed size: {total_uncompressed_size}"
                    )

            except zipfile.BadZipFile:
                msg = f"Invalid or corrupted ZIP/JAR file: {file_path}"
                logger.warning(msg)
                return ScanResult(is_safe=False, message=msg)
            except Exception as e:
                msg = f"Error during archive scanning for {file_path}: {e}"
                logger.error(msg)
                return ScanResult(is_safe=False, message=msg)

        # Placeholder for External Scanner (e.g., ClamAV)
        logger.info(
            f"Placeholder for external malware scan (e.g., ClamAV) for file: {file_path}. Integration would occur here."
        )
        # In a real scenario, you would invoke an external scanner here.
        # For example:
        # external_scan_result = await some_external_scanner_service.scan(file_path)
        # if not external_scan_result.is_safe:
        #     logger.warning(f"External malware scan detected threats in {file_path}: {external_scan_result.details}")
        #     return ScanResult(is_safe=False, message="External scanner detected malware.", details=external_scan_result.details)

        # Current return assumes basic checks passed and no external scanner is integrated or it also passed.
        # If an external scanner was integrated, its result would need to be factored in here.
        logger.info(
            f"File {file_path} passed all implemented security checks (basic archive checks; no external scan performed)."
        )
        return ScanResult(
            is_safe=True, message="File passed implemented security checks."
        )

    async def extract_mod_files(
        self, archive_path: Path, job_id: str, file_type: str
    ) -> ExtractionResult:
        """
        Extracts files from the archive, performs path traversal checks, and looks for manifest files.
        """
        logger.info(
            f"Starting extraction for archive: {archive_path} (job_id: {job_id}, type: {file_type})"
        )
        extraction_dir = Path(f"/tmp/conversions/{job_id}/extracted/")
        extraction_dir.mkdir(parents=True, exist_ok=True)

        extracted_files_count = 0

        if file_type not in ["zip", "jar"]:
            return ExtractionResult(
                success=False,
                message=f"Unsupported file type for extraction: {file_type}",
            )

        try:
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                archive_members = zip_ref.infolist()
                logger.info(f"Archive contains {len(archive_members)} members.")

                for member in archive_members:
                    # Path traversal check (relative to extraction_dir)
                    # We are checking member.filename which is the path *inside* the zip.
                    if member.filename.startswith("/") or ".." in member.filename:
                        logger.warning(
                            f"Skipping potentially unsafe path in archive: {member.filename} for job_id: {job_id}"
                        )
                        continue  # Skip this file

                    # Further check to ensure the resolved path is within extraction_dir
                    # os.path.join will correctly handle member.filename if it's absolute,
                    # but Path.joinpath might not on its own depending on the system.
                    # The initial check for startswith('/') should catch explicit absolute paths.
                    # Forcing join from a root-like path helps, but zipfile.extract should also be safe.
                    target_path = extraction_dir.joinpath(member.filename).resolve()
                    if not str(target_path).startswith(str(extraction_dir.resolve())):
                        logger.warning(
                            f"Skipping file that would extract outside target directory: {member.filename} for job_id: {job_id}"
                        )
                        continue

                    # Skip directories, extract only files
                    if not member.is_dir():
                        zip_ref.extract(member, path=extraction_dir)
                        extracted_files_count += 1

                logger.info(
                    f"Extracted {extracted_files_count} files to {extraction_dir} for job_id: {job_id}"
                )

        except zipfile.BadZipFile:
            msg = f"Invalid or corrupted archive file: {archive_path} for job_id: {job_id}"
            logger.error(msg)
            return ExtractionResult(success=False, message=msg)
        except Exception as e:
            msg = f"Error during archive extraction for {archive_path}, job_id {job_id}: {e}"
            logger.error(msg, exc_info=True)
            return ExtractionResult(success=False, message=msg)

        # Manifest file validation
        manifest_data: Optional[Dict] = None
        found_manifest_type: Optional[str] = None
        manifest_files_priority = [
            "fabric.mod.json",
            "mods.toml",
            "mcmod.info",
        ]  # Order of preference

        # Handle .toml parsing with Python version compatibility
        import json

        tomllib = None
        toml_lib = None

        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # Fallback for Python <3.11

                logger.info("Using tomli for .toml parsing (Python <3.11)")
            except ImportError:
                try:
                    import toml as toml_lib  # Alternative fallback

                    logger.info("Using toml library for .toml parsing")
                except ImportError:
                    logger.warning(
                        "No TOML library found. .toml manifest parsing will be skipped. Install 'tomli' or 'toml' for TOML support."
                    )
                    tomllib = None
                    toml_lib = None

        for manifest_name in manifest_files_priority:
            potential_manifest_path = extraction_dir / manifest_name
            if potential_manifest_path.is_file():
                logger.info(
                    f"Found potential manifest file: {manifest_name} for job_id: {job_id}"
                )
                try:
                    if manifest_name.endswith(".json"):
                        with open(potential_manifest_path, "rb") as f:
                            manifest_data = json.load(f)
                            found_manifest_type = "json"
                    elif manifest_name.endswith(".toml"):
                        if tomllib:
                            with open(potential_manifest_path, "rb") as f:
                                manifest_data = tomllib.load(
                                    f
                                )  # tomllib/tomli.load takes a binary file
                                found_manifest_type = "toml"
                        elif toml_lib:
                            with open(potential_manifest_path, "r") as f:
                                manifest_data = toml_lib.load(
                                    f
                                )  # toml.load takes a text file
                                found_manifest_type = "toml"
                        else:
                            logger.warning(
                                f"Cannot parse {manifest_name} - no TOML library available for job_id: {job_id}"
                            )
                            continue
                    elif manifest_name.endswith(
                        ".info"
                    ):  # mcmod.info can be JSON-like but not always strictly
                        with open(potential_manifest_path, "rb") as f:
                            try:
                                manifest_data = json.load(f)
                                found_manifest_type = "mcmod.info (json)"
                            except json.JSONDecodeError:
                                logger.warning(
                                    f"Could not parse {manifest_name} as JSON for job_id: {job_id}. It might be a different format or malformed."
                                )
                                # Add custom parsing for .info if needed, or treat as plain text
                                manifest_data = {
                                    "raw_content": open(
                                        potential_manifest_path, "r"
                                    ).read()
                                }
                                found_manifest_type = "mcmod.info (raw)"

                        if manifest_data:
                            logger.info(
                                f"Successfully parsed {manifest_name} as {found_manifest_type} for job_id: {job_id}"
                            )
                            break  # Found and parsed, stop searching
                except Exception as e:
                    logger.error(
                        f"Error parsing manifest file {manifest_name} for job_id {job_id}: {e}",
                        exc_info=True,
                    )
                    manifest_data = {
                        "parsing_error": str(e)
                    }  # Store error in manifest_data
                    found_manifest_type = manifest_name + " (parse_error)"
                    # Don't break, allow trying other manifest files if this one failed to parse
            else:
                logger.debug(
                    f"Manifest file {manifest_name} not found at {potential_manifest_path} for job_id: {job_id}"
                )

        if not manifest_data:
            logger.info(
                f"No standard manifest file found or parsed for job_id: {job_id}"
            )
            message = "Extraction completed, but no standard manifest file (fabric.mod.json, mods.toml, mcmod.info) found or parsed."
        else:
            message = f"Extraction completed. Found and parsed {found_manifest_type}."

        return ExtractionResult(
            success=True,
            message=message,
            extracted_files_count=extracted_files_count,
            manifest_data=manifest_data,
            found_manifest_type=found_manifest_type,
        )

    async def download_from_url(self, url: str, job_id: str) -> DownloadResult:
        """
        Downloads a file from the specified URL.
        """
        logger.info(f"Starting download from URL: {url} for job_id: {job_id}")
        download_dir = Path(f"/tmp/conversions/{job_id}/uploaded/")
        download_dir.mkdir(parents=True, exist_ok=True)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True, timeout=30.0)
                response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses

                # Determine filename
                content_disposition = response.headers.get("Content-Disposition")
                filename_from_header = None
                if content_disposition:
                    # Parse Content-Disposition header using email.message
                    msg = EmailMessage()
                    msg["Content-Disposition"] = content_disposition
                    filename_from_header = msg.get_param(
                        "filename", header="Content-Disposition"
                    )

                if filename_from_header:
                    raw_filename = filename_from_header
                else:
                    # Use last part of URL path if no Content-Disposition
                    url_path = Path(response.url.path)
                    raw_filename = url_path.name if url_path.name else "downloaded_file"

                sanitized_filename = self._sanitize_filename(raw_filename)
                if not sanitized_filename.strip():  # Ensure not just whitespace
                    sanitized_filename = "downloaded_file_unnamed"

                # Ensure there's an extension, default if necessary.
                # This is a simplification; proper type detection is harder.
                if not Path(sanitized_filename).suffix:
                    # Try to guess from content-type if possible, otherwise default
                    content_type = response.headers.get("Content-Type", "").split("/")[
                        0
                    ]
                    if "zip" in content_type:
                        sanitized_filename += ".zip"
                    elif (
                        "java-archive" in content_type or "jar" in content_type
                    ):  # application/java-archive or application/x-jar
                        sanitized_filename += ".jar"
                    else:  # Default or unknown
                        logger.warning(
                            f"Could not determine extension for {url} from Content-Type: {content_type}. Defaulting to no specific extension or .bin if needed."
                        )
                        # If a specific default like .bin is needed, add it here.
                        # For now, it might save without one if Path(sanitized_filename).suffix is still empty.

                downloaded_file_path = download_dir / sanitized_filename

                # Save the file
                with open(downloaded_file_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)

                file_size = downloaded_file_path.stat().st_size
                if file_size == 0:
                    logger.warning(
                        f"Downloaded file {downloaded_file_path} is empty for URL: {url}, job_id: {job_id}"
                    )
                    # Optionally return success=False or a specific message

                logger.info(
                    f"Successfully downloaded {sanitized_filename} ({file_size} bytes) to {downloaded_file_path} for job_id: {job_id}"
                )
                return DownloadResult(
                    success=True,
                    message=f"File downloaded successfully as {sanitized_filename}",
                    file_path=downloaded_file_path,
                    file_name=sanitized_filename,
                )

        except httpx.TimeoutException:
            msg = f"Timeout while downloading from URL: {url} for job_id: {job_id}"
            logger.error(msg)
            return DownloadResult(success=False, message=msg)
        except httpx.HTTPStatusError as e:
            msg = f"HTTP error {e.response.status_code} while downloading from URL: {url} for job_id: {job_id} - {e.response.text[:200]}"
            logger.error(msg)
            return DownloadResult(success=False, message=msg)
        except httpx.RequestError as e:  # Covers network errors, DNS failures etc.
            msg = f"Request error while downloading from URL: {url} for job_id: {job_id} - {str(e)}"
            logger.error(msg)
            return DownloadResult(success=False, message=msg)
        except IOError as e:  # File system errors
            msg = f"IO error saving downloaded file for URL {url}, job_id {job_id}: {e}"
            logger.error(msg, exc_info=True)
            return DownloadResult(success=False, message=msg)
        except Exception as e:
            msg = f"An unexpected error occurred during download from {url} for job_id {job_id}: {e}"
            logger.error(msg, exc_info=True)
            return DownloadResult(success=False, message=msg)

    def cleanup_temp_files(self, job_id: str) -> bool:
        """
        Cleans up temporary files and directories associated with a job_id.
        This includes /tmp/conversions/{job_id}.
        Returns True if successful or directory didn't exist, False if deletion failed.
        """
        temp_job_path = Path(f"/tmp/conversions/{job_id}")
        logger.info(
            f"Attempting to cleanup temporary directory: {temp_job_path} for job_id: {job_id}"
        )

        if not temp_job_path.exists():
            logger.info(
                f"Temporary directory {temp_job_path} not found for job_id: {job_id}. No cleanup needed."
            )
            return True

        try:
            shutil.rmtree(temp_job_path)
            logger.info(
                f"Successfully cleaned up temporary directory: {temp_job_path} for job_id: {job_id}"
            )
            return True
        except PermissionError:
            logger.error(
                f"Permission error while trying to delete {temp_job_path} for job_id: {job_id}. Manual cleanup may be required.",
                exc_info=True,
            )
            return False
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while deleting {temp_job_path} for job_id: {job_id}: {e}",
                exc_info=True,
            )
            return False
