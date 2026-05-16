"""
Pre-Conversion Scan API

Provides endpoints for scanning mod files before conversion
to identify potential failure risks and provide recommendations.

Issue: #1542 - DX: Add pre-conversion feature scan showing failure risks before upload
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from services.pre_conversion_scanner import (
    PreConversionScanner,
    PreConversionScanResult,
    RiskSeverity,
    RiskCategory,
    RiskItem,
    ScanMetadata,
)
from api._authz import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pre-conversion-scan", tags=["pre-conversion-scan"])

TEMP_UPLOADS_DIR = os.getenv("TEMP_UPLOADS_DIR", "temp_uploads")
MAX_SCAN_SIZE = 100 * 1024 * 1024  # 100 MB


class RiskItemResponse(BaseModel):
    """Response model for individual risk items"""

    risk_id: str = Field(..., description="Unique identifier for the risk")
    severity: str = Field(..., description="Risk severity: low, medium, high, critical")
    category: str = Field(..., description="Risk category: dependency, complexity, pattern, etc.")
    title: str = Field(..., description="Short title for the risk")
    description: str = Field(..., description="Detailed description of the risk")
    location: Optional[str] = Field(None, description="File/location where risk was detected")
    suggestion: Optional[str] = Field(None, description="How to address this risk")
    conversion_impact: Optional[str] = Field(None, description="Impact on conversion success")
    evidence: list[str] = Field(default_factory=list, description="Evidence for this risk")


class ScanMetadataResponse(BaseModel):
    """Response model for scan metadata"""

    filename: str
    file_size: int
    file_count: int
    has_manifest: bool
    manifest_version: Optional[str] = None
    mod_name: Optional[str] = None
    minecraft_version: Optional[str] = None


class PreConversionScanResponse(BaseModel):
    """Response model for pre-conversion scan"""

    scan_id: str = Field(..., description="Unique scan identifier")
    metadata: ScanMetadataResponse
    overall_risk_level: str = Field(..., description="Overall risk: low, medium, high, critical")
    total_issues: int = Field(..., description="Total number of issues found")
    risks: list[RiskItemResponse] = Field(..., description="List of identified risks")
    can_proceed: bool = Field(..., description="Whether conversion can proceed")
    warnings_summary: str = Field(..., description="Human-readable summary of warnings")
    recommendations: list[str] = Field(..., description="Recommendations for the user")
    scan_timestamp: str = Field(..., description="ISO timestamp of scan")
    download_url: Optional[str] = Field(None, description="URL to download scan report")


class ScanStatusResponse(BaseModel):
    """Response model for scan status check"""

    scan_id: str
    status: str
    progress: int = Field(0, description="Scan progress percentage")
    message: Optional[str] = None


def _validate_file_for_scan(file: UploadFile) -> None:
    """Validate file is acceptable for scanning"""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".jar", ".zip", ".mcaddon"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: .jar, .zip, .mcaddon",
        )


async def _save_temp_file(file: UploadFile, job_id: str) -> tuple[str, int]:
    """
    Save uploaded file to temp location for scanning.

    Args:
        file: Uploaded file
        job_id: Unique job ID

    Returns:
        Tuple of (file_path, file_size)
    """
    file_ext = os.path.splitext(file.filename)[1].lower()
    temp_dir = Path(TEMP_UPLOADS_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)

    file_path = temp_dir / f"{job_id}_scan{file_ext}"

    try:
        content = await file.read()
        file_size = len(content)

        if file_size > MAX_SCAN_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum scan size of {MAX_SCAN_SIZE // (1024 * 1024)}MB",
            )

        with open(file_path, "wb") as f:
            f.write(content)

        await file.seek(0)

        return str(file_path), file_size

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving temp file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file for scanning",
        )


def _build_risk_response(risk: RiskItem) -> RiskItemResponse:
    """Convert RiskItem to RiskItemResponse"""
    return RiskItemResponse(
        risk_id=risk.risk_id,
        severity=risk.severity.value,
        category=risk.category.value,
        title=risk.title,
        description=risk.description,
        location=risk.location,
        suggestion=risk.suggestion,
        conversion_impact=risk.conversion_impact,
        evidence=risk.evidence,
    )


def _build_scan_response(result: PreConversionScanResult) -> PreConversionScanResponse:
    """Convert PreConversionScanResult to PreConversionScanResponse"""
    return PreConversionScanResponse(
        scan_id=result.scan_id,
        metadata=ScanMetadataResponse(
            filename=result.metadata.filename,
            file_size=result.metadata.file_size,
            file_count=result.metadata.file_count,
            has_manifest=result.metadata.has_manifest,
            manifest_version=result.metadata.manifest_version,
            mod_name=result.metadata.mod_name,
            minecraft_version=result.metadata.minecraft_version,
        ),
        overall_risk_level=result.overall_risk_level.value,
        total_issues=result.total_issues,
        risks=[_build_risk_response(r) for r in result.risks],
        can_proceed=result.can_proceed,
        warnings_summary=result.warnings_summary,
        recommendations=result.recommendations,
        scan_timestamp=result.scan_timestamp,
        download_url=f"/api/v1/pre-conversion-scan/{result.scan_id}/report",
    )


@router.post(
    "",
    response_model=PreConversionScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan mod file before conversion",
    description="Upload and scan a mod file to identify potential conversion issues before starting the conversion process.",
)
async def scan_mod_file(
    file: UploadFile = File(..., description="Mod file (.jar, .zip, .mcaddon) to scan"),
    current_user=Depends(get_current_user),
):
    """
    Scan a mod file for pre-conversion analysis.

    This endpoint:
    - Accepts JAR/ZIP mod files up to 100MB
    - Analyzes the file for known problematic patterns
    - Checks for incompatible dependencies
    - Evaluates complexity indicators
    - Returns a detailed risk report with recommendations

    **Response includes:**
    - overall_risk_level: low/medium/high/critical
    - List of identified risks with severity and suggestions
    - Whether the conversion can proceed
    - Human-readable summary and recommendations

    Use the scan_id to retrieve a detailed report later.
    """
    _validate_file_for_scan(file)

    scan_id = str(uuid.uuid4())

    try:
        file_path, file_size = await _save_temp_file(file, scan_id)

        try:
            scanner = PreConversionScanner()
            result = await scanner.scan_file(file_path, file.filename)

            response = _build_scan_response(result)

            logger.info(
                f"Pre-conversion scan completed: scan_id={scan_id}, "
                f"risk_level={result.overall_risk_level.value}, "
                f"total_issues={result.total_issues}"
            )

            return response

        finally:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Could not remove temp scan file: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pre-conversion scan failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scan failed. Please try again or contact support.",
        )


@router.get(
    "/{scan_id}",
    response_model=ScanStatusResponse,
    summary="Get scan status",
    description="Check the status of a previous scan by scan_id.",
)
async def get_scan_status(
    scan_id: str,
    current_user=Depends(get_current_user),
):
    """
    Get the status of a previous scan.

    Note: Scans are typically fast (< 30 seconds), so if the scan
    endpoint returned successfully, the scan is already complete.
    This endpoint is provided for cases where scans might be
    queued or cached.
    """
    return ScanStatusResponse(
        scan_id=scan_id,
        status="completed",
        progress=100,
        message="Scan completed. Use the scan endpoint to get results.",
    )


@router.get(
    "/{scan_id}/report",
    response_model=PreConversionScanResponse,
    summary="Get detailed scan report",
    description="Retrieve the detailed report for a completed scan.",
)
async def get_scan_report(
    scan_id: str,
    current_user=Depends(get_current_user),
):
    """
    Get detailed report for a scan.

    Note: Currently scans are synchronous. This endpoint is
    provided for future caching scenarios where scan results
    might be stored and retrieved.
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Scan report not found. Scans are synchronous and results are returned immediately.",
    )


@router.post(
    "/batch",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch scan multiple files",
    description="Scan multiple mod files in batch. Returns job IDs for tracking.",
)
async def batch_scan(
    files: list[UploadFile] = File(..., description="Mod files to scan (max 5)"),
    current_user=Depends(get_current_user),
):
    """
    Scan multiple mod files in batch.

    Maximum 5 files per batch. Each file is scanned and results
    are returned. For larger batches, use the async job submission.
    """
    if len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 files per batch scan",
        )

    results = []

    for file in files:
        try:
            _validate_file_for_scan(file)

            scan_id = str(uuid.uuid4())
            file_path, _ = await _save_temp_file(file, scan_id)

            try:
                scanner = PreConversionScanner()
                result = await scanner.scan_file(file_path, file.filename)

                results.append({
                    "scan_id": result.scan_id,
                    "filename": file.filename,
                    "risk_level": result.overall_risk_level.value,
                    "can_proceed": result.can_proceed,
                    "total_issues": result.total_issues,
                })

            finally:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass

        except HTTPException as e:
            results.append({
                "filename": file.filename,
                "error": e.detail,
                "can_proceed": False,
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": "Scan failed",
                "can_proceed": False,
            })

    return {
        "batch_id": str(uuid.uuid4()),
        "total_files": len(files),
        "results": results,
    }


__all__ = ["router"]