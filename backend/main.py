from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Path, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.base import get_db, AsyncSessionLocal
from db import crud
from services.cache import CacheService
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import uvicorn
import os
import uuid
import asyncio # Added for simulated AI conversion
from dotenv import load_dotenv

load_dotenv()

TEMP_UPLOADS_DIR = "temp_uploads"
CONVERSION_OUTPUTS_DIR = "conversion_outputs" # Added
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB

# In-memory database for conversion jobs (legacy mirror for test compatibility)
conversion_jobs_db: Dict[str, 'ConversionJob'] = {}

# Cache service instance
cache = CacheService()

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
    # Legacy
    file_name: Optional[str] = None
    # New
    file_id: Optional[str] = None
    original_filename: Optional[str] = None
    target_version: str = Field(default="1.20.0", description="Target Minecraft version for the conversion.")
    options: Optional[dict] = Field(default=None, description="Optional conversion settings.")

    @property
    def resolved_file_id(self) -> str:
        # Use file_id if provided, else generate a new UUID string (should only happen for tests)
        return self.file_id or str(uuid.uuid4())

    @property
    def resolved_original_name(self) -> str:
        return self.original_filename or self.file_name or ""

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

    # Note: file.size is not always available in FastAPI UploadFile
    # We'll validate size during the actual file reading process

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
        size=real_file_size,  # Use the actual size we read
        content_type=file.content_type,
        message=f"File '{original_filename}' saved successfully as '{filename}'"
    )

# Simulated AI Conversion Engine (DB + Redis + mirror)
async def simulate_ai_conversion(job_id: str):
    print(f"Starting AI simulation for job_id: {job_id}")
    async with AsyncSessionLocal() as session:
        job = await crud.get_job(session, job_id)
        if not job:
            print(f"Error: Job {job_id} not found for AI simulation.")
            return

        def mirror_dict_from_job(job, progress_val=None, result_url=None, error_message=None):
            # Compose dict for legacy mirror
            return ConversionJob(
                job_id=str(job.id),
                file_id=job.input_data.get("file_id"),
                original_filename=job.input_data.get("original_filename"),
                status=job.status,
                progress=(progress_val if progress_val is not None else (job.progress.progress if job.progress else 0)),
                target_version=job.input_data.get("target_version"),
                options=job.input_data.get("options"),
                result_url=result_url if result_url is not None else None,
                error_message=error_message,
                created_at=job.created_at,
                updated_at=job.updated_at
            )

        try:
            # Stage 1: Preprocessing -> Processing
            await asyncio.sleep(10)
            job = await crud.update_job_status(session, job_id, "processing")
            progress = await crud.upsert_progress(session, job_id, 25)
            # Mirror
            mirror = mirror_dict_from_job(job, 25)
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.dict())
            await cache.set_progress(job_id, 25)
            print(f"Job {job_id}: Status updated to {job.status}, Progress: 25%")

            # Stage 2: Processing -> Postprocessing
            await asyncio.sleep(15)
            # Recheck cancellation
            job = await crud.get_job(session, job_id)
            if job.status == "cancelled":
                print(f"Job {job_id} was cancelled. Stopping AI simulation.")
                return
            job = await crud.update_job_status(session, job_id, "postprocessing")
            progress = await crud.upsert_progress(session, job_id, 75)
            mirror = mirror_dict_from_job(job, 75)
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.dict())
            await cache.set_progress(job_id, 75)
            print(f"Job {job_id}: Status updated to {job.status}, Progress: 75%")

            # Stage 3: Postprocessing -> Completed
            await asyncio.sleep(10)
            job = await crud.get_job(session, job_id)
            if job.status == "cancelled":
                print(f"Job {job_id} was cancelled. Stopping AI simulation.")
                return

            job = await crud.update_job_status(session, job_id, "completed")
            progress = await crud.upsert_progress(session, job_id, 100)
            # Create mock output file
            os.makedirs(CONVERSION_OUTPUTS_DIR, exist_ok=True)
            mock_output_filename_internal = f"{job.id}_converted.zip"
            mock_output_filepath = os.path.join(CONVERSION_OUTPUTS_DIR, mock_output_filename_internal)
            result_url = f"/api/download/{job.id}"

            try:
                with open(mock_output_filepath, "w") as f:
                    f.write(f"This is a mock converted file for job {job.id}.\n")
                    f.write(f"Original filename: {job.input_data.get('original_filename')}\n")
            except IOError as e:
                print(f"Error creating mock output file for job {job_id}: {e}")
                job = await crud.update_job_status(session, job_id, "failed")
                mirror = mirror_dict_from_job(job, 0, None, f"Failed to create output file: {e}")
                conversion_jobs_db[job_id] = mirror
                await cache.set_job_status(job_id, mirror.dict())
                await cache.set_progress(job_id, 0)
                return

            mirror = mirror_dict_from_job(job, 100, result_url)
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.dict())
            await cache.set_progress(job_id, 100)
            print(f"Job {job_id}: AI Conversion COMPLETED. Output file: {mock_output_filepath}, Result URL: {result_url}")

        except Exception as e:
            print(f"Error during AI simulation for job {job_id}: {e}")
            job = await crud.update_job_status(session, job_id, "failed")
            mirror = mirror_dict_from_job(job, 0, None, str(e))
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.dict())
            await cache.set_progress(job_id, 0)
            print(f"Job {job_id}: Status updated to FAILED due to error.")


# Conversion endpoints
@app.post("/api/convert", response_model=ConversionResponse, tags=["conversion"])
async def start_conversion(request: ConversionRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Start a new mod conversion job.
    """
    # Persist job to DB (status 'preprocessing', progress 0)
    job = await crud.create_job(
        db,
        file_id=request.file_id,
        original_filename=request.original_filename,
        target_version=request.target_version,
        options=request.options
    )

    # Build legacy-mirror dict for in-memory compatibility (ConversionJob pydantic)
    mirror = ConversionJob(
        job_id=str(job.id),
        file_id=request.file_id,
        original_filename=request.original_filename,
        status="preprocessing",
        progress=0,
        target_version=request.target_version,
        options=request.options,
        result_url=None,
        error_message=None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
    conversion_jobs_db[str(job.id)] = mirror

    # Write to Redis
    await cache.set_job_status(str(job.id), mirror.dict())
    await cache.set_progress(str(job.id), 0)

    print(f"Job {job.id}: Queued. Starting simulated AI conversion in background.")
    background_tasks.add_task(simulate_ai_conversion, str(job.id))

    return ConversionResponse(
        job_id=str(job.id),
        status="preprocessing",
        message="Conversion job started and is now preprocessing.",
        estimated_time=35
    )

@app.get("/api/convert/{job_id}", response_model=ConversionStatus, tags=["conversion"])
async def get_conversion_status(job_id: str = Path(..., pattern="^[a-f0-9]{32}$", description="Unique identifier for the conversion job (32-character hex UUID)."), db: AsyncSession = Depends(get_db)):
    """
    Get the current status of a specific conversion job.
    """
    # Try Redis first (for speed/freshness)
    cached = await cache.get_job_status(job_id)
    if cached:
        # Compose descriptive message
        status = cached.get("status")
        progress = cached.get("progress", 0)
        error_message = cached.get("error_message")
        result_url = cached.get("result_url")
        descriptive_message = ""
        if status == "queued":
            descriptive_message = "Job is queued and waiting to start."
        elif status == "preprocessing":
            descriptive_message = "Preprocessing uploaded file."
        elif status == "processing":
            descriptive_message = f"AI conversion in progress ({progress}%)."
        elif status == "postprocessing":
            descriptive_message = "Finalizing conversion results."
        elif status == "completed":
            descriptive_message = "Conversion completed successfully."
        elif status == "failed":
            descriptive_message = f"Conversion failed: {error_message}" if error_message else "Conversion failed."
        elif status == "cancelled":
            descriptive_message = "Job was cancelled by the user."
        else:
            descriptive_message = f"Job status: {status}."
        return ConversionStatus(
            job_id=job_id,
            status=status,
            progress=progress,
            message=descriptive_message,
            result_url=result_url,
            error=error_message
        )
    # Fallback: load from DB
    job = await crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Conversion job with ID '{job_id}' not found.")
    progress = job.progress.progress if job.progress else 0
    error_message = None
    result_url = None
    status = job.status
    # Compose descriptive message
    if status == "queued":
        descriptive_message = "Job is queued and waiting to start."
    elif status == "preprocessing":
        descriptive_message = "Preprocessing uploaded file."
    elif status == "processing":
        descriptive_message = f"AI conversion in progress ({progress}%)."
    elif status == "postprocessing":
        descriptive_message = "Finalizing conversion results."
    elif status == "completed":
        descriptive_message = "Conversion completed successfully."
        # Only set result_url if job is completed
        result_url = f"/api/download/{job_id}"
    elif status == "failed":
        error_message = "Conversion failed."
        descriptive_message = error_message
    elif status == "cancelled":
        descriptive_message = "Job was cancelled by the user."
    else:
        descriptive_message = f"Job status: {status}."
    # Mirror for legacy tests
    mirror = ConversionJob(
        job_id=str(job.id),
        file_id=job.input_data.get("file_id"),
        original_filename=job.input_data.get("original_filename"),
        status=job.status,
        progress=progress,
        target_version=job.input_data.get("target_version"),
        options=job.input_data.get("options"),
        result_url=result_url,
        error_message=error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
    conversion_jobs_db[job_id] = mirror

    return ConversionStatus(
        job_id=job_id,
        status=status,
        progress=progress,
        message=descriptive_message,
        result_url=result_url,
        error=error_message
    )

@app.get("/api/convert", response_model=List[ConversionStatus], tags=["conversion"])
async def list_conversions(db: AsyncSession = Depends(get_db)):
    """
    List all current and past conversion jobs.
    """
    jobs = await crud.list_jobs(db)
    statuses = []
    for job in jobs:
        progress = job.progress.progress if job.progress else 0
        error_message = None
        result_url = None
        status = job.status
        message = f"Job status: {status}"
        if status == "failed":
            error_message = "Conversion failed."
            message = error_message
        elif status == "completed":
            result_url = f"/api/download/{job.id}"
        # Mirror for legacy tests
        mirror = ConversionJob(
            job_id=str(job.id),
            file_id=job.input_data.get("file_id"),
            original_filename=job.input_data.get("original_filename"),
            status=status,
            progress=progress,
            target_version=job.input_data.get("target_version"),
            options=job.input_data.get("options"),
            result_url=result_url,
            error_message=error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        conversion_jobs_db[str(job.id)] = mirror
        statuses.append(ConversionStatus(
            job_id=str(job.id),
            status=status,
            progress=progress,
            message=message,
            result_url=result_url,
            error=error_message
        ))
    return statuses

@app.delete("/api/convert/{job_id}", tags=["conversion"])
async def cancel_conversion(job_id: str = Path(..., pattern="^[a-f0-9]{32}$", description="Unique identifier for the conversion job to be cancelled (32-character hex UUID)."), db: AsyncSession = Depends(get_db)):
    """
    Cancel an ongoing conversion job.
    """
    job = await crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Conversion job with ID '{job_id}' not found.")
    if job.status == "cancelled":
        return {"message": f"Conversion job {job_id} is already cancelled."}
    job = await crud.update_job_status(db, job_id, "cancelled")
    await crud.upsert_progress(db, job_id, 0)
    mirror = ConversionJob(
        job_id=str(job.id),
        file_id=job.input_data.get("file_id"),
        original_filename=job.input_data.get("original_filename"),
        status="cancelled",
        progress=0,
        target_version=job.input_data.get("target_version"),
        options=job.input_data.get("options"),
        result_url=None,
        error_message=None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
    conversion_jobs_db[job_id] = mirror
    await cache.set_job_status(job_id, mirror.dict())
    await cache.set_progress(job_id, 0)
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

from db.init_db import init_db
@app.on_event("startup")
async def on_startup():
    await init_db()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("RELOAD", "true").lower() == "true"
    )