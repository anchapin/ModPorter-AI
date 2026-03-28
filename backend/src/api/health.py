"""
Health check endpoints for Kubernetes readiness and liveness probes.

This module provides:
- /health/readiness: Checks if the application can serve traffic (dependencies available)
- /health/liveness: Checks if the application is running and doesn't need to be restarted

Issue #699: Add health check endpoints
Readiness Pillar: Debugging & Observability
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import APIRouter
from pydantic import BaseModel, Field
import logging

from db.base import async_engine
from services.cache import CacheService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    """Health check response model"""

    status: str = Field(..., description="Overall health status: healthy, degraded, or unhealthy")
    timestamp: str = Field(..., description="ISO timestamp of the health check")
    checks: Dict[str, Any] = Field(..., description="Individual check results")


class DependencyHealth(BaseModel):
    """Individual dependency health status"""

    name: str
    status: str
    latency_ms: float = 0.0
    message: str = ""


# Cache service instance (same as in main.py)
cache = CacheService()


async def check_database_health() -> DependencyHealth:
    """
    Check database connectivity and return health status.
    """
    start_time = time.time()

    try:
        from sqlalchemy import text

        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()

        latency_ms = (time.time() - start_time) * 1000

        return DependencyHealth(
            name="database",
            status="healthy",
            latency_ms=latency_ms,
            message="Database connection successful",
        )
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"Database health check failed: {e}")

        return DependencyHealth(
            name="database",
            status="unhealthy",
            latency_ms=latency_ms,
            message=f"Database connection failed: {str(e)}",
        )


async def check_redis_health() -> DependencyHealth:
    """
    Check Redis connectivity and return health status.
    """
    start_time = time.time()

    try:
        # Check if Redis is available through cache service
        if not cache._redis_available or cache._redis_disabled:
            return DependencyHealth(
                name="redis",
                status="unhealthy",
                latency_ms=0.0,
                message="Redis is not available or disabled",
            )

        # Try a simple Redis operation
        await cache._client.ping()

        latency_ms = (time.time() - start_time) * 1000

        return DependencyHealth(
            name="redis",
            status="healthy",
            latency_ms=latency_ms,
            message="Redis connection successful",
        )
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"Redis health check failed: {e}")

        return DependencyHealth(
            name="redis",
            status="unhealthy",
            latency_ms=latency_ms,
            message=f"Redis connection failed: {str(e)}",
        )


@router.get("/health/readiness", response_model=HealthStatus)
async def readiness_check():
    """
    Readiness probe - checks if the application can serve traffic.

    This endpoint verifies that all required dependencies (database, Redis)
    are available. The application should only receive traffic when this
    endpoint returns healthy.

    Returns:
        HealthStatus with detailed dependency information
    """
    checks: List[DependencyHealth] = []

    # Check database
    db_health = await check_database_health()
    checks.append(db_health)

    # Check Redis (optional dependency - can be degraded)
    redis_health = await check_redis_health()
    checks.append(redis_health)

    # Determine overall status
    unhealthy_checks = [c for c in checks if c.status == "unhealthy"]

    if unhealthy_checks:
        # If database is unhealthy, the app cannot serve traffic
        if any(c.name == "database" and c.status == "unhealthy" for c in checks):
            status = "unhealthy"
        else:
            # Redis is optional - degraded status
            status = "degraded"
    else:
        status = "healthy"

    return HealthStatus(
        status=status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks={
            "dependencies": {
                c.name: {
                    "status": c.status,
                    "latency_ms": c.latency_ms,
                    "message": c.message,
                }
                for c in checks
            }
        },
    )


@router.get("/health/liveness", response_model=HealthStatus)
async def liveness_check():
    """
    Liveness probe - checks if the application is running and doesn't need restart.

    This endpoint verifies that the application process is running and can
    handle requests. A failing liveness probe indicates the container should
    be restarted.

    Returns:
        HealthStatus indicating the application is running
    """
    # Liveness only checks if the process is running
    # No dependency checks - we don't want restart loops
    return HealthStatus(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks={
            "application": {
                "status": "running",
                "message": "Application process is running",
            }
        },
    )


@router.get("/health", response_model=HealthStatus)
async def basic_health_check():
    """
    Basic health check endpoint (alias for liveness).

    Returns:
        HealthStatus with basic health information
    """
    return await liveness_check()
