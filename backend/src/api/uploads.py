"""
Input Validation API Endpoints

Phase 10-03: Input Validation
Provides endpoints for validating mod files before processing.
"""

import base64
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse

# Add ai-engine to path for imports
# __file__ is backend/src/api/uploads.py
# We need to get to the project root
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent.parent  # backend/src/api/ -> backend/src/ -> backend/
project_root = backend_dir.parent  # project root
ai_engine_path = str(project_root / "ai-engine")

# Also add project root to path for ai_engine import
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Make sure ai_engine can be imported as a module
if ai_engine_path not in sys.path:
    sys.path.insert(0, ai_engine_path)

from src.models.validation import (
    ValidationResponse,
    ValidationStatus,
    ValidationError,
    FileInfo,
    BatchValidationRequest,
    BatchValidationResponse,
)

# Import validators - use importlib to load from ai-engine directory
import importlib.util
import importlib.machinery

# Load the input_validator module directly
_validator_module_path = os.path.join(ai_engine_path, "validators", "input_validator.py")
loader = importlib.machinery.SourceFileLoader("input_validator", _validator_module_path)
spec = importlib.util.spec_from_loader("input_validator", loader, origin=_validator_module_path)
if spec:
    _input_validator_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_input_validator_module)
    
    InputValidator = _input_validator_module.InputValidator
    ValidationConfig = _input_validator_module.ValidationConfig
    AIValidationResult = _input_validator_module.ValidationResult
    ValidationErrorCode = _input_validator_module.ValidationErrorCode
else:
    raise ImportError("Could not load input_validator module")

# Initialize validator
_validator: Optional[InputValidator] = None


def get_validator() -> InputValidator:
    """Get or create the input validator instance."""
    global _validator
    if _validator is None:
        # ai_engine_path is already /path/to/ai-engine
        config_path = os.path.join(ai_engine_path, "config", "validation_config.yaml")
        if os.path.exists(config_path):
            _validator = InputValidator(ValidationConfig.from_yaml(config_path))
        else:
            _validator = InputValidator(ValidationConfig.from_default())
    return _validator


def _convert_validation_result(result: AIValidationResult, filename: str, size: int) -> ValidationResponse:
    """Convert AI validation result to API response model."""
    # Determine status
    if result.valid:
        status = ValidationStatus.PASS
    elif result.warnings and not result.errors:
        status = ValidationStatus.WARNING
    else:
        status = ValidationStatus.FAIL

    # Convert errors
    errors = []
    for error in result.errors:
        # Map error code
        try:
            code = ValidationErrorCode(error.code.value)
        except (ValueError, AttributeError):
            code = ValidationErrorCode.INVALID_JAR

        errors.append(ValidationError(
            code=code,
            message=error.message,
            details=error.details,
        ))

    # Convert warnings
    warnings = []
    for warning in result.warnings:
        try:
            code = ValidationErrorCode(warning.code.value)
        except (ValueError, AttributeError):
            code = ValidationErrorCode.INVALID_JAR

        warnings.append(ValidationError(
            code=code,
            message=warning.message,
            details=warning.details,
        ))

    # Extract file info
    file_info = FileInfo(
        filename=filename,
        size=size,
        extension=result.metadata.get("extension", os.path.splitext(filename)[1]),
        detected_mod_type=result.metadata.get("mod_type"),
        file_count=result.metadata.get("file_count"),
        total_size=result.metadata.get("total_size"),
    )

    # Determine message
    if result.valid:
        message = "File validation passed"
    elif result.errors:
        message = f"Validation failed with {len(result.errors)} error(s)"
    else:
        message = f"Validation passed with {len(result.warnings)} warning(s)"

    return ValidationResponse(
        valid=result.valid,
        status=status,
        file_info=file_info,
        errors=errors,
        warnings=warnings,
        message=message,
    )


router = APIRouter(prefix="/api/v1", tags=["Validation"])


@router.post("/validate", response_model=ValidationResponse)
async def validate_file(file: UploadFile = File(...)):
    """
    Validate a mod file without processing it.

    This endpoint performs comprehensive validation of uploaded mod files
    including JAR structure validation, Java syntax checking, and
    security scans.

    Returns:
        ValidationResponse with validation status and detailed results
    """
    validator = get_validator()

    # Read file content
    content = await file.read()
    filename = file.filename or "unknown.jar"

    # Perform validation
    result = validator.validate_mod_file(
        file_content=content,
        filename=filename,
    )

    return _convert_validation_result(result, filename, len(content))


@router.post("/validate/batch", response_model=BatchValidationResponse)
async def validate_batch(request: BatchValidationRequest):
    """
    Validate multiple mod files in a single request.

    Args:
        request: BatchValidationRequest containing list of files to validate

    Returns:
        BatchValidationResponse with results for each file
    """
    validator = get_validator()
    results = []
    passed = 0
    failed = 0
    warnings = 0

    for file_req in request.files:
        try:
            # Decode base64 content
            content = base64.b64decode(file_req.content)
            filename = file_req.filename

            # Validate
            result = validator.validate_mod_file(
                file_content=content,
                filename=filename,
            )

            response = _convert_validation_result(result, filename, len(content))
            results.append(response)

            if response.valid:
                passed += 1
            elif response.errors:
                failed += 1

            if response.warnings:
                warnings += 1

        except Exception as e:
            # Handle decode errors
            error_response = ValidationResponse(
                valid=False,
                status=ValidationStatus.FAIL,
                file_info=FileInfo(
                    filename=file_req.filename,
                    size=0,
                    extension=os.path.splitext(file_req.filename)[1],
                ),
                errors=[ValidationError(
                    code=ValidationErrorCode.INVALID_JAR,
                    message=f"Could not process file: {str(e)}",
                )],
                warnings=[],
                message=f"Validation failed: {str(e)}",
            )
            results.append(error_response)
            failed += 1

    return BatchValidationResponse(
        total_files=len(request.files),
        passed=passed,
        failed=failed,
        warnings=warnings,
        results=results,
    )


@router.post("/validate/java", response_model=ValidationResponse)
async def validate_java_source(file: UploadFile = File(...)):
    """
    Validate Java source code without processing.

    This endpoint performs syntax validation on Java source files
    and detects mod type (Forge/Fabric).

    Returns:
        ValidationResponse with validation status and detailed results
    """
    validator = get_validator()

    # Read file content
    content = await file.read()
    filename = file.filename or "Unknown.java"

    try:
        java_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File content is not valid UTF-8 text"
        )

    # Validate Java syntax
    result = validator.validate_java_source(
        java_content=java_content,
        filename=filename,
    )

    # Convert to response
    return _convert_validation_result(result, filename, len(content))


@router.get("/validate/config")
async def get_validation_config():
    """
    Get the current validation configuration.

    Returns:
        JSON object with current validation limits and settings
    """
    validator = get_validator()
    config = validator.config

    return {
        "file_limits": {
            "max_file_size": config.max_file_size,
            "max_extracted_size": config.max_extracted_size,
            "max_java_files": config.max_java_files,
            "max_file_path_length": config.max_file_path_length,
            "max_files_in_archive": config.max_files_in_archive,
        },
        "allowed_types": {
            "allowed_extensions": config.allowed_extensions,
            "allowed_java_extensions": config.allowed_java_extensions,
            "allowed_mime_types": config.allowed_mime_types,
        },
        "security": {
            "restricted_paths": config.restricted_paths,
            "suspicious_patterns_count": len(config.suspicious_patterns),
            "max_compression_ratio": config.max_compression_ratio,
        },
        "jar_validation": {
            "jar_required_files": config.jar_required_files,
            "validate_zip_structure": config.validate_zip_structure,
            "validate_manifest": config.validate_manifest,
        },
        "java_validation": {
            "syntax_check": config.syntax_check,
            "max_lines_per_file": config.max_lines_per_file,
            "validate_imports": config.validate_imports,
            "detect_mod_type": config.detect_mod_type,
            "supported_java_versions": config.supported_java_versions,
        },
    }


# Integration helper for existing upload endpoint
async def validate_on_upload(file_content: bytes, filename: str) -> ValidationResponse:
    """
    Validate a file during upload process.

    This function can be called from the main upload endpoint to
    integrate validation into the existing workflow.

    Args:
        file_content: File content as bytes
        filename: Original filename

    Returns:
        ValidationResponse with validation results
    """
    validator = get_validator()
    result = validator.validate_mod_file(
        file_content=file_content,
        filename=filename,
    )

    return _convert_validation_result(result, filename, len(file_content))
