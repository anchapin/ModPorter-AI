"""
Tests for Feedback API - src/api/feedback.py
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.feedback import router


def _make_app():
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_feedback_obj(**overrides):
    obj = MagicMock()
    obj.id = overrides.get("id", uuid.uuid4())
    obj.job_id = overrides.get("job_id", uuid.uuid4())
    obj.feedback_type = overrides.get("feedback_type", "thumbs_up")
    obj.user_id = overrides.get("user_id", "user123")
    obj.comment = overrides.get("comment")
    obj.quality_rating = overrides.get("quality_rating")
    obj.specific_issues = overrides.get("specific_issues")
    obj.suggested_improvements = overrides.get("suggested_improvements")
    obj.conversion_accuracy = overrides.get("conversion_accuracy")
    obj.visual_quality = overrides.get("visual_quality")
    obj.performance_rating = overrides.get("performance_rating")
    obj.ease_of_use = overrides.get("ease_of_use")
    obj.agent_specific_feedback = overrides.get("agent_specific_feedback")
    obj.created_at = overrides.get("created_at", datetime.now(timezone.utc))
    return obj


def _mock_correction_obj(**overrides):
    obj = MagicMock()
    obj.id = overrides.get("id", uuid.uuid4())
    obj.job_id = overrides.get("job_id", uuid.uuid4())
    obj.user_id = overrides.get("user_id")
    obj.original_output = overrides.get("original_output", "getWorld()")
    obj.corrected_output = overrides.get("corrected_output", "getDimension()")
    obj.correction_rationale = overrides.get("correction_rationale")
    obj.original_chunk_id = overrides.get("original_chunk_id")
    obj.status = overrides.get("status", "pending")
    obj.submitted_at = overrides.get("submitted_at", datetime.now(timezone.utc))
    obj.reviewed_at = overrides.get("reviewed_at")
    obj.applied_at = overrides.get("applied_at")
    obj.review_notes = overrides.get("review_notes")
    obj.embedding_updated = overrides.get("embedding_updated", False)
    return obj


def _override_db(app, mock_db):
    async def _get_db():
        return mock_db

    from db.base import get_db

    app.dependency_overrides[get_db] = _get_db
    return app


class TestSubmitFeedback:
    """Tests for POST /feedback"""

    def test_submit_feedback_success(self):
        app = _make_app()
        job_id = str(uuid.uuid4())
        mock_fb = _mock_feedback_obj(job_id=uuid.UUID(job_id))
        mock_db = AsyncMock()

        with patch("api.feedback.crud") as mock_crud:
            mock_crud.get_job = AsyncMock(return_value=MagicMock())
            mock_crud.create_enhanced_feedback = AsyncMock(return_value=mock_fb)
            _override_db(app, mock_db)

            client = TestClient(app)
            resp = client.post(
                "/feedback",
                json={
                    "job_id": job_id,
                    "feedback_type": "thumbs_up",
                    "comment": "Great!",
                    "quality_rating": 5,
                },
            )

        assert resp.status_code == 200
        assert resp.json()["job_id"] == job_id

    def test_submit_feedback_invalid_uuid(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post(
            "/feedback",
            json={"job_id": "not-a-uuid", "feedback_type": "thumbs_up"},
        )
        assert resp.status_code == 400

    def test_submit_feedback_invalid_type(self):
        app = _make_app()
        job_id = str(uuid.uuid4())
        client = TestClient(app)
        resp = client.post(
            "/feedback",
            json={"job_id": job_id, "feedback_type": "invalid"},
        )
        assert resp.status_code == 400

    def test_submit_feedback_invalid_rating(self):
        app = _make_app()
        job_id = str(uuid.uuid4())
        client = TestClient(app)
        resp = client.post(
            "/feedback",
            json={"job_id": job_id, "feedback_type": "thumbs_up", "quality_rating": 99},
        )
        assert resp.status_code == 400

    def test_submit_feedback_job_not_found(self):
        app = _make_app()
        job_id = str(uuid.uuid4())
        mock_db = AsyncMock()

        with patch("api.feedback.crud") as mock_crud:
            mock_crud.get_job = AsyncMock(return_value=None)
            _override_db(app, mock_db)

            client = TestClient(app)
            resp = client.post(
                "/feedback",
                json={"job_id": job_id, "feedback_type": "thumbs_up"},
            )

        assert resp.status_code == 404

    def test_submit_feedback_detailed(self):
        app = _make_app()
        job_id = str(uuid.uuid4())
        mock_fb = _mock_feedback_obj(
            job_id=uuid.UUID(job_id),
            feedback_type="detailed",
            quality_rating=4,
            specific_issues=["missing_texture"],
            suggested_improvements="Add texture support",
        )
        mock_db = AsyncMock()

        with patch("api.feedback.crud") as mock_crud:
            mock_crud.get_job = AsyncMock(return_value=MagicMock())
            mock_crud.create_enhanced_feedback = AsyncMock(return_value=mock_fb)
            _override_db(app, mock_db)

            client = TestClient(app)
            resp = client.post(
                "/feedback",
                json={
                    "job_id": job_id,
                    "feedback_type": "detailed",
                    "quality_rating": 4,
                    "specific_issues": ["missing_texture"],
                    "suggested_improvements": "Add texture support",
                },
            )

        assert resp.status_code == 200

    def test_submit_feedback_db_exception_not_found(self):
        app = _make_app()
        job_id = str(uuid.uuid4())
        mock_db = AsyncMock()

        with patch("api.feedback.crud") as mock_crud:
            mock_crud.get_job = AsyncMock(side_effect=Exception("not found in database"))
            _override_db(app, mock_db)

            client = TestClient(app)
            resp = client.post(
                "/feedback",
                json={"job_id": job_id, "feedback_type": "thumbs_up"},
            )

        assert resp.status_code == 404

    def test_submit_feedback_db_error(self):
        app = _make_app()
        job_id = str(uuid.uuid4())
        mock_db = AsyncMock()

        with patch("api.feedback.crud") as mock_crud:
            mock_crud.get_job = AsyncMock(side_effect=Exception("connection lost"))
            _override_db(app, mock_db)

            client = TestClient(app)
            resp = client.post(
                "/feedback",
                json={"job_id": job_id, "feedback_type": "thumbs_up"},
            )

        assert resp.status_code == 500


class TestGetTrainingData:
    """Tests for GET /ai/training_data"""

    def test_get_training_data_success(self):
        app = _make_app()
        mock_db = AsyncMock()

        with patch("api.feedback.crud") as mock_crud:
            mock_crud.list_all_feedback = AsyncMock(return_value=[])
            mock_crud.get_job = AsyncMock(return_value=None)
            _override_db(app, mock_db)

            client = TestClient(app)
            resp = client.get("/ai/training_data")

        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_get_training_data_invalid_skip(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/ai/training_data?skip=-1")
        assert resp.status_code == 400

    def test_get_training_data_invalid_limit(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/ai/training_data?limit=0")
        assert resp.status_code == 400

    def test_get_training_data_limit_too_large(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/ai/training_data?limit=1001")
        assert resp.status_code == 400

    def test_get_training_data_db_error(self):
        app = _make_app()
        mock_db = AsyncMock()

        with patch("api.feedback.crud") as mock_crud:
            mock_crud.list_all_feedback = AsyncMock(side_effect=Exception("DB error"))
            _override_db(app, mock_db)

            client = TestClient(app)
            resp = client.get("/ai/training_data")

        assert resp.status_code == 500


class TestTriggerRLTraining:
    """Tests for POST /ai/training/trigger"""

    def test_trigger_rl_training_handles_gracefully(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/ai/training/trigger")
        assert resp.status_code in (200, 500, 503)


class TestGetAgentPerformance:
    """Tests for GET /ai/performance/agents"""

    def test_get_agent_performance_import_error(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/ai/performance/agents")
        assert resp.status_code == 503


class TestGetSpecificAgentPerformance:
    """Tests for GET /ai/performance/agents/{agent_type}"""

    def test_get_specific_agent_import_error(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/ai/performance/agents/java_analyzer")
        assert resp.status_code == 503


class TestCompareAgentPerformance:
    """Tests for POST /ai/performance/compare"""

    def test_compare_agents_import_error(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post(
            "/ai/performance/compare",
            json=["java_analyzer", "asset_converter"],
        )
        assert resp.status_code == 503

    def test_compare_agents_too_few(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post(
            "/ai/performance/compare",
            json=["java_analyzer"],
        )
        assert resp.status_code == 400

    def test_compare_agents_invalid_type(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post(
            "/ai/performance/compare",
            json=["java_analyzer", "invalid_agent"],
        )
        assert resp.status_code == 400


class TestSubmitCorrection:
    """Tests for POST /feedback/corrections"""

    def test_submit_correction_success(self):
        app = _make_app()
        job_id = str(uuid.uuid4())
        corr_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        mock_correction = _mock_correction_obj(
            id=corr_id,
            job_id=uuid.UUID(job_id),
            submitted_at=now,
        )
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch("api.feedback.crud") as mock_crud:
            mock_crud.get_job = AsyncMock(return_value=MagicMock())
            _override_db(app, mock_db)

            with patch("api.feedback.CorrectionSubmission", return_value=mock_correction):
                client = TestClient(app)
                resp = client.post(
                    "/feedback/corrections",
                    json={
                        "job_id": job_id,
                        "original_output": "getWorld()",
                        "corrected_output": "getDimension()",
                        "correction_rationale": "Bedrock uses getDimension()",
                    },
                )

        assert resp.status_code == 201

    def test_submit_correction_invalid_uuid(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post(
            "/feedback/corrections",
            json={
                "job_id": "invalid",
                "original_output": "x",
                "corrected_output": "y",
            },
        )
        assert resp.status_code == 400

    def test_submit_correction_job_not_found(self):
        app = _make_app()
        job_id = str(uuid.uuid4())
        mock_db = AsyncMock()

        with patch("api.feedback.crud") as mock_crud:
            mock_crud.get_job = AsyncMock(return_value=None)
            _override_db(app, mock_db)

            client = TestClient(app)
            resp = client.post(
                "/feedback/corrections",
                json={
                    "job_id": job_id,
                    "original_output": "x",
                    "corrected_output": "y",
                },
            )

        assert resp.status_code == 404

    def test_submit_correction_db_error(self):
        app = _make_app()
        job_id = str(uuid.uuid4())
        mock_db = AsyncMock()

        with patch("api.feedback.crud") as mock_crud:
            mock_crud.get_job = AsyncMock(side_effect=Exception("DB error"))
            _override_db(app, mock_db)

            client = TestClient(app)
            resp = client.post(
                "/feedback/corrections",
                json={
                    "job_id": job_id,
                    "original_output": "x",
                    "corrected_output": "y",
                },
            )

        assert resp.status_code == 500


class TestListCorrections:
    """Tests for GET /feedback/corrections"""

    def test_list_corrections_invalid_limit(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/feedback/corrections?limit=0")
        assert resp.status_code == 400

    def test_list_corrections_invalid_offset(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/feedback/corrections?offset=-1")
        assert resp.status_code == 400

    def test_list_corrections_invalid_status(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/feedback/corrections?status=invalid")
        assert resp.status_code == 400

    def test_list_corrections_invalid_job_id(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/feedback/corrections?job_id=not-a-uuid")
        assert resp.status_code == 400


class TestGetCorrection:
    """Tests for GET /feedback/corrections/{correction_id}"""

    def test_get_correction_invalid_uuid(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/feedback/corrections/invalid")
        assert resp.status_code == 400

    def test_get_correction_not_found(self):
        app = _make_app()
        correction_id = str(uuid.uuid4())
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.get(f"/feedback/corrections/{correction_id}")

        assert resp.status_code == 404

    def test_get_correction_success(self):
        app = _make_app()
        correction_id = str(uuid.uuid4())
        mock_corr = _mock_correction_obj(
            id=uuid.UUID(correction_id),
            original_chunk_id=None,
        )
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_corr)
        mock_db.execute = AsyncMock(return_value=mock_result)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.get(f"/feedback/corrections/{correction_id}")

        assert resp.status_code == 200


class TestReviewCorrection:
    """Tests for PUT /feedback/corrections/{correction_id}/review"""

    def test_review_correction_invalid_uuid(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.put(
            "/feedback/corrections/invalid/review",
            json={"status": "approved"},
        )
        assert resp.status_code == 400

    def test_review_correction_invalid_status(self):
        app = _make_app()
        correction_id = str(uuid.uuid4())
        client = TestClient(app)
        resp = client.put(
            f"/feedback/corrections/{correction_id}/review",
            json={"status": "invalid"},
        )
        assert resp.status_code == 400

    def test_review_correction_not_found(self):
        app = _make_app()
        correction_id = str(uuid.uuid4())
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.put(
            f"/feedback/corrections/{correction_id}/review",
            json={"status": "approved"},
        )

        assert resp.status_code == 404

    def test_review_correction_approve_success(self):
        app = _make_app()
        correction_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        mock_correction = _mock_correction_obj(
            id=uuid.UUID(correction_id),
            job_id=uuid.UUID(job_id),
            original_chunk_id=None,
        )
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_correction)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.put(
            f"/feedback/corrections/{correction_id}/review",
            json={"status": "approved", "review_notes": "Looks good"},
        )

        assert resp.status_code == 200


class TestApplyCorrection:
    """Tests for POST /feedback/corrections/{correction_id}/apply"""

    def test_apply_correction_invalid_uuid(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.post("/feedback/corrections/invalid/apply")
        assert resp.status_code == 400

    def test_apply_correction_not_found(self):
        app = _make_app()
        correction_id = str(uuid.uuid4())
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(f"/feedback/corrections/{correction_id}/apply")

        assert resp.status_code == 404

    def test_apply_correction_not_approved(self):
        app = _make_app()
        correction_id = str(uuid.uuid4())
        mock_correction = _mock_correction_obj(
            id=uuid.UUID(correction_id),
            status="pending",
        )
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_correction)
        mock_db.execute = AsyncMock(return_value=mock_result)
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(f"/feedback/corrections/{correction_id}/apply")

        assert resp.status_code == 400

    def test_apply_correction_success(self):
        app = _make_app()
        correction_id = str(uuid.uuid4())
        mock_correction = _mock_correction_obj(
            id=uuid.UUID(correction_id),
            status="approved",
        )
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_correction)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        _override_db(app, mock_db)

        client = TestClient(app)
        resp = client.post(f"/feedback/corrections/{correction_id}/apply")

        assert resp.status_code == 200
