"""
ModPorter AI Backend API
Modern FastAPI implementation
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
import uuid
from pathlib import Path
import shutil # For saving file
from backend.src.file_processor import FileProcessor # Import FileProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Note: For production environments, rate limiting should be implemented to protect against abuse.
# This can be done at the API gateway, reverse proxy (e.g., Nginx), or using FastAPI middleware like 'slowapi'.
app = FastAPI(
    title="ModPorter AI API",
    description="AI-powered Minecraft Java to Bedrock mod conversion",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "message": "ModPorter AI Backend is running"
    }

@app.post("/api/v1/convert")
async def convert_mod(
    mod_file: Optional[UploadFile] = File(None),
    mod_url: Optional[str] = None,
    smart_assumptions: bool = True,
    include_dependencies: bool = True,
    background_tasks: BackgroundTasks = None # type: ignore
):
    """
    Convert Java mod to Bedrock add-on
    Implements PRD Feature 1: One-Click Modpack Ingestion
    """
    file_processor = FileProcessor()
    job_id = str(uuid.uuid4())
    # Hypothetical: To get user_id or client_ip, you'd typically need `Request` object as a parameter in your endpoint
    # e.g., async def convert_mod(..., request: Request, background_tasks: BackgroundTasks):
    # user_id = request.state.user.id if hasattr(request, "state") and hasattr(request.state, "user") else "anonymous"
    # client_ip = request.client.host if request.client else "unknown_ip"
    # logger.info(f"Processing request for user: {user_id}, IP: {client_ip}, job_id: {job_id}")
    logger.info(f"Starting conversion request for job_id: {job_id}")

    # Ensure background_tasks is initialized if not provided by FastAPI (e.g. during testing or if None is passed)
    if background_tasks is None:
        background_tasks = BackgroundTasks()

    if not mod_file and not mod_url:
        logger.warning(f"job_id: {job_id} - Missing mod_file and mod_url. Raising HTTPException.")
        # No job_id-specific files created yet by this function, so direct cleanup call for job_id might be premature.
        # However, if job_id itself implies some resource, then it would be relevant.
        # Based on current FileProcessor, job_id folders are created later.
        raise HTTPException(
            status_code=400,
            detail="Either mod_file or mod_url must be provided"
        )

    if mod_file:
        logger.info(f"job_id: {job_id} - Processing uploaded file: {mod_file.filename}")
        validation_result = file_processor.validate_upload(file=mod_file)
        if not validation_result.is_valid:
            logger.error(f"job_id: {job_id} - Uploaded file validation failed: {validation_result.message}")
            # file_processor.validate_upload doesn't create job_id dirs, so cleanup is for any potential future state.
            background_tasks.add_task(file_processor.cleanup_temp_files, job_id)
            raise HTTPException(status_code=400, detail=f"File validation failed: {validation_result.message}")

        sanitized_filename = validation_result.sanitized_filename
        if not sanitized_filename:
             logger.error(f"job_id: {job_id} - Sanitized filename is empty despite successful validation (this should not happen).")
             background_tasks.add_task(file_processor.cleanup_temp_files, job_id)
             raise HTTPException(status_code=500, detail="Internal server error: Sanitized filename not generated.")

        temp_dir = Path(f"/tmp/conversions/{job_id}/uploaded/")
        temp_dir.mkdir(parents=True, exist_ok=True)

        upload_path = temp_dir / sanitized_filename
        try:
            # Ensure file pointer is at the beginning before saving
            mod_file.file.seek(0)
            with upload_path.open("wb") as buffer:
                shutil.copyfileobj(mod_file.file, buffer)
            logger.info(f"job_id: {job_id} - Uploaded file {sanitized_filename} saved to {upload_path}")
        except Exception as e:
            logger.error(f"job_id: {job_id} - Error saving uploaded file {sanitized_filename} to {upload_path}: {e}", exc_info=True)
            background_tasks.add_task(file_processor.cleanup_temp_files, job_id)
            raise HTTPException(status_code=500, detail="Could not save uploaded file.")
        finally:
            mod_file.file.close()

        logger.info(f"job_id: {job_id} - Initiating malware scan for {upload_path} (type: {validation_result.validated_file_type})")
        scan_result = await file_processor.scan_for_malware(
            file_path=upload_path,
            file_type=validation_result.validated_file_type # type: ignore
        )
        if not scan_result.is_safe:
            logger.warning(f"job_id: {job_id} - Malware scan failed for uploaded file {upload_path}: {scan_result.message}")
            background_tasks.add_task(file_processor.cleanup_temp_files, job_id)
            raise HTTPException(status_code=400, detail=f"Security scan failed: {scan_result.message}")

        logger.info(f"job_id: {job_id} - Malware scan successful for uploaded file {upload_path}. File deemed safe.")

        logger.info(f"job_id: {job_id} - Initiating file extraction for {upload_path} (type: {validation_result.validated_file_type})")
        extraction_result = await file_processor.extract_mod_files(
            archive_path=upload_path,
            job_id=job_id,
            file_type=validation_result.validated_file_type # type: ignore
        )
        if not extraction_result.success:
            logger.warning(f"job_id: {job_id} - File extraction failed for uploaded file {upload_path}: {extraction_result.message}")
            background_tasks.add_task(file_processor.cleanup_temp_files, job_id)
            raise HTTPException(status_code=500, detail=f"File extraction failed: {extraction_result.message}")

        logger.info(f"job_id: {job_id} - File extraction successful for uploaded file {upload_path}. Extracted {extraction_result.extracted_files_count} files.")
        current_stage = "extraction_complete"
        current_logs = [
            f"Job {job_id} created.",
            "File validation completed.",
            "Security scan completed.",
            f"File extraction completed: {extraction_result.extracted_files_count} files extracted.",
            f"Manifest info: {extraction_result.message}"
        ]
        technical_details_update = {
            "extracted_files_count": extraction_result.extracted_files_count,
            "found_manifest_type": extraction_result.found_manifest_type,
            "manifest_data": extraction_result.manifest_data,
        }

    elif mod_url:
        logger.info(f"job_id: {job_id} - Processing mod_url: {mod_url}")

        logger.info(f"job_id: {job_id} - Initiating download from URL: {mod_url}")
        download_result = await file_processor.download_from_url(url=mod_url, job_id=job_id)
        if not download_result.success or not download_result.file_path:
            logger.error(f"job_id: {job_id} - Failed to download file from URL {mod_url}: {download_result.message}")
            background_tasks.add_task(file_processor.cleanup_temp_files, job_id)
            raise HTTPException(status_code=400, detail=f"Failed to download file from URL: {download_result.message}")

        downloaded_file_path = download_result.file_path
        logger.info(f"job_id: {job_id} - File {download_result.file_name} downloaded from {mod_url} to {downloaded_file_path}")

        logger.info(f"job_id: {job_id} - Initiating validation for downloaded file: {downloaded_file_path}")
        validation_result = await file_processor.validate_downloaded_file(file_path=downloaded_file_path, original_url=mod_url) # type: ignore
        if not validation_result.is_valid or not validation_result.validated_file_type:
            logger.error(f"job_id: {job_id} - Validation failed for downloaded file {downloaded_file_path} from URL {mod_url}: {validation_result.message}")
            background_tasks.add_task(file_processor.cleanup_temp_files, job_id)
            raise HTTPException(status_code=400, detail=f"Validation failed for downloaded file: {validation_result.message}")

        logger.info(f"job_id: {job_id} - Downloaded file {downloaded_file_path} validated successfully as type: {validation_result.validated_file_type}")

        logger.info(f"job_id: {job_id} - Initiating malware scan for downloaded file {downloaded_file_path} (type: {validation_result.validated_file_type})")
        scan_result = await file_processor.scan_for_malware(
            file_path=downloaded_file_path,
            file_type=validation_result.validated_file_type # type: ignore
        )
        if not scan_result.is_safe:
            logger.warning(f"job_id: {job_id} - Malware scan failed for downloaded file {downloaded_file_path} from URL {mod_url}: {scan_result.message}")
            background_tasks.add_task(file_processor.cleanup_temp_files, job_id)
            raise HTTPException(status_code=400, detail=f"Security scan failed for downloaded file: {scan_result.message}")

        logger.info(f"job_id: {job_id} - Malware scan successful for downloaded file {downloaded_file_path} from URL {mod_url}. File deemed safe.")

        logger.info(f"job_id: {job_id} - Initiating file extraction for downloaded file {downloaded_file_path} (type: {validation_result.validated_file_type})")
        extraction_result = await file_processor.extract_mod_files(
            archive_path=downloaded_file_path,
            job_id=job_id,
            file_type=validation_result.validated_file_type # type: ignore
        )
        if not extraction_result.success:
            logger.warning(f"job_id: {job_id} - File extraction failed for downloaded file {downloaded_file_path} from URL {mod_url}: {extraction_result.message}")
            background_tasks.add_task(file_processor.cleanup_temp_files, job_id)
            raise HTTPException(status_code=500, detail=f"File extraction failed for downloaded file: {extraction_result.message}")

        logger.info(f"job_id: {job_id} - File extraction successful for downloaded file {downloaded_file_path} from URL {mod_url}. Extracted {extraction_result.extracted_files_count} files.")
        current_stage = "extraction_complete_from_url"
        current_logs = [
            f"Job {job_id} created for URL.",
            f"File downloaded from {mod_url}.",
            "Downloaded file validation completed.",
            "Security scan completed for downloaded file.",
            f"File extraction completed: {extraction_result.extracted_files_count} files extracted.",
            f"Manifest info: {extraction_result.message}"
        ]
        technical_details_update = {
            "downloaded_from_url": mod_url,
            "downloaded_file_path": str(downloaded_file_path),
            "validated_file_type": validation_result.validated_file_type,
            "extracted_files_count": extraction_result.extracted_files_count,
            "found_manifest_type": extraction_result.found_manifest_type,
            "manifest_data": extraction_result.manifest_data,
        }
    
    else: # Should be caught by the initial check if not mod_file and not mod_url. This path implies one was true, then became false, which is logically not possible here.
        logger.critical(f"job_id: {job_id} - Logic error: No mod_file or mod_url processed, but initial checks passed. This should not be reached.")
        background_tasks.add_task(file_processor.cleanup_temp_files, job_id) # Still add cleanup as job_id exists
        raise HTTPException(status_code=500, detail="Internal server error: No input processed due to an unexpected state.")

    # Prepare response body
    response_body = {
        "job_id": job_id,
        "status": "pending_analysis", # Next logical status after extraction
        "overall_success_rate": 0.0,
        "converted_mods": [],
        "failed_mods": [],
        "smart_assumptions_applied": [],
        "detailed_report": {
            "stage": current_stage,
            "progress": 10, # Example progress update
            "logs": current_logs,
            "technical_details": technical_details_update
        }
    }

    logger.info(f"job_id: {job_id} - Successfully processed request. Current stage: {current_stage}. Scheduling cleanup and returning response.")
    # Add cleanup task for successful completion too
    background_tasks.add_task(file_processor.cleanup_temp_files, job_id)
    return response_body

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)