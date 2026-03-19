#!/usr/bin/env python3
"""
Fine-Tuning Training Script

Runs LoRA fine-tuning on conversion data for custom model training.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from finetuning.lora_trainer import (
    LoRATrainer,
    TrainingConfig,
    BaseModel,
    FineTuneMethod,
    LoRAConfig,
    Hyperparameters,
    HyperparameterTuner,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune model with LoRA")
    
    # Model
    parser.add_argument(
        "--model",
        type=str,
        default="codellama/CodeLlama-7b-Instruct-hf",
        help="Base model to fine-tune"
    )
    parser.add_argument(
        "--method",
        type=str,
        default="lora",
        choices=["lora", "qlora", "loftq"],
        help="Fine-tuning method"
    )
    
    # LoRA config
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha")
    parser.add_argument("--lora-dropout", type=float, default=0.05, help="LoRA dropout")
    
    # Hyperparameters
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--num-epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    
    # Paths
    parser.add_argument(
        "--train-file",
        type=str,
        required=True,
        help="Training data JSONL file"
    )
    parser.add_argument(
        "--validation-file",
        type=str,
        help="Validation data JSONL file"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./model_checkpoints",
        help="Output directory"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="modporter-v1",
        help="Model name for saving"
    )
    
    # Options
    parser.add_argument(
        "--tune-hyperparameters",
        action="store_true",
        help="Run hyperparameter tuning"
    )
    parser.add_argument(
        "--max-trials",
        type=int,
        default=10,
        help="Max tuning trials"
    )
    
    return parser.parse_args()


async def main():
    args = parse_args()
    
    logger.info("=" * 60)
    logger.info("ModPorter AI Fine-Tuning Pipeline")
    logger.info("=" * 60)
    
    # Create config
    lora_config = LoRAConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
    )
    
    hyperparameters = Hyperparameters(
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        max_seq_length=args.max_seq_length,
    )
    
    config = TrainingConfig(
        base_model=BaseModel(args.model),
        method=FineTuneMethod(args.method),
        lora_config=lora_config,
        hyperparameters=hyperparameters,
        output_dir=args.output_dir,
        train_file=args.train_file,
        validation_file=args.validation_file,
        model_name=args.model_name,
    )
    
    # Check files exist
    if not Path(args.train_file).exists():
        logger.error(f"Training file not found: {args.train_file}")
        sys.exit(1)
    
    if args.validation_file and not Path(args.validation_file).exists():
        logger.error(f"Validation file not found: {args.validation_file}")
        sys.exit(1)
    
    # Run hyperparameter tuning if requested
    if args.tune_hyperparameters:
        logger.info("\n=== Hyperparameter Tuning ===")
        
        param_grid = {
            "r": [8, 16, 32],
            "lora_alpha": [16, 32, 64],
            "lora_dropout": [0.01, 0.05, 0.1],
        }
        
        tuner = HyperparameterTuner(config)
        results = tuner.run_grid_search(
            param_grid,
            args.train_file,
            args.validation_file or "",
            args.max_trials
        )
        
        logger.info("\n=== Tuning Results ===")
        logger.info(f"Best config: {results['best_config']}")
        logger.info(f"Best eval loss: {results['best_loss']}")
        
        # Use best config for final training
        if results['best_config']:
            config = results['best_config']
        else:
            logger.warning("No successful tuning trials, using base config")
    
    # Run training
    logger.info("\n=== Training ===")
    trainer = LoRATrainer(config)
    
    try:
        metrics = trainer.train()
        
        logger.info("\n=== Training Complete ===")
        logger.info(f"Model saved to: {config.output_dir}/{config.model_name}")
        logger.info(f"Train loss: {metrics.get('train_loss', 'N/A')}")
        logger.info(f"Eval loss: {metrics.get('eval_loss', 'N/A')}")
        logger.info(f"Total time: {metrics.get('elapsed_hours', 'N/A')} hours")
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
