"""
ModPorter AI Engine
FastAPI service for AI-powered mod conversion using CrewAI
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import uvicorn
import os
import uuid
import logging
from dotenv import load_dotenv

from .crew.conversion_crew import ModPorterConversionCrew
from .models.smart_assumptions import SmartAssumptionEngine

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.getenv("LOG_LEVEL", "INFO").upper() == "INFO" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI app configuration
app = FastAPI(
    title="ModPorter AI Engine",
    description="AI-powered conversion engine for Minecraft Java to Bedrock mod conversion",
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
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
conversion_crew = None
assumption_engine = None

# Pydantic models
class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    version: str
    timestamp: str
    services: Dict[str, str]

class ConversionRequest(BaseModel):
    """Conversion request model"""
    job_id: str = Field(..., description="Unique job identifier")
    mod_file_path: str = Field(..., description="Path to the mod file")
    conversion_options: Optional[Dict[str, Any]] = Field(default={}, description="Conversion options")

class ConversionResponse(BaseModel):
    """Conversion response model"""
    job_id: str
    status: str
    message: str
    estimated_time: Optional[int] = None

class ConversionStatus(BaseModel):
    """Conversion status model"""
    job_id: str
    status: str
    progress: int
    current_stage: str
    message: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

# In-memory job storage (replace with Redis/database in production)
active_jobs: Dict[str, ConversionStatus] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global conversion_crew, assumption_engine
    
    logger.info("Starting ModPorter AI Engine...")
    
    try:
        # Initialize SmartAssumptionEngine
        assumption_engine = SmartAssumptionEngine()
        logger.info("SmartAssumptionEngine initialized")
        
        # Initialize ConversionCrew
        conversion_crew = ModPorterConversionCrew()
        logger.info("ModPorterConversionCrew initialized")
        
        logger.info("ModPorter AI Engine startup complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize AI Engine: {e}")
        raise

@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Check the health status of the AI Engine"""
    services = {
        "conversion_crew": "healthy" if conversion_crew else "unavailable",
        "assumption_engine": "healthy" if assumption_engine else "unavailable",
    }
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        services=services
    )

@app.post("/api/v1/convert", response_model=ConversionResponse, tags=["conversion"])
async def start_conversion(
    request: ConversionRequest,
    background_tasks: BackgroundTasks
):
    """Start a new mod conversion job"""
    
    if not conversion_crew:
        raise HTTPException(status_code=503, detail="Conversion crew not available")
    
    # Create job status
    job_status = ConversionStatus(
        job_id=request.job_id,
        status="queued",
        progress=0,
        current_stage="initialization",
        message="Conversion job queued",
        started_at=datetime.utcnow()
    )
    
    active_jobs[request.job_id] = job_status
    
    # Start conversion in background
    background_tasks.add_task(
        process_conversion,
        request.job_id,
        request.mod_file_path,
        request.conversion_options
    )
    
    logger.info(f"Started conversion job {request.job_id}")
    
    return ConversionResponse(
        job_id=request.job_id,
        status="queued",
        message="Conversion job started",
        estimated_time=300  # 5 minutes estimate
    )

@app.get("/api/v1/status/{job_id}", response_model=ConversionStatus, tags=["conversion"])
async def get_conversion_status(job_id: str):
    """Get the status of a conversion job"""
    
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return active_jobs[job_id]

@app.get("/api/v1/jobs", response_model=List[ConversionStatus], tags=["conversion"])
async def list_jobs():
    """List all active conversion jobs"""
    return list(active_jobs.values())

async def process_conversion(job_id: str, mod_file_path: str, options: Dict[str, Any]):
    """Process a conversion job using the AI crew"""
    
    try:
        # Update job status
        active_jobs[job_id].status = "processing"
        active_jobs[job_id].current_stage = "analysis"
        active_jobs[job_id].message = "Analyzing mod structure"
        active_jobs[job_id].progress = 10
        
        logger.info(f"Processing conversion for job {job_id}")
        
        # TODO: Implement actual conversion logic using conversion_crew
        # This is a placeholder for the actual AI conversion process
        
        # Simulate conversion stages
        stages = [
            ("analysis", "Analyzing Java mod structure", 20),
            ("planning", "Creating conversion plan", 40),
            ("translation", "Translating logic to Bedrock", 60),
            ("assets", "Converting assets", 80),
            ("packaging", "Packaging Bedrock addon", 90),
            ("validation", "Validating conversion", 100),
        ]
        
        for stage, message, progress in stages:
            active_jobs[job_id].current_stage = stage
            active_jobs[job_id].message = message
            active_jobs[job_id].progress = progress
            
            # Simulate processing time
            import asyncio
            await asyncio.sleep(2)
        
        # Mark as completed
        active_jobs[job_id].status = "completed"
        active_jobs[job_id].message = "Conversion completed successfully"
        active_jobs[job_id].completed_at = datetime.utcnow()
        
        logger.info(f"Completed conversion for job {job_id}")
        
    except Exception as e:
        logger.error(f"Conversion failed for job {job_id}: {e}")
        
        active_jobs[job_id].status = "failed"
        active_jobs[job_id].message = f"Conversion failed: {str(e)}"

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8001)),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )
