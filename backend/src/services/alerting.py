"""
On-call alerting service for Portkit.

Provides incident management and alerting via Better Stack Incidents API.
Supports P0/P1/P2 alert routing with phone/SMS escalation.

Issue: #1212 - Pre-beta: Full observability stack
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""

    P0_CRITICAL = "P0"
    P1_HIGH = "P1"
    P2_MEDIUM = "P2"
    P3_LOW = "P3"
    INFO = "INFO"


class AlertStatus(Enum):
    """Alert status values."""

    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """Represents an alert incident."""

    name: str
    severity: AlertSeverity
    message: str
    status: AlertStatus = AlertStatus.TRIGGERED
    alert_id: Optional[str] = None
    incident_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


@dataclass
class AlertRule:
    """Alert rule definition."""

    name: str
    metric: str
    threshold: float
    operator: str = ">"
    severity: AlertSeverity = AlertSeverity.P2_MEDIUM
    duration_seconds: int = 300


class BetterStackIncidentsClient:
    """Client for Better Stack Incidents API."""

    INCIDENTS_API_URL = "https://api.betterstack.com/incidents"

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("BETTERSTACK_API_TOKEN")
        self._client = None

    def _get_client(self) -> Optional[httpx.AsyncClient]:
        if httpx is None:
            return None
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def create_incident(
        self,
        name: str,
        status: str = "triggered",
        severity: str = "high",
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new incident in Better Stack."""
        client = self._get_client()
        if client is None or not self.api_token:
            logger.warning("Better Stack API client not available")
            return None

        try:
            url = f"{self.INCIDENTS_API_URL}"
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "name": name,
                "status": status,
                "severity": severity,
                "message": message,
                "metadata": metadata or {},
            }
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in (200, 201, 202):
                return response.json()
            else:
                logger.warning(f"Failed to create incident: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error creating incident: {e}")
            return None

    async def resolve_incident(self, incident_id: str) -> bool:
        """Resolve an incident."""
        client = self._get_client()
        if client is None or not self.api_token:
            return False

        try:
            url = f"{self.INCIDENTS_API_URL}/{incident_id}/resolve"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            response = await client.post(url, headers=headers)
            return response.status_code in (200, 202, 204)
        except Exception as e:
            logger.error(f"Error resolving incident: {e}")
            return False

    async def acknowledge_incident(self, incident_id: str) -> bool:
        """Acknowledge an incident."""
        client = self._get_client()
        if client is None or not self.api_token:
            return False

        try:
            url = f"{self.INCIDENTS_API_URL}/{incident_id}/acknowledge"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            response = await client.post(url, headers=headers)
            return response.status_code in (200, 202, 204)
        except Exception as e:
            logger.error(f"Error acknowledging incident: {e}")
            return False


class OnCallAlertManager:
    """Manage alerts and incident routing."""

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._incidents_client: Optional[BetterStackIncidentsClient] = None

    @property
    def incidents_client(self) -> BetterStackIncidentsClient:
        """Get the Better Stack incidents client."""
        if self._incidents_client is None:
            self._incidents_client = BetterStackIncidentsClient()
        return self._incidents_client

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        """Remove an alert rule."""
        if name in self._rules:
            del self._rules[name]

    async def trigger_alert(
        self,
        name: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.P2_MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Alert:
        """Trigger an alert and create an incident."""
        alert = Alert(
            name=name,
            severity=severity,
            message=message,
            metadata=metadata or {},
        )

        self._active_alerts[name] = alert
        self._alert_history.append(alert)

        if self.incidents_client.api_token:
            incident_data = await self.incidents_client.create_incident(
                name=name,
                severity=severity.value.lower(),
                message=message,
                metadata=metadata,
            )
            if incident_data:
                alert.incident_id = incident_data.get("id")

        logger.warning(f"Alert triggered: {name} [{severity.value}] - {message}")

        return alert

    async def resolve_alert(self, name: str) -> bool:
        """Resolve an active alert."""
        if name not in self._active_alerts:
            return False

        alert = self._active_alerts[name]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)

        if alert.incident_id and self.incidents_client.api_token:
            await self.incidents_client.resolve_incident(alert.incident_id)

        del self._active_alerts[name]
        logger.info(f"Alert resolved: {name}")

        return True

    async def acknowledge_alert(self, name: str) -> bool:
        """Acknowledge an active alert."""
        if name not in self._active_alerts:
            return False

        alert = self._active_alerts[name]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)

        if alert.incident_id and self.incidents_client.api_token:
            await self.incidents_client.acknowledge_incident(alert.incident_id)

        logger.info(f"Alert acknowledged: {name}")

        return True

    def evaluate_rules(self, metrics: Dict[str, float]) -> List[Alert]:
        """Evaluate alert rules against current metrics."""
        triggered_alerts = []

        for rule in self._rules.values():
            if rule.metric not in metrics:
                continue

            value = metrics[rule.metric]
            should_trigger = False

            if rule.operator == ">":
                should_trigger = value > rule.threshold
            elif rule.operator == "<":
                should_trigger = value < rule.threshold
            elif rule.operator == ">=":
                should_trigger = value >= rule.threshold
            elif rule.operator == "<=":
                should_trigger = value <= rule.threshold
            elif rule.operator == "==":
                should_trigger = value == rule.threshold

            if should_trigger:
                triggered_alerts.append(
                    Alert(
                        name=rule.name,
                        severity=rule.severity,
                        message=f"{rule.metric} {rule.operator} {rule.threshold} (current: {value})",
                        metadata={
                            "metric": rule.metric,
                            "value": value,
                            "threshold": rule.threshold,
                        },
                    )
                )

        return triggered_alerts

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self._active_alerts.values())

    def get_alert_history(self) -> List[Alert]:
        """Get alert history."""
        return self._alert_history


ALERT_MESSAGES = {
    "queue_backlog_critical": "Queue backlog is critically high: {value} tasks",
    "queue_backlog_warning": "Queue backlog is elevated: {value} tasks",
    "workers_offline": "All Celery workers are offline",
    "task_failure_rate_high": "Task failure rate is {value}%",
    "dead_letter_queue_high": "Dead letter queue has {value} tasks",
    "workers_idle": "No workers processing but tasks are queued",
    "retry_queue_building": "Retry queue is building: {value} tasks",
}


def create_default_alert_manager() -> OnCallAlertManager:
    """Create alert manager with default alert rules."""
    manager = OnCallAlertManager()

    manager.add_rule(
        AlertRule(
            name="queue_backlog_critical",
            metric="queue_depth",
            threshold=1000,
            operator=">",
            severity=AlertSeverity.P0_CRITICAL,
            duration_seconds=300,
        )
    )

    manager.add_rule(
        AlertRule(
            name="queue_backlog_warning",
            metric="queue_depth",
            threshold=100,
            operator=">",
            severity=AlertSeverity.P2_MEDIUM,
            duration_seconds=300,
        )
    )

    manager.add_rule(
        AlertRule(
            name="task_failure_rate_high",
            metric="task_failure_rate",
            threshold=10,
            operator=">",
            severity=AlertSeverity.P1_HIGH,
            duration_seconds=300,
        )
    )

    manager.add_rule(
        AlertRule(
            name="workers_offline",
            metric="workers_online",
            threshold=1,
            operator="<",
            severity=AlertSeverity.P0_CRITICAL,
            duration_seconds=60,
        )
    )

    manager.add_rule(
        AlertRule(
            name="dead_letter_queue_high",
            metric="dead_letter_size",
            threshold=50,
            operator=">",
            severity=AlertSeverity.P2_MEDIUM,
            duration_seconds=300,
        )
    )

    return manager


_async_alert_manager: Optional[OnCallAlertManager] = None


def get_alert_manager() -> OnCallAlertManager:
    """Get the global alert manager instance."""
    global _async_alert_manager
    if _async_alert_manager is None:
        _async_alert_manager = create_default_alert_manager()
    return _async_alert_manager
