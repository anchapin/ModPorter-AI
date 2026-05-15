"""
Security module for file processing and resource management.

This module provides security utilities for:
- ZIP bomb detection and prevention
- Path traversal attack prevention
- Resource limit enforcement
- Secure temporary file management
- Rate limiting for file operations
- Client IP extraction with proxy spoofing prevention
- URL/SSRF protection for webhook requests

Issue: #576 - Backend: File Processing Security
Issue: #1533 - security(backend): verify webhook SSRF guard against RFC1918 targets
Issue: #1534 - security(backend): validate X-Forwarded-For against trusted proxy allowlist
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

from .client_ip import (
    ClientIPExtractor,
    get_client_ip,
    get_client_ip_extractor,
)

from .url_security import (
    is_safe_url,
    is_private_ip,
    SSRFProtectionError,
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
    "ClientIPExtractor",
    "get_client_ip",
    "get_client_ip_extractor",
    "is_safe_url",
    "is_private_ip",
    "SSRFProtectionError",
]
