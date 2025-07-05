"""
ModPorter AI Backend API
Modern FastAPI implementation
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ModPorter AI Backend",
    description="AI-powered Minecraft Java to Bedrock mod conversion",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class ConversionRequest(BaseModel):
    file_name: Optional[str] = None
    target_version: str = "1.20.0"
    options: Optional[Dict[str, Any]] = None

# In-memory storage for testing (would be replaced with database)
conversions_db: Dict[str, Dict[str, Any]] = {}
uploaded_files: List[str] = []

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/health")
async def health_check_v1():
    """Health check endpoint (v1 API)"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a mod file for conversion"""
    # Validate file type
    allowed_types = ["application/java-archive", "application/zip", "application/octet-stream"]
    allowed_extensions = [".jar", ".zip", ".mcaddon"]
    
    if file.content_type not in allowed_types and not any(file.filename.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} is not supported. Please upload .jar, .zip, or .mcaddon files."
        )
    
    # Store filename in memory (in real app, would save to storage)
    uploaded_files.append(file.filename)
    
    return {
        "filename": file.filename,
        "message": f"File {file.filename} uploaded successfully"
    }

@app.post("/api/convert")
async def start_conversion(request: ConversionRequest):
    """Start a conversion job"""
    if not request.file_name:
        raise HTTPException(
            status_code=422,
            detail="file_name is required"
        )
    
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
        "created_at": datetime.now().isoformat()
    }
    
    conversions_db[job_id] = conversion_data
    
    return conversion_data

@app.get("/api/convert")
async def list_conversions():
    """List all conversion jobs"""
    return list(conversions_db.values())

@app.get("/api/convert/{job_id}")
async def get_conversion_status(job_id: str):
    """Get conversion job status"""
    if job_id not in conversions_db:
        raise HTTPException(
            status_code=404,
            detail="Conversion job not found"
        )
    
    return conversions_db[job_id]

@app.delete("/api/convert/{job_id}")
async def cancel_conversion(job_id: str):
    """Cancel a conversion job"""
    if job_id not in conversions_db:
        raise HTTPException(
            status_code=404,
            detail="Conversion job not found"
        )
    
    conversions_db[job_id]["status"] = "cancelled"
    
    return {
        "message": f"Conversion job {job_id} has been cancelled"
    }

@app.get("/api/download/{job_id}")
async def download_converted_mod(job_id: str):
    """Download converted mod"""
    if job_id not in conversions_db:
        raise HTTPException(
            status_code=404,
            detail="Conversion job not found"
        )
    
    conversion = conversions_db[job_id]
    if conversion["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail="Conversion not completed yet"
        )
    
    # In real implementation, would return file download
    return {"download_url": f"/files/{job_id}.mcaddon"}

@app.post("/api/v1/convert")
async def convert_mod_v1(
    mod_file: Optional[UploadFile] = File(None),
    mod_url: Optional[str] = None,
    smart_assumptions: bool = True,
    include_dependencies: bool = True
):
    """
    Convert Java mod to Bedrock add-on (v1 API)
    Implements PRD Feature 1: One-Click Modpack Ingestion
    """
    if not mod_file and not mod_url:
        raise HTTPException(
            status_code=400,
            detail="Either mod_file or mod_url must be provided"
        )
    
    # TODO: Implement actual conversion logic
    return {
        "conversion_id": "mock-conversion-id",
        "status": "processing",
        "overall_success_rate": 0.0,
        "converted_mods": [],
        "failed_mods": [],
        "smart_assumptions_applied": [],
        "detailed_report": {
            "stage": "initialization",
            "progress": 0,
            "logs": ["Conversion started"],
            "technical_details": {}
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)