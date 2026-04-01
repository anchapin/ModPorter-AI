"""
Simple unit tests for batch conversion, build performance, and feedback collection API endpoints.

Issue: 0% coverage for:
- src/api/batch_conversion.py (104 stmts)
- src/api/build_performance.py (76 stmts)
- src/api/feedback_collection.py (84 stmts)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import FastAPI


# ============================================
# FEEDBACK COLLECTION TESTS
# ============================================

from api.feedback_collection import router as feedback_router


feedback_app = FastAPI()
feedback_app.include_router(feedback_router, prefix="/api/v1")


@pytest.fixture
def mock_feedback_db():
    """Mock database session for feedback."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    return mock


@pytest.fixture
def feedback_client(mock_feedback_db):
    """Create test client for feedback."""
    from api.feedback_collection import get_db

    feedback_app.dependency_overrides[get_db] = lambda: mock_feedback_db

    with patch("api.feedback_collection.get_analytics_service") as mock_analytics:
        mock_analytics_instance = MagicMock()
        mock_analytics_instance.track_feedback_submitted = MagicMock()
        mock_analytics.return_value = mock_analytics_instance

        yield TestClient(feedback_app)

    feedback_app.dependency_overrides.clear()


class TestFeedbackEndpoints:
    """Tests for feedback collection endpoints."""

    def test_submit_bug_report(self, feedback_client):
        """Test submitting bug report."""
        response = feedback_client.post(
            "/api/v1/feedback/bug-report",
            json={"title": "Test bug", "description": "Something is broken", "severity": "medium"},
            params={"user_id": "test_user_id"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "bug_id" in data

    def test_submit_bug_report_critical(self, feedback_client):
        """Test submitting critical bug report."""
        response = feedback_client.post(
            "/api/v1/feedback/bug-report",
            json={"title": "Critical bug", "description": "System crashed", "severity": "critical"},
            params={"user_id": "test_user_id"},
        )

        assert response.status_code == 200


# ============================================
# BUILD PERFORMANCE TESTS - Direct Function Tests
# ============================================


def test_build_performance_models_import():
    """Test that build performance models can be imported."""
    from api.build_performance import (
        BuildPerformanceStartRequest,
        BuildPerformanceStartResponse,
        BuildStageUpdateRequest,
        BuildPerformanceEndRequest,
    )

    req = BuildPerformanceStartRequest(
        conversion_id="test", build_type="full", target_version="1.20.0", mod_size_bytes=1000
    )
    assert req.conversion_id == "test"


# ============================================
# BATCH CONVERSION TESTS - Simple Function Tests
# ============================================


def test_batch_conversion_models():
    """Test that batch conversion models work."""
    from api.batch_conversion import (
        BatchConversionRequest,
        BatchConversionResponse,
    )

    req = BatchConversionRequest(
        files=[{"filename": "test1.jar"}, {"filename": "test2.jar"}], priority="normal"
    )
    assert len(req.files) == 2

    resp = BatchConversionResponse(
        batch_id="test", total_files=1, estimated_time_minutes=2, status="queued", message="test"
    )
    assert resp.batch_id == "test"
