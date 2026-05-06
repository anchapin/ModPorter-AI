"""
Sentry configuration for PortKit error monitoring and pipeline alerting.

Issue: #1150 - Pre-beta: Production error monitoring and pipeline alerting

This module provides centralized Sentry initialization for:
- FastAPI application (sync and async)
- Celery workers
- Conversion pipeline errors
"""

import os
import logging
from typing import Optional, Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration

logger = logging.getLogger(__name__)

SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
SENTRY_PROFILES_SAMPLE_RATE = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))
SENTRY_ENABLE_DEV = os.getenv("SENTRY_ENABLE_DEV", "false").lower() == "true"


def _is_enabled() -> bool:
    """Check if Sentry is properly configured."""
    return bool(SENTRY_DSN)


def init_sentry():
    """
    Initialize Sentry for the FastAPI application.

    Called during application startup to configure error tracking,
    performance monitoring, and pipeline alerting.
    """
    if not _is_enabled():
        logger.debug("Sentry DSN not configured, skipping initialization")
        return

    if not SENTRY_ENABLE_DEV and SENTRY_ENVIRONMENT == "development":
        logger.debug("Sentry disabled in development mode (set SENTRY_ENABLE_DEV=true to enable)")
        return

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=False,
        before_send=_filter_events,
        integrations=[
            FastApiIntegration(transaction_naming="http"),
            CeleryIntegration(monitor_all_tasks=True),
            RedisIntegration(),
            SqlalchemyIntegration(),
            HttpxIntegration(),
        ],
    )
    logger.info(f"Sentry initialized for environment: {SENTRY_ENVIRONMENT}")


def init_celery_sentry():
    """
    Initialize Sentry specifically for Celery workers.

    This must be called before Celery workers start processing tasks.
    Uses slightly different configuration optimized for background job
    processing and pipeline error tracking.
    """
    if not _is_enabled():
        logger.debug("Sentry DSN not configured, skipping Celery initialization")
        return

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=False,
        before_send=_filter_events,
        integrations=[
            CeleryIntegration(monitor_all_tasks=True),
            RedisIntegration(),
            SqlalchemyIntegration(),
        ],
    )
    logger.info(f"Sentry Celery integration initialized for environment: {SENTRY_ENVIRONMENT}")


def _filter_events(event: Any, hint: Optional[Any] = None) -> Optional[Any]:
    """
    Filter out noise from Sentry events.

    Filters:
    - Health check endpoints (regular pinging)
    - Liveness probe calls
    - Readiness probe calls
    - Development environment noise
    """
    if event.get("type") == "transaction":
        transaction_name = event.get("transaction", "")
        if any(skip in transaction_name for skip in ["/health", "/health/liveness", "/health/readiness"]):
            return None

    if event.get("type") == "error":
        if hint and "exc_info" in hint:
            exc_type = hint["exc_info"][0]
            if exc_type.__name__ in ("HealthCheckSuccess", "RedisPingSuccess"):
                return None

    return event


def capture_conversion_error(
    job_id: str,
    error: Exception,
    stage: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    Capture a conversion pipeline error with structured context.

    Args:
        job_id: The conversion job ID
        error: The exception that occurred
        stage: Current pipeline stage (e.g., "parsing", "translation", "packaging")
        metadata: Additional context about the conversion
    """
    if not _is_enabled():
        return

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("pipeline", "conversion")
        scope.set_tag("job_id", job_id)
        if stage:
            scope.set_tag("conversion_stage", stage)
        if metadata:
            for key, value in metadata.items():
                scope.set_extra(key, value)

    sentry_sdk.capture_exception(error)


def capture_conversion_success(job_id: str, duration_seconds: float, metadata: Optional[dict] = None):
    """
    Track successful conversion for pipeline success rate monitoring.

    Args:
        job_id: The conversion job ID
        duration_seconds: How long the conversion took
        metadata: Additional context about the conversion
    """
    if not _is_enabled():
        return

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("pipeline", "conversion")
        scope.set_tag("job_id", job_id)
        scope.set_extra("duration_seconds", duration_seconds)
        if metadata:
            for key, value in metadata.items():
                scope.set_extra(key, value)

    sentry_sdk.capture_message("conversion_success", level="info")


def capture_llm_error(
    model: str,
    error: Exception,
    duration_ms: Optional[float] = None,
    metadata: Optional[dict] = None,
):
    """
    Track LLM inference errors.

    Args:
        model: Model name (e.g., "Qwen3-Coder-7B")
        error: The exception that occurred
        duration_ms: How long the failed request took
        metadata: Additional context
    """
    if not _is_enabled():
        return

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("pipeline", "llm_inference")
        scope.set_tag("model", model)
        if duration_ms is not None:
            scope.set_extra("duration_ms", duration_ms)
        if metadata:
            for key, value in metadata.items():
                scope.set_extra(key, value)

    sentry_sdk.capture_exception(error)


def track_conversion_failure_rate(total: int, failed: int):
    """
    Update Sentry context with conversion failure rate for alerting.

    This data is used by Sentry alerts to trigger when error rate
    exceeds threshold (>5% failure rate triggers Slack notification).

    Args:
        total: Total conversions attempted
        failed: Total conversions failed
    """
    if not _is_enabled():
        return

    failure_rate = (failed / total * 100) if total > 0 else 0

    with sentry_sdk.configure_scope() as scope:
        scope.set_context("conversion_metrics", {
            "total_conversions": total,
            "failed_conversions": failed,
            "failure_rate_percent": round(failure_rate, 2),
        })


def get_sentry_enabled() -> bool:
    """Check if Sentry is enabled and configured."""
    return _is_enabled()


def flush():
    """Flush any pending Sentry events."""
    sentry_sdk.flush()