"""
Audit Logging Service for ModPorter-AI.

Provides structured audit logging for security-relevant events:
- File uploads (start, complete, fail)
- File deletions
- Security violations
- Rate limit events

Issue: #973 - File upload security: sandboxing, validation, and virus scanning
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any, Dict
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Upload events
    UPLOAD_STARTED = "upload_started"
    UPLOAD_COMPLETED = "upload_completed"
    UPLOAD_FAILED = "upload_failed"
    UPLOAD_REJECTED = "upload_rejected"

    # File events
    FILE_SCANNED = "file_scanned"
    FILE_CLEAN = "file_clean"
    FILE_INFECTED = "file_infected"
    FILE_DELETED = "file_deleted"
    FILE_AUTO_DELETED = "file_auto_deleted"

    # Security events
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    PATH_TRAVERSAL_BLOCKED = "path_traversal_blocked"
    INVALID_FILE_TYPE = "invalid_file_type"
    FILE_SIZE_EXCEEDED = "file_size_exceeded"

    # Conversion events
    CONVERSION_STARTED = "conversion_started"
    CONVERSION_COMPLETED = "conversion_completed"
    CONVERSION_FAILED = "conversion_failed"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Represents an audit log entry."""

    event_type: AuditEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    job_id: Optional[str] = None
    file_id: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    severity: AuditSeverity = AuditSeverity.INFO
    success: bool = True
    error_message: Optional[str] = None
    scan_result: Optional[str] = None
    threats_found: list = field(default_factory=list)
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = (
            self.event_type.value
            if isinstance(self.event_type, AuditEventType)
            else self.event_type
        )
        data["severity"] = (
            self.severity.value if isinstance(self.severity, AuditSeverity) else self.severity
        )
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """
    Thread-safe audit logger for security events.

    Writes structured audit logs that can be:
    - Written to local file
    - Sent to a SIEM system
    - Stored in database
    """

    def __init__(
        self,
        log_file: Optional[str] = None,
        log_to_console: bool = True,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        backup_count: int = 10,
    ):
        self.log_file = log_file
        self.log_to_console = log_to_console
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self._lock = threading.Lock()

        # Setup file handler if configured
        if log_file:
            self._setup_file_handler()

    def _setup_file_handler(self) -> None:
        """Setup rotating file handler for audit logs."""
        if not self.log_file:
            return

        import logging.handlers

        log_dir = Path(self.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

        # Create dedicated audit logger
        self._audit_logger = logging.getLogger(f"audit.{self.log_file}")
        self._audit_logger.setLevel(logging.INFO)
        self._audit_logger.addHandler(handler)
        self._audit_logger.propagate = False

    def log(self, event: AuditEvent) -> None:
        """
        Log an audit event.

        Args:
            event: The audit event to log
        """
        with self._lock:
            event_dict = event.to_dict()
            event_json = json.dumps(event_dict)

            # Log to audit file if configured
            if hasattr(self, "_audit_logger"):
                if event.severity == AuditSeverity.CRITICAL:
                    self._audit_logger.critical(event_json)
                elif event.severity == AuditSeverity.ERROR:
                    self._audit_logger.error(event_json)
                elif event.severity == AuditSeverity.WARNING:
                    self._audit_logger.warning(event_json)
                elif event.severity == AuditSeverity.INFO:
                    self._audit_logger.info(event_json)
                else:
                    self._audit_logger.debug(event_json)

            # Log to console
            if self.log_to_console:
                if event.severity in (AuditSeverity.CRITICAL, AuditSeverity.ERROR):
                    logger.error(f"AUDIT: {event_json}")
                elif event.severity == AuditSeverity.WARNING:
                    logger.warning(f"AUDIT: {event_json}")
                else:
                    logger.info(f"AUDIT: {event_json}")

    def log_upload_started(
        self,
        job_id: str,
        filename: str,
        user_id: Optional[str] = None,
        file_size: Optional[int] = None,
        ip_address: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log an upload started event."""
        event = AuditEvent(
            event_type=AuditEventType.UPLOAD_STARTED,
            user_id=user_id,
            job_id=job_id,
            filename=filename,
            file_size=file_size,
            ip_address=ip_address,
            severity=AuditSeverity.INFO,
            success=True,
            **kwargs,
        )
        self.log(event)

    def log_upload_completed(
        self,
        job_id: str,
        filename: str,
        file_size: int,
        user_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        ip_address: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log an upload completed event."""
        event = AuditEvent(
            event_type=AuditEventType.UPLOAD_COMPLETED,
            user_id=user_id,
            job_id=job_id,
            filename=filename,
            file_size=file_size,
            severity=AuditSeverity.INFO,
            success=True,
            duration_ms=duration_ms,
            ip_address=ip_address,
            **kwargs,
        )
        self.log(event)

    def log_upload_failed(
        self,
        job_id: str,
        filename: str,
        error_message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log an upload failed event."""
        event = AuditEvent(
            event_type=AuditEventType.UPLOAD_FAILED,
            user_id=user_id,
            job_id=job_id,
            filename=filename,
            severity=AuditSeverity.ERROR,
            success=False,
            error_message=error_message,
            ip_address=ip_address,
            **kwargs,
        )
        self.log(event)

    def log_file_scanned(
        self,
        job_id: str,
        filename: str,
        scan_result: str,
        threats_found: list = None,
        duration_ms: Optional[float] = None,
        **kwargs,
    ) -> None:
        """Log a file scan completed event."""
        is_clean = scan_result == "clean"
        event = AuditEvent(
            event_type=AuditEventType.FILE_CLEAN if is_clean else AuditEventType.FILE_INFECTED,
            job_id=job_id,
            filename=filename,
            severity=AuditSeverity.INFO if is_clean else AuditSeverity.CRITICAL,
            success=is_clean,
            scan_result=scan_result,
            threats_found=threats_found or [],
            duration_ms=duration_ms,
            **kwargs,
        )
        self.log(event)

    def log_security_violation(
        self,
        violation_type: str,
        filename: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log a security violation event."""
        event = AuditEvent(
            event_type=AuditEventType.SECURITY_VIOLATION,
            user_id=user_id,
            filename=filename,
            ip_address=ip_address,
            severity=AuditSeverity.WARNING,
            success=False,
            error_message=f"{violation_type}: {details}" if details else violation_type,
            metadata={"violation_type": violation_type, **(kwargs.get("metadata") or {})},
        )
        self.log(event)

    def log_file_deleted(
        self,
        job_id: str,
        filename: str,
        deleted_by: str = "system",
        reason: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log a file deletion event."""
        event_type = (
            AuditEventType.FILE_AUTO_DELETED
            if deleted_by == "system"
            else AuditEventType.FILE_DELETED
        )
        event = AuditEvent(
            event_type=event_type,
            job_id=job_id,
            filename=filename,
            severity=AuditSeverity.INFO,
            success=True,
            metadata={"deleted_by": deleted_by, "reason": reason, **(kwargs.get("metadata") or {})},
            **kwargs,
        )
        self.log(event)

    def log_rate_limit_exceeded(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log a rate limit exceeded event."""
        event = AuditEvent(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            ip_address=ip_address,
            severity=AuditSeverity.WARNING,
            success=False,
            error_message=f"Rate limit exceeded for endpoint: {endpoint}"
            if endpoint
            else "Rate limit exceeded",
            metadata={"endpoint": endpoint, **(kwargs.get("metadata") or {})},
            **kwargs,
        )
        self.log(event)


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        import os
        from config import settings

        log_file = os.getenv("AUDIT_LOG_FILE", "/var/log/modporter/audit.log")
        _audit_logger = AuditLogger(log_file=log_file, log_to_console=True)
    return _audit_logger


def log_upload_event(
    event_type: str,
    job_id: str,
    filename: str,
    **kwargs,
) -> None:
    """Convenience function to log upload-related events."""
    audit = get_audit_logger()

    if event_type == "started":
        audit.log_upload_started(job_id=job_id, filename=filename, **kwargs)
    elif event_type == "completed":
        audit.log_upload_completed(job_id=job_id, filename=filename, **kwargs)
    elif event_type == "failed":
        audit.log_upload_failed(job_id=job_id, filename=filename, **kwargs)


__all__ = [
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    "AuditLogger",
    "get_audit_logger",
    "log_upload_event",
]
