"""
Tests for Model Registry and Deployment Module
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Import directly
from deployment.model_registry import (
    ModelRegistry,
    ModelStatus,
    DeploymentStrategy,
    DeploymentConfig,
    ABTestConfig,
    ABTester,
    CanaryDeployer,
    MonitoringDashboard,
    TrafficSplitter,
    TestMetrics,
)


class TestModelRegistry:
    """Tests for ModelRegistry class"""

    def setup_method(self):
        """Create temporary registry directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(self.temp_dir)

    def teardown_method(self):
        """Cleanup temporary directory"""
        shutil.rmtree(self.temp_dir)

    def test_register_model(self):
        """Test model registration"""
        model = self.registry.register_model(
            version="v1.0",
            model_path="./models/v1",
            base_model="codellama-7b",
            metrics={"accuracy": 0.85},
            description="Test model",
        )

        assert model.version == "v1.0"
        assert model.status == ModelStatus.TRAINING
        assert model.metrics["accuracy"] == 0.85

    def test_get_model(self):
        """Test getting a model"""
        self.registry.register_model(
            version="v1.0",
            model_path="./models/v1",
            base_model="codellama-7b",
        )

        model = self.registry.get_model("v1.0")

        assert model is not None
        assert model.version == "v1.0"

    def test_update_status(self):
        """Test updating model status"""
        self.registry.register_model(
            version="v1.0",
            model_path="./models/v1",
            base_model="codellama-7b",
        )

        self.registry.update_status("v1.0", ModelStatus.READY)

        model = self.registry.get_model("v1.0")
        assert model.status == ModelStatus.READY
        assert model.trained_at is not None

    def test_list_models(self):
        """Test listing models"""
        self.registry.register_model("v1.0", "./models/v1", "base1")
        self.registry.register_model("v2.0", "./models/v2", "base2")

        models = self.registry.list_models()

        assert len(models) == 2

    def test_list_models_by_status(self):
        """Test filtering models by status"""
        self.registry.register_model("v1.0", "./models/v1", "base1")
        self.registry.register_model("v2.0", "./models/v2", "base2")
        self.registry.update_status("v1.0", ModelStatus.READY)

        ready_models = self.registry.list_models(status=ModelStatus.READY)

        assert len(ready_models) == 1
        assert ready_models[0].version == "v1.0"

    def test_get_latest(self):
        """Test getting latest model"""
        self.registry.register_model("v1.0", "./models/v1", "base1")
        self.registry.register_model("v2.0", "./models/v2", "base2")

        latest = self.registry.get_latest()

        assert latest.version == "v2.0"

    def test_archive_model(self):
        """Test archiving a model"""
        self.registry.register_model(
            version="v1.0",
            model_path="./models/v1",
            base_model="codellama-7b",
        )
        self.registry.update_status("v1.0", ModelStatus.READY)

        self.registry.archive_model("v1.0")

        model = self.registry.get_model("v1.0")
        assert model.status == ModelStatus.ARCHIVED


class TestTrafficSplitter:
    """Tests for TrafficSplitter class"""

    def test_assign_variant_consistent(self):
        """Test consistent variant assignment"""
        splitter = TrafficSplitter(seed=42)

        # Same user should always get same variant
        variant1 = splitter.assign_variant("user123", "control", "treatment", 0.5)
        variant2 = splitter.assign_variant("user123", "control", "treatment", 0.5)

        assert variant1 == variant2

    def test_assign_variant_distribution(self):
        """Test variant distribution"""
        splitter = TrafficSplitter(seed=42)

        results = {"control": 0, "treatment": 0}
        users = [f"user{i}" for i in range(100)]

        for user in users:
            variant = splitter.assign_variant(user, "control", "treatment", 0.5)
            results[variant] += 1

        # Should be roughly 50/50
        assert 40 <= results["control"] <= 60
        assert 40 <= results["treatment"] <= 60


class TestABTester:
    """Tests for ABTester class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(self.temp_dir)
        self.tester = ABTester(self.registry)

        # Register test models
        self.registry.register_model("v1.0", "./models/v1", "base1")
        self.registry.register_model("v2.0", "./models/v2", "base2")

    def teardown_method(self):
        """Cleanup"""
        shutil.rmtree(self.temp_dir)

    def test_start_test(self):
        """Test starting an A/B test"""
        config = ABTestConfig(
            test_id="test-1",
            control_version="v1.0",
            treatment_version="v2.0",
            traffic_split=0.5,
            start_time=datetime.now().isoformat(),
        )

        result = self.tester.start_test(config)

        assert result["test_id"] == "test-1"
        assert result["status"] == "started"

    def test_record_result(self):
        """Test recording test results"""
        config = ABTestConfig(
            test_id="test-1",
            control_version="v1.0",
            treatment_version="v2.0",
            traffic_split=0.5,
            start_time=datetime.now().isoformat(),
            metrics=["accuracy", "latency"],
        )
        self.tester.start_test(config)

        # Record some results
        self.tester.record_result(
            "test-1", "user1", "control", {"accuracy": 0.85, "latency": 100}
        )
        self.tester.record_result(
            "test-1", "user2", "treatment", {"accuracy": 0.90, "latency": 110}
        )

        result = self._test_results.get("test-1")
        assert result is not None
        assert result.sample_size_control == 1
        assert result.sample_size_treatment == 1


class TestCanaryDeployer:
    """Tests for CanaryDeployer class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(self.temp_dir)
        self.canary = CanaryDeployer(self.registry)

        self.registry.register_model("v1.0", "./models/v1", "base1")
        self.registry.register_model("v2.0", "./models/v2", "base2")

    def teardown_method(self):
        """Cleanup"""
        shutil.rmtree(self.temp_dir)

    def test_start_canary(self):
        """Test starting canary deployment"""
        result = self.canary.start_canary("v1.0", "v2.0")

        assert result["target_version"] == "v2.0"
        assert result["canary_percentage"] == 5  # Default

    def test_promote_canary(self):
        """Test promoting canary"""
        self.canary.start_canary("v1.0", "v2.0")
        result = self.canary.promote_canary()

        assert result["status"] == "promoted"

    def test_rollback_canary(self):
        """Test rolling back canary"""
        self.canary.start_canary("v1.0", "v2.0")
        result = self.canary.rollback_canary()

        assert result["status"] == "rolled_back"

    def test_check_health_pass(self):
        """Test health check passing"""
        self.canary.start_canary("v1.0", "v2.0")

        healthy, message = self.canary.check_health({
            "error_rate": 0.01,
            "latency_increase_pct": 5,
        })

        assert healthy is True
        assert message == "Healthy"

    def test_check_health_fail_error_rate(self):
        """Test health check failing due to error rate"""
        self.canary.start_canary("v1.0", "v2.0")

        healthy, message = self.canary.check_health({
            "error_rate": 0.10,  # Above threshold
            "latency_increase_pct": 5,
        })

        assert healthy is False
        assert "Error rate" in message

    def test_check_health_fail_latency(self):
        """Test health check failing due to latency"""
        self.canary.start_canary("v1.0", "v2.0")

        healthy, message = self.canary.check_health({
            "error_rate": 0.01,
            "latency_increase_pct": 20,  # Above threshold
        })

        assert healthy is False
        assert "Latency" in message


class TestMonitoringDashboard:
    """Tests for MonitoringDashboard class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(self.temp_dir)
        self.monitoring = MonitoringDashboard(self.registry)

    def teardown_method(self):
        """Cleanup"""
        shutil.rmtree(self.temp_dir)

    def test_record_metric(self):
        """Test recording metrics"""
        self.monitoring.record_metric("v1.0", "latency_ms", 150.0)

        metrics = self.monitoring.get_metrics("v1.0", "latency_ms")

        assert len(metrics) == 1
        assert metrics[0]["value"] == 150.0

    def test_get_metrics_with_time_window(self):
        """Test getting metrics with time filter"""
        from datetime import timedelta

        # Record metric
        self.monitoring.record_metric("v1.0", "latency_ms", 150.0)

        # Get with recent time window
        metrics = self.monitoring.get_metrics(
            "v1.0", "latency_ms", time_window=timedelta(minutes=5)
        )

        assert len(metrics) >= 1

    def test_get_summary(self):
        """Test getting metrics summary"""
        # Record multiple metrics
        self.monitoring.record_metric("v1.0", "latency_ms", 100.0)
        self.monitoring.record_metric("v1.0", "latency_ms", 150.0)
        self.monitoring.record_metric("v1.0", "latency_ms", 200.0)
        self.monitoring.record_metric("v1.0", "accuracy", 0.85)

        summary = self.monitoring.get_summary("v1.0")

        assert "latency_ms" in summary
        assert summary["latency_ms"]["count"] == 3
        assert summary["latency_ms"]["min"] == 100.0
        assert summary["latency_ms"]["max"] == 200.0


class TestTestMetrics:
    """Tests for TestMetrics dataclass"""

    def test_default_values(self):
        """Test default values"""
        metrics = TestMetrics()

        assert metrics.control == {}
        assert metrics.treatment == {}
        assert metrics.sample_size_control == 0
        assert metrics.sample_size_treatment == 0
        assert metrics.p_value is None
        assert metrics.significant is False
        assert metrics.winner is None


class TestDeploymentConfig:
    """Tests for DeploymentConfig dataclass"""

    def test_default_values(self):
        """Test default configuration"""
        config = DeploymentConfig()

        assert config.strategy == DeploymentStrategy.CANARY
        assert config.canary_percentage == 5
        assert config.canary_increment == 10
        assert config.max_error_rate == 0.05

    def test_custom_values(self):
        """Test custom configuration"""
        config = DeploymentConfig(
            strategy=DeploymentStrategy.BLUE_GREEN,
            canary_percentage=10,
            max_error_rate=0.10,
        )

        assert config.strategy == DeploymentStrategy.BLUE_GREEN
        assert config.canary_percentage == 10
        assert config.max_error_rate == 0.10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
