"""
Tests for Feedback Collection API - src/api/feedback_collection.py
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.feedback_collection import router


def _make_app():
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_conversion(**overrides):
    obj = MagicMock()
    obj.id = overrides.get("id", uuid.uuid4())
    obj.user_id = overrides.get("user_id", "test_user")
    obj.status = overrides.get("status", "completed")
    obj.created_at = overrides.get("created_at", datetime.now(timezone.utc))
    obj.updated_at = overrides.get("updated_at", datetime.now(timezone.utc))
    obj.input_data = overrides.get("input_data", {"file_path": "/test/file.jar"})
    return obj


def _override_db(app, mock_db):
    async def _get_db():
        return mock_db

    from db.base import get_db

    app.dependency_overrides[get_db] = _get_db
    return app


class TestSubmitFeedback:
    """Tests for POST /feedback/submit"""

    def test_submit_feedback_conversion_not_found(self):
        app = _make_app()
        conv_id = str(uuid.uuid4())
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        _override_db(app, mock_db)

        mock_analytics_instance = MagicMock()
        mock_analytics_instance.track_feedback_submitted = AsyncMock()

        with patch(
            "api.feedback_collection.get_analytics_service",
            return_value=mock_analytics_instance,
        ):
            client = TestClient(app)
            resp = client.post(
                "/feedback/submit?user_id=test_user",
                json={
                    "conversion_id": conv_id,
                    "rating": 4,
                    "feedback_type": "conversion_quality",
                },
            )

        assert resp.status_code == 404

    def test_submit_feedback_success(self):
        app = _make_app()
        conv_id = str(uuid.uuid4())
        mock_conversion = _mock_conversion(id=conv_id, user_id="test_user")
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_conversion)
        mock_db.execute = AsyncMock(return_value=mock_result)
        _override_db(app, mock_db)

        mock_analytics_instance = MagicMock()
        mock_analytics_instance.track_feedback_submitted = AsyncMock(return_value=MagicMock())

        with patch(
            "api.feedback_collection.get_analytics_service",
            return_value=mock_analytics_instance,
        ):
            client = TestClient(app)
            resp = client.post(
                "/feedback/submit?user_id=test_user",
                json={
                    "conversion_id": conv_id,
                    "rating": 5,
                    "feedback_type": "conversion_quality",
                    "comment": "Excellent!",
                    "specific_issues": [],
                    "would_recommend": True,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["thank_you"] is True
        assert "feedback_id" in data


class TestRateConversion:
    """Tests for POST /feedback/rate-conversion"""

    def test_rate_conversion_not_found(self):
        app = _make_app()
        conv_id = str(uuid.uuid4())
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/feedback/rate-conversion?user_id=test_user",
            json={
                "conversion_id": conv_id,
                "rating": 3,
                "would_use_again": True,
            },
        )

        assert resp.status_code == 404

    def test_rate_conversion_success(self):
        app = _make_app()
        conv_id = str(uuid.uuid4())
        mock_conversion = _mock_conversion(id=conv_id, user_id="test_user")
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_conversion)
        mock_db.execute = AsyncMock(return_value=mock_result)
        _override_db(app, mock_db)

        mock_analytics_instance = MagicMock()
        mock_analytics_instance.track_feedback_submitted = AsyncMock(return_value=MagicMock())

        with patch(
            "api.feedback_collection.get_analytics_service",
            return_value=mock_analytics_instance,
        ):
            client = TestClient(app)
            resp = client.post(
                "/feedback/rate-conversion?user_id=test_user",
                json={
                    "conversion_id": conv_id,
                    "rating": 4,
                    "would_use_again": False,
                },
            )

        assert resp.status_code == 200
        assert resp.json()["rating"] == 4


class TestSubmitBugReport:
    """Tests for POST /feedback/bug-report"""

    def test_submit_bug_report_success(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/feedback/bug-report?user_id=test_user",
            json={
                "title": "Test bug",
                "description": "Something broke",
                "severity": "high",
                "steps_to_reproduce": "Click button",
            },
        )

        assert resp.status_code == 200
        assert "bug_id" in resp.json()

    def test_submit_critical_bug_report(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/feedback/bug-report?user_id=test_user",
            json={
                "title": "Critical bug",
                "description": "System down",
                "severity": "critical",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["severity"] == "critical"

    def test_submit_low_severity_bug(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/feedback/bug-report?user_id=test_user",
            json={
                "title": "Minor issue",
                "description": "Typo",
                "severity": "low",
            },
        )

        assert resp.status_code == 200

    def test_submit_bug_with_optional_fields(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/feedback/bug-report?user_id=test_user",
            json={
                "title": "Bug with details",
                "description": "Detailed description",
                "severity": "medium",
                "conversion_id": str(uuid.uuid4()),
                "steps_to_reproduce": "1. Open app 2. Click X",
                "expected_behavior": "Should work",
                "actual_behavior": "Crashed",
                "attachments": ["screenshot.png"],
            },
        )

        assert resp.status_code == 200


class TestSubmitFeatureRequest:
    """Tests for POST /feedback/feature-request"""

    def test_submit_feature_request_success(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/feedback/feature-request?user_id=test_user",
            json={
                "title": "Dark mode",
                "description": "Please add dark mode",
                "use_case": "Late night coding",
                "priority": "high",
            },
        )

        assert resp.status_code == 200
        assert "feature_id" in resp.json()

    def test_submit_feature_request_with_similar_tools(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(
            "/feedback/feature-request?user_id=test_user",
            json={
                "title": "Auto-detect mod type",
                "description": "Detect mod type automatically",
                "use_case": "Faster conversion",
                "priority": "medium",
                "similar_tools": "Modrinth plugin checker",
            },
        )

        assert resp.status_code == 200


class TestGetMyFeedback:
    """Tests for GET /feedback/my-feedback"""

    def test_get_my_feedback(self):
        app = _make_app()
        mock_db = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.get("/feedback/my-feedback?user_id=test_user")

        assert resp.status_code == 200
        assert resp.json() == []


class TestGetConversionFeedback:
    """Tests for GET /feedback/conversion/{conversion_id}/feedback"""

    def test_get_conversion_feedback_not_found(self):
        app = _make_app()
        conv_id = str(uuid.uuid4())
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.get(f"/feedback/conversion/{conv_id}/feedback?user_id=test_user")

        assert resp.status_code == 404

    def test_get_conversion_feedback_success(self):
        app = _make_app()
        conv_id = str(uuid.uuid4())
        mock_conversion = _mock_conversion(id=conv_id, user_id="test_user")
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_conversion)
        mock_db.execute = AsyncMock(return_value=mock_result)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.get(f"/feedback/conversion/{conv_id}/feedback?user_id=test_user")

        assert resp.status_code == 200
        data = resp.json()
        assert data["has_feedback"] is False
        assert data["can_submit"] is True
