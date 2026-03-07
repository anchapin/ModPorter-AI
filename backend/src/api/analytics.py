"""
Analytics API endpoints for tracking user behavior and usage.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict

from db.base import get_db
from services.analytics_service import AnalyticsService, AnalyticsEvents

# Configure logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyticsEventRequest(BaseModel):
    """Request model for tracking an analytics event."""

    event_type: str
    event_category: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversion_id: Optional[str] = None
    event_properties: Optional[dict] = None

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "event_type": "page_view",
                    "event_category": "navigation",
                    "session_id": "sess-123-abc",
                    "event_properties": {"page": "/", "referrer": "google.com"},
                },
                {
                    "event_type": "conversion_start",
                    "event_category": "conversion",
                    "user_id": "user-456",
                    "event_properties": {
                        "file_type": "jar",
                        "file_size": 1048576,
                        "target_version": "1.20.0",
                    },
                },
            ]
        },
    )


class AnalyticsEventResponse(BaseModel):
    """Response model for a tracked analytics event."""

    id: str
    event_type: str
    event_category: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversion_id: Optional[str] = None
    event_properties: Optional[dict] = None
    created_at: str


class AnalyticsQueryRequest(BaseModel):
    """Request model for querying analytics events."""

    event_type: Optional[str] = None
    event_category: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversion_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


class AnalyticsStatsResponse(BaseModel):
    """Response model for analytics statistics."""

    total_events: int
    unique_users: Optional[int] = None
    event_counts: List[dict]
    timeline: List[dict]


@router.post("/events", response_model=AnalyticsEventResponse)
async def track_event(
    event: AnalyticsEventRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Track an analytics event.

    This endpoint records user behavior events such as page views,
    button clicks, conversion starts, and other interactions.
    """
    logger.info(f"Tracking analytics event: {event.event_type} ({event.event_category})")

    # Get client information from request
    user_agent = request.headers.get("user-agent")
    referrer = request.headers.get("referer") or request.headers.get("referrer")
    ip_address = request.client.host if request.client else None

    # Parse conversion_id if provided
    conversion_uuid = None
    if event.conversion_id:
        try:
            conversion_uuid = uuid.UUID(event.conversion_id)
        except ValueError:
            logger.warning(f"Invalid conversion_id format: {event.conversion_id}")

    # Create analytics service and track event
    analytics = AnalyticsService(db)

    try:
        db_event = await analytics.track_event(
            event_type=event.event_type,
            event_category=event.event_category,
            user_id=event.user_id,
            session_id=event.session_id,
            conversion_id=conversion_uuid,
            event_properties=event.event_properties,
            user_agent=user_agent,
            ip_address=ip_address,
            referrer=referrer,
        )

        return AnalyticsEventResponse(
            id=str(db_event.id),
            event_type=db_event.event_type,
            event_category=db_event.event_category,
            user_id=db_event.user_id,
            session_id=db_event.session_id,
            conversion_id=(str(db_event.conversion_id) if db_event.conversion_id else None),
            event_properties=db_event.event_properties,
            created_at=db_event.created_at.isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to track analytics event: {e}")
        # Don't fail the request if analytics fails
        raise HTTPException(status_code=500, detail=f"Failed to track event: {str(e)}")


@router.get("/events", response_model=List[AnalyticsEventResponse])
async def get_events(
    event_type: Optional[str] = None,
    event_category: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    conversion_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Query analytics events with filters.

    Use this to retrieve tracked events for analysis.
    """
    # Parse dates
    start = None
    end = None
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")

    # Parse conversion_id
    conv_uuid = None
    if conversion_id:
        try:
            conv_uuid = uuid.UUID(conversion_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid conversion_id format")

    analytics = AnalyticsService(db)

    try:
        events = await analytics.get_events(
            event_type=event_type,
            event_category=event_category,
            user_id=user_id,
            session_id=session_id,
            conversion_id=conv_uuid,
            start_date=start,
            end_date=end,
            limit=limit,
            offset=offset,
        )

        return [
            AnalyticsEventResponse(
                id=str(e.id),
                event_type=e.event_type,
                event_category=e.event_category,
                user_id=e.user_id,
                session_id=e.session_id,
                conversion_id=str(e.conversion_id) if e.conversion_id else None,
                event_properties=e.event_properties,
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ]

    except Exception as e:
        logger.error(f"Failed to query analytics events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query events: {str(e)}")


@router.get("/stats", response_model=AnalyticsStatsResponse)
async def get_analytics_stats(
    event_type: Optional[str] = None,
    event_category: Optional[str] = None,
    days: int = 7,
    group_by: str = "event_type",
    db: AsyncSession = Depends(get_db),
):
    """
    Get analytics statistics and metrics.

    Returns event counts grouped by the specified field and a timeline
    of events per day.
    """
    if group_by not in ["event_type", "event_category", "device_type"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid group_by value. Must be one of: event_type, event_category, device_type",
        )

    analytics = AnalyticsService(db)

    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Get event counts
        event_counts = await analytics.get_event_counts(
            event_type=event_type,
            event_category=event_category,
            start_date=start_date,
            end_date=end_date,
            group_by=group_by,
        )

        # Get timeline
        timeline = await analytics.get_events_timeline(
            days=days,
            event_type=event_type,
            event_category=event_category,
        )

        # Get unique users count
        unique_users = await analytics.get_unique_users(
            start_date=start_date,
            end_date=end_date,
        )

        return AnalyticsStatsResponse(
            total_events=sum(e["count"] for e in event_counts),
            unique_users=unique_users,
            event_counts=event_counts,
            timeline=timeline,
        )

    except Exception as e:
        logger.error(f"Failed to get analytics stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# Convenience endpoint for tracking common events
@router.post("/events/pageview")
async def track_page_view(
    page: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Track a page view event.

    Convenience endpoint for tracking page views.
    """
    user_agent = request.headers.get("user-agent") if request else None
    referrer = None
    if request:
        referrer = request.headers.get("referer") or request.headers.get("referrer")

    analytics = AnalyticsService(db)

    try:
        event = await analytics.track_event(
            event_type=AnalyticsEvents.PAGE_VIEW,
            event_category=AnalyticsEvents.CATEGORY_NAVIGATION,
            user_id=user_id,
            session_id=session_id,
            event_properties={"page": page, "referrer": referrer},
            user_agent=user_agent,
        )

        return {"status": "success", "event_id": str(event.id)}

    except Exception as e:
        logger.error(f"Failed to track page view: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to track page view: {str(e)}")


@router.post("/events/conversion")
async def track_conversion_event(
    conversion_id: str,
    event_type: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    event_properties: Optional[dict] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Track a conversion-related event.

    Convenience endpoint for tracking conversion events like
    start, complete, fail, download, etc.
    """
    # Validate event_type
    valid_types = [
        AnalyticsEvents.CONVERSION_START,
        AnalyticsEvents.CONVERSION_COMPLETE,
        AnalyticsEvents.CONVERSION_FAIL,
        AnalyticsEvents.CONVERSION_CANCEL,
        AnalyticsEvents.CONVERSION_DOWNLOAD,
    ]

    if event_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {', '.join(valid_types)}",
        )

    # Parse conversion_id
    try:
        conversion_uuid = uuid.UUID(conversion_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversion_id format")

    user_agent = request.headers.get("user-agent") if request else None

    analytics = AnalyticsService(db)

    try:
        event = await analytics.track_event(
            event_type=event_type,
            event_category=AnalyticsEvents.CATEGORY_CONVERSION,
            user_id=user_id,
            session_id=session_id,
            conversion_id=conversion_uuid,
            event_properties=event_properties or {},
            user_agent=user_agent,
        )

        return {"status": "success", "event_id": str(event.id)}

    except Exception as e:
        logger.error(f"Failed to track conversion event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to track event: {str(e)}")


@router.get("/events/types")
async def get_event_types():
    """
    Get available event types and categories.

    Returns a list of predefined event types and categories
    that can be used with the analytics tracking endpoints.
    """
    return {
        "event_types": [
            AnalyticsEvents.PAGE_VIEW,
            AnalyticsEvents.LANDING_PAGE,
            AnalyticsEvents.CONVERSION_PAGE,
            AnalyticsEvents.DASHBOARD_PAGE,
            AnalyticsEvents.HISTORY_PAGE,
            AnalyticsEvents.CONVERSION_START,
            AnalyticsEvents.CONVERSION_COMPLETE,
            AnalyticsEvents.CONVERSION_FAIL,
            AnalyticsEvents.CONVERSION_CANCEL,
            AnalyticsEvents.CONVERSION_DOWNLOAD,
            AnalyticsEvents.FILE_UPLOAD_START,
            AnalyticsEvents.FILE_UPLOAD_COMPLETE,
            AnalyticsEvents.FILE_UPLOAD_FAIL,
            AnalyticsEvents.BUTTON_CLICK,
            AnalyticsEvents.LINK_CLICK,
            AnalyticsEvents.FORM_SUBMIT,
            AnalyticsEvents.FEEDBACK_SUBMIT,
            AnalyticsEvents.EXPORT_START,
            AnalyticsEvents.EXPORT_COMPLETE,
            AnalyticsEvents.NAVIGATE,
        ],
        "categories": [
            AnalyticsEvents.CATEGORY_NAVIGATION,
            AnalyticsEvents.CATEGORY_CONVERSION,
            AnalyticsEvents.CATEGORY_UPLOAD,
            AnalyticsEvents.CATEGORY_FEEDBACK,
            AnalyticsEvents.CATEGORY_EXPORT,
            AnalyticsEvents.CATEGORY_USER_ACTION,
        ],
    }
