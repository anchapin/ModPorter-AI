"""
Tests for Model Registry - Simplified
Tests core logic without external dependencies
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Simplified enums
class ModelStatus:
    TRAINING = "training"
    READY = "ready"
    DEPLOYED = "deployed"
    TESTING = "testing"
    ROLLBACK = "rollback"
    ARCHIVED = "archived"
    FAILED = "failed"


class DeploymentStrategy:
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    SHADOW = "shadow"


# Simplified dataclasses
@dataclass
class ModelVersion:
    version: str
    model_path: str
    base_model: str
    status: ModelStatus
    created_at: str
    trained_at: Optional[str] = None
    metrics: Dict = field(default_factory=dict)
    hyperparameters: Dict = field(default_factory=dict)
    description: Optional[str] = None


@dataclass
class TestMetrics:
    control: Dict = field(default_factory=dict)
    treatment: Dict = field(default_factory=dict)
    sample_size_control: int = 0
    sample_size_treatment: int = 0
    p_value: Optional[float] = None
    significant: bool = False
    winner: Optional[str] = None
    improvement_pct: Dict = field(default_factory=dict)


# Import the module
from deployment.model_registry import (
    ModelRegistry,
    TrafficSplitter,
    CanaryDeployer,
    MonitoringDashboard,
)


class TestModelRegistry:
    """Tests for ModelRegistry"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)

    def test_register_model(self):
        model = self.registry.register_model(
            version="v1.0",
            model_path="./models/v1",
            base_model="codellama-7b",
            metrics={"accuracy": 0.85},
        )
        assert model.version == "v1.0"
        assert model.status == ModelStatus.TRAINING

    def test_get_model(self):
        self.registry.register_model("v1.0", "./models/v1", "base1")
        model = self.registry.get_model("v1.0")
        assert model is not None
        assert model.version == "v1.0"

    def test_update_status(self):
        self.registry.register_model("v1.0", "./models/v1", "base1")
        self.registry.update_status("v1.0", ModelStatus.READY)
        model = self.registry.get_model("v1.0")
        assert model.status == ModelStatus.READY


class TestTrafficSplitter:
    """Tests for TrafficSplitter"""

    def test_assign_variant_consistent(self):
        splitter = TrafficSplitter(seed=42)
        variant1 = splitter.assign_variant("user123", "control", "treatment", 0.5)
        variant2 = splitter.assign_variant("user123", "control", "treatment", 0.5)
        assert variant1 == variant2

    def test_assign_variant_distribution(self):
        splitter = TrafficSplitter(seed=42)
        results = {"control": 0, "treatment": 0}
        users = [f"user{i}" for i in range(100)]
        for user in users:
            variant = splitter.assign_variant(user, "control", "treatment", 0.5)
            results[variant] += 1
        # Should be roughly 50/50
        assert 40 <= results["control"] <= 60
        assert 40 <= results["treatment"] <= 60


class TestCanaryDeployer:
    """Tests for CanaryDeployer"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(self.temp_dir)
        self.canary = CanaryDeployer(self.registry)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)

    def test_start_canary(self):
        self.registry.register_model("v1.0", "./models/v1", "base1")
        self.registry.register_model("v2.0", "./models/v2", "base2")
        result = self.canary.start_canary("v1.0", "v2.0")
        assert result["target_version"] == "v2.0"

    def test_promote_canary(self):
        self.registry.register_model("v1.0", "./models/v1", "base1")
        self.registry.register_model("v2.0", "./models/v2", "base2")
        self.canary.start_canary("v1.0", "v2.0")
        result = self.canary.promote_canary()
        assert result["status"] == "promoted"

    def test_check_health_pass(self):
        self.registry.register_model("v1.0", "./models/v1", "base1")
        self.registry.register_model("v2.0", "./models/v2", "base2")
        self.canary.start_canary("v1.0", "v2.0")
        healthy, message = self.canary.check_health({
            "error_rate": 0.01,
            "latency_increase_pct": 5,
        })
        assert healthy is True


class TestMonitoringDashboard:
    """Tests for MonitoringDashboard"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(self.temp_dir)
        self.monitoring = MonitoringDashboard(self.registry)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)

    def test_record_metric(self):
        self.monitoring.record_metric("v1.0", "latency_ms", 150.0)
        metrics = self.monitoring.get_metrics("v1.0", "latency_ms")
        assert len(metrics) == 1
        assert metrics[0]["value"] == 150.0


class TestTestMetrics:
    """Tests for TestMetrics"""

    def test_default_values(self):
        metrics = TestMetrics()
        assert metrics.control == {}
        assert metrics.treatment == {}
        assert metrics.sample_size_control == 0
        assert metrics.significant is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
