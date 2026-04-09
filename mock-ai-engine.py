"""
Mock AI Engine for Contract Testing

This FastAPI app provides a mock AI conversion endpoint that:
1. Returns valid response structure
2. Validates input format
3. Simulates realistic processing delays
4. Does NOT run actual AI models

Use this for integration testing without hitting real AI infrastructure.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
import time

app = FastAPI(title="Mock AI Engine")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "mock-ai-engine"}


@app.post("/convert")
async def convert(request: dict):
    """
    Mock conversion endpoint.

    Accepts conversion requests and returns a valid response structure
    without actually performing any AI processing.
    """
    # Validate required fields
    if "file_path" not in request and "jar_bytes" not in request:
        return JSONResponse(
            status_code=400, content={"error": "Missing required field: file_path or jar_bytes"}
        )

    if "target_version" not in request:
        return JSONResponse(
            status_code=400, content={"error": "Missing required field: target_version"}
        )

    # Simulate processing delay (optional, can disable with fast=true)
    fast = request.get("fast", False)
    if not fast:
        await asyncio.sleep(0.5)  # Simulate processing time

    # Return valid response structure
    return {
        "success": True,
        "job_id": f"mock-job-{int(time.time() * 1000)}",
        "result_url": "https://storage.example.com/mock-result.mcaddon",
        "validation": {
            "valid": True,
            "warnings": [],
            "parsed_mod": {
                "name": "MockMod",
                "version": "1.0.0",
                "mc_version": request.get("target_version", "1.20.0"),
            },
        },
        "processing_time_ms": 500,
        "model_version": "mock-v1.0",
    }


@app.post("/batch-convert")
async def batch_convert(requests: list[dict]):
    """
    Mock batch conversion endpoint.

    Accepts multiple conversion requests and returns a list of results.
    """
    results = []
    for req in requests:
        result = await convert(req)
        if isinstance(result, JSONResponse):
            results.append({"success": False, "error": "Validation failed"})
        else:
            results.append(result)

    return {"success": True, "total": len(requests), "results": results}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """
    Mock status check endpoint.
    """
    return {
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "result_url": "https://storage.example.com/mock-result.mcaddon",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
