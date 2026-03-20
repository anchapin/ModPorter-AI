"""
MLflow Model Registry Integration

Provides MLflow integration for model tracking, versioning,
and registry management.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import tempfile

logger = logging.getLogger(__name__)

# Try to import MLflow
try:
    import mlflow
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logger.warning("MLflow not installed. Using local fallback.")


@dataclass
class MLflowConfig:
    """Configuration for MLflow integration."""
    tracking_uri: str = "http://localhost:5000"
    registry_uri: str = "http://localhost:5000"
    experiment_name: str = "modporter-training"
    artifact_location: str = "./mlartifacts"
    backend_store: str = "sqlite"  # sqlite, postgres


class MLflowRegistry:
    """
    MLflow model registry wrapper.
    
    Provides a unified interface for model tracking and versioning
    with MLflow. Falls back to local storage if MLflow is unavailable.
    """

    def __init__(self, config: Optional[MLflowConfig] = None):
        self.config = config or MLflowConfig()
        self.mlflow_available = MLFLOW_AVAILABLE
        self._client = None
        
        if self.mlflow_available:
            self._setup_mlflow()
        else:
            self._setup_fallback()

    def _setup_mlflow(self):
        """Setup MLflow tracking."""
        try:
            mlflow.set_tracking_uri(self.config.tracking_uri)
            mlflow.set_experiment(self.config.experiment_name)
            
            # Create client for model registry
            self._client = MlflowClient(self.config.registry_uri)
            
            # Ensure artifact directory exists
            Path(self.config.artifact_location).mkdir(parents=True, exist_ok=True)
            
            logger.info(f"MLflow tracking enabled: {self.config.tracking_uri}")
        except Exception as e:
            logger.warning(f"Failed to setup MLflow: {e}. Using local fallback.")
            self.mlflow_available = False
            self._setup_fallback()

    def _setup_fallback(self):
        """Setup local fallback storage."""
        self.fallback_dir = Path("./model_registry/mlflow_fallback")
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using local fallback storage: {self.fallback_dir}")

    def start_run(self, run_name: Optional[str] = None) -> str:
        """
        Start an MLflow run.
        
        Returns:
            Run ID
        """
        if self.mlflow_available:
            run = mlflow.start_run(run_name=run_name)
            return run.info.run_id
        else:
            # Create local run
            run_id = f"local_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            run_dir = self.fallback_dir / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            return run_id

    def end_run(self, run_id: str, status: str = "finished"):
        """End an MLflow run."""
        if self.mlflow_available:
            mlflow.end_run(status=status)
        logger.info(f"Run {run_id} ended with status: {status}")

    def log_metric(self, run_id: str, key: str, value: float, step: Optional[int] = None):
        """Log a metric to the run."""
        if self.mlflow_available:
            mlflow.log_metric(key, value, step)
        else:
            # Save to local file
            self._save_fallback_metric(run_id, key, value, step)

    def log_metrics(self, run_id: str, metrics: Dict[str, float], step: Optional[int] = None):
        """Log multiple metrics."""
        if self.mlflow_available:
            mlflow.log_metrics(metrics, step)
        else:
            for key, value in metrics.items():
                self._save_fallback_metric(run_id, key, value, step)

    def log_param(self, run_id: str, key: str, value: str):
        """Log a parameter."""
        if self.mlflow_available:
            mlflow.log_param(key, value)
        else:
            self._save_fallback_param(run_id, key, value)

    def log_params(self, run_id: str, params: Dict[str, Any]):
        """Log multiple parameters."""
        if self.mlflow_available:
            mlflow.log_params(params)
        else:
            for key, value in params.items():
                self._save_fallback_param(run_id, key, value)

    def log_artifact(self, run_id: str, local_path: str, artifact_path: Optional[str] = None):
        """Log an artifact."""
        if self.mlflow_available:
            mlflow.log_artifact(local_path, artifact_path)
        else:
            self._save_fallback_artifact(run_id, local_path, artifact_path)

    def log_model(self, run_id: str, model_path: str, model_name: str, metadata: Optional[Dict] = None):
        """
        Log a model to the registry.
        
        Args:
            run_id: The MLflow run ID
            model_path: Path to the model directory
            model_name: Name for the model
            metadata: Optional metadata for the model
        """
        if self.mlflow_available:
            # Log the model
            mlflow.log_artifacts(model_path, "model")
            
            # Register model if client available
            if self._client:
                try:
                    # Create model version
                    model_uri = f"runs:/{run_id}/model"
                    model_version = mlflow.register_model(model_uri, model_name)
                    
                    # Add metadata if provided
                    if metadata:
                        self._client.set_model_version_tag(
                            model_name,
                            model_version.version,
                            "metadata",
                            json.dumps(metadata)
                        )
                    
                    logger.info(f"Registered model {model_name} version {model_version.version}")
                except Exception as e:
                    logger.warning(f"Failed to register model: {e}")
        else:
            # Save to local storage
            self._save_fallback_model(run_id, model_path, model_name, metadata)

    def get_model_versions(self, model_name: str) -> List[Dict]:
        """Get all versions of a model."""
        if self.mlflow_available and self._client:
            try:
                versions = self._client.get_latest_versions(model_name)
                return [
                    {
                        "version": v.version,
                        "stage": v.current_stage,
                        "status": v.status,
                        "creation_timestamp": v.creation_timestamp,
                    }
                    for v in versions
                ]
            except Exception as e:
                logger.warning(f"Failed to get model versions: {e}")
        
        return self._get_fallback_model_versions(model_name)

    def transition_model_stage(
        self,
        model_name: str,
        version: int,
        stage: str,
    ) -> bool:
        """
        Transition a model to a new stage.
        
        Stages: Staging, Production, Archived
        """
        if self.mlflow_available and self._client:
            try:
                self._client.transition_model_version_stage(
                    model_name,
                    version,
                    stage,
                )
                logger.info(f"Model {model_name} v{version} transitioned to {stage}")
                return True
            except Exception as e:
                logger.warning(f"Failed to transition model stage: {e}")
                return False
        
        return self._transition_fallback_model_stage(model_name, version, stage)

    def get_best_model(self, metric: str = "eval_loss", direction: str = "minimize") -> Optional[Dict]:
        """Get the best model based on a metric."""
        if self.mlflow_available:
            try:
                # Get experiment
                exp = mlflow.get_experiment_by_name(self.config.experiment_name)
                if not exp:
                    return None
                
                # Query runs
                runs = mlflow.search_runs(
                    experiment_ids=[exp.experiment_id],
                    order_by=[f"metrics.{metric} {'asc' if direction == 'minimize' else 'desc'}"],
                    max_results=1,
                )
                
                if not runs.empty:
                    best_run = runs.iloc[0]
                    return {
                        "run_id": best_run.info.run_id,
                        "metrics": {k: v for k, v in best_run.metrics.items()},
                        "params": {k: v for k, v in best_run.params.items()},
                    }
            except Exception as e:
                logger.warning(f"Failed to get best model: {e}")
        
        return None

    # Fallback methods for local storage
    def _save_fallback_metric(self, run_id: str, key: str, value: float, step: Optional[int]):
        run_dir = self.fallback_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        metrics_file = run_dir / "metrics.json"
        metrics = {}
        if metrics_file.exists():
            with open(metrics_file) as f:
                metrics = json.load(f)
        
        metrics[key] = {"value": value, "step": step}
        
        with open(metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)

    def _save_fallback_param(self, run_id: str, key: str, value: Any):
        run_dir = self.fallback_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        params_file = run_dir / "params.json"
        params = {}
        if params_file.exists():
            with open(params_file) as f:
                params = json.load(f)
        
        params[key] = value
        
        with open(params_file, "w") as f:
            json.dump(params, f, indent=2)

    def _save_fallback_artifact(self, run_id: str, local_path: str, artifact_path: Optional[str]):
        run_dir = self.fallback_dir / run_id
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        dest = artifacts_dir / (artifact_path or Path(local_path).name)
        
        import shutil
        if Path(local_path).is_dir():
            shutil.copytree(local_path, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(local_path, dest)

    def _save_fallback_model(
        self,
        run_id: str,
        model_path: str,
        model_name: str,
        metadata: Optional[Dict],
    ):
        models_dir = self.fallback_dir / "models" / model_name
        versions_dir = models_dir / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        
        # Find latest version
        existing = list(versions_dir.iterdir())
        version = len(existing) + 1
        
        version_dir = versions_dir / f"v{version}"
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy model
        import shutil
        shutil.copytree(model_path, version_dir / "model", dirs_exist_ok=True)
        
        # Save metadata
        if metadata:
            with open(version_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
        
        # Save info
        with open(version_dir / "info.json", "w") as f:
            json.dump({
                "version": version,
                "run_id": run_id,
                "created_at": datetime.now().isoformat(),
            }, f, indent=2)

    def _get_fallback_model_versions(self, model_name: str) -> List[Dict]:
        versions_dir = self.fallback_dir / "models" / model_name / "versions"
        if not versions_dir.exists():
            return []
        
        versions = []
        for v_dir in versions_dir.iterdir():
            if v_dir.is_dir():
                info_file = v_dir / "info.json"
                if info_file.exists():
                    with open(info_file) as f:
                        versions.append(json.load(f))
        
        return sorted(versions, key=lambda v: v.get("version", 0))

    def _transition_fallback_model_stage(
        self,
        model_name: str,
        version: int,
        stage: str,
    ) -> bool:
        versions_dir = self.fallback_dir / "models" / model_name / "versions"
        version_dir = versions_dir / f"v{version}"
        
        if not version_dir.exists():
            return False
        
        # Update stage in info
        info_file = version_dir / "info.json"
        if info_file.exists():
            with open(info_file) as f:
                info = json.load(f)
        else:
            info = {}
        
        info["stage"] = stage
        info["last_updated"] = datetime.now().isoformat()
        
        with open(info_file, "w") as f:
            json.dump(info, f, indent=2)
        
        return True


class MetricsCollector:
    """Collect and aggregate metrics for model monitoring."""

    def __init__(self, mlflow_registry: MLflowRegistry):
        self.registry = mlflow_registry
        self._local_metrics: Dict[str, List[Dict]] = {}

    def collect_conversion_metrics(
        self,
        model_version: str,
        conversion_id: str,
        latency_ms: float,
        success: bool,
        quality_score: Optional[float] = None,
        tokens_used: Optional[int] = None,
    ):
        """Collect metrics from a conversion."""
        metrics = {
            "latency_ms": latency_ms,
            "success": 1.0 if success else 0.0,
            "error": 0.0 if success else 1.0,
        }
        
        if quality_score is not None:
            metrics["quality_score"] = quality_score
        
        if tokens_used is not None:
            metrics["tokens_used"] = tokens_used
        
        # Record in MLflow
        self.registry.log_metric(
            f"model_{model_version}",
            "latency",
            latency_ms,
        )

    def get_latency_stats(
        self,
        model_version: str,
        time_window: Optional[timedelta] = None,
    ) -> Dict[str, float]:
        """Get latency statistics."""
        # In production, this would query MLflow or a metrics DB
        return {
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "mean": 0.0,
            "count": 0,
        }


# Convenience function
def create_mlflow_registry(
    tracking_uri: str = "http://localhost:5000",
    experiment_name: str = "modporter-training",
) -> MLflowRegistry:
    """Create an MLflow registry."""
    config = MLflowConfig(
        tracking_uri=tracking_uri,
        experiment_name=experiment_name,
    )
    return MLflowRegistry(config)
