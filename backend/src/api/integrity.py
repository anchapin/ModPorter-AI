"""
Integrity API

API endpoints for output integrity validation.

Note: Due to ai-engine's hyphenated directory name, validators are invoked
via subprocess to avoid import issues.
"""

import logging
import os
import sys
import json
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Integrity"],
    responses={404: {"description": "Not found"}}
)


class IntegrityValidationRequest(BaseModel):
    """Request for full integrity validation."""
    conversion_id: str = Field(..., description="Conversion ID")
    input_analysis: Dict[str, Any] = Field(default_factory=dict)
    package_path: Optional[str] = Field(None, description="Path to output package")
    report_format: str = Field("json", description="Report format: json, html, markdown")


class IntegrityValidationResponse(BaseModel):
    """Response for integrity validation request."""
    job_id: str
    conversion_id: str
    status: str
    message: str


class IntegrityQuickCheckRequest(BaseModel):
    """Request for quick integrity check."""
    package_path: str = Field(..., description="Path to the package")


# In-memory job storage (would be Redis in production)
_validation_jobs: Dict[str, Dict[str, Any]] = {}


def _run_validator_script(script_name: str, args: list) -> Dict[str, Any]:
    """Run a validator script and return parsed JSON output."""
    project_root = Path(__file__).parent.parent.parent.parent
    script_path = project_root / "ai-engine" / "scripts" / script_name
    script_dir = script_path.parent
    script_dir.mkdir(parents=True, exist_ok=True)

    if not script_path.exists():
        script_content = f"""#!/usr/bin/env python3
import sys
import json
sys.path.insert(0, "{project_root / 'ai-engine'}")

from validators.file_integrity_checker import FileIntegrityChecker

try:
    checker = FileIntegrityChecker()
    result = checker.validate_package("{args[0] if args else ''}")
    print(json.dumps({{
        "valid": result.is_valid,
        "errors": [e.dict() for e in result.errors],
        "warnings": [w.dict() for w in result.warnings]
    }}))
except Exception as e:
    print(json.dumps({{"valid": False, "error": str(e)}}))
"""
        script_path.write_text(script_content)
        script_path.chmod(0o755)

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)] + args,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(project_root)
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            logger.error(f"Validator script failed: {result.stderr}")
            return {"valid": False, "error": result.stderr}
    except Exception as e:
        logger.error(f"Failed to run validator: {e}")
        return {"valid": False, "error": str(e)}


@router.post("/validate", response_model=IntegrityValidationResponse, status_code=202)
async def validate_output_integrity(request: IntegrityValidationRequest) -> IntegrityValidationResponse:
    """Validate conversion output integrity."""
    job_id = str(uuid.uuid4())
    try:
        validation_result = _run_validator_script(
            "validate_package.py",
            [request.package_path] if request.package_path else []
        )
        _validation_jobs[job_id] = {
            "conversion_id": request.conversion_id,
            "status": "completed" if validation_result.get("valid") else "failed",
            "result": validation_result,
        }
        return IntegrityValidationResponse(
            job_id=job_id,
            conversion_id=request.conversion_id,
            status="completed",
            message="Validation completed"
        )
    except Exception as e:
        logger.error(f"Integrity validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_integrity_job(job_id: str) -> Dict[str, Any]:
    """Get integrity validation job status."""
    job = _validation_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": job.get("status"), "result": job.get("result")}


@router.post("/quick-check")
async def quick_integrity_check(request: IntegrityQuickCheckRequest) -> Dict[str, Any]:
    """Quick integrity check for a package."""
    return _run_validator_script("validate_package.py", [request.package_path])


@router.get("/health")
async def integrity_health() -> Dict[str, Any]:
    """Health check for integrity service."""
    return {"status": "healthy", "service": "integrity"}
