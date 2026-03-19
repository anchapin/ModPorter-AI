"""
Input Validation Module for ModPorter AI

Comprehensive input validation for mod files, JAR archives, and Java source code.
Validates file structure, checks for malicious content, and enforces size limits.

Phase 10-03: Input Validation
"""

import io
import os
import re
import zipfile
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class ValidationErrorCode(Enum):
    """Error codes for validation failures."""
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    EXTRACTED_TOO_LARGE = "EXTRACTED_TOO_LARGE"
    INVALID_EXTENSION = "INVALID_EXTENSION"
    INVALID_JAR = "INVALID_JAR"
    MANIFEST_MISSING = "MANIFEST_MISSING"
    PATH_TRAVERSAL = "PATH_TRAVERSAL"
    SUSPICIOUS_CONTENT = "SUSPICIOUS_CONTENT"
    JAVA_SYNTAX_ERROR = "JAVA_SYNTAX_ERROR"
    TOO_MANY_FILES = "TOO_MANY_FILES"
    INVALID_PATH = "INVALID_PATH"
    INVALID_MIME_TYPE = "INVALID_MIME_TYPE"


@dataclass
class ValidationConfig:
    """Configuration for input validation."""

    # File limits
    max_file_size: int = 52428800  # 50MB
    max_extracted_size: int = 524288000  # 500MB
    max_java_files: int = 1000
    max_file_path_length: int = 260
    max_files_in_archive: int = 10000
    max_directory_depth: int = 20

    # Allowed types
    allowed_extensions: list = field(default_factory=lambda: [".jar", ".zip"])
    allowed_java_extensions: list = field(default_factory=lambda: [".java"])
    allowed_mime_types: list = field(default_factory=lambda: [
        "application/java-archive",
        "application/zip",
        "application/x-java-archive",
        "application/x-zip-compressed",
    ])

    # Security
    restricted_paths: list = field(default_factory=list)
    suspicious_patterns: list = field(default_factory=list)
    max_compression_ratio: float = 100.0

    # JAR validation
    jar_required_files: list = field(default_factory=list)
    jar_recommended_files: list = field(default_factory=list)
    validate_zip_structure: bool = True
    validate_manifest: bool = True
    max_manifest_size: int = 1048576
    check_duplicate_entries: bool = True

    # Java validation
    syntax_check: bool = True
    max_lines_per_file: int = 50000
    max_line_length: int = 10000
    validate_imports: bool = True
    check_common_errors: bool = True
    detect_mod_type: bool = True
    supported_java_versions: list = field(default_factory=lambda: ["1.8", "11", "17", "21"])

    # Error messages
    error_messages: dict = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, config_path: str) -> "ValidationConfig":
        """Load configuration from YAML file."""
        # Start with defaults
        config = cls()

        if not os.path.exists(config_path):
            return config

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}

        # Flatten nested config into the instance
        if "file_limits" in config_data:
            for key, value in config_data["file_limits"].items():
                if hasattr(config, key):
                    setattr(config, key, value)

        if "allowed_types" in config_data:
            for key, value in config_data["allowed_types"].items():
                if hasattr(config, key):
                    setattr(config, key, value)

        if "security" in config_data:
            for key, value in config_data["security"].items():
                if hasattr(config, key):
                    setattr(config, key, value)

        if "jar_validation" in config_data:
            for key, value in config_data["jar_validation"].items():
                if hasattr(config, key):
                    setattr(config, key, value)

        if "java_validation" in config_data:
            for key, value in config_data["java_validation"].items():
                if hasattr(config, key):
                    setattr(config, key, value)

        if "error_messages" in config_data:
            config.error_messages = config_data["error_messages"]

        return config

    @classmethod
    def from_default(cls) -> "ValidationConfig":
        """Create configuration with defaults."""
        config = cls()

        # Try to load from default location
        default_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "validation_config.yaml"
        )
        if os.path.exists(default_path):
            return cls.from_yaml(default_path)

        # Set default restricted paths
        config.restricted_paths = [
            "..", "../", "...", "~", "/etc", "/root", "/usr", "/bin", "/sbin", "/tmp",
            "C:\\", "D:\\", "C:", "CON", "PRN", "AUX", "NUL"
        ]

        # Set default suspicious patterns
        config.suspicious_patterns = [
            r".*\.sh$", r".*\.bash$", r".*\.ps1$", r".*\.bat$", r".*\.cmd$",
            r".*\.exe$", r".*\.dll$", r".*\.so$", r".*\.dylib$",
            r".*\.php$", r".*\.phtml$", r".*\.asp$", r".*\.aspx$", r".*\.jsp$",
            r".*\.\..*", r".*//.*//.*", r".*%00.*"
        ]

        # Set default JAR required files
        config.jar_required_files = ["META-INF/MANIFEST.MF"]
        config.jar_recommended_files = ["mcmod.info", "fabric.mod.json", "pack.mcmeta"]

        return config

    def get_error_message(self, code: ValidationErrorCode, **kwargs) -> str:
        """Get error message for code with formatting."""
        template = self.error_messages.get(code.value, f"Validation error: {code.value}")
        try:
            return template.format(**kwargs)
        except KeyError:
            return template


# ============================================================================
# Exceptions
# ============================================================================


class InputValidationError(Exception):
    """Custom exception for input validation errors."""

    def __init__(
        self,
        code: ValidationErrorCode,
        message: str,
        details: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }


# ============================================================================
# Validation Result
# ============================================================================


@dataclass
class ValidationError:
    """Single validation error."""
    code: ValidationErrorCode
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of input validation."""
    valid: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_error(self, code: ValidationErrorCode, message: str, **details):
        """Add an error to the result."""
        self.errors.append(ValidationError(code, message, details))
        self.valid = False

    def add_warning(self, message: str, **details):
        """Add a warning to the result."""
        self.warnings.append(ValidationError(ValidationErrorCode.INVALID_JAR, message, details))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "metadata": self.metadata,
        }


# ============================================================================
# Validators
# ============================================================================


class FileValidator:
    """Validates file properties like size, extension, path safety."""

    def __init__(self, config: ValidationConfig):
        self.config = config

    def validate_extension(self, filename: str) -> ValidationResult:
        """Check if file has an allowed extension."""
        result = ValidationResult(valid=True)

        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.config.allowed_extensions:
            result.add_error(
                ValidationErrorCode.INVALID_EXTENSION,
                self.config.get_error_message(
                    ValidationErrorCode.INVALID_EXTENSION,
                    extension=ext,
                    allowed=", ".join(self.config.allowed_extensions),
                ),
                filename=filename,
                extension=ext,
            )

        return result

    def validate_size(self, file_size: int) -> ValidationResult:
        """Check if file size is within limits."""
        result = ValidationResult(valid=True)

        if file_size > self.config.max_file_size:
            result.add_error(
                ValidationErrorCode.FILE_TOO_LARGE,
                self.config.get_error_message(
                    ValidationErrorCode.FILE_TOO_LARGE,
                    max_size=f"{self.config.max_file_size / 1024 / 1024:.1f}MB",
                ),
                file_size=file_size,
                max_size=self.config.max_file_size,
            )

        return result

    def validate_path_safety(self, filepath: str) -> ValidationResult:
        """Check for path traversal attempts."""
        result = ValidationResult(valid=True)

        # Normalize path
        normalized = os.path.normpath(filepath)

        # Check for restricted paths
        for restricted in self.config.restricted_paths:
            if restricted in normalized:
                result.add_error(
                    ValidationErrorCode.PATH_TRAVERSAL,
                    self.config.get_error_message(
                        ValidationErrorCode.PATH_TRAVERSAL,
                        path=filepath,
                    ),
                    filepath=filepath,
                    restricted=restricted,
                )
                break

        # Check path length
        if len(normalized) > self.config.max_file_path_length:
            result.add_error(
                ValidationErrorCode.INVALID_PATH,
                self.config.get_error_message(
                    ValidationErrorCode.INVALID_PATH,
                    path=filepath,
                ),
                path=filepath,
                length=len(normalized),
                max_length=self.config.max_file_path_length,
            )

        return result

    def scan_for_malware(self, filepath: str, content: Optional[bytes] = None) -> ValidationResult:
        """Scan for suspicious content patterns."""
        result = ValidationResult(valid=True)

        # If we have content, check it directly
        if content is not None:
            try:
                content_str = content.decode("utf-8", errors="ignore")
                for pattern in self.config.suspicious_patterns:
                    if re.search(pattern, content_str, re.IGNORECASE):
                        result.add_error(
                            ValidationErrorCode.SUSPICIOUS_CONTENT,
                            self.config.get_error_message(
                                ValidationErrorCode.SUSPICIOUS_CONTENT,
                                reason=f"Pattern match: {pattern}",
                            ),
                            pattern=pattern,
                            filepath=filepath,
                        )
                        break
            except Exception as e:
                logger.warning(f"Could not scan content for malware: {e}")

        return result


class JARValidator:
    """Validates JAR/ZIP archive structure and contents."""

    def __init__(self, config: ValidationConfig):
        self.config = config

    def validate_jar_structure(self, jar_path: str) -> ValidationResult:
        """Validate JAR/ZIP file structure."""
        result = ValidationResult(valid=True)

        try:
            with zipfile.ZipFile(jar_path, "r") as zf:
                # Test ZIP integrity
                bad_file = zf.testzip()
                if bad_file is not None:
                    result.add_error(
                        ValidationErrorCode.INVALID_JAR,
                        f"Corrupted file in archive: {bad_file}",
                        corrupted_file=bad_file,
                    )
                    return result

                # Check file count
                file_list = zf.namelist()
                if len(file_list) > self.config.max_files_in_archive:
                    result.add_error(
                        ValidationErrorCode.TOO_MANY_FILES,
                        self.config.get_error_message(
                            ValidationErrorCode.TOO_MANY_FILES,
                            count=len(file_list),
                            max=self.config.max_files_in_archive,
                        ),
                        file_count=len(file_list),
                        max_files=self.config.max_files_in_archive,
                    )

                # Check for path traversal in archive
                for filename in file_list:
                    path_result = self._validate_archive_path(filename)
                    if not path_result.valid:
                        result.errors.extend(path_result.errors)

                # Calculate extracted size
                total_size = sum(info.file_size for info in zf.infolist())
                if total_size > self.config.max_extracted_size:
                    result.add_error(
                        ValidationErrorCode.EXTRACTED_TOO_LARGE,
                        self.config.get_error_message(
                            ValidationErrorCode.EXTRACTED_TOO_LARGE,
                            max_size=f"{self.config.max_extracted_size / 1024 / 1024:.1f}MB",
                        ),
                        extracted_size=total_size,
                        max_size=self.config.max_extracted_size,
                    )

                # Check compression ratio
                compressed_size = sum(info.compress_size for info in zf.infolist())
                if compressed_size > 0:
                    ratio = total_size / compressed_size
                    if ratio > self.config.max_compression_ratio:
                        result.add_warning(
                            f"Abnormally high compression ratio: {ratio:.1f}",
                            compression_ratio=ratio,
                        )

                # Store metadata
                result.metadata = {
                    "file_count": len(file_list),
                    "total_size": total_size,
                    "compressed_size": compressed_size,
                }

        except zipfile.BadZipFile:
            result.add_error(
                ValidationErrorCode.INVALID_JAR,
                self.config.get_error_message(
                    ValidationErrorCode.INVALID_JAR,
                    reason="File is not a valid ZIP/JAR archive",
                ),
            )
        except Exception as e:
            result.add_error(
                ValidationErrorCode.INVALID_JAR,
                self.config.get_error_message(
                    ValidationErrorCode.INVALID_JAR,
                    reason=str(e),
                ),
                error=str(e),
            )

        return result

    def _validate_archive_path(self, filepath: str) -> ValidationResult:
        """Validate a path within the archive."""
        result = ValidationResult(valid=True)

        # Normalize and check
        normalized = os.path.normpath(filepath)

        # Check for path traversal
        if ".." in normalized.split(os.sep):
            result.add_error(
                ValidationErrorCode.PATH_TRAVERSAL,
                self.config.get_error_message(
                    ValidationErrorCode.PATH_TRAVERSAL,
                    path=filepath,
                ),
                filepath=filepath,
            )

        # Check path length
        if len(normalized) > self.config.max_file_path_length:
            result.add_error(
                ValidationErrorCode.INVALID_PATH,
                self.config.get_error_message(
                    ValidationErrorCode.INVALID_PATH,
                    path=filepath,
                ),
                path=filepath,
                length=len(normalized),
            )

        # Check for restricted paths
        for restricted in self.config.restricted_paths:
            if restricted in normalized:
                result.add_error(
                    ValidationErrorCode.PATH_TRAVERSAL,
                    self.config.get_error_message(
                        ValidationErrorCode.PATH_TRAVERSAL,
                        path=filepath,
                    ),
                    filepath=filepath,
                    restricted=restricted,
                )
                break

        return result

    def validate_manifest(self, jar_path: str) -> ValidationResult:
        """Parse and validate MANIFEST.MF."""
        result = ValidationResult(valid=True)

        try:
            with zipfile.ZipFile(jar_path, "r") as zf:
                # Check for manifest
                if "META-INF/MANIFEST.MF" not in zf.namelist():
                    result.add_warning(
                        "JAR manifest (META-INF/MANIFEST.MF) is missing",
                        manifest="META-INF/MANIFEST.MF",
                    )
                    return result

                # Read and validate manifest
                manifest_content = zf.read("META-INF/MANIFEST.MF")

                if len(manifest_content) > self.config.max_manifest_size:
                    result.add_error(
                        ValidationErrorCode.INVALID_JAR,
                        f"Manifest file too large: {len(manifest_content)} bytes",
                        manifest_size=len(manifest_content),
                    )
                    return result

                # Basic manifest parsing
                try:
                    manifest_text = manifest_content.decode("utf-8", errors="strict")
                    lines = manifest_text.split("\n")

                    # Check for required manifest headers
                    has_manifest_version = False
                    has_main_attributes = False

                    for line in lines:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if line.startswith("Manifest-Version:"):
                            has_manifest_version = True
                        if line.startswith("Created-By:"):
                            has_main_attributes = True

                    if not has_manifest_version:
                        result.add_warning(
                            "Manifest does not contain Manifest-Version header",
                        )

                    result.metadata["manifest"] = {
                        "size": len(manifest_content),
                        "has_version": has_manifest_version,
                        "has_created_by": has_main_attributes,
                    }

                except UnicodeDecodeError:
                    result.add_warning("Manifest contains invalid UTF-8 characters")

        except zipfile.BadZipFile:
            result.add_error(
                ValidationErrorCode.INVALID_JAR,
                "File is not a valid ZIP/JAR archive",
            )
        except Exception as e:
            result.add_warning(f"Could not validate manifest: {e}")

        return result

    def check_jar_size_limits(self, jar_path: str) -> ValidationResult:
        """Verify extracted size is within limits."""
        result = ValidationResult(valid=True)

        try:
            with zipfile.ZipFile(jar_path, "r") as zf:
                total_size = sum(info.file_size for info in zf.infolist())

                if total_size > self.config.max_extracted_size:
                    result.add_error(
                        ValidationErrorCode.EXTRACTED_TOO_LARGE,
                        self.config.get_error_message(
                            ValidationErrorCode.EXTRACTED_TOO_LARGE,
                            max_size=f"{self.config.max_extracted_size / 1024 / 1024:.1f}MB",
                        ),
                        extracted_size=total_size,
                        max_size=self.config.max_extracted_size,
                    )

        except Exception as e:
            result.add_error(
                ValidationErrorCode.INVALID_JAR,
                f"Could not check size limits: {e}",
            )

        return result

    def detect_suspicious_content(self, jar_path: str) -> ValidationResult:
        """Scan JAR for malicious or suspicious patterns."""
        result = ValidationResult(valid=True)

        try:
            with zipfile.ZipFile(jar_path, "r") as zf:
                file_list = zf.namelist()

                # Check for suspicious file patterns
                for filename in file_list:
                    for pattern in self.config.suspicious_patterns:
                        if re.search(pattern, filename, re.IGNORECASE):
                            result.add_warning(
                                f"Suspicious file pattern detected: {filename}",
                                filename=filename,
                                pattern=pattern,
                            )
                            break

                # Check for executable content
                suspicious_extensions = [".exe", ".dll", ".so", ".dylib", ".sh", ".bat"]
                for ext in suspicious_extensions:
                    matching = [f for f in file_list if f.lower().endswith(ext)]
                    if matching:
                        result.add_warning(
                            f"Potential executable found: {matching[0]}",
                            files=matching,
                        )

        except Exception as e:
            logger.warning(f"Could not scan for suspicious content: {e}")

        return result


class JavaSourceValidator:
    """Validates Java source code syntax and structure."""

    def __init__(self, config: ValidationConfig):
        self.config = config

    def validate_syntax(self, java_content: str, filename: str = "Unknown") -> ValidationResult:
        """Validate Java syntax using javalang."""
        result = ValidationResult(valid=True)

        # Check line count
        lines = java_content.split("\n")
        if len(lines) > self.config.max_lines_per_file:
            result.add_error(
                ValidationErrorCode.JAVA_SYNTAX_ERROR,
                f"File has too many lines: {len(lines)} (max: {self.config.max_lines_per_file})",
                line_count=len(lines),
                max_lines=self.config.max_lines_per_file,
            )
            return result

        # Check line lengths
        for i, line in enumerate(lines, 1):
            if len(line) > self.config.max_line_length:
                result.add_warning(
                    f"Line {i} exceeds maximum length: {len(line)} characters",
                    line=i,
                    length=len(line),
                )

        # Try to parse with javalang
        try:
            import javalang

            tree = javalang.parse.parse(java_content)
            result.metadata["parse_success"] = True
            result.metadata["imports"] = list(tree.imports) if tree.imports else []

        except ImportError:
            result.add_warning("javalang not available - skipping syntax validation")
            result.metadata["parse_success"] = None
        except javalang.parser.JavaSyntaxError as e:
            result.add_error(
                ValidationErrorCode.JAVA_SYNTAX_ERROR,
                self.config.get_error_message(
                    ValidationErrorCode.JAVA_SYNTAX_ERROR,
                    line=getattr(e, "line", 0),
                    error=str(e),
                ),
                line=getattr(e, "line", 0),
                error=str(e),
                filename=filename,
            )
        except Exception as e:
            result.add_warning(f"Could not parse Java syntax: {e}")

        return result

    def validate_imports(self, java_content: str) -> ValidationResult:
        """Check for valid Java imports."""
        result = ValidationResult(valid=True)

        if not self.config.validate_imports:
            return result

        try:
            import javalang

            tree = javalang.parse.parse(java_content)

            valid_imports = []
            invalid_imports = []

            for path, node in tree.filter(javalang.tree.Import):
                import_name = node.path
                if node.static or node.on_demand:
                    # These are harder to validate
                    valid_imports.append(import_name)
                else:
                    # Basic validation - check format
                    if "." in import_name:
                        valid_imports.append(import_name)
                    else:
                        invalid_imports.append(import_name)

            if invalid_imports:
                result.add_warning(
                    f"Invalid imports detected: {invalid_imports}",
                    invalid_imports=invalid_imports,
                )

            result.metadata["valid_imports"] = valid_imports
            result.metadata["invalid_imports"] = invalid_imports

        except ImportError:
            result.add_warning("javalang not available - skipping import validation")
        except Exception as e:
            logger.debug(f"Could not validate imports: {e}")

        return result

    def detect_forge_mod(self, java_content: str) -> ValidationResult:
        """Detect Forge mod patterns."""
        result = ValidationResult(valid=True)

        # Look for common Forge annotations and patterns
        forge_patterns = [
            r"@Mod",
            r"@Mod\.EventBusSubscriber",
            r"@ObjectHolder",
            r"extends\.+ForgeHooks",
            r"@SubscribeEvent",
            r"import\s+net\.minecraftforge",
            r"import\s+cpw\.mods\.fml",
        ]

        matches = []
        for pattern in forge_patterns:
            if re.search(pattern, java_content):
                matches.append(pattern)

        if matches:
            result.metadata["mod_type"] = "forge"
            result.metadata["forge_indicators"] = matches

        return result

    def detect_fabric_mod(self, java_content: str) -> ValidationResult:
        """Detect Fabric mod patterns."""
        result = ValidationResult(valid=True)

        # Look for common Fabric patterns
        fabric_patterns = [
            r"@Mod\(id\s*=",
            r"@Mixin",
            r"@Mixin\(.*\)",
            r"import\s+net\.fabricmc",
            r"import\s+net\.fabricmc\.api",
            r"implements\s+ModInitializer",
            r"implements\s+ClientModInitializer",
        ]

        matches = []
        for pattern in fabric_patterns:
            if re.search(pattern, java_content):
                matches.append(pattern)

        if matches:
            if result.metadata.get("mod_type") == "forge":
                result.add_warning(
                    "File contains indicators of both Forge and Fabric - may be incompatible"
                )
            else:
                result.metadata["mod_type"] = "fabric"
                result.metadata["fabric_indicators"] = matches

        return result


class InputValidator:
    """
    Main input validation class that coordinates all validators.

    This is the primary entry point for input validation.
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig.from_default()
        self.file_validator = FileValidator(self.config)
        self.jar_validator = JARValidator(self.config)
        self.java_validator = JavaSourceValidator(self.config)

    def validate_mod_file(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a mod file (JAR/ZIP).

        Args:
            file_path: Path to the file
            file_content: File content as bytes
            filename: Name of the file

        Returns:
            ValidationResult with validation status and details
        """
        result = ValidationResult(valid=True)

        # Determine filename
        if filename is None:
            if file_path:
                filename = os.path.basename(file_path)
            else:
                filename = "unknown.jar"

        # Get file content
        if file_content is None and file_path:
            try:
                with open(file_path, "rb") as f:
                    file_content = f.read()
            except Exception as e:
                result.add_error(
                    ValidationErrorCode.INVALID_JAR,
                    f"Could not read file: {e}",
                    file_path=file_path,
                )
                return result
        elif file_content is None:
            result.add_error(
                ValidationErrorCode.INVALID_JAR,
                "No file content or path provided",
            )
            return result

        # Get file size
        file_size = len(file_content)

        # Validate extension
        ext_result = self.file_validator.validate_extension(filename)
        result.errors.extend(ext_result.errors)
        if not ext_result.valid:
            result.valid = False

        # Validate size
        size_result = self.file_validator.validate_size(file_size)
        result.errors.extend(size_result.errors)
        if not size_result.valid:
            result.valid = False

        # Add file info to metadata
        result.metadata = {
            "filename": filename,
            "file_size": file_size,
            "extension": os.path.splitext(filename)[1],
        }

        # If already invalid, return early
        if not result.valid:
            return result

        # Write to temporary file for JAR validation
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            # Validate JAR structure
            jar_result = self.jar_validator.validate_jar_structure(tmp_path)
            result.errors.extend(jar_result.errors)
            result.warnings.extend(jar_result.warnings)
            result.metadata.update(jar_result.metadata)
            if not jar_result.valid:
                result.valid = False

            # Validate manifest if enabled
            if self.config.validate_manifest:
                manifest_result = self.jar_validator.validate_manifest(tmp_path)
                result.warnings.extend(manifest_result.warnings)
                result.metadata.update(manifest_result.metadata)

            # Check for suspicious content
            suspicious_result = self.jar_validator.detect_suspicious_content(tmp_path)
            result.warnings.extend(suspicious_result.warnings)

            # Check size limits
            size_result = self.jar_validator.check_jar_size_limits(tmp_path)
            result.errors.extend(size_result.errors)
            if not size_result.valid:
                result.valid = False

        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        return result

    def validate_java_source(
        self,
        java_content: str,
        filename: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate Java source code.

        Args:
            java_content: Java source code as string
            filename: Name of the Java file

        Returns:
            ValidationResult with validation status and details
        """
        result = ValidationResult(valid=True)

        if filename is None:
            filename = "Unknown.java"

        # Check extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.config.allowed_java_extensions:
            result.add_error(
                ValidationErrorCode.INVALID_EXTENSION,
                f"Invalid Java file extension: {ext}",
                extension=ext,
            )
            return result

        # Validate syntax
        if self.config.syntax_check:
            syntax_result = self.java_validator.validate_syntax(java_content, filename)
            result.errors.extend(syntax_result.errors)
            result.warnings.extend(syntax_result.warnings)
            result.metadata.update(syntax_result.metadata)
            if not syntax_result.valid:
                result.valid = False

        # Validate imports
        if self.config.validate_imports:
            import_result = self.java_validator.validate_imports(java_content)
            result.warnings.extend(import_result.warnings)
            result.metadata.update(import_result.metadata)

        # Detect mod type
        if self.config.detect_mod_type:
            forge_result = self.java_validator.detect_forge_mod(java_content)
            fabric_result = self.java_validator.detect_fabric_mod(java_content)

            mod_type = result.metadata.get("mod_type")
            if not mod_type:
                mod_type = forge_result.metadata.get("mod_type") or fabric_result.metadata.get("mod_type")
                if mod_type:
                    result.metadata["mod_type"] = mod_type

        result.metadata["filename"] = filename
        result.metadata["line_count"] = java_content.count("\n") + 1

        return result


# ============================================================================
# Utility Functions
# ============================================================================


def create_validator(config_path: Optional[str] = None) -> InputValidator:
    """Create an InputValidator with configuration."""
    if config_path and os.path.exists(config_path):
        config = ValidationConfig.from_yaml(config_path)
    else:
        config = ValidationConfig.from_default()

    return InputValidator(config)


# ============================================================================
# Main
# ============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"Validating: {file_path}")

        validator = create_validator()
        result = validator.validate_mod_file(file_path=file_path)

        print(f"\nValid: {result.valid}")
        print(f"Errors: {len(result.errors)}")
        for error in result.errors:
            print(f"  - {error.code.value}: {error.message}")

        print(f"Warnings: {len(result.warnings)}")
        for warning in result.warnings:
            print(f"  - {warning.message}")
    else:
        print("Usage: python input_validator.py <file_path>")
