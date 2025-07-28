#!/usr/bin/env python3
"""
Simple test backend for dashboard integration
"""
import asyncio
import json
import os
import uuid
import zipfile
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

class JobModel(BaseModel):
    job_id: str
    file_id: str
    original_filename: str
    status: str
    progress: int
    message: str
    target_version: str
    options: Optional[dict]
    created_at: datetime
    result_url: Optional[str] = None
    error: Optional[str] = None

app = FastAPI(title="ModPorter AI Test Backend", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for testing
jobs: Dict[str, JobModel] = {}
uploads_dir = "temp_uploads"
outputs_dir = "conversion_outputs"

# Create directories
os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(outputs_dir, exist_ok=True)

class UploadResponse(BaseModel):
    file_id: str
    original_filename: str
    saved_filename: str
    size: int
    content_type: Optional[str] = None
    message: str
    filename: str

class ConversionRequest(BaseModel):
    file_id: str
    original_filename: str
    target_version: str = "1.20.0"
    options: Optional[dict] = None

class ConversionResponse(BaseModel):
    job_id: str
    status: str
    message: str
    estimated_time: Optional[int] = None

class ConversionStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    result_url: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/v1/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a mod file for conversion."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate file type
    allowed_extensions = ['.jar', '.zip', '.mcaddon']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not supported. Allowed: {', '.join(allowed_extensions)}"
        )

    # Generate unique file identifier
    file_id = str(uuid.uuid4())
    saved_filename = f"{file_id}{file_ext}"
    file_path = os.path.join(uploads_dir, saved_filename)

    # Save the uploaded file
    try:
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not save file")

    return UploadResponse(
        file_id=file_id,
        original_filename=file.filename,
        saved_filename=saved_filename,
        size=len(content),
        content_type=file.content_type,
        message=f"File '{file.filename}' uploaded successfully",
        filename=file.filename
    )

async def simulate_conversion(job_id: str):
    """Simulate the conversion process with progress updates."""
    await asyncio.sleep(2)
    job = jobs[job_id]
    jobs[job_id] = job.model_copy(update={"status": "processing", "progress": 25, "message": "Analyzing mod structure..."})

    await asyncio.sleep(3)
    job = jobs[job_id]
    jobs[job_id] = job.model_copy(update={"progress": 50, "message": "Converting blocks and items..."})

    await asyncio.sleep(3)
    job = jobs[job_id]
    jobs[job_id] = job.model_copy(update={"progress": 75, "message": "Generating Bedrock format..."})

    await asyncio.sleep(2)
    job = jobs[job_id]
    jobs[job_id] = job.model_copy(update={
        "status": "completed", 
        "progress": 100, 
        "message": "Conversion completed successfully!",
        "result_url": f"/api/v1/convert/{job_id}/download"
    })

    # Create a mock output file as a proper ZIP archive
    output_filename = f"{job_id}_converted.mcaddon"
    output_path = os.path.join(outputs_dir, output_filename)
    with zipfile.ZipFile(output_path, "w") as zf:
        info_content = f"Mock converted file for job {job_id}\nOriginal file: {jobs[job_id].original_filename}\nConverted at: {datetime.utcnow().isoformat()}"
        zf.writestr("info.txt", info_content)
        # Add minimal manifest to make it look like a real mcaddon
        manifest_content = {
            "format_version": 2,
            "header": {
                "name": f"Test Conversion {job_id[:8]}",
                "description": "Mock converted addon for testing",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            },
            "modules": [
                {
                    "type": "data",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                }
            ]
        }
        zf.writestr("manifest.json", json.dumps(manifest_content, indent=2))

@app.post("/api/v1/convert", response_model=ConversionResponse)
async def start_conversion(request: ConversionRequest, background_tasks: BackgroundTasks):
    """Start a new mod conversion job."""
    job_id = str(uuid.uuid4())
    
    # Initialize job
    jobs[job_id] = JobModel(
        job_id=job_id,
        file_id=request.file_id,
        original_filename=request.original_filename,
        status="queued",
        progress=0,
        message="Conversion queued",
        target_version=request.target_version,
        options=request.options,
        created_at=datetime.utcnow(),
        result_url=None,
        error=None
    )

    # Start background conversion
    background_tasks.add_task(simulate_conversion, job_id)

    return ConversionResponse(
        job_id=job_id,
        status="queued",
        message="Conversion job started",
        estimated_time=30
    )

@app.get("/api/v1/convert/{job_id}/status", response_model=ConversionStatus)
async def get_conversion_status(job_id: str):
    """Get the current status of a conversion job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = jobs[job_id]
    return ConversionStatus(
        job_id=job_id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        result_url=job.result_url,
        error=job.error,
        created_at=job.created_at
    )

@app.get("/api/v1/convert/{job_id}/download")
async def download_converted_mod(job_id: str):
    """Download the converted mod file."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = jobs[job_id]
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job {job_id} is not completed yet")

    output_filename = f"{job_id}_converted.mcaddon"
    file_path = os.path.join(outputs_dir, output_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Converted file not found")

    # Determine download filename
    original_base = os.path.splitext(job.original_filename)[0]
    download_filename = f"{original_base}_converted.mcaddon"

    return FileResponse(
        path=file_path,
        media_type='application/zip',
        filename=download_filename
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)