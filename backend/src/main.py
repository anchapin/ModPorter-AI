import os
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from typing import List, Optional
import uuid
import shutil

from db.base import get_db, init_db, AsyncSessionLocal
from db import crud, schemas, models
from db.cache import CacheService

# Legacy global mirrors for conftest.py/test compatibility
conversions_db = []
uploaded_files = {}

app = FastAPI()

# Enable CORS (allow all for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Redis/Cache Service ---

cache_service = CacheService()

# --- Background AI conversion simulation ---

async def simulate_ai_conversion(conversion_id: int, target_format: str):
    # Use dependency-injected AsyncSessionLocal and cache_service
    async with AsyncSessionLocal() as session:
        await cache_service.set_status(conversion_id, "processing")
        # Simulate AI processing (replace with real logic)
        import asyncio
        await asyncio.sleep(1)
        await crud.update_conversion_status(session, conversion_id, "completed")
        await cache_service.set_status(conversion_id, "completed")

# --- API endpoints ---

@app.post("/upload/", response_model=schemas.ConversionOut)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_format: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    # Save uploaded file to disk
    file_id = str(uuid.uuid4())
    upload_dir = "uploaded_files"
    os.makedirs(upload_dir, exist_ok=True)
    file_location = os.path.join(upload_dir, f"{file_id}_{file.filename}")
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create DB record
    conversion = await crud.create_conversion(
        db=db,
        file_path=file_location,
        target_format=target_format,
        status="pending",
        original_filename=file.filename,
    )

    # Legacy test compatibility
    conversions_db.append(conversion)
    uploaded_files[file_id] = file_location

    # Start background conversion
    background_tasks.add_task(simulate_ai_conversion, conversion.id, target_format)
    await cache_service.set_status(conversion.id, "queued")
    return conversion

@app.get("/conversions/", response_model=List[schemas.ConversionOut])
async def list_conversions(db: AsyncSession = Depends(get_db)):
    return await crud.get_conversions(db)

@app.get("/conversion/{conversion_id}", response_model=schemas.ConversionOut)
async def get_conversion(conversion_id: int, db: AsyncSession = Depends(get_db)):
    conv = await crud.get_conversion(db, conversion_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversion not found")
    return conv

@app.get("/conversion/{conversion_id}/status")
async def get_conversion_status(conversion_id: int):
    status = await cache_service.get_status(conversion_id)
    if status is None:
        return JSONResponse({"status": "unknown"})
    return JSONResponse({"status": status})

@app.get("/download/{conversion_id}")
async def download_file(conversion_id: int, db: AsyncSession = Depends(get_db)):
    conv = await crud.get_conversion(db, conversion_id)
    if not conv or not os.path.exists(conv.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(conv.file_path, filename=os.path.basename(conv.file_path))

# --- Startup/shutdown events ---

@app.on_event("startup")
async def on_startup():
    await init_db()