"""
Tests for mode_classification.py API endpoints - classify, modes, pipeline, settings.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.models.conversion_mode import (
    ConversionMode,
    ModFeatures,
    ComplexFeature,
    ModeClassificationResult,
    ClassificationConfidence,
    ConversionSettings,
    ModeSpecificPipelineConfig,
)
from api.mode_classification import router, get_mode_classifier

app = FastAPI()
app.include_router(router)


def _make_features():
    return ModFeatures(
        total_classes=3,
        total_dependencies=1,
        has_items=True,
        has_blocks=True,
        complex_features=[],
    )


def _make_result(mode=ConversionMode.SIMPLE):
    return ModeClassificationResult(
        mode=mode,
        confidence=0.9,
        features=_make_features(),
        alternative_modes=[ClassificationConfidence(mode=ConversionMode.STANDARD, confidence=0.3)],
        convertible_percentage=95.0,
        estimated_time_seconds=30,
        automation_level=99,
    )


def _make_settings(mode=ConversionMode.SIMPLE):
    return ConversionSettings(mode=mode, detail_level="standard", validation_level="standard")


@pytest.fixture
def mock_classifier():
    clf = MagicMock()
    clf.classify = AsyncMock(return_value=_make_result())
    clf.get_recommended_settings = MagicMock(return_value=_make_settings())
    clf.get_pipeline_config = MagicMock(
        return_value=ModeSpecificPipelineConfig(
            mode=ConversionMode.SIMPLE,
            pipeline_name="simple-pipeline",
            steps=["parse", "extract", "translate", "validate", "export"],
            estimated_success_rate=0.99,
        )
    )
    return clf


@pytest.fixture
def client(mock_classifier):
    app.dependency_overrides[get_mode_classifier] = lambda: mock_classifier
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestClassifyMod:
    def test_classify_success(self, client, mock_classifier):
        resp = client.post(
            "/api/v1/classify",
            files={"file": ("test.jar", b"fake jar content", "application/java-archive")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["mode"] == "simple"
        assert data["confidence"] == 0.9
        assert data["convertible_percentage"] == 95.0

    def test_classify_value_error(self, client, mock_classifier):
        mock_classifier.classify = AsyncMock(side_effect=ValueError("bad input"))
        resp = client.post(
            "/api/v1/classify",
            files={"file": ("bad.jar", b"", "application/java-archive")},
        )
        assert resp.status_code == 400
        assert "bad input" in resp.json()["detail"]

    def test_classify_unexpected_error(self, client, mock_classifier):
        mock_classifier.classify = AsyncMock(side_effect=RuntimeError("boom"))
        resp = client.post(
            "/api/v1/classify",
            files={"file": ("test.jar", b"x", "application/java-archive")},
        )
        assert resp.status_code == 500
        assert "unexpectedly" in resp.json()["detail"].lower()

    def test_classify_with_warnings(self, client, mock_classifier):
        features = ModFeatures(
            total_classes=10,
            complex_features=[
                ComplexFeature(
                    feature_type="asm",
                    description="Uses ASM transformations",
                    impact="warning",
                )
            ],
        )
        result = _make_result()
        result.features = features
        mock_classifier.classify = AsyncMock(return_value=result)
        resp = client.post(
            "/api/v1/classify",
            files={"file": ("test.jar", b"x", "application/java-archive")},
        )
        assert resp.status_code == 201
        assert "Uses ASM transformations" in resp.json()["warnings"]


class TestClassifyFromFeatures:
    def test_classify_from_features_success(self, client, mock_classifier):
        resp = client.post(
            "/api/v1/classify/features",
            json={
                "features": {
                    "total_classes": 5,
                    "total_dependencies": 2,
                    "has_items": True,
                }
            },
        )
        assert resp.status_code == 201
        assert resp.json()["mode"] == "simple"

    def test_classify_from_features_missing_features(self, client, mock_classifier):
        resp = client.post(
            "/api/v1/classify/features",
            json={},
        )
        assert resp.status_code == 400

    def test_classify_from_features_error(self, client, mock_classifier):
        mock_classifier.classify = AsyncMock(side_effect=RuntimeError("fail"))
        resp = client.post(
            "/api/v1/classify/features",
            json={
                "features": {
                    "total_classes": 5,
                }
            },
        )
        assert resp.status_code == 500


class TestGetModes:
    def test_get_modes(self, client):
        resp = client.get("/api/v1/classify/modes")
        assert resp.status_code == 200
        modes = resp.json()
        assert len(modes) == 4
        mode_values = [m["mode"] for m in modes]
        assert "simple" in mode_values
        assert "standard" in mode_values
        assert "complex" in mode_values
        assert "expert" in mode_values

    def test_modes_have_required_fields(self, client):
        resp = client.get("/api/v1/classify/modes")
        modes = resp.json()
        for m in modes:
            assert "mode" in m
            assert "name" in m
            assert "description" in m
            assert "automation_level" in m
            assert "features" in m


class TestGetPipeline:
    def test_get_pipeline_simple(self, client, mock_classifier):
        resp = client.get("/api/v1/classify/pipeline/simple")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline_name"] == "simple-pipeline"

    def test_get_pipeline_complex(self, client, mock_classifier):
        mock_classifier.get_pipeline_config.return_value = ModeSpecificPipelineConfig(
            mode=ConversionMode.COMPLEX,
            pipeline_name="complex-pipeline",
            steps=["parse", "extract"],
            estimated_success_rate=0.85,
            requires_human_review=True,
        )
        resp = client.get("/api/v1/classify/pipeline/complex")
        assert resp.status_code == 200
        assert resp.json()["requires_human_review"] is True

    def test_get_pipeline_invalid_mode(self, client, mock_classifier):
        resp = client.get("/api/v1/classify/pipeline/invalid")
        assert resp.status_code == 422


class TestGetSettings:
    def test_get_settings_simple(self, client, mock_classifier):
        resp = client.get("/api/v1/classify/settings/simple")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "simple"
        assert "detail_level" in data

    def test_get_settings_expert(self, client, mock_classifier):
        mock_classifier.get_recommended_settings.return_value = ConversionSettings(
            mode=ConversionMode.EXPERT,
            detail_level="detailed",
            validation_level="strict",
            timeout_seconds=1200,
        )
        resp = client.get("/api/v1/classify/settings/expert")
        assert resp.status_code == 200
        assert resp.json()["detail_level"] == "detailed"
