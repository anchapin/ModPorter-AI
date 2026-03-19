"""
Analytics service for tracking user behavior and usage.
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AnalyticsEvent


class AnalyticsService:
    """Service for tracking and querying analytics events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def hash_ip(ip: str) -> str:
        """Hash IP address for privacy compliance."""
        return hashlib.sha256(ip.encode()).hexdigest()[:64]

    @staticmethod
    def get_device_type(user_agent: Optional[str]) -> Optional[str]:
        """Detect device type from user agent string."""
        if not user_agent:
            return None
        ua = user_agent.lower()
        if "mobile" in ua or "android" in ua:
            return "mobile"
        elif "tablet" in ua or "ipad" in ua:
            return "tablet"
        return "desktop"

    async def track_event(
        self,
        event_type: str,
        event_category: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        conversion_id: Optional[uuid.UUID] = None,
        event_properties: Optional[dict] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        referrer: Optional[str] = None,
        country: Optional[str] = None,
    ) -> AnalyticsEvent:
        """
        Track an analytics event.

        Args:
            event_type: Type of event (e.g., "page_view", "conversion_start")
            event_category: Category of event (e.g., "navigation", "conversion")
            user_id: Optional user identifier
            session_id: Optional session identifier
            conversion_id: Optional conversion job ID
            event_properties: Additional event properties
            user_agent: User agent string
            ip_address: Client IP address (will be hashed)
            referrer: Referrer URL
            country: Country code

        Returns:
            Created AnalyticsEvent instance
        """
        # Hash IP for privacy
        ip_hash = None
        if ip_address:
            ip_hash = self.hash_ip(ip_address)

        # Detect device type
        device_type = self.get_device_type(user_agent)

        # Create analytics event
        event = AnalyticsEvent(
            event_type=event_type,
            event_category=event_category,
            user_id=user_id,
            session_id=session_id,
            conversion_id=conversion_id,
            event_properties=event_properties,
            user_agent=user_agent,
            ip_hash=ip_hash,
            referrer=referrer,
            country=country,
            device_type=device_type,
        )

        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        return event

    async def get_events(
        self,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        conversion_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnalyticsEvent]:
        """Query analytics events with filters."""
        conditions = []

        if event_type:
            conditions.append(AnalyticsEvent.event_type == event_type)
        if event_category:
            conditions.append(AnalyticsEvent.event_category == event_category)
        if user_id:
            conditions.append(AnalyticsEvent.user_id == user_id)
        if session_id:
            conditions.append(AnalyticsEvent.session_id == session_id)
        if conversion_id:
            conditions.append(AnalyticsEvent.conversion_id == conversion_id)
        if start_date:
            conditions.append(AnalyticsEvent.created_at >= start_date)
        if end_date:
            conditions.append(AnalyticsEvent.created_at <= end_date)

        query = select(AnalyticsEvent)
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(AnalyticsEvent.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_event_counts(
        self,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "event_type",
    ) -> list[dict]:
        """
        Get counts of events grouped by specified field.

        Args:
            event_type: Filter by event type
            event_category: Filter by event category
            start_date: Start date for filtering
            end_date: End date for filtering
            group_by: Field to group by ("event_type", "event_category", "device_type")

        Returns:
            List of dicts with count and group value
        """
        conditions = []

        if event_type:
            conditions.append(AnalyticsEvent.event_type == event_type)
        if event_category:
            conditions.append(AnalyticsEvent.event_category == event_category)
        if start_date:
            conditions.append(AnalyticsEvent.created_at >= start_date)
        if end_date:
            conditions.append(AnalyticsEvent.created_at <= end_date)

        # Determine column to group by
        if group_by == "event_category":
            group_column = AnalyticsEvent.event_category
        elif group_by == "device_type":
            group_column = AnalyticsEvent.device_type
        else:
            group_column = AnalyticsEvent.event_type

        query = (
            select(group_column, func.count(AnalyticsEvent.id).label("count"))
            .group_by(group_column)
            .order_by(func.count(AnalyticsEvent.id).desc())
        )

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return [{"group": row[0], "count": row[1]} for row in result.all()]

    async def get_unique_users(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Get count of unique users in date range."""
        conditions = []

        if start_date:
            conditions.append(AnalyticsEvent.created_at >= start_date)
        if end_date:
            conditions.append(AnalyticsEvent.created_at <= end_date)

        # Count distinct user_ids that are not null
        query = select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
            AnalyticsEvent.user_id.isnot(None)
        )

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_events_timeline(
        self,
        days: int = 7,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
    ) -> list[dict]:
        """
        Get event counts per day for the specified number of days.

        Args:
            days: Number of days to look back
            event_type: Optional event type filter
            event_category: Optional event category filter

        Returns:
            List of dicts with date and count
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        conditions = [AnalyticsEvent.created_at >= start_date]

        if event_type:
            conditions.append(AnalyticsEvent.event_type == event_type)
        if event_category:
            conditions.append(AnalyticsEvent.event_category == event_category)

        # Group by date (date only, not datetime)
        query = (
            select(
                func.date(AnalyticsEvent.created_at).label("date"),
                func.count(AnalyticsEvent.id).label("count"),
            )
            .where(and_(*conditions))
            .group_by(func.date(AnalyticsEvent.created_at))
            .order_by(func.date(AnalyticsEvent.created_at).desc())
        )

        result = await self.db.execute(query)
        return [{"date": str(row[0]), "count": row[1]} for row in result.all()]

    async def get_event_count(
        self,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Get count of events matching filters."""
        conditions = []

        if event_type:
            conditions.append(AnalyticsEvent.event_type == event_type)
        if event_category:
            conditions.append(AnalyticsEvent.event_category == event_category)
        if start_date:
            conditions.append(AnalyticsEvent.created_at >= start_date)
        if end_date:
            conditions.append(AnalyticsEvent.created_at <= end_date)

        query = select(func.count(AnalyticsEvent.id))

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_total_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Get total count of all events in date range."""
        conditions = []

        if start_date:
            conditions.append(AnalyticsEvent.created_at >= start_date)
        if end_date:
            conditions.append(AnalyticsEvent.created_at <= end_date)

        query = select(func.count(AnalyticsEvent.id))

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0


# Predefined event types for consistent tracking
class AnalyticsEvents:
    """Constants for common analytics events."""

    # Page views
    PAGE_VIEW = "page_view"
    LANDING_PAGE = "landing_page"
    CONVERSION_PAGE = "conversion_page"
    DASHBOARD_PAGE = "dashboard_page"
    HISTORY_PAGE = "history_page"

    # Conversion events
    CONVERSION_START = "conversion_start"
    CONVERSION_COMPLETE = "conversion_complete"
    CONVERSION_FAIL = "conversion_fail"
    CONVERSION_CANCEL = "conversion_cancel"
    CONVERSION_DOWNLOAD = "conversion_download"

    # Upload events
    FILE_UPLOAD_START = "file_upload_start"
    FILE_UPLOAD_COMPLETE = "file_upload_complete"
    FILE_UPLOAD_FAIL = "file_upload_fail"

    # User actions
    BUTTON_CLICK = "button_click"
    LINK_CLICK = "link_click"
    FORM_SUBMIT = "form_submit"
    FEEDBACK_SUBMIT = "feedback_submit"

    # Export events
    EXPORT_START = "export_start"
    EXPORT_COMPLETE = "export_complete"

    # Navigation events
    NAVIGATE = "navigate"

    # Categories
    CATEGORY_NAVIGATION = "navigation"
    CATEGORY_CONVERSION = "conversion"
    CATEGORY_UPLOAD = "upload"
    CATEGORY_FEEDBACK = "feedback"
    CATEGORY_EXPORT = "export"
    CATEGORY_USER_ACTION = "user_action"
