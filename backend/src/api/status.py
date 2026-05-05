"""
Status page API endpoints for public status page.

Provides aggregated status for:
- Web app / frontend
- API endpoint
- Conversion queue (Celery/Redis)
- Database
- Stripe webhook (optional external check)

Issue #1153: Pre-beta: Uptime monitoring and public status page
"""

import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
import logging

from db.base import async_engine
from services.cache import CacheService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/status", tags=["status"])


class ComponentStatus(BaseModel):
    """Individual component status"""
    name: str
    status: str = Field(..., description="operational, degraded, partial_outage, major_outage, maintenance")
    latency_ms: Optional[float] = None
    message: str = ""
    last_checked: str


class StatusResponse(BaseModel):
    """Public status page response"""
    status: str = Field(..., description="Overall status: operational, degraded, outage, maintenance")
    timestamp: str
    components: List[ComponentStatus]
    message: str = ""


async def check_database() -> ComponentStatus:
    """Check PostgreSQL database connectivity"""
    start = time.time()
    try:
        from sqlalchemy import text
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        latency = (time.time() - start) * 1000
        return ComponentStatus(
            name="Database",
            status="operational",
            latency_ms=round(latency, 2),
            message="PostgreSQL is healthy",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"Database check failed: {e}")
        return ComponentStatus(
            name="Database",
            status="major_outage",
            latency_ms=round(latency, 2),
            message=f"Database unavailable: {str(e)}",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )


async def check_redis() -> ComponentStatus:
    """Check Redis connectivity"""
    start = time.time()
    cache = CacheService()
    try:
        if not cache._redis_available or cache._redis_disabled:
            return ComponentStatus(
                name="Conversion Queue",
                status="degraded",
                message="Redis is not available",
                last_checked=datetime.now(timezone.utc).isoformat(),
            )
        await cache._client.ping()
        latency = (time.time() - start) * 1000
        return ComponentStatus(
            name="Conversion Queue",
            status="operational",
            latency_ms=round(latency, 2),
            message="Redis queue is healthy",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.error(f"Redis check failed: {e}")
        return ComponentStatus(
            name="Conversion Queue",
            status="degraded",
            latency_ms=round(latency, 2),
            message=f"Queue service degraded: {str(e)}",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )


async def check_stripe_webhook() -> ComponentStatus:
    """Check Stripe webhook connectivity (external)"""
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        return ComponentStatus(
            name="Stripe Webhook",
            status="maintenance",
            message="Stripe integration not configured",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )
    start = time.time()
    try:
        import stripe
        stripe.api_key = stripe_key
        stripe.Account.retrieve()
        latency = (time.time() - start) * 1000
        return ComponentStatus(
            name="Stripe Webhook",
            status="operational",
            latency_ms=round(latency, 2),
            message="Stripe connectivity confirmed",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        latency = (time.time() - start) * 1000
        logger.warning(f"Stripe check failed: {e}")
        return ComponentStatus(
            name="Stripe Webhook",
            status="degraded",
            latency_ms=round(latency, 2),
            message=f"Stripe issue: {str(e)[:50]}",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )


@router.get("", response_model=StatusResponse)
async def get_status():
    """
    Get public status for all monitored components.

    Returns aggregated status for:
    - Web App (frontend is always operational if this endpoint is reachable)
    - API (this service)
    - Conversion Queue (Redis/Celery)
    - Database (PostgreSQL)
    - Stripe Webhook

    Reference: Issue #1153
    - Suggested by andrianvaleanu (BetterStack, UptimeRobot, pulsetic.com)
    - Suggested by edifierxuhao (StatusPageBuddy as indie-dev alternative)
    """
    components: List[ComponentStatus] = []

    web_app = ComponentStatus(
        name="Web App",
        status="operational",
        message="Frontend is served and reachable",
        last_checked=datetime.now(timezone.utc).isoformat(),
    )
    components.append(web_app)

    api_status = ComponentStatus(
        name="API",
        status="operational",
        message="API is serving requests",
        last_checked=datetime.now(timezone.utc).isoformat(),
    )
    components.append(api_status)

    db_status = await check_database()
    components.append(db_status)

    redis_status = await check_redis()
    components.append(redis_status)

    stripe_status = await check_stripe_webhook()
    components.append(stripe_status)

    outage_components = [c for c in components if c.status == "major_outage"]
    degraded_components = [c for c in components if c.status == "degraded"]
    maintenance_components = [c for c in components if c.status == "maintenance"]

    if outage_components:
        overall_status = "major_outage"
        overall_message = f"{len(outage_components)} component(s) experiencing outage"
    elif degraded_components:
        overall_status = "degraded"
        overall_message = f"{len(degraded_components)} component(s) degraded"
    elif maintenance_components:
        overall_status = "maintenance"
        overall_message = f"{len(maintenance_components)} component(s) under maintenance"
    else:
        overall_status = "operational"
        overall_message = "All systems operational"

    return StatusResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components,
        message=overall_message,
    )


@router.get("/components", response_model=List[ComponentStatus])
async def get_components():
    """Get detailed status for all components"""
    status = await get_status()
    return status.components


@router.get("/health", response_model=StatusResponse)
async def get_health_status():
    """
    Alias for /status endpoint for health check compatibility.
    """
    return await get_status()