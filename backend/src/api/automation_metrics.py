"""
Automation Metrics API Router

API endpoints for automation metrics tracking and dashboard data.
Provides endpoints for recording conversion events and retrieving automation metrics.

Issue: GAP-2.5-06 - Automation Metrics Dashboard
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
import logging

from services.automation_metrics import (
    get_automation_metrics_service,
    TARGET_AUTOMATION_RATE,
    TARGET_ONE_CLICK_RATE,
    TARGET_AUTO_RECOVERY_RATE,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================


class ConversionEventRequest(BaseModel):
    """Request model for recording a conversion event."""

    conversion_id: str = Field(..., description="Unique identifier for the conversion")
    was_automated: bool = Field(
        False, description="Whether conversion completed without human intervention"
    )
    was_one_click: bool = Field(
        False, description="Whether conversion was started with single click"
    )
    upload_time: Optional[datetime] = Field(None, description="When the file was uploaded")
    download_time: Optional[datetime] = Field(
        None, description="When the converted file was downloaded"
    )
    conversion_time_seconds: Optional[float] = Field(
        None, description="Manual override for conversion time in seconds"
    )
    mode_classification_correct: Optional[bool] = Field(
        None, description="Whether auto mode classification was correct"
    )
    had_error: bool = Field(False, description="Whether an error occurred during conversion")
    auto_recovered: bool = Field(False, description="Whether any error was recovered automatically")
    user_satisfaction_score: Optional[float] = Field(
        None, ge=1.0, le=5.0, description="User satisfaction score (1-5 scale)"
    )

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "conversion_id": "conv-123-abc",
                    "was_automated": True,
                    "was_one_click": True,
                    "upload_time": "2026-03-31T12:00:00Z",
                    "download_time": "2026-03-31T12:05:00Z",
                    "mode_classification_correct": True,
                    "auto_recovered": False,
                },
                {
                    "conversion_id": "conv-456-def",
                    "was_automated": True,
                    "was_one_click": True,
                    "had_error": True,
                    "auto_recovered": True,
                    "user_satisfaction_score": 4.5,
                },
            ]
        },
    )


class ConversionEventResponse(BaseModel):
    """Response model for a recorded conversion event."""

    status: str
    conversion_id: str
    message: str


class MetricValue(BaseModel):
    """Single metric with value, target, and status."""

    value: float
    target: Optional[float] = None
    met: Optional[bool] = None
    unit: str


class MetricsSummary(BaseModel):
    """Summary counts for metrics."""

    total_conversions: int
    automated_conversions: int
    one_click_conversions: int
    total_errors: int
    auto_recovered: int


class MetricsStatus(BaseModel):
    """Overall status of metrics."""

    overall: str
    targets_met: int
    total_targets: int


class MetricsPeriod(BaseModel):
    """Time period for metrics."""

    start: Optional[str] = None
    end: Optional[str] = None
    hours: int


class MetricData(BaseModel):
    """Dashboard metric data."""

    automation_rate: MetricValue
    one_click_rate: MetricValue
    auto_recovery_rate: MetricValue
    avg_conversion_time_seconds: MetricValue
    mode_classification_accuracy: MetricValue
    user_satisfaction: MetricValue


class DashboardData(BaseModel):
    """Dashboard response model."""

    metrics: MetricData
    summary: MetricsSummary
    status: MetricsStatus
    period: MetricsPeriod
    calculated_at: str


class AutomationMetricsResponse(BaseModel):
    """Response model for automation metrics endpoint."""

    automation_rate: float
    one_click_rate: float
    auto_recovery_rate: float
    avg_conversion_time_seconds: float
    mode_classification_accuracy: float
    avg_user_satisfaction: float
    total_conversions: int
    target_automation_rate: float = TARGET_AUTOMATION_RATE
    target_one_click_rate: float = TARGET_ONE_CLICK_RATE
    target_auto_recovery_rate: float = TARGET_AUTO_RECOVERY_RATE
    automation_target_met: bool
    one_click_target_met: bool
    auto_recovery_target_met: bool
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    calculated_at: str


class HistoricalDataPoint(BaseModel):
    """Single point in historical data."""

    timestamp: str
    automation_rate: float
    one_click_rate: float
    auto_recovery_rate: float
    avg_conversion_time_seconds: float
    mode_classification_accuracy: float
    avg_user_satisfaction: float
    total_conversions: int


class HistoricalDataResponse(BaseModel):
    """Response model for historical data endpoint."""

    data: List[HistoricalDataPoint]
    period_days: int
    interval_hours: int
    calculated_at: str


class HistoryEvent(BaseModel):
    """Single event in history list."""

    conversion_id: str
    timestamp: str
    was_automated: bool
    was_one_click: bool
    conversion_time_seconds: Optional[float]
    mode_classification_correct: Optional[bool]
    had_error: bool
    auto_recovered: bool
    user_satisfaction_score: Optional[float]


class HistoryEventsResponse(BaseModel):
    """Response model for history events endpoint."""

    events: List[HistoryEvent]
    total: int
    limit: int
    offset: int


# ============================================
# API Endpoints
# ============================================


@router.get("/automation", response_model=AutomationMetricsResponse)
async def get_automation_metrics(
    period_hours: int = Query(
        24, ge=1, le=720, description="Time period in hours to calculate metrics for"
    ),
):
    """
    Get current automation metrics.

    Returns current automation rate, one-click rate, auto-recovery rate,
    average conversion time, mode classification accuracy, and user satisfaction.
    """
    try:
        service = get_automation_metrics_service()
        snapshot = service.get_current_metrics(period_hours=period_hours)

        return AutomationMetricsResponse(
            automation_rate=snapshot.automation_rate,
            one_click_rate=snapshot.one_click_rate,
            auto_recovery_rate=snapshot.auto_recovery_rate,
            avg_conversion_time_seconds=snapshot.avg_conversion_time_seconds,
            mode_classification_accuracy=snapshot.mode_classification_accuracy,
            avg_user_satisfaction=snapshot.avg_user_satisfaction,
            total_conversions=snapshot.total_conversions,
            target_automation_rate=snapshot.target_automation_rate,
            target_one_click_rate=snapshot.target_one_click_rate,
            target_auto_recovery_rate=snapshot.target_auto_recovery_rate,
            automation_target_met=snapshot.automation_target_met,
            one_click_target_met=snapshot.one_click_target_met,
            auto_recovery_target_met=snapshot.auto_recovery_target_met,
            period_start=snapshot.period_start.isoformat() if snapshot.period_start else None,
            period_end=snapshot.period_end.isoformat() if snapshot.period_end else None,
            calculated_at=snapshot.calculated_at.isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to get automation metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get automation metrics.")


@router.get("/automation/dashboard", response_model=DashboardData)
async def get_automation_dashboard(
    period_hours: int = Query(24, ge=1, le=720, description="Time period in hours"),
):
    """
    Get dashboard-ready automation metrics data.

    Returns formatted metrics with targets, status indicators,
    and summary data suitable for dashboard display.
    """
    try:
        service = get_automation_metrics_service()
        data = service.get_dashboard_data(period_hours=period_hours)

        return DashboardData(
            metrics=MetricData(
                automation_rate=MetricValue(
                    value=data["metrics"]["automation_rate"]["value"],
                    target=data["metrics"]["automation_rate"]["target"],
                    met=data["metrics"]["automation_rate"]["met"],
                    unit=data["metrics"]["automation_rate"]["unit"],
                ),
                one_click_rate=MetricValue(
                    value=data["metrics"]["one_click_rate"]["value"],
                    target=data["metrics"]["one_click_rate"]["target"],
                    met=data["metrics"]["one_click_rate"]["met"],
                    unit=data["metrics"]["one_click_rate"]["unit"],
                ),
                auto_recovery_rate=MetricValue(
                    value=data["metrics"]["auto_recovery_rate"]["value"],
                    target=data["metrics"]["auto_recovery_rate"]["target"],
                    met=data["metrics"]["auto_recovery_rate"]["met"],
                    unit=data["metrics"]["auto_recovery_rate"]["unit"],
                ),
                avg_conversion_time_seconds=MetricValue(
                    value=data["metrics"]["avg_conversion_time_seconds"]["value"],
                    unit=data["metrics"]["avg_conversion_time_seconds"]["unit"],
                ),
                mode_classification_accuracy=MetricValue(
                    value=data["metrics"]["mode_classification_accuracy"]["value"],
                    unit=data["metrics"]["mode_classification_accuracy"]["unit"],
                ),
                user_satisfaction=MetricValue(
                    value=data["metrics"]["user_satisfaction"]["value"],
                    unit=data["metrics"]["user_satisfaction"]["unit"],
                ),
            ),
            summary=MetricsSummary(
                total_conversions=data["summary"]["total_conversions"],
                automated_conversions=data["summary"]["automated_conversions"],
                one_click_conversions=data["summary"]["one_click_conversions"],
                total_errors=data["summary"]["total_errors"],
                auto_recovered=data["summary"]["auto_recovered"],
            ),
            status=MetricsStatus(
                overall=data["status"]["overall"],
                targets_met=data["status"]["targets_met"],
                total_targets=data["status"]["total_targets"],
            ),
            period=MetricsPeriod(
                start=data["period"]["start"],
                end=data["period"]["end"],
                hours=data["period"]["hours"],
            ),
            calculated_at=data["calculated_at"],
        )
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard data.")


@router.post("/automation/record", response_model=ConversionEventResponse, status_code=201)
async def record_conversion_event(
    event: ConversionEventRequest,
):
    """
    Record a conversion event with automation metrics.

    This endpoint should be called after each conversion completes to record
    the automation-related metrics for that conversion.
    """
    try:
        service = get_automation_metrics_service()

        # Convert datetime strings to datetime objects if provided
        upload_time = event.upload_time
        download_time = event.download_time

        service.record_conversion_event(
            conversion_id=event.conversion_id,
            was_automated=event.was_automated,
            was_one_click=event.was_one_click,
            upload_time=upload_time,
            download_time=download_time,
            conversion_time_seconds=event.conversion_time_seconds,
            mode_classification_correct=event.mode_classification_correct,
            had_error=event.had_error,
            auto_recovered=event.auto_recovered,
            user_satisfaction_score=event.user_satisfaction_score,
        )

        return ConversionEventResponse(
            status="success",
            conversion_id=event.conversion_id,
            message="Conversion event recorded successfully",
        )
    except Exception as e:
        logger.error(f"Failed to record conversion event: {e}")
        raise HTTPException(status_code=500, detail="Failed to record conversion event.")


@router.get("/automation/history", response_model=HistoricalDataResponse)
async def get_automation_history(
    days: int = Query(7, ge=1, le=30, description="Number of days of history"),
    interval_hours: int = Query(
        1, ge=1, le=24, description="Interval between data points in hours"
    ),
):
    """
    Get historical automation metrics data.

    Returns a time series of automation metrics over the specified period.
    """
    try:
        service = get_automation_metrics_service()
        data = service.get_historical_data(days=days, interval_hours=interval_hours)

        return HistoricalDataResponse(
            data=[
                HistoricalDataPoint(
                    timestamp=d["timestamp"],
                    automation_rate=d["automation_rate"],
                    one_click_rate=d["one_click_rate"],
                    auto_recovery_rate=d["auto_recovery_rate"],
                    avg_conversion_time_seconds=d["avg_conversion_time_seconds"],
                    mode_classification_accuracy=d["mode_classification_accuracy"],
                    avg_user_satisfaction=d["avg_user_satisfaction"],
                    total_conversions=d["total_conversions"],
                )
                for d in data
            ],
            period_days=days,
            interval_hours=interval_hours,
            calculated_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to get historical data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get historical data.")


@router.get("/automation/events", response_model=HistoryEventsResponse)
async def get_conversion_events(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    start_date: Optional[datetime] = Query(None, description="Filter events after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter events before this date"),
):
    """
    Get recorded conversion events.

    Returns paginated list of conversion events with their automation metrics.
    """
    try:
        service = get_automation_metrics_service()
        events, total = service.get_all_events(
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
        )

        return HistoryEventsResponse(
            events=[
                HistoryEvent(
                    conversion_id=e["conversion_id"],
                    timestamp=e["timestamp"],
                    was_automated=e["was_automated"],
                    was_one_click=e["was_one_click"],
                    conversion_time_seconds=e["conversion_time_seconds"],
                    mode_classification_correct=e["mode_classification_correct"],
                    had_error=e["had_error"],
                    auto_recovered=e["auto_recovered"],
                    user_satisfaction_score=e["user_satisfaction_score"],
                )
                for e in events
            ],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Failed to get conversion events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversion events.")


@router.post("/automation/reset")
async def reset_automation_metrics():
    """
    Reset all automation metrics and history.

    WARNING: This will delete all stored metrics data.
    Use with caution - typically only for testing.
    """
    try:
        service = get_automation_metrics_service()
        service.reset_metrics()

        return {
            "status": "success",
            "message": "Automation metrics reset successfully",
        }
    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset metrics.")
