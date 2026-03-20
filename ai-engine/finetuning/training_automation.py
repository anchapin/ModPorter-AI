"""
Training Pipeline Automation

Automated training pipeline with hyperparameter tuning,
checkpoint management, and Modal GPU integration.
"""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class TrainingEnvironment(str, Enum):
    """Training environment options."""
    LOCAL = "local"
    MODAL = "modal"
    COLAB = "colab"
    SAGEMAKER = "sagemaker"


class CheckpointStrategy(str, Enum):
    """Checkpoint saving strategy."""
    BEST = "best"       # Save only best model
    LAST = "last"       # Save only last checkpoint
    ALL = "all"         # Save all checkpoints
    STEPS = "steps"     # Save every N steps


@dataclass
class CheckpointConfig:
    """Configuration for checkpoint management."""
    strategy: CheckpointStrategy = CheckpointStrategy.BEST
    save_steps: int = 500
    save_total_limit: int = 3
    keep_last_n: int = 3
    checkpoint_dir: str = "./model_checkpoints"


@dataclass
class HyperparameterSearchConfig:
    """Configuration for hyperparameter search."""
    method: str = "grid"  # grid, random, bayesian
    metric: str = "eval_loss"
    direction: str = "minimize"  # minimize, maximize
    
    # Learning rate search
    learning_rates: List[float] = field(default_factory=lambda: [1e-4, 3e-4, 5e-4, 1e-3])
    
    # Batch size search
    batch_sizes: List[int] = field(default_factory=lambda: [2, 4, 8])
    
    # LoRA rank search
    lora_ranks: List[int] = field(default_factory=lambda: [8, 16, 32])
    
    # Epochs
    epochs: List[int] = field(default_factory=lambda: [2, 3, 5])
    
    max_trials: int = 10


@dataclass
class TrainingRun:
    """Record of a training run."""
    run_id: str
    start_time: str
    end_time: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    config: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    checkpoint_path: Optional[str] = None
    best_checkpoint: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ModalConfig:
    """Configuration for Modal GPU training."""
    gpu_type: str = "a10g"  # a10g, a100, h100
    gpu_count: int = 1
    timeout: int = 3600  # seconds
    memory: int = 32000  # MB
    cpu: int = 4
    volume_mount: Optional[str] = None


class TrainingAutomation:
    """
    Automated training pipeline with:
    - Hyperparameter search
    - Checkpoint management
    - Modal GPU integration
    - Training orchestration
    """

    def __init__(
        self,
        base_output_dir: str = "./training_runs",
        checkpoint_config: Optional[CheckpointConfig] = None,
        modal_config: Optional[ModalConfig] = None,
    ):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_config = checkpoint_config or CheckpointConfig()
        self.modal_config = modal_config or ModalConfig()
        
        # Training runs storage
        self.runs_file = self.base_output_dir / "runs.jsonl"
        
        # Active training process
        self.active_run: Optional[TrainingRun] = None

    def create_run(
        self,
        config: Dict[str, Any],
        training_data_path: str,
        validation_data_path: Optional[str] = None,
    ) -> TrainingRun:
        """Create a new training run."""
        run_id = self._generate_run_id(config)
        
        run = TrainingRun(
            run_id=run_id,
            start_time=datetime.now().isoformat(),
            config={
                **config,
                "training_data": training_data_path,
                "validation_data": validation_data_path,
                "checkpoint_config": asdict(self.checkpoint_config),
            },
        )
        
        # Save run to file
        self._save_run(run)
        
        logger.info(f"Created training run: {run_id}")
        return run

    def get_run(self, run_id: str) -> Optional[TrainingRun]:
        """Get a training run by ID."""
        with open(self.runs_file) as f:
            for line in f:
                if line.strip():
                    run = json.loads(line)
                    if run.get("run_id") == run_id:
                        return TrainingRun(**run)
        return None

    def list_runs(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[TrainingRun]:
        """List training runs."""
        runs = []
        if not self.runs_file.exists():
            return runs
        
        with open(self.runs_file) as f:
            for line in f:
                if line.strip():
                    run = json.loads(line)
                    if status is None or run.get("status") == status:
                        runs.append(TrainingRun(**run))
        
        return runs[:limit]

    def update_run(self, run: TrainingRun):
        """Update a training run."""
        self._save_run(run)

    def _save_run(self, run: TrainingRun):
        """Save run to file (append or update)."""
        runs = []
        if self.runs_file.exists():
            with open(self.runs_file) as f:
                for line in f:
                    if line.strip():
                        r = json.loads(line)
                        if r.get("run_id") != run.run_id:
                            runs.append(r)
        
        runs.append(asdict(run))
        
        with open(self.runs_file, "w") as f:
            for run in runs:
                f.write(json.dumps(run) + "\n")

    def generate_hyperparameter_search(
        self,
        base_config: Dict[str, Any],
        search_config: HyperparameterSearchConfig,
    ) -> List[Dict[str, Any]]:
        """Generate hyperparameter search configurations."""
        configs = []
        
        if search_config.method == "grid":
            # Grid search over all combinations
            for lr in search_config.learning_rates:
                for bs in search_config.batch_sizes:
                    for rank in search_config.lora_ranks:
                        for epochs in search_config.epochs:
                            config = {
                                **base_config,
                                "learning_rate": lr,
                                "per_device_train_batch_size": bs,
                                "lora_r": rank,
                                "num_train_epochs": epochs,
                            }
                            configs.append(config)
        
        elif search_config.method == "random":
            import random
            # Random search (sample from ranges)
            for _ in range(search_config.max_trials):
                config = {
                    **base_config,
                    "learning_rate": random.choice(search_config.learning_rates),
                    "per_device_train_batch_size": random.choice(search_config.batch_sizes),
                    "lora_r": random.choice(search_config.lora_ranks),
                    "num_train_epochs": random.choice(search_config.epochs),
                }
                configs.append(config)
        
        # Limit to max_trials
        return configs[:search_config.max_trials]

    def run_hyperparameter_search(
        self,
        base_config: Dict[str, Any],
        search_config: HyperparameterSearchConfig,
        training_data_path: str,
        validation_data_path: Optional[str] = None,
        train_fn: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Run hyperparameter search.
        
        Args:
            base_config: Base configuration for all runs
            search_config: Search configuration
            training_data_path: Path to training data
            validation_data_path: Path to validation data
            train_fn: Function to run training (if None, just generate configs)
            
        Returns:
            Summary of best run and all results
        """
        configs = self.generate_hyperparameter_search(base_config, search_config)
        
        results = []
        best_run = None
        best_metric = float("inf") if search_config.direction == "minimize" else float("-inf")
        
        for i, config in enumerate(configs):
            logger.info(f"Running trial {i+1}/{len(configs)}: {config}")
            
            # Create run
            run = self.create_run(config, training_data_path, validation_data_path)
            
            if train_fn:
                try:
                    # Run training
                    run.status = "running"
                    self.update_run(run)
                    
                    # Execute training function
                    metrics = train_fn(config)
                    
                    # Update run with results
                    run.status = "completed"
                    run.end_time = datetime.now().isoformat()
                    run.metrics = metrics
                    
                    # Check if best
                    metric_value = metrics.get(search_config.metric)
                    if metric_value is not None:
                        if search_config.direction == "minimize":
                            is_better = metric_value < best_metric
                        else:
                            is_better = metric_value > best_metric
                        
                        if is_better:
                            best_metric = metric_value
                            best_run = run
                    
                    results.append(asdict(run))
                    
                except Exception as e:
                    logger.error(f"Trial {i+1} failed: {e}")
                    run.status = "failed"
                    run.error_message = str(e)
                    run.end_time = datetime.now().isoformat()
                    results.append(asdict(run))
            else:
                # Just create configs without running
                results.append(config)
        
        summary = {
            "search_method": search_config.method,
            "total_trials": len(configs),
            "best_metric": best_metric,
            "best_config": asdict(best_run.config) if best_run else None,
            "best_run_id": best_run.run_id if best_run else None,
            "results": results,
        }
        
        return summary

    def get_checkpoint_path(
        self,
        run_id: str,
        checkpoint_name: str = "best"
    ) -> Optional[Path]:
        """Get path to a checkpoint."""
        run_dir = self.base_output_dir / run_id
        
        if checkpoint_name == "best":
            checkpoint_path = run_dir / "best_checkpoint"
        else:
            checkpoint_path = run_dir / "checkpoints" / checkpoint_name
        
        if checkpoint_path.exists():
            return checkpoint_path
        return None

    def cleanup_checkpoints(
        self,
        run_id: str,
        keep_best: bool = True,
        keep_last: bool = True
    ) -> int:
        """Clean up old checkpoints based on strategy."""
        run_dir = self.base_output_dir / run_id
        if not run_dir.exists():
            return 0
        
        removed = 0
        checkpoints_dir = run_dir / "checkpoints"
        
        if not checkpoints_dir.exists():
            return 0
        
        # Get list of checkpoints (by modification time)
        checkpoints = sorted(
            checkpoints_dir.iterdir(),
            key=lambda p: p.stat().st_mtime
        )
        
        # Keep best and last if configured
        to_keep = set()
        if keep_best:
            to_keep.add("best_checkpoint")
        if keep_last and checkpoints:
            to_keep.add(checkpoints[-1].name)
        
        for checkpoint in checkpoints:
            if checkpoint.name not in to_keep:
                if checkpoint.is_dir():
                    shutil.rmtree(checkpoint)
                else:
                    checkpoint.unlink()
                removed += 1
        
        logger.info(f"Cleaned up {removed} checkpoints for run {run_id}")
        return removed

    def get_best_checkpoint(self, metric: str = "eval_loss") -> Optional[Path]:
        """Get the best checkpoint across all runs."""
        runs = self.list_runs(status="completed")
        
        best_run = None
        best_metric = float("inf")
        
        for run in runs:
            run_metric = run.metrics.get(metric, float("inf"))
            if run_metric < best_metric:
                best_metric = run_metric
                best_run = run
        
        if best_run and best_run.best_checkpoint:
            return Path(best_run.best_checkpoint)
        
        return None

    def _generate_run_id(self, config: Dict[str, Any]) -> str:
        """Generate unique run ID from config."""
        config_str = json.dumps(config, sort_keys=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(config_str.encode()).hexdigest()[:6]
        return f"run_{timestamp}_{hash_suffix}"


class ModalGPUManager:
    """Manager for Modal GPU training instances."""

    def __init__(self, config: ModalConfig):
        self.config = config
        self.modal_available = False
        
        # Try to import modal
        try:
            import modal
            self.modal = modal
            self.modal_available = True
        except ImportError:
            logger.warning("Modal not available. Running in local mode.")

    def is_available(self) -> bool:
        """Check if Modal is available."""
        return self.modal_available

    def deploy_training(
        self,
        training_script: str,
        gpu_type: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Deploy training job to Modal.
        
        Returns:
            Job ID for tracking
        """
        if not self.modal_available:
            raise RuntimeError("Modal is not available")
        
        gpu = gpu_type or self.config.gpu_type
        
        # This would create a Modal function with GPU
        # In practice, you'd define the function with @modal.cloud_gpu()
        
        logger.info(f"Deploying training to Modal with {gpu} GPU")
        
        # Return placeholder job ID
        return f"modal_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a Modal job."""
        # In practice, this would query Modal API
        return {
            "job_id": job_id,
            "status": "running",  # pending, running, completed, failed
            "logs": [],
        }

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running Modal job."""
        logger.info(f"Cancelling Modal job: {job_id}")
        return True


# Integration with existing LoRA trainer
def create_automated_training_config(
    base_model: str = "codellama/CodeLlama-7b-Instruct-hf",
    output_dir: str = "./model_checkpoints",
    train_file: Optional[str] = None,
    val_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a complete training configuration."""
    return {
        "base_model": base_model,
        "output_dir": output_dir,
        "train_file": train_file,
        "validation_file": val_file,
        "model_name": "modporter-v1",
        
        # LoRA config
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
        
        # Training hyperparameters
        "learning_rate": 3e-4,
        "num_train_epochs": 3,
        "per_device_train_batch_size": 4,
        "per_device_eval_batch_size": 8,
        "gradient_accumulation_steps": 4,
        "max_seq_length": 2048,
        
        # Evaluation and saving
        "eval_strategy": "steps",
        "eval_steps": 100,
        "save_strategy": "steps",
        "save_steps": 500,
        "logging_steps": 50,
        "warmup_steps": 100,
        
        # Other
        "fp16": True,
        "save_total_limit": 3,
        "load_best_model_at_end": True,
        "metric_for_best_model": "eval_loss",
    }
