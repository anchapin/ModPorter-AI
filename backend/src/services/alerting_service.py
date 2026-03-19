"""
Alerting service for monitoring system health and sending notifications.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db.models import AnalyticsEvent

logger = logging.getLogger(__name__)


class AlertLevel:
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertingService:
    """Service for monitoring metrics and triggering alerts."""

    # Alert thresholds
    ERROR_RATE_THRESHOLD = 5.0  # 5% error rate
    LATENCY_THRESHOLD_MS = 30000  # 30 seconds
    CONVERSION_FAILURE_THRESHOLD = 10.0  # 10% conversion failure rate

    def __init__(self, db: AsyncSession):
        self.db = db
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.alert_email = os.getenv("ALERT_EMAIL")
        self._last_alert_time = {}

    async def check_error_rate(self) -> dict:
        """
        Check if error rate exceeds threshold.
        
        Returns:
            dict with alert status, rate, and threshold
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=1)
        
        # Get total events
        total_query = select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.created_at >= start_date,
            AnalyticsEvent.created_at <= end_date,
        )
        total_result = await self.db.execute(total_query)
        total_events = total_result.scalar() or 0
        
        # Get error events
        error_query = select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.event_type == "conversion_fail",
            AnalyticsEvent.created_at >= start_date,
            AnalyticsEvent.created_at <= end_date,
        )
        error_result = await self.db.execute(error_query)
        error_events = error_result.scalar() or 0
        
        error_rate = (error_events / total_events * 100) if total_events > 0 else 0.0
        
        is_above_threshold = error_rate > self.ERROR_RATE_THRESHOLD
        
        return {
            "alert_triggered": is_above_threshold,
            "error_rate": round(error_rate, 2),
            "threshold": self.ERROR_RATE_THRESHOLD,
            "total_events": total_events,
            "error_events": error_events,
            "window_hours": 1,
        }

    async def check_conversion_failure_rate(self) -> dict:
        """
        Check if conversion failure rate exceeds threshold.
        
        Returns:
            dict with alert status, rate, and threshold
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=1)
        
        # Get total conversions started
        started_query = select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.event_type == "conversion_start",
            AnalyticsEvent.created_at >= start_date,
            AnalyticsEvent.created_at <= end_date,
        )
        started_result = await self.db.execute(started_query)
        total_started = started_result.scalar() or 0
        
        # Get conversions that failed
        failed_query = select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.event_type == "conversion_fail",
            AnalyticsEvent.created_at >= start_date,
            AnalyticsEvent.created_at <= end_date,
        )
        failed_result = await self.db.execute(failed_query)
        total_failed = failed_result.scalar() or 0
        
        failure_rate = (total_failed / total_started * 100) if total_started > 0 else 0.0
        
        is_above_threshold = failure_rate > self.CONVERSION_FAILURE_THRESHOLD
        
        return {
            "alert_triggered": is_above_threshold,
            "failure_rate": round(failure_rate, 2),
            "threshold": self.CONVERSION_FAILURE_THRESHOLD,
            "total_started": total_started,
            "total_failed": total_failed,
            "window_hours": 1,
        }

    async def send_alert(
        self,
        alert_level: str,
        title: str,
        message: str,
        metric_data: Optional[dict] = None,
    ) -> bool:
        """
        Send alert notifications via configured channels.
        
        Args:
            alert_level: Severity level (info, warning, error, critical)
            title: Alert title
            message: Alert message
            metric_data: Optional metrics data to include
            
        Returns:
            True if alert was sent successfully
        """
        # Rate limiting: don't send same alert more than once per hour
        alert_key = f"{title}"
        last_sent = self._last_alert_time.get(alert_key)
        if last_sent and (datetime.utcnow() - last_sent).total_seconds() < 3600:
            logger.info(f"Alert rate-limited: {title}")
            return False
        
        # Prepare Discord embed
        if self.discord_webhook_url:
            await self._send_discord_alert(alert_level, title, message, metric_data)
        
        # Prepare email alert (if configured)
        if self.alert_email:
            await self._send_email_alert(alert_level, title, message, metric_data)
        
        self._last_alert_time[alert_key] = datetime.utcnow()
        
        # Log the alert
        logger.warning(
            f"ALERT [{alert_level.upper()}]: {title} - {message}",
            extra={"metric_data": metric_data},
        )
        
        return True

    async def _send_discord_alert(
        self,
        alert_level: str,
        title: str,
        message: str,
        metric_data: Optional[dict],
    ) -> bool:
        """Send alert to Discord webhook."""
        if not self.discord_webhook_url:
            return False
        
        # Determine color based on level
        colors = {
            AlertLevel.INFO: 3447003,      # Blue
            AlertLevel.WARNING: 16776960,  # Yellow
            AlertLevel.ERROR: 15158332,    # Red
            AlertLevel.CRITICAL: 10038562,  # Purple
        }
        color = colors.get(alert_level, 3447003)
        
        # Build embed
        embed = {
            "embeds": [
                {
                    "title": f"🚨 {title}",
                    "description": message,
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat(),
                    "fields": [],
                }
            ]
        }
        
        # Add metric data fields
        if metric_data:
            for key, value in metric_data.items():
                embed["embeds"][0]["fields"].append({
                    "name": key,
                    "value": str(value),
                    "inline": True,
                })
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.discord_webhook_url,
                    json=embed,
                    timeout=10.0,
                )
                if response.status_code == 204:
                    logger.info(f"Discord alert sent: {title}")
                    return True
                else:
                    logger.error(f"Failed to send Discord alert: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
            return False

    async def _send_email_alert(
        self,
        alert_level: str,
        title: str,
        message: str,
        metric_data: Optional[dict],
    ) -> bool:
        """Send alert via email."""
        # Placeholder for email alerting
        # In production, integrate with email service
        logger.info(f"Email alert would be sent to {self.alert_email}: {title}")
        return True

    async def run_monitoring_check(self) -> dict:
        """
        Run all monitoring checks and send alerts if thresholds exceeded.
        
        Returns:
            dict with check results
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": [],
        }
        
        # Check error rate
        error_rate_check = await self.check_error_rate()
        results["checks"].append({
            "name": "error_rate",
            "result": error_rate_check,
        })
        
        if error_rate_check["alert_triggered"]:
            await self.send_alert(
                AlertLevel.WARNING,
                "High Error Rate Detected",
                f"Error rate is {error_rate_check['error_rate']}% (threshold: {error_rate_check['threshold']}%)",
                error_rate_check,
            )
        
        # Check conversion failure rate
        failure_rate_check = await self.check_conversion_failure_rate()
        results["checks"].append({
            "name": "conversion_failure_rate",
            "result": failure_rate_check,
        })
        
        if failure_rate_check["alert_triggered"]:
            await self.send_alert(
                AlertLevel.ERROR,
                "High Conversion Failure Rate",
                f"Conversion failure rate is {failure_rate_check['failure_rate']}% (threshold: {failure_rate_check['threshold']}%)",
                failure_rate_check,
            )
        
        results["alerts_sent"] = len([c for c in results["checks"] if c["result"].get("alert_triggered")])
        
        return results


async def start_monitoring_loop(interval_seconds: int = 300):
    """
    Start background monitoring loop.
    
    Args:
        interval_seconds: How often to run checks (default: 5 minutes)
    """
    from db.base import AsyncSessionLocal
    
    logger.info(f"Starting alerting monitoring loop (interval: {interval_seconds}s)")
    
    while True:
        try:
            async with AsyncSessionLocal() as db:
                alerting = AlertingService(db)
                results = await alerting.run_monitoring_check()
                logger.debug(f"Monitoring check completed: {results}")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
        
        await asyncio.sleep(interval_seconds)
