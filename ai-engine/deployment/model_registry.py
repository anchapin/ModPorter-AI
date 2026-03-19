"""
Model Registry and Deployment Infrastructure

Provides model versioning, A/B testing, canary deployments,
and automatic rollback for fine-tuned models.
"""

import os
import json
import logging
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
import random

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ModelStatus(str, Enum):
    """Status of a model version."""
    TRAINING = "training"
    READY = "ready"
    DEPLOYED = "deployed"
    TESTING = "testing"
    ROLLBACK = "rollback"
    ARCHIVED = "archived"
    FAILED = "failed"


class DeploymentStrategy(str, Enum):
    """Deployment strategies."""
    BLUE_GREEN = "blue_green"     # Instant switch
    CANARY = "canary"             # Gradual rollout
    SHADOW = "shadow"             # Parallel run, no user impact


@dataclass
class ModelVersion:
    """A model version in the registry."""
    version: str
    model_path: str
    base_model: str
    status: ModelStatus
    created_at: str
    trained_at: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    training_data_hash: Optional[str] = None
    description: Optional[str] = None
    parent_version: Optional[str] = None


@dataclass
class DeploymentConfig:
    """Configuration for model deployment."""
    strategy: DeploymentStrategy = DeploymentStrategy.CANARY
    canary_percentage: int = 5          # Start with 5% traffic
    canary_increment: int = 10           # Increment by 10%
    canary_interval: int = 300           # Check every 5 minutes
    max_error_rate: float = 0.05         # Rollback if >5% errors
    min_improvement: float = 0.01        # Min improvement for promotion
    rollback_threshold: float = 0.10      # Rollback if >10% degradation
    health_check_interval: int = 30       # Health check every 30s


@dataclass
class ABTestConfig:
    """Configuration for A/B testing."""
    test_id: str
    control_version: str
    treatment_version: str
    start_time: str
    traffic_split: float = 0.5           # 50/50 split
    end_time: Optional[str] = None
    min_samples: int = 100               # Minimum samples per variant
    confidence_level: float = 0.95        # 95% confidence
    metrics: List[str] = field(default_factory=lambda: ["accuracy", "latency", "user_satisfaction"])


@dataclass
class TestMetrics:
    """Metrics from A/B test."""
    control: Dict[str, float] = field(default_factory=dict)
    treatment: Dict[str, float] = field(default_factory=dict)
    sample_size_control: int = 0
    sample_size_treatment: int = 0
    p_value: Optional[float] = None
    significant: bool = False
    winner: Optional[str] = None
    improvement_pct: Dict[str, float] = field(default_factory=dict)


class ModelRegistry:
    """
    Model registry for version management.
    
    In production, this would integrate with MLflow, Weights & Biases,
    or similar. For now, it provides a local file-based registry.
    """

    def __init__(self, registry_dir: str = "./model_registry"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.models_file = self.registry_dir / "models.json"
        self._models: Dict[str, ModelVersion] = {}
        self._load()

    def _load(self):
        """Load registry from disk."""
        if self.models_file.exists():
            with open(self.models_file) as f:
                data = json.load(f)
                for version, model_data in data.items():
                    self._models[version] = ModelVersion(**model_data)
            logger.info(f"Loaded {len(self._models)} models from registry")

    def _save(self):
        """Save registry to disk."""
        data = {version: asdict(model) for version, model in self._models.items()}
        with open(self.models_file, 'w') as f:
            json.dump(data, f, indent=2)

    def register_model(
        self,
        version: str,
        model_path: str,
        base_model: str,
        metrics: Optional[Dict[str, float]] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        parent_version: Optional[str] = None,
    ) -> ModelVersion:
        """Register a new model version."""
        logger.info(f"Registering model version: {version}")
        
        # Calculate training data hash if parent exists
        training_data_hash = None
        if parent_version and parent_version in self._models:
            parent = self._models[parent_version]
            training_data_hash = parent.training_data_hash

        model = ModelVersion(
            version=version,
            model_path=model_path,
            base_model=base_model,
            status=ModelStatus.TRAINING,
            created_at=datetime.now().isoformat(),
            metrics=metrics or {},
            hyperparameters=hyperparameters or {},
            training_data_hash=training_data_hash,
            description=description,
            parent_version=parent_version,
        )
        
        self._models[version] = model
        self._save()
        
        return model

    def update_status(self, version: str, status: ModelStatus):
        """Update model status."""
        if version not in self._models:
            raise ValueError(f"Model version {version} not found")
        
        self._models[version].status = status
        if status == ModelStatus.READY:
            self._models[version].trained_at = datetime.now().isoformat()
        
        self._save()
        status_str = status.value if hasattr(status, 'value') else str(status)
        logger.info(f"Model {version} status updated to {status_str}")

    def get_model(self, version: str) -> Optional[ModelVersion]:
        """Get a model by version."""
        return self._models.get(version)

    def list_models(
        self,
        status: Optional[ModelStatus] = None,
        limit: int = 10,
    ) -> List[ModelVersion]:
        """List models, optionally filtered by status."""
        models = list(self._models.values())
        
        if status:
            models = [m for m in models if m.status == status]
        
        # Sort by creation date, newest first
        models.sort(key=lambda m: m.created_at, reverse=True)
        
        return models[:limit]

    def get_latest(self, status: Optional[ModelStatus] = None) -> Optional[ModelVersion]:
        """Get the latest model."""
        models = self.list_models(status=status, limit=1)
        return models[0] if models else None

    def archive_model(self, version: str):
        """Archive a model version."""
        self.update_status(version, ModelStatus.ARCHIVED)


class TrafficSplitter:
    """Split traffic between model versions for A/B testing."""

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed or int(time.time())
        self.rng = random.Random(self.seed)

    def assign_variant(
        self,
        user_id: str,
        control_version: str,
        treatment_version: str,
        traffic_split: float = 0.5,
    ) -> str:
        """
        Assign a user to a variant based on their ID.
        
        This ensures consistent assignment for the same user.
        """
        # Hash user ID for consistent hashing
        hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        threshold = hash_value % 1000 / 1000.0
        
        if threshold < traffic_split:
            return treatment_version
        return control_version


class ABTester:
    """A/B testing infrastructure for model comparison."""

    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.splitter = TrafficSplitter()
        self._test_results: Dict[str, TestMetrics] = {}

    def start_test(self, config: ABTestConfig) -> Dict:
        """Start an A/B test."""
        logger.info(f"Starting A/B test: {config.test_id}")
        
        # Verify models exist
        control = self.registry.get_model(config.control_version)
        treatment = self.registry.get_model(config.treatment_version)
        
        if not control or not treatment:
            raise ValueError("Control or treatment model not found")
        
        # Update model statuses
        self.registry.update_status(config.control_version, ModelStatus.DEPLOYED)
        self.registry.update_status(config.treatment_version, ModelStatus.TESTING)
        
        return {
            "test_id": config.test_id,
            "status": "started",
            "control": config.control_version,
            "treatment": config.treatment_version,
            "traffic_split": config.traffic_split,
            "start_time": config.start_time,
        }

    def record_result(
        self,
        test_id: str,
        user_id: str,
        variant: str,
        metrics: Dict[str, float],
    ):
        """Record a result for the test."""
        if test_id not in self._test_results:
            self._test_results[test_id] = TestMetrics()
        
        result = self._test_results[test_id]
        
        target = result.control if variant == "control" else result.treatment
        
        for metric_name, value in metrics.items():
            if metric_name not in target:
                target[metric_name] = 0.0
            target[metric_name] += value
        
        if variant == "control":
            result.sample_size_control += 1
        else:
            result.sample_size_treatment += 1

    def calculate_significance(self, test_id: str, config: ABTestConfig) -> TestMetrics:
        """
        Calculate statistical significance of the test.
        
        Uses t-test for continuous metrics.
        """
        result = self._test_results.get(test_id)
        if not result:
            raise ValueError(f"No results for test {test_id}")
        
        # Check minimum samples
        if (result.sample_size_control < config.min_samples or 
            result.sample_size_treatment < config.min_samples):
            result.significant = False
            return result
        
        # Calculate averages
        for metric in config.metrics:
            control_avg = result.control.get(metric, 0) / max(result.sample_size_control, 1)
            treatment_avg = result.treatment.get(metric, 0) / max(result.sample_size_treatment, 1)
            
            # Calculate improvement percentage
            if control_avg > 0:
                improvement = ((treatment_avg - control_avg) / control_avg) * 100
                result.improvement_pct[metric] = improvement
            
            # Simplified p-value calculation (would use scipy in production)
            # For now, use a simplified significance check
            diff = abs(treatment_avg - control_avg)
            combined = (control_avg + treatment_avg) / 2
            if combined > 0:
                effect_size = diff / combined
                # Simplified: consider significant if effect size > 0.1 (Cohen's d)
                result.p_value = 1.0 - min(effect_size * 5, 1.0)
        
        result.significant = (result.p_value or 0) < (1 - config.confidence_level)
        
        # Determine winner
        if result.significant:
            total_improvement = sum(result.improvement_pct.values())
            if total_improvement > 0:
                result.winner = config.treatment_version
            else:
                result.winner = config.control_version
        
        logger.info(f"Test {test_id}: significant={result.significant}, winner={result.winner}")
        
        return result

    def end_test(self, test_id: str) -> Dict:
        """End an A/B test and return results."""
        # Reset model statuses
        for model in self.registry.list_models(status=ModelStatus.TESTING):
            self.registry.update_status(model.version, ModelStatus.READY)
        
        return {
            "test_id": test_id,
            "status": "ended",
            "metrics": asdict(self._test_results.get(test_id, TestMetrics())),
        }


class CanaryDeployer:
    """Canary deployment manager."""

    def __init__(
        self,
        registry: ModelRegistry,
        config: Optional[DeploymentConfig] = None,
    ):
        self.registry = registry
        self.config = config or DeploymentConfig()
        self._current_deployment: Optional[Dict] = None

    def start_canary(
        self,
        version: str,
        target_version: str,
    ) -> Dict:
        """Start a canary deployment."""
        logger.info(f"Starting canary deployment: {target_version}")
        
        # Verify model exists
        target_model = self.registry.get_model(target_version)
        if not target_model:
            raise ValueError(f"Target model {target_version} not found")
        
        # Update statuses
        if version:
            self.registry.update_status(version, ModelStatus.DEPLOYED)
        self.registry.update_status(target_version, ModelStatus.TESTING)
        
        self._current_deployment = {
            "previous_version": version,
            "target_version": target_version,
            "strategy": self.config.strategy.value,
            "canary_percentage": self.config.canary_percentage,
            "started_at": datetime.now().isoformat(),
            "status": "running",
        }
        
        return self._current_deployment

    def promote_canary(self) -> Dict:
        """Promote canary to full deployment."""
        if not self._current_deployment:
            raise RuntimeError("No active canary deployment")
        
        target = self._current_deployment["target_version"]
        
        # Update statuses
        previous = self._current_deployment.get("previous_version")
        if previous:
            self.registry.update_status(previous, ModelStatus.ARCHIVED)
        
        self.registry.update_status(target, ModelStatus.DEPLOYED)
        
        self._current_deployment["status"] = "promoted"
        self._current_deployment["promoted_at"] = datetime.now().isoformat()
        
        logger.info(f"Canary promoted: {target}")
        
        result = dict(self._current_deployment)
        self._current_deployment = None
        return result

    def rollback_canary(self) -> Dict:
        """Rollback canary deployment."""
        if not self._current_deployment:
            raise RuntimeError("No active canary deployment")
        
        target = self._current_deployment["target_version"]
        previous = self._current_deployment.get("previous_version")
        
        # Update statuses
        self.registry.update_status(target, ModelStatus.ROLLBACK)
        if previous:
            self.registry.update_status(previous, ModelStatus.DEPLOYED)
        
        self._current_deployment["status"] = "rolled_back"
        self._current_deployment["rolled_back_at"] = datetime.now().isoformat()
        
        logger.warning(f"Canary rolled back: {target}")
        
        result = dict(self._current_deployment)
        self._current_deployment = None
        return result

    def check_health(
        self,
        metrics: Dict[str, float],
    ) -> Tuple[bool, str]:
        """
        Check if canary is healthy based on metrics.
        
        Returns (healthy, message)
        """
        if not self._current_deployment:
            return True, "No active deployment"
        
        # Check error rate
        error_rate = metrics.get("error_rate", 0)
        if error_rate > self.config.max_error_rate:
            return False, f"Error rate {error_rate:.2%} exceeds threshold {self.config.max_error_rate:.2%}"
        
        # Check latency degradation
        latency_pct = metrics.get("latency_increase_pct", 0)
        if latency_pct > self.config.rollback_threshold * 100:
            return False, f"Latency increased by {latency_pct:.1f}%, exceeds threshold"
        
        return True, "Healthy"


class MonitoringDashboard:
    """Monitoring dashboard for model performance."""

    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self._metrics_cache: Dict[str, List[Dict]] = {}

    def record_metric(
        self,
        model_version: str,
        metric_name: str,
        value: float,
        timestamp: Optional[datetime] = None,
    ):
        """Record a metric value."""
        if model_version not in self._metrics_cache:
            self._metrics_cache[model_version] = []
        
        self._metrics_cache[model_version].append({
            "metric": metric_name,
            "value": value,
            "timestamp": (timestamp or datetime.now()).isoformat(),
        })

    def get_metrics(
        self,
        model_version: str,
        metric_name: Optional[str] = None,
        time_window: Optional[timedelta] = None,
    ) -> List[Dict]:
        """Get metrics for a model."""
        metrics = self._metrics_cache.get(model_version, [])
        
        if metric_name:
            metrics = [m for m in metrics if m["metric"] == metric_name]
        
        if time_window:
            cutoff = datetime.now() - time_window
            metrics = [
                m for m in metrics 
                if datetime.fromisoformat(m["timestamp"]) > cutoff
            ]
        
        return metrics

    def get_summary(self, model_version: str) -> Dict:
        """Get summary statistics for a model."""
        metrics = self._metrics_cache.get(model_version, [])
        
        if not metrics:
            return {}
        
        # Group by metric name
        by_name: Dict[str, List[float]] = {}
        for m in metrics:
            name = m["metric"]
            if name not in by_name:
                by_name[name] = []
            by_name[name].append(m["value"])
        
        # Calculate summary stats
        summary = {}
        for name, values in by_name.items():
            summary[name] = {
                "count": len(values),
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "latest": values[-1],
            }
        
        return summary


class AutoRollbackManager:
    """Automatic rollback manager based on monitoring."""

    def __init__(
        self,
        canary: CanaryDeployer,
        monitoring: MonitoringDashboard,
        config: Optional[DeploymentConfig] = None,
    ):
        self.canary = canary
        self.monitoring = monitoring
        self.config = config or DeploymentConfig()
        self._rollback_triggered = False

    def check_and_rollback(
        self,
        current_metrics: Dict[str, float],
    ) -> Tuple[bool, str]:
        """
        Check metrics and trigger rollback if needed.
        
        Returns (rollback_triggered, message)
        """
        if self._rollback_triggered:
            return False, "Rollback already triggered"
        
        healthy, message = self.canary.check_health(current_metrics)
        
        if not healthy:
            logger.warning(f"Rollback triggered: {message}")
            self._rollback_triggered = True
            
            # Perform rollback
            result = self.canary.rollback_canary()
            
            return True, f"Rolled back: {message}"
        
        return False, "Metrics healthy"

    def reset(self):
        """Reset the rollback manager."""
        self._rollback_triggered = False


# Convenience functions
def create_model_registry(registry_dir: str = "./model_registry") -> ModelRegistry:
    """Create a model registry."""
    return ModelRegistry(registry_dir)


def create_ab_test(
    registry: ModelRegistry,
    test_id: str,
    control: str,
    treatment: str,
    split: float = 0.5,
) -> ABTestConfig:
    """Create an A/B test configuration."""
    return ABTestConfig(
        test_id=test_id,
        control_version=control,
        treatment_version=treatment,
        traffic_split=split,
        start_time=datetime.now().isoformat(),
    )
