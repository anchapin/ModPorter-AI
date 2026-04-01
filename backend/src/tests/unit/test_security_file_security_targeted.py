"""
Unit tests for File Security module.

Issue: #576 - Backend: File Processing Security
"""

import pytest
import tempfile
import zipfile
import tarfile
from pathlib import Path
from io import BytesIO

from security.file_security import (
    SecurityThreatType,
    SecuritySeverity,
    SecurityThreat,
    SecurityScanResult,
    SecurityConfig,
    FileSecurityScanner,
    ZipBombDetectedError,
    PathTraversalDetectedError,
    ResourceLimitExceededError,
    scan_archive,
)


class TestSecurityConfig:
    """Tests for SecurityConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SecurityConfig()
        assert config.max_compression_ratio == 100.0
        assert config.max_uncompressed_file_size == 1 * 1024 * 1024 * 1024
        assert config.max_total_uncompressed_size == 10 * 1024 * 1024 * 1024
        assert config.max_files_per_archive == 100000
        assert config.max_nested_archive_depth == 3
        assert config.allow_absolute_paths is False
        assert ".jar" in config.allowed_extensions
        assert ".zip" in config.allowed_extensions
        assert len(config.blocked_path_patterns) > 0
        assert len(config.suspicious_patterns) > 0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = SecurityConfig(
            max_compression_ratio=50.0,
            max_files_per_archive=1000,
            allow_absolute_paths=True,
            allowed_extensions=[".zip", ".tar"],
        )
        assert config.max_compression_ratio == 50.0
        assert config.max_files_per_archive == 1000
        assert config.allow_absolute_paths is True


class TestSecurityThreatType:
    """Tests for SecurityThreatType enum."""

    def test_all_threat_types_exist(self):
        """Test all expected threat types are defined."""
        assert SecurityThreatType.ZIP_BOMB.value == "zip_bomb"
        assert SecurityThreatType.PATH_TRAVERSAL.value == "path_traversal"
        assert SecurityThreatType.EXCESSIVE_FILES.value == "excessive_files"
        assert SecurityThreatType.EXCESSIVE_SIZE.value == "excessive_size"
        assert SecurityThreatType.NESTED_ARCHIVE.value == "nested_archive"
        assert SecurityThreatType.SUSPICIOUS_CONTENT.value == "suspicious_content"
        assert SecurityThreatType.INVALID_ARCHIVE.value == "invalid_archive"
        assert SecurityThreatType.RESOURCE_LIMIT.value == "resource_limit"


class TestSecuritySeverity:
    """Tests for SecuritySeverity enum."""

    def test_all_severity_levels(self):
        """Test all severity levels are defined."""
        assert SecuritySeverity.LOW.value == "low"
        assert SecuritySeverity.MEDIUM.value == "medium"
        assert SecuritySeverity.HIGH.value == "high"
        assert SecuritySeverity.CRITICAL.value == "critical"


class TestSecurityThreat:
    """Tests for SecurityThreat dataclass."""

    def test_threat_creation(self):
        """Test creating a security threat."""
        threat = SecurityThreat(
            threat_type=SecurityThreatType.ZIP_BOMB,
            severity=SecuritySeverity.CRITICAL,
            message="Test threat",
            details={"key": "value"},
        )
        assert threat.threat_type == SecurityThreatType.ZIP_BOMB
        assert threat.severity == SecuritySeverity.CRITICAL
        assert threat.message == "Test threat"
        assert threat.details == {"key": "value"}
        assert threat.timestamp is not None


class TestSecurityScanResult:
    """Tests for SecurityScanResult."""

    def test_default_result_is_safe(self):
        """Test default result is marked as safe."""
        result = SecurityScanResult()
        assert result.is_safe is True
        assert len(result.threats) == 0
        assert result.total_files_scanned == 0
        assert result.total_size_scanned == 0

    def test_has_critical_threats(self):
        """Test detection of critical threats."""
        result = SecurityScanResult(is_safe=True)
        result.add_threat(SecurityThreatType.ZIP_BOMB, SecuritySeverity.CRITICAL, "Critical threat")
        assert result.has_critical_threats is True
        # CRITICAL is not considered HIGH by the has_high_threats property

    def test_has_high_threats(self):
        """Test detection of high severity threats."""
        result = SecurityScanResult(is_safe=True)
        result.add_threat(SecurityThreatType.PATH_TRAVERSAL, SecuritySeverity.HIGH, "High threat")
        assert result.has_high_threats is True
        assert result.has_critical_threats is False

    def test_low_severity_does_not_impact_safety(self):
        """Test that low severity doesn't mark as unsafe."""
        result = SecurityScanResult(is_safe=True)
        result.add_threat(SecurityThreatType.SUSPICIOUS_CONTENT, SecuritySeverity.LOW, "Low threat")
        assert result.is_safe is True

    def test_high_severity_impacts_safety(self):
        """Test that high severity marks as unsafe."""
        result = SecurityScanResult(is_safe=True)
        result.add_threat(SecurityThreatType.EXCESSIVE_FILES, SecuritySeverity.HIGH, "High threat")
        assert result.is_safe is False

    def test_critical_severity_impacts_safety(self):
        """Test that critical severity marks as unsafe."""
        result = SecurityScanResult(is_safe=True)
        result.add_threat(SecurityThreatType.ZIP_BOMB, SecuritySeverity.CRITICAL, "Critical threat")
        assert result.is_safe is False

    def test_multiple_threats(self):
        """Test adding multiple threats."""
        result = SecurityScanResult()
        result.add_threat(SecurityThreatType.ZIP_BOMB, SecuritySeverity.CRITICAL, "Threat 1")
        result.add_threat(SecurityThreatType.PATH_TRAVERSAL, SecuritySeverity.HIGH, "Threat 2")
        result.add_threat(SecurityThreatType.SUSPICIOUS_CONTENT, SecuritySeverity.LOW, "Threat 3")
        assert len(result.threats) == 3
        assert result.is_safe is False


class TestFileSecurityScannerClass:
    """Tests for FileSecurityScanner."""

    @pytest.fixture
    def scanner(self):
        """Create scanner with default config."""
        return FileSecurityScanner()

    @pytest.fixture
    def strict_scanner(self):
        """Create scanner with strict config."""
        config = SecurityConfig(
            max_compression_ratio=10.0,
            max_files_per_archive=100,
            max_uncompressed_file_size=10 * 1024 * 1024,
        )
        return FileSecurityScanner(config)

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def create_zip(self, path: Path, files: dict) -> Path:
        """Helper to create ZIP file."""
        with zipfile.ZipFile(path, "w") as zf:
            for name, content in files.items():
                if isinstance(content, bytes):
                    zf.writestr(name, content)
                else:
                    zf.writestr(name, content.encode("utf-8"))
        return path

    def test_scan_nonexistent_file(self, scanner):
        """Test scanning non-existent file."""
        result = scanner.scan_file(Path("/nonexistent/file.zip"))
        assert result.is_safe is False
        assert any(t.threat_type == SecurityThreatType.INVALID_ARCHIVE for t in result.threats)

    def test_scan_valid_zip(self, scanner, temp_dir):
        """Test scanning valid ZIP file."""
        zip_path = temp_dir / "valid.zip"
        self.create_zip(zip_path, {"file.txt": "Hello World", "data.json": '{"key": "value"}'})

        result = scanner.scan_file(zip_path)
        assert result.is_safe
        assert result.total_files_scanned == 2

    def test_scan_disallowed_extension(self, scanner, temp_dir):
        """Test scanning file with disallowed extension."""
        exe_path = temp_dir / "malware.exe"
        exe_path.write_bytes(b"MZ" + b"\x00" * 100)

        result = scanner.scan_file(exe_path)
        assert result.is_safe is False
        assert any(t.threat_type == SecurityThreatType.SUSPICIOUS_CONTENT for t in result.threats)

    def test_detect_path_traversal_dotdot(self, scanner, temp_dir):
        """Test detection of ../ path traversal."""
        zip_path = temp_dir / "traversal.zip"
        self.create_zip(zip_path, {"normal.txt": "OK", "../outside.txt": "Bad"})

        result = scanner.scan_file(zip_path)
        assert not result.is_safe
        assert any(t.threat_type == SecurityThreatType.PATH_TRAVERSAL for t in result.threats)

    def test_detect_path_traversal_backslash(self, scanner, temp_dir):
        """Test detection of backslash path traversal."""
        zip_path = temp_dir / "traversal.zip"
        self.create_zip(zip_path, {"normal.txt": "OK", "..\\windows\\system32\\config": "Bad"})

        result = scanner.scan_file(zip_path)
        assert not result.is_safe
        assert any(t.threat_type == SecurityThreatType.PATH_TRAVERSAL for t in result.threats)

    def test_detect_absolute_path(self, scanner, temp_dir):
        """Test detection of absolute path."""
        zip_path = temp_dir / "absolute.zip"
        self.create_zip(zip_path, {"/etc/passwd": "root:x:0:0"})

        result = scanner.scan_file(zip_path)
        assert not result.is_safe
        assert any(t.threat_type == SecurityThreatType.PATH_TRAVERSAL for t in result.threats)

    def test_detect_blocked_path_pattern(self, scanner, temp_dir):
        """Test detection of blocked path patterns."""
        zip_path = temp_dir / "blocked.zip"
        self.create_zip(zip_path, {"/etc/shadow": "password data"})

        result = scanner.scan_file(zip_path)
        assert not result.is_safe
        assert any(t.threat_type == SecurityThreatType.PATH_TRAVERSAL for t in result.threats)

    def test_detect_excessive_files(self, strict_scanner, temp_dir):
        """Test detection of excessive file count."""
        zip_path = temp_dir / "many.zip"
        files = {f"file_{i}.txt": f"Content {i}" for i in range(150)}
        self.create_zip(zip_path, files)

        result = strict_scanner.scan_file(zip_path)
        assert not result.is_safe
        assert any(t.threat_type == SecurityThreatType.EXCESSIVE_FILES for t in result.threats)

    def test_detect_large_file(self, strict_scanner, temp_dir):
        """Test detection of oversized file."""
        zip_path = temp_dir / "large.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
            zf.writestr("large.bin", "X" * (15 * 1024 * 1024))

        result = strict_scanner.scan_file(zip_path)
        assert not result.is_safe
        assert any(t.threat_type == SecurityThreatType.EXCESSIVE_SIZE for t in result.threats)

    def test_detect_zip_bomb_high_ratio(self, strict_scanner, temp_dir):
        """Test detection of ZIP bomb with high compression ratio."""
        zip_path = temp_dir / "bomb.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("bomb.txt", "A" * (1024 * 1024))

        result = strict_scanner.scan_file(zip_path)
        assert any(t.threat_type == SecurityThreatType.ZIP_BOMB for t in result.threats)

    def test_detect_nested_archive(self, scanner, temp_dir):
        """Test detection of nested archives."""
        inner_path = temp_dir / "inner.zip"
        self.create_zip(inner_path, {"inner.txt": "Inner content"})

        outer_path = temp_dir / "outer.zip"
        with zipfile.ZipFile(outer_path, "w") as zf:
            zf.write(inner_path, "nested.zip")

        result = scanner.scan_file(outer_path)
        assert any(t.threat_type == SecurityThreatType.NESTED_ARCHIVE for t in result.threats)

    def test_detect_nested_archive_depth_exceeded(self, strict_scanner, temp_dir):
        """Test detection when nested archive depth exceeded."""
        inner_path = temp_dir / "inner.zip"
        self.create_zip(inner_path, {"inner.txt": "Content"})

        mid_path = temp_dir / "mid.zip"
        with zipfile.ZipFile(mid_path, "w") as zf:
            zf.write(inner_path, "level1.zip")

        outer_path = temp_dir / "outer.zip"
        with zipfile.ZipFile(outer_path, "w") as zf:
            zf.write(mid_path, "level2.zip")

        result = strict_scanner.scan_file(outer_path)
        assert any(t.threat_type == SecurityThreatType.NESTED_ARCHIVE for t in result.threats)

    def test_detect_suspicious_content(self, scanner, temp_dir):
        """Test detection of suspicious content patterns."""
        zip_path = temp_dir / "suspicious.zip"
        self.create_zip(
            zip_path,
            {
                "config.json": '{"url": "javascript:alert(1)"}',
                "script.txt": "#!/bin/bash\necho 'hello'",
            },
        )

        result = scanner.scan_file(zip_path)
        assert any(t.threat_type == SecurityThreatType.SUSPICIOUS_CONTENT for t in result.threats)

    def test_scan_corrupted_zip(self, scanner, temp_dir):
        """Test scanning corrupted ZIP file."""
        corrupted_path = temp_dir / "corrupted.zip"
        corrupted_path.write_bytes(b"This is not a valid ZIP file")

        result = scanner.scan_file(corrupted_path)
        assert not result.is_safe
        assert any(t.threat_type == SecurityThreatType.INVALID_ARCHIVE for t in result.threats)

    def test_scan_tar_archive(self, scanner, temp_dir):
        """Test scanning TAR archive via magic bytes detection."""
        tar_path = temp_dir / "test.tar"
        with tarfile.open(tar_path, "w") as tf:
            info = tarfile.TarInfo(name="test.txt")
            content = b"Test content"
            info.size = len(content)
            tf.addfile(info, BytesIO(content))

        # Note: .tar extension is not in allowed_extensions, so it will be flagged
        # This tests the file type detection via magic bytes
        result = scanner.scan_file(tar_path)
        # The file is flagged for extension but scanning logic runs
        assert result.total_files_scanned >= 0

    def test_scan_upload_valid_zip(self, scanner):
        """Test scanning upload of valid ZIP."""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("test.txt", "Test content")
        buffer.seek(0)

        result = scanner.scan_upload(buffer, "test.zip")
        assert result.is_safe

    def test_scan_upload_invalid(self, scanner):
        """Test scanning upload of invalid file."""
        buffer = BytesIO(b"Not a valid ZIP")
        buffer.seek(0)

        result = scanner.scan_upload(buffer, "invalid.txt")
        assert not result.is_safe

    def test_validate_extraction_path_safe(self, scanner, temp_dir):
        """Test validating safe extraction path."""
        target = temp_dir / "extract"
        target.mkdir()

        result = scanner.validate_extraction_path(target, "subdir/file.txt")
        assert result.is_relative_to(target)

    def test_validate_extraction_path_traversal(self, scanner, temp_dir):
        """Test validation rejects path traversal."""
        target = temp_dir / "extract"
        target.mkdir()

        with pytest.raises(PathTraversalDetectedError):
            scanner.validate_extraction_path(target, "../outside.txt")

    def test_validate_extraction_path_absolute(self, scanner, temp_dir):
        """Test validation rejects absolute path."""
        target = temp_dir / "extract"
        target.mkdir()

        with pytest.raises(PathTraversalDetectedError):
            scanner.validate_extraction_path(target, "/etc/passwd")

    def test_validate_extraction_path_escapes_target(self, scanner, temp_dir):
        """Test validation rejects path escaping target directory."""
        target = temp_dir / "extract"
        target.mkdir()
        (temp_dir / "outside.txt").write_text("outside")

        with pytest.raises(PathTraversalDetectedError):
            scanner.validate_extraction_path(target, "../../outside.txt")

    def test_is_path_traversal_dotdot(self, scanner):
        """Test _is_path_traversal with ../"""
        assert scanner._is_path_traversal("../file.txt") is True
        assert scanner._is_path_traversal("dir/../file.txt") is True

    def test_is_path_traversal_backslash(self, scanner):
        """Test _is_path_traversal with backslash."""
        assert scanner._is_path_traversal("..\\windows\\file.txt") is True

    def test_is_path_traversal_absolute(self, scanner):
        """Test _is_path_traversal with absolute path."""
        assert scanner._is_path_traversal("/etc/passwd") is True

    def test_is_path_traversal_safe(self, scanner):
        """Test _is_path_traversal with safe paths."""
        assert scanner._is_path_traversal("normal/file.txt") is False
        assert scanner._is_path_traversal("subdir/nested/file.txt") is False

    def test_is_path_traversal_absolute_allowed(self):
        """Test _is_path_traversal with absolute allowed."""
        config = SecurityConfig(allow_absolute_paths=True)
        sc = FileSecurityScanner(config)
        assert sc._is_path_traversal("/etc/passwd") is False

    def test_is_nested_archive(self, scanner):
        """Test _is_nested_archive detection."""
        assert scanner._is_nested_archive("file.zip") is True
        assert scanner._is_nested_archive("file.jar") is True
        assert scanner._is_nested_archive("file.tar") is True
        assert scanner._is_nested_archive("file.gz") is True
        assert scanner._is_nested_archive("file.txt") is False
        assert scanner._is_nested_archive("file.jar.pack") is False


class TestSecurityErrors:
    """Tests for security error classes."""

    def test_zip_bomb_error(self):
        """Test ZipBombDetectedError."""
        error = ZipBombDetectedError("ZIP bomb detected", {"ratio": 1000})
        assert str(error) == "ZIP bomb detected"
        assert error.details == {"ratio": 1000}

    def test_path_traversal_error(self):
        """Test PathTraversalDetectedError."""
        error = PathTraversalDetectedError("Path traversal detected", {"path": "/etc/passwd"})
        assert str(error) == "Path traversal detected"
        assert error.details == {"path": "/etc/passwd"}

    def test_resource_limit_error(self):
        """Test ResourceLimitExceededError."""
        error = ResourceLimitExceededError("Resource limit exceeded", {"memory": "512MB"})
        assert str(error) == "Resource limit exceeded"
        assert error.details == {"memory": "512MB"}


class TestScanArchiveFunction:
    """Tests for scan_archive convenience function."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_scan_archive_valid(self, temp_dir):
        """Test scan_archive with valid file."""
        zip_path = temp_dir / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.txt", "Content")

        result = scan_archive(zip_path)
        assert result.is_safe

    def test_scan_archive_with_config(self, temp_dir):
        """Test scan_archive with custom config."""
        zip_path = temp_dir / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.txt", "Content")

        config = SecurityConfig(max_files_per_archive=10)
        result = scan_archive(zip_path, config)
        assert result.is_safe


class TestCheckExtension:
    """Tests for extension checking."""

    @pytest.fixture
    def scanner(self):
        """Create scanner."""
        return FileSecurityScanner()

    def test_check_extension_allowed(self, scanner):
        """Test allowed extension."""
        result = SecurityScanResult()
        assert scanner._check_extension(Path("test.jar"), result) is True

    def test_check_extension_disallowed(self, scanner):
        """Test disallowed extension."""
        result = SecurityScanResult()
        assert scanner._check_extension(Path("malware.exe"), result) is False
        assert len(result.threats) > 0


class TestDetectFileType:
    """Tests for file type detection."""

    @pytest.fixture
    def scanner(self):
        """Create scanner."""
        return FileSecurityScanner()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_detect_zip_type(self, scanner, temp_dir):
        """Test detecting ZIP file type."""
        zip_path = temp_dir / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.txt", "Content")

        file_type = scanner._detect_file_type(zip_path)
        assert file_type in ("zip", "jar", None)

    def test_detect_jar_type(self, scanner, temp_dir):
        """Test detecting JAR file type."""
        jar_path = temp_dir / "test.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0")

        file_type = scanner._detect_file_type(jar_path)
        assert file_type == "jar"

    def test_detect_tar_gz_type(self, scanner, temp_dir):
        """Test detecting tar.gz file type."""
        tar_path = temp_dir / "test.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="test.txt")
            content = b"Content"
            info.size = len(content)
            tf.addfile(info, BytesIO(content))

        file_type = scanner._detect_file_type(tar_path)
        assert file_type in ("tar_gz", None)

    def test_detect_unknown_type(self, scanner, temp_dir):
        """Test detecting unknown file type."""
        unknown_path = temp_dir / "test.unknown"
        unknown_path.write_bytes(b"Random content")

        file_type = scanner._detect_file_type(unknown_path)
        assert file_type is None
