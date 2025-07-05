from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import uvicorn
import os
import uuid
import shutil
import asyncio # Added for simulated AI conversion
from dotenv import load_dotenv

load_dotenv()

TEMP_UPLOADS_DIR = "temp_uploads"
CONVERSION_OUTPUTS_DIR = "conversion_outputs" # Added
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB

# In-memory database for conversion jobs (type annotation added after class definition)
conversion_jobs_db: Dict[str, 'ConversionJob'] = {}

# FastAPI app with OpenAPI configuration
app = FastAPI(
    title="ModPorter AI Backend",
    description="AI-powered tool for converting Minecraft Java Edition mods to Bedrock Edition add-ons",
    version="1.0.0",
    contact={
        "name": "ModPorter AI Team",
        "url": "https://github.com/anchapin/ModPorter-AI",
        "email": "support@modporter-ai.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "conversion",
            "description": "Mod conversion operations",
        },
        {
            "name": "files",
            "description": "File upload and management",
        },
        {
            "name": "health",
            "description": "Health check endpoints",
        },
    ]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API documentation
class ConversionRequest(BaseModel):
    """Request model for mod conversion"""
    file_id: str = Field(..., min_length=1, description="Unique identifier of the uploaded file.")
    original_filename: str = Field(..., min_length=1, description="Original name of the uploaded file.")
    target_version: str = Field(default="1.20.0", description="Target Minecraft version for the conversion.")
    options: Optional[dict] = Field(default=None, description="Optional conversion settings.")

class UploadResponse(BaseModel):
    """Response model for file upload"""
    file_id: str = Field(..., description="Unique identifier assigned to the uploaded file.")
    original_filename: str = Field(..., description="The original name of the uploaded file.")
    saved_filename: str = Field(..., description="The name under which the file is saved on the server (job_id + extension).")
    size: int = Field(..., description="Size of the uploaded file in bytes.")
    content_type: Optional[str] = Field(default=None, description="Detected content type of the uploaded file.")
    message: str = Field(..., description="Status message confirming the upload.")

class ConversionResponse(BaseModel):
    """Response model for mod conversion"""
    job_id: str
    status: str
    message: str
    estimated_time: Optional[int] = None

class ConversionStatus(BaseModel):
    """Status model for conversion job"""
    job_id: str
    status: str
    progress: int
    message: str
    result_url: Optional[str] = None
    error: Optional[str] = None

class ConversionJob(BaseModel):
    """Detailed model for a conversion job"""
    job_id: str
    file_id: str
    original_filename: str
    status: str
    progress: int
    target_version: str
    options: Optional[dict] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    version: str
    timestamp: str

# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Check the health status of the API"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

# File upload endpoint
@app.post("/api/upload", response_model=UploadResponse, tags=["files"])
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a mod file (.jar, .zip, .mcaddon) for conversion.

    - Validates file type and size (max 100MB).
    - Saves the file to a temporary location.
    - Returns a unique file identifier and other file details.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Create temporary uploads directory if it doesn't exist
    os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

    # Validate file size
    if file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds the limit of {MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
        )

    # Validate file type
    allowed_extensions = ['.jar', '.zip', '.mcaddon']
    original_filename = file.filename
    file_ext = os.path.splitext(original_filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not supported. Allowed: {', '.join(allowed_extensions)}"
        )

    # Generate unique file identifier
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{file_ext}"
    file_path = os.path.join(TEMP_UPLOADS_DIR, filename)

    # Save the uploaded file
    try:
        real_file_size = 0
        with open(file_path, "wb") as buffer:
            for chunk in file.file:
                real_file_size += len(chunk)
                if real_file_size > MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File size exceeds the limit of {MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
                    )
                buffer.write(chunk)
    except Exception as e:
        # Log the error for debugging
        print(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail="Could not save file")
    finally:
        file.file.close()
    
    return UploadResponse(
        file_id=file_id,
        original_filename=original_filename,
        saved_filename=filename, # The name with job_id and extension
        size=file.size if file.size else 0, # Ensure size is not None
        content_type=file.content_type,
        message=f"File '{original_filename}' saved successfully as '{filename}'"
    )

# Simulated AI Conversion Engine
async def simulate_ai_conversion(job_id: str = Path(..., description="ID of the job to simulate AI conversion for.")):
    """
    Internal simulation of the AI conversion process.
    This function is run as a background task and is not a user-facing endpoint.
    It updates job status, progress, and creates a mock output file.
    """
    print(f"Starting AI simulation for job_id: {job_id}")
    job = conversion_jobs_db.get(job_id)
    if not job:
        print(f"Error: Job {job_id} not found for AI simulation.")
        return

    try:
        # Stage 1: Preprocessing -> Processing
        await asyncio.sleep(10) # Simulate work
        if job.status == "cancelled":
            print(f"Job {job_id} was cancelled. Stopping AI simulation.")
            return
        job.status = "processing"
        job.progress = 25
        job.updated_at = datetime.utcnow()
        conversion_jobs_db[job_id] = job
        print(f"Job {job_id}: Status updated to {job.status}, Progress: {job.progress}%")

        # Stage 2: Processing -> Postprocessing
        await asyncio.sleep(15) # Simulate more work
        if job.status == "cancelled":
            print(f"Job {job_id} was cancelled. Stopping AI simulation.")
            return
        job.status = "postprocessing"
        job.progress = 75
        job.updated_at = datetime.utcnow()
        conversion_jobs_db[job_id] = job
        print(f"Job {job_id}: Status updated to {job.status}, Progress: {job.progress}%")

        # Stage 3: Postprocessing -> Completed
        await asyncio.sleep(10) # Simulate final work
        if job.status == "cancelled":
            print(f"Job {job_id} was cancelled. Stopping AI simulation.")
            return

        job.status = "completed"
        job.progress = 100
        job.updated_at = datetime.utcnow()

        # Create mock output file
        os.makedirs(CONVERSION_OUTPUTS_DIR, exist_ok=True)
        # Use job_id for the actual stored filename to ensure uniqueness
        mock_output_filename_internal = f"{job.job_id}_converted.zip"
        mock_output_filepath = os.path.join(CONVERSION_OUTPUTS_DIR, mock_output_filename_internal)

        try:
            with open(mock_output_filepath, "w") as f:
                f.write(f"This is a mock converted file for job {job.job_id}.\n")
                f.write(f"Original filename: {job.original_filename}\n")

            job.result_url = f"/api/download/{job.job_id}" # This URL is for the API endpoint
            print(f"Job {job_id}: AI Conversion COMPLETED. Output file: {mock_output_filepath}, Result URL: {job.result_url}")
        except IOError as e:
            print(f"Error creating mock output file for job {job_id}: {e}")
            job.status = "failed"
            job.error_message = f"Failed to create output file: {e}"
            job.result_url = None # Ensure no result URL if file creation failed

        conversion_jobs_db[job_id] = job

    except Exception as e:
        print(f"Error during AI simulation for job {job_id}: {e}")
        if job: # Check if job is still accessible
            job.status = "failed"
            job.error_message = str(e)
            job.updated_at = datetime.utcnow()
            conversion_jobs_db[job_id] = job
            print(f"Job {job_id}: Status updated to FAILED due to error.")


# Conversion endpoints
@app.post("/api/convert", response_model=ConversionResponse, tags=["conversion"])
async def start_conversion(request: ConversionRequest, background_tasks: BackgroundTasks):
    """
    Start a new mod conversion job.

    This endpoint initiates an asynchronous conversion process for a previously uploaded file.
    The `file_id` from the file upload response must be provided.
    The job is queued, and its status can be tracked using the GET /api/convert/{job_id} endpoint.
    """
    job_id = uuid.uuid4().hex
    now = datetime.utcnow()

    # TODO: Validate if file_id from request.file_id actually exists
    # For now, we assume file_id is valid and original_filename is provided

    new_job = ConversionJob(
        job_id=job_id,
        file_id=request.file_id,
        original_filename=request.original_filename,
        status="queued", # Initial status
        progress=0,
        target_version=request.target_version,
        options=request.options,
        created_at=now,
        updated_at=now
    )
    conversion_jobs_db[job_id] = new_job

    # Immediately update status to preprocessing and trigger background task
    new_job.status = "preprocessing"
    new_job.updated_at = datetime.utcnow()
    conversion_jobs_db[job_id] = new_job # Save update

    print(f"Job {new_job.job_id}: Queued. Starting simulated AI conversion in background.")
    background_tasks.add_task(simulate_ai_conversion, new_job.job_id)

    return ConversionResponse(
        job_id=new_job.job_id,
        status=new_job.status, # Return "preprocessing" status
        message="Conversion job started and is now preprocessing.",
        estimated_time=35 # Rough total simulation time (10+15+10)
    )

@app.get("/api/convert/{job_id}", response_model=ConversionStatus, tags=["conversion"])
async def get_conversion_status(job_id: str = Path(..., pattern="^[a-f0-9]{32}$", description="Unique identifier for the conversion job (32-character hex UUID).")):
    """
    Get the current status of a specific conversion job.

    Returns information about the job's progress, current status, and any results or errors.
    """
    job = conversion_jobs_db.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Conversion job with ID '{job_id}' not found.")

    # Construct a descriptive message based on job status
    descriptive_message = ""
    if job.status == "queued":
        descriptive_message = "Job is queued and waiting to start."
    elif job.status == "preprocessing":
        descriptive_message = "Preprocessing uploaded file."
    elif job.status == "processing":
        descriptive_message = f"AI conversion in progress ({job.progress}%)."
    elif job.status == "postprocessing":
        descriptive_message = "Finalizing conversion results."
    elif job.status == "completed":
        descriptive_message = "Conversion completed successfully."
    elif job.status == "failed":
        descriptive_message = f"Conversion failed: {job.error_message}" if job.error_message else "Conversion failed."
    elif job.status == "cancelled":
        descriptive_message = "Job was cancelled by the user."
    else:
        descriptive_message = f"Job status: {job.status}." # Fallback for any other status

    return ConversionStatus(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        message=descriptive_message,
        result_url=job.result_url,
        error=job.error_message
    )

@app.get("/api/convert", response_model=List[ConversionStatus], tags=["conversion"])
async def list_conversions():
    """
    List all current and past conversion jobs.

    Returns a list of status objects for all jobs known to the system.
    """
    statuses = []
    for job in conversion_jobs_db.values():
        message = job.error_message if job.status == "failed" else f"Job status: {job.status}"
        statuses.append(ConversionStatus(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            message=message,
            result_url=job.result_url,
            error=job.error_message
        ))
    return statuses

@app.delete("/api/convert/{job_id}", tags=["conversion"])
async def cancel_conversion(job_id: str = Path(..., pattern="^[a-f0-9]{32}$", description="Unique identifier for the conversion job to be cancelled (32-character hex UUID).")):
    """
    Cancel an ongoing conversion job.

    If the job is found and is in a cancellable state, its status will be set to "cancelled".
    This may not immediately stop all processing if the simulation is in a sleep state,
    but it will prevent further stages from running once the current sleep/task completes.
    """
    job = conversion_jobs_db.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Conversion job with ID '{job_id}' not found.")

    if job.status == "cancelled":
        return {"message": f"Conversion job {job_id} is already cancelled."}

    job.status = "cancelled"
    job.updated_at = datetime.utcnow()
    job.progress = 0 # Or keep progress as is, depending on desired behavior
    # Potentially clear result_url or error_message if needed
    # job.result_url = None
    # job.error_message = "Job was cancelled by user."

    conversion_jobs_db[job_id] = job # Update the job in the db

    return {"message": f"Conversion job {job_id} has been cancelled."}

# Download endpoint
@app.get("/api/download/{job_id}", tags=["files"])
async def download_converted_mod(job_id: str = Path(..., pattern="^[a-f0-9]{32}$", description="Unique identifier for the conversion job whose output is to be downloaded (32-character hex UUID).")):
    """
    Download the converted mod file.

    This endpoint allows downloading the output of a successfully completed conversion job.
    The job must have a status of "completed" and a valid result file available.
    """
    job = conversion_jobs_db.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Conversion job with ID '{job_id}' not found.")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job '{job_id}' is not yet completed. Current status: {job.status}.")

    if not job.result_url: # Should be set if status is completed and file was made
        print(f"Error: Job {job_id} (status: {job.status}) has no result_url. Download cannot proceed.")
        # This indicates an internal inconsistency if the job is 'completed'.
        raise HTTPException(status_code=404, detail=f"Result for job '{job_id}' not available or URL is missing.")

    # Construct the path to the mock output file
    # The actual filename stored on server uses job_id for uniqueness
    internal_filename = f"{job.job_id}_converted.zip"
    file_path = os.path.join(CONVERSION_OUTPUTS_DIR, internal_filename)

    if not os.path.exists(file_path):
        print(f"Error: Converted file not found at path: {file_path} for job {job_id}")
        # This case might indicate an issue post-completion or if the file was manually removed.
        raise HTTPException(status_code=404, detail="Converted file not found on server.")

    # Determine a user-friendly download filename
    original_filename_base = os.path.splitext(job.original_filename)[0]
    download_filename = f"{original_filename_base}_converted.zip"

    return FileResponse(
        path=file_path,
        media_type='application/zip',
        filename=download_filename
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("RELOAD", "true").lower() == "true"
    )