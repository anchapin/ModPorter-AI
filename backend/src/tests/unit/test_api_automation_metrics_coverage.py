"""
Tests for Automation Metrics API endpoints - src/api/automation_metrics.py
Covers all 6 endpoints with mocked service layer.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.automation_metrics import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _make_snapshot(**overrides):
    """Build a fake AutomationMetricsSnapshot."""
    defaults = dict(
        automation_rate=95.0,
        one_click_rate=80.0,
        auto_recovery_rate=80.0,
        avg_conversion_time_seconds=45.0,
        mode_classification_accuracy=90.0,
        avg_user_satisfaction=4.5,
        total_conversions=100,
        target_automation_rate=95.0,
        target_one_click_rate=80.0,
        target_auto_recovery_rate=80.0,
        automation_target_met=True,
        one_click_target_met=True,
        auto_recovery_target_met=True,
        period_start=datetime.now(timezone.utc) - timedelta(hours=24),
        period_end=datetime.now(timezone.utc),
        calculated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    snap = MagicMock()
    for k, v in defaults.items():
        setattr(snap, k, v)
    return snap


def _make_dashboard_data():
    return {
        "metrics": {
            "automation_rate": {"value": 95.0, "target": 95.0, "met": True, "unit": "%"},
            "one_click_rate": {"value": 80.0, "target": 80.0, "met": True, "unit": "%"},
            "auto_recovery_rate": {"value": 80.0, "target": 80.0, "met": True, "unit": "%"},
            "avg_conversion_time_seconds": {"value": 45.0, "unit": "seconds"},
            "mode_classification_accuracy": {"value": 90.0, "unit": "%"},
            "user_satisfaction": {"value": 4.5, "unit": "score"},
        },
        "summary": {
            "total_conversions": 100,
            "automated_conversions": 95,
            "one_click_conversions": 80,
            "total_errors": 10,
            "auto_recovered": 8,
        },
        "status": {"overall": "excellent", "targets_met": 3, "total_targets": 3},
        "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-02T00:00:00Z", "hours": 24},
        "calculated_at": "2026-01-02T00:00:00Z",
    }


@patch("api.automation_metrics.get_automation_metrics_service")
def test_get_automation_metrics_success(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.get_current_metrics.return_value = _make_snapshot()
    mock_get_svc.return_value = mock_svc

    resp = client.get("/automation", params={"period_hours": 24})

    assert resp.status_code == 200
    data = resp.json()
    assert data["automation_rate"] == 95.0
    assert data["total_conversions"] == 100
    assert data["automation_target_met"] is True


@patch("api.automation_metrics.get_automation_metrics_service")
def test_get_automation_metrics_error(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.get_current_metrics.side_effect = RuntimeError("db down")
    mock_get_svc.return_value = mock_svc

    resp = client.get("/automation")

    assert resp.status_code == 500
    assert "db down" in resp.json()["detail"]


@patch("api.automation_metrics.get_automation_metrics_service")
def test_get_automation_dashboard_success(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.get_dashboard_data.return_value = _make_dashboard_data()
    mock_get_svc.return_value = mock_svc

    resp = client.get("/automation/dashboard", params={"period_hours": 24})

    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert data["metrics"]["automation_rate"]["value"] == 95.0
    assert data["summary"]["total_conversions"] == 100
    assert data["status"]["overall"] == "excellent"


@patch("api.automation_metrics.get_automation_metrics_service")
def test_get_automation_dashboard_error(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.get_dashboard_data.side_effect = RuntimeError("fail")
    mock_get_svc.return_value = mock_svc

    resp = client.get("/automation/dashboard")

    assert resp.status_code == 500


@patch("api.automation_metrics.get_automation_metrics_service")
def test_record_conversion_event_success(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.record_conversion_event.return_value = None
    mock_get_svc.return_value = mock_svc

    resp = client.post(
        "/automation/record",
        json={
            "conversion_id": "conv-123",
            "was_automated": True,
            "was_one_click": True,
            "had_error": False,
            "auto_recovered": False,
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "success"
    assert data["conversion_id"] == "conv-123"


@patch("api.automation_metrics.get_automation_metrics_service")
def test_record_conversion_event_with_optional_fields(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.record_conversion_event.return_value = None
    mock_get_svc.return_value = mock_svc

    resp = client.post(
        "/automation/record",
        json={
            "conversion_id": "conv-456",
            "was_automated": True,
            "was_one_click": True,
            "upload_time": "2026-03-31T12:00:00Z",
            "download_time": "2026-03-31T12:05:00Z",
            "conversion_time_seconds": 120.0,
            "mode_classification_correct": True,
            "had_error": True,
            "auto_recovered": True,
            "user_satisfaction_score": 4.5,
        },
    )

    assert resp.status_code == 201


@patch("api.automation_metrics.get_automation_metrics_service")
def test_record_conversion_event_error(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.record_conversion_event.side_effect = ValueError("bad")
    mock_get_svc.return_value = mock_svc

    resp = client.post(
        "/automation/record",
        json={"conversion_id": "conv-err", "was_automated": False},
    )

    assert resp.status_code == 500


@patch("api.automation_metrics.get_automation_metrics_service")
def test_get_automation_history_success(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.get_historical_data.return_value = [
        {
            "timestamp": "2026-01-01T00:00:00Z",
            "automation_rate": 95.0,
            "one_click_rate": 80.0,
            "auto_recovery_rate": 80.0,
            "avg_conversion_time_seconds": 45.0,
            "mode_classification_accuracy": 90.0,
            "avg_user_satisfaction": 4.5,
            "total_conversions": 100,
        },
    ]
    mock_get_svc.return_value = mock_svc

    resp = client.get("/automation/history", params={"days": 7, "interval_hours": 1})

    assert resp.status_code == 200
    data = resp.json()
    assert data["period_days"] == 7
    assert data["interval_hours"] == 1
    assert len(data["data"]) == 1
    assert data["data"][0]["automation_rate"] == 95.0


@patch("api.automation_metrics.get_automation_metrics_service")
def test_get_automation_history_empty(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.get_historical_data.return_value = []
    mock_get_svc.return_value = mock_svc

    resp = client.get("/automation/history", params={"days": 7})

    assert resp.status_code == 200
    assert resp.json()["data"] == []


@patch("api.automation_metrics.get_automation_metrics_service")
def test_get_automation_history_error(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.get_historical_data.side_effect = RuntimeError("err")
    mock_get_svc.return_value = mock_svc

    resp = client.get("/automation/history")

    assert resp.status_code == 500


@patch("api.automation_metrics.get_automation_metrics_service")
def test_get_conversion_events_success(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.get_all_events.return_value = (
        [
            {
                "conversion_id": "c1",
                "timestamp": "2026-01-01T00:00:00Z",
                "was_automated": True,
                "was_one_click": True,
                "conversion_time_seconds": 50.0,
                "mode_classification_correct": True,
                "had_error": False,
                "auto_recovered": False,
                "user_satisfaction_score": 4.0,
            },
        ],
        1,
    )
    mock_get_svc.return_value = mock_svc

    resp = client.get("/automation/events", params={"limit": 100, "offset": 0})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["events"][0]["conversion_id"] == "c1"


@patch("api.automation_metrics.get_automation_metrics_service")
def test_get_conversion_events_empty(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.get_all_events.return_value = ([], 0)
    mock_get_svc.return_value = mock_svc

    resp = client.get("/automation/events")

    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@patch("api.automation_metrics.get_automation_metrics_service")
def test_get_conversion_events_error(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.get_all_events.side_effect = RuntimeError("err")
    mock_get_svc.return_value = mock_svc

    resp = client.get("/automation/events")

    assert resp.status_code == 500


@patch("api.automation_metrics.get_automation_metrics_service")
def test_reset_automation_metrics_success(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.reset_metrics.return_value = None
    mock_get_svc.return_value = mock_svc

    resp = client.post("/automation/reset")

    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


@patch("api.automation_metrics.get_automation_metrics_service")
def test_reset_automation_metrics_error(mock_get_svc):
    mock_svc = MagicMock()
    mock_svc.reset_metrics.side_effect = RuntimeError("err")
    mock_get_svc.return_value = mock_svc

    resp = client.post("/automation/reset")

    assert resp.status_code == 500


@patch("api.automation_metrics.get_automation_metrics_service")
def test_get_automation_metrics_null_period(mock_get_svc):
    snapshot = _make_snapshot(period_start=None, period_end=None)
    mock_svc = MagicMock()
    mock_svc.get_current_metrics.return_value = snapshot
    mock_get_svc.return_value = mock_svc

    resp = client.get("/automation")

    assert resp.status_code == 200
    assert resp.json()["period_start"] is None
    assert resp.json()["period_end"] is None
