"""
Tests for Analytics API endpoints - src/api/analytics.py
Covers all 5 endpoints: track_event, get_events, get_stats, pageview, conversion.
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.analytics import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

VALID_CONV_ID = str(uuid.uuid4())


def _make_db_event(**overrides):
    e = MagicMock()
    e.id = overrides.get("id", uuid.uuid4())
    e.event_type = overrides.get("event_type", "page_view")
    e.event_category = overrides.get("event_category", "navigation")
    e.user_id = overrides.get("user_id", None)
    e.session_id = overrides.get("session_id", None)
    e.conversion_id = overrides.get("conversion_id", None)
    e.event_properties = overrides.get("event_properties", None)
    e.created_at = overrides.get("created_at", datetime.now(timezone.utc))
    return e


class TestTrackEvent:
    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_track_event_success(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        db_event = _make_db_event(
            event_type="page_view",
            event_category="navigation",
            user_id="user1",
            session_id="sess1",
        )
        svc = mock_svc_cls.return_value
        svc.track_event = AsyncMock(return_value=db_event)

        resp = client.post(
            "/events",
            json={
                "event_type": "page_view",
                "event_category": "navigation",
                "user_id": "user1",
                "session_id": "sess1",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["event_type"] == "page_view"
        assert data["event_category"] == "navigation"

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_track_event_with_conversion_id(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        db_event = _make_db_event(conversion_id=uuid.UUID(VALID_CONV_ID))
        svc = mock_svc_cls.return_value
        svc.track_event = AsyncMock(return_value=db_event)

        resp = client.post(
            "/events",
            json={
                "event_type": "conversion_start",
                "event_category": "conversion",
                "conversion_id": VALID_CONV_ID,
            },
        )

        assert resp.status_code == 200

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_track_event_invalid_conversion_id(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        db_event = _make_db_event()
        svc = mock_svc_cls.return_value
        svc.track_event = AsyncMock(return_value=db_event)

        resp = client.post(
            "/events",
            json={
                "event_type": "page_view",
                "event_category": "navigation",
                "conversion_id": "not-a-uuid",
            },
        )

        assert resp.status_code == 200

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_track_event_service_error(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        svc = mock_svc_cls.return_value
        svc.track_event = AsyncMock(side_effect=Exception("db error"))

        resp = client.post(
            "/events",
            json={
                "event_type": "page_view",
                "event_category": "navigation",
            },
        )

        assert resp.status_code == 500

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_track_event_with_properties(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        db_event = _make_db_event(event_properties={"page": "/", "referrer": "google.com"})
        svc = mock_svc_cls.return_value
        svc.track_event = AsyncMock(return_value=db_event)

        resp = client.post(
            "/events",
            json={
                "event_type": "page_view",
                "event_category": "navigation",
                "event_properties": {"page": "/", "referrer": "google.com"},
            },
        )

        assert resp.status_code == 200
        assert resp.json()["event_properties"]["page"] == "/"


class TestGetEvents:
    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_get_events_empty(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        svc = mock_svc_cls.return_value
        svc.get_events = AsyncMock(return_value=[])

        resp = client.get("/events")

        assert resp.status_code == 200
        assert resp.json() == []

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_get_events_with_results(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        db_event = _make_db_event()
        svc = mock_svc_cls.return_value
        svc.get_events = AsyncMock(return_value=[db_event])

        resp = client.get("/events", params={"event_type": "page_view"})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["event_type"] == "page_view"

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_get_events_with_date_filters(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        svc = mock_svc_cls.return_value
        svc.get_events = AsyncMock(return_value=[])

        start = "2024-01-01T00:00:00"
        end = "2024-12-31T23:59:59"

        resp = client.get(
            "/events",
            params={"start_date": start, "end_date": end},
        )

        assert resp.status_code == 200

    @patch("api.analytics.get_db")
    def test_get_events_invalid_start_date(self, mock_get_db):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        resp = client.get("/events", params={"start_date": "not-a-date"})

        assert resp.status_code == 400

    @patch("api.analytics.get_db")
    def test_get_events_invalid_end_date(self, mock_get_db):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        resp = client.get("/events", params={"end_date": "bad-date"})

        assert resp.status_code == 400

    @patch("api.analytics.get_db")
    def test_get_events_invalid_conversion_id(self, mock_get_db):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        resp = client.get("/events", params={"conversion_id": "not-uuid"})

        assert resp.status_code == 400

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_get_events_service_error(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        svc = mock_svc_cls.return_value
        svc.get_events = AsyncMock(side_effect=Exception("db error"))

        resp = client.get("/events")

        assert resp.status_code == 500

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_get_events_with_conversion_id(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        svc = mock_svc_cls.return_value
        svc.get_events = AsyncMock(return_value=[])

        resp = client.get("/events", params={"conversion_id": VALID_CONV_ID})

        assert resp.status_code == 200


class TestGetStats:
    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_get_stats_success(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        svc = mock_svc_cls.return_value
        svc.get_event_counts = AsyncMock(return_value=[{"group": "page_view", "count": 10}])
        svc.get_events_timeline = AsyncMock(return_value=[{"date": "2024-01-01", "count": 5}])
        svc.get_unique_users = AsyncMock(return_value=3)

        resp = client.get("/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_events"] == 10
        assert data["unique_users"] == 3
        assert len(data["event_counts"]) == 1
        assert len(data["timeline"]) == 1

    @patch("api.analytics.get_db")
    def test_get_stats_invalid_group_by(self, mock_get_db):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        resp = client.get("/stats", params={"group_by": "invalid_field"})

        assert resp.status_code == 400

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_get_stats_service_error(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        svc = mock_svc_cls.return_value
        svc.get_event_counts = AsyncMock(side_effect=Exception("db error"))

        resp = client.get("/stats")

        assert resp.status_code == 500

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_get_stats_with_filters(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        svc = mock_svc_cls.return_value
        svc.get_event_counts = AsyncMock(return_value=[])
        svc.get_events_timeline = AsyncMock(return_value=[])
        svc.get_unique_users = AsyncMock(return_value=0)

        resp = client.get(
            "/stats",
            params={
                "event_type": "page_view",
                "event_category": "navigation",
                "days": 30,
                "group_by": "event_category",
            },
        )

        assert resp.status_code == 200


class TestTrackPageView:
    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_track_pageview_success(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        mock_event = MagicMock()
        mock_event.id = uuid.uuid4()
        svc = mock_svc_cls.return_value
        svc.track_event = AsyncMock(return_value=mock_event)

        resp = client.post(
            "/events/pageview",
            params={"page": "/"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "event_id" in data

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_track_pageview_with_session(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        mock_event = MagicMock()
        mock_event.id = uuid.uuid4()
        svc = mock_svc_cls.return_value
        svc.track_event = AsyncMock(return_value=mock_event)

        resp = client.post(
            "/events/pageview",
            params={"page": "/convert", "session_id": "sess-123", "user_id": "u-1"},
        )

        assert resp.status_code == 200

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_track_pageview_service_error(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        svc = mock_svc_cls.return_value
        svc.track_event = AsyncMock(side_effect=Exception("fail"))

        resp = client.post(
            "/events/pageview",
            params={"page": "/"},
        )

        assert resp.status_code == 500


class TestTrackConversionEvent:
    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_track_conversion_success(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        mock_event = MagicMock()
        mock_event.id = uuid.uuid4()
        svc = mock_svc_cls.return_value
        svc.track_event = AsyncMock(return_value=mock_event)

        resp = client.post(
            "/events/conversion",
            params={
                "conversion_id": VALID_CONV_ID,
                "event_type": "conversion_start",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    @patch("api.analytics.get_db")
    def test_track_conversion_invalid_event_type(self, mock_get_db):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        resp = client.post(
            "/events/conversion",
            params={
                "conversion_id": VALID_CONV_ID,
                "event_type": "invalid_type",
            },
        )

        assert resp.status_code == 400

    @patch("api.analytics.get_db")
    def test_track_conversion_invalid_uuid(self, mock_get_db):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        resp = client.post(
            "/events/conversion",
            params={
                "conversion_id": "not-a-uuid",
                "event_type": "conversion_start",
            },
        )

        assert resp.status_code == 400

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_track_conversion_service_error(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        svc = mock_svc_cls.return_value
        svc.track_event = AsyncMock(side_effect=Exception("fail"))

        resp = client.post(
            "/events/conversion",
            params={
                "conversion_id": VALID_CONV_ID,
                "event_type": "conversion_start",
            },
        )

        assert resp.status_code == 500

    @patch("api.analytics.AnalyticsService")
    @patch("api.analytics.get_db")
    def test_track_conversion_all_valid_types(self, mock_get_db, mock_svc_cls):
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        mock_event = MagicMock()
        mock_event.id = uuid.uuid4()
        svc = mock_svc_cls.return_value
        svc.track_event = AsyncMock(return_value=mock_event)

        for evt_type in [
            "conversion_start",
            "conversion_complete",
            "conversion_fail",
            "conversion_cancel",
            "conversion_download",
        ]:
            resp = client.post(
                "/events/conversion",
                params={
                    "conversion_id": VALID_CONV_ID,
                    "event_type": evt_type,
                },
            )
            assert resp.status_code == 200, f"Failed for {evt_type}"


class TestGetEventTypes:
    def test_get_event_types(self):
        resp = client.get("/events/types")

        assert resp.status_code == 200
        data = resp.json()
        assert "event_types" in data
        assert "categories" in data
        assert "page_view" in data["event_types"]
        assert "navigation" in data["categories"]
        assert len(data["event_types"]) > 5
        assert len(data["categories"]) > 3
