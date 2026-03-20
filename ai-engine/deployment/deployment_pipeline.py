"""
Complete Deployment Pipeline

Orchestrates model deployment with MLflow, A/B testing,
canary deployments, monitoring, and automatic rollback.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum

from deployment.model_registry import (
    ModelRegistry,
    ModelStatus,
    DeploymentConfig,
    DeploymentStrategy,
    ABTestConfig,
    CanaryDeployer,
    MonitoringDashboard,
    AutoRollbackManager,
    TrafficSplitter,
    ABTester,
)
from deployment.mlflow_integration import (
    MLflowRegistry,
    MLflowConfig,
    MetricsCollector,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DeploymentStage(str, Enum):
    """Deployment stages."""
    REGISTRY = "registry"
    TESTING = "testing"
    CANARY = "canary"
    PRODUCTION = "production"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentPipelineConfig:
    """Configuration for deployment pipeline."""
    # Registry settings
    registry_dir: str = "./model_registry"
    mlflow_tracking_uri: str = "http://localhost:5000"
    experiment_name: str = "modporter-training"
    
    # Canary settings
    canary_percentage: int = 5
    canary_increment: int = 10
    canary_interval: int = 300  # seconds
    max_error_rate: float = 0.05
    
    # A/B testing settings
    ab_test_min_samples: int = 100
    ab_confidence_level: float = 0.95
    
    # Monitoring settings
    metrics_retention_days: int = 30
    alert_webhook: Optional[str] = None


@dataclass
class DeploymentStatus:
    """Status of a deployment."""
    stage: DeploymentStage
    model_version: str
    deployed_at: str
    traffic_percentage: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    health_status: str = "healthy"
    message: str = ""


class DeploymentPipeline:
    """
    Complete deployment pipeline for fine-tuned models.
    
    Handles:
    - Model registration with MLflow
    - A/B testing setup
    - Canary deployment
    - Monitoring and metrics
    - Automatic rollback
    """

    def __init__(self, config: DeploymentPipelineConfig):
        self.config = config
        
        # Initialize components
        self.registry = ModelRegistry(config.registry_dir)
        self.mlflow = MLflowRegistry(MLflowConfig(
            tracking_uri=config.mlflow_tracking_uri,
            experiment_name=config.experiment_name,
        ))
        
        # Initialize deployment components
        deployment_config = DeploymentConfig(
            strategy=DeploymentStrategy.CANARY,
            canary_percentage=config.canary_percentage,
            canary_increment=config.canary_increment,
            canary_interval=config.canary_interval,
            max_error_rate=config.max_error_rate,
        )
        
        self.canary_deployer = CanaryDeployer(self.registry, deployment_config)
        self.monitoring = MonitoringDashboard(self.registry)
        self.rollback_manager = AutoRollbackManager(
            self.canary_deployer,
            self.monitoring,
            deployment_config,
        )
        self.ab_tester = ABTester(self.registry)
        
        # Metrics collector
        self.metrics_collector = MetricsCollector(self.mlflow)
        
        # Traffic splitter for A/B
        self.traffic_splitter = TrafficSplitter()
        
        # Current deployment state
        self.current_deployment: Optional[DeploymentStatus] = None

    def register_and_stage(
        self,
        model_path: str,
        version: str,
        base_model: str,
        metrics: Dict[str, float],
        hyperparameters: Dict[str, Any],
        description: Optional[str] = None,
    ) -> str:
        """
        Register a new model and prepare for deployment.
        
        Returns:
            Model version string
        """
        logger.info(f"Registering model: {version}")
        
        # Register in local registry
        model = self.registry.register_model(
            version=version,
            model_path=model_path,
            base_model=base_model,
            metrics=metrics,
            hyperparameters=hyperparameters,
            description=description,
        )
        
        # Also register in MLflow
        run_id = self.mlflow.start_run(run_name=f"register_{version}")
        self.mlflow.log_metrics(run_id, metrics)
        self.mlflow.log_params(run_id, hyperparameters)
        self.mlflow.log_model(run_id, model_path, f"modporter-{version}")
        self.mlflow.end_run(run_id, "finished")
        
        # Update status to ready
        self.registry.update_status(version, ModelStatus.READY)
        
        logger.info(f"Model {version} registered and ready")
        return version

    def start_canary_deployment(
        self,
        version: str,
        current_version: Optional[str] = None,
    ) -> DeploymentStatus:
        """Start a canary deployment."""
        logger.info(f"Starting canary deployment for {version}")
        
        # Get current production version if not specified
        if not current_version:
            current_model = self.registry.get_latest(status=ModelStatus.DEPLOYED)
            current_version = current_model.version if current_model else None
        
        # Start canary
        deployment_info = self.canary_deployer.start_canary(
            version=current_version,
            target_version=version,
        )
        
        # Create status
        self.current_deployment = DeploymentStatus(
            stage=DeploymentStage.CANARY,
            model_version=version,
            deployed_at=datetime.now().isoformat(),
            traffic_percentage=self.config.canary_percentage,
            message=f"Canary deployment started at {self.config.canary_percentage}%",
        )
        
        logger.info(f"Canary deployment started: {version} at {self.config.canary_percentage}%")
        return self.current_deployment

    def promote_canary(self) -> DeploymentStatus:
        """Promote canary to full production."""
        if not self.current_deployment:
            raise RuntimeError("No active canary deployment")
        
        result = self.canary_deployer.promote_canary()
        
        self.current_deployment = DeploymentStatus(
            stage=DeploymentStage.PRODUCTION,
            model_version=result["target_version"],
            deployed_at=result.get("promoted_at", datetime.now().isoformat()),
            traffic_percentage=100.0,
            message="Canary promoted to full production",
        )
        
        logger.info(f"Canary promoted to production")
        return self.current_deployment

    def rollback(self) -> DeploymentStatus:
        """Rollback current deployment."""
        result = self.canary_deployer.rollback_canary()
        
        previous = result.get("previous_version", "unknown")
        
        self.current_deployment = DeploymentStatus(
            stage=DeploymentStage.ROLLED_BACK,
            model_version=previous,
            deployed_at=datetime.now().isoformat(),
            traffic_percentage=100.0,
            message=f"Rolled back to {previous}",
        )
        
        logger.warning(f"Rolled back to {previous}")
        return self.current_deployment

    def start_ab_test(
        self,
        test_id: str,
        control_version: str,
        treatment_version: str,
        traffic_split: float = 0.5,
    ) -> Dict:
        """Start an A/B test."""
        logger.info(f"Starting A/B test: {test_id}")
        
        config = ABTestConfig(
            test_id=test_id,
            control_version=control_version,
            treatment_version=treatment_version,
            traffic_split=traffic_split,
            start_time=datetime.now().isoformat(),
            min_samples=self.config.ab_test_min_samples,
            confidence_level=self.config.ab_confidence_level,
        )
        
        result = self.ab_tester.start_test(config)
        
        return result

    def assign_to_variant(
        self,
        test_id: str,
        user_id: str,
        control_version: str,
        treatment_version: str,
        traffic_split: float = 0.5,
    ) -> str:
        """Assign a user to a test variant."""
        return self.traffic_splitter.assign_variant(
            user_id=user_id,
            control_version=control_version,
            treatment_version=treatment_version,
            traffic_split=traffic_split,
        )

    def record_ab_result(
        self,
        test_id: str,
        user_id: str,
        variant: str,
        metrics: Dict[str, float],
    ):
        """Record a result for A/B test."""
        self.ab_tester.record_result(test_id, user_id, variant, metrics)

    def get_ab_results(self, test_id: str) -> Dict:
        """Get A/B test results with statistical analysis."""
        # Get config (would need to store it properly in production)
        config = ABTestConfig(
            test_id=test_id,
            control_version="",
            treatment_version="",
            start_time="",
        )
        
        # Calculate significance
        results = self.ab_tester.calculate_significance(test_id, config)
        
        return {
            "test_id": test_id,
            "significant": results.significant,
            "winner": results.winner,
            "p_value": results.p_value,
            "improvement": results.improvement_pct,
            "sample_size": {
                "control": results.sample_size_control,
                "treatment": results.sample_size_treatment,
            },
        }

    def record_metric(
        self,
        model_version: str,
        metric_name: str,
        value: float,
    ):
        """Record a metric for monitoring."""
        self.monitoring.record_metric(model_version, metric_name, value)

    def check_health_and_rollback(
        self,
        current_metrics: Dict[str, float],
    ) -> bool:
        """Check health and trigger rollback if needed."""
        if not self.current_deployment:
            return False
        
        should_rollback, message = self.rollback_manager.check_and_rollback(current_metrics)
        
        if should_rollback:
            self.rollback()
            logger.warning(f"Auto-rollback triggered: {message}")
            return True
        
        return False

    def get_deployment_status(self) -> DeploymentStatus:
        """Get current deployment status."""
        if not self.current_deployment:
            return DeploymentStatus(
                stage=DeploymentStage.REGISTRY,
                model_version="none",
                deployed_at=datetime.now().isoformat(),
                message="No active deployment",
            )
        
        # Update metrics
        if self.current_deployment.model_version != "none":
            summary = self.monitoring.get_summary(self.current_deployment.model_version)
            self.current_deployment.metrics = summary
        
        return self.current_deployment

    def get_model_metrics(
        self,
        model_version: str,
        time_window: Optional[timedelta] = None,
    ) -> Dict:
        """Get metrics for a specific model."""
        summary = self.monitoring.get_summary(model_version)
        
        # Get latency breakdown
        latency_metrics = self.monitoring.get_metrics(
            model_version,
            "latency",
            time_window,
        )
        
        return {
            "summary": summary,
            "latency_samples": len(latency_metrics),
        }


class DeploymentAutomation:
    """Automated deployment workflow."""

    def __init__(self, pipeline: DeploymentPipeline):
        self.pipeline = pipeline
        self._running = False

    async def run_canary_with_monitoring(
        self,
        version: str,
        current_version: Optional[str] = None,
        check_interval: int = 60,
        max_promotions: int = 10,
        metrics_fn: Optional[Callable] = None,
    ) -> DeploymentStatus:
        """
        Run canary deployment with automatic promotion/rollback.
        
        Args:
            version: New model version to deploy
            current_version: Current production version
            check_interval: Seconds between health checks
            max_promotions: Maximum number of promotion steps
            metrics_fn: Function to get current metrics
            
        Returns:
            Final deployment status
        """
        logger.info(f"Starting automated canary deployment for {version}")
        
        # Start canary
        status = self.pipeline.start_canary_deployment(version, current_version)
        
        promotions = 0
        self._running = True
        
        while self._running and promotions < max_promotions:
            # Wait before checking
            await asyncio.sleep(check_interval)
            
            # Get current metrics
            current_metrics = {}
            if metrics_fn:
                try:
                    current_metrics = metrics_fn()
                except Exception as e:
                    logger.error(f"Error getting metrics: {e}")
                    current_metrics = {}
            
            # Check for rollback
            if self.pipeline.check_health_and_rollback(current_metrics):
                logger.warning("Canary failed health check, rolled back")
                break
            
            # Check if ready for promotion
            traffic = status.traffic_percentage
            
            if traffic >= 100:
                logger.info("Canary fully promoted!")
                break
            
            # Calculate next traffic level
            next_traffic = min(
                traffic + self.pipeline.config.canary_increment,
                100.0
            )
            
            # Log progress
            logger.info(f"Canary at {traffic}% traffic, metrics: {current_metrics}")
            
            # Update status
            status.traffic_percentage = next_traffic
            
            if next_traffic >= 100:
                # Full promotion
                status = self.pipeline.promote_canary()
                break
            
            promotions += 1
        
        return status

    def stop(self):
        """Stop the automated deployment."""
        self._running = False
        logger.info("Deployment automation stopped")


# Example usage
def create_deployment_pipeline(
    registry_dir: str = "./model_registry",
    mlflow_uri: str = "http://localhost:5000",
) -> DeploymentPipeline:
    """Create a deployment pipeline."""
    config = DeploymentPipelineConfig(
        registry_dir=registry_dir,
        mlflow_tracking_uri=mlflow_uri,
    )
    return DeploymentPipeline(config)
