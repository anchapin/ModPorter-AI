"""
Conversion Failure Analysis Module

Provides detailed failure analysis logging for conversion jobs.
Tracks failure patterns, root causes, and provides debugging insights.

Issue: #455 - Comprehensive Error Handling (Phase 3)
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import traceback

from .structured_logging import correlation_id_var, set_correlation_id, get_correlation_id

logger = logging.getLogger(__name__)


class FailureSeverity(Enum):
    """Severity level of the failure"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FailureSource(Enum):
    """Source of the failure"""
    FILE_UPLOAD = "file_upload"
    FILE_PARSING = "file_parsing"
    MOD_ANALYSIS = "mod_analysis"
    ASSET_CONVERSION = "asset_conversion"
    CODE_TRANSLATION = "code_translation"
    PACKAGING = "packaging"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class FailureDetail:
    """Detailed information about a failure"""
    error_type: str
    error_message: str
    error_category: str  # parse_error, asset_error, logic_error, etc.
    stack_trace: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionFailure:
    """Complete failure analysis for a conversion job"""
    job_id: str
    correlation_id: str
    timestamp: str
    failure_severity: str
    failure_source: str
    failure_summary: str
    user_message: str
    recovery_suggestions: List[str] = field(default_factory=list)
    failure_details: List[FailureDetail] = field(default_factory=list)
    retry_count: int = 0
    was_retry_successful: Optional[bool] = None
    conversion_stage: Optional[str] = None
    mod_type: Optional[str] = None
    target_version: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "job_id": self.job_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "failure_severity": self.failure_severity,
            "failure_source": self.failure_source,
            "failure_summary": self.failure_summary,
            "user_message": self.user_message,
            "recovery_suggestions": self.recovery_suggestions,
            "failure_details": [
                {
                    "error_type": fd.error_type,
                    "error_message": fd.error_message,
                    "error_category": fd.error_category,
                    "stack_trace": fd.stack_trace,
                    "file_path": fd.file_path,
                    "line_number": fd.line_number,
                    "context": fd.context,
                }
                for fd in self.failure_details
            ],
            "retry_count": self.retry_count,
            "was_retry_successful": self.was_retry_successful,
            "conversion_stage": self.conversion_stage,
            "mod_type": self.mod_type,
            "target_version": self.target_version,
            "additional_context": self.additional_context,
        }


# Recovery suggestions by error category
RECOVERY_SUGGESTIONS = {
    "parse_error": [
        "Verify the mod file is a valid JAR/ZIP archive",
        "Check that the mod was built for a supported Minecraft version",
        "Ensure the mod is not corrupted or encrypted",
    ],
    "asset_error": [
        "Check that all texture files are valid images",
        "Verify sound files are in the correct format (OGG)",
        "Ensure asset paths follow Minecraft's asset naming conventions",
    ],
    "logic_error": [
        "The mod uses complex features that may not fully convert",
        "Some gameplay logic may need manual adjustment",
        "Check the conversion report for specific changes",
    ],
    "package_error": [
        "Try the conversion again",
        "Ensure sufficient disk space is available",
        "Check that the output format is supported",
    ],
    "validation_error": [
        "Review the validation errors and fix the input",
        "Check that all required files are present",
        "Verify the mod metadata is correct",
    ],
    "network_error": [
        "Check your internet connection",
        "Try again - this may be a temporary issue",
        "If the problem persists, contact support",
    ],
    "rate_limit_error": [
        "Wait before making additional requests",
        "Consider reducing request frequency",
        "Contact support if you need higher rate limits",
    ],
    "timeout_error": [
        "The mod is complex and taking longer to process",
        "Try again with a smaller mod file",
        "Check system status for any ongoing issues",
    ],
    "unknown_error": [
        "Try the conversion again",
        "If the problem persists, contact support with the error ID",
    ],
}


def determine_failure_severity(error_category: str, retry_count: int) -> FailureSeverity:
    """Determine the severity of the failure"""
    if retry_count >= 3:
        return FailureSeverity.CRITICAL
    
    critical_categories = {"logic_error", "package_error"}
    high_categories = {"parse_error", "asset_error"}
    medium_categories = {"validation_error", "network_error"}
    
    if error_category in critical_categories:
        return FailureSeverity.CRITICAL if retry_count > 0 else FailureSeverity.HIGH
    elif error_category in high_categories:
        return FailureSeverity.HIGH if retry_count > 0 else FailureSeverity.MEDIUM
    elif error_category in medium_categories:
        return FailureSeverity.MEDIUM
    
    return FailureSeverity.LOW


def determine_failure_source(conversion_stage: Optional[str]) -> FailureSource:
    """Determine the source of the failure based on conversion stage"""
    if not conversion_stage:
        return FailureSource.UNKNOWN
    
    stage_lower = conversion_stage.lower()
    
    if "upload" in stage_lower:
        return FailureSource.FILE_UPLOAD
    elif "parse" in stage_lower:
        return FailureSource.FILE_PARSING
    elif "analy" in stage_lower:
        return FailureSource.MOD_ANALYSIS
    elif "asset" in stage_lower:
        return FailureSource.ASSET_CONVERSION
    elif "translat" in stage_lower or "convert" in stage_lower:
        return FailureSource.CODE_TRANSLATION
    elif "pack" in stage_lower:
        return FailureSource.PACKAGING
    elif "valid" in stage_lower:
        return FailureSource.VALIDATION
    
    return FailureSource.UNKNOWN


def log_conversion_failure(
    job_id: str,
    error: Exception,
    error_category: str,
    conversion_stage: Optional[str] = None,
    mod_type: Optional[str] = None,
    target_version: Optional[str] = None,
    retry_count: int = 0,
    additional_context: Optional[Dict[str, Any]] = None,
) -> ConversionFailure:
    """
    Log a conversion failure with detailed analysis.
    
    Args:
        job_id: The conversion job ID
        error: The exception that occurred
        error_category: Category of the error (parse_error, asset_error, etc.)
        conversion_stage: Current stage of conversion when failure occurred
        mod_type: Type of mod being converted
        target_version: Target Minecraft version
        retry_count: Number of times this conversion was retried
        additional_context: Any additional context to log
    
    Returns:
        ConversionFailure object with detailed failure information
    """
    # Get or create correlation ID
    correlation_id = get_correlation_id() or set_correlation_id()
    
    # Determine failure details
    severity = determine_failure_severity(error_category, retry_count)
    source = determine_failure_source(conversion_stage)
    
    # Create failure detail
    failure_detail = FailureDetail(
        error_type=type(error).__name__,
        error_message=str(error),
        error_category=error_category,
        stack_trace=traceback.format_exc(),
        context=additional_context or {},
    )
    
    # Get recovery suggestions
    suggestions = RECOVERY_SUGGESTIONS.get(
        error_category, 
        RECOVERY_SUGGESTIONS["unknown_error"]
    )
    
    # Create user-friendly message
    user_message = _get_user_message(error_category)
    
    # Create failure object
    failure = ConversionFailure(
        job_id=job_id,
        correlation_id=correlation_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        failure_severity=severity.value,
        failure_source=source.value,
        failure_summary=f"{type(error).__name__}: {str(error)[:100]}",
        user_message=user_message,
        recovery_suggestions=suggestions,
        failure_details=[failure_detail],
        retry_count=retry_count,
        conversion_stage=conversion_stage,
        mod_type=mod_type,
        target_version=target_version,
        additional_context=additional_context or {},
    )
    
    # Log the failure
    _log_failure(failure)
    
    return failure


def _get_user_message(error_category: str) -> str:
    """Get user-friendly message for error category"""
    messages = {
        "parse_error": "Failed to parse the mod file. The file may be corrupted or use an unsupported format.",
        "asset_error": "Some mod assets could not be converted. The output may be missing textures or sounds.",
        "logic_error": "Some mod features could not be fully converted. Manual adjustments may be needed.",
        "package_error": "Failed to create the output package. Please try again.",
        "validation_error": "Validation failed. Please check your input and try again.",
        "network_error": "A network error occurred. Please check your connection and try again.",
        "rate_limit_error": "Too many requests. Please wait a moment before trying again.",
        "timeout_error": "The operation timed out. The mod may be too complex. Please try again.",
    }
    return messages.get(error_category, "An unexpected error occurred. Please try again.")


def _log_failure(failure: ConversionFailure):
    """Log the failure with appropriate level based on severity"""
    log_data = failure.to_dict()
    
    # Determine log level based on severity
    if failure.failure_severity == FailureSeverity.CRITICAL.value:
        logger.error(
            f"[{failure.job_id}] CRITICAL conversion failure: {failure.failure_summary}",
            extra={"failure_analysis": log_data},
        )
    elif failure.failure_severity == FailureSeverity.HIGH.value:
        logger.error(
            f"[{failure.job_id}] High severity failure: {failure.failure_summary}",
            extra={"failure_analysis": log_data},
        )
    elif failure.failure_severity == FailureSeverity.MEDIUM.value:
        logger.warning(
            f"[{failure.job_id}] Medium severity failure: {failure.failure_summary}",
            extra={"failure_analysis": log_data},
        )
    else:
        logger.info(
            f"[{failure.job_id}] Low severity failure: {failure.failure_summary}",
            extra={"failure_analysis": log_data},
        )


def log_retry_success(job_id: str, previous_attempts: int):
    """Log when a retry successfully completes a conversion"""
    correlation_id = get_correlation_id() or ""
    logger.info(
        f"[{job_id}] Conversion succeeded on retry {previous_attempts}",
        extra={
            "retry_success": {
                "job_id": job_id,
                "correlation_id": correlation_id,
                "previous_attempts": previous_attempts,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        },
    )


def log_retry_failure(
    job_id: str,
    attempt: int,
    error: Exception,
    error_category: str,
):
    """Log when a retry attempt fails"""
    correlation_id = get_correlation_id() or ""
    logger.warning(
        f"[{job_id}] Retry attempt {attempt} failed: {type(error).__name__}: {str(error)[:100]}",
        extra={
            "retry_failure": {
                "job_id": job_id,
                "correlation_id": correlation_id,
                "attempt": attempt,
                "error_category": error_category,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        },
    )
