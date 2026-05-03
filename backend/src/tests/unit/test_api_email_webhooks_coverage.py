"""
Tests for Email Webhooks API - src/api/email_webhooks.py
"""

import json
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.email_webhooks import router


def _make_app():
    app = FastAPI()
    app.include_router(router)
    return app


def _override_db(app, mock_db):
    async def _get_db():
        return mock_db

    from db.base import get_db

    app.dependency_overrides[get_db] = _get_db
    return app


def _mock_db_with_user(email="test@example.com", found=True):
    mock_db = AsyncMock()
    mock_result = MagicMock()
    if found:
        user = MagicMock()
        user.id = "user-123"
        user.email = email
        mock_result.scalar_one_or_none = MagicMock(return_value=user)
    else:
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)
    return mock_db


class TestHandleResendEmailEvents:
    def test_bounce_event_with_user(self):
        app = _make_app()
        mock_db = _mock_db_with_user("bounce@example.com")
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "bounce", "email": "bounce@example.com", "bounce_type": "permanent"}],
            headers={"content-type": "application/json"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 1

    def test_bounce_event_no_user(self):
        app = _make_app()
        mock_db = _mock_db_with_user(found=False)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "bounce", "email": "nobody@example.com"}],
        )

        assert resp.status_code == 200

    def test_complaint_event(self):
        app = _make_app()
        mock_db = _mock_db_with_user("spam@example.com")
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "complaint", "email": "spam@example.com"}],
        )

        assert resp.status_code == 200
        assert resp.json()["processed"] == 1

    def test_complaint_no_user(self):
        app = _make_app()
        mock_db = _mock_db_with_user(found=False)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "complaint", "email": "nobody@example.com"}],
        )

        assert resp.status_code == 200

    def test_unsubscribe_event(self):
        app = _make_app()
        mock_db = _mock_db_with_user("unsub@example.com")
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "unsubscribe", "email": "unsub@example.com"}],
        )

        assert resp.status_code == 200

    def test_unsubscribe_no_user(self):
        app = _make_app()
        mock_db = _mock_db_with_user(found=False)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "unsubscribe", "email": "nobody@example.com"}],
        )

        assert resp.status_code == 200

    def test_dropped_event(self):
        app = _make_app()
        mock_db = _mock_db_with_user("drop@example.com")
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "dropped", "email": "drop@example.com", "reason": "invalid address"}],
        )

        assert resp.status_code == 200

    def test_dropped_no_user(self):
        app = _make_app()
        mock_db = _mock_db_with_user(found=False)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "dropped", "email": "nobody@example.com"}],
        )

        assert resp.status_code == 200

    def test_delivered_event_ignored(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "delivered", "email": "test@example.com"}],
        )

        assert resp.status_code == 200
        assert resp.json()["processed"] == 1

    def test_open_event_ignored(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "open", "email": "test@example.com"}],
        )

        assert resp.status_code == 200

    def test_click_event_ignored(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "click", "email": "test@example.com"}],
        )

        assert resp.status_code == 200

    def test_unknown_event_type(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "custom_event", "email": "test@example.com"}],
        )

        assert resp.status_code == 200

    def test_single_event_object_not_array(self):
        app = _make_app()
        mock_db = _mock_db_with_user("test@example.com")
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json={"type": "bounce", "email": "test@example.com"},
        )

        assert resp.status_code == 200

    def test_multiple_events_batch(self):
        app = _make_app()
        mock_db = _mock_db_with_user("test@example.com")
        _override_db(app, mock_db)

        events = [
            {"type": "delivered", "email": "test@example.com"},
            {"type": "open", "email": "test@example.com"},
            {"type": "click", "email": "test@example.com"},
        ]

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=events,
        )

        assert resp.status_code == 200
        assert resp.json()["processed"] == 3

    def test_invalid_json_returns_400(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            content=b"not valid json{{{",
            headers={"content-type": "application/json"},
        )

        assert resp.status_code == 400

    def test_event_processing_error_continues(self):
        app = _make_app()
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("db error"))
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/webhooks/resend/email-events",
            json=[{"type": "bounce", "email": "fail@example.com"}],
        )

        assert resp.status_code == 200
        assert len(resp.json()["errors"]) > 0


class TestUnsubscribe:
    def test_unsubscribe_existing_user(self):
        app = _make_app()
        mock_db = _mock_db_with_user("unsub@example.com")
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.get("/webhooks/unsubscribe?email=unsub@example.com")

        assert resp.status_code == 200
        assert resp.json()["status"] == "unsubscribed"

    def test_unsubscribe_nonexistent_user(self):
        app = _make_app()
        mock_db = _mock_db_with_user(found=False)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.get("/webhooks/unsubscribe?email=nobody@example.com")

        assert resp.status_code == 200
        assert resp.json()["status"] == "unsubscribed"
