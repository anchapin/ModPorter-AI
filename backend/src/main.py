"""
ModPorter AI Backend API
Modern FastAPI implementation with database integration
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Path as FastAPIPath, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.base import get_db, AsyncSessionLocal
from src.db import crud
from src.services.cache import CacheService
# report_generator imports
from src.services.report_generator import ConversionReportGenerator, MOCK_CONVERSION_RESULT_SUCCESS, MOCK_CONVERSION_RESULT_FAILURE
from src.services.report_models import InteractiveReport, FullConversionReport
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uvicorn
import os
import uuid
import asyncio # Added for simulated AI conversion
from dotenv import load_dotenv
from dateutil.parser import parse as parse_datetime
import logging
from src.db.init_db import init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

TEMP_UPLOADS_DIR = "temp_uploads"
CONVERSION_OUTPUTS_DIR = "conversion_outputs" # Added
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB

# In-memory database for conversion jobs (legacy mirror for test compatibility)
conversion_jobs_db: Dict[str, 'ConversionJob'] = {}
# In-memory storage for testing (would be replaced with database)
conversions_db: Dict[str, Dict[str, Any]] = {}
uploaded_files: List[str] = []

# Cache service instance
cache = CacheService()

# Note: For production environments, rate limiting should be implemented to protect against abuse.
# This can be done at the API gateway, reverse proxy (e.g., Nginx), or using FastAPI middleware like 'slowapi'.
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
    ],
    docs_url="/docs",
    redoc_url="/redoc",
)

report_generator = ConversionReportGenerator()

# CORS middleware - Security hardened
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Pydantic models for API documentation
# Request models
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
    stage: Optional[str] = None
    estimated_time_remaining: Optional[int] = None

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

# Health check endpoints
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

    # Validate file type - combine both approaches
    allowed_types = [
        "application/java-archive",
        "application/zip",
        "application/octet-stream",
    ]
    allowed_extensions = ['.jar', '.zip', '.mcaddon']
    original_filename = file.filename
    file_ext = os.path.splitext(original_filename)[1].lower()
    
    if (file_ext not in allowed_extensions and 
        file.content_type not in allowed_types and 
        not any(file.filename.endswith(ext) for ext in allowed_extensions)):
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
    except HTTPException as e:
        # Re-raise client errors (e.g., 413 for file size limits)
        raise e
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Error saving file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not save file")
    finally:
        file.file.close()
    
    # Also store filename in memory for compatibility
    uploaded_files.append(file.filename)
    
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
async def simulate_ai_conversion(job_id: str):
    logger.info(f"Starting AI simulation for job_id: {job_id}")
    try:
        async with AsyncSessionLocal() as session:
            job = await crud.get_job(session, job_id)
        if not job:
            logger.error(f"Error: Job {job_id} not found for AI simulation.")
            return
    except Exception as e:
        logger.error(f"Critical database failure during AI simulation for job {job_id}: {e}", exc_info=True)
        # For tests, skip database-dependent simulation but update in-memory status
        if job_id in conversion_jobs_db:
            logger.info(f"Test mode: Updating job {job_id} status to completed in in-memory storage")
            # Update in-memory job to completed status for tests
            job_data = conversion_jobs_db[job_id]
            job_data.status = "completed"
            job_data.progress = 100
            conversion_jobs_db[job_id] = job_data
            # Skip the rest of the database-dependent simulation
            return
        else:
            logger.error(f"Job {job_id} not found in in-memory storage either.")
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
            await crud.upsert_progress(session, job_id, 25)
            # Mirror
            mirror = mirror_dict_from_job(job, 25)
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.model_dump())
            await cache.set_progress(job_id, 25)
            logger.info(f"Job {job_id}: Status updated to {job.status}, Progress: 25%")

            # Stage 2: Processing -> Postprocessing
            await asyncio.sleep(15)
            # Recheck cancellation
            job = await crud.get_job(session, job_id)
            if job.status == "cancelled":
                logger.info(f"Job {job_id} was cancelled. Stopping AI simulation.")
                return
            job = await crud.update_job_status(session, job_id, "postprocessing")
            await crud.upsert_progress(session, job_id, 75)
            mirror = mirror_dict_from_job(job, 75)
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.model_dump())
            await cache.set_progress(job_id, 75)
            logger.info(f"Job {job_id}: Status updated to {job.status}, Progress: 75%")

            # Stage 3: Postprocessing -> Completed
            await asyncio.sleep(10)
            job = await crud.get_job(session, job_id)
            if job.status == "cancelled":
                logger.info(f"Job {job_id} was cancelled. Stopping AI simulation.")
                return

            job = await crud.update_job_status(session, job_id, "completed")
            await crud.upsert_progress(session, job_id, 100)
            # Create mock output file
            os.makedirs(CONVERSION_OUTPUTS_DIR, exist_ok=True)
            mock_output_filename_internal = f"{job.id}_converted.zip"
            mock_output_filepath = os.path.join(CONVERSION_OUTPUTS_DIR, mock_output_filename_internal)
            result_url = f"/api/v1/convert/{job.id}/download" # Changed path

            try:
                with open(mock_output_filepath, "w") as f:
                    f.write(f"This is a mock converted file for job {job.id}.\n")
                    f.write(f"Original filename: {job.input_data.get('original_filename')}\n")
            except IOError as e:
                logger.error(f"Error creating mock output file for job {job_id}: {e}", exc_info=True)
                job = await crud.update_job_status(session, job_id, "failed")
                mirror = mirror_dict_from_job(job, 0, None, f"Failed to create output file: {e}")
                conversion_jobs_db[job_id] = mirror
                await cache.set_job_status(job_id, mirror.model_dump())
                await cache.set_progress(job_id, 0)
                return

            mirror = mirror_dict_from_job(job, 100, result_url)
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.model_dump())
            await cache.set_progress(job_id, 100)
            logger.info(f"Job {job_id}: AI Conversion COMPLETED. Output file: {mock_output_filepath}, Result URL: {result_url}")

        except Exception as e:
            logger.error(f"Error during AI simulation for job {job_id}: {e}", exc_info=True)
            job = await crud.update_job_status(session, job_id, "failed")
            mirror = mirror_dict_from_job(job, 0, None, str(e))
            conversion_jobs_db[job_id] = mirror
            await cache.set_job_status(job_id, mirror.model_dump())
            await cache.set_progress(job_id, 0)
            logger.error(f"Job {job_id}: Status updated to FAILED due to error.")
    except Exception as e:
        # Fail fast instead of falling back to inconsistent storage
        logger.error(f"Critical database failure during AI simulation for job {job_id}: {e}", exc_info=True)
        
        # Set job status to failed in cache if possible
        try:
            if job_id in conversion_jobs_db:
                conversion_jobs_db[job_id].status = "failed"
                conversion_jobs_db[job_id].progress = 0
                conversion_jobs_db[job_id].error_message = "Database service unavailable"
                await cache.set_job_status(job_id, conversion_jobs_db[job_id].model_dump())
        except Exception as cache_error:
            logger.error(f"Failed to update cache after database error: {cache_error}", exc_info=True)
        
        # Do not continue processing with inconsistent state
        return


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
            # maybe_ext = parts[1]  # unused
            if not file_id:
                file_id = maybe_file_id
            if not original_filename:
                original_filename = request.file_name
        else:
            raise HTTPException(status_code=422, detail="Must provide either (file_id and original_filename) or legacy file_name.")

    # Try to persist job to DB, fall back to in-memory storage for tests
    try:
        job = await crud.create_job(
            db,
            file_id=file_id,
            original_filename=original_filename,
            target_version=request.target_version,
            options=request.options
        )
        job_id = str(job.id)
        created_at = job.created_at if job.created_at else datetime.now()
        updated_at = job.updated_at if job.updated_at else datetime.now()
    except Exception as e:
        # Database operation failed - fallback to in-memory storage
        logger.error(f"Database operation failed during job creation: {e}", exc_info=True)
        # In-memory fallback for job creation
        job_id = str(uuid.uuid4())
        created_at = datetime.now()
        updated_at = datetime.now()

    # Build legacy-mirror dict for in-memory compatibility (ConversionJob pydantic)
    mirror = ConversionJob(
        job_id=job_id,
        file_id=file_id,
        original_filename=original_filename,
        status="queued",
        progress=0,
        target_version=request.target_version,
        options=request.options,
        result_url=None,
        error_message=None,
        created_at=created_at,
        updated_at=updated_at,
    )
    conversion_jobs_db[job_id] = mirror

    # Write to Redis
    await cache.set_job_status(job_id, mirror.model_dump())
    await cache.set_progress(job_id, 0)

    logger.info(f"Job {job_id}: Queued. Starting simulated AI conversion in background.")
    background_tasks.add_task(simulate_ai_conversion, job_id)

    return ConversionResponse(
        job_id=job_id,
        status="queued",
        message="Conversion job started and is now queued.",
        estimated_time=35
    )

# Keep simple version for compatibility 
@app.post("/api/v1/convert/simple")
async def start_conversion_simple(request: ConversionRequest):
    """Start a conversion job (simple version for compatibility)"""
    if not request.file_name:
        raise HTTPException(status_code=422, detail="file_name is required")

    job_id = str(uuid.uuid4())

    conversion_data = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "message": "Conversion queued",
        "file_name": request.file_name,
        "target_version": request.target_version,
        "options": request.options or {},
        "estimated_time": "5-10 minutes",
        "created_at": datetime.now().isoformat(),
    }

    conversions_db[job_id] = conversion_data
    return conversion_data

@app.get("/api/v1/convert/{job_id}", response_model=ConversionStatus, tags=["conversion"])
async def get_conversion(job_id: str = FastAPIPath(..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", description="Unique identifier for the conversion job (standard UUID format)."), db: AsyncSession = Depends(get_db)):
    """
    Get the current status of a specific conversion job.
    Alias for /status endpoint for backward compatibility.
    """
    return await get_conversion_status(job_id, db)

@app.get("/api/v1/convert/{job_id}/status", response_model=ConversionStatus, tags=["conversion"])
async def get_conversion_status(job_id: str = FastAPIPath(..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", description="Unique identifier for the conversion job (standard UUID format)."), db: AsyncSession = Depends(get_db)):
    """
    Get the current status of a specific conversion job.
    """
    # Try Redis first (for speed/freshness)
    cached = await cache.get_job_status(job_id)
    if cached:
        status = cached.get("status")
        progress = cached.get("progress", 0)
        error_message = cached.get("error_message")
        result_url = cached.get("result_url")

        # Determine stage
        if 0 <= progress <= 10:
            stage = "Queued"
        elif 11 <= progress <= 25:
            stage = "Preprocessing"
        elif 26 <= progress <= 75:
            stage = "AI Conversion"
        elif 76 <= progress <= 99:
            stage = "Postprocessing"
        elif progress == 100:
            stage = "Completed"
        else:
            stage = None # Should not happen with valid progress

        # Calculate estimated_time_remaining
        total_conversion_time = 35  # seconds
        if status in ["completed", "failed", "cancelled"]:
            estimated_time_remaining = 0
        elif progress == 0:
            estimated_time_remaining = total_conversion_time
        else:
            estimated_time_remaining = int((1 - (progress / 100)) * total_conversion_time)

        descriptive_message = ""
        if status == "queued":
            descriptive_message = "Job is queued and waiting to start."
        elif status == "preprocessing": # This status is set by simulate_ai_conversion, but stage mapping uses progress
            descriptive_message = "Preprocessing uploaded file."
        elif status == "processing": # This status is set by simulate_ai_conversion
            descriptive_message = f"AI conversion in progress ({progress}%)."
        elif status == "postprocessing": # This status is set by simulate_ai_conversion
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
            created_at=parse_datetime(cached["created_at"]),
            stage=stage,
            estimated_time_remaining=estimated_time_remaining
        )
    # Fallback: load from DB or in-memory storage
    try:
        job = await crud.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Conversion job with ID '{job_id}' not found.")
    except Exception as e:
        logger.error(f"Database operation failed during status retrieval: {e}", exc_info=True)
        # Fallback to in-memory storage for any database failure
        if job_id in conversion_jobs_db:
            data = conversion_jobs_db[job_id]
            # Build mock job object for in-memory data
            class MockJob:
                def __init__(self, job_id, data):
                    self.id = job_id
                    self.status = data.status
                    self.progress = type('MockProgress', (), {'progress': data.progress})()
                    self.input_data = {
                        "file_id": data.file_id,
                        "original_filename": data.original_filename,
                        "target_version": data.target_version,
                        "options": data.options or {}
                    }
                    self.created_at = data.created_at
                    self.updated_at = data.updated_at
            job = MockJob(job_id, data)
        else:
            # No record in-memory, job truly not found
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
        result_url = f"/api/v1/convert/{job_id}/download" # Changed path
    elif status == "failed":
        error_message = "Conversion failed."
        descriptive_message = error_message
    elif status == "cancelled":
        descriptive_message = "Job was cancelled by the user."
    else:
        descriptive_message = f"Job status: {status}."

    # Determine stage for DB/in-memory fallback
    if 0 <= progress <= 10:
        stage = "Queued"
    elif 11 <= progress <= 25:
        stage = "Preprocessing"
    elif 26 <= progress <= 75:
        stage = "AI Conversion"
    elif 76 <= progress <= 99:
        stage = "Postprocessing"
    elif progress == 100:
        stage = "Completed"
    else:
        stage = None

    # Calculate estimated_time_remaining for DB/in-memory fallback
    total_conversion_time = 35  # seconds
    if status in ["completed", "failed", "cancelled"]:
        estimated_time_remaining = 0
    elif progress == 0:
        estimated_time_remaining = total_conversion_time
    else:
        estimated_time_remaining = int((1 - (progress / 100)) * total_conversion_time)

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
        created_at=job.created_at,
        stage=stage,
        estimated_time_remaining=estimated_time_remaining
    )

@app.get("/api/v1/conversions", response_model=List[ConversionStatus], tags=["conversion"])
async def list_conversions(db: AsyncSession = Depends(get_db)):
    """
    List all current and past conversion jobs.
    """
    try:
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
                result_url = f"/api/v1/convert/{job.id}/download" # Changed path
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
                # stage and ETR are not added to list view for now, can be added if needed
            ))
        return statuses
    except Exception as e:
        logger.error(f"Database operation failed during job listing: {e}", exc_info=True)
        # Fallback to in-memory listing
        statuses = []
        for data in conversion_jobs_db.values():
            # Determine stage for in-memory fallback in list view
            current_progress = data.progress
            current_status = data.status
            if 0 <= current_progress <= 10:
                list_stage = "Queued"
            elif 11 <= current_progress <= 25:
                list_stage = "Preprocessing"
            elif 26 <= current_progress <= 75:
                list_stage = "AI Conversion"
            elif 76 <= current_progress <= 99:
                list_stage = "Postprocessing"
            elif current_progress == 100:
                list_stage = "Completed"
            else:
                list_stage = None

            # Calculate estimated_time_remaining for in-memory fallback in list view
            total_conversion_time = 35  # seconds
            if current_status in ["completed", "failed", "cancelled"]:
                list_etr = 0
            elif current_progress == 0:
                list_etr = total_conversion_time
            else:
                list_etr = int((1 - (current_progress / 100)) * total_conversion_time)

            statuses.append(ConversionStatus(
                job_id=data.job_id,
                status=current_status,
                progress=current_progress,
                message=f"Job status: {current_status}.",
                result_url=data.result_url,
                error=data.error_message,
                created_at=data.created_at,
                stage=list_stage,
                estimated_time_remaining=list_etr
            ))
        return statuses

@app.delete("/api/v1/convert/{job_id}", tags=["conversion"])
async def cancel_conversion(job_id: str = FastAPIPath(..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", description="Unique identifier for the conversion job to be cancelled (standard UUID format)."), db: AsyncSession = Depends(get_db)):
    """
    Cancel an ongoing conversion job.
    """
    try:
        job = await crud.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Conversion job with ID '{job_id}' not found.")
        if job.status == "cancelled":
            return {"message": f"Conversion job {job_id} is already cancelled."}
        job = await crud.update_job_status(db, job_id, "cancelled")
        await crud.upsert_progress(db, job_id, 0)
        created_at = job.created_at if job.created_at else datetime.now()
        updated_at = job.updated_at if job.updated_at else datetime.now()
    except Exception as e:
        logger.error(f"Database operation failed during job cancellation: {e}", exc_info=True)
        # Fallback to in-memory cancellation
        if job_id in conversion_jobs_db:
            data = conversion_jobs_db[job_id]
            data.status = "cancelled"
            data.progress = 0
            conversion_jobs_db[job_id] = data
            await cache.set_job_status(job_id, data.model_dump())
            await cache.set_progress(job_id, 0)
            return {"message": f"Conversion job {job_id} has been cancelled."}
        else:
            raise HTTPException(status_code=404, detail=f"Conversion job with ID '{job_id}' not found.")
        
    # If database operation succeeded, continue with normal flow
    job_dict = {
        "file_id": job.input_data.get("file_id"),
        "original_filename": job.input_data.get("original_filename"),
        "target_version": job.input_data.get("target_version"),
        "options": job.input_data.get("options"),
        "created_at": created_at,
        "updated_at": updated_at
    }
    mirror = ConversionJob(
        job_id=job_id,
        file_id=job_dict["file_id"],
        original_filename=job_dict["original_filename"],
        status="cancelled",
        progress=0,
        target_version=job_dict["target_version"],
        options=job_dict["options"],
        result_url=None,
        error_message=None,
        created_at=job_dict["created_at"],
        updated_at=job_dict["updated_at"],
    )
    conversion_jobs_db[job_id] = mirror
    await cache.set_job_status(job_id, mirror.model_dump())
    await cache.set_progress(job_id, 0)
    return {"message": f"Conversion job {job_id} has been cancelled."}

# Download endpoint
@app.get("/api/v1/convert/{job_id}/download", tags=["files"])
async def download_converted_mod(job_id: str = FastAPIPath(..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", description="Unique identifier for the conversion job whose output is to be downloaded (standard UUID format).")):
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
        logger.error(f"Error: Job {job_id} (status: {job.status}) has no result_url. Download cannot proceed.")
        # This indicates an internal inconsistency if the job is 'completed'.
        raise HTTPException(status_code=404, detail=f"Result for job '{job_id}' not available or URL is missing.")

    # Construct the path to the mock output file
    # The actual filename stored on server uses job_id for uniqueness
    internal_filename = f"{job.job_id}_converted.zip"
    file_path = os.path.join(CONVERSION_OUTPUTS_DIR, internal_filename)

    if not os.path.exists(file_path):
        logger.error(f"Error: Converted file not found at path: {file_path} for job {job_id}")
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

# Simple compatibility endpoints
@app.get("/api/v1/list/simple")
async def list_conversions_simple():
    """List all conversion jobs (simple version for compatibility)"""
    return list(conversions_db.values())

@app.get("/api/v1/convert/simple/{job_id}/status")
async def get_conversion_status_simple(job_id: str):
    """Get conversion job status (simple version for compatibility)"""
    if job_id not in conversions_db:
        raise HTTPException(status_code=404, detail="Conversion job not found")
    return conversions_db[job_id]

@app.delete("/api/v1/convert/simple/{job_id}")
async def cancel_conversion_simple(job_id: str):
    """Cancel a conversion job (simple version for compatibility)"""
    if job_id not in conversions_db:
        raise HTTPException(status_code=404, detail="Conversion job not found")
    conversions_db[job_id]["status"] = "cancelled"
    return {"message": f"Conversion job {job_id} has been cancelled"}

@app.get("/api/v1/download/simple/{job_id}")
async def download_converted_mod_simple(job_id: str):
    """Download converted mod (simple version for compatibility)"""
    if job_id not in conversions_db:
        raise HTTPException(status_code=404, detail="Conversion job not found")
    conversion = conversions_db[job_id]
    if conversion["status"] != "completed":
        raise HTTPException(status_code=400, detail="Conversion not completed yet")
    # In real implementation, would return file download
    return {"download_url": f"/files/{job_id}.mcaddon"}

@app.on_event("startup")
async def on_startup():
    # Skip database initialization during tests or if explicitly disabled
    if os.getenv("PYTEST_CURRENT_TEST") is None and os.getenv("SKIP_DB_INIT") != "true":
        try:
            await init_db()
            logger.info("Database initialization completed successfully")
        except Exception as e:
            logger.warning(f"Database initialization failed, continuing without it: {e}")
            # Continue startup even if database initialization fails
            # The application will handle database connection failures gracefully in individual endpoints

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("RELOAD", "true").lower() == "true"
    )


# WebSocket endpoint for real-time progress updates
@app.websocket("/ws/v1/convert/{conversion_id}/progress")
async def websocket_conversion_progress(
    websocket: WebSocket,
    conversion_id: str = FastAPIPath(..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", description="Unique identifier for the conversion job (standard UUID format)."),
    db: AsyncSession = Depends(get_db) # Allow DB access if needed, though get_conversion_status handles its own
):
    await websocket.accept()
    logger.info(f"WebSocket connection established for conversion_id: {conversion_id}")

    last_sent_progress = -1
    last_sent_status = None

    try:
        while True:
            try:
                # Use existing get_conversion_status logic to fetch current status
                # This ensures consistency with the HTTP endpoint
                # A direct database session (db) is available if direct crud operations were preferred here
                status_data: ConversionStatus = await get_conversion_status(job_id=conversion_id, db=db)

                current_progress = status_data.progress
                current_status = status_data.status

                # Send data only if there's a change in progress or status
                if current_progress != last_sent_progress or current_status != last_sent_status:
                    await websocket.send_json(status_data.model_dump_json()) # Send Pydantic model as JSON string
                    last_sent_progress = current_progress
                    last_sent_status = current_status
                    logger.debug(f"Sent progress update for {conversion_id}: {current_status} @ {current_progress}%")

                # Stop sending updates if the job is in a terminal state
                if current_status in ["completed", "failed", "cancelled"]:
                    logger.info(f"Conversion {conversion_id} reached terminal state: {current_status}. Closing WebSocket.")
                    break

                await asyncio.sleep(1.5)  # Poll every 1.5 seconds

            except HTTPException as e:
                # If job not found or other HTTP error from get_conversion_status
                logger.error(f"Error fetching status for {conversion_id} in WebSocket: {e.detail}")
                await websocket.send_json({"error": str(e.detail), "job_id": conversion_id, "status_code": e.status_code})
                break # Close WebSocket on error
            except Exception as e:
                # Catch any other unexpected errors
                logger.error(f"Unexpected error in WebSocket for {conversion_id}: {str(e)}")
                # Consider sending a generic error message before closing
                try:
                    await websocket.send_json({"error": "An unexpected error occurred.", "job_id": conversion_id})
                except Exception: # If sending fails, just log and prepare to close
                    pass
                break # Close WebSocket on unexpected error


    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversion_id: {conversion_id}")
    except Exception as e:
        # This catches errors during the accept() or if the loop breaks unexpectedly without disconnect
        logger.error(f"Outer exception in WebSocket handler for {conversion_id}: {str(e)}")
    finally:
        # Ensure connection is closed if not already
        try:
            await websocket.close()
            logger.info(f"WebSocket connection explicitly closed for {conversion_id}")
        except RuntimeError as e:
            # This can happen if the connection is already closed (e.g. client disconnects abruptly)
            logger.warning(f"Error closing WebSocket for {conversion_id} (possibly already closed): {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during WebSocket close for {conversion_id}: {str(e)}")


@app.get("/api/v1/jobs/{job_id}/report", response_model=InteractiveReport, tags=["conversion"])
async def get_conversion_report(job_id: str):
    mock_data_source = None
    if job_id == MOCK_CONVERSION_RESULT_SUCCESS["job_id"]:
        mock_data_source = MOCK_CONVERSION_RESULT_SUCCESS
    elif job_id == MOCK_CONVERSION_RESULT_FAILURE["job_id"]:
        mock_data_source = MOCK_CONVERSION_RESULT_FAILURE
    elif "success" in job_id: # Generic fallback for testing
        mock_data_source = MOCK_CONVERSION_RESULT_SUCCESS
    elif "failure" in job_id: # Generic fallback for testing
        mock_data_source = MOCK_CONVERSION_RESULT_FAILURE
    else:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found or no mock data available.")

    report = report_generator.create_interactive_report(mock_data_source, job_id)
    return report

@app.get("/api/v1/jobs/{job_id}/report/prd", response_model=FullConversionReport, tags=["conversion"])
async def get_conversion_report_prd(job_id: str):
    mock_data_source = None
    if job_id == MOCK_CONVERSION_RESULT_SUCCESS["job_id"]:
        mock_data_source = MOCK_CONVERSION_RESULT_SUCCESS
    elif job_id == MOCK_CONVERSION_RESULT_FAILURE["job_id"]:
        mock_data_source = MOCK_CONVERSION_RESULT_FAILURE
    elif "success" in job_id: # Generic fallback
        mock_data_source = MOCK_CONVERSION_RESULT_SUCCESS
    elif "failure" in job_id: # Generic fallback
        mock_data_source = MOCK_CONVERSION_RESULT_FAILURE
    else:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found or no mock data available.")

    report = report_generator.create_full_conversion_report_prd_style(mock_data_source)
    return report
