"""
Pydantic Models for Input Validation API Responses

Phase 10-03: Input Validation
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ValidationErrorCode(str, Enum):
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


class ValidationError(BaseModel):
    """Single validation error."""

    code: ValidationErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Result of input validation."""

    valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationError] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": [e.model_dump() for e in self.errors],
            "warnings": [w.model_dump() for w in self.warnings],
            "metadata": self.metadata,
        }


class ValidationStatus(str, Enum):
    """Overall validation status."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


class ValidationReport(BaseModel):
    """Complete validation report for a file."""

    overall_status: ValidationStatus
    filename: str
    results: list[ValidationResult] = Field(default_factory=list)
    summary: str = ""
    timestamp: str = Field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())


class FileInfo(BaseModel):
    """Information about an uploaded file."""

    filename: str
    size: int
    extension: str
    content_type: Optional[str] = None
    detected_mod_type: Optional[str] = None
    java_file_count: Optional[int] = None
    file_count: Optional[int] = None
    total_size: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "example-mod-1.0.0.jar",
                "size": 5242880,
                "extension": ".jar",
                "content_type": "application/java-archive",
                "detected_mod_type": "forge",
                "file_count": 150,
                "total_size": 10485760,
            }
        }


class ValidationRequest(BaseModel):
    """Request model for validation endpoint."""

    filename: str
    content: str = Field(..., description="Base64-encoded file content")


class ValidationResponse(BaseModel):
    """Response model for validation endpoint."""

    valid: bool
    status: ValidationStatus
    file_info: FileInfo
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationError] = Field(default_factory=list)
    message: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "status": "PASS",
                "file_info": {
                    "filename": "example-mod-1.0.0.jar",
                    "size": 5242880,
                    "extension": ".jar",
                    "content_type": "application/java-archive",
                    "detected_mod_type": "forge",
                },
                "errors": [],
                "warnings": [],
                "message": "File validation passed",
            }
        }


class BatchValidationRequest(BaseModel):
    """Request model for batch validation."""

    files: list[ValidationRequest]


class BatchValidationResponse(BaseModel):
    """Response model for batch validation."""

    total_files: int
    passed: int
    failed: int
    warnings: int
    results: list[ValidationResponse]
