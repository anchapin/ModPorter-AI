# backend/src/api/validation.py
from fastapi import APIRouter, HTTPException, Body, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import uuid
import asyncio
from typing import Dict, Any, List, Optional
import time # For mock processing and timestamps
import threading
from .validation_constants import ValidationJobStatus, ValidationMessages

# --- Mock AI Engine components (replace with actual imports/integration later) ---
class MockAgentValidationReportModel(BaseModel):
    conversion_id: str
    semantic_analysis: Dict[str, Any]
    behavior_prediction: Dict[str, Any]
    asset_integrity: Dict[str, Any]
    manifest_validation: Dict[str, Any]
    overall_confidence: float
    recommendations: List[str] = []
    raw_data: Optional[Dict[str, Any]] = None

class MockValidationAgent:
    def validate_conversion(self, conversion_artifacts: Dict[str, Any]) -> MockAgentValidationReportModel:
        # Using string formatting for print
        print("MockValidationAgent: Validating conversion_id %s" % conversion_artifacts.get('conversion_id'))
        time.sleep(0.5) # Simulate processing time
        return MockAgentValidationReportModel(
            conversion_id=conversion_artifacts.get('conversion_id', str(uuid.uuid4())),
            semantic_analysis={"intent_preserved": True, "confidence": 0.85, "findings": ["Mock semantic finding"]},
            behavior_prediction={"behavior_diff": "None", "confidence": 0.9, "potential_issues": ["Mock behavior issue"]},
            asset_integrity={"all_assets_valid": True, "corrupted_files": [], "asset_specific_issues": {}},
            manifest_validation={"is_valid": True, "errors": [], "warnings": ["Mock manifest warning"]},
            overall_confidence=0.88,
            recommendations=["Mock recommendation: Review all generated files."]
        )

# --- Pydantic Models for API ---
class ValidationRequest(BaseModel):
    conversion_id: str = Field(..., description="The ID of the conversion to validate.")
    java_code_snippet: Optional[str] = Field(None, description="Snippet of original Java code.")
    bedrock_code_snippet: Optional[str] = Field(None, description="Snippet of converted Bedrock code.")
    asset_file_paths: Optional[List[str]] = Field(default_factory=list, description="List of asset file paths.")
    manifest_content: Optional[Dict[str, Any]] = Field(None, description="Parsed manifest.json content.")
    artifacts_location: Optional[str] = Field(None, description="Location of the full conversion artifacts.")

class ValidationJob(BaseModel):
    job_id: str = Field(..., description="The ID for this validation job.")
    status: ValidationJobStatus = Field(ValidationJobStatus.PENDING, description="Status of the validation job.")
    message: Optional[str] = None
    conversion_id: str

class ValidationReportResponse(MockAgentValidationReportModel): # Inherits from the (mock) agent's report
    validation_job_id: str = Field(..., description="The ID of the validation job that produced this report.")
    retrieved_at: str = Field(..., description="Timestamp when the report was retrieved.")

router = APIRouter(
    prefix="/validation",
    tags=["Validation"],
    responses={404: {"description": "Not found"}},
)

# Thread-safe storage for validation jobs and reports
_validation_jobs_lock = threading.Lock()
_validation_reports_lock = threading.Lock()
validation_jobs: Dict[str, ValidationJob] = {}
validation_reports: Dict[str, MockAgentValidationReportModel] = {}

def get_validation_agent():
    return MockValidationAgent()

async def process_validation_task(
    job_id: str,
    conversion_id: str,
    artifacts: Dict[str, Any],
    agent: MockValidationAgent
):
    print("Background task started for job_id: %s" % job_id)
    
    with _validation_jobs_lock:
        if job_id not in validation_jobs:
            print("Error: Job ID %s not found in process_validation_task." % job_id)
            return
        validation_jobs[job_id].status = ValidationJobStatus.PROCESSING
        validation_jobs[job_id].message = ValidationMessages.JOB_PROCESSING
    
    try:
        agent_input_artifacts = {
            "conversion_id": conversion_id,
            "java_code": artifacts.get("java_code_snippet"),
            "bedrock_code": artifacts.get("bedrock_code_snippet"),
            "asset_files": artifacts.get("asset_file_paths"),
            "manifest_data": artifacts.get("manifest_content"),
        }
        
        # Use asyncio.sleep instead of time.sleep for non-blocking operation
        await asyncio.sleep(0.5)  # Simulate processing time
        
        report = agent.validate_conversion(agent_input_artifacts)
        
        with _validation_reports_lock:
            validation_reports[job_id] = report
            
        with _validation_jobs_lock:
            validation_jobs[job_id].status = ValidationJobStatus.COMPLETED
            validation_jobs[job_id].message = ValidationMessages.JOB_COMPLETED
            
        print("Background task completed for job_id: %s" % job_id)
        
    except Exception as e:
        print("Error during validation for job_id %s: %s" % (job_id, str(e)))
        
        with _validation_jobs_lock:
            validation_jobs[job_id].status = ValidationJobStatus.FAILED
            validation_jobs[job_id].message = "%s: %s" % (ValidationMessages.JOB_FAILED, str(e))

@router.post("/", response_model=ValidationJob, status_code=202)
async def start_validation_job(
    request: ValidationRequest,
    background_tasks: BackgroundTasks,
    agent: MockValidationAgent = Depends(get_validation_agent)
):
    job_id = str(uuid.uuid4())
    conversion_id = request.conversion_id
    if not conversion_id:
        raise HTTPException(status_code=400, detail="conversion_id is required.")

    job = ValidationJob(job_id=job_id, conversion_id=conversion_id, status="queued")
    validation_jobs[job_id] = job

    artifacts_for_agent = {
        "java_code_snippet": request.java_code_snippet,
        "bedrock_code_snippet": request.bedrock_code_snippet,
        "asset_file_paths": request.asset_file_paths,
        "manifest_content": request.manifest_content,
    }
    background_tasks.add_task(process_validation_task, job_id, conversion_id, artifacts_for_agent, agent)
    print("Validation job %s for conversion %s queued." % (job_id, conversion_id))
    return job

@router.get("/{job_id}/status", response_model=ValidationJob)
async def get_validation_job_status(job_id: str):
    job = validation_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Validation job not found.")
    return job

@router.get("/{job_id}/report", response_model=ValidationReportResponse)
async def get_validation_report(job_id: str):
    job = validation_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Validation job not found.")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Validation job status is '%s'. Report not yet available." % job.status)

    report_data = validation_reports.get(job_id)
    if not report_data:
        raise HTTPException(status_code=404, detail="Validation report data not found, though job completed.")

    response_payload = report_data.model_dump()
    response_payload["validation_job_id"] = job_id
    response_payload["retrieved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return ValidationReportResponse(**response_payload)
