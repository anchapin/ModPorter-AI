"""
Tests for Build Performance API - src/api/build_performance.py
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.build_performance import router


def _make_app():
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_build(**overrides):
    build = MagicMock()
    build.build_id = overrides.get("build_id", "bld-001")
    build.conversion_id = overrides.get("conversion_id", "conv-001")
    build.created_at = overrides.get("created_at", datetime.now(timezone.utc))
    return build


def _full_response(**overrides):
    return {
        "build_id": overrides.get("build_id", "bld-001"),
        "conversion_id": overrides.get("conversion_id", "conv-001"),
        "status": overrides.get("status", "running"),
        "total_duration_ms": overrides.get("total_duration_ms", None),
        "performance_score": overrides.get("performance_score", None),
        "stages": overrides.get("stages", []),
        "resource_usage": overrides.get("resource_usage", None),
        "metadata": overrides.get("metadata", {}),
        "created_at": overrides.get("created_at", datetime.now(timezone.utc).isoformat()),
        "completed_at": overrides.get("completed_at", None),
    }


def _full_snapshot(**overrides):
    return {
        "build_id": overrides.get("build_id", "bld-001"),
        "conversion_id": overrides.get("conversion_id", "conv-001"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "current_stage": overrides.get("current_stage", "analysis"),
        "progress_percent": overrides.get("progress_percent", 0.5),
        "elapsed_ms": overrides.get("elapsed_ms", 1200.0),
        "estimated_remaining_ms": overrides.get("estimated_remaining_ms", None),
        "resource_usage": overrides.get("resource_usage", None),
    }


def _full_summary(**overrides):
    return {
        "build_id": overrides.get("build_id", "bld-001"),
        "conversion_id": overrides.get("conversion_id", "conv-001"),
        "total_duration_ms": overrides.get("total_duration_ms", 5000.0),
        "stage_count": overrides.get("stage_count", 5),
        "failed_stages": overrides.get("failed_stages", 0),
        "performance_score": overrides.get("performance_score", 0.9),
        "status": overrides.get("status", "completed"),
    }


def _full_stats(**overrides):
    return {
        "total_builds": overrides.get("total_builds", 10),
        "completed_builds": overrides.get("completed_builds", 8),
        "failed_builds": overrides.get("failed_builds", 2),
        "average_duration_ms": overrides.get("average_duration_ms", 4500.0),
        "median_duration_ms": overrides.get("median_duration_ms", 4200.0),
        "p95_duration_ms": overrides.get("p95_duration_ms", 8000.0),
        "p99_duration_ms": overrides.get("p99_duration_ms", 9500.0),
        "average_performance_score": overrides.get("average_performance_score", 0.85),
        "stage_stats": overrides.get("stage_stats", {}),
    }


class TestStartPerformanceTracking:
    def test_start_success(self):
        app = _make_app()
        build = _mock_build()

        with patch("api.build_performance.start_build_performance_tracking", return_value=build):
            client = TestClient(app)
            resp = client.post(
                "/start",
                json={
                    "conversion_id": "conv-001",
                    "build_type": "standard",
                    "target_version": "1.20.0",
                    "mod_size_bytes": 1024,
                },
            )

        assert resp.status_code == 201
        assert resp.json()["build_id"] == "bld-001"

    def test_start_failure_returns_500(self):
        app = _make_app()

        with patch(
            "api.build_performance.start_build_performance_tracking",
            side_effect=Exception("db err"),
        ):
            client = TestClient(app)
            resp = client.post(
                "/start",
                json={
                    "conversion_id": "conv-001",
                    "build_type": "standard",
                    "target_version": "1.20.0",
                    "mod_size_bytes": 1024,
                },
            )

        assert resp.status_code == 500


class TestUpdateStage:
    def test_update_stage_success(self):
        app = _make_app()
        mock_svc = MagicMock()
        mock_svc.update_stage.return_value = _mock_build()
        mock_svc.get_response.return_value = _full_response()

        with patch("api.build_performance.get_build_performance_service", return_value=mock_svc):
            client = TestClient(app)
            resp = client.post(
                "/bld-001/stage",
                json={"stage_name": "java_analysis", "status": "running"},
            )

        assert resp.status_code == 200

    def test_update_stage_not_found(self):
        app = _make_app()
        mock_svc = MagicMock()
        mock_svc.update_stage.return_value = None

        with patch("api.build_performance.get_build_performance_service", return_value=mock_svc):
            client = TestClient(app)
            resp = client.post(
                "/bld-missing/stage",
                json={"stage_name": "java_analysis", "status": "running"},
            )

        assert resp.status_code == 404


class TestStartStage:
    def test_start_stage_success(self):
        app = _make_app()
        mock_svc = MagicMock()
        mock_svc.start_stage.return_value = _mock_build()
        mock_svc.get_response.return_value = _full_response()

        with patch("api.build_performance.get_build_performance_service", return_value=mock_svc):
            client = TestClient(app)
            resp = client.post("/bld-001/stage/java_analysis/start")

        assert resp.status_code == 200

    def test_start_stage_not_found(self):
        app = _make_app()
        mock_svc = MagicMock()
        mock_svc.start_stage.return_value = None

        with patch("api.build_performance.get_build_performance_service", return_value=mock_svc):
            client = TestClient(app)
            resp = client.post("/bld-missing/stage/java_analysis/start")

        assert resp.status_code == 404


class TestCompleteStage:
    def test_complete_stage_success(self):
        app = _make_app()
        mock_svc = MagicMock()
        mock_svc.complete_stage.return_value = _mock_build()
        mock_svc.get_response.return_value = _full_response()

        with patch("api.build_performance.get_build_performance_service", return_value=mock_svc):
            client = TestClient(app)
            resp = client.post("/bld-001/stage/java_analysis/complete")

        assert resp.status_code == 200

    def test_complete_stage_failed_status(self):
        app = _make_app()
        mock_svc = MagicMock()
        mock_svc.complete_stage.return_value = _mock_build()
        mock_svc.get_response.return_value = _full_response()

        with patch("api.build_performance.get_build_performance_service", return_value=mock_svc):
            client = TestClient(app)
            resp = client.post(
                "/bld-001/stage/java_analysis/complete?status=failed&error_message=oops"
            )

        assert resp.status_code == 200

    def test_complete_stage_not_found(self):
        app = _make_app()
        mock_svc = MagicMock()
        mock_svc.complete_stage.return_value = None

        with patch("api.build_performance.get_build_performance_service", return_value=mock_svc):
            client = TestClient(app)
            resp = client.post("/bld-missing/stage/java_analysis/complete")

        assert resp.status_code == 404


class TestEndPerformanceTracking:
    def test_end_success(self):
        app = _make_app()
        mock_svc = MagicMock()
        mock_svc.get_response.return_value = _full_response()

        with (
            patch(
                "api.build_performance.end_build_performance_tracking",
                return_value=_mock_build(),
            ),
            patch("api.build_performance.get_build_performance_service", return_value=mock_svc),
        ):
            client = TestClient(app)
            resp = client.post("/bld-001/end", json={"status": "completed"})

        assert resp.status_code == 200

    def test_end_not_found(self):
        app = _make_app()

        with patch("api.build_performance.end_build_performance_tracking", return_value=None):
            client = TestClient(app)
            resp = client.post("/bld-missing/end", json={"status": "failed"})

        assert resp.status_code == 404


class TestGetBuildPerformance:
    def test_get_success(self):
        app = _make_app()

        with patch("api.build_performance.get_build_performance", return_value=_full_response()):
            client = TestClient(app)
            resp = client.get("/bld-001")

        assert resp.status_code == 200

    def test_get_not_found(self):
        app = _make_app()

        with patch("api.build_performance.get_build_performance", return_value=None):
            client = TestClient(app)
            resp = client.get("/bld-missing")

        assert resp.status_code == 404


class TestGetBuildSnapshot:
    def test_snapshot_success(self):
        app = _make_app()

        with patch(
            "api.build_performance.get_build_performance_snapshot",
            return_value=_full_snapshot(),
        ):
            client = TestClient(app)
            resp = client.get("/bld-001/snapshot")

        assert resp.status_code == 200

    def test_snapshot_not_found(self):
        app = _make_app()

        with patch("api.build_performance.get_build_performance_snapshot", return_value=None):
            client = TestClient(app)
            resp = client.get("/bld-missing/snapshot")

        assert resp.status_code == 404


class TestGetBuildSummary:
    def test_summary_success(self):
        app = _make_app()
        mock_svc = MagicMock()
        mock_svc.get_summary.return_value = _full_summary()

        with patch("api.build_performance.get_build_performance_service", return_value=mock_svc):
            client = TestClient(app)
            resp = client.get("/bld-001/summary")

        assert resp.status_code == 200

    def test_summary_not_found(self):
        app = _make_app()
        mock_svc = MagicMock()
        mock_svc.get_summary.return_value = None

        with patch("api.build_performance.get_build_performance_service", return_value=mock_svc):
            client = TestClient(app)
            resp = client.get("/bld-missing/summary")

        assert resp.status_code == 404


class TestGetPerformanceStats:
    def test_stats_default(self):
        app = _make_app()

        with patch("api.build_performance.get_build_performance_stats", return_value=_full_stats()):
            client = TestClient(app)
            resp = client.get("/stats")

        assert resp.status_code == 200
        assert resp.json()["total_builds"] == 10

    def test_stats_with_conversion_filter(self):
        app = _make_app()

        with patch("api.build_performance.get_build_performance_stats", return_value=_full_stats()):
            client = TestClient(app)
            resp = client.get("/stats?conversion_id=conv-001&limit=50")

        assert resp.status_code == 200


class TestGetAvailableStages:
    def test_stages_list(self):
        app = _make_app()
        client = TestClient(app)
        resp = client.get("/stages")

        assert resp.status_code == 200
        stages = resp.json()
        assert isinstance(stages, list)
        assert len(stages) > 0


class TestListBuilds:
    def test_list_builds_default(self):
        app = _make_app()
        mock_svc = MagicMock()
        mock_svc.get_stats.return_value = None

        with patch("api.build_performance.get_build_performance_service", return_value=mock_svc):
            client = TestClient(app)
            resp = client.get("/")

        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
