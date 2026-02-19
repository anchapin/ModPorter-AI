"""
File security scanner for detecting malicious archives and files.

This module provides comprehensive security scanning for uploaded files,
including ZIP bomb detection, path traversal prevention, and resource limits.

Issue: #576 - Backend: File Processing Security
"""

import logging
import os
import zipfile
import tarfile
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, BinaryIO

logger = logging.getLogger(__name__)


class SecurityThreatType(str, Enum):
    """Types of security threats that can be detected."""
    ZIP_BOMB = "zip_bomb"
    PATH_TRAVERSAL = "path_traversal"
    EXCESSIVE_FILES = "excessive_files"
    EXCESSIVE_SIZE = "excessive_size"
    NESTED_ARCHIVE = "nested_archive"
    SUSPICIOUS_CONTENT = "suspicious_content"
    INVALID_ARCHIVE = "invalid_archive"
    RESOURCE_LIMIT = "resource_limit"


class SecuritySeverity(str, Enum):
    """Severity levels for security threats."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityThreat:
    """Represents a detected security threat."""
    threat_type: SecurityThreatType
    severity: SecuritySeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SecurityScanResult:
    """Result of a security scan."""
    is_safe: bool
    threats: List[SecurityThreat] = field(default_factory=list)
    scanned_at: datetime = field(default_factory=datetime.utcnow)
    file_path: Optional[Path] = None
    total_files_scanned: int = 0
    total_size_scanned: int = 0

    @property
    def has_critical_threats(self) -> bool:
        """Check if any critical threats were found."""
        return any(t.severity == SecuritySeverity.CRITICAL for t in self.threats)

    @property
    def has_high_threats(self) -> bool:
        """Check if any high severity threats were found."""
        return any(t.severity == SecuritySeverity.HIGH for t in self.threats)

    def add_threat(
        self,
        threat_type: SecurityThreatType,
        severity: SecuritySeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a threat to the result."""
        self.threats.append(SecurityThreat(
            threat_type=threat_type,
            severity=severity,
            message=message,
            details=details or {}
        ))
        if severity in (SecuritySeverity.HIGH, SecuritySeverity.CRITICAL):
            self.is_safe = False


class SecurityError(Exception):
    """Base exception for security-related errors."""
    pass


class ZipBombDetectedError(SecurityError):
    """Raised when a ZIP bomb is detected."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class PathTraversalDetectedError(SecurityError):
    """Raised when a path traversal attack is detected."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class ResourceLimitExceededError(SecurityError):
    """Raised when resource limits are exceeded."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


@dataclass
class SecurityConfig:
    """Configuration for security scanning."""
    # ZIP bomb detection limits
    max_compression_ratio: float = 100.0  # Maximum allowed compression ratio
    max_uncompressed_file_size: int = 1 * 1024 * 1024 * 1024  # 1GB per file
    max_total_uncompressed_size: int = 10 * 1024 * 1024 * 1024  # 10GB total
    
    # File count limits
    max_files_per_archive: int = 100000
    max_nested_archive_depth: int = 3
    
    # Path traversal settings
    allow_absolute_paths: bool = False
    blocked_path_patterns: List[str] = field(default_factory=lambda: [
        "../", "..\\", "/etc/", "/proc/", "/sys/", "/root/",
        "C:\\Windows", "C:\\Program Files"
    ])
    
    # Resource limits
    max_processing_time_seconds: int = 300  # 5 minutes
    max_memory_usage_mb: int = 512
    
    # File type restrictions
    allowed_extensions: List[str] = field(default_factory=lambda: [
        ".jar", ".zip", ".mcaddon", ".mcpack"
    ])
    
    # Suspicious content patterns
    suspicious_patterns: List[str] = field(default_factory=lambda: [
        "<script", "javascript:", "data:text/html",
        "<?php", "<%", "#!/bin/", "#!/usr/bin/"
    ])


class FileSecurityScanner:
    """
    Comprehensive file security scanner for detecting malicious content.
    
    This scanner checks for:
    - ZIP bombs (high compression ratio archives)
    - Path traversal attacks
    - Excessive file counts
    - Nested archive bombs
    - Suspicious content patterns
    """
    
    # Magic numbers for archive detection
    ZIP_MAGIC = b'PK\x03\x04'
    TAR_GZ_MAGIC = b'\x1f\x8b'
    TAR_BZ2_MAGIC = b'BZ'
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize the scanner with optional custom config."""
        self.config = config or SecurityConfig()
    
    def scan_file(
        self,
        file_path: Path,
        scan_content: bool = True,
        max_depth: int = 0
    ) -> SecurityScanResult:
        """
        Perform a comprehensive security scan on a file.
        
        Args:
            file_path: Path to the file to scan
            scan_content: Whether to scan file contents for suspicious patterns
            max_depth: Current nesting depth for recursive scans
            
        Returns:
            SecurityScanResult with scan findings
        """
        result = SecurityScanResult(file_path=file_path)
        
        if not file_path.exists():
            result.add_threat(
                SecurityThreatType.INVALID_ARCHIVE,
                SecuritySeverity.HIGH,
                f"File does not exist: {file_path}"
            )
            return result
        
        # Check file extension
        if not self._check_extension(file_path, result):
            return result
        
        # Determine file type and scan accordingly
        file_type = self._detect_file_type(file_path)
        
        if file_type in ('zip', 'jar'):
            self._scan_zip_archive(file_path, result, scan_content, max_depth)
        elif file_type == 'tar_gz':
            self._scan_tar_archive(file_path, result, scan_content, max_depth)
        else:
            # Unknown file type - add warning but don't fail
            result.add_threat(
                SecurityThreatType.SUSPICIOUS_CONTENT,
                SecuritySeverity.LOW,
                f"Unknown file type, limited scanning available"
            )
        
        return result
    
    def scan_upload(
        self,
        file_obj: BinaryIO,
        filename: str,
        scan_content: bool = True
    ) -> SecurityScanResult:
        """
        Scan an uploaded file object.
        
        Args:
            file_obj: Binary file object to scan
            filename: Original filename
            scan_content: Whether to scan contents
            
        Returns:
            SecurityScanResult with scan findings
        """
        result = SecurityScanResult()
        
        # Save current position
        original_pos = file_obj.tell()
        
        try:
            # Read magic bytes to detect type
            file_obj.seek(0)
            magic_bytes = file_obj.read(4)
            file_obj.seek(0)
            
            if magic_bytes.startswith(self.ZIP_MAGIC):
                # Create a temporary file to scan
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                    tmp.write(file_obj.read())
                    tmp_path = Path(tmp.name)
                
                try:
                    result = self._scan_zip_archive(tmp_path, result, scan_content, 0)
                finally:
                    tmp_path.unlink(missing_ok=True)
            else:
                result.add_threat(
                    SecurityThreatType.INVALID_ARCHIVE,
                    SecuritySeverity.HIGH,
                    f"Invalid file type for upload: {filename}"
                )
        finally:
            # Restore original position
            file_obj.seek(original_pos)
        
        return result
    
    def _check_extension(self, file_path: Path, result: SecurityScanResult) -> bool:
        """Check if file extension is allowed."""
        ext = file_path.suffix.lower()
        if ext and ext not in self.config.allowed_extensions:
            result.add_threat(
                SecurityThreatType.SUSPICIOUS_CONTENT,
                SecuritySeverity.MEDIUM,
                f"File extension '{ext}' is not in allowed list"
            )
            return False
        return True
    
    def _detect_file_type(self, file_path: Path) -> Optional[str]:
        """Detect the type of archive file."""
        try:
            with open(file_path, 'rb') as f:
                magic = f.read(4)
            
            if magic.startswith(self.ZIP_MAGIC):
                ext = file_path.suffix.lower()
                return 'jar' if ext == '.jar' else 'zip'
            elif magic.startswith(self.TAR_GZ_MAGIC):
                return 'tar_gz'
            elif magic.startswith(self.TAR_BZ2_MAGIC):
                return 'tar_bz2'
            
            return None
        except Exception as e:
            logger.error(f"Error detecting file type: {e}")
            return None
    
    def _scan_zip_archive(
        self,
        file_path: Path,
        result: SecurityScanResult,
        scan_content: bool,
        current_depth: int
    ) -> SecurityScanResult:
        """
        Scan a ZIP/JAR archive for security threats.
        
        Args:
            file_path: Path to the archive
            result: SecurityScanResult to populate
            scan_content: Whether to scan file contents
            current_depth: Current nesting depth
        """
        try:
            with zipfile.ZipFile(file_path, 'r') as archive:
                file_list = archive.infolist()
                total_files = len(file_list)
                result.total_files_scanned = total_files
                
                # Check file count limit
                if total_files > self.config.max_files_per_archive:
                    result.add_threat(
                        SecurityThreatType.EXCESSIVE_FILES,
                        SecuritySeverity.HIGH,
                        f"Archive contains too many files: {total_files} > {self.config.max_files_per_archive}",
                        {"file_count": total_files, "limit": self.config.max_files_per_archive}
                    )
                    return result
                
                total_uncompressed = 0
                total_compressed = 0
                
                for member in file_list:
                    # Check path traversal
                    if self._is_path_traversal(member.filename):
                        result.add_threat(
                            SecurityThreatType.PATH_TRAVERSAL,
                            SecuritySeverity.CRITICAL,
                            f"Path traversal detected in archive member: {member.filename}",
                            {"filename": member.filename}
                        )
                    
                    # Check for blocked path patterns
                    for pattern in self.config.blocked_path_patterns:
                        if pattern.lower() in member.filename.lower():
                            result.add_threat(
                                SecurityThreatType.PATH_TRAVERSAL,
                                SecuritySeverity.HIGH,
                                f"Blocked path pattern detected: {pattern}",
                                {"filename": member.filename, "pattern": pattern}
                            )
                    
                    # Track sizes for ZIP bomb detection
                    total_uncompressed += member.file_size
                    total_compressed += member.compress_size
                    
                    # Check individual file size
                    if member.file_size > self.config.max_uncompressed_file_size:
                        result.add_threat(
                            SecurityThreatType.EXCESSIVE_SIZE,
                            SecuritySeverity.HIGH,
                            f"File exceeds size limit: {member.filename}",
                            {
                                "filename": member.filename,
                                "size": member.file_size,
                                "limit": self.config.max_uncompressed_file_size
                            }
                        )
                    
                    # Check compression ratio for ZIP bomb detection
                    if member.compress_size > 0 and member.file_size > 0:
                        ratio = member.file_size / member.compress_size
                        if ratio > self.config.max_compression_ratio:
                            result.add_threat(
                                SecurityThreatType.ZIP_BOMB,
                                SecuritySeverity.CRITICAL,
                                f"Potential ZIP bomb: extreme compression ratio {ratio:.2f}x",
                                {
                                    "filename": member.filename,
                                    "ratio": ratio,
                                    "compressed_size": member.compress_size,
                                    "uncompressed_size": member.file_size
                                }
                            )
                    
                    # Check for nested archives
                    if self._is_nested_archive(member.filename):
                        if current_depth >= self.config.max_nested_archive_depth:
                            result.add_threat(
                                SecurityThreatType.NESTED_ARCHIVE,
                                SecuritySeverity.HIGH,
                                f"Nested archive depth exceeded: {member.filename}",
                                {"depth": current_depth, "max_depth": self.config.max_nested_archive_depth}
                            )
                    
                    # Scan content for suspicious patterns
                    if scan_content and not member.is_dir():
                        self._scan_member_content(archive, member, result)
                
                result.total_size_scanned = total_uncompressed
                
                # Check total uncompressed size
                if total_uncompressed > self.config.max_total_uncompressed_size:
                    result.add_threat(
                        SecurityThreatType.EXCESSIVE_SIZE,
                        SecuritySeverity.HIGH,
                        f"Total uncompressed size exceeds limit",
                        {
                            "total_size": total_uncompressed,
                            "limit": self.config.max_total_uncompressed_size
                        }
                    )
                
                # Check overall compression ratio
                if total_compressed > 0:
                    overall_ratio = total_uncompressed / total_compressed
                    if overall_ratio > self.config.max_compression_ratio:
                        result.add_threat(
                            SecurityThreatType.ZIP_BOMB,
                            SecuritySeverity.CRITICAL,
                            f"Archive has suspicious overall compression ratio: {overall_ratio:.2f}x",
                            {"ratio": overall_ratio}
                        )
        
        except zipfile.BadZipFile as e:
            result.add_threat(
                SecurityThreatType.INVALID_ARCHIVE,
                SecuritySeverity.HIGH,
                f"Invalid or corrupted ZIP file: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error scanning ZIP archive: {e}")
            result.add_threat(
                SecurityThreatType.INVALID_ARCHIVE,
                SecuritySeverity.MEDIUM,
                f"Error scanning archive: {str(e)}"
            )
        
        return result
    
    def _scan_tar_archive(
        self,
        file_path: Path,
        result: SecurityScanResult,
        scan_content: bool,
        current_depth: int
    ) -> SecurityScanResult:
        """Scan a TAR archive for security threats."""
        try:
            with tarfile.open(file_path, 'r:*') as archive:
                members = archive.getmembers()
                total_files = len(members)
                result.total_files_scanned = total_files
                
                if total_files > self.config.max_files_per_archive:
                    result.add_threat(
                        SecurityThreatType.EXCESSIVE_FILES,
                        SecuritySeverity.HIGH,
                        f"Archive contains too many files: {total_files}",
                        {"file_count": total_files}
                    )
                    return result
                
                for member in members:
                    # Check path traversal
                    if self._is_path_traversal(member.name):
                        result.add_threat(
                            SecurityThreatType.PATH_TRAVERSAL,
                            SecuritySeverity.CRITICAL,
                            f"Path traversal detected: {member.name}",
                            {"filename": member.name}
                        )
                    
                    # Check file size
                    if member.size > self.config.max_uncompressed_file_size:
                        result.add_threat(
                            SecurityThreatType.EXCESSIVE_SIZE,
                            SecuritySeverity.HIGH,
                            f"File exceeds size limit: {member.name}",
                            {"size": member.size}
                        )
        
        except Exception as e:
            logger.error(f"Error scanning TAR archive: {e}")
            result.add_threat(
                SecurityThreatType.INVALID_ARCHIVE,
                SecuritySeverity.MEDIUM,
                f"Error scanning archive: {str(e)}"
            )
        
        return result
    
    def _is_path_traversal(self, path: str) -> bool:
        """Check if a path contains path traversal sequences."""
        # Normalize the path
        normalized = os.path.normpath(path)
        
        # Check for absolute paths
        if os.path.isabs(normalized) and not self.config.allow_absolute_paths:
            return True
        
        # Check for parent directory references
        if normalized.startswith('..') or '/../' in normalized:
            return True
        
        # Check for suspicious patterns
        if '../' in path or '..\\' in path:
            return True
        
        return False
    
    def _is_nested_archive(self, filename: str) -> bool:
        """Check if a file is a nested archive."""
        nested_extensions = {'.zip', '.jar', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar'}
        ext = Path(filename).suffix.lower()
        return ext in nested_extensions
    
    def _scan_member_content(
        self,
        archive: zipfile.ZipFile,
        member: zipfile.ZipInfo,
        result: SecurityScanResult
    ) -> None:
        """Scan the content of an archive member for suspicious patterns."""
        try:
            # Only scan text-like files
            text_extensions = {'.txt', '.json', '.xml', '.properties', '.cfg', '.config', '.yml', '.yaml'}
            ext = Path(member.filename).suffix.lower()
            
            if ext not in text_extensions:
                return
            
            # Read content with size limit
            max_scan_size = 1024 * 1024  # 1MB max for content scanning
            if member.file_size > max_scan_size:
                return
            
            content = archive.read(member.filename)
            
            # Handle encoding
            try:
                text_content = content.decode('utf-8', errors='ignore')
            except Exception:
                return
            
            # Check for suspicious patterns
            for pattern in self.config.suspicious_patterns:
                if pattern.lower() in text_content.lower():
                    result.add_threat(
                        SecurityThreatType.SUSPICIOUS_CONTENT,
                        SecuritySeverity.MEDIUM,
                        f"Suspicious content pattern found in {member.filename}",
                        {"pattern": pattern, "filename": member.filename}
                    )
        
        except Exception as e:
            logger.debug(f"Error scanning member content: {e}")
    
    def validate_extraction_path(
        self,
        target_dir: Path,
        member_path: str
    ) -> Path:
        """
        Validate and resolve an extraction path, ensuring it's within the target directory.
        
        Args:
            target_dir: The target extraction directory
            member_path: The path of the archive member to extract
            
        Returns:
            Resolved safe path
            
        Raises:
            PathTraversalDetectedError: If path traversal is detected
        """
        # Normalize and resolve the target directory
        target_dir = target_dir.resolve()
        
        # Check for path traversal in member path
        if self._is_path_traversal(member_path):
            raise PathTraversalDetectedError(
                f"Path traversal detected in archive member: {member_path}",
                {"member_path": member_path}
            )
        
        # Construct the full path
        full_path = (target_dir / member_path).resolve()
        
        # Ensure the resolved path is within the target directory
        try:
            full_path.relative_to(target_dir)
        except ValueError:
            raise PathTraversalDetectedError(
                f"Resolved path escapes target directory: {member_path}",
                {"member_path": member_path, "target_dir": str(target_dir)}
            )
        
        return full_path


# Convenience function for quick security checks
def scan_archive(file_path: Path, config: Optional[SecurityConfig] = None) -> SecurityScanResult:
    """
    Perform a quick security scan on an archive file.
    
    Args:
        file_path: Path to the archive to scan
        config: Optional security configuration
        
    Returns:
        SecurityScanResult with scan findings
    """
    scanner = FileSecurityScanner(config)
    return scanner.scan_file(file_path)