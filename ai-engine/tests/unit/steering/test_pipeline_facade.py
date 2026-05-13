"""Tests for the SteeringPipeline facade exposed by ``steering.pipeline``.

These pin down the contract that ``agents.logic_translator.steering_tools``
relies on (the ImportError that previously required ``--admin`` to merge PRs).
"""

from __future__ import annotations

import json

import pytest

from steering import (
    SteeringPipeline,
    SteeringPipelineConfig,
    configure_steering_pipeline,
    get_steering_pipeline,
    reset_steering_pipeline,
)


@pytest.fixture(autouse=True)
def _reset_global_pipeline():
    """Ensure each test gets a fresh global pipeline."""
    reset_steering_pipeline()
    yield
    reset_steering_pipeline()


class TestSteeringPipelineConfig:
    def test_defaults_match_steering_tools_contract(self):
        """``configure_steering`` builds a config with these defaults."""
        cfg = SteeringPipelineConfig()
        assert cfg.steering_scale == 2.0
        assert cfg.inference_backend == "openai_compatible"
        assert cfg.suppression_targets == [
            "java_forge_suppress",
            "java_class_suppress",
        ]
        assert cfg.sae_endpoint is None
        assert cfg.sae_api_key is None
        assert cfg.inference_endpoint is None

    def test_kwargs_propagate(self):
        cfg = SteeringPipelineConfig(
            sae_endpoint="https://sae.example/v1",
            sae_api_key="k",
            steering_scale=0.5,
            suppression_targets=["only_one"],
            inference_backend="vllm",
            inference_endpoint="http://vllm.local",
        )
        assert cfg.sae_endpoint == "https://sae.example/v1"
        assert cfg.sae_api_key == "k"
        assert cfg.steering_scale == 0.5
        assert cfg.suppression_targets == ["only_one"]
        assert cfg.inference_backend == "vllm"
        assert cfg.inference_endpoint == "http://vllm.local"


class TestSteeringPipeline:
    def test_starts_disabled(self):
        pipeline = SteeringPipeline()
        assert pipeline._steering_enabled is False
        assert pipeline.is_enabled() is False

    def test_enable_and_disable_toggle_flag(self):
        pipeline = SteeringPipeline()
        pipeline.enable_steering()
        assert pipeline._steering_enabled is True
        assert pipeline.is_enabled() is True
        pipeline.disable_steering()
        assert pipeline._steering_enabled is False

    def test_record_generation_increments_counters(self):
        pipeline = SteeringPipeline()
        pipeline.record_generation(steering_applied=False)
        pipeline.record_generation(steering_applied=True)
        pipeline.record_generation(steering_applied=True)
        stats = pipeline.get_stats()
        assert stats["generations"] == 3
        assert stats["steering_applications"] == 2

    def test_record_features_accumulates(self):
        pipeline = SteeringPipeline()
        pipeline.record_features([1, 2])
        pipeline.record_features([3])
        assert pipeline.get_stats()["features_tracked"] == [1, 2, 3]

    def test_get_stats_includes_config_summary(self):
        cfg = SteeringPipelineConfig(
            steering_scale=1.25,
            suppression_targets=["a", "b"],
            inference_backend="sglang",
        )
        pipeline = SteeringPipeline(config=cfg)
        stats = pipeline.get_stats()
        assert stats["config"] == {
            "steering_scale": 1.25,
            "suppression_targets": ["a", "b"],
            "inference_backend": "sglang",
        }

    def test_get_stats_returns_independent_copy(self):
        pipeline = SteeringPipeline()
        pipeline.record_features([42])
        stats = pipeline.get_stats()
        stats["features_tracked"].append(999)
        # Mutating the snapshot must not affect the pipeline
        assert pipeline.get_stats()["features_tracked"] == [42]

    def test_reset_stats_zeroes_counters(self):
        pipeline = SteeringPipeline()
        pipeline.record_generation(steering_applied=True)
        pipeline.record_features([7])
        pipeline.reset_stats()
        stats = pipeline.get_stats()
        assert stats["generations"] == 0
        assert stats["steering_applications"] == 0
        assert stats["features_tracked"] == []

    def test_get_stats_is_json_serialisable(self):
        """``SteeringTools.get_steering_stats`` json-encodes the dict."""
        pipeline = SteeringPipeline(config=SteeringPipelineConfig())
        pipeline.record_generation(steering_applied=True)
        json.dumps(pipeline.get_stats())  # must not raise


class TestGlobalPipelineAccessors:
    def test_get_steering_pipeline_returns_singleton(self):
        first = get_steering_pipeline()
        second = get_steering_pipeline()
        assert first is second

    def test_configure_steering_pipeline_replaces_singleton(self):
        first = get_steering_pipeline()
        cfg = SteeringPipelineConfig(steering_scale=3.0)
        replacement = configure_steering_pipeline(cfg)
        assert replacement is not first
        assert get_steering_pipeline() is replacement
        assert replacement.config.steering_scale == 3.0

    def test_reset_steering_pipeline_creates_fresh_instance_on_next_get(self):
        first = get_steering_pipeline()
        reset_steering_pipeline()
        second = get_steering_pipeline()
        assert second is not first
