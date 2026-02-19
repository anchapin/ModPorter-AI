"""
Security module for file processing and resource management.

This module provides security utilities for:
- ZIP bomb detection and prevention
- Path traversal attack prevention
- Resource limit enforcement
- Secure temporary file management
- Rate limiting for file operations

Issue: #576 - Backend: File Processing Security
"""

from .file_security import (
    FileSecurityScanner,
    SecurityScanResult,
    SecurityConfig,
    ZipBombDetectedError,
    PathTraversalDetectedError,
    ResourceLimitExceededError,
)

from .resource_limits import (
    ResourceLimiter,
    ResourceLimits,
    ResourceUsage,
)

from .temp_file_manager import (
    SecureTempFileManager,
    TempFileConfig,
)

__all__ = [
    "FileSecurityScanner",
    "SecurityScanResult",
    "SecurityConfig",
    "ZipBombDetectedError",
    "PathTraversalDetectedError",
    "ResourceLimitExceededError",
    "ResourceLimiter",
    "ResourceLimits",
    "ResourceUsage",
    "SecureTempFileManager",
    "TempFileConfig",
]