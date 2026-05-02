---
name: add-api-endpoint
description: Add a new REST API endpoint to PortKit's FastAPI backend
---

# Add a New Backend API Endpoint

## Step 1 — Read context
```bash
cat /workspace/CLAUDE.md
cat /workspace/backend/SKELETON.md
```

## Step 2 — Determine if a new router is needed
- If the endpoint logically belongs to an existing domain (`conversion`, `mods`, `jobs`, `health`), add to the existing router file in `backend/routes/`.
- If it's a new domain, create `backend/routes/<domain>.py` and register it.

## Step 3 — Define the Pydantic models
```python
# In backend/routes/<domain>.py  (or backend/models/<domain>.py for complex models)
from pydantic import BaseModel, Field
from typing import Optional

class <Domain>Request(BaseModel):
    field_name: str = Field(..., description="What this field represents")
    optional_field: Optional[str] = Field(None, description="Optional context")

class <Domain>Response(BaseModel):
    task_id: str
    status: str
    message: Optional[str] = None
```

## Step 4 — Write the route using APIRouter
```python
from fastapi import APIRouter, HTTPException, Depends
from celery_app import celery_app  # Celery app instance
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/<domain>", tags=["<domain>"])

@router.post("/convert", response_model=<Domain>Response)
async def convert_<domain>(req: <Domain>Request) -> <Domain>Response:
    """Brief description of what this endpoint does."""
    try:
        task = celery_app.send_task(
            "tasks.<domain>_task",
            args=[req.field_name],
            kwargs={"optional_field": req.optional_field},
        )
        return <Domain>Response(task_id=task.id, status="queued")
    except Exception as e:
        logger.error(f"<domain> conversion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}/status", response_model=<Domain>Response)
async def get_<domain>_status(task_id: str) -> <Domain>Response:
    """Poll task status."""
    result = celery_app.AsyncResult(task_id)
    return <Domain>Response(
        task_id=task_id,
        status=result.status,
        message=str(result.result) if result.ready() else None,
    )
```

## Step 5 — Register the router in main.py
```python
# backend/main.py — add alongside existing routers
from routes.<domain> import router as <domain>_router
app.include_router(<domain>_router)
```

## Step 6 — Write pytest tests
```python
# backend/tests/routes/test_<domain>.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_convert_<domain>_queues_task():
    response = client.post("/api/v1/<domain>/convert", json={"field_name": "test.jar"})
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "queued"

def test_convert_<domain>_missing_field():
    response = client.post("/api/v1/<domain>/convert", json={})
    assert response.status_code == 422  # Pydantic validation error

def test_get_status_unknown_task():
    response = client.get("/api/v1/<domain>/nonexistent-task-id/status")
    assert response.status_code == 200  # AsyncResult always resolves
```

## Step 7 — Run tests
```bash
cd /workspace/backend && python -m pytest tests/routes/test_<domain>.py -v
```

## Checklist
- [ ] Pydantic request/response models defined
- [ ] APIRouter with correct prefix and tags
- [ ] Celery task dispatched (don't block the endpoint)
- [ ] Error handling with HTTPException
- [ ] Router registered in main.py
- [ ] Tests cover: happy path, missing fields, status polling
- [ ] Tests pass
