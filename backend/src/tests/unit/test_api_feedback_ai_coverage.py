"""
Tests for uncovered AI/RL endpoints and correction listing paths in src/api/feedback.py.

Covers: trigger_rl_training happy/error, agent performance endpoints with mocked
optimizer, correction listing with filters, and submit_correction chunk_id paths.
"""

import sys
import types
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


def _override_db(app, mock_db):
    async def _get_db():
        return mock_db

    from db.base import get_db

    app.dependency_overrides[get_db] = _get_db
    return app


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


class TestTriggerRLTrainingHappyPath:
    """Covers lines 273-278 (training data found, training succeeds)."""

    def test_trigger_rl_training_with_data(self):
        mock_tm = types.ModuleType("training_manager")
        mock_tm.fetch_training_data_from_backend = AsyncMock(
            return_value=[{"id": "1"}, {"id": "2"}]
        )
        mock_tm.train_model_with_feedback = AsyncMock(return_value={"accuracy": 0.95, "loss": 0.05})

        app = _make_app()
        with patch.dict(sys.modules, {"training_manager": mock_tm}):
            client = TestClient(app)
            resp = client.post("/ai/training/trigger")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["training_data_count"] == 2
        assert body["training_result"]["accuracy"] == 0.95

    def test_trigger_rl_training_no_data(self):
        mock_tm = types.ModuleType("training_manager")
        mock_tm.fetch_training_data_from_backend = AsyncMock(return_value=[])
        mock_tm.train_model_with_feedback = AsyncMock(return_value={})

        app = _make_app()
        with patch.dict(sys.modules, {"training_manager": mock_tm}):
            client = TestClient(app)
            resp = client.post("/ai/training/trigger")

        assert resp.status_code == 200
        assert resp.json()["status"] == "warning"

    def test_trigger_rl_training_generic_exception(self):
        """Covers lines 290-294."""
        mock_tm = types.ModuleType("training_manager")
        mock_tm.fetch_training_data_from_backend = AsyncMock(
            side_effect=RuntimeError("training crashed")
        )
        mock_tm.train_model_with_feedback = AsyncMock(return_value={})

        app = _make_app()
        with patch.dict(sys.modules, {"training_manager": mock_tm}):
            client = TestClient(app)
            resp = client.post("/ai/training/trigger")

        assert resp.status_code == 500


class TestAgentPerformanceWithOptimizer:
    """Covers lines 308, 318-323, 327-329 — agent performance with mocked optimizer."""

    def test_get_agent_performance_success(self):
        mock_rl = types.ModuleType("rl")
        mock_optimizer = MagicMock()
        mock_optimizer.get_system_wide_metrics.return_value = {
            "total_agents": 5,
            "avg_accuracy": 0.85,
        }
        mock_rl.agent_optimizer = types.SimpleNamespace(
            create_agent_optimizer=MagicMock(return_value=mock_optimizer)
        )

        app = _make_app()
        with patch.dict(
            sys.modules, {"rl": mock_rl, "rl.agent_optimizer": mock_rl.agent_optimizer}
        ):
            client = TestClient(app)
            resp = client.get("/ai/performance/agents")

        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        assert resp.json()["metrics"]["total_agents"] == 5

    def test_get_agent_performance_generic_exception(self):
        """Covers lines 327-329."""
        mock_rl = types.ModuleType("rl")
        mock_optimizer = MagicMock()
        mock_optimizer.get_system_wide_metrics.side_effect = RuntimeError("metrics failed")
        mock_rl.agent_optimizer = types.SimpleNamespace(
            create_agent_optimizer=MagicMock(return_value=mock_optimizer)
        )

        app = _make_app()
        with patch.dict(
            sys.modules, {"rl": mock_rl, "rl.agent_optimizer": mock_rl.agent_optimizer}
        ):
            client = TestClient(app)
            resp = client.get("/ai/performance/agents")

        assert resp.status_code == 500


class TestSpecificAgentPerformanceWithOptimizer:
    """Covers lines 339, 347-390 — specific agent performance with optimizer."""

    def test_get_specific_agent_with_history(self):
        mock_metric = MagicMock()
        mock_metric.__dict__ = {"accuracy": 0.92, "latency_ms": 150}

        mock_optimizer = MagicMock()
        mock_optimizer.performance_history = {"java_analyzer": [mock_metric]}

        mock_rl = types.ModuleType("rl")
        mock_rl.agent_optimizer = types.SimpleNamespace(
            create_agent_optimizer=MagicMock(return_value=mock_optimizer)
        )

        app = _make_app()
        with patch.dict(
            sys.modules, {"rl": mock_rl, "rl.agent_optimizer": mock_rl.agent_optimizer}
        ):
            client = TestClient(app)
            resp = client.get("/ai/performance/agents/java_analyzer")

        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_get_specific_agent_no_history(self):
        mock_optimizer = MagicMock()
        mock_optimizer.performance_history = {"java_analyzer": []}

        mock_rl = types.ModuleType("rl")
        mock_rl.agent_optimizer = types.SimpleNamespace(
            create_agent_optimizer=MagicMock(return_value=mock_optimizer)
        )

        app = _make_app()
        with patch.dict(
            sys.modules, {"rl": mock_rl, "rl.agent_optimizer": mock_rl.agent_optimizer}
        ):
            client = TestClient(app)
            resp = client.get("/ai/performance/agents/java_analyzer")

        assert resp.status_code == 200
        assert resp.json()["status"] == "warning"

    def test_get_specific_agent_invalid_type(self):
        mock_optimizer = MagicMock()
        mock_optimizer.performance_history = {}

        mock_rl = types.ModuleType("rl")
        mock_rl.agent_optimizer = types.SimpleNamespace(
            create_agent_optimizer=MagicMock(return_value=mock_optimizer)
        )

        app = _make_app()
        with patch.dict(
            sys.modules, {"rl": mock_rl, "rl.agent_optimizer": mock_rl.agent_optimizer}
        ):
            client = TestClient(app)
            resp = client.get("/ai/performance/agents/invalid_agent")

        assert resp.status_code == 400

    def test_get_specific_agent_metric_dict_fallback(self):
        mock_metric = "not_an_object"
        mock_optimizer = MagicMock()
        mock_optimizer.performance_history = {"java_analyzer": [mock_metric]}

        mock_rl = types.ModuleType("rl")
        mock_rl.agent_optimizer = types.SimpleNamespace(
            create_agent_optimizer=MagicMock(return_value=mock_optimizer)
        )

        app = _make_app()
        with patch.dict(
            sys.modules, {"rl": mock_rl, "rl.agent_optimizer": mock_rl.agent_optimizer}
        ):
            client = TestClient(app)
            resp = client.get("/ai/performance/agents/java_analyzer")

        assert resp.status_code == 200
        assert resp.json()["metrics"] == {}

    def test_get_specific_agent_generic_exception(self):
        mock_rl = types.ModuleType("rl")
        mock_optimizer = MagicMock()
        mock_optimizer.performance_history = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        create_fn = MagicMock(return_value=mock_optimizer)
        mock_rl.agent_optimizer = types.SimpleNamespace(create_agent_optimizer=create_fn)

        app = _make_app()
        with patch.dict(
            sys.modules, {"rl": mock_rl, "rl.agent_optimizer": mock_rl.agent_optimizer}
        ):
            client = TestClient(app)
            resp = client.get("/ai/performance/agents/java_analyzer")

        assert resp.status_code == 500


class TestCompareAgentPerformanceWithOptimizer:
    """Covers lines 437-445, 449-453 — compare with mocked optimizer."""

    def test_compare_agents_success(self):
        class Report:
            java_analyzer_score = 0.9
            asset_converter_score = 0.85

        mock_optimizer = MagicMock()
        mock_optimizer.compare_agents.return_value = Report()

        mock_rl = types.ModuleType("rl")
        mock_rl.agent_optimizer = types.SimpleNamespace(
            create_agent_optimizer=MagicMock(return_value=mock_optimizer)
        )

        app = _make_app()
        with patch.dict(
            sys.modules, {"rl": mock_rl, "rl.agent_optimizer": mock_rl.agent_optimizer}
        ):
            client = TestClient(app)
            resp = client.post(
                "/ai/performance/compare",
                json=["java_analyzer", "asset_converter"],
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_compare_agents_report_no_dict(self):
        mock_report = "plain_string"
        mock_optimizer = MagicMock()
        mock_optimizer.compare_agents.return_value = mock_report

        mock_rl = types.ModuleType("rl")
        mock_rl.agent_optimizer = types.SimpleNamespace(
            create_agent_optimizer=MagicMock(return_value=mock_optimizer)
        )

        app = _make_app()
        with patch.dict(
            sys.modules, {"rl": mock_rl, "rl.agent_optimizer": mock_rl.agent_optimizer}
        ):
            client = TestClient(app)
            resp = client.post(
                "/ai/performance/compare",
                json=["java_analyzer", "asset_converter"],
            )

        assert resp.status_code == 200
        assert resp.json()["comparison_report"] == {}

    def test_compare_agents_generic_exception(self):
        """Covers lines 449-453."""
        mock_optimizer = MagicMock()
        mock_optimizer.compare_agents.side_effect = RuntimeError("comparison failed")

        mock_rl = types.ModuleType("rl")
        mock_rl.agent_optimizer = types.SimpleNamespace(
            create_agent_optimizer=MagicMock(return_value=mock_optimizer)
        )

        app = _make_app()
        with patch.dict(
            sys.modules, {"rl": mock_rl, "rl.agent_optimizer": mock_rl.agent_optimizer}
        ):
            client = TestClient(app)
            resp = client.post(
                "/ai/performance/compare",
                json=["java_analyzer", "asset_converter"],
            )

        assert resp.status_code == 500


class TestSubmitCorrectionChunkId:
    """Covers lines 549-552 — original_chunk_id invalid UUID → pass."""

    def test_submit_correction_with_invalid_chunk_id_passes(self):
        job_id = str(uuid.uuid4())
        corr_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        mock_correction = _mock_correction_obj(
            id=corr_id,
            job_id=uuid.UUID(job_id),
            submitted_at=now,
            original_chunk_id=None,
        )
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        app = _make_app()
        with patch("api.feedback.crud") as mock_crud:
            mock_crud.get_job = AsyncMock(return_value=MagicMock())
            _override_db(app, mock_db)

            with patch("api.feedback.CorrectionSubmission", return_value=mock_correction):
                client = TestClient(app)
                resp = client.post(
                    "/feedback/corrections",
                    json={
                        "job_id": job_id,
                        "original_output": "x",
                        "corrected_output": "y",
                        "original_chunk_id": "not-a-valid-uuid",
                    },
                )

        assert resp.status_code == 201


class TestListCorrectionsWithFilters:
    """Covers lines 606-607, 614-643 — full listing with job_id, status, user_id filters."""

    def _make_mock_db(self, corrections=None, total=0):
        mock_db = AsyncMock()
        mock_scalar_result = MagicMock()
        mock_scalar_result.scalars.return_value.all.return_value = corrections or []
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = total
        mock_db.execute = AsyncMock(side_effect=[mock_scalar_result, mock_count_result])
        return mock_db

    def test_list_corrections_with_job_id_filter(self):
        job_id = str(uuid.uuid4())
        correction = _mock_correction_obj(
            job_id=uuid.UUID(job_id),
            original_chunk_id=None,
        )
        mock_db = self._make_mock_db(corrections=[correction], total=1)

        app = _make_app()
        _override_db(app, mock_db)
        client = TestClient(app)
        resp = client.get(f"/feedback/corrections?job_id={job_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_list_corrections_with_status_filter(self):
        correction = _mock_correction_obj(
            status="approved",
            original_chunk_id=None,
        )
        mock_db = self._make_mock_db(corrections=[correction], total=1)

        app = _make_app()
        _override_db(app, mock_db)
        client = TestClient(app)
        resp = client.get("/feedback/corrections?status=approved")

        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_corrections_with_user_id_filter(self):
        correction = _mock_correction_obj(
            user_id="user123",
            original_chunk_id=None,
        )
        mock_db = self._make_mock_db(corrections=[correction], total=1)

        app = _make_app()
        _override_db(app, mock_db)
        client = TestClient(app)
        resp = client.get("/feedback/corrections?user_id=user123")

        assert resp.status_code == 200

    def test_list_corrections_with_all_filters(self):
        job_id = str(uuid.uuid4())
        correction = _mock_correction_obj(
            job_id=uuid.UUID(job_id),
            status="pending",
            user_id="user456",
            original_chunk_id=None,
        )
        mock_db = self._make_mock_db(corrections=[correction], total=1)

        app = _make_app()
        _override_db(app, mock_db)
        client = TestClient(app)
        resp = client.get(f"/feedback/corrections?job_id={job_id}&status=pending&user_id=user456")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"][0]["status"] == "pending"

    def test_list_corrections_empty_results(self):
        mock_db = self._make_mock_db(corrections=[], total=0)

        app = _make_app()
        _override_db(app, mock_db)
        client = TestClient(app)
        resp = client.get("/feedback/corrections")

        assert resp.status_code == 200
        assert resp.json()["data"] == []
        assert resp.json()["total"] == 0

    def test_list_corrections_with_chunk_id(self):
        correction = _mock_correction_obj(
            original_chunk_id=uuid.uuid4(),
        )
        mock_db = self._make_mock_db(corrections=[correction], total=1)

        app = _make_app()
        _override_db(app, mock_db)
        client = TestClient(app)
        resp = client.get("/feedback/corrections")

        assert resp.status_code == 200
        assert resp.json()["data"][0]["original_chunk_id"] is not None
