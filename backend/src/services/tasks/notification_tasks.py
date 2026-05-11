"""
Notification-related Celery tasks.

Includes:
- Conversion completion emails
- Failure notification emails
- Rate limit warnings
- Admin alerts

Issue: #1098 - Consolidate task queues
"""

from typing import Dict, Any, Optional
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from synchronous context."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result(timeout=300)


@shared_task(name="services.tasks.notification_tasks.send_conversion_complete_email")
def send_conversion_complete_email(
    user_email: str,
    job_id: str,
    file_name: str,
    download_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send conversion completion email to user.

    Issue: #1164 - Async conversion job status with progress indicator and completion email
    """
    from services.email_service import email_service

    async def _send():
        await email_service.send_email(
            to=user_email,
            subject=f"Conversion Complete: {file_name}",
            template="conversion_complete",
            context={
                "job_id": job_id,
                "file_name": file_name,
                "download_url": download_url,
            },
        )

    try:
        _run_async(_send())
        logger.info(f"Sent conversion complete email to {user_email} for job {job_id}")
        return {"success": True, "job_id": job_id, "recipient": user_email}
    except Exception as e:
        logger.error(f"Failed to send conversion complete email: {e}")
        return {"success": False, "job_id": job_id, "error": str(e)}


@shared_task(name="services.tasks.notification_tasks.send_conversion_failed_email")
def send_conversion_failed_email(
    user_email: str,
    job_id: str,
    file_name: str,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send conversion failure notification email to user.

    Issue: #1164 - Async conversion job status with progress indicator and completion email
    """
    from services.email_service import email_service

    async def _send():
        await email_service.send_email(
            to=user_email,
            subject=f"Conversion Failed: {file_name}",
            template="conversion_failed",
            context={
                "job_id": job_id,
                "file_name": file_name,
                "error_message": error_message,
            },
        )

    try:
        _run_async(_send())
        logger.info(f"Sent conversion failed email to {user_email} for job {job_id}")
        return {"success": True, "job_id": job_id, "recipient": user_email}
    except Exception as e:
        logger.error(f"Failed to send conversion failed email: {e}")
        return {"success": False, "job_id": job_id, "error": str(e)}


@shared_task(name="services.tasks.notification_tasks.send_rate_limit_warning")
def send_rate_limit_warning(
    user_email: str,
    current_usage: int,
    limit: int,
    reset_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send rate limit warning email to user.

    Issue: #1151 - Per-user rate limiting for conversion jobs
    """
    from services.email_service import email_service

    async def _send():
        await email_service.send_email(
            to=user_email,
            subject="Conversion Rate Limit Approaching",
            template="rate_limit_warning",
            context={
                "current_usage": current_usage,
                "limit": limit,
                "reset_at": reset_at,
            },
        )

    try:
        _run_async(_send())
        logger.info(f"Sent rate limit warning to {user_email}")
        return {"success": True, "recipient": user_email}
    except Exception as e:
        logger.error(f"Failed to send rate limit warning: {e}")
        return {"success": False, "error": str(e)}


@shared_task(name="services.tasks.notification_tasks.send_admin_alert")
def send_admin_alert(
    alert_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send admin alert for system issues.

    Used for:
    - High dead letter queue
    - Queue backup
    - Service degradation
    """
    from services.alerting import alert_manager

    async def _send():
        await alert_manager.send_alert(
            alert_type=alert_type,
            message=message,
            details=details or {},
        )

    try:
        _run_async(_send())
        logger.info(f"Sent admin alert: {alert_type}")
        return {"success": True, "alert_type": alert_type}
    except Exception as e:
        logger.error(f"Failed to send admin alert: {e}")
        return {"success": False, "error": str(e)}
