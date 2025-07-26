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
import httpx  # Add for AI Engine communication
from dotenv import load_dotenv
from db.init_db import init_db
from api.feedback import router as feedback_router

load_dotenv()

# AI Engine settings
AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://localhost:8001")

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

# Include API routers
app.include_router(feedback_router, prefix="/api/v1")

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
    filename: str = Field(..., description="The uploaded filename (matches original_filename)")

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
    created_at: datetime

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
@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Check the health status of the API"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

# File upload endpoint
@app.post("/api/v1/upload", response_model=UploadResponse, tags=["files"])
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
    saved_filename = f"{file_id}{file_ext}"
    file_path = os.path.join(TEMP_UPLOADS_DIR, saved_filename)

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
        saved_filename=saved_filename, # The name with job_id and extension
        size=real_file_size,  # Use the actual size we read
        content_type=file.content_type,
        message=f"File '{original_filename}' saved successfully as '{saved_filename}'",
        filename=original_filename
    )

# Simulated AI Conversion Engine (DB + Redis + mirror)
async def call_ai_engine_conversion(job_id: str):
    """Call the actual AI Engine for conversion instead of simulation"""
    print(f"Starting AI Engine conversion for job_id: {job_id}")
    async with AsyncSessionLocal() as session:
        job = await crud.get_job(session, job_id)
        if not job:
            print(f"Error: Job {job_id} not found for AI Engine conversion.")
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
            # Prepare the output path for AI Engine
            os.makedirs(CONVERSION_OUTPUTS_DIR, exist_ok=True)
            output_filename = f"{job.id}_converted.mcaddon"
            output_path = os.path.join(CONVERSION_OUTPUTS_DIR, output_filename)
            
            # Get the input file path
            input_file_path = os.path.join(TEMP_UPLOADS_DIR, f"{job.input_data.get('file_id')}.jar")
            
            # Call AI Engine
            conversion_options = job.input_data.get("options", {})
            conversion_options["output_path"] = output_path
            
            ai_request = {
                "job_id": job_id,
                "mod_file_path": input_file_path,
                "conversion_options": conversion_options
            }
            
            print(f"Calling AI Engine at {AI_ENGINE_URL}/api/v1/convert with request: {ai_request}")
            
            async with httpx.AsyncClient(timeout=600.0) as client:  # 10 minute timeout
                # Start AI Engine conversion
                response = await client.post(f"{AI_ENGINE_URL}/api/v1/convert", json=ai_request)
                
                if response.status_code != 200:
                    raise Exception(f"AI Engine failed to start conversion: {response.status_code} - {response.text}")
                
                print(f"AI Engine conversion started for job {job_id}")
                
                # Poll AI Engine for status updates
                while True:
                    await asyncio.sleep(2)
                    
                    # Check if job was cancelled
                    current_job = await crud.get_job(session, job_id)
                    if current_job.status == "cancelled":
                        print(f"Job {job_id} was cancelled. Stopping AI Engine polling.")
                        return
                    
                    # Get status from AI Engine
                    status_response = await client.get(f"{AI_ENGINE_URL}/api/v1/status/{job_id}")
                    
                    if status_response.status_code != 200:
                        print(f"Failed to get AI Engine status: {status_response.status_code}")
                        continue
                    
                    ai_status = status_response.json()
                    print(f"AI Engine status for {job_id}: {ai_status}")
                    
                    # Map AI Engine status to backend status
                    backend_status = ai_status["status"]
                    if backend_status == "processing":
                        backend_status = "processing"
                    elif backend_status == "completed":
                        backend_status = "completed"
                    elif backend_status == "failed":
                        backend_status = "failed"
                    
                    # Update database and cache
                    progress = ai_status.get("progress", 0)
                    job = await crud.update_job_status(session, job_id, backend_status)
                    await crud.upsert_progress(session, job_id, progress)
                    
                    # Update in-memory mirror and cache
                    if backend_status == "completed":
                        result_url = f"/api/v1/convert/{job.id}/download"
                        mirror = mirror_dict_from_job(job, progress, result_url)
                    else:
                        mirror = mirror_dict_from_job(job, progress)
                    
                    conversion_jobs_db[job_id] = mirror
                    await cache.set_job_status(job_id, mirror.model_dump())
                    await cache.set_progress(job_id, progress)
                    
                    if backend_status in ["completed", "failed"]:
                        break
                
                if backend_status == "completed":
                    print(f"Job {job_id}: AI Engine conversion COMPLETED. Output should be at: {output_path}")
                    # Verify the file exists
                    if not os.path.exists(output_path):
                        print(f"Warning: Expected output file not found at {output_path}")
                else:
                    print(f"Job {job_id}: AI Engine conversion FAILED")

        except Exception as e:
            print(f"Error during AI Engine conversion for job {job_id}: {e}")
            job = await crud.update_job_status(session, job_id, "failed")
            mirror = mirror_dict_from_job(job, 0, None, str(e))
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.model_dump())
            await cache.set_progress(job_id, 0)
            print(f"Job {job_id}: Status updated to FAILED due to error.")

# Keep the simulation for fallback if AI Engine is not available
async def simulate_ai_conversion(job_id: str):
    """Fallback simulation if AI Engine is not available"""
    print(f"Starting AI simulation fallback for job_id: {job_id}")
    async with AsyncSessionLocal() as session:
        job = await crud.get_job(session, job_id)
        if not job:
            print(f"Error: Job {job_id} not found for AI simulation.")
            return

        def mirror_dict_from_job(job, progress_val=None, result_url=None, error_message=None):
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
            # Quick simulation stages
            await asyncio.sleep(5)
            job = await crud.update_job_status(session, job_id, "processing")
            await crud.upsert_progress(session, job_id, 50)
            mirror = mirror_dict_from_job(job, 50)
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.model_dump())
            await cache.set_progress(job_id, 50)

            await asyncio.sleep(5)
            job = await crud.update_job_status(session, job_id, "completed")
            await crud.upsert_progress(session, job_id, 100)
            
            # Create simple mock file
            os.makedirs(CONVERSION_OUTPUTS_DIR, exist_ok=True)
            mock_output_filename_internal = f"{job.id}_converted.mcaddon"
            mock_output_filepath = os.path.join(CONVERSION_OUTPUTS_DIR, mock_output_filename_internal)
            result_url = f"/api/v1/convert/{job.id}/download"

            with open(mock_output_filepath, "w") as f:
                f.write(f"Mock converted file for job {job.id}.\n")

            mirror = mirror_dict_from_job(job, 100, result_url)
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.model_dump())
            await cache.set_progress(job_id, 100)
            print(f"Job {job_id}: Simulation completed.")

        except Exception as e:
            print(f"Error during simulation for job {job_id}: {e}")
            job = await crud.update_job_status(session, job_id, "failed")
            mirror = mirror_dict_from_job(job, 0, None, str(e))
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.model_dump())
            await cache.set_progress(job_id, 0)
            print(f"Job {job_id}: Status updated to FAILED due to error.")


# Conversion endpoints
@app.post("/api/v1/convert", response_model=ConversionResponse, tags=["conversion"])
async def start_conversion(request: ConversionRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Start a new mod conversion job.
    Handles both legacy (file_name) and new (file_id+original_filename) fields.
    Validates that a file_id and original_filename are resolved.
    """
    # Legacy support: if file_id or original_filename missing, try to resolve from file_name
    file_id = request.file_id
    original_filename = request.original_filename

    if not file_id or not original_filename:
        # Try to resolve from legacy 'file_name'
        if request.file_name:
            # Try to extract file_id from a file_name pattern like "{file_id}.{ext}"
            parts = os.path.splitext(request.file_name)
            maybe_file_id = parts[0]
            # maybe_ext = parts[1]  # unused variable
            if not file_id:
                file_id = maybe_file_id
            if not original_filename:
                original_filename = request.file_name
        else:
            raise HTTPException(status_code=422, detail="Must provide either (file_id and original_filename) or legacy file_name.")

    # Persist job to DB (status 'queued', progress 0)
    job = await crud.create_job(
        db,
        file_id=file_id,
        original_filename=original_filename,
        target_version=request.target_version,
        options=request.options
    )
    # Immediately update job status to 'queued' after creation
    job = await crud.update_job_status(db, job.id, "queued")

    # Build legacy-mirror dict for in-memory compatibility (ConversionJob pydantic)
    # Set mirror status to 'preprocessing', but leave DB as 'queued'
    mirror = ConversionJob(
        job_id=str(job.id),
        file_id=file_id,
        original_filename=original_filename,
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
    await cache.set_job_status(str(job.id), mirror.model_dump())
    await cache.set_progress(str(job.id), 0)

    print(f"Job {job.id}: Queued. Starting AI Engine conversion in background.")
    
    # Try AI Engine first, fallback to simulation if it fails
    background_tasks.add_task(try_ai_engine_or_fallback, str(job.id))

    return ConversionResponse(
        job_id=str(job.id),
        status="preprocessing",
        message="Conversion job started and is now preprocessing.",
        estimated_time=35
    )

@app.get("/api/v1/convert/{job_id}/status", response_model=ConversionStatus, tags=["conversion"])
async def get_conversion_status(job_id: str = Path(..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", description="Unique identifier for the conversion job (standard UUID format)."), db: AsyncSession = Depends(get_db)):
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
            error=error_message,
            created_at=cached.get("created_at", datetime.utcnow()) if cached else datetime.utcnow()
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
        result_url = f"/api/v1/convert/{job_id}/download" # Updated result_url
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
        error=error_message,
        created_at=job.created_at
    )

@app.get("/api/v1/conversions", response_model=List[ConversionStatus], tags=["conversion"])
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
            error=error_message,
            created_at=job.created_at
        ))
    return statuses

@app.delete("/api/v1/convert/{job_id}", tags=["conversion"])
async def cancel_conversion(job_id: str = Path(..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", description="Unique identifier for the conversion job to be cancelled (standard UUID format)."), db: AsyncSession = Depends(get_db)):
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
    await cache.set_job_status(job_id, mirror.model_dump())
    await cache.set_progress(job_id, 0)
    return {"message": f"Conversion job {job_id} has been cancelled."}

# Download endpoint
@app.get("/api/v1/convert/{job_id}/download", tags=["files"])
async def download_converted_mod(job_id: str = Path(..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", description="Unique identifier for the conversion job whose output is to be downloaded (standard UUID format).")):
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
    internal_filename = f"{job.job_id}_converted.mcaddon"
    file_path = os.path.join(CONVERSION_OUTPUTS_DIR, internal_filename)

    if not os.path.exists(file_path):
        print(f"Error: Converted file not found at path: {file_path} for job {job_id}")
        # This case might indicate an issue post-completion or if the file was manually removed.
        raise HTTPException(status_code=404, detail="Converted file not found on server.")

    # Determine a user-friendly download filename
    original_filename_base = os.path.splitext(job.original_filename)[0]
    download_filename = f"{original_filename_base}_converted.mcaddon"

    return FileResponse(
        path=file_path,
        media_type='application/zip',  # Still ZIP format internally
        filename=download_filename
    )

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

async def try_ai_engine_or_fallback(job_id: str):
    """Try AI Engine first, fallback to simulation if it fails"""
    try:
        # Check if AI Engine is available
        async with httpx.AsyncClient(timeout=5.0) as client:
            health_response = await client.get(f"{AI_ENGINE_URL}/api/v1/health")
            if health_response.status_code == 200:
                print(f"AI Engine is available, using real conversion for job {job_id}")
                await call_ai_engine_conversion(job_id)
                return
    except Exception as e:
        print(f"AI Engine not available ({e}), falling back to simulation for job {job_id}")
    
    # Fallback to simulation
    await simulate_ai_conversion(job_id)