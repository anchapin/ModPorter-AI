"""
Alerting API endpoints for monitoring and notifications.
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict

from db.base import get_db
from services.alerting_service import AlertingService, AlertLevel

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()


class AlertRequest(BaseModel):
    """Request model for manually triggering an alert."""
    alert_level: str
    title: str
    message: str
    metric_data: Optional[dict] = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "alert_level": "warning",
                    "title": "High Error Rate",
                    "message": "Error rate has exceeded 5% threshold",
                    "metric_data": {"error_rate": 6.5, "threshold": 5.0},
                }
            ]
        }
    )


class AlertResponse(BaseModel):
    """Response model for alert operations."""
    status: str
    message: str
    alert_id: Optional[str] = None


class AlertStatusResponse(BaseModel):
    """Response model for alert status check."""
    timestamp: str
    checks: list
    alerts_sent: int


@router.post("/test", response_model=AlertResponse)
async def test_alert(
    alert: AlertRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a test alert to verify alerting configuration.
    
    This endpoint allows testing Discord webhooks and email notifications.
    """
    if alert.alert_level not in [AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.ERROR, AlertLevel.CRITICAL]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid alert_level. Must be one of: {', '.join([AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.ERROR, AlertLevel.CRITICAL])}"
        )
    
    alerting = AlertingService(db)
    
    try:
        success = await alerting.send_alert(
            alert_level=alert.alert_level,
            title=alert.title,
            message=alert.message,
            metric_data=alert.metric_data,
        )
        
        if success:
            return AlertResponse(
                status="success",
                message="Test alert sent successfully",
            )
        else:
            return AlertResponse(
                status="rate_limited",
                message="Alert was rate-limited (sent within last hour)",
            )
            
    except Exception as e:
        logger.error(f"Failed to send test alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send alert: {str(e)}")


@router.get("/status", response_model=AlertStatusResponse)
async def get_alert_status(
    db: AsyncSession = Depends(get_db),
):
    """
    Get current alert status and run monitoring checks.
    
    This endpoint triggers a monitoring check and returns the results
    without sending alerts (for status monitoring).
    """
    alerting = AlertingService(db)
    
    try:
        # Run checks but don't send alerts (dry run)
        error_rate = await alerting.check_error_rate()
        failure_rate = await alerting.check_conversion_failure_rate()
        
        return AlertStatusResponse(
            timestamp=datetime.utcnow().isoformat(),
            checks=[
                {
                    "name": "error_rate",
                    "alert_triggered": error_rate["alert_triggered"],
                    "error_rate": error_rate["error_rate"],
                    "threshold": error_rate["threshold"],
                },
                {
                    "name": "conversion_failure_rate",
                    "alert_triggered": failure_rate["alert_triggered"],
                    "failure_rate": failure_rate["failure_rate"],
                    "threshold": failure_rate["threshold"],
                },
            ],
            alerts_sent=0,
        )
        
    except Exception as e:
        logger.error(f"Failed to get alert status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/thresholds")
async def get_alert_thresholds():
    """
    Get current alert threshold configuration.
    
    Returns the configured thresholds for various alerting rules.
    """
    return {
        "error_rate_threshold": AlertingService.ERROR_RATE_THRESHOLD,
        "latency_threshold_ms": AlertingService.LATENCY_THRESHOLD_MS,
        "conversion_failure_threshold": AlertingService.CONVERSION_FAILURE_THRESHOLD,
        "description": {
            "error_rate_threshold": "Triggers alert when error rate exceeds this percentage",
            "latency_threshold_ms": "Triggers alert when latency exceeds this value in milliseconds",
            "conversion_failure_threshold": "Triggers alert when conversion failure rate exceeds this percentage",
        },
    }
