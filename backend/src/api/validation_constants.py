# backend/src/api/validation_constants.py
from enum import Enum


class ValidationJobStatus(str, Enum):
    """Enumeration of validation job statuses"""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationMessages:
    """Constants for validation messages"""

    JOB_QUEUED = "Validation job queued successfully"
    JOB_PROCESSING = "Validation job is currently processing"
    JOB_COMPLETED = "Validation successful"
    JOB_FAILED = "Validation failed"
    JOB_NOT_FOUND = "Validation job not found"
    REPORT_NOT_AVAILABLE = "Report not yet available"
    CONVERSION_ID_REQUIRED = "conversion_id is required"
