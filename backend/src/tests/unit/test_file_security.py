"""
Unit tests for file security scanning.

Issue: #576 - Backend: File Processing Security
"""

import pytest
import tempfile
import zipfile
from pathlib import Path
from io import BytesIO

from backend.src.security.file_security import (
    FileSecurityScanner,
    SecurityConfig,
    SecurityScanResult,
    SecurityThreatType,
    SecuritySeverity,
    ZipBombDetectedError,
    PathTraversalDetectedError,
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
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = SecurityConfig(
            max_compression_ratio=50.0,
            max_files_per_archive=1000,
            allow_absolute_paths=True
        )
        
        assert config.max_compression_ratio == 50.0
        assert config.max_files_per_archive == 1000
        assert config.allow_absolute_paths is True


class TestFileSecurityScanner:
    """Tests for FileSecurityScanner."""
    
    @pytest.fixture
    def scanner(self):
        """Create a scanner with default config."""
        return FileSecurityScanner()
    
    @pytest.fixture
    def strict_scanner(self):
        """Create a scanner with strict config."""
        config = SecurityConfig(
            max_compression_ratio=10.0,
            max_files_per_archive=100,
            max_uncompressed_file_size=10 * 1024 * 1024  # 10MB
        )
        return FileSecurityScanner(config)
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def create_zip(
        self,
        path: Path,
        files: dict,
        compression: int = zipfile.ZIP_DEFLATED
    ) -> Path:
        """Helper to create a zip file."""
        with zipfile.ZipFile(path, 'w', compression=compression) as zf:
            for name, content in files.items():
                if isinstance(content, bytes):
                    zf.writestr(name, content)
                else:
                    zf.writestr(name, content.encode('utf-8'))
        return path
    
    def test_scan_valid_zip(self, scanner, temp_dir):
        """Test scanning a valid ZIP file."""
        zip_path = temp_dir / "valid.zip"
        self.create_zip(zip_path, {
            "file1.txt": "Hello, World!",
            "file2.json": '{"key": "value"}',
            "subdir/file3.txt": "Nested file"
        })
        
        result = scanner.scan_file(zip_path)
        
        assert result.is_safe
        assert len(result.threats) == 0
        assert result.total_files_scanned == 3
    
    def test_scan_valid_jar(self, scanner, temp_dir):
        """Test scanning a valid JAR file."""
        jar_path = temp_dir / "valid.jar"
        self.create_zip(jar_path, {
            "META-INF/MANIFEST.MF": "Manifest-Version: 1.0",
            "com/example/Example.class": b'\xca\xfe\xba\xbe' + b'\x00' * 100
        })
        
        result = scanner.scan_file(jar_path)
        
        assert result.is_safe
        assert result.total_files_scanned == 2
    
    def test_detect_path_traversal_dotdot(self, scanner, temp_dir):
        """Test detection of path traversal with ../"""
        zip_path = temp_dir / "traversal.zip"
        self.create_zip(zip_path, {
            "normal.txt": "Normal file",
            "../outside.txt": "Traversal attempt"
        })
        
        result = scanner.scan_file(zip_path)
        
        assert not result.is_safe
        assert any(
            t.threat_type == SecurityThreatType.PATH_TRAVERSAL
            for t in result.threats
        )
    
    def test_detect_path_traversal_absolute(self, scanner, temp_dir):
        """Test detection of absolute path traversal."""
        zip_path = temp_dir / "absolute.zip"
        self.create_zip(zip_path, {
            "/etc/passwd": "root:x:0:0:root:/root:/bin/bash"
        })
        
        result = scanner.scan_file(zip_path)
        
        assert not result.is_safe
        assert any(
            t.threat_type == SecurityThreatType.PATH_TRAVERSAL
            for t in result.threats
        )
    
    def test_detect_zip_bomb_high_ratio(self, strict_scanner, temp_dir):
        """Test detection of ZIP bomb with high compression ratio."""
        zip_path = temp_dir / "bomb.zip"
        
        # Create a file with highly compressible content
        # This will have a very high compression ratio
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1MB of repeated data compresses very small
            zf.writestr("bomb.txt", "A" * (1024 * 1024))
        
        result = strict_scanner.scan_file(zip_path)
        
        # Should detect high compression ratio
        assert any(
            t.threat_type == SecurityThreatType.ZIP_BOMB
            for t in result.threats
        )
    
    def test_detect_excessive_files(self, strict_scanner, temp_dir):
        """Test detection of excessive file count."""
        zip_path = temp_dir / "many_files.zip"
        
        files = {f"file_{i}.txt": f"Content {i}" for i in range(150)}
        self.create_zip(zip_path, files)
        
        result = strict_scanner.scan_file(zip_path)
        
        assert not result.is_safe
        assert any(
            t.threat_type == SecurityThreatType.EXCESSIVE_FILES
            for t in result.threats
        )
    
    def test_detect_large_file(self, strict_scanner, temp_dir):
        """Test detection of oversized file."""
        zip_path = temp_dir / "large.zip"
        
        # Create a zip with a file that exceeds the limit
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zf:
            # Create uncompressed entry that exceeds limit
            zf.writestr("large.bin", "X" * (15 * 1024 * 1024))  # 15MB
        
        result = strict_scanner.scan_file(zip_path)
        
        assert not result.is_safe
        assert any(
            t.threat_type == SecurityThreatType.EXCESSIVE_SIZE
            for t in result.threats
        )
    
    def test_detect_nested_archive(self, scanner, temp_dir):
        """Test detection of nested archives."""
        # Create inner zip
        inner_path = temp_dir / "inner.zip"
        self.create_zip(inner_path, {"inner_file.txt": "Inner content"})
        
        # Create outer zip containing inner zip
        outer_path = temp_dir / "outer.zip"
        with zipfile.ZipFile(outer_path, 'w') as zf:
            zf.write(inner_path, "nested.zip")
        
        result = scanner.scan_file(outer_path)
        
        # Should detect nested archive
        assert any(
            t.threat_type == SecurityThreatType.NESTED_ARCHIVE
            for t in result.threats
        )
    
    def test_detect_suspicious_content(self, scanner, temp_dir):
        """Test detection of suspicious content patterns."""
        zip_path = temp_dir / "suspicious.zip"
        self.create_zip(zip_path, {
            "config.json": '{"url": "javascript:alert(1)"}',
            "readme.txt": "Normal content"
        })
        
        result = scanner.scan_file(zip_path)
        
        # Should detect suspicious pattern
        assert any(
            t.threat_type == SecurityThreatType.SUSPICIOUS_CONTENT
            for t in result.threats
        )
    
    def test_scan_invalid_zip(self, scanner, temp_dir):
        """Test scanning an invalid/corrupted ZIP file."""
        invalid_path = temp_dir / "invalid.zip"
        invalid_path.write_bytes(b"Not a valid ZIP file")
        
        result = scanner.scan_file(invalid_path)
        
        assert not result.is_safe
        assert any(
            t.threat_type == SecurityThreatType.INVALID_ARCHIVE
            for t in result.threats
        )
    
    def test_scan_nonexistent_file(self, scanner, temp_dir):
        """Test scanning a non-existent file."""
        result = scanner.scan_file(Path("/nonexistent/file.zip"))
        
        assert not result.is_safe
        assert any(
            t.threat_type == SecurityThreatType.INVALID_ARCHIVE
            for t in result.threats
        )
    
    def test_scan_disallowed_extension(self, scanner, temp_dir):
        """Test scanning file with disallowed extension."""
        exe_path = temp_dir / "malware.exe"
        exe_path.write_bytes(b"MZ" + b"\x00" * 100)
        
        result = scanner.scan_file(exe_path)
        
        assert not result.is_safe
        assert any(
            t.threat_type == SecurityThreatType.SUSPICIOUS_CONTENT
            for t in result.threats
        )
    
    def test_validate_extraction_path_safe(self, scanner, temp_dir):
        """Test validation of safe extraction paths."""
        target = temp_dir / "extract"
        target.mkdir()
        
        safe_path = scanner.validate_extraction_path(target, "subdir/file.txt")
        
        assert safe_path.is_relative_to(target)
    
    def test_validate_extraction_path_traversal(self, scanner, temp_dir):
        """Test validation rejects path traversal."""
        target = temp_dir / "extract"
        target.mkdir()
        
        with pytest.raises(PathTraversalDetectedError):
            scanner.validate_extraction_path(target, "../outside.txt")
    
    def test_validate_extraction_path_absolute(self, scanner, temp_dir):
        """Test validation rejects absolute paths."""
        target = temp_dir / "extract"
        target.mkdir()
        
        with pytest.raises(PathTraversalDetectedError):
            scanner.validate_extraction_path(target, "/etc/passwd")
    
    def test_scan_upload_valid(self, scanner):
        """Test scanning a valid upload."""
        # Create in-memory zip
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            zf.writestr("test.txt", "Test content")
        
        buffer.seek(0)
        result = scanner.scan_upload(buffer, "test.zip")
        
        assert result.is_safe
    
    def test_scan_upload_invalid(self, scanner):
        """Test scanning an invalid upload."""
        buffer = BytesIO(b"Not a valid ZIP")
        buffer.seek(0)
        
        result = scanner.scan_upload(buffer, "invalid.txt")
        
        assert not result.is_safe


class TestSecurityScanResult:
    """Tests for SecurityScanResult."""
    
    def test_empty_result_is_safe(self):
        """Test that empty result is safe."""
        result = SecurityScanResult(is_safe=True)
        
        assert result.is_safe
        assert not result.has_critical_threats
        assert not result.has_high_threats
    
    def test_add_threat_updates_safety(self):
        """Test that adding high/critical threats updates safety."""
        result = SecurityScanResult(is_safe=True)
        
        # Low severity doesn't change safety
        result.add_threat(
            SecurityThreatType.SUSPICIOUS_CONTENT,
            SecuritySeverity.LOW,
            "Low threat"
        )
        assert result.is_safe
        
        # High severity changes safety
        result.add_threat(
            SecurityThreatType.PATH_TRAVERSAL,
            SecuritySeverity.HIGH,
            "High threat"
        )
        assert not result.is_safe
        assert result.has_high_threats
    
    def test_has_critical_threats(self):
        """Test detection of critical threats."""
        result = SecurityScanResult(is_safe=True)
        result.add_threat(
            SecurityThreatType.ZIP_BOMB,
            SecuritySeverity.CRITICAL,
            "Critical threat"
        )
        
        assert result.has_critical_threats
        assert not result.is_safe


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_scan_archive_function(self, temp_dir):
        """Test the scan_archive convenience function."""
        zip_path = temp_dir / "test.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("test.txt", "Test content")
        
        result = scan_archive(zip_path)
        
        assert result.is_safe