"""
LoRA Fine-Tuning Infrastructure for Minecraft Mod Conversion

This module provides infrastructure for fine-tuning language models
using LoRA (Low-Rank Adaptation) for efficient training.
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    EarlyStoppingCallback,
)
from peft import (
    LoraConfig,
    get_peft_model,
    TaskType,
    LoftQConfig,
)
from datasets import Dataset
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class BaseModel(Enum):
    """Supported base models for fine-tuning."""
    CODE_LLAMA_7B = "codellama/CodeLlama-7b-Instruct-hf"
    CODE_LLAMA_13B = "codellama/CodeLlama-13b-Instruct-hf"
    DEEPSEEK_CODER = "deepseek-ai/deepseek-coder-6.7b-instruct"
    STARCODER = "bigcode/starcoder2-7b"
    PHI_2 = "microsoft/phi-2"


class FineTuneMethod(Enum):
    """Fine-tuning methods."""
    LORA = "lora"           # Standard LoRA
    QLORA = "qlora"        # Quantized LoRA
    LOFTQ = "loftq"        # LoRA + LoftQ quantization


@dataclass
class LoRAConfig:
    """LoRA configuration parameters."""
    r: int = 16             # LoRA rank
    lora_alpha: int = 32    # LoRA alpha
    lora_dropout: float = 0.05
    target_modules: List[str] = field(default_factory=lambda: ["q_proj", "v_proj", "k_proj", "o_proj"])
    bias: str = "none"      # "none", "all", "lora_only"
    task_type: TaskType = TaskType.CAUSAL_LM


@dataclass
class Hyperparameters:
    """Training hyperparameters."""
    learning_rate: float = 3e-4
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 8
    gradient_accumulation_steps: int = 4
    eval_strategy: str = "steps"
    eval_steps: int = 100
    save_strategy: str = "steps"
    save_steps: int = 500
    logging_steps: int = 50
    warmup_steps: int = 100
    max_seq_length: int = 2048
    weight_decay: float = 0.01
    fp16: bool = True
    save_total_limit: int = 3
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "eval_loss"


@dataclass
class TrainingConfig:
    """Complete training configuration."""
    base_model: BaseModel = BaseModel.CODE_LLAMA_7B
    method: FineTuneMethod = FineTuneMethod.LORA
    lora_config: LoRAConfig = field(default_factory=LoRAConfig)
    hyperparameters: Hyperparameters = field(default_factory=Hyperparameters)
    output_dir: str = "./model_checkpoints"
    logging_dir: str = "./logs"
    train_file: Optional[str] = None
    validation_file: Optional[str] = None
    model_name: str = "modporter-v1"


@dataclass
class TrainingMetrics:
    """Training metrics."""
    train_loss: float = 0.0
    eval_loss: float = 0.0
    epoch: int = 0
    total_steps: int = 0
    learning_rate: float = 0.0
    elapsed_time: float = 0.0
    estimated_remaining_time: float = 0.0


class LoRATrainer:
    """LoRA fine-tuning trainer for mod conversion models."""

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.trainer = None
        self.training_metrics = TrainingMetrics()
        
        # Setup output directories
        self.output_dir = Path(config.output_dir)
        self.logging_dir = Path(config.logging_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logging_dir.mkdir(parents=True, exist_ok=True)

    def load_model_and_tokenizer(self) -> Tuple[Any, Any]:
        """Load base model and tokenizer."""
        logger.info(f"Loading base model: {self.config.base_model.value}")
        
        # Determine device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.base_model.value,
            trust_remote_code=True,
        )
        
        # Set padding token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model with appropriate precision
        if self.config.method == FineTuneMethod.QLORA:
            # Quantized loading for QLoRA
            load_kwargs = {
                "torch_dtype": torch.float16,
                "load_in_4bit": True,
                "device_map": "auto",
            }
        else:
            load_kwargs = {
                "torch_dtype": torch.float16 if self.config.hyperparameters.fp16 else torch.float32,
                "device_map": "auto",
            }
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.base_model.value,
            **load_kwargs
        )
        
        # Configure gradient checkpointing for memory efficiency
        if hasattr(self.model, "gradient_checkpointing_enable"):
            self.model.gradient_checkpointing_enable()
        
        logger.info("Model and tokenizer loaded successfully")
        return self.model, self.tokenizer

    def apply_lora(self) -> Any:
        """Apply LoRA to the model."""
        logger.info(f"Applying {self.config.method.value} with config: {self.config.lora_config}")
        
        # Create LoRA config
        if self.config.method == FineTuneMethod.LOFTQ:
            loftq_config = LoftQConfig(quantization_config="bits = 4")
            lora_config = LoraConfig(
                r=self.config.lora_config.r,
                lora_alpha=self.config.lora_config.lora_alpha,
                lora_dropout=self.config.lora_config.lora_dropout,
                target_modules=self.config.lora_config.target_modules,
                bias=self.config.lora_config.bias,
                task_type=self.config.lora_config.task_type,
                loftq_config=loftq_config,
            )
        else:
            lora_config = LoraConfig(
                r=self.config.lora_config.r,
                lora_alpha=self.config.lora_config.lora_alpha,
                lora_dropout=self.config.lora_config.lora_dropout,
                target_modules=self.config.lora_config.target_modules,
                bias=self.config.lora_config.bias,
                task_type=self.config.lora_config.task_type,
            )
        
        # Apply LoRA
        self.model = get_peft_model(self.model, lora_config)
        
        # Print trainable parameters
        self.model.print_trainable_parameters()
        
        logger.info("LoRA applied successfully")
        return self.model

    def load_training_data(self) -> Tuple[Dataset, Dataset]:
        """Load and prepare training data."""
        logger.info("Loading training data...")
        
        def load_jsonl(file_path: str) -> List[Dict]:
            data = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
            return data
        
        # Load training data
        train_data = []
        if self.config.train_file:
            train_data = load_jsonl(self.config.train_file)
            logger.info(f"Loaded {len(train_data)} training examples")
        
        # Load validation data
        val_data = []
        if self.config.validation_file:
            val_data = load_jsonl(self.config.validation_file)
            logger.info(f"Loaded {len(val_data)} validation examples")
        
        # Convert to HF datasets
        train_dataset = Dataset.from_list(train_data)
        val_dataset = Dataset.from_list(val_data) if val_data else None
        
        # Tokenize
        def tokenize_function(examples):
            # Extract messages and create prompt/completion pairs
            texts = []
            for example in examples["messages"]:
                # Format: [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]
                prompt = ""
                completion = ""
                for msg in example:
                    if msg["role"] == "system":
                        continue
                    elif msg["role"] == "user":
                        prompt += msg["content"] + "\n"
                    elif msg["role"] == "assistant":
                        completion += msg["content"]
                
                # Combine with prompt template
                text = f"### Instruction:\n{prompt}\n### Response:\n{completion}"
                texts.append(text)
            
            # Tokenize
            tokenized = self.tokenizer(
                texts,
                truncation=True,
                max_length=self.config.hyperparameters.max_seq_length,
                padding="max_length",
            )
            
            # Set labels (same as input for causal LM)
            tokenized["labels"] = tokenized["input_ids"].copy()
            
            return tokenized
        
        train_dataset = train_dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=train_dataset.column_names,
        )
        
        if val_dataset:
            val_dataset = val_dataset.map(
                tokenize_function,
                batched=True,
                remove_columns=val_dataset.column_names,
            )
        
        return train_dataset, val_dataset

    def create_trainer(self, train_dataset: Dataset, eval_dataset: Optional[Dataset]):
        """Create the HuggingFace Trainer."""
        logger.info("Creating trainer...")
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,  # Causal LM, not masked LM
        )
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            logging_dir=str(self.logging_dir),
            **asdict(self.config.hyperparameters),
        )
        
        # Create trainer
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
        )
        
        logger.info("Trainer created successfully")
        return self.trainer

    def train(self) -> Dict[str, Any]:
        """Run the training process."""
        logger.info("=" * 60)
        logger.info("Starting Training")
        logger.info("=" * 60)
        logger.info(f"Base Model: {self.config.base_model.value}")
        logger.info(f"Method: {self.config.method.value}")
        logger.info(f"Output Directory: {self.output_dir}")
        
        # Load model
        self.load_model_and_tokenizer()
        
        # Apply LoRA
        self.apply_lora()
        
        # Load data
        train_dataset, eval_dataset = self.load_training_data()
        
        # Create trainer
        self.create_trainer(train_dataset, eval_dataset)
        
        # Train
        logger.info("Starting training...")
        start_time = datetime.now()
        
        train_result = self.trainer.train()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Training completed in {elapsed/3600:.2f} hours")
        
        # Save model
        logger.info("Saving model...")
        self.trainer.save_model(str(self.output_dir / self.config.model_name))
        self.tokenizer.save_pretrained(str(self.output_dir / self.config.model_name))
        
        # Save metrics
        metrics = {
            "train_loss": train_result.training_loss,
            "eval_loss": train_result.metrics.get("eval_loss", 0),
            "total_steps": train_result.global_step,
            "elapsed_hours": elapsed / 3600,
            "model_name": self.config.model_name,
            "base_model": self.config.base_model.value,
            "method": self.config.method.value,
            "lora_config": asdict(self.config.lora_config),
            "hyperparameters": asdict(self.config.hyperparameters),
        }
        
        # Save metrics to JSON
        metrics_path = self.output_dir / "training_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Metrics saved to {metrics_path}")
        
        return metrics

    def evaluate(self) -> Dict[str, float]:
        """Evaluate the model."""
        if not self.trainer:
            raise RuntimeError("Trainer not initialized. Run train() first.")
        
        logger.info("Running evaluation...")
        metrics = self.trainer.evaluate()
        
        logger.info("Evaluation metrics:")
        for key, value in metrics.items():
            logger.info(f"  {key}: {value}")
        
        return metrics


class HyperparameterTuner:
    """Hyperparameter tuning system for LoRA training."""

    def __init__(self, base_config: TrainingConfig):
        self.base_config = base_config
        self.results: List[Dict] = []

    def run_grid_search(
        self,
        param_grid: Dict[str, List[Any]],
        train_file: str,
        validation_file: str,
        max_trials: int = 10
    ) -> Dict[str, Any]:
        """
        Run hyperparameter search.
        
        Args:
            param_grid: Dictionary of parameters to search
            max_trials: Maximum number of trials
        """
        logger.info(f"Starting hyperparameter search with {max_trials} trials")
        
        # Generate parameter combinations
        import itertools
        keys = list(param_grid.keys())
        values = [param_grid[k] for k in keys]
        combinations = list(itertools.product(*values))[:max_trials]
        
        best_config = None
        best_loss = float('inf')
        
        for i, combo in enumerate(combinations):
            logger.info(f"\n--- Trial {i+1}/{len(combinations)} ---")
            
            # Create config for this trial
            trial_config = TrainingConfig(
                base_model=self.base_config.base_model,
                method=self.base_config.method,
                lora_config=LoRAConfig(**{
                    k: v for k, v in zip(keys, combo) 
                    if k in ['r', 'lora_alpha', 'lora_dropout']
                }),
                hyperparameters=self.base_config.hyperparameters,
                output_dir=f"{self.base_config.output_dir}/trial_{i}",
                train_file=train_file,
                validation_file=validation_file,
                model_name=f"trial_{i}"
            )
            
            # Train
            trainer = LoRATrainer(trial_config)
            try:
                metrics = trainer.train()
                eval_loss = metrics.get("eval_loss", float('inf'))
                
                self.results.append({
                    "trial": i,
                    "params": dict(zip(keys, combo)),
                    "eval_loss": eval_loss,
                    "status": "success"
                })
                
                if eval_loss < best_loss:
                    best_loss = eval_loss
                    best_config = trial_config
                    
            except Exception as e:
                logger.error(f"Trial {i} failed: {e}")
                self.results.append({
                    "trial": i,
                    "params": dict(zip(keys, combo)),
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(f"\nBest configuration: {best_config.lora_config if best_config else 'None'}")
        logger.info(f"Best eval loss: {best_loss}")
        
        return {
            "best_config": best_config,
            "best_loss": best_loss,
            "all_results": self.results
        }


class CheckpointManager:
    """Manage model checkpoints during training."""

    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoints: List[Dict] = []

    def list_checkpoints(self) -> List[Dict]:
        """List all available checkpoints."""
        if not self.checkpoint_dir.exists():
            return []
        
        for ckpt in self.checkpoint_dir.iterdir():
            if ckpt.is_dir() and ckpt.name.startswith("checkpoint-"):
                metrics_file = ckpt / "trainer_state.json"
                if metrics_file.exists():
                    with open(metrics_file) as f:
                        state = json.load(f)
                        self.checkpoints.append({
                            "path": str(ckpt),
                            "step": state.get("global_step", 0),
                            "epoch": state.get("epoch", 0),
                            "metrics": state.get("metrics", {})
                        })
        
        # Sort by step
        self.checkpoints.sort(key=lambda x: x["step"], reverse=True)
        return self.checkpoints

    def get_best_checkpoint(self, metric: str = "eval_loss", mode: str = "min") -> Optional[Dict]:
        """Get the best checkpoint based on a metric."""
        checkpoints = self.list_checkpoints()
        
        if not checkpoints:
            return None
        
        best = checkpoints[0]
        for ckpt in checkpoints:
            metrics = ckpt.get("metrics", {}).get("metrics", {})
            if metric in metrics:
                if mode == "min":
                    if metrics[metric] < best["metrics"].get("metrics", {}).get(metric, float('inf')):
                        best = ckpt
                else:
                    if metrics[metric] > best["metrics"].get("metrics", {}).get(metric, 0):
                        best = ckpt
        
        return best

    def load_checkpoint(self, checkpoint_path: str):
        """Load a checkpoint."""
        logger.info(f"Loading checkpoint: {checkpoint_path}")
        
        model = AutoModelForCausalLM.from_pretrained(
            checkpoint_path,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        tokenizer = AutoTokenizer.from_pretrained(checkpoint_path)
        
        return model, tokenizer


# Convenience functions
def create_lora_trainer(
    model_name: str = "codellama/CodeLlama-7b-Instruct-hf",
    method: FineTuneMethod = FineTuneMethod.LORA,
    output_dir: str = "./model_checkpoints",
    train_file: Optional[str] = None,
    validation_file: Optional[str] = None,
) -> LoRATrainer:
    """Create a LoRA trainer with default configuration."""
    config = TrainingConfig(
        base_model=BaseModel(model_name),
        method=method,
        output_dir=output_dir,
        train_file=train_file,
        validation_file=validation_file,
    )
    return LoRATrainer(config)
