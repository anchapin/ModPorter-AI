from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

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
    file_name: str
    target_version: str = "1.20.0"
    options: Optional[dict] = {}

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

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    version: str
    timestamp: str

# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Check the health status of the API"""
    from datetime import datetime
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

# File upload endpoint
@app.post("/api/upload", tags=["files"])
async def upload_file(file: UploadFile = File(...)):
    """Upload a mod file for conversion"""
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
    
    # TODO: Save file and return file info
    return {
        "filename": file.filename,
        "size": file.size,
        "content_type": file.content_type,
        "message": "File uploaded successfully"
    }

# Conversion endpoints
@app.post("/api/convert", response_model=ConversionResponse, tags=["conversion"])
async def start_conversion(request: ConversionRequest):
    """Start a mod conversion job"""
    # TODO: Implement actual conversion logic
    return ConversionResponse(
        job_id="job_12345",
        status="queued",
        message="Conversion job started",
        estimated_time=300
    )

@app.get("/api/convert/{job_id}", response_model=ConversionStatus, tags=["conversion"])
async def get_conversion_status(job_id: str):
    """Get the status of a conversion job"""
    # TODO: Implement actual status checking
    return ConversionStatus(
        job_id=job_id,
        status="processing",
        progress=45,
        message="Converting mod structure..."
    )

@app.get("/api/convert", response_model=List[ConversionStatus], tags=["conversion"])
async def list_conversions():
    """List all conversion jobs"""
    # TODO: Implement actual job listing
    return [
        ConversionStatus(
            job_id="job_12345",
            status="completed",
            progress=100,
            message="Conversion completed successfully",
            result_url="/api/download/job_12345"
        )
    ]

@app.delete("/api/convert/{job_id}", tags=["conversion"])
async def cancel_conversion(job_id: str):
    """Cancel a conversion job"""
    # TODO: Implement actual job cancellation
    return {"message": f"Conversion job {job_id} cancelled"}

# Download endpoint
@app.get("/api/download/{job_id}", tags=["files"])
async def download_converted_mod(job_id: str):
    """Download the converted mod"""
    # TODO: Implement actual file download
    raise HTTPException(status_code=404, detail="Converted file not found")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("RELOAD", "true").lower() == "true"
    )