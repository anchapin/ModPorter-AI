# backend/src/api/validation.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import uuid
import asyncio
from typing import Dict, Any, List, Optional
import time
import threading
from .validation_constants import ValidationJobStatus, ValidationMessages


class ValidationReportModel(BaseModel):
    conversion_id: str = Field(..., description="Unique conversion identifier")
    semantic_analysis: Dict[str, Any] = Field(..., description="Semantic preservation analysis")
    behavior_prediction: Dict[str, Any] = Field(..., description="Behavioral difference predictions")
    asset_integrity: Dict[str, Any] = Field(..., description="Asset validation results")
    manifest_validation: Dict[str, Any] = Field(..., description="Manifest structure validation")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw validation data")


class ValidationAgent:
    def __init__(self) -> None:
        self._weights = {
            'semantic': 0.25,
            'behavior': 0.30,
            'assets': 0.20,
            'manifest': 0.25
        }

    def validate_conversion(self, conversion_artifacts: Dict[str, Any]) -> ValidationReportModel:
        conversion_id = conversion_artifacts.get("conversion_id", str(uuid.uuid4()))

        semantic_analysis = self._analyze_semantic_preservation(conversion_artifacts)
        behavior_prediction = self._predict_behavior_differences(conversion_artifacts)
        asset_integrity = self._validate_asset_integrity(conversion_artifacts)
        manifest_validation = self._validate_manifest_structure(conversion_artifacts)
        
        overall_confidence = self._calculate_weighted_confidence(
            semantic_analysis, behavior_prediction, asset_integrity, manifest_validation
        )
        
        recommendations = self._generate_recommendations(
            semantic_analysis, behavior_prediction, asset_integrity, manifest_validation
        )

        return ValidationReportModel(
            conversion_id=conversion_id,
            semantic_analysis=semantic_analysis,
            behavior_prediction=behavior_prediction,
            asset_integrity=asset_integrity,
            manifest_validation=manifest_validation,
            overall_confidence=overall_confidence,
            recommendations=recommendations,
            raw_data=conversion_artifacts
        )

    def _analyze_semantic_preservation(self, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        java_code = artifacts.get("java_code", "")
        bedrock_code = artifacts.get("bedrock_code", "")
        
        findings = []
        critical_issues = []
        warnings = []
        intent_preserved = True
        confidence = 0.5
        
        if not java_code and not bedrock_code:
            warnings.append("No code provided for semantic analysis")
            confidence = 0.0
        else:
            java_lower = java_code.lower() if java_code else ""
            bedrock_lower = bedrock_code.lower() if bedrock_code else ""
            
            if 'entity' in java_lower:
                if 'entity' in bedrock_lower or 'minecraft:entity' in bedrock_lower:
                    findings.append("Entity concept preserved in conversion")
                    confidence += 0.2
                else:
                    critical_issues.append("Entity concept may not be preserved")
                    intent_preserved = False
                    confidence -= 0.1
            
            if 'block' in java_lower:
                if 'block' in bedrock_lower or 'minecraft:block' in bedrock_lower:
                    findings.append("Block concept preserved in conversion")
                    confidence += 0.2
                else:
                    warnings.append("Block concept may need verification")
            
            if 'function' in java_lower or 'command' in java_lower:
                if 'function' in bedrock_lower:
                    findings.append("Function/command concept preserved")
                    confidence += 0.15
                else:
                    warnings.append("Functions may need manual verification")
            
            if 'event' in java_lower:
                if 'event' in bedrock_lower or 'trigger' in bedrock_lower:
                    findings.append("Event handling preserved")
                    confidence += 0.1
                else:
                    warnings.append("Event handling may differ in Bedrock")
            
            confidence = min(max(confidence, 0.0), 1.0)
            if len(findings) > 0 and len(critical_issues) == 0:
                intent_preserved = True
        
        return {
            "intent_preserved": intent_preserved,
            "confidence": confidence,
            "findings": findings if findings else ["Analysis completed with available data"],
            "critical_issues": critical_issues,
            "warnings": warnings if warnings else ["No warnings"]
        }

    def _predict_behavior_differences(self, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        java_code = artifacts.get("java_code", "")
        bedrock_code = artifacts.get("bedrock_code", "")
        
        potential_issues = []
        behavior_diff = "minimal"
        compatibility_score = 0.9
        
        if not java_code and not bedrock_code:
            return {
                "behavior_diff": "unknown",
                "confidence": 0.0,
                "potential_issues": ["No code provided for behavior analysis"],
                "compatibility_score": 0.0
            }
        
        java_lower = java_code.lower() if java_code else ""
        bedrock_lower = bedrock_code.lower() if bedrock_code else ""
        
        if 'ai' in java_lower or 'goal' in java_lower or 'behavior' in java_lower:
            if 'behavior' not in bedrock_lower and 'minecraft:behavior' not in bedrock_lower:
                potential_issues.append("AI/behavior system differences detected")
                compatibility_score -= 0.15
                behavior_diff = "significant"
        
        if 'inventory' in java_lower or 'itemstack' in java_lower:
            if 'container' not in bedrock_lower and 'item' not in bedrock_lower:
                potential_issues.append("Inventory handling differs between platforms")
                compatibility_score -= 0.1
        
        if 'nbt' in java_lower or 'tag' in java_lower:
            if 'nbt' not in bedrock_lower and 'data' not in bedrock_lower:
                potential_issues.append("NBT data handling differs in Bedrock")
                compatibility_score -= 0.1
                behavior_diff = "moderate"
        
        compatibility_score = max(compatibility_score, 0.0)
        
        return {
            "behavior_diff": behavior_diff,
            "confidence": min(compatibility_score + 0.1, 1.0),
            "potential_issues": potential_issues if potential_issues else ["No major behavior differences detected"],
            "compatibility_score": compatibility_score
        }

    def _validate_asset_integrity(self, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        asset_files = artifacts.get("asset_files", [])
        
        all_valid = True
        corrupted_files = []
        missing_assets = []
        asset_specific_issues = {}
        
        expected_types = ['texture', 'model', 'sound', 'animation', 'particle']
        
        if not asset_files:
            return {
                "all_assets_valid": True,
                "corrupted_files": [],
                "asset_specific_issues": {},
                "missing_assets": [],
                "note": "No assets provided for validation"
            }
        
        for asset_path in asset_files:
            if not asset_path:
                continue
            path_lower = asset_path.lower()
            is_valid = False
            for ext in ['.png', '.json', '.ogg', '.molang']:
                if path_lower.endswith(ext):
                    is_valid = True
                    break
            if not is_valid:
                corrupted_files.append(asset_path)
                all_valid = False
                asset_specific_issues[asset_path] = "Unrecognized file format"
        
        found_types = set()
        for asset_path in asset_files:
            path_lower = asset_path.lower()
            for asset_type in expected_types:
                if asset_type in path_lower:
                    found_types.add(asset_type)
        
        missing_types = set(expected_types) - found_types
        
        return {
            "all_assets_valid": all_valid,
            "corrupted_files": corrupted_files,
            "asset_specific_issues": asset_specific_issues,
            "missing_assets": missing_assets,
            "asset_types_found": list(found_types),
            "asset_types_missing": list(missing_types) if missing_types else []
        }

    def _validate_manifest_structure(self, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        manifest_data = artifacts.get("manifest_data", {})
        
        errors = []
        warnings = []
        is_valid = False
        schema_compliance = False
        
        if not manifest_data:
            return {
                "is_valid": False,
                "errors": ["No manifest content provided"],
                "warnings": [],
                "schema_compliance": False
            }
        
        required_fields = ['header', 'modules']
        for field in required_fields:
            if field not in manifest_data:
                errors.append(f"Missing required field: {field}")
        
        if 'header' in manifest_data:
            header = manifest_data['header']
            header_required = ['name', 'version', 'uuid']
            for field in header_required:
                if field not in header:
                    errors.append(f"Missing required header field: {field}")
            if 'version' in header:
                version = header['version']
                if isinstance(version, list) and len(version) == 3:
                    schema_compliance = True
                elif isinstance(version, str) and '.' in version:
                    schema_compliance = True
        
        if 'modules' in manifest_data:
            modules = manifest_data['modules']
            if not isinstance(modules, list):
                errors.append("Modules must be a list")
            elif len(modules) == 0:
                warnings.append("No modules defined in manifest")
            else:
                for i, module in enumerate(modules):
                    if 'type' not in module:
                        errors.append(f"Module {i} missing type field")
                    if 'uuid' not in module:
                        errors.append(f"Module {i} missing uuid field")
        
        is_valid = len(errors) == 0
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings if warnings else ["No warnings"],
            "schema_compliance": schema_compliance
        }

    def _calculate_weighted_confidence(self, semantic, behavior, assets, manifest) -> float:
        semantic_conf = semantic.get("confidence", 0.5)
        behavior_conf = behavior.get("compatibility_score", 0.5)
        
        if assets.get("all_assets_valid", True):
            asset_conf = 1.0
        else:
            asset_conf = 1.0 - (len(assets.get("corrupted_files", [])) * 0.2)
        
        if manifest.get("is_valid", False):
            manifest_conf = 1.0 if manifest.get("schema_compliance", False) else 0.8
        else:
            manifest_conf = 0.3
        
        semantic_penalty = len(semantic.get("critical_issues", [])) * 0.15
        behavior_penalty = len(behavior.get("potential_issues", [])) * 0.1
        
        weighted_score = (
            semantic_conf * self._weights['semantic'] +
            behavior_conf * self._weights['behavior'] +
            asset_conf * self._weights['assets'] +
            manifest_conf * self._weights['manifest']
        )
        
        final_score = weighted_score - semantic_penalty - behavior_penalty
        return max(min(final_score, 1.0), 0.0)

    def _generate_recommendations(self, semantic, behavior, assets, manifest) -> List[str]:
        recommendations = []
        
        if semantic.get("critical_issues"):
            recommendations.append("Review critical semantic issues in the conversion")
        if semantic.get("warnings"):
            recommendations.append("Verify semantic preservation for complex Java features")
        
        if behavior.get("potential_issues"):
            recommendations.append("Test behavior extensively, especially AI/goals and inventory systems")
        if behavior.get("behavior_diff") == "significant":
            recommendations.append("Manual testing recommended due to significant behavior differences")
        
        if not assets.get("all_assets_valid", True):
            recommendations.append("Review and fix invalid asset files")
        
        if not manifest.get("is_valid", True):
            recommendations.append("Fix manifest validation errors before deploying")
        
        if not recommendations:
            recommendations.append("Conversion appears to be in good shape")
        
        return recommendations


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


class ValidationReportResponse(ValidationReportModel):
    validation_job_id: str = Field(..., description="The ID of the validation job that produced this report.")
    retrieved_at: str = Field(..., description="Timestamp when the report was retrieved.")


router = APIRouter(tags=["Validation"], responses={404: {"description": "Not found"}})

_validation_jobs_lock = threading.Lock()
_validation_reports_lock = threading.Lock()
validation_jobs: Dict[str, ValidationJob] = {}
validation_reports: Dict[str, ValidationReportModel] = {}


def get_validation_agent():
    return ValidationAgent()


async def process_validation_task(job_id: str, conversion_id: str, artifacts: Dict[str, Any], agent: ValidationAgent):
    print(f"Background task started for job_id: {job_id}")

    with _validation_jobs_lock:
        if job_id not in validation_jobs:
            print(f"Error: Job ID {job_id} not found in process_validation_task.")
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

        await asyncio.sleep(0.5)
        report = agent.validate_conversion(agent_input_artifacts)

        with _validation_reports_lock:
            validation_reports[job_id] = report

        with _validation_jobs_lock:
            validation_jobs[job_id].status = ValidationJobStatus.COMPLETED
            validation_jobs[job_id].message = ValidationMessages.JOB_COMPLETED

        print(f"Background task completed for job_id: {job_id}")

    except Exception as e:
        print(f"Error during validation for job_id {job_id}: {str(e)}")

        with _validation_jobs_lock:
            validation_jobs[job_id].status = ValidationJobStatus.FAILED
            validation_jobs[job_id].message = f"{ValidationMessages.JOB_FAILED}: {str(e)}"


@router.post("/", response_model=ValidationJob, status_code=202)
async def start_validation_job(request: ValidationRequest, background_tasks: BackgroundTasks, agent: ValidationAgent = Depends(get_validation_agent)):
    job_id = str(uuid.uuid4())
    conversion_id = request.conversion_id
    if not conversion_id:
        raise HTTPException(status_code=400, detail=ValidationMessages.CONVERSION_ID_REQUIRED)

    job = ValidationJob(
        job_id=job_id,
        conversion_id=conversion_id,
        status=ValidationJobStatus.QUEUED,
        message=ValidationMessages.JOB_QUEUED,
    )

    with _validation_jobs_lock:
        validation_jobs[job_id] = job

    artifacts_for_agent = {
        "java_code_snippet": request.java_code_snippet,
        "bedrock_code_snippet": request.bedrock_code_snippet,
        "asset_file_paths": request.asset_file_paths,
        "manifest_content": request.manifest_content,
    }

    background_tasks.add_task(process_validation_task, job_id, conversion_id, artifacts_for_agent, agent)
    print(f"Validation job {job_id} for conversion {conversion_id} queued.")
    return job


@router.get("/{job_id}/status", response_model=ValidationJob)
async def get_validation_job_status(job_id: str):
    with _validation_jobs_lock:
        job = validation_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=ValidationMessages.JOB_NOT_FOUND)
        return job


@router.get("/{job_id}/report", response_model=ValidationReportResponse)
async def get_validation_report(job_id: str):
    with _validation_jobs_lock:
        job = validation_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=ValidationMessages.JOB_NOT_FOUND)
        if job.status != ValidationJobStatus.COMPLETED:
            raise HTTPException(status_code=400, detail=f"Validation job status is '{job.status}'. {ValidationMessages.REPORT_NOT_AVAILABLE}")

    with _validation_reports_lock:
        report_data = validation_reports.get(job_id)
        if not report_data:
            raise HTTPException(status_code=404, detail="Validation report data not found, though job completed.")

    response_payload = report_data.model_dump()
    response_payload["validation_job_id"] = job_id
    response_payload["retrieved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return ValidationReportResponse(**response_payload)
