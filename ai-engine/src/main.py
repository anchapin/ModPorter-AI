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
import json
from dotenv import load_dotenv
import redis.asyncio as aioredis

from crew.conversion_crew import ModPorterConversionCrew
from models.smart_assumptions import SmartAssumptionEngine

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

# CORS middleware - Restrict origins for security
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Global instances
conversion_crew = None
assumption_engine = None
redis_client = None

# Redis job state management
class RedisJobManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.available = True
    
    async def set_job_status(self, job_id: str, status: ConversionStatus) -> None:
        """Store job status in Redis with error handling"""
        try:
            if not self.available:
                raise HTTPException(status_code=503, detail="Job state storage unavailable")
            
            status_dict = status.model_dump()
            status_dict['started_at'] = status_dict['started_at'].isoformat() if status_dict['started_at'] else None
            status_dict['completed_at'] = status_dict['completed_at'].isoformat() if status_dict['completed_at'] else None
            
            await self.redis.set(
                f"ai_engine:jobs:{job_id}", 
                json.dumps(status_dict),
                ex=3600  # Expire after 1 hour
            )
        except Exception as e:
            logger.error(f"Failed to store job status in Redis: {e}", exc_info=True)
            self.available = False
            raise HTTPException(status_code=503, detail="Job state storage failed")
    
    async def get_job_status(self, job_id: str) -> Optional[ConversionStatus]:
        """Retrieve job status from Redis with error handling"""
        try:
            if not self.available:
                return None
            
            data = await self.redis.get(f"ai_engine:jobs:{job_id}")
            if not data:
                return None
            
            status_dict = json.loads(data)
            # Convert ISO strings back to datetime
            if status_dict.get('started_at'):
                status_dict['started_at'] = datetime.fromisoformat(status_dict['started_at'])
            if status_dict.get('completed_at'):
                status_dict['completed_at'] = datetime.fromisoformat(status_dict['completed_at'])
                
            return ConversionStatus(**status_dict)
        except Exception as e:
            logger.error(f"Failed to retrieve job status from Redis: {e}", exc_info=True)
            self.available = False
            return None
    
    async def delete_job(self, job_id: str) -> None:
        """Remove job from Redis"""
        try:
            if self.available:
                await self.redis.delete(f"ai_engine:jobs:{job_id}")
        except Exception as e:
            logger.error(f"Failed to delete job from Redis: {e}", exc_info=True)

job_manager = None

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

# Job storage is now handled by RedisJobManager - no global dict

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global conversion_crew, assumption_engine, redis_client, job_manager
    
    logger.info("Starting ModPorter AI Engine...")
    
    try:
        # Initialize Redis connection
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        
        # Test Redis connection
        await redis_client.ping()
        logger.info("Redis connection established")
        
        # Initialize job manager
        job_manager = RedisJobManager(redis_client)
        logger.info("RedisJobManager initialized")
        
        # Initialize SmartAssumptionEngine
        assumption_engine = SmartAssumptionEngine()
        logger.info("SmartAssumptionEngine initialized")
        
        # Initialize ConversionCrew
        conversion_crew = ModPorterConversionCrew()
        logger.info("ModPorterConversionCrew initialized")
        
        logger.info("ModPorter AI Engine startup complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize AI Engine: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Service initialization failed")

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
    
    if not job_manager or not job_manager.available:
        raise HTTPException(status_code=503, detail="Job state storage unavailable")
    
    # Create job status
    job_status = ConversionStatus(
        job_id=request.job_id,
        status="queued",
        progress=0,
        current_stage="initialization",
        message="Conversion job queued",
        started_at=datetime.utcnow()
    )
    
    # Store in Redis instead of global dict
    await job_manager.set_job_status(request.job_id, job_status)
    
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
    
    if not job_manager:
        raise HTTPException(status_code=503, detail="Job state storage unavailable")
    
    job_status = await job_manager.get_job_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_status

@app.get("/api/v1/jobs", response_model=List[ConversionStatus], tags=["conversion"])
async def list_jobs():
    """List all active conversion jobs"""
    if not job_manager or not job_manager.available:
        raise HTTPException(status_code=503, detail="Job state storage unavailable")
    
    # Note: In production, implement pagination and filtering
    # For now, return empty list as Redis doesn't have easy "list all" without keys
    logger.warning("list_jobs endpoint returns empty - implement Redis SCAN for production")
    return []

async def process_conversion(job_id: str, mod_file_path: str, options: Dict[str, Any]):
    """Process a conversion job using the AI crew"""
    
    try:
        # Get current job status
        job_status = await job_manager.get_job_status(job_id)
        if not job_status:
            logger.error(f"Job {job_id} not found during processing")
            return
        
        # Update job status
        job_status.status = "processing"
        job_status.current_stage = "analysis"
        job_status.message = "Analyzing mod structure"
        job_status.progress = 10
        await job_manager.set_job_status(job_id, job_status)
        
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
            # Get and update job status
            job_status = await job_manager.get_job_status(job_id)
            if not job_status:
                logger.error(f"Job {job_id} not found during stage {stage}")
                return
                
            job_status.current_stage = stage
            job_status.message = message
            job_status.progress = progress
            await job_manager.set_job_status(job_id, job_status)
            
            # Simulate processing time
            import asyncio
            await asyncio.sleep(2)
        
        # Mark as completed
        job_status = await job_manager.get_job_status(job_id)
        if job_status:
            job_status.status = "completed"
            job_status.message = "Conversion completed successfully"
            job_status.completed_at = datetime.utcnow()
            await job_manager.set_job_status(job_id, job_status)
        
        logger.info(f"Completed conversion for job {job_id}")
        
    except Exception as e:
        logger.error(f"Conversion failed for job {job_id}: {e}", exc_info=True)
        
        # Update job status to failed
        job_status = await job_manager.get_job_status(job_id)
        if job_status:
            job_status.status = "failed"
            job_status.message = f"Conversion failed: {str(e)}"
            try:
                await job_manager.set_job_status(job_id, job_status)
            except Exception as status_error:
                logger.error(f"Failed to update job status after error: {status_error}", exc_info=True)

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8001)),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )
